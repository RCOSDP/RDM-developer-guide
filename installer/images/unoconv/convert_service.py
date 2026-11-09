"""HTTP front for `soffice --convert-to`; the only entry point of the converter container.

POST /convert?format=<target>&ext=<source extension>  body: the document  -> the converted file
GET  /healthz                                                             -> 200

The documents are untrusted. Each request gets its own directory and LibreOffice profile, which are
removed afterwards, so one document cannot see another. The container has no network egress, no
shared volume and no capabilities. Nothing here interprets the document; the size, the time and the
number of concurrent conversions are bounded and the target format is an allow-listed token.
"""
import http.server
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import urllib.parse

MAX_BYTES = int(os.environ.get("CONVERT_MAX_BYTES", str(128 * 1024 * 1024)))
TIMEOUT_SEC = int(os.environ.get("CONVERT_TIMEOUT_SEC", "45"))
MAX_JOBS = int(os.environ.get("CONVERT_MAX_JOBS", "2"))
QUEUE_WAIT_SEC = int(os.environ.get("CONVERT_QUEUE_WAIT_SEC", "10"))
PORT = int(os.environ.get("CONVERT_PORT", "2002"))
SOFFICE = os.environ.get("CONVERT_SOFFICE", "/usr/bin/soffice")
PROFILE_SEED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registrymodifications.xcu")
# Formats MFR asks for (pdf for previews; the others for the export endpoint). A filter option such
# as "pdf:writer_pdf_Export:{...}" cannot pass, because only plain tokens are accepted.
FORMATS = frozenset("pdf html txt csv doc docx odt rtf xls xlsx ods ppt pptx odp png".split())
EXT_RE = re.compile(r"^[a-z0-9]{1,10}$")

slots = threading.BoundedSemaphore(MAX_JOBS)


def remove_job_dir(path):
    # A killed soffice.bin can still write for a moment after the kill, so repeat until it is gone.
    for _ in range(40):
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return
        time.sleep(0.25)


class Rejected(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def convert(job_dir, source, target):
    profile = os.path.join(job_dir, "profile")
    os.makedirs(os.path.join(profile, "user"))
    shutil.copy(PROFILE_SEED, os.path.join(profile, "user", "registrymodifications.xcu"))
    outdir = os.path.join(job_dir, "out")
    os.mkdir(outdir)
    argv = [SOFFICE, "--headless", "--norestore", "--nolockcheck", "--nodefault", "--nologo", "--nofirststartwizard",
            "-env:UserInstallation=file://" + profile, "--convert-to", target, "--outdir", outdir, source]
    env = {"HOME": job_dir, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TMPDIR": job_dir}
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=env, cwd=job_dir, start_new_session=True)
    try:
        proc.wait(timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        raise Rejected(504, "conversion_timeout", "conversion exceeded {}s".format(TIMEOUT_SEC))
    finally:
        # oosplash leaves soffice.bin behind in the same session; always clear the whole group.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
    # soffice exits 0 when a document cannot be loaded, so only the output file proves success.
    output = os.path.join(outdir, os.path.splitext(os.path.basename(source))[0] + "." + target)
    if not os.path.isfile(output) or os.path.getsize(output) == 0:
        raise Rejected(422, "conversion_failed", "the document could not be converted")
    return output


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "grdm-convert"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = TIMEOUT_SEC + QUEUE_WAIT_SEC

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args), flush=True)

    def _json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        if self.path == "/healthz":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"code": "not_found"})

    def do_POST(self):
        try:
            self._convert()
        except Rejected as exc:
            self._json(exc.status, {"code": exc.code, "message": exc.message})

    def _read_body(self, path):
        length = self.headers.get("Content-Length")
        if length is None or not length.isdigit():
            raise Rejected(411, "length_required", "Content-Length is required")
        remaining = int(length)
        if remaining == 0:
            raise Rejected(400, "empty_document", "the request has no document")
        if remaining > MAX_BYTES:
            raise Rejected(413, "too_large", "the document is larger than {} bytes".format(MAX_BYTES))
        with open(path, "wb") as dest:
            while remaining:
                chunk = self.rfile.read(min(remaining, 1024 * 1024))
                if not chunk:
                    raise Rejected(400, "truncated", "the request body ended early")
                dest.write(chunk)
                remaining -= len(chunk)

    def _convert(self):
        url = urllib.parse.urlsplit(self.path)
        query = urllib.parse.parse_qs(url.query)
        target = query.get("format", [""])[0].lower()
        ext = query.get("ext", [""])[0].lower()
        if url.path != "/convert":
            raise Rejected(404, "not_found", "unknown path")
        if target not in FORMATS:
            raise Rejected(400, "unsupported_format", "unsupported target format")
        if not EXT_RE.match(ext):
            raise Rejected(400, "invalid_extension", "invalid source extension")
        if not slots.acquire(timeout=QUEUE_WAIT_SEC):
            raise Rejected(503, "busy", "too many conversions in progress")
        job_dir = tempfile.mkdtemp(prefix="job-", dir="/tmp")
        try:
            source = os.path.join(job_dir, "input." + ext)
            self._read_body(source)
            output = convert(job_dir, source, target)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(os.path.getsize(output)))
            self.send_header("Connection", "close")
            self.end_headers()
            with open(output, "rb") as src:
                shutil.copyfileobj(src, self.wfile, 1024 * 1024)
            self.close_connection = True
        finally:
            remove_job_dir(job_dir)
            slots.release()


def main():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.daemon_threads = True
    print("convert service listening on {}".format(PORT), flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
