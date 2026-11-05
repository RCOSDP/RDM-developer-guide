"""Shared execution context passed to every subcommand (SPEC-02 §7 behavior rules)."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """The repository root is the first parent that contains manifest/upstreams.json."""
    p = (start or Path.cwd()).resolve()
    for cand in (p, *p.parents):
        if (cand / "manifest" / "upstreams.json").exists():
            return cand
    env = os.environ.get("GRDM_DEV_ROOT")
    if env and (Path(env) / "manifest" / "upstreams.json").exists():
        return Path(env).resolve()
    return p


@dataclass
class Context:
    root: Path
    yes: bool = False
    json_output: bool = False
    profile: str | None = None
    verbose: bool = False
    lang: str = field(default_factory=lambda: "ja" if os.environ.get("LANG", "").startswith("ja") else "en")
    stdin_is_tty: bool = field(default_factory=lambda: sys.stdin.isatty())
    env: dict[str, str] = field(default_factory=lambda: dict(os.environ))

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def reports_dir(self) -> Path:
        return self.runtime / "reports"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest" / "upstreams.json"

    def confirm(self, question: str, default: bool = False) -> bool:
        """Ask a yes/no question. Non-interactive without --yes answers 'no' (SPEC-02 §7)."""
        if self.yes:
            return True
        if not self.stdin_is_tty:
            return False
        ans = input(f"{question} [{'Y/n' if default else 'y/N'}] ").strip().lower()
        if not ans:
            return default
        return ans in ("y", "yes")
