"""The Google Analytics guard of ember_osf_web (PR #35 review r1 R1-03), after the static image (PR #2 review r1 R1-03).

The former prebuilt image ran `ember serve`, so the installer carried a node script in the container
command that removed the Google Analytics adapter from dist/index.html before every serve. The static
image built from RDM-ember-osf-web-dev2027 carries the guard itself: its build leaves the adapter out
(docker/static/postbuild.js) and its entrypoint refuses to serve when "GoogleAnalytics" is in the
rendered index.html. The guard therefore holds only while the installer leaves that entrypoint alone:
no `command` or `entrypoint` in the template or the rendered service, and no variable that would bring
the adapter back (GOOGLE_ANALYTICS_ID is a build-time setting the image does not read at run time).
"""
import json
import unittest
from pathlib import Path

from grdm_dev import compose

TEMPLATE = Path(compose.__file__).parent / "templates" / "ember_osf_web.json"


class StaticImageGuardTests(unittest.TestCase):
    def setUp(self):
        self.tpl = json.loads(TEMPLATE.read_text(encoding="utf-8"))

    def test_the_image_entrypoint_is_not_overridden(self):
        self.assertNotIn("command", self.tpl)
        self.assertNotIn("entrypoint", self.tpl)

    def test_no_variable_reintroduces_analytics_or_a_dev_server(self):
        env = self.tpl["environment"]
        for key in env:
            self.assertNotIn("GOOGLE", key.upper())
            self.assertNotIn("ANALYTICS", key.upper())
        for retired in ("BACKEND", "JOBS", "NODE_OPTIONS", "YARN_CACHE_FOLDER", "GRDM_IMAGE", "GRDM_BUILD_RECIPE"):
            self.assertNotIn(retired, env)  # ember serve settings: the static image reads none of them
        self.assertNotIn("GoogleAnalytics", json.dumps(env))

    def test_rendered_service_keeps_the_image_entrypoint(self):
        from test_compose import make_root, render

        root = make_root()
        rc, _, err, _ = render(root)
        self.assertEqual(rc, 0, err)
        svc = json.loads((root / "runtime" / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["ember_osf_web"]
        self.assertNotIn("command", svc)
        self.assertNotIn("entrypoint", svc)


if __name__ == "__main__":
    unittest.main()
