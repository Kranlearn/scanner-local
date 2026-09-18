"""Compact SQLite persistence for scanner reports."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY,
    target TEXT NOT NULL,
    resolved_target TEXT NOT NULL,
    scanned_ports INTEGER NOT NULL,
    timeout_seconds REAL NOT NULL,
    started_at_utc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ports (
    scan_id INTEGER NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    state TEXT NOT NULL,
    service TEXT NOT NULL,
    latency_ms REAL,
    error TEXT,
    PRIMARY KEY (scan_id, port)
);
CREATE INDEX IF NOT EXISTS idx_scans_target_date
    ON scans(target, started_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_ports_state
    ON ports(scan_id, state);
"""


def connect(database: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    return connection


def save_report(database: str | Path, report: dict) -> int:
    """Store one report in normalized rows and return its scan id."""
    connection = connect(database)
    try:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO scans
                    (target, resolved_target, scanned_ports, timeout_seconds, started_at_utc)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report["target"],
                    report["resolved_target"],
                    report["scanned_ports"],
                    report["timeout_seconds"],
                    report["started_at_utc"],
                ),
            )
            scan_id = cursor.lastrowid
            connection.executemany(
                """
                INSERT INTO ports(scan_id, port, state, service, latency_ms, error)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        scan_id,
                        result["port"],
                        result["state"],
                        result["service"],
                        result["latency_ms"],
                        result.get("error"),
                    )
                    for result in report["results"]
                ],
            )
        return int(scan_id)
    finally:
        connection.close()


def list_scans(database: str | Path, limit: int = 20) -> list[dict]:
    connection = connect(database)
    try:
        rows = connection.execute(
            """
            SELECT id, target, resolved_target, scanned_ports, timeout_seconds, started_at_utc
            FROM scans ORDER BY id DESC LIMIT ?
            """,
            (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


def get_scan(database: str | Path, scan_id: int) -> dict | None:
    connection = connect(database)
    try:
        scan = connection.execute(
            "SELECT * FROM scans WHERE id = ?", (scan_id,)
            ).fetchone()
        if scan is None:
            return None
        ports = connection.execute(
            """
            SELECT port, state, service, latency_ms, error
            FROM ports WHERE scan_id = ? ORDER BY port
            """,
            (scan_id,),
            ).fetchall()
        result = dict(scan)
        result["results"] = [dict(row) for row in ports]
        return result
    finally:
        connection.close()


def json_bytes(payload: object) -> bytes:
    """Serialize API responses compactly to reduce transfer size."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
