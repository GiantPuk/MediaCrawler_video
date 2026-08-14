# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/data.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/data", tags=["data"])

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PLATFORMS = ("xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu")
SENSITIVE_DATA_FILE_NAMES = {"platform_credentials.json", "qwen_settings.json"}


def _normalized_rel_path(file_path: Path) -> str:
    return str(file_path.relative_to(DATA_DIR)).replace("\\", "/")


def infer_data_platform(rel_path: str) -> Optional[str]:
    target = rel_path.lower()
    parts = [part.lower() for part in rel_path.split("/") if part]
    for platform in PLATFORMS:
        if platform in parts or Path(target).name.startswith(f"{platform}_"):
            return platform
    aliases = {
        "bilibili": "bili",
        "douyin": "dy",
        "kuaishou": "ks",
        "weibo": "wb",
    }
    for alias, platform in aliases.items():
        if alias in parts or Path(target).name.startswith(f"{alias}_"):
            return platform
    return None


def infer_data_source_area(rel_path: str) -> str:
    parts = [part.lower() for part in rel_path.split("/") if part]
    if parts[:1] == ["video_tasks"]:
        return "video_task"
    if parts[:1] == ["media"]:
        return "media"
    return "crawler"


def infer_data_category(file_path: Path, rel_path: str) -> str:
    target = rel_path.lower()
    name = file_path.name.lower()

    if any(token in name for token in ("comment", "reply", "sub_comment")):
        return "comments"
    if any(token in name for token in ("search_contents", "direct_search", "keyword", "query")):
        return "search"
    if any(token in name for token in ("ranking_contents", "hot_search", "rank")):
        return "ranking"
    if any(token in name for token in ("creator_contents", "author", "user", "profile", "up_info", "account")):
        return "creators"
    if name in {"result.json", "result.md"} or any(token in target for token in ("transcript", "subtitle", "summary", "analysis", "comparison", "status")):
        return "analysis"
    if target.startswith("video_tasks/") and "/raw/" not in target:
        return "analysis"
    if any(token in name for token in ("detail_contents", "contents", "note", "post", "article", "tweet", "weibo")):
        return "content"
    media_target = target.replace("video_tasks", "")
    if any(token in media_target for token in ("media", "video", "image", "download", "cover", "audio")):
        return "media"
    return "other"


def is_sensitive_data_file(file_path: Path) -> bool:
    return file_path.name.lower() in SENSITIVE_DATA_FILE_NAMES


def get_file_info(file_path: Path) -> dict:
    """Get file information"""
    stat = file_path.stat()
    record_count = None
    rel_path = _normalized_rel_path(file_path)

    # Try to get record count
    try:
        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    record_count = len(data)
                elif isinstance(data, dict):
                    for key in ("items", "records", "data", "comments", "contents"):
                        value = data.get(key)
                        if isinstance(value, list):
                            record_count = len(value)
                            break
                    if record_count is None:
                        record_count = 1
        elif file_path.suffix == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for _ in f) - 1  # Subtract header row
    except Exception:
        pass

    return {
        "name": file_path.name,
        "path": rel_path,
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "record_count": record_count,
        "type": file_path.suffix[1:] if file_path.suffix else "unknown",
        "category": infer_data_category(file_path, rel_path),
        "source_area": infer_data_source_area(rel_path),
        "platform": infer_data_platform(rel_path),
    }


@router.get("/files")
async def list_data_files(platform: Optional[str] = None, file_type: Optional[str] = None):
    """Get data file list"""
    if not DATA_DIR.exists():
        return {"files": []}

    files = []
    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue
            if is_sensitive_data_file(file_path):
                continue

            # Platform filter
            if platform:
                rel_path = _normalized_rel_path(file_path)
                if platform.lower() not in rel_path.lower():
                    continue

            # Type filter
            if file_type and file_path.suffix[1:].lower() != file_type.lower():
                continue

            try:
                files.append(get_file_info(file_path))
            except Exception:
                continue

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x["modified_at"], reverse=True)

    return {"files": files}


@router.get("/files/{file_path:path}")
async def get_file_content(file_path: str, preview: bool = True, limit: int = 100):
    """Get file content or preview"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    if is_sensitive_data_file(full_path):
        raise HTTPException(status_code=403, detail="Access denied")

    # Security check: ensure within DATA_DIR
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if preview:
        # Return preview data
        try:
            if full_path.suffix == ".json":
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"data": data[:limit], "total": len(data)}
                    return {"data": data, "total": 1}
            elif full_path.suffix == ".csv":
                import csv
                with open(full_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= limit:
                            break
                        rows.append(row)
                    # Re-read to get total count
                    f.seek(0)
                    total = sum(1 for _ in f) - 1
                    return {"data": rows, "total": total}
            elif full_path.suffix.lower() in (".xlsx", ".xls"):
                import pandas as pd
                # Read first limit rows
                df = pd.read_excel(full_path, nrows=limit)
                # Get total row count (only read first column to save memory)
                df_count = pd.read_excel(full_path, usecols=[0])
                total = len(df_count)
                # Convert to list of dictionaries, handle NaN values
                rows = df.where(pd.notnull(df), None).to_dict(orient='records')
                return {
                    "data": rows,
                    "total": total,
                    "columns": list(df.columns)
                }
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type for preview")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Return file download
        return FileResponse(
            path=full_path,
            filename=full_path.name,
            media_type="application/octet-stream"
        )


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download file"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")
    if is_sensitive_data_file(full_path):
        raise HTTPException(status_code=403, detail="Access denied")

    # Security check
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="application/octet-stream"
    )


@router.get("/stats")
async def get_data_stats():
    """Get data statistics"""
    if not DATA_DIR.exists():
        return {"total_files": 0, "total_size": 0, "by_platform": {}, "by_type": {}}

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_platform": {},
        "by_type": {}
    }

    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue
            if is_sensitive_data_file(file_path):
                continue

            try:
                stat = file_path.stat()
                stats["total_files"] += 1
                stats["total_size"] += stat.st_size

                # Statistics by type
                file_type = file_path.suffix[1:].lower()
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1

                # Statistics by platform (inferred from path)
                rel_path = _normalized_rel_path(file_path)
                platform = infer_data_platform(rel_path)
                if platform:
                    stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
            except Exception:
                continue

    return stats
