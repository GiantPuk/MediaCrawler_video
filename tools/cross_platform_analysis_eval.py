from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = PROJECT_ROOT / "data" / "video_tasks"
OUT_DIR = TASK_ROOT / "analysis_eval"
API_BASE = "http://127.0.0.1:8080/api"


@dataclass
class PlatformCase:
    platform: str
    query: str
    search_keyword: str
    credential_profile_id: str = ""
    source_mode: str = "search"
    max_videos: int = 1


CASES = [
    PlatformCase("bili", "三角洲行动", "三角洲行动"),
    PlatformCase("dy", "白海豚", "白海豚"),
    PlatformCase("xhs", "三角洲行动", "三角洲行动"),
    PlatformCase("ks", "三角洲行动", "三角洲行动"),
    PlatformCase("wb", "三角洲行动", "三角洲行动"),
    PlatformCase("zhihu", "人工智能", "人工智能"),
]


def now_ms() -> int:
    return int(time.time() * 1000)


def request_json(client: httpx.Client, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    response = client.request(method, f"{API_BASE}{path}", **kwargs)
    response.raise_for_status()
    return response.json()


def wait_task(client: httpx.Client, task_id: str, timeout_s: int = 900) -> Dict[str, Any]:
    deadline = time.time() + timeout_s
    last = ""
    transient_errors = 0
    while time.time() < deadline:
        try:
            status = request_json(client, "GET", f"/video-summary/tasks/{task_id}")
            transient_errors = 0
        except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout) as exc:
            transient_errors += 1
            if transient_errors > 8:
                raise
            print(f"[{task_id}] transient poll error {transient_errors}: {type(exc).__name__}", flush=True)
            time.sleep(5)
            continue
        line = f"{status.get('status')} | {status.get('progress_message')}"
        if line != last:
            print(f"[{task_id}] {line}", flush=True)
            last = line
        if status.get("status") in {"completed", "error"}:
            return status
        time.sleep(5)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout_s}s")


def task_payload(case: PlatformCase, *, workflow_mode: str, source_task_id: str = "", selected_item_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "platform": case.platform,
        "creator_id": case.query,
        "creator_display_name": f"{case.platform}:{case.query}",
        "profile_url": "",
        "source_mode": case.source_mode,
        "search_keyword": case.search_keyword,
        "ranking_type": "",
        "ranking_limit": 1,
        "credential_profile_id": case.credential_profile_id or None,
        "workflow_mode": workflow_mode,
        "source_task_id": source_task_id or None,
        "selected_item_ids": selected_item_ids or [],
        "login_type": "cookie",
        "cookies": "",
        "start_date": "2026-07-01",
        "end_date": "2026-08-08",
        "max_videos": case.max_videos,
        "crawl_concurrency": 1,
        "headless": True,
        "crawl_sleep_seconds": 8,
        "crawl_min_sleep_seconds": 8,
        "crawl_max_sleep_seconds": 15,
        "crawl_long_pause_every": 0,
        "crawl_long_pause_min_seconds": 30,
        "crawl_long_pause_max_seconds": 90,
        "summarize": False,
        "video_input_mode": "auto",
        "video_upload_backend": "dashscope",
        "video_fps": 0.5,
        "sample_frames": 4,
        "max_inline_video_mb": 7,
        "max_dashscope_video_mb": 100,
        "dashscope_retry_count": 2,
        "enable_video_compression": True,
        "compression_target_mb": 20,
        "enable_whisper_transcription": False,
        "whisper_model": "turbo",
    }


def item_aliases(item: Dict[str, Any]) -> List[str]:
    raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
    values = [
        item.get("id"),
        raw.get("aid"),
        raw.get("bvid"),
        raw.get("video_id"),
        raw.get("aweme_id"),
        raw.get("note_id"),
        raw.get("content_id"),
    ]
    return [str(value) for value in values if value]


def choose_item(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for item in items:
        raw = item.get("raw") if isinstance(item.get("raw"), dict) else {}
        if item.get("video_path"):
            return item
        if any(raw.get(key) for key in ("video_download_url", "video_play_url", "download_url", "play_url", "media_url")):
            return item
    return items[0] if items else None


def get_active_qwen_secret(client: httpx.Client) -> Dict[str, Any]:
    profiles = request_json(client, "GET", "/video-summary/settings/profiles")
    active = profiles["active_profile_id"]
    return request_json(client, "GET", f"/video-summary/settings/profiles/{active}/secret")


def compatible_base_url(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/api/v1"):
        return f"{base_url[:-len('/api/v1')]}/compatible-mode/v1"
    if base_url == "https://dashscope.aliyuncs.com":
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"
    return base_url


def probe_duration(video_path: Path) -> Optional[float]:
    try:
        output = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        ).strip()
        value = float(output)
        return value if value > 0 else None
    except Exception:
        return None


def compress_for_inline(video_path: Path, case_id: str, target_mb: int = 6) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"{case_id}_{target_mb}mb.mp4"
    if output_path.exists() and 0 < output_path.stat().st_size <= target_mb * 1024 * 1024:
        return output_path

    duration = probe_duration(video_path) or 120
    audio_kbps = 32
    usable_bits = target_mb * 1024 * 1024 * 8 * 0.88
    video_kbps = max(90, int(usable_bits / duration / 1000) - audio_kbps)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        "scale=w='min(854,iw)':h='min(480,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        f"{video_kbps}k",
        "-maxrate",
        f"{int(video_kbps * 1.25)}k",
        "-bufsize",
        f"{int(video_kbps * 2.5)}k",
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
    subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
    if output_path.stat().st_size > 7 * 1024 * 1024:
        raise RuntimeError(f"Compressed video still too large for inline upload: {output_path.stat().st_size}")
    return output_path


def wav_to_float32(audio_path: Path) -> Any:
    import numpy as np

    with wave.open(str(audio_path), "rb") as wav_file:
        channels = int(wav_file.getnchannels())
        sample_rate = int(wav_file.getframerate())
        raw_audio = wav_file.readframes(wav_file.getnframes())
    if sample_rate != 16000:
        raise RuntimeError(f"Unexpected Whisper wav sample rate: {sample_rate}")
    audio = np.frombuffer(raw_audio, np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio


def transcribe_whisper(video_path: Path, case_id: str) -> Tuple[str, float]:
    import torch
    import whisper

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = OUT_DIR / f"{case_id}.wav"
    if not audio_path.exists() or audio_path.stat().st_size <= 0:
        subprocess.run(
            [
                "ffmpeg",
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
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    start = time.perf_counter()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = whisper.load_model("turbo", device=device)
    result = model.transcribe(wav_to_float32(audio_path), fp16=(device == "cuda"))
    lines: List[str] = []
    if isinstance(result, dict) and isinstance(result.get("segments"), list):
        for segment in result["segments"]:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            lines.append(f"[{fmt_time(float(segment.get('start') or 0))}-{fmt_time(float(segment.get('end') or 0))}] {text}")
    elif isinstance(result, dict):
        lines.append(str(result.get("text") or "").strip())
    transcript = "\n".join(line for line in lines if line)
    return transcript, time.perf_counter() - start


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def call_chat_model(
    *,
    api_key: str,
    base_url: str,
    model: str,
    video_path: Path,
    prompt: str,
    transcript: str = "",
    timeout_s: int = 240,
) -> Tuple[str, float]:
    encoded = base64.b64encode(video_path.read_bytes()).decode("ascii")
    text = prompt
    if transcript:
        text += "\n\n下面是本地 Whisper 生成的带时间戳转录，只能作为辅助证据，画面冲突时以画面为准：\n" + transcript[:12000]
    content = [
        {"type": "text", "text": text},
        {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{encoded}"}, "fps": 0.5},
    ]
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
    }
    start = time.perf_counter()
    with httpx.Client(timeout=timeout_s, trust_env=False) as client:
        response = client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    elapsed = time.perf_counter() - start
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"]), elapsed


def main() -> None:
    os.environ["PYTHONIOENCODING"] = "utf-8"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = (
        "你是视频理解评测助手。请必须使用中文回答。输出四节："
        "1）一句话概括；2）时间线摘要，按视频顺序使用 [MM:SS-MM:SS]；"
        "3）关键画面/声音/文字信息；4）可信度与不确定点。"
        "不要编造看不到或听不到的内容。"
    )
    results: List[Dict[str, Any]] = []
    with httpx.Client(timeout=60, trust_env=False) as client:
        qwen = get_active_qwen_secret(client)
        api_key = qwen["api_key"]
        base_url = compatible_base_url(qwen["base_url"])

        for case in CASES:
            print(f"\n=== PLATFORM {case.platform} metadata ===", flush=True)
            row: Dict[str, Any] = {"platform": case.platform, "query": case.query}
            metadata_start = time.perf_counter()
            try:
                start_resp = request_json(client, "POST", "/video-summary/tasks/start", json=task_payload(case, workflow_mode="metadata_only"))
                metadata_status = wait_task(client, start_resp["task_id"], timeout_s=900)
                row["metadata_task_id"] = start_resp["task_id"]
                row["metadata_elapsed_s"] = round(time.perf_counter() - metadata_start, 2)
                row["metadata_status"] = metadata_status.get("status")
                items = ((metadata_status.get("result") or {}).get("items") or [])
                row["metadata_item_count"] = len(items)
                item = choose_item(items)
                if not item:
                    row["sample_status"] = "no_candidate"
                    results.append(row)
                    continue
                row["item_id"] = item.get("id")
                row["title"] = item.get("title")
                aliases = item_aliases(item)
                selected_id = aliases[0] if aliases else str(item.get("id"))

                print(f"=== PLATFORM {case.platform} download {selected_id} ===", flush=True)
                download_start = time.perf_counter()
                download_payload = task_payload(
                    case,
                    workflow_mode="selected_items",
                    source_task_id=start_resp["task_id"],
                    selected_item_ids=[selected_id],
                )
                download_resp = request_json(client, "POST", "/video-summary/tasks/start", json=download_payload)
                download_status = wait_task(client, download_resp["task_id"], timeout_s=900)
                row["download_task_id"] = download_resp["task_id"]
                row["download_elapsed_s"] = round(time.perf_counter() - download_start, 2)
                row["download_status"] = download_status.get("status")
                d_item = (((download_status.get("result") or {}).get("items") or [{}])[0])
                row["download_item_status"] = d_item.get("download_status")
                row["download_item_error"] = d_item.get("error")
                video_path_text = d_item.get("video_path")
                if not video_path_text or not Path(video_path_text).exists():
                    row["sample_status"] = "download_unavailable"
                    row["logs_tail"] = (download_status.get("logs") or [])[-8:]
                    results.append(row)
                    continue

                source_video = Path(video_path_text)
                row["source_video_path"] = str(source_video)
                row["source_video_mb"] = round(source_video.stat().st_size / 1024 / 1024, 2)
                row["source_duration_s"] = round(probe_duration(source_video) or 0, 2)
                inline_video = compress_for_inline(source_video, f"{case.platform}_{uuid.uuid4().hex[:8]}", target_mb=6)
                row["inline_video_path"] = str(inline_video)
                row["inline_video_mb"] = round(inline_video.stat().st_size / 1024 / 1024, 2)

                row["models"] = []
                for label, model, use_whisper in [
                    ("qwen_vl", "qwen-vl-max", False),
                    ("qwen_vl_whisper", "qwen-vl-max", True),
                    ("qwen_omni", "qwen3.5-omni-plus", False),
                ]:
                    print(f"=== {case.platform} {label} ===", flush=True)
                    model_row: Dict[str, Any] = {"label": label, "model": model}
                    try:
                        transcript = ""
                        if use_whisper:
                            transcript, whisper_s = transcribe_whisper(source_video, f"{case.platform}_{row['item_id']}")
                            model_row["whisper_elapsed_s"] = round(whisper_s, 2)
                            model_row["transcript_chars"] = len(transcript)
                        summary, model_s = call_chat_model(
                            api_key=api_key,
                            base_url=base_url,
                            model=model,
                            video_path=inline_video,
                            prompt=prompt,
                            transcript=transcript,
                        )
                        model_row["status"] = "completed"
                        model_row["model_elapsed_s"] = round(model_s, 2)
                        model_row["total_elapsed_s"] = round(model_s + model_row.get("whisper_elapsed_s", 0), 2)
                        model_row["summary_chars"] = len(summary)
                        model_row["summary"] = summary
                        model_row["summary_head"] = summary[:800]
                    except Exception as exc:
                        model_row["status"] = "failed"
                        model_row["error"] = f"{type(exc).__name__}: {exc}"
                    row["models"].append(model_row)
            except Exception as exc:
                row["sample_status"] = "failed"
                row["error"] = f"{type(exc).__name__}: {exc}"
            results.append(row)
            out_path = OUT_DIR / "cross_platform_analysis_eval_latest.json"
            out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    out_path = OUT_DIR / f"cross_platform_analysis_eval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
