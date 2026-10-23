"""Text preprocessing shared by every NLP component.

Normalisation keeps character offsets (tokens carry spans into the normalised text) and never discards
quantities: numbers and unicode fractions are rewritten to ASCII so the quantity parser can read them.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_FRACTIONS = {
    "½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4", "⅕": "1/5", "⅖": "2/5", "⅗": "3/5",
    "⅘": "4/5", "⅙": "1/6", "⅚": "5/6", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8", "⁄": "/",
}
_FRACTION_RE = re.compile("|".join(map(re.escape, _FRACTIONS)))
_TAMIL = re.compile(r"[஀-௿]")


def fold_accents(text: str) -> str:
    """jalapeño -> jalapeno, crème -> creme; non-Latin scripts (e.g. Tamil) are left untouched."""
    out = []
    for ch in text:
        if ord(ch) < 0x250 and not ch.isascii():
            decomposed = unicodedata.normalize("NFKD", ch)
            out.append("".join(c for c in decomposed if not unicodedata.combining(c)))
        else:
            out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    text = text.replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    # "1½" -> "1 1/2", "½" -> "1/2"
    text = _FRACTION_RE.sub(lambda m: " " + _FRACTIONS[m.group(0)], text)
    text = fold_accents(text).lower()
    text = text.replace("�", " ")
    return re.sub(r"[ \t]+", " ", text).strip()


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int

    @property
    def is_word(self) -> bool:
        return self.text[0].isalpha() or bool(_TAMIL.match(self.text[0]))

    @property
    def is_number(self) -> bool:
        return bool(re.fullmatch(r"\d+(?:[./]\d+)?", self.text))


# words (with internal apostrophes), Tamil runs, numbers incl. decimals/fractions, single punctuation
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?|[஀-௿]+|\d+(?:[./]\d+)?|[^\s\w]|_")


def tokenize(normalized_text: str) -> list[Token]:
    return [Token(m.group(0), m.start(), m.end()) for m in _TOKEN_RE.finditer(normalized_text)]


STOPWORDS = frozenset(
    """a an the and or of for to in on at by with from into onto over under about as is are be been being am was were
    i me my mine we us our you your it its this that these those there here some any all can could would should will
    shall may might must do does did done have has had having get got make made want wants need needs like please
    what which who whom whose how when where why something anything thing things recipe recipes dish dishes meal
    meals food foods cook cooking cooked prepare preparing suggest find show give me let let's lets just also very
    really more less most least much many few one ones good nice tasty delicious yummy idea ideas option options
    today tonight now then so but if than too quite pretty kind sort type""".split()
)
