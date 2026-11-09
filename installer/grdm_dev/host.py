"""Host detection: OS, CPU, memory, disk, Python, Docker (SPEC-02 §3 `doctor`, §8 supported hosts).

Everything that touches the machine goes through two seams so unit tests never need Docker:

* `Probe` — plain facts read with `platform`, `os`, `shutil` (OS name, kernel, /etc/os-release,
  /proc/version, memory, free disk). Tests build a `Probe` by hand.
* `runner(argv) -> (returncode, stdout)` — runs `docker ...`. Tests pass a fake.

`detect()` turns those facts into a `HostInfo`; `as_report()` flattens it for TOON/JSON.

A hand-built `Probe` leaves `tools` and `repo_root` empty: those preflights are then "not probed" and
skipped, so a test exercises only the checks it set up. `Probe.from_system()` always fills them.
"""
from __future__ import annotations

import math
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Optional

Runner = Callable[[list[str]], tuple[int, str]]

GIB = 1024 ** 3
MIN_MEMORY_BYTES = 8 * GIB
RECOMMENDED_MEMORY_BYTES = 16 * GIB
MIN_DISK_FREE_BYTES = 40 * GIB
MIN_PYTHON = (3, 11)
MIN_DOCKER_MAJOR = 27
MIN_COMPOSE_MAJOR = 2
SUBPROCESS_TIMEOUT = 15

# Official hosts (SPEC-02 §8). Anything else is best-effort: a warning, not a problem.
OFFICIAL = {("macos", "arm64"), ("ubuntu", "amd64"), ("ubuntu", "arm64"), ("wsl2", "amd64")}

# Tools other than Docker that `install` needs (SPEC-02 §2.2). A missing `git` stops the build (exit 13 from
# doctor); a missing scanner stops `scan` with exit 51 at the very end, so doctor reports it before the build.
REQUIRED_TOOLS = ("git",)
SCANNER_TOOLS = ("trivy", "gitleaks", "semgrep")
WITHOUT_SCAN_ENV = "GRDM_WITHOUT_SCAN"  # install.sh's opt-out of the [scan] extra: semgrep is then absent on purpose
BINFMT_AMD64_FILES = ("/proc/sys/fs/binfmt_misc/qemu-x86_64", "/proc/sys/fs/binfmt_misc/rosetta")
ENABLE_AMD64_EMULATION = "docker run --privileged --rm tonistiigi/binfmt --install amd64"


def default_runner(argv: list[str]) -> tuple[int, str]:
    """Run a command, merging stderr into stdout; a missing or hanging tool is a non-zero result."""
    try:
        cp = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=SUBPROCESS_TIMEOUT
        )
        return cp.returncode, cp.stdout
    except FileNotFoundError:
        return 127, f"{argv[0]}: command not found"
    except subprocess.TimeoutExpired:
        return 124, f"{' '.join(argv)}: timed out after {SUBPROCESS_TIMEOUT}s"
    except OSError as exc:
        return 126, f"{argv[0]}: {exc}"


@dataclass
class Probe:
    """Raw facts about the machine. `Probe.from_system()` reads them; tests set them directly."""

    system: str = ""            # platform.system(): Darwin | Linux | Windows | ...
    release: str = ""           # platform.release(): kernel version
    machine: str = ""           # platform.machine(): arm64 | x86_64 | aarch64 | ...
    mac_ver: str = ""           # platform.mac_ver()[0] on macOS, else ""
    os_release: str = ""        # contents of /etc/os-release (Linux), else ""
    proc_version: str = ""      # contents of /proc/version (Linux), else ""
    env: dict[str, str] = field(default_factory=dict)
    python_version: tuple[int, int, int] = (0, 0, 0)
    memory_bytes: Optional[int] = None
    disk_free_bytes: Optional[int] = None
    docker_path: Optional[str] = None   # shutil.which("docker")
    tools: Optional[dict[str, bool]] = None  # name -> found, for REQUIRED_TOOLS + SCANNER_TOOLS; None = not probed
    repo_root: str = ""                 # resolved repository root; "" = not probed
    binfmt_amd64: Optional[bool] = None  # Linux: an enabled amd64 handler in binfmt_misc; None = unknown

    @classmethod
    def from_system(cls, root: Path | None = None, runner: Runner | None = None) -> "Probe":
        root = root or Path.cwd()
        system = platform.system()
        p = cls(
            system=system,
            release=platform.release(),
            machine=platform.machine(),
            mac_ver=platform.mac_ver()[0] if system == "Darwin" else "",
            os_release=_read_text("/etc/os-release") or _read_text("/usr/lib/os-release") if system == "Linux" else "",
            proc_version=_read_text("/proc/version") if system == "Linux" else "",
            env=dict(os.environ),
            python_version=tuple(sys.version_info[:3]),  # type: ignore[arg-type]
            memory_bytes=_memory_bytes(runner or default_runner, system),
            disk_free_bytes=_disk_free_bytes(root),
            docker_path=shutil.which("docker"),
            tools=_probe_tools(),
            repo_root=str(root.resolve()),
            binfmt_amd64=_binfmt_amd64() if system == "Linux" else None,
        )
        return p


@dataclass
class HostInfo:
    os_name: str = "unsupported"        # macos | ubuntu | wsl2 | linux-other | unsupported
    os_version: str = ""
    arch: str = "other"                 # arm64 | amd64 | other
    memory_bytes: Optional[int] = None
    disk_free_bytes: Optional[int] = None
    python_version: str = ""
    docker_version: str = ""
    compose_version: str = ""
    buildx_present: bool = False
    docker_running: bool = False
    supported: bool = False
    docker_ok: bool = False
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    platform_string: str = ""           # linux/arm64 | linux/amd64 (empty when arch is other)
    prerequisite_problems: list[str] = field(default_factory=list)  # exit 13: git, repository access, emulation, checkout path
    scanner_problems: list[str] = field(default_factory=list)       # exit 51: `scan` could not run


# --- raw readers -------------------------------------------------------------------------------

def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _memory_bytes(runner: Runner, system: str) -> Optional[int]:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and page > 0:
            return int(pages) * int(page)
    except (ValueError, OSError, AttributeError):
        pass
    if system == "Darwin":
        rc, out = runner(["sysctl", "-n", "hw.memsize"])
        if rc == 0 and out.strip().isdigit():
            return int(out.strip())
    return None


def _probe_tools() -> dict[str, bool]:
    from .scan import default_which  # also finds a tool next to the interpreter (semgrep in .venv/bin)

    return {name: default_which(name) for name in (*REQUIRED_TOOLS, *SCANNER_TOOLS)}


def _binfmt_amd64() -> Optional[bool]:
    """True when an amd64 handler is registered and enabled, False when none is, None when unreadable."""
    if not Path("/proc/sys/fs/binfmt_misc").is_dir():
        return None
    return any(_read_text(path).splitlines()[:1] == ["enabled"] for path in BINFMT_AMD64_FILES)


def _disk_free_bytes(root: Path) -> Optional[int]:
    try:
        return shutil.disk_usage(str(root)).free
    except OSError:
        return None


# --- classification ----------------------------------------------------------------------------

def parse_os_release(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def classify_arch(machine: str) -> str:
    m = (machine or "").lower()
    if m in ("arm64", "aarch64"):
        return "arm64"
    if m in ("x86_64", "amd64"):
        return "amd64"
    return "other"


def classify_os(probe: Probe) -> tuple[str, str]:
    """Return (os_name, os_version)."""
    system = (probe.system or "").strip()
    if system == "Darwin":
        return "macos", probe.mac_ver or probe.release
    if system == "Linux":
        rel = parse_os_release(probe.os_release)
        version = rel.get("VERSION_ID", "") or rel.get("PRETTY_NAME", "")
        is_wsl = "microsoft" in (probe.proc_version or "").lower() or "microsoft" in (probe.release or "").lower() \
            or bool(probe.env.get("WSL_DISTRO_NAME"))
        if is_wsl:
            return "wsl2", version
        if rel.get("ID", "").lower() == "ubuntu":
            return "ubuntu", version
        return "linux-other", version
    return "unsupported", f"{system} {probe.release}".strip()


def parse_version(text: str) -> tuple[int, ...]:
    """First dotted number in `text` as a tuple of ints; () when none."""
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text or "")
    if not m:
        return ()
    return tuple(int(g) for g in m.groups() if g is not None)


def _fmt_gib(n: Optional[int]) -> str:
    return "unknown" if n is None else f"{n / GIB:.1f} GiB"


# --- docker ------------------------------------------------------------------------------------

def check_docker(runner: Runner, info: HostInfo) -> None:
    """Fill docker_* fields and append problems; docker_ok is True only when every check passes."""
    rc, out = runner(["docker", "version", "--format", "{{.Server.Version}}"])
    out = (out or "").strip()
    if rc == 127 or (rc != 0 and "command not found" in out):
        info.problems.append("docker command not found / docker コマンドが見つかりません")
        return
    if rc != 0 or not parse_version(out):
        detail = out.splitlines()[0] if out else f"exit {rc}"
        info.problems.append(f"docker daemon not running or unreachable ({detail}) / Docker デーモンが動いていないか到達できません")
        return
    info.docker_running = True
    info.docker_version = out.splitlines()[0]
    ver = parse_version(info.docker_version)
    if ver and ver[0] < MIN_DOCKER_MAJOR:
        info.problems.append(
            f"docker {info.docker_version} is older than {MIN_DOCKER_MAJOR} / Docker {info.docker_version} は {MIN_DOCKER_MAJOR} より古いです"
        )

    rc, out = runner(["docker", "compose", "version"])
    cver = parse_version(out or "")
    if rc != 0 or not cver:
        info.problems.append("docker compose plugin missing / Docker Compose プラグインがありません")
    else:
        info.compose_version = ".".join(str(x) for x in cver)
        if cver[0] < MIN_COMPOSE_MAJOR:
            info.problems.append(
                f"docker compose v{info.compose_version} is older than v{MIN_COMPOSE_MAJOR} / Docker Compose v{info.compose_version} は v{MIN_COMPOSE_MAJOR} より古いです"
            )

    rc, out = runner(["docker", "buildx", "version"])
    if rc == 0 and parse_version(out or ""):
        info.buildx_present = True
    else:
        info.problems.append("docker buildx plugin missing / Docker buildx プラグインがありません")


# --- preflight ---------------------------------------------------------------------------------

def memory_hint(os_name: str, need_gib: float) -> str:
    """How to give the Docker engine more memory here. On WSL2 the limit is `.wslconfig`: Docker Desktop's
    Resources page has no memory control under the WSL 2 backend."""
    need = int(math.ceil(need_gib))
    if os_name == "wsl2":
        return (f"set `memory={need}GB` under `[wsl2]` in %UserProfile%\\.wslconfig on Windows, then run `wsl --shutdown` / "
                f"Windows の %UserProfile%\\.wslconfig の `[wsl2]` に `memory={need}GB` を書き、`wsl --shutdown` を実行してください")
    if os_name == "macos":
        return (f"give the Docker VM at least {need} GiB (Docker Desktop: Settings > Resources; Colima: `colima start --memory {need}`) / "
                f"Docker VM に {need} GiB 以上を割り当ててください（Docker Desktop: Settings > Resources、Colima: `colima start --memory {need}`）")
    return f"this host needs at least {need} GiB of memory / このホストには {need} GiB 以上のメモリが必要です"


def _tool_hint(os_name: str, tool: str) -> str:
    if tool == "semgrep":
        return "./installer/install.sh puts it in .venv"
    if os_name == "macos":
        return f"brew install {tool}"
    return {"git": "sudo apt install -y git",
            "trivy": "https://trivy.dev/latest/getting-started/installation/",
            "gitleaks": "https://github.com/gitleaks/gitleaks/releases"}[tool]


def check_tools(probe: Probe, info: HostInfo) -> None:
    """git -> prerequisite_problems; scanners -> scanner_problems (SPEC-02 §2.2). Nothing when not probed."""
    if probe.tools is None:
        return
    for tool in REQUIRED_TOOLS:
        if not probe.tools.get(tool):
            hint = _tool_hint(info.os_name, tool)
            info.prerequisite_problems.append(f"{tool} not found; install it: {hint} / {tool} が見つかりません。導入してください: {hint}")
    for tool in SCANNER_TOOLS:
        if probe.tools.get(tool):
            continue
        if tool == "semgrep" and probe.env.get(WITHOUT_SCAN_ENV) == "1":
            info.warnings.append(f"semgrep left out by {WITHOUT_SCAN_ENV}=1; `scan` will exit 51 / {WITHOUT_SCAN_ENV}=1 により semgrep がありません。`scan` は終了 51 になります")
            continue
        hint = _tool_hint(info.os_name, tool)
        info.scanner_problems.append(
            f"{tool} not found, so `scan` would exit 51 after the whole build; install it: {hint} / "
            f"{tool} が見つかりません。ビルド全体の後で `scan` が終了 51 になります。導入してください: {hint}"
        )


def check_repo_path(probe: Probe, info: HostInfo) -> None:
    """Reject checkouts Docker cannot use properly (exit 13). Nothing when the path was not probed."""
    root = probe.repo_root
    if not root:
        return
    if info.os_name == "wsl2" and (root == "/mnt" or root.startswith("/mnt/")):
        # A Windows drive (drvfs) has no POSIX modes, so runtime/.env cannot be 0600 (SPEC-03 §3.1, BASE-ENV-MODE).
        info.prerequisite_problems.append(
            f"repository is on a Windows drive ({root}), where file modes such as 0600 on runtime/.env do not work; clone it inside WSL, for example under ~/ / "
            f"リポジトリが Windows のドライブ上にあります（{root}）。runtime/.env の 0600 などのファイルモードが効きません。WSL の中（例: ~/ の下）へ clone してください"
        )
    if info.os_name == "macos":
        home = probe.env.get("HOME", "").rstrip("/")
        if root.startswith("/Volumes/"):
            info.warnings.append(f"{root} must be shared with the Docker VM, or bind mounts will be empty / {root} を Docker VM と共有していないと bind mount が空になります")
        elif not home or not (root == home or root.startswith(home + "/")):
            # Measured on Colima (real engine, 2026-11-10): a bind mount from /private/tmp is silently empty, one under $HOME is not.
            info.prerequisite_problems.append(
                f"repository at {root} is outside your home directory, which the Docker VM may not share (bind mounts would be silently empty); clone it under {home or '~'}/ / "
                f"リポジトリ {root} はホームディレクトリの外にあり、Docker VM と共有されていない可能性があります（bind mount が黙って空になります）。{home or '~'}/ の下へ clone してください"
            )


def check_amd64_emulation(probe: Probe, info: HostInfo, services: list[str]) -> None:
    """Linux arm64 only: `services` run as linux/amd64 and need a binfmt handler (QEMU). Docker Desktop brings its own."""
    if info.arch != "arm64" or info.os_name not in ("ubuntu", "linux-other") or not services or probe.tools is None:
        return
    names = ", ".join(services)
    if probe.binfmt_amd64 is None:
        info.warnings.append(
            f"cannot read binfmt_misc; {names} need amd64 emulation. If they stop with `exec format error`, run: {ENABLE_AMD64_EMULATION} / "
            f"binfmt_misc を読めません。{names} には amd64 エミュレーションが要ります。`exec format error` で止まったら実行してください: {ENABLE_AMD64_EMULATION}"
        )
    elif not probe.binfmt_amd64:
        info.prerequisite_problems.append(
            f"amd64 emulation is not enabled but {names} need it; run this (and again after a reboot): {ENABLE_AMD64_EMULATION} / "
            f"amd64 エミュレーションが無効ですが {names} に必要です。次を実行してください（再起動のたびに必要）: {ENABLE_AMD64_EMULATION}"
        )


# --- entry points ------------------------------------------------------------------------------

def detect(runner: Runner | None = None, probe: Probe | None = None, root: Path | None = None) -> HostInfo:
    """Detect the host. `runner` and `probe` are injectable so tests never touch Docker or the OS."""
    runner = runner or default_runner
    probe = probe or Probe.from_system(root=root, runner=runner)
    info = HostInfo()

    info.os_name, info.os_version = classify_os(probe)
    info.arch = classify_arch(probe.machine)
    info.memory_bytes = probe.memory_bytes
    info.disk_free_bytes = probe.disk_free_bytes
    info.python_version = ".".join(str(x) for x in probe.python_version) if probe.python_version else ""
    if info.arch in ("arm64", "amd64"):
        info.platform_string = f"linux/{info.arch}"

    # Host problems (-> exit 10)
    if info.os_name == "unsupported":
        info.problems.append(
            f"operating system not supported: {info.os_version} / 対応していない OS です: {info.os_version}"
        )
    if info.arch == "other":
        info.problems.append(
            f"CPU architecture not supported: {probe.machine} / 対応していない CPU です: {probe.machine}"
        )
    if probe.python_version and tuple(probe.python_version[:2]) < MIN_PYTHON:
        info.problems.append(
            f"Python {info.python_version} is older than 3.11 / Python {info.python_version} は 3.11 より古いです"
        )
    if info.memory_bytes is not None and info.memory_bytes < MIN_MEMORY_BYTES:
        info.problems.append(
            f"memory {_fmt_gib(info.memory_bytes)} is below the 8 GiB minimum / メモリ {_fmt_gib(info.memory_bytes)} は最低 8 GiB 未満です"
            + (f"; {memory_hint('wsl2', 8)}" if info.os_name == "wsl2" else "")
        )

    # Host warnings (best-effort hosts, SPEC-02 §8)
    if info.os_name in ("macos", "ubuntu", "wsl2", "linux-other") and info.arch != "other" \
            and (info.os_name, info.arch) not in OFFICIAL:
        info.warnings.append(
            f"{info.os_name}/{info.arch} is best-effort, not an official host / {info.os_name}/{info.arch} は公式対応外（可能な限りの対応）です"
        )
    if info.os_name == "macos" and parse_version(info.os_version)[:1] and parse_version(info.os_version)[0] < 14:
        info.warnings.append(f"macOS {info.os_version} is older than 14 / macOS {info.os_version} は 14 より古いです")
    if info.os_name in ("ubuntu", "wsl2") and info.os_version and parse_version(info.os_version)[:1] \
            and parse_version(info.os_version)[0] < 24:
        info.warnings.append(f"Ubuntu {info.os_version} is older than 24.04 / Ubuntu {info.os_version} は 24.04 より古いです")
    if info.memory_bytes is None:
        info.warnings.append("memory size could not be read / メモリ量を読めませんでした")
    elif info.memory_bytes < RECOMMENDED_MEMORY_BYTES:
        info.warnings.append(
            f"memory {_fmt_gib(info.memory_bytes)} is below the recommended 16 GiB / メモリ {_fmt_gib(info.memory_bytes)} は推奨 16 GiB 未満です"
        )
    if info.disk_free_bytes is not None and info.disk_free_bytes < MIN_DISK_FREE_BYTES:
        info.warnings.append(
            f"free disk {_fmt_gib(info.disk_free_bytes)} is below the recommended 40 GiB / 空き容量 {_fmt_gib(info.disk_free_bytes)} は推奨 40 GiB 未満です"
        )

    info.supported = not info.problems

    # Docker (-> exit 11); counted separately so doctor can tell 10 from 11.
    before = len(info.problems)
    check_docker(runner, info)
    info.docker_ok = len(info.problems) == before

    check_tools(probe, info)
    check_repo_path(probe, info)
    return info


def as_report(info: HostInfo) -> dict:
    """Flat, TOON-friendly dict (SPEC-06 §4): scalars plus two string lists."""
    d = asdict(info)
    d["memory_gib"] = None if info.memory_bytes is None else round(info.memory_bytes / GIB, 1)
    d["disk_free_gib"] = None if info.disk_free_bytes is None else round(info.disk_free_bytes / GIB, 1)
    d["official"] = (info.os_name, info.arch) in OFFICIAL
    return d
