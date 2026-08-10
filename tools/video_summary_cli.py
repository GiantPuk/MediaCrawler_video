from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import typer


DEFAULT_API_BASE = "http://127.0.0.1:8080/api"

app = typer.Typer(help="Terminal client for the MediaCrawler video workspace API.")
creators_app = typer.Typer(help="Resolve creator candidates.")
tasks_app = typer.Typer(help="Start and inspect video tasks.")
credentials_app = typer.Typer(help="Manage platform cookie profiles.")
qwen_app = typer.Typer(help="Manage Qwen/DashScope API profiles.")


SUPPORTED_RANKINGS: Dict[str, List[Dict[str, Any]]] = {
    "bili": [
        {"value": "popular", "label": "Bilibili popular", "kind": "video", "downloadable": True},
        {"value": "ranking", "label": "Bilibili all ranking", "kind": "video", "downloadable": True},
        {"value": "precious", "label": "Bilibili must-watch", "kind": "video", "downloadable": True},
        {"value": "weekly", "label": "Bilibili weekly selected", "kind": "video", "downloadable": True, "requires_cookie": True},
        {"value": "hot_search", "label": "Bilibili hot search", "kind": "topic", "downloadable": False},
        {"value": "ranking_douga", "label": "Bilibili douga ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_guochuang", "label": "Bilibili guochuang ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_music", "label": "Bilibili music ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_dance", "label": "Bilibili dance ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_game", "label": "Bilibili game ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_knowledge", "label": "Bilibili knowledge ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_tech", "label": "Bilibili technology ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_sports", "label": "Bilibili sports ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_car", "label": "Bilibili car ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_life", "label": "Bilibili life ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_food", "label": "Bilibili food ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_animal", "label": "Bilibili animal ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_kichiku", "label": "Bilibili kichiku ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_fashion", "label": "Bilibili fashion ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_ent", "label": "Bilibili entertainment ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_cinephile", "label": "Bilibili cinephile ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_movie", "label": "Bilibili movie ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_tv", "label": "Bilibili TV ranking", "kind": "video", "downloadable": True},
        {"value": "ranking_documentary", "label": "Bilibili documentary ranking", "kind": "video", "downloadable": True},
    ],
    "ks": [
        {
            "value": "hot",
            "label": "Kuaishou short-video hot rank",
            "kind": "video_candidate",
            "downloadable": "depends_on_detail_api",
        },
    ],
    "dy": [
        {"value": "hot_search", "label": "Douyin hot search", "kind": "topic", "downloadable": False},
        {"value": "trending", "label": "Douyin trending", "kind": "topic", "downloadable": False},
    ],
    "wb": [
        {"value": "hot_search", "label": "Weibo hot search", "kind": "topic", "downloadable": False},
        {"value": "hot_gov", "label": "Weibo official hot topic", "kind": "topic", "downloadable": False},
    ],
    "zhihu": [
        {"value": "total", "label": "Zhihu hot list", "kind": "question", "downloadable": False},
        {"value": "zvideo", "label": "Zhihu zvideo hot-list endpoint", "kind": "question", "downloadable": False},
    ],
    "tieba": [
        {"value": "hot_topic", "label": "Baidu Tieba hot topics", "kind": "topic", "downloadable": False},
    ],
    "xhs": [],
}


def _endpoint(api_base: str, path: str) -> str:
    return f"{api_base.rstrip('/')}{path}"


def _print_json(data: Any) -> None:
    try:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        typer.echo(json.dumps(data, ensure_ascii=True, indent=2))


def _echo_text(text: str) -> None:
    try:
        typer.echo(text)
    except UnicodeEncodeError:
        typer.echo(text.encode("ascii", errors="backslashreplace").decode("ascii"))


def _request(
    method: str,
    api_base: str,
    path: str,
    *,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    try:
        with httpx.Client(timeout=120.0, trust_env=False) as client:
            response = client.request(method, _endpoint(api_base, path), json=payload)
            response.raise_for_status()
            if response.content:
                return response.json()
            return {}
    except httpx.HTTPStatusError as exc:
        detail: Any
        try:
            detail = exc.response.json()
        except Exception:
            detail = exc.response.text
        raise typer.BadParameter(f"API error {exc.response.status_code}: {detail}") from exc
    except httpx.HTTPError as exc:
        raise typer.BadParameter(f"Cannot connect to backend API: {exc}") from exc


def _read_text(value: str, file_path: Optional[Path]) -> str:
    if file_path:
        return file_path.read_text(encoding="utf-8").strip()
    return value.strip()


def _split_ids(values: Optional[List[str]], csv_values: str) -> List[str]:
    result: List[str] = []
    for value in values or []:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    result.extend(part.strip() for part in csv_values.split(",") if part.strip())
    return result


@creators_app.command("resolve")
def resolve_creators(
    platform: str = typer.Option("bili", "--platform", "-p", help="Platform: xhs, dy, ks, bili, wb, tieba, zhihu."),
    query: str = typer.Option(..., "--query", "-q", help="Creator username, homepage URL, or platform creator ID."),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base", help="Backend API base URL."),
) -> None:
    """Resolve creator candidates before loading creator videos."""

    data = _request("POST", api_base, "/video-summary/creators/resolve", payload={"platform": platform, "query": query})
    _print_json(data)


@tasks_app.command("start")
def start_task(
    platform: str = typer.Option("bili", "--platform", "-p"),
    source_mode: str = typer.Option("creator", "--source-mode", help="creator, search, or ranking."),
    query: str = typer.Option("", "--query", "-q", help="Creator ID/name or search keyword."),
    creator_id: str = typer.Option("", "--creator-id", help="Concrete creator ID. Prefer this after resolving candidates."),
    creator_display_name: str = typer.Option("", "--creator-name", help="Display name for a selected creator."),
    profile_url: str = typer.Option("", "--profile-url", help="Creator homepage URL."),
    ranking_type: str = typer.Option(
        "popular",
        "--ranking-type",
        help=(
            "Bili: popular, ranking, precious, weekly, hot_search, or ranking_<region>. Kuaishou: hot. "
            "Douyin: hot_search or trending. Weibo: hot_search or hot_gov. "
            "Tieba: hot_topic. Zhihu: total or zvideo."
        ),
    ),
    ranking_limit: int = typer.Option(5, "--ranking-limit", min=1, max=50),
    credential_profile_id: str = typer.Option("", "--credential-profile-id", help="Saved platform cookie profile ID."),
    workflow_mode: str = typer.Option("metadata_only", "--workflow-mode", help="metadata_only, selected_items, or full."),
    source_task_id: str = typer.Option("", "--source-task-id", help="Metadata task ID for selected_items workflow."),
    selected_item_id: Optional[List[str]] = typer.Option(None, "--selected-item-id", help="Repeat or comma-separate selected item IDs."),
    selected_items: str = typer.Option("", "--selected-items", help="Comma-separated selected item IDs."),
    login_type: str = typer.Option("qrcode", "--login-type", help="qrcode or cookie."),
    cookies: str = typer.Option("", "--cookies", help="Cookie header. Prefer saved credential profiles."),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies-file", help="Text file containing Cookie header."),
    start_date: str = typer.Option(date.today().isoformat(), "--start-date"),
    end_date: str = typer.Option(date.today().isoformat(), "--end-date"),
    max_videos: int = typer.Option(20, "--max-videos", min=1, max=200),
    crawl_concurrency: int = typer.Option(1, "--crawl-concurrency", min=1, max=8, help="MediaCrawler request concurrency. Keep 1 for conservative account risk."),
    headless: bool = typer.Option(False, "--headless/--headed"),
    crawl_sleep_seconds: float = typer.Option(5.0, "--crawl-sleep-seconds", min=0.0, max=120.0),
    crawl_min_sleep_seconds: Optional[float] = typer.Option(None, "--crawl-min-sleep-seconds", min=0.0, max=120.0),
    crawl_max_sleep_seconds: Optional[float] = typer.Option(None, "--crawl-max-sleep-seconds", min=0.0, max=120.0),
    crawl_long_pause_every: int = typer.Option(0, "--crawl-long-pause-every", min=0, max=1000),
    crawl_long_pause_min_seconds: float = typer.Option(30.0, "--crawl-long-pause-min-seconds", min=0.0, max=3600.0),
    crawl_long_pause_max_seconds: float = typer.Option(90.0, "--crawl-long-pause-max-seconds", min=0.0, max=3600.0),
    summarize: bool = typer.Option(False, "--summarize/--metadata-only"),
    video_upload_backend: str = typer.Option(
        "auto",
        "--video-upload-backend",
        help=(
            "auto, oss, dashscope, or openai. auto first tries a real source video URL, "
            "then source-stream-to-OSS when OSS is enabled, then local upload/download paths."
        ),
    ),
    video_fps: float = typer.Option(2.0, "--video-fps", min=0.1, max=10.0),
    sample_frames: int = typer.Option(8, "--sample-frames", min=1, max=24),
    max_inline_video_mb: int = typer.Option(7, "--max-inline-video-mb", min=1, max=7),
    max_dashscope_video_mb: int = typer.Option(100, "--max-dashscope-video-mb", min=1, max=100),
    dashscope_retry_count: int = typer.Option(3, "--dashscope-retry-count", min=1, max=5),
    enable_video_compression: bool = typer.Option(True, "--compress-video/--no-compress-video"),
    compression_target_mb: int = typer.Option(64, "--compression-target-mb", min=10, max=100),
    enable_whisper_transcription: bool = typer.Option(False, "--whisper/--no-whisper"),
    whisper_model: str = typer.Option("turbo", "--whisper-model"),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    """Start a metadata, download, or download+summary video task."""

    source_mode = source_mode.strip()
    clean_query = query.strip()
    clean_creator_id = creator_id.strip() or clean_query
    search_keyword = clean_query if source_mode == "search" else ""
    if source_mode == "search":
        clean_creator_id = clean_query
    if source_mode == "ranking":
        clean_creator_id = clean_creator_id or f"ranking:{platform}:{ranking_type}"

    payload: Dict[str, Any] = {
        "platform": platform,
        "creator_id": clean_creator_id,
        "creator_display_name": creator_display_name,
        "profile_url": profile_url,
        "source_mode": source_mode,
        "search_keyword": search_keyword,
        "ranking_type": ranking_type,
        "ranking_limit": ranking_limit,
        "credential_profile_id": credential_profile_id or None,
        "workflow_mode": workflow_mode,
        "source_task_id": source_task_id or None,
        "selected_item_ids": _split_ids(selected_item_id, selected_items),
        "login_type": login_type,
        "cookies": _read_text(cookies, cookies_file),
        "start_date": start_date,
        "end_date": end_date,
        "max_videos": max_videos,
        "crawl_concurrency": crawl_concurrency,
        "headless": headless,
        "crawl_sleep_seconds": crawl_sleep_seconds,
        "crawl_min_sleep_seconds": crawl_min_sleep_seconds,
        "crawl_max_sleep_seconds": crawl_max_sleep_seconds,
        "crawl_long_pause_every": crawl_long_pause_every,
        "crawl_long_pause_min_seconds": crawl_long_pause_min_seconds,
        "crawl_long_pause_max_seconds": crawl_long_pause_max_seconds,
        "summarize": summarize,
        "video_input_mode": "auto",
        "video_upload_backend": video_upload_backend,
        "video_fps": video_fps,
        "sample_frames": sample_frames,
        "max_inline_video_mb": max_inline_video_mb,
        "max_dashscope_video_mb": max_dashscope_video_mb,
        "dashscope_retry_count": dashscope_retry_count,
        "enable_video_compression": enable_video_compression,
        "compression_target_mb": compression_target_mb,
        "enable_whisper_transcription": enable_whisper_transcription,
        "whisper_model": whisper_model,
    }
    data = _request("POST", api_base, "/video-summary/tasks/start", payload=payload)
    _print_json(data)


@tasks_app.command("ranking-options")
def ranking_options(
    platform: str = typer.Option("", "--platform", "-p", help="Optional platform filter: xhs, dy, ks, bili, wb, tieba, zhihu."),
) -> None:
    """List ranking types supported by the CLI and backend."""

    clean_platform = platform.strip()
    if clean_platform:
        if clean_platform not in SUPPORTED_RANKINGS:
            raise typer.BadParameter(f"Unknown platform: {clean_platform}")
        data: Dict[str, Any] = {"platform": clean_platform, "options": SUPPORTED_RANKINGS[clean_platform]}
    else:
        data = {"platforms": SUPPORTED_RANKINGS}
    _print_json(data)


@tasks_app.command("status")
def task_status(
    task_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("GET", api_base, f"/video-summary/tasks/{task_id}"))


@tasks_app.command("wait")
def wait_task(
    task_id: str = typer.Argument(...),
    interval: float = typer.Option(2.0, "--interval", min=0.5),
    timeout: float = typer.Option(0.0, "--timeout", help="Seconds. 0 means no timeout."),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    started = time.monotonic()
    while True:
        data = _request("GET", api_base, f"/video-summary/tasks/{task_id}")
        status = data.get("status")
        _echo_text(f"{status}: {data.get('progress_message') or ''}")
        if status in {"completed", "error"}:
            _print_json(data)
            return
        if timeout and time.monotonic() - started >= timeout:
            raise typer.Exit(1)
        time.sleep(interval)


@tasks_app.command("stop")
def stop_task(
    task_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("POST", api_base, f"/video-summary/tasks/{task_id}/stop"))


@credentials_app.command("list")
def list_credentials(api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base")) -> None:
    _print_json(_request("GET", api_base, "/video-summary/platform-credentials"))


@credentials_app.command("show")
def show_credential(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("GET", api_base, f"/video-summary/platform-credentials/{profile_id}/secret"))


@credentials_app.command("create")
def create_credential(
    platform: str = typer.Option("bili", "--platform", "-p"),
    name: str = typer.Option("Default cookies", "--name", "-n"),
    cookies: str = typer.Option("", "--cookies"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies-file"),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    payload = {
        "platform": platform,
        "name": name,
        "cookies": _read_text(cookies, cookies_file),
        "login_method": "cookie",
        "metadata": {},
    }
    _print_json(_request("POST", api_base, "/video-summary/platform-credentials", payload=payload))


@credentials_app.command("update")
def update_credential(
    profile_id: str = typer.Argument(...),
    platform: str = typer.Option("bili", "--platform", "-p"),
    name: str = typer.Option("Default cookies", "--name", "-n"),
    cookies: str = typer.Option("", "--cookies"),
    cookies_file: Optional[Path] = typer.Option(None, "--cookies-file"),
    clear_cookies: bool = typer.Option(False, "--clear-cookies"),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    payload = {
        "platform": platform,
        "name": name,
        "cookies": _read_text(cookies, cookies_file) or None,
        "clear_cookies": clear_cookies,
        "login_method": "cookie",
        "metadata": {},
    }
    _print_json(_request("PUT", api_base, f"/video-summary/platform-credentials/{profile_id}", payload=payload))


@credentials_app.command("activate")
def activate_credential(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("POST", api_base, f"/video-summary/platform-credentials/{profile_id}/activate"))


@credentials_app.command("delete")
def delete_credential(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("DELETE", api_base, f"/video-summary/platform-credentials/{profile_id}"))


@credentials_app.command("qrcode-login")
def qrcode_login(
    platform: str = typer.Option("bili", "--platform", "-p"),
    name: str = typer.Option("扫码登录信息", "--name", "-n"),
    profile_id: str = typer.Option("", "--profile-id", help="Update an existing credential profile. Empty creates a new profile."),
    headless: bool = typer.Option(False, "--headless/--headed", help="Headless QR login only works when the platform login flow can expose a scannable QR image."),
    wait: bool = typer.Option(True, "--wait/--no-wait", help="Poll until the QR-code login task finishes."),
    interval: float = typer.Option(2.0, "--interval", min=0.5),
    timeout: float = typer.Option(0.0, "--timeout", help="Seconds. 0 means no timeout."),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    """Start original MediaCrawler QR-code login and save cookies/profile metadata."""

    payload = {
        "platform": platform,
        "name": name,
        "profile_id": profile_id or None,
        "headless": headless,
    }
    data = _request("POST", api_base, "/video-summary/platform-credentials/qrcode-login/start", payload=payload)
    task_id = str(data.get("task_id") or "")
    _print_json(data)
    if wait and task_id:
        _wait_qrcode_login(task_id, interval, timeout, api_base)


@credentials_app.command("qrcode-status")
def qrcode_status(
    task_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("GET", api_base, f"/video-summary/platform-credentials/qrcode-login/{task_id}"))


@credentials_app.command("qrcode-wait")
def wait_qrcode_login(
    task_id: str = typer.Argument(...),
    interval: float = typer.Option(2.0, "--interval", min=0.5),
    timeout: float = typer.Option(0.0, "--timeout", help="Seconds. 0 means no timeout."),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _wait_qrcode_login(task_id, interval, timeout, api_base)


def _wait_qrcode_login(task_id: str, interval: float, timeout: float, api_base: str) -> None:
    started = time.monotonic()
    while True:
        data = _request("GET", api_base, f"/video-summary/platform-credentials/qrcode-login/{task_id}")
        status = data.get("status")
        typer.echo(f"{status}: {data.get('progress_message') or ''}")
        if status in {"completed", "error"}:
            _print_json(data)
            return
        if timeout and time.monotonic() - started >= timeout:
            raise typer.Exit(1)
        time.sleep(interval)


@qwen_app.command("list")
def list_qwen(api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base")) -> None:
    _print_json(_request("GET", api_base, "/video-summary/settings/profiles"))


@qwen_app.command("show")
def show_qwen(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("GET", api_base, f"/video-summary/settings/profiles/{profile_id}/secret"))


@qwen_app.command("create")
def create_qwen(
    name: str = typer.Option("Default Qwen", "--name", "-n"),
    api_key: str = typer.Option("", "--api-key"),
    api_key_file: Optional[Path] = typer.Option(None, "--api-key-file"),
    api_provider: str = typer.Option("dashscope", "--api-provider", help="dashscope or openai_compatible."),
    base_url: str = typer.Option("https://dashscope.aliyuncs.com/compatible-mode/v1", "--base-url"),
    model: str = typer.Option("qwen3.5-omni-plus", "--model"),
    oss_enabled: bool = typer.Option(False, "--oss-enabled/--no-oss-enabled", help="Upload local videos to OSS and pass signed URLs to Qwen."),
    oss_access_key_id: str = typer.Option("", "--oss-access-key-id"),
    oss_access_key_id_file: Optional[Path] = typer.Option(None, "--oss-access-key-id-file"),
    oss_access_key_secret: str = typer.Option("", "--oss-access-key-secret"),
    oss_access_key_secret_file: Optional[Path] = typer.Option(None, "--oss-access-key-secret-file"),
    oss_bucket: str = typer.Option("", "--oss-bucket"),
    oss_endpoint: str = typer.Option("", "--oss-endpoint", help="Example: oss-cn-beijing.aliyuncs.com"),
    oss_region: str = typer.Option("", "--oss-region", help="Example: cn-beijing"),
    oss_prefix: str = typer.Option("mediacrawler/video-summary", "--oss-prefix"),
    oss_url_expires_seconds: int = typer.Option(7200, "--oss-url-expires-seconds", min=300, max=604800),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    payload = {
        "name": name,
        "api_key": _read_text(api_key, api_key_file) or None,
        "api_provider": api_provider,
        "base_url": base_url,
        "model": model,
        "oss_enabled": oss_enabled,
        "oss_access_key_id": _read_text(oss_access_key_id, oss_access_key_id_file) or None,
        "oss_access_key_secret": _read_text(oss_access_key_secret, oss_access_key_secret_file) or None,
        "oss_bucket": oss_bucket,
        "oss_endpoint": oss_endpoint,
        "oss_region": oss_region,
        "oss_prefix": oss_prefix,
        "oss_url_expires_seconds": oss_url_expires_seconds,
    }
    _print_json(_request("POST", api_base, "/video-summary/settings/profiles", payload=payload))


@qwen_app.command("update")
def update_qwen(
    profile_id: str = typer.Argument(...),
    name: str = typer.Option("Default Qwen", "--name", "-n"),
    api_key: str = typer.Option("", "--api-key"),
    api_key_file: Optional[Path] = typer.Option(None, "--api-key-file"),
    clear_api_key: bool = typer.Option(False, "--clear-api-key"),
    api_provider: str = typer.Option("dashscope", "--api-provider", help="dashscope or openai_compatible."),
    base_url: str = typer.Option("https://dashscope.aliyuncs.com/compatible-mode/v1", "--base-url"),
    model: str = typer.Option("qwen3.5-omni-plus", "--model"),
    oss_enabled: bool = typer.Option(False, "--oss-enabled/--no-oss-enabled", help="Upload local videos to OSS and pass signed URLs to Qwen."),
    oss_access_key_id: str = typer.Option("", "--oss-access-key-id"),
    oss_access_key_id_file: Optional[Path] = typer.Option(None, "--oss-access-key-id-file"),
    oss_access_key_secret: str = typer.Option("", "--oss-access-key-secret"),
    oss_access_key_secret_file: Optional[Path] = typer.Option(None, "--oss-access-key-secret-file"),
    clear_oss_access_key: bool = typer.Option(False, "--clear-oss-access-key"),
    oss_bucket: str = typer.Option("", "--oss-bucket"),
    oss_endpoint: str = typer.Option("", "--oss-endpoint", help="Example: oss-cn-beijing.aliyuncs.com"),
    oss_region: str = typer.Option("", "--oss-region", help="Example: cn-beijing"),
    oss_prefix: str = typer.Option("mediacrawler/video-summary", "--oss-prefix"),
    oss_url_expires_seconds: int = typer.Option(7200, "--oss-url-expires-seconds", min=300, max=604800),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    payload = {
        "name": name,
        "api_key": _read_text(api_key, api_key_file) or None,
        "clear_api_key": clear_api_key,
        "api_provider": api_provider,
        "base_url": base_url,
        "model": model,
        "oss_enabled": oss_enabled,
        "oss_access_key_id": _read_text(oss_access_key_id, oss_access_key_id_file) or None,
        "oss_access_key_secret": _read_text(oss_access_key_secret, oss_access_key_secret_file) or None,
        "clear_oss_access_key": clear_oss_access_key,
        "oss_bucket": oss_bucket,
        "oss_endpoint": oss_endpoint,
        "oss_region": oss_region,
        "oss_prefix": oss_prefix,
        "oss_url_expires_seconds": oss_url_expires_seconds,
    }
    _print_json(_request("PUT", api_base, f"/video-summary/settings/profiles/{profile_id}", payload=payload))


@qwen_app.command("activate")
def activate_qwen(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("POST", api_base, f"/video-summary/settings/profiles/{profile_id}/activate"))


@qwen_app.command("delete")
def delete_qwen(
    profile_id: str = typer.Argument(...),
    api_base: str = typer.Option(DEFAULT_API_BASE, "--api-base"),
) -> None:
    _print_json(_request("DELETE", api_base, f"/video-summary/settings/profiles/{profile_id}"))


app.add_typer(creators_app, name="creators")
app.add_typer(tasks_app, name="tasks")
app.add_typer(credentials_app, name="credentials")
app.add_typer(qwen_app, name="qwen")


if __name__ == "__main__":
    app()
