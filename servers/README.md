# Guard server

`guard-server/` is the guardrail server of the Implementation Project, copied
unchanged from the platform (comments in Portuguese). It serves `GET /health` and
`POST /v1/scan` with a Bearer token, and never stores or logs the texts it receives.

- **Evaluation mode** (`GUARD_EVAL_MODE=1`) loads the candidates of `detectors.json` as
  `candidate:<id>`; `guardbench collect` measures all of them in one round.
- **`GUARD_ONLY`** (comma-separated ids) loads a subset, to split candidates across GPUs.
- **Production mode** (no `GUARD_EVAL_MODE`) loads only `detectors`: the two Strands
  Decider questions chosen with these results.

## Rounds of v0.1.0 (equivalent commands)

```sh
docker build -t guard-server servers/guard-server            # CUDA 12.6 by default
export GUARD_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# GPU 1: eight candidates
docker run -d --name guard-a --gpus device=1 -p 127.0.0.1:8302:8302 \
  -e GUARD_API_KEY=$GUARD_TOKEN -e GUARD_EVAL_MODE=1 \
  -e GUARD_ONLY=pi_protectai_v2,pi_deepset,pi_laya_multilingual,pi_qwen3guard_0_6b,tox_unitary_multilingual,tox_granite_hap_125m,tox_laya_multilingual,tox_qwen3guard_0_6b \
  guard-server
# GPU 0: the two Qwen3Guard 4B candidates
docker run -d --name guard-b --gpus device=0 -p 127.0.0.1:8303:8302 \
  -e GUARD_API_KEY=$GUARD_TOKEN -e GUARD_EVAL_MODE=1 \
  -e GUARD_ONLY=pi_qwen3guard_4b,tox_qwen3guard_4b guard-server
```

Give each container its own Hugging Face cache volume: containers sharing one cache left
stale lock files during the first download.

**Strands Decider candidates.** They call a Decider server instead of loading a model.
Run the Decider server from
[goal-classification-bench](https://github.com/fuljorge/goal-classification-bench/tree/main/servers/strands-decider)
on port 8301, then:

```sh
docker run -d --name guard-c -p 127.0.0.1:8304:8302 --add-host host.docker.internal:host-gateway \
  -e GUARD_API_KEY=$GUARD_TOKEN -e GUARD_EVAL_MODE=1 -e GUARD_DEVICE=cpu \
  -e GUARD_ONLY=pi_strands_decider,tox_strands_decider \
  -e GUARD_DECIDER_TOKEN=<the Decider server's token> guard-server
```

Then, for each server:

```sh
uv run guardbench collect --url http://127.0.0.1:8302 --out results/run/measurements.json
```

## Tests

```sh
uv run --no-project --with fastapi==0.142.2 --with httpx --with pytest \
  pytest servers/guard-server -p no:cacheprovider
```
