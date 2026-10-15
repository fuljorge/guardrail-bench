"""Small, dependency-free statistics: Wilson and Newcombe intervals, exact McNemar and Fisher
tests, percentiles."""

from __future__ import annotations

import math


def wilson(hits: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95% by default)."""
    if n == 0:
        return (0.0, 1.0)
    p = hits / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(only_first: int, only_second: int) -> float:
    """Two-sided exact McNemar p-value from the discordant pairs (binomial, p = 0.5)."""
    n = only_first + only_second
    if n == 0:
        return 1.0
    k = min(only_first, only_second)
    tail = math.fsum(math.comb(n, i) for i in range(k + 1)) / float(1 << n)
    return min(1.0, 2 * tail)


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile: the ceil(q * n)-th smallest value (1-based)."""
    if not values:
        return float("nan")
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def newcombe(hits_a: int, n_a: int, hits_b: int, n_b: int) -> tuple[float, float]:
    """Newcombe hybrid score interval (method 10) for the difference of two independent
    proportions, a - b, built from the two Wilson intervals (95% by default)."""
    p_a = hits_a / n_a if n_a else 0.0
    p_b = hits_b / n_b if n_b else 0.0
    low_a, high_a = wilson(hits_a, n_a)
    low_b, high_b = wilson(hits_b, n_b)
    d = p_a - p_b
    return (
        d - math.sqrt((p_a - low_a) ** 2 + (high_b - p_b) ** 2),
        d + math.sqrt((high_a - p_a) ** 2 + (p_b - low_b) ** 2),
    )


def fisher_exact(hits_a: int, n_a: int, hits_b: int, n_b: int) -> float:
    """Two-sided Fisher exact p-value for two independent proportions: the probability of
    every 2x2 table with the same margins that is no more likely than the observed one."""
    total, hits = n_a + n_b, hits_a + hits_b
    if n_a == 0 or n_b == 0 or hits in (0, total):
        return 1.0

    def log_p(k: int) -> float:  # hypergeometric: k hits in sample a
        return _log_comb(n_a, k) + _log_comb(n_b, hits - k) - _log_comb(total, hits)

    observed = log_p(hits_a)
    ks = range(max(0, hits - n_b), min(n_a, hits) + 1)
    # Relative tolerance, as in R and SciPy, so ties in floating point count as equal.
    p = math.fsum(math.exp(lp) for lp in map(log_p, ks) if lp <= observed + 1e-7)
    return min(1.0, p)


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)
