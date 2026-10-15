from __future__ import annotations

import pytest

from guardbench.stats import mcnemar_exact, percentile, wilson


def test_wilson_interval() -> None:
    low, high = wilson(511, 575)
    assert low == pytest.approx(0.8601, abs=1e-3)
    assert high == pytest.approx(0.9122, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)


def test_mcnemar_exact() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(6, 1) == pytest.approx(0.125)
    assert mcnemar_exact(10, 0) == pytest.approx(2 / 1024)


def test_percentile_nearest_rank() -> None:
    assert percentile([5.0, 1.0, 3.0, 2.0, 4.0], 0.95) == 5.0
    assert percentile([5.0, 1.0, 3.0, 2.0, 4.0], 0.5) == 3.0
