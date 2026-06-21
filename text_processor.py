"""
YouTube Transcriber - Arabic Text Processing Module
Handles linguistic normalization, noise removal, and paragraph structuring.
"""

import re
from typing import List

try:
    import pyarabic.araby as araby

    HAS_PYARABIC = True
except ImportError:
    HAS_PYARABIC = False


class BaseTextRefiner:
    """Base interface for text refining strategies."""

    def clean_text(self, text: str) -> str:
        """Apply basic normalization and noise removal to a single snippet."""
        raise NotImplementedError

    def structure_paragraphs(self, lines: List[str]) -> str:
        """Groups cleaned lines into logical paragraphs based on length."""
        cleaned_lines = [
            self.clean_text(line) for line in lines if line.strip()
        ]

        paragraphs = []
        current_chunk = []
        current_length = 0

        for line in cleaned_lines:
            if not line:
                continue
            current_chunk.append(line)
            current_length += len(line)

            # Trigger new paragraph after ~400 characters
            if current_length > 400:
                paragraphs.append(" ".join(current_chunk))
                current_chunk = []
                current_length = 0

        if current_chunk:
            paragraphs.append(" ".join(current_chunk))

        return "\n\n".join(paragraphs)


class GenericTextRefiner(BaseTextRefiner):
    """Generic text refiner for non-Arabic (English, German, etc.) texts."""

    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        # Remove HTML-like tags
        text = re.sub(r"<[^>]*>", "", text)
        # Remove long character repetitions (e.g., "haahaaaa" -> "haahaa")
        text = re.sub(r"(.)\1{2,}", r"\1\1", text)
        # Clean up punctuation and special chars
        text = re.sub(r"[^\w\s\.\!\?]", " ", text)
        # Final space cleanup
        text = re.sub(r"\s+", " ", text).strip()
        return text


class ArabicTextRefiner(BaseTextRefiner):
    """Refiner using PyArabic and Regex for Arabic transcript text."""

    def __init__(self):
        # List of common Arabic speech fillers to be removed
        self.fillers = [
            r"\bيعني\b",
            r"\bااا\b",
            r"\bطيب\b",
            r"\bكده\b",
            r"\bايه\b",
            r"\bفعليا\b",
            r"\bبشكل\s+كبير\b",
            r"\bتمام\b",
            r"\bاللي\b",
            r"\bعارفين\b",
            r"\bبقى\b",
        ]

    def clean_text(self, text: str) -> str:
        if not text:
            return ""

        # Remove HTML-like tags (sometimes present in auto-transcripts)
        text = re.sub(r"<[^>]*>", "", text)

        if HAS_PYARABIC:
            text = araby.strip_tashkeel(text)
            text = araby.strip_tatweel(text)
            text = araby.normalize_hamza(text)
            text = araby.normalize_alef(text)
            text = araby.normalize_teh(text)
        else:
            text = re.sub(r"[إأآ]", "ا", text)
            text = re.sub(r"ى", "ي", text)
            text = re.sub(r"ة", "ه", text)

        # Remove long character repetitions (e.g., "هههههه" -> "هه")
        text = re.sub(r"(.)\1{2,}", r"\1\1", text)

        # Remove fillers (Case-insensitive check for non-Arabic parts if any)
        for pattern in self.fillers:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Remove adjacent duplicate words (3 or more -> 1, 2 -> 2)
        # This prevents aggressive deletion of double-emphasis like "لا لا"
        text = re.sub(r"\b(\w+)(?:\s+\1){2,}\b", r"\1", text)

        # Clean up punctuation and special chars
        text = re.sub(r"[^\w\s\.\!\?؟،]", " ", text)

        # Final space cleanup
        text = re.sub(r"\s+", " ", text).strip()
        return text


class TextRefinerFactory:
    """Factory to select the text refiner strategy based on language."""

    @staticmethod
    def get_refiner(lang: str) -> BaseTextRefiner:
        """Returns the specific refiner based on language preference."""
        if lang.lower().startswith("ar"):
            return ArabicTextRefiner()
        return GenericTextRefiner()
