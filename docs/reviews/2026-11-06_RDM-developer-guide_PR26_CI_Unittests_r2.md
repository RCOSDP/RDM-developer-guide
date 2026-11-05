# REV PR #26 Unit test CI review r2 / 単体テスト CI レビュー r2

> **Summary:** The missing private fallback check now detects the regression. Accept the revision with no blocking findings.
> **概要:** 欠けていた非公開上流への代替選択の検査が、不具合を検出することを確認。阻害指摘なしで修正を受入可能と判定。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a direct assertion on the private-only component catches loss of the final selection branch. ／ 非公開上流だけの部品を直接検証すると、最後の選択分岐の消失を検出できる。
- Applies to: [PR #26](https://github.com/RCOSDP/RDM-developer-guide/pull/26), `fix/ci-unittests` → `develop`, head (reviewed revision) `55e7c6ad450895c11bad88900afbbb828f00ba18`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR26_CI_Unittests_r1.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Accept — R1 / P2 resolved; no blocking findings.** P2 denotes a normal-priority correction. This is a written review verdict, not a submitted GitHub approval. Scope is the change since r1 and its verification at the stated head.

At `installer/tests/test_manifest.py:81–85`, the synthetic manifest (a copied component configuration) now checks OASys, a private-only component, against its merged private upstream SHA (saved revision identifier). The preceding loop sets every `integration_sha` to `None`, so this exercises fallback (the next choice when the preferred value is absent). The expected value comes from input data, independently of `build_sha`. The additional inequality against waterbutler, the file-transfer component, also passes. The workflow is unchanged from r1.

### Verification

The six local files covering the test, implementation, manifest, test/security workflows and package metadata matched bytes fetched with `gh` at the reviewed head. Tests ran from the supplied `wt-ci` worktree (separate checkout), using Python 3.14.8. Result data uses TOON (compact structured text); these are observed results, not a mirror of a canonical JSON file.

```toon
local_results[4]{check,run,failures,errors,skips}:
  installer,312,0,0,10
  tools,77,0,0,0
  focused_original,1,0,0,0
  focused_private_fallback_removed,1,1,0,0
```

An in-memory mutation test (temporarily introducing a fault without editing source files) replaced only `("public", "private")` with `("public",)` in `Component.build_sha`. Integration selection and public fallback remained intact. The focused test failed at line 84, the new OASys equality, with `None != 'b3860fda51722bbd0faffbe1d49684125e381af3'`. The original implementation passed before and after the temporary replacement. Thus the exact mutation that survived r1 is now detected.

Run the ordinary suites from the repository root; both should finish with `OK`:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
```

CI (automatic checks on proposed changes; [glossary](../reference/REF-01_Glossary.md)) showed all eight checks passing: documentation build, links, manifest/private-URL policy, secret scan, static analysis, filesystem scan, and Unit tests for Python 3.11 and 3.12. The filesystem scan remains report-only at M1. Check with:

```sh
gh pr checks 26 --repo RCOSDP/RDM-developer-guide
gh run view 42100389902 --repo RCOSDP/RDM-developer-guide --json headSha,conclusion,event
```

Run `42100389902` reported `success`, `pull_request`, and the exact reviewed head. Logs for each Python version show 312 installer tests with 10 skips, 77 tools tests, and `grdm-dev 0.1.0` after package installation. The hosted pull-request checkout tests the proposed merge with the base branch, rather than a head-only checkout.

### Limits and remaining work

The ten skipped tests remain unverified, and the synthetic case still depends on real manifest data. Neither limitation blocks resolution of R1. No application source was changed; no commits, pushes, approvals, merges, closures or Docker state changes were performed. The coordinator retains responsibility for recording this report in version control and any later integration action.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**受入可能 — R1 / P2 解消、阻害指摘なし。** P2 は通常優先度の修正です。これは文書上のレビュー判定であり、GitHub の承認送信ではありません。対象は r1 以後の変更と、ヘッダ記載の head（検査対象の版）での検証です。

`installer/tests/test_manifest.py:81–85` で、合成マニフェスト（部品構成を複製したデータ）の OASys（非公開上流だけを持つ部品）を、merged の非公開上流 SHA（保存された版の識別子）と比較しています。直前のループが全 `integration_sha` を `None` にするため、フォールバック（優先値がない場合の次の選択肢）を検証できます。期待値は入力データ由来であり、`build_sha` とは独立しています。waterbutler（ファイル転送を担う部品）との不一致検証も成功しました。ワークフローは r1 から変更されていません。

### 検証

テスト・実装・マニフェスト・テストとセキュリティのワークフロー・パッケージ定義の計6ファイルを、対象 head から `gh` で取得した内容とバイト単位で照合しました。指定 `wt-ci` ワークツリー（独立した作業用コピー）で Python 3.14.8 により実行しました。試験結果は TOON（短い構造化テキスト）で表記します。実測値であり、正本 JSON の写しではありません。

```toon
local_results[4]{check,run,failures,errors,skips}:
  installer,312,0,0,10
  tools,77,0,0,0
  focused_original,1,0,0,0
  focused_private_fallback_removed,1,1,0,0
```

メモリ内の変異試験（ソースを編集せず一時的に誤りを入れる検査）で、`Component.build_sha` の `("public", "private")` だけを `("public",)` に置換しました。統合先選択と公開上流への代替選択は残しています。当該テストは新設の OASys 等値検証である84行目で `None != 'b3860fda51722bbd0faffbe1d49684125e381af3'` により失敗しました。元の実装は差し替えの前後とも成功しました。したがって r1 で見逃した同じ変異を検出できています。

リポジトリのルートで通常の両テスト群を実行します。期待結果は両方 `OK` です。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
```

CI（変更提案の自動検査。[共通用語集](../reference/REF-01_Glossary.md)）は全8件成功でした。文書構築、リンク、マニフェストと非公開 URL 方針、秘密情報走査、静的解析、ファイルシステム走査、Python 3.11 と 3.12 の Unit tests が対象です。ファイルシステム走査は M1 の報告専用のままです。確認コマンドは次のとおりです。

```sh
gh pr checks 26 --repo RCOSDP/RDM-developer-guide
gh run view 42100389902 --repo RCOSDP/RDM-developer-guide --json headSha,conclusion,event
```

run `42100389902` は `success`・`pull_request` で、head も対象の版と一致しました。各 Python 版のログで installer 312件・10 skip、tools 77件、パッケージ導入後の `grdm-dev 0.1.0` を確認しました。ホスト側の pull-request checkout はベースとの仮マージを検査しており、head 単体の checkout ではありません。

### 限界と残作業

skip 10件は未検証で、合成データは引き続き実マニフェストに依存します。いずれも R1 解消の阻害事項ではありません。アプリのソース変更、commit、push、承認、merge、close、Docker の状態変更は行っていません。記録の版管理への追加と、その後の統合判断は連携調整側に残ります。

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| SHA | Identifier of a saved revision. | 保存された版の識別子。 |
| Fallback | Next choice when a preferred value is absent. | 優先値がない場合の次の選択肢。 |
| Mutation test | Deliberately introduce a fault and check detection. | 故意に誤りを入れ、検出を確かめる試験。 |
| CI | Automatic checks triggered by changes. | 変更をきっかけとする自動検査。 |
| TOON | Compact structured text for data. | データを短く表す構造化テキスト。 |
