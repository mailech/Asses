"""Turn a free-text request into the flat token list the rules run against.

Normalisation is deliberately lossy and deliberately small: it removes the
differences that never carry meaning in a lodging request (case, punctuation,
the hyphen in "half-board") and nothing else.
"""

from __future__ import annotations

import re
import unicodedata

_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
# The lookalike characters below are the point, not a typo: requests really do
# arrive with a multiplication sign and with en and em dashes in them.
_MULTIPLIER = re.compile(r"\b(\d+)\s*[x×]\s*(?=[a-z])")  # noqa: RUF001
_HYPHEN_BETWEEN_WORDS = re.compile(r"(?<=[a-z0-9])[-–—/](?=[a-z0-9])")  # noqa: RUF001
_NUMBER_GLUED_TO_WORD = re.compile(r"(?<=\d)(?=[a-z])|(?<=[a-z])(?=\d)")
_NOT_TOKEN = re.compile(r"[^a-z0-9 ]+")
_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Return ``text`` reduced to lowercase words and digits separated by spaces."""
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = normalized.replace("&", " and ")
    normalized = _THOUSANDS.sub("", normalized)
    normalized = _MULTIPLIER.sub(r"\1 ", normalized)
    normalized = _HYPHEN_BETWEEN_WORDS.sub(" ", normalized)
    normalized = _NOT_TOKEN.sub(" ", normalized)
    # "10nights" and "3doubles" are typos, not words.
    normalized = _NUMBER_GLUED_TO_WORD.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    return normalized.split(" ") if normalized else []
