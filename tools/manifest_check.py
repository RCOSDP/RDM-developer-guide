#!/usr/bin/env python3
"""
manifest_check.py - Validate manifest/upstreams.json, its TOON excerpt, and the
repository-wide private-URL / token policy (SPEC-01 §5, SPEC-06 §5).

Standard library only, Python 3.11+. Run from the repository root:

    python3 tools/manifest_check.py                 # manifest + TOON parity + policy scan
    python3 tools/manifest_check.py --manifest-only # SPEC-01 checks only
    python3 tools/manifest_check.py --policy-only   # repository policy scan only

Checks implemented (ids from docs/spec/01_manifest.md §5):

  MC-01  upstreams.json parses as JSON, schema_version == 1, generated_at is an ISO date
  MC-02  component id unique and matches ^[A-Za-z0-9_.-]+$
  MC-03  role in core|infra|subsystem; services is a non-empty list of strings
  MC-04  integration_repo matches ^RDM-[A-Za-z0-9_.-]+-dev2027$, or null for infra
  MC-05  integration_branch == "develop", or null for infra
  MC-06  every upstreams[].sha is ^[0-9a-f]{40}$; base_image_digest is null or
         sha256:<64 hex>; fetched_at is an ISO date not in the future
  MC-07  no string value anywhere contains http, git@, github.com, or a token-like string
  MC-08  the same (repo, branch) pair has one sha across all components
  MC-09  adopted_prs status == adopted; candidate_prs status in candidate|rejected;
         upstreams status in merged|reference|candidate and kind cos => reference;
         PR number is a positive integer
  MC-10  profile in minimum|core|full; platforms subset of linux/arm64,linux/amd64;
         core components list both platforms
  MC-11  upstreams.toon exists and its projection equals the JSON (every component id,
         every upstream field, every adopted PR (repo, number, status), top-level fields,
         and all counts). A missing or stale TOON fails.
  MC-13  tracking_branch follows rule 7: upstream/<kind>[-<tag>]-<branch with / -> ->
  MC-12  (--remote) is NOT implemented here; it runs in the private -dev2027 CI.

Policy scan (not an MC check; SPEC-01 rule 5, SPEC-06 §5): every git-tracked
text file except site/, *.legacy.md and sample-code directories under
docs/guides/<guide>/ is scanned for
  - URLs to private repositories: github.com/RCOSDP/<name>-private or -dev2027
    (https form and ssh form git@github.com:RCOSDP/...),
  - token-like strings: ghp_/gho_/ghu_/ghs_/ghr_, github_pat_, AKIA..., xox[abprs]-,
  - private key blocks: -----BEGIN ... PRIVATE KEY-----.

Exit codes (aligned with SPEC-02 §6):
  0   all checks passed
  1   policy violation(s) found in tracked files (manifest itself valid)
  20  manifest invalid or TOON excerpt disagrees with JSON (takes precedence over 1)
  2   usage error
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_POLICY = 1
EXIT_USAGE = 2
EXIT_MANIFEST = 20

MANIFEST_JSON = Path("manifest/upstreams.json")
MANIFEST_TOON = Path("manifest/upstreams.toon")

ROLES = {"core", "infra", "subsystem"}
KINDS = {"public", "private", "cos"}
UPSTREAM_STATUSES = {"merged", "reference", "candidate"}
ADOPTED_STATUSES = {"adopted"}
CANDIDATE_STATUSES = {"candidate", "rejected"}
PROFILES = {"minimum", "core", "full"}
PLATFORMS = {"linux/arm64", "linux/amd64"}

RE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
RE_SHA = re.compile(r"^[0-9a-f]{40}$")
RE_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
RE_INTEGRATION_REPO = re.compile(r"^RDM-[A-Za-z0-9_.-]+-dev2027$")
RE_REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?$")

UPSTREAM_FIELDS = ("repo", "branch", "kind", "tracking_branch", "status", "sha", "fetched_at")
PR_FIELDS = ("repo", "number", "title", "reason", "status")
COMPONENT_FIELDS = (
    "id", "role", "services", "integration_repo", "integration_branch", "upstreams",
    "adopted_prs", "candidate_prs", "base_image", "base_image_digest", "target_image",
    "profile", "platforms",
)

# Token-like strings (MC-07 and policy scan). Built so that this source file
# itself never matches: each pattern needs the token body after the prefix.
TOKEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Private repository URLs (policy scan): the https, scp-style ssh (git@host:org/repo)
# and ssh:// forms of a github.com/RCOSDP repository whose name ends in -private
# or -dev2027, with or without a .git suffix. (No literal example here: this
# file is itself scanned.)
RE_PRIVATE_URL = re.compile(
    r"(?i)(?:https?://|ssh://)?(?:git@)?github\.com[/:]RCOSDP/[A-Za-z0-9_.-]*?(?:-private|-dev2027)(?:\.git)?\b"
)

POLICY_EXCLUDED_PREFIXES = ("site/",)
POLICY_TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".toon", ".toml", ".yml", ".yaml", ".py", ".js", ".ts", ".html",
    ".css", ".sh", ".cfg", ".ini", ".tsv", ".csv", ".xml", ".svg", ".mako", ".rst", "",
}


# --------------------------------------------------------------------------- helpers

def _is_iso_date(value: Any) -> _dt.date | None:
    if not isinstance(value, str):
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        return None


def _walk_strings(value: Any, path: str = "$"):
    """Yield (json_path, string) for every string inside a JSON value."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from _walk_strings(v, f"{path}[{i}]")


def expected_tracking_branch(kind: str, branch: str) -> str:
    """Rule 7 without a tag: upstream/<kind>-<branch with / replaced by ->."""
    return f"upstream/{kind}-{branch.replace('/', '-')}"


def tracking_branch_ok(tracking_branch: str, kind: str, branch: str, same_kind_count: int) -> bool:
    """Rule 7: upstream/<kind>-<branch>; with 2+ upstreams of one kind in a component the
    second may insert a tag: upstream/<kind>-<tag>-<branch>."""
    plain = expected_tracking_branch(kind, branch)
    if tracking_branch == plain:
        return True
    if same_kind_count >= 2:
        suffix = "-" + branch.replace("/", "-")
        prefix = f"upstream/{kind}-"
        if tracking_branch.startswith(prefix) and tracking_branch.endswith(suffix):
            tag = tracking_branch[len(prefix):-len(suffix)]
            return bool(tag) and RE_ID.match(tag) is not None
    return False


# --------------------------------------------------------------------------- JSON checks

def validate_manifest(data: Any, today: _dt.date | None = None) -> list[str]:
    """Return a list of findings (empty == valid) for the parsed JSON manifest.
    Implements MC-01..MC-10 and MC-13."""
    today = today or _dt.date.today()
    errors: list[str] = []

    # MC-01
    if not isinstance(data, dict):
        return ["MC-01: top level must be a JSON object"]
    if data.get("schema_version") != 1:
        errors.append(f"MC-01: schema_version must be the integer 1 (got {data.get('schema_version')!r})")
    if _is_iso_date(data.get("generated_at")) is None:
        errors.append(f"MC-01: generated_at must be an ISO date (got {data.get('generated_at')!r})")
    components = data.get("components")
    if not isinstance(components, list):
        errors.append("MC-01: components must be a list")
        return errors

    seen_ids: set[str] = set()
    sha_by_repo_branch: dict[tuple[str, str], dict[str, set[str]]] = {}

    for idx, comp in enumerate(components):
        label = f"components[{idx}]"
        if not isinstance(comp, dict):
            errors.append(f"MC-01: {label} must be an object")
            continue
        comp_id = comp.get("id")
        if isinstance(comp_id, str) and comp_id:
            label = f"component '{comp_id}'"

        for field in COMPONENT_FIELDS:
            if field not in comp:
                errors.append(f"MC-01: {label}: missing required field '{field}'")

        # MC-02
        if not isinstance(comp_id, str) or not RE_ID.match(comp_id):
            errors.append(f"MC-02: {label}: id must match ^[A-Za-z0-9_.-]+$ (got {comp_id!r})")
        elif comp_id in seen_ids:
            errors.append(f"MC-02: duplicate component id '{comp_id}'")
        else:
            seen_ids.add(comp_id)

        # MC-03
        role = comp.get("role")
        if role not in ROLES:
            errors.append(f"MC-03: {label}: role must be one of {sorted(ROLES)} (got {role!r})")
        services = comp.get("services")
        if not isinstance(services, list) or not services or not all(isinstance(s, str) and s for s in services):
            errors.append(f"MC-03: {label}: services must be a non-empty list of strings (got {services!r})")

        # MC-04
        repo = comp.get("integration_repo")
        if role == "infra":
            if repo is not None:
                errors.append(f"MC-04: {label}: integration_repo must be null for infra (got {repo!r})")
        elif not isinstance(repo, str) or not RE_INTEGRATION_REPO.match(repo):
            errors.append(f"MC-04: {label}: integration_repo must match ^RDM-[A-Za-z0-9_.-]+-dev2027$ (got {repo!r})")

        # MC-05
        branch = comp.get("integration_branch")
        if role == "infra":
            if branch is not None:
                errors.append(f"MC-05: {label}: integration_branch must be null for infra (got {branch!r})")
        elif branch != "develop":
            errors.append(f"MC-05: {label}: integration_branch must be 'develop' (got {branch!r})")

        # MC-06 base_image_digest
        digest = comp.get("base_image_digest")
        if digest is not None and (not isinstance(digest, str) or not RE_DIGEST.match(digest)):
            errors.append(f"MC-06: {label}: base_image_digest must be null or sha256:<64 hex> (got {digest!r})")
        if not isinstance(comp.get("base_image"), str) or not comp.get("base_image"):
            errors.append(f"MC-01: {label}: base_image must be a non-empty string")
        target = comp.get("target_image")
        if not isinstance(target, dict) or set(target.keys()) != {"M4", "M5"}:
            errors.append(f"MC-01: {label}: target_image must be an object with exactly the keys M4 and M5")

        # upstreams: MC-06, MC-08, MC-09, MC-13
        upstreams = comp.get("upstreams")
        if not isinstance(upstreams, list):
            errors.append(f"MC-01: {label}: upstreams must be a list")
            upstreams = []
        if role == "infra" and upstreams:
            errors.append(f"MC-01: {label}: upstreams must be empty for infra")
        kind_counts: dict[str, int] = {}
        for up in upstreams:
            if isinstance(up, dict) and isinstance(up.get("kind"), str):
                kind_counts[up["kind"]] = kind_counts.get(up["kind"], 0) + 1
        for uidx, up in enumerate(upstreams):
            ulabel = f"{label} upstreams[{uidx}]"
            if not isinstance(up, dict):
                errors.append(f"MC-01: {ulabel}: must be an object")
                continue
            for field in UPSTREAM_FIELDS:
                if field not in up:
                    errors.append(f"MC-01: {ulabel}: missing required field '{field}'")
            urepo, ubranch, kind = up.get("repo"), up.get("branch"), up.get("kind")
            if not isinstance(urepo, str) or not RE_REPO_NAME.match(urepo):
                errors.append(f"MC-01: {ulabel}: repo must be a bare name (got {urepo!r})")
            if not isinstance(ubranch, str) or not ubranch:
                errors.append(f"MC-01: {ulabel}: branch must be a non-empty string (got {ubranch!r})")
            if kind not in KINDS:
                errors.append(f"MC-09: {ulabel}: kind must be one of {sorted(KINDS)} (got {kind!r})")
            status = up.get("status")
            if status not in UPSTREAM_STATUSES:
                errors.append(f"MC-09: {ulabel}: status must be one of {sorted(UPSTREAM_STATUSES)} (got {status!r})")
            elif kind == "cos" and status != "reference":
                errors.append(f"MC-09: {ulabel}: cos upstreams must have status 'reference' (got {status!r})")
            sha = up.get("sha")
            if not isinstance(sha, str) or not RE_SHA.match(sha):
                errors.append(f"MC-06: {ulabel}: sha must match ^[0-9a-f]{{40}}$ (got {sha!r})")
            fetched = _is_iso_date(up.get("fetched_at"))
            if fetched is None:
                errors.append(f"MC-06: {ulabel}: fetched_at must be an ISO date (got {up.get('fetched_at')!r})")
            elif fetched > today:
                errors.append(f"MC-06: {ulabel}: fetched_at {fetched} is in the future (today {today})")
            tb = up.get("tracking_branch")
            if isinstance(urepo, str) and isinstance(ubranch, str) and kind in KINDS:
                if not isinstance(tb, str) or not tracking_branch_ok(tb, kind, ubranch, kind_counts.get(kind, 0)):
                    errors.append(
                        f"MC-13: {ulabel}: tracking_branch {tb!r} does not follow rule 7 "
                        f"(expected {expected_tracking_branch(kind, ubranch)!r}"
                        f"{' or upstream/' + kind + '-<tag>-' + ubranch.replace('/', '-') if kind_counts.get(kind, 0) >= 2 else ''})"
                    )
                if isinstance(sha, str):
                    sha_by_repo_branch.setdefault((urepo, ubranch), {}).setdefault(sha, set()).add(str(comp_id))

        # PR lists: MC-09
        for list_name, allowed in (("adopted_prs", ADOPTED_STATUSES), ("candidate_prs", CANDIDATE_STATUSES)):
            prs = comp.get(list_name)
            if not isinstance(prs, list):
                errors.append(f"MC-01: {label}: {list_name} must be a list")
                continue
            for pidx, pr in enumerate(prs):
                plabel = f"{label} {list_name}[{pidx}]"
                if not isinstance(pr, dict):
                    errors.append(f"MC-01: {plabel}: must be an object")
                    continue
                for field in PR_FIELDS:
                    if field not in pr:
                        errors.append(f"MC-01: {plabel}: missing required field '{field}'")
                number = pr.get("number")
                if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
                    errors.append(f"MC-09: {plabel}: number must be a positive integer (got {number!r})")
                if pr.get("status") not in allowed:
                    errors.append(f"MC-09: {plabel}: status must be one of {sorted(allowed)} (got {pr.get('status')!r})")
                if not isinstance(pr.get("repo"), str) or not RE_REPO_NAME.match(pr.get("repo") or ""):
                    errors.append(f"MC-01: {plabel}: repo must be a bare name (got {pr.get('repo')!r})")

        # MC-10
        profile = comp.get("profile")
        if profile not in PROFILES:
            errors.append(f"MC-10: {label}: profile must be one of {sorted(PROFILES)} (got {profile!r})")
        platforms = comp.get("platforms")
        if not isinstance(platforms, list) or not set(platforms) <= PLATFORMS or not platforms:
            errors.append(f"MC-10: {label}: platforms must be a non-empty subset of {sorted(PLATFORMS)} (got {platforms!r})")
        elif role == "core" and set(platforms) != PLATFORMS:
            errors.append(f"MC-10: {label}: core components must list both platforms (got {platforms!r})")

    # MC-08
    for (urepo, ubranch), shas in sorted(sha_by_repo_branch.items()):
        if len(shas) > 1:
            detail = "; ".join(f"{s} in {sorted(c)}" for s, c in sorted(shas.items()))
            errors.append(f"MC-08: upstream ({urepo}, {ubranch}) pinned to different SHAs: {detail}")

    # MC-07
    errors.extend(f"MC-07: {e}" for e in find_forbidden_strings(data))
    return errors


def find_forbidden_strings(data: Any) -> list[str]:
    """MC-07: no string value contains http, git@, github.com or a token-like string."""
    errors: list[str] = []
    for path, value in _walk_strings(data):
        low = value.lower()
        if "http" in low or "git@" in low or "github.com" in low:
            errors.append(f"{path}: value must not contain http/git@/github.com (names only, rule 5)")
        for name, pattern in TOKEN_PATTERNS:
            if pattern.search(value):
                errors.append(f"{path}: value looks like a {name}")
    return errors


# --------------------------------------------------------------------------- TOON parsing

class ToonError(ValueError):
    pass


def _split_csv(row: str) -> list[str]:
    """Split one TOON tabular row on commas, honouring double quotes."""
    out: list[str] = []
    buf: list[str] = []
    in_q = False
    i = 0
    while i < len(row):
        ch = row[i]
        if in_q:
            if ch == "\\" and i + 1 < len(row):
                buf.append(row[i + 1])
                i += 2
                continue
            if ch == '"':
                in_q = False
            else:
                buf.append(ch)
        elif ch == '"':
            in_q = True
        elif ch == ",":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [v.strip() for v in out]


def _scalar(text: str) -> Any:
    text = text.strip()
    if text == "":
        return ""
    if text.startswith('"') and text.endswith('"') and len(text) >= 2:
        return json.loads(text)
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


_RE_KEY = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)(?:\[(?P<n>\d+)\](?:\{(?P<fields>[^}]*)\})?)?:(?P<rest>.*)$")


def parse_toon(text: str) -> dict[str, Any]:
    """Parse the TOON excerpt format of SPEC-01 §2 into Python data.

    Supports: `key: value`, `key[N]: a,b,c` (inline list), `key[N]:` followed by N
    `- key: value` list items (each item's other fields indented under it),
    `key[N]{f1,f2}:` followed by N CSV rows, and nested `key:` objects.
    Raises ToonError on shape errors (wrong counts, bad indentation)."""
    raw_lines = text.splitlines()
    lines: list[tuple[int, str, int]] = []  # (indent, content, lineno)
    for n, raw in enumerate(raw_lines, 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip(), n))

    pos = 0

    def parse_block(indent: int) -> dict[str, Any]:
        nonlocal pos
        obj: dict[str, Any] = {}
        while pos < len(lines):
            ind, content, lineno = lines[pos]
            if ind < indent:
                break
            if ind > indent:
                raise ToonError(f"line {lineno}: unexpected indentation")
            if content.startswith("- "):
                break
            m = _RE_KEY.match(content)
            if not m:
                raise ToonError(f"line {lineno}: cannot parse {content!r}")
            key, n, fields, rest = m.group("key"), m.group("n"), m.group("fields"), m.group("rest").strip()
            pos += 1
            if n is None and fields is None:
                if rest:
                    obj[key] = _scalar(rest)
                else:  # nested object
                    obj[key] = parse_block(_child_indent(indent))
                continue
            count = int(n)
            if fields is not None:  # tabular rows
                names = [f.strip() for f in fields.split(",")] if fields.strip() else []
                rows: list[dict[str, Any]] = []
                for _ in range(count):
                    if pos >= len(lines) or lines[pos][0] <= indent:
                        raise ToonError(f"line {lineno}: {key}[{count}] declares {count} rows but fewer follow")
                    rind, rcontent, rlineno = lines[pos]
                    values = _split_csv(rcontent)
                    if len(values) != len(names):
                        raise ToonError(f"line {rlineno}: row has {len(values)} values, header has {len(names)}")
                    rows.append({k: _scalar(v) for k, v in zip(names, values)})
                    pos += 1
                if pos < len(lines) and lines[pos][0] > indent and not lines[pos][1].startswith("- "):
                    raise ToonError(f"line {lineno}: {key}[{count}] has more rows than declared")
                obj[key] = rows
                continue
            if rest:  # inline primitive list
                items = [_scalar(v) for v in _split_csv(rest)] if count else []
                if len(items) != count:
                    raise ToonError(f"line {lineno}: {key}[{count}] has {len(items)} inline values")
                obj[key] = items
                continue
            # list of objects: `- field: value` items
            items_obj: list[Any] = []
            for _ in range(count):
                if pos >= len(lines) or lines[pos][0] <= indent or not lines[pos][1].startswith("- "):
                    raise ToonError(f"line {lineno}: {key}[{count}] declares {count} items but fewer follow")
                iind, icontent, ilineno = lines[pos]
                # rewrite "- k: v" as "k: v" at indent iind+2 and parse the item as a block
                lines[pos] = (iind + 2, icontent[2:].strip(), ilineno)
                items_obj.append(parse_block(iind + 2))
            if pos < len(lines) and lines[pos][0] > indent:
                raise ToonError(f"line {lineno}: {key}[{count}] has more items than declared")
            obj[key] = items_obj
        return obj

    def _child_indent(indent: int) -> int:
        if pos < len(lines) and lines[pos][0] > indent:
            return lines[pos][0]
        return indent + 2

    result = parse_block(lines[0][0] if lines else 0)
    if pos != len(lines):
        raise ToonError(f"line {lines[pos][2]}: trailing content {lines[pos][1]!r}")
    return result


def project_manifest(data: dict[str, Any]) -> dict[str, Any]:
    """The projection of the JSON that upstreams.toon must equal (SPEC-01 §2)."""
    out: dict[str, Any] = {"schema_version": data.get("schema_version"), "generated_at": data.get("generated_at")}
    if "note" in data:
        out["note"] = data["note"]
    comps = []
    for c in data.get("components", []):
        comps.append({
            "id": c.get("id"),
            "role": c.get("role"),
            "integration_repo": c.get("integration_repo"),
            "profile": c.get("profile"),
            "upstreams": [{f: u.get(f) for f in UPSTREAM_FIELDS} for u in c.get("upstreams", [])],
            "adopted_prs": [{f: p.get(f) for f in ("repo", "number", "status")} for p in c.get("adopted_prs", [])],
        })
    out["components"] = comps
    return out


def compare_toon(json_data: dict[str, Any], toon_data: dict[str, Any]) -> list[str]:
    """MC-11: every id, upstream and adopted PR in the TOON equals the JSON, counts match."""
    errors: list[str] = []
    expected = project_manifest(json_data)
    for key in ("schema_version", "generated_at", "note"):
        if key in expected and toon_data.get(key) != expected[key]:
            errors.append(f"MC-11: top-level {key}: TOON {toon_data.get(key)!r} != JSON {expected[key]!r}")
    tcomps = toon_data.get("components")
    if not isinstance(tcomps, list):
        return errors + ["MC-11: TOON has no components[] list"]
    if len(tcomps) != len(expected["components"]):
        errors.append(f"MC-11: component count: TOON {len(tcomps)} != JSON {len(expected['components'])}")
    jmap = {c["id"]: c for c in expected["components"]}
    tids = [c.get("id") for c in tcomps if isinstance(c, dict)]
    for cid in jmap:
        if cid not in tids:
            errors.append(f"MC-11: component '{cid}' is in JSON but missing from TOON")
    for tc in tcomps:
        if not isinstance(tc, dict):
            errors.append("MC-11: TOON component is not an object")
            continue
        cid = tc.get("id")
        jc = jmap.get(cid)
        if jc is None:
            errors.append(f"MC-11: component '{cid}' is in TOON but not in JSON")
            continue
        for key in ("role", "integration_repo", "profile"):
            if tc.get(key) != jc[key]:
                errors.append(f"MC-11: component '{cid}' {key}: TOON {tc.get(key)!r} != JSON {jc[key]!r}")
        tups = tc.get("upstreams") if isinstance(tc.get("upstreams"), list) else []
        if "upstreams" not in tc or not isinstance(tc.get("upstreams"), list):
            errors.append(f"MC-11: component '{cid}' has no upstreams[] in TOON")
        if len(tups) != len(jc["upstreams"]):
            errors.append(f"MC-11: component '{cid}' upstream count: TOON {len(tups)} != JSON {len(jc['upstreams'])}")
        for i, (tu, ju) in enumerate(zip(tups, jc["upstreams"])):
            for f in UPSTREAM_FIELDS:
                if tu.get(f) != ju.get(f):
                    errors.append(f"MC-11: component '{cid}' upstreams[{i}].{f}: TOON {tu.get(f)!r} != JSON {ju.get(f)!r}")
        tprs = tc.get("adopted_prs") if isinstance(tc.get("adopted_prs"), list) else []
        if "adopted_prs" not in tc or not isinstance(tc.get("adopted_prs"), list):
            errors.append(f"MC-11: component '{cid}' has no adopted_prs[] in TOON")
        if len(tprs) != len(jc["adopted_prs"]):
            errors.append(f"MC-11: component '{cid}' adopted_prs count: TOON {len(tprs)} != JSON {len(jc['adopted_prs'])}")
        for i, (tp, jp) in enumerate(zip(tprs, jc["adopted_prs"])):
            for f in ("repo", "number", "status"):
                if tp.get(f) != jp.get(f):
                    errors.append(f"MC-11: component '{cid}' adopted_prs[{i}].{f}: TOON {tp.get(f)!r} != JSON {jp.get(f)!r}")
    return errors


def validate_toon_parity(json_data: dict[str, Any], toon_path: Path) -> list[str]:
    if not toon_path.exists():
        return [f"MC-11: {toon_path} is missing (the TOON excerpt is required)"]
    try:
        toon_data = parse_toon(toon_path.read_text(encoding="utf-8"))
    except (ToonError, json.JSONDecodeError, UnicodeDecodeError) as e:
        return [f"MC-11: {toon_path} does not parse: {e}"]
    return compare_toon(json_data, toon_data)


# --------------------------------------------------------------------------- policy scan

def policy_excluded(rel_path: str) -> bool:
    """Files the policy scan skips: generated site/, verbatim legacy guides, and sample
    code directories under docs/guides/<guide>/ (the guide README stays scanned)."""
    if rel_path.startswith(POLICY_EXCLUDED_PREFIXES):
        return True
    if rel_path.endswith(".legacy.md"):
        return True
    parts = rel_path.split("/")
    if len(parts) >= 5 and parts[0] == "docs" and parts[1] == "guides":
        return True  # docs/guides/<guide>/<subdir>/... (sample code); the guide's own *.md stay scanned
    return False


def scan_text_for_policy(text: str, rel_path: str) -> list[str]:
    """Return findings for private URLs, token-like strings and private keys in text."""
    findings: list[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in RE_PRIVATE_URL.finditer(line):
            # Report the repository *name* only; the URL itself is never echoed.
            name = re.split(r"[/:]", m.group(0))[-1].removesuffix(".git")
            findings.append(f"{rel_path}:{lineno}: URL to private repository '{name}' (names only, SPEC-01 rule 5)")
        for name, pattern in TOKEN_PATTERNS:
            if pattern.search(line):
                findings.append(f"{rel_path}:{lineno}: {name} pattern found (value redacted)")
    return findings


def git_tracked_files(root: Path) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    ).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def run_policy_scan(root: Path, files: list[str] | None = None) -> list[str]:
    findings: list[str] = []
    files = git_tracked_files(root) if files is None else files
    for rel in files:
        if policy_excluded(rel):
            continue
        path = root / rel
        if not path.is_file():
            continue
        if Path(rel).suffix.lower() not in POLICY_TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: not a text policy target
        findings.extend(scan_text_for_policy(text, rel))
    return findings


# --------------------------------------------------------------------------- CLI

def check_manifest_files(json_path: Path, toon_path: Path) -> list[str]:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"MC-01: {json_path} not found"]
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        return [f"MC-01: {json_path} is not valid JSON: {e}"]
    errors = validate_manifest(data)
    if isinstance(data, dict):
        errors.extend(validate_toon_parity(data, toon_path))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="manifest_check.py",
        description="SPEC-01 manifest validation (MC-01..MC-11, MC-13) and repository policy scan.",
        epilog="Exit codes: 0 pass; 1 policy violation; 20 manifest invalid or TOON excerpt "
               "disagrees with JSON (SPEC-02 §6); 2 usage error.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--manifest-only", action="store_true", help="run only the SPEC-01 manifest and TOON checks")
    mode.add_argument("--policy-only", action="store_true", help="run only the repository-wide private-URL/token scan")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    json_path, toon_path = root / MANIFEST_JSON, root / MANIFEST_TOON

    print("=" * 70)
    print("manifest_check.py - SPEC-01 manifest validation and policy scan")
    print("=" * 70)

    manifest_errors: list[str] = []
    policy_findings: list[str] = []

    if not args.policy_only:
        if not json_path.exists():
            print(f"Error: {json_path} not found. Run from the repository root.", file=sys.stderr)
            return EXIT_MANIFEST
        manifest_errors = check_manifest_files(json_path, toon_path)
        print(f"\n[manifest] {MANIFEST_JSON} + {MANIFEST_TOON}: {len(manifest_errors)} finding(s)")
        for e in manifest_errors:
            print(f"  - {e}")

    if not args.manifest_only:
        try:
            findings = run_policy_scan(root)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error: git ls-files failed ({e}); the policy scan needs a Git checkout.", file=sys.stderr)
            return EXIT_POLICY
        policy_findings = findings
        print(f"\n[policy] tracked text files: {len(policy_findings)} finding(s)")
        for f in policy_findings:
            print(f"  - {f}")

    print("\n" + "=" * 70)
    if manifest_errors:
        print(f"FAILED: manifest invalid ({len(manifest_errors)} finding(s)) -> exit {EXIT_MANIFEST}")
        print("=" * 70)
        return EXIT_MANIFEST
    if policy_findings:
        print(f"FAILED: policy violations ({len(policy_findings)}) -> exit {EXIT_POLICY}")
        print("=" * 70)
        return EXIT_POLICY
    print("PASSED")
    print("=" * 70)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
