"""Collection: sends every suite text to a guard server that has all candidates loaded.

For each text, the original and the normalised variant (`normalize.py`) go to the server in
parallel, as in the platform's pipeline, each in one `/v1/scan` request with every
candidate; the server runs the candidates one after another and reports each model's time
(`duration_ms`). Per candidate, the worse (higher) score of the two variants counts. The
local layer (injection patterns on the normalised text) is evaluated here, with its time.

Each measured text is appended to a JSONL checkpoint as soon as it finishes, so a run that
stops resumes where it left off (same ids and candidates).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .normalize import normalize
from .patterns import injection_matches

CANDIDATE_PREFIX = "candidate:"


@dataclass
class Measurement:
    id: str
    label: str
    stage: str
    detector: str
    category: str
    # Local layer: injection pattern found in the normalised text (never on output).
    local: bool
    local_ms: float
    # Candidate -> higher score between the original and the normalised text.
    scores: dict[str, float] = field(default_factory=dict)
    # Candidate -> model time in the slower of the two requests.
    model_ms: dict[str, float] = field(default_factory=dict)
    # Network and serialisation, without the wait for other models in the request.
    http_ms: float = 0.0


Scan = Callable[[str, str, list[str]], dict[str, Any]]


def http_scan(base_url: str, token: str | None, timeout: float = 300.0) -> Scan:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    client = httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def scan(text: str, kind: str, detectors: list[str]) -> dict[str, Any]:
        response = client.post(
            "/v1/scan", json={"text": text, "kind": kind, "detectors": detectors}
        )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body

    return scan


def server_candidates(base_url: str, token: str | None) -> list[str]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    health = httpx.get(f"{base_url}/health", headers=headers, timeout=30).json()
    names = [
        d["name"] for d in health.get("detectors", []) if d["name"].startswith(CANDIDATE_PREFIX)
    ]
    if not names:
        raise SystemExit("The server has no candidates: start it with GUARD_EVAL_MODE=1.")
    return names


def measure(
    row: dict[str, str], scan: Scan, candidates: list[str], pool: ThreadPoolExecutor
) -> Measurement:
    """One request per variant (original and normalised, in parallel) with all candidates.

    One request per candidate in parallel hung the server on shared GPUs (several models in
    different threads); one request with all candidates in sequence is stable.
    """
    started = time.perf_counter()
    normalized = normalize(row["text"])
    local = bool(injection_matches(normalized)) and row["stage"] != "output"
    local_ms = (time.perf_counter() - started) * 1000
    variants = list(dict.fromkeys([row["text"], normalized]))

    def one(variant: str) -> tuple[dict[str, Any], float]:
        begun = time.perf_counter()
        answer = scan(variant, row["stage"], candidates)
        return answer, (time.perf_counter() - begun) * 1000

    futures = [pool.submit(one, v) for v in variants]
    result = Measurement(
        row["id"], row["label"], row["stage"], row["detector"], row["category"], local, local_ms
    )
    overheads = []
    for future in futures:
        answer, wall = future.result()
        total = 0.0
        for item in answer["results"]:
            name = item["detector"].removeprefix(CANDIDATE_PREFIX)
            ms = float(item.get("duration_ms", 0.0))
            result.scores[name] = max(result.scores.get(name, 0.0), float(item["score"]))
            result.model_ms[name] = max(result.model_ms.get(name, 0.0), ms)
            total += ms
        overheads.append(max(0.0, wall - total))
    result.http_ms = min(overheads) if overheads else 0.0
    return result


def collect(
    rows: list[dict[str, str]],
    scan: Scan,
    candidates: list[str],
    *,
    checkpoint: Path | None = None,
    progress: Callable[[str], None] = print,
) -> list[Measurement]:
    done: dict[str, Measurement] = {}
    wanted = {c.removeprefix(CANDIDATE_PREFIX) for c in candidates}
    if checkpoint is not None and checkpoint.exists():
        for line in checkpoint.read_text(encoding="utf-8").splitlines():
            if line.strip():
                m = Measurement(**json.loads(line))
                if wanted <= set(m.scores):
                    done[m.id] = m
    pending = [r for r in rows if r["id"] not in done]
    progress(f"{len(done)} texts already measured; {len(pending)} to go")
    started = time.perf_counter()
    handle = None
    if checkpoint is not None:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        handle = checkpoint.open("a", encoding="utf-8")
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            for row in rows[:3]:  # warm-up: first calls load GPU kernels
                if pending:
                    measure(row, scan, candidates, pool)
            for index, row in enumerate(pending, start=1):
                m = measure(row, scan, candidates, pool)
                done[m.id] = m
                if handle is not None:
                    handle.write(json.dumps(asdict(m), ensure_ascii=False) + "\n")
                    handle.flush()
                if index % 50 == 0 or index == len(pending):
                    elapsed = time.perf_counter() - started
                    rest = elapsed / index * (len(pending) - index)
                    progress(
                        f"{index}/{len(pending)} texts; {elapsed / 60:.1f} min;"
                        f" ~{rest / 60:.0f} min left"
                    )
    finally:
        if handle is not None:
            handle.close()
    return [done[r["id"]] for r in rows if r["id"] in done]


def merge(path: Path, measurements: list[Measurement]) -> None:
    """Merges into earlier rounds (same id: adds the new candidates)."""
    current: dict[str, dict[str, Any]] = {}
    if path.exists():
        current = {m["id"]: m for m in json.loads(path.read_text(encoding="utf-8"))}
    for m in measurements:
        old = current.get(m.id)
        data = asdict(m)
        if old:
            data["scores"] = {**old["scores"], **data["scores"]}
            data["model_ms"] = {**old["model_ms"], **data["model_ms"]}
        current[m.id] = data
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(current.values()), ensure_ascii=False), encoding="utf-8")


def load(path: Path) -> list[Measurement]:
    return [Measurement(**m) for m in json.loads(path.read_text(encoding="utf-8"))]


def latency(
    scan: Scan, texts: list[str], detectors: list[str], kind: str, *, rounds: int, warmup: int = 3
) -> list[float]:
    """Wall time of sequential `/v1/scan` calls (production mode, no candidates)."""
    for _ in range(warmup):
        for text in texts:
            scan(text, kind, detectors)
    times = []
    for _ in range(rounds):
        for text in texts:
            begun = time.perf_counter()
            scan(text, kind, detectors)
            times.append((time.perf_counter() - begun) * 1000)
    return times
