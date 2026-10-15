"""Markdown report of a measurement file: every table in `docs/results.md` comes from here."""

from __future__ import annotations

from collections.abc import Sequence

from .analysis import (
    Targets,
    candidates_of,
    cross_validate,
    detector_alone,
    interval,
    local_only,
    model_p95,
    paired_attacks,
    search,
)
from .collect import Measurement

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


def ci(hits: int, n: int, digits: int = 1) -> str:
    low, high = interval(hits, n)
    return f"{pct(hits / n if n else 0.0, digits)} [{pct(low, digits)}, {pct(high, digits)}]"


def alone_table(data: Sequence[Measurement], names: list[str]) -> list[str]:
    cuts = (0.3, 0.5, 0.7, 0.9)
    lines = [
        "| Candidate | " + " | ".join(f"t = {t:.2f}" for t in cuts) + " | Model p95 |",
        "|---|" + "---|" * (len(cuts) + 1),
    ]
    for name in names:
        rows = {r.threshold: r for r in detector_alone(data, name)}
        cells = [
            f"{pct(rows[t].blocked / rows[t].attacks, 0)} / {pct(rows[t].false_positives / rows[t].legit)}"
            for t in cuts
        ]
        lines.append(f"| `{name}` | " + " | ".join(cells) + f" | {model_p95(data, name):.0f} ms |")
    return lines


def markdown(data: Sequence[Measurement], targets: Targets, *, top: int = 8, folds: int = 5) -> str:
    attacks = sum(m.label == "attack" for m in data)
    legit = len(data) - attacks
    pis, toxes = candidates_of(data)
    out = [
        f"Texts: {len(data)} ({attacks} attacks, {legit} legitimate). Candidates: "
        f"{len(pis)} injection, {len(toxes)} toxicity. Targets: block ≥ {pct(targets.block, 0)}, "
        f"false positives < {pct(targets.false_positive, 0)}, input p95 ≤ {targets.input_ms:.0f} ms, "
        f"output p95 ≤ {targets.output_ms:.0f} ms.",
        "",
    ]
    lb, la, lf, ll = local_only(data)
    out += [
        "### Local layer alone",
        "",
        f"Injection attacks blocked: {ci(lb, la)} ({lb}/{la}); false positives: {ci(lf, ll, 2)} ({lf}/{ll}).",
        "",
        "### Each candidate alone (model only; own attacks blocked / false positives)",
        "",
        *alone_table(data, pis + toxes),
        "",
    ]
    pairs = search(data, targets)
    out += [
        f"### Best pairs (local layer + two models; best thresholds with false positives < {pct(targets.false_positive, 0)})",
        "",
        "| Injection (t) | Toxicity (t) | Blocked [95% CI] | False positives [95% CI] | Input p95 | Output p95 | Meets |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in pairs[:top]:
        out.append(
            f"| `{r.injection}` ({r.t_injection:.2f}) | `{r.toxicity}` ({r.t_toxicity:.2f}) "
            f"| {ci(r.blocked, r.attacks)} | {ci(r.false_positives, r.legit, 2)} "
            f"| {r.input_p95_ms:.0f} ms | {r.output_p95_ms:.0f} ms | {'yes' if r.meets(targets) else 'no'} |"
        )
    out += [
        "",
        "### By attack category (same pairs and thresholds)",
        "",
        "| Pair | "
        + " | ".join(f"{title} (n={_n(pairs[0], key)})" for key, title in CATEGORIES)
        + " |",
        "|---|" + "---|" * len(CATEGORIES),
    ]
    for r in pairs[:top]:
        cells = [
            pct(r.by_category[key][0] / r.by_category[key][1], 0) if key in r.by_category else "—"
            for key, _ in CATEGORIES
        ]
        out.append(f"| `{r.injection}` + `{r.toxicity}` | " + " | ".join(cells) + " |")
    out += [
        "",
        f"### Threshold selection, {folds}-fold cross-validation (held-out counts pooled)",
        "",
        "| Pair | In-sample blocked / FP | Held-out blocked [95% CI] | Held-out FP [95% CI] | Thresholds per fold |",
        "|---|---|---|---|---|",
    ]
    for r in pairs[: min(top, 4)]:
        cv = cross_validate(data, r.injection, r.toxicity, targets, folds=folds)
        chosen = ", ".join(f"{a:.2f}/{b:.2f}" for a, b in cv.thresholds)
        out.append(
            f"| `{r.injection}` + `{r.toxicity}` | {pct(r.block_rate)} / {pct(r.fp_rate, 2)} "
            f"| {ci(cv.blocked, cv.attacks)} | {ci(cv.false_positives, cv.legit, 2)} | {chosen} |"
        )
    if len(pairs) > 1:
        out += [
            "",
            "### Paired comparison with the best pair (exact McNemar on the same texts)",
            "",
            "| Other pair | Attacks: only best / only other, p | Legitimate: only best / only other, p |",
            "|---|---|---|",
        ]
        for r in pairs[1:top]:
            a1, a2, ap = paired_attacks(data, pairs[0], r)
            l1, l2, lp = paired_attacks(data, pairs[0], r, label="legit")
            out.append(
                f"| `{r.injection}` + `{r.toxicity}` | {a1} / {a2}, p = {ap:.2g} | {l1} / {l2}, p = {lp:.2g} |"
            )
    return "\n".join(out) + "\n"


def _n(r: object, key: str) -> int:
    by = getattr(r, "by_category", {})
    return int(by[key][1]) if key in by else 0
