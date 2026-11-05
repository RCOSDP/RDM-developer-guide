"""Report output: TOON to stdout by default, JSON with --json; copy kept under runtime/reports/."""
from __future__ import annotations

import datetime as _dt
import json
import sys
from typing import Any

from . import toon
from .context import Context


def timestamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def emit(ctx: Context, name: str, data: dict[str, Any], *, save: bool = True) -> None:
    """Print one report and (by default) save JSON + TOON copies as runtime/reports/<name>_<ts>.*"""
    text = json.dumps(data, ensure_ascii=False, indent=2) if ctx.json_output else toon.encode(data, name=name)
    sys.stdout.write(text + "\n")
    if save:
        try:
            ctx.reports_dir.mkdir(parents=True, exist_ok=True)
            base = ctx.reports_dir / f"{name}_{timestamp()}"
            base.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            base.with_suffix(".toon").write_text(toon.encode(data, name=name) + "\n", encoding="utf-8")
            latest = ctx.reports_dir / f"{name}_latest.json"
            latest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:  # reports are evidence, but failing to save must not hide the result
            sys.stderr.write(f"warning: could not save report: {exc}\n")


def error(ctx: Context, code: int, detail: str = "") -> int:
    """Print the canonical message for an exit code (plus detail) to stderr and return the code."""
    from .exit_codes import describe

    msg = describe(code, ctx.lang)
    sys.stderr.write(f"[grdm-dev] exit {code}: {msg}" + (f" — {detail}" if detail else "") + "\n")
    return code
