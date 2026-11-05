"""grdm-dev redteam preflight — isolation checks before an AI red-team run (SPEC-02 §3, SPEC-03 §6).

Checks, all read-only and none of them an attack:
  1. an approval record `docs/demo/*_redteam_*.md` exists ("no record, no run");
  2. the red-team Compose network exists and has `internal: true` (`docker network inspect`);
  3. a throw-away probe container on that network cannot reach an external address
     (`docker run --rm --pull never --network <net> alpine wget ... http://example.invalid`);
  4. every container attached to that network is one of the targets in manifest/redteam-targets.json.

Exit 53 if any check fails, 20 if the targets manifest is missing or malformed, 0 otherwise.
External commands go through an injectable `runner(argv) -> (returncode, output)`.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from . import exit_codes, report
from .context import Context

PROBE_URL = "http://example.invalid"  # RFC 2606: never resolves; a reply proves a route or a resolver leak
PROBE_MARKER = "GRDM_EGRESS_REACHABLE"
REQUIRED_KEYS = ("project", "network", "targets")


def register(subparsers) -> None:
    p = subparsers.add_parser("redteam", help="AI red-team helpers (preflight only; never runs attacks)")
    sub = p.add_subparsers(dest="redteam_command", metavar="<action>")
    pre = sub.add_parser("preflight", help="verify no egress and targets only from manifest/redteam-targets.json; exit 53 on failure")
    pre.add_argument("--targets", help="path to the targets manifest (default: manifest/redteam-targets.json)")
    pre.add_argument("--approval", help="path to the approval record (default: newest docs/demo/*_redteam_*.md)")
    p.set_defaults(_module=sys.modules[__name__])


def default_runner(argv: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        return 127, str(exc)
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def load_targets(path: Path) -> dict:
    """Parse and validate the targets manifest. Raises ValueError with a readable reason."""
    if not path.exists():
        raise ValueError(f"{path} not found")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be an object")
    for k in REQUIRED_KEYS:
        if k not in data:
            raise ValueError(f"{path}: missing key {k!r}")
    if not isinstance(data["targets"], list) or not data["targets"] or not all(isinstance(t, str) and t for t in data["targets"]):
        raise ValueError(f"{path}: 'targets' must be a non-empty list of names")
    for k in ("project", "network"):
        if not isinstance(data[k], str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", data[k]):
            raise ValueError(f"{path}: {k!r} must be a plain Docker name")
    return data


def service_of(container_name: str, project: str) -> str:
    """Compose names containers `<project>-<service>-<n>` (or with `_` on old versions)."""
    m = re.fullmatch(rf"{re.escape(project)}[-_](.+?)[-_][0-9]+", container_name)
    return m.group(1) if m else container_name


def inspect_network(runner, network: str) -> tuple[dict | None, str]:
    rc, out = runner(["docker", "network", "inspect", network, "--format", "{{json .}}"])
    if rc != 0:
        return None, f"docker network inspect {network} failed: {out.strip()[-200:]}"
    try:
        data = json.loads(out.strip() or "null")
    except json.JSONDecodeError:
        return None, f"docker network inspect {network}: unreadable output"
    if isinstance(data, list):
        data = data[0] if data else None
    if not isinstance(data, dict):
        return None, f"network {network} not found"
    return data, ""


def probe_egress(runner, network: str) -> tuple[str, str]:
    """Return (verdict, detail): verdict is 'blocked', 'reachable', or 'inconclusive'."""
    argv = ["docker", "run", "--rm", "--pull", "never", "--network", network, "alpine", "sh", "-c",
            f"wget -T 3 -q -O- {PROBE_URL} >/dev/null 2>&1 && echo {PROBE_MARKER} || echo blocked"]
    rc, out = runner(argv)
    if PROBE_MARKER in out:
        return "reachable", f"probe fetched {PROBE_URL} from network {network}"
    if rc == 0 and "blocked" in out:
        return "blocked", "probe could not reach outside"
    return "inconclusive", f"probe container did not run (rc={rc}): {out.strip()[-200:]}"


def preflight(ctx: Context, targets_path: Path, approval: Path | None, runner) -> tuple[dict, list[str]]:
    """Run every check. Returns (report data, list of failure reasons)."""
    failures: list[str] = []
    manifest = load_targets(targets_path)  # ValueError propagates: caller maps it to exit 20
    project, network, targets = manifest["project"], manifest["network"], manifest["targets"]
    data: dict = {"project": project, "network": network, "targets": targets, "checks": []}

    def check(name: str, ok: bool, detail: str) -> None:
        data["checks"].append({"check": name, "ok": ok, "detail": detail})
        if not ok:
            failures.append(f"{name}: {detail}")

    # 1. approval record (SPEC-03 §6 rule 3)
    if approval is None:
        candidates = sorted((ctx.root / "docs" / "demo").glob("*_redteam_*.md")) if (ctx.root / "docs" / "demo").is_dir() else []
        approval = candidates[-1] if candidates else None
    if approval and approval.is_file():
        check("approval_record", True, str(approval.relative_to(ctx.root)) if approval.is_relative_to(ctx.root) else str(approval))
    else:
        check("approval_record", False, "no docs/demo/nn_redteam_<date>.md; no record, no run")

    # 2. network is internal
    net, err = inspect_network(runner, network)
    if net is None:
        check("network_internal", False, err)
        check("egress_blocked", False, "skipped: network unavailable")
        check("targets_only", False, "skipped: network unavailable")
        return data, failures
    check("network_internal", bool(net.get("Internal")), f"Internal={net.get('Internal')}")

    # 3. egress probe
    verdict, detail = probe_egress(runner, network)
    check("egress_blocked", verdict == "blocked", detail)

    # 4. attached containers are exactly our targets
    attached = sorted(c.get("Name", "") for c in (net.get("Containers") or {}).values())
    unknown = [n for n in attached if n not in targets and service_of(n, project) not in targets]
    data["attached"] = attached
    data["unknown"] = unknown
    check("targets_only", not unknown, "all attached containers are listed" if not unknown else f"outside list: {', '.join(unknown)}")
    return data, failures


def run(ctx: Context, args, runner=None) -> int:
    runner = runner or default_runner
    if getattr(args, "redteam_command", None) != "preflight":
        return report.error(ctx, exit_codes.USAGE, "usage: grdm-dev redteam preflight")
    targets_path = Path(args.targets) if getattr(args, "targets", None) else ctx.root / "manifest" / "redteam-targets.json"
    approval = Path(args.approval) if getattr(args, "approval", None) else None
    try:
        data, failures = preflight(ctx, targets_path, approval, runner)
    except ValueError as exc:
        return report.error(ctx, exit_codes.MANIFEST_INVALID, str(exc))
    data["result"] = "pass" if not failures else "fail"
    report.emit(ctx, "redteam_preflight", data)
    if failures:
        return report.error(ctx, exit_codes.REDTEAM_PREFLIGHT_FAILED, "; ".join(failures))
    return exit_codes.OK
