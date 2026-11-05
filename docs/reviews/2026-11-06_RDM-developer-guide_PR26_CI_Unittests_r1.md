# REV PR #26 Unit test CI review r1 / 単体テスト CI レビュー r1

> **Summary:** Request changes for one missing private-upstream fallback assertion; the new automated checks pass and their workflow is appropriately restricted.
> **概要:** 非公開上流へのフォールバック検証が一つ欠けるため修正を要請。新しい自動検査は成功し、実行権限も適切。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** an integration pin on a private-only component can hide the loss of its fallback test. ／ 非公開上流だけを持つ部品でも、統合先の固定値があるとフォールバック検証の消失が隠れる。
- Applies to: [PR #26](https://github.com/RCOSDP/RDM-developer-guide/pull/26), `fix/ci-unittests` → `develop`, head `8db7a15c1d8fb4b3be42e47e2e17e9d776eac1f2`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Request changes — one P2 finding.** P2 means a normal-priority correction needed before accepting this review. The PR (proposed code change) fixes the immediate failure introduced by pinned integration commits, but does not fully protect the three-level selection rule it claims to test. This is a review verdict, not a GitHub approval or submitted change-request review.

**R1 / P2 — Restore the private fallback assertion on the synthetic manifest.** At `installer/tests/test_manifest.py:69–70`, OASys (an auxiliary GRDM component) has a nonempty `integration_sha`, so the assertion exercises the integration value. Its private upstream SHA (commit identifier) is also identical to that value. At lines 75–84 the synthetic manifest (a copied component configuration) removes every integration pin, but only waterbutler (the file-transfer component) is asserted. Consequently, an implementation that returns no value for a private-only component without an integration pin passes this test. An in-memory mutation (temporarily replacing behavior without editing files) that entirely removes private fallback survived both the focused test and all 312 installer tests (10 skips, no failures or errors). Add an assertion for `man2.component("OASys").build_sha` against its merged private upstream SHA, after confirming the synthetic integration pin is absent. The mutated implementation must then fail and the correct implementation must pass.

The existing assertions are **not tautological**: expected values come from manifest input fields rather than from the property being tested. Waterbutler's integration, public and private values differ. Separate in-memory mutations that ignore integration pins or prefer private over public both failed the focused test. R1 is missing branch coverage, not a claim that the entire test is meaningless. A small explicit fixture with distinct values could further reduce future dependence on the real manifest, but is not required to resolve R1.

### Workflow review

CI (automatic checks on proposed changes; see the [shared glossary](../reference/REF-01_Glossary.md)) runs for pull requests and pushes to `develop`. Both actions are pinned to full commit identifiers matching `security.yml`: checkout `11d5960a326750d5838078e36cf38b85af677262` and setup-python `a26af69be951a213d495a4c3e4e4022e16d87065`. The workflow grants only `contents: read`, requests no secrets or write permissions, and does not use `pull_request_target`. This is appropriate least privilege for the task.

The matrix (the same checks repeated for different Python versions) covers 3.11, the package's minimum, and 3.12. This is a sensible initial compatibility check, not exhaustive coverage of the unbounded `>=3.11` declaration. `fail-fast: false` preserves both results. Each job runs both suites, installs the package into an isolated environment, and executes `grdm-dev --version`. No blocking workflow issue was found. Tools tests already ran in `security.yml`; this PR adds installer coverage and package installation checks while repeating tools coverage across both versions.

### Evidence and limits

Reviewed both changed files and compared six relevant local files byte-for-byte with contents fetched using `gh` at the stated PR head: the test, implementation, manifest, both workflows and package metadata. Executed the suites from the supplied `wt-ci` worktree root. These commands should finish with `OK`:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
```

Local Python was 3.14.8. The installer suite ran 312 tests with 10 skips and no failures; tools ran 77 with no failures. The skips remain a coverage limitation. No Docker (a tool for running applications in isolated containers) state changes were made. Local package installation was not repeated; the hosted jobs independently provide that evidence.

`gh pr checks 26 --repo RCOSDP/RDM-developer-guide` showed all eight jobs passing, including both new Unit Tests jobs. Run `42099550786` reports the exact head identifier recorded in the header and a successful pull-request event. Its logs show 312 installer tests with 10 skips, 77 tools tests and `grdm-dev 0.1.0` for each matrix entry. GitHub's standard pull-request checkout tests the proposed merge with the base branch; the run's head identity is confirmed, not misrepresented as a head-only checkout. Green checks do not resolve R1.

The author needs to add the missing synthetic OASys assertion and rerun both suites and CI. No source edits, commits, pushes, approvals, merges or closures were performed in this review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**修正要請 — P2 が1件。** P2 はレビュー受入前に必要な通常優先度の修正です。この PR（変更提案）は統合先の固定値による直近の失敗を直しますが、検査すると述べる三段階の選択規則を完全には守れていません。これは文書上の判定であり、GitHub の承認や変更要求レビューの送信ではありません。

**R1 / P2 — 合成マニフェストで private フォールバックの検証を復元してください。** `installer/tests/test_manifest.py:69–70` の OASys（GRDM の補助部品）は `integration_sha` が非空のため、統合先の値を検証しています。非公開上流の SHA（コミットの識別子）も同じ値です。75–84 行では合成マニフェスト（部品構成を複製したデータ）の統合固定値を全て消していますが、検証は waterbutler（ファイル転送を担当する部品）だけです。そのため、統合固定値のない非公開上流だけの部品に値を返さない実装でも成功します。ファイルを書き換えずメモリ内で動作を一時差し替える変異試験で、private フォールバックを丸ごと削除しても当該テストと installer 全312件（10 skip・失敗およびエラーなし）が成功しました。合成側の統合固定値が空であることを確認し、`man2.component("OASys").build_sha` が merged の非公開上流 SHA と等しいことを検証してください。変異実装では失敗し、正しい実装では成功する必要があります。

既存の検証は**同義反復ではありません**。期待値は検証対象のプロパティではなく入力データから得ています。waterbutler の統合先・公開上流・非公開上流の値は異なります。統合固定値を無視する変異と、公開より非公開を優先する変異は、それぞれ当該テストで失敗しました。R1 は一分岐の検査欠落であり、テスト全体が無意味という指摘ではありません。異なる値を持つ小さな専用データを使うと実データへの依存も減らせますが、R1 解消の必須条件ではありません。

### ワークフローの確認

CI（変更提案を自動検査する仕組み。[共通用語集](../reference/REF-01_Glossary.md)参照）は pull request と `develop` への push で動きます。二つの action は完全なコミット識別子に固定され、`security.yml` と一致します。checkout は `11d5960a326750d5838078e36cf38b85af677262`、setup-python は `a26af69be951a213d495a4c3e4e4022e16d87065` です。権限は `contents: read` のみで、秘密情報・書込み権限を要求せず、`pull_request_target` も使いません。必要最小限の権限として適切です。

matrix（Python の版を変えて同じ検査を繰り返す仕組み）は、パッケージの最低要件 3.11 と 3.12 を対象とします。初期の互換性検査として妥当ですが、上限のない `>=3.11` 宣言の全範囲を網羅するものではありません。`fail-fast: false` で両方の結果を残します。各ジョブは両テスト群を実行し、分離環境へパッケージを導入して `grdm-dev --version` を実行します。ワークフローに阻害事項はありません。tools のテストは既に `security.yml` にあり、今回 installer とパッケージ導入の検査が追加され、tools も両バージョンで繰り返されます。

### 証拠と限界

変更2ファイルを確認し、関連するローカル6ファイル（テスト・実装・マニフェスト・両ワークフロー・パッケージ定義）を、指定 head から `gh` で取得した内容とバイト単位で照合しました。指定された `wt-ci` のルートで両テスト群を実行しました。次のコマンドは `OK` で終了することを期待します。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
```

ローカルは Python 3.14.8 でした。installer は312件中10件 skip・失敗なし、tools は77件・失敗なしです。skip 分は検査範囲の限界として残ります。Docker（アプリを分離した箱で動かす道具）の状態変更はありません。ローカルでパッケージ導入は再実行せず、ホスト側の実行結果で確認しました。

`gh pr checks 26 --repo RCOSDP/RDM-developer-guide` で、新設の Unit Tests 2件を含む全8ジョブの成功を確認しました。run `42099550786` の head 識別子はヘッダ記載値と一致し、pull-request イベントが成功しています。ログは各 Python 版で installer 312件・10 skip、tools 77件、`grdm-dev 0.1.0` を示します。GitHub 標準の pull-request checkout はベースとの仮マージを検査します。run が対象 head に属することを確認したのであり、head 単体の checkout と同一視していません。CI 成功だけでは R1 は解消しません。

作者は合成 OASys の検証を追加し、両テスト群と CI を再実行する必要があります。このレビューでソース編集・commit・push・承認・merge・close は行っていません。

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| SHA | Identifier for a particular saved code revision. | 保存されたコードの特定の版を指す識別子。 |
| Integration pin | A recorded revision of the combined code to build. | 組み立て対象の統合コードの版を固定した値。 |
| Fallback | The next choice when the preferred value is absent. | 優先する値がないときに使う次の選択肢。 |
| Mutation test | Temporarily introduce a fault and check whether tests catch it. | わざと一時的に誤りを入れ、検査が見つけるかを確かめる試験。 |
| CI | Automatic checks triggered by code changes. | コード変更をきっかけに実行される自動検査。 |
| Matrix | Repeating checks under several selected conditions. | 条件を変えて同じ検査を繰り返す設定。 |
