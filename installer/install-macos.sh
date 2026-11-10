#!/usr/bin/env bash
# Prerequisites for macOS on Apple Silicon, then installer/install.sh (ADR-08, SPEC-02 §2.3).
# It only prepares the host: every installation decision stays in install.sh and grdm-dev.
#
# What it may change, after showing it and asking: Homebrew formulae (python@3.12, git, trivy, gitleaks; each
# bottle is checked by Homebrew against the checksum in its formula) and starting an already installed Docker
# Desktop. It does not install Homebrew or a Docker runtime: Homebrew's own one-line installer pipes a
# download into a shell, which ADR-08 rejects, and Docker Desktop's licence is the user's decision.
# Runs on the bash that ships with macOS (3.2).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=installer/prereq-lib.sh
. "${SCRIPT_DIR}/prereq-lib.sh"
PREREQ_NAME="install-macos.sh"
DOCKER_WAIT_SECONDS=120
APPLICATIONS="${GRDM_PREREQ_APPLICATIONS:-/Applications}"

prereq_usage() {
  cat <<'EOF'
Usage: ./installer/install-macos.sh [--yes] [--dry-run] [grdm-dev install options...]

  Prepares macOS on Apple Silicon, then runs installer/install.sh.
    --yes       consent to every change listed in the plan
    --dry-run   detect and print what would happen; change nothing
  Other options go to install.sh unchanged, for example --profile minimum.

使い方: ./installer/install-macos.sh [--yes] [--dry-run] [grdm-dev install のオプション...]

  Apple Silicon の macOS を準備し、installer/install.sh を実行します。
    --yes       計画に載せたすべての変更に同意する
    --dry-run   判定して予定を表示するだけで、何も変更しない
  ほかのオプションはそのまま install.sh に渡します。例: --profile minimum
EOF
}

prereq_parse_args "$@"

# --- host check (read-only) ------------------------------------------------------------------------
if [ "$(uname -s)" != "Darwin" ]; then
  prereq_fail 10 "this script is for macOS; on Ubuntu use installer/install-ubuntu.sh / このスクリプトは macOS 用です。Ubuntu では installer/install-ubuntu.sh を使ってください"
fi
if [ "$(uname -m)" != "arm64" ]; then
  prereq_say "Warning: Intel Macs are best-effort only (SPEC-02 §8)." "警告: Intel の Mac はできる範囲での対応です（SPEC-02 §8）。"
fi

# --- Homebrew --------------------------------------------------------------------------------------
BREW=""
for candidate in ${GRDM_PREREQ_BREW_CANDIDATES-/opt/homebrew/bin/brew /usr/local/bin/brew}; do
  if [ -x "${candidate}" ]; then BREW="${candidate}"; break; fi
done
if [ -z "${BREW}" ] && command -v brew >/dev/null 2>&1; then BREW="$(command -v brew)"; fi
if [ -n "${BREW}" ]; then
  PATH="$(dirname "${BREW}"):${PATH}"
  export PATH
else
  prereq_stop 10 "Homebrew is required and was not found. Install it from the signed .pkg on its official releases page, then run this script again: https://github.com/Homebrew/brew/releases/latest" \
    "Homebrew が必要ですが見つかりません。公式のリリースページにある署名付き .pkg から入れて、もう一度実行してください: https://github.com/Homebrew/brew/releases/latest"
fi

# --- detection (read-only) -------------------------------------------------------------------------
FORMULAE=""
if ! prereq_python_ok; then FORMULAE="${FORMULAE} python@3.12"; fi
if ! git --version >/dev/null 2>&1; then FORMULAE="${FORMULAE} git"; fi
if ! command -v trivy >/dev/null 2>&1; then FORMULAE="${FORMULAE} trivy"; fi
if ! command -v gitleaks >/dev/null 2>&1; then FORMULAE="${FORMULAE} gitleaks"; fi
FORMULAE="${FORMULAE# }"

docker_up() { docker info >/dev/null 2>&1; }

START_DESKTOP=0
if ! command -v docker >/dev/null 2>&1 || ! docker_up; then
  if [ -d "${APPLICATIONS}/Docker.app" ]; then
    START_DESKTOP=1
  elif [ -d "${APPLICATIONS}/OrbStack.app" ]; then
    prereq_stop 11 "OrbStack is installed but its Docker engine is not answering. Start OrbStack, then run this script again." \
      "OrbStack は入っていますが Docker エンジンが応答しません。OrbStack を起動して、もう一度実行してください。"
  elif command -v colima >/dev/null 2>&1; then
    prereq_stop 11 "Colima is installed but its Docker engine is not answering. Run 'colima start', then run this script again." \
      "Colima は入っていますが Docker エンジンが応答しません。'colima start' を実行して、もう一度実行してください。"
  else
    prereq_stop 11 "No Docker runtime was found. Install Docker Desktop from https://www.docker.com/products/docker-desktop/ (check that its licence fits your organisation), then run this script again." \
      "Docker の実行基盤が見つかりません。https://www.docker.com/products/docker-desktop/ から Docker Desktop を入れ（ライセンスが所属組織に合うか確認してください）、もう一度実行してください。"
  fi
fi

# --- plan and consent ------------------------------------------------------------------------------
if [ -n "${FORMULAE}" ]; then
  prereq_plan "brew install ${FORMULAE}" "brew install ${FORMULAE} を実行する"
fi
if [ "${START_DESKTOP}" = "1" ]; then
  prereq_plan "start Docker Desktop and wait up to ${DOCKER_WAIT_SECONDS} seconds" "Docker Desktop を起動し、最長 ${DOCKER_WAIT_SECONDS} 秒待つ"
fi
prereq_show_plan
prereq_token_note
if [ "${#PREREQ_PLAN_EN[@]}" -gt 0 ]; then
  prereq_confirm "Make these changes?" "これらの変更を行いますか?"
fi

# --- changes ---------------------------------------------------------------------------------------
if [ -n "${FORMULAE}" ]; then
  # shellcheck disable=SC2086  # FORMULAE is a list of formula names
  prereq_step 10 "install Homebrew formulae: ${FORMULAE}" brew install ${FORMULAE}
fi

if [ "${START_DESKTOP}" = "1" ]; then
  prereq_step 11 "start Docker Desktop" open -a Docker
  if [ "${PREREQ_DRY_RUN}" = "0" ]; then
    waited=0
    until docker_up; do
      if [ "${waited}" -ge "${DOCKER_WAIT_SECONDS}" ]; then
        prereq_fail 11 "Docker Desktop did not answer within ${DOCKER_WAIT_SECONDS} seconds; finish its first-start steps and run this script again" \
          "Docker Desktop が ${DOCKER_WAIT_SECONDS} 秒以内に応答しませんでした。初回起動の手順を済ませて、もう一度実行してください"
      fi
      sleep 5
      waited=$((waited + 5))
    done
  fi
fi

if [ "${PREREQ_DRY_RUN}" = "0" ] && { ! prereq_docker_client_ok || ! prereq_docker_plugins_ok; }; then
  prereq_fail 11 "Docker 27 or newer with the Compose and buildx plugins is required; update your Docker runtime" \
    "Docker 27 以上と Compose・buildx プラグインが必要です。Docker の実行基盤を更新してください"
fi

prereq_handover
