"""
Undo the cheap tricks that hide a prompt from pattern matching and from the
moderation classifier while leaving it readable to a language model.

Two levels. `strip_hidden` runs on the prompt itself before it is stored or
sent anywhere: it drops characters that carry text the reader cannot see.
`fold` builds a second spelling used only for checking: it is lossy on
purpose (look-alike letters, leetspeak, spaced-out words) and never reaches a
model or the dataset.
"""

import base64
import codecs
import re
import unicodedata

# Unicode tag characters (U+E0000-E007F) spell out ASCII that most screens do
# not draw but models read, and bidi controls reorder what an admin sees.
_HIDDEN = re.compile("[\U000e0000-\U000e007f\u202a-\u202e\u2066-\u2069]")

# Characters with no visible width that get slipped between letters so that
# "say" no longer reads as "say" to a regex or a classifier. Category Cf covers
# zero-width spaces and joiners, soft hyphens and word joiners; the rest are
# fillers and selectors that are not Cf.
_INVISIBLE_EXTRA = "\u034f\u115f\u1160\u17b4\u17b5\u180b\u180c\u180d\u3164\uffa0"

# Cyrillic and Greek letters drawn like Latin ones.
_LOOKALIKES = "аеорсухіјѕԁԛԝАВЕКМНОРСТХЅІЈαονρτικχΑΒΕΖΗΙΚΜΝΟΡΤΧΥ"
_LATIN = "aeopcyxijsdqwABEKMHOPCTXSIJaovptikxABEZHIKMNOPTXY"
_CONFUSABLES = str.maketrans(_LOOKALIKES, _LATIN)
_CONFUSABLE_CHARS = frozenset(_LOOKALIKES)
_LEET = str.maketrans("013457@$", "oieastas")

# Three or more single letters split by one separator: "b o m b", "b.o.m.b".
_SPACED = re.compile(r"(?<!\w)(?:[^\W\d_][ .\-_*]){2,}[^\W\d_](?!\w)")
_HORIZONTAL_SPACE = re.compile(r"[^\S\n]+")


def strip_hidden(text: str) -> str:
    return _HIDDEN.sub("", text)


def drop_invisible(text: str) -> str:
    return "".join(
        c
        for c in text
        if unicodedata.category(c) != "Cf"
        and c not in _INVISIBLE_EXTRA
        and not 0xFE00 <= ord(c) <= 0xFE0F
    )


def _fold_word(word: str) -> str:
    has_confusable = any(c in _CONFUSABLE_CHARS for c in word)
    if has_confusable and all(
        c.isascii() or c in _CONFUSABLE_CHARS or not c.isalpha() for c in word
    ):
        word = word.translate(_CONFUSABLES)
    if any(c.isalpha() for c in word) and any(c in "013457@$" for c in word):
        word = word.translate(_LEET)
    return word


def fold(text: str) -> str:
    """The spelling a checker should look at. Lossy, never shown or stored."""
    text = unicodedata.normalize("NFKC", strip_hidden(text))
    text = drop_invisible(text)
    text = re.sub(r"\S+", lambda m: _fold_word(m.group()), text)
    text = _SPACED.sub(lambda m: re.sub(r"[ .\-_*]", "", m.group()), text)
    return _HORIZONTAL_SPACE.sub(" ", text)


_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/_-]{24,}={0,2}")
_ROT13_HINT = re.compile(r"\brot[\s-]*13\b|\bc[ée]sar\b|\bcaesar\b", re.IGNORECASE)
_REVERSED_HINT = re.compile(
    r"\bà l'envers\b|\breversed?\b|\bbackwards?\b|\bà rebours\b|\binvers[ée]e?\b",
    re.IGNORECASE,
)


def _looks_like_text(value: str) -> bool:
    if len(value) < 8:
        return False
    readable = sum(c.isprintable() or c.isspace() for c in value)
    return readable / len(value) >= 0.95 and any(c.isalpha() for c in value)


def decoded_variants(text: str) -> list[str]:
    """
    What a model asked to decode part of the prompt would read: every base64
    blob that decodes to text, and the whole prompt in ROT13 or reversed when
    it mentions either. One level only; nested encodings are not followed.
    """
    variants = []
    for blob in _BASE64_BLOB.findall(text):
        standard = blob.translate(str.maketrans("-_", "+/")).rstrip("=")
        try:
            decoded = base64.b64decode(
                standard + "=" * (-len(standard) % 4), validate=True
            ).decode("utf-8")
        except ValueError:
            continue
        if _looks_like_text(decoded):
            variants.append(decoded)
    if _ROT13_HINT.search(text):
        variants.append(codecs.encode(text, "rot13"))
    if _REVERSED_HINT.search(text):
        variants.append(text[::-1])
    return variants
