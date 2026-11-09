"""Exit codes of grdm-dev (SPEC-02 §6). The canonical table is messages.tsv next to this file."""
from __future__ import annotations

import csv
from pathlib import Path

OK = 0
USAGE = 2
HOST_UNSUPPORTED = 10
DOCKER_MISSING = 11
PORT_IN_USE = 12
PREFLIGHT_FAILED = 13
RESET_FAILED = 14
MANIFEST_INVALID = 20
BUILD_FAILED = 30
HEALTH_FAILED = 40
SCAN_GATE_FAILED = 50
SCANNER_UNAVAILABLE = 51
SERVICES_UNHEALTHY = 52
REDTEAM_PREFLIGHT_FAILED = 53
ACCEPTANCE_FAILED = 60
UPSTREAM_FAILED = 70

_MESSAGES: dict[int, tuple[str, str]] | None = None


def messages() -> dict[int, tuple[str, str]]:
    """Return {code: (english, japanese)} read from messages.tsv (cached)."""
    global _MESSAGES
    if _MESSAGES is None:
        table: dict[int, tuple[str, str]] = {}
        with (Path(__file__).parent / "messages.tsv").open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                table[int(row["code"])] = (row["en"], row["ja"])
        _MESSAGES = table
    return _MESSAGES


def describe(code: int, lang: str = "en") -> str:
    en, ja = messages().get(code, ("unknown exit code", "不明な終了コード"))
    return ja if lang == "ja" else en
