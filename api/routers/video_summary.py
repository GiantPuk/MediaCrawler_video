# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas.video_summary import (
    CreatorResolveRequest,
    CreatorResolveResponse,
    PlatformCredentialRequest,
    PlatformCredentialResponse,
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
    VideoSummaryTaskRequest,
    VideoSummaryTaskStatus,
)
from ..services.video_summary_manager import video_summary_manager

router = APIRouter(prefix="/video-summary", tags=["video-summary"])


@router.get("/settings", response_model=QwenSettingsResponse)
async def get_qwen_settings():
    return video_summary_manager.get_settings()


@router.post("/settings", response_model=QwenSettingsResponse)
async def save_qwen_settings(request: QwenSettingsRequest):
    return video_summary_manager.save_settings(request)


@router.get("/settings/profiles", response_model=QwenProfilesResponse)
async def list_qwen_profiles():
    return video_summary_manager.list_profiles()


@router.get("/settings/profiles/{profile_id}/secret", response_model=QwenProfileSecretResponse)
async def get_qwen_profile_secret(profile_id: str):
    try:
        return video_summary_manager.get_profile_secret(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/settings/profiles", response_model=QwenProfileResponse)
async def create_qwen_profile(request: QwenProfileRequest):
    return video_summary_manager.create_profile(request)


@router.put("/settings/profiles/{profile_id}", response_model=QwenProfileResponse)
async def update_qwen_profile(profile_id: str, request: QwenProfileRequest):
    try:
        return video_summary_manager.update_profile(profile_id, request)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/settings/profiles/{profile_id}", response_model=QwenProfilesResponse)
async def delete_qwen_profile(profile_id: str):
    try:
        return video_summary_manager.delete_profile(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/settings/profiles/{profile_id}/activate", response_model=QwenSettingsResponse)
async def activate_qwen_profile(profile_id: str):
    try:
        return video_summary_manager.activate_profile(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/platform-credentials", response_model=PlatformCredentialsResponse)
async def list_platform_credentials():
    return video_summary_manager.list_platform_credentials()


@router.get("/platform-credentials/{profile_id}/secret", response_model=PlatformCredentialSecretResponse)
async def get_platform_credential_secret(profile_id: str):
    try:
        return video_summary_manager.get_platform_credential_secret(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/platform-credentials", response_model=PlatformCredentialResponse)
async def create_platform_credential(request: PlatformCredentialRequest):
    try:
        return video_summary_manager.create_platform_credential(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/platform-credentials/{profile_id}", response_model=PlatformCredentialResponse)
async def update_platform_credential(profile_id: str, request: PlatformCredentialRequest):
    try:
        return video_summary_manager.update_platform_credential(profile_id, request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/platform-credentials/{profile_id}", response_model=PlatformCredentialsResponse)
async def delete_platform_credential(profile_id: str):
    try:
        return video_summary_manager.delete_platform_credential(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/platform-credentials/{profile_id}/activate", response_model=PlatformCredentialResponse)
async def activate_platform_credential(profile_id: str):
    try:
        return video_summary_manager.activate_platform_credential(profile_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/platform-credentials/qrcode-login/start", response_model=PlatformQrcodeLoginStatus)
async def start_platform_qrcode_login(request: PlatformQrcodeLoginRequest):
    try:
        return await video_summary_manager.start_platform_qrcode_login(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/platform-credentials/qrcode-login/{task_id}", response_model=PlatformQrcodeLoginStatus)
async def get_platform_qrcode_login(task_id: str):
    status = video_summary_manager.get_platform_qrcode_login(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Platform QR-code login task not found")
    return status


@router.post("/creators/resolve", response_model=CreatorResolveResponse)
async def resolve_creators(request: CreatorResolveRequest):
    return await video_summary_manager.resolve_creators(request)


@router.post("/tasks/start", response_model=VideoSummaryTaskStatus)
async def start_video_summary_task(request: VideoSummaryTaskRequest):
    try:
        return await video_summary_manager.start_task(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}", response_model=VideoSummaryTaskStatus)
async def get_video_summary_task(task_id: str):
    status = video_summary_manager.get_task(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Video summary task not found")
    return status


@router.post("/tasks/{task_id}/stop")
async def stop_video_summary_task(task_id: str):
    if not await video_summary_manager.stop_task(task_id):
        raise HTTPException(status_code=400, detail="Video summary task is not running")
    return {"status": "ok", "message": "Video summary task stopped"}
