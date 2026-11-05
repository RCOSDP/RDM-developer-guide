import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from grdm_dev import build, exit_codes
from grdm_dev.context import Context

SHA_OSF = "bacfe64fdc002f09df47145fc17f57630772ac82"
SHA_WB = "004f407fefb071f1dc924d09f99916b1d5ea3561"

def comp(cid, role, profile, repo, services, **extra):
    base = {"id": cid, "role": role, "profile": profile, "integration_repo": repo,
            "integration_branch": "develop" if repo else None, "services": services, "upstreams": [],
            "adopted_prs": [], "candidate_prs": [], "base_image": "x", "base_image_digest": None,
            "target_image": {"M4": None, "M5": None}, "platforms": ["linux/arm64", "linux/amd64"], "note": None}
    base.update(extra)
    return base


UPSTREAM_WB = {"repo": "RDM-waterbutler", "branch": "develop", "kind": "public", "tracking_branch": "upstream/public-develop",
               "status": "merged", "sha": SHA_WB, "fetched_at": "2026-11-05"}

MANIFEST = {
    "schema_version": 1,
    "generated_at": "2026-11-05",
    "components": [
        comp("osf.io", "core", "minimum", "RDM-osf.io-dev2027", ["web"], integration_sha=SHA_OSF),
        comp("waterbutler", "core", "core", "RDM-waterbutler-dev2027", ["wb"], upstreams=[UPSTREAM_WB]),
        comp("OASys", "subsystem", "full", "RDM-OASys-dev2027", ["oasys"]),
        comp("postgres", "infra", "minimum", None, ["postgres"]),
    ],
}


class FakeRunner:
    def __init__(self, fail_build_for=None, fail_git_for=None):
        self.calls = []
        self.fail_build_for = fail_build_for
        self.fail_git_for = fail_git_for

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[0] == "git":
            if argv[1] == "clone":
                repo = argv[-2].rsplit("/", 1)[-1].removesuffix(".git")
                if repo == self.fail_git_for:
                    return 128, "fatal: repository not found"
                Path(argv[-1], ".git").mkdir(parents=True, exist_ok=True)
                return 0, ""
            if argv[-2] == "rev-parse":
                return 0, (SHA_OSF if "osf.io" in argv[2] else SHA_WB) + "\n"
            return 0, ""
        if argv[:3] == ["docker", "buildx", "build"]:
            tag = [a for a in argv if a.startswith("grdm-dev/")][0]
            if self.fail_build_for and tag.startswith(f"grdm-dev/{self.fail_build_for}:"):
                return 1, "ERROR: failed to solve"
            return 0, "ok"
        return 0, ""


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(MANIFEST))
        self.out, self.err = io.StringIO(), io.StringIO()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, ctx, runner, **kw):
        args = argparse.Namespace(platform=kw.pop("platform", None), push=kw.pop("push", False), component=kw.pop("component", None))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return build.run(ctx, args, runner=runner)

    def test_local_build_argv_and_pinned_checkout(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64"), exit_codes.OK)
        clone = [c for c in runner.calls if c[:2] == ["git", "clone"]]
        self.assertEqual(len(clone), 1)
        self.assertIn("--filter=blob:none", clone[0])
        self.assertEqual(clone[0][-2], "https://github.com/RCOSDP/RDM-osf.io-dev2027.git")
        self.assertEqual(clone[0][-1], str(self.root / "runtime" / "src" / "RDM-osf.io-dev2027"))
        checkout = [c for c in runner.calls if "checkout" in c][0]
        self.assertEqual(checkout[-1], SHA_OSF)
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]
        self.assertEqual(len(bx), 1)  # minimum profile builds only osf.io
        self.assertEqual(bx[0][3:5], ["--platform", "linux/arm64"])
        self.assertIn("--load", bx[0])
        self.assertNotIn("--push", bx[0])
        self.assertIn(f"grdm-dev/osf.io:{SHA_OSF[:12]}", bx[0])
        self.assertNotIn(f"ghcr.io/rcosdp/osf.io:{SHA_OSF[:12]}", bx[0])
        self.assertEqual(bx[0][-1], str(self.root / "runtime" / "src" / "RDM-osf.io-dev2027"))

    def test_push_adds_registry_tag_and_branch_fallback(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64,linux/amd64", push=True), exit_codes.OK)
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]
        self.assertEqual(len(bx), 2)  # osf.io + waterbutler, not OASys (full) nor postgres (infra)
        wb = [c for c in bx if any(a.startswith("grdm-dev/waterbutler:") for a in c)][0]
        self.assertIn("--push", wb)
        self.assertIn(f"ghcr.io/rcosdp/waterbutler:{SHA_WB[:12]}", wb)
        self.assertEqual(wb[3:5], ["--platform", "linux/arm64,linux/amd64"])
        checkout = [c for c in runner.calls if "checkout" in c and "waterbutler" in c[2]][0]
        self.assertEqual(checkout[-1], SHA_WB)  # no integration_sha → first merged public upstream SHA

    def test_no_sha_at_all_falls_back_to_branch_head(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, component="OASys"), exit_codes.OK)
        checkout = [c for c in runner.calls if "checkout" in c][0]
        self.assertEqual(checkout[-1], "origin/develop")

    def test_invalid_manifest_is_20(self):
        (self.root / "manifest" / "upstreams.json").write_text("{not json")
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, FakeRunner()), exit_codes.MANIFEST_INVALID)

    def test_rerun_fetches_instead_of_cloning(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.run_cmd(ctx, runner)
        runner2 = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner2), exit_codes.OK)
        self.assertFalse([c for c in runner2.calls if c[:2] == ["git", "clone"]])
        self.assertTrue([c for c in runner2.calls if "fetch" in c])

    def test_build_failure_is_30_and_names_component(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner(fail_build_for="waterbutler")
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.BUILD_FAILED)
        self.assertIn("waterbutler", self.err.getvalue())
        self.assertIn("exit 30", self.err.getvalue())

    def test_clone_failure_is_30(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        rc = self.run_cmd(ctx, FakeRunner(fail_git_for="RDM-osf.io-dev2027"))
        self.assertEqual(rc, exit_codes.BUILD_FAILED)
        self.assertIn("osf.io", self.err.getvalue())

    def test_unknown_component_is_usage_error(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, FakeRunner(), component="nope"), exit_codes.USAGE)

    def test_component_filter_ignores_profile(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, component="OASys"), exit_codes.OK)
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]
        self.assertEqual(len(bx), 1)
        self.assertTrue(any(a.startswith("grdm-dev/oasys:") for a in bx[0]))  # lower-cased image name

    def test_host_platform_mapping(self):
        self.assertIn(build.host_platform(), ("linux/arm64", "linux/amd64") + (f"linux/{build._platform.machine().lower()}",))


if __name__ == "__main__":
    unittest.main()
