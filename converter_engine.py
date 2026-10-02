"""YouTube Transcriber Engine.

Fetches video metadata and transcripts, delegates linguistic refinement,
and writes structured Markdown documents to disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import requests
import yt_dlp
from text_processor import refine_transcript
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    NotTranslatable,
    TranslationLanguageNotAvailable,
    YouTubeTranscriptApi,
)
from yt_dlp.utils import DownloadError

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

StatusCallback = Callable[[str, str, dict], None]


def sanitize_filename(title: str) -> str:
    """Sanitize title for safe cross-platform filesystem storage."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title).strip()
    clean = re.sub(r"\s+", "_", clean)[:100]
    if not clean or clean.upper() in WINDOWS_RESERVED_NAMES:
        return f"transcript_{clean or 'video'}"
    return clean


def get_unique_target(out_dir: Path, title: str) -> Path:
    """Generate a collision-free target Path in the output directory."""
    stem = sanitize_filename(title)
    target = out_dir / f"{stem}.md"
    counter = 1
    while target.exists():
        target = out_dir / f"{stem}_{counter}.md"
        counter += 1
    return target


def status_prefix(event_type: str) -> str:
    """Map a status event to the log prefix shared by CLI and GUI."""
    return {"success": "[OK]", "fail": "[FAIL]"}.get(event_type, "[*]")


def build_transcript_api(cookies_path: Optional[str] = None) -> YouTubeTranscriptApi:
    """Create the transcript client, sending Netscape cookies when given.

    youtube-transcript-api 1.x dropped its cookies argument; cookies now
    travel on the requests session it uses.
    """
    if not cookies_path:
        return YouTubeTranscriptApi()
    jar = MozillaCookieJar(cookies_path)
    jar.load(ignore_discard=True, ignore_expires=True)
    session = requests.Session()
    session.cookies = jar
    return YouTubeTranscriptApi(http_client=session)


@dataclass
class ConversionJob:
    """Settings shared by every video of one convert() call."""

    out_dir: Path
    languages: Sequence[str] = ("ar", "en")
    on_status: Optional[StatusCallback] = None
    check_cancelled: Optional[Callable[[], bool]] = None

    def is_cancelled(self) -> bool:
        return bool(self.check_cancelled and self.check_cancelled())

    def report(self, event_type: str, msg: str, details: dict) -> None:
        if self.on_status:
            self.on_status(event_type, msg, details)


class YTConverterEngine:
    """Core coordinator for metadata retrieval, transcript fetching,
    and output generation.
    """

    def __init__(self, transcript_client=None, ydl_client=None, cookies_path=None):
        self.ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        self.transcript_api = transcript_client or build_transcript_api(cookies_path)
        self.ydl_client = ydl_client or yt_dlp.YoutubeDL

    def get_video_info(self, url: str) -> Tuple[bool, dict]:
        """Fetch video or playlist metadata via yt-dlp."""
        try:
            with self.ydl_client(self.ydl_opts) as ydl:
                return True, ydl.extract_info(url, download=False)
        except DownloadError as err:
            return False, {"error": str(err)}

    def _translate_candidate(self, transcript_list, target_lang: str):
        """Attempt auto-translation of available transcripts to target language."""
        for transcript in transcript_list:
            if getattr(transcript, "is_translatable", False):
                try:
                    return transcript.translate(target_lang)
                except (NotTranslatable, TranslationLanguageNotAvailable):
                    continue
        return None

    def _select_transcript(self, transcript_list, languages: Sequence[str]):
        """Find best transcript: manual or generated, then auto-translated."""
        try:
            # find_transcript already prefers manual tracks over generated ones.
            return transcript_list.find_transcript(languages)
        except NoTranscriptFound:
            pass
        target = languages[0] if languages else "ar"
        translated = self._translate_candidate(transcript_list, target)
        return translated or next(iter(transcript_list))

    def fetch_transcript_segments(
        self, video_id: str, languages: Sequence[str] = ("ar", "en")
    ) -> Tuple[List[str], str, str]:
        """Fetch raw transcript segments; returns (lines, lang_code, error_message)."""
        try:
            t_list = self.transcript_api.list(video_id)
            candidate = self._select_transcript(t_list, languages)
            lines = [snippet.text for snippet in candidate.fetch()]
        except CouldNotRetrieveTranscript as err:
            return [], "", str(err)
        return lines, candidate.language_code, ""

    def _write_document(self, target: Path, title: str, url: str, content: str) -> None:
        """Write formatted transcript to disk."""
        target.parent.mkdir(parents=True, exist_ok=True)
        header = f"# {title}\nSource: {url}\n\n"
        target.write_text(header + content, encoding="utf-8")

    def process_single_video(
        self, video_id: str, title: str, url: str, job: ConversionJob
    ) -> Tuple[bool, str]:
        """Process one video to a markdown file, reporting outcome or reason."""
        if job.is_cancelled():
            return False, "Cancelled by user"
        raw_lines, lang, err_msg = self.fetch_transcript_segments(
            video_id, job.languages
        )
        if not raw_lines:
            return False, f"Transcript unavailable: {err_msg or 'No captions found'}"
        if job.is_cancelled():
            return False, "Cancelled by user"
        content = refine_transcript(raw_lines, lang=lang)
        target = get_unique_target(job.out_dir, title)
        self._write_document(target, title, url, content)
        return True, target.name

    def _process_entry(
        self, video_id: str, title: str, url: str, job: ConversionJob
    ) -> Tuple[bool, str]:
        """Process one video with status events, isolating its failure."""
        job.report("start_video", title, {"url": url})
        try:
            ok, msg = self.process_single_video(video_id, title, url, job)
        # Batch boundary: one broken video (network, disk) must not abort the
        # rest of the queue; the failure is reported, not hidden.
        except Exception as err:
            ok, msg = False, f"{type(err).__name__}: {err}"
        job.report("success" if ok else "fail", msg, {"title": title})
        return ok, msg

    def _process_playlist(
        self, entries: list, job: ConversionJob
    ) -> List[Tuple[bool, str]]:
        """Iterate over playlist entries and process each sequentially."""
        results = []
        for entry in entries:
            if job.is_cancelled():
                results.append((False, "Cancelled by user"))
                break
            v_id = entry.get("id")
            v_url = f"https://www.youtube.com/watch?v={v_id}"
            results.append(
                self._process_entry(v_id, entry.get("title", "video"), v_url, job)
            )
        return results

    def convert(self, url: str, job: ConversionJob) -> List[Tuple[bool, str]]:
        """Main entry for single video or playlist conversion."""
        ok, info = self.get_video_info(url)
        if not ok:
            msg = f"Metadata error: {info.get('error', 'unknown')}"
            job.report("fail", msg, {"url": url})
            return [(False, msg)]
        if "entries" in info:
            return self._process_playlist(list(info["entries"]), job)
        title = info.get("title", "video")
        return [self._process_entry(info.get("id"), title, url, job)]
