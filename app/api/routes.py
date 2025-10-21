"""API routes for upload and agent orchestration workflows."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from starlette import status

from app.config import Settings, get_settings
from app.schemas import (
    AgentRunRequest,
    AgentRunResponse,
    FileUploadResponse,
)
from app.services.agent_service import AgentService
from app.storage import MetadataStore

router = APIRouter(tags=["agents"])


metadata_store: MetadataStore | None = None


def get_metadata_store(settings: Settings = Depends(get_settings)) -> MetadataStore:
    global metadata_store
    if metadata_store is None:
        metadata_store = MetadataStore(settings.database_path)
    return metadata_store


def get_agent_service(
    settings: Settings = Depends(get_settings),
    store: MetadataStore = Depends(get_metadata_store),
) -> AgentService:
    """Dependency to provide AgentService with current settings."""
    return AgentService(settings=settings, store=store)


@router.post(
    "/uploads",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV/XLSX file and forward to OpenAI Files API.",
)
async def upload_file(
    file: UploadFile = File(..., description="CSV or XLSX export to analyze."),
    provider: str | None = None,
    service: AgentService = Depends(get_agent_service),
) -> FileUploadResponse:
    if file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV or XLSX files are supported.",
        )
    try:
        result = await service.upload_source(file=file, provider=provider)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return FileUploadResponse(**result)


@router.post(
    "/runs",
    response_model=AgentRunResponse,
    summary="Create an agent run with uploaded file attachments.",
)
async def create_run(
    request: AgentRunRequest,
    service: AgentService = Depends(get_agent_service),
) -> AgentRunResponse:
    try:
        run = await service.start_agent_run(request=request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return AgentRunResponse(**run)
