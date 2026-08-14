# MediaCrawler Video Workbench

<div align="center">

A video search, download, and multimodal understanding workbench based on [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler).

[中文](README.md) · [Upstream](https://github.com/NanmiCoder/MediaCrawler) · [Data Storage Guide](docs/data_storage_guide.md) · [CDP Guide](docs/CDP模式使用指南.md)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Node.js](https://img.shields.io/badge/Node.js-16%2B-green)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Vite](https://img.shields.io/badge/WebUI-Vite-646CFF)
![License](https://img.shields.io/badge/License-Non--commercial-orange)

</div>

> [!WARNING]
> This project is limited to personal learning, research, and technical validation. Follow platform rules, applicable law, and data-compliance requirements. Do not use it for commercial collection, bulk crawling, platform restriction bypassing, or infringement.

## Overview

MediaCrawler Video Workbench extends [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) for video-oriented tasks. Upstream command-line entry points, platform crawlers, login methods, and data storage remain available; this repository adds WebUI, API, and CLI support for video discovery, candidate filtering, download, and summarization.

Main capabilities:

- Discover candidate videos by keyword, creator, or platform ranking.
- Return metadata first, then let the user select videos for download or analysis.
- Download selected videos with resume support, temporary OSS transfer, Qwen/DashScope/Ollama analysis, and optional Whisper transcription.
- Produce per-video timeline summaries, aggregate reports, Markdown output, and Mermaid mindmaps.
- Share the same backend API and task state across WebUI and CLI.

Task status keeps candidate, download, upload, transcription, and model-analysis stage details so issues can be inspected from either WebUI or CLI.

## Table of Contents

- [Overview](#overview)
- [Relationship With MediaCrawler](#relationship-with-mediacrawler)
- [Core Capabilities](#core-capabilities)
- [Common Platform Entrypoints](#common-platform-entrypoints)
- [Quick Start](#quick-start)
- [WebUI Workflow](#webui-workflow)
- [Configuration](#configuration)
- [CLI Usage](#cli-usage)
- [Data and Results](#data-and-results)
- [Video Understanding Pipeline](#video-understanding-pipeline)
- [Risk and Performance Notes](#risk-and-performance-notes)
- [User Guide](#user-guide)
- [Technical Report](#technical-report)
- [FAQ](#faq)
- [Development Checks](#development-checks)
- [License and Disclaimer](#license-and-disclaimer)

## Relationship With MediaCrawler

This fork keeps and reuses the upstream crawler foundation:

- `main.py`, `media_platform/`, `store/`, `config/base_config.py`, and upstream-style entry points remain available.
- Platform login, cookies, CDP, Playwright, and browser context handling are kept close to upstream behavior.
- The video workbench adds API routes, WebUI, task state, OSS/Qwen integration, download progress, and result rendering around that foundation.

Crawler-side behavior prefers upstream MediaCrawler implementations. Direct APIs, field normalization, progress tracking, and task orchestration are added only where the video workflow requires them.

## Core Capabilities

| Capability | Current implementation |
| --- | --- |
| Video discovery | Search by keyword, creator, or platform ranking. Metadata-only is the default, so videos are not downloaded automatically. |
| Creator disambiguation | Bilibili supports username candidate search with UID, avatar, follower count, and video count. Other platforms are most reliable with profile URLs or creator IDs. |
| Candidate selection | Search returns candidates first. The user selects videos before download or analysis. |
| Download progress | Tracks current video, downloaded bytes, total bytes, speed, percent, step duration, and failure reason. |
| Resumable tasks | Task state is persisted to `task_state.json`; failed, stopped, or interrupted tasks can be resumed. |
| Expired link handling | Bilibili download failures trigger a real playurl refresh before retrying. |
| Multimodal analysis | Qwen/DashScope compatible API support plus Ollama local vision models. The cloud default model is `qwen3.5-omni-plus`; Whisper is disabled by default. |
| Whisper fusion | Optional openai-whisper through PyTorch. When enabled, every selected video is saved locally and transcribed before model analysis; transcript text is injected into the video-analysis prompt. |
| OSS transfer | Source streams or local videos can be uploaded to Alibaba Cloud OSS with multipart upload, then passed to models as signed URLs. Source-stream OSS preparation can run in parallel with local download. Temporary objects are removed after analysis by default. |
| Markdown output | WebUI renders Markdown, tables, and Mermaid mindmaps. |
| Data browser | Separates search records, ranking records, creator records, content records, comments, and video-analysis results. |
| CLI | `tools/video_summary_cli.py` covers creator resolution, task start/poll/stop/resume, platform credentials, and Qwen/OSS profiles. |

## Common Platform Entrypoints

| Platform | Recommended Input | Common Entrypoints | Download and Summary |
| --- | --- | --- | --- |
| Bilibili | Keyword, creator name, UID, space URL | Keyword search, creator candidates, creator videos, popular/region/weekly rankings | Supports playurl parsing, link refresh, download, and summary. |
| Xiaohongshu | Keyword, creator profile URL, creator ID | Keyword search, creator videos | Can enter the summary pipeline after a video file is available. |
| Douyin | Keyword, profile URL, `sec_user_id` | Keyword search, creator videos, hot-term follow-up search | Can download and summarize when a real video URL is available. |
| Kuaishou | Keyword, profile URL, creator ID | Keyword search, creator videos, hot-ranking candidates | Can download and summarize when a real video URL is available. |
| Weibo | Keyword, profile URL, UID | Video search, creator videos, hot-term follow-up search | Can download and summarize when a real video URL is available. |

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

Avoid `--reload` for long video tasks. Task state is persisted to `data/video_tasks/<task_id>/task_state.json`, so failed or interrupted tasks can be resumed, but reload still interrupts an active download, transcription, upload, or model request.

### Upstream MediaCrawler Entry Points

The original crawler entry points are still available:

```shell
uv run main.py --platform xhs --lt qrcode --type search
uv run main.py --platform xhs --lt qrcode --type detail
uv run main.py --help
```

Base configuration remains in:

```text
config/base_config.py
```

## WebUI Workflow

### Video Search

1. Open the `Search` view.
2. Select a platform.
3. Choose `Title/Keyword` or `Creator`.
4. Start discovery and review candidate metadata first.
5. Check title, author, publish time, views, likes, comments, duration, file size, and cover image when available.
6. Select videos and start download or download plus analysis.

### Creator Tasks

Bilibili supports username-based creator search. When names conflict, the UI shows candidate creator cards first; a concrete UID must be selected before loading videos.

Other platforms are currently more reliable with profile URLs or platform creator IDs.

### Ranking Tasks

Use the `Rankings` view to select a platform and ranking type. The ranking list itself is returned by the platform in real time; date range filters apply mainly to follow-up video search results.

### Task Resume

When a task fails, is manually stopped, or is interrupted by backend restart, the UI shows a resume action when saved state is available. Resume reuses downloaded files, completed summaries, and saved candidates.

### Settings

The top-right settings page contains:

- Platform credentials: multiple cookie or QR-code profiles, plus login health checks.
- Video analysis API: Qwen/DashScope API key, model name, Base URL, and OSS settings.
- Base parameters: crawl intervals, max videos, concurrency, upload backend, frame count, and Whisper settings.

## Configuration

### Platform Credentials

Two methods are supported:

- Cookie profiles: paste a DevTools cookie table, JSON cookie export, or Cookie header.
- QR-code login: reuse the original MediaCrawler login flow, then save captured cookies and `browser_data/<platform>_user_data_dir` metadata.

Cookie profiles and QR-code login both eventually provide cookies for authenticated platform requests. If a platform has a valid cookie profile, tasks can use `login_type=cookie`.

The settings page includes a login health check:

- Bilibili calls the real `https://api.bilibili.com/x/web-interface/nav` endpoint and checks `isLogin`.
- Other platforms check key cookie fields and show health status plus hints in the settings page.

Sensitive local state is stored in:

```text
data/video_tasks/platform_credentials.json
data/video_tasks/qwen_settings.json
browser_data/
```

These paths are ignored by Git and should never be committed.

### Video Analysis API

Common settings:

| Setting | Meaning |
| --- | --- |
| API Provider | DashScope, OpenAI-compatible, and local Ollama providers are supported. |
| API Key | Qwen/DashScope or compatible API key. |
| Base URL | Compatible endpoint. DashScope compatible mode defaults to `https://dashscope.aliyuncs.com/compatible-mode/v1`. |
| Model | Model name. The UI provides common Qwen choices and also allows manual input. |
| Video Input Mode | Auto, video-first, frames, or text-first. Auto is recommended. |
| Whisper | Optional audio transcription. When enabled, every selected video is saved locally and transcribed; transcript text is fused into the video prompt. |

Ollama local mode uses `http://127.0.0.1:11434` and does not require an API key. The current integration uses Ollama's image-input capability: the backend samples video frames with ffmpeg, then sends those frame images plus text context to the local VL model. It does not pass `.mp4` files to Ollama as native video objects.

### OSS

When OSS is enabled, the backend can temporarily upload a source stream or local video to OSS and pass the signed URL to the model. Selected analysis videos are still retained locally; when possible, source-stream OSS preparation runs alongside local download and Whisper. Keep cleanup enabled to avoid filling the bucket with one-time videos.

### Crawl Pace

Recommended conservative defaults:

- Max concurrency: `1`
- Min/max sleep interval: randomized range
- Long pause every N items: enabled
- Comment crawling: disabled by default

## CLI Usage

The CLI calls the local backend API, so start the backend first.

### Help

```shell
uv run python tools/video_summary_cli.py --help
uv run python tools/video_summary_cli.py tasks start --help
```

### Creator Resolution

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

### Metadata-Only Task by Creator UID

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode creator ^
  --creator-id 11332884 ^
  --creator-name Key725 ^
  --start-date 2026-08-07 ^
  --end-date 2026-08-07 ^
  --workflow-mode metadata_only ^
  --max-crawl-items 100 ^
  --max-videos 2 ^
  --credential-profile-id <bili_profile_id> ^
  --login-type cookie ^
  --headless ^
  --crawl-min-sleep-seconds 5 ^
  --crawl-max-sleep-seconds 10
```

`--max-crawl-items` is the raw platform crawl cap. `--max-videos` is the final candidate count after date/type filtering. Search/creator metadata tasks count filtered candidates while crawling and stop early once `--max-videos` is reached; if not enough candidates match, they crawl up to `--max-crawl-items`.

### Download and Summarize Selected Videos

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

### Search and Rankings

```shell
uv run python tools/video_summary_cli.py tasks ranking-options
uv run python tools/video_summary_cli.py tasks ranking-options --platform bili

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode search --query "Shanghai Jiao Tong University CS summer camp" --workflow-mode metadata_only --credential-profile-id <bili_profile_id> --headless --crawl-min-sleep-seconds 5 --crawl-max-sleep-seconds 10

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type popular --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type ranking_game --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform dy --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <dy_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform ks --source-mode ranking --ranking-type hot --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <ks_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform wb --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <wb_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform zhihu --source-mode ranking --ranking-type total --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <zhihu_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform tieba --source-mode ranking --ranking-type hot_topic --ranking-limit 5 --workflow-mode metadata_only
```

### Status, Wait, Stop, Resume

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
uv run python tools/video_summary_cli.py tasks stop <task_id>
uv run python tools/video_summary_cli.py tasks resume <task_id>
```

### Platform Cookie Profiles

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
uv run python tools/video_summary_cli.py credentials show <credential_profile_id>
uv run python tools/video_summary_cli.py credentials health <credential_profile_id>
uv run python tools/video_summary_cli.py credentials update <credential_profile_id> --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials delete <credential_profile_id>
```

### QR-Code Login

```shell
uv run python tools/video_summary_cli.py credentials qrcode-login --platform bili --name "bili-qrcode"
uv run python tools/video_summary_cli.py credentials qrcode-status <login_task_id>
uv run python tools/video_summary_cli.py credentials qrcode-wait <login_task_id>
```

### Qwen/DashScope and OSS

```shell
uv run python tools/video_summary_cli.py qwen list
uv run python tools/video_summary_cli.py qwen create --name "dashscope-main" --api-key-file .\qwen.key.txt --model qwen3.5-omni-plus
uv run python tools/video_summary_cli.py qwen activate <qwen_profile_id>
uv run python tools/video_summary_cli.py qwen show <qwen_profile_id>

uv run python tools/video_summary_cli.py qwen create --name "ollama-local" --api-provider ollama --base-url http://127.0.0.1:11434 --model qwen2.5vl:3b

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

### OSS + Qwen Video URL Test

```shell
uv run python tools/test_qwen_oss_video.py --video path\to\video.mp4 --model qwen-vl-max --model qwen3.5-omni-plus
uv run python tools/test_qwen_oss_video.py
```

## Data and Results

The original crawler still supports JSON, JSONL, CSV, Excel, SQLite, MySQL, MongoDB, and other storage options. See:

```text
docs/data_storage_guide.md
```

Video task data is stored in:

```text
data/video_tasks/<task_id>/
  raw/                 # Raw platform metadata and downloaded files
  transcripts/         # Whisper transcripts
  task_state.json      # Resumable task state, subtask progress, candidate state
  result.json          # Task result, per-video summaries, aggregate summary
```

The WebUI data browser hides sensitive configuration files and separates search, ranking, comment, content, creator, and video-analysis records.

## Video Understanding Pipeline

The default upload backend is `auto`. The real execution order is:

1. After a video is selected for download and analysis, the backend always saves that video locally. A successful source URL or OSS model input no longer skips local files.
2. If Whisper is enabled, every selected video extracts audio with ffmpeg and transcribes it using PyTorch-based openai-whisper. If no usable transcript is generated, that item is marked failed.
3. If OSS is enabled and the model supports video URLs, source-stream OSS preparation can run while local download and Whisper are in progress.
4. Model input first tries a public source URL. If that fails, it tries the prepared source-stream OSS signed URL, then local-video OSS upload, DashScope local video upload, OpenAI-compatible base64 video, or sampled-frame analysis according to the configured model and limits.
5. If API Provider is Ollama, local models skip video URL/file upload and use sampled-frame image analysis plus text context.
6. If `oss_cleanup_after_analysis` is enabled, temporary OSS objects are deleted after analysis; local videos and result files remain.

## Risk and Performance Notes

- Keep max concurrency at `1` by default. Increase it only when you want multiple selected videos to process concurrently across download, transcription, OSS, and model analysis.
- Use randomized min/max sleep intervals and long pauses every N items.
- Run metadata-only first, then select videos for download or analysis.
- For sensitive platforms, prefer real Chrome/CDP login state when possible.
- Avoid large-scale comment crawling.
- Use OSS as temporary transfer storage and keep cleanup enabled.

## User Guide

For first-time setup, search, download, summary, and CLI usage, read:

```text
使用文档.md
```

## Technical Report

Implementation details, platform coverage, test statistics, and performance estimates are documented in:

```text
技术报告.md
```

## FAQ

### Why does the aggregate summary sometimes use local aggregation?

If the aggregate model call does not return usable text, or the API key is not configured, the backend builds a local aggregate from completed per-video summaries and keeps the corresponding status in logs and results.

### Why does Qwen source URL input fail?

Many platform video URLs require cookies, Referer, User-Agent, or temporary signatures. Qwen servers cannot access those URLs directly. Enable OSS transfer or use local download plus upload.

### Where do Whisper timestamps come from?

openai-whisper itself outputs segment timestamps. This project extracts audio with ffmpeg and runs PyTorch-based openai-whisper; CUDA and fp16 are used when available.

### What happens when Bilibili download is interrupted?

Bilibili downloads keep `.part` files and refresh playurl when the link fails. If the server supports Range, the downloader tries to resume; otherwise it restarts the file.

## Development Checks

Common checks:

```shell
uv run python -m py_compile api\services\video_summary_manager.py api\routers\video_summary.py api\schemas\video_summary.py tools\video_summary_cli.py

cd webui
npm run build
```

## License and Disclaimer

This project is modified from [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) and inherits its non-commercial learning and research purpose. Read and follow the repository `LICENSE`.

This project is only for learning, research, and technical validation. Users must confirm platform rules, laws, account risks, and data compliance requirements by themselves. Commercial use, bulk collection, platform risk-control bypassing, privacy infringement, copyright infringement, or illegal activity is strictly prohibited. Any account, data, cost, legal, or other risk caused by using this project is the user's responsibility.
