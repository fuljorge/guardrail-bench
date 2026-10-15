from __future__ import annotations

import filecmp
from collections import Counter
from pathlib import Path

import pytest

from guardbench.suite import FILES, LANGS, bank_for, load_suite, write_suite

DATA = Path(__file__).parents[1] / "data"
SIZES = {"pt-br": (575, 1091), "en-us": (575, 1080)}


@pytest.mark.parametrize("lang", LANGS)
def test_generator_reproduces_the_published_files(tmp_path: Path, lang: str) -> None:
    assert write_suite(tmp_path, lang) == SIZES[lang]
    for name in bank_for(lang).files:
        assert filecmp.cmp(tmp_path / name, DATA / name, shallow=False), name


def test_default_files_are_the_ptbr_suite() -> None:
    assert FILES == ("attacks_ptbr.jsonl", "legit_ptbr.jsonl")


@pytest.mark.parametrize("lang", LANGS)
def test_rows_are_well_formed(lang: str) -> None:
    rows = load_suite(DATA, lang)
    ids = [r["id"] for r in rows]
    attacks, legit = SIZES[lang]

    assert len(ids) == len(set(ids)) == attacks + legit
    assert Counter(r["label"] for r in rows) == {"attack": attacks, "legit": legit}
    assert {r["stage"] for r in rows} == {"input", "indirect", "output"}
    for r in rows:
        assert (r["detector"] == "none") == (r["label"] == "legit"), r["id"]


def test_both_suites_have_the_same_attack_shape() -> None:
    def shape(lang: str) -> Counter[tuple[str, str, str]]:
        rows = load_suite(DATA, lang)
        return Counter(
            (r["category"], r["stage"], r["detector"]) for r in rows if r["label"] == "attack"
        )

    assert shape("pt-br") == shape("en-us")


def test_enus_bank_mirrors_the_ptbr_sizes_without_reusing_its_phrases() -> None:
    pt, en = bank_for("pt-br"), bank_for("en-us")
    for field in ("injection", "jailbreak", "prompt_leak", "exfiltration", "offensive",
                  "indirect_context", "indirect_payload", "mixed_language",
                  "false_positive_traps", "greetings", "closings"):  # fmt: skip
        assert len(getattr(pt, field)) == len(getattr(en, field)), field
        assert not set(getattr(pt, field)) & set(getattr(en, field)) - {""}, field
    assert [len(v) for v in pt.legit_base.values()] == [len(v) for v in en.legit_base.values()]
