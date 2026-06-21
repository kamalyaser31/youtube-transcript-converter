"""
YouTube Transcriber Pro - Main Entry Point with PyArabic Refinement
"""

import argparse
import os
import sys
from typing import List, Optional

import wx
from converter_engine import YTConverterEngine
from converter_gui import YTMainFrame


def run_cli(
    urls: List[str],
    output: Optional[str],
    langs: List[str],
    cookies: Optional[str],
):
    """CLI execution path."""
    engine = YTConverterEngine()
    out_dir = output or os.getcwd()
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    print(f"[*] Processing {len(urls)} URLs...")
    print(f"[*] Preferred Languages: {langs}")
    if cookies:
        print(f"[*] Using Cookies: {cookies}")

    def on_status(event_type, msg, details):
        if event_type == "start_video":
            print(f"    - Fetching: {msg}")
        elif event_type == "success":
            print(f"    - [OK] {msg}")
        elif event_type == "fail":
            print(f"    - [FAIL] {msg}")

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Working on: {url}")
        engine.convert(url, out_dir, langs, cookies, on_status=on_status)


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description="YouTube Transcriber Pro (PyArabic Enhanced)"
    )
    parser.add_argument("-i", "--input", nargs="+", help="URLs to process")
    parser.add_argument("-o", "--output", help="Custom output directory")
    parser.add_argument(
        "-l",
        "--langs",
        nargs="+",
        default=["ar", "en"],
        help="Language codes in order of preference",
    )
    parser.add_argument("-c", "--cookies", help="Path to cookies.txt file")

    if len(sys.argv) == 1:
        app = wx.App()
        frame = YTMainFrame()
        frame.Show()
        app.MainLoop()
    else:
        args = parser.parse_args()
        if not args.input:
            parser.print_help()
        else:
            run_cli(args.input, args.output, args.langs, args.cookies)


if __name__ == "__main__":
    main()
