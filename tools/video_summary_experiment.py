from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TASK_ROOT = PROJECT_ROOT / "data" / "video_tasks"
EXPERIMENT_ROOT = PROJECT_ROOT / "data" / "experiments"
DEFAULT_API_BASE = "http://127.0.0.1:8080/api"
TERMINAL_STATUSES = {"completed", "error"}


def now_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def safe_text(value: Any) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def csv_filter(value: str) -> set[str]:
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def resolve_date_range(args: argparse.Namespace) -> tuple[str, str]:
    end_text = str(args.end_date or args.today)
    end_date = date.fromisoformat(end_text)
    if args.start_date:
        start_text = str(args.start_date)
    elif int(args.date_window_days or 0) > 0:
        start_text = (end_date - timedelta(days=int(args.date_window_days))).isoformat()
    else:
        start_text = end_text
    return start_text, end_text


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: Dict[str, Any] = {}
        for key, item in value.items():
            lower = str(key).lower()
            if lower in {"cookies", "api_key", "oss_access_key_id", "oss_access_key_secret"}:
                redacted[key] = "<redacted>" if item else ""
            elif "cookie" in lower and isinstance(item, str) and item:
                redacted[key] = "<redacted>"
            elif "access_key" in lower and isinstance(item, str) and item:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_sensitive(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


class ApiClient:
    def __init__(self, api_base: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.client = httpx.Client(timeout=120.0, trust_env=False)

    def close(self) -> None:
        self.client.close()

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        response = self.client.request(method, f"{self.api_base}{path}", json=payload)
        response.raise_for_status()
        if response.content:
            return response.json()
        return {}

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("POST", path, payload)


class ProfileSwitcher:
    def __init__(self, client: ApiClient) -> None:
        self.client = client
        self.original_profile_id = ""

    def __enter__(self) -> "ProfileSwitcher":
        settings = self.client.get("/video-summary/settings")
        self.original_profile_id = str(settings.get("profile_id") or "")
        return self

    def activate(self, profile_id: str) -> None:
        self.client.post(f"/video-summary/settings/profiles/{profile_id}/activate")

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.original_profile_id:
            try:
                self.activate(self.original_profile_id)
            except Exception:
                pass


def load_profiles() -> Dict[str, Any]:
    return read_json(TASK_ROOT / "qwen_settings.json")


def load_credentials() -> Dict[str, Any]:
    return read_json(TASK_ROOT / "platform_credentials.json")


def active_credential_id(platform: str) -> Optional[str]:
    store = load_credentials()
    active = store.get("active_by_platform") or {}
    return active.get(platform)


def qwen_profile_by_id(profile_id: str) -> Optional[Dict[str, Any]]:
    for profile in (load_profiles().get("profiles") or []):
        if str(profile.get("id")) == str(profile_id):
            return profile
    return None


def task_dir(task_id: str) -> Path:
    return TASK_ROOT / task_id


def poll_task(client: ApiClient, task_id: str, poll_interval: float, timeout_seconds: int) -> Dict[str, Any]:
    started = time.perf_counter()
    last_status: Dict[str, Any] = {}
    while True:
        status = client.get(f"/video-summary/tasks/{task_id}")
        last_status = status
        if status.get("status") in TERMINAL_STATUSES:
            return status
        if time.perf_counter() - started > timeout_seconds:
            try:
                client.post(f"/video-summary/tasks/{task_id}/stop")
            except Exception:
                pass
            status = client.get(f"/video-summary/tasks/{task_id}")
            status["experiment_timeout"] = True
            return status
        time.sleep(poll_interval)


def start_and_wait(
    client: ApiClient,
    payload: Dict[str, Any],
    *,
    poll_interval: float,
    timeout_seconds: int,
) -> Dict[str, Any]:
    started = time.perf_counter()
    status = client.post("/video-summary/tasks/start", payload)
    task_id = str(status["task_id"])
    final_status = poll_task(client, task_id, poll_interval, timeout_seconds)
    final_status["_experiment_wall_seconds"] = round(time.perf_counter() - started, 3)
    return final_status


def copy_task_artifacts(task_id: str, destination: Path) -> Dict[str, str]:
    source = task_dir(task_id)
    destination.mkdir(parents=True, exist_ok=True)
    copied: Dict[str, str] = {}
    for name in ["task_state.json", "result.json"]:
        src = source / name
        if src.exists():
            dst = destination / name
            try:
                write_json(dst, redact_sensitive(read_json(src)))
            except Exception:
                shutil.copy2(src, dst)
            copied[name] = str(dst)
    for name in ["raw", "transcripts", "compressed"]:
        src = source / name
        if src.exists():
            dst = destination / name
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied[name] = str(dst)
    return copied


def summarize_task_status(status: Dict[str, Any]) -> Dict[str, Any]:
    result = status.get("result") or {}
    items = result.get("items") or status.get("result", {}).get("items") or []
    if not items and status.get("result") is None:
        state = read_json(task_dir(str(status.get("task_id"))) / "task_state.json")
        items = state.get("items") or []
        result = state.get("result") or result
    subtasks = status.get("subtasks") or []
    step_seconds: Dict[str, float] = {}
    failed_steps: List[str] = []
    for step in subtasks:
        phase = str(step.get("phase") or "unknown")
        duration = step.get("duration_seconds")
        if isinstance(duration, (int, float)):
            step_seconds[phase] = round(step_seconds.get(phase, 0.0) + float(duration), 3)
        if step.get("status") == "failed":
            failed_steps.append(f"{step.get('label')}: {step.get('message')}")
    return {
        "task_id": status.get("task_id"),
        "status": status.get("status"),
        "wall_seconds": status.get("_experiment_wall_seconds"),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "progress_message": status.get("progress_message"),
        "error_message": status.get("error_message"),
        "total_records": result.get("total_records"),
        "matched_videos": result.get("matched_videos"),
        "summarized_videos": result.get("summarized_videos"),
        "item_count": len(items),
        "summary_completed": sum(1 for item in items if item.get("summary_status") == "completed"),
        "download_completed": sum(1 for item in items if item.get("download_status") in {"downloaded", "existing"}),
        "download_failed": sum(1 for item in items if item.get("download_status") == "failed"),
        "analysis_modes": sorted({str(item.get("analysis_mode") or "none") for item in items}),
        "step_seconds": step_seconds,
        "failed_steps": failed_steps,
        "logs_tail": (status.get("logs") or [])[-12:],
        "items_preview": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "download_status": item.get("download_status"),
                "summary_status": item.get("summary_status"),
                "analysis_mode": item.get("analysis_mode"),
                "error": item.get("error"),
            }
            for item in items[:8]
        ],
    }


def base_payload(
    platform: str,
    *,
    credential_profile_id: Optional[str],
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    return {
        "platform": platform,
        "creator_id": "",
        "creator_display_name": "",
        "profile_url": "",
        "source_mode": "search",
        "search_keyword": "",
        "ranking_type": "",
        "ranking_limit": 5,
        "credential_profile_id": credential_profile_id,
        "workflow_mode": "metadata_only",
        "source_task_id": None,
        "selected_item_ids": [],
        "login_type": "cookie" if credential_profile_id else "qrcode",
        "cookies": "",
        "start_date": start_date,
        "end_date": end_date,
        "max_videos": 3,
        "crawl_concurrency": 1,
        "headless": True,
        "crawl_sleep_seconds": 8.0,
        "crawl_min_sleep_seconds": 6.0,
        "crawl_max_sleep_seconds": 12.0,
        "crawl_long_pause_every": 0,
        "crawl_long_pause_min_seconds": 30.0,
        "crawl_long_pause_max_seconds": 90.0,
        "summarize": False,
        "video_input_mode": "auto",
        "video_upload_backend": "auto",
        "video_fps": 2.0,
        "sample_frames": 8,
        "max_inline_video_mb": 7,
        "max_dashscope_video_mb": 100,
        "dashscope_retry_count": 3,
        "enable_video_compression": True,
        "compression_target_mb": 64,
        "enable_whisper_transcription": False,
        "whisper_model": "turbo",
    }


def metadata_cases(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for platform, query in [
        ("bili", "泰坦尼克号"),
        ("dy", "美食"),
        ("xhs", "咖啡"),
        ("ks", "旅行"),
        ("zhihu", "AI"),
    ]:
        credential_id = active_credential_id(platform)
        payload = base_payload(platform, credential_profile_id=credential_id, start_date=start_date, end_date=end_date)
        payload.update(
            {
                "source_mode": "search",
                "search_keyword": query,
                "creator_id": query,
                "creator_display_name": f"Search: {query}",
                "max_videos": 3,
            }
        )
        cases.append({"case_id": f"metadata_search_{platform}", "kind": "metadata", "payload": payload})

    for platform, ranking_type in [
        ("bili", "popular"),
        ("dy", "hot_search"),
        ("ks", "hot"),
        ("wb", "hot_search"),
        ("zhihu", "total"),
        ("tieba", "hot_topic"),
    ]:
        credential_id = active_credential_id(platform)
        payload = base_payload(platform, credential_profile_id=credential_id, start_date=start_date, end_date=end_date)
        payload.update(
            {
                "source_mode": "ranking",
                "ranking_type": ranking_type,
                "ranking_limit": 5,
                "max_videos": 5,
                "creator_id": f"ranking:{platform}:{ranking_type}",
                "creator_display_name": f"{platform} {ranking_type}",
            }
        )
        cases.append({"case_id": f"metadata_ranking_{platform}_{ranking_type}", "kind": "metadata", "payload": payload})
    return cases


def pick_candidate_ids(status: Dict[str, Any], limit: int = 1) -> List[str]:
    result = status.get("result") or {}
    items = result.get("items") or []
    ids: List[str] = []
    for item in items:
        if item.get("download_status") in {"unsupported", "failed"}:
            continue
        item_id = str(item.get("id") or "").strip()
        if item_id:
            ids.append(item_id)
        if len(ids) >= limit:
            break
    return ids


def analysis_payload_from_metadata(
    metadata_status: Dict[str, Any],
    *,
    qwen_profile_id: str,
    whisper: bool,
    sample_frames: int,
    video_upload_backend: str,
    start_date: str,
    end_date: str,
) -> Optional[Dict[str, Any]]:
    source_task_id = str(metadata_status.get("task_id") or "")
    result = metadata_status.get("result") or {}
    platform = str(result.get("platform") or metadata_status.get("platform") or "")
    selected_ids = pick_candidate_ids(metadata_status, limit=1)
    if not source_task_id or not platform or not selected_ids:
        return None
    credential_id = active_credential_id(platform)
    payload = base_payload(platform, credential_profile_id=credential_id, start_date=start_date, end_date=end_date)
    payload.update(
        {
            "source_mode": result.get("source_mode") or "search",
            "creator_id": result.get("creator_id") or f"selected:{source_task_id}",
            "creator_display_name": result.get("creator_display_name") or "selected item",
            "search_keyword": result.get("search_keyword") or "",
            "ranking_type": result.get("ranking_type") or "",
            "workflow_mode": "selected_items",
            "source_task_id": source_task_id,
            "selected_item_ids": selected_ids,
            "summarize": True,
            "sample_frames": sample_frames,
            "video_upload_backend": video_upload_backend,
            "enable_whisper_transcription": whisper,
            "whisper_model": "turbo",
        }
    )
    return payload


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        return
    fieldnames = [
        "case_id",
        "kind",
        "platform",
        "source_mode",
        "qwen_profile_id",
        "qwen_model",
        "whisper",
        "sample_frames",
        "video_upload_backend",
        "task_id",
        "status",
        "wall_seconds",
        "total_records",
        "matched_videos",
        "summarized_videos",
        "download_completed",
        "download_failed",
        "analysis_modes",
        "error_message",
        "artifact_dir",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            row = dict(row)
            row["analysis_modes"] = ",".join(row.get("analysis_modes") or [])
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run reproducible MediaCrawler video-summary experiments.")
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--metadata-only", action="store_true", help="Only run metadata/ranking environment cases.")
    parser.add_argument("--analysis", action="store_true", help="Run analysis cases after metadata.")
    parser.add_argument("--max-analysis-cases", type=int, default=4)
    parser.add_argument("--poll-interval", type=float, default=3.0)
    parser.add_argument("--task-timeout", type=int, default=1800)
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--start-date", default="", help="Start date for metadata filtering, YYYY-MM-DD.")
    parser.add_argument("--end-date", default="", help="End date for metadata filtering, YYYY-MM-DD.")
    parser.add_argument("--date-window-days", type=int, default=0, help="If start date is omitted, use end_date minus this many days.")
    parser.add_argument("--metadata-platforms", default="", help="Comma-separated platform filter for metadata cases.")
    parser.add_argument("--analysis-platforms", default="", help="Comma-separated platform filter for analysis cases.")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir) if args.output_dir else EXPERIMENT_ROOT / f"deep_experiment_{now_id()}"
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    jsonl_path = output_dir / "runs.jsonl"
    csv_path = output_dir / "runs.csv"
    start_date, end_date = resolve_date_range(args)

    client = ApiClient(args.api_base)
    rows: List[Dict[str, Any]] = []
    manifest: Dict[str, Any] = {
        "created_at": datetime.now().isoformat(),
        "api_base": args.api_base,
        "output_dir": str(output_dir),
        "today": args.today,
        "start_date": start_date,
        "end_date": end_date,
        "metadata_only": bool(args.metadata_only),
        "analysis": bool(args.analysis),
        "cases": [],
    }

    metadata_status_by_case: Dict[str, Dict[str, Any]] = {}
    try:
        with ProfileSwitcher(client) as switcher:
            metadata_platforms = csv_filter(args.metadata_platforms)
            analysis_platforms = csv_filter(args.analysis_platforms)
            metadata = metadata_cases(start_date, end_date)
            if metadata_platforms:
                metadata = [
                    case
                    for case in metadata
                    if str((case.get("payload") or {}).get("platform") or "") in metadata_platforms
                ]
            for case in metadata:
                payload = case["payload"]
                platform = str(payload.get("platform") or "")
                run_record = {
                    "case_id": case["case_id"],
                    "kind": case["kind"],
                    "platform": platform,
                    "source_mode": payload.get("source_mode"),
                    "qwen_profile_id": "",
                    "qwen_model": "",
                    "whisper": False,
                    "sample_frames": payload.get("sample_frames"),
                    "video_upload_backend": payload.get("video_upload_backend"),
                    "payload": payload,
                }
                manifest["cases"].append(run_record)
                if args.dry_run:
                    continue
                started = time.perf_counter()
                try:
                    status = start_and_wait(
                        client,
                        payload,
                        poll_interval=args.poll_interval,
                        timeout_seconds=args.task_timeout,
                    )
                    summary = summarize_task_status(status)
                    artifact_dir = output_dir / case["case_id"] / str(status.get("task_id"))
                    copied = copy_task_artifacts(str(status.get("task_id")), artifact_dir)
                    run_record.update(summary)
                    run_record["seconds_observed"] = round(time.perf_counter() - started, 3)
                    run_record["artifact_dir"] = str(artifact_dir)
                    run_record["artifacts"] = copied
                    metadata_status_by_case[case["case_id"]] = status
                except Exception as exc:
                    run_record.update(
                        {
                            "status": "experiment_error",
                            "wall_seconds": round(time.perf_counter() - started, 3),
                            "error_message": f"{type(exc).__name__}: {exc}",
                            "artifact_dir": "",
                        }
                    )
                append_jsonl(jsonl_path, run_record)
                rows.append(run_record)
                write_json(manifest_path, manifest)
                write_csv(csv_path, rows)

            if args.analysis and not args.metadata_only and not args.dry_run:
                profile_store = load_profiles()
                profiles = profile_store.get("profiles") or []
                profile_ids = [
                    str(profile.get("id"))
                    for profile in profiles
                    if profile.get("api_provider") in {"ollama", "dashscope"} and (profile.get("api_provider") == "ollama" or profile.get("api_key"))
                ]
                selected_sources: Dict[str, Dict[str, Any]] = {}
                for case_id, status in metadata_status_by_case.items():
                    result = status.get("result") or {}
                    platform = str(result.get("platform") or status.get("platform") or "")
                    if analysis_platforms and platform not in analysis_platforms:
                        continue
                    if not platform or platform in selected_sources:
                        continue
                    if pick_candidate_ids(status, limit=1):
                        selected_sources[platform] = status
                analysis_cases: List[Dict[str, Any]] = []
                for platform, source_status in selected_sources.items():
                    for profile_id in profile_ids:
                        profile = qwen_profile_by_id(profile_id) or {}
                        provider = profile.get("api_provider")
                        model = str(profile.get("model") or "")
                        if provider == "ollama":
                            sample_frames = 6 if "qwen3-vl:8b" in model else 4
                            whisper_options = [False, True]
                        else:
                            sample_frames = 8
                            whisper_options = [False]
                        for whisper in whisper_options:
                            payload = analysis_payload_from_metadata(
                                source_status,
                                qwen_profile_id=profile_id,
                                whisper=whisper,
                                sample_frames=sample_frames,
                                video_upload_backend="auto",
                                start_date=start_date,
                                end_date=end_date,
                            )
                            if payload:
                                analysis_cases.append(
                                    {
                                        "case_id": f"analysis_{platform}_{profile_id}_{'whisper' if whisper else 'no_whisper'}",
                                        "kind": "analysis",
                                        "qwen_profile_id": profile_id,
                                        "qwen_model": model,
                                        "payload": payload,
                                    }
                                )
                if analysis_cases:
                    for case in analysis_cases[: max(0, args.max_analysis_cases)]:
                        switcher.activate(case["qwen_profile_id"])
                        payload = case["payload"]
                        run_record = {
                            "case_id": case["case_id"],
                            "kind": case["kind"],
                            "platform": payload.get("platform"),
                            "source_mode": payload.get("source_mode"),
                            "qwen_profile_id": case["qwen_profile_id"],
                            "qwen_model": case["qwen_model"],
                            "whisper": payload.get("enable_whisper_transcription"),
                            "sample_frames": payload.get("sample_frames"),
                            "video_upload_backend": payload.get("video_upload_backend"),
                            "payload": payload,
                        }
                        manifest["cases"].append(run_record)
                        started = time.perf_counter()
                        try:
                            status = start_and_wait(
                                client,
                                payload,
                                poll_interval=args.poll_interval,
                                timeout_seconds=args.task_timeout,
                            )
                            summary = summarize_task_status(status)
                            artifact_dir = output_dir / case["case_id"] / str(status.get("task_id"))
                            copied = copy_task_artifacts(str(status.get("task_id")), artifact_dir)
                            run_record.update(summary)
                            run_record["seconds_observed"] = round(time.perf_counter() - started, 3)
                            run_record["artifact_dir"] = str(artifact_dir)
                            run_record["artifacts"] = copied
                        except Exception as exc:
                            run_record.update(
                                {
                                    "status": "experiment_error",
                                    "wall_seconds": round(time.perf_counter() - started, 3),
                                    "error_message": f"{type(exc).__name__}: {exc}",
                                    "artifact_dir": "",
                                }
                            )
                        append_jsonl(jsonl_path, run_record)
                        rows.append(run_record)
                        write_json(manifest_path, manifest)
                        write_csv(csv_path, rows)
    finally:
        client.close()

    manifest["completed_at"] = datetime.now().isoformat()
    manifest["run_count"] = len(rows)
    write_json(manifest_path, manifest)
    write_csv(csv_path, rows)
    print(json.dumps({"output_dir": str(output_dir), "run_count": len(rows), "csv": str(csv_path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
