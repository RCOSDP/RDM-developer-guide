# REV PR24 M3 preparation review r3 / PR24 M3 準備レビュー r3

> **Summary:** R2-01 is resolved and all six automated checks pass. The updated head has a reproducible unit-test failure, so revision is still required.
> **概要:** R2-01 は解消し、自動検査6件は成功した。更新された先端で単体試験の失敗が再現するため、引き続き修正を要求する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a green security gate does not prove the local unit suite passes after integrating other changes. ／ 他の変更を統合した後は、セキュリティ検査の成功だけでローカル単体試験の成功を判断できない。
- Applies to: [PR #24](https://github.com/RCOSDP/RDM-developer-guide/pull/24), `feat/m3-idp-prep`, SHA (commit identity / コミット識別子) `4d1826e467188fe2797fc1ff2d6660112b6883bf`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2](2026-11-06_RDM-developer-guide_PR24_M3_Prep_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary / 共通用語集](../reference/REF-01_Glossary.md).
- Used by: [Upstream status](../status/upstream/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and resolution

**Needs revision: R3-01. R2-01 is resolved.** This is a review judgment, not a GitHub approval. The review targets the helper extraction and requested verification; it does not repeat the completed r2 attribute review or certify live authentication.

Commit `805cabed071cb65bd594638e23597e3dcf21af78` moves `transport_status_must_be` unchanged into `acceptance.netguard`, a module that needs only Python's standard library. The acceptance test and unit test import it normally. The tests retain acceptance of HTTP (web response) statuses 401/403 and rejection of status 200 with embedded 403, ordinary 200, 404, and non-JSON 200. No dynamic `exec` or built-in `compile` call remains in the searched test directories. The four remaining `re.compile` calls in acceptance files build text patterns, not executable Python.

The head changed during review from `19d0461` to `4d1826e` after integration of `develop`. I checked the three helper-related files plus the manifest data, loader and failing test against the exact remote head using the GitHub API (a programmatic way to read GitHub); all six matched byte for byte.

### R3-01 — P2: full unit suite fails on the integrated head

`installer/tests/test_manifest.py:60`, `ManifestLoadTests.test_build_sha_prefers_public_merged_upstream`, assumes WaterButler's build identity equals the merged public upstream identity. The current manifest has `integration_sha`; `installer/grdm_dev/manifest.py:116` correctly prioritizes that explicit identity. Actual: `e9b1ac266374d4f477083b327d9620badfc15ad9`; expected by the stale test: `004f407fefb071f1dc924d09f99916b1d5ea3561`. The failure reproduces both in the complete suite and the manifest-only suite. It arrived with the integrated manifest state and is unrelated to the helper extraction, but prevents reporting this head's unit suite as passing.

Update the test to cover explicit integration priority and public/private fallback with controlled fixtures (test input data), instead of assuming the live manifest lacks an integration identity. Rerun the full suite. Do not change the correct loader priority merely to satisfy the old expectation.

### Validation and limits

Commands ran in the supplied `scratchpad/wt-m3` root:

```sh
rg -n '\b(exec|compile)\s*\(' installer/tests installer/acceptance
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s installer/tests -p test_manifest.py
python3 -m py_compile installer/acceptance/*.py
python3 tools/docs_check.py
gh pr checks 24 --repo RCOSDP/RDM-developer-guide
```

The final full run executed 320 tests with one failure and 10 skips (exit 1). The manifest-only run executed 17 tests with the same one failure (exit 1). Compilation succeeded (exit 0). Documentation validation passed 66 files, exempted 8 and reported 193 warnings before adding this review. The initial 298-test run overlapped the branch update and failed its documentation-wrapper test; a subsequent standalone documentation check passed, so that initial run is not treated as stable-head evidence.

CI (automated checks) passed all six checks on `4d1826e`: links, documentation build, manifest/private-URL policy, secret scan, Semgrep (security pattern checking), and the report-only filesystem scan. Both workflow runs identify that exact head: [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269258) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269059). [Semgrep job](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269059/job/127497448989) passed in 42 seconds. These checks do not erase the independently observed unit failure.

S1–S5 remain skipped acceptance designs; live authentication and container execution were not tested. The r2 M3 follow-ups remain. No implementation edits, commits, pushes, approvals, merges, closures or Docker state changes were made.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と解消

**修正要求: R3-01。R2-01 は解消。** これはレビュー判定で、GitHub の承認操作ではない。補助関数の切り出しと指定検証を対象とし、完了済みの r2 属性レビューの再実施や実認証の保証はしない。

コミット `805cabed071cb65bd594638e23597e3dcf21af78` は `transport_status_must_be` を内容を変えず、Python 標準機能だけに依存する `acceptance.netguard` へ移した。受入試験と単体試験は通常の import で読み込む。HTTP（Web 応答）の401/403を受け入れ、内部に403を持つ200、通常の200、404、JSON形式でない200を拒否する試験を維持した。検索した試験ディレクトリには動的な `exec` や組み込み `compile` の呼出しは残らない。受入ファイルに残る4件の `re.compile` は文字列パターンを作り、Pythonコードを実行しない。

レビュー中に `develop` が統合され、先端が `19d0461` から `4d1826e` に変わった。補助関数関連3ファイルと、manifestデータ・読込処理・失敗した試験を GitHub API（プログラムからGitHubを読む仕組み）で厳密な先端と比較し、6ファイルすべてのバイト一致を確認した。

### R3-01 — P2: 統合後の先端で単体試験全体が不合格

`installer/tests/test_manifest.py:60` の `ManifestLoadTests.test_build_sha_prefers_public_merged_upstream` は、WaterButler のビルド識別子が統合済み公開上流の識別子と同じと仮定する。現在のmanifestには `integration_sha` があり、`installer/grdm_dev/manifest.py:116` は正しくその明示値を優先する。実値は `e9b1ac266374d4f477083b327d9620badfc15ad9`、古い試験の期待値は `004f407fefb071f1dc924d09f99916b1d5ea3561`。全体実行とmanifest試験単独の両方で再現した。統合されたmanifest状態によるもので補助関数の切り出しとは無関係だが、この先端の単体試験を成功とは報告できない。

固定したfixture（試験用入力データ）で、明示された統合識別子の優先と公開・非公開上流への代替選択を検査するよう試験を更新し、全体を再実行する。現在のmanifestに統合識別子がないと仮定しない。古い期待値に合わせて正しい読込優先順位を変更しない。

### 検証と限界

指定された `scratchpad/wt-m3` ルートで英語節のコマンドを実行した。最後の全体実行は320件、失敗1件、スキップ10件（終了1）。manifest単独は17件、同じ失敗1件（終了1）。構文確認は成功（終了0）。文書検査はこのレビュー追加前に66ファイル成功、8除外、193警告。最初の298件の実行はブランチ更新と重なり文書検査のラッパー試験で失敗したが、その後の文書検査単独は成功したため、初回は安定した先端の検証結果として扱わない。

CI（自動検査）は `4d1826e` で6件すべて成功した。対象はリンク、文書ビルド、manifest/非公開URL方針、秘密検査、Semgrep（危険なコードの形を探す検査）、報告専用のファイル検査。[文書の実行記録](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269258)と[セキュリティの実行記録](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269059)の双方で同じ先端を確認した。[Semgrepのジョブ](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42099269059/job/127497448989)は42秒で成功。ただし、独立に観測した単体試験の失敗は残る。

S1〜S5 はスキップ付き受入設計であり、実認証やコンテナの実行は未検証。r2 のM3後続作業は残る。実装変更、コミット、push、承認、マージ、閉鎖、Docker状態変更は行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| SHA | Identity of a saved code revision. | 保存したコードの版を識別する値。 |
| CI | Automatic checks run after a change. | 変更後に自動で行う検査。 |
| HTTP status | The response number sent by a web server. | Webサーバーが返す応答番号。 |
| Fixture | Controlled input used by a test. | 試験に使う固定した入力。 |
| Semgrep | A tool that finds selected patterns in code. | コードから指定のパターンを探す道具。 |
