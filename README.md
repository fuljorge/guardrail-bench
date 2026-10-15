# guardbench

A reproducible benchmark of **open-weight guardrail models for customer-service AI agents in
Brazilian Portuguese**: which prompt-injection and toxicity detectors block attacks without
blocking real customers, and how fast.

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

## Quick start

```sh
uv sync
uv run pytest
uv run guardbench build-suite --out data                     # byte-identical regeneration
uv run guardbench report results/v0.1.0/measurements.json    # every table in docs/results.md
```

New measurements need a guard server with GPU: [`servers/README.md`](servers/README.md).

## Layout

| Path | Content |
|---|---|
| `data/` | The suite and its dataset card |
| `src/guardbench/` | Generator, local layer, collection, analysis, statistics, report and CLI |
| `servers/guard-server/` | The guard server with all candidate adapters |
| `results/v0.1.0/` | Merged measurements, the raw round checkpoints and the latency scripts |
| `docs/` | Method and results |

## Provenance

Built during the guardrails feature of the Implementation Project, where it chose the
production detectors. The suite, the local layer and the guard server are copied from that
project; this repository is self-contained and depends on none of it.

## License

Code: Apache 2.0 ([`LICENSE`](LICENSE)). Dataset: CC BY 4.0
([`data/README.md`](data/README.md)). Each evaluated model keeps its own license (see the
method).
