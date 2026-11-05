"""grdm-dev report — bundle the latest doctor / plan / health / scan / accept reports (SPEC-02 §3).

Reads runtime/reports/<name>_latest.json for each report, writes runtime/reports/report_<ts>.json
and .toon with a summary (which reports exist, their timestamps, overall status) and prints it.
Values found in runtime/.env are masked before anything is written (SPEC-03 §3.1).
"""
from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any

from . import exit_codes, report
from .context import Context

REPORT_NAMES = ("doctor", "plan", "health", "scan", "accept")


def register(subparsers) -> None:
    p = subparsers.add_parser("report", help="bundle the latest doctor, plan, health, scan and accept reports")
    p.set_defaults(_module=sys.modules[__name__])


def _status_of(data: Any) -> str:
    if not isinstance(data, dict):
        return "unreadable"
    if "exit_code" in data:
        return "ok" if data.get("exit_code") in (0, "0") else f"fail ({data.get('exit_code')})"
    for key in ("gate", "status", "result"):
        if key in data:
            return str(data[key])
    return "present"


def collect(reports_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bundle: dict[str, Any] = {}
    for name in REPORT_NAMES:
        path = reports_dir / f"{name}_latest.json"
        if not path.exists():
            rows.append({"name": name, "present": False, "timestamp": "", "status": "missing"})
            continue
        ts = _dt.datetime.fromtimestamp(path.stat().st_mtime, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = None
        rows.append({"name": name, "present": True, "timestamp": ts, "status": _status_of(data)})
        bundle[name] = data if data is not None else {"error": "unreadable"}
    return rows, bundle


def run(ctx: Context, args) -> int:
    from .scan import _env_secrets, mask_secrets  # same masking rule as scan

    rows, bundle = collect(ctx.reports_dir)
    present = [r["name"] for r in rows if r["present"]]
    failed = [r["name"] for r in rows if r["present"] and r["status"].startswith("fail")]
    if not present:
        overall = "empty"
    elif failed:
        overall = "fail"
    elif len(present) == len(REPORT_NAMES):
        overall = "complete"
    else:
        overall = "partial"
    data: dict[str, Any] = {
        "date": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "overall": overall,
        "present": present,
        "missing": [r["name"] for r in rows if not r["present"]],
        "failed": failed,
        "reports": rows,
        "bundle": bundle,
    }
    data = mask_secrets(data, _env_secrets(ctx.runtime / ".env"))
    report.emit(ctx, "report", data)
    return exit_codes.OK
