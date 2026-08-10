# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .crawler import LoginTypeEnum, PlatformEnum

VideoInputMode = Literal["auto", "video", "frames", "text_first"]
VideoUploadBackend = Literal["auto", "oss", "dashscope", "openai"]
VideoAnalysisApiProvider = Literal["dashscope", "openai_compatible"]
VideoTaskWorkflowMode = Literal["full", "metadata_only", "selected_items"]
VideoTaskSourceMode = Literal["creator", "search", "ranking"]
DownloadStatus = Literal["downloaded", "existing", "missing", "unsupported", "failed", "skipped"]
SummaryStatus = Literal["completed", "skipped", "failed"]
AnalysisMode = Literal["none", "video", "source_url_video", "remote_oss_video", "oss_video", "dashscope_video", "base64_video", "frames", "text", "whisper_text"]
DownloadProgressStatus = Literal["idle", "downloading", "completed", "failed", "skipped"]
VideoTaskStepStatus = Literal["pending", "running", "completed", "failed", "skipped"]

QWEN_BASE64_RAW_VIDEO_LIMIT_MB = 7
QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB = 100
QWEN_DASHSCOPE_RETRY_COUNT = 3
QWEN_VIDEO_COMPRESSION_TARGET_MB = 64


class QwenSettingsRequest(BaseModel):
    api_key: Optional[str] = None
    api_provider: VideoAnalysisApiProvider = "dashscope"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-omni-plus"
    oss_enabled: bool = False
    oss_access_key_id: Optional[str] = None
    oss_access_key_secret: Optional[str] = None
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_region: str = ""
    oss_prefix: str = "mediacrawler/video-summary"
    oss_url_expires_seconds: int = Field(default=7200, ge=300, le=604800)
    oss_cleanup_after_analysis: Optional[bool] = None


class QwenSettingsResponse(BaseModel):
    profile_id: str = "default"
    profile_name: str = "默认配置"
    api_key_configured: bool = False
    api_key_masked: Optional[str] = None
    api_provider: VideoAnalysisApiProvider = "dashscope"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-omni-plus"
    video_input_mode: VideoInputMode = "auto"
    video_upload_backend: VideoUploadBackend = "auto"
    video_fps: float = 2.0
    sample_frames: int = 8
    max_inline_video_mb: int = QWEN_BASE64_RAW_VIDEO_LIMIT_MB
    max_dashscope_video_mb: int = QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB
    oss_enabled: bool = False
    oss_access_key_id_configured: bool = False
    oss_access_key_id_masked: Optional[str] = None
    oss_access_key_secret_configured: bool = False
    oss_access_key_secret_masked: Optional[str] = None
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_region: str = ""
    oss_prefix: str = "mediacrawler/video-summary"
    oss_url_expires_seconds: int = 7200
    oss_cleanup_after_analysis: bool = True
    settings_path: str


class QwenProfileRequest(QwenSettingsRequest):
    name: str = Field(default="默认配置", min_length=1, max_length=80)
    clear_api_key: bool = False
    clear_oss_access_key: bool = False


class QwenProfileResponse(BaseModel):
    id: str
    name: str
    active: bool = False
    api_key_configured: bool = False
    api_key_masked: Optional[str] = None
    api_provider: VideoAnalysisApiProvider = "dashscope"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-omni-plus"
    video_input_mode: VideoInputMode = "auto"
    video_upload_backend: VideoUploadBackend = "auto"
    video_fps: float = 2.0
    sample_frames: int = 8
    max_inline_video_mb: int = QWEN_BASE64_RAW_VIDEO_LIMIT_MB
    max_dashscope_video_mb: int = QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB
    oss_enabled: bool = False
    oss_access_key_id_configured: bool = False
    oss_access_key_id_masked: Optional[str] = None
    oss_access_key_secret_configured: bool = False
    oss_access_key_secret_masked: Optional[str] = None
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_region: str = ""
    oss_prefix: str = "mediacrawler/video-summary"
    oss_url_expires_seconds: int = 7200
    oss_cleanup_after_analysis: bool = True
    created_at: str = ""
    updated_at: str = ""


class QwenProfileSecretResponse(QwenProfileResponse):
    api_key: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""


class QwenProfilesResponse(BaseModel):
    active_profile_id: str
    profiles: List[QwenProfileResponse]
    settings_path: str


class PlatformCredentialRequest(BaseModel):
    platform: PlatformEnum
    name: str = Field(default="Default cookies", min_length=1, max_length=80)
    cookies: Optional[str] = None
    clear_cookies: bool = False
    login_method: str = "cookie"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlatformCredentialResponse(BaseModel):
    id: str
    platform: PlatformEnum
    name: str
    active: bool = False
    cookies_configured: bool = False
    cookies_masked: Optional[str] = None
    login_method: str = "cookie"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class PlatformCredentialSecretResponse(PlatformCredentialResponse):
    cookies: str = ""


class PlatformCredentialsResponse(BaseModel):
    active_by_platform: Dict[str, str] = Field(default_factory=dict)
    profiles: List[PlatformCredentialResponse] = Field(default_factory=list)
    settings_path: str


class PlatformQrcodeLoginRequest(BaseModel):
    platform: PlatformEnum
    name: str = Field(default="扫码登录信息", min_length=1, max_length=80)
    profile_id: Optional[str] = None
    headless: bool = False


class PlatformQrcodeLoginStatus(BaseModel):
    task_id: str
    status: Literal["pending", "running", "completed", "error"]
    platform: PlatformEnum
    profile_id: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    progress_message: str = ""
    logs: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    credential: Optional[PlatformCredentialResponse] = None
    cookie_count: int = 0
    cookie_keys: List[str] = Field(default_factory=list)
    browser_data_dir: str = ""


class CreatorCandidate(BaseModel):
    id: str
    platform: PlatformEnum
    display_name: str
    avatar_url: str = ""
    profile_url: str = ""
    description: str = ""
    follower_count: Optional[int] = None
    video_count: Optional[int] = None
    verified: bool = False
    verification: str = ""
    metrics: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)


class CreatorResolveRequest(BaseModel):
    platform: PlatformEnum
    query: str


class CreatorResolveResponse(BaseModel):
    candidates: List[CreatorCandidate]
    message: str
    needs_manual_id: bool = False


class VideoSummaryTaskRequest(BaseModel):
    platform: PlatformEnum
    creator_id: str
    creator_display_name: str = ""
    profile_url: str = ""
    source_mode: VideoTaskSourceMode = "creator"
    search_keyword: str = ""
    ranking_type: str = "popular"
    ranking_limit: int = Field(default=5, ge=1, le=50)
    credential_profile_id: Optional[str] = None
    workflow_mode: VideoTaskWorkflowMode = "full"
    source_task_id: Optional[str] = None
    selected_item_ids: List[str] = Field(default_factory=list)
    login_type: LoginTypeEnum = LoginTypeEnum.QRCODE
    cookies: str = ""
    start_date: date = Field(default_factory=date.today)
    end_date: date = Field(default_factory=date.today)
    max_videos: int = Field(default=20, ge=1, le=200)
    crawl_concurrency: int = Field(default=1, ge=1, le=8)
    headless: bool = False
    # Legacy single-value interval kept for older clients. New clients should
    # send crawl_min_sleep_seconds and crawl_max_sleep_seconds.
    crawl_sleep_seconds: float = Field(default=5.0, ge=0, le=120)
    crawl_min_sleep_seconds: Optional[float] = Field(default=None, ge=0, le=120)
    crawl_max_sleep_seconds: Optional[float] = Field(default=None, ge=0, le=120)
    crawl_long_pause_every: int = Field(default=0, ge=0, le=1000)
    crawl_long_pause_min_seconds: float = Field(default=30.0, ge=0, le=3600)
    crawl_long_pause_max_seconds: float = Field(default=90.0, ge=0, le=3600)
    summarize: bool = True
    video_input_mode: VideoInputMode = "auto"
    video_upload_backend: VideoUploadBackend = "auto"
    video_fps: float = Field(default=2.0, ge=0.1, le=10.0)
    sample_frames: int = Field(default=8, ge=1, le=24)
    max_inline_video_mb: int = Field(default=QWEN_BASE64_RAW_VIDEO_LIMIT_MB, ge=1, le=QWEN_BASE64_RAW_VIDEO_LIMIT_MB)
    max_dashscope_video_mb: int = Field(default=QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB, ge=1, le=QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB)
    dashscope_retry_count: int = Field(default=QWEN_DASHSCOPE_RETRY_COUNT, ge=1, le=5)
    enable_video_compression: bool = True
    compression_target_mb: int = Field(default=QWEN_VIDEO_COMPRESSION_TARGET_MB, ge=10, le=QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB)
    enable_whisper_transcription: bool = False
    whisper_model: str = Field(default="turbo", min_length=1, max_length=80)


class VideoDownloadProgress(BaseModel):
    status: DownloadProgressStatus = "idle"
    platform: str = ""
    item_id: str = ""
    file_name: str = ""
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bps: float = 0.0
    percent: Optional[float] = None
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    message: str = ""


class VideoTaskStep(BaseModel):
    id: str
    label: str
    phase: str = ""
    item_id: str = ""
    status: VideoTaskStepStatus = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    progress_percent: Optional[float] = None
    transferred_bytes: int = 0
    total_bytes: Optional[int] = None
    speed_bps: float = 0.0
    message: str = ""


class VideoSummaryItem(BaseModel):
    id: str
    title: str = ""
    desc: str = ""
    url: str = ""
    published_at: Optional[str] = None
    video_path: Optional[str] = None
    download_status: DownloadStatus = "missing"
    summary_status: SummaryStatus = "skipped"
    analysis_mode: AnalysisMode = "none"
    summary: str = ""
    error: str = ""
    raw: Dict[str, Any] = Field(default_factory=dict)


class VideoSummaryResult(BaseModel):
    task_id: str
    platform: PlatformEnum
    creator_id: str
    creator_display_name: str = ""
    source_mode: VideoTaskSourceMode = "creator"
    search_keyword: str = ""
    ranking_type: str = ""
    workflow_mode: VideoTaskWorkflowMode = "full"
    date_range: Dict[str, str]
    output_dir: str
    total_records: int = 0
    matched_videos: int = 0
    summarized_videos: int = 0
    aggregate_summary: str = ""
    items: List[VideoSummaryItem] = Field(default_factory=list)


class VideoSummaryTaskStatus(BaseModel):
    task_id: str
    status: Literal["pending", "running", "completed", "error"]
    platform: PlatformEnum
    creator_id: str
    source_mode: VideoTaskSourceMode = "creator"
    started_at: str
    completed_at: Optional[str] = None
    progress_message: str = ""
    download_progress: Optional[VideoDownloadProgress] = None
    subtasks: List[VideoTaskStep] = Field(default_factory=list)
    logs: List[str] = Field(default_factory=list)
    result: Optional[VideoSummaryResult] = None
    error_message: Optional[str] = None
