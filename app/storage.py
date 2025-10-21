"""Simple SQLite-backed metadata store for uploads and agent runs."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class UploadRecord:
    file_id: str
    filename: str
    provider: str | None
    content_type: str
    bytes: int
    uploaded_at: datetime


@dataclass(slots=True)
class RunRecord:
    run_id: str
    thread_id: str
    assistant_id: str | None
    status: str
    schema_profile: str | None
    metadata: dict[str, Any]
    started_at: datetime


class MetadataStore:
    """Lightweight persistence layer around SQLite."""

    def __init__(self, database_path: Path):
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _initialise(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT UNIQUE NOT NULL,
                    filename TEXT NOT NULL,
                    provider TEXT,
                    content_type TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    uploaded_at TEXT NOT NULL
                );
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT UNIQUE NOT NULL,
                    thread_id TEXT NOT NULL,
                    assistant_id TEXT,
                    status TEXT NOT NULL,
                    schema_profile TEXT,
                    metadata_json TEXT,
                    started_at TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self._database_path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    async def log_upload(self, record: UploadRecord) -> None:
        """Persist upload metadata asynchronously."""

        def _write() -> None:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO uploads (
                        file_id, filename, provider, content_type, bytes, uploaded_at
                    ) VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (
                        record.file_id,
                        record.filename,
                        record.provider,
                        record.content_type,
                        record.bytes,
                        record.uploaded_at.isoformat(),
                    ),
                )

        logger.debug("Persisting upload metadata for file_id=%s", record.file_id)
        await asyncio.to_thread(_write)

    async def log_run(self, record: RunRecord) -> None:
        """Persist run metadata asynchronously."""

        def _write() -> None:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO runs (
                        run_id, thread_id, assistant_id, status, schema_profile, metadata_json, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        record.run_id,
                        record.thread_id,
                        record.assistant_id,
                        record.status,
                        record.schema_profile,
                        json.dumps(record.metadata, separators=(",", ":")),
                        record.started_at.isoformat(),
                    ),
                )

        logger.debug("Persisting run metadata for run_id=%s", record.run_id)
        await asyncio.to_thread(_write)

    async def update_run_status(self, run_id: str, status: str) -> None:
        """Update run status when polling results (placeholder for future use)."""

        def _update() -> None:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE runs SET status = ? WHERE run_id = ?;",
                    (status, run_id),
                )

        logger.debug("Updating run status run_id=%s status=%s", run_id, status)
        await asyncio.to_thread(_update)
