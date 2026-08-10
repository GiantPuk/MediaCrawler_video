from __future__ import annotations

import json
import os
import subprocess
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from cross_platform_analysis_eval import (
    OUT_DIR,
    call_chat_model,
    compatible_base_url,
    fmt_time,
    get_active_qwen_secret,
    probe_duration,
    wav_to_float32,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = PROJECT_ROOT / "data" / "video_tasks"
TARGET_INLINE_MB = 6
QWEN_VL_MODEL = "qwen-vl-max"
QWEN_OMNI_MODEL = "qwen3.5-omni-plus"
WHISPER_MODEL = "turbo"
LATEST_RESULT_PATH = OUT_DIR / "model_compare_local_samples_latest.json"


SAMPLES = [
    {
        "platform": "bili",
        "task_id": "119f08623bad",
        "item_id": "117058729740078",
        "video_path": TASK_ROOT / "119f08623bad" / "raw" / "bili" / "videos" / "117058729740078" / "video.mp4",
        "fresh_extraction_note": "fresh metadata + fresh download in this run",
    },
    {
        "platform": "dy",
        "task_id": "6252bba3d69a",
        "item_id": "7671505270274542883",
        "video_path": TASK_ROOT / "6252bba3d69a" / "raw" / "douyin" / "videos" / "7671505270274542883" / "video.mp4",
        "fresh_extraction_note": "downloaded in this run from an existing real Douyin metadata task",
    },
    {
        "platform": "wb",
        "task_id": "1cc3dea948ac",
        "item_id": "5314023902938272",
        "video_path": TASK_ROOT / "1cc3dea948ac" / "raw" / "weibo" / "videos" / "5314023902938272" / "video.mp4",
        "fresh_extraction_note": "existing real Weibo downloadable sample reused",
    },
]


PROMPT_TEMPLATE = """请必须全程使用中文回答，不要使用英文。

你是视频理解评测助手。请基于视频本身进行总结，不要编造无法确认的内容。

视频平台：{platform}
视频标题：{title}
视频描述：{desc}

输出必须包含：
1. 一句话概括。
2. 时间线摘要：按视频顺序列出 [MM:SS-MM:SS]，每段说明该时间段真实发生了什么。
3. 画面证据：列出你看到的关键画面、字幕、人物、场景或界面。
4. 声音/语音证据：如果能获取声音或辅助转录，说明关键信息；如果不能确认，请说“不确定”。
5. 不确定点：明确哪些判断不够可靠。
"""


def load_item_metadata(task_id: str, item_id: str) -> Dict[str, Any]:
    result_path = TASK_ROOT / task_id / "result.json"
    if not result_path.exists():
        return {}
    data = json.loads(result_path.read_text(encoding="utf-8"))
    for item in data.get("items") or []:
        if str(item.get("id")) == str(item_id):
            return item
    return {}


def extract_audio(video_path: Path, case_id: str) -> Tuple[Path, float]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audio_path = OUT_DIR / f"{case_id}.wav"
    if audio_path.exists() and audio_path.stat().st_size > 0:
        return audio_path, 0.0
    start = time.perf_counter()
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
        timeout=900,
    )
    return audio_path, time.perf_counter() - start


def transcribe_with_cached_model(model: Any, video_path: Path, case_id: str) -> Tuple[str, float, int, float]:
    audio_path, extract_elapsed = extract_audio(video_path, case_id)
    start = time.perf_counter()
    result = model.transcribe(wav_to_float32(audio_path), fp16=True, language="zh", task="transcribe")
    elapsed = time.perf_counter() - start
    lines: List[str] = []
    if isinstance(result, dict) and isinstance(result.get("segments"), list):
        for segment in result["segments"]:
            text = str(segment.get("text") or "").strip()
            if not text:
                continue
            lines.append(f"[{fmt_time(float(segment.get('start') or 0))}-{fmt_time(float(segment.get('end') or 0))}] {text}")
    elif isinstance(result, dict):
        text = str(result.get("text") or "").strip()
        if text:
            lines.append(text)
    transcript = "\n".join(lines)
    return transcript, elapsed, len(lines), extract_elapsed


def make_inline_video(video_path: Path, platform: str, item_id: str) -> Tuple[Path, Optional[float]]:
    if video_path.stat().st_size <= TARGET_INLINE_MB * 1024 * 1024:
        return video_path, 0.0
    start = time.perf_counter()
    duration = probe_duration(video_path) or 120.0
    plans = [
        {"target_mb": TARGET_INLINE_MB, "width": 640, "height": 360, "audio_kbps": 16, "min_video_kbps": 30, "safety": 0.82},
        {"target_mb": 5, "width": 534, "height": 300, "audio_kbps": 12, "min_video_kbps": 22, "safety": 0.80},
        {"target_mb": 4, "width": 426, "height": 240, "audio_kbps": 10, "min_video_kbps": 18, "safety": 0.78},
    ]

    last_error = ""
    for plan in plans:
        target_mb = int(plan["target_mb"])
        audio_kbps = int(plan["audio_kbps"])
        usable_bits = target_mb * 1024 * 1024 * 8 * float(plan["safety"])
        video_kbps = max(int(plan["min_video_kbps"]), int(usable_bits / duration / 1000) - audio_kbps)
        output_path = OUT_DIR / f"compare_{platform}_{item_id}_{target_mb}mb_h{plan['height']}.mp4"
        if output_path.exists() and 0 < output_path.stat().st_size <= 7 * 1024 * 1024:
            return output_path, time.perf_counter() - start
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
            (
                f"scale=w='min({plan['width']},iw)':h='min({plan['height']},ih)':"
                "force_original_aspect_ratio=decrease:force_divisible_by=2"
            ),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            f"{video_kbps}k",
            "-maxrate",
            f"{int(video_kbps * 1.15)}k",
            "-bufsize",
            f"{int(video_kbps * 2.0)}k",
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
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1800,
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue
        size = output_path.stat().st_size
        if size <= 7 * 1024 * 1024:
            return output_path, time.perf_counter() - start
        last_error = f"{output_path.name} is {size} bytes"
    raise RuntimeError(f"Could not compress video under inline limit: {last_error}")


def write_latest(results: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LATEST_RESULT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")


def load_resume_models() -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    if not LATEST_RESULT_PATH.exists():
        return {}
    try:
        previous = json.loads(LATEST_RESULT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    resume: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for sample in previous.get("samples") or []:
        platform = str(sample.get("platform") or "")
        item_id = str(sample.get("item_id") or "")
        for model_row in sample.get("models") or []:
            label = str(model_row.get("label") or "")
            if model_row.get("status") == "completed" and label:
                copied = dict(model_row)
                copied["resumed_from_previous_run"] = True
                resume[(platform, item_id, label)] = copied
    return resume


def main() -> None:
    os.environ["PYTHONIOENCODING"] = "utf-8"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    resume_models = load_resume_models()
    run_id = time.strftime("%Y%m%d_%H%M%S")
    results: Dict[str, Any] = {
        "run_id": run_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "resumed_completed_model_count": len(resume_models),
        "target_inline_mb": TARGET_INLINE_MB,
        "models": {
            "qwen_vl": QWEN_VL_MODEL,
            "qwen_vl_whisper": QWEN_VL_MODEL,
            "qwen_omni": QWEN_OMNI_MODEL,
            "whisper": WHISPER_MODEL,
        },
        "runtime": {},
        "samples": [],
    }
    write_latest(results)

    import torch
    import whisper

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available; this evaluation requires torch CUDA for Whisper.")
    results["runtime"]["torch_cuda"] = True
    results["runtime"]["cuda_device"] = torch.cuda.get_device_name(0)

    with httpx.Client(timeout=60, trust_env=False) as client:
        qwen = get_active_qwen_secret(client)
    api_key = qwen["api_key"]
    base_url = compatible_base_url(qwen["base_url"])
    results["runtime"]["qwen_base_url"] = base_url
    results["runtime"]["active_profile_id"] = qwen.get("id") or qwen.get("profile_id")

    whisper_load_start = time.perf_counter()
    whisper_model = whisper.load_model(WHISPER_MODEL, device="cuda")
    results["runtime"]["whisper_model_load_s"] = round(time.perf_counter() - whisper_load_start, 2)
    write_latest(results)

    for sample in SAMPLES:
        row: Dict[str, Any] = dict(sample)
        row["video_path"] = str(sample["video_path"])
        row["status"] = "pending"
        row["models"] = []
        results["samples"].append(row)
        write_latest(results)

        video_path = Path(sample["video_path"])
        if not video_path.exists():
            row["status"] = "missing_video"
            write_latest(results)
            continue

        metadata = load_item_metadata(str(sample["task_id"]), str(sample["item_id"]))
        title = str(metadata.get("title") or "")
        desc = str(metadata.get("desc") or metadata.get("raw", {}).get("desc") or "")
        row["title"] = title
        row["desc"] = desc
        row["source_video_mb"] = round(video_path.stat().st_size / 1024 / 1024, 2)
        duration = probe_duration(video_path)
        row["duration_s"] = round(duration or 0, 2)
        row["status"] = "preparing_inline_video"
        write_latest(results)

        inline_path, compress_s = make_inline_video(video_path, str(sample["platform"]), str(sample["item_id"]))
        row["inline_video_path"] = str(inline_path)
        row["inline_video_mb"] = round(inline_path.stat().st_size / 1024 / 1024, 2)
        row["compression_elapsed_s"] = round(compress_s or 0.0, 2)
        prompt = PROMPT_TEMPLATE.format(platform=sample["platform"], title=title, desc=desc)

        row["status"] = "running_models"
        write_latest(results)

        for label, model_name, use_whisper in [
            ("qwen_vl", QWEN_VL_MODEL, False),
            ("qwen_vl_whisper", QWEN_VL_MODEL, True),
            ("qwen_omni", QWEN_OMNI_MODEL, False),
        ]:
            resume_key = (str(sample["platform"]), str(sample["item_id"]), label)
            if resume_key in resume_models:
                row["models"].append(resume_models[resume_key])
                write_latest(results)
                continue
            model_row: Dict[str, Any] = {
                "label": label,
                "model": model_name,
                "status": "running",
            }
            row["models"].append(model_row)
            write_latest(results)
            try:
                transcript = ""
                if use_whisper:
                    transcript, whisper_s, segment_count, audio_extract_s = transcribe_with_cached_model(
                        whisper_model,
                        video_path,
                        f"compare_{sample['platform']}_{sample['item_id']}",
                    )
                    model_row["audio_extract_elapsed_s"] = round(audio_extract_s, 2)
                    model_row["whisper_elapsed_s"] = round(whisper_s, 2)
                    model_row["whisper_segment_count"] = segment_count
                    model_row["transcript_chars"] = len(transcript)
                    model_row["transcript_head"] = transcript[:1200]
                    write_latest(results)

                summary, model_s = call_chat_model(
                    api_key=api_key,
                    base_url=base_url,
                    model=model_name,
                    video_path=inline_path,
                    prompt=prompt,
                    transcript=transcript,
                    timeout_s=600,
                )
                model_row["status"] = "completed"
                model_row["model_elapsed_s"] = round(model_s, 2)
                model_row["total_elapsed_s"] = round(
                    model_s
                    + float(model_row.get("audio_extract_elapsed_s", 0.0))
                    + float(model_row.get("whisper_elapsed_s", 0.0)),
                    2,
                )
                model_row["summary_chars"] = len(summary)
                model_row["summary"] = summary
                model_row["summary_head"] = summary[:1200]
            except Exception as exc:
                model_row["status"] = "failed"
                model_row["error"] = f"{type(exc).__name__}: {exc}"
            write_latest(results)

        row["status"] = "completed"
        write_latest(results)

    final_path = OUT_DIR / f"model_compare_local_samples_{run_id}.json"
    final_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    write_latest(results)
    print(f"Saved: {final_path}")


if __name__ == "__main__":
    main()
