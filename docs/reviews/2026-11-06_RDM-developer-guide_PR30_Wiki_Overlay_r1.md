# PR30 Wiki Overlay Review r1 / Wiki オーバーレイレビュー r1

> **Summary:** Revision required: Compose expands the copier's shell variables before execution, preventing core startup. Volume permissions and browser wiring also need resolution.
> **概要:** 要修正。Compose がコピー処理のシェル変数を実行前に展開するため core が起動できない。ボリューム権限とブラウザへの接続も解決が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** Testing generated JSON does not test Compose interpolation or filesystem ownership. ／ 生成 JSON の試験だけでは Compose の変数展開やファイル所有権を検査できない。
- Applies to: PR #30, head `0b6f660de38458c46428659bb3d837ec2eab4f0c`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-01](../spec/01_manifest.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) and the PR author for the next revision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Needs revision.** No approval, merge, commit, push, or Docker state changes were performed. A successful test suite does not establish a working Wiki editor.

1. **R1-01 — P1, definite startup failure:** `installer/grdm_dev/templates/wiki_assets.json:9` embeds `$src`, `$dst`, and `$f` in Compose command text. Compose substitutes host variables before the container shell runs. A temporary core render followed by read-only `docker compose -f <generated file> config --format json` warned that these variables were unset and produced `ls "" >/dev/null; find "" -mindepth 1 -delete; cp -a ""/. ""/`. With `set -e`, the copier fails immediately, and all four dependent application services cannot start. Escape shell variables as `$$src`, `$$dst`, `$$f`, or use a script file; add a test of the actual Compose-parsed command.
2. **R1-02 — P1, first-run permissions:** `compose.py` creates `runtime/volumes/wiki_static` with ordinary `mkdir` and binds it through a local-driver volume; the copier runs as `1000:1000` without capabilities. The temporary render created a directory owned by UID 501 with mode 0755. On native Linux with a non-1000 installer UID, the copier cannot write there; Desktop permission mapping needs separate verification. Provide a deliberate ownership/provisioning strategy and test a fresh volume with a non-1000 host user. Do not resolve this by silently removing the hardening controls.
3. **R1-03 — P2, editor wiring remains missing:** the actual osf.io checkout's `addons/wiki/templates/edit.mako:733` still loads `/static/js/pages/wiki-edit-page.js`, while the new mount provides `/static/public/js/wiki/wiki-edit-page.js`. Neither the base image nor its template is changed here. ADR-06 openly records this unfinished step; the new bundle therefore is not yet used by the page. Track and pin the integration-repository fix, then demonstrate editor load and collaborative editing before declaring M2 working. Verify vendor/chunk loading in a browser rather than assuming that the alias alone is sufficient.

### Verified implementation and evidence

Read-only source checks used wiki commit `203d32fab60aad8d78e9b743987519252f99b817` and osf.io commit `356a997eb5fe7d4aa49c05a0bbcf736a3cf1e31f`. The wiki Dockerfile requires many base-only paths; webpack has the single `wiki-edit-page` entry and production output `website/static/public/js` with hashed names. Python application dependency installation, pybabel and collectstatic are commented out, so this image cannot serve the Python application. The literal claim “every Python step is commented out” is inaccurate: Python packages are installed and `python3 -m compileall /usr/lib/python3.6 || true` remains active. Narrow that wording in both languages.

Context assembly recreates the destination, excludes `.git` at every level, and copies the overlay over the base; ordinary overlapping files use the overlay version. Tests cover replacement and removal of stale context files. The tag and rendered image are `grdm-dev/wiki-frontend:356a997eb5fe-203d32fab60a`; build reports carry both source identities and the combined tag. The base keeps its own image. Rendered `wiki_assets` has user `1000:1000`, `cap_drop: [ALL]`, `no-new-privileges:true`, `read_only: true`, `restart: "no"`, no published port, and only the internal network. All four consumers mount the subdirectory read-only and wait for successful completion; minimum drops the dependency.

MC-14 rejects unknown/self/infra/overlay/prebuilt bases, infra/prebuilt overlays, and multiple overlays per base. The installer checks the one-shot template flag. Empty-string `overlay_of` is treated as absent rather than rejected despite the documented “when present” rule; tighten validation or document that normalization. Health correctly handles explicit zero/nonzero exit codes, but missing, null, and empty exit codes are also accepted as success; unknown completion should fail closed.

ADR-06, SPEC-00/01/02, and DEMO-20 carry corresponding English/Japanese changes and version learning notes; no substantive translation mismatch was found. Anchors and Jump links pass the documentation checker. ADR-06 links to the docs root but omits its immediate parent index, contrary to SPEC-06 §5; add `docs/decisions/README.md`. DEMO-20 records run 4's missing-COPY failure, not a successful overlay build or startup.

Additional runtime risks: `cp -a` attempts to retain root-owned build metadata under UID 1000; verify Alpine/BusyBox exit behavior and use a copy strategy that does not require ownership preservation. Clearing the shared directory before copying is not atomic: a retry or update can expose missing files to already-running consumers. Initial dependency ordering is correct once the copier succeeds, but does not protect a running application during asset replacement. Require a nonempty expected bundle/manifest before returning success. The actual merged image build, fresh-volume copy, restart/update behavior and browser acceptance were not run because Docker state changes were prohibited.

### Validation

Executed from the review worktree:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
```

Installer: 340 tests, OK, 10 skipped. Tools: 86 tests, OK. Manifest: zero findings. Documentation before adding this record: 79 files checked, eight exempt, 215 nonblocking glossary warnings. All eight GitHub checks passed, including Python 3.11/3.12 tests. None of these tests caught R1-01; the separate Compose parser check did.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正。** approve・merge・commit・push、および Docker の状態変更は行っていない。試験成功だけでは Wiki エディタの動作を証明できない。

1. **R1-01 — P1、確定した起動失敗:** `installer/grdm_dev/templates/wiki_assets.json:9` の `$src`・`$dst`・`$f` はコンテナのシェルより先に Compose がホスト変数として展開する。一時ディレクトリで core を生成し、読み取り専用の `docker compose -f <生成ファイル> config --format json` で確認すると未設定警告が出て、`ls "" >/dev/null; find "" -mindepth 1 -delete; cp -a ""/. ""/` になった。`set -e` により直ちに失敗し、依存する四つのアプリサービスも起動できない。`$$src`・`$$dst`・`$$f` とするかスクリプトファイルへ移し、Compose 解析後のコマンドを試験する。
2. **R1-02 — P1、初回の権限:** `compose.py` は通常の `mkdir` で `runtime/volumes/wiki_static` を作り、local driver で bind する。コピー側は capability のない `1000:1000`。一時生成では UID 501、0755 のディレクトリになった。ネイティブ Linux で実行者の UID が 1000 以外なら書き込めない。Desktop の権限変換は別途検証が必要。所有権を明示的に準備する方法と、非 1000 ホストユーザーによる新規ボリューム試験を追加する。防御設定を黙って外して解決しない。
3. **R1-03 — P2、画面への接続が未実装:** 実 osf.io checkout の `addons/wiki/templates/edit.mako:733` は `/static/js/pages/wiki-edit-page.js` を読む。新規 mount は `/static/public/js/wiki/wiki-edit-page.js` に置くが、この PR はベースイメージもテンプレートも変更しない。ADR-06 は未完と明記しているが、新しい束はまだ画面で利用されない。統合リポジトリの修正を追跡して固定し、M2 動作を宣言する前にエディタ表示・共同編集を実証する。別名ファイルだけで十分と仮定せず、vendor/chunk の読み込みもブラウザで確認する。

### 実装確認と証跡

読み取り専用で確認したコミットは wiki が `203d32fab60aad8d78e9b743987519252f99b817`、osf.io が `356a997eb5fe7d4aa49c05a0bbcf736a3cf1e31f`。wiki の Dockerfile は多数のベース側パスを必要とし、webpack の entry は `wiki-edit-page` 一つ、production 出力先は `website/static/public/js`、ファイル名にはハッシュが付く。Python アプリ依存の導入・pybabel・collectstatic はコメントアウトされ、このイメージは Python アプリを動かせない。ただし「すべての Python 手順がコメントアウト」は不正確で、Python パッケージ導入と `python3 -m compileall /usr/lib/python3.6 || true` は残る。英和とも表現を限定する。

文脈の組み立てはコピー先を作り直し、各階層の `.git` を除外し、ベースの上へオーバーレイをコピーする。通常の同名ファイルはオーバーレイが優先され、置換と古い文脈の除去は試験済み。タグと生成イメージは `grdm-dev/wiki-frontend:356a997eb5fe-203d32fab60a`。報告には双方の元と結合タグが入り、ベースは独自イメージを保持する。生成された `wiki_assets` は `1000:1000`、`cap_drop: [ALL]`、`no-new-privileges:true`、`read_only: true`、`restart: "no"`、公開ポートなし、内部ネットワークのみ。四つの利用側はサブディレクトリを読み取り専用で mount し、成功終了を待つ。minimum では依存を除く。

MC-14 は不明・自身・infra・overlay・prebuilt のベース、infra/prebuilt のオーバーレイ、同一ベースへの複数オーバーレイを拒否し、installer は一回限りのテンプレート印を検査する。ただし空文字の `overlay_of` は「存在するとき」という仕様に反して省略扱いになる。検証を強めるか正規化を明記する。health は明示的な終了コード 0/非 0 を扱うが、欠落・null・空文字まで成功とする。結果不明は成功にしない。

ADR-06・SPEC-00/01/02・DEMO-20 の英和変更と版の学習記録は対応し、実質的な翻訳不一致は見つからなかった。アンカーと Jump は文書検査を通過した。ADR-06 は docs ルートにリンクするが直属の親索引がなく SPEC-06 §5 に不足するため `docs/decisions/README.md` を加える。DEMO-20 の第 4 回は COPY 元欠落による失敗記録であり、オーバーレイのビルド・起動成功記録ではない。

追加リスク: `cp -a` は root 所有のビルド成果の属性を UID 1000 で保持しようとするため、Alpine/BusyBox での終了結果を確認し、所有権保持を必要としない方法にする。共有ディレクトリを消してからコピーする更新は不可分ではなく、再試行・更新中に稼働済み利用側からファイルが消える。初回の依存順序はコピー成功後なら正しいが、稼働中の更新は保護しない。成功扱いの前に期待する束と manifest が存在して空でないことも確認する。Docker 状態変更は禁止のため、実ビルド・新規ボリュームコピー・再起動更新・ブラウザ受入は未実施。

### 検証

実行コマンドは英語部のコードブロックのとおり。installer は 340 件 OK（10 skip）、tools は 86 件 OK、manifest は指摘 0。本記録追加前の文書検査は 79 ファイル、例外 8、非阻害の用語警告 215 で成功。GitHub の八つの検査は Python 3.11/3.12 を含め全成功。それらでは R1-01 を検出できず、別途実施した Compose 解析で検出した。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Overlay | Files laid over a base source tree before building. | 組む前にベースの木へ重ねるファイル。 |
| Compose | A tool that reads a file and coordinates containers. | ファイルを読んで複数の実行環境を動かす道具。 |
| UID | Numeric identity used to decide file access. | ファイルへのアクセスを決める利用者番号。 |
| Bundle / chunk | Browser code packaged into one or several files. | ブラウザ用コードをまとめたファイル。 |
| One-shot | A process that completes and exits. | 処理を終えたら終了するプログラム。 |
| SHA / tag | Commit identity / image name suffix. | コミットの識別値／イメージ名の末尾。 |
| CI | Automated checks run for proposed changes. | 変更案を自動で検査する仕組み。 |
