"""grdm-dev manifest check | toon — SPEC-01 validation and the TOON excerpt (SPEC-02 §3).

`check` runs the CI validator tools/manifest_check.py in-process (loaded with importlib from
<root>/tools so the two never drift) and maps its exit codes: 20 manifest invalid or TOON excerpt
disagrees with JSON (SPEC-02 §6), 1 repository policy violation (private URL / token, SPEC-01 §5),
2 usage. `toon` prints the excerpt that manifest/upstreams.toon must equal (SPEC-01 §2), built from
the validator's own projection so `check` and `toon` agree by construction.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from . import exit_codes, report, toon
from .context import Context


def register(subparsers) -> None:
    p = subparsers.add_parser("manifest", help="validate manifest/upstreams.json or print its TOON excerpt (SPEC-01)")
    sub = p.add_subparsers(dest="manifest_action", metavar="<check|toon>")
    c = sub.add_parser("check", help="validate the manifest, TOON parity and repository policy; exit 20 / 1 on failure")
    c.add_argument("--manifest-only", action="store_true", help="skip the repository policy scan")
    c.add_argument("--policy-only", action="store_true", help="run only the repository policy scan")
    t = sub.add_parser("toon", help="print the excerpt that manifest/upstreams.toon must equal")
    t.add_argument("--check", action="store_true", help="compare with manifest/upstreams.toon instead of printing; exit 20 on mismatch")
    t.add_argument("--write", action="store_true", help="write manifest/upstreams.toon")
    p.set_defaults(_module=sys.modules[__name__])


def load_tool(root: Path, name: str) -> ModuleType:
    """Import <root>/tools/<name>.py as a module without touching sys.path."""
    path = root / "tools" / f"{name}.py"
    if not path.exists():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(f"grdm_dev_tools_{name}", path)
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # @dataclass in the tool looks its module up in sys.modules
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def map_check_exit(code: int) -> int:
    """tools/manifest_check.py codes -> grdm-dev codes (they already share SPEC-02's numbers)."""
    if code == 0:
        return exit_codes.OK
    if code == 20:
        return exit_codes.MANIFEST_INVALID
    if code == 2:
        return exit_codes.USAGE
    return 1  # policy violation: SPEC-01 §5 / SPEC-06 §5, not a manifest schema error


# --------------------------------------------------------------------------- TOON excerpt

def _table(label: str, rows: list[dict[str, Any]], fields: tuple[str, ...], pad: str) -> list[str]:
    if not rows:
        return [f"{pad}{label}[0]:"]
    out = [f"{pad}{label}[{len(rows)}]{{{','.join(fields)}}}:"]
    for r in rows:
        out.append(pad + "  " + ",".join(toon._scalar(r.get(f)) for f in fields))
    return out


def excerpt(data: dict[str, Any], mc: ModuleType) -> str:
    """Render the SPEC-01 §2 projection in the layout of manifest/upstreams.toon."""
    proj = mc.project_manifest(data)
    lines: list[str] = []
    for key in ("schema_version", "generated_at", "note"):
        if key in proj:
            lines.append(f"{key}: {toon._scalar(proj[key])}")
    comps = proj.get("components", [])
    lines.append(f"components[{len(comps)}]:")
    for c in comps:
        lines.append(f"  - id: {toon._scalar(c['id'])}")
        for key in ("role", "integration_repo", "profile"):
            lines.append(f"    {key}: {toon._scalar(c.get(key))}")
        lines += _table("upstreams", c.get("upstreams", []), tuple(mc.UPSTREAM_FIELDS), "    ")
        lines += _table("adopted_prs", c.get("adopted_prs", []), ("repo", "number", "status"), "    ")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- run

def run(ctx: Context, args) -> int:
    action = getattr(args, "manifest_action", None)
    if action not in ("check", "toon"):
        sys.stderr.write("usage: grdm-dev manifest <check|toon>\n")
        return exit_codes.USAGE
    try:
        mc = load_tool(ctx.root, "manifest_check")
    except FileNotFoundError as exc:
        return report.error(ctx, exit_codes.USAGE, f"validator not found: {exc}")

    if action == "check":
        argv = ["--root", str(ctx.root)]
        if getattr(args, "manifest_only", False):
            argv.append("--manifest-only")
        if getattr(args, "policy_only", False):
            argv.append("--policy-only")
        code = map_check_exit(int(mc.main(argv)))
        if code != exit_codes.OK:
            return report.error(ctx, code, "see the findings above")
        return code

    try:
        data = json.loads(ctx.manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, f"{ctx.manifest_path}: {exc}")
    if mc.validate_structure(data):
        return report.error(ctx, exit_codes.MANIFEST_INVALID, "manifest fails structural checks; run manifest check")
    text = excerpt(data, mc)
    toon_path = ctx.root / "manifest" / "upstreams.toon"
    if getattr(args, "write", False):
        toon_path.write_text(text, encoding="utf-8")
        sys.stdout.write(f"wrote {toon_path}\n")
        return exit_codes.OK
    if getattr(args, "check", False):
        current = toon_path.read_text(encoding="utf-8") if toon_path.exists() else ""
        if current != text:
            return report.error(ctx, exit_codes.MANIFEST_INVALID, f"{toon_path} differs from the generated excerpt")
        sys.stdout.write(f"{toon_path} is up to date\n")
        return exit_codes.OK
    sys.stdout.write(text)
    return exit_codes.OK
