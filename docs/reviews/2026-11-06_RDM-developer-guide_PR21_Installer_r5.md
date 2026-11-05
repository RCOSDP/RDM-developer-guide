# REV PR21 Installer review r5 / インストーラーレビュー r5

> **Summary:** The remaining prebuilt publication policy finding is resolved at `c5ec1cf`; no regression was found in the previously verified scope. The code/test review passes; real-install acceptance remains separate.
> **概要:** `c5ec1cf` で事前ビルド済みイメージの公開方針に関する残件は解消し、確認済み範囲に後退はない。コード・試験レビューは合格。実機導入の受入は別途必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a publication request can deliberately exclude third-party images when the exception and actual outcome are explicit in both the specification and report. ／ 第三者のイメージを公開要求から意図的に除外するには、仕様と結果の両方で例外と実績を明示すればよいと分かった。
- Applies to: PR (proposed change / 変更案) [#21](https://github.com/RCOSDP/RDM-developer-guide/pull/21), “feat(installer): grdm-dev インストーラー実装（M2 第 1 段）”, head `c5ec1cf2ca66e9e079bd52f151439f602b1f00f9`; REV (reviewer / 担当レビュワ).
- Related: [Review index](README.md) · [r4](2026-11-05_RDM-developer-guide_PR21_Installer_r4.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Installer](../../installer/README.md) · [Status board](../status/README.md) · [Mac Studio run record](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**PASS for code/test review: R3-01 is fully resolved; no blocking findings remain in the reviewed scope.** This verdict does not grant merge authorization or real-install acceptance. GitHub access used `gh` only; no approve, merge, close, commit or push operation was performed. Docker (the tool running application boxes) state was not changed; additional probes used fake runners (functions returning controlled command results).

The remote comparison from `6df8c4b` to `c5ec1cf` changes only the r4 record, [SPEC-02](../spec/02_installer_cli.md), [build.py](../../installer/grdm_dev/build.py) and [test_build.py](../../installer/tests/test_build.py). Before writing r5, all 327 files under `installer/`, `tools/`, `manifest/` and `docs/` in the requested remote tree matched their local file-content fingerprints, checked against `gh api` output.

### Resolution and English/Japanese parity

In `build.py`, lines 212–235, a prebuilt image (an already-built application package) still follows the pull (download) loop once per requested platform (operating-system/processor target). With `--push`, successful pulls report `status: prebuilt-not-pushed` and `pushed: false`, and a warning explains the third-party publication exception. The branch continues before source synchronization or buildx (the image builder), so it cannot re-publish the image to GHCR (the image distribution service). A failed pull still takes precedence: `pull-failed`, successful targets only in `pulled`, and exit 30. Without `--push`, success remains `prebuilt` with `pushed: false`. The top-level `push` field records the request, not publication evidence.

SPEC-02 §3's build row in both languages states the same contract: one pull per requested platform, no re-publication of third-party prebuilt images to `ghcr.io/rcosdp` even with `--push`, and explicit `prebuilt-not-pushed` / `pushed: false` reporting. Both retain `pull-failed` → exit 30 and the source-build publication behavior. The explicit exception resolves the r4 mismatch.

`test_prebuilt_with_push_is_pulled_but_never_pushed` asserts success, no buildx build call, no `ghcr.io` argument, and the exact status/false flag. It does not directly assert that a pull occurred; the existing pull tests and an independent eight-case probe supply that evidence. The probe covered `push=False/True` with both targets succeeding, either target failing, and both failing. It asserted exact ordered pull-only arguments, exit code, status, `pushed: false`, and the successful-target list. All eight cases passed without downloading an image.

### Regression evidence and validation

R1 source-build publication still uses only the GHCR tag. Credential rotation/rollback, listener checks, baseline checks, scanner failure handling, port preservation, acceptance collection and packaging are unchanged. R2 trace quarantine (private storage for raw browser records), redirect/WebSocket guards, broken-probe detection, recorded egress (outbound traffic) grants and prior bilingual corrections are unchanged. R3's per-platform pull accounting remains intact and was exercised with and without `--push`.

Observed results in TOON (compact structured text), not canonical manifest (component inventory) data:

```toon
checks[6]{check,result}:
  installer_unittest,"290 run; OK; 10 skipped because system Python lacks pytest"
  guard_tests_venv,"10 run; OK; covers those 10 skips"
  tools_unittest,"77 run; OK"
  independent_prebuilt_matrix,"8 cases; all assertions pass"
  docs_check,"54 checked; 8 exempt; 127 existing glossary warnings; exit 0"
  github_ci,"6 checks pass at c5ec1cf"
```

Commands executed from the repository root, each with exit 0:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

Terminology: Manifest (component inventory), Secret (password or key), MkDocs (documentation site builder), Semgrep (code-pattern checker), Trivy (dependency vulnerability scanner).

CI (automatic checks) passed: Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, and Trivy filesystem scan (report only at M1). MkDocs builds the documentation site; Secret means a password or key; Semgrep checks code patterns; Trivy checks dependencies for vulnerabilities. The untracked r5 file was additionally checked directly with `tools.docs_check.check_file`.

Real startup, initialized-store rejection of old credentials, browser acceptance and actual network behavior remain separate stage-two evidence. The ongoing installation was not touched. No implementation changes are requested by r5.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**コード・試験レビュー合格: R3-01 は完全解消。確認範囲に阻害指摘は残らない。** マージ権限の付与や実機導入の受入判定ではない。GitHub 操作は `gh` のみで、approve・merge・close・commit・push はしていない。Docker（アプリケーションの箱を動かす道具）の状態は変えていない。追加検査では偽 runner（決まったコマンド結果を返す関数）を使った。

`6df8c4b` から `c5ec1cf` のリモート差分は r4 記録、[SPEC-02](../spec/02_installer_cli.md)、[build.py](../../installer/grdm_dev/build.py)、[test_build.py](../../installer/tests/test_build.py) のみ。r5 作成前に指定リモート版の `installer/`・`tools/`・`manifest/`・`docs/` の327ファイルについて、`gh api` の内容指紋とローカルファイルの一致を確認した。

### 解消内容と英和の一致

`build.py` の212〜235行では、prebuilt image（組み立て済みの実行用パッケージ）を要求された platform（OS・プロセッサの対象）ごとに pull（取得）する。`--push` 時の取得成功は `status: prebuilt-not-pushed` と `pushed: false` を報告し、第三者の成果物を再公開しない旨を警告する。ソース同期や buildx（イメージを組み立てる道具）より前で次の部品へ進むため、GHCR（イメージ配布サービス）への再公開は起こらない。取得失敗があればそちらを優先し、`pull-failed`、成功対象だけの `pulled`、終了30を維持する。`--push` なしの成功は `prebuilt`、`pushed: false`。最上位の `push` は要求を表し、公開実績ではない。

SPEC-02 §3 の build 行は両言語で同じ契約を示す。要求された対象ごとに取得し、`--push` でも第三者の prebuilt を `ghcr.io/rcosdp` へ再公開せず、`prebuilt-not-pushed` / `pushed: false` を明示する。両言語とも `pull-failed` → 終了30とソースビルドの公開動作を維持する。明示的な例外により r4 の不一致は解消した。

`test_prebuilt_with_push_is_pulled_but_never_pushed` は成功、buildx build 呼出しなし、引数に `ghcr.io` なし、正確な status と false を検証する。この新試験単体には取得実行の直接検証がないが、既存の取得試験と独立した8ケースの検査で補った。追加検査は `push=False/True` のそれぞれで両対象成功・片方ずつ失敗・両方失敗を扱う。順序も含めた取得専用の引数、終了値、status、`pushed: false`、成功対象一覧を検証し、8ケースすべて合格した。実イメージは取得していない。

### 後退確認と検証

R1 のソースビルド公開先は GHCR タグのみを維持する。資格情報の更新・巻戻し、待受検査、baseline 検査、スキャン失敗処理、ポート維持、受入結果収集、パッケージ化は不変。R2 の trace 隔離（ブラウザ生記録の非公開保管）、転送・WebSocket の通信制限、壊れた検査道具の検出、記録された egress（外向き通信）許可、以前の英和修正も不変。R3 の対象別取得実績は維持され、`--push` の有無それぞれで検証した。

TOON（構造化データの短い文字表記）による観測結果。manifest（部品一覧）の正本ではない。

```toon
checks[6]{check,result}:
  installer_unittest,"290件; OK; system Python に pytest がないため10件スキップ"
  guard_tests_venv,"10件; OK; スキップ分を補完"
  tools_unittest,"77件; OK"
  independent_prebuilt_matrix,"8ケース; 全アサーション合格"
  docs_check,"54件検査; 8件免除; 既存の用語注警告127件; 終了0"
  github_ci,"c5ec1cf の6チェック成功"
```

リポジトリルートから実行し、各終了0を確認した。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer:installer/tests .venv/bin/python -m unittest test_accept.GuardedRequestTests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
gh pr checks 21 --repo RCOSDP/RDM-developer-guide
```

CI（自動検査）は Build MkDocs Site、Check Links、Manifest validation and private-URL policy、Secret scan (gitleaks)、Semgrep static analysis、Trivy filesystem scan (report only at M1) の6件が成功。MkDocs は文書サイト生成、Secret はパスワードや鍵、Semgrep はコードパターン検査、Trivy は依存部品の弱点検査を指す。未追跡の r5 ファイルは `tools.docs_check.check_file` でも直接検査した。

実起動、初期化済みストアでの旧資格情報拒否、ブラウザ受入、実ネットワーク挙動は第二段階の証拠として別途必要。進行中の導入には触れていない。r5 からの実装修正要求はない。

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| REV | Reviewer | 担当レビュワ |
| Prebuilt | Already-built application image | 組み立て済みの実行用イメージ |
| Pull / push | Download / publish an image | イメージの取得／公開 |
| Platform | Operating-system and processor target | OS とプロセッサの対象 |
| Regression | Previously working behavior becomes broken | 動いていた機能が変更で壊れること |
| Runner | Function executing or simulating a command | コマンドを実行または模擬する関数 |
