#!/usr/bin/env bash
# Prerequisites for Ubuntu 24.04 (amd64, arm64) and for Ubuntu 24.04 inside WSL2, then installer/install.sh
# (ADR-08, SPEC-02 §2.3). It only prepares the host: every installation decision stays in install.sh and grdm-dev.
#
# What it may change, after showing it and asking: apt packages (git, python3, python3-venv, curl, gnupg,
# ca-certificates), Docker Engine with the Compose and buildx plugins from Docker's signed apt repository, the
# docker group, qemu-user-static for amd64 emulation on arm64, and trivy and gitleaks in ~/.local/bin.
# Inside WSL2 Docker comes from Docker Desktop, so the Docker Engine steps are skipped.
#
# Trust: the apt signing key is accepted only when its fingerprint equals DOCKER_SIGNER_FPR, and the
# scanner tarballs only when their SHA-256 equals the values below (copied from each release's checksums file).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=installer/prereq-lib.sh
. "${SCRIPT_DIR}/prereq-lib.sh"
PREREQ_NAME="install-ubuntu.sh"

DOCKER_SIGNER_FPR="9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
DOCKER_APT_URL="https://download.docker.com/linux/ubuntu"
DOCKER_APT_PGP="/etc/apt/keyrings/docker.asc"
DOCKER_APT_SOURCES="/etc/apt/sources.list.d/docker.sources"
DOCKER_PACKAGES="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin"
DOCKER_CONFLICTS="docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc"
TRIVY_VERSION="0.75.0"
GITLEAKS_VERSION="8.21.2"
LOCAL_BIN="${HOME}/.local/bin"

prereq_usage() {
  cat <<'EOF'
Usage: ./installer/install-ubuntu.sh [--yes] [--dry-run] [grdm-dev install options...]

  Prepares Ubuntu 24.04 (amd64 or arm64), then runs installer/install.sh.
    --yes       consent to every change listed in the plan, including sudo steps and the docker group
    --dry-run   detect and print what would happen; change nothing
  Other options go to install.sh unchanged, for example --profile minimum.

使い方: ./installer/install-ubuntu.sh [--yes] [--dry-run] [grdm-dev install のオプション...]

  Ubuntu 24.04（amd64 または arm64）を準備し、installer/install.sh を実行します。
    --yes       計画に載せたすべての変更（sudo の段と docker グループを含む）に同意する
    --dry-run   判定して予定を表示するだけで、何も変更しない
  ほかのオプションはそのまま install.sh に渡します。例: --profile minimum
EOF
}

prereq_parse_args "$@"

# --- host check (read-only) ------------------------------------------------------------------------
if [ "$(uname -s)" != "Linux" ]; then
  prereq_fail 10 "this script is for Ubuntu 24.04; on macOS use installer/install-macos.sh / このスクリプトは Ubuntu 24.04 用です。macOS では installer/install-macos.sh を使ってください"
fi
OS_RELEASE="${GRDM_PREREQ_OS_RELEASE:-/etc/os-release}"
os_value() { awk -F= -v key="$1" '$1 == key { gsub(/"/, "", $2); print $2; exit }' "${OS_RELEASE}" 2>/dev/null || true; }
if [ "$(os_value ID)" != "ubuntu" ] || [ "$(os_value VERSION_ID)" != "24.04" ]; then
  prereq_fail 10 "only Ubuntu 24.04 is supported here; on other Linux prepare the host yourself and run installer/install.sh / ここで対応するのは Ubuntu 24.04 だけです。他の Linux では自分で準備して installer/install.sh を実行してください"
fi
case "$(uname -m)" in
  x86_64) ARCH="amd64"; TRIVY_ASSET="Linux-64bit"; GITLEAKS_ASSET="linux_x64"
    TRIVY_SUM="c6e65abddb348e25f10549df887045629cf28cc72453cd1c63acb717316b3f3f"
    GITLEAKS_SUM="5bc41815076e6ed6ef8fbecc9d9b75bcae31f39029ceb55da08086315316e3ba" ;;
  aarch64|arm64) ARCH="arm64"; TRIVY_ASSET="Linux-ARM64"; GITLEAKS_ASSET="linux_arm64"
    TRIVY_SUM="a1ee9f6ffb7d112b64ff726a2a0717c21175c1114361391f4a132956751a13b3"
    GITLEAKS_SUM="654c935542c89f565aabe7bf7c6c500830f116c114f0aeb509d2460c1ac2e6da" ;;
  *) prereq_fail 10 "unsupported CPU: $(uname -m) / 対応していない CPU です: $(uname -m)" ;;
esac

IS_WSL=0
if [ -n "${WSL_DISTRO_NAME:-}" ] || grep -qi microsoft "${GRDM_PREREQ_PROC_VERSION:-/proc/version}" 2>/dev/null; then IS_WSL=1; fi
if [ "${IS_WSL}" = "1" ]; then
  case "${PREREQ_ROOT}" in
    /mnt/*) prereq_fail 10 "this checkout is on the Windows disk (${PREREQ_ROOT}); clone it inside WSL, for example under ~/ / このチェックアウトは Windows のディスク上にあります（${PREREQ_ROOT}）。~/ など WSL の中に clone してください" ;;
  esac
fi

# --- detection (read-only) -------------------------------------------------------------------------
pkg_installed() { [ "$(dpkg-query -W -f='${Status}' "$1" 2>/dev/null || true)" = "install ok installed" ]; }

APT_MISSING=""
for pkg in git python3 python3-venv curl gnupg ca-certificates; do
  if ! pkg_installed "${pkg}"; then APT_MISSING="${APT_MISSING} ${pkg}"; fi
done
APT_MISSING="${APT_MISSING# }"

NEED_ENGINE=0
if ! command -v docker >/dev/null 2>&1 || ! prereq_docker_client_ok || ! prereq_docker_plugins_ok; then
  if [ "${IS_WSL}" = "1" ]; then
    prereq_stop 11 "Docker is not usable inside this WSL distribution. Install Docker Desktop on Windows and enable Settings > Resources > WSL Integration for this distribution." \
      "この WSL ディストリビューションで Docker を使えません。Windows に Docker Desktop を入れ、Settings > Resources > WSL Integration でこのディストリビューションを有効にしてください。"
  else
    NEED_ENGINE=1
  fi
fi
if [ "${NEED_ENGINE}" = "1" ]; then
  CONFLICTS=""
  for pkg in ${DOCKER_CONFLICTS}; do
    if pkg_installed "${pkg}"; then CONFLICTS="${CONFLICTS} ${pkg}"; fi
  done
  if [ -n "${CONFLICTS}" ]; then
    prereq_stop 11 "these packages conflict with Docker's official packages:${CONFLICTS}" \
      "Remove them yourself (your images and volumes stay in /var/lib/docker), then run this script again: sudo apt-get remove${CONFLICTS}" \
      "これらは Docker 公式のパッケージと衝突します。自分で削除して（イメージとボリュームは /var/lib/docker に残ります）、もう一度実行してください。"
  fi
fi

NEED_EMULATION=0
if [ "${ARCH}" = "arm64" ] && [ "${IS_WSL}" = "0" ]; then
  # The F flag is what makes the interpreter usable from inside a container.
  binfmt="${GRDM_PREREQ_BINFMT_DIR:-/proc/sys/fs/binfmt_misc}/qemu-x86_64"
  if ! grep -q '^enabled' "${binfmt}" 2>/dev/null || ! grep -q '^flags:.*F' "${binfmt}" 2>/dev/null; then NEED_EMULATION=1; fi
fi

export PATH="${LOCAL_BIN}:${PATH}"
NEED_TRIVY=0; command -v trivy >/dev/null 2>&1 || NEED_TRIVY=1
NEED_GITLEAKS=0; command -v gitleaks >/dev/null 2>&1 || NEED_GITLEAKS=1

# --- plan and consent ------------------------------------------------------------------------------
if [ -n "${APT_MISSING}" ]; then
  prereq_plan "sudo: install apt packages: ${APT_MISSING}" "sudo: apt パッケージを入れる: ${APT_MISSING}"
fi
if [ "${NEED_ENGINE}" = "1" ]; then
  prereq_plan "sudo: add Docker's signed apt repository and install ${DOCKER_PACKAGES}, then start the docker service" \
    "sudo: Docker の署名付き apt リポジトリを追加し、${DOCKER_PACKAGES} を入れて docker サービスを起動する"
fi
if [ "${NEED_EMULATION}" = "1" ]; then
  prereq_plan "sudo: install qemu-user-static so that amd64 images can run on this arm64 host" \
    "sudo: この arm64 ホストで amd64 イメージを動かすため qemu-user-static を入れる"
fi
if [ "${NEED_TRIVY}" = "1" ]; then
  prereq_plan "download trivy ${TRIVY_VERSION} (SHA-256 checked) into ${LOCAL_BIN}" "trivy ${TRIVY_VERSION} を（SHA-256 を検証して）${LOCAL_BIN} に入れる"
fi
if [ "${NEED_GITLEAKS}" = "1" ]; then
  prereq_plan "download gitleaks ${GITLEAKS_VERSION} (SHA-256 checked) into ${LOCAL_BIN}" "gitleaks ${GITLEAKS_VERSION} を（SHA-256 を検証して）${LOCAL_BIN} に入れる"
fi
prereq_show_plan
prereq_token_note
if [ "${#PREREQ_PLAN_EN[@]}" -gt 0 ]; then
  prereq_confirm "Make these changes?" "これらの変更を行いますか?"
fi

# --- changes ---------------------------------------------------------------------------------------
if [ -n "${APT_MISSING}" ]; then
  prereq_step 10 "update the apt package lists" prereq_as_root apt-get update
  # shellcheck disable=SC2086  # APT_MISSING is a list of package names
  prereq_step 10 "install ${APT_MISSING}" prereq_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y ${APT_MISSING}
fi

verify_docker_signer() {  # verify_docker_signer <file>: exactly one primary key, with the expected fingerprint
  GNUPGHOME="${PREREQ_TMP}/gnupg"
  export GNUPGHOME
  mkdir -m 700 -p "${GNUPGHOME}"
  listing="$(gpg --show-keys --with-colons --with-fingerprint "$1" 2>/dev/null || true)"
  primaries="$(printf '%s\n' "${listing}" | grep -c '^pub:' || true)"
  fingerprint="$(printf '%s\n' "${listing}" | awk -F: '$1 == "fpr" { print $10; exit }')"
  if [ "${primaries}" != "1" ] || [ "${fingerprint}" != "${DOCKER_SIGNER_FPR}" ]; then
    prereq_fail 11 "the downloaded Docker signing key has an unexpected fingerprint: refusing to trust it" \
      "expected ${DOCKER_SIGNER_FPR}, got ${fingerprint:-none} (${primaries} primary keys)" \
      "ダウンロードした Docker の署名鍵の指紋が想定と違うため、信頼しません。"
  fi
}

if [ "${NEED_ENGINE}" = "1" ]; then
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    prereq_say "[dry-run] download ${DOCKER_APT_URL}/gpg, require fingerprint ${DOCKER_SIGNER_FPR}, install it as ${DOCKER_APT_PGP}, write ${DOCKER_APT_SOURCES} (noble stable ${ARCH})"
  else
    prereq_tmp
    prereq_step 11 "download Docker's apt signing key" curl --proto '=https' --tlsv1.2 -fsSL -o "${PREREQ_TMP}/docker.asc" "${DOCKER_APT_URL}/gpg"
    verify_docker_signer "${PREREQ_TMP}/docker.asc"
    prereq_say "Docker signing key verified: ${DOCKER_SIGNER_FPR}" "Docker の署名鍵を検証しました: ${DOCKER_SIGNER_FPR}"
    cat > "${PREREQ_TMP}/docker.sources" <<EOF
Types: deb
URIs: ${DOCKER_APT_URL}
Suites: noble
Components: stable
Architectures: ${ARCH}
Signed-By: ${DOCKER_APT_PGP}
EOF
    prereq_step 11 "install the signing key" prereq_as_root install -D -m 0644 "${PREREQ_TMP}/docker.asc" "${DOCKER_APT_PGP}"
    prereq_step 11 "add Docker's apt repository" prereq_as_root install -D -m 0644 "${PREREQ_TMP}/docker.sources" "${DOCKER_APT_SOURCES}"
  fi
  prereq_step 11 "update the apt package lists" prereq_as_root apt-get update
  # shellcheck disable=SC2086  # DOCKER_PACKAGES is a list of package names
  prereq_step 11 "install Docker Engine and its plugins" prereq_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y ${DOCKER_PACKAGES}
  prereq_step 11 "start the docker service" prereq_as_root systemctl enable --now docker.service
fi

if [ "${NEED_EMULATION}" = "1" ]; then
  prereq_step 11 "update the apt package lists" prereq_as_root apt-get update
  prereq_step 11 "install amd64 emulation" prereq_as_root env DEBIAN_FRONTEND=noninteractive apt-get install -y qemu-user-static
  if [ "${PREREQ_DRY_RUN}" = "0" ] && ! grep -q '^enabled' "${binfmt}" 2>/dev/null; then
    prereq_fail 11 "amd64 emulation is not registered in the kernel after installing qemu-user-static (${binfmt})" \
      "qemu-user-static を入れた後もカーネルに amd64 エミュレーションが登録されていません（${binfmt}）"
  fi
fi

install_scanner() {  # install_scanner <name> <url> <sha256>
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    prereq_say "[dry-run] download $2, require SHA-256 $3, install $1 into ${LOCAL_BIN}"
    return 0
  fi
  prereq_tmp
  archive="${PREREQ_TMP}/$1.tar.gz"
  prereq_step 10 "download $1" curl --proto '=https' --tlsv1.2 -fsSL -o "${archive}" "$2"
  if ! printf '%s  %s\n' "$3" "${archive}" | sha256sum -c --status; then
    prereq_fail 10 "$1: the download does not match its pinned SHA-256; nothing was installed / $1: ダウンロードが固定した SHA-256 と一致しないため、入れていません"
  fi
  mkdir -p "${PREREQ_TMP}/$1" "${LOCAL_BIN}"
  prereq_step 10 "unpack $1" tar -xzf "${archive}" -C "${PREREQ_TMP}/$1" "$1"
  prereq_step 10 "install $1 into ${LOCAL_BIN}" install -m 0755 "${PREREQ_TMP}/$1/$1" "${LOCAL_BIN}/$1"
}
if [ "${NEED_TRIVY}" = "1" ]; then
  install_scanner trivy "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_${TRIVY_ASSET}.tar.gz" "${TRIVY_SUM}"
fi
if [ "${NEED_GITLEAKS}" = "1" ]; then
  install_scanner gitleaks "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_${GITLEAKS_ASSET}.tar.gz" "${GITLEAKS_SUM}"
fi

# --- docker group: root-equivalent, so it has its own question -------------------------------------
# Only a socket this user cannot open is a group problem; a stopped daemon is for `grdm-dev doctor` to report.
USE_SG=""
DOCKER_SOCK="/var/run/docker.sock"
if [ "${IS_WSL}" = "0" ] && [ "$(id -u)" != "0" ] \
  && { [ "${NEED_ENGINE}" = "1" ] || { [ -S "${DOCKER_SOCK}" ] && [ ! -w "${DOCKER_SOCK}" ]; }; } \
  && ! docker info >/dev/null 2>&1; then
  me="$(id -un)"
  if id -nG "${me}" 2>/dev/null | tr ' ' '\n' | grep -qx docker; then
    USE_SG="sg"
  else
    prereq_say "Warning: members of the docker group can act as root on this computer." \
      "警告: docker グループの利用者は、このコンピュータの管理者と同じことができます。"
    prereq_confirm "Add ${me} to the docker group?" "${me} を docker グループに加えますか?"
    prereq_step 11 "add ${me} to the docker group" prereq_as_root usermod -aG docker "${me}"
    USE_SG="sg"
    prereq_say "This run continues in the docker group. For new terminals, log out and back in once." \
      "この実行は docker グループで続けます。新しい端末のために、一度ログアウトしてログインし直してください。"
  fi
fi

prereq_handover ${USE_SG}
