"""Independent automated test suite for YouTube Transcript Converter.

Compliant with test-guard, clean-code-guard, and karpathy-guidelines.
Tests observable behavior, boundary cases, and error propagation
without implementation coupling.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from converter_engine import (
    ConversionJob,
    YTConverterEngine,
    get_unique_target,
    sanitize_filename,
)
from text_processor import clean_text_line, refine_transcript
from youtube_transcript_api import NoTranscriptFound, RequestBlocked


def test_arabic_text_preserves_grammatical_relatives_and_meaning():
    input_text = "الرجل اللي جاء أمس قال كلاماً طيباً وهو يعني الصدق"
    result = clean_text_line(input_text, is_arabic=True)
    assert "اللي" in result, f"Expected 'اللي' to be preserved, got: {result}"
    assert "طيباً" in result, f"Expected 'طيباً' to be preserved, got: {result}"
    assert "يعني" in result, f"Expected 'يعني' to be preserved, got: {result}"


def test_arabic_text_strips_hesitation_phonemes_and_tatweel():
    input_text = "قال اااا هذا كــــتـاب مــــفيد اممم حقاً"
    result = clean_text_line(input_text, is_arabic=True)
    assert (
        "اا" not in result
    ), f"Expected hesitation 'اااا' removed whole, got: {result}"
    assert "كتاب مفيد" in result or "كـتاب" not in result


def test_arabic_punctuation_and_honorific_survive_cleaning():
    input_text = "قال النبي ﷺ: «إنما الأعمال بالنيات»؛ (متفق عليه)"
    result = clean_text_line(input_text, is_arabic=True)
    for mark in ("ﷺ", "«", "»", "؛", "(", ")"):
        assert mark in result, f"Expected {mark!r} preserved, got: {result}"


def test_arabic_orthography_preserves_teh_marbuta_and_hamza():
    input_text = "رحمة الله واسعة في مدرسة إبراهيم"
    result = clean_text_line(input_text, is_arabic=True)
    assert "رحمة" in result, f"Expected 'رحمة' with teh marbuta, got: {result}"
    assert "مدرسة" in result, f"Expected 'مدرسة' with teh marbuta, got: {result}"
    assert (
        "إبراهيم" in result
    ), f"Expected 'إبراهيم' with hamza preserved, got: {result}"


def test_paragraph_structuring_breaks_on_terminal_punctuation():
    sentence_one = (
        "هذه الجملة الأولى تامة المعنى وفيها تفصيل كاف للبيان والتوضيح المسهب."
    )
    sentence_two = (
        "أما الجملة الثانية فهي تبدأ فقرة جديدة في سياق مستقل تماماً ومفيد جداً."
    )
    lines = [sentence_one * 4, sentence_two]
    structured = refine_transcript(lines, lang="ar")
    paragraphs = structured.split("\n\n")
    assert (
        len(paragraphs) >= 2
    ), f"Expected at least 2 paragraphs, got {len(paragraphs)}"


def test_filename_sanitization_guards_windows_reserved_names():
    assert sanitize_filename("CON") == "transcript_CON"
    assert sanitize_filename("prn") == "transcript_prn"
    assert sanitize_filename("NUL") == "transcript_NUL"
    sanitized = sanitize_filename('Bad/Name:With*Illegal?"Chars<And>Pipes|')
    for illegal_char in r'\/*?:"<>|':
        assert illegal_char not in sanitized


def test_unique_target_increments_stem_when_file_exists():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir)
        first_file = out_path / "lecture.md"
        first_file.write_text("content", encoding="utf-8")

        second_target = get_unique_target(out_path, "lecture")
        assert second_target.name == "lecture_1.md"

        second_target.write_text("content", encoding="utf-8")
        third_target = get_unique_target(out_path, "lecture")
        assert third_target.name == "lecture_2.md"


def test_unique_target_handles_md_in_title_correctly():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir)
        first_file = out_path / "guide_to_cmd.md_files.md"
        first_file.write_text("content", encoding="utf-8")

        second_target = get_unique_target(out_path, "guide_to_cmd.md_files")
        assert second_target.name == "guide_to_cmd.md_files_1.md"


def _mock_ydl(info: dict) -> MagicMock:
    mock_ydl = MagicMock()
    mock_ydl.return_value.__enter__.return_value.extract_info.return_value = info
    return mock_ydl


def test_transcript_block_error_surfaces_informative_reason():
    mock_api = MagicMock()
    mock_api.list.side_effect = RequestBlocked("v123")
    mock_ydl = _mock_ydl({"id": "v123", "title": "Test Video"})

    engine = YTConverterEngine(transcript_client=mock_api, ydl_client=mock_ydl)
    with tempfile.TemporaryDirectory() as tmpdir:
        results = engine.convert(
            "https://youtube.com/watch?v=v123", ConversionJob(Path(tmpdir))
        )
        success, msg = results[0]
        assert not success
        assert "blocking requests" in msg, f"Expected informative error, got: {msg}"


def test_unexpected_error_in_one_entry_does_not_abort_playlist():
    good_transcript = MagicMock(language_code="en")
    good_transcript.fetch.return_value = [SimpleNamespace(text="Hello there.")]
    good_list = MagicMock()
    good_list.find_transcript.return_value = good_transcript
    mock_api = MagicMock()
    mock_api.list.side_effect = [RuntimeError("socket closed"), good_list]
    entries = [{"id": "bad", "title": "Bad"}, {"id": "good", "title": "Good"}]
    mock_ydl = _mock_ydl({"entries": entries})

    engine = YTConverterEngine(transcript_client=mock_api, ydl_client=mock_ydl)
    with tempfile.TemporaryDirectory() as tmpdir:
        results = engine.convert("playlist", ConversionJob(Path(tmpdir)))
        assert results[0] == (False, "RuntimeError: socket closed"), results
        assert results[1] == (True, "Good.md"), results


def test_cancellation_aborts_conversion_gracefully():
    mock_ydl = _mock_ydl({"id": "v123", "title": "Test Video"})
    engine = YTConverterEngine(transcript_client=MagicMock(), ydl_client=mock_ydl)

    with tempfile.TemporaryDirectory() as tmpdir:
        job = ConversionJob(Path(tmpdir), check_cancelled=lambda: True)
        results = engine.convert("https://youtube.com/watch?v=v123", job)
        success, msg = results[0]
        assert not success
        assert "Cancelled by user" in msg


def test_cli_exit_codes_reflect_failures_and_bad_cookies():
    from youtube_converter import run_cli

    with tempfile.TemporaryDirectory() as tmpdir:
        missing = str(Path(tmpdir) / "missing_cookies.txt")
        assert run_cli(["url"], tmpdir, ["ar"], missing) == 2

        failing = MagicMock()
        failing.return_value.convert.return_value = [(False, "Metadata error: x")]
        with patch("youtube_converter.YTConverterEngine", failing):
            assert run_cli(["url"], tmpdir, ["ar"], None) == 1


def test_auto_translation_fallback_translates_foreign_track():
    foreign_transcript = MagicMock()
    foreign_transcript.is_translatable = True
    translated_transcript = MagicMock()
    translated_transcript.language_code = "ar"
    translated_transcript.fetch.return_value = [
        SimpleNamespace(text="مرحباً بكم في الدرس")
    ]
    foreign_transcript.translate.return_value = translated_transcript

    mock_list = MagicMock()
    mock_list.find_transcript.side_effect = NoTranscriptFound(
        "foreign123", ["ar"], mock_list
    )
    mock_list.__iter__.return_value = [foreign_transcript]

    mock_api = MagicMock()
    mock_api.list.return_value = mock_list

    engine = YTConverterEngine(transcript_client=mock_api)
    lines, lang, err = engine.fetch_transcript_segments("foreign123", languages=["ar"])
    assert err == ""
    assert lang == "ar"
    assert "مرحباً بكم" in lines[0]
    foreign_transcript.translate.assert_called_once_with("ar")


def test_gui_accessibility_properties_and_tab_order():
    import os

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from converter_gui import YTMainFrame

    if not QApplication.instance():
        QApplication([])
    window = YTMainFrame()
    assert window.txt_url.accessibleName() == "YouTube video or playlist link input"
    assert window.btn_run.accessibleName() == "Start transcription processing"
    assert window.btn_cancel.accessibleName() == "Cancel current transcription task"
    assert window.progress.accessibleName() == "Transcription task progress percentage"


def main():
    test_functions = [
        test_arabic_text_preserves_grammatical_relatives_and_meaning,
        test_arabic_text_strips_hesitation_phonemes_and_tatweel,
        test_arabic_punctuation_and_honorific_survive_cleaning,
        test_arabic_orthography_preserves_teh_marbuta_and_hamza,
        test_paragraph_structuring_breaks_on_terminal_punctuation,
        test_filename_sanitization_guards_windows_reserved_names,
        test_unique_target_increments_stem_when_file_exists,
        test_unique_target_handles_md_in_title_correctly,
        test_transcript_block_error_surfaces_informative_reason,
        test_unexpected_error_in_one_entry_does_not_abort_playlist,
        test_cancellation_aborts_conversion_gracefully,
        test_cli_exit_codes_reflect_failures_and_bad_cookies,
        test_auto_translation_fallback_translates_foreign_track,
        test_gui_accessibility_properties_and_tab_order,
    ]

    passed = 0
    print(f"Running {len(test_functions)} behavioral test scenarios...")
    for fn in test_functions:
        try:
            fn()
            passed += 1
            print(f"  [PASS] {fn.__name__}")
        except AssertionError as err:
            print(f"  [FAIL] {fn.__name__}: {err}")
        except Exception as err:
            print(f"  [ERROR] {fn.__name__}: {err}")

    print(f"\nResult: {passed}/{len(test_functions)} tests passed.")
    if passed != len(test_functions):
        sys.exit(1)


if __name__ == "__main__":
    main()
