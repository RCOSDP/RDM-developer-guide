"""grdm-dev install — the SPEC-02 §2.1 sequence, stopping at the first non-zero step.

    doctor → plan → secrets init (skipped when runtime/.env exists) → compose render → build
    → up → health --network → scan (if the module exists) → report

Each step is run through the normal CLI parser so that every sibling module keeps ownership of its
own flags: the step's argv is parsed with cli.build_parser() and `args._module.run(ctx, args)` is
called. Modules are imported lazily by the parser, so a step whose module is not yet implemented
is reported as "not available" — fatal for required steps, a notice for optional ones (scan, report).

Tests inject `run_step(ctx, argv) -> int` and never touch Docker.
"""
from __future__ import annotations

import sys
from collections.abc import Callable

from . import exit_codes, report
from .context import Context

OPTIONAL_STEPS: frozenset[str] = frozenset({"scan", "report"})


def default_run_step(ctx: Context, argv: list[str]) -> int:
    """Parse argv with the real parser and run the matching module. Returns -1 when the subcommand is missing."""
    from . import cli

    parser = cli.build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return -1
    mod = getattr(args, "_module", None)
    if mod is None:
        return -1
    return int(mod.run(ctx, args))


def plan_steps(ctx: Context, *, platform: str | None, no_open: bool, memory_gib: float | None = None) -> list[tuple[str, list[str]]]:
    from .secrets import env_path

    memory = ["--memory-gib", f"{memory_gib:g}"] if memory_gib else []
    steps: list[tuple[str, list[str]]] = [("doctor", ["doctor"] + memory), ("plan", ["plan"])]
    if not env_path(ctx).exists():
        steps.append(("secrets init", ["secrets", "init"]))
    steps.append(("compose render", ["compose", "render"] + memory))
    build = ["build"] + (["--platform", platform] if platform else [])
    steps.append(("build", build))
    steps.append(("up", ["up"] + (["--no-open"] if no_open else [])))
    steps.append(("health --network", ["health", "--network"]))
    steps.append(("scan", ["scan"]))
    steps.append(("report", ["report"]))
    return steps


def register(subparsers) -> None:
    p = subparsers.add_parser("install", help="doctor → plan → secrets → compose → build → up → health → scan → report")
    p.add_argument("--platform", help="comma-separated platforms for build (default: host platform)")
    p.add_argument("--no-open", dest="no_open", action="store_true", help="do not open the browser after up")
    p.add_argument("--memory-gib", type=float, help="passed to doctor and compose render: overcommit knowingly when the profile's memory floors do not fit")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, run_step: Callable[[Context, list[str]], int] | None = None) -> int:
    from .lifecycle import web_url
    from .secrets import env_path

    run_step = run_step or default_run_step
    steps = plan_steps(ctx, platform=getattr(args, "platform", None), no_open=bool(getattr(args, "no_open", False)),
                       memory_gib=getattr(args, "memory_gib", None))
    skipped_secrets = env_path(ctx).exists()
    rows: list[dict] = []
    if skipped_secrets:
        rows.append({"step": "secrets init", "code": 0, "status": "skipped (runtime/.env exists)"})
    final = exit_codes.OK
    for name, argv in steps:
        sys.stderr.write(f"[grdm-dev] install: {name}\n")
        code = run_step(ctx, argv)
        if code == -1:
            key = argv[0]
            if key in OPTIONAL_STEPS:
                sys.stderr.write(f"[grdm-dev] install: `{name}` is not yet available; continuing\n")
                rows.append({"step": name, "code": 0, "status": "not available"})
                continue
            rows.append({"step": name, "code": exit_codes.USAGE, "status": "not available"})
            final = exit_codes.USAGE
            report.emit(ctx, "install", {"steps": rows, "result": final, "url": None})
            return report.error(ctx, exit_codes.USAGE, f"required step `{name}` is not available in this build of grdm-dev")
        rows.append({"step": name, "code": code, "status": "ok" if code == 0 else "failed"})
        if code != 0:
            final = code
            break
    url = web_url(ctx) if final == exit_codes.OK else None
    report.emit(ctx, "install", {"steps": rows, "result": final, "url": url})
    if final != exit_codes.OK:
        failed = next((r["step"] for r in rows if r["status"] == "failed"), "?")
        return report.error(ctx, final, f"stopped at `{failed}`")
    sys.stdout.write(f"\nGakuNin RDM developer environment is ready: {url}\n")
    return exit_codes.OK
