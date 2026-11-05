#!/usr/bin/env bash
# grdm-dev bootstrap (SPEC-02 §2.1). Does four things and nothing else:
#   1. runs on the bash that ships with macOS (3.2): no associative arrays, no mapfile, no ${var,,}
#   2. finds python3 >= 3.11, or prints how to install one for this OS and exits 10
#   3. creates .venv/ at the repository root and runs `pip install -e installer`
#   4. exec .venv/bin/grdm-dev install "$@"
# OS differences live in installer/grdm_dev/host.py. Exit-code messages come from
# installer/grdm_dev/messages.tsv so bash and Python say the same thing.
#
# Environment: GRDM_PYTHON=<path> use this interpreter; GRDM_WITH_ACCEPT=1 also installs the
# [accept] extra (pytest-playwright); GRDM_SKIP_EXEC=1 stop after the venv (tests only).
# --- 0. CRLF guard. bash misreads a CRLF file, so this runs before `set` and stays on ONE line that ends in a
#        comment: the stray \r then lands inside the comment and the line still parses.
if grep -q "$(printf '\r')" "${BASH_SOURCE[0]}" 2>/dev/null; then printf '[install.sh] exit 2: %s\n  this script has CRLF line endings; fix: sed -i "" "s/\\r$//" installer/install.sh\n  このスクリプトの改行が CRLF です。修正: sed -i "" "s/\\r$//" installer/install.sh\n' "$(awk -F '\t' '$1 == "2" { printf "%s / %s", $2, $3; exit }' "$(dirname "${BASH_SOURCE[0]}")/grdm_dev/messages.tsv" 2>/dev/null || echo 'usage error')" >&2; exit 2; fi # one line, see above
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INST="${ROOT}/installer"
MESSAGES="${INST}/grdm_dev/messages.tsv"
VENV="${ROOT}/.venv"
MIN_MAJOR=3
MIN_MINOR=11

# --- messages ------------------------------------------------------------------------------------
# message <code>: print "en / ja" for an exit code from messages.tsv (awk only; bash 3.2 safe).
message() {
  if [ -f "${MESSAGES}" ]; then
    awk -F '\t' -v code="$1" '$1 == code { printf "%s / %s\n", $2, $3; exit }' "${MESSAGES}"
  else
    printf 'exit %s\n' "$1"
  fi
}
fail() {  # fail <code> <detail...>
  code="$1"; shift
  printf '[install.sh] exit %s: %s\n' "${code}" "$(message "${code}")" >&2
  if [ $# -gt 0 ]; then printf '%s\n' "$@" | sed 's/^/  /' >&2; fi
  exit "${code}"
}

usage() {
  cat <<'EOF'
Usage: ./installer/install.sh [grdm-dev install options...]

  Bootstraps the GakuNin RDM developer environment 2027:
    1. checks that python3 is 3.11 or newer (exit 10 with install hints otherwise)
    2. creates .venv/ at the repository root and installs installer/ into it
    3. runs  .venv/bin/grdm-dev install "$@"  and exits with its code
  Options after the script name are passed to grdm-dev install unchanged, e.g.
    --yes                  answer every question with its default
    --profile minimum|core|full
    --json                 print reports as JSON instead of TOON
  Environment: GRDM_PYTHON=<python3 path>, GRDM_WITH_ACCEPT=1 (install the [accept] extra).
  Exit codes: see installer/grdm_dev/messages.tsv (SPEC-02 §6).

使い方: ./installer/install.sh [grdm-dev install のオプション...]

  GakuNin RDM 開発環境 2027 を起動する薄いスクリプトです:
    1. python3 が 3.11 以上か確かめる（違えば導入方法を示して終了コード 10）
    2. リポジトリのルートに .venv/ を作り installer/ を入れる
    3. .venv/bin/grdm-dev install "$@" を実行し、その終了コードで終わる
  スクリプト名の後ろの引数はそのまま grdm-dev install に渡します。例:
    --yes                  すべての質問に既定で答える
    --profile minimum|core|full
    --json                 報告を TOON ではなく JSON で出す
  環境変数: GRDM_PYTHON=<python3 の場所>、GRDM_WITH_ACCEPT=1（[accept] 追加分も入れる）
  終了コード: installer/grdm_dev/messages.tsv を参照（SPEC-02 §6）
EOF
}
for a in "$@"; do
  case "$a" in
    -h|--help) usage; exit 0 ;;
    --) break ;;
  esac
done

# --- 1. find python3 >= 3.11 --------------------------------------------------------------------
py_ok() {  # py_ok <interpreter>: 0 when it runs and is >= MIN_MAJOR.MIN_MINOR
  "$1" -c "import sys; sys.exit(0 if sys.version_info[:2] >= (${MIN_MAJOR}, ${MIN_MINOR}) else 1)" >/dev/null 2>&1
}
py_version() { "$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || echo "unknown"; }

PY=""
FOUND=""
for cand in ${GRDM_PYTHON:-} python3 python3.13 python3.12 python3.11 python; do
  if command -v "${cand}" >/dev/null 2>&1; then
    if [ -z "${FOUND}" ]; then FOUND="${cand} ($(py_version "${cand}"))"; fi
    if py_ok "${cand}"; then PY="${cand}"; break; fi
  fi
done

os_hint() {  # how to install Python for this OS (the only OS-specific text in this script)
  uname_s="$(uname -s 2>/dev/null || echo unknown)"
  case "${uname_s}" in
    Darwin)
      echo "macOS: brew install python@3.12   (Homebrew, https://brew.sh)"
      echo "macOS: brew install python@3.12   （Homebrew、https://brew.sh）" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then
        echo "WSL2 (Ubuntu): sudo apt update && sudo apt install -y python3.12 python3.12-venv"
        echo "WSL2（Ubuntu）: sudo apt update && sudo apt install -y python3.12 python3.12-venv"
      else
        echo "Ubuntu: sudo apt update && sudo apt install -y python3.12 python3.12-venv"
        echo "Ubuntu: sudo apt update && sudo apt install -y python3.12 python3.12-venv"
      fi ;;
    *)
      echo "install Python 3.11 or newer from https://www.python.org/downloads/"
      echo "Python 3.11 以上を https://www.python.org/downloads/ から入れてください" ;;
  esac
}

if [ -z "${PY}" ]; then
  if [ -n "${FOUND}" ]; then
    detail="python3 found but too old: ${FOUND}; need ${MIN_MAJOR}.${MIN_MINOR} or newer / python3 が古すぎます: ${FOUND}（${MIN_MAJOR}.${MIN_MINOR} 以上が必要）"
  else
    detail="python3 not found on PATH / python3 が PATH にありません"
  fi
  fail 10 "${detail}" "$(os_hint)"
fi

# --- 2. virtual environment ---------------------------------------------------------------------
if [ ! -x "${VENV}/bin/python" ]; then
  printf '[install.sh] creating %s with %s (%s)\n' ".venv/" "${PY}" "$(py_version "${PY}")"
  if ! "${PY}" -m venv "${VENV}"; then
    rm -rf "${VENV}"
    fail 10 "could not create .venv/ (python3-venv missing?) / .venv/ を作れません（python3-venv が無い?）" "$(os_hint)"
  fi
fi
VPY="${VENV}/bin/python"
if ! py_ok "${VPY}"; then
  fail 10 "existing .venv/ uses Python $(py_version "${VPY}"); remove .venv/ and rerun / 既存の .venv/ の Python $(py_version "${VPY}") が古いです。.venv/ を消して再実行してください"
fi

EXTRA=""
if [ "${GRDM_WITH_ACCEPT:-0}" = "1" ]; then EXTRA="[accept]"; fi
"${VPY}" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
if ! "${VPY}" -m pip install -q -e "${INST}${EXTRA}"; then
  fail 2 "pip install -e installer${EXTRA} failed / pip install -e installer${EXTRA} に失敗しました"
fi

if [ "${GRDM_SKIP_EXEC:-0}" = "1" ]; then exit 0; fi

# --- 3. hand over -------------------------------------------------------------------------------
[ -x "${VENV}/bin/grdm-dev" ] || fail 2 ".venv/bin/grdm-dev was not installed / .venv/bin/grdm-dev が入っていません"
cd "${ROOT}"
exec "${VENV}/bin/grdm-dev" install "$@"
