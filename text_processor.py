"""YouTube transcript linguistic refinement module.

Provides functional normalization, noise removal, and semantic paragraphing
using Python standard library only.
"""

from __future__ import annotations

import re
from typing import List


def clean_text_line(text: str, is_arabic: bool = True) -> str:
    """Normalize a single transcript line while preserving grammar and orthography."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]*>", "", text)
    if is_arabic:
        cleaned = cleaned.replace("ـ", "")
    # Fillers go first: the repeat collapse below shortens them to two letters.
    cleaned = re.sub(r"\b[اإأآ]{3,}\b|\b[م]{3,}\b", "", cleaned)
    cleaned = re.sub(r"(.)\1{2,}", r"\1\1", cleaned)
    cleaned = re.sub(r"[^\w\s\.\!\?؟،؛,:\-—\"'()«»ﷺ\u064B-\u0652]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _should_break_paragraph(chunk_len: int, line: str) -> bool:
    """Determine if current accumulated chunk should break into a new paragraph."""
    has_terminal_punct = bool(re.search(r"[\.\!\?؟]\s*$", line))
    return (chunk_len >= 250 and has_terminal_punct) or chunk_len >= 500


def refine_transcript(lines: List[str], lang: str = "ar") -> str:
    """Refine and structure raw transcript segments into readable paragraphs."""
    is_ar = lang.lower().startswith("ar")
    paragraphs: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for line in lines:
        cleaned = clean_text_line(line, is_arabic=is_ar)
        if not cleaned:
            continue
        current_chunk.append(cleaned)
        current_len += len(cleaned)
        if _should_break_paragraph(current_len, cleaned):
            paragraphs.append(" ".join(current_chunk))
            current_chunk, current_len = [], 0

    if current_chunk:
        paragraphs.append(" ".join(current_chunk))
    return "\n\n".join(paragraphs)
