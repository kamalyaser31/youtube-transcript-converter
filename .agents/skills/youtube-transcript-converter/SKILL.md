---
name: youtube-transcript-converter
description: Extracts and formats YouTube video transcripts or playlist captions into refined Markdown files with Arabic text normalization.
disable-model-invocation: true
---

# YouTube Transcript Converter

Automates the retrieval and linguistic refinement of YouTube transcripts (single videos or playlists) into structured Markdown documents.

## CLI Specification

The CLI runner is located at `youtube_converter.py` within the project root (`skills/youtube transcript/`).

| Flag | Argument | Description | Default |
|---|---|---|---|
| `-i`, `--input` | `<URL...>` | One or more video or playlist URLs | **Required** |
| `-o`, `--output` | `<DIR>` | Destination directory for `.md` files | `./md` |
| `-l`, `--langs` | `<LANG...>` | Language preference list in priority order | `ar en` |
| `-c`, `--cookies` | `<FILE>` | Path to Netscape `cookies.txt` for restricted videos | Optional |
| `--gui` | None | Launch PySide6 accessible graphical interface | False |

---

## Execution Workflow

### 1. Resolve Parameters
Determine the input parameters from user instructions:
- Target URL (video or playlist).
- Desired language (defaults to `ar`, with fallback to `en`).
- Output directory: Always specify `-o md` to store transcripts consistently under `md/`.
- Cookies file: Identify if the target video requires authentication or age verification.

### 2. Execute Extraction
Set terminal encoding and invoke `youtube_converter.py` from the project directory:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python youtube_converter.py -i "<URL>" -o md -l <lang>
```

> [!IMPORTANT]
> Always enclose URLs in double quotes to prevent shell misinterpretation of query parameters (`&`, `?`).

**Completion Criterion**: Process exits with code 0 and emits `[OK] <filename.md>` in stdout for each processed video.

Exit codes: `0` every video succeeded; `1` at least one video failed (read its `[FAIL]` line for the reason, then retry or report it); `2` the cookies file is missing or not a valid Netscape `cookies.txt`.

### 3. Verify Output
Inspect the generated file in `md/` using platform inspection tools (`list_dir` and `view_file`):
1. Confirm the file exists and is populated with non-trivial content (> 100 bytes).
2. Ensure the header contains the video title and source URL followed by the refined transcript paragraphs.

**Completion Criterion**: Target `.md` file confirmed present, non-empty, and structurally sound.

### 4. Present Result
Report a concise completion summary to the user with a clickable relative file link to each generated transcript:
- `[<Video Title>](file:///skills/youtube%20transcript/md/<filename>.md)`

---

## Failure Recovery

- **Captions Unavailable (`[FAIL] No transcript found`)**: If neither manual nor auto-generated captions exist in preferred languages, query available caption tracks or inform the user.
- **Bot Detection or Geo-Restriction**: Pass `-c cookies.txt` pointing to an exported Netscape cookies file.
- **Playlist Partial Failure**: The engine processes items sequentially; if a single video in a playlist fails, remaining items continue. Report successes and failures explicitly.
