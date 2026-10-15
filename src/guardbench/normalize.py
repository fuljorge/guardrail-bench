"""Disguise normalisation before the detectors (the "local layer", part 1).

Attacks swap Latin letters for look-alike Cyrillic or Greek ones, hide invisible
characters, separate letters ("i.g.n.o.r.e") or use leetspeak ("1gn0r3"). The normalised
text undoes these disguises for the patterns and the models; the detectors also receive the
original text, and the worse result counts.

Copied unchanged (code) from the Implementation Project, where it runs in the
Control Plane before every guardrail check; comments are in Portuguese.
"""

from __future__ import annotations

import re
import unicodedata

# Letras cirílicas e gregas que imitam letras latinas (já em minúsculas, depois do casefold),
# em escapes: o código-fonte não mostra caracteres que se confundem com os latinos.
_HOMOGLYPHS = str.maketrans(
    {
        "\u0430": "a", "\u0432": "b", "\u0435": "e", "\u0451": "e", "\u043a": "k", "\u043c": "m",
        "\u043d": "h", "\u043e": "o", "\u0440": "p", "\u0441": "c", "\u0442": "t", "\u0443": "y",
        "\u0445": "x", "\u0456": "i", "\u0457": "i", "\u0458": "j", "\u0455": "s", "\u0501": "d",
        "\u051b": "q", "\u051d": "w", "\u0261": "g", "\u0131": "i", "\u03b1": "a", "\u03b2": "b",
        "\u03b5": "e", "\u03b7": "n", "\u03b9": "i", "\u03ba": "k", "\u03bd": "v", "\u03bf": "o",
        "\u03c1": "p", "\u03c4": "t", "\u03c5": "u", "\u03c7": "x", "\u03c9": "w",
    }
)  # fmt: skip
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"})
_LEET_CHARS = frozenset("013457")
# Quatro ou mais letras isoladas separadas sempre pelo mesmo sinal: "i.g.n.o.r.e",
# "i g n o r e". O mesmo sinal evita juntar a palavra anterior ("o j.a.i.l...").
_SPACED_LETTERS = re.compile(r"(?<![\w])[a-z]([ .\-_*·•|/])(?:[a-z]\1){2,}[a-z](?![\w])")
_SEPARATORS = re.compile(r"[ .\-_*·•|/]")
_SPACES = re.compile(r"\s+")


def _visible(text: str) -> str:
    """Sem caracteres de formatação (largura zero, hífen invisível, direção do texto)."""
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def _without_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return unicodedata.normalize(
        "NFC", "".join(c for c in decomposed if not unicodedata.combining(c))
    )


def _is_leet_word(token: str) -> bool:
    return any(c.isalpha() for c in token) and any(c in _LEET_CHARS for c in token)


def _undo_leet(tokens: list[str]) -> list[str]:
    """Palavras com letras e dígitos trocados; um dígito sozinho só ao lado de uma delas."""
    leet = [_is_leet_word(t) for t in tokens]
    result = []
    for i, token in enumerate(tokens):
        lone = len(token) == 1 and token in _LEET_CHARS
        beside = (i > 0 and leet[i - 1]) or (i + 1 < len(tokens) and leet[i + 1])
        result.append(token.translate(_LEET) if leet[i] or (lone and beside) else token)
    return result


def normalize(text: str) -> str:
    value = _visible(unicodedata.normalize("NFKC", text)).casefold().translate(_HOMOGLYPHS)
    value = _without_accents(value)
    value = " ".join(_undo_leet(_SPACES.split(value.strip())))
    return _SPACED_LETTERS.sub(lambda m: _SEPARATORS.sub("", m.group(0)), value)
