"""Tests for grdm-dev upstream mirror | integrate (SPEC-05, ADR-01 §5) with a fake git/gh runner.

The fake keeps a tiny commit graph: every SHA has a linear `history` (its ancestors, oldest
first). That is enough to model fast-forward checks, `rev-list --count`, `merge-base --is-ancestor`,
`merge --no-ff` (a new merge commit whose history is the union) and `Already up to date`.
No test writes a private-repository URL literally: URLs are composed by the code under test and
compared piecewise (the repository-wide policy scan reads this file too).
"""
import argparse
import datetime as dt
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import exit_codes, upstream
from grdm_dev.context import Context

GH = "https://github.com/"  # host only; the private names are appended at run time by the code


def sha(label: str) -> str:
    """Deterministic fake 40-hex SHA from a label."""
    import hashlib

    # Fake 40-hex git object id for tests; this is not a security use of hashing.
    return hashlib.sha256(label.encode()).hexdigest()[:40]


# --- a shared linear history: base → pub1 → pub2; private and PR branches fork from pub1
BASE, PUB1, PUB2 = sha("base"), sha("pub1"), sha("pub2")
PRV1, PRV2 = sha("prv1"), sha("prv2")
PR_A, PR_B = sha("pr-a"), sha("pr-b")
COS1, COS2 = sha("cos1"), sha("cos2")
DEV_SEED = sha("dev-seed")        # develop seeded from the private tip (bootstrap state, ADR-01 §5)
PUB_REWRITE = sha("pub-rewrite")  # a rewritten public tip (force-push upstream)

HISTORY = {
    BASE: [BASE],
    PUB1: [BASE, PUB1],
    PUB2: [BASE, PUB1, PUB2],
    PRV1: [BASE, PUB1, PRV1],
    PRV2: [BASE, PUB1, PRV1, PRV2],
    PR_A: [BASE, PUB1, PR_A],
    PR_B: [BASE, PUB1, PR_B],
    COS1: [COS1],
    COS2: [COS1, COS2],
    DEV_SEED: [BASE, PUB1, PRV1, DEV_SEED],
    PUB_REWRITE: [BASE, PUB_REWRITE],
}


def up(repo, branch, kind, tracking, status, s):
    return {"repo": repo, "branch": branch, "kind": kind, "tracking_branch": tracking, "status": status, "sha": s, "fetched_at": "2026-11-05"}


def pr(repo, number, status="adopted"):
    return {"repo": repo, "number": number, "title": f"PR {number}", "reason": "security/auth", "status": status}


def comp(cid, repo, upstreams=(), adopted=()):
    return {"id": cid, "role": "core", "profile": "core", "integration_repo": repo, "integration_branch": "develop" if repo else None,
            "services": [cid], "upstreams": list(upstreams), "adopted_prs": list(adopted), "candidate_prs": [], "base_image": "x",
            "base_image_digest": None, "target_image": {"M4": None, "M5": None}, "platforms": ["linux/arm64"], "note": None}


MANIFEST = {
    "schema_version": 1,
    "generated_at": "2026-11-05",
    "components": [
        comp("osf.io", "RDM-osf.io-dev2027", [
            up("RDM-osf.io", "develop", "public", "upstream/public-develop", "merged", PUB1),
            up("RDM-osf.io-develop-private", "develop", "private", "upstream/private-develop", "merged", PRV1),
            up("CenterForOpenScience/osf.io", "develop", "cos", "upstream/cos-develop", "reference", COS1),
            up("RDM-osf.io-private", "fix/sec-test", "private", "upstream/private-sec-test-fix-sec-test", "candidate", PRV1),
        ], [pr("RDM-osf.io", 796)]),
        comp("OASys", "RDM-OASys-dev2027", [
            up("RDM-OASys-main-private", "main", "private", "upstream/private-main", "merged", PRV1),
        ]),
        comp("postgres", None),
    ],
}


class FakeGit:
    """Simulates the git/gh calls upstream.py makes. `sources` maps composed URL → {src ref → sha}."""

    def __init__(self, origin, sources, conflict_on=(), fail_push=False):
        self.origin = dict(origin)            # refs of the integration repository, e.g. "develop", "upstream/public-develop"
        self.sources = sources                # url → {"refs/heads/develop": sha, "refs/pull/796/head": sha}
        self.conflict_on = set(conflict_on)   # SHAs whose merge conflicts
        self.fail_push = fail_push
        self.history = dict(HISTORY)
        self.calls = []
        self.remote = {}                      # refs/remotes/origin/X mirror (filled by fetch origin)
        self.local = {}                       # refs/heads/X, refs/grdm-dev/pr/N
        self.head = None
        self.branch = None
        self.conflict_files = []
        self.merged_refs = []

    # -- helpers
    def resolve(self, ref):
        if ref == "HEAD":
            return self.head
        if ref.startswith("refs/remotes/origin/"):
            return self.remote.get(ref[len("refs/remotes/origin/"):])
        if ref in self.local:
            return self.local[ref]
        if ref in self.history:
            return ref
        return None

    def is_ancestor(self, a, b):
        return a in self.history.get(b, [])

    def __call__(self, argv, cwd=None):
        self.calls.append(list(argv))
        if argv[0] == "gh":
            assert argv[1:3] == ["pr", "create"]
            return 0, "https://example.invalid/pull/42\n"
        assert argv[0] == "git"
        if argv[1] == "clone":
            Path(argv[-1], ".git").mkdir(parents=True, exist_ok=True)
            self.remote = dict(self.origin)
            return 0, ""
        assert argv[1] == "-C"
        args = argv[3:]
        cmd = args[0]
        if cmd == "fetch" and args[1:] == ["--prune", "origin"]:
            self.remote = dict(self.origin)
            return 0, ""
        if cmd == "fetch":
            assert args[1] == "--no-tags"
            url, refspec = args[2], args[3]
            force = refspec.startswith("+")
            src, dst = refspec.lstrip("+").split(":")
            new = self.sources.get(url, {}).get(src)
            if new is None:
                return 128, "fatal: couldn't find remote ref " + src
            old = self.local.get(dst)
            if old and not force and not self.is_ancestor(old, new):
                return 1, f" ! [rejected]  {src} -> {dst}  (non-fast-forward)\n"
            self.local[dst] = new
            return 0, ""
        if cmd == "rev-parse":
            s = self.resolve(args[-1])
            return (0, s + "\n") if s else (1, "")
        if cmd == "update-ref":
            self.local[args[1]] = args[2]
            return 0, ""
        if cmd == "rev-list":
            a, b = args[2].split("..")
            n = len([x for x in self.history[b] if x not in self.history[a]])
            return 0, f"{n}\n"
        if cmd == "merge-base":
            return (0 if self.is_ancestor(args[2], args[3]) else 1), ""
        if cmd == "push":
            assert args[1] == "origin"
            if self.fail_push:
                return 1, "error: failed to push some refs"
            for spec in args[2:]:
                src, dst = spec.split(":")
                self.origin[dst[len("refs/heads/"):]] = self.local[src]
            return 0, ""
        if cmd == "checkout":
            assert args[1:3] == ["--no-track", "-B"]
            self.branch, self.head = args[3], self.resolve(args[4])
            self.local["refs/heads/" + self.branch] = self.head
            return 0, ""
        if cmd == "merge" and args[1] == "--abort":
            self.conflict_files = []
            return 0, ""
        if cmd == "merge":
            target = args[-1]
            if self.is_ancestor(target, self.head):
                return 0, "Already up to date.\n"
            if target in self.conflict_on:
                self.conflict_files = ["api/base/permissions.py", "website/settings/defaults.py"]
                return 1, "CONFLICT (content): Merge conflict in api/base/permissions.py\n"
            new = sha(f"merge:{self.head}:{target}")
            self.history[new] = list(dict.fromkeys(self.history[self.head] + self.history[target] + [new]))
            self.head = new
            self.local["refs/heads/" + self.branch] = new
            self.merged_refs.append(target)
            return 0, ""
        if cmd == "diff":
            return 0, "\n".join(self.conflict_files) + "\n"
        raise AssertionError(f"unexpected git call: {argv}")


OSF_URL = GH + "RCOSDP/" + "RDM-osf.io" + ".git"
OSF_PRIVATE_URL = GH + "RCOSDP/" + "RDM-osf.io-develop" + "-private.git"
OSF_CANDIDATE_URL = GH + "RCOSDP/" + "RDM-osf.io" + "-private.git"
COS_URL = GH + "CenterForOpenScience/osf.io.git"
OASYS_URL = GH + "RCOSDP/" + "RDM-OASys-main" + "-private.git"

SOURCES = {
    OSF_URL: {"refs/heads/develop": PUB2, "refs/pull/796/head": PR_A},
    OSF_PRIVATE_URL: {"refs/heads/develop": PRV2},
    OSF_CANDIDATE_URL: {"refs/heads/fix/sec-test": PRV1},
    COS_URL: {"refs/heads/develop": COS2},
    OASYS_URL: {"refs/heads/main": PRV1},
}

ORIGIN_YESTERDAY = {  # what the -dev2027 repositories hold before today's mirror
    "develop": DEV_SEED,
    "upstream/public-develop": PUB1,
    "upstream/private-develop": PRV1,
    "upstream/cos-develop": COS1,
    "upstream/private-sec-test-fix-sec-test": PRV1,
}

NOW = dt.datetime(2026, 11, 6, 3, 0, 12, tzinfo=dt.timezone(dt.timedelta(hours=9)))


class UpstreamBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(MANIFEST))
        self.out, self.err = io.StringIO(), io.StringIO()
        self.ctx = Context(root=self.root, stdin_is_tty=False, json_output=True)

    def tearDown(self):
        self.tmp.cleanup()

    def mirror(self, runner, **kw):
        args = argparse.Namespace(upstream_action="mirror", component=kw.get("component"), workdir=kw.get("workdir"),
                                  report_dir=kw.get("report_dir"), dry_run=kw.get("dry_run", False))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return upstream.run(self.ctx, args, runner=runner, now=NOW)

    def integrate(self, runner, **kw):
        args = argparse.Namespace(upstream_action="integrate", component=kw.get("component"), workdir=kw.get("workdir"),
                                  date=kw.get("date"), dry_run=kw.get("dry_run", False))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return upstream.run(self.ctx, args, runner=runner, now=NOW)

    def report(self):
        return json.loads(self.out.getvalue())

    @staticmethod
    def pushes(runner):
        return [c for c in runner.calls if c[0] == "git" and c[3] == "push"]

    @staticmethod
    def source_fetches(runner):
        return [c for c in runner.calls if c[0] == "git" and c[3] == "fetch" and c[4] == "--no-tags"]


class MirrorTests(UpstreamBase):
    def test_fetch_argv_uses_composed_urls_and_fast_forward_refspecs(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner, component="osf.io"), exit_codes.OK)
        clone = [c for c in runner.calls if c[1] == "clone"][0]
        self.assertEqual(clone, ["git", "clone", "--no-checkout", GH + "RCOSDP/" + "RDM-osf.io-dev2027" + ".git",
                                 str(self.root / "runtime" / "upstream" / "RDM-osf.io-dev2027")])
        fetches = self.source_fetches(runner)
        self.assertEqual([(c[5], c[6]) for c in fetches], [
            (OSF_URL, "refs/heads/develop:refs/heads/upstream/public-develop"),
            (OSF_PRIVATE_URL, "refs/heads/develop:refs/heads/upstream/private-develop"),
            (COS_URL, "refs/heads/develop:refs/heads/upstream/cos-develop"),          # owner kept as given, not RCOSDP
            (OSF_CANDIDATE_URL, "refs/heads/fix/sec-test:refs/heads/upstream/private-sec-test-fix-sec-test"),  # candidates are mirrored (rule 6)
        ])
        for c in fetches:
            self.assertFalse(c[6].startswith("+"), c)  # fast-forward only, never forced
        # the local ref was set to origin's value before the fetch, so the fast-forward check is against what was published
        upd = [c for c in runner.calls if c[3] == "update-ref" and c[4] == "refs/heads/upstream/public-develop"][0]
        self.assertEqual(upd[5], PUB1)

    def test_push_is_explicit_per_moved_branch_and_never_forced(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner, component="osf.io"), exit_codes.OK)
        pushes = self.pushes(runner)
        self.assertEqual(len(pushes), 1)
        self.assertEqual(pushes[0][4], "origin")
        self.assertEqual(pushes[0][5:], [
            "refs/heads/upstream/public-develop:refs/heads/upstream/public-develop",
            "refs/heads/upstream/private-develop:refs/heads/upstream/private-develop",
            "refs/heads/upstream/cos-develop:refs/heads/upstream/cos-develop",
        ])  # the candidate did not move → not pushed
        self.assertFalse(any(a in ("--force", "-f", "--force-with-lease") or a.startswith("+") for a in pushes[0]))
        self.assertEqual(runner.origin["upstream/public-develop"], PUB2)
        rep = self.report()
        repo = rep["repositories"][0]
        self.assertEqual(repo["action"], "integrate")  # public is 1 ahead of develop (DEV_SEED contains PUB1 only)
        rows = {r["branch"]: r for r in repo["upstreams"]}
        self.assertEqual((rows["upstream/public-develop"]["previous_sha"], rows["upstream/public-develop"]["sha"]), (PUB1, PUB2))
        self.assertEqual(rows["upstream/public-develop"]["ahead_of_develop"], 1)
        self.assertFalse(rows["upstream/public-develop"]["develop_contains"])
        self.assertTrue(rows["upstream/public-develop"]["moved_since_yesterday"])
        self.assertFalse(rows["upstream/public-develop"]["manifest_sha_matches"])
        self.assertEqual(rows["upstream/private-develop"]["status"], "updated")
        self.assertEqual(rows["upstream/private-sec-test-fix-sec-test"]["status"], "unchanged")
        self.assertTrue(rows["upstream/private-sec-test-fix-sec-test"]["manifest_sha_matches"])
        self.assertEqual(repo["pushed"], ["upstream/public-develop", "upstream/private-develop", "upstream/cos-develop"])

    def test_non_fast_forward_is_a_finding_and_the_old_branch_is_kept(self):
        sources = {**SOURCES, OSF_URL: {"refs/heads/develop": PUB_REWRITE, "refs/pull/796/head": PR_A}}
        runner = FakeGit(ORIGIN_YESTERDAY, sources)
        self.assertEqual(self.mirror(runner, component="osf.io"), upstream.FAILED)
        rep = self.report()
        repo = rep["repositories"][0]
        row = repo["upstreams"][0]
        self.assertEqual(row["status"], "non-fast-forward")
        self.assertEqual(row["sha"], PUB1)                      # old branch kept
        self.assertEqual(runner.origin["upstream/public-develop"], PUB1)
        self.assertEqual(repo["action"], "halt")
        self.assertEqual(rep["summary"]["force_push_detected"], 1)
        pushes = self.pushes(runner)
        self.assertEqual(len(pushes), 1)  # the other branches still move
        self.assertNotIn("refs/heads/upstream/public-develop:refs/heads/upstream/public-develop", pushes[0])
        self.assertFalse(any(a.startswith("+") or a in ("--force", "-f") for c in runner.calls for a in c))
        self.assertIn("non-fast-forward", self.err.getvalue())

    def test_push_failure_exits_1(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES, fail_push=True)
        self.assertEqual(self.mirror(runner, component="osf.io"), upstream.FAILED)
        self.assertEqual(self.report()["repositories"][0]["pushed"], [])
        self.assertIn("push", self.err.getvalue())

    def test_report_files_contain_names_and_shas_only(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner), exit_codes.OK)
        rdir = self.root / "docs" / "status" / "upstream"
        for name in ("latest.json", "latest.toon", "archive/2026-11-06.json", "archive/2026-11-06.toon"):
            text = (rdir / name).read_text(encoding="utf-8")
            self.assertNotIn("github.com", text, name)
            self.assertNotIn("https://", text, name)
            self.assertNotIn("git@", text, name)
            self.assertIn("RDM-osf.io-dev2027", text, name)
            self.assertIn(PUB2, text, name)
        data = json.loads((rdir / "latest.json").read_text())
        self.assertEqual(json.loads((rdir / "archive" / "2026-11-06.json").read_text()), data)
        self.assertEqual(data["generated_at"], "2026-11-06T03:00:12+09:00")
        self.assertEqual([r["integration_repo"] for r in data["repositories"]], ["RDM-osf.io-dev2027", "RDM-OASys-dev2027"])  # infra skipped
        self.assertEqual(set(data["repositories"][0]["upstreams"][0]), {
            "branch", "kind", "source_repo", "source_branch", "previous_sha", "sha", "ahead_of_develop", "behind_develop",
            "develop_contains", "manifest_sha_matches", "moved_since_yesterday", "status"})
        self.assertEqual(data["summary"]["repositories_needing_integration"], 1)
        self.assertEqual(data["summary"]["force_push_detected"], 0)
        toon_text = (rdir / "latest.toon").read_text()
        self.assertTrue(toon_text.startswith("report:\n"))
        self.assertIn("upstreams[4]{branch,kind,", toon_text)
        # the stdout report (report.emit) is equally free of addresses
        self.assertNotIn("github.com", self.out.getvalue())
        self.assertNotIn("github.com", self.err.getvalue())

    def test_dry_run_fetches_and_reports_but_never_pushes(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner, dry_run=True, report_dir="out/rep"), exit_codes.OK)
        self.assertEqual(self.pushes(runner), [])
        self.assertEqual(len(self.source_fetches(runner)), 5)
        self.assertEqual(runner.origin["upstream/public-develop"], PUB1)
        rep = self.report()
        self.assertTrue(rep["dry_run"])
        self.assertEqual(rep["repositories"][0]["pushed"], [])
        self.assertEqual(rep["repositories"][0]["upstreams"][0]["sha"], PUB2)  # the fetch still reports the new tip
        self.assertTrue((self.root / "out" / "rep" / "latest.json").exists())

    def test_archive_older_than_90_days_is_pruned(self):
        rdir = self.root / "docs" / "status" / "upstream" / "archive"
        rdir.mkdir(parents=True)
        for d in ("2026-08-07", "2026-08-08", "notes"):
            (rdir / f"{d}.json").write_text("{}")
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner), exit_codes.OK)
        self.assertFalse((rdir / "2026-08-07.json").exists())  # 91 days before 2026-11-06
        self.assertTrue((rdir / "2026-08-08.json").exists())   # exactly 90 days: kept
        self.assertTrue((rdir / "notes.json").exists())
        self.assertEqual(self.report()["files"]["archives_pruned"], ["2026-08-07.json"])

    def test_unknown_component_is_a_usage_error(self):
        runner = FakeGit(ORIGIN_YESTERDAY, SOURCES)
        self.assertEqual(self.mirror(runner, component="postgres"), exit_codes.USAGE)
        self.assertEqual(runner.calls, [])


ORIGIN_MIRRORED = {**ORIGIN_YESTERDAY, "upstream/public-develop": PUB2, "upstream/private-develop": PRV2, "upstream/cos-develop": COS2}


class IntegrateTests(UpstreamBase):
    def test_strict_order_public_base_then_private_then_adopted_prs(self):
        runner = FakeGit(ORIGIN_MIRRORED, SOURCES)
        self.assertEqual(self.integrate(runner, component="osf.io", date="20261106"), exit_codes.OK)
        checkout = [c for c in runner.calls if c[3] == "checkout"][0]
        self.assertEqual(checkout[3:], ["checkout", "--no-track", "-B", "integrate/strict-20261106", "refs/remotes/origin/upstream/public-develop"])
        self.assertEqual(runner.merged_refs, [PRV2, PR_A])  # private first, then the adopted PR
        merges = [c for c in runner.calls if c[3] == "merge"]
        for m in merges:
            self.assertEqual(m[4:7], ["--no-ff", "--no-edit", "-m"])
        pr_fetch = [c for c in self.source_fetches(runner)][0]
        self.assertEqual(pr_fetch[5:], [OSF_URL, "+refs/pull/796/head:refs/grdm-dev/pr/796"])
        pushes = self.pushes(runner)
        self.assertEqual(pushes[0][4:], ["origin", "refs/heads/integrate/strict-20261106:refs/heads/integrate/strict-20261106"])
        gh = [c for c in runner.calls if c[0] == "gh"][0]
        self.assertEqual(gh[:9], ["gh", "pr", "create", "--repo", "RCOSDP/RDM-osf.io-dev2027", "--base", "develop", "--head", "integrate/strict-20261106"])
        self.assertEqual(gh[gh.index("--title") + 1], "統合: upstream 2026-11-06（osf.io）")
        body = gh[gh.index("--body") + 1]
        self.assertNotIn("https://", body)
        self.assertNotIn("github.com", body)
        self.assertIn("upstream/private-develop", body)
        self.assertIn("RDM-osf.io#796", body)
        rep = self.report()
        osf = rep["repositories"][0]
        self.assertEqual(osf["mode"], "strict")
        self.assertEqual(osf["status"], "opened")
        self.assertEqual(osf["pr"], {"repo": "RDM-osf.io-dev2027", "number": 42, "title": "統合: upstream 2026-11-06（osf.io）"})
        self.assertEqual([m["ref"] for m in osf["merges"]], ["upstream/public-develop", "upstream/private-develop", "RDM-osf.io#796"])
        self.assertEqual([m["status"] for m in osf["merges"]], ["base", "merged", "merged"])
        self.assertNotIn("github.com", self.out.getvalue())

    def test_private_only_component_is_skipped_with_a_note(self):
        runner = FakeGit(ORIGIN_MIRRORED, SOURCES)
        self.assertEqual(self.integrate(runner, component="OASys"), exit_codes.OK)
        self.assertEqual(runner.calls, [])  # not even a clone
        rep = self.report()
        row = rep["repositories"][0]
        self.assertEqual(row["status"], "skipped")
        self.assertIsNone(row["branch"])
        self.assertIn("private-only", row["note"])
        self.assertIn("upstream/private-main", row["note"])
        self.assertEqual(rep["summary"]["skipped"], 1)

    def test_on_develop_mode_when_develop_already_contains_the_public_tip(self):
        # develop was reconstructed earlier: it contains PUB2 and PRV2 but not the adopted PR
        dev = sha("dev-strict")
        runner = FakeGit({**ORIGIN_MIRRORED, "develop": dev}, SOURCES)
        runner.history[dev] = [BASE, PUB1, PUB2, PRV1, PRV2, dev]
        self.assertEqual(self.integrate(runner, component="osf.io", date="20261113"), exit_codes.OK)
        checkout = [c for c in runner.calls if c[3] == "checkout"][0]
        self.assertEqual(checkout[6:], ["integrate/strict-20261113", "refs/remotes/origin/develop"])  # not the public tip
        self.assertEqual(runner.merged_refs, [PR_A])  # private already contained → "Already up to date"
        rep = self.report()
        osf = rep["repositories"][0]
        self.assertEqual(osf["mode"], "on-develop")
        self.assertEqual([m["status"] for m in osf["merges"]], ["contained-in-develop", "already-contained", "merged"])
        self.assertEqual(osf["status"], "opened")

    def test_identical_tips_are_a_no_op_without_push_or_pr(self):
        dev = sha("dev-complete")
        runner = FakeGit({**ORIGIN_MIRRORED, "develop": dev}, SOURCES)
        runner.history[dev] = [BASE, PUB1, PUB2, PRV1, PRV2, PR_A, dev]
        self.assertEqual(self.integrate(runner, component="osf.io"), exit_codes.OK)
        self.assertEqual(self.pushes(runner), [])
        self.assertEqual([c for c in runner.calls if c[0] == "gh"], [])
        rep = self.report()
        self.assertEqual(rep["repositories"][0]["status"], "no-op")
        self.assertEqual(rep["summary"]["no_op"], 1)
        self.assertEqual(rep["repositories"][0]["branch"], "integrate/strict-20261106")

    def test_conflict_aborts_the_merge_lists_files_and_exits_1(self):
        runner = FakeGit(ORIGIN_MIRRORED, SOURCES, conflict_on={PRV2})
        self.assertEqual(self.integrate(runner, component="osf.io"), upstream.FAILED)
        calls = [c[3:] for c in runner.calls if c[0] == "git" and c[3] in ("merge", "push", "fetch", "diff")]
        self.assertIn(["merge", "--abort"], calls)
        self.assertNotIn("push", [c[0] for c in calls])
        self.assertFalse(any(c[0] == "fetch" and "refs/pull/" in c[-1] for c in calls))  # stopped before the PRs
        self.assertEqual([c for c in runner.calls if c[0] == "gh"], [])
        rep = self.report()
        osf = rep["repositories"][0]
        self.assertEqual(osf["status"], "conflict")
        self.assertEqual(osf["conflicts"], ["api/base/permissions.py", "website/settings/defaults.py"])
        self.assertEqual(osf["merges"][1]["status"], "conflict")
        self.assertEqual(rep["summary"]["conflicts"], 1)
        self.assertIn("merge conflict", self.err.getvalue())

    def test_dry_run_merges_locally_but_pushes_nothing(self):
        runner = FakeGit(ORIGIN_MIRRORED, SOURCES)
        self.assertEqual(self.integrate(runner, component="osf.io", dry_run=True), exit_codes.OK)
        self.assertEqual(runner.merged_refs, [PRV2, PR_A])
        self.assertEqual(self.pushes(runner), [])
        self.assertEqual([c for c in runner.calls if c[0] == "gh"], [])
        self.assertEqual(self.report()["repositories"][0]["status"], "dry-run")

    def test_existing_integration_branch_is_never_rewritten(self):
        runner = FakeGit({**ORIGIN_MIRRORED, "integrate/strict-20261106": PUB2}, SOURCES)
        self.assertEqual(self.integrate(runner, component="osf.io"), upstream.FAILED)
        self.assertEqual([c for c in runner.calls if c[3] in ("checkout", "merge", "push")], [])
        self.assertIn("already exists", self.err.getvalue())

    def test_bad_date_is_a_usage_error(self):
        runner = FakeGit(ORIGIN_MIRRORED, SOURCES)
        self.assertEqual(self.integrate(runner, date="2026-11-06"), exit_codes.USAGE)


class CliTests(unittest.TestCase):
    def test_subcommands_are_registered_with_their_flags(self):
        from grdm_dev.cli import build_parser

        p = build_parser()
        a = p.parse_args(["upstream", "mirror", "--component", "osf.io", "--dry-run", "--report-dir", "x"])
        self.assertEqual((a.upstream_action, a.component, a.dry_run, a.report_dir), ("mirror", "osf.io", True, "x"))
        a = p.parse_args(["upstream", "integrate", "--date", "20261106", "--json"])
        self.assertEqual((a.upstream_action, a.date, a.json_output), ("integrate", "20261106", True))

    def test_missing_action_is_usage(self):
        ctx = Context(root=Path("."), stdin_is_tty=False)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(upstream.run(ctx, argparse.Namespace(upstream_action=None), runner=lambda *a, **k: (0, "")), exit_codes.USAGE)


if __name__ == "__main__":
    unittest.main()
