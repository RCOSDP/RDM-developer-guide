"""HTTP front for `soffice --convert-to`; the only entry point of the converter container.

POST /convert?format=<target>&ext=<source extension>  body: the document  -> the converted file
     Authorization: Bearer <CONVERT_SECRET>, checked before the body is read
GET  /healthz                                                             -> 200

The documents are untrusted. Each request gets its own directory and LibreOffice profile, removed
afterwards; the container has no volume shared with MFR and no capabilities. This is resource
separation, not a sandbox between jobs: concurrent conversions run under one uid, so a parser
compromised by one document could reach another document being converted at that moment.

Limits. A fixed set of worker threads serves connections from a bounded queue and anything beyond it
is answered 503 at once, so no peer can grow the thread count. Each connection has monotonic
deadlines, enforced by shutting the socket down so that a peer trickling bytes cannot extend them:
HEADER_DEADLINE_SEC up to authentication, then REQUEST_DEADLINE_SEC for upload, conversion and
response together. A conversion slot is held only while soffice runs, never during a transfer.
"""
import glob
import hmac
import http.server
import json
import os
import queue
import re
import shutil
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse

MAX_BYTES = int(os.environ.get("CONVERT_MAX_BYTES", str(128 * 1024 * 1024)))
MAX_OUTPUT_BYTES = int(os.environ.get("CONVERT_MAX_OUTPUT_BYTES", str(256 * 1024 * 1024)))
TIMEOUT_SEC = float(os.environ.get("CONVERT_TIMEOUT_SEC", "45"))
MAX_JOBS = int(os.environ.get("CONVERT_MAX_JOBS", "2"))
QUEUE_WAIT_SEC = float(os.environ.get("CONVERT_QUEUE_WAIT_SEC", "10"))
MAX_CONNECTIONS = int(os.environ.get("CONVERT_MAX_CONNECTIONS", "8"))
MAX_PENDING = int(os.environ.get("CONVERT_MAX_PENDING", "8"))
HEADER_DEADLINE_SEC = float(os.environ.get("CONVERT_HEADER_DEADLINE_SEC", "5"))
# Below MFR's 60 s deadline for the whole exchange.
REQUEST_DEADLINE_SEC = float(os.environ.get("CONVERT_REQUEST_DEADLINE_SEC", "58"))
PORT = int(os.environ.get("CONVERT_PORT", "2002"))
SECRET = os.environ.get("CONVERT_SECRET", "")
SOFFICE = os.environ.get("CONVERT_SOFFICE", "/usr/bin/soffice")
PRLIMIT = os.environ.get("CONVERT_PRLIMIT", "/usr/bin/prlimit")
JOB_ROOT = os.environ.get("CONVERT_JOB_ROOT", "/tmp")
PROFILE_SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registrymodifications.xcu")
# Formats MFR asks for (pdf for previews; the others for the export endpoint). A filter option such
# as "pdf:writer_pdf_Export:{...}" cannot pass, because only plain tokens are accepted.
FORMATS = frozenset("pdf html txt csv doc docx odt rtf xls xlsx ods ppt pptx odp png".split())
EXT_RE = re.compile(r"[a-z0-9]{1,10}")
BUSY_RESPONSE = (b"HTTP/1.1 503 Service Unavailable\r\nContent-Type: application/json\r\nContent-Length: 16\r\n"
                 b"Connection: close\r\n\r\n" b'{"code": "busy"}')

slots = threading.BoundedSemaphore(MAX_JOBS)


class Rejected(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def remove_job_dir(path):
    # A killed soffice.bin can still write for a moment after the kill, so repeat until it is gone.
    for _ in range(40):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return
        time.sleep(0.25)
    print("could not remove " + path, flush=True)


def sweep_stale_pipes():
    # soffice killed at a timeout leaves its single-instance socket behind, which uses an inode. A
    # socket nothing listens on refuses the connection; a running conversion's socket does not.
    for path in glob.glob(os.path.join(JOB_ROOT, "OSL_PIPE_*")):
        probe = socket.socket(socket.AF_UNIX)
        probe.settimeout(0.2)
        try:
            probe.connect(path)
        except ConnectionRefusedError:
            try:
                os.unlink(path)
            except OSError:
                pass
        except OSError:
            pass
        finally:
            probe.close()


def convert(job_dir, source, target, limit_sec):
    profile = os.path.join(job_dir, "profile")
    os.makedirs(os.path.join(profile, "user"))
    shutil.copy(PROFILE_SEED, os.path.join(profile, "user", "registrymodifications.xcu"))
    outdir = os.path.join(job_dir, "out")
    os.mkdir(outdir)
    argv = [SOFFICE, "--headless", "--norestore", "--nolockcheck", "--nodefault", "--nologo", "--nofirststartwizard",
            "-env:UserInstallation=file://" + profile, "--convert-to", target, "--outdir", outdir, source]
    if PRLIMIT:
        argv = [PRLIMIT, "--fsize={}".format(MAX_OUTPUT_BYTES)] + argv
    env = {"HOME": job_dir, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TMPDIR": job_dir}
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=env, cwd=job_dir, start_new_session=True)
    timed_out = False
    try:
        proc.wait(timeout=limit_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        # oosplash leaves soffice.bin behind in the same session; always clear the whole group.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    if timed_out:
        time.sleep(0.2)
        sweep_stale_pipes()
        raise Rejected(504, "conversion_timeout", "conversion exceeded the time limit")
    # soffice exits 0 when a document cannot be loaded, so only the output file proves success.
    output = os.path.join(outdir, os.path.splitext(os.path.basename(source))[0] + "." + target)
    if not os.path.isfile(output) or os.path.getsize(output) == 0:
        raise Rejected(422, "conversion_failed", "the document could not be converted")
    if os.path.getsize(output) >= MAX_OUTPUT_BYTES:
        raise Rejected(413, "output_too_large", "the converted file is too large")
    return output


class Deadline:
    """Shuts the socket when time is up, which wakes any blocked read or write on it."""

    def __init__(self, sock):
        self.sock = sock
        self.timer = None
        self.expires = 0.0

    def set(self, seconds):
        self.cancel()
        self.expires = time.monotonic() + seconds
        self.timer = threading.Timer(seconds, self._fire)
        self.timer.daemon = True
        self.timer.start()

    def remaining(self):
        return max(0.0, self.expires - time.monotonic())

    def cancel(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def _fire(self):
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "grdm-convert"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = REQUEST_DEADLINE_SEC

    def setup(self):
        super().setup()
        self.deadline = Deadline(self.connection)
        self.deadline.set(HEADER_DEADLINE_SEC)

    def finish(self):
        self.deadline.cancel()
        try:
            super().finish()
        except OSError:
            pass

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.close_connection = True
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except OSError:
            pass  # the peer has gone or the deadline has closed the connection

    def do_GET(self):
        if self.path == "/healthz":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"code": "not_found"})

    def do_POST(self):
        self.close_connection = True
        try:
            self._authorize()
            self.deadline.set(REQUEST_DEADLINE_SEC)
            self._convert()
        except Rejected as exc:
            self._json(exc.status, {"code": exc.code, "message": exc.message})
        except OSError:
            pass  # the peer has gone or the deadline has closed the connection
        except Exception as exc:
            print("internal error: " + type(exc).__name__, flush=True)
            self._json(500, {"code": "internal_error"})

    def _authorize(self):
        supplied = self.headers.get("Authorization", "").encode("latin-1", "replace")
        if not hmac.compare_digest(supplied, ("Bearer " + SECRET).encode("latin-1", "replace")):
            raise Rejected(401, "unauthorized", "a valid credential is required")

    def _read_body(self, path):
        length = self.headers.get("Content-Length")
        if length is None or not length.isdecimal():
            raise Rejected(411, "length_required", "Content-Length is required")
        remaining = int(length)
        if remaining == 0:
            raise Rejected(400, "empty_document", "the request has no document")
        if remaining > MAX_BYTES:
            raise Rejected(413, "too_large", "the document is larger than the limit")
        try:
            dest = open(path, "wb")
        except OSError:
            raise Rejected(503, "storage_unavailable", "no room for the document")
        with dest:
            while remaining:
                chunk = self.rfile.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise Rejected(400, "truncated", "the request body ended early")
                try:
                    dest.write(chunk)
                except OSError:
                    raise Rejected(503, "storage_unavailable", "no room for the document")
                remaining -= len(chunk)

    def _convert_in_slot(self, job_dir, source, target):
        wait = min(QUEUE_WAIT_SEC, self.deadline.remaining())
        if wait <= 0 or not slots.acquire(timeout=wait):
            raise Rejected(503, "busy", "too many conversions in progress")
        try:
            limit = min(TIMEOUT_SEC, self.deadline.remaining())
            if limit <= 0:
                raise Rejected(504, "conversion_timeout", "no time left for the conversion")
            try:
                return convert(job_dir, source, target, limit)
            except OSError:
                raise Rejected(503, "storage_unavailable", "no room for the conversion")
        finally:
            slots.release()

    def _convert(self):
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        target = query.get("format", [""])[0].lower()
        ext = query.get("ext", [""])[0].lower()
        if url.path != "/convert":
            raise Rejected(404, "not_found", "unknown path")
        if target not in FORMATS:
            raise Rejected(400, "unsupported_format", "unsupported target format")
        if not EXT_RE.fullmatch(ext):
            raise Rejected(400, "invalid_extension", "invalid source extension")
        job_dir = None
        try:
            try:
                job_dir = tempfile.mkdtemp(prefix="job-", dir=JOB_ROOT)
            except OSError:
                raise Rejected(503, "storage_unavailable", "no room for the document")
            source = os.path.join(job_dir, "input." + ext)
            self._read_body(source)
            output = self._convert_in_slot(job_dir, source, target)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(os.path.getsize(output)))
            self.send_header("Connection", "close")
            self.end_headers()
            with open(output, "rb") as src:
                shutil.copyfileobj(src, self.wfile, 1024 * 1024)
        finally:
            if job_dir is not None:
                remove_job_dir(job_dir)


class BoundedServer(socketserver.TCPServer):
    allow_reuse_address = True
    request_queue_size = 32

    def __init__(self, address, handler=Handler, workers=None, pending=None):
        super().__init__(address, handler)
        self.pending = queue.Queue(maxsize=MAX_PENDING if pending is None else pending)
        for _ in range(MAX_CONNECTIONS if workers is None else workers):
            threading.Thread(target=self._work, daemon=True).start()

    def process_request(self, request, client_address):
        # Runs on the accepting thread, so it must never wait on the peer.
        try:
            self.pending.put_nowait((request, client_address, time.monotonic()))
        except queue.Full:
            self._refuse(request)
            self.shutdown_request(request)

    @staticmethod
    def _refuse(request):
        try:
            request.settimeout(0.2)
            request.sendall(BUSY_RESPONSE)
        except OSError:
            pass

    def _work(self):
        while True:
            request, client_address, queued_at = self.pending.get()
            try:
                if time.monotonic() - queued_at > QUEUE_WAIT_SEC:
                    self._refuse(request)
                else:
                    self.finish_request(request, client_address)
            except Exception as exc:
                print("connection error: " + type(exc).__name__, flush=True)
            finally:
                self.shutdown_request(request)


def main():
    if not SECRET:
        sys.exit("CONVERT_SECRET is required")
    server = BoundedServer(("0.0.0.0", PORT))
    print("convert service listening on {}".format(PORT), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
