# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import base64
import hashlib
from html import unescape
import json
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time as time_module
import uuid
import wave
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urlencode, urlparse
from zoneinfo import ZoneInfo

import httpx

from tools.crawler_util import normalize_cookie_input, parse_cookie_input

from ..schemas.video_summary import (
    CreatorCandidate,
    CreatorResolveRequest,
    CreatorResolveResponse,
    PlatformCredentialRequest,
    PlatformCredentialResponse,
    PlatformCredentialHealthResponse,
    PlatformCredentialSelfTestResponse,
    PlatformCredentialSecretResponse,
    PlatformCredentialsResponse,
    PlatformQrcodeLoginRequest,
    PlatformQrcodeLoginStatus,
    QwenProfileRequest,
    QwenProfileResponse,
    QwenProfileSecretResponse,
    QwenProfilesResponse,
    QwenSettingsRequest,
    QwenSettingsResponse,
    VideoDownloadProgress,
    VideoSummaryItem,
    VideoSummaryResult,
    VideoSummaryTaskRequest,
    VideoSummaryTaskStatus,
    VideoTaskStep,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_ROOT = PROJECT_ROOT / "data" / "video_tasks"
QWEN_SETTINGS_PATH = TASK_ROOT / "qwen_settings.json"
PLATFORM_CREDENTIALS_PATH = TASK_ROOT / "platform_credentials.json"
TASK_STATE_FILE_NAME = "task_state.json"
LOCAL_TZ = ZoneInfo("Asia/Shanghai")
QWEN_BASE64_RAW_VIDEO_LIMIT_MB = 7
QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB = 100
QWEN_PUBLIC_URL_VIDEO_LIMIT_MB = 2048
QWEN_DASHSCOPE_RETRY_COUNT = 3
QWEN_VIDEO_COMPRESSION_TARGET_MB = 64
OSS_MULTIPART_THRESHOLD_BYTES = 2 * 1024 * 1024
OSS_MULTIPART_PART_SIZE_BYTES = 4 * 1024 * 1024
REMOTE_OSS_MAX_UPLOAD_ATTEMPTS_PER_ITEM = 1
DEFAULT_WHISPER_MODEL = "turbo"
OLLAMA_DEFAULT_RUNTIME_PROFILE = {
    "num_ctx": 8192,
    "num_predict": 1200,
    "max_images": 4,
    "text_context_chars": 5000,
}
OLLAMA_MODEL_RUNTIME_PROFILES = [
    (
        ("qwen2.5vl:3b", "qwen2.5-vl:3b", "qwen2.5vl-3b"),
        {"num_ctx": 8192, "num_predict": 1100, "max_images": 4, "text_context_chars": 4200},
    ),
    (
        ("qwen2.5vl:7b", "qwen2.5-vl:7b", "qwen2.5vl-7b"),
        {"num_ctx": 8192, "num_predict": 1300, "max_images": 5, "text_context_chars": 5500},
    ),
    (
        ("qwen3-vl:8b", "qwen3-vl-8b", "qwen3vl:8b", "qwen3vl-8b"),
        {"num_ctx": 12288, "num_predict": 1400, "max_images": 6, "text_context_chars": 6500},
    ),
    (
        ("llama3.2-vision:11b", "llama3.2-vision-11b"),
        {"num_ctx": 8192, "num_predict": 1200, "max_images": 4, "text_context_chars": 5000},
    ),
    (
        ("llava:7b", "llava-7b"),
        {"num_ctx": 4096, "num_predict": 900, "max_images": 2, "text_context_chars": 2600},
    ),
]

DEFAULT_QWEN_SETTINGS = {
    "api_key": "",
    "api_provider": "dashscope",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model": "qwen3.5-omni-plus",
    "video_input_mode": "auto",
    "video_upload_backend": "auto",
    "video_fps": 2.0,
    "sample_frames": 8,
    "max_inline_video_mb": QWEN_BASE64_RAW_VIDEO_LIMIT_MB,
    "max_dashscope_video_mb": QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB,
    "oss_enabled": False,
    "oss_access_key_id": "",
    "oss_access_key_secret": "",
    "oss_bucket": "",
    "oss_endpoint": "",
    "oss_region": "",
    "oss_prefix": "mediacrawler/video-summary",
    "oss_url_expires_seconds": 7200,
    "oss_cleanup_after_analysis": True,
}
QWEN_PROFILE_FIELDS = set(DEFAULT_QWEN_SETTINGS)
QWEN_API_PROVIDERS = {"dashscope", "openai_compatible", "ollama"}
VIDEO_UPLOAD_BACKENDS = {"auto", "oss", "dashscope", "openai"}

PLATFORM_STORE_NAMES = {
    "xhs": "xhs",
    "dy": "douyin",
    "ks": "kuaishou",
    "bili": "bili",
    "wb": "weibo",
    "tieba": "tieba",
    "zhihu": "zhihu",
}

PLATFORM_LABELS = {
    "xhs": "Xiaohongshu",
    "dy": "Douyin",
    "ks": "Kuaishou",
    "bili": "Bilibili",
    "wb": "Weibo",
    "tieba": "Baidu Tieba",
    "zhihu": "Zhihu",
}

CONTENT_ID_KEYS = {
    "xhs": ["note_id"],
    "dy": ["aweme_id"],
    "ks": ["video_id"],
    "bili": ["video_id", "aid", "bvid"],
    "wb": ["note_id"],
    "tieba": ["note_id"],
    "zhihu": ["content_id"],
}

TITLE_KEYS = ["title", "desc", "content", "content_text", "text"]
DESC_KEYS = ["desc", "content", "content_text", "description", "title"]
URL_KEYS = [
    "note_url",
    "aweme_url",
    "video_url",
    "content_url",
    "url",
    "share_url",
    "arcurl",
]
COVER_KEYS = [
    "video_cover_url",
    "cover",
    "cover_url",
    "pic",
    "pic_url",
    "first_frame",
    "thumbnail",
    "thumbnail_url",
    "poster",
    "image",
    "image_url",
    "image_list",
]
TIME_KEYS = [
    "time",
    "create_time",
    "created_time",
    "published_at",
    "publish_time",
    "pub_ts",
    "created_at",
    "create_date_time",
    "pubdate",
]
DIRECT_VIDEO_FIELDS = [
    "video_download_url",
    "video_play_url",
    "download_url",
    "play_url",
    "media_url",
    "video_url",
]
TEXT_SOURCE_FIELDS = [
    "subtitle_text",
    "subtitles",
    "transcript",
    "caption",
    "whisper_transcript",
    "ai_summary",
    "summary",
    "content",
    "content_text",
    "desc",
    "description",
]
STRONG_TEXT_SOURCE_LABELS = {
    "B站字幕",
    "B站 AI 总结",
    "已有字幕",
    "已有转录",
    "字幕/文案",
    "平台 AI 总结",
    "已有摘要",
    "正文",
    "Whisper 转录",
}
SHORT_METADATA_LABELS = {"标题", "描述"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".flv", ".mkv"}
PLATFORM_COOKIE_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "bili": {
        "required": [],
        "required_any": ["SESSDATA", "DedeUserID"],
        "recommended": ["bili_jct"],
    },
    "dy": {
        "required": [],
        "required_any": ["LOGIN_STATUS", "sessionid+sid_guard"],
        "recommended": ["LOGIN_STATUS", "uid_tt", "passport_csrf_token"],
    },
    "ks": {
        "required": ["passToken"],
        "recommended": ["kuaishou.server.web_ph", "userId"],
    },
    "xhs": {
        "required": ["web_session"],
        "recommended": ["a1", "webId"],
    },
    "wb": {
        "required": [],
        "required_any": ["SSOLoginState", "WBPSESS"],
        "recommended": ["SUB", "SUBP", "WBPSESS"],
    },
    "zhihu": {
        "required": ["z_c0"],
        "recommended": ["_xsrf"],
    },
    "tieba": {
        "required": ["BDUSS"],
        "recommended": ["STOKEN", "BAIDUID"],
    },
}
NATIVE_DOWNLOAD_PLATFORMS = {"xhs", "dy", "bili", "ks"}
NATIVE_DETAIL_DOWNLOAD_PLATFORMS = {"xhs", "dy", "bili", "ks"}
VIDEO_INPUT_MODES = {"auto", "video", "frames", "text_first"}
BILI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.bilibili.com",
    "Origin": "https://www.bilibili.com",
}
BILI_WBI_MIXIN_KEY_ENC_TAB = (
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 34, 44, 52,
)
BILI_RANKING_REGIONS: Dict[str, Tuple[int, str]] = {
    "ranking": (0, "全站"),
    "ranking_all": (0, "全站"),
    "ranking_douga": (1, "动画"),
    "ranking_guochuang": (168, "国创"),
    "ranking_music": (3, "音乐"),
    "ranking_dance": (129, "舞蹈"),
    "ranking_game": (4, "游戏"),
    "ranking_knowledge": (36, "知识"),
    "ranking_tech": (188, "科技"),
    "ranking_sports": (234, "运动"),
    "ranking_car": (223, "汽车"),
    "ranking_life": (160, "生活"),
    "ranking_food": (211, "美食"),
    "ranking_animal": (217, "动物圈"),
    "ranking_kichiku": (119, "鬼畜"),
    "ranking_fashion": (155, "时尚"),
    "ranking_ent": (5, "娱乐"),
    "ranking_cinephile": (181, "影视"),
    "ranking_movie": (23, "电影"),
    "ranking_tv": (11, "电视剧"),
    "ranking_documentary": (177, "纪录片"),
}

KS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.kuaishou.com/brilliant",
    "Origin": "https://www.kuaishou.com",
    "Content-Type": "application/json;charset=UTF-8",
}
KS_HOT_RANK_QUERY = """
query hotRankQuery($page: String) {
  visionHotRank(page: $page) {
    result
    pcursor
    webPageArea
    items {
      rank
      id
      name
      viewCount
      hotValue
      iconUrl
      poster
      tagType
      photoIds
    }
  }
}
""".strip()
DOUYIN_HOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.douyin.com/hot",
    "Accept": "application/json, text/plain, */*",
}
WEIBO_HOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://weibo.com/",
    "Accept": "application/json, text/plain, */*",
}
ZHIHU_HOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Referer": "https://www.zhihu.com/hot",
    "Accept": "application/json, text/plain, */*",
    "x-api-version": "3.0.76",
}
TIEBA_HOT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://tieba.baidu.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _safe_print(text: str) -> None:
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text, flush=True)


@dataclass
class VideoTask:
    task_id: str
    request: VideoSummaryTaskRequest
    task_dir: Path
    raw_data_dir: Path
    status: str = "pending"
    started_at: datetime = field(default_factory=lambda: datetime.now(LOCAL_TZ))
    completed_at: Optional[datetime] = None
    progress_message: str = ""
    logs: List[str] = field(default_factory=list)
    result: Optional[VideoSummaryResult] = None
    error_message: Optional[str] = None
    process: Optional[subprocess.Popen] = None
    runner: Optional[asyncio.Task[Any]] = None
    cancel_requested: bool = False
    download_progress: Optional[VideoDownloadProgress] = None
    subtasks: List[VideoTaskStep] = field(default_factory=list)
    records: List[Dict[str, Any]] = field(default_factory=list)
    items: List[VideoSummaryItem] = field(default_factory=list)
    resume_from_state: bool = False
    last_state_save_at: float = 0.0

    def add_log(self, message: str) -> None:
        timestamp = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        _safe_print(f"[VideoSummary][{self.task_id}] {message}")
        try:
            from .crawler_manager import crawler_manager

            level = "error" if any(token in message.lower() for token in ("error", "failed", "notimplemented")) else "info"
            crawler_manager.publish_external_log(f"[VideoSummary] {message}", level)
        except Exception:
            pass

    def to_status(self) -> VideoSummaryTaskStatus:
        return VideoSummaryTaskStatus(
            task_id=self.task_id,
            status=self.status,  # type: ignore[arg-type]
            platform=self.request.platform,
            creator_id=self.request.creator_id,
            source_mode=self.request.source_mode,
            started_at=self.started_at.isoformat(),
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            progress_message=self.progress_message,
            download_progress=self.download_progress,
            subtasks=self.subtasks,
            logs=self.logs,
            result=self.result,
            error_message=self.error_message,
        )


@dataclass
class PlatformLoginTask:
    task_id: str
    request: PlatformQrcodeLoginRequest
    status: str = "pending"
    started_at: datetime = field(default_factory=lambda: datetime.now(LOCAL_TZ))
    completed_at: Optional[datetime] = None
    progress_message: str = ""
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    runner: Optional[asyncio.Task[Any]] = None
    credential: Optional[PlatformCredentialResponse] = None
    cookie_count: int = 0
    cookie_keys: List[str] = field(default_factory=list)
    browser_data_dir: str = ""

    def add_log(self, message: str, level: str = "info") -> None:
        timestamp = datetime.now(LOCAL_TZ).strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        if len(self.logs) > 300:
            self.logs = self.logs[-300:]
        _safe_print(f"[PlatformLogin][{self.task_id}] {message}")
        try:
            from .crawler_manager import crawler_manager

            crawler_manager.publish_external_log(f"[PlatformLogin] {message}", level)
        except Exception:
            pass

    def to_status(self) -> PlatformQrcodeLoginStatus:
        return PlatformQrcodeLoginStatus(
            task_id=self.task_id,
            status=self.status,  # type: ignore[arg-type]
            platform=self.request.platform,
            profile_id=self.request.profile_id,
            started_at=self.started_at.isoformat(),
            completed_at=self.completed_at.isoformat() if self.completed_at else None,
            progress_message=self.progress_message,
            logs=self.logs,
            error_message=self.error_message,
            credential=self.credential,
            cookie_count=self.cookie_count,
            cookie_keys=self.cookie_keys,
            browser_data_dir=self.browser_data_dir,
        )


class VideoSummaryManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, VideoTask] = {}
        self._login_tasks: Dict[str, PlatformLoginTask] = {}
        self._creator_search_cache: Dict[Tuple[str, str], Tuple[float, List[CreatorCandidate]]] = {}
        self._whisper_model_cache: Dict[Tuple[str, ...], Any] = {}

    def get_settings(self) -> QwenSettingsResponse:
        store = self._load_profile_store(include_secret=True)
        profile = self._active_profile(store)
        return self._settings_response(profile)

    def save_settings(self, request: QwenSettingsRequest) -> QwenSettingsResponse:
        store = self._load_profile_store(include_secret=True)
        active_id = str(store["active_profile_id"])
        profile = self._profile_by_id(store, active_id)
        self._apply_profile_request(profile, request)
        self._save_profile_store(store)
        return self._settings_response(profile)

    def list_profiles(self) -> QwenProfilesResponse:
        store = self._load_profile_store(include_secret=True)
        return self._profiles_response(store)

    def get_profile_secret(self, profile_id: str) -> QwenProfileSecretResponse:
        store = self._load_profile_store(include_secret=True)
        profile = self._profile_by_id(store, profile_id)
        return self._profile_secret_response(profile, active_profile_id=str(store["active_profile_id"]))

    def create_profile(self, request: QwenProfileRequest) -> QwenProfileResponse:
        store = self._load_profile_store(include_secret=True)
        profile_id = self._new_profile_id(store)
        now = self._now_iso()
        profile: Dict[str, Any] = {
            **dict(DEFAULT_QWEN_SETTINGS),
            "id": profile_id,
            "name": request.name.strip() or "未命名配置",
            "created_at": now,
            "updated_at": now,
        }
        self._apply_profile_request(profile, request)
        store["profiles"].append(profile)
        store["active_profile_id"] = profile_id
        self._save_profile_store(store)
        return self._profile_response(profile, active_profile_id=profile_id)

    def update_profile(self, profile_id: str, request: QwenProfileRequest) -> QwenProfileResponse:
        store = self._load_profile_store(include_secret=True)
        profile = self._profile_by_id(store, profile_id)
        profile["name"] = request.name.strip() or profile.get("name") or "未命名配置"
        self._apply_profile_request(profile, request)
        self._save_profile_store(store)
        return self._profile_response(profile, active_profile_id=str(store["active_profile_id"]))

    def delete_profile(self, profile_id: str) -> QwenProfilesResponse:
        store = self._load_profile_store(include_secret=True)
        profiles = list(store["profiles"])
        if len(profiles) <= 1:
            raise RuntimeError("至少保留一套 Qwen 配置，不能删除最后一套。")
        next_profiles = [profile for profile in profiles if str(profile["id"]) != profile_id]
        if len(next_profiles) == len(profiles):
            raise RuntimeError(f"配置不存在：{profile_id}")
        store["profiles"] = next_profiles
        if str(store["active_profile_id"]) == profile_id:
            store["active_profile_id"] = str(next_profiles[0]["id"])
        self._save_profile_store(store)
        return self._profiles_response(store)

    def activate_profile(self, profile_id: str) -> QwenSettingsResponse:
        store = self._load_profile_store(include_secret=True)
        profile = self._profile_by_id(store, profile_id)
        store["active_profile_id"] = str(profile["id"])
        self._save_profile_store(store)
        return self._settings_response(profile)

    def list_platform_credentials(self) -> PlatformCredentialsResponse:
        store = self._load_credential_store(include_secret=True)
        return self._credential_store_response(store)

    def get_platform_credential_secret(self, profile_id: str) -> PlatformCredentialSecretResponse:
        store = self._load_credential_store(include_secret=True)
        profile = self._credential_by_id(store, profile_id)
        return self._credential_secret_response(profile, dict(store.get("active_by_platform") or {}))

    def create_platform_credential(self, request: PlatformCredentialRequest) -> PlatformCredentialResponse:
        store = self._load_credential_store(include_secret=True)
        profile_id = self._new_credential_id(store)
        now = self._now_iso()
        cookies = normalize_cookie_input(request.cookies or "") if request.cookies else ""
        profile: Dict[str, Any] = {
            "id": profile_id,
            "platform": request.platform.value,
            "name": request.name.strip() or "Default cookies",
            "cookies": cookies,
            "login_method": request.login_method.strip() or "cookie",
            "metadata": dict(request.metadata or {}),
            "created_at": now,
            "updated_at": now,
        }
        store["profiles"].append(profile)
        active = dict(store.get("active_by_platform") or {})
        active[request.platform.value] = profile_id
        store["active_by_platform"] = active
        self._save_credential_store(store)
        return self._credential_response(profile, active)

    def update_platform_credential(self, profile_id: str, request: PlatformCredentialRequest) -> PlatformCredentialResponse:
        store = self._load_credential_store(include_secret=True)
        profile = self._credential_by_id(store, profile_id)
        profile["platform"] = request.platform.value
        profile["name"] = request.name.strip() or profile.get("name") or "Default cookies"
        profile["login_method"] = request.login_method.strip() or profile.get("login_method") or "cookie"
        profile["metadata"] = dict(request.metadata or {})
        if request.clear_cookies:
            profile["cookies"] = ""
        elif request.cookies is not None and request.cookies.strip():
            normalized = normalize_cookie_input(request.cookies)
            if not normalized:
                raise RuntimeError("No valid cookies were recognized.")
            profile["cookies"] = normalized
        profile["updated_at"] = self._now_iso()
        self._save_credential_store(store)
        return self._credential_response(profile, dict(store.get("active_by_platform") or {}))

    def delete_platform_credential(self, profile_id: str) -> PlatformCredentialsResponse:
        store = self._load_credential_store(include_secret=True)
        profiles = list(store.get("profiles") or [])
        next_profiles = [profile for profile in profiles if str(profile.get("id")) != profile_id]
        if len(next_profiles) == len(profiles):
            raise RuntimeError(f"Credential profile does not exist: {profile_id}")
        active = {
            platform: active_id
            for platform, active_id in dict(store.get("active_by_platform") or {}).items()
            if active_id != profile_id
        }
        for profile in next_profiles:
            platform = str(profile.get("platform") or "")
            if platform and platform not in active:
                active[platform] = str(profile.get("id"))
        store["profiles"] = next_profiles
        store["active_by_platform"] = active
        self._save_credential_store(store)
        return self._credential_store_response(store)

    def activate_platform_credential(self, profile_id: str) -> PlatformCredentialResponse:
        store = self._load_credential_store(include_secret=True)
        profile = self._credential_by_id(store, profile_id)
        active = dict(store.get("active_by_platform") or {})
        active[str(profile["platform"])] = str(profile["id"])
        store["active_by_platform"] = active
        self._save_credential_store(store)
        return self._credential_response(profile, active)

    async def check_platform_credential_health(self, profile_id: str) -> PlatformCredentialHealthResponse:
        store = self._load_credential_store(include_secret=True)
        profile = self._credential_by_id(store, profile_id)
        platform = str(profile.get("platform") or "")
        cookies = str(profile.get("cookies") or "")
        cookie_dict = parse_cookie_input(cookies)
        present_keys = sorted(cookie_dict)
        requirements = PLATFORM_COOKIE_REQUIREMENTS.get(platform, {"required": [], "recommended": []})
        missing_required = [key for key in requirements.get("required", []) if not cookie_dict.get(key)]
        required_any = requirements.get("required_any", [])
        if required_any and not self._cookie_requirement_any_satisfied(cookie_dict, required_any):
            missing_required.append(" or ".join(required_any))
        missing_recommended = [key for key in requirements.get("recommended", []) if not cookie_dict.get(key)]

        status = "ok"
        message = "Cookie profile contains the required login fields."
        probe_result: Dict[str, Any] = {
            "live_probe_supported": False,
            "live_probe_ok": None,
            "probe_url": "",
            "http_status": None,
            "authenticated": None,
            "details": {},
        }
        if missing_required:
            status = "error"
            message = "Cookie profile is missing required login fields: " + ", ".join(missing_required)
        elif platform == "bili":
            probe_result = await self._probe_bili_credential(cookies)
            if probe_result.get("live_probe_ok"):
                status = "ok"
                message = "Bilibili nav API confirmed the account is logged in."
            else:
                status = "error"
                detail = str((probe_result.get("details") or {}).get("message") or "")
                message = "Bilibili nav API did not confirm login" + (f": {detail}" if detail else ".")
        elif platform in {"dy", "ks", "xhs", "wb", "zhihu", "tieba"}:
            status = "warning"
            message = (
                f"{PLATFORM_LABELS.get(platform, platform)} required cookie fields are present, "
                "but this workbench has no stable low-risk live login probe for this platform yet. "
                "Run a conservative metadata-only task to verify platform acceptance."
            )

        return PlatformCredentialHealthResponse(
            profile_id=str(profile["id"]),
            platform=profile["platform"],
            status=status,  # type: ignore[arg-type]
            checked_at=self._now_iso(),
            message=message,
            cookie_count=len(present_keys),
            present_keys=present_keys,
            missing_required_keys=missing_required,
            missing_recommended_keys=missing_recommended,
            live_probe_supported=bool(probe_result.get("live_probe_supported")),
            live_probe_ok=probe_result.get("live_probe_ok"),
            probe_url=str(probe_result.get("probe_url") or ""),
            http_status=probe_result.get("http_status"),
            authenticated=probe_result.get("authenticated"),
            details=dict(probe_result.get("details") or {}),
        )

    async def self_test_platform_credential(self, profile_id: str) -> PlatformCredentialSelfTestResponse:
        health = await self.check_platform_credential_health(profile_id)
        if health.status == "error":
            return PlatformCredentialSelfTestResponse(
                profile_id=profile_id,
                platform=health.platform,
                status="error",
                checked_at=self._now_iso(),
                message=f"Cookie field check failed before live self-test: {health.message}",
                health=health,
                error_message=health.message,
            )

        request, probe_keyword = self._build_credential_self_test_request(profile_id, health.platform.value)
        started = time_module.perf_counter()
        initial_status = await self.start_task(request)
        task_id = initial_status.task_id
        last_status = initial_status
        timeout_seconds = 120.0

        while last_status.status not in {"completed", "error"}:
            if time_module.perf_counter() - started > timeout_seconds:
                await self.stop_task(task_id)
                last_status = self.get_task(task_id) or last_status
                break
            await asyncio.sleep(2.0)
            last_status = self.get_task(task_id) or last_status

        wall_seconds = round(time_module.perf_counter() - started, 3)
        result = last_status.result
        total_records = int(result.total_records if result else 0)
        matched_videos = int(result.matched_videos if result else 0)
        item_count = len(result.items) if result else 0
        logs_tail = list(last_status.logs[-16:])

        if last_status.status == "completed":
            if total_records > 0 or item_count > 0:
                status = "ok"
                message = (
                    f"Live metadata-only self-test succeeded: collected {total_records} raw record(s), "
                    f"prepared {item_count} candidate item(s)."
                )
            else:
                status = "warning"
                message = "Live metadata-only self-test completed, but no records were collected."
        else:
            status = "error"
            message = last_status.error_message or "Live metadata-only self-test failed."

        return PlatformCredentialSelfTestResponse(
            profile_id=profile_id,
            platform=health.platform,
            status=status,  # type: ignore[arg-type]
            checked_at=self._now_iso(),
            message=message,
            health=health,
            task_id=task_id,
            task_status=last_status.status,
            source_mode=request.source_mode,
            probe_keyword=probe_keyword,
            total_records=total_records,
            matched_videos=matched_videos,
            item_count=item_count,
            wall_seconds=wall_seconds,
            error_message=last_status.error_message,
            logs_tail=logs_tail,
        )

    def _build_credential_self_test_request(self, profile_id: str, platform: str) -> Tuple[VideoSummaryTaskRequest, str]:
        probe_keyword_by_platform = {
            "bili": "泰坦尼克号",
            "dy": "美食",
            "xhs": "咖啡",
            "ks": "旅行",
            "wb": "美食",
            "zhihu": "AI",
            "tieba": "",
        }
        ranking_type_by_platform = {
            "tieba": "hot_topic",
        }
        probe_keyword = probe_keyword_by_platform.get(platform, "测试")
        source_mode = "ranking" if platform in ranking_type_by_platform else "search"
        today = date.today()
        return (
            VideoSummaryTaskRequest(
                platform=platform,
                creator_id=probe_keyword if source_mode == "search" else f"self-test:{platform}",
                creator_display_name=f"{PLATFORM_LABELS.get(platform, platform)} credential self-test",
                source_mode=source_mode,  # type: ignore[arg-type]
                search_keyword=probe_keyword,
                ranking_type=ranking_type_by_platform.get(platform, ""),
                ranking_limit=1,
                credential_profile_id=profile_id,
                workflow_mode="metadata_only",
                login_type="cookie",  # type: ignore[arg-type]
                cookies="",
                start_date=today - timedelta(days=30),
                end_date=today,
                max_crawl_items=10,
                max_videos=1,
                crawl_concurrency=1,
                headless=True,
                crawl_sleep_seconds=6.0,
                crawl_min_sleep_seconds=3.0,
                crawl_max_sleep_seconds=6.0,
                crawl_long_pause_every=0,
                summarize=False,
                enable_whisper_transcription=False,
            ),
            probe_keyword,
        )

    async def _probe_bili_credential(self, cookies: str) -> Dict[str, Any]:
        probe_url = "https://api.bilibili.com/x/web-interface/nav"
        headers = dict(BILI_HEADERS)
        headers["Cookie"] = cookies
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers, follow_redirects=True, trust_env=False) as client:
                response = await client.get(probe_url)
            payload = response.json()
            data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
            authenticated = bool(data.get("isLogin"))
            return {
                "live_probe_supported": True,
                "live_probe_ok": response.status_code == 200 and payload.get("code") == 0 and authenticated,
                "probe_url": probe_url,
                "http_status": response.status_code,
                "authenticated": authenticated,
                "details": {
                    "code": payload.get("code"),
                    "message": payload.get("message"),
                    "uname": data.get("uname"),
                    "mid": data.get("mid"),
                },
            }
        except Exception as exc:
            return {
                "live_probe_supported": True,
                "live_probe_ok": False,
                "probe_url": probe_url,
                "http_status": None,
                "authenticated": None,
                "details": {"error": f"{type(exc).__name__}: {exc}"},
            }

    def _cookie_requirement_any_satisfied(self, cookie_dict: Dict[str, str], required_any: List[str]) -> bool:
        for requirement in required_any:
            keys = [part.strip() for part in str(requirement).split("+") if part.strip()]
            if keys and all(cookie_dict.get(key) for key in keys):
                return True
        return False

    async def start_platform_qrcode_login(self, request: PlatformQrcodeLoginRequest) -> PlatformQrcodeLoginStatus:
        if request.platform.value == "tieba":
            raise RuntimeError("贴吧当前没有接入视频任务平台登录配置，请使用原爬虫流程或其他已接入平台。")
        async with self._lock:
            running_video = [task for task in self._tasks.values() if task.status in {"pending", "running"}]
            if running_video:
                raise RuntimeError(f"Video task {running_video[0].task_id} is already running")
            running_login = [task for task in self._login_tasks.values() if task.status in {"pending", "running"}]
            if running_login:
                raise RuntimeError(f"Platform login task {running_login[0].task_id} is already running")

            profile_id = (request.profile_id or "").strip() or None
            if profile_id:
                store = self._load_credential_store(include_secret=True)
                profile = self._credential_by_id(store, profile_id)
                if str(profile.get("platform") or "") != request.platform.value:
                    raise RuntimeError(f"Credential profile {profile_id} does not belong to platform {request.platform.value}.")

            task_id = uuid.uuid4().hex[:12]
            normalized_request = request.model_copy(update={"profile_id": profile_id})
            task = PlatformLoginTask(
                task_id=task_id,
                request=normalized_request,
                progress_message="QR-code login queued",
            )
            self._login_tasks[task_id] = task
            task.runner = asyncio.create_task(self._run_platform_qrcode_login(task))
            return task.to_status()

    def get_platform_qrcode_login(self, task_id: str) -> Optional[PlatformQrcodeLoginStatus]:
        task = self._login_tasks.get(task_id)
        return task.to_status() if task else None

    async def _run_platform_qrcode_login(self, task: PlatformLoginTask) -> None:
        import config
        from playwright.async_api import async_playwright
        from tools import utils as crawler_utils

        platform = task.request.platform.value
        original_config = {
            "PLATFORM": getattr(config, "PLATFORM", None),
            "LOGIN_TYPE": getattr(config, "LOGIN_TYPE", None),
            "SAVE_LOGIN_STATE": getattr(config, "SAVE_LOGIN_STATE", None),
            "HEADLESS": getattr(config, "HEADLESS", None),
            "ENABLE_CDP_MODE": getattr(config, "ENABLE_CDP_MODE", None),
            "CDP_CONNECT_EXISTING": getattr(config, "CDP_CONNECT_EXISTING", None),
            "COOKIES": getattr(config, "COOKIES", None),
        }
        browser_context = None
        task.status = "running"
        task.progress_message = "Opening original MediaCrawler QR-code login flow"
        try:
            crawler_cls, login_cls = self._platform_qrcode_classes(platform)
            config.PLATFORM = platform
            config.LOGIN_TYPE = "qrcode"
            config.SAVE_LOGIN_STATE = True
            config.HEADLESS = bool(task.request.headless)
            config.ENABLE_CDP_MODE = False
            config.CDP_CONNECT_EXISTING = False
            config.COOKIES = ""

            browser_data_dir = Path.cwd() / "browser_data" / (config.USER_DATA_DIR % platform)
            task.browser_data_dir = str(browser_data_dir)
            task.add_log(
                f"Starting QR-code login for {PLATFORM_LABELS.get(platform, platform)}; profile dir: {task.browser_data_dir}"
            )

            crawler = crawler_cls()
            user_agent = getattr(crawler, "mobile_user_agent", None) or getattr(crawler, "user_agent", None) or crawler_utils.get_user_agent()
            async with async_playwright() as playwright:
                browser_context = await crawler.launch_browser(
                    playwright.chromium,
                    None,
                    user_agent,
                    headless=bool(task.request.headless),
                )
                stealth_path = PROJECT_ROOT / "libs" / "stealth.min.js"
                if stealth_path.exists():
                    await browser_context.add_init_script(path=str(stealth_path))
                page = await browser_context.new_page()
                if platform == "ks":
                    from media_platform.kuaishou.help import KS_SIGN_CAPTURE_SCRIPT

                    await page.add_init_script(KS_SIGN_CAPTURE_SCRIPT)
                start_url = self._platform_login_start_url(platform, crawler)
                task.progress_message = "Waiting for scan/confirmation in the opened browser"
                task.add_log("Browser opened. Scan the platform QR code and finish any in-browser confirmation.")
                await page.goto(start_url, wait_until="domcontentloaded", timeout=60_000)

                login = login_cls(
                    login_type="qrcode",
                    login_phone="",
                    browser_context=browser_context,
                    context_page=page,
                    cookie_str="",
                )
                await login.begin()

                if platform == "wb":
                    mobile_url = getattr(crawler, "mobile_index_url", "")
                    if mobile_url:
                        await page.goto(mobile_url, wait_until="domcontentloaded", timeout=60_000)
                        await asyncio.sleep(2)

                cookie_urls = self._platform_cookie_urls(platform, crawler)
                cookies, cookie_dict = await crawler_utils.convert_browser_context_cookies(browser_context, urls=cookie_urls)
                normalized = normalize_cookie_input(cookies)
                if not normalized:
                    raise RuntimeError("QR-code login completed but no platform cookies were captured.")

                cookie_keys = sorted(cookie_dict.keys())
                task.cookie_count = len(cookie_keys)
                task.cookie_keys = cookie_keys
                credential = self._save_qrcode_credential(
                    task=task,
                    cookies=normalized,
                    cookie_keys=cookie_keys,
                )
                task.credential = credential
                task.request = task.request.model_copy(update={"profile_id": credential.id})
                task.status = "completed"
                task.progress_message = "QR-code login saved"
                task.add_log(f"QR-code login saved {task.cookie_count} cookies to credential profile {credential.id}.")
        except SystemExit as exc:
            task.status = "error"
            task.error_message = f"Original MediaCrawler login exited before success: {exc}"
            task.progress_message = "QR-code login failed"
            task.add_log(task.error_message, level="error")
        except Exception as exc:
            task.status = "error"
            task.error_message = f"{type(exc).__name__}: {exc}"
            task.progress_message = "QR-code login failed"
            task.add_log(task.error_message, level="error")
        finally:
            if browser_context is not None:
                try:
                    await browser_context.close()
                except Exception:
                    pass
            for key, value in original_config.items():
                if value is not None:
                    setattr(config, key, value)
            task.completed_at = datetime.now(LOCAL_TZ)

    def _platform_qrcode_classes(self, platform: str) -> Tuple[Any, Any]:
        if platform == "bili":
            from media_platform.bilibili.core import BilibiliCrawler
            from media_platform.bilibili.login import BilibiliLogin

            return BilibiliCrawler, BilibiliLogin
        if platform == "xhs":
            from media_platform.xhs.core import XiaoHongShuCrawler
            from media_platform.xhs.login import XiaoHongShuLogin

            return XiaoHongShuCrawler, XiaoHongShuLogin
        if platform == "dy":
            from media_platform.douyin.core import DouYinCrawler
            from media_platform.douyin.login import DouYinLogin

            return DouYinCrawler, DouYinLogin
        if platform == "ks":
            from media_platform.kuaishou.core import KuaishouCrawler
            from media_platform.kuaishou.login import KuaishouLogin

            return KuaishouCrawler, KuaishouLogin
        if platform == "wb":
            from media_platform.weibo.core import WeiboCrawler
            from media_platform.weibo.login import WeiboLogin

            return WeiboCrawler, WeiboLogin
        if platform == "zhihu":
            from media_platform.zhihu.core import ZhihuCrawler
            from media_platform.zhihu.login import ZhiHuLogin

            return ZhihuCrawler, ZhiHuLogin
        raise RuntimeError(f"QR-code login is not connected for platform: {platform}")

    def _platform_login_start_url(self, platform: str, crawler: Any) -> str:
        if platform == "ks":
            return f"{crawler.index_url}?isHome=1"
        return str(getattr(crawler, "index_url", "") or self._platform_cookie_urls(platform, crawler)[0])

    def _platform_cookie_urls(self, platform: str, crawler: Any) -> List[str]:
        urls = list(getattr(crawler, "cookie_urls", []) or [])
        extras = {
            "bili": ["https://www.bilibili.com", "https://api.bilibili.com", "https://passport.bilibili.com"],
            "xhs": ["https://www.xiaohongshu.com", "https://edith.xiaohongshu.com"],
            "dy": ["https://www.douyin.com", "https://douyin.com", "https://creator.douyin.com"],
            "ks": ["https://www.kuaishou.com"],
            "wb": ["https://m.weibo.cn", "https://weibo.com", "https://passport.weibo.com"],
            "zhihu": ["https://www.zhihu.com"],
        }.get(platform, [])
        seen: set[str] = set()
        result: List[str] = []
        for url in [*urls, *extras]:
            if url and url not in seen:
                seen.add(url)
                result.append(url)
        return result

    def _save_qrcode_credential(
        self,
        *,
        task: PlatformLoginTask,
        cookies: str,
        cookie_keys: List[str],
    ) -> PlatformCredentialResponse:
        store = self._load_credential_store(include_secret=True)
        now = self._now_iso()
        profile_id = (task.request.profile_id or "").strip()
        if profile_id:
            profile = self._credential_by_id(store, profile_id)
            if str(profile.get("platform") or "") != task.request.platform.value:
                raise RuntimeError(f"Credential profile {profile_id} does not belong to platform {task.request.platform.value}.")
        else:
            profile_id = self._new_credential_id(store)
            profile = {
                "id": profile_id,
                "platform": task.request.platform.value,
                "created_at": now,
            }
            store.setdefault("profiles", []).append(profile)

        profile.update(
            {
                "platform": task.request.platform.value,
                "name": task.request.name.strip() or profile.get("name") or "QR-code login",
                "cookies": cookies,
                "login_method": "qrcode",
                "metadata": {
                    "saved_from": "original_mediacrawler_qrcode",
                    "captured_at": now,
                    "browser_data_dir": task.browser_data_dir,
                    "cookie_keys": cookie_keys,
                },
                "updated_at": now,
            }
        )
        active = dict(store.get("active_by_platform") or {})
        active[task.request.platform.value] = str(profile["id"])
        store["active_by_platform"] = active
        self._save_credential_store(store)
        return self._credential_response(profile, active)

    async def resolve_creators(self, request: CreatorResolveRequest) -> CreatorResolveResponse:
        lines = self._split_creator_inputs(request.query)
        candidates: List[CreatorCandidate] = []
        errors: List[str] = []

        for line in lines:
            try:
                display_name, raw_identifier, description = self._parse_candidate_line(line)
                creator_value, parsed_id = self._normalize_creator_identifier(
                    request.platform.value,
                    raw_identifier,
                )
                candidates.append(
                    CreatorCandidate(
                        id=creator_value,
                        platform=request.platform,
                        display_name=display_name or f"{PLATFORM_LABELS[request.platform.value]} creator {parsed_id}",
                        profile_url=self._build_profile_url(request.platform.value, creator_value, parsed_id),
                        description=description,
                        verification="manual_or_url",
                        metrics={
                            "parsed_id": parsed_id,
                            "source": "manual_or_url",
                        },
                        raw={
                            "input": line,
                            "crawler_value": creator_value,
                        },
                    )
                )
            except ValueError as exc:
                if request.platform.value == "bili":
                    search_candidates = await self._search_bili_creators(request, line)
                    if search_candidates:
                        candidates.extend(search_candidates)
                        continue
                errors.append(str(exc))

        if candidates:
            candidates = self._dedupe_candidates(candidates)
            message = "已解析创作者链接/ID；B 站也支持按用户名搜索。重名用户请根据 UID、粉丝数、视频数和简介选择具体账号。"
            if errors:
                message += " 部分输入未能解析：" + "；".join(errors[:3])
            return CreatorResolveResponse(candidates=candidates, message=message)

        return CreatorResolveResponse(
            candidates=[],
            message="没有解析到创作者。B 站可输入用户名搜索；其他平台请粘贴创作者主页链接或平台 creator ID。",
            needs_manual_id=True,
        )

    async def start_task(self, request: VideoSummaryTaskRequest) -> VideoSummaryTaskStatus:
        request = await self._normalize_task_request(request)
        async with self._lock:
            running = [task for task in self._tasks.values() if task.status in {"pending", "running"}]
            if running:
                raise RuntimeError(f"Video task {running[0].task_id} is already running")
            running_login = [task for task in self._login_tasks.values() if task.status in {"pending", "running"}]
            if running_login:
                raise RuntimeError(f"Platform login task {running_login[0].task_id} is already running")

            task_id = uuid.uuid4().hex[:12]
            task_dir = TASK_ROOT / task_id
            raw_data_dir = task_dir / "raw"
            raw_data_dir.mkdir(parents=True, exist_ok=True)

            task = VideoTask(
                task_id=task_id,
                request=request,
                task_dir=task_dir,
                raw_data_dir=raw_data_dir,
                progress_message="Task queued",
            )
            self._tasks[task_id] = task
            self._save_task_state(task, force=True)
            task.runner = asyncio.create_task(self._run_task(task))
            return task.to_status()

    def get_task(self, task_id: str) -> Optional[VideoSummaryTaskStatus]:
        task = self._tasks.get(task_id)
        if not task:
            task = self._load_task_from_state(task_id)
            if task:
                self._tasks[task_id] = task
        return task.to_status() if task else None

    async def stop_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.status not in {"pending", "running"}:
            return False

        task.cancel_requested = True
        task.add_log("Stopping video summary task...")
        if task.process:
            self._terminate_process_tree(task.process)
        if task.runner and not task.runner.done():
            task.runner.cancel()
        task.status = "error"
        task.error_message = "Task was stopped by user"
        task.progress_message = "Task stopped"
        task.completed_at = datetime.now(LOCAL_TZ)
        self._set_download_progress(task, status="failed", message="Task was stopped by user")
        self._save_task_state(task, force=True)
        return True

    async def resume_task(self, task_id: str) -> VideoSummaryTaskStatus:
        async with self._lock:
            running = [task for task in self._tasks.values() if task.status in {"pending", "running"}]
            if running:
                raise RuntimeError(f"Video task {running[0].task_id} is already running")
            running_login = [task for task in self._login_tasks.values() if task.status in {"pending", "running"}]
            if running_login:
                raise RuntimeError(f"Platform login task {running_login[0].task_id} is already running")

            task = self._tasks.get(task_id) or self._load_task_from_state(task_id)
            if not task:
                raise RuntimeError(f"Video task state was not found: {task_id}")
            if task.status == "completed":
                return task.to_status()

            task.status = "pending"
            task.completed_at = None
            task.error_message = None
            task.cancel_requested = False
            task.process = None
            task.runner = None
            task.resume_from_state = True
            task.progress_message = "Task queued for resume"
            task.add_log("Resuming video summary task from saved state")
            self._tasks[task_id] = task
            self._save_task_state(task, force=True)
            task.runner = asyncio.create_task(self._run_task(task))
            return task.to_status()

    async def _run_task(self, task: VideoTask) -> None:
        task.status = "running"
        task.progress_message = "Running MediaCrawler metadata task"
        task.add_log("Video task started")
        saved_resume_items = [item.model_copy(deep=True) for item in task.items] if task.resume_from_state else []
        self._save_task_state(task, force=True)
        self._start_step(task, "metadata", "检索/加载候选视频元数据", phase="metadata")

        try:
            source_items = self._load_source_items(task)
            if source_items is not None:
                records: List[Dict[str, Any]] = []
                items = source_items
                task.add_log(f"Loaded {len(items)} candidate videos from source task {task.request.source_task_id}")
            elif task.request.source_mode == "ranking":
                task.progress_message = "Fetching platform ranking metadata"
                records = await self._fetch_platform_ranking_records(task)
                self._save_source_records(task, records, "ranking_contents.json")
                task.add_log(f"Loaded {len(records)} ranking records from {PLATFORM_LABELS.get(task.request.platform.value, task.request.platform.value)}")
                items = await self._collect_video_items(task, records, apply_date_filter=False, preserve_order=True)
            elif task.request.source_mode == "search":
                records = []
                if task.request.platform.value == "bili":
                    task.progress_message = "Fetching Bili search metadata via direct API"
                    try:
                        records = await self._fetch_bili_search_records(task)
                        self._save_source_records(task, records, "bili_direct_search_contents.json")
                        if records:
                            task.add_log(
                                f"Bili direct search API loaded {len(records)} records; skipped MediaCrawler browser startup"
                            )
                        else:
                            task.add_log("Bili direct search API returned no records; falling back to MediaCrawler")
                    except Exception as exc:
                        records = []
                        task.add_log(f"Bili direct search API failed; falling back to MediaCrawler: {type(exc).__name__}: {exc}")

                if not records:
                    exit_code = await self._run_crawler(
                        task,
                        self._build_search_metadata_command(task),
                        "Search metadata crawler command",
                        monitor_filtered_candidates=True,
                    )
                    self._check_cancelled(task)
                    if exit_code != 0:
                        task.error_message = self._crawler_exit_error_message(task, exit_code)
                        task.add_log(task.error_message)

                    task.progress_message = "Collecting search JSON output"
                    records = self._load_content_records(task.raw_data_dir)
                    task.add_log(f"Loaded {len(records)} content records from {task.raw_data_dir}")

                task.progress_message = "Filtering search videos by publish date"
                items = await self._collect_video_items(task, records)
            else:
                records = []
                if task.request.platform.value == "bili" and str(task.request.creator_id or "").strip().isdigit():
                    task.progress_message = "Fetching Bili creator metadata via direct API"
                    try:
                        records = await self._fetch_bili_creator_arc_records(task, str(task.request.creator_id).strip())
                        self._save_source_records(task, records, "bili_direct_creator_contents.json")
                        if records:
                            task.add_log(
                                f"Bili direct creator API loaded {len(records)} records; skipped MediaCrawler browser startup"
                            )
                        else:
                            task.add_log("Bili direct creator API returned no records; falling back to MediaCrawler")
                    except Exception as exc:
                        records = []
                        task.add_log(f"Bili direct creator API failed; falling back to MediaCrawler: {type(exc).__name__}: {exc}")

                if not records:
                    exit_code = await self._run_crawler(
                        task,
                        self._build_creator_metadata_command(task),
                        "Metadata crawler command",
                        monitor_filtered_candidates=True,
                    )
                    self._check_cancelled(task)
                    if exit_code != 0:
                        task.error_message = self._crawler_exit_error_message(task, exit_code)
                        task.add_log(task.error_message)

                    task.progress_message = "Collecting crawler JSON output"
                    records = self._load_content_records(task.raw_data_dir)
                    task.add_log(f"Loaded {len(records)} content records from {task.raw_data_dir}")

                if not records and task.request.platform.value == "bili":
                    task.progress_message = "Collecting Bili metadata fallback"
                    fallback_records = await self._fetch_bili_creator_records_fallback(task)
                    if fallback_records:
                        records.extend(fallback_records)
                        self._save_fallback_records(task, fallback_records)
                        task.add_log(f"Loaded {len(fallback_records)} Bili records from public search fallback")

                task.progress_message = "Filtering videos by publish date"
                items = await self._collect_video_items(task, records)
            if saved_resume_items:
                items = self._merge_saved_item_state(items, saved_resume_items)
                task.add_log(f"Restored saved progress for {len(saved_resume_items)} candidate item(s)")
                if items and task.error_message:
                    task.add_log(f"Resume will continue with saved candidates despite metadata refresh warning: {task.error_message}")
                    task.error_message = None
            task.records = records
            task.items = items
            self._save_task_state(task, force=True)
            task.add_log(
                f"Candidate limits: crawled up to {self._task_crawl_limit(task)} raw item(s), "
                f"kept up to {task.request.max_videos} filtered candidate(s)"
            )
            if task.request.source_mode == "ranking":
                task.add_log(f"Prepared {len(items)} ranking candidates")
            else:
                task.add_log(f"Matched {len(items)} video records in selected date range")
            self._finish_step(task, "metadata", message=f"{len(items)} candidate item(s)")
            items = self._filter_selected_items(task, items)
            task.items = items
            self._save_task_state(task, force=True)
            if task.request.selected_item_ids:
                task.add_log(f"Selected {len(items)} video records for download and summary")

            if task.request.workflow_mode == "metadata_only":
                result = await self._build_result(task, records, items)
                task.result = result
                task.completed_at = datetime.now(LOCAL_TZ)
                self._save_result(task)
                self._save_task_state(task, force=True)
                metadata_failure_reason = self._metadata_failure_reason(task, records, items)
                if (task.error_message or metadata_failure_reason) and not records and not items:
                    task.status = "error"
                    task.error_message = task.error_message or metadata_failure_reason
                    task.progress_message = "Candidate metadata failed"
                    task.add_log(task.error_message or "Candidate metadata task failed; no records were collected")
                else:
                    task.status = "completed"
                    task.progress_message = "Candidate metadata ready"
                    task.add_log(f"Candidate metadata task completed in {self._format_elapsed(self._task_elapsed_seconds(task))}")
                self._save_task_state(task, force=True)
                return

            if items and not self._should_defer_download_until_summary(task):
                task.progress_message = "Downloading matched videos"
                await self._prepare_video_files(task, items)
                task.items = items
                self._save_task_state(task, force=True)

            self._check_cancelled(task)
            task.progress_message = "Summarizing videos with Qwen-VL"
            await self._summarize_items(task, items)
            task.items = items
            self._save_task_state(task, force=True)

            task.progress_message = "Building aggregate summary"
            self._start_step(
                task,
                "aggregate_summary",
                "生成整体汇总",
                phase="summary",
                message=self._qwen_runtime_label(self._runtime_qwen_settings(task)),
            )
            result = await self._build_result(task, records, items)
            self._finish_step(task, "aggregate_summary")
            task.result = result
            task.completed_at = datetime.now(LOCAL_TZ)
            failed_downloads = [item for item in items if item.download_status == "failed" and not item.video_path]
            completed_summaries = [item for item in items if item.summary_status == "completed"]
            if items and failed_downloads and not completed_summaries:
                task.status = "error"
                task.error_message = f"{len(failed_downloads)} selected video download(s) failed."
                task.progress_message = "Task failed"
            else:
                task.status = "completed"
                task.progress_message = "Task completed"
            self._save_result(task)
            self._save_task_state(task, force=True)
            if task.status == "completed":
                task.add_log(f"Video task completed in {self._format_elapsed(self._task_elapsed_seconds(task))}")
            else:
                task.add_log(f"{task.error_message or 'Video task failed'} in {self._format_elapsed(self._task_elapsed_seconds(task))}")
        except asyncio.CancelledError:
            task.status = "error"
            task.completed_at = task.completed_at or datetime.now(LOCAL_TZ)
            task.error_message = task.error_message or "Task was stopped by user"
            task.progress_message = "Task stopped"
            self._finish_running_steps(task, status="failed", message=task.error_message)
            self._set_download_progress(task, status="failed", message=task.error_message)
            task.add_log(f"{task.error_message} after {self._format_elapsed(self._task_elapsed_seconds(task))}")
            self._save_task_state(task, force=True)
        except Exception as exc:
            task.status = "error"
            task.completed_at = datetime.now(LOCAL_TZ)
            task.error_message = f"{type(exc).__name__}: {exc}"
            task.progress_message = "Task failed"
            self._finish_running_steps(task, status="failed", message=task.error_message)
            task.add_log(f"{task.error_message} after {self._format_elapsed(self._task_elapsed_seconds(task))}")
            self._save_task_state(task, force=True)

    def _check_cancelled(self, task: VideoTask) -> None:
        if task.cancel_requested:
            raise asyncio.CancelledError()

    def _find_matching_content_record(
        self,
        platform: str,
        item: VideoSummaryItem,
        records: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        candidates = {str(item.id or "").strip()}
        for key in CONTENT_ID_KEYS.get(platform, []):
            value = item.raw.get(key)
            if value not in (None, ""):
                candidates.add(str(value).strip())
        for record in records:
            for key in CONTENT_ID_KEYS.get(platform, []):
                value = record.get(key)
                if value not in (None, "") and str(value).strip() in candidates:
                    return record
            if item.url:
                for key in URL_KEYS:
                    value = str(record.get(key) or "").strip()
                    if value and value == item.url:
                        return record
        return None

    def _merge_content_record_into_item(self, item: VideoSummaryItem, record: Dict[str, Any]) -> None:
        for key, value in record.items():
            if value not in (None, "", [], {}):
                item.raw[key] = value
        item.title = item.title or self._first_value(record, TITLE_KEYS)
        item.desc = item.desc or self._first_value(record, DESC_KEYS)
        item.url = item.url or self._first_value(record, URL_KEYS)

    def _metadata_failure_reason(
        self,
        task: VideoTask,
        records: List[Dict[str, Any]],
        items: List[VideoSummaryItem],
    ) -> str:
        if records or items:
            return ""
        recent_logs = "\n".join(task.logs[-120:]).lower()
        login_markers = (
            "no login",
            "unauthenticated",
            "need_login",
            "cookie may be invalid",
            "cookie login failed",
            "login failed",
            "have not found qrcode",
            "captcha appeared",
            "unhuman",
            "登录已过期",
            "登录状态失效",
            "未登录",
            "请登录",
        )
        if any(marker in recent_logs for marker in login_markers):
            return (
                "Platform login or anti-bot verification failed during metadata crawl; "
                "no records were collected. Please refresh the platform credential before retrying."
            )
        return ""

    def _crawler_exit_error_message(self, task: VideoTask, exit_code: int) -> str:
        login_or_antibot_reason = self._metadata_failure_reason(task, [], [])
        if login_or_antibot_reason:
            return login_or_antibot_reason
        return f"MediaCrawler exited with code {exit_code}; collecting any partial data."

    def _load_source_items(self, task: VideoTask) -> Optional[List[VideoSummaryItem]]:
        if task.request.workflow_mode != "selected_items" or not task.request.source_task_id:
            return None

        source_result = self._load_result(task.request.source_task_id)
        if not source_result:
            task.add_log(f"Source task {task.request.source_task_id} was not found; falling back to metadata crawl")
            return None
        if source_result.platform != task.request.platform:
            task.add_log(f"Source task platform {source_result.platform.value} does not match current platform")
            return None
        return [item.model_copy(deep=True) for item in source_result.items]

    def _load_result(self, task_id: str) -> Optional[VideoSummaryResult]:
        memory_task = self._tasks.get(task_id)
        if memory_task and memory_task.result:
            return memory_task.result

        result_path = TASK_ROOT / task_id / "result.json"
        if not result_path.exists():
            return None
        try:
            with result_path.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return VideoSummaryResult.model_validate(data)
        except Exception:
            return None
        return None

    def _task_state_path(self, task_id: str) -> Path:
        return TASK_ROOT / task_id / TASK_STATE_FILE_NAME

    def _save_task_state(self, task: VideoTask, *, force: bool = False) -> None:
        now = time_module.monotonic()
        if not force and task.status == "running" and now - task.last_state_save_at < 1.5:
            return
        task.last_state_save_at = now
        task.task_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "task_id": task.task_id,
            "request": task.request.model_dump(mode="json"),
            "status": task.status,
            "started_at": task.started_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "progress_message": task.progress_message,
            "logs": task.logs[-500:],
            "error_message": task.error_message,
            "download_progress": task.download_progress.model_dump(mode="json") if task.download_progress else None,
            "subtasks": [step.model_dump(mode="json") for step in task.subtasks],
            "records": task.records,
            "items": [item.model_dump(mode="json") for item in task.items],
            "result": task.result.model_dump(mode="json") if task.result else None,
            "updated_at": datetime.now(LOCAL_TZ).isoformat(),
        }
        state_path = self._task_state_path(task.task_id)
        temp_path = state_path.with_suffix(".json.tmp")
        try:
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
            temp_path.replace(state_path)
        except Exception as exc:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass
            _safe_print(f"[VideoSummary][{task.task_id}] Failed to save task state: {type(exc).__name__}: {exc}")

    def _load_task_from_state(self, task_id: str) -> Optional[VideoTask]:
        state_path = self._task_state_path(task_id)
        if not state_path.exists():
            return None
        try:
            with state_path.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None
            request = VideoSummaryTaskRequest.model_validate(data.get("request") or {})
            task_dir = TASK_ROOT / task_id
            raw_data_dir = task_dir / "raw"
            task = VideoTask(
                task_id=task_id,
                request=request,
                task_dir=task_dir,
                raw_data_dir=raw_data_dir,
                status=str(data.get("status") or "error"),
                started_at=self._parse_task_datetime(data.get("started_at")) or datetime.now(LOCAL_TZ),
                completed_at=self._parse_task_datetime(data.get("completed_at")),
                progress_message=str(data.get("progress_message") or ""),
                logs=[str(value) for value in (data.get("logs") or []) if value is not None][-500:],
                error_message=str(data.get("error_message") or "") or None,
            )
            if task.status in {"pending", "running"}:
                task.status = "error"
                task.completed_at = task.completed_at or datetime.now(LOCAL_TZ)
                task.error_message = task.error_message or "Backend process ended before task completed"
                task.progress_message = "Task interrupted; resume is available"
            elif task.status not in {"completed", "error"}:
                task.status = "error"
                task.error_message = task.error_message or "Task state file contains an unknown status"
            if isinstance(data.get("download_progress"), dict):
                task.download_progress = VideoDownloadProgress.model_validate(data["download_progress"])
            task.subtasks = [
                VideoTaskStep.model_validate(step)
                for step in (data.get("subtasks") or [])
                if isinstance(step, dict)
            ][-80:]
            task.records = [record for record in (data.get("records") or []) if isinstance(record, dict)]
            task.items = [
                VideoSummaryItem.model_validate(item)
                for item in (data.get("items") or [])
                if isinstance(item, dict)
            ]
            if isinstance(data.get("result"), dict):
                task.result = VideoSummaryResult.model_validate(data["result"])
                if not task.items:
                    task.items = [item.model_copy(deep=True) for item in task.result.items]
            else:
                loaded_result = self._load_result(task_id)
                if loaded_result:
                    task.result = loaded_result
                    if not task.items:
                        task.items = [item.model_copy(deep=True) for item in loaded_result.items]
            return task
        except Exception as exc:
            _safe_print(f"[VideoSummary][{task_id}] Failed to load task state: {type(exc).__name__}: {exc}")
            return None

    def _parse_task_datetime(self, value: Any) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=LOCAL_TZ)
            return parsed
        except ValueError:
            return None

    def _filter_selected_items(self, task: VideoTask, items: List[VideoSummaryItem]) -> List[VideoSummaryItem]:
        selected_ids = {str(value).strip() for value in task.request.selected_item_ids if str(value).strip()}
        if not selected_ids:
            return items

        filtered: List[VideoSummaryItem] = []
        platform = task.request.platform.value
        for item in items:
            aliases = {
                item.id,
                self._detail_identifier_for_item(platform, item),
                str(item.raw.get("aid") or ""),
                str(item.raw.get("bvid") or ""),
                str(item.raw.get("video_id") or ""),
                str(item.raw.get("note_id") or ""),
                str(item.raw.get("aweme_id") or ""),
            }
            if any(alias and alias in selected_ids for alias in aliases):
                filtered.append(item)
        return filtered

    def _merge_saved_item_state(
        self,
        current_items: List[VideoSummaryItem],
        saved_items: List[VideoSummaryItem],
    ) -> List[VideoSummaryItem]:
        if not saved_items:
            return current_items
        if not current_items:
            return [item.model_copy(deep=True) for item in saved_items]

        saved_by_key: Dict[str, VideoSummaryItem] = {}
        for saved in saved_items:
            for key in self._item_resume_keys(saved):
                saved_by_key.setdefault(key, saved)

        merged: List[VideoSummaryItem] = []
        matched_saved_ids: set[int] = set()
        for item in current_items:
            saved = next((saved_by_key.get(key) for key in self._item_resume_keys(item) if saved_by_key.get(key)), None)
            if not saved:
                merged.append(item)
                continue

            matched_saved_ids.add(id(saved))
            item.raw = {**saved.raw, **item.raw}
            if saved.video_path:
                saved_path = Path(saved.video_path)
                if saved_path.exists() and self._local_file_has_video_stream(saved_path):
                    item.video_path = str(saved_path)
                    item.download_status = "existing" if saved.download_status in {"downloaded", "existing"} else saved.download_status
            if saved.summary_status == "completed" and saved.summary:
                item.summary = saved.summary
                item.summary_status = "completed"
                item.analysis_mode = saved.analysis_mode
                item.error = ""
            elif saved.error and item.download_status in {"downloaded", "existing"}:
                item.error = saved.error
            merged.append(item)
        for saved in saved_items:
            if id(saved) not in matched_saved_ids:
                merged.append(saved.model_copy(deep=True))
        return merged

    def _item_resume_keys(self, item: VideoSummaryItem) -> List[str]:
        raw = item.raw if isinstance(item.raw, dict) else {}
        keys = [
            item.id,
            raw.get("video_id"),
            raw.get("aid"),
            raw.get("bvid"),
            raw.get("bv_id"),
            raw.get("note_id"),
            raw.get("aweme_id"),
            raw.get("photo_id"),
            raw.get("content_id"),
            item.url,
        ]
        normalized: List[str] = []
        for key in keys:
            value = str(key or "").strip()
            if value and value not in normalized:
                normalized.append(value)
        return normalized

    async def _build_result(
        self,
        task: VideoTask,
        records: List[Dict[str, Any]],
        items: List[VideoSummaryItem],
    ) -> VideoSummaryResult:
        aggregate_summary = ""
        if task.request.workflow_mode != "metadata_only":
            aggregate_summary = await self._build_aggregate_summary(task, items)

        return VideoSummaryResult(
            task_id=task.task_id,
            platform=task.request.platform,
            creator_id=task.request.creator_id,
            creator_display_name=task.request.creator_display_name,
            source_mode=task.request.source_mode,
            search_keyword=task.request.search_keyword,
            ranking_type=task.request.ranking_type if task.request.source_mode == "ranking" else "",
            workflow_mode=task.request.workflow_mode,
            date_range={
                "start": task.request.start_date.isoformat(),
                "end": task.request.end_date.isoformat(),
            },
            output_dir=str(task.task_dir),
            total_records=len(records) if records else len(items),
            matched_videos=len(items),
            summarized_videos=sum(1 for item in items if item.summary_status == "completed"),
            aggregate_summary=aggregate_summary,
            items=items,
        )

    def _set_download_progress(
        self,
        task: VideoTask,
        *,
        status: str,
        item_id: str = "",
        platform: str = "",
        file_name: str = "",
        downloaded_bytes: Optional[int] = None,
        total_bytes: Optional[int] = None,
        speed_bps: float = 0.0,
        message: str = "",
    ) -> None:
        previous = task.download_progress
        downloaded = int(downloaded_bytes if downloaded_bytes is not None else (previous.downloaded_bytes if previous else 0))
        total = total_bytes if total_bytes is not None else (previous.total_bytes if previous else None)
        percent = None
        if total and total > 0:
            percent = min(100.0, round(downloaded * 100 / total, 2))
        now = datetime.now(LOCAL_TZ).isoformat()
        task.download_progress = VideoDownloadProgress(
            status=status,  # type: ignore[arg-type]
            platform=platform or (previous.platform if previous else ""),
            item_id=item_id or (previous.item_id if previous else ""),
            file_name=file_name or (previous.file_name if previous else ""),
            downloaded_bytes=downloaded,
            total_bytes=total,
            speed_bps=float(speed_bps),
            percent=percent,
            started_at=previous.started_at if previous and previous.started_at else now,
            updated_at=now,
            message=message or (previous.message if previous else ""),
        )
        active_item_id = item_id or (previous.item_id if previous else "")
        if active_item_id:
            for step in reversed(task.subtasks):
                if step.status == "running" and step.phase == "download" and step.item_id == active_item_id:
                    self._update_step(
                        task,
                        step.id,
                        progress_percent=percent,
                        transferred_bytes=downloaded,
                        total_bytes=total,
                        speed_bps=speed_bps,
                        message=message,
                    )
                    break
        self._save_task_state(task)

    def _task_elapsed_seconds(self, task: VideoTask) -> float:
        end = task.completed_at or datetime.now(LOCAL_TZ)
        return max(0.0, (end - task.started_at).total_seconds())

    def _format_elapsed(self, seconds: Optional[float]) -> str:
        if seconds is None:
            return "-"
        seconds = max(0.0, float(seconds))
        if seconds < 60:
            return f"{seconds:.1f}s"
        minutes = int(seconds // 60)
        rest = seconds - minutes * 60
        if minutes < 60:
            return f"{minutes}m {rest:.1f}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {rest:.1f}s"

    def _qwen_runtime_label(self, settings: Dict[str, Any]) -> str:
        provider = str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"]) or DEFAULT_QWEN_SETTINGS["api_provider"])
        model = str(settings.get("model", DEFAULT_QWEN_SETTINGS["model"]) or DEFAULT_QWEN_SETTINGS["model"])
        base_url = str(settings.get("base_url", DEFAULT_QWEN_SETTINGS["base_url"]) or "").rstrip("/")
        backend = str(settings.get("video_upload_backend", DEFAULT_QWEN_SETTINGS["video_upload_backend"]) or DEFAULT_QWEN_SETTINGS["video_upload_backend"])
        suffix = f", base_url={base_url}" if base_url else ""
        if provider == "ollama":
            profile = self._ollama_runtime_profile(settings)
            suffix += (
                f", local_ctx={profile['num_ctx']}, local_frames={profile['max_images']}, "
                f"local_text={profile['text_context_chars']}"
            )
        return f"model={model}, provider={provider}, upload_backend={backend}{suffix}"

    def _ollama_runtime_profile(self, settings: Dict[str, Any]) -> Dict[str, int]:
        model = str(settings.get("model") or "").strip().lower()
        profile = dict(OLLAMA_DEFAULT_RUNTIME_PROFILE)
        for names, overrides in OLLAMA_MODEL_RUNTIME_PROFILES:
            if any(name in model for name in names):
                profile.update(overrides)
                break
        for key in ("num_ctx", "num_predict", "max_images", "text_context_chars"):
            explicit_key = f"ollama_{key}"
            if explicit_key in settings and settings.get(explicit_key) not in (None, ""):
                try:
                    profile[key] = int(settings[explicit_key])
                except (TypeError, ValueError):
                    pass
        profile["num_ctx"] = min(32768, max(2048, int(profile["num_ctx"])))
        profile["num_predict"] = min(4096, max(256, int(profile["num_predict"])))
        profile["max_images"] = min(12, max(1, int(profile["max_images"])))
        profile["text_context_chars"] = min(20000, max(1000, int(profile["text_context_chars"])))
        return profile

    def _is_ollama_provider(self, settings: Dict[str, Any]) -> bool:
        return str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"])) == "ollama"

    def _limit_ollama_frames(self, settings: Dict[str, Any], frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self._is_ollama_provider(settings):
            return frames
        profile = self._ollama_runtime_profile(settings)
        limit = int(profile["max_images"])
        if len(frames) <= limit:
            return frames
        if limit == 1:
            return [frames[len(frames) // 2]]
        indexes = [
            int(round(index * (len(frames) - 1) / (limit - 1)))
            for index in range(limit)
        ]
        unique_indexes = list(dict.fromkeys(max(0, min(len(frames) - 1, index)) for index in indexes))
        return [frames[index] for index in unique_indexes]

    def _whisper_config_label(self, task: VideoTask) -> str:
        if not task.request.enable_whisper_transcription:
            return "Whisper disabled"
        model = self._normalize_whisper_model_name(task.request.whisper_model)
        return f"Whisper enabled: openai-whisper model={model}"

    def _whisper_runtime_label(self, task: VideoTask, device: str, use_fp16: bool) -> str:
        model = self._normalize_whisper_model_name(task.request.whisper_model)
        return f"openai-whisper model={model}, device={device}, fp16={str(use_fp16).lower()}"

    def _find_step(self, task: VideoTask, step_id: str) -> Optional[VideoTaskStep]:
        for step in task.subtasks:
            if step.id == step_id:
                return step
        return None

    def _start_step(
        self,
        task: VideoTask,
        step_id: str,
        label: str,
        *,
        phase: str = "",
        item_id: str = "",
        message: str = "",
    ) -> VideoTaskStep:
        now = datetime.now(LOCAL_TZ).isoformat()
        existing = self._find_step(task, step_id)
        if existing:
            existing.label = label
            existing.phase = phase or existing.phase
            existing.item_id = item_id or existing.item_id
            existing.status = "running"
            existing.started_at = existing.started_at or now
            existing.completed_at = None
            existing.duration_seconds = None
            existing.message = message or existing.message
            self._save_task_state(task)
            return existing
        step = VideoTaskStep(
            id=step_id,
            label=label,
            phase=phase,
            item_id=item_id,
            status="running",
            started_at=now,
            message=message,
        )
        task.subtasks.append(step)
        if len(task.subtasks) > 80:
            task.subtasks = task.subtasks[-80:]
        self._save_task_state(task)
        return step

    def _update_step(
        self,
        task: VideoTask,
        step_id: str,
        *,
        progress_percent: Optional[float] = None,
        transferred_bytes: Optional[int] = None,
        total_bytes: Optional[int] = None,
        speed_bps: Optional[float] = None,
        message: str = "",
    ) -> None:
        step = self._find_step(task, step_id)
        if not step:
            return
        if progress_percent is not None:
            step.progress_percent = max(0.0, min(100.0, float(progress_percent)))
        if transferred_bytes is not None:
            step.transferred_bytes = max(0, int(transferred_bytes))
        if total_bytes is not None:
            step.total_bytes = max(0, int(total_bytes))
        if speed_bps is not None:
            step.speed_bps = max(0.0, float(speed_bps))
        if message:
            step.message = message
        self._save_task_state(task)

    def _finish_step(
        self,
        task: VideoTask,
        step_id: str,
        *,
        status: str = "completed",
        message: str = "",
        log: bool = True,
    ) -> None:
        step = self._find_step(task, step_id)
        if not step:
            return
        now_dt = datetime.now(LOCAL_TZ)
        step.completed_at = now_dt.isoformat()
        if step.started_at:
            try:
                started = datetime.fromisoformat(step.started_at)
                step.duration_seconds = max(0.0, (now_dt - started).total_seconds())
            except ValueError:
                step.duration_seconds = None
        step.status = status  # type: ignore[assignment]
        if message:
            step.message = message
        if status == "completed" and step.progress_percent is None:
            step.progress_percent = 100.0
        if log:
            outcome = {
                "completed": "completed",
                "failed": "failed",
                "skipped": "skipped",
            }.get(status, status)
            detail = f" ({step.message})" if step.message else ""
            task.add_log(f"Subtask {outcome} in {self._format_elapsed(step.duration_seconds)}: {step.label}{detail}")
        self._save_task_state(task, force=True)

    def _finish_running_steps(self, task: VideoTask, *, status: str, message: str = "") -> None:
        for step in list(task.subtasks):
            if step.status == "running":
                self._finish_step(task, step.id, status=status, message=message, log=False)

    async def _run_crawler(
        self,
        task: VideoTask,
        cmd: List[str],
        label: str = "Crawler command",
        *,
        monitor_filtered_candidates: bool = False,
    ) -> int:
        task.add_log(f"{label}: " + self._redact_command(cmd))

        env = {
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
        }
        create_kwargs: Dict[str, Any] = {}
        if os.name == "nt":
            create_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            create_kwargs["startupinfo"] = startupinfo

        return await asyncio.to_thread(self._run_crawler_blocking, task, cmd, env, create_kwargs, monitor_filtered_candidates)

    def _run_crawler_blocking(
        self,
        task: VideoTask,
        cmd: List[str],
        env: Dict[str, str],
        create_kwargs: Dict[str, Any],
        monitor_filtered_candidates: bool,
    ) -> int:
        process = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            **create_kwargs,
        )
        task.process = process

        def read_stdout() -> None:
            if not process.stdout:
                return
            for line in process.stdout:
                if task.cancel_requested:
                    self._terminate_process_tree(process)
                    break
                text = line.strip()
                if text:
                    task.add_log(text)

        reader = threading.Thread(target=read_stdout, name=f"video-crawler-log-{task.task_id}", daemon=True)
        reader.start()

        early_stop_reached = False
        last_matched_count = -1
        while process.poll() is None:
            if task.cancel_requested:
                self._terminate_process_tree(process)
                break
            if monitor_filtered_candidates and self._crawler_filtered_early_stop_enabled(task):
                raw_count, matched_count = self._current_filtered_candidate_counts(task)
                if matched_count != last_matched_count:
                    last_matched_count = matched_count
                    if raw_count:
                        self._update_step(
                            task,
                            "metadata",
                            message=(
                                f"matched {matched_count}/{task.request.max_videos} filtered candidate(s); "
                                f"raw {raw_count}/{self._task_crawl_limit(task)}"
                            ),
                        )
                if matched_count >= task.request.max_videos:
                    early_stop_reached = True
                    task.add_log(
                        f"Filtered candidate target reached ({matched_count}/{task.request.max_videos}); "
                        f"stopping MediaCrawler before raw cap {self._task_crawl_limit(task)}"
                    )
                    self._terminate_process_tree(process)
                    break
            time_module.sleep(1.0)

        exit_code = process.wait()
        reader.join(timeout=5.0)
        task.process = None
        if task.cancel_requested:
            task.add_log("MediaCrawler process stopped by user")
            return -1
        if early_stop_reached:
            task.add_log("MediaCrawler process stopped after filtered candidate target was reached")
            return 0
        task.add_log(f"MediaCrawler process exited with code {exit_code}")
        return int(exit_code or 0)

    def _crawler_filtered_early_stop_enabled(self, task: VideoTask) -> bool:
        if task.request.source_mode not in {"search", "creator"}:
            return False
        if task.request.workflow_mode == "selected_items":
            return False
        return self._task_crawl_limit(task) > max(1, int(task.request.max_videos or 1))

    def _current_filtered_candidate_counts(self, task: VideoTask) -> Tuple[int, int]:
        records = self._load_content_records(task.raw_data_dir)
        return len(records), self._count_filtered_video_records(task, records)

    def _count_filtered_video_records(
        self,
        task: VideoTask,
        records: List[Dict[str, Any]],
        *,
        apply_date_filter: bool = True,
    ) -> int:
        seen: set[str] = set()
        count = 0
        for record in records:
            if not self._record_matches_video_filters(task, record, apply_date_filter=apply_date_filter):
                continue
            key = self._record_identity(task.request.platform.value, record)
            if key in seen:
                continue
            seen.add(key)
            count += 1
            if count >= task.request.max_videos:
                break
        return count

    def _record_identity(self, platform: str, record: Dict[str, Any]) -> str:
        for key in CONTENT_ID_KEYS.get(platform, []):
            value = str(record.get(key) or "").strip()
            if value:
                return f"{platform}:{key}:{value}"
        for key in URL_KEYS:
            value = str(record.get(key) or "").strip()
            if value:
                return f"{platform}:url:{value}"
        return f"{platform}:object:{hash(json.dumps(record, sort_keys=True, ensure_ascii=False, default=str))}"

    def _terminate_process_tree(self, process: subprocess.Popen[Any]) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=10,
                    check=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return
            except Exception:
                pass
        try:
            process.terminate()
        except Exception:
            try:
                process.kill()
            except Exception:
                pass

    def _build_base_crawler_command(self, task: VideoTask, crawler_type: str, enable_get_medias: bool) -> List[str]:
        req = task.request
        crawl_limit = self._task_crawl_limit(task)
        cmd = [
            "uv",
            "run",
            "python",
            "main.py",
            "--platform",
            req.platform.value,
            "--lt",
            req.login_type.value,
            "--type",
            crawler_type,
            "--save_data_option",
            "json",
            "--save_data_path",
            str(task.raw_data_dir),
            "--get_comment",
            "false",
            "--get_sub_comment",
            "false",
            "--headless",
            "true" if req.headless else "false",
            "--enable_cdp_mode",
            "false" if req.headless else "true",
            "--cdp_connect_existing",
            "false" if req.headless else "true",
            "--crawler_max_notes_count",
            str(crawl_limit),
            "--max_concurrency_num",
            str(max(1, min(int(req.crawl_concurrency or 1), 8))),
            "--enable_get_medias",
            "true" if enable_get_medias else "false",
            "--crawler_min_sleep_sec",
            str(req.crawl_min_sleep_seconds if req.crawl_min_sleep_seconds is not None else req.crawl_sleep_seconds),
            "--crawler_max_sleep_sec",
            str(req.crawl_max_sleep_seconds if req.crawl_max_sleep_seconds is not None else req.crawl_sleep_seconds),
            "--crawler_long_pause_every",
            str(req.crawl_long_pause_every),
            "--crawler_long_pause_min_sec",
            str(req.crawl_long_pause_min_seconds),
            "--crawler_long_pause_max_sec",
            str(req.crawl_long_pause_max_seconds),
        ]
        if req.cookies:
            cmd.extend(["--cookies", req.cookies])
        return cmd

    def _task_crawl_limit(self, task: VideoTask) -> int:
        requested = int(task.request.max_crawl_items or task.request.max_videos or 20)
        filtered = int(task.request.max_videos or 20)
        return max(1, min(max(requested, filtered), 500))

    def _build_creator_metadata_command(self, task: VideoTask) -> List[str]:
        cmd = self._build_base_crawler_command(task, "creator", enable_get_medias=False)
        cmd.extend([
            "--creator_id",
            task.request.creator_id,
            "--creator_video_only",
            "true",
        ])
        return cmd

    def _build_search_metadata_command(self, task: VideoTask) -> List[str]:
        keyword = (task.request.search_keyword or task.request.creator_id).strip()
        cmd = self._build_base_crawler_command(task, "search", enable_get_medias=False)
        cmd.extend([
            "--keywords",
            keyword,
            "--creator_video_only",
            "true",
        ])
        if task.request.platform.value == "wb":
            cmd.extend([
                "--weibo_search_type",
                "video",
                "--enable_weibo_full_text",
                "false",
            ])
        return cmd

    def _build_detail_download_command(self, task: VideoTask, specified_ids: List[str]) -> List[str]:
        cmd = self._build_base_crawler_command(task, "detail", enable_get_medias=True)
        cmd.extend(["--specified_id", ",".join(specified_ids)])
        return cmd

    def _load_content_records(self, raw_data_dir: Path) -> List[Dict[str, Any]]:
        records: List[Dict[str, Any]] = []
        for json_file in raw_data_dir.rglob("*contents*.json"):
            try:
                with json_file.open("r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    records.extend(item for item in data if isinstance(item, dict))
                elif isinstance(data, dict):
                    records.append(data)
            except Exception:
                continue

        for jsonl_file in raw_data_dir.rglob("*contents*.jsonl"):
            try:
                with jsonl_file.open("r", encoding="utf-8-sig") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        if isinstance(data, dict):
                            records.append(data)
            except Exception:
                continue
        return records

    async def _fetch_platform_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        platform = task.request.platform.value
        if platform == "bili":
            task.add_log("Ranking source uses Bilibili current platform ranking; publish date filter is skipped.")
            return await self._fetch_bili_ranking_records(task)
        if platform == "ks":
            task.add_log(
                "Ranking source uses Kuaishou short-video hot rank photoIds; "
                "publish date filter is skipped. Direct video URLs still depend on Kuaishou detail/search APIs."
            )
            return await self._fetch_ks_ranking_records(task)
        if platform == "dy":
            task.add_log("Ranking source uses Douyin hot-search topic list. These are hot topics, not direct video files.")
            return await self._fetch_douyin_hot_ranking_records(task)
        if platform == "wb":
            task.add_log("Ranking source uses Weibo hot band topic list. These are hot topics, not direct video files.")
            return await self._fetch_weibo_hot_ranking_records(task)
        if platform == "zhihu":
            task.add_log("Ranking source uses Zhihu hot list. These are hot questions/cards, not direct zvideo files.")
            return await self._fetch_zhihu_hot_ranking_records(task)
        if platform == "tieba":
            task.add_log("Ranking source uses Baidu Tieba hot topic list. These are hot topics, not direct video files.")
            return await self._fetch_tieba_hot_ranking_records(task)

        label = PLATFORM_LABELS.get(platform, platform)
        raise RuntimeError(
            f"{label} platform ranking is not wired to a verified platform-native list endpoint yet. "
            "Use source mode 'search' with a keyword/video title for this platform."
        )

    async def _fetch_bili_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_bili_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(BILI_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        if ranking_type == "popular":
            url = "https://api.bilibili.com/x/web-interface/popular"
            params: Dict[str, Any] = {"ps": limit, "pn": 1}
            source_name = "bili_popular"
        elif ranking_type == "precious":
            url = "https://api.bilibili.com/x/web-interface/popular/precious"
            params = {"page_size": limit, "page": 1}
            source_name = "bili_precious"
        elif ranking_type == "weekly":
            return await self._fetch_bili_weekly_records(task, headers=headers, limit=limit)
        elif ranking_type == "hot_search":
            return await self._fetch_bili_hot_search_records(task, headers=headers, limit=limit)
        else:
            rid, region_label = BILI_RANKING_REGIONS.get(ranking_type, BILI_RANKING_REGIONS["ranking"])
            url = "https://api.bilibili.com/x/web-interface/ranking/v2"
            params = {"rid": rid, "type": "all"}
            source_name = f"bili_{ranking_type}"

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        if payload.get("code") != 0:
            raise RuntimeError(f"Bilibili ranking API failed: {payload.get('message') or payload}")

        raw_items = ((payload.get("data") or {}).get("list") or [])
        if not isinstance(raw_items, list):
            return []

        records = [
            self._bili_ranking_item_to_record(raw_item, index=index, source_name=source_name)
            for index, raw_item in enumerate(raw_items[:limit], start=1)
            if isinstance(raw_item, dict)
        ]
        if ranking_type in BILI_RANKING_REGIONS:
            _, region_label = BILI_RANKING_REGIONS.get(ranking_type, BILI_RANKING_REGIONS["ranking"])
            for record in records:
                record["ranking_tag"] = region_label
        task.add_log(f"Fetched Bilibili {ranking_type} Top {len(records)}")
        return records

    def _normalize_bili_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        aliases = {
            "rank": "ranking",
            "chart": "ranking",
            "bili_ranking": "ranking",
            "all": "ranking",
            "popular": "popular",
            "hot": "popular",
            "precious": "precious",
            "must_watch": "precious",
            "mustwatch": "precious",
            "weekly": "weekly",
            "weekly_latest": "weekly",
            "series": "weekly",
            "hot_search": "hot_search",
            "search_hot": "hot_search",
        }
        raw = aliases.get(raw, raw)
        if raw == "ranking":
            return "ranking"
        if raw in BILI_RANKING_REGIONS:
            return raw
        if raw in {"popular", "precious", "weekly", "hot_search"}:
            return raw
        return "popular"

    def _bili_ranking_item_to_record(self, raw_item: Dict[str, Any], *, index: int, source_name: str) -> Dict[str, Any]:
        aid = str(raw_item.get("aid") or "")
        bvid = str(raw_item.get("bvid") or "")
        owner = raw_item.get("owner") if isinstance(raw_item.get("owner"), dict) else {}
        stat = raw_item.get("stat") if isinstance(raw_item.get("stat"), dict) else {}
        title = str(raw_item.get("title") or "")
        desc = str(raw_item.get("desc") or raw_item.get("dynamic") or "")
        pubdate = raw_item.get("pubdate") or raw_item.get("ctime")
        video_url = str(raw_item.get("short_link_v2") or raw_item.get("arcurl") or "")
        if not video_url and bvid:
            video_url = f"https://www.bilibili.com/video/{bvid}"
        elif not video_url and aid:
            video_url = f"https://www.bilibili.com/video/av{aid}"

        return {
            **raw_item,
            "type": "video",
            "video_id": aid or bvid,
            "aid": aid,
            "bvid": bvid,
            "title": title,
            "desc": desc,
            "pubdate": pubdate,
            "publish_time": pubdate,
            "url": video_url,
            "arcurl": video_url,
            "video_cover_url": str(raw_item.get("pic") or raw_item.get("cover") or raw_item.get("first_frame") or ""),
            "cover": str(raw_item.get("pic") or raw_item.get("cover") or raw_item.get("first_frame") or ""),
            "creator_id": str(owner.get("mid") or ""),
            "creator_name": str(owner.get("name") or ""),
            "rank": index,
            "ranking_source": source_name,
            "ranking_score": raw_item.get("score") or stat.get("view"),
            "source": source_name,
        }

    async def _fetch_bili_weekly_records(
        self,
        task: VideoTask,
        *,
        headers: Dict[str, str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            list_response = await client.get("https://api.bilibili.com/x/web-interface/popular/series/list")
            list_response.raise_for_status()
            list_payload = list_response.json()
            if list_payload.get("code") != 0:
                raise RuntimeError(f"Bilibili weekly series list API failed: {list_payload.get('message') or list_payload}")
            series_list = ((list_payload.get("data") or {}).get("list") or [])
            if not isinstance(series_list, list) or not series_list:
                return []
            latest_number = (series_list[0] or {}).get("number")
            one_response = await client.get("https://api.bilibili.com/x/web-interface/popular/series/one", params={"number": latest_number})
            one_response.raise_for_status()
            one_payload = one_response.json()

        if one_payload.get("code") != 0:
            raise RuntimeError(
                "Bilibili weekly series API failed: "
                f"{one_payload.get('message') or one_payload}. This endpoint may require a valid Bilibili cookie."
            )
        data = one_payload.get("data") if isinstance(one_payload.get("data"), dict) else {}
        config_data = data.get("config") if isinstance(data.get("config"), dict) else {}
        raw_items = data.get("list") or []
        if not isinstance(raw_items, list):
            return []
        source_name = "bili_weekly"
        records = [
            self._bili_ranking_item_to_record(raw_item, index=index, source_name=source_name)
            for index, raw_item in enumerate(raw_items[:limit], start=1)
            if isinstance(raw_item, dict)
        ]
        label = str(config_data.get("label") or config_data.get("name") or "")
        subject = str(config_data.get("subject") or "")
        for record in records:
            record["ranking_tag"] = label
            record["ranking_subject"] = subject
            if subject:
                record["desc"] = f"{subject} | {record.get('desc') or ''}".strip(" |")
        task.add_log(f"Fetched Bilibili weekly latest Top {len(records)}")
        return records

    async def _fetch_bili_hot_search_records(
        self,
        task: VideoTask,
        *,
        headers: Dict[str, str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get("https://api.bilibili.com/x/web-interface/search/square", params={"limit": limit})
            response.raise_for_status()
            payload = response.json()

        if payload.get("code") != 0:
            raise RuntimeError(f"Bilibili hot-search API failed: {payload.get('message') or payload}")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        trending = data.get("trending") if isinstance(data.get("trending"), dict) else {}
        raw_items = trending.get("list") or []
        if not isinstance(raw_items, list):
            return []
        records: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            record = self._bili_hot_search_item_to_record(raw_item, index=len(records) + 1)
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        task.add_log(f"Fetched Bilibili hot_search Top {len(records)} topic item(s)")
        return records

    def _bili_hot_search_item_to_record(self, raw_item: Dict[str, Any], *, index: int) -> Optional[Dict[str, Any]]:
        keyword = str(raw_item.get("keyword") or raw_item.get("show_name") or "").strip()
        if not keyword:
            return None
        title = str(raw_item.get("show_name") or keyword)
        heat_score = raw_item.get("heat_score")
        icon = str(raw_item.get("icon") or "")
        return {
            **raw_item,
            "type": "ranking_topic",
            "ranking_item_type": "topic",
            "ranking_item_id": f"bili_hot:{keyword}",
            "title": title,
            "desc": f"Bilibili hot search #{index}",
            "url": f"https://search.bilibili.com/all?keyword={quote(keyword)}",
            "search_keyword": keyword,
            "rank": index,
            "hot_value": heat_score,
            "video_cover_url": icon,
            "cover": icon,
            "ranking_source": "bili_hot_search",
            "ranking_score": heat_score,
            "source": "bili_hot_search",
            "detail_status": "topic_only",
            "detail_note": "Bilibili hot-search returns topics/keywords; use this item as a video-search keyword.",
        }

    async def _fetch_ks_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_ks_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(KS_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        payload = {
            "operationName": "hotRankQuery",
            "variables": {"page": "brilliant"},
            "query": KS_HOT_RANK_QUERY,
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.post(
                "https://www.kuaishou.com/graphql",
                json=payload,
            )
            response.raise_for_status()
            payload_json = response.json()

        if payload_json.get("errors"):
            raise RuntimeError(f"Kuaishou hot rank GraphQL failed: {payload_json.get('errors')}")

        data = ((payload_json.get("data") or {}).get("visionHotRank") or {})
        raw_items = data.get("items") or []
        if not isinstance(raw_items, list):
            return []

        records: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            record = self._ks_ranking_item_to_record(raw_item, index=len(records) + 1, source_name=f"ks_{ranking_type}_rank")
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break

        task.add_log(f"Fetched Kuaishou {ranking_type} Top {len(records)} video candidate(s)")
        return records

    def _normalize_ks_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"hot", "hotrank", "hot_rank", "ranking", "rank", "popular", "ks_hot"}:
            return "hot"
        return "hot"

    def _ks_ranking_item_to_record(self, raw_item: Dict[str, Any], *, index: int, source_name: str) -> Optional[Dict[str, Any]]:
        photo_ids = raw_item.get("photoIds")
        if isinstance(photo_ids, dict):
            photo_ids = photo_ids.get("json")
        if not isinstance(photo_ids, list):
            photo_ids = []
        photo_id = next((str(value).strip() for value in photo_ids if str(value).strip()), "")
        if not photo_id:
            return None

        topic_name = str(raw_item.get("name") or raw_item.get("id") or photo_id)
        hot_value = str(raw_item.get("hotValue") or "").strip()
        raw_rank = self._safe_int(raw_item.get("rank"))
        display_rank = index
        video_url = f"https://www.kuaishou.com/short-video/{photo_id}?streamSource=hotrank"
        if topic_name:
            video_url += f"&trendingId={quote(topic_name)}"

        desc_parts = [f"Kuaishou hot rank #{display_rank}", topic_name]
        if hot_value:
            desc_parts.append(f"hot value {hot_value}")
        tag_type = str(raw_item.get("tagType") or "").strip()
        if tag_type:
            desc_parts.append(f"tag {tag_type}")

        return {
            **raw_item,
            "type": "video",
            "video_id": photo_id,
            "photo_id": photo_id,
            "title": topic_name,
            "desc": " | ".join(part for part in desc_parts if part),
            "url": video_url,
            "video_url": video_url,
            "video_cover_url": str(raw_item.get("poster") or ""),
            "cover": str(raw_item.get("poster") or ""),
            "viewd_count": raw_item.get("viewCount"),
            "view_count": raw_item.get("viewCount"),
            "hot_value": hot_value,
            "rank": display_rank,
            "platform_rank": raw_rank,
            "ranking_source": source_name,
            "ranking_score": hot_value or raw_item.get("viewCount"),
            "ranking_tag": tag_type,
            "source": source_name,
            "detail_status": "photo_id_only",
            "detail_note": (
                "Kuaishou hot rank exposes photoIds and cover metadata; "
                "direct video URLs require Kuaishou detail/search APIs and may be blocked by captcha."
            ),
        }

    async def _fetch_douyin_hot_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_douyin_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(DOUYIN_HOT_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get("https://www.douyin.com/aweme/v1/web/hot/search/list/", params={"detail_list": 1})
            response.raise_for_status()
            payload = response.json()

        if payload.get("status_code") not in (None, 0):
            raise RuntimeError(f"Douyin hot-search API failed: {payload}")

        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        list_key = "trending_list" if ranking_type == "trending" else "word_list"
        raw_items = data.get(list_key) or []
        if not isinstance(raw_items, list):
            return []

        records: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            record = self._douyin_hot_item_to_record(raw_item, index=len(records) + 1, source_name=f"dy_{ranking_type}")
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        task.add_log(f"Fetched Douyin {ranking_type} Top {len(records)} hot topic item(s)")
        return records

    def _normalize_douyin_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"trending", "trend", "douyin_trending"}:
            return "trending"
        return "hot_search"

    def _douyin_hot_item_to_record(self, raw_item: Dict[str, Any], *, index: int, source_name: str) -> Optional[Dict[str, Any]]:
        word = str(raw_item.get("word") or "").strip()
        if not word:
            return None
        sentence_id = str(raw_item.get("sentence_id") or raw_item.get("group_id") or word)
        cover = ""
        word_cover = raw_item.get("word_cover")
        if isinstance(word_cover, dict):
            url_list = word_cover.get("url_list")
            if isinstance(url_list, list):
                cover = next((str(url) for url in url_list if url), "")
        rank = self._safe_int(raw_item.get("position")) or index
        hot_value = raw_item.get("hot_value")
        video_count = raw_item.get("video_count") or raw_item.get("discuss_video_count")
        search_url = f"https://www.douyin.com/search/{quote(word)}?type=video"
        return {
            **raw_item,
            "type": "ranking_topic",
            "ranking_item_type": "topic",
            "ranking_item_id": f"dy:{sentence_id}",
            "title": word,
            "desc": f"Douyin hot topic #{rank}" + (f" | videos {video_count}" if video_count is not None else ""),
            "url": search_url,
            "search_keyword": word,
            "video_cover_url": cover,
            "cover": cover,
            "rank": rank,
            "hot_value": hot_value,
            "video_count": video_count,
            "ranking_source": source_name,
            "ranking_score": hot_value,
            "source": source_name,
            "detail_status": "topic_only",
            "detail_note": "Douyin hot-search returns topics/words; use this item as a video-search keyword.",
        }

    async def _fetch_weibo_hot_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_weibo_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(WEIBO_HOT_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get("https://weibo.com/ajax/statuses/hot_band")
            response.raise_for_status()
            payload = response.json()

        if payload.get("ok") != 1:
            raise RuntimeError(f"Weibo hot band API failed: {payload}")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if ranking_type == "hot_gov":
            raw_hotgov = data.get("hotgov")
            raw_items = [raw_hotgov] if isinstance(raw_hotgov, dict) else []
        else:
            raw_items = data.get("band_list") or []
        if not isinstance(raw_items, list):
            return []

        records: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            record = self._weibo_hot_item_to_record(raw_item, index=len(records) + 1, source_name=f"wb_{ranking_type}")
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        task.add_log(f"Fetched Weibo {ranking_type} Top {len(records)} hot topic item(s)")
        return records

    def _normalize_weibo_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"hot_gov", "hotgov", "gov", "government", "official"}:
            return "hot_gov"
        return "hot_search"

    def _weibo_hot_item_to_record(self, raw_item: Dict[str, Any], *, index: int, source_name: str) -> Optional[Dict[str, Any]]:
        word = str(raw_item.get("word") or raw_item.get("name") or raw_item.get("note") or raw_item.get("word_scheme") or "").strip().strip("#")
        if not word:
            return None
        rank = self._safe_int(raw_item.get("rank")) or self._safe_int(raw_item.get("pos")) or index
        hot_value = raw_item.get("num") or raw_item.get("onboard_time")
        category = str(raw_item.get("category") or "").strip()
        label = str(raw_item.get("label_name") or raw_item.get("icon_desc") or "").strip()
        source_url = str(raw_item.get("url") or "").strip()
        search_url = source_url or f"https://s.weibo.com/weibo?q={quote(word)}"
        desc_parts = [f"Weibo hot topic #{rank}"]
        if category:
            desc_parts.append(category)
        if label:
            desc_parts.append(label)
        return {
            **raw_item,
            "type": "ranking_topic",
            "ranking_item_type": "topic",
            "ranking_item_id": f"wb:{word}",
            "title": word,
            "desc": " | ".join(desc_parts),
            "url": search_url,
            "search_keyword": word,
            "rank": rank,
            "hot_value": hot_value,
            "ranking_source": source_name,
            "ranking_score": hot_value,
            "ranking_tag": label,
            "source": source_name,
            "detail_status": "topic_only",
            "detail_note": "Weibo hot band returns topics/words; use this item as a video-search keyword.",
        }

    async def _fetch_zhihu_hot_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_zhihu_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(ZHIHU_HOT_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get(f"https://www.zhihu.com/api/v3/feed/topstory/hot-lists/{ranking_type}", params={"limit": limit})
            response.raise_for_status()
            payload = response.json()

        if payload.get("error"):
            raise RuntimeError(f"Zhihu hot list API failed: {payload.get('error')}")
        raw_items = payload.get("data") or []
        if not isinstance(raw_items, list):
            return []

        records: List[Dict[str, Any]] = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            record = self._zhihu_hot_item_to_record(raw_item, index=len(records) + 1, source_name=f"zhihu_{ranking_type}_hot")
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        task.add_log(f"Fetched Zhihu {ranking_type} Top {len(records)} hot item(s)")
        return records

    def _normalize_zhihu_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"total", "hot", "hot_question", "hot_questions", "question"}:
            return "total"
        if raw in {"video", "zvideo"}:
            return "zvideo"
        return "total"

    def _zhihu_hot_item_to_record(self, raw_item: Dict[str, Any], *, index: int, source_name: str) -> Optional[Dict[str, Any]]:
        target = raw_item.get("target") if isinstance(raw_item.get("target"), dict) else {}
        title_area = target.get("title_area") if isinstance(target.get("title_area"), dict) else {}
        excerpt_area = target.get("excerpt_area") if isinstance(target.get("excerpt_area"), dict) else {}
        image_area = target.get("image_area") if isinstance(target.get("image_area"), dict) else {}
        metrics_area = target.get("metrics_area") if isinstance(target.get("metrics_area"), dict) else {}
        link = target.get("link") if isinstance(target.get("link"), dict) else {}
        title = str(title_area.get("text") or target.get("title") or raw_item.get("id") or "").strip()
        if not title:
            return None
        url = str(link.get("url") or target.get("url") or "")
        item_id = str(raw_item.get("card_id") or raw_item.get("id") or url or title)
        metrics_text = str(metrics_area.get("text") or "").strip()
        cover = str(image_area.get("url") or image_area.get("image") or "")
        return {
            **raw_item,
            "type": "ranking_topic",
            "ranking_item_type": "question",
            "ranking_item_id": f"zhihu:{item_id}",
            "title": title,
            "desc": str(excerpt_area.get("text") or metrics_text or f"Zhihu hot item #{index}"),
            "url": url,
            "search_keyword": title,
            "rank": index,
            "hot_value": metrics_text,
            "video_cover_url": cover,
            "cover": cover,
            "ranking_source": source_name,
            "ranking_score": metrics_text,
            "source": source_name,
            "detail_status": "question_only",
            "detail_note": "Zhihu hot list returns questions/cards; use this item as a video-search keyword if needed.",
        }

    async def _fetch_tieba_hot_ranking_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        ranking_type = self._normalize_tieba_ranking_type(task.request.ranking_type)
        limit = max(1, min(int(task.request.ranking_limit or task.request.max_videos or 5), 50))
        headers = dict(TIEBA_HOT_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            response = await client.get("https://tieba.baidu.com/hottopic/browse/topicList", params={"res_type": 1})
            response.raise_for_status()
            html_text = response.text

        raw_items = re.findall(r'<li class="[^"]*topic-top-item[^"]*"[^>]*>(.*?)</li>', html_text, flags=re.S)
        records: List[Dict[str, Any]] = []
        for raw_html in raw_items:
            record = self._tieba_hot_item_to_record(raw_html, index=len(records) + 1, source_name=f"tieba_{ranking_type}")
            if not record:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        task.add_log(f"Fetched Tieba {ranking_type} Top {len(records)} hot topic item(s)")
        return records

    def _normalize_tieba_ranking_type(self, value: str) -> str:
        raw = str(value or "").strip().lower()
        if raw in {"hot", "hot_topic", "topic", "hottopic", "ranking", "rank"}:
            return "hot_topic"
        return "hot_topic"

    def _tieba_hot_item_to_record(self, raw_html: str, *, index: int, source_name: str) -> Optional[Dict[str, Any]]:
        link_match = re.search(r'<a[^>]+href="([^"]+)"[^>]*class="topic-text"[^>]*>(.*?)</a>', raw_html, flags=re.S)
        if not link_match:
            return None
        url = unescape(link_match.group(1)).strip()
        title = self._strip_inline_html(link_match.group(2))
        if not title:
            return None
        cover_match = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="topic-cover"', raw_html, flags=re.S)
        cover = unescape(cover_match.group(1)).strip() if cover_match else ""
        discussion_match = re.search(r'<span[^>]*class="topic-num"[^>]*>(.*?)</span>', raw_html, flags=re.S)
        discussion_text = self._strip_inline_html(discussion_match.group(1)) if discussion_match else ""
        desc_match = re.search(r'<p[^>]*class="[^"]*topic-top-item-desc[^"]*"[^>]*>(.*?)</p>', raw_html, flags=re.S)
        desc = self._strip_inline_html(desc_match.group(1)) if desc_match else ""
        topic_id = self._regex_first(url, r"topic_id=(\d+)") or title
        hot_value = discussion_text.replace("实时讨论", "").replace("W", "万").strip()
        return {
            "type": "ranking_topic",
            "ranking_item_type": "topic",
            "ranking_item_id": f"tieba:{topic_id}",
            "title": title,
            "desc": desc or f"Tieba hot topic #{index}",
            "url": url,
            "search_keyword": title,
            "rank": index,
            "hot_value": hot_value,
            "hot_value_text": discussion_text,
            "video_cover_url": cover,
            "cover": cover,
            "ranking_source": source_name,
            "ranking_score": hot_value,
            "source": source_name,
            "video_search_supported": False,
            "detail_status": "topic_only",
            "detail_note": "Tieba hot topic list is not a video source in this demo; view the topic, or search this keyword on a supported video platform.",
        }

    @staticmethod
    def _strip_inline_html(value: str) -> str:
        text = re.sub(r"<[^>]+>", "", value or "")
        return unescape(re.sub(r"\s+", " ", text)).strip()

    def _save_source_records(self, task: VideoTask, records: List[Dict[str, Any]], file_name: str) -> None:
        output_path = task.raw_data_dir / file_name
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    async def _fetch_bili_search_records(self, task: VideoTask) -> List[Dict[str, Any]]:
        keyword = str(task.request.search_keyword or task.request.creator_id or "").strip()
        if not keyword:
            return []
        headers = {
            **BILI_HEADERS,
            "Referer": f"https://search.bilibili.com/all?keyword={quote(keyword)}",
        }
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        start_dt = datetime.combine(task.request.start_date, time.min, tzinfo=LOCAL_TZ)
        end_dt = datetime.combine(task.request.end_date, time.max, tzinfo=LOCAL_TZ)
        crawl_limit = self._task_crawl_limit(task)
        page_size = min(20, max(1, crawl_limit))
        max_pages = min(25, max(1, (crawl_limit + page_size - 1) // page_size + 2))
        records: List[Dict[str, Any]] = []
        matched_count = 0

        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            img_key, sub_key = await self._fetch_bili_wbi_keys(client)
            for page in range(1, max_pages + 1):
                params: Dict[str, Any] = {
                    "search_type": "video",
                    "keyword": keyword,
                    "page": page,
                    "page_size": page_size,
                    "order": "totalrank",
                    "pubtime_begin_s": int(start_dt.timestamp()),
                    "pubtime_end_s": int(end_dt.timestamp()),
                }
                if img_key and sub_key:
                    params = self._sign_bili_wbi(params, img_key, sub_key)
                response = await client.get("https://api.bilibili.com/x/web-interface/wbi/search/type", params=params)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(f"Bilibili search API failed: {payload.get('message') or payload}")

                data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
                raw_items = data.get("result") or []
                if not isinstance(raw_items, list) or not raw_items:
                    break
                for raw_item in raw_items:
                    if not isinstance(raw_item, dict):
                        continue
                    record = self._bili_search_item_to_record(raw_item, keyword)
                    if not record:
                        continue
                    records.append(record)
                    if self._record_matches_video_filters(task, record):
                        matched_count += 1
                        if matched_count >= task.request.max_videos:
                            task.add_log(
                                f"Bili direct search reached filtered candidate target "
                                f"({matched_count}/{task.request.max_videos}); stopped before raw cap {crawl_limit}"
                            )
                            break
                    if len(records) >= crawl_limit:
                        break
                if matched_count >= task.request.max_videos or len(records) >= crawl_limit or len(raw_items) < page_size:
                    break
        return records

    def _bili_search_item_to_record(self, raw_item: Dict[str, Any], keyword: str) -> Optional[Dict[str, Any]]:
        aid = str(raw_item.get("aid") or "")
        bvid = str(raw_item.get("bvid") or "")
        if not aid and not bvid:
            return None
        title = self._strip_inline_html(str(raw_item.get("title") or ""))
        desc = self._strip_inline_html(str(raw_item.get("description") or raw_item.get("desc") or ""))
        pubdate = raw_item.get("pubdate") or raw_item.get("senddate")
        video_url = str(raw_item.get("arcurl") or "")
        if not video_url and bvid:
            video_url = f"https://www.bilibili.com/video/{bvid}"
        elif not video_url and aid:
            video_url = f"https://www.bilibili.com/video/av{aid}"
        cover = str(raw_item.get("pic") or raw_item.get("cover") or "")
        if cover.startswith("//"):
            cover = "https:" + cover
        return {
            **raw_item,
            "type": "video",
            "video_id": aid or bvid,
            "aid": aid,
            "bvid": bvid,
            "title": title,
            "desc": desc,
            "pubdate": pubdate,
            "publish_time": pubdate,
            "create_time": pubdate,
            "url": video_url,
            "arcurl": video_url,
            "video_cover_url": cover,
            "cover": cover,
            "creator_id": str(raw_item.get("mid") or ""),
            "creator_name": str(raw_item.get("author") or ""),
            "view_count": raw_item.get("play"),
            "danmaku_count": raw_item.get("video_review"),
            "favorite_count": raw_item.get("favorites"),
            "reply_count": raw_item.get("review"),
            "search_keyword": keyword,
            "source": "bili_direct_search",
        }

    async def _fetch_bili_creator_records_fallback(self, task: VideoTask) -> List[Dict[str, Any]]:
        direct_creator_id = str(task.request.creator_id or "").strip()
        if direct_creator_id.isdigit():
            try:
                records = await self._fetch_bili_creator_arc_records(task, direct_creator_id)
                if records:
                    task.add_log(f"Bili metadata fallback loaded {len(records)} records from signed space arc API")
                    return records
            except Exception as exc:
                task.add_log(
                    f"Bili signed space arc fallback failed for UID {direct_creator_id}: {type(exc).__name__}: {exc}"
                )

        queries = [
            task.request.creator_display_name,
            task.request.creator_id,
        ]
        seen_queries: set[str] = set()
        for query in queries:
            query = str(query or "").strip()
            if not query or query in seen_queries:
                continue
            seen_queries.add(query)
            try:
                resolve_request = CreatorResolveRequest(platform=task.request.platform, query=query)
                candidates = await self._search_bili_creators(resolve_request, query)
            except Exception as exc:
                task.add_log(f"Bili metadata fallback search failed for {query}: {type(exc).__name__}: {exc}")
                continue

            candidate = self._pick_bili_fallback_candidate(task, candidates)
            if not candidate:
                continue
            records = self._bili_candidate_video_records(candidate)
            if records:
                task.add_log(
                    f"Bili metadata fallback selected {candidate.display_name} ({candidate.id}) with {len(records)} recent videos"
                )
                return records
        return []

    async def _fetch_bili_creator_arc_records(self, task: VideoTask, creator_id: str) -> List[Dict[str, Any]]:
        headers = {
            **BILI_HEADERS,
            "Referer": f"https://space.bilibili.com/{creator_id}/video",
        }
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        records: List[Dict[str, Any]] = []
        page = 1
        crawl_limit = self._task_crawl_limit(task)
        page_size = min(30, max(1, crawl_limit))
        matched_count = 0
        async with httpx.AsyncClient(timeout=30.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            img_key, sub_key = await self._fetch_bili_wbi_keys(client)
            while len(records) < crawl_limit:
                params: Dict[str, Any] = {
                    "mid": creator_id,
                    "pn": page,
                    "ps": page_size,
                    "order": "pubdate",
                }
                if img_key and sub_key:
                    params = self._sign_bili_wbi(params, img_key, sub_key)
                response = await client.get("https://api.bilibili.com/x/space/wbi/arc/search", params=params)
                response.raise_for_status()
                payload = response.json()
                if payload.get("code") != 0:
                    raise RuntimeError(f"Bilibili space arc API failed: {payload.get('message') or payload}")

                data = payload.get("data") or {}
                raw_videos = ((data.get("list") or {}).get("vlist") or [])
                if not isinstance(raw_videos, list) or not raw_videos:
                    break

                for raw_video in raw_videos:
                    if not isinstance(raw_video, dict):
                        continue
                    record = self._bili_space_arc_item_to_record(raw_video, creator_id)
                    records.append(record)
                    if self._record_matches_video_filters(task, record):
                        matched_count += 1
                        if matched_count >= task.request.max_videos:
                            task.add_log(
                                f"Bili direct creator reached filtered candidate target "
                                f"({matched_count}/{task.request.max_videos}); stopped before raw cap {crawl_limit}"
                            )
                            break
                    if len(records) >= crawl_limit:
                        break

                total_count = int((data.get("page") or {}).get("count") or 0)
                if matched_count >= task.request.max_videos or len(records) >= crawl_limit or len(records) >= total_count or len(raw_videos) < page_size:
                    break
                page += 1
            await self._enrich_bili_records_with_view_info(client, records, concurrency=4)
        return records

    async def _enrich_bili_records_with_view_info(
        self,
        client: httpx.AsyncClient,
        records: List[Dict[str, Any]],
        *,
        concurrency: int = 4,
    ) -> None:
        if not records:
            return
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def enrich(record: Dict[str, Any]) -> None:
            async with semaphore:
                await self._enrich_bili_record_with_view_info(client, record)

        await asyncio.gather(*(enrich(record) for record in records))

    async def _enrich_bili_record_with_view_info(self, client: httpx.AsyncClient, record: Dict[str, Any]) -> None:
        aid = str(record.get("aid") or "")
        bvid = str(record.get("bvid") or "")
        if not aid and not bvid:
            return
        params = {"bvid": bvid} if bvid else {"aid": aid}
        try:
            response = await client.get("https://api.bilibili.com/x/web-interface/view", params=params)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return
        if payload.get("code") != 0:
            return
        view_data = payload.get("data")
        if isinstance(view_data, dict):
            self._merge_bili_view_data(record, view_data)

    def _merge_bili_view_data(self, record: Dict[str, Any], view_data: Dict[str, Any]) -> None:
        for key in ("aid", "bvid", "cid", "title", "desc", "pic", "pubdate", "ctime", "duration"):
            value = view_data.get(key)
            if value not in (None, ""):
                record[key] = value
        stat = view_data.get("stat") if isinstance(view_data.get("stat"), dict) else {}
        owner = view_data.get("owner") if isinstance(view_data.get("owner"), dict) else {}
        if stat:
            current_stat = record.get("stat") if isinstance(record.get("stat"), dict) else {}
            record["stat"] = {**current_stat, **stat}
            metric_aliases = {
                "view_count": "view",
                "like_count": "like",
                "coin_count": "coin",
                "favorite_count": "favorite",
                "reply_count": "reply",
                "danmaku_count": "danmaku",
                "share_count": "share",
            }
            for alias, stat_key in metric_aliases.items():
                value = stat.get(stat_key)
                if value is not None:
                    record[alias] = value
            if stat.get("view") is not None:
                record["play"] = stat.get("view")
            if stat.get("reply") is not None:
                record["comment"] = stat.get("reply")
            if stat.get("danmaku") is not None:
                record["video_review"] = stat.get("danmaku")
        if owner:
            record["creator_id"] = str(owner.get("mid") or record.get("creator_id") or "")
            record["creator_name"] = str(owner.get("name") or record.get("creator_name") or "")
            record["creator_avatar_url"] = str(owner.get("face") or record.get("creator_avatar_url") or "")

    def _bili_space_arc_item_to_record(self, raw_video: Dict[str, Any], creator_id: str) -> Dict[str, Any]:
        aid = str(raw_video.get("aid") or "")
        bvid = str(raw_video.get("bvid") or "")
        created = raw_video.get("created") or raw_video.get("pubdate")
        title = str(raw_video.get("title") or "")
        desc = str(raw_video.get("description") or raw_video.get("desc") or "")
        video_url = str(raw_video.get("arcurl") or "")
        if not video_url and bvid:
            video_url = f"https://www.bilibili.com/video/{bvid}"
        elif not video_url and aid:
            video_url = f"https://www.bilibili.com/video/av{aid}"

        return {
            **raw_video,
            "type": "video",
            "video_id": aid or bvid,
            "aid": aid,
            "bvid": bvid,
            "title": title,
            "desc": desc,
            "pubdate": created,
            "publish_time": created,
            "create_time": created,
            "url": video_url,
            "arcurl": video_url,
            "creator_id": creator_id,
            "creator_name": raw_video.get("author") or "",
            "source": "bili_space_arc_fallback",
        }

    def _pick_bili_fallback_candidate(
        self,
        task: VideoTask,
        candidates: List[CreatorCandidate],
    ) -> Optional[CreatorCandidate]:
        creator_id = str(task.request.creator_id or "").strip()
        display_name = str(task.request.creator_display_name or "").strip().casefold()
        for candidate in candidates:
            if str(candidate.id) == creator_id:
                return candidate
        if creator_id.isdigit():
            return None
        if display_name:
            for candidate in candidates:
                if candidate.display_name.strip().casefold() == display_name:
                    return candidate
        return candidates[0] if len(candidates) == 1 else None

    def _bili_candidate_video_records(self, candidate: CreatorCandidate) -> List[Dict[str, Any]]:
        raw_videos = candidate.raw.get("res") if isinstance(candidate.raw, dict) else []
        if not isinstance(raw_videos, list):
            return []

        records: List[Dict[str, Any]] = []
        for raw_video in raw_videos:
            if not isinstance(raw_video, dict):
                continue
            aid = raw_video.get("aid")
            bvid = str(raw_video.get("bvid") or "")
            title = str(raw_video.get("title") or "")
            desc = str(raw_video.get("desc") or "")
            arcurl = str(raw_video.get("arcurl") or "")
            if not arcurl and bvid:
                arcurl = f"https://www.bilibili.com/video/{bvid}"
            records.append(
                {
                    **raw_video,
                    "type": "video",
                    "video_id": str(aid or bvid),
                    "aid": str(aid or ""),
                    "bvid": bvid,
                    "title": title,
                    "desc": desc,
                    "pubdate": raw_video.get("pubdate"),
                    "publish_time": raw_video.get("pubdate"),
                    "url": arcurl,
                    "arcurl": arcurl,
                    "creator_id": candidate.id,
                    "creator_name": candidate.display_name,
                    "source": "bili_user_search_fallback",
                }
            )
        return records

    def _save_fallback_records(self, task: VideoTask, records: List[Dict[str, Any]]) -> None:
        fallback_path = task.raw_data_dir / "bili_fallback_contents.json"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with fallback_path.open("w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    async def _collect_video_items(
        self,
        task: VideoTask,
        records: List[Dict[str, Any]],
        *,
        apply_date_filter: bool = True,
        preserve_order: bool = False,
    ) -> List[VideoSummaryItem]:
        platform = task.request.platform.value

        items: List[VideoSummaryItem] = []
        for record in records:
            ranking_item_type = str(record.get("ranking_item_type") or "")
            is_ranking_list_item = task.request.source_mode == "ranking" and ranking_item_type in {"topic", "question"}
            if not self._record_matches_video_filters(task, record, apply_date_filter=apply_date_filter):
                continue
            published_dt = self._get_published_datetime(record)

            content_id = (
                self._first_value(record, CONTENT_ID_KEYS.get(platform, []))
                or str(record.get("ranking_item_id") or "")
                or uuid.uuid4().hex[:8]
            )
            if platform == "zhihu" and not self._first_value(record, CONTENT_ID_KEYS.get(platform, [])):
                content_id = self._regex_first(str(record.get("content_url") or ""), r"/zvideo/(\d+)") or content_id
            title = self._first_value(record, TITLE_KEYS)
            desc = self._first_value(record, DESC_KEYS)
            url = self._first_value(record, URL_KEYS)
            cover = self._first_url_value(record, COVER_KEYS)
            if cover:
                if not record.get("cover"):
                    record["cover"] = cover
                if not record.get("video_cover_url"):
                    record["video_cover_url"] = cover

            item = VideoSummaryItem(
                id=str(content_id),
                title=str(title or ""),
                desc=str(desc or ""),
                url=str(url or ""),
                published_at=published_dt.isoformat() if published_dt else None,
                download_status="unsupported" if is_ranking_list_item else "missing",
                error=str(record.get("detail_note") or "") if is_ranking_list_item else "",
                raw=record,
            )
            duration_seconds = self._item_duration_seconds(item)
            if duration_seconds and not self._parse_duration_value(item.raw.get("duration_seconds"), "duration_seconds"):
                item.raw["duration_seconds"] = round(duration_seconds, 3)
            items.append(item)

            if len(items) >= task.request.max_videos:
                break

        if not preserve_order:
            items.sort(key=lambda item: item.published_at or "", reverse=True)
        return items

    def _record_matches_video_filters(
        self,
        task: VideoTask,
        record: Dict[str, Any],
        *,
        apply_date_filter: bool = True,
    ) -> bool:
        platform = task.request.platform.value
        ranking_item_type = str(record.get("ranking_item_type") or "")
        is_ranking_list_item = task.request.source_mode == "ranking" and ranking_item_type in {"topic", "question"}
        if not self._is_video_record(platform, record) and not is_ranking_list_item:
            return False
        if apply_date_filter:
            published_dt = self._get_published_datetime(record)
            if not published_dt:
                return False
            start_dt = datetime.combine(task.request.start_date, time.min, tzinfo=LOCAL_TZ)
            end_dt = datetime.combine(task.request.end_date, time.max, tzinfo=LOCAL_TZ)
            if not (start_dt <= published_dt <= end_dt):
                return False
        return True

    def _should_defer_download_until_summary(self, task: VideoTask) -> bool:
        return bool(task.request.summarize)

    async def _prepare_video_files(self, task: VideoTask, items: List[VideoSummaryItem]) -> None:
        for index, item in enumerate(items, start=1):
            self._check_cancelled(task)
            task.progress_message = f"Downloading matched video {index}/{len(items)}"
            await self._attach_or_download_video(task, item, item.raw)
            task.items = items
            self._save_task_state(task, force=True)

        native_items = [
            item
            for item in items
            if not item.video_path
            and item.download_status == "missing"
            and task.request.platform.value in NATIVE_DETAIL_DOWNLOAD_PLATFORMS
        ]
        if not native_items:
            return

        specified_ids = [identifier for item in native_items if (identifier := self._detail_identifier_for_item(task.request.platform.value, item))]
        if not specified_ids:
            task.add_log("No detail identifiers available for native video download")
            return

        task.progress_message = f"Downloading {len(specified_ids)} matched videos via detail mode"
        self._set_download_progress(
            task,
            status="downloading",
            platform=task.request.platform.value,
            item_id=native_items[0].id if native_items else "",
            message="Native MediaCrawler detail download is running",
        )
        exit_code = await self._run_crawler(
            task,
            self._build_detail_download_command(task, specified_ids),
            "Matched video download command",
        )
        if exit_code != 0:
            task.add_log(f"Matched video download crawler exited with code {exit_code}; continuing with available files")

        detail_records = self._load_content_records(task.raw_data_dir)
        for item in native_items:
            existing = self._find_existing_video_file(task.raw_data_dir, task.request.platform.value, item.id)
            if existing:
                self._set_item_video_file_metadata(item, existing)
                item.video_path = str(existing)
                item.download_status = "downloaded"
                item.error = ""
            else:
                detail_record = self._find_matching_content_record(task.request.platform.value, item, detail_records)
                if detail_record:
                    self._merge_content_record_into_item(item, detail_record)
                    direct_urls = self._extract_direct_video_urls(task.request.platform.value, item.raw)
                    if direct_urls:
                        downloaded = await self._download_direct_video(
                            task,
                            item.id,
                            task.request.platform.value,
                            direct_urls,
                            referer=item.url or str(detail_record.get("video_url") or ""),
                        )
                        if downloaded:
                            self._set_item_video_file_metadata(item, downloaded)
                            item.video_path = str(downloaded)
                            item.download_status = "downloaded"
                            item.error = ""
                            continue
                        item.download_status = "failed"
                        item.error = "Detail API returned a direct video URL, but the download failed."
                        continue
                item.download_status = "failed"
                item.error = self._native_download_missing_message(task.request.platform.value, item)

        if any(item.video_path for item in native_items):
            self._set_download_progress(task, status="completed", message="Native MediaCrawler detail download completed")
        elif native_items:
            detail_message = native_items[0].error or "Native MediaCrawler detail download did not produce a local video file"
            self._set_download_progress(task, status="failed", message=detail_message)

    async def _ensure_item_video_prepared(self, task: VideoTask, item: VideoSummaryItem) -> None:
        if item.video_path:
            existing_path = Path(item.video_path)
            if existing_path.exists() and self._local_file_has_video_stream(existing_path):
                return
            item.video_path = None
            item.download_status = "failed"
            item.error = "本地媒体文件不是有效视频：未检测到视频流。"
        await self._prepare_video_files(task, [item])

    async def _attach_or_download_video(self, task: VideoTask, item: VideoSummaryItem, record: Dict[str, Any]) -> None:
        platform = task.request.platform.value
        if item.video_path:
            existing_path = Path(item.video_path)
            if existing_path.exists() and existing_path.stat().st_size > 0:
                if self._local_file_has_video_stream(existing_path):
                    if item.download_status == "missing":
                        item.download_status = "existing"
                    return
                invalid_path = self._quarantine_invalid_video_file(existing_path)
                item.video_path = None
                item.download_status = "failed"
                item.error = "本地媒体文件不是有效视频：未检测到视频流。"
                task.add_log(f"Existing media for {item.id} has no video stream; moved to {invalid_path}")

        if platform == "dy" and self._is_douyin_non_video_record(record):
            item.download_status = "unsupported"
            item.error = "该抖音记录是图文/音频素材，不是可分析的视频。"
            task.add_log(f"Download unsupported for Douyin non-video record {item.id}: {item.error}")
            return

        if record.get("ranking_item_type") in {"topic", "question"}:
            item.download_status = "unsupported"
            item.error = str(record.get("detail_note") or "该榜单项不是视频文件，请先用它作为关键词检索视频。")
            task.add_log(f"Download unsupported for ranking item {item.id}: {item.error}")
            return

        existing = self._find_existing_video_file(task.raw_data_dir, platform, item.id)
        if existing:
            self._set_item_video_file_metadata(item, existing)
            item.video_path = str(existing)
            item.download_status = "existing"
            return

        if platform == "bili":
            step_id = f"download:{item.id}"
            self._start_step(task, step_id, f"下载视频 {item.id}", phase="download", item_id=item.id)
            try:
                downloaded = await self._download_bili_public_video(task, item)
                if downloaded:
                    self._set_item_video_file_metadata(item, downloaded)
                    item.video_path = str(downloaded)
                    item.download_status = "downloaded"
                    item.error = ""
                    self._finish_step(task, step_id)
                    return
                item.download_status = "missing"
                item.error = ""
                self._finish_step(task, step_id, status="skipped", message="Public direct download did not complete; falling back to native detail download")
                task.add_log(f"Bili public direct download did not complete for {item.id}; falling back to native detail download")
                return
            except Exception as exc:
                self._finish_step(task, step_id, status="failed", message=f"{type(exc).__name__}: {exc}")
                raise

        direct_urls = self._extract_direct_video_urls(platform, record)
        if direct_urls:
            step_id = f"download:{item.id}"
            self._start_step(task, step_id, f"下载视频 {item.id}", phase="download", item_id=item.id)
            try:
                downloaded = await self._download_direct_video(task, item.id, platform, direct_urls, referer=item.url)
                if downloaded:
                    self._set_item_video_file_metadata(item, downloaded)
                    item.video_path = str(downloaded)
                    item.download_status = "downloaded"
                    item.error = ""
                    self._finish_step(task, step_id)
                    return
                item.download_status = "failed"
                item.error = "Direct video URL was present, but download failed."
                self._finish_step(task, step_id, status="failed", message=item.error)
                return
            except Exception as exc:
                self._finish_step(task, step_id, status="failed", message=f"{type(exc).__name__}: {exc}")
                raise

        if platform not in NATIVE_DOWNLOAD_PLATFORMS:
            item.download_status = "unsupported"
            if record.get("detail_status") == "photo_id_only":
                item.error = (
                    f"{PLATFORM_LABELS.get(platform, platform)} 榜单只返回 photoId/封面；"
                    "当前可验证详情接口没有稳定返回公开视频直链。"
                )
            else:
                item.error = f"{PLATFORM_LABELS.get(platform, platform)} 在当前仓库里没有稳定的公开视频直链下载链路。"
            task.add_log(f"Download unsupported for {platform} video {item.id}: {item.error}")
        else:
            item.download_status = "missing"
            item.error = "爬虫没有为这条记录保存本地视频文件。"

    def _native_download_missing_message(self, platform: str, item: VideoSummaryItem) -> str:
        if platform == "xhs" and item.raw.get("type") == "video" and not str(item.raw.get("video_url") or "").strip():
            return (
                "小红书详情 API 与 HTML 详情均未返回可下载视频流地址；"
                "当前只能确认这是视频笔记，无法真实下载 mp4。请重新扫码/更新 cookie 后再试，"
                "或换一条详情页能暴露视频流的笔记。"
            )
        if platform == "dy" and self._is_douyin_non_video_record(item.raw):
            return "该抖音记录是图文/音频素材，不是可分析的视频。"
        return item.error or "匹配后视频下载未生成本地文件。"

    def _set_item_video_file_metadata(self, item: VideoSummaryItem, video_path: Path) -> None:
        try:
            size_bytes = video_path.stat().st_size
        except OSError:
            return
        if size_bytes > 0:
            item.raw["video_size_bytes"] = size_bytes
            item.raw["video_size_mb"] = round(size_bytes / (1024 * 1024), 2)
        if not self._item_duration_seconds(item):
            duration_seconds = self._probe_video_duration_seconds(video_path)
            if duration_seconds:
                item.raw["local_video_duration_seconds"] = round(duration_seconds, 3)

    def _detail_identifier_for_item(self, platform: str, item: VideoSummaryItem) -> str:
        if platform == "bili":
            raw_bvid = self._first_value(item.raw, ["bvid", "bv_id"])
            if raw_bvid:
                return raw_bvid
            for value in (item.url, str(item.raw.get("video_url") or ""), str(item.raw.get("url") or "")):
                bvid = self._regex_first(value, r"(BV[a-zA-Z0-9]+)")
                if bvid:
                    return bvid
                aid = self._regex_first(value, r"av(\d+)")
                if aid:
                    return f"av{aid}"
            if item.id.isdigit():
                return f"av{item.id}"
        return item.url or item.id

    def _find_existing_video_file(self, raw_data_dir: Path, platform: str, content_id: str) -> Optional[Path]:
        store_name = PLATFORM_STORE_NAMES.get(platform, platform)
        videos_root = raw_data_dir / store_name / "videos"
        if not videos_root.exists():
            return None

        direct_dir = videos_root / str(content_id)
        if direct_dir.exists():
            direct_match = self._first_video_file(direct_dir.rglob("*"))
            if direct_match:
                return direct_match

        for file_path in videos_root.rglob("*"):
            if not self._looks_like_local_video(file_path):
                continue
            if str(content_id) in str(file_path):
                return file_path
        return None

    def _first_video_file(self, paths: Iterable[Path]) -> Optional[Path]:
        for path in paths:
            if self._looks_like_local_video(path) and self._local_file_has_video_stream(path):
                return path
        return None

    def _looks_like_local_video(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if path.stat().st_size <= 0:
            return False
        return path.suffix.lower() in VIDEO_EXTENSIONS or path.name.lower() in {"mp4", "video"}

    def _local_file_has_video_stream(self, path: Path) -> bool:
        if not self._looks_like_local_video(path):
            return False
        streams = self._probe_media_streams(path)
        if streams is None:
            return True
        return any(stream.get("codec_type") == "video" for stream in streams if isinstance(stream, dict))

    def _probe_media_streams(self, path: Path) -> Optional[List[Dict[str, Any]]]:
        ffprobe = self._find_ffprobe()
        if not ffprobe:
            return None
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            return []
        try:
            payload = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            return []
        streams = payload.get("streams")
        return streams if isinstance(streams, list) else []

    def _quarantine_invalid_video_file(self, path: Path) -> Path:
        target = path.with_name(f"{path.name}.invalid")
        if target.exists():
            target = path.with_name(f"{path.name}.{uuid.uuid4().hex[:8]}.invalid")
        try:
            path.replace(target)
            return target
        except OSError:
            return path

    def _extract_direct_video_urls(self, platform: str, record: Dict[str, Any]) -> List[str]:
        if platform == "dy" and self._is_douyin_non_video_record(record):
            return []
        urls: List[str] = []
        for field_name in DIRECT_VIDEO_FIELDS:
            raw_value = record.get(field_name)
            if not raw_value:
                continue
            for url in self._split_urls(raw_value):
                if not url.startswith(("http://", "https://")):
                    continue
                if self._is_landing_page_url(platform, field_name, url):
                    continue
                if field_name in {"video_download_url", "video_play_url", "download_url", "play_url", "media_url"}:
                    urls.append(url)
                elif self._looks_like_remote_video_url(url):
                    urls.append(url)
        return list(dict.fromkeys(urls))

    async def _download_direct_video(
        self,
        task: VideoTask,
        content_id: str,
        platform: str,
        urls: List[str],
        referer: str = "",
    ) -> Optional[Path]:
        store_name = PLATFORM_STORE_NAMES.get(platform, platform)
        target_dir = task.raw_data_dir / store_name / "videos" / str(content_id)
        target_dir.mkdir(parents=True, exist_ok=True)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        if platform == "bili":
            headers.update(BILI_HEADERS)
            headers["Referer"] = referer or headers.get("Referer", "https://www.bilibili.com")
            headers["Sec-Fetch-Dest"] = "video"
            headers["Sec-Fetch-Mode"] = "no-cors"
            headers["Sec-Fetch-Site"] = "cross-site"
        elif platform == "ks":
            headers.update(KS_HEADERS)
            headers["Referer"] = referer or "https://www.kuaishou.com"
            headers["Sec-Fetch-Dest"] = "video"
            headers["Sec-Fetch-Mode"] = "no-cors"
            headers["Sec-Fetch-Site"] = "cross-site"
        elif referer:
            headers["Referer"] = referer
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies

        timeout = httpx.Timeout(connect=30.0, read=90.0, write=90.0, pool=30.0)
        max_attempts = 10 if platform == "bili" else 3
        reuse_part_across_urls = platform == "bili"
        if platform in {"dy", "wb", "xhs", "ks"}:
            curl_downloaded = await self._download_direct_video_with_curl(task, content_id, platform, urls, referer)
            if curl_downloaded:
                return curl_downloaded
            task.add_log(f"Curl direct downloader did not complete for {content_id}; trying Python downloader")
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers=headers,
            trust_env=platform != "bili",
        ) as client:
            for index, url in enumerate(urls):
                target_path = target_dir / ("video.mp4" if reuse_part_across_urls else ("video.mp4" if index == 0 else f"video_{index + 1}.mp4"))
                part_path = target_path.with_name(f"{target_path.name}.part")
                if target_path.exists() and target_path.stat().st_size > 0:
                    if not self._local_file_has_video_stream(target_path):
                        invalid_path = self._quarantine_invalid_video_file(target_path)
                        task.add_log(f"Existing direct media for {content_id} has no video stream; moved to {invalid_path}")
                    else:
                        self._set_download_progress(
                            task,
                            status="completed",
                            item_id=content_id,
                            platform=platform,
                            file_name=target_path.name,
                            downloaded_bytes=target_path.stat().st_size,
                            total_bytes=target_path.stat().st_size,
                            message=f"Using existing video file {target_path.name}",
                        )
                        return target_path
                for attempt in range(1, max_attempts + 1):
                    self._check_cancelled(task)
                    downloaded = part_path.stat().st_size if part_path.exists() else 0
                    request_headers: Dict[str, str] = {}
                    if downloaded > 0:
                        request_headers["Range"] = f"bytes={downloaded}-"

                    task.progress_message = f"Downloading {content_id}"
                    self._set_download_progress(
                        task,
                        status="downloading",
                        item_id=content_id,
                        platform=platform,
                        file_name=target_path.name,
                        downloaded_bytes=downloaded,
                        message=(
                            f"Starting direct video download ({attempt}/{max_attempts})"
                            if downloaded == 0
                            else f"Resuming direct video download from {downloaded} bytes ({attempt}/{max_attempts})"
                        ),
                    )

                    total_bytes: Optional[int] = None
                    try:
                        async with client.stream("GET", url, headers=request_headers) as response:
                            if response.status_code == 416 and downloaded > 0:
                                part_path.replace(target_path)
                                self._set_download_progress(
                                    task,
                                    status="completed",
                                    item_id=content_id,
                                    platform=platform,
                                    file_name=target_path.name,
                                    downloaded_bytes=target_path.stat().st_size,
                                    total_bytes=target_path.stat().st_size,
                                    message="Resumed video file is already complete",
                                )
                                task.add_log(f"Downloaded direct video to {target_path}")
                                if self._local_file_has_video_stream(target_path):
                                    return target_path
                                invalid_path = self._quarantine_invalid_video_file(target_path)
                                task.add_log(
                                    f"Resumed media for {content_id} is not a valid video stream; moved to {invalid_path}"
                                )
                                break
                            response.raise_for_status()

                            content_length = response.headers.get("content-length")
                            if content_length and content_length.isdigit():
                                total_bytes = int(content_length)
                                if response.status_code == 206:
                                    total_bytes += downloaded
                            content_range = response.headers.get("content-range", "")
                            range_match = re.search(r"/(\d+)$", content_range)
                            if range_match:
                                total_bytes = int(range_match.group(1))

                            mode = "ab" if response.status_code == 206 and downloaded > 0 else "wb"
                            if downloaded > 0 and response.status_code != 206:
                                task.add_log(f"Server ignored Range for {content_id}; restarting this direct URL")
                            if mode == "wb":
                                downloaded = 0
                            last_update_at = time_module.monotonic()
                            last_update_bytes = downloaded
                            with part_path.open(mode) as f:
                                async for chunk in response.aiter_bytes():
                                    self._check_cancelled(task)
                                    if not chunk:
                                        continue
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    now = time_module.monotonic()
                                    if now - last_update_at >= 0.5:
                                        delta_bytes = downloaded - last_update_bytes
                                        speed_bps = delta_bytes / max(now - last_update_at, 0.001)
                                        self._set_download_progress(
                                            task,
                                            status="downloading",
                                            item_id=content_id,
                                            platform=platform,
                                            file_name=target_path.name,
                                            downloaded_bytes=downloaded,
                                            total_bytes=total_bytes,
                                            speed_bps=speed_bps,
                                            message="Downloading direct video",
                                        )
                                        last_update_at = now
                                        last_update_bytes = downloaded

                        if part_path.exists() and part_path.stat().st_size > 0:
                            part_size = part_path.stat().st_size
                            if total_bytes and part_size < total_bytes:
                                raise RuntimeError(f"incomplete video download: received {part_size} bytes, expected {total_bytes}")
                            part_path.replace(target_path)
                            self._set_download_progress(
                                task,
                                status="completed",
                                item_id=content_id,
                                platform=platform,
                                file_name=target_path.name,
                                downloaded_bytes=target_path.stat().st_size,
                                total_bytes=total_bytes or target_path.stat().st_size,
                                message="Direct video download completed",
                            )
                            task.add_log(f"Downloaded direct video to {target_path}")
                            if self._local_file_has_video_stream(target_path):
                                return target_path
                            invalid_path = self._quarantine_invalid_video_file(target_path)
                            task.add_log(
                                f"Downloaded media for {content_id} is not a valid video stream; moved to {invalid_path}"
                            )
                            break

                        self._set_download_progress(
                            task,
                            status="failed",
                            item_id=content_id,
                            platform=platform,
                            file_name=target_path.name,
                            downloaded_bytes=downloaded,
                            total_bytes=total_bytes,
                            message="Direct video download produced no local file",
                        )
                    except Exception as exc:
                        self._check_cancelled(task)
                        partial_bytes = part_path.stat().st_size if part_path.exists() else 0
                        status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
                        stale_direct_url = status_code in {401, 403, 404} and partial_bytes == 0
                        self._set_download_progress(
                            task,
                            status="failed" if stale_direct_url or attempt >= max_attempts else "downloading",
                            item_id=content_id,
                            platform=platform,
                            file_name=target_path.name,
                            downloaded_bytes=partial_bytes,
                            total_bytes=total_bytes,
                            message=(
                                f"Direct URL returned HTTP {status_code}; source URL is rejected or expired"
                                if stale_direct_url
                                else f"Download interrupted; retrying with Range ({attempt}/{max_attempts})"
                            ),
                        )
                        if stale_direct_url:
                            task.add_log(
                                f"Direct video URL rejected for {content_id}: HTTP {status_code}; source URL is rejected or expired"
                            )
                            break
                        if attempt < max_attempts:
                            task.add_log(
                                f"Direct video download interrupted for {content_id}: {type(exc).__name__}; "
                                f"saved {partial_bytes} bytes, retrying with Range"
                            )
                            await asyncio.sleep(min(2 + attempt, 8))
                            continue
                        task.add_log(f"Direct video download failed after {max_attempts} attempts: {type(exc).__name__}: {exc}")
                    break
        return None

    async def _download_direct_video_with_curl(
        self,
        task: VideoTask,
        content_id: str,
        platform: str,
        urls: List[str],
        referer: str = "",
    ) -> Optional[Path]:
        curl = self._find_curl()
        if not curl:
            return None

        store_name = PLATFORM_STORE_NAMES.get(platform, platform)
        target_dir = task.raw_data_dir / store_name / "videos" / str(content_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        base_headers = self._direct_video_request_headers(task, platform, referer)

        create_kwargs: Dict[str, Any] = {}
        if os.name == "nt":
            create_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        for index, url in enumerate(urls):
            self._check_cancelled(task)
            target_path = target_dir / ("video.mp4" if index == 0 else f"video_{index + 1}.mp4")
            part_path = target_path.with_name(f"{target_path.name}.part")

            if target_path.exists() and target_path.stat().st_size > 0:
                if self._local_file_has_video_stream(target_path):
                    self._set_download_progress(
                        task,
                        status="completed",
                        item_id=content_id,
                        platform=platform,
                        file_name=target_path.name,
                        downloaded_bytes=target_path.stat().st_size,
                        total_bytes=target_path.stat().st_size,
                        message=f"Using existing video file {target_path.name}",
                    )
                    return target_path
                invalid_path = self._quarantine_invalid_video_file(target_path)
                task.add_log(f"Existing direct media for {content_id} has no video stream; moved to {invalid_path}")

            total_bytes: Optional[int] = None
            try:
                probe = await self._probe_platform_source_video_url(task, url, platform, referer)
                if probe.get("ok") and probe.get("size_mb"):
                    total_bytes = int(float(probe["size_mb"]) * 1024 * 1024)
            except Exception:
                total_bytes = None

            cmd = [
                curl,
                "--location",
                "--fail",
                "--silent",
                "--show-error",
                "--connect-timeout",
                "30",
                "--retry",
                "5",
                "--retry-all-errors",
                "--retry-delay",
                "2",
                "--continue-at",
                "-",
                "--output",
                str(part_path),
            ]
            for key, value in base_headers.items():
                if value:
                    cmd.extend(["--header", f"{key}: {value}"])
            cmd.append(url)

            task.add_log(f"Downloading direct video with curl for {content_id}")
            last_update_at = time_module.monotonic()
            last_update_bytes = part_path.stat().st_size if part_path.exists() else 0
            self._set_download_progress(
                task,
                status="downloading",
                item_id=content_id,
                platform=platform,
                file_name=target_path.name,
                downloaded_bytes=last_update_bytes,
                total_bytes=total_bytes,
                message="Starting curl direct video download",
            )

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                **create_kwargs,
            )
            try:
                while process.poll() is None:
                    self._check_cancelled(task)
                    await asyncio.sleep(0.5)
                    downloaded = part_path.stat().st_size if part_path.exists() else 0
                    now = time_module.monotonic()
                    if now - last_update_at >= 0.5:
                        delta_bytes = downloaded - last_update_bytes
                        speed_bps = delta_bytes / max(now - last_update_at, 0.001)
                        self._set_download_progress(
                            task,
                            status="downloading",
                            item_id=content_id,
                            platform=platform,
                            file_name=target_path.name,
                            downloaded_bytes=downloaded,
                            total_bytes=total_bytes,
                            speed_bps=speed_bps,
                            message="Downloading direct video with curl",
                        )
                        last_update_at = now
                        last_update_bytes = downloaded
            except asyncio.CancelledError:
                self._terminate_process_tree(process)
                raise

            stdout, stderr = process.communicate(timeout=10)
            if process.returncode != 0:
                details = (stderr or stdout or "").strip()[-800:]
                task.add_log(f"Curl direct video download failed for {content_id}: exit {process.returncode}; {details}")
                continue

            if not part_path.exists() or part_path.stat().st_size <= 0:
                task.add_log(f"Curl direct video download produced no local file for {content_id}")
                continue

            if total_bytes and part_path.stat().st_size < total_bytes:
                task.add_log(
                    f"Curl direct video download incomplete for {content_id}: "
                    f"received {part_path.stat().st_size} bytes, expected about {total_bytes}"
                )
                continue

            part_path.replace(target_path)
            self._set_download_progress(
                task,
                status="completed",
                item_id=content_id,
                platform=platform,
                file_name=target_path.name,
                downloaded_bytes=target_path.stat().st_size,
                total_bytes=total_bytes or target_path.stat().st_size,
                message="Curl direct video download completed",
            )
            task.add_log(f"Downloaded direct video to {target_path}")
            if self._local_file_has_video_stream(target_path):
                return target_path
            invalid_path = self._quarantine_invalid_video_file(target_path)
            task.add_log(f"Downloaded media for {content_id} is not a valid video stream; moved to {invalid_path}")

        return None

    def _find_curl(self) -> Optional[str]:
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if curl:
            return curl
        if os.name != "nt":
            return None
        system_root = os.environ.get("SystemRoot") or r"C:\Windows"
        candidate = Path(system_root) / "System32" / "curl.exe"
        return str(candidate) if candidate.exists() else None

    async def _fetch_bili_public_video_urls(self, task: VideoTask, item: VideoSummaryItem) -> Tuple[List[str], str]:
        bvid = self._bili_bvid_from_item(item)
        aid = self._bili_aid_from_item(item)
        if not bvid and not aid:
            return [], ""

        headers = dict(BILI_HEADERS)
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies
        async with httpx.AsyncClient(timeout=60.0, headers=headers, follow_redirects=True, trust_env=False) as client:
            view_params = {"bvid": bvid} if bvid else {"aid": aid}
            view_response = await client.get("https://api.bilibili.com/x/web-interface/view", params=view_params)
            view_response.raise_for_status()
            view_payload = view_response.json()
            if view_payload.get("code") != 0:
                task.add_log(f"Bili public view API failed for {item.id}: {view_payload.get('message')}")
                return [], ""

            view_data = view_payload.get("data") or {}
            cid = str(view_data.get("cid") or "")
            aid = str(view_data.get("aid") or aid or "")
            bvid = str(view_data.get("bvid") or bvid or "")
            if not cid:
                return [], ""

            if isinstance(view_data, dict):
                self._merge_bili_view_data(item.raw, view_data)
            item.raw["cid"] = cid
            item.raw["aid"] = aid
            item.raw["bvid"] = bvid

            play_params: Dict[str, Any] = {
                "cid": cid,
                "qn": 16,
                "fnval": 0,
                "fourk": 0,
            }
            if bvid:
                play_params["bvid"] = bvid
            elif aid:
                play_params["aid"] = aid

            play_response = await client.get("https://api.bilibili.com/x/player/playurl", params=play_params)
            play_response.raise_for_status()
            play_payload = play_response.json()
            if play_payload.get("code") != 0:
                task.add_log(f"Bili public playurl API failed for {item.id}: {play_payload.get('message')}")
                return [], ""

            durl_value = (play_payload.get("data") or {}).get("durl")
            urls = self._bili_playurl_candidates(durl_value)
            if not urls:
                return [], ""
            item.raw["video_play_url"] = urls[0]
            video_size_bytes = self._bili_playurl_primary_size_bytes(durl_value)
            if video_size_bytes:
                item.raw["video_size_bytes"] = video_size_bytes
                item.raw["video_size_mb"] = round(video_size_bytes / (1024 * 1024), 2)
            referer = item.url or (f"https://www.bilibili.com/video/{bvid}" if bvid else "https://www.bilibili.com")
            return urls, referer

    async def _download_bili_public_video(self, task: VideoTask, item: VideoSummaryItem) -> Optional[Path]:
        last_error = ""
        for refresh_attempt in range(1, 4):
            try:
                urls, referer = await self._fetch_bili_public_video_urls(task, item)
                if not urls:
                    return None
                if refresh_attempt > 1:
                    task.add_log(f"Refreshed Bili playurl for {item.id} (attempt {refresh_attempt}/3)")
                task.add_log(f"Downloading Bili public low-quality video for {item.id}")
                downloaded = await self._download_direct_video(task, item.id, "bili", urls, referer=referer)
                if downloaded:
                    return downloaded
                last_error = "direct downloader returned no file"
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                task.add_log(f"Bili public video download failed for {item.id}: {last_error}")
            if refresh_attempt < 3:
                task.add_log(f"Re-resolving Bili playurl for {item.id} after failed download")
                await asyncio.sleep(1.5 * refresh_attempt)
        if last_error:
            task.add_log(f"Bili public video download exhausted refreshed playurls for {item.id}: {last_error}")
        return None

    def _bili_playurl_candidates(self, durl_value: Any) -> List[str]:
        if not isinstance(durl_value, list):
            return []
        urls: List[str] = []
        for item in sorted(
            (value for value in durl_value if isinstance(value, dict)),
            key=lambda value: int(value.get("size") or 0),
        ):
            url = str(item.get("url") or "")
            if url:
                urls.append(url)
            backup_urls = item.get("backup_url")
            if isinstance(backup_urls, list):
                urls.extend(str(backup_url) for backup_url in backup_urls if backup_url)
        return list(dict.fromkeys(urls))

    def _bili_playurl_primary_size_bytes(self, durl_value: Any) -> Optional[int]:
        if not isinstance(durl_value, list):
            return None
        sizes = [
            int(value.get("size") or 0)
            for value in durl_value
            if isinstance(value, dict) and int(value.get("size") or 0) > 0
        ]
        return min(sizes) if sizes else None

    async def _summarize_items(self, task: VideoTask, items: List[VideoSummaryItem]) -> None:
        if not task.request.summarize:
            for item in items:
                item.summary_status = "skipped"
                item.error = item.error or "本次任务未开启 Qwen 总结。"
            return

        settings = self._runtime_qwen_settings(task)
        api_provider = str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"]))
        video_input_mode = str(settings.get("video_input_mode", DEFAULT_QWEN_SETTINGS["video_input_mode"]))
        qwen_label = self._qwen_runtime_label(settings)
        whisper_label = self._whisper_config_label(task)
        task.add_log(f"Video analysis runtime: {qwen_label}; {whisper_label}")
        if api_provider != "ollama" and not settings.get("api_key"):
            for item in items:
                item.summary_status = "skipped"
                item.error = item.error or "尚未配置 Qwen API Key。"
            task.add_log("Qwen API key is not configured; skipped summaries")
            return

        for index, item in enumerate(items, start=1):
            self._check_cancelled(task)
            if item.summary_status == "completed" and item.summary:
                task.add_log(f"Skipping already summarized video {item.id}")
                continue
            task.progress_message = f"Summarizing video {index}/{len(items)} with {qwen_label}"
            try:
                context_sources = await self._collect_text_sources(task, item)
                if not item.video_path and video_input_mode in {"auto", "video"}:
                    try:
                        source_summary = await self._try_source_url_video_summary(task, settings, item, context_sources)
                        if source_summary:
                            item.summary = source_summary
                            item.summary_status = "completed"
                            item.analysis_mode = "source_url_video"
                            item.download_status = "skipped"
                            item.error = ""
                            task.add_log(f"Summarized video {item.id} with source URL input")
                            continue
                    except Exception as exc:
                        task.add_log(f"Source URL direct Qwen input failed for {item.id}: {type(exc).__name__}: {exc}")

                if not item.video_path and video_input_mode in {"auto", "video"}:
                    try:
                        remote_oss_summary = await self._try_remote_oss_video_summary(task, settings, item, context_sources)
                        if remote_oss_summary:
                            item.summary = remote_oss_summary
                            item.summary_status = "completed"
                            item.analysis_mode = "remote_oss_video"
                            item.download_status = "skipped"
                            item.error = ""
                            task.add_log(f"Summarized video {item.id} with remote stream OSS input")
                            continue
                    except Exception as exc:
                        task.add_log(f"Remote stream OSS Qwen input failed for {item.id}: {type(exc).__name__}: {exc}")

                if self._has_substantial_text_source(context_sources) and not item.video_path and video_input_mode in {"auto", "text_first"}:
                    await self._summarize_from_text_sources(task, settings, item, context_sources)
                    continue

                if self._should_try_whisper_transcription(task, context_sources):
                    try:
                        transcript = await self._try_whisper_transcription(task, item)
                        if transcript:
                            context_sources.append(("Whisper 转录", transcript))
                    except Exception as exc:
                        task.add_log(f"Whisper context extraction failed for {item.id}: {type(exc).__name__}: {exc}")

                context_sources = self._dedupe_text_sources(context_sources)
                if context_sources:
                    task.add_log(f"Using text context for visual analysis of {item.id}: {', '.join(label for label, _ in context_sources)}")

                if not item.video_path:
                    if self._has_substantial_text_source(context_sources) and video_input_mode in {"auto", "text_first"}:
                        await self._summarize_from_text_sources(task, settings, item, context_sources)
                        continue
                    await self._ensure_item_video_prepared(task, item)

                if not item.video_path:
                    item.summary_status = "skipped"
                    item.error = item.error or "没有可供 Qwen-VL 抽帧分析的本地视频文件。"
                    continue

                video_path = Path(item.video_path)
                if not self._local_file_has_video_stream(video_path):
                    item.video_path = None
                    item.download_status = "failed"
                    item.summary_status = "failed"
                    item.error = "本地媒体文件不是有效视频：未检测到视频流。"
                    task.add_log(f"Skipping video analysis for {item.id}: local media has no video stream")
                    continue
                task.progress_message = f"Analyzing video {index}/{len(items)} with {qwen_label}"
                if video_input_mode != "frames":
                    try:
                        item.summary, item.analysis_mode = await self._call_qwen_direct_video_summary(task, settings, item, video_path, context_sources)
                        item.summary_status = "completed"
                        task.add_log(f"Summarized video {item.id} with {item.analysis_mode} input")
                        continue
                    except Exception as exc:
                        task.add_log(
                            f"Direct video input failed for {item.id} using {qwen_label}; falling back to frames: {type(exc).__name__}: {exc}"
                        )

                frames = await asyncio.to_thread(
                    self._sample_video_frames,
                    video_path,
                    int(settings.get("sample_frames", 8)),
                )
                if not frames:
                    if self._has_substantial_text_source(context_sources):
                        await self._summarize_from_text_sources(task, settings, item, context_sources)
                    else:
                        item.summary_status = "failed"
                        item.error = "无法从本地视频文件抽取画面。"
                    continue

                task.progress_message = f"Analyzing sampled frames {index}/{len(items)} with {qwen_label}"
                frame_step_id = f"qwen_frames:{item.id}"
                self._start_step(task, frame_step_id, f"Qwen sampled-frame analysis {item.id}", phase="qwen", item_id=item.id, message=qwen_label)
                try:
                    item.summary = await self._call_qwen_frame_summary(settings, item, frames, context_sources)
                    self._finish_step(task, frame_step_id)
                except Exception as exc:
                    self._finish_step(task, frame_step_id, status="failed", message=f"{qwen_label}; {type(exc).__name__}: {exc}")
                    if self._has_substantial_text_source(context_sources):
                        task.add_log(
                            f"Sampled-frame analysis failed for {item.id}; "
                            f"using available text context instead: {type(exc).__name__}: {exc}"
                        )
                        await self._summarize_from_text_sources(task, settings, item, context_sources)
                        continue
                    raise
                item.summary_status = "completed"
                item.analysis_mode = "frames"
                task.add_log(f"Summarized video {item.id}")
            except Exception as exc:
                item.summary_status = "failed"
                item.error = f"{type(exc).__name__}: {exc}"
                task.add_log(f"Qwen summary failed for {item.id}: {item.error}")
            finally:
                task.items = items
                self._save_task_state(task, force=True)

    async def _try_text_first_summary(self, task: VideoTask, settings: Dict[str, Any], item: VideoSummaryItem) -> bool:
        sources = await self._collect_text_sources(task, item)
        if self._should_try_whisper_transcription(task, sources):
            try:
                transcript = await self._try_whisper_transcription(task, item)
                if transcript:
                    sources.append(("Whisper 转录", transcript))
            except Exception as exc:
                task.add_log(f"Whisper transcription failed for {item.id}: {type(exc).__name__}: {exc}")

        sources = self._dedupe_text_sources(sources)
        if not sources:
            return False
        if self._only_short_metadata_sources(sources):
            task.add_log(f"Only title/short description available for {item.id}; falling back to video analysis")
            return False

        prompt = self._text_first_prompt(
            item,
            sources,
            max_chars=self._ollama_runtime_profile(settings)["text_context_chars"] if self._is_ollama_provider(settings) else 12000,
        )
        qwen_label = self._qwen_runtime_label(settings)
        step_id = f"qwen_text_first:{item.id}"
        task.progress_message = f"Summarizing text-first context for {item.id} with {qwen_label}"
        self._start_step(task, step_id, f"Qwen text-first analysis {item.id}", phase="qwen", item_id=item.id, message=qwen_label)
        try:
            item.summary = await self._call_qwen_text(settings, prompt)
            self._finish_step(task, step_id)
        except Exception as exc:
            self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; {type(exc).__name__}: {exc}")
            raise
        item.summary_status = "completed"
        item.analysis_mode = "whisper_text" if any(label == "Whisper 转录" for label, _ in sources) else "text"
        if not item.video_path:
            item.download_status = "skipped"
        task.add_log(f"Summarized video {item.id} with text-first input using {qwen_label}")
        return True

    async def _summarize_from_text_sources(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        sources: List[Tuple[str, str]],
    ) -> None:
        sources = self._dedupe_text_sources(sources)
        if not sources:
            raise RuntimeError("No text sources available for text-first summary")
        if self._only_short_metadata_sources(sources):
            raise RuntimeError("Only title/short description available; refusing text-only summary")

        qwen_label = self._qwen_runtime_label(settings)
        task.progress_message = f"Summarizing text context for {item.id} with {qwen_label}"
        prompt = self._text_first_prompt(
            item,
            sources,
            max_chars=self._ollama_runtime_profile(settings)["text_context_chars"] if self._is_ollama_provider(settings) else 12000,
        )
        step_id = f"qwen_text:{item.id}"
        self._start_step(task, step_id, f"Qwen text-context analysis {item.id}", phase="qwen", item_id=item.id, message=qwen_label)
        try:
            item.summary = await self._call_qwen_text(settings, prompt)
            self._finish_step(task, step_id)
        except Exception as exc:
            self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; {type(exc).__name__}: {exc}")
            raise
        item.summary_status = "completed"
        item.analysis_mode = "whisper_text" if any(label == "Whisper 转录" for label, _ in sources) else "text"
        if not item.video_path:
            item.download_status = "skipped"
        task.add_log(f"Summarized video {item.id} with text-first input using {qwen_label}")

    async def _collect_text_sources(self, task: VideoTask, item: VideoSummaryItem) -> List[Tuple[str, str]]:
        sources: List[Tuple[str, str]] = []
        if task.request.platform.value == "bili":
            sources.extend(await self._fetch_bili_text_sources(task, item))

        for field_name in TEXT_SOURCE_FIELDS:
            value = item.raw.get(field_name)
            text = self._normalize_text_value(value)
            if text:
                sources.append((self._text_source_label(field_name), text))

        if item.title:
            sources.append(("标题", item.title))
        if item.desc and item.desc != item.title:
            sources.append(("描述", item.desc))

        return self._dedupe_text_sources(sources)

    async def _collect_vision_context_sources(self, task: VideoTask, item: VideoSummaryItem) -> List[Tuple[str, str]]:
        try:
            sources = await self._collect_text_sources(task, item)
            if self._should_try_whisper_transcription(task, sources) and item.video_path:
                try:
                    transcript = await self._try_whisper_transcription(task, item)
                    if transcript:
                        sources.append(("Whisper 转录", transcript))
                except Exception as exc:
                    task.add_log(f"Whisper context extraction failed for {item.id}: {type(exc).__name__}: {exc}")
            sources = self._dedupe_text_sources(sources)
            if sources:
                task.add_log(f"Using text context for visual analysis of {item.id}: {', '.join(label for label, _ in sources)}")
            return sources
        except Exception as exc:
            task.add_log(f"Text context collection failed for {item.id}: {type(exc).__name__}: {exc}")
            return []

    def _should_try_whisper_transcription(self, task: VideoTask, sources: List[Tuple[str, str]]) -> bool:
        if not task.request.enable_whisper_transcription:
            return False
        return not self._has_substantial_text_source(sources)

    def _has_substantial_text_source(self, sources: List[Tuple[str, str]]) -> bool:
        for label, text in self._dedupe_text_sources(sources):
            compact_length = len(re.sub(r"\s+", "", text))
            if label in STRONG_TEXT_SOURCE_LABELS and compact_length >= 20:
                return True
            if label == "描述" and compact_length >= 160:
                return True
            if label not in SHORT_METADATA_LABELS and compact_length >= 300:
                return True
        return False

    def _only_short_metadata_sources(self, sources: List[Tuple[str, str]]) -> bool:
        if not sources or self._has_substantial_text_source(sources):
            return False
        return all(label in SHORT_METADATA_LABELS for label, _ in sources)

    async def _try_whisper_transcription(self, task: VideoTask, item: VideoSummaryItem) -> str:
        self._check_cancelled(task)
        if not item.video_path:
            task.add_log(f"No substantial text source for {item.id}; preparing video for Whisper transcription")
            await self._ensure_item_video_prepared(task, item)
        if not item.video_path:
            task.add_log(f"Whisper transcription skipped for {item.id}: no local video file available")
            return ""

        video_path = Path(item.video_path)
        if not video_path.exists():
            task.add_log(f"Whisper transcription skipped for {item.id}: video file no longer exists")
            return ""

        task.progress_message = f"Extracting audio for {item.id}"
        extract_step_id = f"whisper_audio:{item.id}"
        self._start_step(
            task,
            extract_step_id,
            f"提取音频 {item.id}",
            phase="transcribe",
            item_id=item.id,
            message=f"for {self._whisper_config_label(task)}",
        )
        try:
            audio_path = await asyncio.to_thread(self._extract_audio_for_whisper, task, item, video_path)
            self._finish_step(task, extract_step_id)
        except Exception as exc:
            self._finish_step(task, extract_step_id, status="failed", message=f"{type(exc).__name__}: {exc}")
            raise
        self._check_cancelled(task)
        device, use_fp16 = self._torch_whisper_runtime()
        whisper_runtime = self._whisper_runtime_label(task, device, use_fp16)
        task.progress_message = f"Transcribing audio for {item.id} with {whisper_runtime}"
        task.add_log(f"Whisper transcription runtime for {item.id}: {whisper_runtime}")
        transcribe_step_id = f"whisper_transcribe:{item.id}"
        self._start_step(task, transcribe_step_id, f"Whisper 转录 {item.id}", phase="transcribe", item_id=item.id, message=whisper_runtime)
        try:
            transcript = await asyncio.to_thread(
                self._transcribe_audio_with_whisper,
                audio_path,
                task.request.whisper_model,
            )
            self._finish_step(task, transcribe_step_id)
        except Exception as exc:
            self._finish_step(task, transcribe_step_id, status="failed", message=f"{type(exc).__name__}: {exc}")
            raise
        self._check_cancelled(task)
        transcript = self._normalize_text_value(transcript)
        if transcript:
            self._write_whisper_transcript(task, item, transcript)
            item.raw["whisper_transcript"] = transcript
            task.add_log(f"Whisper transcript generated for {item.id} ({len(transcript)} chars)")
        return transcript

    def _extract_audio_for_whisper(self, task: VideoTask, item: VideoSummaryItem, video_path: Path) -> Path:
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("ffmpeg is not installed or not available in PATH")

        target_dir = task.task_dir / "audio"
        target_dir.mkdir(parents=True, exist_ok=True)
        audio_path = target_dir / f"{self._safe_item_id(item.id)}.wav"
        if audio_path.exists() and audio_path.stat().st_size > 0:
            return audio_path

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        if completed.returncode != 0 or not audio_path.exists() or audio_path.stat().st_size <= 0:
            details = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(f"ffmpeg audio extraction failed: {details}")
        return audio_path

    def _find_ffmpeg(self) -> Optional[str]:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            return ffmpeg

        if os.name != "nt":
            return None

        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                user_path, _ = winreg.QueryValueEx(key, "Path")
            ffmpeg = shutil.which("ffmpeg", path=os.path.expandvars(str(user_path)))
            if ffmpeg:
                return ffmpeg
        except OSError:
            pass

        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None

        local_app_path = Path(local_app_data)
        candidates = [
            local_app_path / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
            local_app_path / "Microsoft" / "WindowsApps" / "ffmpeg.exe",
        ]
        package_root = local_app_path / "Microsoft" / "WinGet" / "Packages"
        if package_root.exists():
            candidates.extend(package_root.glob("Gyan.FFmpeg*/*/bin/ffmpeg.exe"))

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def _transcribe_audio_with_whisper(self, audio_path: Path, model_name: str) -> str:
        model_name = self._normalize_whisper_model_name(model_name)
        return self._transcribe_with_openai_whisper(audio_path, model_name)

    def _transcribe_with_openai_whisper(self, audio_path: Path, model_name: str) -> str:
        import whisper  # type: ignore[import-not-found]

        device, use_fp16 = self._torch_whisper_runtime()
        cache_key = ("openai-whisper", model_name, device)
        model = self._whisper_model_cache.get(cache_key)
        if model is None:
            model = whisper.load_model(model_name, device=device)
            self._whisper_model_cache[cache_key] = model

        audio = self._load_whisper_wav_audio(audio_path)
        result = model.transcribe(audio, fp16=use_fp16)
        if isinstance(result, dict):
            segments = result.get("segments")
            if isinstance(segments, list):
                lines: List[str] = []
                for segment in segments:
                    if not isinstance(segment, dict):
                        continue
                    text = self._normalize_text_value(segment.get("text"))
                    if not text:
                        continue
                    start = float(segment.get("start") or 0.0)
                    end = float(segment.get("end") or start)
                    lines.append(f"[{self._format_time_range(start, end)}] {text}")
                if lines:
                    return "\n".join(lines)
            return self._normalize_text_value(result.get("text"))
        return self._normalize_text_value(result)

    def _load_whisper_wav_audio(self, audio_path: Path) -> Any:
        import numpy as np

        with wave.open(str(audio_path), "rb") as wav_file:
            channels = int(wav_file.getnchannels())
            sample_width = int(wav_file.getsampwidth())
            sample_rate = int(wav_file.getframerate())
            raw_audio = wav_file.readframes(wav_file.getnframes())

        if sample_rate != 16000:
            raise RuntimeError(f"Whisper audio must be 16kHz after extraction, got {sample_rate}Hz")
        if sample_width != 2:
            raise RuntimeError(f"Whisper audio must be 16-bit PCM after extraction, got {sample_width * 8}-bit")

        audio = np.frombuffer(raw_audio, np.int16).astype(np.float32) / 32768.0
        if channels > 1:
            audio = audio.reshape(-1, channels).mean(axis=1)
        return audio

    def _format_time_range(self, start_seconds: float, end_seconds: float) -> str:
        return f"{self._format_timestamp(start_seconds)}-{self._format_timestamp(end_seconds)}"

    def _format_timestamp(self, seconds: float) -> str:
        seconds = max(0.0, float(seconds or 0.0))
        whole = int(seconds)
        hours, remainder = divmod(whole, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _torch_whisper_runtime(self) -> Tuple[str, bool]:
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("openai-whisper requires PyTorch; please install CUDA-enabled torch first.") from exc

        if not bool(torch.cuda.is_available()):
            raise RuntimeError("PyTorch CUDA is not available; Whisper GPU transcription requires CUDA-enabled torch.")
        return "cuda", True

    def _cuda_available(self) -> bool:
        return self._torch_cuda_available()

    def _torch_cuda_available(self) -> bool:
        try:
            import torch  # type: ignore[import-not-found]

            return bool(torch.cuda.is_available())
        except Exception:
            return False

    def _normalize_whisper_model_name(self, model_name: str) -> str:
        clean = str(model_name or "").strip()
        clean = re.sub(r"[^0-9A-Za-z._/-]+", "", clean)
        return clean or DEFAULT_WHISPER_MODEL

    def _write_whisper_transcript(self, task: VideoTask, item: VideoSummaryItem, transcript: str) -> None:
        target_dir = task.task_dir / "transcripts"
        target_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = target_dir / f"{self._safe_item_id(item.id)}.txt"
        transcript_path.write_text(transcript, encoding="utf-8")

    def _safe_item_id(self, value: str) -> str:
        safe = re.sub(r"[^0-9A-Za-z._-]+", "_", str(value or "")).strip("._-")
        return safe or uuid.uuid4().hex[:8]

    async def _fetch_bili_text_sources(self, task: VideoTask, item: VideoSummaryItem) -> List[Tuple[str, str]]:
        aid = self._bili_aid_from_item(item)
        bvid = self._bili_bvid_from_item(item)
        sources: List[Tuple[str, str]] = []
        if not aid and not bvid:
            return sources

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=BILI_HEADERS, follow_redirects=True) as client:
                view_params = {"aid": aid} if aid else {"bvid": bvid}
                view_response = await client.get("https://api.bilibili.com/x/web-interface/view", params=view_params)
                view_response.raise_for_status()
                view_payload = view_response.json()
                if view_payload.get("code") != 0:
                    return sources

                view_data = view_payload.get("data") or {}
                aid = str(view_data.get("aid") or aid or "")
                bvid = str(view_data.get("bvid") or bvid or "")
                cid = str(view_data.get("cid") or "")
                owner = view_data.get("owner") if isinstance(view_data.get("owner"), dict) else {}
                mid = str(owner.get("mid") or "")

                subtitle_urls = self._bili_subtitle_urls(view_data.get("subtitle", {}).get("list", []))
                if not subtitle_urls and cid:
                    subtitle_urls = await self._fetch_bili_player_subtitle_urls(client, aid, bvid, cid)
                subtitle_text = await self._download_first_bili_subtitle(client, subtitle_urls)
                if subtitle_text:
                    sources.append(("B站字幕", subtitle_text))

                conclusion_text = await self._fetch_bili_ai_conclusion(client, aid, cid, mid)
                if conclusion_text:
                    sources.append(("B站 AI 总结", conclusion_text))
        except Exception as exc:
            task.add_log(f"Bili text source extraction failed for {item.id}: {type(exc).__name__}: {exc}")
        return sources

    async def _fetch_bili_player_subtitle_urls(
        self,
        client: httpx.AsyncClient,
        aid: str,
        bvid: str,
        cid: str,
    ) -> List[Dict[str, str]]:
        img_key, sub_key = await self._fetch_bili_wbi_keys(client)
        params: Dict[str, Any] = {"cid": cid}
        if aid:
            params["aid"] = aid
        elif bvid:
            params["bvid"] = bvid
        if img_key and sub_key:
            params = self._sign_bili_wbi(params, img_key, sub_key)
        response = await client.get("https://api.bilibili.com/x/player/wbi/v2", params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            return []
        return self._bili_subtitle_urls((payload.get("data") or {}).get("subtitle", {}).get("subtitles", []))

    async def _fetch_bili_ai_conclusion(self, client: httpx.AsyncClient, aid: str, cid: str, mid: str) -> str:
        if not aid or not cid or not mid:
            return ""
        img_key, sub_key = await self._fetch_bili_wbi_keys(client)
        params: Dict[str, Any] = {"aid": aid, "cid": cid, "up_mid": mid}
        if img_key and sub_key:
            params = self._sign_bili_wbi(params, img_key, sub_key)
        response = await client.get("https://api.bilibili.com/x/web-interface/view/conclusion/get", params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            return ""

        model_result = ((payload.get("data") or {}).get("model_result") or {})
        parts: List[str] = []
        summary = self._normalize_text_value(model_result.get("summary"))
        if summary:
            parts.append(summary)
        for section in model_result.get("outline") or []:
            if not isinstance(section, dict):
                continue
            title = self._normalize_text_value(section.get("title"))
            if title:
                parts.append(f"## {title}")
            for key_point in section.get("key_point") or []:
                content = self._normalize_text_value(key_point.get("content") if isinstance(key_point, dict) else key_point)
                if content:
                    parts.append(f"- {content}")
        return "\n".join(parts)

    async def _fetch_bili_wbi_keys(self, client: httpx.AsyncClient) -> Tuple[str, str]:
        try:
            response = await client.get("https://api.bilibili.com/x/web-interface/nav")
            response.raise_for_status()
            payload = response.json()
            wbi_img = ((payload.get("data") or {}).get("wbi_img") or {})
            img_url = str(wbi_img.get("img_url") or "")
            sub_url = str(wbi_img.get("sub_url") or "")
            img_key = img_url.rsplit("/", 1)[-1].split(".", 1)[0]
            sub_key = sub_url.rsplit("/", 1)[-1].split(".", 1)[0]
            return img_key, sub_key
        except Exception:
            return "", ""

    def _sign_bili_wbi(self, params: Dict[str, Any], img_key: str, sub_key: str) -> Dict[str, Any]:
        key_material = img_key + sub_key
        if len(key_material) <= max(BILI_WBI_MIXIN_KEY_ENC_TAB):
            return params
        mixin_key = "".join(key_material[index] for index in BILI_WBI_MIXIN_KEY_ENC_TAB)[:32]
        signed = {**params, "wts": int(datetime.now(LOCAL_TZ).timestamp())}
        sanitized = {
            key: "".join(ch for ch in str(value) if ch not in "!'()*")
            for key, value in sorted(signed.items())
        }
        query = urlencode(sanitized)
        sanitized["w_rid"] = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
        return sanitized

    def _bili_subtitle_urls(self, subtitles: Any) -> List[Dict[str, str]]:
        urls: List[Dict[str, str]] = []
        if not isinstance(subtitles, list):
            return urls
        for subtitle in subtitles:
            if not isinstance(subtitle, dict):
                continue
            subtitle_url = str(subtitle.get("subtitle_url") or "")
            if not subtitle_url:
                continue
            if subtitle_url.startswith("//"):
                subtitle_url = "https:" + subtitle_url
            urls.append({
                "url": subtitle_url,
                "lang": str(subtitle.get("lan_doc") or subtitle.get("lan") or "subtitle"),
            })
        return urls

    async def _download_first_bili_subtitle(self, client: httpx.AsyncClient, subtitles: List[Dict[str, str]]) -> str:
        ordered = sorted(subtitles, key=lambda item: 0 if "中文" in item.get("lang", "") or "zh" in item.get("lang", "").lower() else 1)
        for subtitle in ordered:
            try:
                response = await client.get(subtitle["url"])
                response.raise_for_status()
                payload = response.json()
                lines = [
                    str(line.get("content") or "").strip()
                    for line in payload.get("body", [])
                    if isinstance(line, dict) and str(line.get("content") or "").strip()
                ]
                text = "\n".join(lines)
                if text:
                    return text
            except Exception:
                continue
        return ""

    def _bili_aid_from_item(self, item: VideoSummaryItem) -> str:
        raw_aid = self._first_value(item.raw, ["aid", "video_id"])
        if raw_aid.isdigit():
            return raw_aid
        for value in (item.id, item.url, str(item.raw.get("video_url") or "")):
            aid = self._regex_first(value, r"av(\d+)")
            if aid:
                return aid
            if value.isdigit():
                return value
        return ""

    def _bili_bvid_from_item(self, item: VideoSummaryItem) -> str:
        raw_bvid = self._first_value(item.raw, ["bvid", "bv_id"])
        if raw_bvid.startswith("BV"):
            return raw_bvid
        for value in (item.url, str(item.raw.get("video_url") or ""), item.id):
            bvid = self._regex_first(value, r"(BV[a-zA-Z0-9]+)")
            if bvid:
                return bvid
        return ""

    def _normalize_text_value(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(self._normalize_text_value(item) for item in value if self._normalize_text_value(item))
        if isinstance(value, dict):
            for key in ("text", "content", "summary", "desc", "description"):
                text = self._normalize_text_value(value.get(key))
                if text:
                    return text
            return ""
        text = str(value).strip()
        text = re.sub(r"\r\n?", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    def _text_source_label(self, field_name: str) -> str:
        labels = {
            "subtitle_text": "已有字幕",
            "subtitles": "已有字幕",
            "transcript": "已有转录",
            "caption": "字幕/文案",
            "whisper_transcript": "Whisper 转录",
            "ai_summary": "平台 AI 总结",
            "summary": "已有摘要",
            "content": "正文",
            "content_text": "正文",
            "desc": "描述",
            "description": "描述",
        }
        return labels.get(field_name, field_name)

    def _dedupe_text_sources(self, sources: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        unique: List[Tuple[str, str]] = []
        seen: set[str] = set()
        for label, text in sources:
            clean = self._normalize_text_value(text)
            if not clean:
                continue
            key = re.sub(r"\s+", "", clean)[:300]
            if key in seen:
                continue
            seen.add(key)
            unique.append((label, clean[:12000]))
        return unique

    def _text_first_prompt(self, item: VideoSummaryItem, sources: List[Tuple[str, str]], max_chars: int = 12000) -> str:
        metadata = {
            "id": item.id,
            "title": item.title,
            "desc": item.desc,
            "published_at": item.published_at,
            "url": item.url,
            "text_sources": [label for label, _ in sources],
        }
        source_text = self._format_text_context_for_prompt(sources, max_chars=max_chars)
        return (
            "你是视频内容分析助手。下面不是完整视频画面，而是按优先级收集到的文本材料，"
            "可能包括字幕、平台 AI 总结、Whisper 转录、标题和描述。请只基于材料中有依据的信息写中文 Markdown 报告。"
            "固定使用这些加粗小标题：\n"
            "## **一句话概括**\n"
            "用 1 句完整的话说明视频核心内容。\n\n"
            "## **时间线摘要**\n"
            "按视频时间顺序写 6-12 个时间段，每段使用 [MM:SS-MM:SS] 或 [HH:MM:SS-HH:MM:SS]，"
            "每段 1-2 句，必须说明这个时间段具体发生了什么、人物在做什么、观点如何推进。"
            "如果文本材料已有时间戳，请保留、归并相邻片段并补充上下文；如果没有时间戳，只能按文本先后顺序概括并标注“时间未知”，不要虚构精确时间。\n\n"
            "## **主要内容**\n"
            "用 2-4 段较完整的文字描述视频结构、关键情节/观点、重要转折和结论，避免只列关键词。\n\n"
            "## **关键信息**\n"
            "用不超过 5 条要点列出人物、场景、对象、数据或明确观点。\n\n"
            "## **标题一致性**\n"
            "判断标题/描述与内容是否一致，并说明依据；材料不足时明确说可信度有限。\n\n"
            "## **检索标签**\n"
            "给出 8-12 个标签。\n\n"
            "不要编造材料中没有的信息；如果材料只有标题/描述，要明显降低判断置信度。\n\n"
            f"元信息：{json.dumps(metadata, ensure_ascii=False)}\n\n"
            f"{source_text}"
        )

    async def _build_aggregate_summary(self, task: VideoTask, items: List[VideoSummaryItem]) -> str:
        completed = [item for item in items if item.summary_status == "completed" and item.summary]
        if not items:
            return "所选创作者和时间范围内没有匹配到视频。"
        if not completed:
            return f"共匹配到 {len(items)} 条视频记录，但没有生成 Qwen-VL 总结。"

        settings = self._runtime_qwen_settings(task)
        if not self._is_ollama_provider(settings) and not settings.get("api_key"):
            return self._fallback_aggregate_summary(completed)
        model_name = str(settings.get("model") or "").lower()
        if self._is_ollama_provider(settings) and any(token in model_name for token in ("qwen3-vl", "qwen3vl")):
            task.add_log(
                "Using deterministic aggregate summary for local Qwen3-VL because this Ollama model returns "
                "thinking-only content for text-only chat on the current runtime."
            )
            return self._fallback_aggregate_summary(completed)

        summaries_text = "\n\n".join(
            f"{idx}. {item.title or item.id}\nPublished: {item.published_at}\nSummary: {item.summary}"
            for idx, item in enumerate(completed, start=1)
        )
        if self._is_ollama_provider(settings):
            max_chars = self._ollama_runtime_profile(settings)["text_context_chars"]
            if len(summaries_text) > max_chars:
                summaries_text = summaries_text[:max_chars].rstrip() + "\n[truncated for local Ollama context]"
        prompt = (
            "请基于下面这些单视频摘要，用中文输出一个信息充足、排版清楚的整体总结。"
            "必须使用 Markdown，并严格按以下结构组织；小标题必须加粗，正文尽量使用自然段，不要堆太多分点。\n\n"
            "## **共同主题**\n"
            "用 1-2 个自然段提炼 1-3 个共同主题。每个主题都要说明依据来自哪些视频内容，"
            "只写摘要中有证据的内容，不要扩展商业化模式、后续追踪点、观众运营建议或创作者画像。\n\n"
            "## **各自内容梗概**\n"
            "按视频逐条写。每条使用三级加粗小标题，例如 `### **1. 视频标题**`，然后包含："
            "`**发布时间**：...` 和 `**内容梗概**：...`。内容梗概要写成 120-240 字左右的完整段落，"
            "交代开头、中段、结尾和主要信息点。如果只有一个视频，也必须保留这一节。\n\n"
            "## **摘要**\n"
            "用 1-3 个自然段给出总体摘要，强调内容本身、共同信息和差异点；不要写成清单。\n\n"
            "## **思维导图**\n"
            "如果材料足够，请输出一个 Mermaid mindmap fenced code block，必须严格使用这个形式：\n"
            "```mermaid\n"
            "mindmap\n"
            "  root((视频内容汇总))\n"
            "    共同主题\n"
            "    各视频\n"
            "```\n"
            "在代码块内补充 2-3 层节点即可，节点文字要短。"
            "如果摘要不足以生成可靠思维导图，则只写“材料不足，无法生成可靠思维导图”。\n\n"
            f"{summaries_text}"
        )
        try:
            return await self._call_qwen_text(settings, prompt)
        except Exception as exc:
            task.add_log(f"Aggregate Qwen summary failed: {type(exc).__name__}: {exc}")
            return self._fallback_aggregate_summary(completed)

    def _runtime_qwen_settings(self, task: VideoTask) -> Dict[str, Any]:
        settings = self._load_settings(include_secret=True)
        settings.update(
            {
                "video_input_mode": task.request.video_input_mode,
                "video_upload_backend": task.request.video_upload_backend,
                "video_fps": task.request.video_fps,
                "sample_frames": task.request.sample_frames,
                "max_inline_video_mb": task.request.max_inline_video_mb,
                "max_dashscope_video_mb": task.request.max_dashscope_video_mb,
                "dashscope_retry_count": task.request.dashscope_retry_count,
                "enable_video_compression": task.request.enable_video_compression,
                "compression_target_mb": task.request.compression_target_mb,
            }
        )
        return settings

    async def _try_source_url_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        if str(settings.get("video_upload_backend", DEFAULT_QWEN_SETTINGS["video_upload_backend"])) != "auto":
            return ""
        candidates = await self._source_video_url_candidates(task, item)
        urls = [url for url, _referer in candidates]
        if not urls:
            return ""

        errors: List[str] = []
        qwen_label = self._qwen_runtime_label(settings)
        for url_index, url in enumerate(urls[:3], start=1):
            self._check_cancelled(task)
            host = urlparse(url).netloc or "unknown-host"
            step_id = f"source_url:{item.id}:{url_index}"
            self._start_step(task, step_id, f"尝试源 URL 直传 Qwen {item.id}", phase="qwen", item_id=item.id, message=f"{qwen_label}; host={host}")
            probe = await self._probe_public_source_video_url(url)
            if not probe["ok"]:
                reason = str(probe.get("reason") or "")
                if not self._source_probe_can_still_try_qwen(reason):
                    task.add_log(f"Source video URL is not publicly readable for Qwen: {host} ({reason})")
                    self._finish_step(task, step_id, status="skipped", message=reason)
                    continue
                task.add_log(f"Source URL probe inconclusive for {item.id}: {host} ({reason}); trying Qwen direct URL anyway")
            try:
                task.add_log(f"Trying Qwen source video URL input for {item.id}: {host}; {qwen_label}")
                summary = await self._call_qwen_source_url_video_summary(
                    settings,
                    item,
                    url,
                    context_sources,
                    float(probe.get("size_mb") or 0.0),
                )
                item.raw["qwen_source_video_url_host"] = host
                self._finish_step(task, step_id)
                return summary
            except Exception as exc:
                message = f"{host}: {type(exc).__name__}: {exc}"
                errors.append(message)
                self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; {message}")
                task.add_log(f"Qwen source video URL failed for {item.id} using {qwen_label}: {message}")
        if errors:
            raise RuntimeError("; ".join(errors))
        return ""

    async def _source_video_url_candidates(self, task: VideoTask, item: VideoSummaryItem) -> List[Tuple[str, str]]:
        platform = task.request.platform.value
        if platform == "bili":
            try:
                urls, referer = await self._fetch_bili_public_video_urls(task, item)
                return [(url, referer) for url in urls]
            except Exception as exc:
                task.add_log(f"Bili source URL lookup failed for {item.id}: {type(exc).__name__}: {exc}")
                return []
        return [(url, item.url) for url in self._extract_direct_video_urls(platform, item.raw)]

    async def _probe_public_source_video_url(self, url: str) -> Dict[str, Any]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Range": "bytes=0-0",
        }
        timeout = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout, trust_env=False) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code not in {200, 206}:
                        return {"ok": False, "reason": f"HTTP {response.status_code}"}
                    content_type = (response.headers.get("content-type") or "").lower()
                    if content_type and not any(token in content_type for token in ("video", "octet-stream", "mp4", "mpegurl")):
                        return {"ok": False, "reason": f"content-type {content_type}"}
                    total_bytes = self._response_total_bytes(response.headers)
                    return {
                        "ok": True,
                        "reason": "ok",
                        "size_mb": round(total_bytes / (1024 * 1024), 2) if total_bytes else 0.0,
                        "content_type": content_type,
                    }
        except Exception as exc:
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}

    def _source_probe_can_still_try_qwen(self, reason: str) -> bool:
        reason_lower = reason.lower()
        return any(
            token in reason_lower
            for token in (
                "connecterror",
                "connecttimeout",
                "readtimeout",
                "timeout",
                "remoteprotocolerror",
                "sslerror",
                "network",
            )
        )

    async def _probe_platform_source_video_url(
        self,
        task: VideoTask,
        url: str,
        platform: str,
        referer: str,
    ) -> Dict[str, Any]:
        headers = self._direct_video_request_headers(task, platform, referer)
        headers["Range"] = "bytes=0-0"
        timeout = httpx.Timeout(connect=8.0, read=12.0, write=8.0, pool=8.0)
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
                trust_env=platform != "bili",
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code not in {200, 206}:
                        return {"ok": False, "reason": f"HTTP {response.status_code}"}
                    content_type = (response.headers.get("content-type") or "").lower()
                    if content_type and not any(token in content_type for token in ("video", "octet-stream", "mp4", "mpegurl")):
                        return {"ok": False, "reason": f"content-type {content_type}"}
                    total_bytes = self._response_total_bytes(response.headers)
                    return {
                        "ok": True,
                        "reason": "ok",
                        "size_mb": round(total_bytes / (1024 * 1024), 2) if total_bytes else 0.0,
                        "content_type": content_type,
                    }
        except Exception as exc:
            return {"ok": False, "reason": f"{type(exc).__name__}: {exc}"}

    def _response_total_bytes(self, headers: httpx.Headers) -> int:
        content_range = headers.get("content-range", "")
        range_match = re.search(r"/(\d+)$", content_range)
        if range_match:
            return int(range_match.group(1))
        content_length = headers.get("content-length")
        if content_length and content_length.isdigit():
            return int(content_length)
        return 0

    async def _call_qwen_source_url_video_summary(
        self,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        source_url: str,
        context_sources: List[Tuple[str, str]],
        video_size_mb: float,
    ) -> str:
        return await self._call_qwen_video_url_summary(
            settings,
            item,
            source_url,
            context_sources,
            video_size_mb,
            {
                "source_url_host": urlparse(source_url).netloc,
                "source_url_mode": "direct_platform_url",
            },
        )

    async def _call_qwen_video_url_summary(
        self,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_url: str,
        context_sources: List[Tuple[str, str]],
        video_size_mb: float,
        metadata_extra: Dict[str, Any],
    ) -> str:
        metadata = self._video_prompt_metadata(item, video_size_mb)
        metadata.update(metadata_extra)
        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": self._direct_video_prompt(metadata, context_sources),
            },
            {
                "type": "video_url",
                "video_url": {"url": video_url},
                "fps": float(settings.get("video_fps", DEFAULT_QWEN_SETTINGS["video_fps"])),
            },
        ]
        return await self._call_qwen(settings, content)

    async def _try_remote_oss_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        if str(settings.get("video_upload_backend", DEFAULT_QWEN_SETTINGS["video_upload_backend"])) != "auto":
            return ""
        if not bool(settings.get("oss_enabled")):
            return ""
        candidates = await self._source_video_url_candidates(task, item)
        if not candidates:
            return ""

        duration_seconds = self._item_duration_seconds(item)
        duration_limit_seconds = self._public_url_video_duration_limit_seconds(settings)
        if duration_seconds and duration_limit_seconds and duration_seconds > duration_limit_seconds:
            task.add_log(
                f"Skipping remote stream OSS for {item.id}: known duration "
                f"{duration_seconds / 60:.1f}min exceeds model public URL limit "
                f"{duration_limit_seconds / 60:.1f}min"
            )
            return ""

        platform = task.request.platform.value
        errors: List[str] = []
        upload_attempts = 0
        max_upload_attempts = max(1, REMOTE_OSS_MAX_UPLOAD_ATTEMPTS_PER_ITEM)
        for url, referer in candidates[:3]:
            self._check_cancelled(task)
            host = urlparse(url).netloc or "unknown-host"
            try:
                probe = await self._probe_platform_source_video_url(task, url, platform, referer)
                if not probe["ok"]:
                    task.add_log(f"Remote stream source URL is not readable for {item.id}: {host} ({probe['reason']})")
                    continue
                size_mb = float(probe.get("size_mb") or 0.0)
                max_mb = self._public_url_video_limit_mb(settings)
                if size_mb and size_mb > max_mb:
                    task.add_log(
                        f"Skipping remote stream OSS for {item.id}: source video is {size_mb:.1f}MB, "
                        f"larger than model public URL limit {max_mb}MB"
                    )
                    return ""
                if upload_attempts >= max_upload_attempts:
                    task.add_log(
                        f"Skipping additional remote stream OSS candidates for {item.id}: "
                        f"already attempted {upload_attempts} upload(s)"
                    )
                    break
                upload_attempts += 1
                task.add_log(f"Streaming source video to OSS for {item.id}: {host}")
                public_url, object_key, size_mb = await asyncio.to_thread(
                    self._stream_remote_video_to_oss,
                    task,
                    settings,
                    item,
                    url,
                    platform,
                    referer,
                )
                metadata_extra = {
                    "oss_object": object_key,
                    "source_url_host": host,
                    "source_url_mode": "stream_to_oss",
                }
                item.raw["qwen_remote_oss_object"] = object_key
                item.raw["qwen_source_video_url_host"] = host
                qwen_step_id = f"qwen_remote_oss:{item.id}"
                self._start_step(
                    task,
                    qwen_step_id,
                    f"Qwen 读取远程转存 OSS 视频并分析 {item.id}",
                    phase="qwen",
                    item_id=item.id,
                    message=self._qwen_runtime_label(settings),
                )
                try:
                    summary = await self._call_qwen_video_url_summary(settings, item, public_url, context_sources, size_mb, metadata_extra)
                    self._finish_step(task, qwen_step_id)
                finally:
                    await self._cleanup_oss_object_after_analysis(task, settings, object_key, item.id, "remote stream OSS")
                return summary
            except Exception as exc:
                qwen_step = self._find_step(task, f"qwen_remote_oss:{item.id}")
                if qwen_step and qwen_step.status == "running":
                    self._finish_step(
                        task,
                        qwen_step.id,
                        status="failed",
                        message=f"{self._qwen_runtime_label(settings)}; {type(exc).__name__}: {exc}",
                    )
                message = f"{host}: {type(exc).__name__}: {exc}"
                errors.append(message)
                task.add_log(f"Remote stream OSS failed for {item.id} using {self._qwen_runtime_label(settings)}: {message}")
                if upload_attempts >= max_upload_attempts:
                    task.add_log(
                        f"Remote stream OSS stopped for {item.id} after {upload_attempts} upload attempt(s); "
                        "falling back to local download or frame/text analysis"
                    )
                    break
        if errors:
            raise RuntimeError("; ".join(errors))
        return ""

    def _stream_remote_video_to_oss(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        source_url: str,
        platform: str,
        referer: str,
    ) -> Tuple[str, str, float]:
        access_key_id = str(settings.get("oss_access_key_id") or "").strip()
        access_key_secret = str(settings.get("oss_access_key_secret") or "").strip()
        bucket_name = str(settings.get("oss_bucket") or "").strip()
        endpoint = self._normalize_oss_endpoint(str(settings.get("oss_endpoint") or "").strip())
        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            raise RuntimeError("OSS configuration is incomplete; access key, bucket, and endpoint are required.")

        try:
            import oss2  # type: ignore[import-not-found]
            from oss2.models import PartInfo  # type: ignore[import-not-found]
            import requests
        except ImportError as exc:
            raise RuntimeError("oss2 and requests are required for remote stream OSS upload.") from exc

        auth = oss2.Auth(access_key_id, access_key_secret)
        bucket = oss2.Bucket(auth, endpoint, bucket_name)
        object_key = self._remote_oss_object_key(task, settings, item, source_url)
        expires = int(settings.get("oss_url_expires_seconds") or DEFAULT_QWEN_SETTINGS["oss_url_expires_seconds"])
        expires = min(max(300, expires), 604800)
        request_headers = self._direct_video_request_headers(task, platform, referer)
        timeout = (20, 60)
        part_size = 16 * 1024 * 1024
        upload_id = ""
        parts: List[Any] = []
        downloaded = 0
        total_bytes = 0
        last_progress = {"percent": -10, "time": 0.0}
        last_speed = {"bytes": 0, "time": time_module.monotonic()}
        step_id = f"remote_oss_upload:{item.id}"
        self._start_step(task, step_id, f"源视频流式转存 OSS {item.id}", phase="upload", item_id=item.id, message=urlparse(source_url).netloc)

        try:
            with requests.get(source_url, headers=request_headers, stream=True, timeout=timeout, allow_redirects=True) as response:
                if response.status_code < 200 or response.status_code >= 300:
                    raise RuntimeError(f"source URL returned HTTP {response.status_code}")
                total_bytes = self._requests_total_bytes(response.headers)
                max_mb = self._public_url_video_limit_mb(settings)
                if total_bytes and total_bytes / (1024 * 1024) > max_mb:
                    raise RuntimeError(f"source video is {total_bytes / (1024 * 1024):.1f}MB, larger than public URL limit {max_mb}MB.")
                content_type = self._guess_remote_content_type(source_url, response.headers.get("content-type", ""))
                upload = bucket.init_multipart_upload(object_key, headers={"Content-Type": content_type})
                upload_id = upload.upload_id
                part_number = 1
                buffer = bytearray()
                self._update_step(task, step_id, total_bytes=total_bytes, message="Streaming source video to OSS")

                def flush_part() -> None:
                    nonlocal part_number, buffer
                    if not buffer:
                        return
                    result = bucket.upload_part(object_key, upload_id, part_number, bytes(buffer))
                    parts.append(PartInfo(part_number, result.etag, size=len(buffer)))
                    part_number += 1
                    buffer = bytearray()

                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    self._check_cancelled(task)
                    if not chunk:
                        continue
                    buffer.extend(chunk)
                    downloaded += len(chunk)
                    while len(buffer) >= part_size:
                        part_data = bytes(buffer[:part_size])
                        del buffer[:part_size]
                        result = bucket.upload_part(object_key, upload_id, part_number, part_data)
                        parts.append(PartInfo(part_number, result.etag, size=len(part_data)))
                        part_number += 1
                    now = time_module.monotonic()
                    elapsed = max(now - last_speed["time"], 0.001)
                    speed_bps = (downloaded - last_speed["bytes"]) / elapsed
                    last_speed["bytes"] = downloaded
                    last_speed["time"] = now
                    if total_bytes:
                        percent = int(downloaded * 100 / total_bytes)
                        should_log = percent >= last_progress["percent"] + 10 or now - last_progress["time"] >= 30 or downloaded >= total_bytes
                    else:
                        percent = 0
                        should_log = now - last_progress["time"] >= 30
                    if should_log:
                        last_progress["percent"] = percent
                        last_progress["time"] = now
                        total_label = f"/{total_bytes / (1024 * 1024):.1f}MB" if total_bytes else ""
                        task.add_log(
                            f"Remote stream OSS progress for {item.id}: {percent}% "
                            f"({downloaded / (1024 * 1024):.1f}{total_label})"
                        )
                    self._update_step(
                        task,
                        step_id,
                        progress_percent=percent if total_bytes else None,
                        transferred_bytes=downloaded,
                        total_bytes=total_bytes or None,
                        speed_bps=speed_bps,
                        message="Streaming source video to OSS",
                    )
                flush_part()
                if not parts:
                    raise RuntimeError("source stream produced no upload parts")
                bucket.complete_multipart_upload(object_key, upload_id, parts)
                upload_id = ""
        except Exception:
            if upload_id:
                try:
                    bucket.abort_multipart_upload(object_key, upload_id)
                    task.add_log(f"Aborted incomplete OSS multipart upload for {item.id}: {object_key}")
                except Exception as abort_exc:
                    task.add_log(f"Failed to abort OSS multipart upload for {item.id}: {type(abort_exc).__name__}: {abort_exc}")
            self._finish_step(task, step_id, status="failed")
            raise

        signed_url = bucket.sign_url("GET", object_key, expires)
        size_mb = (total_bytes or downloaded) / (1024 * 1024)
        task.add_log(f"Remote stream OSS upload completed for {item.id}: {object_key} ({size_mb:.1f}MB)")
        self._finish_step(task, step_id, message=f"{size_mb:.1f}MB")
        return signed_url, object_key, size_mb

    def _direct_video_request_headers(self, task: VideoTask, platform: str, referer: str = "") -> Dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        if platform == "bili":
            headers.update(BILI_HEADERS)
            headers["Referer"] = referer or headers.get("Referer", "https://www.bilibili.com")
            headers["Sec-Fetch-Dest"] = "video"
            headers["Sec-Fetch-Mode"] = "no-cors"
            headers["Sec-Fetch-Site"] = "cross-site"
        elif platform == "ks":
            headers.update(KS_HEADERS)
            headers["Referer"] = referer or "https://www.kuaishou.com"
            headers["Sec-Fetch-Dest"] = "video"
            headers["Sec-Fetch-Mode"] = "no-cors"
            headers["Sec-Fetch-Site"] = "cross-site"
        elif referer:
            headers["Referer"] = referer
        if task.request.cookies:
            headers["Cookie"] = task.request.cookies
        return headers

    def _requests_total_bytes(self, headers: Any) -> int:
        content_range = headers.get("content-range", "")
        range_match = re.search(r"/(\d+)$", content_range)
        if range_match:
            return int(range_match.group(1))
        content_length = headers.get("content-length")
        if content_length and str(content_length).isdigit():
            return int(content_length)
        return 0

    def _remote_oss_object_key(self, task: VideoTask, settings: Dict[str, Any], item: VideoSummaryItem, source_url: str) -> str:
        prefix = str(settings.get("oss_prefix") or DEFAULT_QWEN_SETTINGS["oss_prefix"]).strip().strip("/")
        safe_platform = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task.request.platform.value))
        safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", task.task_id)
        safe_item_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(item.id or "video"))
        suffix = Path(urlparse(source_url).path).suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            suffix = ".mp4"
        file_name = f"{safe_item_id}_remote_{uuid.uuid4().hex[:8]}{suffix}"
        return "/".join(part for part in [prefix, safe_platform, safe_task_id, safe_item_id, file_name] if part)

    def _guess_remote_content_type(self, source_url: str, content_type: str) -> str:
        clean = str(content_type or "").split(";", 1)[0].strip()
        if clean:
            return clean
        guessed = mimetypes.guess_type(urlparse(source_url).path)[0]
        return guessed or "video/mp4"

    async def _call_qwen_direct_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_path: Path,
        context_sources: List[Tuple[str, str]],
    ) -> Tuple[str, str]:
        backend = str(settings.get("video_upload_backend", DEFAULT_QWEN_SETTINGS["video_upload_backend"]))
        api_provider = str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"]))
        if api_provider == "ollama":
            raise RuntimeError("Ollama provider does not support direct video files or video URLs; sampled-frame image analysis is required.")
        errors: List[str] = []
        duration_limit_seconds = self._public_url_video_duration_limit_seconds(settings)
        duration_seconds = self._probe_video_duration_seconds(video_path) or self._item_duration_seconds(item)
        if duration_seconds and duration_limit_seconds and duration_seconds > duration_limit_seconds:
            raise RuntimeError(
                f"Video duration is {duration_seconds / 60:.1f}min, larger than model video input limit "
                f"{duration_limit_seconds / 60:.1f}min.; use frame/text analysis instead"
            )

        if backend in {"auto", "oss"}:
            try:
                summary = await self._call_qwen_oss_video_summary(task, settings, item, video_path, context_sources)
                return summary, "oss_video"
            except Exception as exc:
                message = f"OSS public URL video failed: {type(exc).__name__}: {exc}"
                errors.append(message)
                if backend == "oss":
                    raise RuntimeError(message) from exc

        if backend in {"auto", "dashscope"}:
            if api_provider != "dashscope":
                message = (
                    "DashScope SDK local video upload requires API provider 'dashscope'. "
                    f"Current provider is '{api_provider}'."
                )
                errors.append(message)
                if backend == "dashscope":
                    raise RuntimeError(message)
            else:
                try:
                    summary = await asyncio.to_thread(self._call_qwen_dashscope_video_summary, task, settings, item, video_path, context_sources)
                    return summary, "dashscope_video"
                except Exception as exc:
                    message = f"DashScope SDK local video failed: {type(exc).__name__}: {exc}"
                    errors.append(message)
                    if backend == "dashscope":
                        raise RuntimeError(message) from exc

        if backend in {"auto", "openai"}:
            try:
                summary = await self._call_qwen_base64_video_summary(task, settings, item, video_path, context_sources)
                return summary, "base64_video"
            except Exception as exc:
                message = f"OpenAI-compatible base64 video failed: {type(exc).__name__}: {exc}"
                errors.append(message)

        raise RuntimeError("; ".join(errors) or f"Unsupported video upload backend: {backend}")

    async def _call_qwen_oss_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_path: Path,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        public_url, object_key = await asyncio.to_thread(self._upload_video_to_oss, task, settings, item, video_path)
        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        metadata = self._video_prompt_metadata(item, video_size_mb)
        metadata["oss_object"] = object_key
        metadata["upload_file"] = video_path.name
        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": self._direct_video_prompt(metadata, context_sources),
            },
            {
                "type": "video_url",
                "video_url": {"url": public_url},
                "fps": float(settings.get("video_fps", DEFAULT_QWEN_SETTINGS["video_fps"])),
            },
        ]
        step_id = f"qwen_oss:{item.id}"
        self._start_step(
            task,
            step_id,
            f"Qwen 读取 OSS 视频并分析 {item.id}",
            phase="qwen",
            item_id=item.id,
            message=self._qwen_runtime_label(settings),
        )
        try:
            summary = await self._call_qwen(settings, content)
            self._finish_step(task, step_id)
            return summary
        except Exception as exc:
            self._finish_step(task, step_id, status="failed", message=f"{self._qwen_runtime_label(settings)}; {type(exc).__name__}: {exc}")
            raise
        finally:
            await self._cleanup_oss_object_after_analysis(task, settings, object_key, item.id, "local OSS upload")

    def _upload_video_to_oss(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_path: Path,
    ) -> Tuple[str, str]:
        if not bool(settings.get("oss_enabled")):
            raise RuntimeError("OSS upload is not enabled in the active Qwen profile.")
        access_key_id = str(settings.get("oss_access_key_id") or "").strip()
        access_key_secret = str(settings.get("oss_access_key_secret") or "").strip()
        bucket_name = str(settings.get("oss_bucket") or "").strip()
        endpoint = self._normalize_oss_endpoint(str(settings.get("oss_endpoint") or "").strip())
        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            raise RuntimeError("OSS configuration is incomplete; access key, bucket, and endpoint are required.")

        max_mb = self._public_url_video_limit_mb(settings)
        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        if video_size_mb > max_mb:
            raise RuntimeError(f"Video is {video_size_mb:.1f}MB, larger than public URL limit {max_mb}MB.")
        duration_limit_seconds = self._public_url_video_duration_limit_seconds(settings)
        if duration_limit_seconds:
            duration_seconds = self._probe_video_duration_seconds(video_path)
            if duration_seconds and duration_seconds > duration_limit_seconds:
                raise RuntimeError(
                    f"Video duration is {duration_seconds / 60:.1f}min, larger than model public URL limit "
                    f"{duration_limit_seconds / 60:.1f}min."
                )

        try:
            import oss2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("oss2 package is not installed; run `uv sync` after adding the OSS dependency.") from exc

        object_key = self._oss_object_key(task, settings, item, video_path)
        content_type = self._guess_video_content_type(video_path)
        expires = int(settings.get("oss_url_expires_seconds") or DEFAULT_QWEN_SETTINGS["oss_url_expires_seconds"])
        expires = min(max(300, expires), 604800)
        step_id = f"oss_upload:{item.id}"
        self._start_step(task, step_id, f"上传本地视频到 OSS {item.id}", phase="upload", item_id=item.id, message=video_path.name)

        task.add_log(
            f"Uploading video {item.id} to OSS bucket {bucket_name}: {object_key} ({video_size_mb:.1f}MB)"
        )
        old_connect_timeout = getattr(oss2.defaults, "connect_timeout", None)
        old_request_retries = getattr(oss2.defaults, "request_retries", None)
        oss_timeout = 300
        oss_retries = 5
        oss2.defaults.connect_timeout = max(int(old_connect_timeout or 0), oss_timeout)
        oss2.defaults.request_retries = max(int(old_request_retries or 0), oss_retries)
        try:
            auth = oss2.Auth(access_key_id, access_key_secret)
            bucket = oss2.Bucket(auth, endpoint, bucket_name, connect_timeout=oss_timeout)
            if video_path.stat().st_size >= OSS_MULTIPART_THRESHOLD_BYTES:
                task.task_dir.mkdir(parents=True, exist_ok=True)
                store = oss2.ResumableStore(root=str(task.task_dir / "oss_resumable"))
                last_progress = {"percent": -10, "time": 0.0}
                last_speed = {"bytes": 0, "time": time_module.monotonic()}
                task.add_log(
                    f"Using OSS resumable multipart upload for {item.id} "
                    f"(threshold {OSS_MULTIPART_THRESHOLD_BYTES / (1024 * 1024):.0f}MB)"
                )
                self._update_step(task, step_id, total_bytes=video_path.stat().st_size, message="Uploading video to OSS")

                def progress_callback(consumed_bytes: int, total_bytes: int) -> None:
                    if total_bytes <= 0:
                        return
                    percent = int(consumed_bytes * 100 / total_bytes)
                    now = time_module.monotonic()
                    elapsed = max(now - last_speed["time"], 0.001)
                    speed_bps = (consumed_bytes - last_speed["bytes"]) / elapsed
                    last_speed["bytes"] = consumed_bytes
                    last_speed["time"] = now
                    if percent >= last_progress["percent"] + 10 or now - last_progress["time"] >= 30 or consumed_bytes >= total_bytes:
                        last_progress["percent"] = percent
                        last_progress["time"] = now
                        task.add_log(
                            f"OSS upload progress for {item.id}: {percent}% "
                            f"({consumed_bytes / (1024 * 1024):.1f}/{total_bytes / (1024 * 1024):.1f}MB)"
                        )
                    self._update_step(
                        task,
                        step_id,
                        progress_percent=percent,
                        transferred_bytes=consumed_bytes,
                        total_bytes=total_bytes,
                        speed_bps=speed_bps,
                        message="Uploading video to OSS",
                    )

                upload_error: Optional[Exception] = None
                for attempt in range(1, 4):
                    self._check_cancelled(task)
                    try:
                        if attempt > 1:
                            task.add_log(f"Retrying OSS resumable upload for {item.id} ({attempt}/3)")
                        oss2.resumable_upload(
                            bucket,
                            object_key,
                            str(video_path),
                            store=store,
                            headers={"Content-Type": content_type},
                            multipart_threshold=OSS_MULTIPART_THRESHOLD_BYTES,
                            part_size=OSS_MULTIPART_PART_SIZE_BYTES,
                            num_threads=4,
                            progress_callback=progress_callback,
                        )
                        upload_error = None
                        break
                    except Exception as exc:
                        upload_error = exc
                        if attempt >= 3:
                            break
                        delay = 5 * attempt
                        task.add_log(f"OSS resumable upload failed for {item.id}: {type(exc).__name__}; retrying in {delay}s")
                        time_module.sleep(delay)
                if upload_error:
                    raise upload_error
            else:
                task.add_log(f"Using OSS single-part upload for {item.id}")
                self._update_step(task, step_id, total_bytes=video_path.stat().st_size, message="Uploading video to OSS")
                bucket.put_object_from_file(object_key, str(video_path), headers={"Content-Type": content_type})
            signed_url = bucket.sign_url("GET", object_key, expires)
            task.add_log(f"OSS upload completed for {item.id}; signed URL expires in {expires}s")
            self._update_step(
                task,
                step_id,
                progress_percent=100.0,
                transferred_bytes=video_path.stat().st_size,
                total_bytes=video_path.stat().st_size,
                message="OSS upload completed",
            )
            self._finish_step(task, step_id)
            return signed_url, object_key
        except Exception as exc:
            self._finish_step(task, step_id, status="failed", message=f"{type(exc).__name__}: {exc}")
            raise
        finally:
            if old_connect_timeout is not None:
                oss2.defaults.connect_timeout = old_connect_timeout
            if old_request_retries is not None:
                oss2.defaults.request_retries = old_request_retries

    async def _cleanup_oss_object_after_analysis(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        object_key: str,
        item_id: str,
        source_label: str,
    ) -> None:
        if not object_key or not bool(settings.get("oss_cleanup_after_analysis", DEFAULT_QWEN_SETTINGS["oss_cleanup_after_analysis"])):
            return
        try:
            await asyncio.to_thread(self._delete_oss_object, settings, object_key)
            task.add_log(f"Deleted temporary OSS object for {item_id} after {source_label}: {object_key}")
        except Exception as exc:
            task.add_log(f"Failed to delete temporary OSS object for {item_id}: {type(exc).__name__}: {exc}")

    def _delete_oss_object(self, settings: Dict[str, Any], object_key: str) -> None:
        access_key_id = str(settings.get("oss_access_key_id") or "").strip()
        access_key_secret = str(settings.get("oss_access_key_secret") or "").strip()
        bucket_name = str(settings.get("oss_bucket") or "").strip()
        endpoint = self._normalize_oss_endpoint(str(settings.get("oss_endpoint") or "").strip())
        if not all([access_key_id, access_key_secret, bucket_name, endpoint]):
            raise RuntimeError("OSS configuration is incomplete; cannot delete temporary object.")
        try:
            import oss2  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("oss2 package is not installed; cannot delete temporary OSS object.") from exc
        bucket = oss2.Bucket(oss2.Auth(access_key_id, access_key_secret), endpoint, bucket_name)
        bucket.delete_object(object_key)

    def _normalize_oss_endpoint(self, endpoint: str) -> str:
        endpoint = endpoint.strip().rstrip("/")
        if not endpoint:
            return ""
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return f"https://{endpoint}"

    def _oss_object_key(self, task: VideoTask, settings: Dict[str, Any], item: VideoSummaryItem, video_path: Path) -> str:
        prefix = str(settings.get("oss_prefix") or DEFAULT_QWEN_SETTINGS["oss_prefix"]).strip().strip("/")
        safe_platform = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(task.request.platform.value))
        safe_task_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", task.task_id)
        safe_item_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(item.id or "video"))
        suffix = video_path.suffix.lower() if video_path.suffix else ".mp4"
        file_name = f"{safe_item_id}_{uuid.uuid4().hex[:8]}{suffix}"
        parts = [part for part in [prefix, safe_platform, safe_task_id, safe_item_id, file_name] if part]
        return "/".join(parts)

    def _guess_video_content_type(self, video_path: Path) -> str:
        guessed = mimetypes.guess_type(str(video_path))[0]
        if guessed:
            return guessed
        return {
            ".mp4": "video/mp4",
            ".m4v": "video/mp4",
            ".mov": "video/quicktime",
            ".webm": "video/webm",
            ".flv": "video/x-flv",
            ".mkv": "video/x-matroska",
        }.get(video_path.suffix.lower(), "video/mp4")

    def _item_duration_seconds(self, item: VideoSummaryItem) -> Optional[float]:
        raw = item.raw or {}
        duration_keys = (
            "local_video_duration_seconds",
            "duration_seconds",
            "video_duration_seconds",
            "duration",
            "video_duration",
            "duration_sec",
            "play_time",
            "runtime",
            "length",
            "video_length",
            "media_info.duration",
            "page_info.media_info.duration",
        )
        for key in duration_keys:
            value = self._nested_raw_value(raw, key)
            parsed = self._parse_duration_value(value, key)
            if parsed:
                return parsed

        millisecond_keys = (
            "duration_ms",
            "video_duration_ms",
            "video.duration",
            "video.duration_ms",
            "video_info.duration",
            "video_info.duration_ms",
            "aweme_detail.video.duration",
            "aweme_detail.video.duration_ms",
            "photo.duration",
            "photo.duration_ms",
            "note_card.video.duration",
            "note_card.video.duration_ms",
        )
        for key in millisecond_keys:
            value = self._nested_raw_value(raw, key)
            parsed = self._parse_duration_value(value, key)
            if parsed:
                return parsed
        return None

    def _nested_raw_value(self, raw: Dict[str, Any], key: str) -> Any:
        if "." not in key:
            return raw.get(key)
        value: Any = raw
        for part in key.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    def _parse_duration_value(self, value: Any, key_name: str = "") -> Optional[float]:
        if value is None or value == "":
            return None
        key_name = key_name.lower()
        is_millisecond_key = (
            "duration_ms" in key_name
            or key_name == "video.duration"
            or key_name.endswith(".video.duration")
            or key_name == "photo.duration"
            or key_name.endswith(".photo.duration")
            or key_name.endswith("aweme_detail.video.duration")
            or key_name.endswith("note_card.video.duration")
        )
        if isinstance(value, (int, float)):
            seconds = float(value)
            if seconds <= 0:
                return None
            if is_millisecond_key or seconds > 24 * 60 * 60 * 1000:
                return seconds / 1000
            return seconds
        text = str(value).strip()
        if not text:
            return None
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return self._parse_duration_value(float(text), key_name)
        if re.fullmatch(r"\d{1,2}(?::\d{1,2}){1,2}", text):
            parts = [int(part) for part in text.split(":")]
            if len(parts) == 2:
                minutes, seconds = parts
                return minutes * 60 + seconds
            hours, minutes, seconds = parts
            return hours * 3600 + minutes * 60 + seconds
        return None

    def _public_url_video_limit_mb(self, settings: Dict[str, Any]) -> int:
        model = str(settings.get("model", DEFAULT_QWEN_SETTINGS["model"]) or "").lower()
        if model.startswith("qwen3.5-omni"):
            return 2048
        if model.startswith("qwen3-omni-flash"):
            return 256
        if model.startswith("qwen-omni-turbo"):
            return 150
        if model.startswith("qwen-vl-max"):
            return 2048
        if model.startswith(("qwen3.5", "qwen3.", "qwen-vl-plus", "qwen2.5-vl", "qvq")):
            return 1024
        return 150

    def _public_url_video_duration_limit_seconds(self, settings: Dict[str, Any]) -> Optional[float]:
        model = str(settings.get("model", DEFAULT_QWEN_SETTINGS["model"]) or "").lower()
        if model.startswith("qwen3.5-omni"):
            return 60 * 60
        if model.startswith("qwen3-omni-flash"):
            return 150
        if model.startswith("qwen-omni-turbo"):
            return 40
        if model.startswith("qwen-vl-max"):
            return 20 * 60
        if model.startswith(("qwen3-vl-plus", "qwen3-vl-flash", "qwen3-vl-235b")):
            return 60 * 60
        if model.startswith(("qwen3-vl", "qwen-vl-plus", "qwen2.5-vl", "qvq")):
            return 10 * 60
        return 40

    def _call_qwen_dashscope_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_path: Path,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        if str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"])) != "dashscope":
            raise RuntimeError("DashScope SDK local video upload is only available for DashScope/Qwen API profiles.")

        max_dashscope_mb = int(settings.get("max_dashscope_video_mb", DEFAULT_QWEN_SETTINGS["max_dashscope_video_mb"]))
        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        try:
            import dashscope  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("dashscope package is not installed; run `uv sync` or `pip install dashscope>=1.24.6`") from exc

        old_base_url = getattr(dashscope, "base_http_api_url", None)
        dashscope.base_http_api_url = self._dashscope_base_api_url(settings)
        try:
            candidates = self._dashscope_upload_video_candidates(task, item, video_path, settings, max_dashscope_mb)
            if not candidates:
                raise ValueError(
                    f"Local video is {video_size_mb:.1f}MB, larger than DashScope SDK local-file limit {max_dashscope_mb}MB"
                )

            errors: List[str] = []
            for candidate in candidates:
                candidate_size_mb = candidate.stat().st_size / (1024 * 1024)
                if candidate_size_mb > max_dashscope_mb:
                    errors.append(f"{candidate.name} is {candidate_size_mb:.1f}MB > {max_dashscope_mb}MB")
                    continue
                try:
                    return self._call_qwen_dashscope_video_once_with_retries(
                        task,
                        dashscope,
                        settings,
                        item,
                        candidate,
                        context_sources,
                    )
                except Exception as exc:
                    errors.append(f"{candidate.name}: {type(exc).__name__}: {exc}")
                    task.add_log(f"DashScope upload candidate failed for {item.id}: {candidate.name}: {type(exc).__name__}: {exc}")
            raise RuntimeError("; ".join(errors))
        finally:
            if old_base_url is not None:
                dashscope.base_http_api_url = old_base_url

    def _dashscope_upload_video_candidates(
        self,
        task: VideoTask,
        item: VideoSummaryItem,
        video_path: Path,
        settings: Dict[str, Any],
        max_dashscope_mb: int,
    ) -> List[Path]:
        original_size_mb = video_path.stat().st_size / (1024 * 1024)
        compression_enabled = bool(settings.get("enable_video_compression", True))
        compression_target_mb = int(settings.get("compression_target_mb", QWEN_VIDEO_COMPRESSION_TARGET_MB))
        compression_target_mb = min(max(10, compression_target_mb), max_dashscope_mb)

        candidates: List[Path] = []
        compressed: Optional[Path] = None
        if compression_enabled and original_size_mb > compression_target_mb:
            try:
                compressed = self._compress_video_for_dashscope(
                    task,
                    item,
                    video_path,
                    compression_target_mb,
                    max_dashscope_mb,
                )
                candidates.append(compressed)
            except Exception as exc:
                task.add_log(f"Video compression failed for {item.id}: {type(exc).__name__}: {exc}")

        if original_size_mb <= max_dashscope_mb:
            candidates.append(video_path)
        elif compressed is None:
            task.add_log(
                f"Original video {item.id} is {original_size_mb:.1f}MB and exceeds DashScope local-file limit {max_dashscope_mb}MB"
            )

        unique: List[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate.resolve())
            if key not in seen and candidate.exists() and candidate.stat().st_size > 0:
                unique.append(candidate)
                seen.add(key)
        return unique

    def _call_qwen_dashscope_video_once_with_retries(
        self,
        task: VideoTask,
        dashscope: Any,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        upload_path: Path,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        retry_count = int(settings.get("dashscope_retry_count", QWEN_DASHSCOPE_RETRY_COUNT))
        retry_count = min(max(1, retry_count), 5)
        upload_size_mb = upload_path.stat().st_size / (1024 * 1024)
        metadata = self._video_prompt_metadata(item, upload_size_mb)
        metadata["upload_file"] = upload_path.name
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "video": self._local_file_url(upload_path),
                        "fps": float(settings.get("video_fps", DEFAULT_QWEN_SETTINGS["video_fps"])),
                    },
                    {
                        "text": self._direct_video_prompt(metadata, context_sources),
                    },
                ],
            }
        ]

        last_error: Optional[Exception] = None
        qwen_label = self._qwen_runtime_label(settings)
        step_id = f"qwen_dashscope:{item.id}:{self._safe_item_id(upload_path.stem)}"
        self._start_step(
            task,
            step_id,
            f"DashScope SDK video analysis {item.id}",
            phase="qwen",
            item_id=item.id,
            message=f"{qwen_label}; file={upload_path.name}",
        )
        for attempt in range(1, retry_count + 1):
            self._check_cancelled(task)
            self._update_step(
                task,
                step_id,
                progress_percent=((attempt - 1) / retry_count) * 100,
                transferred_bytes=attempt - 1,
                total_bytes=retry_count,
                message=f"{qwen_label}; attempt {attempt}/{retry_count}; file={upload_path.name}",
            )
            task.add_log(
                f"DashScope local video upload attempt {attempt}/{retry_count} for {item.id}: "
                f"{upload_path.name} ({upload_size_mb:.1f}MB); {qwen_label}"
            )
            try:
                response = dashscope.MultiModalConversation.call(
                    api_key=settings["api_key"],
                    model=settings.get("model", DEFAULT_QWEN_SETTINGS["model"]),
                    messages=messages,
                )
                summary = self._extract_dashscope_message_text(response)
                self._finish_step(task, step_id, message=f"{qwen_label}; file={upload_path.name}")
                return summary
            except Exception as exc:
                self._check_cancelled(task)
                last_error = exc
                if attempt >= retry_count:
                    break
                delay = min(5 * (2 ** (attempt - 1)), 30)
                task.add_log(
                    f"DashScope local video upload failed for {item.id}: {type(exc).__name__}: {exc}; "
                    f"retrying in {delay}s"
                )
                time_module.sleep(delay)

        if last_error:
            self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; {type(last_error).__name__}: {last_error}")
            raise last_error
        self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; unknown failure")
        raise RuntimeError("DashScope local video upload failed without an exception")

    def _compress_video_for_dashscope(
        self,
        task: VideoTask,
        item: VideoSummaryItem,
        video_path: Path,
        target_mb: int,
        max_mb: int,
    ) -> Path:
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError("ffmpeg is not installed or not available in PATH")

        original_size_mb = video_path.stat().st_size / (1024 * 1024)
        target_dir = task.task_dir / "compressed"
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_id = self._safe_item_id(item.id)
        output_path = target_dir / f"{safe_id}_{target_mb}mb.mp4"
        if output_path.exists() and output_path.stat().st_size > 0:
            existing_size_mb = output_path.stat().st_size / (1024 * 1024)
            if existing_size_mb <= max_mb and existing_size_mb <= target_mb * 1.15:
                task.add_log(f"Using existing compressed video for {item.id}: {existing_size_mb:.1f}MB")
                return output_path

        duration = self._probe_video_duration_seconds(video_path)
        tight_target = target_mb <= 20
        audio_kbps = 32 if tight_target else 64
        min_video_kbps = 96 if tight_target else 260
        video_kbps = 420 if tight_target else 650
        max_width = 854 if tight_target else 1280
        max_height = 480 if tight_target else 720
        if duration and duration > 0:
            usable_bits = target_mb * 1024 * 1024 * 8 * 0.9
            video_kbps = max(min_video_kbps, int(usable_bits / duration / 1000) - audio_kbps)
        maxrate_kbps = max(video_kbps, int(video_kbps * 1.35))
        bufsize_kbps = maxrate_kbps * 2

        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-vf",
            f"scale=w='min({max_width},iw)':h='min({max_height},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            f"{video_kbps}k",
            "-maxrate",
            f"{maxrate_kbps}k",
            "-bufsize",
            f"{bufsize_kbps}k",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_kbps}k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        task.add_log(
            f"Compressing video for DashScope upload {item.id}: "
            f"{original_size_mb:.1f}MB -> target {target_mb}MB"
        )
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
        if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size <= 0:
            details = (completed.stderr or completed.stdout or "").strip()[-1200:]
            raise RuntimeError(f"ffmpeg video compression failed: {details}")

        compressed_size_mb = output_path.stat().st_size / (1024 * 1024)
        if compressed_size_mb > max_mb:
            raise RuntimeError(
                f"compressed video is {compressed_size_mb:.1f}MB, still larger than DashScope limit {max_mb}MB"
            )
        task.add_log(f"Compressed video ready for {item.id}: {compressed_size_mb:.1f}MB")
        return output_path

    def _probe_video_duration_seconds(self, video_path: Path) -> Optional[float]:
        ffprobe = self._find_ffprobe()
        if not ffprobe:
            return None
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if completed.returncode != 0:
            return None
        try:
            duration = float((completed.stdout or "").strip())
        except ValueError:
            return None
        return duration if duration > 0 else None

    def _find_ffprobe(self) -> Optional[str]:
        ffmpeg = self._find_ffmpeg()
        if ffmpeg:
            ffprobe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
            ffprobe_path = Path(ffmpeg).with_name(ffprobe_name)
            if ffprobe_path.exists():
                return str(ffprobe_path)
        return shutil.which("ffprobe")

    async def _call_qwen_base64_video_summary(
        self,
        task: VideoTask,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        video_path: Path,
        context_sources: List[Tuple[str, str]],
    ) -> str:
        max_inline_mb = int(settings.get("max_inline_video_mb", DEFAULT_QWEN_SETTINGS["max_inline_video_mb"]))
        video_size_mb = video_path.stat().st_size / (1024 * 1024)
        if video_size_mb > max_inline_mb:
            raise ValueError(
                f"Local video is {video_size_mb:.1f}MB, larger than Base64 raw-file limit {max_inline_mb}MB "
                "(official encoded payload limit is under 10MB)"
            )

        mime_type, encoded_video = await asyncio.to_thread(self._encode_video_file, video_path)
        metadata = self._video_prompt_metadata(item, video_size_mb)
        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": self._direct_video_prompt(metadata, context_sources),
            },
            {
                "type": "video_url",
                "video_url": {
                    "url": f"data:{mime_type};base64,{encoded_video}",
                },
                "fps": float(settings.get("video_fps", DEFAULT_QWEN_SETTINGS["video_fps"])),
            },
        ]
        step_id = f"qwen_base64:{item.id}"
        qwen_label = self._qwen_runtime_label(settings)
        self._start_step(task, step_id, f"Qwen Base64 video analysis {item.id}", phase="qwen", item_id=item.id, message=qwen_label)
        try:
            summary = await self._call_qwen(settings, content)
            self._finish_step(task, step_id)
            return summary
        except Exception as exc:
            self._finish_step(task, step_id, status="failed", message=f"{qwen_label}; {type(exc).__name__}: {exc}")
            raise

    def _video_prompt_metadata(self, item: VideoSummaryItem, video_size_mb: float) -> Dict[str, Any]:
        return {
            "id": item.id,
            "title": item.title,
            "desc": item.desc,
            "published_at": item.published_at,
            "url": item.url,
            "video_size_mb": round(video_size_mb, 2),
        }

    def _direct_video_prompt(self, metadata: Dict[str, Any], context_sources: List[Tuple[str, str]]) -> str:
        text_context = self._format_text_context_for_prompt(context_sources)
        prompt = (
            "你是视频内容分析助手。请直接分析随请求提供的视频，并结合可用的标题、描述、字幕或转录文本。"
            "请用中文输出信息充足的 Markdown 报告，固定使用以下加粗小标题：\n\n"
            "## **一句话概括**\n"
            "用 1 句完整的话说明视频核心内容。\n\n"
            "## **时间线摘要**\n"
            "这是必填部分。按视频时间顺序写 8-14 个时间段，使用 [00:00-00:45] 或 [01:02:10-01:03:00] 这类时间范围。"
            "每段 1-2 句，具体描述画面、人物动作、对白/观点推进、场景变化或结论，不要只列关键词。"
            "如果只能估计时间，请使用近似时间并说明不确定性。\n\n"
            "## **主要内容**\n"
            "用 2-4 段自然段详细说明视频的开头、中段、重点片段、结尾和核心观点/事件；不要写成过短提纲。\n\n"
            "## **关键信息**\n"
            "用不超过 5 条要点列出人物、场景、对象、数据、品牌、游戏/影视作品、明确观点等可核验信息。\n\n"
            "## **标题一致性**\n"
            "判断标题/描述与实际内容是否一致，并说明依据。\n\n"
            "## **检索标签**\n"
            "给出 8-12 个可用于检索的标签。\n\n"
            "视觉证据优先；提取到的文本上下文只能作为辅助证据。若文本与画面冲突，请指出冲突，不要静默合并。"
            "不要编造视频或上下文里没有出现的事实。\n\n"
            f"元信息：{json.dumps(metadata, ensure_ascii=False)}"
        )
        if text_context:
            prompt += (
                "\n\n可用于融合分析的文本上下文，可能包括字幕、平台 AI 总结、Whisper 转录、标题或描述：\n"
                f"{text_context}"
            )
        return prompt

    def _format_text_context_for_prompt(self, sources: List[Tuple[str, str]], max_chars: int = 12000) -> str:
        parts: List[str] = []
        used = 0
        for label, text in self._dedupe_text_sources(sources):
            block = f"### {label}\n{text.strip()}"
            remaining = max_chars - used
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = block[:remaining] + "\n[truncated]"
            parts.append(block)
            used += len(block)
        return "\n\n".join(parts)

    def _local_file_url(self, video_path: Path) -> str:
        return f"file://{video_path.resolve().as_posix()}"

    def _dashscope_base_api_url(self, settings: Dict[str, Any]) -> str:
        base_url = settings.get("base_url", DEFAULT_QWEN_SETTINGS["base_url"]).rstrip("/")
        compatible_suffix = "/compatible-mode/v1"
        if base_url.endswith(compatible_suffix):
            return f"{base_url[:-len(compatible_suffix)]}/api/v1"
        if base_url.endswith("/api/v1"):
            return base_url
        if base_url == "https://dashscope.aliyuncs.com":
            return "https://dashscope.aliyuncs.com/api/v1"
        return base_url

    def _chat_completions_base_url(self, settings: Dict[str, Any]) -> str:
        base_url = settings.get("base_url", DEFAULT_QWEN_SETTINGS["base_url"]).rstrip("/")
        if str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"])) != "dashscope":
            return base_url

        api_suffix = "/api/v1"
        if base_url.endswith(api_suffix):
            return f"{base_url[:-len(api_suffix)]}/compatible-mode/v1"
        if base_url == "https://dashscope.aliyuncs.com":
            return "https://dashscope.aliyuncs.com/compatible-mode/v1"
        return base_url

    def _extract_dashscope_message_text(self, response: Any) -> str:
        status_code = self._object_value(response, "status_code")
        if status_code and int(status_code) >= 400:
            code = self._object_value(response, "code", "")
            message = self._object_value(response, "message", "")
            raise RuntimeError(f"{status_code} {code} {message}".strip())

        output = self._object_value(response, "output", {})
        choices = self._object_value(output, "choices", [])
        if not choices:
            raise RuntimeError(f"DashScope response has no choices: {response}")

        message = self._object_value(choices[0], "message", {})
        content = self._object_value(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for part in content:
                text = self._object_value(part, "text")
                if text:
                    parts.append(str(text))
            if parts:
                return "\n".join(parts)
        raise RuntimeError(f"DashScope response has no text content: {response}")

    def _object_value(self, value: Any, key: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)

    async def _call_qwen_frame_summary(
        self,
        settings: Dict[str, Any],
        item: VideoSummaryItem,
        frames: List[Dict[str, Any]],
        context_sources: List[Tuple[str, str]],
    ) -> str:
        requested_frame_count = len(frames)
        ollama_profile = self._ollama_runtime_profile(settings) if self._is_ollama_provider(settings) else None
        frames = self._limit_ollama_frames(settings, frames)
        frame_points = [
            {
                "index": index,
                "timestamp": frame.get("time_label", ""),
            }
            for index, frame in enumerate(frames, start=1)
        ]
        metadata = {
            "id": item.id,
            "title": item.title,
            "desc": item.desc,
            "published_at": item.published_at,
            "url": item.url,
            "sampled_frames": frame_points,
        }
        if ollama_profile and requested_frame_count != len(frames):
            metadata["local_ollama_limits"] = {
                "requested_frames": requested_frame_count,
                "sent_frames": len(frames),
                "num_ctx": ollama_profile["num_ctx"],
                "text_context_chars": ollama_profile["text_context_chars"],
            }
        text_context = self._format_text_context_for_prompt(
            context_sources,
            max_chars=ollama_profile["text_context_chars"] if ollama_profile else 12000,
        )
        prompt = (
            "你是视频内容分析助手。下面是同一条视频按时间顺序抽取的关键画面，以及爬虫得到的元信息。"
            "请用中文输出信息充足的 Markdown 报告，固定使用以下加粗小标题：\n\n"
            "## **一句话概括**\n"
            "用 1 句完整的话说明视频核心内容。\n\n"
            "## **时间线摘要**\n"
            "这是必填部分。按采样帧时间顺序写 6-12 个时间段，使用 [MM:SS-MM:SS] 或 [HH:MM:SS-HH:MM:SS]。"
            "每段 1-2 句，具体描述这个时间段画面中发生了什么；相邻采样帧之间可以合理概括，但不要编造未出现的事件。\n\n"
            "## **主要内容**\n"
            "用 2-4 段自然段详细说明视频结构、重点画面、核心事件/观点和结论，避免只写短要点。\n\n"
            "## **关键信息**\n"
            "用不超过 5 条要点列出人物、场景、对象、数据、品牌、游戏/影视作品、明确观点等可核验信息。\n\n"
            "## **标题一致性**\n"
            "判断标题/描述与实际内容是否一致，并说明依据。\n\n"
            "## **检索标签**\n"
            "给出 8-12 个可用于检索的标签。\n\n"
            "如果提供了字幕、平台 AI 总结或 Whisper 转录，请把它作为辅助证据融合进分析；"
            "但画面证据优先，文本与画面冲突时请明确指出。不要编造画面或文本中没有的事实。\n\n"
            f"元信息：{json.dumps(metadata, ensure_ascii=False)}"
        )
        if ollama_profile and requested_frame_count != len(frames):
            prompt += (
                "\n\n本地 Ollama 模型上下文有限，系统已按时间均匀抽取 "
                f"{len(frames)}/{requested_frame_count} 帧进行分析。"
            )
        if text_context:
            prompt += f"\n\n可用文本上下文：\n{text_context}"
        content: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": prompt,
            }
        ]
        for index, frame in enumerate(frames, start=1):
            time_label = str(frame.get("time_label") or "")
            content.append(
                {
                    "type": "text",
                    "text": f"采样帧 {index}/{len(frames)}，时间戳：{time_label}",
                }
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{frame.get('image_base64', '')}"},
                }
            )

        return await self._call_qwen(settings, content)

    async def _call_qwen_text(self, settings: Dict[str, Any], prompt: str) -> str:
        return await self._call_qwen(settings, [{"type": "text", "text": prompt}])

    async def _call_qwen(self, settings: Dict[str, Any], content: List[Dict[str, Any]]) -> str:
        api_provider = str(settings.get("api_provider", DEFAULT_QWEN_SETTINGS["api_provider"]))
        if api_provider not in QWEN_API_PROVIDERS:
            raise RuntimeError(f"Unsupported video analysis API provider: {api_provider}")
        if api_provider == "ollama":
            return await self._call_ollama(settings, content)
        base_url = self._chat_completions_base_url(settings)
        url = f"{base_url}/chat/completions"
        model = str(settings.get("model", DEFAULT_QWEN_SETTINGS["model"]) or DEFAULT_QWEN_SETTINGS["model"])
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        }
        if self._is_omni_model(model):
            payload.update(
                {
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    "modalities": ["text"],
                }
            )
            if model.lower().startswith("qwen3-omni-flash"):
                payload["enable_thinking"] = False
            return await self._call_qwen_streaming(url, payload, headers)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    def _is_omni_model(self, model: str) -> bool:
        return "omni" in model.lower()

    async def _call_qwen_streaming(self, url: str, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        chunks: List[str] = []
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    line = raw_line.strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        line = line[len("data:") :].strip()
                    if not line or line == "[DONE]":
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    chunks.extend(self._extract_openai_stream_text(data))
        text = "".join(chunks).strip()
        if not text:
            raise RuntimeError("Streaming Qwen response did not contain text content.")
        return text

    async def _call_ollama(self, settings: Dict[str, Any], content: List[Dict[str, Any]]) -> str:
        base_url = str(settings.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        url = f"{base_url}/api/chat"
        model = str(settings.get("model") or "qwen3-vl:8b")
        profile = self._ollama_runtime_profile(settings)
        prompt, images = self._ollama_content_parts(content)
        prompt = (
            "你必须使用中文回答，除非用户明确要求其他语言。"
            "不要输出思考过程；如果只能从少量抽帧判断，请明确说明不确定性。\n\n"
            f"{prompt}"
        )
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    **({"images": images} if images else {}),
                }
            ],
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2,
                "num_ctx": int(profile["num_ctx"]),
                "num_predict": int(profile["num_predict"]),
            },
        }
        async with httpx.AsyncClient(timeout=900.0, trust_env=False) as client:
            response = await client.post(url, json=payload)
            if response.status_code >= 400:
                body = response.text.strip()
                detail = body[:1200] if body else response.reason_phrase
                raise RuntimeError(f"Ollama API {response.status_code} for model {model}: {detail}")
            data = response.json()
        message = data.get("message") if isinstance(data, dict) else None
        text = ""
        if isinstance(message, dict):
            text = str(message.get("content") or "").strip()
        if not text and isinstance(data, dict):
            text = str(data.get("response") or "").strip()
        if not text:
            raise RuntimeError(f"Ollama response did not contain text content: {data}")
        return text

    def _ollama_content_parts(self, content: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        texts: List[str] = []
        images: List[str] = []
        unsupported: List[str] = []
        for part in content:
            part_type = str(part.get("type") or "")
            if part_type == "text":
                text = str(part.get("text") or "")
                if text:
                    texts.append(text)
                continue
            if part_type == "image_url":
                image_url = part.get("image_url")
                url = ""
                if isinstance(image_url, dict):
                    url = str(image_url.get("url") or "")
                elif isinstance(image_url, str):
                    url = image_url
                encoded = self._extract_data_url_base64(url, expected_prefix="data:image/")
                if not encoded:
                    unsupported.append("non-base64 image_url")
                    continue
                images.append(encoded)
                continue
            if part_type == "video_url":
                unsupported.append("video_url")
                continue
            if part_type:
                unsupported.append(part_type)

        if unsupported:
            raise RuntimeError(
                "Ollama provider only supports text and sampled image frames in this workbench; "
                f"unsupported content: {', '.join(sorted(set(unsupported)))}"
            )
        prompt = "\n\n".join(text.strip() for text in texts if text.strip()).strip()
        if not prompt:
            prompt = "请分析随请求提供的图片内容。"
        return prompt, images

    def _extract_data_url_base64(self, url: str, *, expected_prefix: str) -> str:
        url = str(url or "").strip()
        if not url.startswith(expected_prefix):
            return ""
        marker = ";base64,"
        if marker not in url:
            return ""
        return url.split(marker, 1)[1].strip()

    def _extract_openai_stream_text(self, data: Dict[str, Any]) -> List[str]:
        parts: List[str] = []
        choices = data.get("choices")
        if not isinstance(choices, list):
            return parts
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            delta = choice.get("delta")
            message = choice.get("message")
            for payload in (delta, message):
                if not isinstance(payload, dict):
                    continue
                content = payload.get("content")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict):
                            text = item.get("text") or item.get("content")
                            if isinstance(text, str):
                                parts.append(text)
        return parts

    def _encode_video_file(self, video_path: Path) -> Tuple[str, str]:
        mime_map = {
            ".mp4": "video/mp4",
            ".m4v": "video/mp4",
            ".mov": "video/quicktime",
            ".webm": "video/webm",
            ".flv": "video/x-flv",
            ".mkv": "video/x-matroska",
        }
        mime_type = mime_map.get(video_path.suffix.lower(), "video/mp4")
        return mime_type, base64.b64encode(video_path.read_bytes()).decode("ascii")

    def _sample_video_frames(self, video_path: Path, sample_count: int) -> List[Dict[str, Any]]:
        ffmpeg_frames = self._sample_video_frames_with_ffmpeg(video_path, sample_count)
        if ffmpeg_frames:
            return ffmpeg_frames
        return self._sample_video_frames_with_cv2(video_path, sample_count)

    def _sample_video_frames_with_ffmpeg(self, video_path: Path, sample_count: int) -> List[Dict[str, Any]]:
        ffmpeg = self._find_ffmpeg()
        if not ffmpeg:
            return []

        duration = self._probe_video_duration_seconds(video_path)
        sample_count = max(1, int(sample_count or 1))
        if duration and duration > 0:
            end = max(0.0, duration - 0.25)
            if sample_count == 1:
                timestamps = [end / 2]
            else:
                timestamps = [min(end, i * end / (sample_count - 1)) for i in range(sample_count)]
        else:
            # Fallback probes for paths/codecs where ffprobe fails. Missing late frames are skipped.
            timestamps = [0.0, 30.0, 60.0, 120.0, 240.0, 360.0, 540.0, 720.0][:sample_count]

        frames: List[Dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="mediacrawler_frames_") as temp_dir:
            temp_root = Path(temp_dir)
            for index, timestamp in enumerate(timestamps, start=1):
                output_path = temp_root / f"frame_{index:03d}.jpg"
                cmd = [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-ss",
                    f"{timestamp:.3f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=w='min(640,iw)':h=-2",
                    "-q:v",
                    "3",
                    str(output_path),
                ]
                completed = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                )
                if completed.returncode != 0 or not output_path.exists() or output_path.stat().st_size <= 0:
                    continue
                frames.append(
                    {
                        "timestamp": round(timestamp, 3),
                        "time_label": self._format_timestamp(timestamp),
                        "frame_index": index,
                        "image_base64": base64.b64encode(output_path.read_bytes()).decode("ascii"),
                    }
                )
        return frames

    def _sample_video_frames_with_cv2(self, video_path: Path, sample_count: int) -> List[Dict[str, Any]]:
        import cv2

        frames: List[Dict[str, Any]] = []
        cap = cv2.VideoCapture(str(video_path))
        try:
            if not cap.isOpened():
                return []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if total_frames <= 0:
                positions = [0]
            elif sample_count == 1:
                positions = [max(total_frames // 2, 0)]
            else:
                positions = sorted(
                    set(int(i * (total_frames - 1) / (sample_count - 1)) for i in range(sample_count))
                )

            for position in positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                ok, frame = cap.read()
                if not ok or frame is None:
                    continue

                height, width = frame.shape[:2]
                max_width = 640
                if width > max_width:
                    ratio = max_width / width
                    frame = cv2.resize(frame, (max_width, int(height * ratio)))

                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ok:
                    timestamp = (position / fps) if fps > 0 else 0.0
                    frames.append(
                        {
                            "timestamp": round(timestamp, 3),
                            "time_label": self._format_timestamp(timestamp),
                            "frame_index": int(position),
                            "image_base64": base64.b64encode(buffer).decode("ascii"),
                        }
                    )
        finally:
            cap.release()
        return frames

    def _save_result(self, task: VideoTask) -> None:
        if not task.result:
            return
        task.task_dir.mkdir(parents=True, exist_ok=True)
        result_path = task.task_dir / "result.json"
        with result_path.open("w", encoding="utf-8") as f:
            json.dump(task.result.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        self._save_task_state(task, force=True)

    def _load_settings(self, include_secret: bool = False) -> Dict[str, Any]:
        store = self._load_profile_store(include_secret=include_secret)
        profile = dict(self._active_profile(store))
        if not include_secret:
            profile.pop("api_key", None)
            profile.pop("oss_access_key_id", None)
            profile.pop("oss_access_key_secret", None)
        return profile

    def _load_profile_store(self, include_secret: bool = False) -> Dict[str, Any]:
        now = self._now_iso()
        raw: Dict[str, Any] = {}
        if QWEN_SETTINGS_PATH.exists():
            try:
                with QWEN_SETTINGS_PATH.open("r", encoding="utf-8-sig") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    raw = data
            except Exception:
                raw = {}

        if isinstance(raw.get("profiles"), list):
            active_profile_id = str(raw.get("active_profile_id") or "")
            profiles = [
                self._normalize_profile(profile, index=index, now=now)
                for index, profile in enumerate(raw.get("profiles") or [])
                if isinstance(profile, dict)
            ]
        else:
            legacy = dict(DEFAULT_QWEN_SETTINGS)
            legacy.update({key: value for key, value in raw.items() if key in QWEN_PROFILE_FIELDS})
            profiles = [
                self._normalize_profile(
                    {
                        **legacy,
                        "id": str(raw.get("profile_id") or "default"),
                        "name": str(raw.get("profile_name") or "默认配置"),
                        "created_at": str(raw.get("created_at") or now),
                        "updated_at": str(raw.get("updated_at") or now),
                    },
                    index=0,
                    now=now,
                )
            ]
            active_profile_id = profiles[0]["id"]

        if not profiles:
            profiles = [self._normalize_profile({"id": "default", "name": "默认配置"}, index=0, now=now)]
        profile_ids = {str(profile["id"]) for profile in profiles}
        if active_profile_id not in profile_ids:
            active_profile_id = str(profiles[0]["id"])

        if not include_secret:
            profiles = [
                {
                    key: value
                    for key, value in profile.items()
                    if key not in {"api_key", "oss_access_key_id", "oss_access_key_secret"}
                }
                for profile in profiles
            ]
        return {
            "active_profile_id": active_profile_id,
            "profiles": profiles,
        }

    def _save_profile_store(self, store: Dict[str, Any]) -> None:
        TASK_ROOT.mkdir(parents=True, exist_ok=True)
        profiles = [self._normalize_profile(profile, index=index, now=self._now_iso()) for index, profile in enumerate(store["profiles"])]
        payload = {
            "active_profile_id": str(store["active_profile_id"]),
            "profiles": profiles,
        }
        with QWEN_SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _normalize_profile(self, profile: Dict[str, Any], index: int, now: str) -> Dict[str, Any]:
        profile_id = str(profile.get("id") or ("default" if index == 0 else uuid.uuid4().hex[:8]))
        has_explicit_provider = "api_provider" in profile
        normalized = {
            **dict(DEFAULT_QWEN_SETTINGS),
            "id": profile_id,
            "name": str(profile.get("name") or ("默认配置" if index == 0 else f"配置 {index + 1}")),
            "created_at": str(profile.get("created_at") or now),
            "updated_at": str(profile.get("updated_at") or now),
        }
        normalized.update({key: value for key, value in profile.items() if key in QWEN_PROFILE_FIELDS})
        normalized["base_url"] = str(normalized.get("base_url") or DEFAULT_QWEN_SETTINGS["base_url"]).rstrip("/")
        if not has_explicit_provider:
            normalized["api_provider"] = self._infer_api_provider(normalized["base_url"])
        normalized["api_provider"] = (
            normalized.get("api_provider")
            if normalized.get("api_provider") in QWEN_API_PROVIDERS
            else self._infer_api_provider(normalized["base_url"])
        )
        normalized["model"] = str(normalized.get("model") or DEFAULT_QWEN_SETTINGS["model"])
        normalized["video_input_mode"] = normalized.get("video_input_mode") if normalized.get("video_input_mode") in VIDEO_INPUT_MODES else "auto"
        normalized["video_upload_backend"] = normalized.get("video_upload_backend") if normalized.get("video_upload_backend") in VIDEO_UPLOAD_BACKENDS else "auto"
        normalized["video_fps"] = float(normalized.get("video_fps") or DEFAULT_QWEN_SETTINGS["video_fps"])
        normalized["sample_frames"] = int(normalized.get("sample_frames") or DEFAULT_QWEN_SETTINGS["sample_frames"])
        normalized["max_inline_video_mb"] = min(
            QWEN_BASE64_RAW_VIDEO_LIMIT_MB,
            max(1, int(normalized.get("max_inline_video_mb") or DEFAULT_QWEN_SETTINGS["max_inline_video_mb"])),
        )
        normalized["max_dashscope_video_mb"] = min(
            QWEN_DASHSCOPE_LOCAL_VIDEO_LIMIT_MB,
            max(1, int(normalized.get("max_dashscope_video_mb") or DEFAULT_QWEN_SETTINGS["max_dashscope_video_mb"])),
        )
        normalized["api_key"] = str(normalized.get("api_key") or "")
        normalized["oss_enabled"] = bool(normalized.get("oss_enabled"))
        normalized["oss_access_key_id"] = str(normalized.get("oss_access_key_id") or "")
        normalized["oss_access_key_secret"] = str(normalized.get("oss_access_key_secret") or "")
        normalized["oss_bucket"] = str(normalized.get("oss_bucket") or "")
        normalized["oss_endpoint"] = str(normalized.get("oss_endpoint") or "")
        normalized["oss_region"] = str(normalized.get("oss_region") or "")
        normalized["oss_prefix"] = str(normalized.get("oss_prefix") or DEFAULT_QWEN_SETTINGS["oss_prefix"]).strip().strip("/")
        normalized["oss_url_expires_seconds"] = min(
            604800,
            max(300, int(normalized.get("oss_url_expires_seconds") or DEFAULT_QWEN_SETTINGS["oss_url_expires_seconds"])),
        )
        normalized["oss_cleanup_after_analysis"] = bool(
            normalized.get("oss_cleanup_after_analysis", DEFAULT_QWEN_SETTINGS["oss_cleanup_after_analysis"])
        )
        return normalized

    def _infer_api_provider(self, base_url: str) -> str:
        parsed = urlparse(str(base_url or ""))
        hostname = parsed.hostname or ""
        if hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == 11434:
            return "ollama"
        return "dashscope" if hostname.endswith("dashscope.aliyuncs.com") else "openai_compatible"

    def _apply_profile_request(self, profile: Dict[str, Any], request: QwenSettingsRequest) -> None:
        if isinstance(request, QwenProfileRequest) and request.clear_api_key:
            profile["api_key"] = ""
        elif request.api_key and request.api_key.strip():
            profile["api_key"] = request.api_key.strip()
        if isinstance(request, QwenProfileRequest) and request.clear_oss_access_key:
            profile["oss_access_key_id"] = ""
            profile["oss_access_key_secret"] = ""
        elif request.oss_access_key_id and request.oss_access_key_id.strip():
            profile["oss_access_key_id"] = request.oss_access_key_id.strip()
        if request.oss_access_key_secret and request.oss_access_key_secret.strip():
            profile["oss_access_key_secret"] = request.oss_access_key_secret.strip()
        profile["api_provider"] = (
            request.api_provider
            if request.api_provider in QWEN_API_PROVIDERS
            else self._infer_api_provider(request.base_url)
        )
        profile["base_url"] = (request.base_url or DEFAULT_QWEN_SETTINGS["base_url"]).rstrip("/")
        profile["model"] = request.model or DEFAULT_QWEN_SETTINGS["model"]
        profile["oss_enabled"] = bool(request.oss_enabled)
        profile["oss_bucket"] = (request.oss_bucket or "").strip()
        profile["oss_endpoint"] = (request.oss_endpoint or "").strip().rstrip("/")
        profile["oss_region"] = (request.oss_region or "").strip()
        profile["oss_prefix"] = (request.oss_prefix or DEFAULT_QWEN_SETTINGS["oss_prefix"]).strip().strip("/")
        profile["oss_url_expires_seconds"] = min(604800, max(300, int(request.oss_url_expires_seconds or 7200)))
        if request.oss_cleanup_after_analysis is not None:
            profile["oss_cleanup_after_analysis"] = bool(request.oss_cleanup_after_analysis)
        profile["updated_at"] = self._now_iso()

    def _settings_response(self, profile: Dict[str, Any]) -> QwenSettingsResponse:
        api_key = profile.get("api_key", "")
        oss_access_key_id = profile.get("oss_access_key_id", "")
        oss_access_key_secret = profile.get("oss_access_key_secret", "")
        return QwenSettingsResponse(
            profile_id=str(profile["id"]),
            profile_name=str(profile["name"]),
            api_key_configured=bool(api_key),
            api_key_masked=self._mask_api_key(api_key) if api_key else None,
            api_provider=profile["api_provider"],
            base_url=profile["base_url"],
            model=profile["model"],
            video_input_mode=profile["video_input_mode"],
            video_upload_backend=profile["video_upload_backend"],
            video_fps=float(profile["video_fps"]),
            sample_frames=int(profile["sample_frames"]),
            max_inline_video_mb=int(profile["max_inline_video_mb"]),
            max_dashscope_video_mb=int(profile["max_dashscope_video_mb"]),
            oss_enabled=bool(profile["oss_enabled"]),
            oss_access_key_id_configured=bool(oss_access_key_id),
            oss_access_key_id_masked=self._mask_api_key(oss_access_key_id) if oss_access_key_id else None,
            oss_access_key_secret_configured=bool(oss_access_key_secret),
            oss_access_key_secret_masked=self._mask_api_key(oss_access_key_secret) if oss_access_key_secret else None,
            oss_bucket=str(profile["oss_bucket"]),
            oss_endpoint=str(profile["oss_endpoint"]),
            oss_region=str(profile["oss_region"]),
            oss_prefix=str(profile["oss_prefix"]),
            oss_url_expires_seconds=int(profile["oss_url_expires_seconds"]),
            oss_cleanup_after_analysis=bool(profile["oss_cleanup_after_analysis"]),
            settings_path=str(QWEN_SETTINGS_PATH),
        )

    def _profile_response(self, profile: Dict[str, Any], active_profile_id: str) -> QwenProfileResponse:
        api_key = profile.get("api_key", "")
        oss_access_key_id = profile.get("oss_access_key_id", "")
        oss_access_key_secret = profile.get("oss_access_key_secret", "")
        return QwenProfileResponse(
            id=str(profile["id"]),
            name=str(profile["name"]),
            active=str(profile["id"]) == active_profile_id,
            api_key_configured=bool(api_key),
            api_key_masked=self._mask_api_key(api_key) if api_key else None,
            api_provider=profile["api_provider"],
            base_url=profile["base_url"],
            model=profile["model"],
            video_input_mode=profile["video_input_mode"],
            video_upload_backend=profile["video_upload_backend"],
            video_fps=float(profile["video_fps"]),
            sample_frames=int(profile["sample_frames"]),
            max_inline_video_mb=int(profile["max_inline_video_mb"]),
            max_dashscope_video_mb=int(profile["max_dashscope_video_mb"]),
            oss_enabled=bool(profile["oss_enabled"]),
            oss_access_key_id_configured=bool(oss_access_key_id),
            oss_access_key_id_masked=self._mask_api_key(oss_access_key_id) if oss_access_key_id else None,
            oss_access_key_secret_configured=bool(oss_access_key_secret),
            oss_access_key_secret_masked=self._mask_api_key(oss_access_key_secret) if oss_access_key_secret else None,
            oss_bucket=str(profile["oss_bucket"]),
            oss_endpoint=str(profile["oss_endpoint"]),
            oss_region=str(profile["oss_region"]),
            oss_prefix=str(profile["oss_prefix"]),
            oss_url_expires_seconds=int(profile["oss_url_expires_seconds"]),
            oss_cleanup_after_analysis=bool(profile["oss_cleanup_after_analysis"]),
            created_at=str(profile.get("created_at") or ""),
            updated_at=str(profile.get("updated_at") or ""),
        )

    def _profile_secret_response(self, profile: Dict[str, Any], active_profile_id: str) -> QwenProfileSecretResponse:
        return QwenProfileSecretResponse(
            **self._profile_response(profile, active_profile_id).model_dump(),
            api_key=str(profile.get("api_key") or ""),
            oss_access_key_id=str(profile.get("oss_access_key_id") or ""),
            oss_access_key_secret=str(profile.get("oss_access_key_secret") or ""),
        )

    def _profiles_response(self, store: Dict[str, Any]) -> QwenProfilesResponse:
        active_profile_id = str(store["active_profile_id"])
        return QwenProfilesResponse(
            active_profile_id=active_profile_id,
            profiles=[self._profile_response(profile, active_profile_id) for profile in store["profiles"]],
            settings_path=str(QWEN_SETTINGS_PATH),
        )

    def _load_credential_store(self, *, include_secret: bool) -> Dict[str, Any]:
        raw: Dict[str, Any] = {}
        if PLATFORM_CREDENTIALS_PATH.exists():
            try:
                with PLATFORM_CREDENTIALS_PATH.open("r", encoding="utf-8-sig") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    raw = loaded
            except Exception:
                raw = {}

        profiles = raw.get("profiles") if isinstance(raw.get("profiles"), list) else []
        now = self._now_iso()
        normalized_profiles = [
            self._normalize_credential_profile(profile, index=index, now=now)
            for index, profile in enumerate(profiles)
            if isinstance(profile, dict)
        ]
        active = {
            str(platform): str(profile_id)
            for platform, profile_id in dict(raw.get("active_by_platform") or {}).items()
            if platform and profile_id
        }
        valid_ids = {str(profile["id"]) for profile in normalized_profiles}
        active = {platform: profile_id for platform, profile_id in active.items() if profile_id in valid_ids}
        for profile in normalized_profiles:
            platform = str(profile.get("platform") or "")
            if platform and platform not in active:
                active[platform] = str(profile["id"])

        if not include_secret:
            normalized_profiles = [
                {key: value for key, value in profile.items() if key != "cookies"}
                for profile in normalized_profiles
            ]
        return {
            "active_by_platform": active,
            "profiles": normalized_profiles,
        }

    def _save_credential_store(self, store: Dict[str, Any]) -> None:
        TASK_ROOT.mkdir(parents=True, exist_ok=True)
        now = self._now_iso()
        profiles = [
            self._normalize_credential_profile(profile, index=index, now=now)
            for index, profile in enumerate(store.get("profiles") or [])
            if isinstance(profile, dict)
        ]
        active = dict(store.get("active_by_platform") or {})
        valid_ids = {str(profile["id"]) for profile in profiles}
        active = {str(platform): str(profile_id) for platform, profile_id in active.items() if str(profile_id) in valid_ids}
        payload = {
            "active_by_platform": active,
            "profiles": profiles,
        }
        with PLATFORM_CREDENTIALS_PATH.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _normalize_credential_profile(self, profile: Dict[str, Any], index: int, now: str) -> Dict[str, Any]:
        platform = str(profile.get("platform") or "bili")
        profile_id = str(profile.get("id") or uuid.uuid4().hex[:8])
        created_at = str(profile.get("created_at") or now)
        metadata = profile.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        return {
            "id": profile_id,
            "platform": platform,
            "name": str(profile.get("name") or ("Default cookies" if index == 0 else f"Cookies {index + 1}")),
            "cookies": str(profile.get("cookies") or ""),
            "login_method": str(profile.get("login_method") or "cookie"),
            "metadata": metadata,
            "created_at": created_at,
            "updated_at": str(profile.get("updated_at") or created_at),
        }

    def _new_credential_id(self, store: Dict[str, Any]) -> str:
        existing = {str(profile.get("id")) for profile in store.get("profiles") or []}
        while True:
            profile_id = uuid.uuid4().hex[:8]
            if profile_id not in existing:
                return profile_id

    def _credential_by_id(self, store: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        for profile in store.get("profiles") or []:
            if str(profile.get("id")) == profile_id:
                return profile
        raise RuntimeError(f"Credential profile does not exist: {profile_id}")

    def _credential_response(
        self,
        profile: Dict[str, Any],
        active_by_platform: Dict[str, str],
    ) -> PlatformCredentialResponse:
        cookies = str(profile.get("cookies") or "")
        return PlatformCredentialResponse(
            id=str(profile["id"]),
            platform=profile["platform"],
            name=str(profile.get("name") or "Default cookies"),
            active=active_by_platform.get(str(profile.get("platform"))) == str(profile.get("id")),
            cookies_configured=bool(cookies),
            cookies_masked=self._mask_cookie_header(cookies) if cookies else None,
            login_method=str(profile.get("login_method") or "cookie"),
            metadata=dict(profile.get("metadata") or {}),
            created_at=str(profile.get("created_at") or ""),
            updated_at=str(profile.get("updated_at") or ""),
        )

    def _credential_secret_response(
        self,
        profile: Dict[str, Any],
        active_by_platform: Dict[str, str],
    ) -> PlatformCredentialSecretResponse:
        return PlatformCredentialSecretResponse(
            **self._credential_response(profile, active_by_platform).model_dump(),
            cookies=str(profile.get("cookies") or ""),
        )

    def _credential_store_response(self, store: Dict[str, Any]) -> PlatformCredentialsResponse:
        active = dict(store.get("active_by_platform") or {})
        return PlatformCredentialsResponse(
            active_by_platform=active,
            profiles=[self._credential_response(profile, active) for profile in store.get("profiles") or []],
            settings_path=str(PLATFORM_CREDENTIALS_PATH),
        )

    def _cookies_for_credential(self, platform: str, profile_id: Optional[str]) -> str:
        store = self._load_credential_store(include_secret=True)
        if not profile_id:
            profile_id = str((store.get("active_by_platform") or {}).get(platform) or "")
        if not profile_id:
            return ""
        profile = self._credential_by_id(store, profile_id)
        if str(profile.get("platform") or "") != platform:
            raise RuntimeError(f"Credential profile {profile_id} does not belong to platform {platform}.")
        return str(profile.get("cookies") or "")

    def _mask_cookie_header(self, cookies: str) -> str:
        names = []
        for part in cookies.split(";"):
            name = part.split("=", 1)[0].strip()
            if name:
                names.append(name)
        if not names:
            return "***"
        preview = ", ".join(names[:4])
        suffix = "" if len(names) <= 4 else f", +{len(names) - 4}"
        return f"{preview}{suffix}"

    def _active_profile(self, store: Dict[str, Any]) -> Dict[str, Any]:
        return self._profile_by_id(store, str(store["active_profile_id"]))

    def _profile_by_id(self, store: Dict[str, Any], profile_id: str) -> Dict[str, Any]:
        for profile in store["profiles"]:
            if str(profile["id"]) == profile_id:
                return profile
        raise RuntimeError(f"配置不存在：{profile_id}")

    def _new_profile_id(self, store: Dict[str, Any]) -> str:
        existing = {str(profile["id"]) for profile in store["profiles"]}
        while True:
            profile_id = uuid.uuid4().hex[:8]
            if profile_id not in existing:
                return profile_id

    def _now_iso(self) -> str:
        return datetime.now(LOCAL_TZ).isoformat()

    def _normalized_crawl_timing_updates(self, request: VideoSummaryTaskRequest) -> Dict[str, Any]:
        legacy_sleep = max(0.0, float(request.crawl_sleep_seconds or 0.0))
        min_sleep = request.crawl_min_sleep_seconds
        max_sleep = request.crawl_max_sleep_seconds

        if min_sleep is None and max_sleep is None:
            min_sleep = legacy_sleep
            max_sleep = legacy_sleep
        elif min_sleep is None:
            min_sleep = min(legacy_sleep, float(max_sleep or 0.0))
        elif max_sleep is None:
            max_sleep = max(legacy_sleep, float(min_sleep or 0.0))

        min_sleep = max(0.0, float(min_sleep or 0.0))
        max_sleep = max(0.0, float(max_sleep or 0.0))
        if max_sleep < min_sleep:
            min_sleep, max_sleep = max_sleep, min_sleep

        long_pause_min = max(0.0, float(request.crawl_long_pause_min_seconds or 0.0))
        long_pause_max = max(0.0, float(request.crawl_long_pause_max_seconds or 0.0))
        if long_pause_max < long_pause_min:
            long_pause_min, long_pause_max = long_pause_max, long_pause_min

        return {
            "crawl_sleep_seconds": max_sleep,
            "crawl_min_sleep_seconds": min_sleep,
            "crawl_max_sleep_seconds": max_sleep,
            "crawl_long_pause_every": max(0, int(request.crawl_long_pause_every or 0)),
            "crawl_long_pause_min_seconds": long_pause_min,
            "crawl_long_pause_max_seconds": long_pause_max,
        }

    async def _normalize_task_request(self, request: VideoSummaryTaskRequest) -> VideoSummaryTaskRequest:
        platform = request.platform.value
        source_mode = request.source_mode
        creator_id = request.creator_id.strip()
        if platform == "tieba" and source_mode != "ranking":
            raise RuntimeError("贴吧当前没有接入真实的视频搜索、视频下载和视频总结流程；只支持热议榜 metadata 展示。")
        if platform == "tieba" and request.workflow_mode != "metadata_only":
            raise RuntimeError("贴吧热议榜只支持 metadata_only 展示，不能进入视频下载或总结。")
        if not creator_id and source_mode == "creator":
            raise RuntimeError("请先输入创作者用户名、主页链接或平台 creator ID。")

        selected_item_ids = [str(value).strip() for value in request.selected_item_ids if str(value).strip()]
        if request.workflow_mode == "selected_items" and not selected_item_ids:
            raise RuntimeError("Please select at least one candidate video first.")
        task_updates: Dict[str, Any] = {
            "selected_item_ids": selected_item_ids,
            "source_task_id": str(request.source_task_id or "").strip() or None,
            "video_input_mode": request.video_input_mode,
            "max_crawl_items": max(int(request.max_crawl_items or 0), int(request.max_videos or 0), 1),
            **self._normalized_crawl_timing_updates(request),
        }

        cookie_updates: Dict[str, Any] = {}
        credential_cookies = self._cookies_for_credential(platform, request.credential_profile_id)
        if credential_cookies and not request.cookies:
            cookie_updates["cookies"] = credential_cookies
        elif request.cookies:
            normalized_cookies = normalize_cookie_input(request.cookies)
            if normalized_cookies:
                cookie_updates["cookies"] = normalized_cookies
        if cookie_updates.get("cookies"):
            cookie_updates["login_type"] = type(request.login_type).COOKIE

        if source_mode == "ranking":
            if platform == "bili":
                ranking_type = self._normalize_bili_ranking_type(request.ranking_type)
            elif platform == "ks":
                ranking_type = self._normalize_ks_ranking_type(request.ranking_type)
            elif platform == "dy":
                ranking_type = self._normalize_douyin_ranking_type(request.ranking_type)
            elif platform == "wb":
                ranking_type = self._normalize_weibo_ranking_type(request.ranking_type)
            elif platform == "zhihu":
                ranking_type = self._normalize_zhihu_ranking_type(request.ranking_type)
            elif platform == "tieba":
                ranking_type = self._normalize_tieba_ranking_type(request.ranking_type)
            else:
                ranking_type = str(request.ranking_type or "platform").strip() or "platform"
            ranking_limit = max(1, min(int(request.ranking_limit or request.max_videos or 5), 50))
            ranking_id = creator_id or f"ranking:{platform}:{ranking_type}"
            display_name = request.creator_display_name or f"{PLATFORM_LABELS.get(platform, platform)} {ranking_type} Top {ranking_limit}"
            return request.model_copy(
                update={
                    **task_updates,
                    **cookie_updates,
                    "creator_id": ranking_id,
                    "creator_display_name": display_name,
                    "ranking_type": ranking_type,
                    "ranking_limit": ranking_limit,
                    "max_videos": max(request.max_videos, ranking_limit),
                    "max_crawl_items": max(request.max_crawl_items, request.max_videos, ranking_limit),
                }
            )

        if source_mode == "search":
            keyword = (request.search_keyword or creator_id).strip()
            if not keyword:
                raise RuntimeError("Please enter a keyword or video title for search source mode.")
            return request.model_copy(
                update={
                    **task_updates,
                    **cookie_updates,
                    "creator_id": keyword,
                    "creator_display_name": request.creator_display_name or f"Search: {keyword}",
                    "search_keyword": keyword,
                }
            )

        try:
            creator_value, parsed_id = self._normalize_creator_identifier(platform, creator_id)
            if platform == "bili":
                creator_value = parsed_id
            return request.model_copy(update={**task_updates, **cookie_updates, "creator_id": creator_value})
        except ValueError:
            if platform != "bili":
                raise RuntimeError("当前平台请使用创作者主页链接或平台 creator ID，暂不支持可靠的用户名搜索。")

        resolve_request = CreatorResolveRequest(platform=request.platform, query=creator_id)
        candidates = await self._search_bili_creators(resolve_request, creator_id)
        if not candidates:
            raise RuntimeError(f"没有搜索到 B 站创作者：{creator_id}。请换关键词，或粘贴空间链接/UID。")

        exact_candidates = [candidate for candidate in candidates if candidate.display_name == creator_id]
        if len(exact_candidates) == 1:
            selected = exact_candidates[0]
        elif len(candidates) == 1:
            selected = candidates[0]
        else:
            preview = "；".join(
                f"{candidate.display_name}(UID {candidate.id})"
                for candidate in candidates[:5]
            )
            raise RuntimeError(
                "这个用户名匹配到多个 B 站候选，请先点击搜索创作者并选择具体 UID。"
                f" 候选：{preview}"
            )

        return request.model_copy(
            update={
                **task_updates,
                **cookie_updates,
                "creator_id": selected.id,
                "creator_display_name": selected.display_name,
                "profile_url": selected.profile_url,
            }
        )

    async def _search_bili_creators(self, request: CreatorResolveRequest, query: str) -> List[CreatorCandidate]:
        cache_key = (request.platform.value, query.strip())
        now_ts = datetime.now(LOCAL_TZ).timestamp()
        cached = self._creator_search_cache.get(cache_key)
        if cached and now_ts - cached[0] <= 300:
            return cached[1]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://search.bilibili.com/",
        }
        params = {
            "search_type": "bili_user",
            "keyword": query,
            "page": 1,
            "page_size": 10,
        }
        try:
            async with httpx.AsyncClient(timeout=20.0, headers=headers, trust_env=False) as client:
                payload = None
                results: List[Any] = []
                for url in (
                    "https://api.bilibili.com/x/web-interface/wbi/search/type",
                    "https://api.bilibili.com/x/web-interface/search/type",
                ):
                    try:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        candidate_payload = response.json()
                        if candidate_payload.get("code") != 0:
                            continue
                        candidate_results = ((candidate_payload.get("data") or {}).get("result") or [])
                        if not isinstance(candidate_results, list):
                            continue
                        payload = candidate_payload
                        results = candidate_results
                        if results:
                            break
                    except httpx.HTTPStatusError:
                        continue
                if payload is None:
                    return []
        except Exception:
            return []

        if payload.get("code") != 0:
            return []
        candidates: List[CreatorCandidate] = []
        normalized_query = query.strip().casefold()
        for item in results:
            if not isinstance(item, dict):
                continue
            mid = item.get("mid")
            if not mid:
                continue
            uname = str(item.get("uname") or mid)
            official = item.get("official_verify") if isinstance(item.get("official_verify"), dict) else {}
            official_type_raw = official.get("type")
            official_type = int(official_type_raw) if official_type_raw is not None else -1
            verification = str(official.get("desc") or "")
            fans = self._safe_int(item.get("fans"))
            videos = self._safe_int(item.get("videos"))
            description_parts = [
                str(value).strip()
                for value in (item.get("usign"), verification)
                if value and str(value).strip()
            ]
            creator_id = str(mid)
            candidates.append(
                CreatorCandidate(
                    id=creator_id,
                    platform=request.platform,
                    display_name=uname,
                    avatar_url=str(item.get("upic") or ""),
                    profile_url=f"https://space.bilibili.com/{creator_id}",
                    description=" | ".join(description_parts),
                    follower_count=fans,
                    video_count=videos,
                    verified=official_type in {0, 1},
                    verification=verification,
                    metrics={
                        "parsed_id": creator_id,
                        "source": "bili_user_search",
                        "fans": fans or 0,
                        "videos": videos or 0,
                        "level": item.get("level", 0),
                        "official_type": official_type,
                        "verification": verification,
                        "exact_name_match": uname.strip().casefold() == normalized_query,
                    },
                    raw=item,
                )
            )
        candidates.sort(
            key=lambda candidate: (
                0 if bool(candidate.metrics.get("exact_name_match")) else 1,
                -int(candidate.metrics.get("fans") or 0),
            )
        )
        if candidates:
            self._creator_search_cache[cache_key] = (now_ts, candidates)
        return candidates

    def _dedupe_candidates(self, candidates: List[CreatorCandidate]) -> List[CreatorCandidate]:
        seen: set[Tuple[str, str]] = set()
        unique: List[CreatorCandidate] = []
        for candidate in candidates:
            key = (candidate.platform.value, candidate.id)
            if key in seen:
                continue
            seen.add(key)
            unique.append(candidate)
        return unique

    def _split_creator_inputs(self, query: str) -> List[str]:
        return [part.strip() for part in re.split(r"[\n,]+", query or "") if part.strip()]

    def _parse_candidate_line(self, line: str) -> Tuple[str, str, str]:
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1], " | ".join(parts[2:])
        return "", line.strip(), ""

    def _normalize_creator_identifier(self, platform: str, raw_identifier: str) -> Tuple[str, str]:
        value = raw_identifier.strip().rstrip("/")
        if not value:
            raise ValueError("Empty creator identifier")

        if platform == "xhs":
            parsed_id = self._regex_first(value, r"/user/profile/([^/?#]+)") or value
            if not re.match(r"^[a-zA-Z0-9_-]+$", parsed_id):
                raise ValueError(f"Unable to parse Xiaohongshu creator: {value}")
            return value, parsed_id

        if platform == "dy":
            parsed_id = self._regex_first(value, r"/user/([^/?#]+)") or value
            if not parsed_id or parsed_id.startswith("http"):
                raise ValueError(f"Unable to parse Douyin creator: {value}")
            return value, parsed_id

        if platform == "ks":
            parsed_id = self._regex_first(value, r"/profile/([^/?#]+)") or value
            if not parsed_id or parsed_id.startswith("http"):
                raise ValueError(f"Unable to parse Kuaishou creator: {value}")
            return value, parsed_id

        if platform == "bili":
            parsed_id = self._regex_first(value, r"space\.bilibili\.com/(\d+)") or value
            if not parsed_id.isdigit():
                raise ValueError(f"Unable to parse Bilibili creator: {value}")
            return value, parsed_id

        if platform == "wb":
            parsed_id = (
                self._regex_first(value, r"(?:weibo\.com|m\.weibo\.cn)/(?:u/)?(\d+)")
                or self._regex_first(value, r"/u/(\d+)")
                or value
            )
            if not parsed_id.isdigit():
                raise ValueError(f"Unable to parse Weibo creator: {value}")
            return parsed_id, parsed_id

        if platform == "tieba":
            parsed_id = (
                self._regex_first(value, r"[?&]id=([^&#]+)")
                or self._regex_first(value, r"/home/main/([^/?#]+)")
                or value
            )
            return value, parsed_id

        if platform == "zhihu":
            parsed_id = self._regex_first(value, r"/people/([^/?#]+)") or value
            if not parsed_id or parsed_id.startswith("http"):
                raise ValueError(f"Unable to parse Zhihu creator: {value}")
            return parsed_id, parsed_id

        raise ValueError(f"Unsupported platform: {platform}")

    def _build_profile_url(self, platform: str, creator_value: str, parsed_id: str) -> str:
        if creator_value.startswith(("http://", "https://")):
            return creator_value
        if platform == "xhs":
            return f"https://www.xiaohongshu.com/user/profile/{parsed_id}"
        if platform == "dy":
            return f"https://www.douyin.com/user/{parsed_id}"
        if platform == "ks":
            return f"https://www.kuaishou.com/profile/{parsed_id}"
        if platform == "bili":
            return f"https://space.bilibili.com/{parsed_id}"
        if platform == "wb":
            return f"https://weibo.com/u/{parsed_id}"
        if platform == "tieba":
            return f"https://tieba.baidu.com/home/main?id={parsed_id}"
        if platform == "zhihu":
            return f"https://www.zhihu.com/people/{parsed_id}"
        return creator_value

    def _regex_first(self, text: str, pattern: str) -> Optional[str]:
        match = re.search(pattern, text)
        return match.group(1) if match else None

    def _is_video_record(self, platform: str, record: Dict[str, Any]) -> bool:
        if platform == "xhs":
            return record.get("type") == "video" or bool(record.get("video_url"))
        if platform == "dy":
            return bool(record.get("video_download_url")) and not self._is_douyin_non_video_record(record)
        if platform in {"ks", "bili"}:
            return bool(self._first_value(record, CONTENT_ID_KEYS.get(platform, [])))
        if platform == "wb":
            return bool(record.get("is_video") or record.get("video_page_url") or self._extract_direct_video_urls(platform, record))
        if platform == "zhihu":
            return record.get("content_type") == "zvideo" or "/zvideo/" in str(record.get("content_url", ""))
        return bool(self._extract_direct_video_urls(platform, record))

    def _is_douyin_non_video_record(self, record: Dict[str, Any]) -> bool:
        aweme_type = str(record.get("aweme_type") or "").strip()
        if aweme_type in {"68"}:
            return True
        video_download_url = str(record.get("video_download_url") or "").strip()
        music_download_url = str(record.get("music_download_url") or "").strip()
        if video_download_url and music_download_url and video_download_url == music_download_url:
            return True
        return False

    def _get_published_datetime(self, record: Dict[str, Any]) -> Optional[datetime]:
        for key in TIME_KEYS:
            value = record.get(key)
            parsed = self._parse_datetime_value(value)
            if parsed:
                return parsed
        return None

    def _parse_datetime_value(self, value: Any) -> Optional[datetime]:
        if value is None or value == "":
            return None
        if isinstance(value, (int, float)):
            return self._datetime_from_timestamp(float(value))
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            if text.isdigit():
                return self._datetime_from_timestamp(float(text))
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    return parsed.replace(tzinfo=LOCAL_TZ)
                except ValueError:
                    pass
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo:
                    return parsed.astimezone(LOCAL_TZ)
                return parsed.replace(tzinfo=LOCAL_TZ)
            except ValueError:
                return None
        return None

    def _datetime_from_timestamp(self, timestamp: float) -> Optional[datetime]:
        if timestamp <= 0:
            return None
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        try:
            return datetime.fromtimestamp(timestamp, LOCAL_TZ)
        except (OverflowError, OSError, ValueError):
            return None

    def _first_value(self, record: Dict[str, Any], keys: List[str]) -> str:
        for key in keys:
            value = record.get(key)
            if value is not None and value != "":
                return str(value)
        return ""

    def _first_url_value(self, record: Dict[str, Any], keys: List[str]) -> str:
        for key in keys:
            for url in self._iter_url_values(record.get(key)):
                if url.startswith("//"):
                    return f"https:{url}"
                if url.startswith(("http://", "https://", "data:")):
                    return url
        return ""

    def _iter_url_values(self, value: Any) -> Iterable[str]:
        if value in (None, "", [], {}):
            return []
        if isinstance(value, str):
            return [part.strip() for part in re.split(r"[\s,;]+", value) if part.strip()]
        if isinstance(value, dict):
            values: List[str] = []
            for key in ("url", "src", "href", "image", "cover", "origin", "url_list", "urls"):
                values.extend(self._iter_url_values(value.get(key)))
            return values
        if isinstance(value, list):
            values: List[str] = []
            for item in value:
                values.extend(self._iter_url_values(item))
            return values
        return [str(value).strip()] if str(value).strip() else []

    def _split_urls(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [part.strip() for part in re.split(r"[,;\s]+", str(value)) if part.strip()]

    def _is_landing_page_url(self, platform: str, field_name: str, url: str) -> bool:
        if field_name not in {"video_url", "content_url", "url", "note_url", "aweme_url"}:
            return False
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        landing_hosts = ["bilibili.com", "douyin.com", "kuaishou.com", "weibo.com", "zhihu.com", "tieba.baidu.com"]
        if any(host.endswith(item) for item in landing_hosts) and not path.endswith(tuple(VIDEO_EXTENSIONS)):
            if platform == "xhs" and "sns-video" in host:
                return False
            return True
        return False

    def _looks_like_remote_video_url(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        host = parsed.netloc.lower()
        return (
            path.endswith(tuple(VIDEO_EXTENSIONS))
            or "video" in host
            or "mime_type=video" in url.lower()
            or "video_id" in url.lower()
        )

    def _extract_markdown_section(self, markdown: str, section_names: List[str]) -> str:
        if not markdown:
            return ""
        headings: List[Tuple[int, int, str]] = []
        for match in re.finditer(r"(?m)^#{1,6}\s*(?:\*\*)?\s*([^*\n#]+?)\s*(?:\*\*)?\s*$", markdown):
            name = re.sub(r"\s+", "", match.group(1).strip())
            headings.append((match.start(), match.end(), name))
        targets = {re.sub(r"\s+", "", name) for name in section_names}
        for index, (_start, end, name) in enumerate(headings):
            if name not in targets:
                continue
            next_start = headings[index + 1][0] if index + 1 < len(headings) else len(markdown)
            return markdown[end:next_start].strip()
        return ""

    def _markdown_to_plain_text(self, markdown: str) -> str:
        text = re.sub(r"```[\s\S]*?```", " ", markdown or "")
        text = re.sub(r"(?m)^#{1,6}\s*", "", text)
        text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
        text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
        text = re.sub(r"[*_`>#]", "", text)
        text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _clip_plain_text(self, text: str, max_chars: int = 600) -> str:
        clean = self._markdown_to_plain_text(text)
        if len(clean) <= max_chars:
            return clean
        cut = clean[:max_chars]
        boundary = max(cut.rfind("。"), cut.rfind("；"), cut.rfind("！"), cut.rfind("？"), cut.rfind(". "))
        if boundary >= max_chars - 120:
            cut = cut[:boundary + 1]
        return cut.rstrip("，,；;：: ") + "..."

    def _item_summary_digest(self, item: VideoSummaryItem) -> Dict[str, str]:
        summary = item.summary or ""
        one_sentence = self._clip_plain_text(
            self._extract_markdown_section(summary, ["一句话概括", "一句话总结", "概括"]) or summary,
            220,
        )
        main_content = (
            self._extract_markdown_section(summary, ["主要内容"])
            or self._extract_markdown_section(summary, ["内容梗概"])
            or self._extract_markdown_section(summary, ["时间线摘要"])
            or summary
        )
        synopsis = self._clip_plain_text(main_content, 760)
        timeline = self._extract_markdown_section(summary, ["时间线摘要"])
        timeline_plain = self._clip_plain_text(timeline, 360)
        return {
            "title": item.title or item.id,
            "published_at": item.published_at or "未知",
            "one_sentence": one_sentence or "暂无可用一句话概括。",
            "synopsis": synopsis or one_sentence or "暂无可用内容梗概。",
            "timeline": timeline_plain,
        }

    def _mermaid_node_text(self, text: str, max_chars: int = 42) -> str:
        clean = self._markdown_to_plain_text(text)
        clean = re.sub(r"[\[\]【】{}()（）<>《》:：;；|\\\"'“”‘’`*_#]", "", clean)
        clean = re.sub(r"[!?！？,，.。、…—-]+", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return (clean[:max_chars] or "未命名").rstrip()

    def _fallback_mindmap(self, digests: List[Dict[str, str]]) -> str:
        if not digests:
            return "材料不足，无法生成可靠思维导图。"
        lines = [
            "```mermaid",
            "mindmap",
            "  root((视频内容汇总))",
            "    共同主题",
        ]
        if len(digests) == 1:
            lines.append(f"      {self._mermaid_node_text(digests[0]['one_sentence'], 36)}")
        else:
            for digest in digests[:3]:
                lines.append(f"      {self._mermaid_node_text(digest['one_sentence'], 32)}")
        lines.append("    各视频")
        for digest in digests[:8]:
            lines.extend(
                [
                    f"      {self._mermaid_node_text(digest['title'], 34)}",
                    f"        {self._mermaid_node_text(digest['one_sentence'], 34)}",
                ]
            )
        lines.append("```")
        return "\n".join(lines)

    def _fallback_aggregate_summary(self, items: List[VideoSummaryItem]) -> str:
        digests = [self._item_summary_digest(item) for item in items if item.summary]
        if not digests:
            return "## **共同主题**\n暂无可用单视频摘要，无法生成整体汇总。"

        if len(digests) == 1:
            common_theme = (
                f"本次任务只有 1 条已完成视频，核心主题集中在：{digests[0]['one_sentence']} "
                "下面的整体汇总由单视频摘要自动整理生成。"
            )
            aggregate = digests[0]["synopsis"]
        else:
            theme_text = "；".join(digest["one_sentence"] for digest in digests[:4])
            common_theme = (
                f"本批共 {len(digests)} 条已完成视频。根据单视频摘要，内容主要围绕："
                f"{self._clip_plain_text(theme_text, 520)}"
            )
            aggregate = (
                f"本次共整理 {len(digests)} 条视频。"
                + " ".join(f"{digest['title']}：{digest['one_sentence']}" for digest in digests[:5])
            )
            aggregate = self._clip_plain_text(aggregate, 900)

        lines = [
            "## **共同主题**",
            common_theme,
            "",
            "## **各自内容梗概**",
        ]
        for index, digest in enumerate(digests[:10], start=1):
            synopsis = digest["synopsis"]
            if digest["timeline"] and digest["timeline"] not in synopsis:
                synopsis = f"{synopsis} 时间线要点：{digest['timeline']}"
            lines.extend(
                [
                    f"### **{index}. {digest['title']}**",
                    f"**发布时间**：{digest['published_at']}",
                    f"**内容梗概**：{synopsis}",
                    "",
                ]
            )
        lines.extend(
            [
                "## **摘要**",
                aggregate,
                "",
                "## **思维导图**",
                self._fallback_mindmap(digests),
            ]
        )
        return "\n".join(lines)

    def _safe_int(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(float(str(value).replace(",", "").strip()))
        except (TypeError, ValueError):
            return None

    def _mask_api_key(self, api_key: str) -> str:
        if len(api_key) <= 8:
            return api_key[:2] + "***" + api_key[-2:]
        return api_key[:4] + "..." + api_key[-4:]

    def _redact_command(self, cmd: List[str]) -> str:
        redacted: List[str] = []
        skip_next = False
        for item in cmd:
            if skip_next:
                redacted.append("***")
                skip_next = False
                continue
            redacted.append(item)
            if item == "--cookies":
                skip_next = True
        return " ".join(redacted)


video_summary_manager = VideoSummaryManager()
