import type { ComponentProps, ReactNode } from 'react'
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  KeyRound,
  ListChecks,
  Loader2,
  Play,
  Plus,
  Search,
  Square,
  Trash2,
  UserRound,
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
  type QwenProfile,
  type QwenSettings,
  type VideoDownloadProgress,
  type VideoSummaryTaskStatus,
} from '@/lib/api'

const PLATFORM_OPTIONS = [
  { value: 'xhs', label: '小红书' },
  { value: 'dy', label: '抖音' },
  { value: 'ks', label: '快手' },
  { value: 'bili', label: 'B站' },
  { value: 'wb', label: '微博' },
  { value: 'tieba', label: '贴吧' },
  { value: 'zhihu', label: '知乎' },
]

const LOGIN_OPTIONS = [
  { value: 'qrcode', label: '扫码登录' },
  { value: 'cookie', label: 'Cookie 登录' },
  { value: 'phone', label: '手机号登录' },
]

const VIDEO_UPLOAD_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: 'oss', label: 'OSS URL' },
  { value: 'dashscope', label: 'DashScope SDK' },
  { value: 'openai', label: 'OpenAI Compatible' },
] as const

const WHISPER_MODEL_OPTIONS = [
  { value: 'tiny', label: 'tiny' },
  { value: 'base', label: 'base' },
  { value: 'small', label: 'small' },
  { value: 'medium', label: 'medium' },
  { value: 'turbo', label: 'turbo' },
  { value: 'large-v3', label: 'large-v3' },
] as const

const SOURCE_MODE_OPTIONS = [
  { value: 'creator', label: '创作者' },
  { value: 'search', label: '关键词/视频名' },
  { value: 'ranking', label: '平台榜单' },
] as const

const BILI_RANKING_OPTIONS = [
  { value: 'popular', label: 'B站热门' },
  { value: 'ranking', label: 'B站排行榜' },
] as const

const QWEN_BASE64_RAW_VIDEO_LIMIT_MB = 7
const QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB = 100
const QWEN_PUBLIC_URL_VIDEO_LIMIT_MB = 2048
const QWEN_DASHSCOPE_RETRY_COUNT = 3
const QWEN_VIDEO_COMPRESSION_TARGET_MB = 64

type BadgeVariant = ComponentProps<typeof Badge>['variant']
type TaskWorkflowMode = 'full' | 'metadata_only' | 'selected_items'
type TaskSourceMode = 'creator' | 'search' | 'ranking'

type FieldProps = {
  label: string
  hint?: string
  children: ReactNode
}

function Field({ label, hint, children }: FieldProps) {
  return (
    <div className="space-y-2">
      <div className="space-y-0.5">
        <Label className="text-xs text-cyber-text-secondary font-mono">{label}</Label>
        {hint ? <p className="text-[10px] text-cyber-text-muted leading-snug">{hint}</p> : null}
      </div>
      {children}
    </div>
  )
}

const markdownComponents: Components = {
  h1: ({ children }) => <h4 className="text-sm font-semibold text-cyber-text-primary mt-3 first:mt-0">{children}</h4>,
  h2: ({ children }) => <h4 className="text-sm font-semibold text-cyber-text-primary mt-3 first:mt-0">{children}</h4>,
  h3: ({ children }) => <h5 className="text-xs font-semibold text-cyber-text-primary mt-2.5 first:mt-0">{children}</h5>,
  h4: ({ children }) => <h5 className="text-xs font-semibold text-cyber-text-primary mt-2.5 first:mt-0">{children}</h5>,
  p: ({ children }) => <p className="my-1.5 leading-relaxed">{children}</p>,
  ul: ({ children }) => <ul className="my-1.5 list-disc space-y-1 pl-4">{children}</ul>,
  ol: ({ children }) => <ol className="my-1.5 list-decimal space-y-1 pl-4">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold text-cyber-text-primary">{children}</strong>,
  em: ({ children }) => <em className="text-cyber-text-secondary">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-cyber-neon-cyan underline underline-offset-2 hover:text-cyber-neon-cyanDim"
    >
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-cyber-neon-cyan/50 pl-3 text-cyber-text-secondary">
      {children}
    </blockquote>
  ),
  code: ({ className, children }) => (
    <code className={`${className ?? ''} rounded bg-cyber-bg-secondary px-1 py-0.5 font-mono text-[11px] text-cyber-neon-green`}>
      {children}
    </code>
  ),
  pre: ({ children }) => (
    <pre className="my-2 max-w-full overflow-x-auto rounded-md border border-cyber-border-subtle bg-cyber-bg-secondary p-2 text-[11px] leading-relaxed">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-2 max-w-full overflow-x-auto">
      <table className="w-full border-collapse text-[11px]">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-cyber-border-subtle bg-cyber-bg-secondary px-2 py-1 text-left font-semibold text-cyber-text-primary">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border border-cyber-border-subtle px-2 py-1 align-top">{children}</td>,
  hr: () => <hr className="my-3 border-cyber-border-subtle" />,
}

function MarkdownResult({ value }: { value: string }) {
  return (
    <div className="text-xs leading-relaxed text-cyber-text-primary">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={markdownComponents}>
        {value}
      </ReactMarkdown>
    </div>
  )
}

function todayString() {
  return new Date().toLocaleDateString('sv-SE')
}

function extractErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          const path = Array.isArray(item.loc) ? item.loc.join('.') : item.loc
          return `${path || 'request'}: ${item.msg || JSON.stringify(item)}`
        })
        .join('; ')
    }
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') return JSON.stringify(detail)
    return error.message
  }
  if (error instanceof Error) return error.message
  return String(error)
}

function clampNumber(value: number, min: number, max: number, fallback: number) {
  if (!Number.isFinite(value)) return fallback
  return Math.min(max, Math.max(min, value))
}

function taskBadgeVariant(status?: VideoSummaryTaskStatus['status']): BadgeVariant {
  if (status === 'completed') return 'success'
  if (status === 'running' || status === 'pending') return 'running'
  if (status === 'error') return 'destructive'
  return 'idle'
}

function downloadBadgeVariant(status: string): BadgeVariant {
  if (status === 'downloaded' || status === 'existing') return 'success'
  if (status === 'unsupported') return 'warning'
  if (status === 'failed') return 'destructive'
  return 'secondary'
}

function summaryBadgeVariant(status: string): BadgeVariant {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'destructive'
  return 'secondary'
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

function formatBytes(value?: number | null) {
  if (!value || value <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = value
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }
  return `${size >= 10 || unitIndex === 0 ? size.toFixed(0) : size.toFixed(1)} ${units[unitIndex]}`
}

function formatSpeed(value?: number | null) {
  if (!value || value <= 0) return '-'
  return `${formatBytes(value)}/s`
}

function DownloadProgressView({ progress }: { progress: VideoDownloadProgress }) {
  const percent = progress.percent ?? 0
  const hasTotal = progress.total_bytes !== null && progress.total_bytes > 0
  return (
    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2 text-[11px] font-mono">
        <span className="min-w-0 truncate text-cyber-text-secondary">
          {progress.file_name || progress.item_id || 'video'}
        </span>
        <Badge variant={progress.status === 'completed' ? 'success' : progress.status === 'failed' ? 'destructive' : 'running'}>
          {progress.status}
        </Badge>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-cyber-bg-secondary border border-cyber-border-subtle">
        <div
          className="h-full bg-cyber-neon-cyan transition-all"
          style={{ width: hasTotal ? `${Math.min(100, Math.max(0, percent))}%` : '35%' }}
        />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[10px] text-cyber-text-muted">
        <span>{formatBytes(progress.downloaded_bytes)}{hasTotal ? ` / ${formatBytes(progress.total_bytes)}` : ''}</span>
        <span>{hasTotal ? `${percent.toFixed(1)}%` : '未知总大小'}</span>
        <span>{formatSpeed(progress.speed_bps)}</span>
        <span className="truncate">{progress.message || '-'}</span>
      </div>
    </div>
  )
}

function isBiliDirectCreatorInput(value: string) {
  return /^\d+$/.test(value) || /space\.bilibili\.com\/\d+/.test(value)
}

function normalizeCreatorName(value: string) {
  return value.trim().toLocaleLowerCase()
}

function stringifyCookiePairs(pairs: Array<[string, string]>) {
  const cookieMap = new Map<string, string>()
  pairs.forEach(([rawName, rawValue]) => {
    const name = rawName.trim()
    const value = rawValue.trim()
    if (name) cookieMap.set(name, value)
  })
  return Array.from(cookieMap.entries())
    .map(([name, value]) => `${name}=${value}`)
    .join('; ')
}

function normalizeCookieJsonInput(text: string) {
  try {
    const parsed = JSON.parse(text) as unknown
    const pairs: Array<[string, string]> = []
    const appendArray = (items: unknown[]) => {
      items.forEach((item) => {
        if (!item || typeof item !== 'object') return
        const record = item as Record<string, unknown>
        const name = record.name
        const value = record.value
        if (name !== undefined && value !== undefined) {
          pairs.push([String(name), String(value)])
        }
      })
    }

    if (Array.isArray(parsed)) {
      appendArray(parsed)
    } else if (parsed && typeof parsed === 'object') {
      const record = parsed as Record<string, unknown>
      if (Array.isArray(record.cookies)) {
        appendArray(record.cookies)
      } else {
        Object.entries(record).forEach(([name, value]) => {
          if (['string', 'number', 'boolean'].includes(typeof value)) {
            pairs.push([name, String(value)])
          }
        })
      }
    }

    return stringifyCookiePairs(pairs)
  } catch {
    return ''
  }
}

function normalizeCookieTableInput(text: string) {
  const pairs: Array<[string, string]> = []
  text.split(/\r?\n/).forEach((line) => {
    const columns = line.trim().split('\t').map((part) => part.trim())
    if (columns.length < 2) return
    const [name, value] = columns
    if (name.toLocaleLowerCase() === 'name' && value.toLocaleLowerCase() === 'value') return
    if (name) pairs.push([name, value])
  })
  return stringifyCookiePairs(pairs)
}

function normalizeCookieHeaderInput(text: string) {
  const cookieLine = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find((line) => /^cookie\s*:/i.test(line))
  const header = (cookieLine ? cookieLine.replace(/^cookie\s*:\s*/i, '') : text).trim().replace(/^['"]|['"]$/g, '')
  const pairs: Array<[string, string]> = []
  header.split(';').forEach((part) => {
    const separatorIndex = part.indexOf('=')
    if (separatorIndex <= 0) return
    pairs.push([part.slice(0, separatorIndex), part.slice(separatorIndex + 1)])
  })
  return stringifyCookiePairs(pairs)
}

function normalizeCookieInput(value: string) {
  const text = value.trim()
  if (!text) return ''
  return normalizeCookieJsonInput(text) || normalizeCookieTableInput(text) || normalizeCookieHeaderInput(text)
}

function formatMetric(value: unknown) {
  if (typeof value === 'number') return value.toLocaleString()
  if (typeof value === 'string' && value) return value
  return '-'
}

export function VideoSummaryPanel() {
  const [expanded, setExpanded] = useState(true)
  const [settings, setSettings] = useState<QwenSettings | null>(null)
  const [profiles, setProfiles] = useState<QwenProfile[]>([])
  const [selectedProfileId, setSelectedProfileId] = useState('')
  const [activeProfileId, setActiveProfileId] = useState('')
  const [profileName, setProfileName] = useState('默认配置')
  const [apiKey, setApiKey] = useState('')
  const [clearApiKey, setClearApiKey] = useState(false)
  const [baseUrl, setBaseUrl] = useState('https://dashscope.aliyuncs.com/compatible-mode/v1')
  const [model, setModel] = useState('qwen3.5-omni-plus')
  const [videoUploadBackend, setVideoUploadBackend] = useState<'auto' | 'oss' | 'dashscope' | 'openai'>('auto')
  const [videoFps, setVideoFps] = useState(2)
  const [sampleFrames, setSampleFrames] = useState(8)
  const [maxInlineVideoMb, setMaxInlineVideoMb] = useState(QWEN_BASE64_RAW_VIDEO_LIMIT_MB)
  const [maxDashscopeVideoMb, setMaxDashscopeVideoMb] = useState(QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB)
  const [dashscopeRetryCount, setDashscopeRetryCount] = useState(QWEN_DASHSCOPE_RETRY_COUNT)
  const [enableVideoCompression, setEnableVideoCompression] = useState(true)
  const [compressionTargetMb, setCompressionTargetMb] = useState(QWEN_VIDEO_COMPRESSION_TARGET_MB)
  const [enableWhisperTranscription, setEnableWhisperTranscription] = useState(false)
  const [whisperModel, setWhisperModel] = useState('turbo')
  const [loadingSettings, setLoadingSettings] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [creatingProfile, setCreatingProfile] = useState(false)
  const [activatingProfile, setActivatingProfile] = useState(false)
  const [deletingProfile, setDeletingProfile] = useState(false)

  const [platform, setPlatform] = useState('xhs')
  const [sourceMode, setSourceMode] = useState<TaskSourceMode>('creator')
  const [creatorQuery, setCreatorQuery] = useState('')
  const [searchKeyword, setSearchKeyword] = useState('')
  const [rankingType, setRankingType] = useState('popular')
  const [rankingLimit, setRankingLimit] = useState(5)
  const [candidates, setCandidates] = useState<CreatorCandidate[]>([])
  const [selectedCandidateId, setSelectedCandidateId] = useState('')
  const [resolveMessage, setResolveMessage] = useState('')
  const [resolving, setResolving] = useState(false)

  const [startDate, setStartDate] = useState(todayString())
  const [endDate, setEndDate] = useState(todayString())
  const [maxVideos, setMaxVideos] = useState(20)
  const [crawlSleepSeconds, setCrawlSleepSeconds] = useState(5)
  const [loginType, setLoginType] = useState('qrcode')
  const [cookies, setCookies] = useState('')
  const [headless, setHeadless] = useState(false)
  const [summarize, setSummarize] = useState(true)
  const [starting, setStarting] = useState(false)
  const [taskId, setTaskId] = useState('')
  const [taskStatus, setTaskStatus] = useState<VideoSummaryTaskStatus | null>(null)
  const [stopping, setStopping] = useState(false)
  const [selectedVideoIds, setSelectedVideoIds] = useState<string[]>([])
  const [selectionSeedTaskId, setSelectionSeedTaskId] = useState('')

  const selectedCandidate = useMemo(
    () => candidates.find((candidate) => candidate.id === selectedCandidateId),
    [candidates, selectedCandidateId],
  )
  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.id === selectedProfileId),
    [profiles, selectedProfileId],
  )
  const isTaskRunning = taskStatus?.status === 'running' || taskStatus?.status === 'pending'
  const isSelectedProfileActive = Boolean(selectedProfileId && selectedProfileId === activeProfileId)
  const taskItems = taskStatus?.result?.items ?? []
  const candidateSelectionReady = Boolean(
    taskStatus?.status === 'completed'
    && taskStatus.result?.workflow_mode === 'metadata_only'
    && taskItems.length > 0,
  )

  const applyQwenConfigToForm = (config: QwenSettings | QwenProfile) => {
    setProfileName('profile_name' in config ? config.profile_name : config.name)
    setBaseUrl(config.base_url)
    setModel(config.model)
    setApiKey('')
    setClearApiKey(false)
  }

  const cleanQwenPayload = () => {
    return {
      api_key: apiKey.trim() || undefined,
      name: profileName.trim() || '未命名配置',
      clear_api_key: clearApiKey,
      base_url: baseUrl,
      model,
    }
  }

  const cleanTaskVideoPayload = () => {
    const cleanVideoFps = clampNumber(videoFps, 0.1, 10, 2)
    const cleanSampleFrames = Math.round(clampNumber(sampleFrames, 1, 24, 8))
    const cleanMaxInlineVideoMb = Math.round(
      clampNumber(maxInlineVideoMb, 1, QWEN_BASE64_RAW_VIDEO_LIMIT_MB, QWEN_BASE64_RAW_VIDEO_LIMIT_MB),
    )
    const cleanMaxDashscopeVideoMb = Math.round(
      clampNumber(
        maxDashscopeVideoMb,
        1,
        QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB,
        QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB,
      ),
    )
    const cleanDashscopeRetryCount = Math.round(clampNumber(dashscopeRetryCount, 1, 5, QWEN_DASHSCOPE_RETRY_COUNT))
    const cleanCompressionTargetMb = Math.round(
      clampNumber(
        compressionTargetMb,
        10,
        QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB,
        QWEN_VIDEO_COMPRESSION_TARGET_MB,
      ),
    )
    setVideoFps(cleanVideoFps)
    setSampleFrames(cleanSampleFrames)
    setMaxInlineVideoMb(cleanMaxInlineVideoMb)
    setMaxDashscopeVideoMb(cleanMaxDashscopeVideoMb)
    setDashscopeRetryCount(cleanDashscopeRetryCount)
    setCompressionTargetMb(cleanCompressionTargetMb)
    return {
      video_input_mode: 'auto' as const,
      video_upload_backend: videoUploadBackend,
      video_fps: cleanVideoFps,
      sample_frames: cleanSampleFrames,
      max_inline_video_mb: cleanMaxInlineVideoMb,
      max_dashscope_video_mb: cleanMaxDashscopeVideoMb,
      dashscope_retry_count: cleanDashscopeRetryCount,
      enable_video_compression: enableVideoCompression,
      compression_target_mb: cleanCompressionTargetMb,
      enable_whisper_transcription: enableWhisperTranscription,
      whisper_model: whisperModel,
    }
  }

  useEffect(() => {
    let mounted = true
    setLoadingSettings(true)
    Promise.all([videoSummaryApi.getSettings(), videoSummaryApi.getProfiles()])
      .then(([settingsResponse, profilesResponse]) => {
        if (!mounted) return
        const data = settingsResponse.data
        setSettings(data)
        setProfiles(profilesResponse.data.profiles)
        setActiveProfileId(profilesResponse.data.active_profile_id)
        setSelectedProfileId(data.profile_id)
        applyQwenConfigToForm(data)
      })
      .catch((error: unknown) => {
        toast.error(`读取 Qwen 配置失败: ${extractErrorMessage(error)}`)
      })
      .finally(() => {
        if (mounted) setLoadingSettings(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!taskId || !isTaskRunning) return

    let disposed = false
    const refreshStatus = async () => {
      try {
        const { data } = await videoSummaryApi.getTask(taskId)
        if (!disposed) setTaskStatus(data)
      } catch (error) {
        if (!disposed) toast.error(`刷新视频任务失败: ${extractErrorMessage(error)}`)
      }
    }

    const timer = window.setInterval(() => {
      void refreshStatus()
    }, 2000)
    void refreshStatus()

    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [taskId, isTaskRunning])

  useEffect(() => {
    if (!candidateSelectionReady || !taskStatus?.task_id || selectionSeedTaskId === taskStatus.task_id) return
    setSelectedVideoIds([])
    setSelectionSeedTaskId(taskStatus.task_id)
  }, [candidateSelectionReady, selectionSeedTaskId, taskItems, taskStatus?.task_id])

  const handleSaveSettings = async () => {
    setSavingSettings(true)
    try {
      const payload = cleanQwenPayload()
      if (selectedProfileId) {
        await videoSummaryApi.updateProfile(selectedProfileId, payload)
      } else {
        const { data } = await videoSummaryApi.createProfile(payload)
        setSelectedProfileId(data.id)
      }
      const [{ data: currentSettings }, { data: profileData }] = await Promise.all([
        videoSummaryApi.getSettings(),
        videoSummaryApi.getProfiles(),
      ])
      setSettings(currentSettings)
      setProfiles(profileData.profiles)
      setActiveProfileId(profileData.active_profile_id)
      setApiKey('')
      setClearApiKey(false)
      toast.success('配置档案已保存')
    } catch (error) {
      toast.error(`保存配置档案失败: ${extractErrorMessage(error)}`)
    } finally {
      setSavingSettings(false)
    }
  }

  const handleCreateProfile = async () => {
    setCreatingProfile(true)
    try {
      const payload = {
        ...cleanQwenPayload(),
        name: profileName.trim() ? `${profileName.trim()} 副本` : '新配置',
        api_key: apiKey.trim() || undefined,
      }
      const { data } = await videoSummaryApi.createProfile(payload)
      const { data: profileData } = await videoSummaryApi.getProfiles()
      setProfiles(profileData.profiles)
      setActiveProfileId(profileData.active_profile_id)
      setSelectedProfileId(data.id)
      setSettings(await videoSummaryApi.getSettings().then((response) => response.data))
      applyQwenConfigToForm(data)
      toast.success('配置档案已新增')
    } catch (error) {
      toast.error(`新增配置档案失败: ${extractErrorMessage(error)}`)
    } finally {
      setCreatingProfile(false)
    }
  }

  const handleSelectProfile = (profileId: string) => {
    const profile = profiles.find((item) => item.id === profileId)
    if (!profile) return
    setSelectedProfileId(profileId)
    applyQwenConfigToForm(profile)
  }

  const handleActivateProfile = async () => {
    if (!selectedProfileId) return
    setActivatingProfile(true)
    try {
      const { data } = await videoSummaryApi.activateProfile(selectedProfileId)
      const { data: profileData } = await videoSummaryApi.getProfiles()
      setSettings(data)
      setProfiles(profileData.profiles)
      setActiveProfileId(profileData.active_profile_id)
      applyQwenConfigToForm(data)
      toast.success('默认配置已切换')
    } catch (error) {
      toast.error(`切换默认配置失败: ${extractErrorMessage(error)}`)
    } finally {
      setActivatingProfile(false)
    }
  }

  const handleDeleteProfile = async () => {
    if (!selectedProfileId) return
    const target = selectedProfile
    if (!window.confirm(`删除配置档案「${target?.name ?? selectedProfileId}」？`)) return
    setDeletingProfile(true)
    try {
      const { data } = await videoSummaryApi.deleteProfile(selectedProfileId)
      setProfiles(data.profiles)
      setActiveProfileId(data.active_profile_id)
      const nextProfile = data.profiles.find((profile) => profile.id === data.active_profile_id) ?? data.profiles[0]
      setSelectedProfileId(nextProfile?.id ?? '')
      if (nextProfile) applyQwenConfigToForm(nextProfile)
      setSettings(await videoSummaryApi.getSettings().then((response) => response.data))
      toast.success('配置档案已删除')
    } catch (error) {
      toast.error(`删除配置档案失败: ${extractErrorMessage(error)}`)
    } finally {
      setDeletingProfile(false)
    }
  }

  const handleResolveCreators = async () => {
    if (!creatorQuery.trim()) {
      toast.warning('请先输入创作者用户名、主页链接或 ID')
      return
    }
    setResolving(true)
    try {
      const { data } = await videoSummaryApi.resolveCreators({
        platform,
        query: creatorQuery,
      })
      setCandidates(data.candidates)
      setSelectedCandidateId(data.candidates[0]?.id ?? '')
      setResolveMessage(data.message)
      if (data.candidates.length === 0) {
        toast.warning('没有解析到创作者候选')
      } else {
        toast.success(`解析到 ${data.candidates.length} 个候选`)
      }
    } catch (error) {
      toast.error(`解析创作者失败: ${extractErrorMessage(error)}`)
    } finally {
      setResolving(false)
    }
  }

  const handlePlatformChange = (value: string) => {
    setPlatform(value)
    setCandidates([])
    setSelectedCandidateId('')
    setResolveMessage('')
  }

  const handleFormatCookies = () => {
    const normalizedCookies = normalizeCookieInput(cookies)
    if (!normalizedCookies) {
      toast.warning('没有识别到可用 Cookie')
      return
    }
    setCookies(normalizedCookies)
    toast.success(`已格式化 ${normalizedCookies.split(';').filter(Boolean).length} 个 Cookie`)
  }

  const handleStartTask = async (workflowMode: TaskWorkflowMode = 'full') => {
    const sourceResult = workflowMode === 'selected_items' ? taskStatus?.result : null
    const effectiveSourceMode = (sourceResult?.source_mode ?? sourceMode) as TaskSourceMode
    const effectivePlatform = sourceResult?.platform ?? platform
    const rawCreatorInput = creatorQuery.trim().split(/[\n,]/)[0]?.trim()
    const keywordInput = (sourceResult?.search_keyword || searchKeyword.trim() || rawCreatorInput).trim()
    const cleanRankingLimit = Math.round(clampNumber(rankingLimit, 1, 50, 5))
    let taskCandidate = effectiveSourceMode === 'creator' ? selectedCandidate : undefined
    let creatorId = sourceResult?.creator_id
      || (effectiveSourceMode === 'creator'
        ? taskCandidate?.id || rawCreatorInput
        : effectiveSourceMode === 'search'
          ? keywordInput
          : `ranking:${effectivePlatform}:${rankingType}`)
    if (effectiveSourceMode === 'creator' && !creatorId) {
      toast.warning('请先选择或输入创作者')
      return
    }
    if (effectiveSourceMode === 'search' && !keywordInput) {
      toast.warning('Please enter a keyword or video title')
      return
    }
    if (effectiveSourceMode === 'ranking' && effectivePlatform !== 'bili' && !sourceResult) {
      toast.warning('This platform ranking source is not wired yet; use Search for this platform.')
      return
    }
    setRankingLimit(cleanRankingLimit)
    if (!creatorId) {
      toast.warning('Missing source identifier')
      return
    }
    if (startDate > endDate) {
      toast.warning('开始日期不能晚于结束日期')
      return
    }
    const taskCookies = loginType === 'cookie' ? normalizeCookieInput(cookies) : ''
    if (loginType === 'cookie' && cookies.trim() && !taskCookies) {
      toast.warning('没有识别到可用 Cookie')
      return
    }
    if (taskCookies && taskCookies !== cookies) {
      setCookies(taskCookies)
    }
    if (workflowMode === 'selected_items' && selectedVideoIds.length === 0) {
      toast.warning('请先勾选至少一条候选视频')
      return
    }
    setStarting(true)
    try {
      if (effectiveSourceMode === 'creator' && !taskCandidate && effectivePlatform === 'bili' && rawCreatorInput && !isBiliDirectCreatorInput(rawCreatorInput)) {
        const { data: resolved } = await videoSummaryApi.resolveCreators({
          platform: effectivePlatform,
          query: rawCreatorInput,
        })
        setCandidates(resolved.candidates)
        setResolveMessage(resolved.message)

        const normalizedInput = normalizeCreatorName(rawCreatorInput)
        const exactCandidates = resolved.candidates.filter(
          (candidate) => normalizeCreatorName(candidate.display_name) === normalizedInput,
        )
        if (exactCandidates.length === 1) {
          taskCandidate = exactCandidates[0]
        } else if (resolved.candidates.length === 1) {
          taskCandidate = resolved.candidates[0]
        } else if (resolved.candidates.length === 0) {
          toast.warning('没有搜索到 B 站创作者，请换关键词或粘贴空间链接/UID')
          return
        } else {
          setSelectedCandidateId(resolved.candidates[0]?.id ?? '')
          toast.warning('匹配到多个 B 站创作者，请先在候选列表里选择具体 UID')
          return
        }

        if (!taskCandidate) return
        setSelectedCandidateId(taskCandidate.id)
        creatorId = taskCandidate.id
      }

      const { data } = await videoSummaryApi.startTask({
        platform: effectivePlatform,
        creator_id: creatorId,
        creator_display_name: sourceResult?.creator_display_name
          ?? (effectiveSourceMode === 'creator'
            ? taskCandidate?.display_name ?? ''
            : effectiveSourceMode === 'search'
              ? `Search: ${keywordInput}`
              : `${effectivePlatform} ${rankingType} Top ${cleanRankingLimit}`),
        profile_url: effectiveSourceMode === 'creator' ? taskCandidate?.profile_url ?? '' : '',
        source_mode: effectiveSourceMode,
        search_keyword: effectiveSourceMode === 'search' ? keywordInput : sourceResult?.search_keyword ?? '',
        ranking_type: effectiveSourceMode === 'ranking' ? sourceResult?.ranking_type || rankingType : '',
        ranking_limit: effectiveSourceMode === 'ranking' ? cleanRankingLimit : 5,
        workflow_mode: workflowMode,
        source_task_id: workflowMode === 'selected_items' ? taskStatus?.result?.task_id ?? taskStatus?.task_id ?? null : null,
        selected_item_ids: workflowMode === 'selected_items' ? selectedVideoIds : [],
        login_type: loginType,
        cookies: taskCookies,
        start_date: startDate,
        end_date: endDate,
        max_videos: effectiveSourceMode === 'ranking' ? Math.max(maxVideos, cleanRankingLimit) : maxVideos,
        crawl_concurrency: 1,
        headless,
        crawl_sleep_seconds: crawlSleepSeconds,
        summarize: workflowMode === 'metadata_only' ? false : summarize,
        ...cleanTaskVideoPayload(),
      })
      setTaskId(data.task_id)
      setTaskStatus(data)
      toast.success(workflowMode === 'metadata_only' ? '候选检索任务已启动' : '视频任务已启动')
    } catch (error) {
      toast.error(`启动视频任务失败: ${extractErrorMessage(error)}`)
    } finally {
      setStarting(false)
    }
  }

  const handleStopTask = async () => {
    if (!taskId) return
    setStopping(true)
    try {
      await videoSummaryApi.stopTask(taskId)
      const { data } = await videoSummaryApi.getTask(taskId)
      setTaskStatus(data)
      toast.success('视频任务已停止')
    } catch (error) {
      toast.error(`停止视频任务失败: ${extractErrorMessage(error)}`)
    } finally {
      setStopping(false)
    }
  }

  const handleToggleVideo = (itemId: string, checked: boolean) => {
    setSelectedVideoIds((current) => {
      if (checked) return current.includes(itemId) ? current : [...current, itemId]
      return current.filter((id) => id !== itemId)
    })
  }

  const handleSelectAllVideos = () => {
    setSelectedVideoIds(taskItems.map((item) => item.id))
  }

  const handleClearVideoSelection = () => {
    setSelectedVideoIds([])
  }

  return (
    <section className="rounded-lg glass-panel float-panel overflow-hidden animate-slide-up">
      <header className="px-4 py-3 border-b border-cyber-border-subtle/50 flex items-center gap-3 bg-cyber-bg-tertiary/30">
        <div className="h-8 w-8 rounded-md bg-cyber-bg-tertiary border border-cyber-border-subtle flex items-center justify-center flex-shrink-0">
          <Video className="h-4 w-4 text-cyber-neon-cyan" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-mono font-semibold text-cyber-text-primary tracking-wide">
            创作者视频总结
          </div>
          <div className="text-[10px] text-cyber-text-muted leading-snug truncate">
            用户视频采集、按日期筛选、文本/视频理解
          </div>
        </div>
        <Badge variant={taskBadgeVariant(taskStatus?.status)}>
          {taskStatus?.status ?? 'idle'}
        </Badge>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setExpanded((value) => !value)}
          aria-label={expanded ? '收起视频任务面板' : '展开视频任务面板'}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
      </header>

      {expanded ? (
        <div className="p-4 grid grid-cols-1 xl:grid-cols-[0.95fr_1.05fr] gap-4">
          <div className="space-y-4">
            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 min-w-0">
                  <KeyRound className="h-4 w-4 text-cyber-neon-cyan" />
                  <h3 className="text-xs font-mono font-semibold text-cyber-text-primary">配置管理</h3>
                </div>
                <Badge variant={settings?.api_key_configured ? 'success' : 'warning'}>
                  {selectedProfile?.api_key_configured ? selectedProfile.api_key_masked : settings?.api_key_configured ? settings.api_key_masked : '未配置'}
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr] gap-3">
                <Field label="配置档案" hint="任务会使用标记为默认的配置。">
                  <Select
                    value={selectedProfileId}
                    onValueChange={handleSelectProfile}
                    disabled={loadingSettings || profiles.length === 0}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue placeholder="选择配置档案" />
                    </SelectTrigger>
                    <SelectContent>
                      {profiles.map((profile) => (
                        <SelectItem key={profile.id} value={profile.id}>
                          {profile.name}{profile.active ? ' · 默认' : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="档案名称">
                  <Input
                    value={profileName}
                    onChange={(event) => setProfileName(event.target.value)}
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Field label="API Key">
                  <Input
                    type="password"
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    placeholder={(selectedProfile?.api_key_configured ?? settings?.api_key_configured) ? '留空则保留当前 Key' : 'sk-...'}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="模型">
                  <Input
                    value={model}
                    onChange={(event) => setModel(event.target.value)}
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2.5">
                <Checkbox
                  checked={clearApiKey}
                  onCheckedChange={(checked) => setClearApiKey(checked === true)}
                />
                <span className="text-xs font-mono text-cyber-text-primary">清空当前档案的 API Key</span>
              </label>

              <div className="grid grid-cols-1 gap-3">
                <Field label="Base URL">
                  <Input
                    value={baseUrl}
                    onChange={(event) => setBaseUrl(event.target.value)}
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <Button
                  type="button"
                  onClick={handleSaveSettings}
                  disabled={savingSettings || loadingSettings}
                  className="h-9 text-xs"
                >
                  {savingSettings ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  保存
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCreateProfile}
                  disabled={creatingProfile || loadingSettings}
                  className="h-9 text-xs"
                >
                  {creatingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                  新增
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleActivateProfile}
                  disabled={activatingProfile || loadingSettings || !selectedProfileId || isSelectedProfileActive}
                  className="h-9 text-xs"
                >
                  {activatingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                  设为默认
                </Button>
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleDeleteProfile}
                  disabled={deletingProfile || loadingSettings || profiles.length <= 1}
                  className="h-9 text-xs"
                >
                  {deletingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  删除
                </Button>
              </div>
              {settings?.settings_path ? (
                <div className="text-[10px] text-cyber-text-muted break-all">
                  默认配置：{settings.profile_name}；保存位置：{settings.settings_path}
                </div>
              ) : null}
            </div>

            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-4">
              <div className="flex items-center gap-2">
                <UserRound className="h-4 w-4 text-cyber-neon-cyan" />
                <h3 className="text-xs font-mono font-semibold text-cyber-text-primary">任务配置</h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                <Field label="任务来源">
                  <Select
                    value={sourceMode}
                    onValueChange={(value) => setSourceMode(value as TaskSourceMode)}
                    disabled={isTaskRunning}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SOURCE_MODE_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="平台">
                  <Select value={platform} onValueChange={handlePlatformChange} disabled={isTaskRunning}>
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLATFORM_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="登录方式">
                  <Select value={loginType} onValueChange={setLoginType} disabled={isTaskRunning}>
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {LOGIN_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="最大视频数">
                  <Input
                    type="number"
                    min={1}
                    max={200}
                    value={maxVideos}
                    onChange={(event) => setMaxVideos(parseInt(event.target.value, 10) || 1)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <Field label="创作者" hint="B 站支持用户名搜索；其他平台请使用主页链接或 ID。重名时先搜索再选择具体 UID。">
                <div className="grid grid-cols-[1fr_auto] gap-2">
                  <textarea
                    value={creatorQuery}
                    onChange={(event) => setCreatorQuery(event.target.value)}
                    disabled={isTaskRunning || sourceMode !== 'creator'}
                    placeholder="用户名、https://.../profile/... 或 creator_id"
                    className="min-h-[70px] w-full rounded-md border border-cyber-border-DEFAULT bg-cyber-bg-tertiary px-3 py-2 text-xs font-mono text-cyber-text-primary placeholder:text-cyber-text-muted focus-visible:outline-none focus-visible:border-cyber-neon-cyan/50 focus-visible:shadow-cyber-soft disabled:cursor-not-allowed disabled:opacity-50 transition-all resize-none"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={handleResolveCreators}
                    disabled={resolving || isTaskRunning || sourceMode !== 'creator'}
                    className="h-[70px] w-10"
                    aria-label="解析创作者"
                  >
                    {resolving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                  </Button>
                </div>
              </Field>

              {sourceMode === 'search' ? (
                <Field label="关键词/视频名" hint="复用项目已有 search 爬虫，按所选平台检索候选视频。">
                  <textarea
                    value={searchKeyword}
                    onChange={(event) => setSearchKeyword(event.target.value)}
                    disabled={isTaskRunning}
                    placeholder="关键词、视频标题、话题..."
                    className="min-h-[64px] w-full rounded-md border border-cyber-border-DEFAULT bg-cyber-bg-tertiary px-3 py-2 text-xs font-mono text-cyber-text-primary placeholder:text-cyber-text-muted focus-visible:outline-none focus-visible:border-cyber-neon-cyan/50 focus-visible:shadow-cyber-soft disabled:cursor-not-allowed disabled:opacity-50 transition-all resize-none"
                  />
                </Field>
              ) : null}

              {sourceMode === 'ranking' ? (
                <div className="grid grid-cols-1 md:grid-cols-[1fr_140px] gap-3">
                  <Field label="榜单类型" hint={platform === 'bili' ? '当前接入 B站热门/B站排行榜。' : '该平台榜单源暂未接入，请使用关键词/视频名。'}>
                    <Select value={rankingType} onValueChange={setRankingType} disabled={isTaskRunning || platform !== 'bili'}>
                      <SelectTrigger className="h-9 text-xs">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {BILI_RANKING_OPTIONS.map((option) => (
                          <SelectItem key={option.value} value={option.value}>
                            {option.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field label="Top N">
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      value={rankingLimit}
                      onChange={(event) => setRankingLimit(parseInt(event.target.value, 10) || 5)}
                      disabled={isTaskRunning}
                      className="h-9 text-xs"
                    />
                  </Field>
                </div>
              ) : null}

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Field label="开始日期">
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(event) => setStartDate(event.target.value)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="结束日期">
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(event) => setEndDate(event.target.value)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="采集间隔秒数">
                  <Input
                    type="number"
                    min={0}
                    max={120}
                    step={0.5}
                    value={crawlSleepSeconds}
                    onChange={(event) => setCrawlSleepSeconds(parseFloat(event.target.value) || 0)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <Field label="视频理解模式" hint="统一使用智能模式：优先直传视频，失败后用带时间戳抽帧回退，并融合可用文本上下文。">
                  <Input
                    value="智能模式"
                    readOnly
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="上传后端" hint="Auto 会优先 DashScope SDK 本地直传，再回落到兼容接口。">
                  <Select
                    value={videoUploadBackend}
                    onValueChange={(value) => setVideoUploadBackend(value as 'auto' | 'dashscope' | 'openai')}
                    disabled={isTaskRunning}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {VIDEO_UPLOAD_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="抽帧数">
                  <Input
                    type="number"
                    min={1}
                    max={24}
                    value={sampleFrames}
                    onChange={(event) => setSampleFrames(parseInt(event.target.value, 10) || 8)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="视频 FPS">
                  <Input
                    type="number"
                    min={0.1}
                    max={10}
                    step={0.1}
                    value={videoFps}
                    onChange={(event) => setVideoFps(parseFloat(event.target.value) || 2)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="Base64 上限 MB" hint="官方限制为编码后小于 10MB，原始视频按 7MB 控制。">
                  <Input
                    type="number"
                    min={1}
                    max={QWEN_BASE64_RAW_VIDEO_LIMIT_MB}
                    value={maxInlineVideoMb}
                    onChange={(event) => setMaxInlineVideoMb(parseInt(event.target.value, 10) || QWEN_BASE64_RAW_VIDEO_LIMIT_MB)}
                    disabled={isTaskRunning}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="DashScope 本地上限 MB" hint={`本地文件路径最大 ${QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB}MB；OSS 公网签名 URL 最大 ${QWEN_PUBLIC_URL_VIDEO_LIMIT_MB}MB。`}>
                  <Input
                    type="number"
                    min={1}
                    max={QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB}
                    value={maxDashscopeVideoMb}
                    onChange={(event) => setMaxDashscopeVideoMb(parseInt(event.target.value, 10) || QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB)}
                    disabled={isTaskRunning || videoUploadBackend === 'openai'}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="SDK 重试次数">
                  <Input
                    type="number"
                    min={1}
                    max={5}
                    value={dashscopeRetryCount}
                    onChange={(event) => setDashscopeRetryCount(parseInt(event.target.value, 10) || QWEN_DASHSCOPE_RETRY_COUNT)}
                    disabled={isTaskRunning || videoUploadBackend === 'openai'}
                    className="h-9 text-xs"
                  />
                </Field>
                <Field label="压缩目标 MB" hint="仅压缩上传给模型的临时副本，不改原始视频。">
                  <Input
                    type="number"
                    min={10}
                    max={QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB}
                    value={compressionTargetMb}
                    onChange={(event) => setCompressionTargetMb(parseInt(event.target.value, 10) || QWEN_VIDEO_COMPRESSION_TARGET_MB)}
                    disabled={
                      isTaskRunning
                      || videoUploadBackend === 'openai'
                      || !enableVideoCompression
                    }
                    className="h-9 text-xs"
                  />
                </Field>
              </div>

              <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2.5">
                <Checkbox
                  checked={enableVideoCompression}
                  onCheckedChange={(checked) => setEnableVideoCompression(checked === true)}
                  disabled={isTaskRunning || videoUploadBackend === 'openai'}
                />
                <span className="text-xs font-mono text-cyber-text-primary">DashScope 上传前自动压缩大视频</span>
              </label>

              <div className="grid grid-cols-1 md:grid-cols-[1fr_180px] gap-3">
                <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2.5">
                  <Checkbox
                    checked={enableWhisperTranscription}
                    onCheckedChange={(checked) => setEnableWhisperTranscription(checked === true)}
                    disabled={isTaskRunning}
                  />
                  <span className="text-xs font-mono text-cyber-text-primary">融合 Whisper 转录</span>
                </label>
                <Field label="Whisper 模型" hint="用于补充字幕或平台文本不足的视频；需要本地安装 ffmpeg 和 Whisper 包。">
                  <Select
                    value={whisperModel}
                    onValueChange={setWhisperModel}
                    disabled={isTaskRunning || !enableWhisperTranscription}
                  >
                    <SelectTrigger className="h-9 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {WHISPER_MODEL_OPTIONS.map((option) => (
                        <SelectItem key={option.value} value={option.value}>
                          {option.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </div>

              {loginType === 'cookie' ? (
                <Field label="Cookies" hint="可粘贴 Cookie Header、DevTools 表格或 Cookie-Editor JSON。">
                  <div className="space-y-2">
                    <textarea
                      value={cookies}
                      onChange={(event) => setCookies(event.target.value)}
                      disabled={isTaskRunning}
                      placeholder="SESSDATA=...; bili_jct=... 或直接粘贴 DevTools Cookies 表格"
                      className="min-h-[88px] w-full rounded-md border border-cyber-border-DEFAULT bg-cyber-bg-tertiary px-3 py-2 text-xs font-mono text-cyber-text-primary placeholder:text-cyber-text-muted focus-visible:outline-none focus-visible:border-cyber-neon-cyan/50 focus-visible:shadow-cyber-soft disabled:cursor-not-allowed disabled:opacity-50 transition-all resize-none"
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleFormatCookies}
                      disabled={isTaskRunning || !cookies.trim()}
                      className="h-8 text-xs font-mono"
                    >
                      <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
                      格式化 Cookie
                    </Button>
                  </div>
                </Field>
              ) : null}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2.5">
                  <Checkbox
                    checked={headless}
                    onCheckedChange={(checked) => setHeadless(checked === true)}
                    disabled={isTaskRunning}
                  />
                  <span className="text-xs font-mono text-cyber-text-primary">无头浏览器</span>
                </label>
                <label className="flex items-center gap-3 rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2.5">
                  <Checkbox
                    checked={summarize}
                    onCheckedChange={(checked) => setSummarize(checked === true)}
                    disabled={isTaskRunning}
                  />
                  <span className="text-xs font-mono text-cyber-text-primary">Qwen 总结</span>
                </label>
              </div>

              {isTaskRunning ? (
                <Button
                  type="button"
                  variant="destructive"
                  onClick={handleStopTask}
                  disabled={stopping}
                  className="w-full h-10 text-xs"
                >
                  {stopping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
                  停止视频任务
                </Button>
              ) : (
                <Button
                  type="button"
                  onClick={() => handleStartTask('metadata_only')}
                  disabled={starting}
                  className="w-full h-10 text-xs"
                >
                  {starting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                  启动任务
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-4">
            {sourceMode === 'creator' ? (
            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-cyber-neon-cyan" />
                  <h3 className="text-xs font-mono font-semibold text-cyber-text-primary">候选创作者</h3>
                </div>
                <Badge variant="secondary">{candidates.length}</Badge>
              </div>

              {resolveMessage ? (
                <div className="text-[11px] leading-snug text-cyber-text-secondary border border-cyber-border-subtle bg-cyber-bg-tertiary/40 rounded-md p-2">
                  {resolveMessage}
                </div>
              ) : null}

              <div className="space-y-2 max-h-64 overflow-y-auto pr-1 rounded-md">
                {candidates.length === 0 ? (
                  <div className="min-h-14 py-4 rounded-lg border border-dashed border-cyber-border-subtle flex items-center justify-center text-xs text-cyber-text-muted">
                    暂无候选
                  </div>
                ) : (
                  candidates.map((candidate) => (
                    <button
                      key={`${candidate.platform}-${candidate.id}`}
                      type="button"
                      onClick={() => setSelectedCandidateId(candidate.id)}
                      disabled={isTaskRunning}
                      className={`w-full rounded-lg border p-3 text-left transition-all ${
                        selectedCandidateId === candidate.id
                          ? 'border-cyber-neon-cyan bg-cyber-neon-cyan/10'
                          : 'border-cyber-border-subtle bg-cyber-bg-tertiary/30 hover:border-cyber-neon-cyan/40'
                      }`}
                    >
                      <div className="flex items-start gap-3 min-w-0">
                        <UserRound className="h-4 w-4 mt-0.5 text-cyber-text-secondary flex-shrink-0" />
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="text-xs font-mono text-cyber-text-primary truncate">
                            {candidate.display_name}
                          </div>
                          <div className="text-[10px] text-cyber-text-muted break-all">
                            {candidate.profile_url || candidate.id}
                          </div>
                          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-cyber-text-muted">
                            <span>UID: {candidate.metrics.parsed_id ? String(candidate.metrics.parsed_id) : candidate.id}</span>
                            {candidate.metrics.fans !== undefined ? (
                              <span>粉丝: {formatMetric(candidate.metrics.fans)}</span>
                            ) : null}
                            {candidate.metrics.videos !== undefined ? (
                              <span>视频: {formatMetric(candidate.metrics.videos)}</span>
                            ) : null}
                          </div>
                          {candidate.description ? (
                            <div className="text-[10px] text-cyber-text-secondary line-clamp-2">
                              {candidate.description}
                            </div>
                          ) : null}
                        </div>
                        {selectedCandidateId === candidate.id ? (
                          <CheckCircle2 className="h-4 w-4 text-cyber-neon-green flex-shrink-0" />
                        ) : null}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
            ) : (
            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4 text-cyber-neon-cyan" />
                  <h3 className="text-xs font-mono font-semibold text-cyber-text-primary">任务来源</h3>
                </div>
                <Badge variant="secondary">{sourceMode}</Badge>
              </div>
              <div className="text-[11px] leading-relaxed text-cyber-text-secondary border border-cyber-border-subtle bg-cyber-bg-tertiary/40 rounded-md p-3">
                {sourceMode === 'search'
                  ? '关键词/视频名会复用项目已有 search 模块。先启动任务获取候选视频，再勾选需要下载和总结的视频。'
                  : platform === 'bili'
                    ? 'B站榜单已接入当前平台榜单接口。先启动任务获取 Top N 候选视频，再勾选需要下载和总结的视频。'
                    : '该平台榜单源暂未接入。请先使用关键词/视频名，或继续补充该平台专用榜单抓取器。'}
              </div>
            </div>
            )}

            <div className="rounded-lg border border-cyber-border-subtle bg-cyber-bg-tertiary/20 p-4 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-cyber-neon-cyan" />
                  <h3 className="text-xs font-mono font-semibold text-cyber-text-primary">任务结果</h3>
                </div>
                {taskStatus ? <Badge variant={taskBadgeVariant(taskStatus.status)}>{taskStatus.status}</Badge> : null}
              </div>

              {!taskStatus ? (
                <div className="min-h-16 py-4 rounded-lg border border-dashed border-cyber-border-subtle flex items-center justify-center text-xs text-cyber-text-muted">
                  暂无任务
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2">
                      <div className="text-[10px] text-cyber-text-muted">任务 ID</div>
                      <div className="text-xs font-mono text-cyber-text-primary truncate">{taskStatus.task_id}</div>
                    </div>
                    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2">
                      <div className="text-[10px] text-cyber-text-muted">记录</div>
                      <div className="text-xs font-mono text-cyber-text-primary">
                        {taskStatus.result?.total_records ?? 0}
                      </div>
                    </div>
                    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2">
                      <div className="text-[10px] text-cyber-text-muted">匹配视频</div>
                      <div className="text-xs font-mono text-cyber-text-primary">
                        {taskStatus.result?.matched_videos ?? 0}
                      </div>
                    </div>
                    <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-2">
                      <div className="text-[10px] text-cyber-text-muted">已总结</div>
                      <div className="text-xs font-mono text-cyber-text-primary">
                        {taskStatus.result?.summarized_videos ?? 0}
                      </div>
                    </div>
                  </div>

                  <div className="rounded-md border border-cyber-border-subtle bg-cyber-bg-tertiary/30 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-xs font-mono text-cyber-text-secondary">
                      {isTaskRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CalendarDays className="h-3.5 w-3.5" />}
                      {taskStatus.progress_message || '等待状态'}
                    </div>
                    <div className="text-[10px] text-cyber-text-muted">
                      {formatDateTime(taskStatus.started_at)} - {formatDateTime(taskStatus.completed_at)}
                    </div>
                    {taskStatus.error_message ? (
                      <div className="flex items-start gap-2 rounded-md border border-cyber-neon-orange/30 bg-cyber-neon-orange/10 p-2 text-[11px] text-cyber-neon-orange">
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                        <span>{taskStatus.error_message}</span>
                      </div>
                    ) : null}
                    {taskStatus.download_progress ? (
                      <DownloadProgressView progress={taskStatus.download_progress} />
                    ) : null}
                  </div>

                  {taskStatus.result?.aggregate_summary ? (
                    <div className="rounded-md border border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 p-3">
                      <div className="text-[10px] font-mono text-cyber-neon-cyan mb-2">整体总结</div>
                      <MarkdownResult value={taskStatus.result.aggregate_summary} />
                    </div>
                  ) : null}

                  {candidateSelectionReady ? (
                    <div className="rounded-md border border-cyber-neon-cyan/30 bg-cyber-neon-cyan/10 p-3 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <ListChecks className="h-4 w-4 text-cyber-neon-cyan" />
                          <div>
                            <div className="text-xs font-mono text-cyber-text-primary">候选视频</div>
                            <div className="text-[10px] text-cyber-text-muted">已选 {selectedVideoIds.length} / {taskItems.length}</div>
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Button type="button" variant="outline" size="sm" className="h-7 text-[11px]" onClick={handleSelectAllVideos}>
                            全选
                          </Button>
                          <Button type="button" variant="outline" size="sm" className="h-7 text-[11px]" onClick={handleClearVideoSelection}>
                            清空
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            className="h-7 text-[11px]"
                            disabled={starting || selectedVideoIds.length === 0}
                            onClick={() => handleStartTask('selected_items')}
                          >
                            <Download className="h-3.5 w-3.5" />
                            下载并总结
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {taskStatus.result?.items?.length ? (
                    <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1 rounded-md">
                      {taskStatus.result.items.map((item) => (
                        <div
                          key={item.id}
                          className={`rounded-md border p-3 space-y-2 transition-all ${
                            candidateSelectionReady && selectedVideoIds.includes(item.id)
                              ? 'border-cyber-neon-cyan bg-cyber-neon-cyan/10'
                              : 'border-cyber-border-subtle bg-cyber-bg-tertiary/30'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-2">
                            {candidateSelectionReady ? (
                              <Checkbox
                                checked={selectedVideoIds.includes(item.id)}
                                onCheckedChange={(checked) => handleToggleVideo(item.id, checked === true)}
                                className="mt-0.5"
                              />
                            ) : null}
                            <div className="min-w-0 flex-1">
                              <div className="text-xs font-mono text-cyber-text-primary truncate">
                                {item.title || item.id}
                              </div>
                              <div className="text-[10px] text-cyber-text-muted">
                                {formatDateTime(item.published_at)}
                              </div>
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              {candidateSelectionReady ? (
                                <Badge variant={selectedVideoIds.includes(item.id) ? 'running' : 'secondary'}>
                                  候选
                                </Badge>
                              ) : (
                                <>
                                  <Badge variant={downloadBadgeVariant(item.download_status)}>
                                    <Download className="h-3 w-3 mr-1" />
                                    {item.download_status}
                                  </Badge>
                                  <Badge variant={summaryBadgeVariant(item.summary_status)}>
                                    {item.summary_status}
                                  </Badge>
                                  {item.analysis_mode !== 'none' ? (
                                    <Badge variant="outline">{item.analysis_mode}</Badge>
                                  ) : null}
                                </>
                              )}
                            </div>
                          </div>
                          {item.video_path ? (
                            <div className="text-[10px] text-cyber-text-muted break-all">{item.video_path}</div>
                          ) : null}
                          {item.summary ? (
                            <MarkdownResult value={item.summary} />
                          ) : null}
                          {item.error ? (
                            <div className="text-[10px] text-cyber-neon-orange leading-snug">{item.error}</div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}

                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
