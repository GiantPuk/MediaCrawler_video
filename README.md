# MediaCrawler Video

基于 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的视频检索、下载与多模态理解工作台。

这个 fork 的目标已经不只是“把平台内容爬到本地”，而是围绕视频任务形成一条可操作的流程：

1. 真实调用各平台已有爬虫或公开接口检索候选视频。
2. 先返回候选元数据，人工勾选需要处理的视频。
3. 对选中视频执行下载、OSS 转存、Qwen/DashScope 视频理解、可选 Whisper 转录。
4. 生成单视频时间线摘要、整体汇总、Markdown 结果和 Mermaid 思维导图。
5. 同一套后端能力同时支持 WebUI 和 CLI。

本项目仍继承原 MediaCrawler 的非商业学习研究属性。请只在个人学习、研究、测试场景使用，不要用于商业化、大规模抓取、绕过平台限制或任何违法违规行为。

## 当前重点能力

- 视频搜索工作台：支持按标题/关键词、作者、榜单检索候选。
- 作者候选：B 站支持用户名候选搜索，重名时先返回 UID、头像、粉丝数、视频数等信息；其他平台优先使用主页链接或 creator ID。
- 候选勾选：默认先爬元数据，不自动下载全部结果，降低流量和账号风险。
- 下载与分析流水线：支持下载、进度条、子任务耗时、上传速率、失败原因展示。
- 多模态理解：支持 Qwen/DashScope 兼容 API，默认模型为 `qwen3.5-omni-plus`，默认不启用 Whisper。
- 文本融合：可选 Whisper 转录，结果会作为文本上下文融合进视频理解。
- OSS 转存：支持把本地视频或源站视频流转存到阿里云 OSS，再用签名 URL 交给模型；默认分析后清理临时 OSS 对象。
- Markdown 渲染：前端支持 Markdown、表格和 Mermaid mindmap。
- 数据管理：区分搜索记录、榜单记录、创作者记录、内容记录、评论记录、视频理解结果。
- CLI：`tools/video_summary_cli.py` 覆盖作者解析、任务启动、任务轮询、平台 Cookie 档案和 Qwen/OSS 配置管理。
- 原爬虫兼容：保留 `main.py` 和原 MediaCrawler 的 search/detail/creator 入口。

## 项目结构

```text
api/
  routers/video_summary.py        # 视频工作台 API
  schemas/video_summary.py        # 视频任务、配置、进度 schema
  services/video_summary_manager.py
webui/src/components/video/
  VideoWorkspace.tsx              # 当前 WebUI 视频工作台
tools/
  video_summary_cli.py            # 视频工作台 CLI
  test_qwen_oss_video.py          # OSS + Qwen 视频 URL 测试工具
media_platform/                  # 原 MediaCrawler 平台爬虫与本 fork 的增量适配
store/                           # 各平台采集结果写入逻辑
data/                            # 本地任务数据，默认不提交 Git
browser_data/                    # 扫码登录持久化浏览器上下文，默认不提交 Git
```

## 快速启动

### 依赖

- Python 3.11
- [uv](https://docs.astral.sh/uv/getting-started/installation)
- Node.js 16+
- Chrome 或 Playwright 浏览器
- 可选：ffmpeg，Whisper 音频转录需要
- 可选：CUDA 版 PyTorch，本地 Whisper GPU 转录需要

### 安装

```shell
cd MediaCrawler_video
uv sync

cd webui
npm install
```

标准 Playwright 模式需要安装浏览器：

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

构建静态前端后，也可以只通过后端访问：

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

长视频任务运行时不建议使用 `--reload`，因为 reload 会重启进程，内存中的实时任务状态会丢失。

## 登录与账号状态

平台登录信息在 WebUI 右上角“设置 > 平台登录信息”中管理。

支持两种方式：

- Cookie 档案：粘贴浏览器 DevTools 里的 Cookie 表格、JSON cookie 导出或 Cookie header。
- 扫码登录：调用原 MediaCrawler 平台登录流程，扫码后保存 Cookie 和 `browser_data/<platform>_user_data_dir` 元信息。

Cookie 与扫码保存的结果本质上都用于后续请求认证。只要某个平台有可用 Cookie 档案，视频任务就可以用 `login_type=cookie` 运行；没有 Cookie 时会根据平台能力尝试二维码登录或无头浏览器流程。

敏感配置默认保存在：

```text
data/video_tasks/platform_credentials.json
data/video_tasks/qwen_settings.json
browser_data/
```

这些路径已被 `.gitignore` 忽略，不应提交到远程仓库。

## WebUI 工作流

### 搜索视频

1. 进入“搜索”页。
2. 选择平台。
3. 搜索方式选择“标题/关键词”或“作者”。
4. 点击检索。
5. 在候选列表中查看标题、作者、发布时间、播放量、点赞数、评论数、时长、封面等元数据。
6. 勾选视频后选择下载或下载并分析。

### 作者任务

B 站支持作者用户名搜索；如果有重名作者，前端会先展示候选作者卡片，选中具体 UID 后再加载该作者视频。

其他平台目前更可靠的方式是输入主页链接或平台 creator ID。未真实接入的作者搜索不会伪装成功。

### 榜单任务

进入“排行榜”页，选择平台和榜单类型。榜单结果分两类：

- 视频候选：可以直接勾选下载或分析。
- 话题/热搜词/问题卡：只能继续作为关键词搜索视频，不会假装成可下载视频。

### 设置

“设置”页分三类：

- 平台登录信息：管理多套 Cookie/扫码登录档案。
- 视频分析 API：管理 Qwen/DashScope API、模型名称、Base URL、OSS 配置。
- 基础参数：抓取间隔、最大视频数、并发、下载/上传模式、抽帧数、Whisper 参数等。

## 视频分析链路

默认上传后端为 `auto`，真实执行顺序如下：

1. 如果平台返回的源视频 URL 可被 Qwen 直接访问，优先尝试源 URL 直给模型。
2. 如果源 URL 需要平台请求头且 OSS 已启用，后端会边读源站视频流边 multipart 上传 OSS，再把签名 URL 交给模型。
3. 如果前两步不可用，进入本地下载。
4. 本地下载成功后，按配置尝试 OSS URL、DashScope SDK 本地视频上传、OpenAI-compatible base64 视频或抽帧。
5. 如果启用 Whisper，会先用 ffmpeg 提取音频，再用 openai-whisper 基于 PyTorch 转录，转录文本会融合到模型 prompt 中。
6. 任务结束后，如启用 `oss_cleanup_after_analysis`，会删除本次分析上传到 OSS 的临时对象。

不会为了“看起来成功”而伪造下载、榜单或模型分析结果。未接入或平台未返回可用直链时，会显示明确的 unsupported、missing 或 failed 状态。

## 平台接入状态

| 平台 | 标题/关键词视频搜索 | 作者候选搜索 | 作者视频 | 榜单 | 下载 | 总结 |
| --- | --- | --- | --- | --- | --- | --- |
| B 站 | 已接入并实测通过 | 支持用户名候选，返回 UID/头像/粉丝/视频数 | 已接入并实测通过 | `popular`、`ranking`、`ranking_<region>`、`precious`、`weekly`、`hot_search`；`weekly` 通常需要有效 Cookie | 已接入并实测通过 | 已接入并实测通过 |
| 小红书 | 已用有效 Cookie 实测可返回 `type=video` 候选 | 可靠方式是主页链接或 creator ID | 依赖有效 Cookie 与原项目能力 | 未接入真实榜单 | 候选可能不含直链，需要走 detail/native 链路 | 有本地视频后可总结 |
| 抖音 | 已用有效 Cookie/CDP 或标准模式实测可返回视频候选和播放直链 | 可靠方式是主页链接或 `sec_user_id` | 依赖有效 Cookie | `hot_search`、`trending` 返回热搜词/话题，可继续搜视频 | 有真实视频直链时可下载 | 有本地视频后可总结 |
| 快手 | 已用有效 Cookie 实测，使用原项目签名搜索接口 | 可靠方式是主页链接或 creator ID | 依赖有效 Cookie，已同步签名 REST profile feed | `hot` 返回 brilliant 短视频热榜 `photoId` 候选 | 有真实视频直链时可下载；仅有 `photoId` 会标记不支持 | 有本地视频后可总结 |
| 微博 | 保留原项目视频搜索路径；依赖有效 Cookie | 可靠方式是主页链接或 UID | 依赖有效 Cookie 和原项目能力 | `hot_search`、`hot_gov` 返回热搜词/话题，可继续搜视频 | 有真实视频直链时可下载 | 有本地视频后可总结 |
| 知乎 | 已用有效 Cookie 实测 `zvideo` 搜索通过；注意日期范围 | 可靠方式是主页链接或 creator ID | 已接入 zvideo feed，依赖有效 Cookie | `total`、`zvideo` 返回 hot-lists 榜单；常见结果是问题卡 | 未验证稳定直链下载 | 有本地视频后可总结 |
| 贴吧 | 未接入真实视频搜索/下载 | 不适用于视频任务 | 不适用于视频任务 | `hot_topic` 返回热议话题，仅展示或作为关键词 | 未接入 | 未接入 |

## CLI 使用

CLI 调用本地后端 API，所以需要先启动后端。

查看帮助：

```shell
uv run python tools/video_summary_cli.py --help
uv run python tools/video_summary_cli.py tasks start --help
```

解析作者候选：

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

按作者 UID 只爬元数据：

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

对元数据任务中的选中视频下载并总结：

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

搜索和榜单：

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

查询、等待、停止：

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
uv run python tools/video_summary_cli.py tasks stop <task_id>
```

平台 Cookie 档案：

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
uv run python tools/video_summary_cli.py credentials show <credential_profile_id>
uv run python tools/video_summary_cli.py credentials update <credential_profile_id> --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials delete <credential_profile_id>
```

扫码登录并保存 Cookie：

```shell
uv run python tools/video_summary_cli.py credentials qrcode-login --platform bili --name "bili-qrcode"
uv run python tools/video_summary_cli.py credentials qrcode-status <login_task_id>
uv run python tools/video_summary_cli.py credentials qrcode-wait <login_task_id>
```

Qwen/DashScope 与 OSS：

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

测试 OSS + Qwen 大视频 URL：

```shell
uv run python tools/test_qwen_oss_video.py --video path\to\video.mp4 --model qwen-vl-max --model qwen3.5-omni-plus
uv run python tools/test_qwen_oss_video.py
```

## 原 MediaCrawler 入口

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

视频工作台会在需要时复用原项目的平台 crawler、client、store 和 login 模块，但不会完全绕开原项目重造爬虫。

## 数据保存

原爬虫数据仍支持 JSON、JSONL、CSV、Excel、SQLite、MySQL、MongoDB 等方式，具体见：

```text
docs/data_storage_guide.md
```

视频任务数据默认在：

```text
data/video_tasks/<task_id>/
  raw/                 # 平台原始元数据、下载文件
  transcripts/         # Whisper 转录
  result.json          # 任务结果、单视频摘要、整体汇总
```

WebUI 的“数据管理”会隐藏敏感配置文件，并按类别展示搜索、榜单、评论、内容、创作者和视频理解结果。

## 风控与性能建议

- 默认并发建议保持 `1`。
- 使用“最小间隔 / 最大间隔 / 每 N 条长暂停”随机化请求节奏。
- 先 metadata-only，确认候选后再勾选下载和总结。
- 对账号敏感平台优先复用真实 Chrome/CDP 登录态；无头模式更方便，但未必更像真人环境。
- 不建议开启评论大规模抓取。
- OSS 只作为临时转存，建议保持“分析后删除临时对象”开启。

## 常见问题

### 为什么整体汇总有时走 fallback？

当聚合模型调用失败、API key 未配置或模型没有返回可用文本时，后端会用已生成的单视频摘要自动整理一个本地 fallback 汇总。fallback 不再截断 Markdown，会保留共同主题、各自梗概、摘要和 Mermaid 思维导图。

### 为什么有些榜单项不能下载？

一些平台榜单返回的是热搜词、话题、问题或 `photoId`，不是可公开视频直链。本项目会明确标记这类项，并提供“继续搜视频”的路径。

### 为什么 Qwen 源 URL 直传会失败？

很多平台的视频 URL 需要 Cookie、Referer、User-Agent 或临时签名，Qwen 服务器无法直接访问。此时可以启用 OSS 转存，或走本地下载后上传。

### Whisper 时间戳来自哪里？

Whisper/openai-whisper 模型本身支持分段时间信息。本项目会用 ffmpeg 抽音频，再用 PyTorch 版 openai-whisper 运行；如果有 CUDA 可用，会使用 GPU 和 fp16。

## 开发验证

常用检查：

```shell
uv run python -m py_compile api\services\video_summary_manager.py api\routers\data.py api\schemas\crawler.py api\schemas\video_summary.py

cd webui
npm run build
```

## 许可与免责声明

本项目基于上游 [NanmiCoder/MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 修改，继承其非商业学习研究定位。请阅读并遵守仓库中的 `LICENSE`。

本项目仅用于学习、研究和技术验证。使用者需要自行确认目标平台规则、法律法规、账号风险和数据合规要求。严禁用于商业用途、批量采集、绕过平台风控、侵犯隐私、侵犯版权或其他违法违规行为。因使用本项目造成的账号、数据、费用、法律或其他风险，由使用者自行承担。
