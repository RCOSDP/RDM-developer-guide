"""grdm-dev doctor — host detection (SPEC-02 §3). Reference implementation of the module contract.

Contract for every subcommand module:
  register(subparsers): add the sub-parser and call set_defaults(_module=sys.modules[__name__])
  run(ctx, args) -> int: return an exit code from grdm_dev.exit_codes
Tests inject a fake `runner` (callable taking argv list, returning (returncode, stdout)) so Docker
is never required by unit tests (SPEC-02 §10).

Exit codes: 10 when the host itself is unsupported (OS, CPU, memory, Python), 11 when Docker is
missing, not running, or lacks the Compose / buildx plugin. Warnings (best-effort host, low
memory, little disk) do not change the exit code unless `--strict` is given, which turns them
into exit 10 so CI can insist on an official host.
"""
from __future__ import annotations

import sys

from . import exit_codes, host, report
from .context import Context


def register(subparsers) -> None:
    p = subparsers.add_parser("doctor", help="detect OS, CPU, memory, disk, Docker; exit 10/11 if unsupported")
    p.add_argument("--strict", action="store_true", help="treat warnings (best-effort host, low memory) as exit 10")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, runner=None, probe=None) -> int:
    info = host.detect(runner=runner, probe=probe, root=ctx.root)
    data = host.as_report(info)
    data["strict"] = bool(getattr(args, "strict", False))
    report.emit(ctx, "doctor", data)
    if not info.supported:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, "; ".join(info.problems))
    if not info.docker_ok:
        return report.error(ctx, exit_codes.DOCKER_MISSING, "; ".join(info.problems))
    if data["strict"] and info.warnings:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, "--strict: " + "; ".join(info.warnings))
    return exit_codes.OK
