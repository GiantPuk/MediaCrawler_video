# MediaCrawler Video

A video search, download, and multimodal understanding workbench based on [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler).

This fork is no longer just a generic crawler UI. Its main purpose is to provide an end-to-end video workflow:

1. Search real video candidates through existing platform crawlers or public platform endpoints.
2. Return metadata first, then let the user choose which videos to process.
3. Download selected videos, optionally transfer them to OSS, and summarize them with Qwen/DashScope models.
4. Generate per-video timeline summaries, aggregate summaries, Markdown reports, and Mermaid mindmaps.
5. Expose the same backend capabilities through both WebUI and CLI.

This project inherits MediaCrawler's non-commercial learning and research purpose. Do not use it for commercial operations, large-scale crawling, platform bypassing, privacy-invasive collection, or illegal activity.

## Key Capabilities

- Video workbench: search by title/keyword, creator, or platform rankings.
- Creator disambiguation: Bilibili supports username candidate search with UID, avatar, follower count, and video count. Other platforms are most reliable with profile URLs or creator IDs.
- Candidate-first workflow: metadata-only by default; selected videos are downloaded or analyzed only after explicit selection.
- Structured progress: task stages, per-step elapsed time, download/upload progress, speed, and failure reasons.
- Multimodal analysis: Qwen/DashScope compatible API profiles. Default model is `qwen3.5-omni-plus`; Whisper is disabled by default.
- Text fusion: optional Whisper transcription can be injected into the video-analysis prompt.
- OSS transfer: local videos or source video streams can be uploaded to Alibaba Cloud OSS and passed to Qwen as signed URLs. Temporary OSS objects are deleted after analysis by default.
- Markdown rendering: WebUI supports Markdown, tables, and Mermaid mindmaps.
- Data browser: separates search records, ranking records, creator records, content records, comment records, and video-analysis results.
- CLI: `tools/video_summary_cli.py` covers creator resolution, task start/poll/stop, platform credential profiles, and Qwen/OSS profiles.
- Original crawler compatibility: `main.py` and MediaCrawler's search/detail/creator flows are still available.

## Project Layout

```text
api/
  routers/video_summary.py        # Video workbench API
  schemas/video_summary.py        # Video task/config/progress schemas
  services/video_summary_manager.py
webui/src/components/video/
  VideoWorkspace.tsx              # Current video workbench UI
tools/
  video_summary_cli.py            # CLI for the video workbench
  test_qwen_oss_video.py          # OSS + Qwen video URL test helper
media_platform/                  # Upstream platform crawlers plus fork-specific adaptations
store/                           # Platform store/write logic
data/                            # Local task data, ignored by Git
browser_data/                    # Persistent browser profiles from QR-code login, ignored by Git
```

## Quick Start

### Requirements

- Python 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js 16+
- Chrome or Playwright browsers
- Optional: ffmpeg for Whisper audio extraction
- Optional: CUDA-enabled PyTorch for local Whisper GPU transcription

### Install

```shell
cd MediaCrawler_video
uv sync

cd webui
npm install
```

Install Playwright browsers when using standard Playwright mode:

```shell
uv run playwright install
```

### Start WebUI

Run backend and frontend in two terminals:

```shell
# Terminal 1: backend API on 8080
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080

# Terminal 2: Vite frontend on 5173
cd webui
npm run dev
```

Open:

```text
http://localhost:5173/
```

You can also build the frontend and serve it from the backend:

```shell
cd webui
npm run build

cd ..
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080
```

Then open:

```text
http://localhost:8080/
```

Avoid `--reload` for long video tasks, because reload restarts the backend process and loses in-memory live task state.

## Login and Credentials

Platform credentials are managed in WebUI under `Settings > Platform Login`.

Two methods are supported:

- Cookie profiles: paste a DevTools cookie table, JSON cookie export, or Cookie header.
- QR-code login: reuse the original MediaCrawler login flow, then save captured cookies and `browser_data/<platform>_user_data_dir` metadata.

Cookie profiles and QR-code login both eventually provide cookies for authenticated platform requests. If a platform has a valid cookie profile, tasks can use `login_type=cookie`.

Sensitive local state is stored in:

```text
data/video_tasks/platform_credentials.json
data/video_tasks/qwen_settings.json
browser_data/
```

These paths are ignored by Git and should never be committed.

## WebUI Workflow

### Video Search

1. Open the `Search` view.
2. Select a platform.
3. Choose `Title/Keyword` or `Creator`.
4. Start discovery.
5. Review real candidate metadata such as title, author, publish time, views, likes, comments, duration, and cover image.
6. Select videos and start download or download + analysis.

### Creator Tasks

Bilibili supports username-based creator search. When names conflict, the UI shows candidate creator cards first; a concrete UID must be selected before loading videos.

Other platforms are currently more reliable with profile URLs or platform creator IDs. Unsupported creator search paths are reported explicitly instead of being faked.

### Ranking Tasks

The `Rankings` view returns either:

- video candidates that can be selected for download/analysis, or
- topic/search/question cards that can only be used as search keywords.

Topic cards are not presented as downloadable videos.

### Settings

The settings page contains:

- Platform credentials: multiple cookie/QR-code profiles.
- Video analysis API: Qwen/DashScope API key, model name, Base URL, and OSS settings.
- Base parameters: crawl intervals, max videos, concurrency, upload backend, frame count, and Whisper settings.

## Video Analysis Pipeline

The default upload backend is `auto`. The real execution order is:

1. Try passing a source video URL directly to Qwen when it is publicly reachable.
2. If the source URL requires platform headers and OSS is enabled, stream the source video to OSS with multipart upload, then pass the signed OSS URL to Qwen.
3. If source URL paths fail, download the video locally.
4. After local download, try OSS URL, DashScope local video upload, OpenAI-compatible base64 video, or frame fallback according to the configured model and limits.
5. If Whisper is enabled, extract audio with ffmpeg and transcribe it using PyTorch-based openai-whisper; the transcript is fused into the model prompt.
6. If `oss_cleanup_after_analysis` is enabled, delete temporary OSS objects after analysis.

The project does not fake downloads, rankings, or model output. Unsupported or missing capabilities are reported as `unsupported`, `missing`, or `failed`.

## Platform Status

| Platform | Title/Keyword Search | Creator Candidate Search | Creator Videos | Rankings | Download | Summary |
| --- | --- | --- | --- | --- | --- | --- |
| Bilibili | Implemented and tested | Username candidates with UID/avatar/follower/video count | Implemented and tested | `popular`, `ranking`, `ranking_<region>`, `precious`, `weekly`, `hot_search`; `weekly` usually requires cookies | Implemented and tested | Implemented and tested |
| Xiaohongshu | Tested with valid cookies for `type=video` candidates | Reliable path is profile URL or creator ID | Depends on valid cookies and upstream behavior | No real ranking endpoint wired | Candidates may not include direct URLs; detail/native path is required | Works after local video is available |
| Douyin | Tested with valid cookies/CDP or standard mode, can return video candidates and playback URLs | Reliable path is profile URL or `sec_user_id` | Depends on valid cookies | `hot_search`, `trending` return hot topics/search terms for further video search | Works when real video URL is available | Works after local video is available |
| Kuaishou | Tested with valid cookies via upstream signed search API | Reliable path is profile URL or creator ID | Depends on valid cookies; signed REST profile feed is wired | `hot` returns brilliant video-ranking `photoId` candidates | Works when real video URL is available; `photoId`-only items are marked unsupported | Works after local video is available |
| Weibo | Upstream video search path is retained; depends on valid cookies | Reliable path is profile URL or UID | Depends on valid cookies and upstream behavior | `hot_search`, `hot_gov` return hot terms/topics for further video search | Works when real video URL is available | Works after local video is available |
| Zhihu | `zvideo` search tested with valid cookies; date range matters | Reliable path is profile URL or creator ID | Zvideo feed is wired, depends on valid cookies | `total`, `zvideo` hot lists; often returns question cards | Stable direct video download not verified | Works after local video is available |
| Tieba | No real video search/download flow | Not applicable | Not applicable | `hot_topic` returns hot topics only | Not wired | Not wired |

## CLI Usage

The CLI calls the local backend API, so start the backend first.

Help:

```shell
uv run python tools/video_summary_cli.py --help
uv run python tools/video_summary_cli.py tasks start --help
```

Resolve creator candidates:

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

Metadata-only task by creator UID:

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode creator ^
  --creator-id 11332884 ^
  --creator-name Key725 ^
  --start-date 2026-08-07 ^
  --end-date 2026-08-07 ^
  --workflow-mode metadata_only ^
  --max-videos 2 ^
  --credential-profile-id <bili_profile_id> ^
  --login-type cookie ^
  --headless ^
  --crawl-min-sleep-seconds 5 ^
  --crawl-max-sleep-seconds 10
```

Download and summarize selected videos from a metadata task:

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode creator ^
  --workflow-mode selected_items ^
  --source-task-id <metadata_task_id> ^
  --selected-item-id <video_id_or_bvid> ^
  --credential-profile-id <bili_profile_id> ^
  --login-type cookie ^
  --headless ^
  --summarize
```

Search and rankings:

```shell
uv run python tools/video_summary_cli.py tasks ranking-options
uv run python tools/video_summary_cli.py tasks ranking-options --platform bili

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode search --query "Shanghai Jiao Tong University CS Summer Camp" --workflow-mode metadata_only --credential-profile-id <bili_profile_id> --headless --crawl-min-sleep-seconds 5 --crawl-max-sleep-seconds 10

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type popular --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform dy --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <dy_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform ks --source-mode ranking --ranking-type hot --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <ks_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform wb --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <wb_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform zhihu --source-mode ranking --ranking-type total --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <zhihu_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform tieba --source-mode ranking --ranking-type hot_topic --ranking-limit 5 --workflow-mode metadata_only
```

Inspect, wait, stop:

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
uv run python tools/video_summary_cli.py tasks stop <task_id>
```

Platform cookie profiles:

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
uv run python tools/video_summary_cli.py credentials show <credential_profile_id>
uv run python tools/video_summary_cli.py credentials update <credential_profile_id> --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials delete <credential_profile_id>
```

QR-code login:

```shell
uv run python tools/video_summary_cli.py credentials qrcode-login --platform bili --name "bili-qrcode"
uv run python tools/video_summary_cli.py credentials qrcode-status <login_task_id>
uv run python tools/video_summary_cli.py credentials qrcode-wait <login_task_id>
```

Qwen/DashScope and OSS:

```shell
uv run python tools/video_summary_cli.py qwen list
uv run python tools/video_summary_cli.py qwen create --name "dashscope-main" --api-key-file .\qwen.key.txt --model qwen3.5-omni-plus
uv run python tools/video_summary_cli.py qwen activate <qwen_profile_id>
uv run python tools/video_summary_cli.py qwen show <qwen_profile_id>

uv run python tools/video_summary_cli.py qwen update <qwen_profile_id> ^
  --name "dashscope-main" ^
  --api-key-file .\qwen.key.txt ^
  --model qwen3.5-omni-plus ^
  --oss-enabled ^
  --oss-access-key-id-file .\oss-ak-id.txt ^
  --oss-access-key-secret-file .\oss-ak-secret.txt ^
  --oss-bucket <bucket_name> ^
  --oss-endpoint oss-cn-beijing.aliyuncs.com ^
  --oss-region cn-beijing ^
  --oss-prefix mediacrawler/video-summary ^
  --oss-url-expires-seconds 7200
```

Test OSS + Qwen video URL:

```shell
uv run python tools/test_qwen_oss_video.py --video path\to\video.mp4 --model qwen-vl-max --model qwen3.5-omni-plus
uv run python tools/test_qwen_oss_video.py
```

## Original MediaCrawler Entry

The upstream crawler entry remains available:

```shell
uv run main.py --platform xhs --lt qrcode --type search
uv run main.py --platform xhs --lt qrcode --type detail
uv run main.py --help
```

Base configuration is still in:

```text
config/base_config.py
```

The video workbench reuses upstream crawler, client, store, and login modules whenever possible.

## Data Storage

The original crawler still supports JSON, JSONL, CSV, Excel, SQLite, MySQL, and MongoDB storage. See:

```text
docs/data_storage_guide.md
```

Video task output:

```text
data/video_tasks/<task_id>/
  raw/                 # Platform metadata and downloaded files
  transcripts/         # Whisper transcripts
  result.json          # Task result, per-video summaries, aggregate summary
```

The WebUI data browser hides sensitive settings files and categorizes search, ranking, comment, content, creator, and video-analysis results.

## Risk and Performance Notes

- Keep concurrency at `1` by default.
- Use randomized min/max intervals and long pauses every N items.
- Run metadata-only first, then select videos for download/analysis.
- For sensitive accounts, reusing a real Chrome/CDP login state can be safer than pure headless mode.
- Avoid large comment crawls.
- Keep OSS temporary-object cleanup enabled for one-off video analysis.

## FAQ

### Why does aggregate summary sometimes use fallback?

When the aggregate model call fails, the API key is missing, or the model returns no usable text, the backend creates a local fallback summary from completed per-video summaries. The fallback keeps common themes, per-video synopsis, aggregate summary, and Mermaid mindmap sections.

### Why are some ranking items not downloadable?

Some platforms return hot search terms, topics, questions, or `photoId` cards instead of public video URLs. These items can be used for further video search but are not marked as downloadable videos.

### Why can direct Qwen source URL input fail?

Many platform video URLs require Cookie, Referer, User-Agent, or temporary signatures. Qwen servers cannot access them directly. Enable OSS transfer or use local download/upload paths.

### Where do Whisper timestamps come from?

openai-whisper returns segmented timestamps. This project extracts audio with ffmpeg and runs PyTorch-based openai-whisper. CUDA and fp16 are used when available.

## Development Checks

```shell
uv run python -m py_compile api\services\video_summary_manager.py api\routers\data.py api\schemas\crawler.py api\schemas\video_summary.py

cd webui
npm run build
```

## License and Disclaimer

This project is based on [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) and inherits its non-commercial learning/research purpose. Read and follow `LICENSE`.

This repository is for learning, research, and technical validation only. Users are responsible for platform terms, account risks, legal compliance, data compliance, and any cost incurred by OSS/API usage. Do not use this project for commercial crawling, bulk collection, bypassing platform controls, privacy-invasive collection, copyright infringement, or any illegal activity.
