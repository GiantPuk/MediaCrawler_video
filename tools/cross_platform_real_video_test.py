# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.services.video_summary_manager import QWEN_SETTINGS_PATH


DEFAULT_API_BASE = "http://127.0.0.1:8080/api"
DEFAULT_MODELS = ["qwen3.5-omni-plus", "qwen-vl-max"]
DEFAULT_PLATFORMS = ["dy", "bili", "wb", "xhs", "ks"]
DIRECT_VIDEO_FIELDS = [
    "video_download_url",
    "video_play_url",
    "download_url",
    "play_url",
    "media_url",
    "video_url",
]
VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".flv")

SCENARIOS: Dict[str, List[Dict[str, Any]]] = {
    "dy": [
        {"label": "short", "query": "三角洲行动精彩操作"},
        {"label": "long", "query": "科普 完整版"},
    ],
    "bili": [
        {"label": "short", "query": "key725 三角洲行动"},
        {"label": "long", "query": "三角洲行动 攻略 12分钟"},
    ],
    "wb": [
        {"label": "short", "query": "三角洲行动 vlog"},
        {"label": "long", "query": "科普 完整版 视频"},
    ],
    "xhs": [
        {"label": "short", "query": "三角洲行动 视频"},
        {"label": "long", "query": "旅行 vlog 视频"},
    ],
    "ks": [
        {"label": "short", "query": "三角洲行动 精彩操作"},
        {"label": "long", "query": "科普 完整版"},
    ],
}


def api_request(method: str, api_base: str, path: str, *, payload: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
    url = f"{api_base.rstrip('/')}/{path.lstrip('/')}"
    response = requests.request(method, url, json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def wait_task(api_base: str, task_id: str, *, timeout_seconds: int, poll_seconds: float = 5.0) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_status = api_request("GET", api_base, f"/video-summary/tasks/{task_id}", timeout=30)
        status = last_status.get("status")
        if status in {"completed", "error"}:
            return last_status
        time.sleep(poll_seconds)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout_seconds}s; last status={last_status.get('status')}")


def timed_start_and_wait(api_base: str, payload: Dict[str, Any], timeout_seconds: int) -> Tuple[Dict[str, Any], float]:
    start = time.perf_counter()
    status = start_and_wait(api_base, payload, timeout_seconds=timeout_seconds)
    return status, elapsed_since(start)


def elapsed_since(start: float) -> float:
    return round(time.perf_counter() - start, 3)


def parse_task_elapsed_seconds(status: Dict[str, Any]) -> Optional[float]:
    started_at = parse_iso_datetime(str(status.get("started_at") or ""))
    completed_at = parse_iso_datetime(str(status.get("completed_at") or ""))
    if not started_at or not completed_at:
        return None
    return round((completed_at - started_at).total_seconds(), 3)


def parse_iso_datetime(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def log_seconds(log_line: str) -> Optional[int]:
    match = re.match(r"\[(\d{2}):(\d{2}):(\d{2})\]", log_line)
    if not match:
        return None
    hours, minutes, seconds = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def diff_log_seconds(start: Optional[int], end: Optional[int]) -> Optional[int]:
    if start is None or end is None:
        return None
    if end < start:
        end += 24 * 3600
    return end - start


def task_phase_metrics(status: Dict[str, Any]) -> Dict[str, Any]:
    logs = [str(line) for line in (status.get("logs") or [])]
    download_start: Optional[int] = None
    download_end: Optional[int] = None
    oss_start: Optional[int] = None
    oss_end: Optional[int] = None
    summary_end: Optional[int] = None
    for line in logs:
        second = log_seconds(line)
        if second is None:
            continue
        if download_start is None and (
            "Downloading direct video" in line
            or "Downloading Bili public" in line
            or "Matched video download command" in line
        ):
            download_start = second
        if (
            "Downloaded direct video" in line
            or "Native MediaCrawler detail download completed" in line
            or "save video" in line
        ):
            download_end = second
        if oss_start is None and "Uploading video" in line and "OSS bucket" in line:
            oss_start = second
        if "OSS upload completed" in line:
            oss_end = second
        if "Summarized video" in line:
            summary_end = second
    qwen_start = oss_end or download_end
    return {
        "task_elapsed_seconds": parse_task_elapsed_seconds(status),
        "download_log_seconds": diff_log_seconds(download_start, download_end),
        "oss_upload_log_seconds": diff_log_seconds(oss_start, oss_end),
        "qwen_after_upload_log_seconds": diff_log_seconds(qwen_start, summary_end),
    }


def compact_log_tail(logs: Iterable[Any], *, count: int = 15, max_chars: int = 1000) -> List[str]:
    compacted: List[str] = []
    for line in list(logs)[-count:]:
        text = str(line)
        if len(text) > max_chars:
            text = f"{text[:max_chars]}... <truncated {len(text) - max_chars} chars>"
        compacted.append(text)
    return compacted


def active_credentials(api_base: str) -> Dict[str, str]:
    try:
        data = api_request("GET", api_base, "/video-summary/platform-credentials", timeout=30)
    except Exception:
        return {}
    active = data.get("active_by_platform")
    return active if isinstance(active, dict) else {}


def credential_cookie(api_base: str, credential_id: str) -> str:
    if not credential_id:
        return ""
    try:
        data = api_request("GET", api_base, f"/video-summary/platform-credentials/{credential_id}/secret", timeout=30)
    except Exception:
        return ""
    return str(data.get("cookies") or "")


def set_active_qwen_model(model: str) -> None:
    data = json.loads(QWEN_SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    active_id = str(data.get("active_profile_id") or "")
    for profile in data.get("profiles", []):
        if str(profile.get("id")) == active_id:
            profile["model"] = model
            break
    QWEN_SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def active_qwen_model() -> str:
    data = json.loads(QWEN_SETTINGS_PATH.read_text(encoding="utf-8-sig"))
    active_id = str(data.get("active_profile_id") or "")
    for profile in data.get("profiles", []):
        if str(profile.get("id")) == active_id:
            return str(profile.get("model") or "")
    return ""


def task_payload(
    platform: str,
    *,
    source_mode: str,
    query: str = "",
    source_task_id: str = "",
    selected_item_id: str = "",
    credential_profile_id: str = "",
    summarize: bool = False,
    workflow_mode: str = "metadata_only",
    max_videos: int = 5,
    lookback_days: int = 900,
) -> Dict[str, Any]:
    today = date.today()
    start_date = today - timedelta(days=lookback_days)
    return {
        "platform": platform,
        "creator_id": query or f"test:{platform}",
        "creator_display_name": f"Test: {query}" if query else "",
        "source_mode": source_mode,
        "search_keyword": query if source_mode == "search" else "",
        "ranking_type": "",
        "ranking_limit": max_videos,
        "credential_profile_id": credential_profile_id or None,
        "workflow_mode": workflow_mode,
        "source_task_id": source_task_id or None,
        "selected_item_ids": [selected_item_id] if selected_item_id else [],
        "login_type": "cookie" if credential_profile_id else "qrcode",
        "cookies": "",
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "max_videos": max_videos,
        "crawl_concurrency": 1,
        "headless": True,
        "crawl_sleep_seconds": 16,
        "crawl_min_sleep_seconds": 8,
        "crawl_max_sleep_seconds": 16,
        "crawl_long_pause_every": 0,
        "crawl_long_pause_min_seconds": 30,
        "crawl_long_pause_max_seconds": 90,
        "summarize": summarize,
        "video_input_mode": "auto",
        "video_upload_backend": "oss",
        "video_fps": 0.5,
        "sample_frames": 8,
        "max_inline_video_mb": 7,
        "max_dashscope_video_mb": 100,
        "dashscope_retry_count": 1,
        "enable_video_compression": True,
        "compression_target_mb": 64,
        "enable_whisper_transcription": False,
        "whisper_model": "turbo",
    }


def duration_seconds(item: Dict[str, Any]) -> Optional[float]:
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    for source in (item, raw):
        for key in ("duration", "video_duration", "duration_sec", "duration_seconds"):
            value = source.get(key)
            parsed = parse_number(value)
            if parsed and parsed > 0:
                return parsed
        for key in ("duration_ms", "video_duration_ms"):
            value = source.get(key)
            parsed = parse_number(value)
            if parsed and parsed > 0:
                return parsed / 1000.0
    return None


def parse_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            parsed = parse_duration_text(value)
            if parsed is not None:
                return parsed
            return None
    return None


def parse_duration_text(value: str) -> Optional[float]:
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", text):
        parts = [int(part) for part in text.split(":")]
        if len(parts) == 2:
            return float(parts[0] * 60 + parts[1])
        return float(parts[0] * 3600 + parts[1] * 60 + parts[2])
    match = re.fullmatch(r"(?:(\d+(?:\.\d+)?)\s*分)?\s*(?:(\d+(?:\.\d+)?)\s*秒)?", text)
    if match and (match.group(1) or match.group(2)):
        minutes = float(match.group(1) or 0)
        seconds = float(match.group(2) or 0)
        return minutes * 60 + seconds
    return None


def choose_item(
    items: List[Dict[str, Any]],
    label: str,
    used_ids: Iterable[str],
    *,
    platform: str,
    cookies: str,
    max_probed_size_mb: float,
) -> Optional[Dict[str, Any]]:
    used = set(used_ids)
    candidates = [item for item in items if item.get("id") not in used and item.get("download_status") != "unsupported"]
    if not candidates:
        return None
    max_bytes = int(max_probed_size_mb * 1024 * 1024) if max_probed_size_mb > 0 else 0
    with_size = [(candidate_size_bytes(platform, item, cookies), item) for item in candidates]
    size_known = [(size, item) for size, item in with_size if size is not None and size > 0]
    size_allowed = [(size, item) for size, item in size_known if not max_bytes or size <= max_bytes]
    if label == "short" and size_allowed:
        return sorted(size_allowed, key=lambda pair: pair[0])[0][1]
    if label == "long" and size_allowed:
        return sorted(size_allowed, key=lambda pair: pair[0], reverse=True)[0][1]
    if size_known and max_bytes:
        return None
    with_duration = [(duration_seconds(item), item) for item in candidates]
    known = [(duration, item) for duration, item in with_duration if duration is not None]
    if label == "short" and known:
        return sorted(known, key=lambda pair: pair[0])[0][1]
    if label == "long" and known:
        return sorted(known, key=lambda pair: pair[0], reverse=True)[0][1]
    return candidates[0]


def annotate_candidate_sizes(platform: str, items: List[Dict[str, Any]], cookies: str, max_probed_size_mb: float) -> List[Dict[str, Any]]:
    annotated: List[Dict[str, Any]] = []
    max_bytes = int(max_probed_size_mb * 1024 * 1024) if max_probed_size_mb > 0 else 0
    for item in items:
        size = candidate_size_bytes(platform, item, cookies)
        annotated.append(
            {
                "id": str(item.get("id") or ""),
                "title": item.get("title"),
                "size_mb": round(size / (1024 * 1024), 2) if size else None,
                "over_size_limit": bool(size and max_bytes and size > max_bytes),
                "duration_seconds": duration_seconds(item),
            }
        )
    return annotated


def candidate_size_bytes(platform: str, item: Dict[str, Any], cookies: str) -> Optional[int]:
    if "_probe_size_bytes" in item:
        value = item.get("_probe_size_bytes")
        return int(value) if isinstance(value, int) and value > 0 else None
    size = probe_candidate_size_bytes(platform, item, cookies)
    item["_probe_size_bytes"] = size or 0
    return size


def probe_candidate_size_bytes(platform: str, item: Dict[str, Any], cookies: str) -> Optional[int]:
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    for url in extract_direct_video_urls(platform, raw):
        size = probe_remote_size_bytes(url, platform=platform, referer=str(item.get("url") or ""), cookies=cookies)
        if size:
            return size
    return None


def extract_direct_video_urls(platform: str, record: Dict[str, Any]) -> List[str]:
    if platform == "dy":
        aweme_type = str(record.get("aweme_type") or "").strip()
        video_download_url = str(record.get("video_download_url") or "").strip()
        music_download_url = str(record.get("music_download_url") or "").strip()
        if aweme_type == "68" or (video_download_url and music_download_url and video_download_url == music_download_url):
            return []
    urls: List[str] = []
    for field_name in DIRECT_VIDEO_FIELDS:
        raw_value = record.get(field_name)
        if not raw_value:
            continue
        for url in split_urls(raw_value):
            if not url.startswith(("http://", "https://")):
                continue
            if field_name == "video_url" and is_landing_page_url(platform, url):
                continue
            if field_name != "video_url" or looks_like_remote_video_url(url):
                urls.append(url)
    return list(dict.fromkeys(urls))


def split_urls(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in re.split(r"[,;\s]+", str(value)) if part.strip()]


def is_landing_page_url(platform: str, url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    landing_hosts = ["bilibili.com", "douyin.com", "kuaishou.com", "weibo.com", "zhihu.com", "tieba.baidu.com"]
    if any(host.endswith(item) for item in landing_hosts) and not path.endswith(VIDEO_EXTENSIONS):
        if platform == "xhs" and "sns-video" in host:
            return False
        return True
    return False


def looks_like_remote_video_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    host = parsed.netloc.lower()
    return (
        path.endswith(VIDEO_EXTENSIONS)
        or "video" in host
        or "mime_type=video" in url.lower()
        or "video_id" in url.lower()
    )


def probe_remote_size_bytes(url: str, *, platform: str, referer: str, cookies: str) -> Optional[int]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Range": "bytes=0-0",
    }
    if referer:
        headers["Referer"] = referer
    if cookies:
        headers["Cookie"] = cookies
    try:
        with requests.get(url, headers=headers, stream=True, timeout=(10, 20), allow_redirects=True) as response:
            if response.status_code not in {200, 206}:
                return None
            content_type = (response.headers.get("content-type") or "").lower()
            if content_type and not any(token in content_type for token in ("video", "octet-stream", "mp4", "mpegurl")):
                return None
            content_range = response.headers.get("content-range", "")
            match = re.search(r"/(\d+)$", content_range)
            if match:
                return int(match.group(1))
            content_length = response.headers.get("content-length")
            if content_length and content_length.isdigit():
                return int(content_length)
    except Exception:
        return None
    return None


def start_and_wait(api_base: str, payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
    started = api_request("POST", api_base, "/video-summary/tasks/start", payload=payload, timeout=60)
    task_id = str(started.get("task_id") or "")
    if not task_id:
        raise RuntimeError(f"Task start response had no task_id: {started}")
    return wait_task(api_base, task_id, timeout_seconds=timeout_seconds)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    run_start = time.perf_counter()
    platforms = args.platform or DEFAULT_PLATFORMS
    models = args.model or DEFAULT_MODELS
    credentials = active_credentials(args.api_base)
    original_model = active_qwen_model()
    report: Dict[str, Any] = {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "api_base": args.api_base,
        "platforms": platforms,
        "models": models,
        "original_active_model": original_model,
        "max_probed_size_mb": args.max_probed_size_mb,
        "results": [],
    }

    try:
        for platform in platforms:
            credential_id = credentials.get(platform, "")
            credential_cookies = credential_cookie(args.api_base, credential_id)
            used_item_ids: List[str] = []
            for scenario in SCENARIOS.get(platform, []):
                metadata_entry: Dict[str, Any] = {
                    "platform": platform,
                    "scenario": scenario["label"],
                    "query": scenario["query"],
                    "credential_profile_id": credential_id,
                }
                try:
                    metadata_status, metadata_wall_seconds = timed_start_and_wait(
                        args.api_base,
                        task_payload(
                            platform,
                            source_mode="search",
                            query=scenario["query"],
                            credential_profile_id=credential_id,
                            summarize=False,
                            workflow_mode="metadata_only",
                            max_videos=args.max_candidates,
                            lookback_days=args.lookback_days,
                        ),
                        timeout_seconds=args.metadata_timeout,
                    )
                    metadata_result = metadata_status.get("result") or {}
                    items = metadata_result.get("items") or []
                    metadata_entry.update(
                        {
                            "metadata_task_id": metadata_status.get("task_id"),
                            "metadata_status": metadata_status.get("status"),
                            "metadata_wall_seconds": metadata_wall_seconds,
                            "metadata_task_elapsed_seconds": parse_task_elapsed_seconds(metadata_status),
                            "candidate_count": len(items),
                            "candidate_probe": annotate_candidate_sizes(
                                platform,
                                items,
                                credential_cookies,
                                args.max_probed_size_mb,
                            ),
                        }
                    )
                    item = choose_item(
                        items,
                        scenario["label"],
                        used_item_ids,
                        platform=platform,
                        cookies=credential_cookies,
                        max_probed_size_mb=args.max_probed_size_mb,
                    )
                    if not item:
                        metadata_entry["error"] = "No selectable video candidate returned by metadata task."
                        report["results"].append(metadata_entry)
                        continue
                    item_id = str(item.get("id"))
                    used_item_ids.append(item_id)
                    metadata_entry["selected_item"] = {
                        "id": item_id,
                        "title": item.get("title"),
                        "duration_seconds": duration_seconds(item),
                        "size_mb": (
                            round(candidate_size_bytes(platform, item, credential_cookies) / (1024 * 1024), 2)
                            if candidate_size_bytes(platform, item, credential_cookies)
                            else None
                        ),
                        "url": item.get("url"),
                    }
                    report["results"].append(metadata_entry)

                    for model in models:
                        set_active_qwen_model(model)
                        analysis_entry: Dict[str, Any] = {
                            "platform": platform,
                            "scenario": scenario["label"],
                            "model": model,
                            "source_task_id": metadata_status.get("task_id"),
                            "selected_item_id": item_id,
                        }
                        try:
                            analysis_status, analysis_wall_seconds = timed_start_and_wait(
                                args.api_base,
                                task_payload(
                                    platform,
                                    source_mode="search",
                                    query=scenario["query"],
                                    source_task_id=str(metadata_status.get("task_id") or ""),
                                    selected_item_id=item_id,
                                    credential_profile_id=credential_id,
                                    summarize=True,
                                    workflow_mode="selected_items",
                                    max_videos=1,
                                    lookback_days=args.lookback_days,
                                ),
                                timeout_seconds=args.analysis_timeout,
                            )
                            result = analysis_status.get("result") or {}
                            result_items = result.get("items") or []
                            first = result_items[0] if result_items else {}
                            analysis_entry.update(
                                {
                                    "task_id": analysis_status.get("task_id"),
                                    "status": analysis_status.get("status"),
                                    "analysis_wall_seconds": analysis_wall_seconds,
                                    **task_phase_metrics(analysis_status),
                                    "download_status": first.get("download_status"),
                                    "summary_status": first.get("summary_status"),
                                    "analysis_mode": first.get("analysis_mode"),
                                    "video_path": first.get("video_path"),
                                    "error": first.get("error") or analysis_status.get("error_message"),
                                    "summary_chars": len(first.get("summary") or ""),
                                    "logs_tail": compact_log_tail(analysis_status.get("logs") or []),
                                }
                            )
                        except Exception as exc:
                            analysis_entry["error"] = f"{type(exc).__name__}: {exc}"
                        report["results"].append(analysis_entry)
                except Exception as exc:
                    metadata_entry["error"] = f"{type(exc).__name__}: {exc}"
                    report["results"].append(metadata_entry)
    finally:
        if original_model:
            set_active_qwen_model(original_model)
        report["ended_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        report["total_wall_seconds"] = elapsed_since(run_start)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real cross-platform metadata/download/analysis tests via the local backend API.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--platform", action="append", choices=DEFAULT_PLATFORMS)
    parser.add_argument("--model", action="append")
    parser.add_argument("--max-candidates", type=int, default=5)
    parser.add_argument("--lookback-days", type=int, default=900)
    parser.add_argument("--metadata-timeout", type=int, default=900)
    parser.add_argument("--analysis-timeout", type=int, default=1200)
    parser.add_argument("--max-probed-size-mb", type=float, default=300.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    report = run(args)
    output = Path(args.output) if args.output else Path("data/video_tasks/cross_platform_real_video_test") / f"{int(time.time())}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(output), "results": len(report["results"])}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
