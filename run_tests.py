"""
Manual and Unit Test runner for YouTube Transcriber.
"""

import sys
from text_processor import (
    TextRefinerFactory,
    ArabicTextRefiner,
    GenericTextRefiner,
)
from converter_engine import YTConverterEngine


def test_refiners():
    print("[*] Testing Text Refiners...")

    # 1. Arabic strategy
    ar_refiner = TextRefinerFactory.get_refiner("ar")
    assert isinstance(ar_refiner, ArabicTextRefiner)

    ar_text = "يعني البرمجة كويسة كده تمام"
    ar_cleaned = ar_refiner.clean_text(ar_text)
    # Fillers 'يعني', 'كده', 'تمام' should be removed
    assert "البرمجة" in ar_cleaned or "البرمجه" in ar_cleaned
    assert "كويسة" in ar_cleaned or "كويسه" in ar_cleaned
    assert "يعني" not in ar_cleaned

    # 2. Generic strategy
    en_refiner = TextRefinerFactory.get_refiner("en")
    assert isinstance(en_refiner, GenericTextRefiner)

    en_text = "<b>Hello</b> world!!! This is is cool."
    en_cleaned = en_refiner.clean_text(en_text)
    assert "Hello world" in en_cleaned
    assert "<b>" not in en_cleaned

    print("[✔] Text Refiners verified.")


class MockYoutubeDL:
    """Mock client for yt_dlp."""

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def extract_info(self, url, download=False):
        return {"id": "mock_id_123", "title": "Mock Video Title"}


class MockTranscript:
    def __init__(self):
        self.language_code = "en"

    def fetch(self):
        return [{"text": "Hello"}, {"text": "World"}]


class MockTranscriptList:
    def __init__(self, video_id):
        self.video_id = video_id

    def find_transcript(self, languages):
        return MockTranscript()


class MockTranscriptApi:
    """Mock client for youtube_transcript_api."""

    @staticmethod
    def list(video_id, cookies=None):
        return MockTranscriptList(video_id)


def test_engine_di():
    print("[*] Testing YTConverterEngine with Dependency Injection...")

    # Inject Mock clients into YTConverterEngine
    engine = YTConverterEngine(
        youtube_dl_client=MockYoutubeDL,
        transcript_api_client=MockTranscriptApi,
    )

    success, info = engine.get_video_info(
        "https://www.youtube.com/watch?v=mock"
    )
    assert success is True
    assert info["id"] == "mock_id_123"

    lines, lang = engine.fetch_transcript_segments("mock_id_123")
    assert lang == "en"
    assert lines == ["Hello", "World"]

    print("[✔] Dependency Injection and mock engine execution verified.")


if __name__ == "__main__":
    try:
        test_refiners()
        test_engine_di()
        print("\n[✔] All tests passed successfully!")
    except AssertionError as e:
        print(f"\n[✘] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[✘] Unexpected error during tests: {e}")
        sys.exit(1)
