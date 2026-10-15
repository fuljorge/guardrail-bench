"""Servidor de guardrails do Implementation Project (specs/010-guardrails, plano §4.1).

Roda num servidor com GPU fora da instalação, como o classificador de Goals (§40.1). Não
conhece organização, agente nem cliente: recebe só o texto, devolve uma pontuação por
detector e não grava nem registra o texto.

    GET  /health    sem token: {"status": "ok"}; com token: versão e detectores carregados
    POST /v1/scan   {"text", "kind", "detectors"} -> {"results": [...], "duration_ms"}

Cada detector (`prompt_injection`, `toxicity`) é um modelo escolhido no benchmark em PT-BR
(plano §4.8), descrito num arquivo de configuração JSON:

    {"detectors": {"prompt_injection": {"adapter": "systemone_choice",
                                         "model": "org/modelo", "revision": "<commit>",
                                         "instructions": "...", "criteria": {...},
                                         "questions_sha256": "<12 hex>",
                                         "threshold": 0.35}},
     "candidates": {...}}

Os escolhidos (T024) são perguntas `choice` ao Strands Decider, no servidor que já roda para
o classificador de Goals (plano §4.1). Os detectores de um pedido rodam em paralelo.

`candidates` só é carregado em modo de avaliação (`GUARD_EVAL_MODE=1`) e é chamado pelos
nomes `candidate:<id>`, recusados em produção.

Configuração por variáveis de ambiente (README.md):
    GUARD_API_KEY        token Bearer (obrigatório, a menos que GUARD_ALLOW_NO_AUTH=1)
    GUARD_CONFIG         caminho do JSON de detectores (padrão: detectors.json ao lado)
    GUARD_EVAL_MODE      1 para carregar também os candidatos do benchmark
    GUARD_ONLY           nomes separados por vírgula: carrega só esses (benchmark em rodadas)
    GUARD_DEVICE         cuda ou cpu
    GUARD_LANG           idioma das perguntas do Laya e do Decider (padrão: o do JSON, "pt")
    GUARD_DECIDER_URL    endereço base do Strands Decider (HTTPS ou da mesma máquina)
    GUARD_DECIDER_TOKEN_FILE  arquivo com o token do Decider (padrão: /run/secrets/decider_api_key)
    GUARD_HOST, GUARD_PORT, GUARD_LOG_LEVEL
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

SERVICE = "guard-server"
VERSION = "0.1.0"
MAX_TEXT_CHARS = 16_000
MAX_DETECTORS = 10
CANDIDATE_PREFIX = "candidate:"
# Trechos sobrepostos para textos maiores que a janela do modelo: vale a maior pontuação.
CHUNK_CHARS = 1_500
CHUNK_OVERLAP = 200

Score = Callable[[str], float]


@dataclass(frozen=True)
class Detector:
    name: str
    model: str
    model_version: str
    threshold: float
    score: Score
    # Modelo local na GPU: uma avaliação por vez. Servidor remoto: chamadas concorrentes.
    exclusive: bool = True


class ScanRequest(BaseModel):
    # Sem `max_length` aqui: acima do limite responde 413, não 422.
    text: str
    kind: Literal["input", "indirect", "output"]
    detectors: list[str] = Field(..., min_length=1, max_length=MAX_DETECTORS)


def chunks(text: str) -> list[str]:
    """Janelas de até `CHUNK_CHARS` com sobreposição, para não perder ataques na emenda."""
    if len(text) <= CHUNK_CHARS:
        return [text]
    step = CHUNK_CHARS - CHUNK_OVERLAP
    return [
        text[i : i + CHUNK_CHARS] for i in range(0, len(text) - CHUNK_OVERLAP, step)
    ]


def build_app(
    detectors: dict[str, Detector],
    *,
    api_key: str | None,
    eval_mode: bool = False,
    details: dict[str, Any] | None = None,
) -> FastAPI:
    """Monta o app sobre os detectores; separado do carregamento dos modelos para os testes."""
    app = FastAPI(
        title="Implementation Project Guard Server", docs_url=None, redoc_url=None, openapi_url=None
    )
    # Um modelo por GPU: uma avaliação por vez em cada detector local.
    locks = {name: threading.Lock() for name, d in detectors.items() if d.exclusive}
    # Os detectores de um pedido rodam em paralelo (RNF-007: a entrada soma os dois).
    pool = ThreadPoolExecutor(max_workers=max(4, 4 * len(detectors)))

    def evaluate(detector: Detector, text: str) -> tuple[float, float]:
        one = time.perf_counter()
        with locks.get(detector.name) or nullcontext():
            score = max(detector.score(piece) for piece in chunks(text))
        return score, (time.perf_counter() - one) * 1000

    def authorized(request: Request) -> bool:
        if api_key is None:
            return True
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        return scheme.lower() == "bearer" and hmac.compare_digest(token, api_key)

    def require_token(request: Request) -> None:
        if not authorized(request):
            raise HTTPException(status_code=401, detail="token inválido ou ausente")

    def available(name: str) -> Detector:
        detector = detectors.get(name)
        if detector is None or (name.startswith(CANDIDATE_PREFIX) and not eval_mode):
            raise HTTPException(
                status_code=422, detail=f"detector desconhecido: {name[:80]}"
            )
        return detector

    @app.get("/health")
    def health(request: Request) -> dict[str, Any]:
        if not authorized(request):
            return {"status": "ok"}
        listed = [
            {"name": d.name, "model": d.model, "model_version": d.model_version}
            for d in detectors.values()
            if eval_mode or not d.name.startswith(CANDIDATE_PREFIX)
        ]
        return {
            "status": "ok", "service": SERVICE, "version": VERSION, "detectors": listed,
            "eval_mode": eval_mode, **(details or {}),
        }  # fmt: skip

    @app.post("/v1/scan", dependencies=[Depends(require_token)])
    def scan(body: ScanRequest) -> dict[str, Any]:
        if len(body.text) > MAX_TEXT_CHARS:
            raise HTTPException(status_code=413, detail="texto acima do limite")
        chosen = [available(name) for name in dict.fromkeys(body.detectors)]
        started = time.perf_counter()
        futures = [pool.submit(evaluate, detector, body.text) for detector in chosen]
        results = []
        for detector, future in zip(chosen, futures, strict=True):
            try:
                score, duration_ms = future.result()
            except Exception as exc:  # noqa: BLE001
                # Qualquer falha do modelo vira 500 sem a mensagem: ela pode trazer o texto.
                # No log, só o tipo da falha e o detector.
                logging.getLogger(SERVICE).warning(
                    "detector_failed", extra={"detector": detector.name,
                                              "error": type(exc).__name__}
                )  # fmt: skip
                raise HTTPException(
                    status_code=500, detail="falha no detector"
                ) from None
            results.append(
                {"detector": detector.name, "score": round(float(score), 6),
                 "flagged": score >= detector.threshold,
                 "model_version": detector.model_version,
                 "duration_ms": round(duration_ms, 2)}
            )  # fmt: skip
        return {
            "results": results,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    return app


# --- Carregamento dos modelos -----------------------------------------------------------


def _sequence_classifier(spec: dict[str, Any], device: str) -> Score:
    """Classificador de sequência do Hugging Face: probabilidade dos rótulos positivos."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    revision = spec["revision"]
    # Alguns repositórios trazem só o arquivo do tokenizador base: `tokenizer` aponta para ele.
    tokenizer = AutoTokenizer.from_pretrained(
        spec.get("tokenizer", spec["model"]),
        revision=spec.get("tokenizer_revision", revision),
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        spec["model"], revision=revision
    )
    model.to(device).eval()
    labels = {
        i
        for i, label in model.config.id2label.items()
        if label in spec["positive_labels"]
    }
    if not labels:
        raise SystemExit(f"Rótulos positivos não encontrados em {spec['model']}")
    # Um só rótulo (ex.: "toxic") ou vários independentes: sigmoide; senão, softmax.
    multi_label = (
        model.config.problem_type == "multi_label_classification"
        or model.config.num_labels == 1
    )
    max_length = int(spec.get("max_length", 512))

    def score(text: str) -> float:
        encoded = tokenizer(
            text, truncation=True, max_length=max_length, return_tensors="pt"
        ).to(device)
        with torch.inference_mode():
            logits = model(**encoded).logits[0]
        probs = torch.sigmoid(logits) if multi_label else torch.softmax(logits, dim=-1)
        return float(max(probs[i] for i in labels))

    return score


# Qwen3Guard-Gen: responde "Safety: Safe|Unsafe|Controversial" e "Categories: ...".
QWEN_SAFETY = re.compile(r"Safety:\s*(Safe|Unsafe|Controversial)")
QWEN_CATEGORIES = re.compile(
    r"(Violent|Non-violent Illegal Acts|Sexual Content or Sexual Acts|PII|Suicide & Self-Harm"
    r"|Unethical Acts|Politically Sensitive Topics|Copyright Violation|Jailbreak|None)"
)
QWEN_SCORES = {"Unsafe": 0.95, "Controversial": 0.6, "Safe": 0.05}


def qwen_guard_score(content: str, categories: list[str] | None) -> float:
    """Pontuação a partir da resposta do Qwen3Guard; `categories` restringe o que conta.

    O modelo é generativo: a pontuação é grosseira (três níveis), e o benchmark a mede como
    está (plano §4.8).
    """
    match = QWEN_SAFETY.search(content)
    if match is None:
        raise ValueError("resposta do Qwen3Guard fora do formato")
    label = match.group(1)
    if label != "Safe" and categories is not None:
        found = set(QWEN_CATEGORIES.findall(content))
        if not found & set(categories):
            return QWEN_SCORES["Safe"]
    return QWEN_SCORES[label]


def _qwen3guard(spec: dict[str, Any], device: str) -> Score:
    """Qwen3Guard-Gen (Apache 2.0): moderação da mensagem do usuário (`role: user`)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    revision = spec["revision"]
    tokenizer = AutoTokenizer.from_pretrained(spec["model"], revision=revision)
    model = AutoModelForCausalLM.from_pretrained(
        spec["model"], revision=revision, torch_dtype="auto"
    )
    model.to(device).eval()
    categories = spec.get("categories")

    def score(text: str) -> float:
        messages = [{"role": "user", "content": text}]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False)
        encoded = tokenizer([prompt], return_tensors="pt").to(device)
        with torch.inference_mode():
            generated = model.generate(**encoded, max_new_tokens=32, do_sample=False)
        content = tokenizer.decode(
            generated[0][encoded.input_ids.shape[1] :], skip_special_tokens=True
        )
        return qwen_guard_score(content, categories)

    return score


def _laya(spec: dict[str, Any], device: str) -> Score:
    """LayaGuardrail (pacote `laya`, Apache 2.0): perguntas sim/não (`noul`); vale a maior
    probabilidade de violação entre as perguntas."""
    import laya

    agent = laya.load(
        spec["model"],
        device=device,
        revision=spec["revision"],
        subfolder=spec.get("subfolder"),
    )
    questions = {
        key: {"type": "noul", "instructions": instructions}
        for key, instructions in spec["questions"].items()
    }
    lang = spec.get("lang", "pt")

    def score(text: str) -> float:
        out = agent.system_one({"prompt": text}, questions, lang=lang)
        answers = out.get("answers", out)
        return max(float(answers[key]["noul"]) for key in questions)

    return score


QUESTION_ID = "guard"


def choice_score(answer: dict[str, Any], positive: str) -> float:
    """Probabilidade da opção `positive` na resposta `choice` de um servidor System One."""
    try:
        return float(answer["answers"][QUESTION_ID]["probabilities"][positive])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("resposta do servidor System One fora do formato") from exc


def questions_digest(spec: dict[str, Any]) -> str:
    """Impressão digital das perguntas: mudar o texto equivale a trocar de modelo (plano
    §4.1) e exige nova rodada do benchmark e novo `questions_sha256` no `detectors.json`."""
    fields = {k: spec[k] for k in ("instructions", "criteria", "positive")}
    canonical = json.dumps(fields, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


# Sem HTTPS, só endereços da mesma máquina (Princípio X; plano §4.1).
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})


def systemone_url(spec: dict[str, Any]) -> str:
    """Endereço do servidor: a primeira variável de `url_env` definida, senão `url`. Uma
    variável por detector deixa cada um numa instância do Decider (plano §10)."""
    names = spec.get("url_env") or []
    names = [names] if isinstance(names, str) else names
    base = next((os.environ[n] for n in names if os.environ.get(n)), spec["url"])
    parts = urlsplit(base)
    if parts.scheme != "https" and not (
        parts.scheme == "http" and parts.hostname in LOCAL_HOSTS
    ):
        raise SystemExit(
            f"Endereço do servidor System One sem HTTPS fora da máquina local: {parts.hostname}"
        )
    return base.rstrip("/") + "/v1/systemone"


def systemone_token(spec: dict[str, Any]) -> str:
    """Token do servidor System One: de um arquivo de segredo (produção) ou do ambiente
    (candidatos do benchmark); nunca do `detectors.json`."""
    if spec.get("token_file"):
        env = spec.get("token_file_env")
        path = Path((os.environ.get(env, "") if env else "") or spec["token_file"])
        try:
            token = path.read_text(encoding="utf-8").strip()
        except OSError:
            token = ""
        if not token:
            raise SystemExit(f"Token do servidor System One ausente em {path}.")
        return token
    token = os.environ.get(spec["token_env"], "")
    if not token:
        raise SystemExit(f"Defina {spec['token_env']} para {spec['model']}.")
    return token


def _systemone_choice(spec: dict[str, Any], device: str) -> Score:
    """Pergunta `choice` a um servidor com a interface do laya-serve (`/v1/systemone`), como
    o Strands Decider (Apache 2.0) que já roda para o classificador de Goals (004).

    Escolhido no benchmark para os dois detectores (T024): o modelo não é carregado aqui, e
    o servidor de guardrails só faz a pergunta.
    """
    import urllib.error
    import urllib.request

    token = systemone_token(spec)
    url = systemone_url(spec)
    question = {
        QUESTION_ID: {
            "type": "choice",
            "instructions": spec["instructions"],
            "criteria": spec["criteria"],
        }
    }
    positive = spec["positive"]
    timeout = float(spec.get("timeout", 30))

    def score(text: str) -> float:
        body = {
            "state": {"message": text},
            "questions": question,
            "lang": spec.get("lang", "pt"),
        }
        if spec.get("model_field"):
            body["model"] = spec["model_field"]
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        # Uma nova tentativa em falha de rede ou 5xx: o servidor System One atende uma
        # pergunta por vez e pode recusar conexões sob carga.
        for attempt in (1, 2):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return choice_score(json.loads(response.read()), positive)
            except urllib.error.HTTPError as exc:
                if exc.code < 500 or attempt == 2:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(0.5)
        raise RuntimeError("inalcançável")

    return score


ADAPTERS: dict[str, Callable[[dict[str, Any], str], Score]] = {
    "systemone_choice": _systemone_choice,
    "sequence_classifier": _sequence_classifier,
    "qwen3guard": _qwen3guard,
    "laya": _laya,
}
# Adaptadores que chamam outro servidor: sem trava por detector.
REMOTE_ADAPTERS = frozenset({"systemone_choice"})


def model_version(spec: dict[str, Any]) -> str:
    version = f"{spec['model']}@{str(spec['revision'])[:12]}"
    if spec["adapter"] == "systemone_choice":
        version += f"+q{questions_digest(spec)}"
    return version


def check_questions(name: str, spec: dict[str, Any], *, required: bool) -> None:
    """Perguntas iguais às medidas no benchmark: `questions_sha256` confere com o texto."""
    if spec["adapter"] != "systemone_choice":
        return
    expected = spec.get("questions_sha256")
    if expected is None and not required:
        return
    if expected != questions_digest(spec):
        raise SystemExit(
            f"Perguntas de {name} diferentes das medidas no benchmark (questions_sha256)."
        )


DEFAULT_LANG = "pt"


def apply_lang(config: dict[str, Any], lang: str) -> dict[str, Any]:
    """Idioma das perguntas do Laya e do Decider (`lang`) em todos os detectores que o
    usam: o benchmark em outro idioma roda os mesmos candidatos com `GUARD_LANG`."""
    return {
        group: {
            name: ({**spec, "lang": lang} if "lang" in spec else spec)
            for name, spec in specs.items()
        }
        if isinstance(specs, dict)
        else specs
        for group, specs in config.items()
    }


def load_detectors(
    config: dict[str, Any], device: str, *, eval_mode: bool
) -> dict[str, Detector]:
    for name, spec in config.get("detectors", {}).items():
        check_questions(name, spec, required=True)
    specs = dict(config.get("detectors", {}))
    if eval_mode:
        specs.update(
            {
                f"{CANDIDATE_PREFIX}{k}": v
                for k, v in config.get("candidates", {}).items()
            }
        )
    loaded = {}
    for name, spec in specs.items():
        adapter = ADAPTERS.get(spec["adapter"])
        if adapter is None:
            raise SystemExit(f"Adaptador desconhecido em {name}: {spec['adapter']}")
        loaded[name] = Detector(
            name=name,
            model=spec["model"],
            model_version=model_version(spec),
            threshold=float(spec.get("threshold", 0.5)),
            score=adapter(spec, device),
            exclusive=spec["adapter"] not in REMOTE_ADAPTERS,
        )
    return loaded


def main() -> None:
    import uvicorn

    api_key = os.environ.get("GUARD_API_KEY") or None
    if api_key is None and os.environ.get("GUARD_ALLOW_NO_AUTH") != "1":
        raise SystemExit(
            "Defina GUARD_API_KEY (ou GUARD_ALLOW_NO_AUTH=1 só no ambiente local)."
        )
    config_path = Path(
        os.environ.get("GUARD_CONFIG", Path(__file__).with_name("detectors.json"))
    )
    config = json.loads(config_path.read_text(encoding="utf-8"))
    eval_mode = os.environ.get("GUARD_EVAL_MODE") == "1"
    # Só alguns detectores (benchmark em rodadas, quando todos não cabem na GPU).
    only = {n.strip() for n in os.environ.get("GUARD_ONLY", "").split(",") if n.strip()}
    if only:
        config = {
            "detectors": {
                k: v for k, v in config.get("detectors", {}).items() if k in only
            },
            "candidates": {
                k: v for k, v in config.get("candidates", {}).items() if k in only
            },
        }
    lang = os.environ.get("GUARD_LANG") or None
    if lang:
        config = apply_lang(config, lang)
    device = os.environ.get("GUARD_DEVICE", "cuda")
    detectors = load_detectors(config, device, eval_mode=eval_mode)
    app = build_app(
        detectors,
        api_key=api_key,
        eval_mode=eval_mode,
        details={"device": device, "lang": lang or DEFAULT_LANG},
    )
    uvicorn.run(
        app,
        host=os.environ.get("GUARD_HOST", "127.0.0.1"),
        port=int(os.environ.get("GUARD_PORT", "8302")),
        workers=1,
        # Sem log de acesso: só caminho e status, mas evita qualquer dado da requisição.
        access_log=False,
        log_level=os.environ.get("GUARD_LOG_LEVEL", "warning"),
    )


if __name__ == "__main__":
    main()
