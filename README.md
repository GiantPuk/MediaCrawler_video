# 🔥 MediaCrawler - 自媒体平台爬虫 🕷️

<div align="center">

### 🤝 特别感谢白金赞助商

<a href="https://www.browseract.ai/mediacrawler" target="_blank">
  <img src="docs/static/images/browseract_ad.jpg" alt="BrowserAct" width="600">
</a>

<br>

<a href="https://www.browseract.ai/mediacrawler" target="_blank">
<small>BrowserAct 支持从任意网站提取数据。只需描述所需数据，BrowserAct 就会在真实浏览器中探索并测试网页，生成可靠、可复用的数据采集 Bot，并返回结构化结果。内置隐身浏览和验证码处理，并提供高质量住宅代理。无需代码，立即免费试用。</small>
</a>

</div>

---

<div align="center">

<a href="https://trendshift.io/repositories/8291" target="_blank">
  <img src="https://trendshift.io/api/badge/repositories/8291" alt="NanmiCoder%2FMediaCrawler | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/>
</a>

[![GitHub Stars](https://img.shields.io/github/stars/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/NanmiCoder/MediaCrawler?style=social)](https://github.com/NanmiCoder/MediaCrawler/network/members)
[![GitHub Issues](https://img.shields.io/github/issues/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/issues)
[![GitHub Pull Requests](https://img.shields.io/github/issues-pr/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/pulls)
[![License](https://img.shields.io/github/license/NanmiCoder/MediaCrawler)](https://github.com/NanmiCoder/MediaCrawler/blob/main/LICENSE)
[![中文](https://img.shields.io/badge/🇨🇳_中文-当前-blue)](README.md)
[![English](https://img.shields.io/badge/🇺🇸_English-Available-green)](README_en.md)
[![Español](https://img.shields.io/badge/🇪🇸_Español-Available-green)](README_es.md)
</div>



> **免责声明：**
> 
> 大家请以学习为目的使用本仓库⚠️⚠️⚠️⚠️，[爬虫违法违规的案件](https://github.com/HiddenStrawberry/Crawler_Illegal_Cases_In_China)  <br>
>
>本仓库的所有内容仅供学习和参考之用，禁止用于商业用途。任何人或组织不得将本仓库的内容用于非法用途或侵犯他人合法权益。本仓库所涉及的爬虫技术仅用于学习和研究，不得用于对其他平台进行大规模爬虫或其他非法行为。对于因使用本仓库内容而引起的任何法律责任，本仓库不承担任何责任。使用本仓库的内容即表示您同意本免责声明的所有条款和条件。
>
> 点击查看更为详细的免责声明。[点击跳转](#disclaimer)




## 📖 项目简介

一个功能强大的**多平台自媒体数据采集工具**，支持小红书、抖音、快手、B站、微博、贴吧、知乎等主流平台的公开信息抓取。

### 🔧 技术原理

- **核心技术**：基于 [Playwright](https://playwright.dev/) 浏览器自动化框架登录保存登录态
- **无需JS逆向**：利用保留登录态的浏览器上下文环境，通过 JS 表达式获取签名参数
- **优势特点**：无需逆向复杂的加密算法，大幅降低技术门槛


## ✨ 功能特性
| 平台   | 关键词搜索 | 指定帖子ID爬取 | 二级评论 | 指定创作者主页 | 登录态缓存 | IP代理池 | 生成评论词云图 |
| ------ | ---------- | -------------- | -------- | -------------- | ---------- | -------- | -------------- |
| 小红书 | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| 抖音   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| 快手   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| B 站   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| 微博   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| 贴吧   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |
| 知乎   | ✅          | ✅              | ✅        | ✅              | ✅          | ✅        | ✅              |



<strong>MediaCrawlerPro 重磅发布！开源不易，欢迎订阅支持</strong>

> 专注于学习成熟项目的架构设计，不仅仅是爬虫技术，Pro 版本的代码设计思路同样值得深入学习！

[MediaCrawlerPro](https://github.com/MediaCrawlerPro) 相较于开源版本的核心优势：

#### 🎯 核心功能升级
- ✅ **自媒体内容拆解Agent**（新增功能）
- ✅ **断点续爬功能**（重点特性）
- ✅ **多账号 + IP代理池支持**（重点特性）
- ✅ **去除 Playwright 依赖**，使用更简单
- ✅ **完整 Linux 环境支持**

#### 🏗️ 架构设计优化
- ✅ **代码重构优化**，更易读易维护（解耦 JS 签名逻辑）
- ✅ **企业级代码质量**，适合构建大型爬虫项目
- ✅ **完美架构设计**，高扩展性，源码学习价值更大

#### 🎁 额外功能
- ✅ **自媒体视频下载器桌面端**（适合学习全栈开发）
- ✅ **多平台首页信息流推荐**（HomeFeed）
- ✅ **AI Agent Skill 支持**（[OpenClaw](https://openclaw.ai/) 🦞 / Claude Code / Cursor 一键安装，让 Agent 自动爬取数据）
- [ ] **基于评论分析AI Agent正在开发中 🚀🚀**

点击查看：[MediaCrawlerPro 项目主页](https://github.com/MediaCrawlerPro) 更多介绍



## 🚀 快速开始

> 💡 **如果这个项目对您有帮助，请给个 ⭐ Star 支持一下！**

## 📋 前置依赖

### 🚀 uv 安装（推荐）

在进行下一步操作之前，请确保电脑上已经安装了 uv：

- **安装地址**：[uv 官方安装指南](https://docs.astral.sh/uv/getting-started/installation)
- **验证安装**：终端输入命令 `uv --version`，如果正常显示版本号，证明已经安装成功
- **推荐理由**：uv 是目前最强的 Python 包管理工具，速度快、依赖解析准确

### 🟢 Node.js 安装

项目依赖 Node.js，请前往官网下载安装：

- **下载地址**：https://nodejs.org/en/download/
- **版本要求**：>= 16.0.0

### 📦 Python 包安装

```shell
# 进入项目目录
cd MediaCrawler

# 使用 uv sync 命令来保证 python 版本和相关依赖包的一致性
uv sync
```

### 🌐 浏览器驱动安装（可选）

> 如果使用默认的 CDP 模式（连接已有 Chrome 浏览器），**无需安装浏览器驱动**。仅在使用标准 Playwright 模式时需要安装。

```shell
# 仅在标准 Playwright 模式下需要安装浏览器驱动
uv run playwright install
```

### 🌍 Chrome 浏览器配置（推荐）

项目默认使用 CDP 模式连接用户已有的 Chrome 浏览器，可以复用浏览器已有的登录状态、Cookie、扩展等，**大幅降低平台风控检测风险**。

使用前需要：

1. **安装最新版 Chrome 浏览器**（版本 >= 144），[下载地址](https://www.google.com/chrome/)
2. **开启远程调试功能**：在 Chrome 地址栏输入 `chrome://inspect/#remote-debugging`，勾选 **"Allow remote debugging for this browser instance"**
3. 页面显示 `Server running at: 127.0.0.1:9222` 表示已就绪

> 💡 **提示**：运行爬虫后，Chrome 浏览器会弹出确认对话框，点击"接受"即可。程序会等待用户确认，60秒内操作完成即可。
>
> 如果不想使用 CDP 模式，可以在 `config/base_config.py` 中设置 `ENABLE_CDP_MODE = False` 切换为标准 Playwright 模式。

## 🚀 运行爬虫程序

```shell
# 在 config/base_config.py 查看配置项目功能，写的有中文注释

# 从配置文件中读取关键词搜索相关的帖子并爬取帖子信息与评论
uv run main.py --platform xhs --lt qrcode --type search

# 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
uv run main.py --platform xhs --lt qrcode --type detail

# 打开对应APP扫二维码登录

# 其他平台爬虫使用示例，执行下面的命令查看
uv run main.py --help
```

<details>
<summary>🖥️ <strong>WebUI 可视化操作界面</strong></summary>

MediaCrawler 提供了基于 Web 的可视化操作界面，无需命令行也能轻松使用爬虫功能。

#### 开发调试（推荐）

开发时需要同时启动后端 API 服务和前端 Vite 开发服务器：

```shell
# 终端 1：启动 API 服务器（默认端口 8080）
uv run uvicorn api.main:app --port 8080 --reload

# 终端 2：启动前端开发服务器
cd webui
npm install
npm run dev        # 默认在 5173 端口启动，并代理 /api 到 8080
```

启动成功后，访问 `http://localhost:5173/` 即可打开 WebUI 界面。

> 首次打开会进行环境检测（调用 `/api/env/check`），请确保后端服务已启动。如果检测失败，可点击「跳过检测」临时跳过。

#### 构建生产资源

如果希望通过 API 服务器直接提供 WebUI 静态资源，需要先构建前端：

```shell
cd webui
npm install
npm run build      # 产物输出到 api/webui/
```

构建完成后，只需启动 API 服务器：

```shell
uv run uvicorn api.main:app --port 8080 --reload
```

然后访问 `http://localhost:8080` 即可。

#### WebUI 功能特性

- 可视化配置爬虫参数（平台、登录方式、爬取类型等）
- 实时查看爬虫运行状态和日志
- 数据预览和导出

#### 界面预览

<img src="docs/static/images/img_8.png" alt="WebUI 界面预览">

</details>

### 视频工作台与命令行调用

本分支新增了视频检索、候选勾选、下载、Qwen-VL 总结归纳和配置管理能力。前端和命令行都复用同一个后端 API，不维护两套逻辑。

#### 启动前后端

```shell
# 终端 1：启动后端 API
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload

# 终端 2：启动前端
cd webui
npm install
npm run dev
```

访问 `http://localhost:5173/` 打开 WebUI。若执行 `npm run build`，后端也可以直接在 `http://localhost:8080` 提供构建后的静态页面。

长时间跑视频下载/总结时建议后端不带 `--reload` 启动，避免代码变更触发 reload 后丢失内存中的实时任务状态：

```shell
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080
```

视频任务勾选“无头模式”时，后端会传入 `--headless true --enable_cdp_mode false --cdp_connect_existing false`，即不等待本机 Chrome 的 CDP 确认，改用标准 Playwright 无头浏览器。若需要复用已打开 Chrome 的反检测环境，请关闭无头模式并使用 CDP。

#### 前端视频工作流

- 标题/关键词搜索：选择平台和“标题/关键词”，输入关键词，点击“检索候选”，返回候选视频后勾选下载或下载并分析。
- 作者搜索：选择“作者”，输入作者名、主页链接或 creator ID，先点击“搜索作者”。页面会先返回作者候选，包含头像、UID、粉丝数、视频数、认证/简介等真实返回信息。选中具体作者后，再点击“加载视频”或“加载选中作者视频”。
- 重名作者：不会直接抓取多个重名账号；必须在候选作者里选定具体 UID 后才会加载视频。
- 榜单：B 站 `popular` / `ranking`、分区排行榜、`precious` 入站必刷、`weekly` 每周必看返回可勾选的视频候选；B 站 `hot_search` 返回热搜词。快手 `hot` 返回短视频热榜 `photoId` 候选，后续直链下载取决于详情接口是否放行；抖音 `hot_search` / `trending`、微博 `hot_search` / `hot_gov`、知乎 `total` / `zvideo` 返回平台热搜、话题或问题榜单项，界面会提供“搜视频”；贴吧 `hot_topic` 返回热议话题榜，仅展示榜单项。它们都不会被伪装成可下载视频。
- 设置：右上角“设置”管理平台 Cookie 档案和 Qwen/DashScope API 档案。列表默认只显示遮罩值，需要点击“加载明文”才会查看或编辑保存内容。
- OSS 转存上传：在“设置 > 视频分析 API”里启用 OSS 后，下载好的本地视频会先上传到 OSS，再把签名 URL 传给 Qwen。`Auto` 上传后端会优先尝试源 URL 直给 Qwen，再尝试源站流式转存 OSS；失败后继续走已有本地下载、DashScope SDK / Base64 / 抽帧链路。当前默认分析是 `qwen3.5-omni-plus`，默认不启用 Whisper。
- 扫码登录保存：在“设置 > 平台登录信息”选择平台后点击“扫码登录并保存”，后端会直接调用原 MediaCrawler 对应平台的 `login.py` 和持久化 Playwright 浏览器上下文。扫码成功后会保存 Cookie 档案，并记录 `browser_data/<platform>_user_data_dir` 目录；详细状态仍只进入底部系统控制台。

#### 视频任务真实接入状态

| 平台 | 标题/关键词视频搜索 | 作者候选搜索 | 作者视频 | 榜单 | 直接下载 | 总结归纳 |
| --- | --- | --- | --- | --- | --- | --- |
| B 站 | 已接入并实测通过 | 支持用户名候选，返回 UID/头像/粉丝/视频数 | 已接入并实测通过 | `popular` / `ranking` / `ranking_<region>` / `precious` / `weekly` / `hot_search` 已接入并实测通过；`weekly` 通常需要有效 Cookie | 已接入并实测通过 | 已接入并实测通过 |
| 微博 | 保留原项目视频搜索路径；本轮未配置微博 Cookie，未做通过性声明 | 仅可靠支持主页链接或 UID | 依赖有效 Cookie 和原项目能力 | `hot_search` 已接入 `hot_band` 热搜词/话题榜；`hot_gov` 已接入官方热点；榜单项可继续作为关键词检索视频 | 有真实视频直链时可下载，当前未实测 | 有本地视频后可总结 |
| 小红书 | 已用有效 Cookie 实测通过，可返回 `type=video` 候选 | 仅可靠支持主页链接或 creator ID | 依赖有效 Cookie | 未接入；探索页/homefeed 是推荐流，不作为榜单 | 候选可能不含直链；需要走原项目 detail/native 下载链路 | 有本地视频后可总结 |
| 抖音 | 已用有效 Cookie/CDP 或标准模式实测通过，可返回视频候选和播放直链 | 仅可靠支持主页链接或 sec_user_id | 依赖有效 Cookie | `hot_search` / `trending` 已接入热搜词/话题榜；榜单项可继续作为关键词检索视频 | 有真实视频直链时可下载 | 有本地视频后可总结 |
| 快手 | 已用有效 Cookie 实测通过，使用原项目签名搜索接口 | 仅可靠支持主页链接或 creator ID | 依赖有效 Cookie，已同步上游签名 REST profile feed | `hot` 已接入快手 brilliant 短视频热榜 photoId 候选；详情接口可能触发 captcha | 有真实视频直链时可下载，榜单候选若仅有 photoId 会明确标记后续下载不支持 | 有本地视频后可总结 |
| 知乎 | 已用有效 Cookie 实测 `zvideo` 搜索通过；候选常为历史视频，注意日期范围 | 仅可靠支持主页链接或 creator ID | 已接入 zvideo feed，依赖有效 Cookie | `total` / `zvideo` 已接入 hot-lists 榜单；当前平台实际常返回问题卡，榜单项可继续作为关键词检索视频 | 未验证稳定直链下载 | 有本地视频后可总结 |
| 贴吧 | 未接入真实视频搜索/下载流程 | 不适用于视频任务 | 不适用于视频任务 | `hot_topic` 已接入百度贴吧热议话题榜；仅展示榜单项，不进入视频下载 | 未接入 | 未接入 |

#### 命令行调用视频功能

命令行工具调用本地后端 API，所以需要先启动后端：

```shell
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload
```

查看帮助：

```shell
uv run python tools/video_summary_cli.py --help
uv run python tools/video_summary_cli.py tasks start --help
```

作者候选解析：

```shell
uv run python tools/video_summary_cli.py creators resolve --platform bili --query key725
```

按选中的作者 UID 只爬元数据：

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
  --crawl-concurrency 1 ^
  --login-type cookie ^
  --headless ^
  --crawl-min-sleep-seconds 5 ^
  --crawl-max-sleep-seconds 10
```

`--crawl-concurrency` 会真实传给 MediaCrawler 的 `--max_concurrency_num`，取值 1-8。默认 1 最保守；调高会提升详情抓取吞吐，但账号和平台风控风险也会同步上升。

对元数据任务中勾选的视频进行下载并总结：

```shell
uv run python tools/video_summary_cli.py tasks start ^
  --platform bili ^
  --source-mode creator ^
  --workflow-mode selected_items ^
  --source-task-id <metadata_task_id> ^
  --selected-item-id <video_id_or_bvid> ^
  --login-type cookie ^
  --headless ^
  --summarize
```

标题/关键词搜索和平台榜单：

```shell
uv run python tools/video_summary_cli.py tasks ranking-options
uv run python tools/video_summary_cli.py tasks ranking-options --platform bili
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode search --query "上海交通大学计算机夏令营" --workflow-mode metadata_only --credential-profile-id <bili_profile_id> --headless --crawl-min-sleep-seconds 5 --crawl-max-sleep-seconds 10
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type popular --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type ranking_game --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type precious --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type weekly --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <bili_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform ks --source-mode ranking --ranking-type hot --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <ks_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform dy --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <dy_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform wb --source-mode ranking --ranking-type hot_search --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <wb_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform wb --source-mode ranking --ranking-type hot_gov --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <wb_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform tieba --source-mode ranking --ranking-type hot_topic --ranking-limit 5 --workflow-mode metadata_only
uv run python tools/video_summary_cli.py tasks start --platform zhihu --source-mode ranking --ranking-type total --ranking-limit 5 --workflow-mode metadata_only --credential-profile-id <zhihu_profile_id>
uv run python tools/video_summary_cli.py tasks start --platform dy --source-mode search --query "三角洲行动" --workflow-mode metadata_only --credential-profile-id <dy_profile_id> --headless --crawl-min-sleep-seconds 8 --crawl-max-sleep-seconds 15
```

查询、等待和停止任务：

```shell
uv run python tools/video_summary_cli.py tasks status <task_id>
uv run python tools/video_summary_cli.py tasks wait <task_id>
uv run python tools/video_summary_cli.py tasks stop <task_id>
```

平台 Cookie 档案管理：

```shell
uv run python tools/video_summary_cli.py credentials list
uv run python tools/video_summary_cli.py credentials create --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials activate <credential_profile_id>
uv run python tools/video_summary_cli.py credentials show <credential_profile_id>
uv run python tools/video_summary_cli.py credentials update <credential_profile_id> --platform bili --name "bili-main" --cookies-file .\bili.cookie.txt
uv run python tools/video_summary_cli.py credentials delete <credential_profile_id>
```

原 MediaCrawler 扫码登录并保存为平台 Cookie 档案：

```shell
# 启动后端后执行；浏览器由后端进程打开，扫码成功后自动保存 Cookie 和 browser_data 元信息
uv run python tools/video_summary_cli.py credentials qrcode-login --platform bili --name "bili-qrcode"
uv run python tools/video_summary_cli.py credentials qrcode-status <login_task_id>
uv run python tools/video_summary_cli.py credentials qrcode-wait <login_task_id>
```

Qwen/DashScope 配置管理：

```shell
uv run python tools/video_summary_cli.py qwen list
uv run python tools/video_summary_cli.py qwen create --name "dashscope-main" --api-key-file .\qwen.key.txt --model qwen3.5-omni-plus
uv run python tools/video_summary_cli.py qwen activate <qwen_profile_id>
uv run python tools/video_summary_cli.py qwen show <qwen_profile_id>
uv run python tools/video_summary_cli.py qwen update <qwen_profile_id> --name "dashscope-main" --api-key-file .\qwen.key.txt --model qwen3.5-omni-plus
uv run python tools/video_summary_cli.py qwen delete <qwen_profile_id>
```

启用 OSS 转存上传：

```shell
# 建议把密钥放在本地文本文件里，不要直接写进命令历史
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

# 任务侧可以显式使用 OSS，也可以保留 auto 让后端按真实链路自动选择
uv run python tools/video_summary_cli.py tasks start --platform bili --source-mode creator --workflow-mode selected_items --source-task-id <metadata_task_id> --selected-item-id <video_id_or_bvid> --summarize --video-upload-backend oss
```

说明：`--video-upload-backend auto` 的真实顺序是：未有本地视频时先尝试把平台源视频 URL 直接交给 Qwen；如果源 URL 对 Qwen 不公开且 OSS 已启用，则后端会使用平台请求头从源 URL 分块读取并 multipart 上传到 OSS，再把 OSS 签名 URL 交给 Qwen；这些真实链路失败后，才进入本地下载并走 OSS / DashScope SDK / Base64 / 抽帧链路。`oss` 显式模式仍表示“已有本地视频后上传 OSS”，不会伪造未接入平台的下载能力。

测试当前 OSS + Qwen 大视频公网 URL 链路：

```shell
# 使用指定本地视频，上传到 OSS 后分别调用 Qwen-VL 和 Qwen-Omni
uv run python tools/test_qwen_oss_video.py --video data\video_tasks\oss_public_test\vl_large_under20.mp4 --model qwen-vl-max --model qwen3.5-omni-plus

# 不指定 --video 时，会选 data/video_tasks 下最大的 mp4；注意 qwen-vl-max 还受 20 分钟时长限制
uv run python tools/test_qwen_oss_video.py
```

说明：B 站支持作者用户名搜索；其他平台目前只能可靠解析创作者主页链接或平台 creator ID。下载与总结是否可用取决于项目中对应平台已有的真实媒体下载链路，未接入的平台会返回明确的 unsupported 状态。

<details>
<summary>🔗 <strong>使用 Python 原生 venv 管理环境（不推荐）</strong></summary>

#### 创建并激活 Python 虚拟环境

> 如果是爬取抖音和知乎，需要提前安装 nodejs 环境，版本大于等于：`16` 即可

```shell
# 进入项目根目录
cd MediaCrawler

# 创建虚拟环境
# 我的 python 版本是：3.11 requirements.txt 中的库是基于这个版本的
# 如果是其他 python 版本，可能 requirements.txt 中的库不兼容，需自行解决
python -m venv venv

# macOS & Linux 激活虚拟环境
source venv/bin/activate

# Windows 激活虚拟环境
venv\Scripts\activate
```

#### 安装依赖库

```shell
pip install -r requirements.txt
```

#### 安装 playwright 浏览器驱动

```shell
playwright install
```

#### 运行爬虫程序（原生环境）

```shell
# 项目默认是没有开启评论爬取模式，如需评论请在 config/base_config.py 中的 ENABLE_GET_COMMENTS 变量修改
# 一些其他支持项，也可以在 config/base_config.py 查看功能，写的有中文注释

# 从配置文件中读取关键词搜索相关的帖子并爬取帖子信息与评论
python main.py --platform xhs --lt qrcode --type search

# 从配置文件中读取指定的帖子ID列表获取指定帖子的信息与评论信息
python main.py --platform xhs --lt qrcode --type detail

# 打开对应APP扫二维码登录

# 其他平台爬虫使用示例，执行下面的命令查看
python main.py --help
```

</details>


## 💾 数据保存

MediaCrawler 支持多种数据存储方式，包括 CSV、JSON、JSONL、Excel、SQLite 和 MySQL 数据库。

📖 **详细使用说明请查看：[数据存储指南](docs/data_storage_guide.md)**


[🚀 MediaCrawlerPro 重磅发布 🚀！更多的功能，更好的架构设计！开源不易，欢迎订阅支持！](https://github.com/MediaCrawlerPro)


## 💬 交流群组
- **微信交流群**：[点击加入](https://nanmicoder.github.io/MediaCrawler/%E5%BE%AE%E4%BF%A1%E4%BA%A4%E6%B5%81%E7%BE%A4.html)
- **B站账号**：[关注我](https://space.bilibili.com/434377496)，分享AI与爬虫技术知识


## 💰 赞助商展示

<table>
  <thead>
    <tr>
      <th width="220">赞助商</th>
      <th align="left">介绍</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td align="center" valign="middle">
        <a href="https://tikhub.io/?utm_source=github.com/NanmiCoder/MediaCrawler&utm_medium=marketing_social&utm_campaign=retargeting&utm_content=carousel_ad"><img src="docs/static/images/tikhub_banner_zh.png" width="180" alt="TikHub"></a>
      </td>
      <td valign="middle">
        <a href="https://tikhub.io/?utm_source=github.com/NanmiCoder/MediaCrawler&utm_medium=marketing_social&utm_campaign=retargeting&utm_content=carousel_ad">TikHub.io</a> 提供 900+ 高稳定性数据接口，覆盖 TK、DY、XHS、Y2B、Ins、X 等 14+ 海内外主流平台，支持用户、内容、商品、评论等多维度公开数据 API，并配套 4000 万+ 已清洗结构化数据集，使用邀请码 <code>cfzyejV9</code> <a href="https://tikhub.io/?utm_source=github.com/NanmiCoder/MediaCrawler&utm_medium=marketing_social&utm_campaign=retargeting&utm_content=carousel_ad">注册并充值</a>，即可额外获得 $2 赠送额度。
      </td>
    </tr>
    <tr>
      <td align="center" valign="middle">
        <a href="https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=mei%27da%27c%27rmeidacrawler"><img width="160" alt="Atlas Cloud" src="docs/static/images/atlas_cloud_logo_black.png#gh-light-mode-only"><img width="160" alt="Atlas Cloud" src="docs/static/images/atlas_cloud_logo_white.png#gh-dark-mode-only"></a>
      </td>
      <td valign="middle">
        <a href="https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=mei%27da%27c%27rmeidacrawler">Atlas Cloud</a> 是一个全模态 AI 推理平台，让开发者通过统一的 AI API 访问视频生成、图像生成和 LLM API，无需分别维护多个厂商集成，即可调用 300+ 精选模型。Atlas Cloud 最新推出 <a href="https://www.atlascloud.ai/console/coding-plan">coding plan 优惠</a>，为开发者提供更具性价比的 API 访问预算。
      </td>
    </tr>
    <tr>
      <td align="center" valign="middle">
        <a href="https://bloome.im/app?ref=NanmiCoder&utm_medium=github&utm_source=NanmiCoder-MediaCrawler-ivor-202607"><img src="docs/static/images/bloome_logo.png" width="180" alt="Bloome"></a>
      </td>
      <td valign="middle">
        <a href="https://bloome.im/app?ref=NanmiCoder&utm_medium=github&utm_source=NanmiCoder-MediaCrawler-ivor-202607">Bloome</a> 是一个 AI Agent IM 平台——让多个 AI agent（Claude、ChatGPT、DeepSeek 等）和你在同一个对话里像团队成员一样协作，自动分工、互相校对，直接生成表格、文档与可视化看板。零配置、云端运行，网页和手机都能用，还能把配好的 agent 一键分享给团队。👉 <a href="https://bloome.im/app?ref=NanmiCoder&utm_medium=github&utm_source=NanmiCoder-MediaCrawler-ivor-202607">试试 Bloome</a>
      </td>
    </tr>
    <tr>
      <td align="center" valign="middle">
        <a href="https://go.nodemaven.com/MediaCrawler"><img src="docs/static/images/nodemaven_logo.svg" width="180" alt="NodeMaven"></a>
      </td>
      <td valign="middle">
        <a href="https://go.nodemaven.com/MediaCrawler">NodeMaven</a> 提供稳定可靠的高质量代理服务，适用于自动化、网页抓取、SEO 研究和社交媒体管理。服务支持 99.9% 可用性、最长 7 天的粘性会话、IP 质量筛选（所有代理的欺诈评分均低于 97%）、无需 KYC，以及最高 10% 的流量返现。MediaCrawler 用户使用优惠码 <code>CRAWLER35</code> 可享移动和住宅代理 35% 折扣，使用 <code>CRAWLER40</code> 可享 ISP（静态）代理 40% 折扣。👉 <a href="https://go.nodemaven.com/MediaCrawler">访问 NodeMaven</a>
      </td>
    </tr>
  </tbody>
</table>

---

## 🤝 成为赞助者

成为赞助者，可以将您的产品展示在这里，每天获得大量曝光！

**联系方式**：
- 微信：`relakkes`
- 邮箱：`relakkes@gmail.com`
---

## ☕ 请作者喝杯咖啡

如果这个项目对您有帮助，欢迎打赏支持，您的每一份支持都是我持续更新的动力 ❤️

<table>
<tr>
<td align="center" width="33%">
<img src="docs/static/images/wechat_pay.jpeg" width="250" alt="微信赞赏"><br>
<b>微信赞赏</b>
</td>
<td align="center" width="33%">
<img src="docs/static/images/zfb_pay.png" width="250" alt="支付宝"><br>
<b>支付宝</b>
</td>
<td align="center" width="33%">
<a href="https://buymeacoffee.com/relakkes" target="_blank">
<img src="docs/static/images/bmc_button.png" width="250" alt="Buy Me a Coffee">
</a><br>
<b>Buy Me a Coffee</b>
</td>
</tr>
</table>

---

## 📚 其他
- **常见问题**：[MediaCrawler 完整文档](https://nanmicoder.github.io/MediaCrawler/)
- **爬虫入门教程**：[CrawlerTutorial 免费教程](https://github.com/NanmiCoder/CrawlerTutorial)
- **新闻爬虫开源项目**：[NewsCrawlerCollection](https://github.com/NanmiCoder/NewsCrawlerCollection)


## ⭐ Star 趋势图

如果这个项目对您有帮助，请给个 ⭐ Star 支持一下，让更多的人看到 MediaCrawler！

[![Star History Chart](https://api.star-history.com/svg?repos=NanmiCoder/MediaCrawler&type=Date)](https://star-history.com/#NanmiCoder/MediaCrawler&Date)


## 📚 参考

- **小红书签名仓库**：[Cloxl 的 xhs 签名仓库](https://github.com/Cloxl/xhshow)
- **小红书客户端**：[ReaJason 的 xhs 仓库](https://github.com/ReaJason/xhs)
- **短信转发**：[SmsForwarder 参考仓库](https://github.com/pppscn/SmsForwarder)
- **内网穿透工具**：[ngrok 官方文档](https://ngrok.com/docs/)


# 免责声明
<div id="disclaimer"> 

## 1. 项目目的与性质
本项目（以下简称“本项目”）是作为一个技术研究与学习工具而创建的，旨在探索和学习网络数据采集技术。本项目专注于自媒体平台的数据爬取技术研究，旨在提供给学习者和研究者作为技术交流之用。

## 2. 法律合规性声明
本项目开发者（以下简称“开发者”）郑重提醒用户在下载、安装和使用本项目时，严格遵守中华人民共和国相关法律法规，包括但不限于《中华人民共和国网络安全法》、《中华人民共和国反间谍法》等所有适用的国家法律和政策。用户应自行承担一切因使用本项目而可能引起的法律责任。

## 3. 使用目的限制
本项目严禁用于任何非法目的或非学习、非研究的商业行为。本项目不得用于任何形式的非法侵入他人计算机系统，不得用于任何侵犯他人知识产权或其他合法权益的行为。用户应保证其使用本项目的目的纯属个人学习和技术研究，不得用于任何形式的非法活动。

## 4. 免责声明
开发者已尽最大努力确保本项目的正当性及安全性，但不对用户使用本项目可能引起的任何形式的直接或间接损失承担责任。包括但不限于由于使用本项目而导致的任何数据丢失、设备损坏、法律诉讼等。

## 5. 知识产权声明
本项目的知识产权归开发者所有。本项目受到著作权法和国际著作权条约以及其他知识产权法律和条约的保护。用户在遵守本声明及相关法律法规的前提下，可以下载和使用本项目。

## 6. 最终解释权
关于本项目的最终解释权归开发者所有。开发者保留随时更改或更新本免责声明的权利，恕不另行通知。
</div>
