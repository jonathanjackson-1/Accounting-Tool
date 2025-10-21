"""Agent service coordinating uploads and run creation against OpenAI APIs."""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

import httpx
from fastapi import UploadFile

from app.agents import get_response_format
from app.config import Settings
from app.schemas import AgentRunRequest
from app.storage import MetadataStore, RunRecord, UploadRecord

logger = logging.getLogger(__name__)


class AgentService:
    """High-level coordination layer for OpenAI Agents workflows."""

    def __init__(self, settings: Settings, store: MetadataStore | None = None):
        self._settings = settings
        self._store = store
        self._base_url = settings.openai_base_url.rstrip("/")

    async def upload_source(self, file: UploadFile, provider: str | None) -> dict[str, Any]:
        """Upload a source file to OpenAI's Files API and persist metadata."""
        headers = self._build_headers()
        contents = await file.read()
        filename = file.filename or "upload"
        content_type = file.content_type or "application/octet-stream"

        data = {"purpose": "assistants"}
        files = {"file": (filename, contents, content_type)}

        logger.info("Uploading file '%s' (%d bytes) to OpenAI Files API", filename, len(contents))
        try:
            async with httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=60.0) as client:
                response = await client.post("/files", data=data, files=files)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:500]
            logger.error(
                "OpenAI Files API error (%s): %s", exc.response.status_code, error_body, exc_info=True
            )
            raise RuntimeError(
                f"OpenAI Files API error ({exc.response.status_code}): {error_body}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Failed to reach OpenAI Files API: %s", exc, exc_info=True)
            raise RuntimeError(f"Failed to reach OpenAI Files API: {exc}") from exc

        payload = response.json()
        file_id = payload.get("id")
        if not file_id:
            logger.error("OpenAI Files API response missing file id: %s", payload)
            raise RuntimeError("OpenAI Files API response did not include a file id.")
        uploaded_at = dt.datetime.now(tz=dt.timezone.utc)

        result = {
            "file_id": file_id,
            "filename": payload.get("filename", filename),
            "provider": provider,
            "content_type": content_type,
            "bytes": len(contents),
            "uploaded_at": uploaded_at,
        }

        if self._store and file_id:
            await self._store.log_upload(
                UploadRecord(
                    file_id=file_id,
                    filename=result["filename"],
                    provider=provider,
                    content_type=content_type,
                    bytes=len(contents),
                    uploaded_at=uploaded_at,
                )
            )

        return result

    async def start_agent_run(self, request: AgentRunRequest) -> dict[str, Any]:
        """Start an OpenAI Agent run with structured output enforcement."""
        headers = self._build_headers()
        assistant_id = self._settings.openai_assistant_id
        if not assistant_id:
            raise RuntimeError("OPENAI_ASSISTANT_ID is not configured.")

        message_payload = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please review the attached spreadsheets. Follow the run instructions to generate the required financial summaries.",
                },
            ],
            "attachments": [{"file_id": file_id} for file_id in request.file_ids],
        }

        logger.info("Creating OpenAI thread with %d attachments", len(request.file_ids))
        try:
            async with httpx.AsyncClient(base_url=self._base_url, headers=headers, timeout=60.0) as client:
                thread_response = await client.post("/threads", json={"messages": [message_payload]})
                thread_response.raise_for_status()
                thread_payload = thread_response.json()
                thread_id = thread_payload.get("id")
                if not thread_id:
                    logger.error("OpenAI Threads API response missing id: %s", thread_payload)
                    raise RuntimeError("OpenAI Threads API response did not include a thread id.")

                run_body: dict[str, Any] = {
                    "assistant_id": assistant_id,
                }

                if request.metadata:
                    run_body["metadata"] = request.metadata

                response_format = get_response_format(request.response_schema)
                if response_format:
                    run_body["response_format"] = response_format

                instructions_text = request.instructions.strip()
                if instructions_text:
                    run_body["instructions"] = instructions_text

                if "instructions" not in run_body:
                    run_body["instructions"] = (
                        "Read the uploaded spreadsheets and produce the structured JSON outputs defined by the schema."
                    )

                run_response = await client.post(f"/threads/{thread_id}/runs", json=run_body)
                run_response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            error_body = exc.response.text[:500]
            logger.error(
                "OpenAI Agents API error (%s): %s", exc.response.status_code, error_body, exc_info=True
            )
            raise RuntimeError(
                f"OpenAI Agents API error ({exc.response.status_code}): {error_body}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Failed to reach OpenAI Agents API: %s", exc, exc_info=True)
            raise RuntimeError(f"Failed to reach OpenAI Agents API: {exc}") from exc

        run_payload = run_response.json()
        run_id = run_payload.get("id")
        if not run_id:
            logger.error("OpenAI Agents API response missing run id: %s", run_payload)
            raise RuntimeError("OpenAI Agents API response did not include a run id.")
        status = run_payload.get("status", "queued")
        created_at = run_payload.get("created_at")
        if isinstance(created_at, (int, float)):
            started_at = dt.datetime.fromtimestamp(created_at, tz=dt.timezone.utc)
        else:
            started_at = dt.datetime.now(tz=dt.timezone.utc)

        result = {
            "run_id": run_id,
            "status": status,
            "thread_id": thread_id,
            "started_at": started_at,
            "dashboard_url": run_payload.get("dashboard_url"),
            "assistant_id": run_payload.get("assistant_id", assistant_id),
            "requested_schema": request.response_schema,
            "metadata": request.metadata or {},
        }

        if self._store and run_id:
            await self._store.log_run(
                RunRecord(
                    run_id=run_id,
                    thread_id=thread_id,
                    assistant_id=result["assistant_id"],
                    status=status,
                    schema_profile=request.response_schema,
                    metadata=request.metadata or {},
                    started_at=started_at,
                )
            )

        return result

    def _build_headers(self) -> dict[str, str]:
        if not self._settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        return {
            "Authorization": f"Bearer {self._settings.openai_api_key}",
            "OpenAI-Beta": "assistants=v2",
        }
