"""Analysis of a measurement file: per-stage blocking rules, threshold search and statistics.

Blocking rules per stage follow the platform's pipeline:
- `input` (customer message): local layer, or injection detector, or toxicity detector;
- `indirect` (documents, tool results): local layer, or injection detector;
- `output` (agent reply): toxicity detector only.

A pair is one injection candidate (`pi_*`) and one toxicity candidate (`tox_*`), each with a
threshold from 0.05 to 0.95 in steps of 0.05. The selection rule for a pair is: among the
threshold combinations with false positives below the target, the one that blocks the most;
if none is below the target, the lowest false-positive rate.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass, field

from .collect import Measurement
from .stats import mcnemar_exact, percentile, wilson

THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]


@dataclass(frozen=True)
class Targets:
    """Acceptance targets of the platform's specification (stage 1, before revision)."""

    block: float = 0.95
    false_positive: float = 0.02
    input_ms: float = 150.0
    output_ms: float = 300.0


@dataclass(frozen=True)
class PairResult:
    injection: str
    toxicity: str
    t_injection: float
    t_toxicity: float
    blocked: int
    attacks: int
    false_positives: int
    legit: int
    input_p95_ms: float
    output_p95_ms: float
    by_category: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def block_rate(self) -> float:
        return self.blocked / self.attacks if self.attacks else 0.0

    @property
    def fp_rate(self) -> float:
        return self.false_positives / self.legit if self.legit else 0.0

    def meets(self, targets: Targets) -> bool:
        return (
            self.block_rate >= targets.block
            and self.fp_rate < targets.false_positive
            and self.input_p95_ms <= targets.input_ms
            and self.output_p95_ms <= targets.output_ms
        )


def candidates_of(data: Sequence[Measurement]) -> tuple[list[str], list[str]]:
    names = sorted({name for m in data for name in m.scores})
    return [n for n in names if n.startswith("pi_")], [n for n in names if n.startswith("tox_")]


def blocked(m: Measurement, pi: str, tox: str, t_pi: float, t_tox: float) -> bool:
    hit_pi = m.scores.get(pi, 0.0) >= t_pi
    hit_tox = m.scores.get(tox, 0.0) >= t_tox
    if m.stage == "input":
        return m.local or hit_pi or hit_tox
    if m.stage == "indirect":
        return m.local or hit_pi
    return hit_tox


def evaluate_pair(
    data: Sequence[Measurement], pi: str, tox: str, t_pi: float, t_tox: float
) -> PairResult:
    attacks = [m for m in data if m.label == "attack"]
    legit = [m for m in data if m.label == "legit"]
    hits = [blocked(m, pi, tox, t_pi, t_tox) for m in attacks]
    categories: dict[str, list[bool]] = {}
    for m, hit in zip(attacks, hits, strict=True):
        categories.setdefault(m.category, []).append(hit)
    # Latency as the pipeline would see it: local layer + network + the models of the stage
    # (in the collection, the candidates of a request run one after another on the server).
    input_ms = [
        m.local_ms + m.http_ms + m.model_ms.get(pi, 0.0) + m.model_ms.get(tox, 0.0)
        for m in data
        if m.stage == "input"
    ]
    output_ms = [m.http_ms + m.model_ms.get(tox, 0.0) for m in data if m.stage == "output"]
    return PairResult(
        pi,
        tox,
        t_pi,
        t_tox,
        sum(hits),
        len(attacks),
        sum(blocked(m, pi, tox, t_pi, t_tox) for m in legit),
        len(legit),
        percentile(input_ms, 0.95),
        percentile(output_ms, 0.95),
        {k: (sum(v), len(v)) for k, v in sorted(categories.items())},
    )


def _rank(r: PairResult, targets: Targets) -> tuple[bool, float, float]:
    below = r.fp_rate < targets.false_positive
    return (below, r.block_rate if below else -r.fp_rate, -r.fp_rate)


def best_thresholds(data: Sequence[Measurement], pi: str, tox: str, targets: Targets) -> PairResult:
    options = [evaluate_pair(data, pi, tox, a, b) for a in THRESHOLDS for b in THRESHOLDS]
    return max(options, key=lambda r: _rank(r, targets))


def search(data: Sequence[Measurement], targets: Targets) -> list[PairResult]:
    pis, toxes = candidates_of(data)
    best = [best_thresholds(data, pi, tox, targets) for pi in pis for tox in toxes]
    return sorted(best, key=lambda r: _rank(r, targets), reverse=True)


@dataclass(frozen=True)
class AloneRow:
    threshold: float
    blocked: int
    attacks: int
    false_positives: int
    legit: int


def detector_alone(data: Sequence[Measurement], name: str) -> list[AloneRow]:
    """Model only, no local layer: attacks of its own detector vs all legitimate texts."""
    kind = "prompt_injection" if name.startswith("pi_") else "toxicity"
    attacks = [m for m in data if m.label == "attack" and m.detector == kind]
    legit = [m for m in data if m.label == "legit"]
    return [
        AloneRow(
            t,
            sum(m.scores.get(name, 0.0) >= t for m in attacks),
            len(attacks),
            sum(m.scores.get(name, 0.0) >= t for m in legit),
            len(legit),
        )
        for t in THRESHOLDS
    ]


def local_only(data: Sequence[Measurement]) -> tuple[int, int, int, int]:
    """(injection attacks blocked, injection attacks, false positives, legitimate)."""
    attacks = [m for m in data if m.label == "attack" and m.detector == "prompt_injection"]
    legit = [m for m in data if m.label == "legit"]
    return sum(m.local for m in attacks), len(attacks), sum(m.local for m in legit), len(legit)


def model_p95(data: Sequence[Measurement], name: str) -> float:
    return percentile([m.model_ms[name] for m in data if name in m.model_ms], 0.95)


@dataclass(frozen=True)
class CrossValidated:
    blocked: int
    attacks: int
    false_positives: int
    legit: int
    thresholds: list[tuple[float, float]]


def cross_validate(
    data: Sequence[Measurement],
    pi: str,
    tox: str,
    targets: Targets,
    *,
    folds: int = 5,
    seed: int = 0,
) -> CrossValidated:
    """Thresholds chosen on k-1 folds and applied to the held-out fold, stratified by label.

    The in-sample search picks the thresholds on the same texts it reports, which is
    optimistic; the pooled held-out counts estimate the rate on unseen texts.
    """
    rng = random.Random(seed)
    fold_of: dict[str, int] = {}
    for label in ("attack", "legit"):
        ids = sorted(m.id for m in data if m.label == label)
        rng.shuffle(ids)
        fold_of.update({id_: i % folds for i, id_ in enumerate(ids)})
    totals = [0, 0, 0, 0]
    chosen = []
    for k in range(folds):
        train = [m for m in data if fold_of[m.id] != k]
        test = [m for m in data if fold_of[m.id] == k]
        fit = best_thresholds(train, pi, tox, targets)
        chosen.append((fit.t_injection, fit.t_toxicity))
        held = evaluate_pair(test, pi, tox, fit.t_injection, fit.t_toxicity)
        for i, value in enumerate((held.blocked, held.attacks, held.false_positives, held.legit)):
            totals[i] += value
    return CrossValidated(totals[0], totals[1], totals[2], totals[3], chosen)


def paired_attacks(
    data: Sequence[Measurement], first: PairResult, second: PairResult, label: str = "attack"
) -> tuple[int, int, float]:
    """Exact McNemar on the same texts: (only first blocks, only second blocks, p-value)."""
    rows = [m for m in data if m.label == label]
    a = [
        blocked(m, first.injection, first.toxicity, first.t_injection, first.t_toxicity)
        for m in rows
    ]
    b = [
        blocked(m, second.injection, second.toxicity, second.t_injection, second.t_toxicity)
        for m in rows
    ]
    only_a = sum(x and not y for x, y in zip(a, b, strict=True))
    only_b = sum(y and not x for x, y in zip(a, b, strict=True))
    return only_a, only_b, mcnemar_exact(only_a, only_b)


def interval(hits: int, n: int) -> tuple[float, float]:
    return wilson(hits, n)
