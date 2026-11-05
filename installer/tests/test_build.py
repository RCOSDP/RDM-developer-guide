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
            tag = argv[argv.index("-t") + 1]
            if self.fail_build_for and tag.split("/")[-1].startswith(f"{self.fail_build_for}:"):
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
        self.assertEqual(clone[0][-2], "https://github.com/" + "RCOSDP/" + "RDM-osf.io-dev2027" + ".git")  # built at run time: no private address literal
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

    def test_push_uses_only_the_ghcr_tag_and_branch_fallback(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64,linux/amd64", push=True), exit_codes.OK)
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]
        self.assertEqual(len(bx), 2)  # osf.io + waterbutler, not OASys (full) nor postgres (infra)
        wb = [c for c in bx if "waterbutler" in c[-1]][0]
        # the complete argument list: exactly one -t, fully qualified, no Docker Hub (unqualified) destination
        self.assertEqual(wb, [
            "docker", "buildx", "build", "--platform", "linux/arm64,linux/amd64",
            "--push", "-t", f"ghcr.io/rcosdp/waterbutler:{SHA_WB[:12]}",
            "--label", "org.gakunin-rdm.component=waterbutler", "--label", f"org.gakunin-rdm.sha={SHA_WB[:12]}",
            str(self.root / "runtime" / "src" / "RDM-waterbutler-dev2027"),
        ])
        self.assertEqual(wb.count("-t"), 1)
        self.assertFalse(any(a.startswith("grdm-dev/") for a in wb))
        self.assertNotIn("--load", wb)
        checkout = [c for c in runner.calls if "checkout" in c and "waterbutler" in c[2]][0]
        self.assertEqual(checkout[-1], SHA_WB)  # no integration_sha → first merged public upstream SHA
        rows = json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]
        self.assertEqual([r["status"] for r in rows], ["pushed", "pushed"])
        self.assertEqual(rows[1]["image"], f"ghcr.io/rcosdp/waterbutler:{SHA_WB[:12]}")

    def test_local_build_argv_is_exactly_the_load_form(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64"), exit_codes.OK)
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]][0]
        self.assertEqual(bx, [
            "docker", "buildx", "build", "--platform", "linux/arm64",
            "--load", "-t", f"grdm-dev/osf.io:{SHA_OSF[:12]}",
            "--label", "org.gakunin-rdm.component=osf.io", "--label", f"org.gakunin-rdm.sha={SHA_OSF[:12]}",
            str(self.root / "runtime" / "src" / "RDM-osf.io-dev2027"),
        ])

    # ---- per-component build_platform (manifest field; coordinator addendum after the first arm64 run)

    def test_build_platform_from_manifest_wins_over_host_and_yields_to_flag(self):
        data = json.loads((self.root / "manifest" / "upstreams.json").read_text())
        data["components"][1]["build_platform"] = "linux/amd64"  # waterbutler stands in for mfr here
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(data))
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.OK)
        bx = {c[-1].rsplit("/", 1)[-1]: c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]}
        self.assertEqual(bx["RDM-waterbutler-dev2027"][3:5], ["--platform", "linux/amd64"])
        self.assertEqual(bx["RDM-osf.io-dev2027"][3:5], ["--platform", build.host_platform()])
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["waterbutler"]["platforms"], "linux/amd64")
        self.assertEqual(rows["osf.io"]["platforms"], build.host_platform())
        # --platform overrides every component
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64"), exit_codes.OK)
        for c in (c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]):
            self.assertEqual(c[3:5], ["--platform", "linux/arm64"])

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

    # ---- prebuilt_image (SPEC-01 §3): the component is pulled, not cloned or built (ember-osf-web until M4)

    PREBUILT = "niicloudoperation/rdm-ember-osf-web@sha256:" + "e" * 64

    def _with_prebuilt_waterbutler(self):
        data = json.loads((self.root / "manifest" / "upstreams.json").read_text())
        data["components"][1]["prebuilt_image"] = self.PREBUILT  # waterbutler stands in for ember-osf-web here
        data["components"][1]["build_platform"] = "linux/amd64"
        data["components"][1]["note"] = "schema-1 base image; remove at M4"
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(data))

    def test_prebuilt_component_is_pulled_and_recorded_not_built(self):
        self._with_prebuilt_waterbutler()
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.OK)
        self.assertFalse([c for c in runner.calls if c[0] == "git" and "waterbutler" in " ".join(c)])
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]
        self.assertEqual(len(bx), 1)  # osf.io only
        self.assertFalse(any("waterbutler" in a for c in bx for a in c))
        pulls = [c for c in runner.calls if c[:2] == ["docker", "pull"]]
        self.assertEqual(pulls, [["docker", "pull", "--platform", "linux/amd64", self.PREBUILT]])
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["waterbutler"]["status"], "prebuilt")
        self.assertEqual(rows["waterbutler"]["image"], self.PREBUILT)
        self.assertEqual(rows["waterbutler"]["sha12"], "")
        self.assertEqual(rows["waterbutler"]["platforms"], "linux/amd64")
        self.assertIn("M4", rows["waterbutler"]["note"])
        self.assertEqual(rows["osf.io"]["status"], "built")
        self.assertIn("prebuilt_image", self.err.getvalue())
        self.assertFalse((self.root / "runtime" / "src" / "RDM-waterbutler-dev2027").exists())

    def test_prebuilt_pull_failure_is_30_and_names_component(self):
        self._with_prebuilt_waterbutler()

        class PullFails(FakeRunner):
            def __call__(self, argv):
                if argv[:2] == ["docker", "pull"]:
                    self.calls.append(argv)
                    return 1, "Error response from daemon: manifest unknown"
                return super().__call__(argv)

        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, PullFails()), exit_codes.BUILD_FAILED)
        self.assertIn("waterbutler", self.err.getvalue())
        self.assertIn("prebuilt_image", self.err.getvalue())
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["waterbutler"]["status"], "pull-failed")

    def test_prebuilt_multi_platform_pulls_each_and_fails_on_any(self):
        """Review r3 R3-01: with --platform a,b every platform is pulled; a missing one fails with 30."""
        self._with_prebuilt_waterbutler()
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)

        class PlatformRunner(FakeRunner):
            def __call__(self, argv):
                if argv[:2] == ["docker", "pull"] and "linux/arm64" in argv:
                    self.calls.append(list(argv))
                    return 1, "no matching manifest for linux/arm64"
                return super().__call__(argv)

        runner = PlatformRunner()
        rc = self.run_cmd(ctx, runner, platform="linux/arm64,linux/amd64", component="waterbutler")
        pulls = [c for c in runner.calls if c[:2] == ["docker", "pull"]]
        self.assertEqual(sorted(c[3] for c in pulls), ["linux/amd64", "linux/arm64"])
        self.assertEqual(rc, exit_codes.BUILD_FAILED)
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["waterbutler"]["status"], "pull-failed")
        self.assertEqual(rows["waterbutler"]["pulled"], "linux/amd64")

    def test_prebuilt_component_can_be_selected_alone_and_platform_flag_applies(self):
        self._with_prebuilt_waterbutler()
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, component="waterbutler", platform="linux/arm64"), exit_codes.OK)
        self.assertEqual(runner.calls, [["docker", "pull", "--platform", "linux/arm64", self.PREBUILT]])

    def test_pull_argv(self):
        self.assertEqual(build.pull_argv("img@sha256:" + "0" * 64, None), ["docker", "pull", "img@sha256:" + "0" * 64])

    def test_host_platform_mapping(self):
        self.assertIn(build.host_platform(), ("linux/arm64", "linux/amd64") + (f"linux/{build._platform.machine().lower()}",))


if __name__ == "__main__":
    unittest.main()
