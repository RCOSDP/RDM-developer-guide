"""grdm-dev command line: argument parsing and subcommand dispatch (SPEC-02 §3, §5, §6)."""
from __future__ import annotations

import argparse
import importlib
import sys

from . import __version__, exit_codes
from .context import Context, find_repo_root

# Each module exposes register(subparsers) and run(ctx, args). Order = help order.
SUBCOMMAND_MODULES = [
    "doctor", "plan", "secrets", "compose", "build", "lifecycle", "health",
    "scan", "redteam", "accept", "upstream", "manifest_cmd", "docs", "report_cmd", "install",
]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="grdm-dev",
        description="GakuNin RDM developer environment 2027 — one-command installer (SPEC-02)",
    )
    p.add_argument("--version", action="version", version=f"grdm-dev {__version__}")
    _add_global_flags(p)
    p.add_argument("--root", help="repository root (default: auto-detect from manifest/upstreams.json)")
    sub = p.add_subparsers(dest="command", metavar="<command>")
    for name in SUBCOMMAND_MODULES:
        try:
            # `name` comes only from the fixed SUBCOMMAND_MODULES list above, never from user input.
            mod = importlib.import_module(f".{name}", __package__)  # nosemgrep: python.lang.security.audit.non-literal-import.non-literal-import
        except ImportError as exc:
            # A subcommand (or one of its in-package helpers) is not implemented yet: hide it from
            # help instead of breaking every other command. Errors outside this package still raise.
            missing = getattr(exc, "name", None) or ""
            if missing.startswith(__package__) or f"from '{__package__}'" in str(exc):
                continue
            raise
        mod.register(sub)
    # SPEC-02 §2.2: every subcommand accepts --json (and the other global flags) after its name too,
    # e.g. `grdm-dev doctor --json`. Add them to each sub-parser with SUPPRESS defaults so that a
    # value given in either position wins and the global default is kept otherwise.
    for sp in sub.choices.values():
        _add_global_flags_recursive(sp)
    return p


def _add_global_flags_recursive(p: argparse.ArgumentParser) -> None:
    """Add the global flags to a sub-parser and to any nested sub-parsers (e.g. `secrets init`)."""
    _add_global_flags(p, suppress=True)
    for action in p._actions:  # noqa: SLF001 - argparse has no public API for nested sub-parsers
        if isinstance(action, argparse._SubParsersAction):
            for child in action.choices.values():
                _add_global_flags_recursive(child)


def _add_global_flags(p: argparse.ArgumentParser, suppress: bool = False) -> None:
    d = argparse.SUPPRESS if suppress else None
    kw = {"default": d} if suppress else {}
    p.add_argument("--yes", action="store_true", help="answer every question with its default (required without a terminal)", **kw)
    p.add_argument("--json", dest="json_output", action="store_true", help="print reports as JSON instead of TOON", **kw)
    p.add_argument("--profile", choices=["minimum", "core", "full"], help="service profile (default: saved value or core)", **kw)
    p.add_argument("-v", "--verbose", action="store_true", **kw)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # argparse exits 2 on usage errors; keep SPEC-02's code 2
        return exit_codes.USAGE if exc.code not in (0, None) else 0
    if not getattr(args, "command", None):
        parser.print_help()
        return exit_codes.USAGE
    from pathlib import Path

    root = Path(args.root).resolve() if args.root else find_repo_root()
    ctx = Context(root=root, yes=args.yes, json_output=args.json_output, profile=args.profile, verbose=args.verbose)
    mod = getattr(args, "_module", None)  # set by each module's register(): parser.set_defaults(_module=sys.modules[__name__])
    if mod is None:
        parser.print_help()
        return exit_codes.USAGE
    try:
        return int(mod.run(ctx, args))
    except KeyboardInterrupt:
        sys.stderr.write("\ninterrupted\n")
        return exit_codes.USAGE


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
