from __future__ import annotations

import filecmp
from collections import Counter
from pathlib import Path

from guardbench.suite import FILES, load_suite, write_suite

DATA = Path(__file__).parents[1] / "data"


def test_generator_reproduces_the_published_files(tmp_path: Path) -> None:
    assert write_suite(tmp_path) == (575, 1091)
    for name in FILES:
        assert filecmp.cmp(tmp_path / name, DATA / name, shallow=False), name


def test_rows_are_well_formed() -> None:
    rows = load_suite(DATA)
    ids = [r["id"] for r in rows]

    assert len(ids) == len(set(ids)) == 1666
    assert Counter(r["label"] for r in rows) == {"attack": 575, "legit": 1091}
    assert {r["stage"] for r in rows} == {"input", "indirect", "output"}
    for r in rows:
        assert (r["detector"] == "none") == (r["label"] == "legit"), r["id"]
