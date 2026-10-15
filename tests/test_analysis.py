from __future__ import annotations

from guardbench.analysis import (
    Targets,
    blocked,
    cross_validate,
    detector_alone,
    evaluate_pair,
    local_only,
    search,
)
from guardbench.collect import Measurement


def m(id_: str, label: str, stage: str, pi: float, tox: float, *, local: bool = False,
      category: str = "c", detector: str = "prompt_injection") -> Measurement:  # fmt: skip
    return Measurement(id_, label, stage, detector if label == "attack" else "none", category,
                       local, 0.1, {"pi_a": pi, "tox_b": tox}, {"pi_a": 10.0, "tox_b": 5.0},
                       1.0)  # fmt: skip


def test_rules_per_stage() -> None:
    assert blocked(m("1", "attack", "input", 0.0, 0.9), "pi_a", "tox_b", 0.5, 0.5)
    assert blocked(m("2", "attack", "input", 0.0, 0.0, local=True), "pi_a", "tox_b", 0.5, 0.5)
    # Indirect content: toxicity does not count.
    assert not blocked(m("3", "attack", "indirect", 0.0, 0.9), "pi_a", "tox_b", 0.5, 0.5)
    # Output: only toxicity counts; the local layer never runs on output.
    assert not blocked(m("4", "attack", "output", 0.9, 0.0), "pi_a", "tox_b", 0.5, 0.5)
    assert blocked(m("5", "attack", "output", 0.0, 0.9), "pi_a", "tox_b", 0.5, 0.5)


def test_evaluate_counts_and_latency() -> None:
    data = [m("a1", "attack", "input", 0.9, 0.0, category="x"),
            m("a2", "attack", "input", 0.2, 0.0, category="y"),
            m("l1", "legit", "input", 0.6, 0.0), m("l2", "legit", "input", 0.1, 0.0)]  # fmt: skip

    r = evaluate_pair(data, "pi_a", "tox_b", 0.5, 0.5)

    assert (r.blocked, r.attacks, r.false_positives, r.legit) == (1, 2, 1, 2)
    assert r.by_category == {"x": (1, 1), "y": (0, 1)}
    assert r.input_p95_ms == 0.1 + 1.0 + 10.0 + 5.0


def test_search_prefers_most_blocking_under_the_fp_target() -> None:
    attacks = [m(f"a{i}", "attack", "input", i / 10, 0.0) for i in range(10)]
    legit = [m(f"l{i}", "legit", "input", 0.05, 0.0) for i in range(100)]
    legit[0] = m("l0", "legit", "input", 0.45, 0.0)

    best = search(attacks + legit, Targets())[0]

    # 0.45 would block one legitimate text (1% < 2%): allowed, and blocks the most.
    assert best.t_injection == 0.1
    assert best.false_positives == 1


def test_cross_validation_is_deterministic() -> None:
    data = [m(f"a{i}", "attack", "input", (i % 10) / 10, 0.0) for i in range(50)]
    data += [m(f"l{i}", "legit", "input", 0.05, 0.0) for i in range(100)]

    first = cross_validate(data, "pi_a", "tox_b", Targets(), folds=5)
    second = cross_validate(data, "pi_a", "tox_b", Targets(), folds=5)

    assert first == second
    assert first.attacks == 50 and first.legit == 100


def test_detector_alone_and_local_layer() -> None:
    data = [m("a1", "attack", "input", 0.9, 0.0, local=True),
            m("a2", "attack", "input", 0.1, 0.8, detector="toxicity"),
            m("l1", "legit", "input", 0.1, 0.0)]  # fmt: skip

    rows = {r.threshold: r for r in detector_alone(data, "pi_a")}

    assert (rows[0.5].blocked, rows[0.5].attacks) == (1, 1)
    assert local_only(data) == (1, 1, 0, 1)
