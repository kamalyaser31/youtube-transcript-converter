# حالة المشروع (YouTube Transcriber Pro)

- **الوحدات:** `converter_engine.py` (جلب البيانات والتفريغ والكتابة)، `text_processor.py` (تنظيف النص وتقسيم الفقرات)، `youtube_converter.py` (CLI ومدخل الواجهة)، `converter_gui.py` (PySide6 + `QThread`)، `run_tests.py` (14 اختباراً).
- **واجهة المحرك:** `YTConverterEngine(transcript_client=None, ydl_client=None, cookies_path=None).convert(url, ConversionJob(out_dir, languages, on_status, check_cancelled))` تعيد `[(ok, msg)]`.
- **الكوكيز:** `youtube-transcript-api>=1.2` لا يقبل وسيط `cookies`؛ فتُحمَّل بـ `MozillaCookieJar` على `requests.Session` تُمرَّر `http_client`.
- **الأخطاء:** يُلتقط `CouldNotRetrieveTranscript` و`DownloadError` تحديداً؛ و`_process_entry` حدُّ الدفعة: يسجل فشل المقطع ويمضي إلى ما بعده.
- **رموز خروج CLI:** 0 نجاح الكل، 1 فشل مقطع فأكثر، 2 ملف كوكيز مفقود أو تالف.
- **`.gitignore`:** يتجاهل المخرجات في `md/` و`cookies.txt` والمخابئ؛ أما ملفات الجذر (`README.md` و`CHANGELOG.md` و`project_state.md`) فمتتبَّعة.
