"""grdm-dev upstream mirror | integrate — placeholder for SPEC-05 upstream tracking.

Not implemented in M2. The daily mirror and the weekly integration are specified in
docs/spec/05_upstream_tracking.md and need Git credentials for the private -dev2027 repositories,
so they never run in this repository's CI (SPEC-02 §3). Both subcommands exit 2 with that message
until the SPEC-05 implementation lands.
"""
from __future__ import annotations

import sys

from . import exit_codes
from .context import Context

NOT_IMPLEMENTED = (
    "grdm-dev upstream {action} is not implemented in M2; see docs/spec/05_upstream_tracking.md "
    "(SPEC-05) for the mirror / integrate procedure to run by hand."
)


def register(subparsers) -> None:
    p = subparsers.add_parser("upstream", help="daily mirror / weekly integration of SPEC-05 (not implemented in M2)")
    sub = p.add_subparsers(dest="upstream_action", metavar="<mirror|integrate>")
    sub.add_parser("mirror", help="mirror upstream branches into the -dev2027 repositories (SPEC-05)")
    sub.add_parser("integrate", help="weekly integration merge (SPEC-05)")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args) -> int:
    action = getattr(args, "upstream_action", None) or "<mirror|integrate>"
    sys.stderr.write("[grdm-dev] exit 2: " + NOT_IMPLEMENTED.format(action=action) + "\n")
    return exit_codes.USAGE
