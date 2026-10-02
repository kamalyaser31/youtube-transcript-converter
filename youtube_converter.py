"""YouTube Transcriber - Main CLI and GUI Entry Point.

Provides instant CLI transcription and on-demand PySide6 GUI launch via lazy import.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from converter_engine import ConversionJob, YTConverterEngine, status_prefix


def _on_cli_status(event_type: str, msg: str, _details: dict) -> None:
    """Status callback formatting progress for CLI stdout."""
    print(f"  {status_prefix(event_type)} {msg}")


def run_cli(
    urls: List[str], output: Optional[str], langs: List[str], cookies: Optional[str]
) -> int:
    """Execute batch conversion; exit code 1 when any video failed."""
    try:
        engine = YTConverterEngine(cookies_path=cookies)
    except OSError as err:  # missing file, or http.cookiejar.LoadError
        print(f"[FAIL] Cannot load cookies file {cookies}: {err}", file=sys.stderr)
        return 2
    out_dir = Path(output) if output else Path.cwd() / "md"
    out_dir.mkdir(parents=True, exist_ok=True)
    job = ConversionJob(out_dir, langs, on_status=_on_cli_status)
    print(f"[*] Processing {len(urls)} URL(s) -> {out_dir}")
    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Target: {url}")
        results.extend(engine.convert(url, job))
    return 0 if all(ok for ok, _ in results) else 1


def launch_gui() -> int:
    """Launch PySide6 graphical interface with lazy module import."""
    from PySide6.QtWidgets import QApplication
    from converter_gui import YTMainFrame

    app = QApplication(sys.argv)
    window = YTMainFrame()
    window.show()
    return app.exec()


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="YouTube Transcriber (CLI & Accessible PySide6 GUI)"
    )
    parser.add_argument(
        "-i", "--input", nargs="+", help="YouTube video or playlist URLs"
    )
    parser.add_argument(
        "-o", "--output", help="Output directory path (defaults to ./md)"
    )
    parser.add_argument(
        "-l",
        "--langs",
        nargs="+",
        default=["ar", "en"],
        help="Preferred language codes",
    )
    parser.add_argument("-c", "--cookies", help="Path to cookies.txt file")
    parser.add_argument(
        "--gui", action="store_true", help="Launch graphical user interface"
    )
    return parser


def main() -> int:
    """Application entry point routing to GUI or CLI mode."""
    parser = build_parser()
    if len(sys.argv) == 1:
        return launch_gui()
    args = parser.parse_args()
    if args.gui:
        return launch_gui()
    if not args.input:
        parser.print_help()
        return 1
    return run_cli(args.input, args.output, args.langs, args.cookies)


if __name__ == "__main__":
    sys.exit(main())
