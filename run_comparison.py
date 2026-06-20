"""
Comparison Script: Raw vs Refined Arabic Transcript
"""

import os
import re
from converter_engine import YTConverterEngine
from text_processor import ArabicTextRefiner

def run_comparison(url):
    engine = YTConverterEngine()
    refiner = ArabicTextRefiner()
    
    print(f"[*] Fetching transcript for: {url}")
    success, title, video_id = engine.get_video_info(url)
    if not success:
        print(f"Error: {title}")
        return

    raw_lines = engine.fetch_transcript_segments(video_id)
    if not raw_lines:
        print("Error: Could not fetch transcript.")
        return

    # 1. RAW Version
    raw_content = " ".join(raw_lines)
    with open("Raw_Transcript.md", "w", encoding="utf-8") as f:
        f.write(f"Title: {title} (RAW)\nURL: {url}\n\n" + raw_content)

    # 2. REFINED Version
    refined_content = refiner.structure_paragraphs(raw_lines)
    with open("Refined_Transcript.md", "w", encoding="utf-8") as f:
        f.write(f"Title: {title} (REFINED)\nURL: {url}\n\n" + refined_content)

    print("[*] Comparison files created: Raw_Transcript.md and Refined_Transcript.md")

if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=CGqhTO1ruGQ"
    run_comparison(url)
