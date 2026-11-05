"""grdm-dev docs build | check — MkDocs build and the SPEC-06 §8 checks (SPEC-02 §3).

`build` runs `mkdocs build --strict` with the MkDocs of the current virtual environment (installed by
`pip install -e "installer[docs]"`); a missing mkdocs is exit 2 with that hint. `check` runs the CI
validator tools/docs_check.py in-process and returns its exit code (0 pass, 1 failure, 2 usage).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable

from . import exit_codes, report
from .context import Context
from .manifest_cmd import load_tool

INSTALL_HINT = 'pip install -e "installer[docs]"'
Runner = Callable[[list[str]], tuple[int, str]]


def register(subparsers) -> None:
    p = subparsers.add_parser("docs", help="build the MkDocs site or run the SPEC-06 documentation checks")
    sub = p.add_subparsers(dest="docs_action", metavar="<build|check>")
    sub.add_parser("build", help="mkdocs build --strict into site/ (exit 2 with install hint if mkdocs is missing)")
    c = sub.add_parser("check", help="SPEC-06 §8 checks via tools/docs_check.py")
    c.add_argument("--all-warnings", action="store_true", help="print every glossary warning")
    p.set_defaults(_module=sys.modules[__name__])


def find_mkdocs() -> str | None:
    """Prefer the mkdocs next to the running Python (the .venv), then PATH."""
    cand = Path(sys.executable).parent / ("mkdocs.exe" if sys.platform == "win32" else "mkdocs")
    if cand.exists():
        return str(cand)
    return shutil.which("mkdocs")


def _default_runner(cwd: Path) -> Runner:
    def _run(argv: list[str]) -> tuple[int, str]:
        try:
            proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True)
        except FileNotFoundError:
            return 127, ""
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode, proc.stdout
    return _run


def run(ctx: Context, args, runner: Runner | None = None, mkdocs: str | None = None) -> int:
    action = getattr(args, "docs_action", None)
    if action == "build":
        exe = mkdocs or find_mkdocs()
        if not exe:
            return report.error(ctx, exit_codes.USAGE, f"mkdocs not found; install with {INSTALL_HINT}")
        runner = runner or _default_runner(ctx.root)
        rc, _ = runner([exe, "build", "--strict", "-f", str(ctx.root / "mkdocs.yml")])
        if rc == 127:
            return report.error(ctx, exit_codes.USAGE, f"mkdocs could not start; install with {INSTALL_HINT}")
        if rc != 0:
            sys.stderr.write(f"[grdm-dev] mkdocs build --strict failed (rc {rc})\n")
            return 1
        sys.stdout.write(f"site built into {ctx.root / 'site'}\n")
        return exit_codes.OK
    if action == "check":
        try:
            dc = load_tool(ctx.root, "docs_check")
        except FileNotFoundError as exc:
            return report.error(ctx, exit_codes.USAGE, f"validator not found: {exc}")
        argv = ["--root", str(ctx.root)]
        if getattr(args, "all_warnings", False):
            argv.append("--all-warnings")
        return int(dc.main(argv))
    sys.stderr.write("usage: grdm-dev docs <build|check>\n")
    return exit_codes.USAGE
