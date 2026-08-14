# MediaCrawler Video Workbench

<div align="center">

基于 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 改造的视频检索、下载与多模态理解工作台。

[English](README_en.md) · [原项目](https://github.com/NanmiCoder/MediaCrawler) · [数据存储说明](docs/data_storage_guide.md) · [CDP 模式说明](docs/CDP模式使用指南.md)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Node.js](https://img.shields.io/badge/Node.js-16%2B-green)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)
![Vite](https://img.shields.io/badge/WebUI-Vite-646CFF)
![License](https://img.shields.io/badge/License-Non--commercial-orange)

</div>

> [!WARNING]
> 本项目仅限个人学习、科研验证和技术测试。请遵守目标平台规则、法律法规和数据合规要求，不要用于商业采集、批量抓取、绕过平台限制或侵犯他人权益。

## 项目简介

MediaCrawler Video Workbench 是在 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 基础上扩展的视频任务工作台。原项目的命令行入口、平台爬虫、登录方式和数据存储仍然保留；本仓库新增了一套面向视频检索、候选筛选、下载和内容归纳的 WebUI、API 与 CLI。

主要能力：

- 按关键词、作者或平台榜单检索视频候选。
- 先返回元数据，再由用户勾选需要下载或分析的视频。
- 对选中视频执行下载、断点续传、OSS 临时转存、Qwen/DashScope/Ollama 分析和可选 Whisper 转录。
- 输出单视频时间线摘要、整体汇总、Markdown 结果和 Mermaid mindmap。
- WebUI 与 CLI 共用同一套后端接口和任务状态。

任务状态会保留候选、下载、上传、转录和模型分析的阶段结果，方便在界面或 CLI 中定位问题并继续执行。

## 目录

- [项目简介](#项目简介)
- [与原 MediaCrawler 的关系](#与原-mediacrawler-的关系)
- [核心能力](#核心能力)
- [常用平台入口](#常用平台入口)
- [快速开始](#快速开始)
- [WebUI 使用流程](#webui-使用流程)
- [配置说明](#配置说明)
- [CLI 使用](#cli-使用)
- [数据与结果](#数据与结果)
- [视频理解链路](#视频理解链路)
- [运行建议](#运行建议)
- [使用文档](#使用文档)
- [技术报告](#技术报告)
- [常见问题](#常见问题)
- [开发验证](#开发验证)
- [许可与免责声明](#许可与免责声明)

## 与原 MediaCrawler 的关系

本项目保留并复用原仓库的核心能力：

- `main.py`、`media_platform/`、`store/`、`config/base_config.py` 等原入口仍然可用。
- 平台登录、Cookie、CDP/Playwright 浏览器上下文尽量沿用原项目设计。
- 视频工作台只在必要处增加 API、WebUI、任务状态、OSS/Qwen、下载进度、结果渲染等能力。

爬虫侧优先复用原 MediaCrawler 的平台实现；只有在原项目能力不足以支撑视频任务时，才补充直连接口、字段归一化、下载进度和任务管理逻辑。

## 核心能力

| 能力 | 当前实现 |
| --- | --- |
| 视频检索 | 支持按关键词、作者、平台榜单检索候选；默认 metadata-only，不自动下载全部结果。 |
| 作者消歧 | B 站支持按用户名返回候选作者卡片，包含 UID、头像、粉丝数、视频数等；其他平台优先使用主页链接或 creator ID。 |
| 候选勾选 | 搜索后先展示候选视频，再勾选下载或总结，降低流量和账号风险。 |
| 下载进度 | 记录当前视频、已下载大小、总大小、速度、百分比、阶段耗时和失败原因。 |
| 断点续跑 | 任务状态写入 `task_state.json`，失败、停止或后端重启后可继续任务。 |
| 链接过期处理 | B 站下载失败时会重新解析真实 playurl 后再重试。 |
| 多模态理解 | 支持 Qwen/DashScope 兼容 API，也支持 Ollama 本地视觉模型；当前云端默认模型为 `qwen3.5-omni-plus`，默认不启用 Whisper。 |
| Whisper 融合 | 可选 openai-whisper，基于 PyTorch；转录文本会作为上下文融合进视频理解 prompt。 |
| OSS 转存 | 支持源流或本地视频 multipart 上传到阿里云 OSS，使用签名 URL 交给模型；默认分析后清理临时对象。 |
| Markdown 结果 | 前端支持 Markdown、表格和 Mermaid mindmap 渲染。 |
| 数据管理 | 区分搜索记录、榜单记录、创作者记录、内容记录、评论记录、视频理解结果。 |
| CLI | `tools/video_summary_cli.py` 覆盖作者解析、任务启动/轮询/停止/续跑、平台 Cookie、Qwen/OSS 配置。 |

## 常用平台入口

| 平台 | 推荐输入 | 常用入口 | 下载与总结 |
| --- | --- | --- | --- |
| B 站 | 关键词、作者名、UID、空间链接 | 关键词搜索、作者候选、作者视频、热门/分区/每周榜单 | 支持 playurl 解析、链接过期重解析、下载后总结。 |
| 小红书 | 关键词、作者主页链接、creator ID | 关键词搜索、作者视频 | 获取到视频文件后可进入总结流程。 |
| 抖音 | 关键词、主页链接、`sec_user_id` | 关键词搜索、作者视频、热搜词二次检索 | 有真实视频直链时可下载并总结。 |
| 快手 | 关键词、主页链接、creator ID | 关键词搜索、作者视频、热榜候选 | 有真实视频直链时可下载并总结。 |
| 微博 | 关键词、主页链接、UID | 视频搜索、作者视频、热搜词二次检索 | 有真实视频直链时可下载并总结。 |

## 快速开始

### 环境要求

- Python 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js 16+
- Chrome 或 Playwright 浏览器
- 可选：ffmpeg，Whisper 音频转录需要
- 可选：CUDA 版 PyTorch，本地 Whisper GPU 转录需要

### 安装依赖

```shell
cd MediaCrawler_video
uv sync

cd webui
npm install
```

如果使用标准 Playwright 模式，需要安装浏览器：

```shell
uv run playwright install
```

### 启动 WebUI

开发模式需要前后端各一个进程：

```shell
# 终端 1：后端 API，默认 8080
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080

# 终端 2：前端 Vite，默认 5173
cd webui
npm run dev
```

访问：

```text
http://localhost:5173/
```

也可以先构建静态前端，再只启动后端：

```shell
cd webui
npm run build

cd ..
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080
```

然后访问：

```text
http://localhost:8080/
```

长视频任务运行时不建议使用 `--reload`。任务会写入 `data/video_tasks/<task_id>/task_state.json`，后端重启或任务失败后可以续跑，但 `--reload` 仍会中断正在执行的下载、转录、上传或模型请求。

### 原 MediaCrawler 入口

原爬虫入口仍可使用：

```shell
uv run main.py --platform xhs --lt qrcode --type search
uv run main.py --platform xhs --lt qrcode --type detail
uv run main.py --help
```

基础配置仍在：

```text
config/base_config.py
```

## WebUI 使用流程

### 搜索视频

1. 进入“搜索”页。
2. 选择平台。
3. 选择搜索方式：标题/关键词、作者。
4. 点击检索，先返回候选视频。
5. 查看标题、作者、发布时间、播放量、点赞数、评论数、时长、大小、封面等元数据。
6. 勾选需要处理的视频，选择下载或下载并分析。

### 作者任务

B 站支持作者用户名搜索。如果有重名作者，前端会先展示候选作者卡片，选中具体 UID 后再加载该作者视频。

其他平台当前更可靠的输入方式是主页链接或平台 creator ID。

### 榜单任务

进入“排行榜”页后选择平台和榜单类型。榜单本身由平台实时返回，日期范围主要用于过滤榜单项继续检索到的视频发布时间。

### 任务续跑

任务失败、手动停止或后端重启后，前端会在可恢复任务旁显示“继续”。续跑会复用已下载文件、已完成摘要和已保存候选。

### 设置

右上角“设置”分三类：

- 平台登录信息：管理多套 Cookie/扫码登录档案，并支持登录健康检查。
- 视频分析 API：管理 Qwen/DashScope API、模型名称、Base URL、OSS 配置。
- 基础参数：抓取间隔、最大视频数、并发、下载/上传模式、抽帧数、Whisper 参数等。

## 配置说明

### 平台登录信息

支持两种方式：

- Cookie 档案：粘贴浏览器 DevTools Cookie 表格、JSON cookie 导出或 Cookie header。
- 扫码登录：调用原 MediaCrawler 平台登录流程，扫码后保存 Cookie 和 `browser_data/<platform>_user_data_dir` 元信息。

Cookie 与扫码保存的结果本质上都用于后续请求认证。只要某个平台有可用 Cookie 档案，视频任务就可以用 `login_type=cookie` 运行。

设置页支持“检测登录”：

- B 站会调用真实 `https://api.bilibili.com/x/web-interface/nav` 接口确认 `isLogin`。
- 其他平台会检查 Cookie 关键字段，并在设置页显示健康状态和提示信息。

敏感配置默认保存在：

```text
data/video_tasks/platform_credentials.json
data/video_tasks/qwen_settings.json
browser_data/
```

这些路径已被 `.gitignore` 忽略，不应提交到远程仓库。

### 视频分析 API

常用配置项：

| 配置 | 含义 |
| --- | --- |
| API Provider | 当前支持 DashScope、OpenAI-compatible 和 Ollama 本地。 |
| API Key | Qwen/DashScope 或兼容接口密钥。 |
| Base URL | 兼容接口地址，DashScope 兼容模式默认 `https://dashscope.aliyuncs.com/compatible-mode/v1`。 |
| Model | 模型名称，前端提供常用 Qwen 候选，也允许手动输入。 |
| Video Input Mode | 自动、视频优先、抽帧、文本优先等模式；当前推荐保持自动。 |
| Whisper | 可选，用于转录音频并融合到视频理解 prompt。 |

Ollama 本地模式使用 `http://127.0.0.1:11434`，不需要 API Key。当前接入的是 Ollama 官方图片输入能力：后端会先用 ffmpeg 对视频抽帧，再把抽帧图片和文本上下文交给本地 VL 模型。它不是把 `.mp4` 作为视频对象直接交给 Ollama。

### OSS 配置

启用 OSS 后，后端会把源流或本地视频临时上传到 OSS，再把签名 URL 交给模型。建议保持“分析后删除临时对象”开启，避免 bucket 被一次性视频占满。

### 抓取节奏

建议使用保守策略：

- 最大并发：`1`
- 最小间隔 / 最大间隔：使用随机区间
- 每 N 条长暂停：开启
- 评论抓取：默认关闭

## CLI 使用

CLI 调用本地后端 API，所以需要先启动后端。

### 帮助

```shell
uv run python tools/video_summary_cli.py --help
uv run python tools/video_summary_cli.py tasks start --help
```

### 作者解析

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

### 按作者 UID 只爬元数据

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

`--max-crawl-items` 是平台侧原始抓取上限，`--max-videos` 是日期/视频类型等筛选后的候选数量。搜索/作者元数据任务会边抓取边按筛选条件计数，筛满 `--max-videos` 后会提前停止；如果一直筛不满，才会最多抓到 `--max-crawl-items`。

### 对选中视频下载并总结

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

### 搜索与榜单

```shell
uv run python tools/video_summary_cli.py tasks ranking-options
uv run python tools/video_summary_cli.py tasks ranking-options --platform bili

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode search --query "上海交通大学计算机夏令营" --workflow-mode metadata_only --credential-profile-id <bili_profile_id> --headless --crawl-min-sleep-seconds 5 --crawl-max-sleep-seconds 10

uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type popular --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type ranking_game --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform dy --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <dy_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform ks --source-mode ranking --ranking-type hot --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <ks_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform wb --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <wb_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform zhihu --source-mode ranking --ranking-type total --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <zhihu_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform tieba --source-mode ranking --ranking-type hot_topic --ranking-limit 5 --workflow-mode metadata_only
```

### 查询、等待、停止、续跑

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
uv run python tools/video_summary_cli.py tasks stop <task_id>
uv run python tools/video_summary_cli.py tasks resume <task_id>
```

### 平台 Cookie 档案

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
uv run python tools/video_summary_cli.py credentials show <credential_profile_id>
uv run python tools/video_summary_cli.py credentials health <credential_profile_id>
uv run python tools/video_summary_cli.py credentials update <credential_profile_id> --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials delete <credential_profile_id>
```

### 扫码登录并保存 Cookie

```shell
uv run python tools/video_summary_cli.py credentials qrcode-login --platform bili --name "bili-qrcode"
uv run python tools/video_summary_cli.py credentials qrcode-status <login_task_id>
uv run python tools/video_summary_cli.py credentials qrcode-wait <login_task_id>
```

### Qwen/DashScope 与 OSS

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

### OSS + Qwen 视频 URL 测试

```shell
uv run python tools/test_qwen_oss_video.py --video path\to\video.mp4 --model qwen-vl-max --model qwen3.5-omni-plus
uv run python tools/test_qwen_oss_video.py
```

## 数据与结果

原爬虫数据仍支持 JSON、JSONL、CSV、Excel、SQLite、MySQL、MongoDB 等方式，具体见：

```text
docs/data_storage_guide.md
```

视频任务默认保存到：

```text
data/video_tasks/<task_id>/
  raw/                 # 平台原始元数据、下载文件
  transcripts/         # Whisper 转录
  task_state.json      # 可恢复任务状态、子任务进度、候选项状态
  result.json          # 任务结果、单视频摘要、整体汇总
```

WebUI 的“数据管理”会隐藏敏感配置文件，并按类别展示搜索、榜单、评论、内容、创作者和视频理解结果。

## 视频理解链路

默认上传后端为 `auto`，真实执行顺序如下：

1. 如果 API Provider 是 Ollama，本地模型会跳过视频 URL/视频文件直传，直接走抽帧图片分析。
2. 如果平台返回的源视频 URL 可被 Qwen 直接访问，优先尝试源 URL 直给模型。
3. 如果源 URL 需要平台请求头且 OSS 已启用，后端会边读源站视频流边 multipart 上传 OSS，再把签名 URL 交给模型。
4. 如果前两步不可用，进入本地下载。
5. 本地下载成功后，按配置尝试 OSS URL、DashScope SDK 本地视频上传、OpenAI-compatible base64 视频或抽帧。
6. 如果启用 Whisper，会先用 ffmpeg 提取音频，再用 openai-whisper 基于 PyTorch 转录，转录文本会融合到模型 prompt 中。
7. 任务结束后，如启用 `oss_cleanup_after_analysis`，会删除本次分析上传到 OSS 的临时对象。

## 运行建议

- 默认并发建议保持 `1`。
- 使用“最小间隔 / 最大间隔 / 每 N 条长暂停”随机化请求节奏。
- 先 metadata-only，确认候选后再勾选下载和总结。
- 对账号敏感平台优先复用真实 Chrome/CDP 登录态；无头模式更方便，但未必更像真人环境。
- 不建议开启评论大规模抓取。
- OSS 只作为临时转存，建议保持“分析后删除临时对象”开启。

## 使用文档

从零开始配置、搜索、下载、总结和 CLI 调用，请阅读：

```text
使用文档.md
```

## 技术报告

完整实现说明、常用平台路径、运行记录和耗时参考见：

```text
技术报告.md
```

## 常见问题

### 为什么整体汇总有时使用本地汇总？

当聚合模型调用失败、API key 未配置或模型没有返回可用文本时，后端会根据已完成的单视频摘要生成本地汇总，并在日志和结果中保留对应状态。

### 为什么 Qwen 源 URL 直传会失败？

很多平台的视频 URL 需要 Cookie、Referer、User-Agent 或临时签名，Qwen 服务器无法直接访问。此时可以启用 OSS 转存，或走本地下载后上传。

### Whisper 时间戳来自哪里？

Whisper/openai-whisper 模型本身支持分段时间信息。本项目会用 ffmpeg 抽音频，再用 PyTorch 版 openai-whisper 运行；如果有 CUDA 可用，会使用 GPU 和 fp16。

### B 站下载中断后会怎样？

B 站下载会保留 `.part` 临时文件，并在链接失败时重新解析 playurl。若服务端提供 Range，会尽量续传；否则会重新下载当前文件。

## 开发验证

常用检查：

```shell
uv run python -m py_compile api\services\video_summary_manager.py api\routers\video_summary.py api\schemas\video_summary.py tools\video_summary_cli.py

cd webui
npm run build
```

## 许可与免责声明

本项目基于上游 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 修改，继承其非商业学习研究定位。请阅读并遵守仓库中的 `LICENSE`。

本项目仅用于学习、研究和技术验证。使用者需要自行确认目标平台规则、法律法规、账号风险和数据合规要求。严禁用于商业用途、批量采集、绕过平台限制、侵犯隐私、侵犯版权或其他违法违规行为。因使用本项目造成的账号、数据、费用、法律或其他风险，由使用者自行承担。
