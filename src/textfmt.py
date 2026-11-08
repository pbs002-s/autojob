"""Plain-text cleanup for LLM output that lands in emails and job forms."""
import re

_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__", re.S)
_HEADING = re.compile(r"(?m)^#{1,6}\s*")
_BULLET = re.compile(r"(?m)^(\s*)[*\-+]\s+")
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def clean_markdown(text: str) -> str:
    """Strip markdown syntax so the text reads naturally when pasted or emailed."""
    text = _BOLD.sub(lambda m: m.group(1) or m.group(2), text or "")
    text = _HEADING.sub("", text)
    text = _BULLET.sub(r"\1• ", text)
    text = _ITALIC.sub(r"\1", text)
    text = _LINK.sub(r"\1 (\2)", text)
    return text.strip()
