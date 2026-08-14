import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  BarChart3,
  CheckCircle2,
  Copy,
  Download,
  Eye,
  EyeOff,
  FolderOpen,
  KeyRound,
  Loader2,
  Play,
  Plus,
  QrCode,
  Search,
  Settings,
  SlidersHorizontal,
  Square,
  Video,
} from 'lucide-react'
import axios from 'axios'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  videoSummaryApi,
  type CreatorCandidate,
  type PlatformCredential,
  type PlatformCredentialSelfTest,
  type PlatformQrcodeLoginStatus,
  type QwenProfile,
  type QwenSettings,
  type VideoSummaryItem,
  type VideoSummaryTaskPayload,
  type VideoSummaryTaskStatus,
  type VideoTaskStep,
} from '@/lib/api'

type WorkspaceView = 'search' | 'ranking' | 'settings'
type SearchSource = 'search' | 'creator'
type SettingsSection = 'credentials' | 'api' | 'defaults'
type SortKey = 'relevance' | 'published_desc' | 'published_asc' | 'views_desc' | 'likes_desc'

const PLATFORM_OPTIONS = [
  { value: 'xhs', label: '小红书' },
  { value: 'dy', label: '抖音' },
  { value: 'ks', label: '快手' },
  { value: 'bili', label: 'B站' },
  { value: 'wb', label: '微博' },
  { value: 'tieba', label: '贴吧' },
  { value: 'zhihu', label: '知乎' },
]

const RANKING_OPTIONS_BY_PLATFORM: Record<string, Array<{ value: string; label: string; note: string }>> = {
  bili: [
    { value: 'popular', label: 'B站热门', note: '读取 B 站当前热门视频列表。' },
    { value: 'ranking', label: 'B站全站排行榜', note: '读取 B 站全站排行榜。' },
    { value: 'precious', label: 'B站入站必刷', note: '读取 B 站入站必刷视频列表。' },
    { value: 'weekly', label: 'B站每周必看', note: '读取 B 站最新一期每周必看视频列表；该接口通常需要有效 B 站 Cookie。' },
    { value: 'hot_search', label: 'B站热搜榜', note: '读取 B 站热搜词；榜单项可继续作为关键词检索视频。' },
    { value: 'ranking_douga', label: 'B站动画榜', note: '读取 B 站动画分区排行榜。' },
    { value: 'ranking_guochuang', label: 'B站国创榜', note: '读取 B 站国创分区排行榜。' },
    { value: 'ranking_music', label: 'B站音乐榜', note: '读取 B 站音乐分区排行榜。' },
    { value: 'ranking_dance', label: 'B站舞蹈榜', note: '读取 B 站舞蹈分区排行榜。' },
    { value: 'ranking_game', label: 'B站游戏榜', note: '读取 B 站游戏分区排行榜。' },
    { value: 'ranking_knowledge', label: 'B站知识榜', note: '读取 B 站知识分区排行榜。' },
    { value: 'ranking_tech', label: 'B站科技榜', note: '读取 B 站科技分区排行榜。' },
    { value: 'ranking_sports', label: 'B站运动榜', note: '读取 B 站运动分区排行榜。' },
    { value: 'ranking_car', label: 'B站汽车榜', note: '读取 B 站汽车分区排行榜。' },
    { value: 'ranking_life', label: 'B站生活榜', note: '读取 B 站生活分区排行榜。' },
    { value: 'ranking_food', label: 'B站美食榜', note: '读取 B 站美食分区排行榜。' },
    { value: 'ranking_animal', label: 'B站动物圈榜', note: '读取 B 站动物圈分区排行榜。' },
    { value: 'ranking_kichiku', label: 'B站鬼畜榜', note: '读取 B 站鬼畜分区排行榜。' },
    { value: 'ranking_fashion', label: 'B站时尚榜', note: '读取 B 站时尚分区排行榜。' },
    { value: 'ranking_ent', label: 'B站娱乐榜', note: '读取 B 站娱乐分区排行榜。' },
    { value: 'ranking_cinephile', label: 'B站影视榜', note: '读取 B 站影视分区排行榜。' },
    { value: 'ranking_movie', label: 'B站电影榜', note: '读取 B 站电影分区排行榜。' },
    { value: 'ranking_tv', label: 'B站电视剧榜', note: '读取 B 站电视剧分区排行榜。' },
    { value: 'ranking_documentary', label: 'B站纪录片榜', note: '读取 B 站纪录片分区排行榜。' },
  ],
  ks: [
    {
      value: 'hot',
      label: '快手短视频热榜',
      note: '读取快手 brilliant 页面原生短视频热榜 photoId 候选；直链下载仍取决于快手详情接口是否放行。',
    },
  ],
  dy: [
    { value: 'hot_search', label: '抖音热搜榜', note: '读取抖音平台热搜词/话题榜；榜单项可继续作为关键词检索视频。' },
    { value: 'trending', label: '抖音趋势榜', note: '读取抖音趋势话题；榜单项可继续作为关键词检索视频。' },
  ],
  wb: [
    { value: 'hot_search', label: '微博热搜榜', note: '读取微博 hot_band 热搜词/话题榜；榜单项可继续作为关键词检索视频。' },
    { value: 'hot_gov', label: '微博官方热点', note: '读取微博 hot_band 返回的官方热点；榜单项可继续作为关键词检索视频。' },
  ],
  zhihu: [
    { value: 'total', label: '知乎热榜', note: '读取知乎热榜问题/卡片；不是 zvideo 文件，可继续作为关键词检索视频。' },
    { value: 'zvideo', label: '知乎热视频入口', note: '读取知乎 hot-lists/zvideo 入口；当前平台实际常返回问题卡，按榜单项展示。' },
  ],
  tieba: [
    { value: 'hot_topic', label: '贴吧热议榜', note: '读取百度贴吧热议话题榜；该平台未接入视频检索，只展示榜单项。' },
  ],
}

const RANKING_SUPPORT_NOTES: Record<string, string> = {
  xhs: '小红书当前可验证入口是探索/推荐 feed，不是平台视频排行榜。',
}

const WHISPER_MODELS = ['tiny', 'base', 'small', 'medium', 'turbo', 'large-v3']
type QwenApiProvider = QwenSettings['api_provider']
type QwenProviderScope = 'cloud' | 'remote' | 'local'

const QWEN_API_PROVIDER_OPTIONS: Array<{ value: QwenApiProvider; label: string; scope: QwenProviderScope; baseUrl: string; model: string }> = [
  {
    value: 'dashscope',
    label: 'DashScope 官方云端',
    scope: 'cloud',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen3.5-omni-plus',
  },
  {
    value: 'openai_compatible',
    label: 'OpenAI Compatible 远程 API',
    scope: 'remote',
    baseUrl: 'https://api.openai.com/v1',
    model: 'qwen3.5-omni-plus',
  },
  {
    value: 'ollama',
    label: '本地 Ollama',
    scope: 'local',
    baseUrl: 'http://127.0.0.1:11434',
    model: 'qwen2.5vl:3b',
  },
]

const QWEN_MODEL_OPTIONS_BY_PROVIDER: Record<QwenApiProvider, string[]> = {
  dashscope: [
    'qwen-vl-max',
    'qwen-vl-max-latest',
    'qwen-vl-max-2025-04-08',
    'qwen-vl-plus',
    'qwen-vl-plus-0102',
    'qwen3.8-max',
    'qwen3.7-plus',
    'qwen3.7-flash',
    'qwen3.6-plus',
    'qwen3.6-flash',
    'qwen3.5-plus',
    'qwen3.5-flash',
    'qwen3-vl-plus',
    'qwen3-vl-flash',
    'qwen3-vl-235b-a22b-instruct',
    'qwen3-vl-235b-a22b-thinking',
    'qwen3-vl-8b-instruct',
    'qwen3-vl-8b-thinking',
    'qwen3-vl-4b-instruct',
    'qwen2.5-vl-72b-instruct',
    'qwen2.5-vl-32b-instruct',
    'qwen2.5-vl-7b-instruct',
    'qwen3.5-omni-plus',
    'qwen3.5-omni-flash',
    'qwen3-omni-flash',
    'qwen-omni-turbo',
    'qvq-max-latest',
    'qvq-plus-latest',
  ],
  openai_compatible: [
    'qwen-vl-max',
    'qwen-vl-max-latest',
    'qwen-vl-max-2025-04-08',
    'qwen-vl-plus',
    'qwen3.5-omni-plus',
    'qwen3.5-omni-flash',
    'qwen3-omni-flash',
    'qwen-omni-turbo',
    'qwen3.8-max',
    'qwen3.7-plus',
    'qwen3.7-flash',
    'qwen3.6-plus',
    'qwen3.6-flash',
    'qwen3.5-plus',
    'qwen3.5-flash',
    'qwen3-vl-plus',
    'qwen3-vl-flash',
    'qwen3-vl-235b-a22b-instruct',
    'qwen3-vl-235b-a22b-thinking',
    'qwen2.5-vl-72b-instruct',
    'qwen2.5-vl-32b-instruct',
    'qwen2.5-vl-7b-instruct',
  ],
  ollama: [
    'qwen2.5vl:3b',
    'qwen3-vl:8b',
    'qwen2.5vl:7b',
    'llama3.2-vision:11b',
    'llava:7b',
  ],
}

const QWEN_PROVIDER_SHORT_LABELS: Record<QwenApiProvider, string> = {
  dashscope: 'DashScope',
  openai_compatible: '远程 API',
  ollama: '本地 Ollama',
}

type QwenModelOption = {
  value: string
  sources: QwenApiProvider[]
}

const ALL_QWEN_MODEL_OPTIONS: QwenModelOption[] = Object.entries(QWEN_MODEL_OPTIONS_BY_PROVIDER)
  .flatMap(([provider, models]) => models.map((model) => ({ provider: provider as QwenApiProvider, model })))
  .reduce<QwenModelOption[]>((options, item) => {
    const existing = options.find((option) => option.value === item.model)
    if (existing) {
      if (!existing.sources.includes(item.provider)) existing.sources.push(item.provider)
      return options
    }
    options.push({ value: item.model, sources: [item.provider] })
    return options
  }, [])

const ALL_QWEN_MODEL_VALUES = new Set(ALL_QWEN_MODEL_OPTIONS.map((option) => option.value))

function providerScopeLabel(scope: QwenProviderScope): string {
  if (scope === 'local') return '本地'
  if (scope === 'cloud') return '云端'
  return '远程'
}

function scopeBadgeClass(isLocal: boolean): string {
  return isLocal
    ? 'rounded border border-emerald-400/40 bg-emerald-400/10 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300'
    : 'rounded border border-cyber-border-subtle bg-cyber-bg-tertiary px-1.5 py-0.5 text-[10px] text-cyber-text-muted'
}

function modelScopeLabel(option: QwenModelOption): string {
  return option.sources.map((source) => QWEN_PROVIDER_SHORT_LABELS[source]).join(' / ')
}

function modelHasLocalSource(option: QwenModelOption): boolean {
  return option.sources.includes('ollama')
}

function qwenModelOption(value: string): QwenModelOption | undefined {
  return ALL_QWEN_MODEL_OPTIONS.find((option) => option.value === value)
}

function preferredProviderForModel(option: QwenModelOption, currentProvider: QwenApiProvider): QwenApiProvider {
  if (option.sources.includes(currentProvider)) return currentProvider
  if (option.sources.includes('ollama')) return 'ollama'
  if (option.sources.includes('dashscope')) return 'dashscope'
  return option.sources[0] ?? currentProvider
}

const VIEW_METRIC_KEYS = [
  'stat.view',
  'statistics.play_count',
  'statistics.view_count',
  'statistics.video_play_count',
  'statistics.vv_count',
  'statistics.vv',
  'video_play_count',
  'viewd_count',
  'view_count',
  'play_count',
  'views',
  'view',
  'play',
  'vv',
]
const LIKE_METRIC_KEYS = ['stat.like', 'liked_count', 'like_count', 'voteup_count', 'likes', 'like', 'digg_count']
const FAVORITE_METRIC_KEYS = ['stat.favorite', 'video_favorite_count', 'collected_count', 'favorite_count', 'fav_count', 'favorites', 'favorite', 'fav', 'collect_count']
const COMMENT_METRIC_KEYS = ['stat.reply', 'video_comment', 'comment_count', 'comments_count', 'comments', 'comment', 'reply_count']
const DANMAKU_METRIC_KEYS = ['stat.danmaku', 'video_danmaku', 'danmaku_count', 'video_review', 'dm']
const CREATOR_NAME_KEYS = [
  'creator_name',
  'author',
  'nickname',
  'user_name',
  'name',
  'owner.name',
  'owner.uname',
  'user.nickname',
  'user.name',
  'author.nickname',
  'author.name',
]
const DURATION_KEYS = [
  'duration',
  'local_video_duration_seconds',
  'duration_seconds',
  'video_duration_seconds',
  'video_duration',
  'duration_sec',
  'length',
  'video_length',
  'duration_ms',
  'video_duration_ms',
  'video.duration',
  'video.duration_ms',
  'video_info.duration',
  'video_info.duration_ms',
  'photo.duration',
  'photo.duration_ms',
  'media_info.duration',
  'page_info.media_info.duration',
  'aweme_detail.video.duration',
  'aweme_detail.video.duration_ms',
  'note_card.video.duration',
  'note_card.video.duration_ms',
]
const VIDEO_SIZE_KEYS = [
  'video_size_bytes',
  'size_bytes',
  'file_size_bytes',
  'file_size',
  'content_length',
  'total_bytes',
  'video_file_size',
  'video_size',
  'size',
]
const VIDEO_SIZE_MB_KEYS = ['video_size_mb', 'size_mb', 'file_size_mb']

const DEFAULT_TASK_SETTINGS = {
  settingsVersion: 3,
  maxCrawlItems: 100,
  maxVideos: 20,
  crawlConcurrency: 1,
  crawlMinSleepSeconds: 5,
  crawlMaxSleepSeconds: 15,
  crawlLongPauseEvery: 0,
  crawlLongPauseMinSeconds: 30,
  crawlLongPauseMaxSeconds: 90,
  loginType: 'qrcode',
  headless: false,
  videoUploadBackend: 'auto',
  videoFps: 2,
  sampleFrames: 8,
  maxInlineVideoMb: 7,
  maxDashscopeVideoMb: 100,
  dashscopeRetryCount: 3,
  enableVideoCompression: true,
  compressionTargetMb: 64,
  enableWhisperTranscription: false,
  whisperModel: 'turbo',
}

const VIDEO_WORKSPACE_COPY = {
  zh: {
    title: '视频检索与分析工作台',
    subtitle: '真实搜索、候选勾选、下载与视频理解共用同一任务流水线',
    search: '搜索',
    ranking: '排行榜',
    settings: '设置',
    credentials: '平台登录信息',
    api: '视频分析 API',
    defaults: '基础参数',
    apiDesc: '这里管理 Qwen/DashScope 兼容接口配置，任务分析时使用当前默认档案。',
    profile: '配置档案',
    profileName: '档案名',
    apiProvider: '接口类型',
    model: '模型',
    modelName: '模型名称',
    commonModel: '常用模型',
    customModelInput: '手动输入',
    modelHint: '模型下拉展示所有常用候选，并标注来源；实际调用链路由上方接口类型与 Base URL 决定，也可以直接输入服务商实际支持的模型名。',
    localDownloadRoot: '本地下载根目录',
    localDownloadRootDesc: '留空时使用项目默认 data/video_tasks；填写后，新任务会在该目录下按任务 ID 保存下载视频。',
    localDownloadRootPlaceholder: '例如 E:\\视频下载\\MediaCrawler',
    localDownloadRootSaved: '本地下载根目录',
    defaultDownloadRoot: '项目默认目录',
    openDownloadDir: '打开下载目录',
    downloadDir: '下载目录',
    ossUpload: 'OSS 转存上传',
    ossDesc: '启用后，长视频会先上传到 OSS 并用签名 URL 传给模型；未配置完整时自动回到原上传链路。',
    ossCleanup: '分析结束后删除 OSS 临时视频',
    ossCleanupDesc: '适合一次性视频；关闭后 signed URL 过期但对象仍保留在 bucket。',
    ossCleanupStatus: 'OSS 临时对象清理',
    ossCleanupEnabled: '分析后删除',
    ossCleanupDisabled: '保留对象',
    ossAccessKeyId: 'OSS AccessKey ID',
    ossAccessKeySecret: 'OSS AccessKey Secret',
    ossBucket: 'Bucket',
    ossEndpoint: 'Endpoint',
    ossRegion: '地域',
    ossPrefix: '对象前缀',
    ossExpires: '签名 URL 过期秒数',
    clearOssKey: '清空当前档案 OSS AccessKey',
    showOssKey: '显示 OSS Key',
    hideOssKey: '隐藏 OSS Key',
    ossSaved: 'OSS 已启用',
    ossMissing: 'OSS 未启用',
    savedValue: '当前保存值',
    defaultProfile: '默认配置',
    nonDefaultProfile: '非默认配置',
    keySaved: '已保存 Key',
    keyMissing: '未保存 Key',
    keyEmpty: '为空',
    provider: '接口',
    updated: '更新',
    loadSecret: '加载明文',
    copy: '复制',
    selectApiProfileHint: '选择一个 API 档案可查看当前保存摘要；点击“加载明文”后才会把 Key 放入编辑框。',
    clearApiKey: '清空当前档案 API Key',
    save: '保存',
    create: '新增',
    setDefault: '设为默认',
    delete: '删除',
    settingsPath: '保存位置',
    keepExistingKey: '留空保留当前 Key',
    showApiKey: '显示 API Key',
    hideApiKey: '隐藏 API Key',
    subtaskProgress: '子任务进度',
    stepUnit: 'steps',
    elapsed: '耗时',
    downloadAnalysisTask: '下载/分析任务',
    overallSummary: '整体汇总',
    perVideoResults: '分视频结果',
    mindmapRenderFailed: '思维导图渲染失败',
    mindmapRendering: '正在渲染思维导图...',
    openLink: '打开',
    emptyCandidates: '启动检索后，真实候选视频会出现在这里。',
  },
  en: {
    title: 'Video Search & Analysis',
    subtitle: 'Real search, selectable candidates, download, and video understanding share one task pipeline',
    search: 'Search',
    ranking: 'Rankings',
    settings: 'Settings',
    credentials: 'Platform Login',
    api: 'Video Analysis API',
    defaults: 'Base Parameters',
    apiDesc: 'Manage Qwen/DashScope compatible API profiles. Analysis tasks use the current default profile.',
    profile: 'Profile',
    profileName: 'Profile Name',
    apiProvider: 'API Provider',
    model: 'Model',
    modelName: 'Model name',
    commonModel: 'Common models',
    customModelInput: 'Custom input',
    modelHint: 'The model menu shows all common candidates with source tags. The actual request path is controlled by API Provider and Base URL, and you can still type any supported model name.',
    localDownloadRoot: 'Local Download Root',
    localDownloadRootDesc: 'Leave empty to use project data/video_tasks. When set, new tasks save downloaded videos under this root by task ID.',
    localDownloadRootPlaceholder: 'Example: E:\\Videos\\MediaCrawler',
    localDownloadRootSaved: 'Local download root',
    defaultDownloadRoot: 'Project default',
    openDownloadDir: 'Open Download Folder',
    downloadDir: 'Download folder',
    ossUpload: 'OSS Transfer Upload',
    ossDesc: 'When enabled, long videos are uploaded to OSS first and passed to the model as signed URLs. Incomplete config falls back to the existing upload path.',
    ossCleanup: 'Delete OSS temporary videos after analysis',
    ossCleanupDesc: 'Best for one-off videos. When disabled, signed URLs expire but objects remain in the bucket.',
    ossCleanupStatus: 'OSS temporary cleanup',
    ossCleanupEnabled: 'Delete after analysis',
    ossCleanupDisabled: 'Keep objects',
    ossAccessKeyId: 'OSS AccessKey ID',
    ossAccessKeySecret: 'OSS AccessKey Secret',
    ossBucket: 'Bucket',
    ossEndpoint: 'Endpoint',
    ossRegion: 'Region',
    ossPrefix: 'Object prefix',
    ossExpires: 'Signed URL expiry seconds',
    clearOssKey: 'Clear OSS AccessKey for this profile',
    showOssKey: 'Show OSS Key',
    hideOssKey: 'Hide OSS Key',
    ossSaved: 'OSS enabled',
    ossMissing: 'OSS disabled',
    savedValue: 'Saved Values',
    defaultProfile: 'Default profile',
    nonDefaultProfile: 'Non-default profile',
    keySaved: 'Key saved',
    keyMissing: 'No key saved',
    keyEmpty: 'empty',
    provider: 'Provider',
    updated: 'Updated',
    loadSecret: 'Load Secret',
    copy: 'Copy',
    selectApiProfileHint: 'Select an API profile to inspect saved values. Click "Load Secret" to put the key into the editor.',
    clearApiKey: 'Clear API key for this profile',
    save: 'Save',
    create: 'New',
    setDefault: 'Set Default',
    delete: 'Delete',
    settingsPath: 'Saved at',
    keepExistingKey: 'Leave empty to keep the current key',
    showApiKey: 'Show API key',
    hideApiKey: 'Hide API key',
    subtaskProgress: 'Subtask Progress',
    stepUnit: 'steps',
    elapsed: 'Elapsed',
    downloadAnalysisTask: 'Download/Analysis Task',
    overallSummary: 'Overall Summary',
    perVideoResults: 'Per-video Results',
    mindmapRenderFailed: 'Mindmap Render Failed',
    mindmapRendering: 'Rendering mindmap...',
    openLink: 'Open',
    emptyCandidates: 'Start a search and real candidate videos will appear here.',
  },
} as const

type TaskSettings = typeof DEFAULT_TASK_SETTINGS

type VideoWorkspaceCopy = { [Key in keyof typeof VIDEO_WORKSPACE_COPY.zh]: string }

function getVideoWorkspaceCopy(language: string): VideoWorkspaceCopy {
  return language.toLowerCase().startsWith('en') ? VIDEO_WORKSPACE_COPY.en : VIDEO_WORKSPACE_COPY.zh
}

function todayString() {
  return new Date().toLocaleDateString('sv-SE')
}

function extractErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') return JSON.stringify(detail)
    return error.message
  }
  return error instanceof Error ? error.message : String(error)
}

function clampNumber(value: number, min: number, max: number, fallback: number) {
  if (!Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, value))
}

function loadTaskSettings(): TaskSettings {
  try {
    const raw = window.localStorage.getItem('mediacrawler_video_task_settings')
    if (!raw) return DEFAULT_TASK_SETTINGS
    const parsed = JSON.parse(raw)
    const migrated = { ...DEFAULT_TASK_SETTINGS, ...parsed }
    const parsedVersion = parsed.settingsVersion ?? 1
    if (parsedVersion < 2) {
      migrated.enableWhisperTranscription = DEFAULT_TASK_SETTINGS.enableWhisperTranscription
    }
    if (parsedVersion < 3 && typeof parsed.maxCrawlItems !== 'number') {
      migrated.maxCrawlItems = Math.max(DEFAULT_TASK_SETTINGS.maxCrawlItems, Number(parsed.maxVideos) || DEFAULT_TASK_SETTINGS.maxVideos)
    }
    if (parsedVersion < DEFAULT_TASK_SETTINGS.settingsVersion) {
      migrated.settingsVersion = DEFAULT_TASK_SETTINGS.settingsVersion
    }
    if (
      typeof parsed.crawlSleepSeconds === 'number' &&
      typeof parsed.crawlMinSleepSeconds !== 'number'
    ) {
      migrated.crawlMinSleepSeconds = parsed.crawlSleepSeconds
    }
    if (
      typeof parsed.crawlSleepSeconds === 'number' &&
      typeof parsed.crawlMaxSleepSeconds !== 'number'
    ) {
      migrated.crawlMaxSleepSeconds = Math.max(parsed.crawlSleepSeconds, DEFAULT_TASK_SETTINGS.crawlMaxSleepSeconds)
    }
    return migrated
  } catch {
    return DEFAULT_TASK_SETTINGS
  }
}

function saveTaskSettings(settings: TaskSettings) {
  window.localStorage.setItem('mediacrawler_video_task_settings', JSON.stringify(settings))
}

function parseMetricNumber(value: unknown) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string') return null
  const text = value.replace(/,/g, '').trim()
  if (!text) return null
  const unit = text.match(/^(\d+(?:\.\d+)?)\s*([万億亿kKmM])?$/)
  if (!unit) return null
  const base = Number(unit[1])
  if (!Number.isFinite(base)) return null
  const suffix = unit[2]
  if (suffix === '万') return Math.round(base * 10000)
  if (suffix === '亿' || suffix === '億') return Math.round(base * 100000000)
  if (suffix === 'k' || suffix === 'K') return Math.round(base * 1000)
  if (suffix === 'm' || suffix === 'M') return Math.round(base * 1000000)
  return base
}

function rawValue(item: VideoSummaryItem, name: string) {
  const parts = name.split('.')
  let value: unknown = item.raw || {}
  for (const part of parts) {
    if (!value || typeof value !== 'object') return undefined
    value = (value as Record<string, unknown>)[part]
  }
  return value
}

function metricValue(item: VideoSummaryItem, names: string[]) {
  for (const name of names) {
    const value = rawValue(item, name)
    const parsed = parseMetricNumber(value)
    if (parsed !== null) return parsed
  }
  return null
}

function formatNumber(value: number | null) {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString()
}

function firstTextValue(item: VideoSummaryItem, names: string[]) {
  for (const name of names) {
    const value = rawValue(item, name)
    if (typeof value === 'string' && value.trim()) return value.trim()
    if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  }
  return ''
}

function parseDurationSeconds(value: unknown, keyName = '') {
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || value <= 0) return null
    const millisecondKey =
      keyName.includes('duration_ms') ||
      keyName === 'video.duration' ||
      keyName.endsWith('.video.duration') ||
      keyName === 'photo.duration' ||
      keyName.endsWith('.photo.duration') ||
      keyName.endsWith('aweme_detail.video.duration') ||
      keyName.endsWith('note_card.video.duration')
    if (millisecondKey || value > 24 * 60 * 60 * 1000) return value / 1000
    return value
  }
  if (typeof value !== 'string') return null
  const text = value.trim()
  if (!text) return null
  if (/^\d+(?:\.\d+)?$/.test(text)) return parseDurationSeconds(Number(text), keyName)
  if (/^\d{1,2}(?::\d{1,2}){1,2}$/.test(text)) {
    const parts = text.split(':').map((part) => Number(part))
    if (parts.some((part) => !Number.isFinite(part))) return null
    if (parts.length === 2) return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]
  }
  return null
}

function durationSeconds(item: VideoSummaryItem) {
  for (const key of DURATION_KEYS) {
    const parsed = parseDurationSeconds(rawValue(item, key), key.toLowerCase())
    if (parsed !== null) return parsed
  }
  return null
}

function formatDuration(value: number | null) {
  if (value === null || value === undefined) return '未返回'
  const seconds = Math.max(0, Math.round(value))
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const two = (part: number) => String(part).padStart(2, '0')
  return h > 0 ? `${h}:${two(m)}:${two(s)}` : `${m}:${two(s)}`
}

function parseByteSize(value: unknown, keyName = '') {
  if (typeof value === 'number') {
    if (!Number.isFinite(value) || value <= 0) return null
    if (keyName.endsWith('_mb') || keyName.includes('size_mb')) return value * 1024 * 1024
    return value
  }
  if (typeof value !== 'string') return null
  const text = value.replace(/,/g, '').trim()
  if (!text) return null
  const match = text.match(/^(\d+(?:\.\d+)?)\s*(b|kb|kib|mb|mib|gb|gib)?$/i)
  if (!match) return null
  const base = Number(match[1])
  if (!Number.isFinite(base) || base <= 0) return null
  const unit = (match[2] || '').toLowerCase()
  if (unit === 'gb' || unit === 'gib') return base * 1024 * 1024 * 1024
  if (unit === 'mb' || unit === 'mib') return base * 1024 * 1024
  if (unit === 'kb' || unit === 'kib') return base * 1024
  if (keyName.endsWith('_mb') || keyName.includes('size_mb')) return base * 1024 * 1024
  return base
}

function videoSizeBytes(item: VideoSummaryItem) {
  for (const key of VIDEO_SIZE_MB_KEYS) {
    const parsed = parseByteSize(rawValue(item, key), key.toLowerCase())
    if (parsed !== null) return parsed
  }
  for (const key of VIDEO_SIZE_KEYS) {
    const parsed = parseByteSize(rawValue(item, key), key.toLowerCase())
    if (parsed !== null) return parsed
  }
  return null
}

function formatByteSize(value: number | null) {
  if (value === null || value === undefined) return '未返回'
  if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(2)}GB`
  if (value >= 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)}MB`
  if (value >= 1024) return `${(value / 1024).toFixed(1)}KB`
  return `${Math.round(value)}B`
}

function formatElapsedSeconds(value?: number | null) {
  if (value === null || value === undefined) return '-'
  const seconds = Math.max(0, value)
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const minutes = Math.floor(seconds / 60)
  const rest = seconds - minutes * 60
  if (minutes < 60) return `${minutes}m ${rest.toFixed(1)}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m ${rest.toFixed(1)}s`
}

function elapsedBetweenSeconds(start?: string | null, end?: string | null) {
  if (!start) return null
  const startTime = new Date(start).getTime()
  const endTime = end ? new Date(end).getTime() : Date.now()
  if (!Number.isFinite(startTime) || !Number.isFinite(endTime)) return null
  return Math.max(0, (endTime - startTime) / 1000)
}

function formatSpeed(value?: number | null) {
  if (!value || value <= 0) return '-'
  return `${formatByteSize(value)}/s`
}

function taskStepBadgeVariant(status: VideoTaskStep['status']) {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'destructive'
  if (status === 'skipped') return 'warning'
  if (status === 'running') return 'running'
  return 'secondary'
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function normalizeMediaUrl(value: unknown) {
  const raw = String(value || '').trim()
  if (!raw) return ''
  if (raw.startsWith('//')) return `https:${raw}`
  if (/^https?:\/\//i.test(raw)) return raw
  return raw.replace(/^['"]|['"]$/g, '')
}

function firstString(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = record[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function coverUrl(item: VideoSummaryItem) {
  const raw = item.raw || {}
  return normalizeMediaUrl(firstString(raw, ['video_cover_url', 'pic', 'cover', 'cover_url', 'first_frame', 'thumbnail', 'thumbnail_url', 'poster', 'pic_url', 'image']))
}

function creatorAvatarUrl(candidate: CreatorCandidate) {
  return normalizeMediaUrl(candidate.avatar_url || firstString(candidate.raw || {}, ['upic', 'face', 'avatar', 'avatar_url', 'head_url']))
}

function creatorMetric(candidate: CreatorCandidate, field: 'follower_count' | 'video_count', fallbackKeys: string[]) {
  const direct = candidate[field]
  if (typeof direct === 'number') return direct
  return metricValue({ raw: candidate.metrics } as VideoSummaryItem, fallbackKeys)
}

function videoUrl(item: VideoSummaryItem) {
  return item.url || String(item.raw.arcurl || item.raw.video_url || item.raw.share_url || '')
}

function isRankingTopicItem(item: VideoSummaryItem) {
  return ['topic', 'question'].includes(String(item.raw?.ranking_item_type || ''))
}

function rankingSearchKeyword(item: VideoSummaryItem) {
  return String(item.raw?.search_keyword || item.title || '').trim()
}

function rankingVideoSearchSupported(item: VideoSummaryItem) {
  return item.raw?.video_search_supported !== false
}

function TaskStepTimeline({ steps, copy }: { steps: VideoTaskStep[]; copy: VideoWorkspaceCopy }) {
  if (!steps.length) return null
  return (
    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="text-[11px] font-mono font-semibold text-cyber-text-primary">{copy.subtaskProgress}</div>
        <div className="text-[10px] text-cyber-text-muted">{steps.length} {copy.stepUnit}</div>
      </div>
      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
        {steps.map((step) => {
          const percent = step.progress_percent ?? (step.status === 'completed' ? 100 : 0)
          const hasTotal = step.total_bytes !== null && step.total_bytes > 0
          return (
            <div key={step.id} className="rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary/40 p-2">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate text-xs font-medium text-cyber-text-primary">{step.label}</div>
                  <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-cyber-text-muted">
                    <span>{step.phase || '-'}</span>
                    <span>{copy.elapsed} {formatElapsedSeconds(step.duration_seconds)}</span>
                    {step.item_id ? <span>ID {step.item_id}</span> : null}
                  </div>
                </div>
                <Badge variant={taskStepBadgeVariant(step.status)}>{step.status}</Badge>
              </div>
              {(step.status === 'running' || step.progress_percent !== null || hasTotal) ? (
                <div className="mt-2 space-y-1.5">
                  <div className="h-1.5 overflow-hidden rounded-full bg-cyber-bg-tertiary">
                    <div className="h-full bg-cyber-neon-cyan transition-all" style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[10px] text-cyber-text-muted md:grid-cols-3">
                    <span>{hasTotal ? `${formatByteSize(step.transferred_bytes)} / ${formatByteSize(step.total_bytes)}` : formatByteSize(step.transferred_bytes || null)}</span>
                    <span>{step.progress_percent !== null ? `${step.progress_percent.toFixed(1)}%` : '-'}</span>
                    <span>{formatSpeed(step.speed_bps)}</span>
                  </div>
                  {step.message ? (
                    <div className="break-words rounded bg-cyber-bg-tertiary/60 px-2 py-1 text-[10px] leading-4 text-cyber-text-secondary">
                      {step.message}
                    </div>
                  ) : null}
                </div>
              ) : step.message ? (
                <div className="mt-1 break-words rounded bg-cyber-bg-tertiary/60 px-2 py-1 text-[10px] leading-4 text-cyber-text-secondary">{step.message}</div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function normalizeMarkdownContent(value: string) {
  const text = value.trim()
  if (!text || /```mermaid/i.test(text)) return text
  return text.replace(
    /(##\s*(?:\*\*)?思维导图(?:\*\*)?\s*\n)(?!```)(mindmap[\s\S]*)$/m,
    (_match, heading: string, diagram: string) => `${heading}\`\`\`mermaid\n${diagram.trim()}\n\`\`\``,
  )
}

function MermaidDiagram({ chart, copy }: { chart: string; copy: VideoWorkspaceCopy }) {
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const id = `video-summary-mermaid-${Date.now()}-${Math.random().toString(36).slice(2)}`

    async function renderDiagram() {
      setSvg('')
      setError('')
      try {
        const mermaid = (await import('mermaid')).default
        const darkMode = document.documentElement.classList.contains('dark')
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: 'strict',
          theme: darkMode ? 'dark' : 'default',
        })
        const result = await mermaid.render(id, chart)
        if (!cancelled) setSvg(result.svg)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      }
    }

    void renderDiagram()
    return () => {
      cancelled = true
    }
  }, [chart])

  if (svg) {
    return (
      <div
        className="my-3 overflow-auto rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary p-3 [&_svg]:mx-auto [&_svg]:max-w-full"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    )
  }

  if (error) {
    return (
      <div className="my-3 rounded-md border border-cyber-neon-orange/40 bg-cyber-neon-orange/10 p-3">
        <div className="mb-2 text-[11px] font-semibold text-cyber-neon-orange">{copy.mindmapRenderFailed}</div>
        <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words text-[11px] text-cyber-text-secondary">{chart}</pre>
      </div>
    )
  }

  return (
    <div className="my-3 rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary p-3 text-[11px] text-cyber-text-muted">
      {copy.mindmapRendering}
    </div>
  )
}

function createMarkdownComponents(copy: VideoWorkspaceCopy): Components {
  return {
    h1: ({ children }) => <h1 className="mb-3 mt-4 text-base font-bold text-cyber-text-primary first:mt-0">{children}</h1>,
    h2: ({ children }) => <h2 className="mb-2 mt-4 text-sm font-bold text-cyber-neon-cyan first:mt-0">{children}</h2>,
    h3: ({ children }) => <h3 className="mb-1.5 mt-3 text-xs font-bold text-cyber-text-primary">{children}</h3>,
    p: ({ children }) => <p className="mb-2 leading-6 text-cyber-text-primary last:mb-0">{children}</p>,
    ul: ({ children }) => <ul className="mb-3 list-disc space-y-1.5 pl-5 leading-6 text-cyber-text-primary">{children}</ul>,
    ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1.5 pl-5 leading-6 text-cyber-text-primary">{children}</ol>,
    li: ({ children }) => <li className="pl-1">{children}</li>,
    strong: ({ children }) => <strong className="font-bold text-cyber-text-primary">{children}</strong>,
    blockquote: ({ children }) => (
      <blockquote className="my-3 border-l-2 border-cyber-neon-cyan/60 bg-cyber-neon-cyan/10 py-2 pl-3 text-cyber-text-secondary">
        {children}
      </blockquote>
    ),
    table: ({ children }) => <table className="my-3 w-full border-collapse text-left text-[11px]">{children}</table>,
    th: ({ children }) => <th className="border border-cyber-border-subtle bg-cyber-bg-tertiary px-2 py-1 font-semibold text-cyber-text-primary">{children}</th>,
    td: ({ children }) => <td className="border border-cyber-border-subtle px-2 py-1 text-cyber-text-secondary">{children}</td>,
    pre: ({ children }) => <>{children}</>,
    code: ({ className, children, ...props }) => {
      const value = String(children).replace(/\n$/, '')
      const language = /language-(\w+)/.exec(className || '')?.[1]?.toLowerCase()
      if (language === 'mermaid' || (!className && value.trim().startsWith('mindmap'))) {
        return <MermaidDiagram chart={value} copy={copy} />
      }
      if (className) {
        return (
          <pre className="my-3 max-h-72 overflow-auto rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary p-3">
            <code className="whitespace-pre-wrap break-words font-mono text-[11px] text-cyber-text-secondary">{value}</code>
          </pre>
        )
      }
      return (
        <code className="rounded bg-cyber-bg-tertiary px-1 py-0.5 font-mono text-[0.9em] text-cyber-neon-cyan" {...props}>
          {children}
        </code>
      )
    },
  }
}

function MarkdownResult({ content, copy }: { content: string; copy: VideoWorkspaceCopy }) {
  const normalized = useMemo(() => normalizeMarkdownContent(content), [content])
  const components = useMemo(() => createMarkdownComponents(copy), [copy])
  return (
    <div className="video-summary-markdown text-xs leading-relaxed text-cyber-text-primary">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
        {normalized}
      </ReactMarkdown>
    </div>
  )
}

function normalizeCookieInput(value: string) {
  const text = value.trim()
  if (!text) return ''
  try {
    const parsed = JSON.parse(text) as unknown
    const pairs: Array<[string, string]> = []
    const appendArray = (items: unknown[]) => {
      items.forEach((item) => {
        if (!item || typeof item !== 'object') return
        const record = item as Record<string, unknown>
        if (record.name !== undefined && record.value !== undefined) {
          pairs.push([String(record.name), String(record.value)])
        }
      })
    }
    if (Array.isArray(parsed)) appendArray(parsed)
    else if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>
      if (Array.isArray(record.cookies)) appendArray(record.cookies)
      else {
        Object.entries(record).forEach(([name, cookieValue]) => {
          if (['string', 'number', 'boolean'].includes(typeof cookieValue)) {
            pairs.push([name, String(cookieValue)])
          }
        })
      }
    }
    if (pairs.length) return pairs.map(([name, cookieValue]) => `${name.trim()}=${cookieValue.trim()}`).join('; ')
  } catch {
    // Continue with header/table parsing.
  }
  const tablePairs = text
    .split(/\r?\n/)
    .map((line) => line.trim().split('\t').map((part) => part.trim()))
    .filter((columns) => columns.length >= 2 && columns[0].toLowerCase() !== 'name')
    .map((columns) => `${columns[0]}=${columns[1]}`)
  if (tablePairs.length) return tablePairs.join('; ')
  const cookieLine = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => /^cookie\s*:/i.test(line))
  return (cookieLine ? cookieLine.replace(/^cookie\s*:\s*/i, '') : text).trim().replace(/^['"]|['"]$/g, '')
}

export function VideoWorkspace() {
  const { i18n } = useTranslation()
  const uiText = useMemo(() => getVideoWorkspaceCopy(i18n.language), [i18n.language])
  const [view, setView] = useState<WorkspaceView>('search')
  const [platform, setPlatform] = useState('bili')
  const [searchSource, setSearchSource] = useState<SearchSource>('search')
  const [query, setQuery] = useState('')
  const [startDate, setStartDate] = useState(todayString())
  const [endDate, setEndDate] = useState(todayString())
  const [sortKey, setSortKey] = useState<SortKey>('relevance')
  const [rankingType, setRankingType] = useState('popular')
  const [rankingLimit, setRankingLimit] = useState(5)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [creatorCandidates, setCreatorCandidates] = useState<CreatorCandidate[]>([])
  const [creatorResolveMessage, setCreatorResolveMessage] = useState('')
  const [selectedCreator, setSelectedCreator] = useState<CreatorCandidate | null>(null)
  const [resolvingCreators, setResolvingCreators] = useState(false)
  const [taskSettings, setTaskSettings] = useState<TaskSettings>(() => loadTaskSettings())

  const [credentials, setCredentials] = useState<PlatformCredential[]>([])
  const [credentialPath, setCredentialPath] = useState('')
  const [selectedCredentialId, setSelectedCredentialId] = useState('')

  const [qwenSettings, setQwenSettings] = useState<QwenSettings | null>(null)
  const [qwenProfiles, setQwenProfiles] = useState<QwenProfile[]>([])
  const [selectedQwenProfileId, setSelectedQwenProfileId] = useState('')
  const [qwenName, setQwenName] = useState('默认配置')
  const [qwenApiKey, setQwenApiKey] = useState('')
  const [qwenApiProvider, setQwenApiProvider] = useState<QwenApiProvider>('dashscope')
  const [qwenBaseUrl, setQwenBaseUrl] = useState('https://dashscope.aliyuncs.com/compatible-mode/v1')
  const [qwenModel, setQwenModel] = useState('qwen3.5-omni-plus')
  const [qwenLocalDownloadRoot, setQwenLocalDownloadRoot] = useState('')
  const [clearQwenKey, setClearQwenKey] = useState(false)
  const [showQwenApiKey, setShowQwenApiKey] = useState(false)
  const [qwenOssEnabled, setQwenOssEnabled] = useState(false)
  const [qwenOssAccessKeyId, setQwenOssAccessKeyId] = useState('')
  const [qwenOssAccessKeySecret, setQwenOssAccessKeySecret] = useState('')
  const [qwenOssBucket, setQwenOssBucket] = useState('')
  const [qwenOssEndpoint, setQwenOssEndpoint] = useState('')
  const [qwenOssRegion, setQwenOssRegion] = useState('')
  const [qwenOssPrefix, setQwenOssPrefix] = useState('mediacrawler/video-summary')
  const [qwenOssUrlExpiresSeconds, setQwenOssUrlExpiresSeconds] = useState(7200)
  const [qwenOssCleanupAfterAnalysis, setQwenOssCleanupAfterAnalysis] = useState(true)
  const [clearQwenOssKey, setClearQwenOssKey] = useState(false)
  const [showQwenOssKey, setShowQwenOssKey] = useState(false)

  const [settingsSection, setSettingsSection] = useState<SettingsSection>('credentials')
  const [credentialFormPlatform, setCredentialFormPlatform] = useState('bili')
  const [credentialFormId, setCredentialFormId] = useState('')
  const [credentialName, setCredentialName] = useState('默认登录信息')
  const [credentialCookies, setCredentialCookies] = useState('')
  const [clearCredentialCookies, setClearCredentialCookies] = useState(false)
  const [credentialSelfTest, setCredentialSelfTest] = useState<PlatformCredentialSelfTest | null>(null)
  const [selfTestingCredential, setSelfTestingCredential] = useState(false)
  const [qrcodeLoginTaskId, setQrcodeLoginTaskId] = useState('')
  const [qrcodeLoginStatus, setQrcodeLoginStatus] = useState<PlatformQrcodeLoginStatus | null>(null)
  const [startingQrcodeLogin, setStartingQrcodeLogin] = useState(false)

  const [discoveryTaskId, setDiscoveryTaskId] = useState('')
  const [discoveryStatus, setDiscoveryStatus] = useState<VideoSummaryTaskStatus | null>(null)
  const [actionTaskId, setActionTaskId] = useState('')
  const [actionStatus, setActionStatus] = useState<VideoSummaryTaskStatus | null>(null)
  const [startingDiscovery, setStartingDiscovery] = useState(false)
  const [startingAction, setStartingAction] = useState(false)
  const [stopping, setStopping] = useState(false)
  const [resuming, setResuming] = useState(false)

  const platformCredentials = useMemo(
    () => credentials.filter((credential) => credential.platform === platform),
    [credentials, platform],
  )
  const activeCredential = useMemo(
    () => platformCredentials.find((credential) => credential.active) ?? null,
    [platformCredentials],
  )
  const credentialFormProfile = useMemo(
    () => credentials.find((credential) => credential.id === credentialFormId) ?? null,
    [credentials, credentialFormId],
  )
  const selectedQwenProfile = useMemo(
    () => qwenProfiles.find((profile) => profile.id === selectedQwenProfileId) ?? null,
    [qwenProfiles, selectedQwenProfileId],
  )
  const qwenProfileDirty = useMemo(() => {
    if (!selectedQwenProfile) return false
    return (
      selectedQwenProfile.name !== qwenName ||
      selectedQwenProfile.api_provider !== qwenApiProvider ||
      selectedQwenProfile.base_url !== qwenBaseUrl ||
      selectedQwenProfile.model !== qwenModel ||
      (selectedQwenProfile.local_download_root ?? '') !== qwenLocalDownloadRoot ||
      selectedQwenProfile.oss_enabled !== qwenOssEnabled ||
      (selectedQwenProfile.oss_bucket ?? '') !== qwenOssBucket ||
      (selectedQwenProfile.oss_endpoint ?? '') !== qwenOssEndpoint ||
      (selectedQwenProfile.oss_region ?? '') !== qwenOssRegion ||
      (selectedQwenProfile.oss_prefix ?? '') !== qwenOssPrefix ||
      selectedQwenProfile.oss_url_expires_seconds !== qwenOssUrlExpiresSeconds ||
      selectedQwenProfile.oss_cleanup_after_analysis !== qwenOssCleanupAfterAnalysis ||
      Boolean(qwenApiKey.trim()) ||
      Boolean(qwenOssAccessKeyId.trim()) ||
      Boolean(qwenOssAccessKeySecret.trim()) ||
      clearQwenKey ||
      clearQwenOssKey
    )
  }, [
    clearQwenKey,
    clearQwenOssKey,
    qwenApiKey,
    qwenApiProvider,
    qwenBaseUrl,
    qwenLocalDownloadRoot,
    qwenModel,
    qwenName,
    qwenOssAccessKeyId,
    qwenOssAccessKeySecret,
    qwenOssBucket,
    qwenOssCleanupAfterAnalysis,
    qwenOssEnabled,
    qwenOssEndpoint,
    qwenOssPrefix,
    qwenOssRegion,
    qwenOssUrlExpiresSeconds,
    selectedQwenProfile,
  ])
  const candidateItems = discoveryStatus?.result?.items ?? []
  const selectableCandidateItems = useMemo(
    () => candidateItems.filter((item) => !isRankingTopicItem(item)),
    [candidateItems],
  )
  const selectedCount = selectedIds.length
  const currentRankingOptions = RANKING_OPTIONS_BY_PLATFORM[platform] ?? []
  const rankingSupported = currentRankingOptions.length > 0
  const rankingSupportNote = currentRankingOptions[0]?.note || RANKING_SUPPORT_NOTES[platform] || '该平台榜单未真实接入，请切换到搜索页。'
  const qrcodeLoginRunning = qrcodeLoginStatus?.status === 'pending' || qrcodeLoginStatus?.status === 'running'
  const visibleQrcodeLoginStatus = useMemo(() => {
    if (!qrcodeLoginStatus) return null
    if (qrcodeLoginStatus.platform !== credentialFormPlatform) return null
    const statusProfileId = qrcodeLoginStatus.credential?.id ?? qrcodeLoginStatus.profile_id ?? ''
    if (statusProfileId) return credentialFormId === statusProfileId ? qrcodeLoginStatus : null
    if (qrcodeLoginStatus.status !== 'pending' && qrcodeLoginStatus.status !== 'running' && !statusProfileId && credentialFormId) return null
    return qrcodeLoginStatus
  }, [credentialFormId, credentialFormPlatform, qrcodeLoginStatus])

  const sortedItems = useMemo(() => {
    const next = [...candidateItems]
    if (sortKey === 'relevance') return next
    const published = (item: VideoSummaryItem) => new Date(item.published_at || 0).getTime() || 0
    if (sortKey === 'published_desc') next.sort((a, b) => published(b) - published(a))
    if (sortKey === 'published_asc') next.sort((a, b) => published(a) - published(b))
    if (sortKey === 'views_desc') {
      next.sort((a, b) => (metricValue(b, VIEW_METRIC_KEYS) ?? -1) - (metricValue(a, VIEW_METRIC_KEYS) ?? -1))
    }
    if (sortKey === 'likes_desc') {
      next.sort((a, b) => (metricValue(b, LIKE_METRIC_KEYS) ?? -1) - (metricValue(a, LIKE_METRIC_KEYS) ?? -1))
    }
    return next
  }, [candidateItems, sortKey])

  useEffect(() => {
    void refreshSettings()
  }, [])

  useEffect(() => {
    saveTaskSettings(taskSettings)
  }, [taskSettings])

  useEffect(() => {
    if (!currentRankingOptions.length) return
    if (!currentRankingOptions.some((option) => option.value === rankingType)) {
      setRankingType(currentRankingOptions[0].value)
    }
  }, [currentRankingOptions, rankingType])

  useEffect(() => {
    setCreatorCandidates([])
    setCreatorResolveMessage('')
    setSelectedCreator(null)
  }, [platform, searchSource, query])

  useEffect(() => {
    if (!qrcodeLoginStatus || qrcodeLoginRunning) return
    if (qrcodeLoginStatus.platform !== credentialFormPlatform) {
      setQrcodeLoginStatus(null)
      return
    }
    const statusProfileId = qrcodeLoginStatus.credential?.id ?? qrcodeLoginStatus.profile_id ?? ''
    if (statusProfileId && statusProfileId !== credentialFormId) {
      setQrcodeLoginStatus(null)
    }
  }, [credentialFormId, credentialFormPlatform, qrcodeLoginRunning, qrcodeLoginStatus])

  useEffect(() => {
    const active = credentials.find((credential) => credential.platform === platform && credential.active)
    setSelectedCredentialId(active?.id ?? '')
  }, [credentials, platform])

  useEffect(() => {
    if (!discoveryTaskId) return
    let disposed = false
    const refresh = async () => {
      try {
        const { data } = await videoSummaryApi.getTask(discoveryTaskId)
        if (!disposed) setDiscoveryStatus(data)
      } catch (error) {
        if (!disposed) toast.error(`刷新候选任务失败: ${extractErrorMessage(error)}`)
      }
    }
    const timer = window.setInterval(() => void refresh(), 2000)
    void refresh()
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [discoveryTaskId])

  useEffect(() => {
    if (!actionTaskId) return
    let disposed = false
    const refresh = async () => {
      try {
        const { data } = await videoSummaryApi.getTask(actionTaskId)
        if (!disposed) setActionStatus(data)
      } catch (error) {
        if (!disposed) toast.error(`刷新下载/分析任务失败: ${extractErrorMessage(error)}`)
      }
    }
    const timer = window.setInterval(() => void refresh(), 2000)
    void refresh()
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [actionTaskId])

  useEffect(() => {
    if (!qrcodeLoginTaskId) return
    let disposed = false
    const refresh = async () => {
      try {
        const { data } = await videoSummaryApi.getPlatformQrcodeLogin(qrcodeLoginTaskId)
        if (disposed) return
        setQrcodeLoginStatus(data)
        if (data.status === 'completed' || data.status === 'error') {
          setQrcodeLoginTaskId('')
          if (data.status === 'completed') {
            const profileId = data.credential?.id ?? data.profile_id ?? undefined
            await refreshSettings({ credentialProfileId: profileId })
            toast.success('扫码登录信息已保存')
          } else {
            toast.error(`扫码登录失败: ${data.error_message ?? data.progress_message}`)
          }
        }
      } catch (error) {
        if (!disposed) toast.error(`刷新扫码登录状态失败: ${extractErrorMessage(error)}`)
      }
    }
    const timer = window.setInterval(() => void refresh(), 2000)
    void refresh()
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [qrcodeLoginTaskId])

  async function refreshSettings(preferred?: { qwenProfileId?: string; credentialProfileId?: string }) {
    try {
      const [credentialResponse, settingsResponse, profilesResponse] = await Promise.all([
        videoSummaryApi.getPlatformCredentials(),
        videoSummaryApi.getSettings(),
        videoSummaryApi.getProfiles(),
      ])
      setCredentials(credentialResponse.data.profiles)
      setCredentialPath(credentialResponse.data.settings_path)
      setQwenSettings(settingsResponse.data)
      setQwenProfiles(profilesResponse.data.profiles)
      if (preferred?.credentialProfileId && credentialResponse.data.profiles.some((item) => item.id === preferred.credentialProfileId)) {
        setCredentialFormId(preferred.credentialProfileId)
      }
      const nextQwenProfileId = preferred?.qwenProfileId && profilesResponse.data.profiles.some((item) => item.id === preferred.qwenProfileId)
        ? preferred.qwenProfileId
        : settingsResponse.data.profile_id
      setSelectedQwenProfileId(nextQwenProfileId)
      applyQwenProfile(profilesResponse.data.profiles.find((item) => item.id === nextQwenProfileId) ?? settingsResponse.data)
    } catch (error) {
      toast.error(`读取设置失败: ${extractErrorMessage(error)}`)
    }
  }

  function applyQwenProfile(profile: QwenSettings | QwenProfile) {
    setQwenName('profile_name' in profile ? profile.profile_name : profile.name)
    setQwenApiProvider(profile.api_provider)
    setQwenBaseUrl(profile.base_url)
    setQwenModel(profile.model)
    setQwenLocalDownloadRoot(profile.local_download_root ?? '')
    setQwenApiKey('')
    setClearQwenKey(false)
    setShowQwenApiKey(false)
    setQwenOssEnabled(profile.oss_enabled)
    setQwenOssAccessKeyId('')
    setQwenOssAccessKeySecret('')
    setQwenOssBucket(profile.oss_bucket ?? '')
    setQwenOssEndpoint(profile.oss_endpoint ?? '')
    setQwenOssRegion(profile.oss_region ?? '')
    setQwenOssPrefix(profile.oss_prefix || 'mediacrawler/video-summary')
    setQwenOssUrlExpiresSeconds(profile.oss_url_expires_seconds || 7200)
    setQwenOssCleanupAfterAnalysis(profile.oss_cleanup_after_analysis ?? true)
    setClearQwenOssKey(false)
    setShowQwenOssKey(false)
  }

  function updateQwenApiProvider(value: QwenApiProvider, options: { forceBaseUrl?: boolean; preserveModel?: boolean } = {}) {
    const nextOption = QWEN_API_PROVIDER_OPTIONS.find((option) => option.value === value)
    setQwenApiProvider(value)
    if (!nextOption) return
    const knownBaseUrls = new Set(QWEN_API_PROVIDER_OPTIONS.map((option) => option.baseUrl))
    setQwenBaseUrl((current) => (options.forceBaseUrl || knownBaseUrls.has(current.trim().replace(/\/$/, '')) ? nextOption.baseUrl : current))
    if (!options.preserveModel && !qwenModel.trim()) setQwenModel(nextOption.model)
  }

  function syncProviderForSelectedModel(modelName: string) {
    const option = qwenModelOption(modelName)
    if (!option) return
    const nextProvider = preferredProviderForModel(option, qwenApiProvider)
    if (nextProvider !== qwenApiProvider) {
      updateQwenApiProvider(nextProvider, { forceBaseUrl: true, preserveModel: true })
      toast.info(`已根据模型来源切换接口类型：${QWEN_API_PROVIDER_OPTIONS.find((item) => item.value === nextProvider)?.label ?? nextProvider}`)
    }
  }

  function selectKnownQwenModel(modelName: string) {
    setQwenModel(modelName)
    syncProviderForSelectedModel(modelName)
  }

  async function copyToClipboard(value: string, label: string) {
    if (!value) {
      toast.warning(`${label} 还没有保存明文内容`)
      return
    }
    try {
      await navigator.clipboard.writeText(value)
      toast.success(`${label} 已复制`)
    } catch (error) {
      toast.error(`复制 ${label} 失败: ${extractErrorMessage(error)}`)
    }
  }

  async function loadCredentialSecret(profileId = credentialFormId) {
    if (!profileId) {
      toast.warning('请先选择一个登录档案')
      return
    }
    try {
      const { data } = await videoSummaryApi.getPlatformCredentialSecret(profileId)
      setCredentialFormId(data.id)
      setCredentialFormPlatform(data.platform)
      setCredentialName(data.name)
      setCredentialCookies(data.cookies)
      setClearCredentialCookies(false)
      toast.success('Cookie 明文已加载到编辑框')
    } catch (error) {
      toast.error(`读取 Cookie 明文失败: ${extractErrorMessage(error)}`)
    }
  }

  async function copyCredentialSecret(profileId = credentialFormId) {
    if (!profileId) {
      toast.warning('请先选择一个登录档案')
      return
    }
    try {
      const { data } = await videoSummaryApi.getPlatformCredentialSecret(profileId)
      await copyToClipboard(data.cookies, 'Cookie')
    } catch (error) {
      toast.error(`读取 Cookie 明文失败: ${extractErrorMessage(error)}`)
    }
  }

  async function loadQwenSecret(profileId = selectedQwenProfileId) {
    if (!profileId) {
      toast.warning('请先选择一个 API 配置')
      return
    }
    try {
      const { data } = await videoSummaryApi.getProfileSecret(profileId)
      setSelectedQwenProfileId(data.id)
      setQwenName(data.name)
      setQwenApiProvider(data.api_provider)
      setQwenBaseUrl(data.base_url)
      setQwenModel(data.model)
      setQwenLocalDownloadRoot(data.local_download_root ?? '')
      setQwenApiKey(data.api_key)
      setClearQwenKey(false)
      setShowQwenApiKey(true)
      setQwenOssEnabled(data.oss_enabled)
      setQwenOssAccessKeyId(data.oss_access_key_id)
      setQwenOssAccessKeySecret(data.oss_access_key_secret)
      setQwenOssBucket(data.oss_bucket ?? '')
      setQwenOssEndpoint(data.oss_endpoint ?? '')
      setQwenOssRegion(data.oss_region ?? '')
      setQwenOssPrefix(data.oss_prefix || 'mediacrawler/video-summary')
      setQwenOssUrlExpiresSeconds(data.oss_url_expires_seconds || 7200)
      setQwenOssCleanupAfterAnalysis(data.oss_cleanup_after_analysis ?? true)
      setClearQwenOssKey(false)
      setShowQwenOssKey(Boolean(data.oss_access_key_id || data.oss_access_key_secret))
      toast.success('API Key 明文已加载到编辑框')
    } catch (error) {
      toast.error(`读取 API Key 明文失败: ${extractErrorMessage(error)}`)
    }
  }

  async function copyQwenSecret(profileId = selectedQwenProfileId) {
    if (!profileId) {
      toast.warning('请先选择一个 API 配置')
      return
    }
    try {
      const { data } = await videoSummaryApi.getProfileSecret(profileId)
      await copyToClipboard(data.api_key, 'API Key')
    } catch (error) {
      toast.error(`读取 API Key 明文失败: ${extractErrorMessage(error)}`)
    }
  }

  function updateDefaults(update: Partial<TaskSettings>) {
    setTaskSettings((current) => ({ ...current, ...update }))
  }

  function buildTaskPayload(update: Partial<VideoSummaryTaskPayload>): VideoSummaryTaskPayload {
    const credentialId = selectedCredentialId || activeCredential?.id || null
    const crawlMinRaw = clampNumber(taskSettings.crawlMinSleepSeconds, 0, 120, 5)
    const crawlMaxRaw = clampNumber(taskSettings.crawlMaxSleepSeconds, 0, 120, 15)
    const crawlMinSeconds = Math.min(crawlMinRaw, crawlMaxRaw)
    const crawlMaxSeconds = Math.max(crawlMinRaw, crawlMaxRaw)
    const longPauseMinRaw = clampNumber(taskSettings.crawlLongPauseMinSeconds, 0, 3600, 30)
    const longPauseMaxRaw = clampNumber(taskSettings.crawlLongPauseMaxSeconds, 0, 3600, 90)
    const longPauseMinSeconds = Math.min(longPauseMinRaw, longPauseMaxRaw)
    const longPauseMaxSeconds = Math.max(longPauseMinRaw, longPauseMaxRaw)
    const filteredLimit = Math.round(clampNumber(taskSettings.maxVideos, 1, 200, 20))
    const crawlLimit = Math.round(clampNumber(taskSettings.maxCrawlItems, 1, 500, 100))
    return {
      platform,
      creator_id: '',
      credential_profile_id: credentialId,
      workflow_mode: 'metadata_only',
      login_type: credentialId ? 'cookie' : taskSettings.loginType,
      cookies: '',
      start_date: startDate,
      end_date: endDate,
      max_crawl_items: Math.max(crawlLimit, filteredLimit),
      max_videos: filteredLimit,
      crawl_concurrency: Math.round(clampNumber(taskSettings.crawlConcurrency, 1, 8, 1)),
      headless: taskSettings.headless,
      crawl_sleep_seconds: crawlMaxSeconds,
      crawl_min_sleep_seconds: crawlMinSeconds,
      crawl_max_sleep_seconds: crawlMaxSeconds,
      crawl_long_pause_every: Math.round(clampNumber(taskSettings.crawlLongPauseEvery, 0, 1000, 0)),
      crawl_long_pause_min_seconds: longPauseMinSeconds,
      crawl_long_pause_max_seconds: longPauseMaxSeconds,
      summarize: false,
      video_input_mode: 'auto',
      video_upload_backend: taskSettings.videoUploadBackend as 'auto' | 'oss' | 'dashscope' | 'openai',
      video_fps: clampNumber(taskSettings.videoFps, 0.1, 10, 2),
      sample_frames: Math.round(clampNumber(taskSettings.sampleFrames, 1, 24, 8)),
      max_inline_video_mb: 7,
      max_dashscope_video_mb: Math.round(clampNumber(taskSettings.maxDashscopeVideoMb, 1, 100, 100)),
      dashscope_retry_count: Math.round(clampNumber(taskSettings.dashscopeRetryCount, 1, 5, 3)),
      enable_video_compression: taskSettings.enableVideoCompression,
      compression_target_mb: Math.round(clampNumber(taskSettings.compressionTargetMb, 10, 100, 64)),
      enable_whisper_transcription: taskSettings.enableWhisperTranscription,
      whisper_model: taskSettings.whisperModel,
      ...update,
    }
  }

  async function resolveCreatorCandidates() {
    const cleanQuery = query.trim()
    if (!cleanQuery) {
      toast.warning('请输入作者主页、ID 或用户名')
      return
    }
    setResolvingCreators(true)
    setCreatorCandidates([])
    setCreatorResolveMessage('')
    setSelectedCreator(null)
    setDiscoveryTaskId('')
    setDiscoveryStatus(null)
    setSelectedIds([])
    try {
      const { data } = await videoSummaryApi.resolveCreators({ platform, query: cleanQuery })
      setCreatorCandidates(data.candidates)
      setCreatorResolveMessage(data.message)
      if (data.candidates.length) {
        toast.success(`找到 ${data.candidates.length} 个作者候选`)
      } else {
        toast.warning(data.message || '没有找到作者候选')
      }
    } catch (error) {
      toast.error(`搜索作者失败: ${extractErrorMessage(error)}`)
    } finally {
      setResolvingCreators(false)
    }
  }

  async function startCreatorVideoDiscovery(candidate = selectedCreator) {
    if (!candidate) {
      toast.warning('请先选择一个作者候选')
      return
    }
    if (startDate > endDate) {
      toast.warning('开始日期不能晚于结束日期')
      return
    }
    setStartingDiscovery(true)
    setSelectedIds([])
    try {
      const payload = buildTaskPayload({
        source_mode: 'creator',
        creator_id: candidate.id,
        creator_display_name: candidate.display_name,
        profile_url: candidate.profile_url,
        search_keyword: '',
        ranking_type: '',
        workflow_mode: 'metadata_only',
        summarize: false,
      })
      const { data } = await videoSummaryApi.startTask(payload)
      setSelectedCreator(candidate)
      setDiscoveryTaskId(data.task_id)
      setDiscoveryStatus(data)
      toast.success(`开始加载 ${candidate.display_name} 的视频`)
    } catch (error) {
      toast.error(`加载作者视频失败: ${extractErrorMessage(error)}`)
    } finally {
      setStartingDiscovery(false)
    }
  }

  async function startDiscovery() {
    if (view === 'ranking' && !rankingSupported) {
      toast.warning(rankingSupportNote)
      return
    }
    if (view === 'search' && !query.trim()) {
      toast.warning(searchSource === 'creator' ? '请输入作者主页/ID/用户名' : '请输入关键词或视频标题')
      return
    }
    if (startDate > endDate) {
      toast.warning('开始日期不能晚于结束日期')
      return
    }

    const sourceMode = view === 'ranking' ? 'ranking' : searchSource
    if (sourceMode === 'creator') {
      await resolveCreatorCandidates()
      return
    }
    const cleanRankingLimit = Math.round(clampNumber(rankingLimit, 1, 50, 5))
    setRankingLimit(cleanRankingLimit)
    setStartingDiscovery(true)
    setSelectedIds([])
    try {
      const payload = buildTaskPayload({
        source_mode: sourceMode,
        creator_id: sourceMode === 'search' ? query.trim() : '',
        creator_display_name: sourceMode === 'search' ? `Search: ${query.trim()}` : '',
        search_keyword: sourceMode === 'search' ? query.trim() : '',
        ranking_type: sourceMode === 'ranking' ? rankingType : '',
        ranking_limit: cleanRankingLimit,
        max_crawl_items: Math.max(cleanRankingLimit, taskSettings.maxCrawlItems, taskSettings.maxVideos),
        max_videos: sourceMode === 'ranking' ? Math.max(cleanRankingLimit, taskSettings.maxVideos) : taskSettings.maxVideos,
        workflow_mode: 'metadata_only',
        summarize: false,
      })
      const { data } = await videoSummaryApi.startTask(payload)
      setDiscoveryTaskId(data.task_id)
      setDiscoveryStatus(data)
      toast.success('候选视频检索已启动')
    } catch (error) {
      toast.error(`启动检索失败: ${extractErrorMessage(error)}`)
    } finally {
      setStartingDiscovery(false)
    }
  }

  async function startSearchFromRankingItem(item: VideoSummaryItem) {
    const keyword = rankingSearchKeyword(item)
    if (!rankingVideoSearchSupported(item)) {
      toast.warning(String(item.raw?.detail_note || '该榜单项暂不支持在当前平台继续检索视频'))
      return
    }
    if (!keyword) {
      toast.warning('这个榜单项没有可用于检索的关键词')
      return
    }
    setView('search')
    setSearchSource('search')
    setQuery(keyword)
    setStartingDiscovery(true)
    setSelectedIds([])
    setCreatorCandidates([])
    setSelectedCreator(null)
    try {
      const payload = buildTaskPayload({
        platform: discoveryStatus?.result?.platform || platform,
        source_mode: 'search',
        creator_id: keyword,
        creator_display_name: `Search: ${keyword}`,
        search_keyword: keyword,
        ranking_type: '',
        workflow_mode: 'metadata_only',
        summarize: false,
      })
      const { data } = await videoSummaryApi.startTask(payload)
      setDiscoveryTaskId(data.task_id)
      setDiscoveryStatus(data)
      toast.success(`已按榜单项检索视频：${keyword}`)
    } catch (error) {
      toast.error(`按榜单项检索视频失败: ${extractErrorMessage(error)}`)
    } finally {
      setStartingDiscovery(false)
    }
  }

  async function startSelectedAction(summarize: boolean) {
    const result = discoveryStatus?.result
    if (!result || selectedIds.length === 0) {
      toast.warning('请先勾选至少一个视频')
      return
    }
    setStartingAction(true)
    try {
      const payload = buildTaskPayload({
        platform: result.platform,
        source_mode: result.source_mode,
        creator_id: result.creator_id,
        creator_display_name: result.creator_display_name,
        search_keyword: result.search_keyword,
        ranking_type: result.ranking_type,
        workflow_mode: 'selected_items',
        source_task_id: result.task_id,
        selected_item_ids: selectedIds,
        summarize,
      })
      const { data } = await videoSummaryApi.startTask(payload)
      setActionTaskId(data.task_id)
      setActionStatus(data)
      toast.success(summarize ? '下载并分析任务已启动' : '下载任务已启动')
    } catch (error) {
      toast.error(`启动下载/分析失败: ${extractErrorMessage(error)}`)
    } finally {
      setStartingAction(false)
    }
  }

  async function stopActiveTask() {
    const taskId = actionTaskId || discoveryTaskId
    if (!taskId) return
    setStopping(true)
    try {
      await videoSummaryApi.stopTask(taskId)
      toast.success('任务已停止')
    } catch (error) {
      toast.error(`停止任务失败: ${extractErrorMessage(error)}`)
    } finally {
      setStopping(false)
    }
  }

  async function resumeActiveTask() {
    const taskId = actionTaskId || discoveryTaskId
    if (!taskId) return
    setResuming(true)
    try {
      const { data } = await videoSummaryApi.resumeTask(taskId)
      if (taskId === actionTaskId) {
        setActionStatus(data)
      } else {
        setDiscoveryStatus(data)
      }
      toast.success('任务已继续')
    } catch (error) {
      toast.error(`继续任务失败: ${extractErrorMessage(error)}`)
    } finally {
      setResuming(false)
    }
  }

  async function openTaskDownloadDir(taskId = actionTaskId || discoveryTaskId) {
    if (!taskId) {
      toast.warning('还没有可打开的任务目录')
      return
    }
    try {
      const { data } = await videoSummaryApi.openTaskDownloadDir(taskId)
      toast.success(`已请求打开下载目录：${data.path}`)
    } catch (error) {
      toast.error(`打开下载目录失败: ${extractErrorMessage(error)}`)
    }
  }

  function toggleItem(itemId: string, checked: boolean) {
    setSelectedIds((current) => {
      if (checked) return current.includes(itemId) ? current : [...current, itemId]
      return current.filter((id) => id !== itemId)
    })
  }

  async function startQrcodeLogin() {
    setStartingQrcodeLogin(true)
    setQrcodeLoginStatus(null)
    try {
      const { data } = await videoSummaryApi.startPlatformQrcodeLogin({
        platform: credentialFormPlatform,
        name: credentialName.trim() || '扫码登录信息',
        profile_id: credentialFormId || null,
        headless: false,
      })
      setQrcodeLoginTaskId(data.task_id)
      setQrcodeLoginStatus(data)
      toast.success('已打开原 MediaCrawler 扫码登录流程')
    } catch (error) {
      toast.error(`启动扫码登录失败: ${extractErrorMessage(error)}`)
    } finally {
      setStartingQrcodeLogin(false)
    }
  }

  async function saveCredential() {
    const normalized = credentialCookies.trim() ? normalizeCookieInput(credentialCookies) : ''
    if (credentialCookies.trim() && !normalized) {
      toast.warning('没有识别到可用 Cookie')
      return
    }
    try {
      let nextCredentialId = credentialFormId
      if (credentialFormId) {
        const { data } = await videoSummaryApi.updatePlatformCredential(credentialFormId, {
          platform: credentialFormPlatform,
          name: credentialName,
          cookies: normalized || null,
          clear_cookies: clearCredentialCookies,
          login_method: 'cookie',
          metadata: {},
        })
        nextCredentialId = data.id
      } else {
        const { data } = await videoSummaryApi.createPlatformCredential({
          platform: credentialFormPlatform,
          name: credentialName,
          cookies: normalized,
          login_method: 'cookie',
          metadata: {},
        })
        nextCredentialId = data.id
      }
      setCredentialCookies('')
      setClearCredentialCookies(false)
      setCredentialSelfTest(null)
      await refreshSettings({ credentialProfileId: nextCredentialId })
      toast.success('平台登录信息已保存')
    } catch (error) {
      toast.error(`保存登录信息失败: ${extractErrorMessage(error)}`)
    }
  }

  async function deleteCredential() {
    if (!credentialFormId) return
    try {
      await videoSummaryApi.deletePlatformCredential(credentialFormId)
      setCredentialFormId('')
      setCredentialCookies('')
      setCredentialSelfTest(null)
      await refreshSettings()
      toast.success('平台登录信息已删除')
    } catch (error) {
      toast.error(`删除登录信息失败: ${extractErrorMessage(error)}`)
    }
  }

  async function activateCredential(profileId: string) {
    try {
      await videoSummaryApi.activatePlatformCredential(profileId)
      await refreshSettings({ credentialProfileId: profileId })
      toast.success('默认登录信息已切换')
    } catch (error) {
      toast.error(`切换登录信息失败: ${extractErrorMessage(error)}`)
    }
  }

  function selectCredentialForEdit(profile: PlatformCredential) {
    setCredentialFormId(profile.id)
    setCredentialFormPlatform(profile.platform)
    setCredentialName(profile.name)
    setCredentialCookies('')
    setClearCredentialCookies(false)
    setCredentialSelfTest(null)
  }

  function startNewCredentialProfile() {
    setCredentialFormId('')
    setCredentialName('新登录信息')
    setCredentialCookies('')
    setClearCredentialCookies(false)
    setCredentialSelfTest(null)
    setQrcodeLoginTaskId('')
    setQrcodeLoginStatus(null)
  }

  async function selfTestCredential() {
    if (!credentialFormId) return
    setSelfTestingCredential(true)
    setCredentialSelfTest(null)
    try {
      const { data } = await videoSummaryApi.selfTestPlatformCredential(credentialFormId)
      setCredentialSelfTest(data)
      if (data.status === 'ok') {
        toast.success(`平台配置自测通过：${data.total_records} 条原始记录，${data.item_count} 个候选`)
      } else if (data.status === 'warning') {
        toast.warning(data.message)
      } else {
        toast.error(data.message)
      }
    } catch (error) {
      toast.error(`平台配置自测失败: ${extractErrorMessage(error)}`)
    } finally {
      setSelfTestingCredential(false)
    }
  }

  async function saveQwenProfile() {
    try {
      const payload = {
        name: qwenName.trim() || '默认配置',
        api_key: qwenApiKey.trim() || undefined,
        clear_api_key: clearQwenKey,
        api_provider: qwenApiProvider,
        base_url: qwenBaseUrl,
        model: qwenModel,
        local_download_root: qwenLocalDownloadRoot.trim(),
        oss_enabled: qwenOssEnabled,
        oss_access_key_id: qwenOssAccessKeyId.trim() || undefined,
        oss_access_key_secret: qwenOssAccessKeySecret.trim() || undefined,
        clear_oss_access_key: clearQwenOssKey,
        oss_bucket: qwenOssBucket.trim(),
        oss_endpoint: qwenOssEndpoint.trim(),
        oss_region: qwenOssRegion.trim(),
        oss_prefix: qwenOssPrefix.trim(),
        oss_url_expires_seconds: Math.round(clampNumber(qwenOssUrlExpiresSeconds, 300, 604800, 7200)),
        oss_cleanup_after_analysis: qwenOssCleanupAfterAnalysis,
      }
      let nextProfileId = selectedQwenProfileId
      if (selectedQwenProfileId) await videoSummaryApi.updateProfile(selectedQwenProfileId, payload)
      else {
        const { data } = await videoSummaryApi.createProfile(payload)
        nextProfileId = data.id
      }
      await refreshSettings({ qwenProfileId: nextProfileId })
      toast.success('视频分析 API 配置已保存')
    } catch (error) {
      toast.error(`保存 API 配置失败: ${extractErrorMessage(error)}`)
    }
  }

  async function createQwenProfile() {
    try {
      const { data } = await videoSummaryApi.createProfile({
        name: qwenName.trim() ? `${qwenName.trim()} 副本` : '新配置',
        api_key: qwenApiKey.trim() || undefined,
        clear_api_key: false,
        api_provider: qwenApiProvider,
        base_url: qwenBaseUrl,
        model: qwenModel,
        local_download_root: qwenLocalDownloadRoot.trim(),
        oss_enabled: qwenOssEnabled,
        oss_access_key_id: qwenOssAccessKeyId.trim() || undefined,
        oss_access_key_secret: qwenOssAccessKeySecret.trim() || undefined,
        clear_oss_access_key: false,
        oss_bucket: qwenOssBucket.trim(),
        oss_endpoint: qwenOssEndpoint.trim(),
        oss_region: qwenOssRegion.trim(),
        oss_prefix: qwenOssPrefix.trim(),
        oss_url_expires_seconds: Math.round(clampNumber(qwenOssUrlExpiresSeconds, 300, 604800, 7200)),
        oss_cleanup_after_analysis: qwenOssCleanupAfterAnalysis,
      })
      setSelectedQwenProfileId(data.id)
      await refreshSettings({ qwenProfileId: data.id })
      toast.success('视频分析 API 配置已新增')
    } catch (error) {
      toast.error(`新增 API 配置失败: ${extractErrorMessage(error)}`)
    }
  }

  async function activateQwenProfile() {
    if (!selectedQwenProfileId) return
    try {
      await videoSummaryApi.activateProfile(selectedQwenProfileId)
      await refreshSettings({ qwenProfileId: selectedQwenProfileId })
      toast.success('默认视频分析 API 配置已切换')
    } catch (error) {
      toast.error(`切换 API 配置失败: ${extractErrorMessage(error)}`)
    }
  }

  async function deleteQwenProfile() {
    if (!selectedQwenProfileId || qwenProfiles.length <= 1) return
    try {
      await videoSummaryApi.deleteProfile(selectedQwenProfileId)
      await refreshSettings()
      toast.success('视频分析 API 配置已删除')
    } catch (error) {
      toast.error(`删除 API 配置失败: ${extractErrorMessage(error)}`)
    }
  }

  const running = discoveryStatus?.status === 'running' || discoveryStatus?.status === 'pending' || actionStatus?.status === 'running' || actionStatus?.status === 'pending'
  const canResume = !running && ((actionTaskId && actionStatus?.status === 'error') || (discoveryTaskId && discoveryStatus?.status === 'error'))
  const actionDownloadDir = actionStatus?.local_download_dir || actionStatus?.result?.local_download_dir || actionStatus?.result?.output_dir || ''

  return (
    <section className="glass-panel float-panel overflow-hidden animate-slide-up">
      <header className="border-b border-cyber-border-subtle/60 bg-cyber-bg-tertiary/40 px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary flex items-center justify-center">
              <Video className="h-4 w-4 text-cyber-neon-cyan" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-mono font-semibold text-cyber-text-primary">{uiText.title}</div>
              <div className="text-[11px] text-cyber-text-muted">{uiText.subtitle}</div>
            </div>
          </div>
          <nav className="flex items-center gap-1 rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary p-1">
            {[
              ['search', Search, uiText.search] as const,
              ['ranking', BarChart3, uiText.ranking] as const,
              ['settings', Settings, uiText.settings] as const,
            ].map(([value, Icon, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setView(value)}
                className={`h-8 rounded px-3 text-xs font-mono transition-all inline-flex items-center gap-1.5 ${
                  view === value ? 'bg-cyber-neon-cyan text-cyber-bg-primary' : 'text-cyber-text-secondary hover:bg-cyber-bg-tertiary'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {view !== 'settings' ? (
        <div className="space-y-4 p-4">
          <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4">
            <div className="grid grid-cols-1 lg:grid-cols-[140px_150px_1fr_140px] gap-3">
              <Select value={platform} onValueChange={setPlatform} disabled={running}>
                <SelectTrigger className="h-10 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PLATFORM_OPTIONS.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}
                </SelectContent>
              </Select>

              {view === 'search' ? (
                <Select value={searchSource} onValueChange={(value) => setSearchSource(value as SearchSource)} disabled={running}>
                  <SelectTrigger className="h-10 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="search">标题/关键词</SelectItem>
                    <SelectItem value="creator">作者</SelectItem>
                  </SelectContent>
                </Select>
              ) : (
                <Select value={rankingType} onValueChange={setRankingType} disabled={running || !rankingSupported}>
                  <SelectTrigger className="h-10 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {currentRankingOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {view === 'search' ? (
                <div className="relative">
                  <Search className="absolute left-3 top-3 h-4 w-4 text-cyber-text-muted" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    disabled={running}
                    placeholder={searchSource === 'creator' ? '作者主页/ID，B站可输入用户名' : '搜索视频标题、关键词、话题'}
                    className="h-10 pl-9 text-sm"
                  />
                </div>
              ) : (
                <div className="grid grid-cols-[1fr_110px] gap-3">
                  <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary px-3 py-2 text-xs text-cyber-text-secondary">
                    {rankingSupportNote}
                  </div>
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={rankingLimit}
                    onChange={(event) => setRankingLimit(parseInt(event.target.value, 10) || 5)}
                    disabled={running}
                    className="h-10 text-xs"
                  />
                </div>
              )}

              <Button type="button" onClick={startDiscovery} disabled={startingDiscovery || resolvingCreators || running || (view === 'ranking' && !rankingSupported)} className="h-10">
                {startingDiscovery || resolvingCreators ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                {view === 'search' && searchSource === 'creator' ? '搜索作者' : '检索候选'}
              </Button>
            </div>

            <div className="mt-3 grid grid-cols-1 md:grid-cols-[132px_132px_132px_132px_150px_1fr_auto] gap-3 items-end">
              <div>
                <Label className="text-[11px] text-cyber-text-muted">开始日期</Label>
                <Input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} disabled={running} className="h-9 text-xs" />
              </div>
              <div>
                <Label className="text-[11px] text-cyber-text-muted">结束日期</Label>
                <Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} disabled={running} className="h-9 text-xs" />
              </div>
              <SettingNumber
                label="筛选后数量"
                value={taskSettings.maxVideos}
                min={1}
                max={200}
                onChange={(value) => updateDefaults({ maxVideos: value })}
              />
              <SettingNumber
                label="最大抓取上限"
                value={taskSettings.maxCrawlItems}
                min={1}
                max={500}
                onChange={(value) => updateDefaults({ maxCrawlItems: value })}
              />
              <div>
                <Label className="text-[11px] text-cyber-text-muted">排序</Label>
                <Select value={sortKey} onValueChange={(value) => setSortKey(value as SortKey)}>
                  <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="relevance">平台返回顺序</SelectItem>
                    <SelectItem value="published_desc">发布时间新到旧</SelectItem>
                    <SelectItem value="published_asc">发布时间旧到新</SelectItem>
                    <SelectItem value="views_desc">播放量高到低</SelectItem>
                    <SelectItem value="likes_desc">点赞高到低</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary px-3 py-2 text-[11px] text-cyber-text-muted">
                {view === 'ranking'
                  ? '日期用于过滤榜单项继续检索到的视频发布时间；榜单本身由平台实时返回。'
                  : `登录档案：${activeCredential ? `${activeCredential.name} (${activeCredential.cookies_masked ?? 'configured'})` : '未选择，按任务登录方式运行'}`}
              </div>
              {running ? (
                <Button type="button" variant="destructive" onClick={stopActiveTask} disabled={stopping} className="h-9">
                  {stopping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
                  停止
                </Button>
              ) : null}
              {canResume ? (
                <Button type="button" variant="outline" onClick={resumeActiveTask} disabled={resuming} className="h-9">
                  {resuming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  继续
                </Button>
              ) : null}
            </div>
          </div>

          {view === 'search' && searchSource === 'creator' ? (
            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-cyber-text-primary">作者候选</div>
                  <div className="text-[11px] text-cyber-text-muted">
                    先确认作者身份，再加载该作者在日期范围内的视频，避免抓取无关重名账号。
                  </div>
                </div>
                <Button type="button" size="sm" onClick={() => startCreatorVideoDiscovery()} disabled={running || startingDiscovery || !selectedCreator}>
                  {startingDiscovery ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
                  加载选中作者视频
                </Button>
              </div>
              {creatorResolveMessage ? (
                <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary px-3 py-2 text-xs text-cyber-text-secondary">
                  {creatorResolveMessage}
                </div>
              ) : null}
              {creatorCandidates.length ? (
                <div className="max-h-80 overflow-y-auto pr-1 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  {creatorCandidates.map((candidate) => {
                    const avatar = creatorAvatarUrl(candidate)
                    const followers = creatorMetric(candidate, 'follower_count', ['fans', 'followers', 'follower_count'])
                    const videos = creatorMetric(candidate, 'video_count', ['videos', 'video_count'])
                    const selected = selectedCreator?.id === candidate.id && selectedCreator?.platform === candidate.platform
                    return (
                      <article
                        key={`${candidate.platform}:${candidate.id}`}
                        onClick={() => setSelectedCreator(candidate)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') setSelectedCreator(candidate)
                        }}
                        className={`cursor-pointer rounded-lg border bg-cyber-bg-tertiary/30 p-3 text-left transition-all ${selected ? 'border-cyber-neon-cyan bg-cyber-neon-cyan/10' : 'border-cyber-border-subtle hover:border-cyber-neon-cyan/50'}`}
                      >
                        <div className="flex gap-3">
                          <div className="h-14 w-14 shrink-0 overflow-hidden rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary">
                            {avatar ? (
                              <img src={avatar} alt="" className="h-full w-full object-cover" loading="lazy" referrerPolicy="no-referrer" />
                            ) : (
                              <div className="flex h-full w-full items-center justify-center text-cyber-text-muted">
                                <KeyRound className="h-5 w-5" />
                              </div>
                            )}
                          </div>
                          <div className="min-w-0 flex-1 space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="truncate text-sm font-medium text-cyber-text-primary">{candidate.display_name}</span>
                              {candidate.verified ? <Badge variant="success">认证</Badge> : null}
                            </div>
                            <div className="text-[11px] text-cyber-text-muted">UID {candidate.id}</div>
                            <div className="grid grid-cols-2 gap-2 text-[11px] text-cyber-text-secondary">
                              <span>粉丝 {formatNumber(followers)}</span>
                              <span>视频 {formatNumber(videos)}</span>
                            </div>
                            {candidate.description ? <div className="line-clamp-2 text-[11px] text-cyber-text-muted">{candidate.description}</div> : null}
                          </div>
                        </div>
                        <div className="mt-3 flex items-center justify-between gap-2">
                          {candidate.profile_url ? (
                            <a href={candidate.profile_url} target="_blank" rel="noreferrer" onClick={(event) => event.stopPropagation()} className="text-[11px] text-cyber-neon-cyan hover:underline">
                              打开主页
                            </a>
                          ) : <span />}
                          <Button
                            type="button"
                            variant={selected ? 'default' : 'outline'}
                            size="sm"
                            onClick={(event) => {
                              event.stopPropagation()
                              setSelectedCreator(candidate)
                              void startCreatorVideoDiscovery(candidate)
                            }}
                            disabled={running || startingDiscovery}
                          >
                            加载视频
                          </Button>
                        </div>
                      </article>
                    )
                  })}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-cyber-border-subtle p-4 text-sm text-cyber-text-muted">
                  输入作者名、主页链接或 ID 后点击“搜索作者”，候选会显示在这里。B 站支持用户名搜索；其他平台目前需要主页链接或平台 creator ID。
                </div>
              )}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-cyber-text-secondary">
              <Badge variant={discoveryStatus?.status === 'completed' ? 'success' : discoveryStatus?.status === 'error' ? 'destructive' : discoveryStatus ? 'running' : 'secondary'}>
                {discoveryStatus?.status ?? 'idle'}
              </Badge>
              <span>原始记录 {discoveryStatus?.result?.total_records ?? 0}，候选项 {candidateItems.length}，可选视频 {selectableCandidateItems.length}，已选 {selectedCount}</span>
            </div>
            <div className="flex items-center gap-2">
              <Button type="button" variant="outline" size="sm" onClick={() => setSelectedIds(selectableCandidateItems.map((item) => item.id))} disabled={!selectableCandidateItems.length}>全选</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => setSelectedIds([])} disabled={!selectedIds.length}>清空</Button>
              <Button type="button" variant="outline" size="sm" onClick={() => startSelectedAction(false)} disabled={startingAction || !selectedIds.length}>
                <Download className="h-3.5 w-3.5" />
                下载
              </Button>
              <Button type="button" size="sm" onClick={() => startSelectedAction(true)} disabled={startingAction || !selectedIds.length}>
                {startingAction ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Video className="h-3.5 w-3.5" />}
                下载并分析
              </Button>
            </div>
          </div>

          {candidateItems.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {sortedItems.map((item) => {
                const views = metricValue(item, VIEW_METRIC_KEYS)
                const likes = metricValue(item, LIKE_METRIC_KEYS)
                const favorites = metricValue(item, FAVORITE_METRIC_KEYS)
                const comments = metricValue(item, COMMENT_METRIC_KEYS)
                const danmaku = metricValue(item, DANMAKU_METRIC_KEYS)
                const selected = selectedIds.includes(item.id)
                const cover = coverUrl(item)
                const url = videoUrl(item)
                const rankingScore = parseMetricNumber(item.raw?.hot_value ?? item.raw?.ranking_score)
                const rankingRank = item.raw?.rank ? String(item.raw.rank) : ''
                const rankingTopic = isRankingTopicItem(item)
                const keyword = rankingSearchKeyword(item)
                const canSearchRankingVideo = rankingTopic && rankingVideoSearchSupported(item)
                const itemPlatform = discoveryStatus?.result?.platform || platform
                const viewsLabel = itemPlatform === 'dy' && views === null ? '未返回' : formatNumber(views)
                const creatorName = firstTextValue(item, CREATOR_NAME_KEYS)
                const durationLabel = formatDuration(durationSeconds(item))
                const sizeBytes = videoSizeBytes(item)
                const sizeLabel = formatByteSize(sizeBytes)
                return (
                  <article key={item.id} className={`rounded-lg border bg-cyber-bg-tertiary/30 overflow-hidden transition-all ${selected ? 'border-cyber-neon-cyan' : 'border-cyber-border-subtle'}`}>
                    <div className="aspect-video bg-cyber-bg-secondary relative">
                      {cover ? <img src={cover} alt="" className="h-full w-full object-cover" loading="lazy" referrerPolicy="no-referrer" /> : (
                        <div className="h-full w-full flex items-center justify-center text-cyber-text-muted"><Video className="h-8 w-8" /></div>
                      )}
                      <div className="absolute left-2 top-2">
                        {rankingTopic ? (
                          <Badge variant="secondary">榜单项</Badge>
                        ) : (
                          <Checkbox checked={selected} onCheckedChange={(checked) => toggleItem(item.id, checked === true)} />
                        )}
                      </div>
                    </div>
                    <div className="p-3 space-y-2">
                      <div className="min-h-10 text-sm font-medium text-cyber-text-primary line-clamp-2">{item.title || item.id}</div>
                      <div className="text-[11px] text-cyber-text-muted line-clamp-2">{item.desc || '-'}</div>
                      <div className="grid grid-cols-3 gap-2 text-[10px] text-cyber-text-muted">
                        <span className="truncate" title={creatorName || '平台检索结果未返回作者'}>作者 {creatorName || '未返回'}</span>
                        <span className="truncate">时长 {durationLabel}</span>
                        <span className="truncate" title={sizeBytes === null ? '平台检索结果未返回视频大小；下载或探测到真实文件后会显示。' : undefined}>大小 {sizeLabel}</span>
                      </div>
                      <div className="grid grid-cols-4 gap-2 text-[10px] text-cyber-text-muted">
                        <span title={itemPlatform === 'dy' && views === null ? '抖音当前返回的搜索/详情数据未包含视频播放量字段' : undefined}>播放 {viewsLabel}</span>
                        <span>点赞 {formatNumber(likes)}</span>
                        <span>收藏 {formatNumber(favorites)}</span>
                        <span>评论 {formatNumber(comments)}</span>
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-cyber-text-muted">
                        {item.raw?.ranking_source && rankingRank ? <span>榜单 #{rankingRank}</span> : null}
                        {item.raw?.ranking_source && rankingScore !== null ? <span>热度 {formatNumber(rankingScore)}</span> : null}
                        <span>弹幕 {formatNumber(danmaku)}</span>
                        <span>{formatDate(item.published_at)}</span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1">
                          <Badge variant={item.download_status === 'downloaded' || item.download_status === 'existing' ? 'success' : item.download_status === 'failed' ? 'destructive' : 'secondary'}>
                            {item.download_status}
                          </Badge>
                          <Badge variant={item.summary_status === 'completed' ? 'success' : item.summary_status === 'failed' ? 'destructive' : 'secondary'}>
                            {item.summary_status}
                          </Badge>
                        </div>
                        {rankingTopic ? (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => void startSearchFromRankingItem(item)}
                            disabled={running || startingDiscovery || !keyword || !canSearchRankingVideo}
                          >
                            <Search className="h-3.5 w-3.5" />
                            {canSearchRankingVideo ? '搜视频' : '仅展示'}
                          </Button>
                        ) : url ? (
                          <a href={url} target="_blank" rel="noreferrer" className="text-[11px] text-cyber-neon-cyan hover:underline">{uiText.openLink}</a>
                        ) : null}
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : (
            <div className="min-h-52 rounded-lg border border-dashed border-cyber-border-subtle flex items-center justify-center text-sm text-cyber-text-muted">
              {uiText.emptyCandidates}
            </div>
          )}

          {actionStatus ? (
            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-sm font-mono text-cyber-text-primary">{uiText.downloadAnalysisTask}: {actionStatus.task_id}</div>
                  {actionDownloadDir ? (
                    <div className="mt-1 break-all text-[11px] text-cyber-text-muted">
                      {uiText.downloadDir}: {actionDownloadDir}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-shrink-0 items-center gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => void openTaskDownloadDir(actionStatus.task_id)}>
                    <FolderOpen className="h-3.5 w-3.5" />
                    {uiText.openDownloadDir}
                  </Button>
                  <Badge variant={actionStatus.status === 'completed' ? 'success' : actionStatus.status === 'error' ? 'destructive' : 'running'}>{actionStatus.status}</Badge>
                </div>
              </div>
              <div className="text-xs text-cyber-text-secondary">{actionStatus.progress_message}</div>
              <div className="text-[11px] text-cyber-text-muted">
                {formatDate(actionStatus.started_at)} - {formatDate(actionStatus.completed_at)} · {uiText.elapsed} {formatElapsedSeconds(elapsedBetweenSeconds(actionStatus.started_at, actionStatus.completed_at))}
              </div>
              {actionStatus.download_progress ? (
                <div className="h-2 rounded-full bg-cyber-bg-secondary overflow-hidden">
                  <div className="h-full bg-cyber-neon-cyan" style={{ width: `${actionStatus.download_progress.percent ?? 0}%` }} />
                </div>
              ) : null}
              <TaskStepTimeline steps={actionStatus.subtasks ?? []} copy={uiText} />
              {actionStatus.result?.aggregate_summary ? (
                <div className="max-h-[38rem] overflow-y-auto rounded-md border border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 p-4 text-xs text-cyber-text-primary">
                  <div className="mb-2 text-[11px] font-mono font-semibold text-cyber-neon-cyan">{uiText.overallSummary}</div>
                  <MarkdownResult content={actionStatus.result.aggregate_summary} copy={uiText} />
                </div>
              ) : null}
              {actionStatus.result?.items?.some((item) => item.summary || item.error) ? (
                <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3">
                  <div className="mb-2 text-[11px] font-mono font-semibold text-cyber-text-primary">{uiText.perVideoResults}</div>
                  <div className="max-h-96 space-y-3 overflow-y-auto pr-1">
                    {actionStatus.result.items.map((item) => (
                      <article key={item.id} className="rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary/40 p-3">
                        <div className="mb-2 flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="truncate text-xs font-semibold text-cyber-text-primary">{item.title || item.id}</div>
                            <div className="mt-0.5 text-[10px] text-cyber-text-muted">{formatDate(item.published_at)} · {item.id}</div>
                          </div>
                          <div className="flex flex-shrink-0 flex-wrap gap-1">
                            <Badge variant={item.summary_status === 'completed' ? 'success' : item.summary_status === 'failed' ? 'destructive' : 'secondary'}>
                              {item.summary_status}
                            </Badge>
                            {item.analysis_mode !== 'none' ? <Badge variant="outline">{item.analysis_mode}</Badge> : null}
                          </div>
                        </div>
                        {item.summary ? (
                          <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-3">
                            <MarkdownResult content={item.summary} copy={uiText} />
                          </div>
                        ) : null}
                        {item.error ? <div className="mt-2 text-[11px] text-cyber-neon-orange">{item.error}</div> : null}
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[230px_1fr] min-h-[680px]">
          <aside className="border-r border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-3">
            {[
              ['credentials', KeyRound, uiText.credentials] as const,
              ['api', Video, uiText.api] as const,
              ['defaults', SlidersHorizontal, uiText.defaults] as const,
            ].map(([value, Icon, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setSettingsSection(value)}
                className={`mb-1 flex h-10 w-full items-center gap-3 rounded-full px-4 text-left text-sm transition-all ${
                  settingsSection === value ? 'bg-cyber-neon-cyan/15 text-cyber-neon-cyan' : 'text-cyber-text-secondary hover:bg-cyber-bg-tertiary'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </aside>
          <main className="p-6">
            {settingsSection === 'credentials' ? (
              <div className="max-w-4xl space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-cyber-text-primary">平台登录信息</h2>
                    <p className="mt-2 text-sm text-cyber-text-secondary">Cookie 会保存在后端本地文件，任务运行时按平台和默认档案注入，不在任务列表里明文展示。</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={startNewCredentialProfile}>
                    <Plus className="h-4 w-4" />
                    新增
                  </Button>
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-5">
                  <div className="space-y-2">
                    {credentials.length ? credentials.map((credential) => (
                      <button
                        key={credential.id}
                        type="button"
                        onClick={() => selectCredentialForEdit(credential)}
                        className={`w-full rounded-lg border p-3 text-left ${credentialFormId === credential.id ? 'border-cyber-neon-cyan bg-cyber-neon-cyan/10' : 'border-cyber-border-subtle bg-cyber-bg-tertiary/20'}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm text-cyber-text-primary">{credential.name}</span>
                          {credential.active ? <Badge variant="success">默认</Badge> : null}
                        </div>
                        <div className="mt-1 text-[11px] text-cyber-text-muted">
                          {credential.platform} · {credential.login_method === 'qrcode' ? '扫码' : 'Cookie'} · {credential.cookies_masked ?? '未配置 Cookie'}
                        </div>
                      </button>
                    )) : (
                      <div className="rounded-lg border border-dashed border-cyber-border-subtle p-4 text-sm text-cyber-text-muted">还没有保存的平台登录信息。</div>
                    )}
                  </div>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div>
                        <Label className="text-xs">平台</Label>
                        <Select value={credentialFormPlatform} onValueChange={setCredentialFormPlatform}>
                          <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                          <SelectContent>{PLATFORM_OPTIONS.map((item) => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent>
                        </Select>
                      </div>
                      <div>
                        <Label className="text-xs">档案名</Label>
                        <Input value={credentialName} onChange={(event) => setCredentialName(event.target.value)} className="h-9 text-xs" />
                      </div>
                    </div>
                    {credentialFormProfile ? (
                      <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="space-y-1">
                            <div className="text-xs font-medium text-cyber-text-primary">当前保存值</div>
                            <div className="text-[11px] text-cyber-text-secondary">
                              {credentialFormProfile.platform} · {credentialFormProfile.active ? '平台默认' : '非默认'} · {credentialFormProfile.login_method === 'qrcode' ? '扫码保存' : '手工 Cookie'} · {credentialFormProfile.cookies_configured ? '已保存 Cookie' : '未保存 Cookie'}
                            </div>
                            <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                              {credentialFormProfile.cookies_masked ?? 'Cookie 为空'}
                            </div>
                            <div className="text-[11px] text-cyber-text-muted">
                              更新：{formatDate(credentialFormProfile.updated_at)}
                            </div>
                            {typeof credentialFormProfile.metadata?.browser_data_dir === 'string' ? (
                              <div className="break-all text-[11px] text-cyber-text-muted">
                                浏览器目录：{credentialFormProfile.metadata.browser_data_dir}
                              </div>
                            ) : null}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Button type="button" variant="outline" size="sm" onClick={() => loadCredentialSecret(credentialFormProfile.id)}>
                              <Eye className="h-4 w-4" />加载明文
                            </Button>
                            <Button type="button" variant="outline" size="sm" onClick={() => copyCredentialSecret(credentialFormProfile.id)}>
                              <Copy className="h-4 w-4" />复制
                            </Button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="rounded-lg border border-dashed border-cyber-border-subtle p-3 text-xs text-cyber-text-muted">
                        选择左侧档案可查看当前保存摘要；点击“加载明文”后才会把 Cookie 放入编辑框。
                      </div>
                    )}
                    {credentialFormProfile ? (
                      <div className="flex flex-wrap items-center gap-2">
                        <Button type="button" variant="outline" size="sm" onClick={selfTestCredential} disabled={selfTestingCredential}>
                          {selfTestingCredential ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                          自测当前配置
                        </Button>
                        {credentialSelfTest ? (
                          <Badge variant={credentialSelfTest.status === 'ok' ? 'success' : credentialSelfTest.status === 'error' ? 'destructive' : 'secondary'}>
                            self-test {credentialSelfTest.status}
                          </Badge>
                        ) : null}
                      </div>
                    ) : null}
                    {credentialSelfTest ? (
                      <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3 text-xs text-cyber-text-secondary">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="font-medium text-cyber-text-primary">平台配置自测</div>
                          <Badge variant={credentialSelfTest.status === 'ok' ? 'success' : credentialSelfTest.status === 'error' ? 'destructive' : 'secondary'}>
                            {credentialSelfTest.status}
                          </Badge>
                        </div>
                        <div className="mt-2">{credentialSelfTest.message}</div>
                        <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-cyber-text-muted md:grid-cols-4">
                          <div>任务：{credentialSelfTest.task_id ?? '-'}</div>
                          <div>耗时：{formatDuration(credentialSelfTest.wall_seconds)}</div>
                          <div>原始记录：{credentialSelfTest.total_records}</div>
                          <div>候选：{credentialSelfTest.item_count}</div>
                        </div>
                        {credentialSelfTest.error_message ? (
                          <div className="mt-2 text-red-400">{credentialSelfTest.error_message}</div>
                        ) : null}
                        {credentialSelfTest.logs_tail.length ? (
                          <div className="mt-2 max-h-36 overflow-auto rounded-md border border-cyber-border-subtle bg-cyber-bg-primary/50 p-2 font-mono text-[11px] text-cyber-text-muted">
                            {credentialSelfTest.logs_tail.map((line, index) => (
                              <div key={`${credentialSelfTest.task_id ?? 'self-test'}-${index}`} className="break-all">
                                {line}
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                    <div>
                      <Label className="text-xs">Cookie</Label>
                      <textarea
                        value={credentialCookies}
                        onChange={(event) => setCredentialCookies(event.target.value)}
                        placeholder="可粘贴 Cookie Header、DevTools 表格或 Cookie-Editor JSON；留空保存则保留原 Cookie"
                        className="mt-2 min-h-36 w-full rounded-md border border-cyber-border-DEFAULT bg-cyber-bg-tertiary px-3 py-2 text-xs font-mono text-cyber-text-primary placeholder:text-cyber-text-muted focus-visible:outline-none focus-visible:border-cyber-neon-cyan/50"
                      />
                    </div>
                    <label className="flex items-center gap-3 text-xs text-cyber-text-secondary">
                      <Checkbox checked={clearCredentialCookies} onCheckedChange={(checked) => setClearCredentialCookies(checked === true)} />
                      清空该档案 Cookie
                    </label>
                    {visibleQrcodeLoginStatus ? (
                      <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3 text-xs text-cyber-text-secondary">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span>扫码登录：{visibleQrcodeLoginStatus.progress_message || visibleQrcodeLoginStatus.status}</span>
                          <Badge variant={visibleQrcodeLoginStatus.status === 'completed' ? 'success' : visibleQrcodeLoginStatus.status === 'error' ? 'destructive' : 'running'}>
                            {visibleQrcodeLoginStatus.status}
                          </Badge>
                        </div>
                        {visibleQrcodeLoginStatus.cookie_count ? (
                          <div className="mt-2 break-all font-mono text-[11px] text-cyber-text-muted">
                            cookies: {visibleQrcodeLoginStatus.cookie_count}; keys: {visibleQrcodeLoginStatus.cookie_keys.slice(0, 12).join(', ')}
                            {visibleQrcodeLoginStatus.cookie_keys.length > 12 ? `, +${visibleQrcodeLoginStatus.cookie_keys.length - 12}` : ''}
                          </div>
                        ) : null}
                        {visibleQrcodeLoginStatus.browser_data_dir ? (
                          <div className="mt-1 break-all text-[11px] text-cyber-text-muted">
                            browser profile: {visibleQrcodeLoginStatus.browser_data_dir}
                          </div>
                        ) : null}
                        {visibleQrcodeLoginStatus.error_message ? (
                          <div className="mt-2 text-[11px] text-red-400">{visibleQrcodeLoginStatus.error_message}</div>
                        ) : null}
                      </div>
                    ) : null}
                    <div className="flex flex-wrap gap-2">
                      <Button type="button" onClick={saveCredential}><CheckCircle2 className="h-4 w-4" />保存</Button>
                      <Button
                        type="button"
                        variant="outline"
                        disabled={startingQrcodeLogin || qrcodeLoginRunning || credentialFormPlatform === 'tieba'}
                        onClick={startQrcodeLogin}
                      >
                        {startingQrcodeLogin || qrcodeLoginRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <QrCode className="h-4 w-4" />}
                        扫码登录并保存
                      </Button>
                      <Button type="button" variant="outline" disabled={!credentialFormId} onClick={() => activateCredential(credentialFormId)}>设为平台默认</Button>
                      <Button type="button" variant="destructive" disabled={!credentialFormId} onClick={deleteCredential}>删除</Button>
                    </div>
                    {credentialPath ? <div className="text-[11px] text-cyber-text-muted break-all">保存位置：{credentialPath}</div> : null}
                  </div>
                </div>
              </div>
            ) : null}

            {settingsSection === 'api' ? (
              <div className="max-w-3xl space-y-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-cyber-text-primary">{uiText.api}</h2>
                    <p className="mt-2 text-sm text-cyber-text-secondary">{uiText.apiDesc}</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={createQwenProfile}>
                    <Plus className="h-4 w-4" />
                    {uiText.create}
                  </Button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label className="text-xs">{uiText.profile}</Label>
                    <Select
                      value={selectedQwenProfileId}
                      onValueChange={(value) => {
                        const profile = qwenProfiles.find((item) => item.id === value)
                        setSelectedQwenProfileId(value)
                        if (profile) applyQwenProfile(profile)
                      }}
                    >
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>{qwenProfiles.map((profile) => <SelectItem key={profile.id} value={profile.id}>{profile.name}{profile.active ? ` · ${uiText.defaultProfile}` : ''}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">{uiText.profileName}</Label>
                    <Input value={qwenName} onChange={(event) => setQwenName(event.target.value)} className="h-9 text-xs" />
                  </div>
                  <div>
                    <Label className="text-xs">API Key</Label>
                    <div className="mt-1 flex gap-2">
                      <Input type={showQwenApiKey ? 'text' : 'password'} value={qwenApiKey} onChange={(event) => setQwenApiKey(event.target.value)} placeholder={selectedQwenProfile?.api_key_configured ? uiText.keepExistingKey : 'sk-...'} className="h-9 text-xs" />
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-9 w-9"
                        title={showQwenApiKey ? uiText.hideApiKey : uiText.showApiKey}
                        onClick={() => setShowQwenApiKey((current) => !current)}
                        disabled={!qwenApiKey}
                      >
                        {showQwenApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs">{uiText.apiProvider}</Label>
                    <Select value={qwenApiProvider} onValueChange={(value) => updateQwenApiProvider(value as QwenApiProvider)}>
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {QWEN_API_PROVIDER_OPTIONS.map((option) => (
                          <SelectItem
                            key={option.value}
                            value={option.value}
                            rightSlot={<span className={scopeBadgeClass(option.scope === 'local')}>{providerScopeLabel(option.scope)}</span>}
                          >
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="md:col-span-2">
                    <Label className="text-xs">{uiText.model}</Label>
                    <div className="mt-1 grid grid-cols-1 gap-2 md:grid-cols-[minmax(0,1fr)_220px]">
                      <Input
                        value={qwenModel}
                        onChange={(event) => setQwenModel(event.target.value)}
                        onBlur={() => syncProviderForSelectedModel(qwenModel.trim())}
                        placeholder={uiText.modelName}
                        className="h-9 text-xs"
                      />
                      <Select
                        value={ALL_QWEN_MODEL_VALUES.has(qwenModel) ? qwenModel : '__custom__'}
                        onValueChange={(value) => {
                          if (value !== '__custom__') selectKnownQwenModel(value)
                        }}
                      >
                        <SelectTrigger className="h-9 text-xs">
                          <SelectValue placeholder={uiText.commonModel} />
                        </SelectTrigger>
                        <SelectContent className="max-h-72">
                          <SelectItem value="__custom__">{uiText.customModelInput}</SelectItem>
                          {ALL_QWEN_MODEL_OPTIONS.map((model) => (
                            <SelectItem
                              key={model.value}
                              value={model.value}
                              rightSlot={<span className={scopeBadgeClass(modelHasLocalSource(model))}>{modelScopeLabel(model)}</span>}
                            >
                              {model.value}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="mt-1 text-[11px] text-cyber-text-muted">
                      {uiText.modelHint}
                    </div>
                    {qwenProfileDirty ? (
                      <div className="mt-2 rounded-md border border-cyber-neon-orange/40 bg-cyber-neon-orange/10 px-3 py-2 text-[11px] leading-5 text-cyber-neon-orange">
                        当前编辑尚未保存。新任务会使用下方“当前保存值”；点击保存后，模型和接口配置才会生效。
                      </div>
                    ) : null}
                  </div>
                </div>
                <div>
                  <Label className="text-xs">Base URL</Label>
                  <Input value={qwenBaseUrl} onChange={(event) => setQwenBaseUrl(event.target.value)} className="mt-2 h-9 text-xs" />
                </div>
                <div>
                  <Label className="text-xs">{uiText.localDownloadRoot}</Label>
                  <Input
                    value={qwenLocalDownloadRoot}
                    onChange={(event) => setQwenLocalDownloadRoot(event.target.value)}
                    placeholder={uiText.localDownloadRootPlaceholder}
                    className="mt-2 h-9 text-xs"
                  />
                  <div className="mt-1 text-[11px] leading-5 text-cyber-text-muted">
                    {uiText.localDownloadRootDesc}
                  </div>
                </div>
                <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-3">
                  <label className="flex items-start gap-3 text-xs text-cyber-text-primary">
                    <Checkbox checked={qwenOssEnabled} onCheckedChange={(checked) => setQwenOssEnabled(checked === true)} />
                    <span>
                      <span className="block font-medium">{uiText.ossUpload}</span>
                      <span className="mt-1 block text-[11px] leading-5 text-cyber-text-muted">{uiText.ossDesc}</span>
                    </span>
                  </label>
                  <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
                    <div>
                      <Label className="text-xs">{uiText.ossAccessKeyId}</Label>
                      <Input
                        value={qwenOssAccessKeyId}
                        onChange={(event) => setQwenOssAccessKeyId(event.target.value)}
                        placeholder={selectedQwenProfile?.oss_access_key_id_configured ? uiText.keepExistingKey : 'LTAI...'}
                        className="mt-1 h-9 text-xs"
                      />
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossAccessKeySecret}</Label>
                      <div className="mt-1 flex gap-2">
                        <Input
                          type={showQwenOssKey ? 'text' : 'password'}
                          value={qwenOssAccessKeySecret}
                          onChange={(event) => setQwenOssAccessKeySecret(event.target.value)}
                          placeholder={selectedQwenProfile?.oss_access_key_secret_configured ? uiText.keepExistingKey : 'secret'}
                          className="h-9 text-xs"
                        />
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          className="h-9 w-9"
                          title={showQwenOssKey ? uiText.hideOssKey : uiText.showOssKey}
                          onClick={() => setShowQwenOssKey((current) => !current)}
                          disabled={!qwenOssAccessKeySecret}
                        >
                          {showQwenOssKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossBucket}</Label>
                      <Input value={qwenOssBucket} onChange={(event) => setQwenOssBucket(event.target.value)} className="mt-1 h-9 text-xs" />
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossEndpoint}</Label>
                      <Input value={qwenOssEndpoint} onChange={(event) => setQwenOssEndpoint(event.target.value)} placeholder="oss-cn-beijing.aliyuncs.com" className="mt-1 h-9 text-xs" />
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossRegion}</Label>
                      <Input value={qwenOssRegion} onChange={(event) => setQwenOssRegion(event.target.value)} placeholder="cn-beijing" className="mt-1 h-9 text-xs" />
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossPrefix}</Label>
                      <Input value={qwenOssPrefix} onChange={(event) => setQwenOssPrefix(event.target.value)} className="mt-1 h-9 text-xs" />
                    </div>
                    <div>
                      <Label className="text-xs">{uiText.ossExpires}</Label>
                      <Input
                        type="number"
                        min={300}
                        max={604800}
                        value={qwenOssUrlExpiresSeconds}
                        onChange={(event) => setQwenOssUrlExpiresSeconds(parseInt(event.target.value, 10) || 7200)}
                        className="mt-1 h-9 text-xs"
                      />
                    </div>
                    <label className="flex items-start gap-3 text-xs text-cyber-text-secondary md:mt-6">
                      <Checkbox checked={qwenOssCleanupAfterAnalysis} onCheckedChange={(checked) => setQwenOssCleanupAfterAnalysis(checked === true)} />
                      <span>
                        <span className="block font-medium text-cyber-text-primary">{uiText.ossCleanup}</span>
                        <span className="mt-1 block text-[11px] leading-5 text-cyber-text-muted">{uiText.ossCleanupDesc}</span>
                      </span>
                    </label>
                    <label className="flex items-center gap-3 text-xs text-cyber-text-secondary md:mt-6">
                      <Checkbox checked={clearQwenOssKey} onCheckedChange={(checked) => setClearQwenOssKey(checked === true)} />
                      {uiText.clearOssKey}
                    </label>
                  </div>
                </div>
                {selectedQwenProfile ? (
                  <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="text-xs font-medium text-cyber-text-primary">{uiText.savedValue}</div>
                        <div className="text-[11px] text-cyber-text-secondary">
                          {selectedQwenProfile.active ? uiText.defaultProfile : uiText.nonDefaultProfile} · {selectedQwenProfile.api_key_configured ? uiText.keySaved : uiText.keyMissing} · {selectedQwenProfile.model}
                        </div>
                        <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                          Key: {selectedQwenProfile.api_key_masked ?? uiText.keyEmpty}
                        </div>
                        <div className="text-[11px] text-cyber-text-muted">
                          {uiText.provider}: {QWEN_API_PROVIDER_OPTIONS.find((option) => option.value === selectedQwenProfile.api_provider)?.label ?? selectedQwenProfile.api_provider}
                        </div>
                        <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                          URL: {selectedQwenProfile.base_url}
                        </div>
                        <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                          {uiText.localDownloadRootSaved}: {selectedQwenProfile.local_download_root || uiText.defaultDownloadRoot}
                        </div>
                        <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                          OSS: {selectedQwenProfile.oss_enabled ? uiText.ossSaved : uiText.ossMissing}
                          {selectedQwenProfile.oss_bucket ? ` · ${selectedQwenProfile.oss_bucket}` : ''}
                          {selectedQwenProfile.oss_endpoint ? ` · ${selectedQwenProfile.oss_endpoint}` : ''}
                        </div>
                        <div className="break-all font-mono text-[11px] text-cyber-text-muted">
                          OSS AK: {selectedQwenProfile.oss_access_key_id_masked ?? uiText.keyEmpty} · Secret: {selectedQwenProfile.oss_access_key_secret_configured ? uiText.keySaved : uiText.keyMissing}
                        </div>
                        <div className="text-[11px] text-cyber-text-muted">
                          {uiText.ossCleanupStatus}: {selectedQwenProfile.oss_cleanup_after_analysis ? uiText.ossCleanupEnabled : uiText.ossCleanupDisabled}
                        </div>
                        <div className="text-[11px] text-cyber-text-muted">
                          {uiText.updated}: {formatDate(selectedQwenProfile.updated_at)}
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Button type="button" variant="outline" size="sm" onClick={() => loadQwenSecret(selectedQwenProfile.id)}>
                          <Eye className="h-4 w-4" />{uiText.loadSecret}
                        </Button>
                        <Button type="button" variant="outline" size="sm" onClick={() => copyQwenSecret(selectedQwenProfile.id)}>
                          <Copy className="h-4 w-4" />{uiText.copy}
                        </Button>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-lg border border-dashed border-cyber-border-subtle p-3 text-xs text-cyber-text-muted">
                    {uiText.selectApiProfileHint}
                  </div>
                )}
                <label className="flex items-center gap-3 text-xs text-cyber-text-secondary">
                  <Checkbox checked={clearQwenKey} onCheckedChange={(checked) => setClearQwenKey(checked === true)} />
                  {uiText.clearApiKey}
                </label>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" onClick={saveQwenProfile}><CheckCircle2 className="h-4 w-4" />{uiText.save}</Button>
                  <Button type="button" variant="outline" onClick={activateQwenProfile} disabled={!selectedQwenProfileId}>{uiText.setDefault}</Button>
                  <Button type="button" variant="destructive" onClick={deleteQwenProfile} disabled={qwenProfiles.length <= 1}>{uiText.delete}</Button>
                </div>
                {qwenSettings?.settings_path ? <div className="text-[11px] text-cyber-text-muted break-all">{uiText.settingsPath}: {qwenSettings.settings_path}</div> : null}
              </div>
            ) : null}

            {settingsSection === 'defaults' ? (
              <div className="max-w-4xl space-y-5">
                <h2 className="text-xl font-semibold text-cyber-text-primary">基础参数</h2>
                <p className="text-sm text-cyber-text-secondary">这些参数真实参与任务请求，保存在浏览器本地设置中。</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <SettingNumber label="筛选后数量" value={taskSettings.maxVideos} min={1} max={200} onChange={(value) => updateDefaults({ maxVideos: value })} />
                  <SettingNumber label="最大抓取上限" value={taskSettings.maxCrawlItems} min={1} max={500} onChange={(value) => updateDefaults({ maxCrawlItems: value })} />
                  <SettingNumber label="抓取并发" value={taskSettings.crawlConcurrency} min={1} max={8} onChange={(value) => updateDefaults({ crawlConcurrency: value })} />
                  <SettingNumber label="最小间隔秒" value={taskSettings.crawlMinSleepSeconds} min={0} max={120} step={0.5} onChange={(value) => updateDefaults({ crawlMinSleepSeconds: value })} />
                  <SettingNumber label="最大间隔秒" value={taskSettings.crawlMaxSleepSeconds} min={0} max={120} step={0.5} onChange={(value) => updateDefaults({ crawlMaxSleepSeconds: value })} />
                  <SettingNumber label="每 N 条长暂停" value={taskSettings.crawlLongPauseEvery} min={0} max={1000} onChange={(value) => updateDefaults({ crawlLongPauseEvery: value })} />
                  <SettingNumber label="长暂停最小秒" value={taskSettings.crawlLongPauseMinSeconds} min={0} max={3600} step={1} onChange={(value) => updateDefaults({ crawlLongPauseMinSeconds: value })} />
                  <SettingNumber label="长暂停最大秒" value={taskSettings.crawlLongPauseMaxSeconds} min={0} max={3600} step={1} onChange={(value) => updateDefaults({ crawlLongPauseMaxSeconds: value })} />
                  <div>
                    <Label className="text-xs">登录方式</Label>
                    <Select value={taskSettings.loginType} onValueChange={(value) => updateDefaults({ loginType: value })}>
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="qrcode">扫码登录</SelectItem>
                        <SelectItem value="cookie">Cookie 登录</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="text-xs">上传后端</Label>
                    <Select value={taskSettings.videoUploadBackend} onValueChange={(value) => updateDefaults({ videoUploadBackend: value })}>
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="auto">Auto</SelectItem>
                        <SelectItem value="oss">OSS URL</SelectItem>
                        <SelectItem value="dashscope">DashScope SDK</SelectItem>
                        <SelectItem value="openai">OpenAI Compatible</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <SettingNumber label="抽帧 FPS" value={taskSettings.videoFps} min={0.1} max={10} step={0.1} onChange={(value) => updateDefaults({ videoFps: value })} />
                  <SettingNumber label="抽帧数量" value={taskSettings.sampleFrames} min={1} max={24} onChange={(value) => updateDefaults({ sampleFrames: value })} />
                  <SettingNumber label="DashScope 上限 MB" value={taskSettings.maxDashscopeVideoMb} min={1} max={100} onChange={(value) => updateDefaults({ maxDashscopeVideoMb: value })} />
                  <SettingNumber label="SDK 重试次数" value={taskSettings.dashscopeRetryCount} min={1} max={5} onChange={(value) => updateDefaults({ dashscopeRetryCount: value })} />
                  <SettingNumber label="压缩目标 MB" value={taskSettings.compressionTargetMb} min={10} max={100} onChange={(value) => updateDefaults({ compressionTargetMb: value })} />
                  <div>
                    <Label className="text-xs">Whisper 模型</Label>
                    <Select value={taskSettings.whisperModel} onValueChange={(value) => updateDefaults({ whisperModel: value })}>
                      <SelectTrigger className="h-9 text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>{WHISPER_MODELS.map((model) => <SelectItem key={model} value={model}>{model}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <ToggleRow label="无头浏览器" checked={taskSettings.headless} onChange={(checked) => updateDefaults({ headless: checked })} />
                  <ToggleRow label="上传前压缩大视频" checked={taskSettings.enableVideoCompression} onChange={(checked) => updateDefaults({ enableVideoCompression: checked })} />
                  <ToggleRow label="融合 Whisper 转录" checked={taskSettings.enableWhisperTranscription} onChange={(checked) => updateDefaults({ enableWhisperTranscription: checked })} />
                </div>
              </div>
            ) : null}
          </main>
        </div>
      )}
    </section>
  )
}

function SettingNumber({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
}) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(event) => onChange(parseFloat(event.target.value) || min)}
        className="h-9 text-xs"
      />
    </div>
  )
}

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return (
    <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-3 text-xs text-cyber-text-primary">
      <Checkbox checked={checked} onCheckedChange={(value) => onChange(value === true)} />
      {label}
    </label>
  )
}
