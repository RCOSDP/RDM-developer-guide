"""installer/images/unoconv/convert_service.py with a stub soffice: limits, deadlines and authentication."""
from __future__ import annotations

import http.client
import importlib.util
import os
import shutil
import socket
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

SERVICE = Path(__file__).resolve().parents[1] / "images" / "unoconv" / "convert_service.py"
SECRET = "probe-secret"
AUTH = {"Authorization": "Bearer " + SECRET}
STUB = """#!/bin/sh
outdir=""; prev=""
for a in "$@"; do [ "$prev" = "--outdir" ] && outdir="$a"; prev="$a"; done
sleep "${STUB_SLEEP:-0}"
printf 'converted' > "$outdir/input.pdf"
"""


def load_service(root: Path):
    spec = importlib.util.spec_from_file_location(f"convert_service_{id(root)}", SERVICE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stub = root / "soffice"
    stub.write_text(STUB)
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    jobs = root / "jobs"
    jobs.mkdir()
    module.SECRET = SECRET
    module.SOFFICE = str(stub)
    module.PRLIMIT = ""
    module.JOB_ROOT = str(jobs)
    module.PROFILE_SEED = str(SERVICE.parent / "registrymodifications.xcu")
    return module


class ConvertServiceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="convert-test-"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.svc = load_service(self.root)
        self.svc.HEADER_DEADLINE_SEC = 0.5
        self.svc.REQUEST_DEADLINE_SEC = 1.5
        self.svc.QUEUE_WAIT_SEC = 0.3
        self.svc.TIMEOUT_SEC = 1.0
        self.start_server(workers=4, pending=2)

    def start_server(self, workers, pending):
        self.server = self.svc.BoundedServer(("127.0.0.1", 0), self.svc.Handler, workers=workers, pending=pending)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def post(self, body=b"doc", headers=AUTH, query="format=pdf&ext=docx"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            conn.request("POST", "/convert?" + query, body=body, headers=headers)
            response = conn.getresponse()
            return response.status, response.read()
        finally:
            conn.close()

    def raw(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        self.addCleanup(sock.close)
        return sock

    def wait_for(self, predicate, seconds=5.0):
        limit = time.monotonic() + seconds
        while time.monotonic() < limit:
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def free_slots(self):
        return self.svc.slots._value

    def test_valid_request_returns_the_converted_file_and_cleans_up(self):
        self.assertEqual(self.post(), (200, b"converted"))
        self.assertTrue(self.wait_for(lambda: os.listdir(self.svc.JOB_ROOT) == []))

    def test_missing_or_invalid_credential_is_refused_before_the_body(self):
        status, body = self.post(headers={})
        self.assertEqual(status, 401)
        self.assertIn(b"unauthorized", body)
        self.assertEqual(self.post(headers={"Authorization": "Bearer wrong"})[0], 401)
        self.assertEqual(os.listdir(self.svc.JOB_ROOT), [])

    def test_rejected_parameters_keep_their_codes(self):
        self.assertIn(b"unsupported_format", self.post(query="format=exe&ext=docx")[1])
        self.assertIn(b"invalid_extension", self.post(query="format=pdf&ext=docx%0A")[1])

    def test_failed_job_directory_returns_the_error_and_loses_no_slot(self):
        before = self.free_slots()
        with mock.patch.object(self.svc.tempfile, "mkdtemp", side_effect=OSError(28, "no space")):
            for _ in range(4):
                status, body = self.post()
                self.assertEqual(status, 503)
                self.assertIn(b"storage_unavailable", body)
        self.assertEqual(self.free_slots(), before)
        self.assertEqual(self.post(), (200, b"converted"))

    def test_unexpected_error_is_a_controlled_response_and_releases_the_slot(self):
        before = self.free_slots()
        with mock.patch.object(self.svc, "convert", side_effect=RuntimeError("boom")):
            status, body = self.post()
        self.assertEqual(status, 500)
        self.assertIn(b"internal_error", body)
        self.assertEqual(self.free_slots(), before)

    def test_header_only_peer_is_dropped_at_the_header_deadline(self):
        sock = self.raw()
        sock.sendall(b"POST /convert?format=pdf&ext=docx HTTP/1.1\r\n")
        started = time.monotonic()
        sock.settimeout(5)
        self.assertEqual(sock.recv(100), b"")
        self.assertLess(time.monotonic() - started, 2.0)

    def test_trickling_header_cannot_extend_the_deadline(self):
        sock = self.raw()
        sock.sendall(b"POST /convert?format=pdf&ext=docx HTTP/1.1\r\n")
        started = time.monotonic()
        closed = False
        try:
            for _ in range(60):
                sock.sendall(b"X-Slow: y\r\n")
                time.sleep(0.05)
                sock.settimeout(0.01)
                try:
                    if sock.recv(1) == b"":
                        closed = True
                        break
                except socket.timeout:
                    pass
        except OSError:
            closed = True
        self.assertTrue(closed)
        self.assertLess(time.monotonic() - started, 2.0)

    def test_slow_upload_stops_at_the_total_deadline_and_holds_no_slot(self):
        sock = self.raw()
        sock.sendall(b"POST /convert?format=pdf&ext=docx HTTP/1.1\r\nAuthorization: Bearer " + SECRET.encode()
                     + b"\r\nContent-Length: 1000\r\n\r\n")
        self.assertTrue(self.wait_for(lambda: os.listdir(self.svc.JOB_ROOT)))
        self.assertEqual(self.free_slots(), self.svc.MAX_JOBS)  # the upload does not take a conversion slot
        started = time.monotonic()
        try:
            for _ in range(100):
                sock.sendall(b"x")
                time.sleep(0.05)
        except OSError:
            pass
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertTrue(self.wait_for(lambda: os.listdir(self.svc.JOB_ROOT) == []))
        self.assertEqual(self.post(), (200, b"converted"))

    def test_slow_reader_is_dropped_at_the_total_deadline_and_cleaned_up(self):
        sock = self.raw()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        original = self.svc.convert

        def big_output(job_dir, source, target, limit_sec):
            output = os.path.join(job_dir, "big.pdf")
            with open(output, "wb") as dest:
                dest.write(b"x" * (32 * 1024 * 1024))
            return output

        with mock.patch.object(self.svc, "convert", big_output):
            sock.sendall(b"POST /convert?format=pdf&ext=docx HTTP/1.1\r\nAuthorization: Bearer " + SECRET.encode()
                         + b"\r\nContent-Length: 3\r\n\r\ndoc")
            time.sleep(2.2)  # never read while the deadline passes
        self.assertIs(self.svc.convert, original)
        self.assertTrue(self.wait_for(lambda: os.listdir(self.svc.JOB_ROOT) == []))
        self.assertEqual(self.free_slots(), self.svc.MAX_JOBS)
        self.assertEqual(self.post(), (200, b"converted"))

    def test_overload_is_refused_at_once_and_the_service_recovers(self):
        held = [self.raw() for _ in range(6)]  # 4 workers + 2 pending
        time.sleep(0.1)
        conn = self.raw()
        conn.sendall(b"GET /healthz HTTP/1.1\r\nHost: x\r\n\r\n")
        conn.settimeout(3)
        self.assertIn(b"503", conn.recv(200))
        for sock in held:
            sock.close()
        self.assertTrue(self.wait_for(lambda: self._healthz() == 200, seconds=3))
        self.assertEqual(self.post(), (200, b"converted"))

    def _healthz(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            conn.request("GET", "/healthz")
            return conn.getresponse().status
        except OSError:
            return 0
        finally:
            conn.close()

    def test_conversion_over_the_time_limit_returns_504_and_clears_the_job(self):
        with mock.patch.dict(os.environ, {"STUB_SLEEP": "0"}):
            original = self.svc.convert

            def slow(job_dir, source, target, limit_sec):
                return original(job_dir, source, target, 0.05)

            stub = Path(self.svc.SOFFICE)
            stub.write_text(STUB.replace('${STUB_SLEEP:-0}', '5'))
            with mock.patch.object(self.svc, "convert", slow):
                status, body = self.post()
        self.assertEqual(status, 504)
        self.assertIn(b"conversion_timeout", body)
        self.assertTrue(self.wait_for(lambda: os.listdir(self.svc.JOB_ROOT) == []))
        self.assertEqual(self.free_slots(), self.svc.MAX_JOBS)


if __name__ == "__main__":
    unittest.main()
