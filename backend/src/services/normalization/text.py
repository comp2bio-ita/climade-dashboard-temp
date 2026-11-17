import re
import unicodedata


def normalize_text(text: str) -> str:
    """Fold a string for deterministic geographic comparison.

    For lookup and matching only. Never use the return value to build
    ``location_normalized`` or other persisted canonical location strings.
    """
    if not text:
        return ""

    decomposed = unicodedata.normalize("NFKD", str(text))
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    folded = without_marks.casefold().strip()
    folded = re.sub(r"[^\w\s-]", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    return folded


def parse_location(location: str) -> tuple[str | None, list[str]]:
    """Split ``Country: part1, part2`` into country and trimmed sub-country parts."""
    if not location or ":" not in location:
        return None, []

    country, remainder = location.split(":", 1)
    country = country.strip()
    parts = [part.strip() for part in remainder.split(",") if part.strip()]
    return country or None, parts
