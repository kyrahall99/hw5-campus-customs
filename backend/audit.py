"""Append-only audit trail at output/audit_trail.json (a JSON array of step records)."""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_MAX_FIELD = 2000  # truncate long tool outputs so the file stays readable

_lock = threading.Lock()


def _clip(value: Any) -> Any:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return value if len(text) <= _MAX_FIELD else text[:_MAX_FIELD] + "...[truncated]"


def append(record: dict) -> None:
    """Add one record to the trail. Existing records are never removed."""
    record = {"logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **record}
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            trail = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
        except json.JSONDecodeError:
            # Never discard an unreadable trail: keep it aside and start a new one.
            AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{datetime.now():%Y%m%d%H%M%S}.json"))
            trail = []
        trail.append({k: _clip(v) if k in ("args", "text") else v for k, v in record.items()})
        AUDIT_PATH.write_text(json.dumps(trail, indent=2, default=str))
