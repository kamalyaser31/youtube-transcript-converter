"""
YouTube Transcriber Engine - Professional Logic
Uses text_processor for linguistic refinement.
"""

import os
import re
from typing import Tuple, List, Optional
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from text_processor import ArabicTextRefiner


class YTConverterEngine:
    """Core logic with robust fetching and modular text processing."""

    def __init__(self):
        self.ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
        self.refiner = ArabicTextRefiner()

    def get_video_info(self, url: str) -> Tuple[bool, dict]:
        """Fetches video or playlist info."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return True, info
        except Exception as e:
            return False, {"error": str(e)}

    def fetch_transcript_segments(
        self,
        video_id: str,
        languages: List[str] = ("ar", "en"),
        cookies_path: Optional[str] = None,
    ) -> List[str]:
        """Ultra-compatible fetcher using API instance."""
        try:
            # Note: In some versions list() doesn't take cookies,
            # we may need to set them in the constructor or session if needed.
            # For now, let's try without cookies to get basic functionality.
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            if not transcript_list:
                return []

            # Identify best transcript (manual then generated)
            try:
                transcript = transcript_list.find_transcript(languages)
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                except Exception:
                    transcript = next(iter(transcript_list))

            data = transcript.fetch()
            return [
                (
                    item.get("text", "")
                    if isinstance(item, dict)
                    else getattr(item, "text", str(item))
                )
                for item in data
            ]
        except Exception as e:
            print(f"Error fetching for {video_id}: {e}")
            return []

    def process_single_video(
        self,
        video_id: str,
        title: str,
        url: str,
        output_dir: str,
        languages: List[str],
        cookies_path: Optional[str],
    ) -> Tuple[bool, str]:
        """Core processing for one video."""
        try:
            raw_lines = self.fetch_transcript_segments(
                video_id, languages, cookies_path
            )
            if not raw_lines:
                return False, f"Could not fetch transcript for: {title}"

            final_content = self.refiner.structure_paragraphs(raw_lines)
            clean_title = re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")
            target = os.path.join(output_dir, f"{clean_title[:100]}.md")

            counter = 1
            base_target = target
            while os.path.exists(target):
                target = base_target.replace(".md", f"_{counter}.md")
                counter += 1

            with open(target, "w", encoding="utf-8") as f:
                header = f"Title: {title}\nURL: {url}\n\n"
                f.write(header + final_content)

            return True, os.path.basename(target)
        except Exception as e:
            return False, str(e)

    def convert(
        self,
        url: str,
        output_dir: str,
        languages: List[str] = ("ar", "en"),
        cookies_path: Optional[str] = None,
    ) -> List[Tuple[bool, str]]:
        """Main conversion flow handling both single videos and playlists."""
        results = []
        success, info = self.get_video_info(url)
        if not success:
            return [(False, f"Info Error: {info.get('error')}")]

        if "entries" in info:
            # It's a playlist
            entries = list(info["entries"])
            for entry in entries:
                v_id = entry.get("id")
                v_title = entry.get("title", "video")
                v_url = f"https://www.youtube.com/watch?v={v_id}"
                ok, msg = self.process_single_video(
                    v_id, v_title, v_url, output_dir, languages, cookies_path
                )
                results.append((ok, msg))
        else:
            # Single video
            v_id = info.get("id")
            v_title = info.get("title", "video")
            ok, msg = self.process_single_video(
                v_id, v_title, url, output_dir, languages, cookies_path
            )
            results.append((ok, msg))

        return results
