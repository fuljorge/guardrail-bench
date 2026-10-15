# Results, EN-US (guardbench 0.2.0, 2026-10-15)

## Setup

- **Suite:** 1,655 US English texts, 575 attacks and 1,080 legitimate, written for a US
  deployment, not translated ([dataset card](../data/README_enus.md)).
- **Candidates, pipeline and rules:** the same 12 models, revisions, questions, local layer
  and per-stage blocking rules as the PT-BR run ([method](method.md)). The only change is
  the language hint of the Laya and Strands Decider questions (`GUARD_LANG=en`).
- **Hardware:** the same workstation (2× RTX 3090), three collection rounds on 2026-10-15,
  laid out as in v0.1.0: eight candidates on GPU 1, both Qwen3Guard 4B on GPU 0, then both
  Strands Decider candidates (guard server on CPU, Decider server on GPU 1).
- **Raw data:** [`results/v0.2.0-enus/measurements.json`](../results/v0.2.0-enus/measurements.json)
  and the round checkpoints in [`results/v0.2.0-enus/rounds/`](../results/v0.2.0-enus/rounds/).

Section 1 is the output of `guardbench report results/v0.2.0-enus/measurements.json`.
Rates are on all 575 attacks or all 1,080 legitimate texts unless stated; intervals are
95% Wilson. The side-by-side comparison with PT-BR is in [`comparison.md`](comparison.md).

## 1. Quality

Texts: 1655 (575 attacks, 1080 legitimate). Candidates: 6 injection, 6 toxicity. Targets: block ≥ 95%, false positives < 2%, input p95 ≤ 150 ms, output p95 ≤ 300 ms.

### Local layer alone

Injection attacks blocked: 19.8% [16.5%, 23.5%] (99/500); false positives: 1.39% [0.84%, 2.28%] (15/1080).

### Each candidate alone (model only; own attacks blocked / false positives)

| Candidate | t = 0.30 | t = 0.50 | t = 0.70 | t = 0.90 | Model p95 |
|---|---|---|---|---|---|
| `pi_deepset` | 93% / 38.7% | 92% / 34.0% | 91% / 31.0% | 90% / 25.6% | 998 ms |
| `pi_laya_multilingual` | 68% / 10.4% | 64% / 9.1% | 59% / 6.7% | 49% / 3.8% | 1144 ms |
| `pi_protectai_v2` | 84% / 8.1% | 83% / 7.9% | 82% / 7.3% | 81% / 6.9% | 998 ms |
| `pi_qwen3guard_0_6b` | 25% / 0.0% | 25% / 0.0% | 2% / 0.0% | 2% / 0.0% | 4360 ms |
| `pi_qwen3guard_4b` | 44% / 0.0% | 44% / 0.0% | 7% / 0.0% | 7% / 0.0% | 4584 ms |
| `pi_strands_decider` | 88% / 2.0% | 84% / 0.2% | 67% / 0.0% | 29% / 0.0% | 644 ms |
| `tox_granite_hap_125m` | 84% / 0.5% | 80% / 0.3% | 73% / 0.2% | 65% / 0.0% | 371 ms |
| `tox_laya_multilingual` | 76% / 0.9% | 59% / 0.5% | 43% / 0.2% | 0% / 0.0% | 1136 ms |
| `tox_qwen3guard_0_6b` | 84% / 1.0% | 84% / 1.0% | 15% / 0.0% | 15% / 0.0% | 4313 ms |
| `tox_qwen3guard_4b` | 93% / 1.0% | 93% / 1.0% | 13% / 0.0% | 13% / 0.0% | 4605 ms |
| `tox_strands_decider` | 97% / 1.8% | 96% / 0.5% | 92% / 0.5% | 76% / 0.0% | 661 ms |
| `tox_unitary_multilingual` | 88% / 0.9% | 81% / 0.7% | 71% / 0.3% | 53% / 0.0% | 374 ms |

### Best pairs (local layer + two models; best thresholds with false positives < 2%)

| Injection (t) | Toxicity (t) | Blocked [95% CI] | False positives [95% CI] | Input p95 | Output p95 | Meets |
|---|---|---|---|---|---|---|
| `pi_strands_decider` (0.45) | `tox_strands_decider` (0.85) | 85.6% [82.5%, 88.2%] | 1.94% [1.28%, 2.95%] | 1180 ms | 615 ms | no |
| `pi_strands_decider` (0.50) | `tox_unitary_multilingual` (0.55) | 85.0% [81.9%, 87.7%] | 1.85% [1.20%, 2.84%] | 989 ms | 380 ms | no |
| `pi_strands_decider` (0.45) | `tox_granite_hap_125m` (0.85) | 84.9% [81.7%, 87.6%] | 1.85% [1.20%, 2.84%] | 990 ms | 376 ms | no |
| `pi_strands_decider` (0.45) | `tox_laya_multilingual` (0.75) | 83.5% [80.2%, 86.3%] | 1.85% [1.20%, 2.84%] | 1744 ms | 1139 ms | no |
| `pi_strands_decider` (0.45) | `tox_qwen3guard_4b` (0.65) | 83.0% [79.7%, 85.8%] | 1.85% [1.20%, 2.84%] | 5161 ms | 4720 ms | no |
| `pi_strands_decider` (0.45) | `tox_qwen3guard_0_6b` (0.65) | 82.6% [79.3%, 85.5%] | 1.85% [1.20%, 2.84%] | 4828 ms | 4331 ms | no |
| `pi_qwen3guard_4b` (0.10) | `tox_strands_decider` (0.40) | 61.2% [57.2%, 65.1%] | 1.85% [1.20%, 2.84%] | 5146 ms | 615 ms | no |
| `pi_qwen3guard_4b` (0.10) | `tox_granite_hap_125m` (0.10) | 58.1% [54.0%, 62.1%] | 1.85% [1.20%, 2.84%] | 4914 ms | 376 ms | no |

### By attack category (same pairs and thresholds)

| Pair | Direct injection (n=180) | Jailbreak (n=135) | Indirect injection (n=40) | Language mix (n=10) | Offensive (n=75) | Prompt leak (n=105) | Third-party data (n=30) |
|---|---|---|---|---|---|---|---|
| `pi_strands_decider` + `tox_strands_decider` | 98% | 93% | 100% | 100% | 89% | 68% | 3% |
| `pi_strands_decider` + `tox_unitary_multilingual` | 98% | 93% | 100% | 100% | 87% | 69% | 3% |
| `pi_strands_decider` + `tox_granite_hap_125m` | 98% | 93% | 100% | 100% | 84% | 68% | 3% |
| `pi_strands_decider` + `tox_laya_multilingual` | 98% | 93% | 100% | 100% | 73% | 68% | 3% |
| `pi_strands_decider` + `tox_qwen3guard_4b` | 98% | 96% | 100% | 100% | 65% | 68% | 3% |
| `pi_strands_decider` + `tox_qwen3guard_0_6b` | 98% | 94% | 100% | 100% | 65% | 68% | 3% |
| `pi_qwen3guard_4b` + `tox_strands_decider` | 69% | 75% | 55% | 90% | 97% | 21% | 0% |
| `pi_qwen3guard_4b` + `tox_granite_hap_125m` | 63% | 73% | 55% | 70% | 87% | 27% | 0% |

### Threshold selection, 5-fold cross-validation (held-out counts pooled)

| Pair | In-sample blocked / FP | Held-out blocked [95% CI] | Held-out FP [95% CI] | Thresholds per fold |
|---|---|---|---|---|
| `pi_strands_decider` + `tox_strands_decider` | 85.6% / 1.94% | 85.7% [82.6%, 88.4%] | 2.22% [1.50%, 3.29%] | 0.45/0.85, 0.45/0.85, 0.50/0.80, 0.50/0.85, 0.40/0.75 |
| `pi_strands_decider` + `tox_unitary_multilingual` | 85.0% / 1.85% | 84.7% [81.5%, 87.4%] | 2.13% [1.42%, 3.18%] | 0.50/0.55, 0.50/0.55, 0.50/0.75, 0.50/0.75, 0.40/0.75 |
| `pi_strands_decider` + `tox_granite_hap_125m` | 84.9% / 1.85% | 84.7% [81.5%, 87.4%] | 2.22% [1.50%, 3.29%] | 0.50/0.10, 0.45/0.85, 0.50/0.60, 0.50/0.85, 0.40/0.35 |
| `pi_strands_decider` + `tox_laya_multilingual` | 83.5% / 1.85% | 83.5% [80.2%, 86.3%] | 2.22% [1.50%, 3.29%] | 0.50/0.40, 0.45/0.75, 0.50/0.65, 0.50/0.75, 0.40/0.70 |

### Paired comparison with the best pair (exact McNemar on the same texts)

| Other pair | Attacks: only best / only other, p | Legitimate: only best / only other, p |
|---|---|---|
| `pi_strands_decider` + `tox_unitary_multilingual` | 8 / 5, p = 0.58 | 3 / 2, p = 1 |
| `pi_strands_decider` + `tox_granite_hap_125m` | 6 / 2, p = 0.29 | 1 / 0, p = 1 |
| `pi_strands_decider` + `tox_laya_multilingual` | 13 / 1, p = 0.0018 | 1 / 0, p = 1 |
| `pi_strands_decider` + `tox_qwen3guard_4b` | 19 / 4, p = 0.0026 | 1 / 0, p = 1 |
| `pi_strands_decider` + `tox_qwen3guard_0_6b` | 19 / 2, p = 0.00022 | 1 / 0, p = 1 |
| `pi_qwen3guard_4b` + `tox_strands_decider` | 146 / 6, p = 5.7e-36 | 5 / 4, p = 1 |
| `pi_qwen3guard_4b` + `tox_granite_hap_125m` | 163 / 5, p = 5.8e-42 | 5 / 4, p = 1 |

## 2. Latency

Collection times ("Model p95" above, pair latencies) are inflated and not comparable with
the targets, as in v0.1.0. Two collection details differ from v0.1.0: the first attempt
put both GPU containers on GPU 0 (Docker Desktop on WSL2 ignores `--gpus device=N`; the
containers were recreated with `CUDA_VISIBLE_DEVICES`), and the SSH tunnel to the server
dropped once mid-round (both rounds resumed from their checkpoints). Neither changes a
score. Production-mode latency was not measured again: the guard server and the Decider
are the same, and the texts are of the same length.

## 3. Findings

1. **No candidate or pair meets the targets in English either.** The best pair blocks
   85.6% of attacks at 1.94% false positives (held-out: 85.7% / 2.22%).
2. **The Strands Decider is again the only injection detector that works:** 84% of
   injection attacks at 0.2% false positives (0.50), the injection half of every pair in
   the top six.
3. **English-trained injection classifiers are far better in English, but still not
   usable:** `protectai` flags 7.9% of legitimate messages (PT-BR: 79.1%) and `deepset`
   34.0% (PT-BR: 82.5%), against the 2% target.
4. **Toxicity is easy in English:** the Decider (96% / 0.5%), Qwen3Guard 4B (93% / 1.0%),
   `unitary` (81% / 0.7%) and Granite HAP (80% / 0.3%, PT-BR: 5%) all work.
5. **The local layer costs more than it gives in English:** alone it blocks 19.8% of
   injection attacks at 1.39% false positives, and every attack it blocks is already
   blocked by the Decider at the production thresholds. Its 15 false positives use most of
   the 2% budget, which pushes the threshold search to stricter, less protective
   thresholds (0.45 / 0.85 instead of 0.35 / 0.50).
6. **The same two categories fail:** prompt leaks (68–69%) and third-party data requests
   (3%), against 89–100% for the other categories.
