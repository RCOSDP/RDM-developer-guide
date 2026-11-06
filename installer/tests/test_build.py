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

    def _with_native_elasticsearch(self):
        data = json.loads((self.root / "manifest" / "upstreams.json").read_text())
        data["components"].append(comp("elasticsearch2", "infra", "minimum", None, ["elasticsearch"],
                                       image_build={"context": "installer/images/elasticsearch2", "tag": "2.4.6-1"},
                                       base_image="eclipse-temurin:8-jre", base_image_digest="sha256:" + "ab" * 32,
                                       note="official image is amd64-only (ADR-07); retired at M5"))
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(data))
        ctxdir = self.root / "installer" / "images" / "elasticsearch2"
        ctxdir.mkdir(parents=True)
        (ctxdir / "Dockerfile").write_text("FROM scratch\n")

    def test_image_build_component_is_built_from_the_repository_without_a_clone(self):
        """SPEC-01 §3 image_build (ADR-07): an infra image built from a Dockerfile in this repository."""
        self._with_native_elasticsearch()
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.OK, self.err.getvalue())
        self.assertFalse([c for c in runner.calls if c[0] == "git" and "elasticsearch" in " ".join(c)])
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"] and "elasticsearch2" in " ".join(c)]
        self.assertEqual(len(bx), 1)
        self.assertIn("-t", bx[0]); self.assertIn("grdm-dev/elasticsearch2:2.4.6-1", bx[0])
        self.assertEqual(bx[0][-1], str(self.root / "installer" / "images" / "elasticsearch2"))
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["elasticsearch2"]["status"], "built")
        self.assertEqual(rows["elasticsearch2"]["image"], "grdm-dev/elasticsearch2:2.4.6-1")
        self.assertEqual(rows["elasticsearch2"]["image_tag"], "2.4.6-1")
        self.assertEqual(rows["elasticsearch2"]["context"], "installer/images/elasticsearch2")
        self.assertIn("natively", self.err.getvalue())
        # SPEC-03 §3.4: the pinned base digest travels into the image as a label (review PR #34 r1 R1-03)
        self.assertIn("org.opencontainers.image.base.digest=sha256:" + "ab" * 32, bx[0])

    def test_image_build_without_dockerfile_is_30(self):
        self._with_native_elasticsearch()
        (self.root / "installer" / "images" / "elasticsearch2" / "Dockerfile").unlink()
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, FakeRunner()), exit_codes.BUILD_FAILED)
        self.assertIn("no Dockerfile", self.err.getvalue())

    def test_image_build_push_uses_the_registry_tag(self):
        self._with_native_elasticsearch()
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, push=True), exit_codes.OK, self.err.getvalue())
        bx = [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"] and "elasticsearch2" in " ".join(c)][0]
        self.assertIn("--push", bx); self.assertIn("ghcr.io/rcosdp/elasticsearch2:2.4.6-1", bx)
        self.assertNotIn("grdm-dev/elasticsearch2:2.4.6-1", bx)

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

    def test_prebuilt_with_push_is_pulled_but_never_pushed(self):
        """Review r4: --push must not re-publish a third-party prebuilt image to ghcr.io."""
        self._with_prebuilt_waterbutler()
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = FakeRunner()
        self.assertEqual(self.run_cmd(ctx, runner, push=True, component="waterbutler"), exit_codes.OK)
        self.assertFalse([c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]])
        self.assertFalse(any("ghcr.io" in a for c in runner.calls for a in c))
        rows = {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}
        self.assertEqual(rows["waterbutler"]["status"], "prebuilt-not-pushed")
        self.assertIs(rows["waterbutler"]["pushed"], False)

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


# ---- overlay_of (SPEC-01 §3, ADR-06): wiki-frontend is built from the osf.io checkout + its files; its own image, both SHAs in the tag

SHA_WIKI = "203d32fab60aad8d78e9b743987519252f99b817"
OVERLAY_MANIFEST = {
    "schema_version": 1,
    "generated_at": "2026-11-06",
    "components": [
        comp("osf.io", "core", "minimum", "RDM-osf.io-dev2027", ["web", "api"], integration_sha=SHA_OSF),
        comp("waterbutler", "core", "core", "RDM-waterbutler-dev2027", ["wb"], upstreams=[UPSTREAM_WB]),
        comp("wiki-frontend", "core", "core", "RDM-wiki-frontend-dev2027", ["wiki_assets"], integration_sha=SHA_WIKI, overlay_of="osf.io"),
        comp("postgres", "infra", "minimum", None, ["postgres"]),
    ],
}

# What the two checkouts contain after a fake clone (relative path -> content). The real layout: the
# wiki-frontend checkout has only addons/wiki, website/static, package.json, yarn.lock, the two
# webpack configs, a Dockerfile derived from osf.io's and a README (real install run 4).
BASE_FILES = {
    "Dockerfile": "FROM node:12-alpine3.9\n",
    "package.json": '{"webpack": "3.8.1"}\n',
    "addons/s3/requirements.txt": "boto3\n",
    "addons/wiki/static/old.js": "// webpack 3 bundle entry\n",
    "admin/yarn.lock": "# admin\n",
    "website/static/js/pages/base-page.js": "// base\n",
}
OVERLAY_FILES = {
    "Dockerfile": "FROM node:21-alpine\n",
    "package.json": '{"webpack": "^5.93.0"}\n',
    "addons/wiki/static/wikiPageMilkdown.js": "// milkdown\n",
    "website/static/js/wikiTree.js": "// tree\n",
    "README.md": "This is RDM wiki code for bundle with webpack5\n",
}


class OverlayRunner(FakeRunner):
    """A fake clone also writes the checkout's files, so the overlay context assembly is observable."""

    def __init__(self, fail_git_for=None, fail_build_for=None):
        super().__init__(fail_git_for=fail_git_for, fail_build_for=fail_build_for)

    def __call__(self, argv):
        if argv[0] == "git" and argv[1] == "clone":
            repo = argv[-2].rsplit("/", 1)[-1].removesuffix(".git")
            if repo == self.fail_git_for:
                self.calls.append(argv)
                return 128, "fatal: repository not found"
            dest = Path(argv[-1])
            files = OVERLAY_FILES if "wiki" in repo else BASE_FILES
            for rel, text in files.items():
                (dest / rel).parent.mkdir(parents=True, exist_ok=True)
                (dest / rel).write_text(text)
            (dest / ".git").mkdir(parents=True, exist_ok=True)
            (dest / ".git" / "HEAD").write_text("ref: refs/heads/develop\n")
            self.calls.append(argv)
            return 0, ""
        if argv[0] == "git" and argv[-2] == "rev-parse":
            self.calls.append(argv)
            return 0, (SHA_WIKI if "wiki" in argv[2] else SHA_OSF if "osf.io" in argv[2] else SHA_WB) + "\n"
        return super().__call__(argv)


class OverlayBuildTests(unittest.TestCase):
    TAG = f"{SHA_OSF[:12]}-{SHA_WIKI[:12]}"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "manifest").mkdir()
        (self.root / "manifest" / "upstreams.json").write_text(json.dumps(OVERLAY_MANIFEST))
        self.out, self.err = io.StringIO(), io.StringIO()
        self.src = self.root / "runtime" / "src"
        self.context = self.src / "_overlay" / "wiki-frontend"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, ctx, runner, **kw):
        args = argparse.Namespace(platform=kw.pop("platform", None), push=kw.pop("push", False), component=kw.pop("component", None))
        with redirect_stdout(self.out), redirect_stderr(self.err):
            return build.run(ctx, args, runner=runner)

    def rows(self):
        return {r["component"]: r for r in json.loads((self.root / "runtime" / "reports" / "build_latest.json").read_text())["components"]}

    def bx(self, runner):
        return [c for c in runner.calls if c[:3] == ["docker", "buildx", "build"]]

    def test_overlay_is_built_from_the_merged_context_with_its_dockerfile_and_both_shas_in_the_tag(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = OverlayRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64"), exit_codes.OK, self.err.getvalue())
        clones = [c[-2].rsplit("/", 1)[-1] for c in runner.calls if c[:2] == ["git", "clone"]]
        self.assertEqual(clones, ["RDM-osf.io-dev2027.git", "RDM-waterbutler-dev2027.git", "RDM-wiki-frontend-dev2027.git"])  # the base is synced once
        checkouts = {c[2].rsplit("/", 1)[-1]: c[-1] for c in runner.calls if "checkout" in c}
        self.assertEqual(checkouts["RDM-wiki-frontend-dev2027"], SHA_WIKI)
        self.assertEqual(checkouts["RDM-osf.io-dev2027"], SHA_OSF)
        bx = {c[c.index("-t") + 1].split("/")[1].split(":")[0]: c for c in self.bx(runner)}
        self.assertEqual(set(bx), {"osf.io", "waterbutler", "wiki-frontend"})  # three images: the base is built normally too
        self.assertEqual(bx["osf.io"], [
            "docker", "buildx", "build", "--platform", "linux/arm64",
            "--load", "-t", f"grdm-dev/osf.io:{SHA_OSF[:12]}",
            "--label", "org.gakunin-rdm.component=osf.io", "--label", f"org.gakunin-rdm.sha={SHA_OSF[:12]}",
            str(self.src / "RDM-osf.io-dev2027"),
        ])
        self.assertEqual(bx["wiki-frontend"], [
            "docker", "buildx", "build", "--platform", "linux/arm64",
            "--load", "-t", f"grdm-dev/wiki-frontend:{self.TAG}",
            "--label", "org.gakunin-rdm.component=wiki-frontend", "--label", f"org.gakunin-rdm.sha={self.TAG}",
            "--label", "org.gakunin-rdm.overlay-of=osf.io", "--label", f"org.gakunin-rdm.base-sha={SHA_OSF[:12]}",
            "-f", str(self.context / "Dockerfile"),
            str(self.context),
        ])
        # the assembled context: base tree + overlay files on top, overlay wins on conflicts, no .git
        self.assertEqual((self.context / "Dockerfile").read_text(), OVERLAY_FILES["Dockerfile"])
        self.assertEqual((self.context / "package.json").read_text(), OVERLAY_FILES["package.json"])
        self.assertEqual((self.context / "addons/s3/requirements.txt").read_text(), BASE_FILES["addons/s3/requirements.txt"])  # base only
        self.assertEqual((self.context / "admin/yarn.lock").read_text(), BASE_FILES["admin/yarn.lock"])
        self.assertTrue((self.context / "addons/wiki/static/old.js").exists())  # base file next to the overlay's
        self.assertEqual((self.context / "addons/wiki/static/wikiPageMilkdown.js").read_text(), OVERLAY_FILES["addons/wiki/static/wikiPageMilkdown.js"])
        self.assertEqual((self.context / "README.md").read_text(), OVERLAY_FILES["README.md"])
        self.assertFalse((self.context / ".git").exists())
        # the checkouts themselves are untouched
        self.assertEqual((self.src / "RDM-osf.io-dev2027" / "Dockerfile").read_text(), BASE_FILES["Dockerfile"])
        self.assertTrue((self.src / "RDM-osf.io-dev2027" / ".git").exists())
        self.assertTrue((self.src / "RDM-wiki-frontend-dev2027" / ".git").exists())
        rows = self.rows()
        self.assertEqual(list(rows), ["osf.io", "waterbutler", "wiki-frontend"])
        osf = rows["osf.io"]
        self.assertEqual((osf["status"], osf["sha12"], osf["image_tag"], osf["image"]), ("built", SHA_OSF[:12], SHA_OSF[:12], f"grdm-dev/osf.io:{SHA_OSF[:12]}"))
        self.assertNotIn("overlay_of", osf)
        row = rows["wiki-frontend"]
        self.assertEqual(row["status"], "built")
        self.assertEqual(row["sha12"], SHA_WIKI[:12])
        self.assertEqual(row["image_tag"], self.TAG)
        self.assertEqual(row["image"], f"grdm-dev/wiki-frontend:{self.TAG}")
        self.assertEqual(row["overlay_of"], "osf.io")
        self.assertEqual(row["base_repo"], "RDM-osf.io-dev2027")
        self.assertEqual(row["base_sha12"], SHA_OSF[:12])
        self.assertEqual(row["context"], str(self.context))
        self.assertIn("overlay of osf.io", self.err.getvalue())

    def test_compose_reads_both_tags_from_the_build_report(self):
        from grdm_dev import compose
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, OverlayRunner()), exit_codes.OK)
        self.assertEqual(compose.built_image_tags(ctx), {"osf.io": SHA_OSF[:12], "waterbutler": SHA_WB[:12], "wiki-frontend": self.TAG})

    def test_component_flag_naming_the_overlay_syncs_its_base_but_builds_only_the_overlay(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = OverlayRunner()
        self.assertEqual(self.run_cmd(ctx, runner, component="wiki-frontend", platform="linux/arm64"), exit_codes.OK)
        clones = sorted(c[-2].rsplit("/", 1)[-1] for c in runner.calls if c[:2] == ["git", "clone"])
        self.assertEqual(clones, ["RDM-osf.io-dev2027.git", "RDM-wiki-frontend-dev2027.git"])
        bx = self.bx(runner)
        self.assertEqual(len(bx), 1)
        self.assertIn(f"grdm-dev/wiki-frontend:{self.TAG}", bx[0])
        self.assertFalse(any("grdm-dev/osf.io" in a for a in bx[0]))
        self.assertEqual(list(self.rows()), ["wiki-frontend"])

    def test_minimum_profile_does_not_build_the_overlay(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = OverlayRunner()
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.OK)
        self.assertEqual(len(self.bx(runner)), 1)  # osf.io only (wiki-frontend is core)
        self.assertFalse(self.context.exists())

    def test_push_uses_the_combined_tag_under_ghcr(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = OverlayRunner()
        self.assertEqual(self.run_cmd(ctx, runner, platform="linux/arm64,linux/amd64", push=True, component="wiki-frontend"), exit_codes.OK)
        bx = self.bx(runner)[0]
        self.assertEqual(bx[bx.index("-t") + 1], f"ghcr.io/rcosdp/wiki-frontend:{self.TAG}")
        self.assertEqual(bx.count("-t"), 1)
        self.assertFalse(any(a.startswith("grdm-dev/") for a in bx))
        self.assertEqual(self.rows()["wiki-frontend"]["image"], f"ghcr.io/rcosdp/wiki-frontend:{self.TAG}")

    def test_rerun_recreates_the_context_and_drops_stale_files(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        self.assertEqual(self.run_cmd(ctx, OverlayRunner()), exit_codes.OK)
        (self.context / "stale.txt").write_text("left over from an older overlay commit\n")
        runner = OverlayRunner()
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.OK)
        self.assertFalse([c for c in runner.calls if c[:2] == ["git", "clone"]])  # every checkout is fetched, not cloned
        self.assertEqual(len([c for c in runner.calls if "fetch" in c]), 3)  # osf.io once, waterbutler, wiki-frontend
        self.assertFalse((self.context / "stale.txt").exists())
        self.assertEqual((self.context / "Dockerfile").read_text(), OVERLAY_FILES["Dockerfile"])

    def test_base_clone_failure_while_building_the_overlay_alone_is_30(self):
        ctx = Context(root=self.root, profile="minimum", stdin_is_tty=False)
        runner = OverlayRunner(fail_git_for="RDM-osf.io-dev2027")
        self.assertEqual(self.run_cmd(ctx, runner, component="wiki-frontend"), exit_codes.BUILD_FAILED)
        self.assertFalse(self.bx(runner))
        self.assertIn("wiki-frontend", self.err.getvalue())
        self.assertIn("base of overlay", self.err.getvalue())
        row = self.rows()["wiki-frontend"]
        self.assertEqual(row["status"], "source-failed")
        self.assertEqual(row["overlay_of"], "osf.io")
        self.assertFalse(self.context.exists())

    def test_overlay_build_failure_is_30_and_names_the_overlay_and_its_base(self):
        ctx = Context(root=self.root, profile="core", stdin_is_tty=False)
        runner = OverlayRunner(fail_build_for="wiki-frontend")
        self.assertEqual(self.run_cmd(ctx, runner), exit_codes.BUILD_FAILED)
        self.assertIn("component wiki-frontend", self.err.getvalue())
        self.assertIn("(overlay of osf.io)", self.err.getvalue())
        rows = self.rows()
        self.assertEqual(rows["osf.io"]["status"], "built")  # the base image is unaffected
        self.assertEqual(rows["wiki-frontend"]["status"], "build-failed")

    def test_assemble_overlay_context_directly(self):
        base, overlay, target = self.root / "base", self.root / "overlay", self.root / "ctx"
        for rel, text in BASE_FILES.items():
            (base / rel).parent.mkdir(parents=True, exist_ok=True); (base / rel).write_text(text)
        for rel, text in OVERLAY_FILES.items():
            (overlay / rel).parent.mkdir(parents=True, exist_ok=True); (overlay / rel).write_text(text)
        (base / ".git").mkdir(); (base / ".git" / "config").write_text("x")
        (overlay / ".git").mkdir(); (overlay / ".git" / "config").write_text("y")
        self.assertEqual(build.assemble_overlay_context(target, base, overlay), target)
        names = sorted(str(p.relative_to(target)) for p in target.rglob("*") if p.is_file())
        self.assertEqual(names, sorted(set(BASE_FILES) | set(OVERLAY_FILES)))
        self.assertEqual((target / "Dockerfile").read_text(), OVERLAY_FILES["Dockerfile"])
        self.assertEqual(build.overlay_context_dir(self.root / "runtime", "wiki-frontend"), self.root / "runtime" / "src" / "_overlay" / "wiki-frontend")


if __name__ == "__main__":
    unittest.main()
