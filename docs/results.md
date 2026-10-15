# Results (guardbench 0.1.0, 2026-10-14)

## Setup

- **Suite:** 1,666 Brazilian Portuguese texts, 575 attacks and 1,091 legitimate
  ([dataset card](../data/README.md)).
- **Candidates:** 6 injection and 6 toxicity models, all OSI-licensed ([method](method.md)).
- **Pipeline:** local layer (normalisation + injection patterns) plus one injection and
  one toxicity model, with the per-stage blocking rules of the method.
- **Hardware:** 2× RTX 3090; three collection rounds on 2026-10-14.
- **Raw data:** [`results/v0.1.0/measurements.json`](../results/v0.1.0/measurements.json)
  (one record per text, with every candidate's score and time).

Everything in section 1 is the output of
`guardbench report results/v0.1.0/measurements.json`. Rates are on all 575 attacks or all
1,091 legitimate texts unless stated; intervals are 95% Wilson.

## 1. Quality

Texts: 1666 (575 attacks, 1091 legitimate). Candidates: 6 injection, 6 toxicity. Targets: block ≥ 95%, false positives < 2%, input p95 ≤ 150 ms, output p95 ≤ 300 ms.

### Local layer alone

Injection attacks blocked: 34.0% [30.0%, 38.3%] (170/500); false positives: 0.46% [0.20%, 1.07%] (5/1091).

### Each candidate alone (model only; own attacks blocked / false positives)

| Candidate | t = 0.30 | t = 0.50 | t = 0.70 | t = 0.90 | Model p95 |
|---|---|---|---|---|---|
| `pi_deepset` | 95% / 83.0% | 95% / 82.5% | 95% / 81.5% | 94% / 78.6% | 1403 ms |
| `pi_laya_multilingual` | 79% / 12.8% | 74% / 10.7% | 68% / 9.7% | 62% / 6.3% | 1452 ms |
| `pi_protectai_v2` | 98% / 80.3% | 98% / 79.1% | 98% / 78.2% | 98% / 76.4% | 1443 ms |
| `pi_qwen3guard_0_6b` | 24% / 0.0% | 24% / 0.0% | 4% / 0.0% | 4% / 0.0% | 4837 ms |
| `pi_qwen3guard_4b` | 43% / 0.0% | 43% / 0.0% | 7% / 0.0% | 7% / 0.0% | 6863 ms |
| `pi_strands_decider` | 88% / 1.9% | 82% / 0.2% | 64% / 0.0% | 27% / 0.0% | 1034 ms |
| `tox_granite_hap_125m` | 7% / 0.2% | 5% / 0.1% | 4% / 0.1% | 3% / 0.1% | 58 ms |
| `tox_laya_multilingual` | 55% / 1.2% | 29% / 0.3% | 15% / 0.0% | 0% / 0.0% | 1440 ms |
| `tox_qwen3guard_0_6b` | 79% / 2.9% | 79% / 2.9% | 11% / 0.0% | 11% / 0.0% | 3853 ms |
| `tox_qwen3guard_4b` | 91% / 0.6% | 91% / 0.6% | 12% / 0.0% | 12% / 0.0% | 4616 ms |
| `tox_strands_decider` | 97% / 3.3% | 85% / 0.5% | 81% / 0.2% | 67% / 0.0% | 718 ms |
| `tox_unitary_multilingual` | 77% / 2.3% | 69% / 1.1% | 57% / 0.5% | 25% / 0.1% | 51 ms |

### Best pairs (local layer + two models; best thresholds with false positives < 2%)

| Injection (t) | Toxicity (t) | Blocked [95% CI] | False positives [95% CI] | Input p95 | Output p95 | Meets |
|---|---|---|---|---|---|---|
| `pi_strands_decider` (0.35) | `tox_qwen3guard_4b` (0.10) | 89.7% [87.0%, 92.0%] | 1.56% [0.98%, 2.48%] | 5268 ms | 4455 ms | no |
| `pi_strands_decider` (0.35) | `tox_strands_decider` (0.50) | 88.9% [86.0%, 91.2%] | 1.56% [0.98%, 2.48%] | 1758 ms | 764 ms | no |
| `pi_strands_decider` (0.35) | `tox_unitary_multilingual` (0.55) | 88.0% [85.1%, 90.4%] | 1.92% [1.26%, 2.92%] | 1323 ms | 104 ms | no |
| `pi_strands_decider` (0.35) | `tox_laya_multilingual` (0.40) | 86.3% [83.2%, 88.8%] | 1.92% [1.26%, 2.92%] | 2326 ms | 1380 ms | no |
| `pi_strands_decider` (0.35) | `tox_granite_hap_125m` (0.05) | 85.7% [82.6%, 88.4%] | 1.74% [1.12%, 2.70%] | 1686 ms | 1380 ms | no |
| `pi_strands_decider` (0.35) | `tox_qwen3guard_0_6b` (0.65) | 85.4% [82.3%, 88.0%] | 1.10% [0.63%, 1.91%] | 4445 ms | 3744 ms | no |
| `pi_qwen3guard_4b` (0.10) | `tox_qwen3guard_4b` (0.10) | 73.0% [69.3%, 76.5%] | 1.10% [0.63%, 1.91%] | 11444 ms | 4455 ms | no |
| `pi_qwen3guard_4b` (0.10) | `tox_strands_decider` (0.40) | 65.9% [61.9%, 69.7%] | 1.47% [0.90%, 2.37%] | 7234 ms | 764 ms | no |

### By attack category (same pairs and thresholds)

| Pair | Direct injection (n=180) | Jailbreak (n=135) | Indirect injection (n=40) | PT/EN mix (n=10) | Offensive (n=75) | Prompt leak (n=105) | Third-party data (n=30) |
|---|---|---|---|---|---|---|---|
| `pi_strands_decider` + `tox_qwen3guard_4b` | 99% | 96% | 100% | 100% | 97% | 77% | 10% |
| `pi_strands_decider` + `tox_strands_decider` | 98% | 96% | 100% | 100% | 95% | 77% | 10% |
| `pi_strands_decider` + `tox_unitary_multilingual` | 98% | 96% | 100% | 100% | 88% | 77% | 10% |
| `pi_strands_decider` + `tox_laya_multilingual` | 98% | 96% | 100% | 100% | 75% | 77% | 10% |
| `pi_strands_decider` + `tox_granite_hap_125m` | 98% | 96% | 100% | 100% | 71% | 77% | 10% |
| `pi_strands_decider` + `tox_qwen3guard_0_6b` | 98% | 97% | 100% | 100% | 65% | 77% | 10% |
| `pi_qwen3guard_4b` + `tox_qwen3guard_4b` | 91% | 84% | 68% | 90% | 92% | 36% | 0% |
| `pi_qwen3guard_4b` + `tox_strands_decider` | 77% | 75% | 68% | 70% | 91% | 35% | 0% |

### Threshold selection, 5-fold cross-validation (held-out counts pooled)

| Pair | In-sample blocked / FP | Held-out blocked [95% CI] | Held-out FP [95% CI] | Thresholds per fold |
|---|---|---|---|---|
| `pi_strands_decider` + `tox_qwen3guard_4b` | 89.7% / 1.56% | 89.7% [87.0%, 92.0%] | 1.56% [0.98%, 2.48%] | 0.35/0.10, 0.35/0.10, 0.35/0.10, 0.35/0.10, 0.35/0.10 |
| `pi_strands_decider` + `tox_strands_decider` | 88.9% / 1.56% | 88.7% [85.8%, 91.0%] | 1.56% [0.98%, 2.48%] | 0.35/0.70, 0.35/0.50, 0.35/0.50, 0.35/0.50, 0.35/0.50 |
| `pi_strands_decider` + `tox_unitary_multilingual` | 88.0% / 1.92% | 87.8% [84.9%, 90.3%] | 1.92% [1.26%, 2.92%] | 0.35/0.55, 0.35/0.55, 0.35/0.55, 0.35/0.55, 0.35/0.60 |
| `pi_strands_decider` + `tox_laya_multilingual` | 86.3% / 1.92% | 86.1% [83.0%, 88.7%] | 1.74% [1.12%, 2.70%] | 0.35/0.35, 0.35/0.35, 0.35/0.50, 0.35/0.35, 0.35/0.45 |

### Paired comparison with the best pair (exact McNemar on the same texts)

| Other pair | Attacks: only best / only other, p | Legitimate: only best / only other, p |
|---|---|---|
| `pi_strands_decider` + `tox_strands_decider` | 6 / 1, p = 0.12 | 5 / 5, p = 1 |
| `pi_strands_decider` + `tox_unitary_multilingual` | 12 / 2, p = 0.013 | 5 / 9, p = 0.42 |
| `pi_strands_decider` + `tox_laya_multilingual` | 21 / 1, p = 1.1e-05 | 5 / 9, p = 0.42 |
| `pi_strands_decider` + `tox_granite_hap_125m` | 24 / 1, p = 1.5e-06 | 5 / 7, p = 0.77 |
| `pi_strands_decider` + `tox_qwen3guard_0_6b` | 27 / 2, p = 1.6e-06 | 5 / 0, p = 0.062 |
| `pi_qwen3guard_4b` + `tox_qwen3guard_4b` | 96 / 0, p = 2.5e-29 | 5 / 0, p = 0.062 |
| `pi_qwen3guard_4b` + `tox_strands_decider` | 138 / 1, p = 4e-40 | 10 / 9, p = 1 |

## 2. Latency

### 2.1 During collection (not comparable with the targets)

The "Model p95" column above and the pair latencies come from the collection, with up to
eight models sharing one GPU and two concurrent requests. The DeBERTa classifiers took about
1.4 s at p95 there, against 35–55 ms with a free GPU in an earlier local run on an RTX 5080. They only rank
the candidates: classifiers ≪ Laya ≈ Decider ≪ Qwen3Guard.

### 2.2 Strands Decider alone

60 sequential calls per question, straight to the Decider server, GPU otherwise idle:

| Question | p50 | p95 |
|---|---|---|
| Injection | 129 ms | 273 ms |
| Toxicity | 155 ms | 288 ms |

### 2.3 Guard server in production mode (Decider for both detectors)

Sequential `/v1/scan` calls on the same machine, only the two chosen detectors loaded. The
server runs the detectors of a request in parallel.

| Configuration | n | Input (both detectors) p50 / p95 | Output (toxicity) p50 / p95 |
|---|---|---|---|
| One Decider instance | 60 | 293 / 486 ms | 128 / 262 ms |
| One Decider instance per detector (one per GPU) | 100 | 201 / 282 ms | 132 / 290 ms |
| One instance, both questions in one System One request (direct, no guard server) | 60 | 277 / 486 ms | — |

The Decider server answers one question at a time, so with one instance the two input
questions queue and their times add up; sending both questions in one request does not
help. With one instance per detector, input fits 300 ms and output fits 300 ms with little
margin. **No configuration fits the original 150 ms input target.** The first row had no
warm-up; the second had 3 warm-up rounds.

## 3. Findings

1. **No candidate or pair meets the targets.** The best pairs block 88–90% of attacks with
   false positives below 2%, against a 95% target, and none fits 150 ms on input.
2. **The Strands Decider is the only ready-made injection detector that works in
   Brazilian Portuguese here:** 88% of injection attacks alone at 1.9% false positives
   (0.30), and the injection half of every pair in the top six.
3. **English-trained injection classifiers are unusable in Portuguese without
   fine-tuning:** `protectai` and `deepset` flag 76–83% of legitimate messages at any
   threshold, while catching 94–98% of attacks.
4. **Multilingual generative guards miss most injections:** Qwen3Guard 4B catches 43% of
   injection attacks (0.6B: 24%), with no false positives, and is the slowest candidate.
   Laya multilingual's injection questions reach 79% only at 12.8% false positives.
5. **Toxicity is easier:** Qwen3Guard 4B (91% / 0.6%) and the Decider (85% / 0.5% at 0.50)
   lead; `unitary` reaches 69% / 1.1% at about 50 ms.
6. **Toxicity choice barely matters for the pair once the Decider handles injection:**
   Decider + Qwen3Guard 4B and Decider + Decider differ by 6 attacks against 1 (exact
   McNemar p = 0.12) and have the same number of false positives, while the Decider is about six
   times faster than Qwen3Guard 4B.
7. **Threshold selection is not overfitted:** five-fold cross-validated rates are within
   0.2 points of the in-sample ones for the top pairs, and the folds choose the same
   injection threshold (0.35).
8. **The gaps are by category, not by disguise:** Decider + Decider catches 95–100% of direct
   injection, jailbreak, indirect injection, the language mix and offensive language, but
   77% of prompt-leak requests and 10% of third-party data requests. Without those two
   categories, Decider + Decider blocks 97.0% (427 of 440). The Decider's injection question
   does not mention requests for other customers' data.
9. **The local layer alone** blocks 34% of injection attacks at 0.46% false positives: a
   cheap first filter, not a replacement for a model.

## 4. Decision taken with these results

The platform chose the **Strands Decider for both detectors** (thresholds 0.35 and 0.50)
and revised its targets for the first release: at least 88% of attacks blocked overall and
at least 95% in direct injection, indirect injection and jailbreak, with input p95 ≤ 300 ms
and one Decider instance per detector. The 95% overall target moved to the next release,
with questions extended to prompt leaks and third-party data and validated on a separate
attack set (tuning them on this suite would be training on the test).

## Limitations

- Synthetic, single-author suite; the false-positive rate is likely optimistic (see the
  [dataset card](../data/README.md)).
- Small categories (indirect 40, third-party data 30, language mix 10) have wide intervals.
- Latency comes from one machine with consumer GPUs; production hardware may differ.
- Prompt leaks and third-party data requests meet other defences in the platform (output
  checks, authorisation, tenant isolation) that this input-only suite does not measure.
