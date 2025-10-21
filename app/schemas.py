"""Pydantic models for API requests and responses."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class FileUploadResponse(BaseModel):
    """Response returned when a file is uploaded and forwarded to OpenAI."""

    file_id: str = Field(..., description="Identifier returned by OpenAI Files API.")
    filename: str
    provider: str | None = Field(default=None, description="Optional provider hint supplied by the caller.")
    content_type: str
    bytes: int
    uploaded_at: datetime


class AgentRunRequest(BaseModel):
    """Request payload used to start an agent run."""

    file_ids: list[str] = Field(..., min_items=1, description="Files previously uploaded via /uploads.")
    instructions: str = Field(
        ...,
        description="Custom instructions to include alongside the system prompt.",
    )
    response_schema: Literal["default", "income_cashflow_expense"] = Field(
        default="income_cashflow_expense",
        description="Schema profile the agent should satisfy.",
    )
    metadata: dict[str, str] | None = Field(default=None, description="Optional metadata stored with the run.")


class AgentRunResponse(BaseModel):
    """Response returned once an agent run is created."""

    run_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    thread_id: str
    started_at: datetime
    dashboard_url: HttpUrl | None = None
    assistant_id: str | None = Field(
        default=None, description="Assistant identifier used for the run."
    )
    requested_schema: str | None = Field(
        default=None, description="Schema profile the run was instructed to satisfy."
    )
    metadata: dict[str, str] | None = Field(
        default=None, description="Caller-supplied metadata stored alongside the run."
    )
