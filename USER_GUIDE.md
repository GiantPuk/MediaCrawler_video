# MediaCrawler Video Workbench 使用文档

本文档面向日常使用，按“启动服务、配置账号、搜索候选、下载总结、查看结果、CLI 调用”的顺序说明。项目根目录以下命令默认在：

```text
E:\大三下\北深实习\MediaCrawler_video
```

## 1. 启动前检查

### 1.1 基础环境

需要准备：

- Python 3.11
- uv
- Node.js 16+
- Chrome 或 Playwright 浏览器
- ffmpeg：启用 Whisper 或本地 Ollama 抽帧时需要
- 可选 CUDA 版 PyTorch：本地 Whisper GPU 转录需要

安装依赖：

```shell
uv sync

cd webui
npm install
cd ..
```

如果使用标准 Playwright 浏览器模式：

```shell
uv run playwright install
```

### 1.2 启动后端和前端

后端固定使用 8080：

```shell
uv run python -m uvicorn api.main:app --host 127.0.0.1 --port 8080
```

前端固定使用 5173：

```shell
cd webui
npm run dev -- --host 127.0.0.1 --port 5173
```

打开：

```text
http://127.0.0.1:5173/
```

健康检查：

```text
http://127.0.0.1:8080/api/health
```

长视频任务运行时不要给后端加 `--reload`。任务状态会写入 `data/video_tasks/<task_id>/task_state.json`，可用于失败后续跑，但 reload 会中断正在进行的下载、转录、上传或模型请求。

## 2. 首次配置

进入 WebUI 右上角“设置”。

### 2.1 平台登录信息

平台登录信息用于搜索、作者页、详情页和下载链路。推荐每个平台保存一套 Cookie 档案。

常用方式：

1. 在浏览器打开目标平台并确认已经登录。
2. 打开开发者工具。
3. 在 Application/Storage/Cookies 中复制 Cookie 表格，或在 Network 请求中复制 Cookie header。
4. 回到 WebUI 设置页，进入“平台登录信息”。
5. 新建或更新对应平台档案。
6. 点击“自测”或“检测登录”，确认当前档案能被任务使用。

扫码登录也可以使用。扫码完成后，后端会保存 Cookie 和浏览器 profile 信息。后续任务可以直接选择保存好的登录档案。

建议：

- B 站可以使用用户名搜索作者，也可以直接输入 UID 或空间链接。
- 抖音建议保存登录 Cookie 后使用主页链接或 `sec_user_id`。
- 快手建议保存登录 Cookie 后使用主页链接或 creator ID。
- 小红书建议低频使用，并尽量复用真实浏览器登录态。
- 微博建议保存 Cookie 后按关键词或主页链接检索。

### 2.2 视频分析 API

进入“视频分析 API”，创建或选择一个配置档案。

DashScope/Qwen 云端配置：

| 字段 | 建议 |
| --- | --- |
| 接口类型 | DashScope 官方云端 |
| API Key | 填写 Qwen/DashScope key |
| Base URL | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 模型 | `qwen3.5-omni-plus` 或 `qwen-vl-max` |
| OSS 转存 | 长视频建议开启 |
| 分析后删除 OSS 临时视频 | 建议开启 |

Ollama 本地模型配置：

| 字段 | 建议 |
| --- | --- |
| 接口类型 | Ollama 本地 |
| Base URL | `http://127.0.0.1:11434` |
| 模型 | 选择本地已拉取的视觉模型 |
| API Key | 留空 |

Ollama 当前走抽帧图片分析，不直接把 mp4 当作视频对象交给模型。适合低成本测试，正式结果建议优先使用云端大模型。

### 2.3 基础参数

建议初始参数：

| 参数 | 推荐值 |
| --- | --- |
| 最大并发 | `1` |
| 最小间隔 | `5` 秒 |
| 最大间隔 | `10` 秒 |
| 每 N 条长暂停 | 可开启 |
| 最大抓取上限 | `50` 到 `100` |
| 筛选后数量 | `3` 到 `5` |
| 评论抓取 | 关闭 |
| Whisper | 需要音频内容时再开启 |

`最大抓取上限` 和 `筛选后数量` 的关系：

- `最大抓取上限` 是平台侧最多抓多少条原始记录。
- `筛选后数量` 是按日期、视频类型等条件过滤后最多保留多少个候选。
- 搜索和作者任务会边抓边筛，筛够数量就提前停止。

## 3. 搜索并返回候选视频

### 3.1 按关键词搜索

1. 打开“搜索”页。
2. 选择平台。
3. 搜索方式选择“标题/关键词”。
4. 输入关键词，例如：

```text
上海交通大学计算机夏令营
```

5. 设置日期范围、筛选后数量和最大抓取上限。
6. 点击“检索候选”。
7. 等候候选视频列表返回。

候选列表会尽量显示：

- 标题
- 作者
- 发布时间
- 封面
- 播放量、点赞数、评论数
- 时长
- 视频大小
- 当前状态

平台没有返回的字段会留空或显示占位值，不影响后续勾选。

### 3.2 按作者检索

1. 打开“搜索”页。
2. 搜索方式选择“作者”。
3. 输入作者信息。

B 站可以输入作者名。若存在重名作者，界面会先返回候选作者卡片，包含头像、UID、粉丝数、视频数和主页链接。选择具体作者后，再加载该作者的视频。

其他常用平台建议输入主页链接或平台 creator ID。这样更稳定，也能减少误匹配。

### 3.3 排行榜与热搜词

打开“排行榜”页，选择平台和榜单类型。

推荐用法：

- B 站：选择热门、分区榜、每周榜，直接获取视频候选。
- 抖音、微博：先读取热搜词，再点击词条进行关键词视频检索。
- 快手：读取热榜候选后再勾选下载或总结。

## 4. 勾选、下载和总结

候选返回后，不会自动下载全部结果。需要先勾选视频，再选择任务动作。

### 4.1 只下载

适合先确认视频文件是否能成功获取。

流程：

1. 在候选列表中勾选视频。
2. 点击下载。
3. 查看进度条和系统控制台。
4. 下载完成后，文件会保存在任务目录下。

下载过程中会显示：

- 当前视频
- 已下载大小
- 总大小
- 下载速度
- 百分比
- 子任务耗时

### 4.2 下载并总结

适合直接生成视频内容报告。

流程：

1. 勾选一个或多个候选视频。
2. 点击下载并总结。
3. 后端按配置执行下载、OSS、Whisper、模型分析。
4. 在结果区查看单视频摘要和整体汇总。

建议先从 1 个短视频开始测试，确认登录、下载、模型和 OSS 都可用后，再扩大到多个视频。

## 5. 视频理解配置建议

### 5.1 默认推荐

普通视频：

- Provider：DashScope
- 模型：`qwen3.5-omni-plus`
- 上传后端：`auto`
- Whisper：关闭
- OSS：长视频开启

解说、访谈、游戏讲解、电影解说：

- Provider：DashScope
- 模型：`qwen3.5-omni-plus` 或 `qwen-vl-max`
- Whisper：开启
- OSS：视频较大时开启

本地快速测试：

- Provider：Ollama
- 模型：本地视觉模型
- Whisper：按需要开启
- 分析方式：抽帧图片 + 文本上下文

### 5.2 Whisper

Whisper 用于从视频音频中提取文本。启用后会增加处理时间，但对口播、解说类视频帮助明显。

转录文件保存到：

```text
data/video_tasks/<task_id>/transcripts/
```

### 5.3 OSS

OSS 用于把本地视频或源站视频流临时转存成模型可访问的签名 URL。建议：

- 长视频开启 OSS。
- 保持“分析结束后删除 OSS 临时视频”开启。
- Bucket 权限保持私有，通过签名 URL 访问。
- 签名有效期可设为 7200 秒。

## 6. 查看结果

每个任务会在本地生成目录：

```text
data/video_tasks/<task_id>/
```

常用文件：

| 文件/目录 | 内容 |
| --- | --- |
| `task_state.json` | 任务状态、日志、候选、子任务进度，可用于续跑。 |
| `result.json` | 最终结果、单视频摘要、整体汇总。 |
| `raw/` | 平台原始元数据和下载文件。 |
| `transcripts/` | Whisper 转录文本。 |

WebUI 里可以直接查看 Markdown 结果和 Mermaid mindmap。

## 7. 续跑与停止

### 7.1 停止任务

在 WebUI 点击停止，或用 CLI：

```shell
uv run python tools/video_summary_cli.py tasks stop <task_id>
```

停止后，已保存的候选、下载文件和摘要会保留在任务目录。

### 7.2 续跑任务

WebUI 会在可恢复任务旁显示“继续”。也可以用 CLI：

```shell
uv run python tools/video_summary_cli.py tasks resume <task_id>
```

续跑会尽量复用：

- 已下载视频
- 已完成摘要
- 已保存候选
- 已写入的任务状态

## 8. CLI 常用命令

CLI 调用本地后端 API，所以需要先启动后端。

### 8.1 作者解析

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

### 8.2 关键词只取候选

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode search ^
  --query "上海交通大学计算机夏令营" ^
  --workflow-mode metadata_only ^
  --max-crawl-items 100 ^
  --max-videos 5 ^
  --credential-profile-id <profile_id> ^
  --login-type cookie ^
  --headless ^
  --crawl-min-sleep-seconds 5 ^
  --crawl-max-sleep-seconds 10
```

### 8.3 作者视频只取候选

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode creator ^
  --creator-id <creator_uid> ^
  --creator-name "<creator_name>" ^
  --workflow-mode metadata_only ^
  --start-date 2026-08-14 ^
  --end-date 2026-08-14 ^
  --max-crawl-items 100 ^
  --max-videos 5 ^
  --credential-profile-id <profile_id> ^
  --login-type cookie ^
  --headless
```

### 8.4 对已勾选候选下载并总结

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode search ^
  --workflow-mode selected_items ^
  --source-task-id <metadata_task_id> ^
  --selected-item-id <video_id_or_bvid> ^
  --credential-profile-id <profile_id> ^
  --login-type cookie ^
  --headless ^
  --summarize
```

### 8.5 查看任务

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
```

### 8.6 平台 Cookie 档案

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials health <credential_profile_id>
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
```

### 8.7 视频分析 API 档案

```shell
uv run python tools/video_summary_cli.py qwen list
uv run python tools/video_summary_cli.py qwen create --name "dashscope-main" --api-key-file .\qwen.key.txt --model qwen3.5-omni-plus
uv run python tools/video_summary_cli.py qwen activate <qwen_profile_id>
```

## 9. 推荐使用顺序

第一次使用建议按下面顺序走：

1. 启动后端和前端。
2. 在设置页保存 B 站 Cookie。
3. 配置 DashScope/Qwen API。
4. 用 B 站关键词搜索 3 到 5 个候选。
5. 勾选 1 个短视频下载并总结。
6. 确认结果可用后，再配置其他平台 Cookie。
7. 每个平台先跑 metadata-only，再勾选下载总结。
8. 长视频开启 OSS，口播视频再开启 Whisper。

## 10. 常见处理

### 10.1 搜索没有候选

检查：

- 平台 Cookie 是否过期。
- 日期范围是否太窄。
- `最大抓取上限` 是否太小。
- 关键词是否过于精确。
- 是否开启了过长的抓取间隔。

### 10.2 下载慢

常见原因：

- 源站视频直链限速。
- 视频文件较大。
- 网络波动。
- Range 续传正在重试。

处理建议：

- 先只下载 1 个视频测试。
- 观察下载进度条中的速度和总大小。
- 对长视频开启 OSS，但仍需先确认源站访问稳定。

### 10.3 总结质量不够

可以尝试：

- 使用更大的云端模型。
- 开启 Whisper。
- 增加抽帧数量。
- 确认下载的视频是目标视频。
- 查看 `transcripts/` 中的转录质量。

### 10.4 OSS 空间占用

保持“分析结束后删除 OSS 临时视频”开启。任务完成后，后端会清理本次分析上传的临时对象。

## 11. 文件位置速查

| 路径 | 用途 |
| --- | --- |
| `README.md` | 项目概览。 |
| `USER_GUIDE.md` | 使用步骤。 |
| `TECHNICAL_REPORT.md` | 技术实现、测试和性能评估。 |
| `api/services/video_summary_manager.py` | 视频任务主编排。 |
| `webui/src/components/video/VideoWorkspace.tsx` | 当前视频工作台前端。 |
| `tools/video_summary_cli.py` | CLI 入口。 |
| `data/video_tasks/` | 本地任务数据。 |
