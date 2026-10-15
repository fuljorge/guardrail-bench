from __future__ import annotations

import pytest

from guardbench.stats import fisher_exact, mcnemar_exact, newcombe, percentile, wilson


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


def test_newcombe_matches_the_published_example() -> None:
    # Newcombe (1998), example (a): 56/70 vs 48/80 -> 0.0524 to 0.3339.
    low, high = newcombe(56, 70, 48, 80)
    assert round(low, 4) == 0.0524
    assert round(high, 4) == 0.3339


def test_fisher_exact_matches_r() -> None:
    # R: fisher.test(matrix(c(3, 1, 1, 3), 2))$p.value == 0.4857
    assert round(fisher_exact(3, 4, 1, 4), 4) == 0.4857
    assert round(fisher_exact(1, 10, 9, 10), 6) == 0.001093
    assert round(fisher_exact(5, 10, 5, 10), 9) == 1.0
    assert fisher_exact(0, 10, 0, 10) == 1.0
