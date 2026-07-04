---
name: youtube-transcript-converter
description: Extracts and formats YouTube video transcripts or playlist captions into refined Markdown files on Windows, applying Arabic normalization. Trigger when the user asks to "تفريغ يوتيوب", "تحويل مقطع يوتيوب لنص", "تنزيل ترجمة يوتيوب", "transcribe YouTube video", or "convert YouTube video to markdown".
---

# YouTube Transcript Converter Skill

This skill governs the automated transcription of YouTube videos and playlists into structured Markdown files, applying Arabic text processing using local python utilities.

## 1. Input Parameters & Validation

Before launching execution, the agent MUST resolve and validate these inputs:
1. **URL**: A valid link to a YouTube video or playlist.
2. **Language** (`lang`): Target language code (default is `ar`).
3. **Cookies** (`cookies`): (Optional) Path to a `cookies.txt` file if the video is restricted.

If the URL is missing, halt execution and request it from the user.

## 2. Codebase Structure & Logic

The project consists of three core Python scripts, each with distinct responsibilities:

### 1. Main Entry Point (`youtube_converter.py`)
Handles execution modes:
- **GUI Mode**: Triggered when the script is run without arguments. Launches a `wxPython` native window (`YTMainFrame`).
- **CLI Mode**: Triggered when arguments are provided.
  - `-i`/`--input` (list of URLs to process) [Required]
  - `-o`/`--output` (custom directory path; defaults to current working directory) [Optional]
  - `-l`/`--langs` (list of language codes in order of preference; defaults to `["ar", "en"]`) [Optional]
  - `-c`/`--cookies` (path to `cookies.txt`) [Optional]

### 2. Transcription Engine (`converter_engine.py`)
Orchestrates metadata fetching and transcript downloads:
- **Metadata**: Uses `yt_dlp.YoutubeDL` to extract video info or playlist entries.
- **Transcript Retrieval**: Uses `YouTubeTranscriptApi` to fetch captions.
  - **Fallback Strategy**: Searches for manual transcripts matching preferred languages first. If not found, searches for generated transcripts. If those fail, retrieves the first available caption.
- **Title Sanitization**: Replaces forbidden OS characters: `re.sub(r'[\\/*?:"<>|]', "", title).replace(" ", "_")` and limits the filename to 100 characters.
- **Name Collision**: Appends `_1.md`, `_2.md` etc., if the output file already exists.

### 3. Text Processing (`text_processor.py`)
Refines raw transcript chunks into readable prose:
- **Generic Refiner**: Standard HTML tag stripping and noise cleanup for English/German.
- **Arabic Text Refiner**:
  - Uses `pyarabic` library if available to strip `tashkeel` (diacritics), `tatweel` (stretched letters), and normalize hamzas, alefs, and teh marbuta.
  - Removes common spoken fillers: (يعني, ااا, طيب, كده, ايه, فعليا, بشكل كبير, تمام, اللي, عارفين, بقى).
  - Cleans repetitive words (3 or more adjacent repetitions are reduced to a single word; 2 repetitions are kept to preserve emphasis like "لا لا").
- **Paragraphing**: Groups cleaned transcript snippets into paragraphs of approximately ~400 characters (separated by double newlines).

---

## 3. Sequential Execution Steps

### Step 1: Environment Readiness Check
Verify that dependencies are met in the local Python environment. Run:
```powershell
python -c "import yt_dlp, youtube_transcript_api, pyarabic"
```
If an import error occurs, warn the user and propose running `pip install -r requirements.txt` before proceeding.

### Step 2: Command Invocation
Execute the transcriber via command line using the Python wrapper. Run:
```powershell
python youtube_converter.py -i "<URL>" -l <lang>
```
*Note: Make sure to wrap the URL in double quotes to prevent shell parsing errors for characters like `&` and `?` in YouTube links.*

**Completion Criterion**: The console output must show successful extraction and end with `0` exit code.

### Step 3: Output Verification
1. List the files in the `md/` directory:
```powershell
Get-ChildItem md/
```
2. Locate the newly generated Markdown file (named after the video title).
3. Confirm that the file is not empty and contains the formatted transcript.

**Completion Criterion**: A verified, non-empty Markdown file exists in `md/`.

### Step 4: Handover to User
Provide the user with a summary of the transcription and a clickable file link to the generated Markdown file:
`[عنوان المقطع](file:///E:/GitHub/my%20workflows/youtube%20transcript/md/[اسم_الملف].md)`

---

## 4. Reference & Troubleshooting

### Windows Console Encoding
When running commands on Windows, keep in mind that console logs may contain non-UTF-8 characters. The python script handles this internally, but the agent must execute commands in the project directory: `E:\GitHub\my workflows\youtube transcript`.

### Subprocess Failures
If the command fails with download errors:
- Ensure `yt-dlp` is updated.
- Verify internet connectivity.
- Check if the video contains captions (manual or auto-generated).
