# REV-PR41 Render stale tags review r1 / 古いビルドタグの render レビュー r1

> **Summary:** Pass: stale records yield manifest pins, a visible warning and a structured report.
> **概要:** 判定は pass。古い記録の代わりに manifest の固定値を使い、警告と構造化報告を出す。

**Jump:** [English](#english) · [日本語](#japanese)

Version / 版: 0.1 — 2026-11-10. **Learned:** A build record is historical evidence and must not override the desired pin. ／ ビルド記録は履歴であり、動かすべき固定値を上書きしてはならない。

**Applies to:** RCOSDP/RDM-developer-guide PR #41, head `4ce0922ada43e7fa3deca2c303acdeded6f1327f`.

**Related:** [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md)

**Used by:** [Review index](README.md), coordinator acceptance decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and inspected behavior

**Pass.** `split_stale_build_tags()` removes a mismatched recorded tag before `services_for_profile()` chooses image references. Built components use `integration_sha` or the merged-upstream pin; overlays compare both base and overlay halves. Matching records remain usable, unpinned components retain the record, deleted components are ignored, and warnings are restricted to rendered components. Failed-build records are excluded by `built_image_tags()`. The tests verify all four osf services and the wiki overlay use current pins and contain no old tag.

`stale_build_tags` reports `component`, `pinned`, `recorded` and `image`; stderr names the mismatch and instructs `grdm-dev build`, then `grdm-dev up`. Render remains exit 0 because install renders before building. SPEC-02 version 0.18 describes this contract consistently in both languages.

The generated service has the exact desired image reference, with no alternate old tag or build fallback. `lifecycle.run_up()` propagates nonzero Compose exit as exit 40 before health success; its unit test covers this. An unavailable exact image fails instead of selecting an old tag. Compose may attempt to pull the exact reference under its default policy; this change does not enforce local-only availability or cryptographic image provenance. Missing-image behavior was checked by code and injected-runner tests, not a live Docker start. No Docker state was changed and no live runtime/.env was accessed; tests create disposable runtime fixtures.

### Suppression assessment

The single-rule `nosemgrep` at `installer/images/unoconv/convert_service.py:111` is justified. `Popen` receives a list, leaves `shell=False`, uses explicit executable configuration and constructs `--fsize` from an integer. Request target is allowlisted by `FORMATS`; extension must fully match `[a-z0-9]{1,10}`; the source path is a generated temporary directory plus `input.<ext>`. Request input cannot select an executable or add shell syntax/filter options. `CONVERT_SOFFICE` and `CONVERT_PRLIMIT` are trusted process configuration, not request values. Minor wording precision: these two executable overrides currently use code defaults rather than being explicitly emitted by compose render; this does not invalidate the suppression. No broad scanner disable was added.

### Verification

Run from `/private/tmp/rev-6914/guide` with the system PATH `python3` (`/opt/homebrew/bin/python3`, Python 3.15.2):

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

```toon
checks[4]{check,result,exit}:
  installer unit tests,539 run and 10 skipped,0
  tools unit tests,93 passed,0
  docs_check,141 checked and 8 exempt and 25 warnings,0
  manifest_check,PASSED,0
```

Logs are `/private/tmp/rev-6914/installer-tests-python3.log`, `tools-tests-python3.log`, `docs-python3.log` and `manifest-python3.log`. An initial `/usr/bin/python3` (macOS Python 3.9.6) attempt ran 414 installer tests with 12 errors and 10 skips, exit 1: existing union annotations in tests require newer Python. That interpreter's tools/docs/manifest checks each exited 0. The requested PATH `python3` run passed; no source was changed to accommodate the old interpreter.

No source changes, commits, pushes, approvals, merges or close actions. This review file is uncommitted. One Japanese PR comment reports pass.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と確認した動作

**Pass。** `split_stale_build_tags()` は `services_for_profile()` がイメージを選ぶ前に、不一致の記録タグを除外する。組み立てる部品は `integration_sha` または統合済み上流の固定値を使い、overlay はベースと overlay の両側を比較する。一致した記録は維持し、固定値のない部品は記録を利用し、削除済み部品は無視する。警告対象は render された部品に限る。失敗したビルド記録は `built_image_tags()` で除外される。テストは osf の4サービスと wiki overlay が現在の固定値を使い、古いタグを含まないことを確認する。

`stale_build_tags` は `component`・`pinned`・`recorded`・`image` を報告する。標準エラーは不一致と `grdm-dev build` の後に `grdm-dev up` を実行する対処を示す。install はビルド前に render するため終了0を維持する。SPEC-02 0.18 はこの契約を英日で一致して説明している。

生成されたサービスは指定した正確なイメージ参照を持ち、古いタグやビルドへの代替経路はない。`lifecycle.run_up()` は Compose の非0終了を、健康確認の成功より前に終了40として伝播し、単体テストも確認している。指定のイメージを取得できなければ古いタグを選ばず失敗する。Compose の既定方針では正確な参照の pull を試す可能性があり、この変更はローカル限定やイメージの暗号学的な来歴を強制しない。イメージ欠落時の挙動はコードと差し替え runner のテストで確認し、実 Docker 起動はしていない。Docker 状態変更や実環境 runtime/.env の参照はなく、テストは使い捨ての runtime fixture を作る。

### 抑制コメントの評価

`installer/images/unoconv/convert_service.py:111` の単一ルール向け `nosemgrep` は妥当。`Popen` はリストを受け取り、`shell=False` のままで、実行ファイルはプロセス設定、`--fsize` は整数から構成する。要求の target は `FORMATS` の許可集合に限定し、拡張子は `[a-z0-9]{1,10}` に完全一致させる。入力パスは生成した一時ディレクトリと `input.<ext>` である。要求から実行ファイルを選択したり、シェル構文・フィルターオプションを追加したりできない。`CONVERT_SOFFICE`・`CONVERT_PRLIMIT` は要求値ではなく信頼するプロセス設定。表現上の軽微な補足として、この2値は現在 compose render が明示設定するのではなくコードの既定値を使うが、抑制の妥当性を損なわない。スキャナー全体の無効化はない。

### 検証

`/private/tmp/rev-6914/guide` で PATH 上のシステム `python3`（`/opt/homebrew/bin/python3`、Python 3.15.2）を使う:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

```toon
checks[4]{check,result,exit}:
  installer 単体テスト,539件実行・10件スキップ,0
  tools 単体テスト,93件成功,0
  docs_check,141件検査・8件免除・25件警告,0
  manifest_check,PASSED,0
```

ログは `/private/tmp/rev-6914/installer-tests-python3.log`、`tools-tests-python3.log`、`docs-python3.log`、`manifest-python3.log`。最初に `/usr/bin/python3`（macOS Python 3.9.6）で試した installer 検査は414件実行・12エラー・10スキップで終了1だった。既存テストの union 型注釈に新しい Python が必要なため。同インタープリターでも tools・docs・manifest の検査は各終了0。指定の PATH `python3` では成功し、古い環境に合わせたソース変更はしていない。

ソース変更・commit・push・承認・merge・close は行っていない。この記録は未コミット。日本語の PR コメント1件で pass を報告する。
