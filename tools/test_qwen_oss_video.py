from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.schemas.crawler import PlatformEnum
from api.schemas.video_summary import VideoSummaryItem, VideoSummaryTaskRequest
from api.services.video_summary_manager import TASK_ROOT, VideoSummaryManager, VideoTask


DEFAULT_MODELS = ["qwen-vl-max", "qwen3.5-omni-plus"]


def _find_largest_video() -> Path:
    candidates = sorted(TASK_ROOT.rglob("*.mp4"), key=lambda path: path.stat().st_size if path.exists() else 0, reverse=True)
    if not candidates:
        raise RuntimeError(f"No mp4 file found under {TASK_ROOT}")
    return candidates[0]


def _build_task(video_path: Path) -> tuple[VideoTask, VideoSummaryItem]:
    task_id = f"osscheck_{uuid.uuid4().hex[:8]}"
    request = VideoSummaryTaskRequest(
        platform=PlatformEnum.BILIBILI,
        creator_id="oss-check",
        source_mode="search",
        search_keyword="oss-check",
        start_date=date.today(),
        end_date=date.today(),
        max_videos=1,
        crawl_concurrency=1,
        login_type="cookie",
        cookies="",
        headless=True,
        summarize=True,
        video_upload_backend="oss",
        enable_whisper_transcription=False,
    )
    task_dir = TASK_ROOT / task_id
    task = VideoTask(
        task_id=task_id,
        request=request,
        task_dir=task_dir,
        raw_data_dir=task_dir / "raw",
    )
    item = VideoSummaryItem(
        id=video_path.parent.name or video_path.stem,
        title="OSS public URL large video test",
        desc="Local large video uploaded to OSS and passed to Qwen by signed URL.",
        url="",
        video_path=str(video_path),
        download_status="existing",
        raw={},
    )
    return task, item


async def _run_model(
    manager: VideoSummaryManager,
    base_settings: Dict[str, Any],
    video_path: Path,
    model: str,
    prompt: str,
    fps: float,
) -> Dict[str, Any]:
    task, item = _build_task(video_path)
    settings = dict(base_settings)
    settings["model"] = model
    settings["video_upload_backend"] = "oss"
    settings["video_fps"] = fps
    started = time.perf_counter()
    result: Dict[str, Any] = {
        "model": model,
        "ok": False,
        "elapsed_seconds": None,
        "analysis_mode": None,
        "error": "",
        "summary_preview": "",
    }
    try:
        summary, mode = await manager._call_qwen_direct_video_summary(
            task,
            settings,
            item,
            video_path,
            [("测试说明", prompt)],
        )
        result.update(
            {
                "ok": True,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "analysis_mode": mode,
                "summary_preview": summary[:500],
            }
        )
    except Exception as exc:
        result.update(
            {
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    return result


async def _run_model_with_oss_object(
    manager: VideoSummaryManager,
    base_settings: Dict[str, Any],
    object_key: str,
    model: str,
    prompt: str,
    fps: float,
) -> Dict[str, Any]:
    settings = dict(base_settings)
    settings["model"] = model
    settings["video_fps"] = fps
    try:
        import oss2  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("oss2 package is not installed.") from exc

    endpoint = manager._normalize_oss_endpoint(str(settings.get("oss_endpoint") or ""))
    bucket_name = str(settings.get("oss_bucket") or "")
    expires = int(settings.get("oss_url_expires_seconds") or 7200)
    auth = oss2.Auth(str(settings["oss_access_key_id"]), str(settings["oss_access_key_secret"]))
    bucket = oss2.Bucket(auth, endpoint, bucket_name)
    signed_url = bucket.sign_url("GET", object_key, expires)
    content = [
        {"type": "text", "text": prompt},
        {"type": "video_url", "video_url": {"url": signed_url}, "fps": fps},
    ]
    started = time.perf_counter()
    result: Dict[str, Any] = {
        "model": model,
        "ok": False,
        "elapsed_seconds": None,
        "analysis_mode": "oss_video",
        "error": "",
        "summary_preview": "",
    }
    try:
        summary = await manager._call_qwen(settings, content)
        result.update(
            {
                "ok": True,
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "summary_preview": summary[:500],
            }
        )
    except Exception as exc:
        result.update(
            {
                "elapsed_seconds": round(time.perf_counter() - started, 2),
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    return result


async def main() -> None:
    parser = argparse.ArgumentParser(description="Test OSS signed-URL video upload with Qwen-VL and Qwen-Omni.")
    parser.add_argument("--video", type=Path, default=None, help="Local video path. Defaults to the largest mp4 under data/video_tasks.")
    parser.add_argument("--model", action="append", dest="models", help="Model to test. Repeatable. Defaults to qwen-vl-max and qwen3.5-omni-plus.")
    parser.add_argument("--fps", type=float, default=0.5, help="Video sampling fps passed to Qwen.")
    parser.add_argument("--oss-object", default="", help="Existing OSS object key to reuse instead of uploading the local video.")
    parser.add_argument("--upload-only", action="store_true", help="Only upload the video to OSS and verify the signed URL, without calling Qwen.")
    args = parser.parse_args()

    video_path = args.video or _find_largest_video()
    video_path = video_path.resolve()
    if not video_path.exists():
        raise RuntimeError(f"Video does not exist: {video_path}")

    manager = VideoSummaryManager()
    settings = manager._load_settings(include_secret=True)
    checks = {
        "api_key_configured": bool(settings.get("api_key")),
        "oss_enabled": bool(settings.get("oss_enabled")),
        "oss_access_key_id_configured": bool(settings.get("oss_access_key_id")),
        "oss_access_key_secret_configured": bool(settings.get("oss_access_key_secret")),
        "oss_bucket": settings.get("oss_bucket") or "",
        "oss_endpoint": settings.get("oss_endpoint") or "",
    }
    if not checks["api_key_configured"]:
        raise RuntimeError("Active Qwen profile has no API key.")
    if not checks["oss_enabled"] or not checks["oss_access_key_id_configured"] or not checks["oss_access_key_secret_configured"]:
        raise RuntimeError(f"Active Qwen profile OSS credentials are incomplete: {checks}")

    size_mb = round(video_path.stat().st_size / (1024 * 1024), 2)
    if args.upload_only:
        if args.models:
            settings["model"] = args.models[0]
        task, item = _build_task(video_path)
        started = time.perf_counter()
        signed_url, object_key = manager._upload_video_to_oss(task, settings, item, video_path)
        upload_elapsed = round(time.perf_counter() - started, 2)
        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            response = await client.get(signed_url, headers={"Range": "bytes=0-0"})
        print(
            json.dumps(
                {
                    "ok": response.status_code in {200, 206},
                    "video": str(video_path),
                    "size_mb": size_mb,
                    "oss_bucket": checks["oss_bucket"],
                    "oss_endpoint": checks["oss_endpoint"],
                    "oss_object": object_key,
                    "upload_elapsed_seconds": upload_elapsed,
                    "signed_url_probe_status": response.status_code,
                    "signed_url_probe_content_range": response.headers.get("content-range"),
                    "signed_url_probe_content_type": response.headers.get("content-type"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    prompt = (
        "这是一次链路测试。请用中文简短回答：是否能读取该视频、你能看到/听到的主要内容、"
        "以及不要编造无法确认的信息。"
    )
    models: List[str] = args.models or DEFAULT_MODELS
    results = []
    for model in models:
        if args.oss_object:
            results.append(await _run_model_with_oss_object(manager, settings, args.oss_object, model, prompt, args.fps))
        else:
            results.append(await _run_model(manager, settings, video_path, model, prompt, args.fps))

    print(
        json.dumps(
            {
                "video": str(video_path),
                "size_mb": size_mb,
                "oss_bucket": checks["oss_bucket"],
                "oss_endpoint": checks["oss_endpoint"],
                "oss_object": args.oss_object or None,
                "fps": args.fps,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
