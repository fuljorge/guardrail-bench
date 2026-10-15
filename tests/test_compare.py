from __future__ import annotations

from guardbench.analysis import Targets
from guardbench.collect import Measurement
from guardbench.compare import comparison

PI, TOX = "pi_strands_decider", "tox_strands_decider"


def suite(attack_score: float, legit_score: float) -> list[Measurement]:
    def m(id_: str, label: str, category: str, score: float) -> Measurement:
        detector = "none" if label == "legit" else "prompt_injection"
        return Measurement(id_, label, "input", detector, category, False, 0.1,
                           {PI: score, TOX: 0.0}, {PI: 10.0, TOX: 5.0}, 1.0)  # fmt: skip

    attacks = [m(f"a{i}", "attack", "injection_direct", attack_score) for i in range(40)]
    legit = [m(f"l{i}", "legit", "billing", legit_score if i < 4 else 0.0) for i in range(100)]
    return attacks + legit


def test_comparison_reports_both_languages_and_the_difference() -> None:
    text = comparison(suite(0.9, 0.0), suite(0.2, 0.9), Targets())

    assert "PT-BR: 140 texts (40 attacks, 100 legitimate)" in text
    # Production thresholds (0.35): every attack blocked in the first suite, none in the second.
    assert (
        "| Production: `pi_strands_decider` (0.35) + `tox_strands_decider` (0.50) "
        "| 100.0% | 0.0% | -100.0" in text
    )
    # Four legitimate texts at 0.9 in the second suite: 4% false positives there.
    assert "| 0.00% | 4.00% |" in text
    assert "| Direct injection | 40 / 40 | 100% | 0% |" in text
