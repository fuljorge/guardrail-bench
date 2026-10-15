"""Injection patterns (the "local layer", part 2) and credential patterns.

- **Injection:** typical phrases that try to change the agent's rules, in Brazilian
  Portuguese and English, searched in the **normalised** text (`normalize.py`: lower case,
  no accents, no disguises). They catch the obvious cases without a model.
- **Credentials:** not used by the benchmark.

Copied unchanged (code) from the Implementation Project, version
`PATTERNS_VERSION`; comments are in Portuguese. Linear-time expressions only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS_VERSION = "patterns-2026-10-14"
CREDENTIAL_LABEL = "<CREDENCIAL>"

_W = r"(?:\w+\s+){0,3}?"

INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "override",
        re.compile(
            r"\b(?:ignor\w*|desconsider\w*|esquec\w*|desobedec\w*|anul\w*|burl\w*)\s+" + _W
            + r"(?:instruc\w*|regras?|diretriz\w*|ordens|orientac\w*|restric\w*|politicas?"
            r"|prompt)\b"
        ),
    ),
    (
        "override",
        re.compile(
            r"\b(?:ignore|disregard|forget|override|bypass)\s+" + _W
            + r"(?:instructions?|rules|guidelines|prompt|directives)\b"
        ),
    ),
    (
        "reveal_prompt",
        re.compile(
            r"\b(?:mostr\w*|revel\w*|exib\w*|imprim\w*|repit\w*|repet\w*|diga|informe|passe"
            r"|copie|transcrev\w*)\s+" + _W
            + r"(?:prompt|instrucoes\s+(?:iniciais|originais|do\s+sistema|de\s+sistema)"
            r"|mensagem\s+(?:do|de)\s+sistema|configurac\w+\s+(?:interna|do\s+sistema))\b"
        ),
    ),
    (
        "reveal_prompt",
        re.compile(
            r"\b(?:show|reveal|print|repeat|output|display|tell\s+me)\s+" + _W
            + r"(?:system\s+prompt|prompt|initial\s+instructions|system\s+message"
            r"|instructions)\b"
        ),
    ),
    (
        "role_play",
        re.compile(
            r"\b(?:voce|vc)\s+(?:agora\s+)?(?:e|sera|vai\s+ser|passa\s+a\s+ser)\s+"
            r"(?:o\s+|a\s+|um\s+|uma\s+)?(?:dan\b|(?:ia|assistente|chatbot)\s+sem\s+"
            r"(?:regras|restricoes|filtros|limites))"
        ),
    ),
    (
        "role_play",
        re.compile(
            r"\b(?:you\s+are\s+now|act\s+as|you\s+will\s+act\s+as)\s+(?:an?\s+)?"
            r"(?:dan\b|unrestricted|unfiltered|jailbroken)"
        ),
    ),
    (
        "special_mode",
        re.compile(
            r"\bmodo\s+(?:desenvolvedor|developer|deus|god|jailbreak|dan|irrestrito"
            r"|sem\s+(?:restricoes|filtros|regras))\b"
        ),
    ),
    ("special_mode", re.compile(r"\b(?:developer|god|jailbreak|dan)\s+mode\b")),
    (
        "pretend",
        re.compile(
            r"\b(?:finja|fingir|faca\s+de\s+conta|imagine|suponha)\s+(?:que\s+)?"
            r"(?:voce\s+|vc\s+)?(?:nao\s+tem|nao\s+possui|esta\s+sem|e\s+livre\s+de"
            r"|nao\s+segue)\s+(?:\w+\s+){0,2}?(?:regras|restricoes|filtros|limites|diretrizes)"
        ),
    ),
    (
        "pretend",
        re.compile(
            r"\bpretend\s+(?:that\s+)?you\s+(?:have\s+no|are\s+without|don'?t\s+have)\s+"
            r"(?:any\s+)?(?:rules|restrictions|filters|limits|guidelines)"
        ),
    ),
    (
        "from_now_on",
        re.compile(
            r"\ba\s+partir\s+de\s+agora,?\s+(?:voce|vc)\s+(?:deve|vai|ira|precisa)\s+"
            r"(?:ignorar|desobedecer|esquecer|responder\s+sem)"
        ),
    ),
    (
        "from_now_on",
        re.compile(r"\bfrom\s+now\s+on,?\s+you\s+(?:will|must|should)\s+(?:ignore|disregard)"),
    ),
    ("fake_system", re.compile(r"\bnovas?\s+instruc\w*(?:\s+do\s+sistema)?\s*:")),
    ("fake_system", re.compile(r"<\|?\s*(?:im_start|system|endoftext)")),
    ("fake_system", re.compile(r"(?:^|\n)\s*#{2,}\s*(?:system|instruc\w*|instruction)")),
    ("fake_system", re.compile(r"(?:^|\n)\s*(?:system|sistema)\s*:")),
)  # fmt: skip


def injection_matches(normalized: str) -> list[str]:
    """Ids dos padrões de injeção encontrados no texto normalizado (sem repetição)."""
    return list(dict.fromkeys(name for name, rx in INJECTION_PATTERNS if rx.search(normalized)))


CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("api_key", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"), 0),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), 0),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}"), 0),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}"), 0),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), 0),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]{0,40}PRIVATE KEY-----"), 0),
    ("bearer", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{20,}=*"), 0),
    (
        "assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|senha|password|passwd|client[_-]?secret)\b"
            r"\s*[:=]\s*(\S{8,})"
        ),
        1,
    ),
)  # fmt: skip


@dataclass(frozen=True)
class CredentialFinding:
    kind: str
    start: int
    end: int


def find_credentials(text: str) -> list[CredentialFinding]:
    """Credenciais no texto original, sem sobreposição (a mais longa vence)."""
    found = [
        CredentialFinding(kind, *match.span(group))
        for kind, rx, group in CREDENTIAL_PATTERNS
        for match in rx.finditer(text)
    ]
    found.sort(key=lambda f: (-(f.end - f.start), f.start))
    chosen: list[CredentialFinding] = []
    for item in found:
        if all(item.end <= c.start or item.start >= c.end for c in chosen):
            chosen.append(item)
    return sorted(chosen, key=lambda f: f.start)


def mask_credentials(text: str) -> str:
    pieces, last = [], 0
    for finding in find_credentials(text):
        pieces += [text[last : finding.start], CREDENTIAL_LABEL]
        last = finding.end
    return "".join(pieces) + text[last:]
