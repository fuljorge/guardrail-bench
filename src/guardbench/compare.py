"""Markdown comparison of two measurement files: the same candidates on two suites.

    guardbench compare results/v0.1.0/measurements.json results/v0.2.0-enus/measurements.json

The two suites are written separately (not translated), so their texts are independent
samples: rates are compared with the Newcombe interval for the difference and the
two-sided Fisher exact test, never with paired tests. Three views:

- **each candidate and the local layer alone**, at a fixed threshold (no search): the
  language effect on the model itself;
- **fixed configurations**: the production pair and each language's best pair, with their
  thresholds, applied unchanged to both suites (does a configuration chosen in one language
  carry over to the other?);
- **best pair per language**, with thresholds searched again on each suite.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from .analysis import (
    PairResult,
    Targets,
    candidates_of,
    detector_alone,
    evaluate_pair,
    local_only,
    model_p95,
    search,
)
from .collect import Measurement
from .stats import fisher_exact, newcombe

Config = tuple[str, str, float, float]  # injection, toxicity, their thresholds

# The configuration the Implementation Project chose with the PT-BR results.
PRODUCTION: Config = ("pi_strands_decider", "tox_strands_decider", 0.35, 0.50)
ALONE_THRESHOLD = 0.50

CATEGORIES = [
    ("injection_direct", "Direct injection"),
    ("jailbreak", "Jailbreak"),
    ("injection_indirect", "Indirect injection"),
    ("mixed_language", "Language mix"),
    ("offensive", "Offensive"),
    ("prompt_leak", "Prompt leak"),
    ("data_exfiltration", "Third-party data"),
]


def pct(x: float, digits: int = 1) -> str:
    return f"{100 * x:.{digits}f}%"


def rate(hits: int, n: int, digits: int = 1) -> str:
    return pct(hits / n if n else 0.0, digits)


def difference(a: tuple[int, int], b: tuple[int, int], digits: int = 1) -> str:
    """b - a in points, with its 95% Newcombe interval and the Fisher p-value."""
    low, high = newcombe(b[0], b[1], a[0], a[1])
    d = (b[0] / b[1] if b[1] else 0.0) - (a[0] / a[1] if a[1] else 0.0)
    p = fisher_exact(a[0], a[1], b[0], b[1])
    return f"{100 * d:+.{digits}f} [{100 * low:+.{digits}f}, {100 * high:+.{digits}f}], p = {p:.2g}"


def without_local(data: Sequence[Measurement]) -> list[Measurement]:
    """The same measurements as if the pipeline had no local layer."""
    return [replace(m, local=False) for m in data]


def _sizes(data: Sequence[Measurement]) -> tuple[int, int]:
    attacks = sum(m.label == "attack" for m in data)
    return attacks, len(data) - attacks


def _alone(data: Sequence[Measurement], name: str) -> tuple[tuple[int, int], tuple[int, int]]:
    row = next(r for r in detector_alone(data, name) if r.threshold == ALONE_THRESHOLD)
    return (row.blocked, row.attacks), (row.false_positives, row.legit)


def _fixed_rows(
    first: Sequence[Measurement], second: Sequence[Measurement], configs: list[tuple[str, Config]]
) -> list[str]:
    lines = []
    for label, (pi, tox, t_pi, t_tox) in configs:
        a = evaluate_pair(first, pi, tox, t_pi, t_tox)
        b = evaluate_pair(second, pi, tox, t_pi, t_tox)
        lines.append(
            f"| {label}: `{pi}` ({t_pi:.2f}) + `{tox}` ({t_tox:.2f}) "
            f"| {rate(a.blocked, a.attacks)} | {rate(b.blocked, b.attacks)} "
            f"| {difference((a.blocked, a.attacks), (b.blocked, b.attacks))} "
            f"| {rate(a.false_positives, a.legit, 2)} | {rate(b.false_positives, b.legit, 2)} "
            f"| {difference((a.false_positives, a.legit), (b.false_positives, b.legit), 2)} |"
        )
    return lines


def _config(r: PairResult) -> Config:
    return (r.injection, r.toxicity, r.t_injection, r.t_toxicity)


def comparison(
    first: Sequence[Measurement],
    second: Sequence[Measurement],
    targets: Targets,
    *,
    names: tuple[str, str] = ("PT-BR", "EN-US"),
    top: int = 5,
) -> str:
    na, nb = names
    (a_atk, a_leg), (b_atk, b_leg) = _sizes(first), _sizes(second)
    out = [
        f"{na}: {len(first)} texts ({a_atk} attacks, {a_leg} legitimate). "
        f"{nb}: {len(second)} texts ({b_atk} attacks, {b_leg} legitimate). "
        f"Differences are {nb} minus {na}, in percentage points, with 95% Newcombe intervals "
        "and two-sided Fisher exact p-values (independent samples).",
        "",
    ]

    la, lb = local_only(first), local_only(second)
    pis_a, toxes_a = candidates_of(first)
    pis_b, toxes_b = candidates_of(second)
    shared = [n for n in pis_a + toxes_a if n in set(pis_b + toxes_b)]
    out += [
        f"### Each candidate alone (model only, threshold {ALONE_THRESHOLD:.2f})",
        "",
        f"| Candidate | Blocked {na} | Blocked {nb} | Difference | FP {na} | FP {nb} | Difference "
        f"| Model p95 {na} / {nb} |",
        "|---|---|---|---|---|---|---|---|",
        f"| local layer (injection attacks) | {rate(la[0], la[1])} | {rate(lb[0], lb[1])} "
        f"| {difference(la[:2], lb[:2])} | {rate(la[2], la[3], 2)} | {rate(lb[2], lb[3], 2)} "
        f"| {difference(la[2:], lb[2:], 2)} | — |",
    ]
    for name in shared:
        (ab, af), (bb, bf) = _alone(first, name), _alone(second, name)
        out.append(
            f"| `{name}` | {rate(*ab, 0)} | {rate(*bb, 0)} | {difference(ab, bb)} "
            f"| {rate(*af)} | {rate(*bf)} | {difference(af, bf)} "
            f"| {model_p95(first, name):.0f} / {model_p95(second, name):.0f} ms |"
        )

    best_a, best_b = search(first, targets), search(second, targets)
    configs: list[tuple[str, Config]] = [("Production", PRODUCTION)]
    if best_a and _config(best_a[0]) != PRODUCTION:
        configs.append((f"Best in {na}", _config(best_a[0])))
    if best_b and _config(best_b[0]) not in (PRODUCTION, _config(best_a[0]) if best_a else None):
        configs.append((f"Best in {nb}", _config(best_b[0])))
    out += [
        "",
        "### Fixed configurations (same pair and thresholds on both suites)",
        "",
        f"| Configuration | Blocked {na} | Blocked {nb} | Difference | FP {na} | FP {nb} "
        "| Difference |",
        "|---|---|---|---|---|---|---|",
        *_fixed_rows(first, second, configs),
    ]

    prod_a, prod_b = evaluate_pair(first, *PRODUCTION), evaluate_pair(second, *PRODUCTION)
    out += [
        "",
        "### Production configuration by attack category",
        "",
        f"| Category | n {na} / {nb} | Blocked {na} | Blocked {nb} | Difference |",
        "|---|---|---|---|---|",
    ]
    for key, title in CATEGORIES:
        a = prod_a.by_category.get(key, (0, 0))
        b = prod_b.by_category.get(key, (0, 0))
        out.append(
            f"| {title} | {a[1]} / {b[1]} | {rate(*a, 0)} | {rate(*b, 0)} | {difference(a, b)} |"
        )

    out += [
        "",
        "### Local layer contribution (production thresholds; best pair searched without it)",
        "",
        "| Suite | Production | Production, no local layer | Best pair, no local layer |",
        "|---|---|---|---|",
    ]
    for suite, data, prod in ((na, first, prod_a), (nb, second, prod_b)):
        bare = without_local(data)
        no_local = evaluate_pair(bare, *PRODUCTION)
        best = search(bare, targets)[0]
        out.append(
            f"| {suite} | {rate(prod.blocked, prod.attacks)} / "
            f"{rate(prod.false_positives, prod.legit, 2)} "
            f"| {rate(no_local.blocked, no_local.attacks)} / "
            f"{rate(no_local.false_positives, no_local.legit, 2)} "
            f"| `{best.injection}` ({best.t_injection:.2f}) + `{best.toxicity}` "
            f"({best.t_toxicity:.2f}): {rate(best.blocked, best.attacks)} / "
            f"{rate(best.false_positives, best.legit, 2)} |"
        )

    out += [
        "",
        f"### Best pairs, thresholds searched on each suite (false positives < "
        f"{pct(targets.false_positive, 0)})",
        "",
        "| Suite | Injection (t) | Toxicity (t) | Blocked | False positives | Meets |",
        "|---|---|---|---|---|---|",
    ]
    for suite, pairs in ((na, best_a), (nb, best_b)):
        for r in pairs[:top]:
            out.append(
                f"| {suite} | `{r.injection}` ({r.t_injection:.2f}) | `{r.toxicity}` "
                f"({r.t_toxicity:.2f}) | {rate(r.blocked, r.attacks)} "
                f"| {rate(r.false_positives, r.legit, 2)} | {'yes' if r.meets(targets) else 'no'} |"
            )
    return "\n".join(out) + "\n"
