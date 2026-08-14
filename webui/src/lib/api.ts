import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface CrawlerConfig {
  platform: string
  login_type: string
  crawler_type: string
  keywords: string
  start_page: number
  enable_comments: boolean
  enable_sub_comments: boolean
  save_option: string
  cookies: string
  headless: boolean
}

export interface CrawlerStatus {
  status: 'idle' | 'running' | 'stopping' | 'error'
  platform: string | null
  crawler_type: string | null
  started_at: string | null
  error_message: string | null
}

export interface LogEntry {
  id: number
  timestamp: string
  level: 'info' | 'warning' | 'error' | 'success' | 'debug'
  message: string
}

export interface DataFile {
  name: string
  path: string
  size: number
  modified_at: number
  record_count: number | null
  type: string
  category?: string | null
  source_area?: string | null
  platform?: string | null
}

export interface FilePreviewResponse {
  data: Record<string, unknown>[] | Record<string, unknown>
  total: number
  columns?: string[]
}

export interface Platform {
  value: string
  label: string
  icon: string
}

export interface ConfigOption {
  value: string
  label: string
}

export interface QwenSettings {
  profile_id: string
  profile_name: string
  api_key_configured: boolean
  api_key_masked: string | null
  api_provider: 'dashscope' | 'openai_compatible' | 'ollama'
  base_url: string
  model: string
  local_download_root: string
  video_input_mode: 'auto' | 'video' | 'frames' | 'text_first'
  video_upload_backend: 'auto' | 'oss' | 'dashscope' | 'openai'
  video_fps: number
  sample_frames: number
  max_inline_video_mb: number
  max_dashscope_video_mb: number
  oss_enabled: boolean
  oss_access_key_id_configured: boolean
  oss_access_key_id_masked: string | null
  oss_access_key_secret_configured: boolean
  oss_access_key_secret_masked: string | null
  oss_bucket: string
  oss_endpoint: string
  oss_region: string
  oss_prefix: string
  oss_url_expires_seconds: number
  oss_cleanup_after_analysis: boolean
  settings_path: string
}

export interface QwenSettingsPayload {
  api_key?: string
  api_provider?: 'dashscope' | 'openai_compatible' | 'ollama'
  base_url: string
  model: string
  local_download_root?: string
  oss_enabled?: boolean
  oss_access_key_id?: string
  oss_access_key_secret?: string
  oss_bucket?: string
  oss_endpoint?: string
  oss_region?: string
  oss_prefix?: string
  oss_url_expires_seconds?: number
  oss_cleanup_after_analysis?: boolean
}

export interface QwenProfile {
  id: string
  name: string
  active: boolean
  api_key_configured: boolean
  api_key_masked: string | null
  api_provider: 'dashscope' | 'openai_compatible' | 'ollama'
  base_url: string
  model: string
  local_download_root: string
  video_input_mode: 'auto' | 'video' | 'frames' | 'text_first'
  video_upload_backend: 'auto' | 'oss' | 'dashscope' | 'openai'
  video_fps: number
  sample_frames: number
  max_inline_video_mb: number
  max_dashscope_video_mb: number
  oss_enabled: boolean
  oss_access_key_id_configured: boolean
  oss_access_key_id_masked: string | null
  oss_access_key_secret_configured: boolean
  oss_access_key_secret_masked: string | null
  oss_bucket: string
  oss_endpoint: string
  oss_region: string
  oss_prefix: string
  oss_url_expires_seconds: number
  oss_cleanup_after_analysis: boolean
  created_at: string
  updated_at: string
}

export interface QwenProfileSecret extends QwenProfile {
  api_key: string
  oss_access_key_id: string
  oss_access_key_secret: string
}

export interface QwenProfilePayload extends QwenSettingsPayload {
  name: string
  clear_api_key?: boolean
  clear_oss_access_key?: boolean
}

export interface QwenProfilesResponse {
  active_profile_id: string
  profiles: QwenProfile[]
  settings_path: string
}

export interface PlatformCredential {
  id: string
  platform: string
  name: string
  active: boolean
  cookies_configured: boolean
  cookies_masked: string | null
  login_method: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface PlatformCredentialSecret extends PlatformCredential {
  cookies: string
}

export interface PlatformCredentialHealth {
  profile_id: string
  platform: string
  status: 'ok' | 'warning' | 'error'
  checked_at: string
  message: string
  cookie_count: number
  present_keys: string[]
  missing_required_keys: string[]
  missing_recommended_keys: string[]
  live_probe_supported: boolean
  live_probe_ok: boolean | null
  probe_url: string
  http_status: number | null
  authenticated: boolean | null
  details: Record<string, unknown>
}

export interface PlatformCredentialSelfTest {
  profile_id: string
  platform: string
  status: 'ok' | 'warning' | 'error'
  checked_at: string
  message: string
  health: PlatformCredentialHealth
  task_id: string | null
  task_status: 'pending' | 'running' | 'completed' | 'error' | null
  source_mode: 'creator' | 'search' | 'ranking'
  probe_keyword: string
  total_records: number
  matched_videos: number
  item_count: number
  wall_seconds: number | null
  error_message: string | null
  logs_tail: string[]
}

export interface PlatformCredentialPayload {
  platform: string
  name: string
  cookies?: string | null
  clear_cookies?: boolean
  login_method?: string
  metadata?: Record<string, unknown>
}

export interface PlatformCredentialsResponse {
  active_by_platform: Record<string, string>
  profiles: PlatformCredential[]
  settings_path: string
}

export interface PlatformQrcodeLoginPayload {
  platform: string
  name: string
  profile_id?: string | null
  headless?: boolean
}

export interface PlatformQrcodeLoginStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'error'
  platform: string
  profile_id: string | null
  started_at: string
  completed_at: string | null
  progress_message: string
  logs: string[]
  error_message: string | null
  credential: PlatformCredential | null
  cookie_count: number
  cookie_keys: string[]
  browser_data_dir: string
}

export interface CreatorCandidate {
  id: string
  platform: string
  display_name: string
  avatar_url: string
  profile_url: string
  description: string
  follower_count: number | null
  video_count: number | null
  verified: boolean
  verification: string
  metrics: Record<string, unknown>
  raw: Record<string, unknown>
}

export interface CreatorResolvePayload {
  platform: string
  query: string
}

export interface CreatorResolveResponse {
  candidates: CreatorCandidate[]
  message: string
  needs_manual_id: boolean
}

export interface VideoSummaryTaskPayload {
  platform: string
  creator_id: string
  creator_display_name?: string
  profile_url?: string
  source_mode?: 'creator' | 'search' | 'ranking'
  search_keyword?: string
  ranking_type?: string
  ranking_limit?: number
  credential_profile_id?: string | null
  workflow_mode?: 'full' | 'metadata_only' | 'selected_items'
  source_task_id?: string | null
  selected_item_ids?: string[]
  login_type: string
  cookies?: string
  start_date: string
  end_date: string
  max_crawl_items: number
  max_videos: number
  crawl_concurrency: number
  analysis_concurrency: number
  headless: boolean
  crawl_sleep_seconds: number
  crawl_min_sleep_seconds?: number
  crawl_max_sleep_seconds?: number
  crawl_long_pause_every?: number
  crawl_long_pause_min_seconds?: number
  crawl_long_pause_max_seconds?: number
  summarize: boolean
  video_input_mode: 'auto' | 'video' | 'frames' | 'text_first'
  video_upload_backend: 'auto' | 'oss' | 'dashscope' | 'openai'
  video_fps: number
  sample_frames: number
  max_inline_video_mb: number
  max_dashscope_video_mb: number
  dashscope_retry_count: number
  enable_video_compression: boolean
  compression_target_mb: number
  enable_whisper_transcription: boolean
  whisper_model: string
}

export interface VideoSummaryItem {
  id: string
  title: string
  desc: string
  url: string
  published_at: string | null
  video_path: string | null
  download_status: 'downloaded' | 'existing' | 'missing' | 'unsupported' | 'failed' | 'skipped'
  summary_status: 'completed' | 'skipped' | 'failed'
  analysis_mode: 'none' | 'video' | 'source_url_video' | 'remote_oss_video' | 'oss_video' | 'dashscope_video' | 'base64_video' | 'frames' | 'text' | 'whisper_text'
  summary: string
  error: string
  raw: Record<string, unknown>
}

export interface VideoDownloadProgress {
  status: 'idle' | 'downloading' | 'completed' | 'failed' | 'skipped'
  platform: string
  item_id: string
  file_name: string
  downloaded_bytes: number
  total_bytes: number | null
  speed_bps: number
  percent: number | null
  started_at: string | null
  updated_at: string | null
  message: string
}

export interface VideoTaskStep {
  id: string
  label: string
  phase: string
  item_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped'
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  progress_percent: number | null
  transferred_bytes: number
  total_bytes: number | null
  speed_bps: number
  message: string
}

export interface VideoSummaryResult {
  task_id: string
  platform: string
  creator_id: string
  creator_display_name: string
  source_mode: 'creator' | 'search' | 'ranking'
  search_keyword: string
  ranking_type: string
  workflow_mode: 'full' | 'metadata_only' | 'selected_items'
  date_range: Record<string, string>
  output_dir: string
  local_download_dir: string
  total_records: number
  matched_videos: number
  summarized_videos: number
  aggregate_summary: string
  items: VideoSummaryItem[]
}

export interface VideoSummaryTaskStatus {
  task_id: string
  status: 'pending' | 'running' | 'completed' | 'error'
  platform: string
  creator_id: string
  source_mode: 'creator' | 'search' | 'ranking'
  started_at: string
  completed_at: string | null
  local_download_dir: string
  progress_message: string
  download_progress: VideoDownloadProgress | null
  subtasks: VideoTaskStep[]
  logs: string[]
  result: VideoSummaryResult | null
  error_message: string | null
}

// API functions
export const crawlerApi = {
  start: (config: CrawlerConfig) => api.post('/crawler/start', config),
  stop: () => api.post('/crawler/stop'),
  getStatus: () => api.get<CrawlerStatus>('/crawler/status'),
  getLogs: (limit = 100) => api.get<{ logs: LogEntry[] }>('/crawler/logs', { params: { limit } }),
}

export const dataApi = {
  getFiles: (platform?: string, fileType?: string) =>
    api.get<{ files: DataFile[] }>('/data/files', { params: { platform, file_type: fileType } }),
  getFileContent: (path: string, limit = 100) =>
    api.get<FilePreviewResponse>('/data/files/' + encodePath(path), { params: { preview: true, limit } }),
  getStats: () => api.get('/data/stats'),
  getDownloadUrl: (path: string) => `/api/data/download/${encodePath(path)}`,
}

function encodePath(path: string) {
  return path.split(/[\\/]+/).map(encodeURIComponent).join('/')
}

export const configApi = {
  getPlatforms: () => api.get<{ platforms: Platform[] }>('/config/platforms'),
  getOptions: () =>
    api.get<{
      login_types: ConfigOption[]
      crawler_types: ConfigOption[]
      save_options: ConfigOption[]
    }>('/config/options'),
}

export const videoSummaryApi = {
  getSettings: () => api.get<QwenSettings>('/video-summary/settings'),
  saveSettings: (payload: QwenSettingsPayload) =>
    api.post<QwenSettings>('/video-summary/settings', payload),
  getProfiles: () => api.get<QwenProfilesResponse>('/video-summary/settings/profiles'),
  getProfileSecret: (profileId: string) =>
    api.get<QwenProfileSecret>(`/video-summary/settings/profiles/${profileId}/secret`),
  createProfile: (payload: QwenProfilePayload) =>
    api.post<QwenProfile>('/video-summary/settings/profiles', payload),
  updateProfile: (profileId: string, payload: QwenProfilePayload) =>
    api.put<QwenProfile>(`/video-summary/settings/profiles/${profileId}`, payload),
  deleteProfile: (profileId: string) =>
    api.delete<QwenProfilesResponse>(`/video-summary/settings/profiles/${profileId}`),
  activateProfile: (profileId: string) =>
    api.post<QwenSettings>(`/video-summary/settings/profiles/${profileId}/activate`),
  getPlatformCredentials: () =>
    api.get<PlatformCredentialsResponse>('/video-summary/platform-credentials'),
  getPlatformCredentialSecret: (profileId: string) =>
    api.get<PlatformCredentialSecret>(`/video-summary/platform-credentials/${profileId}/secret`),
  checkPlatformCredentialHealth: (profileId: string) =>
    api.post<PlatformCredentialHealth>(`/video-summary/platform-credentials/${profileId}/health`),
  selfTestPlatformCredential: (profileId: string) =>
    api.post<PlatformCredentialSelfTest>(`/video-summary/platform-credentials/${profileId}/self-test`, undefined, { timeout: 150000 }),
  createPlatformCredential: (payload: PlatformCredentialPayload) =>
    api.post<PlatformCredential>('/video-summary/platform-credentials', payload),
  updatePlatformCredential: (profileId: string, payload: PlatformCredentialPayload) =>
    api.put<PlatformCredential>(`/video-summary/platform-credentials/${profileId}`, payload),
  deletePlatformCredential: (profileId: string) =>
    api.delete<PlatformCredentialsResponse>(`/video-summary/platform-credentials/${profileId}`),
  activatePlatformCredential: (profileId: string) =>
    api.post<PlatformCredential>(`/video-summary/platform-credentials/${profileId}/activate`),
  startPlatformQrcodeLogin: (payload: PlatformQrcodeLoginPayload) =>
    api.post<PlatformQrcodeLoginStatus>('/video-summary/platform-credentials/qrcode-login/start', payload),
  getPlatformQrcodeLogin: (taskId: string) =>
    api.get<PlatformQrcodeLoginStatus>(`/video-summary/platform-credentials/qrcode-login/${taskId}`),
  resolveCreators: (payload: CreatorResolvePayload) =>
    api.post<CreatorResolveResponse>('/video-summary/creators/resolve', payload),
  startTask: (payload: VideoSummaryTaskPayload) =>
    api.post<VideoSummaryTaskStatus>('/video-summary/tasks/start', payload),
  getTask: (taskId: string) =>
    api.get<VideoSummaryTaskStatus>(`/video-summary/tasks/${taskId}`),
  openTaskDownloadDir: (taskId: string, path = '') =>
    api.post<{ status: string; path: string }>(
      `/video-summary/tasks/${taskId}/open-download-dir`,
      path ? { path } : {},
    ),
  stopTask: (taskId: string) =>
    api.post(`/video-summary/tasks/${taskId}/stop`),
  resumeTask: (taskId: string) =>
    api.post<VideoSummaryTaskStatus>(`/video-summary/tasks/${taskId}/resume`),
}

export interface EnvCheckResult {
  success: boolean
  message: string
  output?: string
  error?: string
}

export const envApi = {
  check: () => api.get<EnvCheckResult>('/env/check'),
}

export default api
