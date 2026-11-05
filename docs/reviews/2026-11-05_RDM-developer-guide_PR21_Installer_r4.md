# REV PR21 Installer review r4 / インストーラーレビュー r4

> **Summary:** The multi-platform pull defect is fixed at `6df8c4b`; previous verified fixes show no regression. Changes requested only for the remaining prebuilt `--push` policy/reporting part of R3-01.
> **概要:** `6df8c4b` で複数プラットフォームの取得不具合は解消し、確認済み修正の後退はない。R3-01 のうち prebuilt の `--push` 方針・結果表示が残るため、その部分のみ修正要求とする。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** checking every requested platform fixes pull accounting, but does not define what a push request means for a prebuilt component. ／ 全指定対象を検査すれば取得実績は正しくなるが、事前ビルド済み部品への送信要求の意味は別途定義が必要と分かった。
- Applies to: PR (proposed change / 変更案) [#21](https://github.com/RCOSDP/RDM-developer-guide/pull/21), `feat/m2-installer` → `develop`, head `6df8c4b20b810fc8cf67b5786f63e933f0be8c07`; REV（担当レビュワ）.
- Related: [Review index](README.md) · [r1](2026-11-05_RDM-developer-guide_PR21_Installer_r1.md) · [r2](2026-11-05_RDM-developer-guide_PR21_Installer_r2.md) · [r3](2026-11-05_RDM-developer-guide_PR21_Installer_r3.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Installer](../../installer/README.md) · [Status board](../status/README.md) · [Mac Studio run record](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested: R3-01 partially resolved; only the prebuilt `--push` contract remains (P2, behavior/documentation mismatch).** No new regression was found in the previously verified R1/R2 fixes. This is a code/test review, not real-install acceptance. GitHub access used `gh` only; no approve, merge, close, commit or push operation was performed. Docker (the tool running application boxes) state was not changed. External operations in build probes used fake runners (functions returning controlled answers).

The remote comparison from `9fbb734` to `6df8c4b` contains only `build.py`, `test_build.py` and the r3 review record. Before writing r4, all 326 tracked files under `installer/`, `tools/`, `manifest/` and `docs/` matched the requested head's blob hashes (file-content fingerprints), obtained through `gh api`. Thus the prior security and documentation fixes are unchanged; the installer and tools suites were rerun to check integration regressions. Earlier real-install limitations remain unchanged.

### R3-01: pull accounting resolved

[build.py](../../installer/grdm_dev/build.py), lines 164–171 and 213–229, now passes a single platform (operating-system/processor target) to `pull_argv(reference, platform)` and calls it once for every requested target. It continues after an individual failure, records only successful targets in `pulled`, sets `pull-failed` if any return code is nonzero, and exits 30 through the existing error path. `platforms` retains the requested list. The host fallback still makes one pull when the list is empty.

[test_build.py](../../installer/tests/test_build.py), lines 252–274, adds `test_prebuilt_multi_platform_pulls_each_and_fails_on_any`. For `linux/arm64,linux/amd64`, a simulated arm64 (Apple Silicon processor family) failure produces exactly two pulls, exit 30, `pull-failed`, and `pulled=linux/amd64`. arm64 (Apple Silicon processor family) and amd64 (Intel/AMD processor family) identify processor targets. The existing single-platform success/failure and source-build tests still pass.

An independent temporary-fixture probe additionally tested both `push=False` and `push=True` with four outcomes: both successful, first failing, second failing, and both failing. All eight cases asserted the exact ordered pull arguments, exit code, status and successful-target list. Both targets are attempted in every case; all-success exits 0, any failure exits 30, and both-failed records an empty `pulled` string. No real image was downloaded.

### Remaining part of R3-01

**P2: prebuilt `--push` is silently skipped without a defined exception.** With only a prebuilt component selected, `platform="linux/arm64,linux/amd64"`, `push=True` and two successful fake pulls, the command returns 0. Its report has top-level `push: true`, row `status: prebuilt`, and two successful `pulled` targets; the only operations are two `docker pull` calls. There is no push operation or explicit skipped-push result. The warning only says the component is not built from its source repository. See [build.py](../../installer/grdm_dev/build.py), lines 213–230 and 244.

[SPEC-02](../spec/02_installer_cli.md), English line 80 and Japanese line 272, still says `--push` sends the multi-architecture manifest to GHCR (the image distribution service), without defining a prebuilt exception. The r3 requested remedy explicitly included rejecting or explicitly skipping prebuilt push and aligning the result and documentation. Commit (saved change) `6df8c4b` addresses the platform loop but leaves that remedy unchanged. A caller requesting publication can receive success with no published image.

Reject this combination before pulling, or define a deliberate skip in both language halves and report it explicitly per component. Add a test for the chosen policy, including a prebuilt-only successful-pull request with `--push`. Do not interpret the top-level flag, which records input, as proof that anything was published.

### Regression evidence and validation

The r1 source-build push destination remains the single GHCR tag; the prebuilt branch does not alter that path. R1 credential rotation/rollback, listener checks, baseline checks, scanner failure handling, port preservation, acceptance collection and packaging retain their previous code. R2 trace quarantine (private storage for raw browser records), redirect/WebSocket guards, broken-probe detection, recorded egress (outbound traffic) grants and bilingual contract corrections are unchanged from r3. The full suites and the separately executed guard tests pass. This confirms no regression in the verified scope, not new real-store, browser or network evidence.

Observed results in TOON (compact structured text); these are review observations, not canonical manifest data:

```toon
checks[5]{check,result}:
  installer_unittest,"289 run; OK; 10 skipped because system Python lacks pytest"
  guard_tests_venv,"10 run; OK; covers those 10 skips"
  tools_unittest,"77 run; OK"
  independent_prebuilt_matrix,"8 cases; all assertions pass"
  github_ci,"6 checks pass at 6df8c4b"
```

Commands executed from the repository root, each with exit 0:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
python3 -m unittest discover -s tools/tests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

Terminology: PR (proposed change), Manifest (component inventory), Secret (password or key), Trivy (dependency vulnerability scanner), Semgrep (source-code pattern checker), MkDocs (documentation website builder).

CI (automatic checks) passed: Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, and Trivy filesystem scan (report only at M1). These are the six checks attached to the [reviewed PR](https://github.com/RCOSDP/RDM-developer-guide/pull/21). The new review file was also checked directly with `tools.docs_check.check_file` because it is not yet tracked.

Real startup, initialized-store credential rejection, browser acceptance and actual network behavior remain separate stage-two evidence. The ongoing real installation was not touched. No merge authorization is given.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**修正要求: R3-01 は部分解消。残るのは prebuilt の `--push` 契約のみ（P2、動作と文書の不一致）。** 確認済みの R1/R2 修正に新たな後退は見つからなかった。コードと試験のレビューであり、実機導入の受入判定ではない。GitHub 操作は `gh` のみで、approve・merge・close・commit・push はしていない。Docker（アプリケーションの箱を動かす道具）の状態は変えていない。build の追加検査では外部操作を偽 runner（決まった応答を返す関数）に差し替えた。

`9fbb734` から `6df8c4b` のリモート差分は `build.py`、`test_build.py`、r3 記録のみ。r4 作成前に `gh api` で指定 head の blob ハッシュ（ファイル内容の指紋）を取得し、`installer/`・`tools/`・`manifest/`・`docs/` の追跡済み326ファイルすべての一致を確認した。従来の安全対策と文書修正は変わっておらず、組合せによる後退も確認するため installer と tools の試験を再実行した。従来の実機未検証範囲はそのまま残る。

### R3-01: 取得実績の不具合は解消

[build.py](../../installer/grdm_dev/build.py) の164〜171行・213〜229行は、`pull_argv(reference, platform)` に単一プラットフォーム（OS・プロセッサの対象）を渡し、指定対象ごとに1回呼び出す。途中で失敗しても残りを取得し、成功した対象だけを `pulled` に記録する。一つでも非ゼロ終了なら `pull-failed` とし、既存のエラー経路で終了30を返す。`platforms` は要求一覧を保持する。空の一覧でもホスト既定の pull を1回行う。

[test_build.py](../../installer/tests/test_build.py) の252〜274行に `test_prebuilt_multi_platform_pulls_each_and_fails_on_any` が加わった。`linux/arm64,linux/amd64` の arm64 取得を失敗させ、pull が正確に2回、終了30、`pull-failed`、`pulled=linux/amd64` を確認する。arm64 と amd64 はプロセッサの系列名。単一対象の成功・失敗とソースビルドの既存試験も合格した。

さらに独立した一時データで、`push=False` と `push=True` のそれぞれについて全成功・先頭失敗・後続失敗・両方失敗を検査した。8ケースすべてで pull 引数の順序と全内容、終了値、状態、成功対象一覧を照合した。毎回両対象を試し、全成功なら終了0、失敗があれば終了30、両方失敗なら `pulled` は空文字になる。実イメージは取得していない。

### R3-01 の残件

**P2: prebuilt の `--push` は例外を定義せず暗黙に省略される。** prebuilt 部品だけを選択し、`platform="linux/arm64,linux/amd64"`、`push=True` として偽 pull を2回成功させると終了0になる。結果は最上位に `push: true`、部品に `status: prebuilt` と成功した2対象の `pulled` を記録するが、実行するのは `docker pull` の2回だけ。送信処理も、送信を省略したという明示的な結果もない。警告はソースリポジトリからビルドしないことだけを述べる。[build.py](../../installer/grdm_dev/build.py) の213〜230行・244行が該当する。

[SPEC-02](../spec/02_installer_cli.md) の英語80行・日本語272行は、`--push` が複数アーキテクチャの manifest を GHCR（イメージの配布先）へ送ると記載したままで、prebuilt の例外を定義していない。r3 は prebuilt の push を拒否するか明示的に省略し、結果と文書を揃えることも要求した。`6df8c4b` は対象ごとのループを直したが、この要求は未対応。公開を要求した利用者が、何も公開されていない成功結果を受け取り得る。

取得前にこの組合せを拒否するか、意図した省略として両言語の仕様で定義し、部品単位で明示的に記録すること。prebuilt のみを選び pull が成功する `--push` 要求を含め、採用した方針を試験すること。最上位のフラグは入力の記録であり、公開済みの証拠とは解釈しない。

### 回帰確認と検証

r1 のソースビルドの push 先は引き続き単一 GHCR タグであり、prebuilt 分岐はその経路を変更しない。R1 の資格情報更新・巻戻し、待受検査、baseline 検査、スキャン失敗処理、ポート維持、受入結果収集、パッケージ化は従来のコードを保つ。R2 の trace 隔離（ブラウザの生記録の非公開保管）、転送・WebSocket の通信制限、壊れた検査道具の検出、記録された egress（外向き通信）許可、英和の契約修正は r3 から不変。全体試験と別実行した通信制限試験も合格した。確認済み範囲の後退がないことを示し、新たな実ストア・ブラウザ・ネットワークの証拠ではない。

観測結果を TOON（構造化データの短い文字表記）で示す。manifest の正本ではない。

```toon
checks[5]{check,result}:
  installer_unittest,"289件; OK; system Python に pytest がないため10件スキップ"
  guard_tests_venv,"10件; OK; スキップ分を補完"
  tools_unittest,"77件; OK"
  independent_prebuilt_matrix,"8ケース; 全アサーション合格"
  github_ci,"6df8c4b の6チェック成功"
```

リポジトリルートから次を実行し、各終了0を確認した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
python3 -m unittest discover -s tools/tests
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

用語注: PR（変更案）、Manifest（部品の一覧）、Secret（パスワードや鍵）、Trivy（依存部品の弱点を検査する道具）、Semgrep（コードのパターンを検査する道具）、MkDocs（文書をサイトにする道具）。

CI（自動検査）は Build MkDocs Site、Check Links、Manifest validation and private-URL policy、Secret scan (gitleaks)、Semgrep static analysis、Trivy filesystem scan (report only at M1) の6件が成功した。[対象 PR](https://github.com/RCOSDP/RDM-developer-guide/pull/21) に付いた検査である。新規レビューは未追跡のため `tools.docs_check.check_file` でも直接検査した。

実起動、初期化済みストアでの旧資格情報拒否、ブラウザ受入、実ネットワーク挙動は第二段階の証拠として別途必要。進行中の実機導入には触れていない。マージ承認は与えない。

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| REV | Reviewer | 担当レビュワ |
| Prebuilt | Already-built application image | 既に組み立てた実行用イメージ |
| Pull / push | Download / publish an image | イメージの取得／公開 |
| Platform | Operating-system and processor target | OS とプロセッサの対象 |
| Runner | Function executing or simulating a command | コマンドを実行または模擬する関数 |
| Regression | Previously working behavior becomes broken | 動いていた機能が変更で壊れること |
| P2 | Behavior or documentation contract defect | 動作または文書の契約不一致 |
