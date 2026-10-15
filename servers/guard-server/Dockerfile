# syntax=docker/dockerfile:1.10
# Servidor de guardrails do Implementation Project (specs/010-guardrails, plano §4.1). Mesmo formato da
# imagem do Strands Decider (services/strands-decider): roda num servidor com GPU, sem
# estado e sem tenant, e só o Control Plane e o harness de avaliação o chamam.
#
#   GPU (padrão, CUDA 12.6):  docker build -t guard-server services/guard-server
#   CPU (local):              docker build --build-arg TORCH_INDEX=cpu -t guard-server:cpu services/guard-server
#
# Contexto de build: esta pasta. Ver README.md para rodar no servidor.

FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3

ARG TORCH_INDEX=cu126
ARG TORCH_VERSION=2.14.0

# Correções de segurança do Debian publicadas depois da imagem base (varredura Trivy).
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 guard \
    && useradd --system --uid 10001 --gid guard --create-home --home-dir /home/guard guard \
    && mkdir -p /home/guard/.cache/huggingface \
    && chown -R guard:guard /home/guard/.cache

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONUNBUFFERED=1
RUN pip install --index-url "https://download.pytorch.org/whl/${TORCH_INDEX}" \
        "torch==${TORCH_VERSION}"
COPY requirements.txt /opt/guard/requirements.txt
# setuptools e wheel só servem para instalar pacotes e vêm da imagem base com CVEs (Trivy).
RUN pip install -r /opt/guard/requirements.txt \
    && pip uninstall -y setuptools wheel
COPY guard_server.py detectors.json /opt/guard/

# Os modelos (revisões fixadas em detectors.json) são baixados na primeira partida para o
# volume do cache do Hugging Face.
ENV GUARD_HOST=0.0.0.0 \
    GUARD_PORT=8302 \
    GUARD_DEVICE=cuda \
    GUARD_CONFIG=/opt/guard/detectors.json \
    GUARD_LOG_LEVEL=warning \
    HF_HOME=/home/guard/.cache/huggingface \
    PYTHONPATH=/opt/guard

USER guard
VOLUME ["/home/guard/.cache/huggingface"]
EXPOSE 8302

# /health sem token responde só {"status": "ok"}; não expõe detalhes.
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8302/health', timeout=4)"]

# GUARD_API_KEY vem do ambiente (obrigatório).
CMD ["python", "-m", "guard_server"]
