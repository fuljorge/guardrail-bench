# guardbench

A reproducible benchmark of **open-weight guardrail models for customer-service AI agents in
Brazilian Portuguese**, with a US English counterpart: which prompt-injection and toxicity
detectors block attacks without blocking real customers, how fast, and what changes with
the language.

The pipeline under test has two layers, as in the platform it was built for:
1. a local layer: disguise normalisation (homoglyphs, invisible characters, separated
   letters, leetspeak) and injection patterns;
2. one model per detector, `prompt_injection` and `toxicity`, behind a guard server.

Blocking rules differ by stage: customer input, indirect content (documents, tool results)
and the agent's own output.

- **Method:** [`docs/method.md`](docs/method.md).
- **Dataset card:** [`data/README.md`](data/README.md): 575 attacks and 1,091 legitimate
  texts, generated deterministically.
- **Results:** [`docs/results.md`](docs/results.md), with per-text raw scores of all 12
  candidates in [`results/v0.1.0/`](results/v0.1.0/).
- **EN-US counterpart (v0.2.0):** [`data/README_enus.md`](data/README_enus.md): 575
  attacks and 1,080 legitimate texts written for a US deployment (not translated), with
  the same categories and sizes. Results: [`docs/results_enus.md`](docs/results_enus.md);
  side by side: [`docs/comparison.md`](docs/comparison.md).

## Results at a glance (v0.1.0)

Best pairs through the full pipeline, thresholds chosen with false positives below 2%; 95%
Wilson intervals. Targets: ≥ 95% blocked, < 2% false positives.

| Injection + toxicity | Blocked | False positives | Held-out blocked (5-fold CV) |
|---|---|---|---|
| Strands Decider + Qwen3Guard 4B | 89.7% [87.0, 92.0] | 1.56% [0.98, 2.48] | 89.7% |
| **Strands Decider + Strands Decider** | 88.9% [86.0, 91.2] | 1.56% [0.98, 2.48] | 88.7% |
| Strands Decider + unitary multilingual | 88.0% [85.1, 90.4] | 1.92% [1.26, 2.92] | 87.8% |
| Qwen3Guard 4B + Qwen3Guard 4B | 73.0% [69.3, 76.5] | 1.10% [0.63, 1.91] | — |

- **No configuration meets the targets.** The Strands Decider (2 B, Apache 2.0), asked one
  `choice` question per detector, is the only ready-made injection detector that works in
  Portuguese here.
- **English-trained injection classifiers** (`protectai`, `deepset`) flag 76–83% of
  legitimate Portuguese messages.
- **Multilingual generative guards** (Qwen3Guard) miss most injections and are slow.
- **The misses are by category:** 77% of prompt-leak requests and 10% of third-party data
  requests are caught, against 95–100% of direct and indirect injection, jailbreak and
  offensive language.
- **Latency:** with one Decider instance per detector, the guard server adds 282 ms (p95)
  on input and 290 ms on output. That is over the original 150 ms input target.

## PT-BR versus EN-US at a glance (v0.2.0)

| Measure | PT-BR | EN-US | Difference [95% CI], p |
|---|---|---|---|
| Production pair (Decider 0.35 + Decider 0.50), blocked | 88.9% | 88.7% | -0.2 [-3.8, +3.5], p = 1 |
| Same, false positives | 1.56% | 3.24% | +1.68 [+0.39, +3.05], p = 0.011 |
| Same without the local layer, false positives | 1.10% | 1.85% | — |
| `protectai` alone (0.50), false positives | 79.1% | 7.9% | -71.2 [-74.0, -68.2] |
| Granite HAP alone (0.50), offensive blocked | 5% | 80% | +74.7 [+61.8, +82.8] |

- **Attack coverage carries over; false positives do not.** The local layer's English
  patterns add false positives and no blocks; the Decider flags more English idioms.
- **English-trained classifiers improve sharply in English** but `protectai` still flags
  7.9% of legitimate messages, against a 2% target.
- Independent samples: Newcombe intervals and Fisher exact tests. Details:
  [`docs/comparison.md`](docs/comparison.md).

## Quick start

```sh
uv sync
uv run pytest
uv run guardbench build-suite --out data                     # byte-identical regeneration
uv run guardbench build-suite --lang en-us --out data        # the EN-US suite
uv run guardbench report results/v0.1.0/measurements.json    # every table in docs/results.md
uv run guardbench report results/v0.2.0-enus/measurements.json
uv run guardbench compare results/v0.1.0/measurements.json results/v0.2.0-enus/measurements.json
```

New measurements need a guard server with GPU: [`servers/README.md`](servers/README.md).

## Layout

| Path | Content |
|---|---|
| `data/` | The two suites and their dataset cards |
| `src/guardbench/` | Generator, local layer, collection, analysis, statistics, report and CLI |
| `servers/guard-server/` | The guard server with all candidate adapters |
| `results/v0.1.0/` | PT-BR: merged measurements, the raw round checkpoints and the latency scripts |
| `results/v0.2.0-enus/` | EN-US: merged measurements and the raw round checkpoints |
| `docs/` | Method, results per language and the comparison |

## Provenance

Built during the guardrails feature of the Implementation Project, where it chose the
production detectors. The suite, the local layer and the guard server are copied from that
project; this repository is self-contained and depends on none of it.

## License

Code: Apache 2.0 ([`LICENSE`](LICENSE)). Dataset: CC BY 4.0
([`data/README.md`](data/README.md)). Each evaluated model keeps its own license (see the
method).
