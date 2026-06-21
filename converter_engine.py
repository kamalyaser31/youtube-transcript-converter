"""
YouTube Transcriber Engine - Professional Logic
Uses text_processor for linguistic refinement.
"""

import os
import re
from typing import Tuple, List, Optional
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from text_processor import TextRefinerFactory


class YTConverterEngine:
    """Core logic with robust fetching and modular text processing."""

    def __init__(
        self,
        refiner_factory: Optional[TextRefinerFactory] = None,
        youtube_dl_client=None,
        transcript_api_client=None,
    ):
        # Dependency Injection for refiner factory and external API clients
        self.ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }
        self.refiner_factory = refiner_factory or TextRefinerFactory()
        self.ydl_client = youtube_dl_client or yt_dlp.YoutubeDL
        self.transcript_api = transcript_api_client or YouTubeTranscriptApi

    def get_video_info(self, url: str) -> Tuple[bool, dict]:
        """Fetches video or playlist info."""
        try:
            with self.ydl_client(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return True, info
        except Exception as e:
            return False, {"error": str(e)}

    def fetch_transcript_segments(
        self,
        video_id: str,
        languages: List[str] = ("ar", "en"),
        cookies_path: Optional[str] = None,
    ) -> Tuple[List[str], str]:
        """Fetcher returning transcript lines and its language code."""
        try:
            api = self.transcript_api()
            # If cookies_path is set, list() supports cookie loading
            if cookies_path and os.path.exists(cookies_path):
                transcript_list = api.list(video_id, cookies=cookies_path)
            else:
                transcript_list = api.list(video_id)

            if not transcript_list:
                return [], ""

            # Identify best transcript (manual then generated)
            try:
                transcript = transcript_list.find_transcript(languages)
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(
                        languages
                    )
                except Exception:
                    transcript = next(iter(transcript_list))

            data = transcript.fetch()
            lines = [
                (
                    item.get("text", "")
                    if isinstance(item, dict)
                    else getattr(item, "text", str(item))
                )
                for item in data
            ]
            return lines, transcript.language_code
        except Exception:
            return [], ""

    def process_single_video(
        self,
        video_id: str,
        title: str,
        url: str,
        output_dir: str,
        languages: List[str],
        cookies_path: Optional[str],
        on_status=None,
        check_cancelled=None,
    ) -> Tuple[bool, str]:
        """Core processing for one video with cancellation checks."""
        if check_cancelled and check_cancelled():
            return False, "Cancelled by user"

        try:
            raw_lines, lang_code = self.fetch_transcript_segments(
                video_id, languages, cookies_path
            )
            if not raw_lines:
                return False, f"Could not fetch transcript for: {title}"

            if check_cancelled and check_cancelled():
                return False, "Cancelled by user"

            # Dynamically select the refiner strategy based on language
            refiner = self.refiner_factory.get_refiner(lang_code)
            final_content = refiner.structure_paragraphs(raw_lines)

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
        on_status=None,
        check_cancelled=None,
    ) -> List[Tuple[bool, str]]:
        """Main conversion flow handling both single videos and playlists."""
        results = []
        if check_cancelled and check_cancelled():
            return [(False, "Cancelled by user")]

        success, info = self.get_video_info(url)
        if not success:
            return [(False, f"Info Error: {info.get('error')}")]

        if "entries" in info:
            # It's a playlist
            entries = list(info["entries"])
            for entry in entries:
                if check_cancelled and check_cancelled():
                    results.append((False, "Cancelled by user"))
                    break
                v_id = entry.get("id")
                v_title = entry.get("title", "video")
                v_url = f"https://www.youtube.com/watch?v={v_id}"

                if on_status:
                    on_status("start_video", v_title, {"url": v_url})

                ok, msg = self.process_single_video(
                    v_id,
                    v_title,
                    v_url,
                    output_dir,
                    languages,
                    cookies_path,
                    on_status,
                    check_cancelled,
                )
                results.append((ok, msg))

                if on_status:
                    on_status(
                        "success" if ok else "fail", msg, {"title": v_title}
                    )
        else:
            # Single video
            v_id = info.get("id")
            v_title = info.get("title", "video")

            if on_status:
                on_status("start_video", v_title, {"url": url})

            ok, msg = self.process_single_video(
                v_id,
                v_title,
                url,
                output_dir,
                languages,
                cookies_path,
                on_status,
                check_cancelled,
            )
            results.append((ok, msg))

            if on_status:
                on_status("success" if ok else "fail", msg, {"title": v_title})

        return results
