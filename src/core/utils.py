"""Shared utilities."""
import re


def slugify(text: str) -> str:
    """Convert text to a lowercase kebab-case slug."""
    if not text:
        return ""
    s = text.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9\-\s]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")
