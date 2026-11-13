# REV PR24 M3 preparation review r4 / PR24 M3 準備レビュー r4

> **Summary:** R3-01 is resolved. The complete local unit suite and all eight automated checks pass; earlier fixes remain intact.
> **概要:** R3-01 は解消。ローカル単体試験全体と自動検査8件が成功し、過去の修正も維持されている。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** testing selection precedence and running the suite in CI prevents an integration pin from invalidating an obsolete expectation. ／ 選択優先順位の試験と CI での全体実行により、統合先の固定値が古い期待値を無効にする問題を検出できる。
- Applies to: [PR #24](https://github.com/RCOSDP/RDM-developer-guide/pull/24), `feat/m3-idp-prep`, SHA (saved revision identifier / 保存した版の識別子) `76d8bbb55018a83d3681e1c2dccc91fe50a6b9a9`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r3](2026-11-06_RDM-developer-guide_PR24_M3_Prep_r3.md) · [r2](2026-11-06_RDM-developer-guide_PR24_M3_Prep_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary / 共通用語集](../reference/REF-01_Glossary.md).
- Used by: [Upstream status](../status/upstream/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Acceptable for M3 preparation: no blocking findings. R3-01 is resolved; I1–I3 and R2-01 remain resolved.** This is a review judgment, not a GitHub approval. Live authentication remains outside this preparation review.

### Evidence and regression review

[PR #26](https://github.com/RCOSDP/RDM-developer-guide/pull/26) is merged, with merge commit `1a3baba609d2a1b98c259a028cb761418dec160c`. The comparison from r3 head `4d1826e` to the reviewed head changes only the unit-test workflow, `installer/tests/test_manifest.py`, and three review records. No M3 implementation or existing regression test changed in that comparison.

**R3-01:** `test_build_sha_precedence_integration_sha_then_public_then_private` replaces the stale expectation. It checks the explicit integration value, then clears integration values in a copied manifest (component configuration) and checks both the merged public WaterButler identity and the merged private OASys identity. The correct loader priority is unchanged. The copied inputs still depend on the repository manifest; they are not fully independent fixed fixtures (controlled test inputs).

**I1:** The passing contract test still compares all emitted IdP (login provider) names with SP (login receiver) names, checks Japanese identifiers, targeted-identifier raw encoding and decoder types, and verifies generation, mapping and filtering with `uid` excluded. The r2 correction of the Japanese identifier recommendation remains valid; no new external-source audit was needed for these unchanged files.

**I2:** Structural comparison still checks each mock user's credentials and attributes. Visible mock values, the four-value affiliation exception, and success/rejection membership checks remain covered.

**I3 / R2-01:** S2 still requires actual HTTP status (web response number) 401/403. Its normally imported `acceptance.netguard` helper rejects 200 with embedded 403, ordinary 200, 404 and non-JSON 200. Searching the test directories found no dynamic `exec` or built-in `compile`; the four `re.compile` calls only build text patterns. Semgrep (code-pattern security checking) passes.

Eleven local files matched the exact remote head byte for byte using `gh api`: the manifest test, loader, manifest data, unit workflow, compose tests, netguard, S2, hosted IdP template, SP attribute map, authentication-source template and mock-user fixture.

### Validation

Commands ran in the supplied `scratchpad/wt-m3` root. Expected outcomes are `OK` and all checks passing:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
gh pr checks 24 --repo RCOSDP/RDM-developer-guide
gh run view 42101447467 --repo RCOSDP/RDM-developer-guide --json headSha,conclusion,jobs
python3 tools/docs_check.py
```

Observed results use TOON (compact structured text); they are observations, not a canonical data-file excerpt:

```toon
local_installer:
  tests: 320
  failures: 0
  errors: 0
  skipped: 10
  exit: 0
ci:
  passed: 8
  failed: 0
  python_versions: "3.11, 3.12"
```

CI (automated checks) passed documentation build, links, manifest/private-URL policy, secret scan, Semgrep, the report-only filesystem scan, and both Unit tests jobs. [Unit-test run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447467) reports success and the exact reviewed head; both jobs successfully ran installer tests, tools tests and package installation checks. Hosted pull-request checkout checks the proposed merge with the base branch. [Documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447445) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447635) supply the other six checks.

Documentation validation after adding this review passed: 69 files checked, 8 exempt, 199 warnings, exit 0.

### Limits and remaining work

Ten skipped unit tests and the skipped S1–S5 acceptance designs do not demonstrate live authentication. The r2 M3 follow-ups remain: image/version pinning, rendering, secrets, actual attribute exchange, institution login routing and removal of hardening exceptions. No implementation edits, commits, pushes, approvals, merges, closures or Docker state changes were performed. Recording this review in version control and deciding subsequent integration remain with the coordinator.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**M3 準備として受入可能。阻害指摘なし。R3-01 は解消し、I1〜I3／R2-01 も解消を維持。** これはレビュー判定であり、GitHub の承認操作ではない。実認証は今回の準備レビューの対象外。

### 根拠と回帰確認

[PR #26](https://github.com/RCOSDP/RDM-developer-guide/pull/26) は統合済みで、マージコミットは `1a3baba609d2a1b98c259a028cb761418dec160c`。r3 の先端 `4d1826e` と対象先端との差分は、単体試験ワークフロー、`installer/tests/test_manifest.py`、レビュー記録3件のみ。M3 の実装と既存の回帰試験はこの比較で変更されていない。

**R3-01:** 古い期待値は `test_build_sha_precedence_integration_sha_then_public_then_private` に置換された。明示された統合先の値を検査し、複製した manifest（部品構成）で統合先の値を消してから、WaterButler の統合済み公開上流と OASys の統合済み非公開上流の双方を検査する。正しい読込優先順位は変わらない。複製入力は実manifestに依存し、完全に独立した固定fixture（試験用入力）ではない。

**I1:** 成功した契約試験は、IdP（ログイン提供側）と SP（ログイン受信側）の属性名集合、日本語識別子、targeted identifier の raw 符号化と decoder 型を引き続き検査する。識別子生成・名前変換・属性制限と `uid` の除外も確認する。r2 の日本語識別子推奨の訂正は有効であり、変更のないファイルについて外部一次資料の再調査は行っていない。

**I2:** 利用者ごとの認証情報と属性の構造比較を維持する。模擬値と分かる表記、所属語彙の四値限定例外、成功用・拒否用利用者の所属確認も試験されている。

**I3／R2-01:** S2 は実際の HTTP ステータス（Web応答番号）401/403を要求する。通常の import で読み込む `acceptance.netguard` の補助関数は、内部に403を含む200、通常の200、404、JSON形式でない200を拒否する。試験ディレクトリの検索で動的 `exec` や組み込み `compile` はなく、4件の `re.compile` は文字列パターンの生成のみ。Semgrep（危険なコードの形を探す検査）も成功。

ローカル11ファイルを `gh api` で厳密な対象先端とバイト照合した。対象はmanifest試験・読込処理・データ、単体試験ワークフロー、compose試験、netguard、S2、hosted IdPテンプレート、SP属性対応表、認証情報テンプレート、模擬利用者fixture。

### 検証

指定された `scratchpad/wt-m3` ルートで次を実行した。期待結果は `OK` と全検査成功。

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
gh pr checks 24 --repo RCOSDP/RDM-developer-guide
gh run view 42101447467 --repo RCOSDP/RDM-developer-guide --json headSha,conclusion,jobs
python3 tools/docs_check.py
```

実測結果を TOON（短い構造化テキスト）で示す。正本データファイルの写しではない。

```toon
local_installer:
  tests: 320
  failures: 0
  errors: 0
  skipped: 10
  exit: 0
ci:
  passed: 8
  failed: 0
  python_versions: "3.11, 3.12"
```

CI（自動検査）は文書構築、リンク、manifest／非公開URL方針、秘密検査、Semgrep、報告専用ファイル走査、Unit testsの2件がすべて成功。[単体試験の実行記録](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447467) は対象先端と一致し、成功を報告している。両ジョブともinstaller試験、tools試験、パッケージ導入検査を成功した。ホスト側のpull-request checkoutはベースとの仮マージを検査する。[文書実行記録](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447445)と[セキュリティ実行記録](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42101447635)が残り6件の根拠。

この記録追加後の文書検査は成功。69ファイル検査、8除外、199警告、終了0。

### 限界と残作業

単体試験のスキップ10件と、スキップ付きのS1〜S5受入設計は実認証の証明ではない。r2 のM3後続作業であるイメージ／版の固定、設定生成、秘密情報、属性の実送受信、機関ログイン経路、堅牢化例外の除去は残る。実装変更、commit、push、承認、merge、close、Docker状態変更は行っていない。記録の版管理への追加と後続の統合判断は連携調整側に残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| SHA | Identifier of a saved revision. | 保存した版の識別子。 |
| CI | Automatic checks triggered by changes. | 変更をきっかけとする自動検査。 |
| IdP / SP | Login provider / receiver. | ログインの提供側／受信側。 |
| Fixture | Controlled input for a test. | 試験に使う入力データ。 |
| HTTP status | Web server response number. | Webサーバーの応答番号。 |
| TOON | Compact structured text for data. | データを短く表す構造化テキスト。 |
