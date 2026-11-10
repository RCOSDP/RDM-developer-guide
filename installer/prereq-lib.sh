# shellcheck shell=bash
# Shared helpers for the per-OS prerequisite scripts (ADR-08, SPEC-02 §2.3). Sourced, never run.
# Stays on bash 3.2 (the macOS bash): no associative arrays, no mapfile, no ${var,,}.
#
# Contract kept by every script that sources this file:
#   - detection is read-only; each change is listed first and needs consent (--yes gives it up front);
#   - --dry-run performs detection and prints what would happen, and changes nothing;
#   - the last action is always installer/install.sh, so there is one decision path;
#   - exit codes are the ones in installer/grdm_dev/messages.tsv: 2 refused or no consent, 10 host or
#     Python/git prerequisite, 11 Docker prerequisite. No new number is introduced.
#   - no token is read, stored or passed; prereq_token_note only says how to provide one.

PREREQ_NAME="prereq"
PREREQ_YES=0
PREREQ_DRY_RUN=0
PREREQ_FORWARD=()
PREREQ_TMP=""
PREREQ_PLAN_EN=()
PREREQ_PLAN_JA=()
# Physical path (pwd -P): a symlinked checkout must be judged by where its files really are (PR #44 review r1 R2).
PREREQ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
PREREQ_MESSAGES="${PREREQ_ROOT}/installer/grdm_dev/messages.tsv"

prereq_say() {  # prereq_say <english> [<japanese>]
  printf '[%s] %s\n' "${PREREQ_NAME}" "$1"
  if [ $# -gt 1 ]; then printf '[%s] %s\n' "${PREREQ_NAME}" "$2"; fi
}

prereq_cleanup() {
  if [ -n "${PREREQ_TMP}" ]; then rm -rf "${PREREQ_TMP}"; PREREQ_TMP=""; fi
}
trap prereq_cleanup EXIT

prereq_tmp() {  # creates the private temporary directory once; the path is left in PREREQ_TMP
  if [ -z "${PREREQ_TMP}" ]; then PREREQ_TMP="$(mktemp -d)"; fi
}

prereq_message() {  # the canonical "en / ja" sentence for an exit code
  if [ -f "${PREREQ_MESSAGES}" ]; then
    awk -F '\t' -v code="$1" '$1 == code { printf "%s / %s\n", $2, $3; exit }' "${PREREQ_MESSAGES}"
  else
    printf 'exit %s\n' "$1"
  fi
}

prereq_fail() {  # prereq_fail <code> <detail line>...: always stops
  code="$1"; shift
  printf '[%s] exit %s: %s\n' "${PREREQ_NAME}" "${code}" "$(prereq_message "${code}")" >&2
  if [ $# -gt 0 ]; then printf '%s\n' "$@" | sed 's/^/  /' >&2; fi
  exit "${code}"
}

prereq_stop() {  # like prereq_fail, but --dry-run reports the stop and goes on, to show the rest of the plan
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    code="$1"; shift
    printf '[%s] [dry-run] would stop with exit %s: %s\n' "${PREREQ_NAME}" "${code}" "$(prereq_message "${code}")"
    if [ $# -gt 0 ]; then printf '%s\n' "$@" | sed 's/^/  /'; fi
    return 0
  fi
  prereq_fail "$@"
}

prereq_parse_args() {  # sets PREREQ_YES and PREREQ_DRY_RUN; every other argument goes to install.sh unchanged
  for a in "$@"; do
    case "${a}" in
      -h|--help) prereq_usage; exit 0 ;;
      --dry-run) PREREQ_DRY_RUN=1 ;;
      -y|--yes) PREREQ_YES=1; PREREQ_FORWARD+=("--yes") ;;
      *) PREREQ_FORWARD+=("${a}") ;;
    esac
  done
}

prereq_plan() {  # prereq_plan <english> <japanese>: one planned change
  PREREQ_PLAN_EN+=("$1")
  PREREQ_PLAN_JA+=("$2")
}

prereq_show_plan() {
  if [ "${#PREREQ_PLAN_EN[@]}" -eq 0 ]; then
    prereq_say "All prerequisites are already present; nothing to change." "前提条件はすべて揃っています。変更するものはありません。"
    return 0
  fi
  prereq_say "This script will make these changes:" "このスクリプトは次の変更を行います:"
  i=0
  while [ "${i}" -lt "${#PREREQ_PLAN_EN[@]}" ]; do
    printf '  %d. %s\n     %s\n' "$((i + 1))" "${PREREQ_PLAN_EN[${i}]}" "${PREREQ_PLAN_JA[${i}]}"
    i=$((i + 1))
  done
}

prereq_confirm() {  # prereq_confirm <english question> <japanese question>: returns 0 on consent, otherwise stops with exit 2
  if [ "${PREREQ_YES}" = "1" ]; then return 0; fi
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    if [ ! -t 0 ]; then
      prereq_say "[dry-run] would stop with exit 2: no terminal and no --yes" "[dry-run] 端末が無く --yes も無いため終了 2 で止まります"
    fi
    return 0
  fi
  if [ ! -t 0 ]; then
    prereq_fail 2 "no terminal to ask on: add --yes to consent / 確認する端末がありません。同意するには --yes を付けてください"
  fi
  printf '%s\n%s [y/N] ' "$1" "$2"
  answer=""
  read -r answer || answer=""
  case "${answer}" in
    y|Y|yes|YES|Yes) return 0 ;;
    *) prereq_fail 2 "declined; nothing further was changed / 同意がなかったため、これ以上は変更しません" ;;
  esac
}

prereq_step() {  # prereq_step <exit code> <description> <command...>: prints or runs; a failure stops with the code
  code="$1"; what="$2"; shift 2
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    shown="$*"
    printf '[%s] [dry-run] %s: %s\n' "${PREREQ_NAME}" "${what}" "${shown/#prereq_as_root/sudo}"
    return 0
  fi
  prereq_say "${what}"
  if ! "$@"; then
    prereq_fail "${code}" "failed: ${what} / 失敗しました: ${what}" "command: $*"
  fi
}

prereq_as_root() {  # runs a command with sudo; without a terminal sudo must not ask, so it fails instead of hanging
  if [ "$(id -u)" = "0" ]; then
    "$@"
  elif [ -t 0 ]; then
    sudo "$@"
  else
    sudo -n "$@"
  fi
}

prereq_python_ok() {  # 0 when an interpreter of 3.11 or newer is on PATH (same candidates as install.sh)
  for cand in python3 python3.13 python3.12 python3.11; do
    if command -v "${cand}" >/dev/null 2>&1 \
      && "${cand}" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

prereq_docker_client_ok() {  # 0 when the docker client is version 27 or newer (the daemon may be unreachable)
  version="$(docker version --format '{{.Client.Version}}' 2>/dev/null || true)"
  major="${version%%.*}"
  case "${major}" in
    ''|*[!0-9]*) return 1 ;;
  esac
  [ "${major}" -ge 27 ]
}

prereq_docker_plugins_ok() {
  docker compose version >/dev/null 2>&1 && docker buildx version >/dev/null 2>&1
}

prereq_token_note() {
  prereq_say "Note: the integration repositories are private. This script never asks for, reads or stores a token." \
    "注意: 統合リポジトリは非公開です。このスクリプトはトークンを尋ねず、読まず、保存しません。"
  prereq_say "Before the build, give git your own access, for example: gh auth login && gh auth setup-git" \
    "ビルドの前に git へ自分の権限を設定してください。例: gh auth login && gh auth setup-git"
}

prereq_handover() {  # prereq_handover [sg]: the last action of every script. "sg" runs it in the docker group.
  prereq_cleanup
  target="${PREREQ_ROOT}/installer/install.sh"
  if [ "${PREREQ_DRY_RUN}" = "1" ]; then
    printf '[%s] [dry-run] would run: %s' "${PREREQ_NAME}" "${target}"
    if [ "${#PREREQ_FORWARD[@]}" -gt 0 ]; then printf ' %s' "${PREREQ_FORWARD[@]}"; fi
    printf '\n'
    exit 0
  fi
  if [ "${1:-}" = "sg" ]; then
    # shellcheck disable=SC2068  # the ${a[@]+"${a[@]}"} form is what keeps an empty array safe on bash 3.2
    quoted="$(printf '%q ' bash "${target}" ${PREREQ_FORWARD[@]+"${PREREQ_FORWARD[@]}"})"
    exec sg docker -c "${quoted}"
  fi
  # shellcheck disable=SC2068  # see above
  exec bash "${target}" ${PREREQ_FORWARD[@]+"${PREREQ_FORWARD[@]}"}
}
