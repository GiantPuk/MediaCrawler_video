# MediaCrawler Video Workbench 技术报告

生成日期：2026-08-14
项目路径：`E:\大三下\北深实习\MediaCrawler_video`

## 1. 项目目标与完成概览

本项目基于 `NanmiCoder/MediaCrawler` 改造，目标是完成“支持小红书、抖音、快手、B站、微博等平台视频搜索和抓取，并对视频内容进行下载和文字归纳”的动手题目。相比原仓库，本项目重点从“通用内容采集”扩展为“视频检索、候选筛选、下载、视频理解、结果管理”的工作台。

当前已经实现的核心流程如下：

1. 支持按平台进行视频关键词搜索、作者视频检索、平台榜单/热榜检索。
2. 默认先只爬取元数据，返回候选视频列表，不自动下载全部结果。
3. 用户可勾选候选视频，再执行下载或下载并总结。
4. 支持 Qwen/DashScope、OpenAI-compatible、Ollama 本地视觉模型三类视频理解接口配置。
5. 支持源 URL 直传、OSS 临时转存、DashScope 本地视频上传、base64 小视频上传、抽帧分析等多种输入链路。
6. 支持可选 Whisper 转录，并把字幕、平台文本、Whisper 转录作为文本上下文融合进视频理解 prompt。
7. 支持任务进度、子任务耗时、下载/上传速度、断点续跑、临时 OSS 对象清理。
8. 同一套后端能力同时提供给 WebUI 和 CLI。

项目坚持真实接入原则：能真实调用平台接口或原 MediaCrawler 能力的才标记为已接入；只能返回热搜词、话题或问题卡的榜单不会伪装为可下载视频；平台不返回可用直链或登录态失效时会显示明确失败状态。

## 2. 系统架构

### 2.1 总体结构

项目由四层组成：

| 层次 | 主要文件 | 作用 |
| --- | --- | --- |
| 原 MediaCrawler 爬虫层 | `main.py`, `media_platform/`, `store/`, `config/base_config.py` | 保留原项目的平台登录、搜索、详情、创作者采集与 JSON 存储能力。 |
| 视频工作台后端 | `api/routers/video_summary.py`, `api/schemas/video_summary.py`, `api/services/video_summary_manager.py` | 统一任务编排、候选筛选、下载、OSS、Whisper、Qwen/Ollama 调用、状态持久化。 |
| WebUI 前端 | `webui/src/components/video/VideoWorkspace.tsx`, `webui/src/lib/api.ts` | 提供视频网站式搜索、候选列表、勾选下载/总结、排行榜、设置管理和结果渲染。 |
| CLI 工具 | `tools/video_summary_cli.py` | 支持用终端完成作者解析、任务启动/停止/续跑、榜单任务、配置管理和登录健康检查。 |

后端以 FastAPI 暴露接口，主要 API 包括：

- `GET/POST /api/video-summary/settings`：视频分析 API 配置。
- `GET/POST/PUT/DELETE /api/video-summary/settings/profiles`：多套模型/API 配置档案。
- `GET/POST/PUT/DELETE /api/video-summary/platform-credentials`：各平台 Cookie/扫码登录信息。
- `POST /api/video-summary/platform-credentials/{id}/health`：登录健康检查。
- `POST /api/video-summary/platform-credentials/{id}/self-test`：低风险自测。
- `POST /api/video-summary/creators/resolve`：作者候选解析。
- `POST /api/video-summary/tasks/start`：启动视频任务。
- `GET /api/video-summary/tasks/{task_id}`：查询任务状态。
- `POST /api/video-summary/tasks/{task_id}/stop`：停止任务。
- `POST /api/video-summary/tasks/{task_id}/resume`：续跑任务。

### 2.2 任务模型

一个视频任务的核心参数包括：

| 参数 | 含义 |
| --- | --- |
| `platform` | 平台：`xhs`, `dy`, `ks`, `bili`, `wb`, `tieba`, `zhihu`。 |
| `source_mode` | 来源模式：`search` 关键词搜索、`creator` 作者视频、`ranking` 排行榜/热榜。 |
| `workflow_mode` | 工作流：`metadata_only` 只取候选，`selected_items` 处理已勾选候选，`full` 完整流程。 |
| `max_crawl_items` | 平台侧原始抓取上限。 |
| `max_videos` | 按日期和视频类型筛选后最多保留的候选数。 |
| `start_date/end_date` | 发布时间过滤范围。 |
| `selected_item_ids` | 用户勾选的视频 ID。 |
| `video_input_mode` | 视频理解输入模式，目前推荐 `auto`。 |
| `video_upload_backend` | 上传链路：`auto`, `oss`, `dashscope`, `openai`, `frames`。 |
| `enable_whisper_transcription` | 是否启用 Whisper 转录。 |

任务状态持久化在：

```text
data/video_tasks/<task_id>/task_state.json
data/video_tasks/<task_id>/result.json
data/video_tasks/<task_id>/raw/
data/video_tasks/<task_id>/transcripts/
```

这使得任务失败、停止或后端重启后可以恢复已下载视频、已完成摘要和已选候选。

## 3. 已实现能力

### 3.1 视频搜索与候选筛选

当前检索不是语义向量搜索，也不是模糊语义搜索，而是直接调用平台搜索、作者页、榜单接口或原 MediaCrawler 搜索逻辑。检索输入会作为平台关键词、作者 ID/主页或榜单类型传入平台侧能力。后续视频理解只负责对已找到的视频进行内容分析。

为了避免“先抓很多无关内容再筛选”，项目实现了两级数量控制：

| 字段 | 作用 |
| --- | --- |
| `max_crawl_items` | 最多从平台拿多少条原始记录。 |
| `max_videos` | 日期/视频类型筛选后最多保留多少候选。 |

最新实现已经支持边抓取边筛选：搜索和作者元数据任务会实时统计满足日期与视频类型条件的候选，达到 `max_videos` 后提前停止。如果一直筛不满，才会最多抓到 `max_crawl_items`。B 站直连 API 路径在每页结果内直接提前停止；其他 MediaCrawler 子进程路径通过监控 JSON 输出实时计数，达到目标后终止子进程。

相关实现位置：

- `api/schemas/video_summary.py`：新增 `max_crawl_items`。
- `api/services/video_summary_manager.py`：
  - `_task_crawl_limit`
  - `_run_crawler(..., monitor_filtered_candidates=True)`
  - `_current_filtered_candidate_counts`
  - `_count_filtered_video_records`
  - `_record_matches_video_filters`
  - `_fetch_bili_search_records`
  - `_fetch_bili_creator_arc_records`
- `webui/src/components/video/VideoWorkspace.tsx`：前端区分“筛选后数量”和“最大抓取上限”。
- `tools/video_summary_cli.py`：CLI 新增 `--max-crawl-items`。

### 3.2 作者搜索与重名消歧

B 站支持作者名搜索。输入用户名后，后端调用 B 站搜索接口返回候选作者列表，前端展示头像、UID、粉丝数、视频数、主页链接等元信息；用户选择具体作者后再加载该作者视频。这避免了重名作者直接误抓。

其他平台目前更稳定的方式是输入主页链接或平台 creator ID。对未稳定支持用户名搜索的平台，项目不会假装解析成功，而是提示使用主页或 ID。

### 3.3 排行榜与热榜

已接入的平台榜单分为两类：

| 平台 | 已接入榜单 | 类型 |
| --- | --- | --- |
| B 站 | `popular`, `ranking`, `ranking_<region>`, `precious`, `weekly`, `hot_search` | 前几类是真实视频候选；`hot_search` 是热搜词。 |
| 快手 | `hot` | brilliant 热榜 photoId 候选，下载仍取决于详情接口放行。 |
| 抖音 | `hot_search`, `trending` | 热搜词/话题，可继续作为关键词搜索视频。 |
| 微博 | `hot_search`, `hot_gov` | 热搜词/话题，可继续作为关键词搜索视频。 |
| 知乎 | `total`, `zvideo` | hot-lists，实际常返回问题卡或 zvideo 入口。 |
| 贴吧 | `hot_topic` | 热议话题，仅展示，不接入视频下载。 |

榜单项如果是话题、热搜词或问题卡，会标记为不可直接下载，但可以在前端作为关键词继续检索视频。

### 3.4 下载链路

下载逻辑优先利用平台返回的真实直链，不伪造下载结果。主要能力包括：

1. 平台候选里含直接视频 URL 时，走直接下载。
2. 对 B 站支持 public playurl 解析，并在链接过期或下载失败后重新解析 playurl。
3. 对需要 detail 模式的平台，调用原 MediaCrawler detail 爬取获取媒体链接。
4. 下载采用 `.part` 临时文件，成功后再改名为 `video.mp4`。
5. 支持 HTTP Range 断点续传；服务器忽略 Range 时会重新开始当前 URL。
6. 前端展示下载进度、总大小、速度、百分比、当前视频和子任务耗时。

### 3.5 视频理解链路

视频理解采用统一的智能路线。后端会按配置和可用条件选择输入方式：

1. Ollama 本地模型：只支持文本和抽帧图片，不直接把 `.mp4` 交给 Ollama。
2. 源 URL 直传：如果平台视频 URL 可被模型服务访问，优先尝试直接传 URL。
3. 源流转存 OSS：如果源 URL 需要 Cookie/Referer，但 OSS 配置完整，则边读源站视频流边上传 OSS，并把签名 URL 交给模型。
4. 本地下载后 OSS：下载本地视频后 multipart 上传 OSS，再交给模型。
5. DashScope SDK 本地视频上传：适用于 DashScope 官方路径。
6. OpenAI-compatible base64：仅用于小视频，项目默认限制为 7MB。
7. 抽帧分析：视频直传失败或本地模型限制时，用 ffmpeg 抽帧后分析。

模型 prompt 要求输出：

- 一句话概括
- 时间线摘要
- 主要内容
- 关键信息/人物/场景
- 是否与标题描述一致
- 可用于检索的标签

整体汇总会尝试输出共同主题、各自内容梗概、摘要以及 Mermaid mindmap。若聚合模型失败，会根据单视频摘要生成确定性兜底汇总，但会明确说明不是模型聚合结果。

### 3.6 Whisper 转录融合

Whisper 是可选能力。启用后，后端会：

1. 用 ffmpeg 提取音频并转为 Whisper 需要的 16kHz 16-bit PCM。
2. 使用基于 PyTorch 的 `openai-whisper` 运行转录。
3. 如果 CUDA 可用，则使用 GPU 和 fp16。
4. 将转录文本保存到 `data/video_tasks/<task_id>/transcripts/`。
5. 将 Whisper 转录作为“文本上下文”插入视频理解 prompt。

Whisper 的时间戳能力来自 Whisper 模型分段输出本身；本项目目前主要利用其文本结果融合进视频理解，摘要中的时间线主要由多模态模型基于视频/抽帧和文本共同生成。

### 3.7 设置管理与 CLI

WebUI 设置页已经支持：

- 多套视频分析 API 配置。
- DashScope、OpenAI-compatible、Ollama 三类 provider。
- 模型名称常用候选与手动输入。
- OSS 参数配置。
- 平台 Cookie/扫码登录档案管理。
- 平台登录健康检查与自测。
- 基础抓取、下载、上传、Whisper、抽帧参数。

CLI 覆盖主要能力：

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query "作者名"
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode search --query "关键词" --workflow-mode metadata_only --max-crawl-items 100 --max-videos 5
uv run python tools/video_summary_cli.py tasks resume <task_id>
uv run python tools/video_summary_cli.py credentials health <profile_id>
uv run python tools/video_summary_cli.py settings profiles
```

## 4. 平台接入状态评估

| 平台 | 搜索候选 | 作者视频 | 榜单/热榜 | 下载 | 总结 | 主要限制 |
| --- | --- | --- | --- | --- | --- | --- |
| B 站 | 已接入，支持直连 WBI 搜索和 MediaCrawler fallback | 已接入，支持 UID 和作者候选消歧 | 已接入多种真实视频榜单和热搜词 | 已接入，支持 playurl 解析和过期重解析 | 已接入 | Cookie 对 weekly 等接口有帮助；低清 public playurl 可能影响画质。 |
| 抖音 | 已接入，依赖 Cookie/CDP 或原项目签名逻辑 | 可靠方式为主页链接或 `sec_user_id` | 热搜词/话题 | 有真实直链时可下载 | 已接入 | 登录态和反爬影响大；部分源 URL 需 Referer/Cookie。 |
| 快手 | 已接入，依赖 Cookie 与签名接口 | 可靠方式为主页链接或 creator ID | brilliant 热榜 photoId | 有真实直链时可下载 | 已接入 | Cookie 失效会返回 No Login/UNAUTHENTICATED。 |
| 小红书 | 可返回视频候选 | 依赖主页链接或 creator ID | 未接入稳定真实视频榜单 | 候选不总是含直链，依赖 detail/native 链路 | 有视频后可总结 | 风控较严格，建议低频和真实浏览器上下文。 |
| 微博 | 保留原项目视频搜索路径 | 依赖主页链接或 UID | 热搜词/话题 | 有真实直链时可下载 | 已接入 | 播放数等字段不总是由搜索接口返回。 |
| 知乎 | 已验证 zvideo 搜索/入口 | 依赖主页链接或 ID | hot-lists | 下载直链未稳定验证 | 有视频文件后可总结 | 常返回问题卡，不一定是可下载视频。 |
| 贴吧 | 不接入视频搜索下载 | 不适用 | 热议话题 | 未接入 | 未接入 | 仅展示话题，不伪装成视频能力。 |

## 5. 测试与评估

### 5.1 验证方式

本项目的验证分为四类：

1. 静态编译验证：
   - `uv run python -m py_compile api/schemas/video_summary.py api/services/video_summary_manager.py tools/video_summary_cli.py`
   - `npm run build`
2. 无网络逻辑验证：
   - 构造本地候选记录，验证 `max_crawl_items` 与 `max_videos` 的边抓边筛逻辑。
3. 真实平台任务验证：
   - 使用 `data/video_tasks/*/task_state.json` 中的真实任务状态评估。
   - 使用 `data/video_tasks/cross_platform_real_video_test/*.json` 中的跨平台实验记录评估。
4. 前后端可用性验证：
   - 后端健康检查：`http://127.0.0.1:8080/api/health`
   - 前端访问：`http://127.0.0.1:5173/`

### 5.2 本地任务数据统计

截至本报告生成时，本地 `data/video_tasks/*/task_state.json` 中统计到：

| 指标 | 数值 |
| --- | --- |
| 总任务数 | 88 |
| completed | 73 |
| error | 13 |
| running | 2 |
| 覆盖平台 | xhs, dy, ks, bili, wb, tieba, zhihu |

按平台任务数量：

| 平台 | 任务数 |
| --- | ---: |
| B 站 | 21 |
| 抖音 | 15 |
| 小红书 | 14 |
| 快手 | 14 |
| 微博 | 12 |
| 知乎 | 9 |
| 贴吧 | 3 |

### 5.3 元数据检索耗时

从已完成 metadata-only 任务统计：

| 来源模式 | 样本数 | 中位数 | 平均值 | 最小值 | 最大值 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 关键词搜索 | 29 | 17.5s | 17.3s | 0.4s | 61.0s |
| 作者视频 | 1 | 1.2s | 1.2s | 1.2s | 1.2s |
| 榜单/热榜 | 16 | 0.3s | 0.3s | 0.1s | 0.5s |

按平台的 metadata 子任务耗时：

| 平台 | 样本数 | 中位数 | 平均值 | 最大值 |
| --- | ---: | ---: | ---: | ---: |
| B 站 | 21 | 0.0s | 0.3s | 1.2s |
| 抖音 | 15 | 0.5s | 6.8s | 24.7s |
| 快手 | 14 | 0.5s | 7.9s | 26.6s |
| 微博 | 12 | 0.1s | 5.8s | 23.2s |
| 小红书 | 13 | 0.0s | 16.7s | 60.9s |
| 知乎 | 8 | 19.6s | 15.7s | 35.8s |
| 贴吧 | 3 | 0.2s | 0.2s | 0.2s |

注意：部分 metadata 子任务显示接近 0 秒，是因为 selected_items 任务复用了已有候选，不代表真实平台搜索总是 0 秒。真实“搜一个视频”的时间更应参考关键词搜索模式中位数和平台实际路径。

### 5.4 下载、转录、上传、模型分析耗时

子任务统计结果：

| 阶段 | 样本数 | 中位数 | 平均值 | 最小值 | 最大值 |
| --- | ---: | ---: | ---: | ---: | ---: |
| metadata | 86 | 0.3s | 7.3s | 0.0s | 60.9s |
| download | 13 | 2.7s | 27.5s | 0.8s | 156.3s |
| transcribe | 12 | 9.0s | 18.2s | 0.2s | 51.7s |
| upload | 4 | 16.3s | 16.3s | 14.0s | 18.5s |
| qwen | 23 | 32.5s | 58.4s | 5.6s | 150.8s |

按平台下载耗时：

| 平台 | 样本数 | 中位数 | 平均值 | 最大值 |
| --- | ---: | ---: | ---: | ---: |
| B 站 | 7 | 2.1s | 5.7s | 17.2s |
| 抖音 | 4 | 75.0s | 78.3s | 156.3s |
| 微博 | 2 | 2.1s | 2.1s | 2.5s |

按模型/Provider 的已完成分析阶段样本：

| 模型/Provider | 样本数 | 中位数 | 平均值 | 最大值 |
| --- | ---: | ---: | ---: | ---: |
| DashScope provider | 22 | 20.5s | 25.1s | 125.5s |
| Ollama provider | 32 | 12.3s | 42.8s | 150.8s |
| `qwen3.5-omni-plus` | 10 | 19.2s | 20.4s | 57.0s |
| `qwen-vl-max` | 12 | 24.0s | 28.9s | 125.5s |
| `qwen2.5vl:3b` 本地 | 21 | 6.3s | 14.2s | 95.1s |
| `qwen3-vl:8b` 本地 | 11 | 106.4s | 97.4s | 150.8s |

这些结果说明：

- 云端 DashScope 在短视频上通常更稳定，模型分析本身常在 20-60 秒。
- 本地 3B 模型响应较快，但质量和细节通常弱于云端大模型。
- 本地 8B 模型在 4070 上能跑，但抽帧+上下文更重时会明显慢于云端。
- Whisper GPU 转录可用，但耗时主要受视频时长和音频长度影响；已记录样本中位数约 9 秒，长视频可到 30-50 秒。

### 5.5 “搜一个视频”时间估计

这里把“搜一个视频”拆成两个概念：

1. 只搜索候选：返回视频卡片，不下载、不总结。
2. 完整处理一个视频：搜索候选后，下载并生成摘要。

基于本机、当前网络、保守抓取配置和已有任务统计，估计如下：

| 场景 | 估计耗时 |
| --- | ---: |
| B 站榜单/热门 Top 候选 | < 1s |
| B 站关键词搜索，走直连 WBI API | 1-3s |
| B 站关键词搜索，走浏览器/MediaCrawler fallback | 10-30s |
| 抖音/快手/微博普通关键词搜索 | 10-30s 常见，登录或风控波动可到 60s |
| 小红书关键词搜索 | 20-60s，受风控和页面写盘粒度影响较大 |
| 知乎 zvideo/搜索 | 15-35s |
| 只从已存在候选中勾选一个视频 | 接近 0s 元数据阶段 |
| B 站下载并云端总结一个短视频 | 1-2 分钟常见 |
| 抖音/快手下载并云端总结一个视频 | 2-5 分钟常见，大文件或限速时更久 |
| 本地 Ollama 3B 抽帧总结一个短视频 | 20-60s 常见，但质量较弱 |
| 本地 Ollama 8B 抽帧总结一个视频 | 2-5 分钟常见 |

影响耗时的主要因素：

- 平台是否有直连 API。
- 是否需要 Playwright/CDP 浏览器启动或登录验证。
- `crawl_min_sleep_seconds/crawl_max_sleep_seconds` 的保守间隔。
- `max_videos` 和 `max_crawl_items`。
- 平台视频直链是否限速。
- 视频大小、视频时长。
- 是否启用 Whisper。
- 是否启用 OSS 转存。
- 选择的模型和 provider。

## 6. 性能优化设计

已经实现或正在使用的优化包括：

1. metadata-only 默认流程：先展示候选，避免搜到就自动下载。
2. 候选早停：边抓边筛，到 `max_videos` 即停。
3. B 站直连 API：关键词搜索、作者视频、榜单尽量跳过浏览器启动。
4. B 站 playurl 重解析：下载链接过期后重新解析。
5. Range 断点续传：减少接近完成时中断造成的浪费。
6. `.part` 临时文件：避免把未完成文件误认为可用视频。
7. OSS multipart 上传：大视频上传更稳定，可显示进度和速度。
8. OSS 临时对象清理：分析结束后删除一次性视频，避免 bucket 占满。
9. 任务状态持久化：可续跑，不必重做已完成摘要。
10. 单控制台策略：系统控制台输出阶段日志，任务区域显示结构化进度，避免多个控制台互相割裂。

仍可继续优化：

- 对更多平台实现稳定的直连元数据 API，减少浏览器路径。
- 对小红书、抖音、快手进一步抽象“源 URL 复用、重新解析、请求头补全”逻辑。
- 对下载速度慢的平台加入更细的测速和失败分类。
- 对 Qwen/Ollama 的模型选择建立基准集，按视频类型自动推荐模型。
- 对 Whisper 分段时间戳进一步利用，生成更可靠的时间线对齐。
- 前端可增加结果质量评分或人工标注，以便后续做 prompt 与模型评估。

## 7. 稳定性与风控

当前稳定性策略：

1. 默认不开评论、不开子评论。
2. 默认 metadata-only，减少下载和详情请求。
3. 支持最小间隔、最大间隔、每 N 条长暂停，并由后端统一随机执行。
4. 推荐并发数为 1。
5. 支持 Cookie/扫码登录持久化。
6. 支持平台登录健康检查和低风险自测。
7. 支持 headless 或 CDP 真实浏览器模式。
8. 对未真实接入或登录失败的平台明确报错，不用假数据兜底。

风险点：

- 小红书、抖音、快手等平台风控较强，Cookie 质量和账号行为会影响成功率。
- 无头浏览器不弹窗，但仍需要有效登录态；扫码保存的本质也是 Cookie/浏览器上下文。
- 过于固定的请求间隔容易被检测，建议使用随机区间。
- 平台接口字段经常变化，播放量、封面、时长等字段可能缺失。
- 下载和模型分析会消耗网络流量、OSS 容量、API 额度和本地 GPU/CPU。

## 8. 结果质量评估

从实际测试看，视频总结质量主要受三点影响：

1. 是否能把完整视频交给云端多模态模型。
2. 是否有可靠字幕、平台摘要或 Whisper 转录。
3. 模型本身对视频主题和领域术语的理解能力。

已观察到的现象：

- 单纯抽帧容易遗漏音频叙事，特别是游戏解说、电影解说、测评类视频。
- 仅 Whisper 转录又会丢失画面信息，无法判断镜头、人物、场景和标题一致性。
- “Whisper/字幕文本 + 视频/抽帧视觉理解”融合效果更稳。
- 云端大模型通常比本地小模型更能生成完整时间线摘要。
- 本地小模型速度快，但容易内容泛化、细节不足或格式不稳。

因此当前默认推荐：

- 短视频：优先 Qwen/DashScope 视频输入。
- 长视频或平台 URL 不可直连：启用 OSS 临时转存。
- 解说类、游戏类、测评类视频：建议启用 Whisper。
- 本地实验：Ollama 可以用于快速低成本测试，但不建议作为最终高质量报告唯一来源。

## 9. 对原题目的完成度判断

原题目要求：

> 支持小红书、抖音、快手、B站、微博等平台视频搜索和抓取，支持对视频内容进行下载和文字归纳。

当前完成度判断：

| 要求 | 完成情况 |
| --- | --- |
| 多平台视频搜索 | 基本完成，B站最完整；抖音、快手、小红书、微博依赖 Cookie 和平台接口稳定性。 |
| 视频抓取/下载 | 部分完成，B站、微博、抖音/快手有真实直链时可下载；小红书依赖详情链路；知乎/贴吧未稳定下载。 |
| 今天排行榜前 5 | B站视频榜单完成度高；快手有热榜候选；抖音/微博多为热搜词/话题，需要二次关键词搜索；贴吧/知乎多为话题/问题卡。 |
| 某用户今天发布视频 | B站完成度高，支持作者消歧；其他平台建议主页链接或 creator ID，依赖登录态。 |
| 下载后总结归纳 | 已完成，支持云端 Qwen、OSS、Whisper、本地 Ollama。 |
| 稳定、快速、本地部署 | WebUI/CLI、本地任务持久化、Ollama/Whisper 已接入；平台风控和视频下载速度仍是主要瓶颈。 |

整体来看，本项目已经完成可演示、可测试、可迭代的版本。B 站链路最接近完整生产可用；抖音、快手、微博、小红书已具备真实搜索和部分下载分析能力，但需要更多账号、Cookie、接口稳定性测试才能达到 B 站同等级别。

## 10. 运行与复现建议

启动后端：

```shell
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8080
```

启动前端：

```shell
cd webui
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：

```text
http://127.0.0.1:5173/
```

典型 CLI 任务：

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode search ^
  --query "上海交通大学计算机夏令营" ^
  --workflow-mode metadata_only ^
  --max-crawl-items 100 ^
  --max-videos 5 ^
  --headless ^
  --crawl-min-sleep-seconds 5 ^
  --crawl-max-sleep-seconds 10
```

推荐测试顺序：

1. 先在设置页配置平台 Cookie 并运行自测。
2. 先 metadata-only 搜索候选。
3. 勾选 1 个小视频做下载和总结。
4. 确认模型配置可用后再扩大到 3-5 个视频。
5. 长视频建议启用 OSS，并保持“分析后删除 OSS 临时视频”开启。

## 11. 结论

本项目已经把原 MediaCrawler 扩展为面向视频理解任务的完整工作台：前端具备搜索、榜单、候选勾选、设置管理和结果渲染；后端具备真实平台采集、候选早停、下载续传、OSS、Whisper、Qwen/Ollama 分析和任务续跑；CLI 能覆盖核心功能，方便实验和复现。

从当前测试数据看，搜索候选本身通常在秒级到几十秒完成，榜单最快，平台浏览器路径最慢；完整下载并总结一个视频通常需要 1-5 分钟，主要耗时来自下载、上传、Whisper 和模型分析。后续优化应重点放在平台直连接口扩展、下载链路稳定性、模型质量基准和更细的错误分类上。
