"""grdm-dev upstream mirror | integrate — daily mirror and weekly integration of SPEC-05.

Both subcommands work on a local clone of each integration repository `RDM-<name>-dev2027`
under `--workdir` (default runtime/upstream/<integration_repo>). Clone and fetch URLs are composed
at run time from the bare names in the manifest (SPEC-01 rule 5); a `repo` that already carries
its owner (`CenterForOpenScience/osf.io`) is used as is, a bare name belongs to the RCOSDP
organization. No URL is ever written to a report.

`upstream mirror` (SPEC-05 §2), per component with an `integration_repo`:

1. fetch `origin` (the integration repository) so that `origin/develop` and the pushed
   `origin/upstream/*` branches are known; the local `upstream/<kind>-<branch>` ref is set to the
   value origin has (the previous SHA) — or deleted when origin does not have the branch yet, so a
   stale local ref left by an earlier dry-run or failed push never stands in for the published state;
2. `git fetch <source> refs/heads/<branch>:refs/heads/upstream/<kind>-<branch>` for every
   `upstreams[]` entry (merged, reference and candidate alike: rule 6 mirrors candidates too).
   The refspec has no `+`, so Git refuses a non-fast-forward: that is the force-push detection of
   SPEC-05 §1 — the old branch is kept, the row is `non-fast-forward`, the repository's action is
   `halt`, nothing is ever forced;
3. `git push origin refs/heads/upstream/X:refs/heads/upstream/X` for each branch whose fetched
   SHA differs from what origin publishes (origin lacks the branch, or its SHA is older). The
   decision is taken from the remote state, not from "did the local ref move", so a dry-run or a
   failed push followed by a real run still publishes (one explicit refspec per branch, never
   `--force`); skipped with `--dry-run`;
4. per upstream: previous SHA, new SHA, commits ahead of / behind `develop`, whether `develop`
   already contains the new SHA, whether the SHA equals the one pinned in the manifest;
5. the report (names, branches, SHAs, counts only) is written to `<report-dir>/latest.json`,
   `latest.toon` and `archive/YYYY-MM-DD.{json,toon}`; archives older than 90 days are removed.

Exit 0 whether or not anything moved; exit 70 (`UPSTREAM_FAILED`, SPEC-02 §6) when a fetch was
refused or failed, or a push failed.

`upstream integrate` (SPEC-05 §3, ADR-01 §5 strict order), per component in scope — a component
with a `public` upstream of `status: merged`. A private-only component (the five subsystems) has
nothing to reconstruct: its `develop` is seeded from `upstream/private-<branch>`, so it is
reported `skipped` with a note and no branch is made.

Starting point rule (made explicit here and tested):

* `strict`: `develop` does NOT yet contain the public tip → the branch `integrate/strict-<YYYYMMDD>`
  starts at `origin/upstream/public-<branch>` (ADR-01 §5 step 1), then the private tracking branch
  and each adopted PR are merged `--no-ff` on top. The PR to `develop` then carries the
  public-first order.
* `on-develop`: `develop` already contains the public tip (the strict order was established
  earlier) → the branch starts at `origin/develop` and only the private tracking branch and the
  adopted PRs are merged `--no-ff` on top. Starting again from the public tip would throw away
  every earlier integration.

The branch is created with `git switch -c` (never `checkout -B`): a branch of that name that
already exists on origin OR in the local clone is refused with an error, so a conflict resolution
committed by hand on the local branch (SPEC-05 §4) is never reset. Merge order never changes:
public (as the base, or already contained) → private → adopted PRs in manifest order
(`refs/pull/<n>/head` of the PR's repository). Candidate upstreams and the `cos` reference are
never merged. A conflict stops the component: the conflicted files are listed, `git merge --abort`
runs, the row is `conflict`, exit 70. When every merge was already contained the branch tip equals
`develop`: `no-op`, nothing pushed, no PR. Otherwise the branch is pushed (no force) and
`gh pr create` opens the PR to `develop` with a Japanese title and body. `--dry-run` performs the
same merges on a detached HEAD (`git switch --detach <base>`) so conflicts are still detected, but
it creates no local branch, pushes nothing and opens no PR.

Runner: `runner(argv, cwd=None) -> (returncode, stdout)`; tests inject a fake. The default
streams child output lines to stderr while collecting them, like build.py.
"""
from __future__ import annotations

import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from . import exit_codes, report, toon
from .context import Context

GITHUB_ORG = "RCOSDP"
DEFAULT_WORKDIR = "runtime/upstream"
DEFAULT_REPORT_DIR = "docs/status/upstream"
ARCHIVE_KEEP_DAYS = 90
PR_REF_PREFIX = "refs/grdm-dev/pr"  # scratch refs for adopted PR heads; not tracking branches

Runner = Callable[..., tuple[int, str]]


def default_runner(argv: list[str], cwd: str | None = None) -> tuple[int, str]:
    """Run argv, stream every output line to stderr, return (returncode, collected output)."""
    lines: list[str] = []
    try:
        proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except OSError as exc:
        return 127, str(exc)
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stderr.write(line)
        lines.append(line)
    return proc.wait(), "".join(lines)


# --------------------------------------------------------------------------- names and URLs


def repo_url(repo_name: str) -> str:
    """Compose the HTTPS URL at run time. Never stored in the manifest, docs, or reports."""
    path = repo_name if "/" in repo_name else f"{GITHUB_ORG}/{repo_name}"
    return f"https://github.com/{path}.git"


def gh_repo(repo_name: str) -> str:
    """OWNER/REPO form for `gh --repo` (a name, not a URL)."""
    return repo_name if "/" in repo_name else f"{GITHUB_ORG}/{repo_name}"


def today(now: _dt.datetime | None = None) -> _dt.date:
    return (now or _dt.datetime.now().astimezone()).date()


def generated_at(now: _dt.datetime | None = None) -> str:
    return (now or _dt.datetime.now().astimezone()).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- git helpers


class Git:
    """Thin wrapper: every call is `git -C <dest> ...` through the injected runner."""

    def __init__(self, runner: Runner, dest: Path):
        self.runner = runner
        self.dest = dest

    def __call__(self, *args: str) -> tuple[int, str]:
        return self.runner(["git", "-C", str(self.dest), *args])

    def rev_parse(self, ref: str) -> str | None:
        rc, out = self("rev-parse", "--verify", "--quiet", ref)
        sha = out.strip().splitlines()[0].strip() if rc == 0 and out.strip() else ""
        return sha or None

    def count(self, rng: str) -> int | None:
        rc, out = self("rev-list", "--count", rng)
        try:
            return int(out.strip().splitlines()[0]) if rc == 0 else None
        except (ValueError, IndexError):
            return None

    def is_ancestor(self, sha: str, of: str) -> bool:
        rc, _ = self("merge-base", "--is-ancestor", sha, of)
        return rc == 0


def ensure_clone(repo: str, dest: Path, runner: Runner) -> tuple[int, str]:
    """Clone the integration repository (no checkout) or fetch it when already present."""
    if (dest / ".git").exists():
        return runner(["git", "-C", str(dest), "fetch", "--prune", "origin"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    return runner(["git", "clone", "--no-checkout", repo_url(repo), str(dest)])


def components_in(ctx: Context, only: str | None) -> tuple[list, str | None]:
    """Components with an integration repository (optionally one), or an error detail."""
    from . import manifest as _manifest

    try:
        comps = [c for c in _manifest.load(ctx).components if c.integration_repo]
    except Exception as exc:  # ManifestError, OSError → SPEC-02 exit 20 by the caller
        return [], "; ".join(getattr(exc, "errors", []) or [str(exc)])
    if only is not None:
        comps = [c for c in comps if c.id == only]
        if not comps:
            return [], f"unknown component or no integration_repo: {only}"
    return comps, None


def resolve_dir(ctx: Context, value: str | None, default: str) -> Path:
    p = Path(value or default)
    return p if p.is_absolute() else ctx.root / p


def _fail(detail: str) -> int:
    """Exit 70 (SPEC-02 §6 `UPSTREAM_FAILED`) with the canonical message and the failure details."""
    code = exit_codes.UPSTREAM_FAILED
    sys.stderr.write(f"[grdm-dev] exit {code}: {exit_codes.describe(code)} — {detail}\n")
    return code


# --------------------------------------------------------------------------- mirror


def mirror_component(comp, workdir: Path, runner: Runner, dry_run: bool) -> dict[str, Any]:
    """Mirror every upstream of one component; returns its report entry (names and SHAs only)."""
    repo = comp.integration_repo
    dest = workdir / repo
    dev_branch = comp.integration_branch or "develop"
    entry: dict[str, Any] = {"component": comp.id, "integration_repo": repo, "develop_sha": None,
                             "upstreams": [], "to_publish": [], "pushed": [], "action": "none", "errors": []}
    rc, out = ensure_clone(repo, dest, runner)
    if rc != 0:
        entry["errors"].append(f"clone/fetch of {repo} failed (exit {rc})")
        entry["action"] = "error"
        return entry
    git = Git(runner, dest)
    develop_sha = git.rev_parse(f"refs/remotes/origin/{dev_branch}")
    entry["develop_sha"] = develop_sha
    to_publish: list[str] = []
    halt = False
    for up in comp.upstreams:
        tracking = up.tracking_branch
        local = f"refs/heads/{tracking}"
        # "previous" is what the integration repository publishes — never a local ref: a local ref
        # left behind by a dry-run or by a failed push is not published state (review U1)
        remote = git.rev_parse(f"refs/remotes/origin/{tracking}")
        previous = remote
        if remote:
            # the local ref starts where the integration repository has it, so the fast-forward
            # check below compares the source with what was published, not with a stale local ref
            git("update-ref", local, remote)
        elif git.rev_parse(local):
            # origin has no such branch: nothing is published, so nothing needs protecting
            git("update-ref", "-d", local)
        rc, out = git("fetch", "--no-tags", repo_url(up.repo), f"refs/heads/{up.branch}:{local}")
        row: dict[str, Any] = {"branch": tracking, "kind": up.kind, "source_repo": up.repo, "source_branch": up.branch,
                               "previous_sha": previous, "sha": previous, "ahead_of_develop": None, "behind_develop": None,
                               "develop_contains": None, "manifest_sha_matches": None, "moved_since_yesterday": False,
                               "status": "unchanged"}
        if rc != 0:
            if "non-fast-forward" in out or "rejected" in out:
                row["status"] = "non-fast-forward"
                halt = True
                entry["errors"].append(f"{tracking}: source {up.repo} {up.branch} is non-fast-forward against the mirrored branch (force push upstream?); old branch kept")
            else:
                row["status"] = "fetch-failed"
                entry["errors"].append(f"{tracking}: fetch from {up.repo} {up.branch} failed (exit {rc})")
        else:
            new = git.rev_parse(local) or previous
            row["sha"] = new
            if new != previous:
                row["status"] = "updated" if previous else "created"
                row["moved_since_yesterday"] = True
            # publication is decided against the remote state (branch missing on origin, or origin's
            # SHA differs from the fetched one), independently of the local fast-forward check above
            if new and (remote is None or remote != new):
                to_publish.append(tracking)
        sha = row["sha"]
        if sha:
            row["manifest_sha_matches"] = sha == up.sha
            if develop_sha:
                row["ahead_of_develop"] = git.count(f"{develop_sha}..{sha}")
                row["behind_develop"] = git.count(f"{sha}..{develop_sha}")
                row["develop_contains"] = git.is_ancestor(sha, develop_sha)
        entry["upstreams"].append(row)
    entry["to_publish"] = list(to_publish)
    if to_publish and not dry_run:
        refspecs = [f"refs/heads/{t}:refs/heads/{t}" for t in to_publish]
        rc, out = git("push", "origin", *refspecs)
        if rc == 0:
            entry["pushed"] = to_publish
        else:
            entry["errors"].append(f"push of {len(to_publish)} tracking branch(es) to {repo} failed (exit {rc}); "
                                   "the next run publishes them again")
    needs = any(r["kind"] in ("public", "private") and (r["ahead_of_develop"] or 0) > 0
                for r, up in zip(entry["upstreams"], comp.upstreams) if up.status == "merged")
    entry["action"] = "halt" if halt else "integrate" if needs else "none"
    if entry["errors"] and not halt:
        entry["action"] = "error" if entry["action"] == "none" else entry["action"]
    return entry


def prune_archive(archive: Path, as_of: _dt.date, keep_days: int = ARCHIVE_KEEP_DAYS) -> list[str]:
    removed: list[str] = []
    if not archive.is_dir():
        return removed
    for p in sorted(archive.iterdir()):
        try:
            d = _dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if (as_of - d).days > keep_days:
            p.unlink()
            removed.append(p.name)
    return removed


def write_report_files(report_dir: Path, data: dict[str, Any], as_of: _dt.date) -> list[str]:
    """latest.{json,toon} + archive/YYYY-MM-DD.{json,toon}; returns the relative names written."""
    archive = report_dir / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    js = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tn = toon.encode(data, name="report") + "\n"
    written = []
    for base in (report_dir / "latest", archive / as_of.isoformat()):
        base.with_suffix(".json").write_text(js, encoding="utf-8")
        base.with_suffix(".toon").write_text(tn, encoding="utf-8")
        written += [str(base.with_suffix(".json").relative_to(report_dir)), str(base.with_suffix(".toon").relative_to(report_dir))]
    return written


def run_mirror(ctx: Context, args, runner: Runner, now: _dt.datetime | None = None) -> int:
    only = getattr(args, "component", None)
    dry_run = bool(getattr(args, "dry_run", False))
    comps, detail = components_in(ctx, only)
    if detail is not None:
        return report.error(ctx, exit_codes.MANIFEST_INVALID if only is None else exit_codes.USAGE, detail)
    workdir = resolve_dir(ctx, getattr(args, "workdir", None), DEFAULT_WORKDIR)
    report_dir = resolve_dir(ctx, getattr(args, "report_dir", None), DEFAULT_REPORT_DIR)
    as_of = today(now)
    repos = [mirror_component(c, workdir, runner, dry_run) for c in comps]
    errors = [f"{r['integration_repo']}: {e}" for r in repos for e in r["errors"]]
    data = {
        "generated_at": generated_at(now),
        "dry_run": dry_run,
        "repositories": repos,
        "summary": {
            "repositories": len(repos),
            "repositories_needing_integration": sum(1 for r in repos if r["action"] == "integrate"),
            "force_push_detected": sum(1 for r in repos for u in r["upstreams"] if u["status"] == "non-fast-forward"),
            "branches_moved": sum(1 for r in repos for u in r["upstreams"] if u["moved_since_yesterday"]),
            "branches_pushed": sum(len(r["pushed"]) for r in repos),
            "errors": len(errors),
        },
    }
    written = write_report_files(report_dir, data, as_of)
    pruned = prune_archive(report_dir / "archive", as_of)
    out = dict(data)
    out["files"] = {"report_dir": str(report_dir), "written": written, "archives_pruned": pruned}
    out["error_details"] = errors
    report.emit(ctx, "upstream_mirror", out)
    if errors:
        return _fail(f"upstream mirror: {len(errors)} failure(s): " + " | ".join(errors))
    return exit_codes.OK


# --------------------------------------------------------------------------- integrate


def integrate_scope(comp) -> tuple[Any, Any, str | None]:
    """(public upstream, private upstream, skip reason) following ADR-01 §5 / SPEC-01 rule 3."""
    public = next((u for u in comp.upstreams if u.kind == "public" and u.status == "merged"), None)
    private = next((u for u in comp.upstreams if u.kind == "private" and u.status == "merged"), None)
    if public is None:
        if private is None:
            return None, None, "no merged upstream in the manifest"
        return None, private, f"private-only: develop is seeded from {private.tracking_branch}; ADR-01 §5 strict reconstruction does not apply"
    return public, private, None


def pr_title(comp, as_of: _dt.date) -> str:
    return f"統合: upstream {as_of.isoformat()}（{comp.id}）"


def pr_body(comp, entry: dict[str, Any]) -> str:
    lines = [
        f"SPEC-05 §3 / ADR-01 §5 の統合ブランチ `{entry['branch']}`（{comp.id}）。",
        "",
        f"- 開始点: {'`upstream/public` の先端（厳密再構築）' if entry['mode'] == 'strict' else '`develop` の先端（公開先端は既に develop に含まれる）'}",
        f"- develop: `{entry['develop_sha']}`",
        "",
        "| 順 | 取り込み元 | SHA | 状態 |",
        "|---|---|---|---|",
    ]
    for i, m in enumerate(entry["merges"], 1):
        lines.append(f"| {i} | `{m['ref']}` | `{m['sha'] or ''}` | {m['status']} |")
    lines += ["", "マージ順は 公開 → 非公開 → 採用 PR（マニフェスト順）。force push と squash は行わない。",
              "レビュー: REV、検査: QAE、マージ: 所有者（ADR-04）。"]
    return "\n".join(lines)


def integrate_component(comp, workdir: Path, runner: Runner, as_of: _dt.date, dry_run: bool) -> dict[str, Any]:
    repo = comp.integration_repo
    dest = workdir / repo
    dev_branch = comp.integration_branch or "develop"
    date_tag = as_of.strftime("%Y%m%d")
    branch = f"integrate/strict-{date_tag}"
    entry: dict[str, Any] = {"component": comp.id, "integration_repo": repo, "branch": branch, "mode": None,
                             "develop_sha": None, "merges": [], "conflicts": [], "status": "pending",
                             "pushed": False, "pr": None, "note": None, "errors": []}
    public, private, skip = integrate_scope(comp)
    if skip:
        entry["status"], entry["note"], entry["branch"] = "skipped", skip, None
        return entry
    rc, _ = ensure_clone(repo, dest, runner)
    if rc != 0:
        entry["status"] = "error"
        entry["errors"].append(f"clone/fetch of {repo} failed (exit {rc})")
        return entry
    git = Git(runner, dest)
    develop_sha = git.rev_parse(f"refs/remotes/origin/{dev_branch}")
    public_sha = git.rev_parse(f"refs/remotes/origin/{public.tracking_branch}")
    entry["develop_sha"] = develop_sha
    if not develop_sha or not public_sha:
        entry["status"] = "error"
        entry["errors"].append(f"origin lacks {dev_branch} or {public.tracking_branch}; run upstream mirror first")
        return entry
    if git.rev_parse(f"refs/remotes/origin/{branch}"):
        entry["status"] = "error"
        entry["errors"].append(f"{branch} already exists in {repo}; it is never rewritten")
        return entry
    if git.rev_parse(f"refs/heads/{branch}"):
        # a local branch may hold a conflict resolution committed by hand (SPEC-05 §4); never reset it
        entry["status"] = "error"
        entry["errors"].append(f"{branch} already exists in the local clone {dest.name}; it is never rewritten "
                               "(push or delete it by hand first)")
        return entry
    on_develop = git.is_ancestor(public_sha, develop_sha)
    entry["mode"] = "on-develop" if on_develop else "strict"
    base = f"refs/remotes/origin/{dev_branch}" if on_develop else f"refs/remotes/origin/{public.tracking_branch}"
    entry["merges"].append({"order": 0, "ref": public.tracking_branch, "sha": public_sha,
                            "status": "contained-in-develop" if on_develop else "base"})
    if dry_run:
        # preview on a detached HEAD: the merges (and their conflicts) are real, but no local branch
        # is created, so a dry-run leaves nothing behind that a later run could reset or refuse
        rc, out = git("switch", "--detach", base)
    else:
        # `switch -c` creates only; it refuses an existing branch instead of resetting it like `checkout -B`
        rc, out = git("switch", "-c", branch, "--no-track", base)
    if rc != 0:
        entry["status"] = "error"
        entry["errors"].append(f"could not {'detach at' if dry_run else 'create ' + branch + ' from'} "
                               f"{base.rsplit('/', 1)[-1]} (exit {rc})")
        return entry

    def merge(ref: str, label: str, msg: str) -> bool:
        sha = git.rev_parse(ref)
        row = {"order": len(entry["merges"]), "ref": label, "sha": sha, "status": "merged"}
        entry["merges"].append(row)
        if not sha:
            row["status"] = "missing"
            entry["errors"].append(f"{label}: ref not found")
            return False
        rc, out = git("merge", "--no-ff", "--no-edit", "-m", msg, sha)
        if rc == 0:
            if "Already up to date" in out:
                row["status"] = "already-contained"
            return True
        rc2, files = git("diff", "--name-only", "--diff-filter=U")
        entry["conflicts"] = [f for f in files.splitlines() if f.strip()] if rc2 == 0 else []
        git("merge", "--abort")
        row["status"] = "conflict"
        entry["errors"].append(f"{label}: merge conflict in {len(entry['conflicts'])} file(s)")
        return False

    ok = True
    if private is not None:
        ok = merge(f"refs/remotes/origin/{private.tracking_branch}", private.tracking_branch,
                   f"統合: {private.tracking_branch} を取り込む（{comp.id}）")
    for pr in comp.adopted_prs if ok else []:
        scratch = f"{PR_REF_PREFIX}/{pr.number}"
        # a PR head may be rewritten by its author; the scratch ref is not a tracking branch, so `+` is allowed here
        rc, out = git("fetch", "--no-tags", repo_url(pr.repo), f"+refs/pull/{pr.number}/head:{scratch}")
        label = f"{pr.repo}#{pr.number}"
        if rc != 0:
            entry["merges"].append({"order": len(entry["merges"]), "ref": label, "sha": None, "status": "fetch-failed"})
            entry["errors"].append(f"{label}: fetch of refs/pull/{pr.number}/head failed (exit {rc})")
            ok = False
            break
        ok = merge(scratch, label, f"統合: 採用 PR {label} を再適用する（{comp.id}）")
        if not ok:
            break
    if not ok:
        entry["status"] = "conflict" if entry["conflicts"] else "error"
        return entry
    head = git.rev_parse("HEAD")
    if head == develop_sha:
        entry["status"], entry["note"] = "no-op", "every source is already contained in develop; nothing to push, no PR"
        return entry
    if dry_run:
        entry["status"], entry["note"] = "dry-run", "merged on a detached HEAD; no branch created, push and PR skipped"
        return entry
    rc, out = git("push", "origin", f"refs/heads/{branch}:refs/heads/{branch}")
    if rc != 0:
        entry["status"] = "error"
        entry["errors"].append(f"push of {branch} to {repo} failed (exit {rc})")
        return entry
    entry["pushed"] = True
    rc, out = runner(["gh", "pr", "create", "--repo", gh_repo(repo), "--base", dev_branch, "--head", branch,
                      "--title", pr_title(comp, as_of), "--body", pr_body(comp, entry)])
    if rc != 0:
        entry["status"] = "error"
        entry["errors"].append(f"gh pr create failed for {repo} (exit {rc}); branch {branch} is pushed")
        return entry
    number = next((seg.rsplit("/", 1)[-1] for seg in out.split() if "/pull/" in seg), None)
    entry["pr"] = {"repo": repo, "number": int(number) if number and number.isdigit() else None, "title": pr_title(comp, as_of)}
    entry["status"] = "opened"
    return entry


def run_integrate(ctx: Context, args, runner: Runner, now: _dt.datetime | None = None) -> int:
    only = getattr(args, "component", None)
    dry_run = bool(getattr(args, "dry_run", False))
    comps, detail = components_in(ctx, only)
    if detail is not None:
        return report.error(ctx, exit_codes.MANIFEST_INVALID if only is None else exit_codes.USAGE, detail)
    date_arg = getattr(args, "date", None)
    if date_arg:
        try:
            as_of = _dt.datetime.strptime(date_arg, "%Y%m%d").date()
        except ValueError:
            return report.error(ctx, exit_codes.USAGE, f"--date must be YYYYMMDD, got {date_arg}")
    else:
        as_of = today(now)
    workdir = resolve_dir(ctx, getattr(args, "workdir", None), DEFAULT_WORKDIR)
    repos = [integrate_component(c, workdir, runner, as_of, dry_run) for c in comps]
    errors = [f"{r['integration_repo']}: {e}" for r in repos for e in r["errors"]]
    data = {
        "date": as_of.isoformat(),
        "dry_run": dry_run,
        "repositories": repos,
        "summary": {
            "repositories": len(repos),
            "opened": sum(1 for r in repos if r["status"] == "opened"),
            "no_op": sum(1 for r in repos if r["status"] == "no-op"),
            "skipped": sum(1 for r in repos if r["status"] == "skipped"),
            "conflicts": sum(1 for r in repos if r["status"] == "conflict"),
            "errors": len(errors),
        },
        "error_details": errors,
    }
    report.emit(ctx, "upstream_integrate", data)
    if errors:
        return _fail(f"upstream integrate: {len(errors)} failure(s): " + " | ".join(errors))
    return exit_codes.OK


# --------------------------------------------------------------------------- CLI


def register(subparsers) -> None:
    p = subparsers.add_parser("upstream", help="daily mirror / weekly integration of SPEC-05 (needs Git access to the -dev2027 repositories)")
    sub = p.add_subparsers(dest="upstream_action", metavar="<mirror|integrate>")
    m = sub.add_parser("mirror", help="fast-forward upstream/* tracking branches into the -dev2027 repositories and write the diff report")
    m.add_argument("--component", help="only this component id")
    m.add_argument("--workdir", help=f"where the integration repositories are cloned (default: {DEFAULT_WORKDIR})")
    m.add_argument("--report-dir", dest="report_dir", help=f"where latest.* and archive/ are written (default: {DEFAULT_REPORT_DIR})")
    m.add_argument("--dry-run", dest="dry_run", action="store_true", help="fetch and report only; push nothing")
    i = sub.add_parser("integrate", help="create integrate/strict-<date>, merge public → private → adopted PRs, open the PR to develop")
    i.add_argument("--component", help="only this component id")
    i.add_argument("--workdir", help=f"where the integration repositories are cloned (default: {DEFAULT_WORKDIR})")
    i.add_argument("--date", help="YYYYMMDD used in the branch name and PR title (default: today)")
    i.add_argument("--dry-run", dest="dry_run", action="store_true", help="merge locally and report; push nothing, open no PR")
    p.set_defaults(_module=sys.modules[__name__])


def run(ctx: Context, args, runner: Runner | None = None, now: _dt.datetime | None = None) -> int:
    runner = runner or default_runner
    action = getattr(args, "upstream_action", None)
    if action == "mirror":
        return run_mirror(ctx, args, runner, now)
    if action == "integrate":
        return run_integrate(ctx, args, runner, now)
    sys.stderr.write("[grdm-dev] exit 2: usage: grdm-dev upstream <mirror|integrate>\n")
    return exit_codes.USAGE
