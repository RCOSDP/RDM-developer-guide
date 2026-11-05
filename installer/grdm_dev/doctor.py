"""grdm-dev doctor — host detection (SPEC-02 §3). Reference implementation of the module contract.

Contract for every subcommand module:
  register(subparsers): add the sub-parser and call set_defaults(_module=sys.modules[__name__])
  run(ctx, args) -> int: return an exit code from grdm_dev.exit_codes
Tests inject a fake `runner` (callable taking argv list, returning (returncode, stdout)) so Docker
is never required by unit tests (SPEC-02 §10).
"""
from __future__ import annotations

import sys

from . import exit_codes, host, report
from .context import Context


def register(subparsers) -> None:
    p = subparsers.add_parser("doctor", help="detect OS, CPU, memory, disk, Docker; exit 10/11 if unsupported")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, runner=None) -> int:
    info = host.detect(runner=runner)
    data = host.as_report(info)
    report.emit(ctx, "doctor", data)
    if not info.supported:
        return report.error(ctx, exit_codes.HOST_UNSUPPORTED, "; ".join(info.problems))
    if not info.docker_ok:
        return report.error(ctx, exit_codes.DOCKER_MISSING, "; ".join(info.problems))
    return exit_codes.OK
