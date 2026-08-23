"""Slug generation. Slugs are derived server-side, never taken from the client."""
import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

_TRANSLIT = str.maketrans(
    {"ʻ": "", "ʼ": "", "'": "", "’": "", "ў": "u", "қ": "q", "ғ": "g", "ҳ": "h"}
)


def slugify(value: str, max_length: int = 120) -> str:
    lowered = value.strip().lower().translate(_TRANSLIT)
    normalized = unicodedata.normalize("NFKD", lowered)
    ascii_only = normalized.encode("ascii", "ignore").decode()
    slug = _NON_ALNUM.sub("-", ascii_only).strip("-")
    return slug[:max_length] or "item"
