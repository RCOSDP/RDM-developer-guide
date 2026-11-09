"""The Google Analytics guard of templates/ember_osf_web.json, run for real (PR #35 review r1 R1-03).

The ember image has node and a read-only /code, so the guard is a node script carried as the last
element of the container command. These tests execute that exact script and that exact shell command
(with /code pointed at a temporary directory and yarn/ember replaced by stubs).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import quote, unquote

from grdm_dev import compose

TEMPLATE = Path(compose.__file__).parent / "templates" / "ember_osf_web.json"
NODE = shutil.which("node")
NAME = "ember-osf-web/config/environment"
GA = {"name": "GoogleAnalytics", "environments": ["all"], "config": {"id": "UA-84580271-1"}}
KEEN = {"name": "Keen", "environments": ["all"], "config": {}}


def encode(config) -> str:
    return quote(json.dumps(config), safe="")


def page(content: str, meta=None) -> str:
    tag = f'<meta name="{NAME}" content="{content}" />' if meta is None else meta
    return f'<!DOCTYPE html><html><head><meta charset="utf-8">{tag}<title>x</title></head><body></body></html>\n'


def config(*adapters):
    return {"modulePrefix": "ember-osf-web", "metricsAdapters": list(adapters)}


def adapters_in(html: str) -> list[str]:
    start = html.index('content="', html.index(NAME)) + len('content="')
    return [a["name"] for a in json.loads(unquote(html[start:html.index('"', start)]))["metricsAdapters"]]


@unittest.skipUnless(NODE, "node is not installed")
class GuardScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = Path(self.tmp.name) / "index.html"
        self.script = json.loads(TEMPLATE.read_text(encoding="utf-8"))["command"][-1]

    def guard(self, html: str):
        self.index.write_text(html, encoding="utf-8")
        proc = subprocess.run([NODE, "-e", self.script, str(self.index)], capture_output=True, text=True)
        return proc.returncode, proc.stderr

    def assert_refused(self, html: str, reason: str):
        rc, err = self.guard(html)
        self.assertEqual(rc, 1, err)
        self.assertIn(reason, err)

    def test_normal_build_loses_only_the_ga_adapter(self):
        self.assertEqual(self.guard(page(encode(config(GA, KEEN))))[0], 0)
        html = self.index.read_text(encoding="utf-8")
        self.assertEqual(adapters_in(html), ["Keen"])
        self.assertNotIn("GoogleAnalytics", unquote(html))

    def test_other_attribute_order_and_quotes_are_still_parsed(self):
        meta = f"<META content='{encode(config(GA, KEEN))}' data-x=\"1\" name='{NAME}'>"
        self.assertEqual(self.guard(page("", meta=meta))[0], 0)
        self.assertNotIn("GoogleAnalytics", unquote(self.index.read_text(encoding="utf-8")))

    def test_percent_encoded_adapter_name_is_removed(self):
        content = encode(config(GA, KEEN)).replace("GoogleAnalytics", "%47oogleAnalytics")
        html = page(content)
        self.assertNotIn("GoogleAnalytics", html)  # the old raw grep sees nothing here
        self.assertEqual(self.guard(html)[0], 0)
        self.assertEqual(adapters_in(self.index.read_text(encoding="utf-8")), ["Keen"])

    def test_already_clean_output_is_left_untouched(self):
        html = page(encode(config(KEEN)))
        self.assertEqual(self.guard(html)[0], 0)
        self.assertEqual(self.index.read_text(encoding="utf-8"), html)

    def test_no_matching_tag_stops(self):
        self.assert_refused("<html><head></head></html>", "exactly one config meta tag, found 0")
        self.assert_refused(page("", meta=f'<meta name="other/config/environment" content="{encode(config(GA))}">'), "found 0")

    def test_two_tags_stop(self):
        tag = f'<meta name="{NAME}" content="{encode(config(KEEN))}">'
        self.assert_refused(page("", meta=tag + tag), "found 2")

    def test_unquoted_or_missing_content_stops(self):
        self.assert_refused(page("", meta=f'<meta name="{NAME}">'), "no quoted content")
        self.assert_refused(page("", meta=f'<meta name="{NAME}" content={encode(config(GA))}>'), "no quoted content")

    def test_invalid_config_stops(self):
        self.assert_refused(page("not%20json"), "does not decode")
        self.assert_refused(page("%E0%A4%A"), "does not decode")
        self.assert_refused(page(encode(["x"])), "metricsAdapters")
        self.assert_refused(page(encode({"modulePrefix": "x"})), "metricsAdapters")
        self.assert_refused(page(encode({"metricsAdapters": "GoogleAnalytics"})), "metricsAdapters")
        self.assert_refused(page(encode({"metricsAdapters": ["GoogleAnalytics"]})), "no name")

    def test_html_entities_in_content_stop(self):
        """A browser decodes `&#37;` before ember decodes the URI, so the name would not be what we parsed."""
        content = encode(config(KEEN)).replace("Keen", "&#37;47oogleAnalytics")
        self.assert_refused(page(content), "not URI-encoded")

    def test_ga_left_elsewhere_in_the_page_or_config_stops(self):
        self.assert_refused(page(encode({"note": "GoogleAnalytics", "metricsAdapters": [KEEN]})), "still in the built page")
        html = page(encode(config(KEEN))).replace("<title>x</title>", "<script>GoogleAnalytics()</script>")
        self.assert_refused(html, "still in the built page")


@unittest.skipUnless(NODE, "node is not installed")
class ContainerCommandTests(unittest.TestCase):
    """The whole shell command: the guard must run before every serve, and a refusal must stop the serve."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.code = Path(self.tmp.name) / "code"
        (self.code / "dist").mkdir(parents=True)
        bin_dir = self.code / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (self.code / "stub").mkdir()
        self.log = self.code / "ember.log"
        self.write_exe(self.code / "stub" / "yarn", "#!/bin/sh\nexit 0\n")
        self.built = self.code / "built.html"
        self.write_exe(bin_dir / "ember", f'#!/bin/sh\necho "$1" >> "{self.log}"\n'
                                          f'if [ "$1" = build ]; then cp "{self.built}" "{self.code}/dist/index.html"; fi\n')
        self.built.write_text(page(encode(config(GA, KEEN))), encoding="utf-8")
        command = json.loads(TEMPLATE.read_text(encoding="utf-8"))["command"]
        self.assertEqual(command[:2], ["/bin/sh", "-c"])
        self.argv = [command[0], command[1], command[2].replace("/code", str(self.code)), *command[3:]]
        self.env = {**os.environ, "PATH": f"{self.code / 'stub'}:{os.environ['PATH']}", "GRDM_IMAGE": "img@sha256:abc", "GRDM_BUILD_RECIPE": "3"}

    @staticmethod
    def write_exe(path: Path, body: str) -> None:
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def start(self):
        return subprocess.run(self.argv, capture_output=True, text=True, env=self.env)

    def calls(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").split() if self.log.exists() else []

    def test_fresh_build_is_cleaned_and_served(self):
        proc = self.start()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls(), ["build", "serve"])
        self.assertEqual(adapters_in((self.code / "dist" / "index.html").read_text(encoding="utf-8")), ["Keen"])

    def test_cache_hit_is_checked_and_served_without_a_rebuild(self):
        self.assertEqual(self.start().returncode, 0)
        self.log.unlink()
        self.assertEqual(self.start().returncode, 0)
        self.assertEqual(self.calls(), ["serve"])

    def test_cached_output_with_ga_is_cleaned_before_the_serve(self):
        self.assertEqual(self.start().returncode, 0)
        self.log.unlink()
        cached = self.code / "dist" / "index.html"
        cached.write_text(page(encode(config(GA, KEEN))), encoding="utf-8")
        proc = self.start()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.calls(), ["serve"])
        self.assertNotIn("GoogleAnalytics", unquote(cached.read_text(encoding="utf-8")))

    def test_cached_output_that_cannot_be_checked_stops_the_start(self):
        self.assertEqual(self.start().returncode, 0)
        self.log.unlink()
        (self.code / "dist" / "index.html").write_text("<html><head></head></html>", encoding="utf-8")
        proc = self.start()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refusing to serve", proc.stderr)
        self.assertEqual(self.calls(), [])

    def test_a_refused_build_is_not_recorded_as_cached_and_is_not_served(self):
        self.built.write_text("<html><head></head></html>", encoding="utf-8")
        proc = self.start()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(self.calls(), ["build"])
        self.assertFalse((self.code / "dist" / ".grdm-build").exists())


if __name__ == "__main__":
    unittest.main()
