# REV M1 Skeleton PR Review r3 / REV（担当レビュワ）M1 文書骨格 PR 再レビュー r3

> **Summary:** Approve recommendation for PR (pull request: a proposed change) #19 at 413520e. All three r2 findings are resolved; no regression was found in the r1 corrections within the checks recorded here.
> **概要:** PR（プルリクエスト: 変更提案）#19 の 413520e は approve 推奨。r2 の3件は解消し、記録した検査の範囲では r1 修正の回帰も見つかりませんでした。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** replaying the earlier failing inputs confirms both rejection and safe reporting; a passing normal-input check alone cannot establish either. ／ 過去に失敗した入力の再実行で、拒否と安全な報告の両方を確かめられた。正常入力の合格だけでは両方を保証できない。
- Applies to: PR #19, `feat/m1-skeleton` → `develop`, head `413520e20a98862d7eb5b203bdda1900d49019ac`.
- Related: [Review index](README.md) · [r1](2026-11-05_RDM-developer-guide_M1_Skeleton_PR_r1.md) · [r2](2026-11-05_RDM-developer-guide_M1_Skeleton_PR_r2.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: the owner's integration decision under [ADR-01 §5](../decisions/ADR-01_Integration_Repository_Placement.md#english).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Approve. No remaining technical findings from r2 and no newly identified regression in r1 fixes.** This is an independent review recommendation, not a GitHub approval or merge. The three owner decisions remain open. CI (continuous integration: automatic checks of changes) passes on the exact reviewed head. See the [shared glossary](../reference/REF-01_Glossary.md) for background terms.

### Resolution of r2 findings

1. **R2-01 resolved.** `scan_policy` in `tools/manifest_check.py` scans tracked files without path or extension exclusions. An independent temporary copy detected a runtime-built prohibited address on line 2 in each of seven paths: `site/index.html`, `site/search/search_index.json`, `docs/guides/api/README.legacy.md`, `docs/guides/api/addon/x.py`, `docs/README.md`, `Dockerfile`, and `assets/data.unknownext`. Each direct call returned one finding; the temporary Git repository's command-line policy check rejected the files with exit code (the completion status number) 1. Neither output included the matched address. The real tree reports 451 scanned, 62 skipped as non-UTF-8 (not readable in the expected text encoding), zero over 5 MB, and zero findings. Binary/size skip accounting and detection in former exclusions are covered by tests. Source inspection also shows unreadable files are recorded as skipped; this is a technical read limitation, not a path exemption. The scan does not inspect image pixels.

2. **R2-02 resolved.** `STRUCT_TOP`, `STRUCT_COMPONENT`, `STRUCT_UPSTREAM`, and `STRUCT_PR` declare field types; `validate_structure` runs before value comparisons and TOON (a compact text form of structured data) projection. Integer validation explicitly excludes booleans. The independent copy used the real JSON (structured data written as named fields), with the real TOON unchanged. Each original rejection case—`schema_version: true`, `target_image.M4: true`, `components: "bad"`, and component `role: []`—now reports the relevant MC (manifest-check rule) finding, exits 20, and produces no traceback (an internal error stack). The unchanged copy exits 0. Structural failures do not attempt MC-11 comparison. Added subprocess tests in `tools/tests/test_manifest_check.py` assert these outcomes and additional malformed shapes; all pass.

3. **R2-03 resolved.** SPEC-06 §8 version 0.3 now describes file and fragment checking in both languages. The implementation checks same-file anchors (page bookmarks) and anchors/headings in Markdown targets. Independent negative checks reject a missing file with fragment, a missing same-file anchor, and a missing anchor in an existing Markdown file; an existing `#english` target passes. `tools/docs_check.py` is unchanged from r2.

### Regression check of r1 fixes

| r1 finding | r3 evidence and disposition |
|---|---|
| R1 published private addresses | Resolved: real-tree policy scan has zero findings, and old excluded locations now reject synthetic cases. |
| R2 disabled gitleaks | Resolved: unchanged `[extend] useDefault = true`, four whole-line exceptions, no path exception; hosted secret scan passes. gitleaks is the secret-detection tool. Its synthetic-secret container test was not independently rerun in r3. |
| R3 missing Trivy | Resolved: unchanged pinned filesystem job and report artifact, with explicit M1 report-only scope; hosted job passes. Trivy is the vulnerability/configuration scanner; a green report-only job does not mean zero vulnerabilities. |
| R4 incomplete manifest validation | Resolved for the reviewed defects: 66 checker tests pass, normal JSON/TOON comparison passes, and original malformed-input cases now reject correctly. |
| R5 ZAP scans itself | Still resolved in both language specifications: ZAP (the running-web-application scanner) uses service names and internal ports; host port remapping does not change those targets. Specification unchanged since r2; no deployed installer test was performed. |
| R6 malformed diagram/data blocks | All 34 Mermaid (text-defined diagram) blocks reparse successfully using the existing Mermaid 11.4.1 harness. All 34 Mermaid and 44 TOON blocks are unchanged from r2; the 44 TOON blocks retain r2's independent parse evidence rather than a new external-parser run. |
| R7 documentation checker gaps | Resolved within the disclosed M1 scope: checker tests pass, fragment rejection was independently reproduced, and explicit legacy-format exceptions and SHA-only excerpt checking remain documented. SHA is a revision fingerprint; excerpt checking does not prove equality of arbitrary fields. |
| R8 C4/core/M2 conflict | Still resolved: unchanged JSON/TOON and SPEC-00/02/04 place `y_websocket` in `core` and require C4 in both core/full without skipping. |

### Reproduction and CI evidence

Run these commands from the repository root; all returned 0:

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
python3 -m unittest discover -s tools/tests -v
gh pr checks 19 -R RCOSDP/RDM-developer-guide
```

The unit suite reports **66 tests passed**. Documentation checking reports **46 checked files, 8 exempt files, and 116 nonblocking glossary warnings** before adding this untracked review. The new review is checked separately through `check_file`; tracked-file enumeration does not include it yet.

The independent negative cases ran only in `scratchpad/rev-r3-toxvm83j/` under the task's designated temporary directory. The checker and real manifest files were copied there; synthetic addresses were assembled at runtime and never written to this repository. The four original type mutations were tested separately with unchanged TOON. No production file was mutated for rejection tests.

Using only `gh`, PR (pull request: a proposed change) metadata and both run records confirmed head `413520e20a98862d7eb5b203bdda1900d49019ac`. All six checks pass: MkDocs (the documentation-to-website tool) site build, links, manifest/policy, gitleaks, Semgrep (source-code pattern checking), and Trivy. Both the [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42014695527) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42014695443) conclude `success`. The generated SPEC-06 site page changed along with its source. This review does not newly audit private integration repositories, session-link contents, all image pixels, or deployed installer behavior.

### Remaining owner decisions

- **ADR-01 §5 bootstrap interpretation:** the initial integration-order interpretation remains explicitly proposed and awaiting the owner. This recommendation does not approve that exception; record the owner's decision and align affected normative records if accepted.
- **Claude-Session link retention:** decide whether to retain the session link in public metadata after checking sharing visibility. The link's contents were not inspected or republished.
- **Legacy Semgrep deferral:** explicitly accept or reject the documented M2/M3 deferral of historical sample-code findings. Publication-policy scanning now covers those paths even while Semgrep exceptions remain.

No code correction is requested by r3. The coordinator still needs to integrate this review record and handle the owner decisions; no commit, push, approval, or merge was performed by this reviewer.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Approve。r2 の技術的指摘は残っておらず、r1 修正に新しい回帰も見つかりませんでした。** 独立レビューの推奨であり、GitHub の承認やマージ操作ではありません。所有者の判断3点は未決です。CI（変更を自動検査する仕組み）は、確認対象と同じ head で合格しています。背景用語は[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

### r2 指摘の解消確認

1. **R2-01 解消。** `tools/manifest_check.py` の `scan_policy` はパス・拡張子の除外なく追跡ファイルを検査します。独立した一時コピーで、実行時に組み立てた禁止アドレスを7種類のパスの2行目に配置しました。対象は `site/index.html`、`site/search/search_index.json`、`docs/guides/api/README.legacy.md`、`docs/guides/api/addon/x.py`、`docs/README.md`、`Dockerfile`、`assets/data.unknownext` です。直接呼出しは各1件を検出し、一時 Git リポジトリのコマンドライン検査も終了コード（処理結果を表す数）1で拒否しました。出力に一致アドレスはありません。実ツリーは451ファイル検査、UTF-8（想定する文字の符号化方式）で読めない62ファイルをスキップ、5 MB超は0件、検出0件でした。旧除外領域の検出とバイナリ・サイズ別の集計は試験でも確認しました。コード上は読取不能もスキップとして記録します。これは読取の技術的限界であり、パス例外ではありません。画像の画素は検査しません。

2. **R2-02 解消。** `STRUCT_TOP`、`STRUCT_COMPONENT`、`STRUCT_UPSTREAM`、`STRUCT_PR` が項目の型を宣言し、`validate_structure` が値の比較と TOON（構造化データを短く表す文字形式）の抄録生成に先行します。整数判定は真偽値を明示的に除きます。独立コピーでは実際の JSON（名前付き項目で書く構造化データ）を使用し、TOON は変更していません。元の4ケース `schema_version: true`、`target_image.M4: true`、`components: "bad"`、部品の `role: []` はすべて対応する MC（manifest 検査規則）の指摘を出し、終了20、traceback（内部エラーの呼出し履歴）なしでした。無変更コピーは終了0です。構造不正時は MC-11 比較を実行しません。`tools/tests/test_manifest_check.py` に追加された子プロセス試験もこれらと追加の不正構造を検査し、すべて合格しました。

3. **R2-03 解消。** SPEC-06 §8 の版0.3は、両言語ともファイルとフラグメントの検査を説明しています。実装は同一ファイルのアンカー（ページ内のしおり）とリンク先 Markdown のアンカー・見出しを検査します。独立試験で、存在しないファイルにフラグメントを付けたリンク、同一ファイルの欠落アンカー、存在する Markdown 内の欠落アンカーを拒否し、存在する `#english` は合格しました。`tools/docs_check.py` は r2 から変更されていません。

### r1 修正の回帰確認

| r1 指摘 | r3 の根拠と扱い |
|---|---|
| R1 非公開アドレス掲載 | 解消。実ツリーの方針検出0件。旧除外領域の模擬ケースも拒否。 |
| R2 gitleaks 無効 | 解消。`[extend] useDefault = true`、行全体に限定した4例外、パス例外なしを維持し、hosted 検査も合格。gitleaks は秘密検出ツール。模擬秘密のコンテナ試験は r3 で独立再実行していません。 |
| R3 Trivy 欠落 | 解消。版固定のファイルシステム検査・報告保存と M1 報告のみの範囲は不変で、hosted 検査も合格。Trivy は脆弱性・設定の検査ツールで、報告のみの合格は脆弱性ゼロを意味しません。 |
| R4 manifest 検査不足 | レビュー対象の不具合は解消。66試験と正常 JSON/TOON 比較が合格し、元の不正型を正しく拒否。 |
| R5 ZAP が自身を検査 | 英和仕様上の解消を維持。ZAP（稼働中の Web アプリを検査するツール）はサービス名・内部ポートを使用し、ホスト側ポート変更で対象は変わりません。仕様は r2 から不変。導入済みインストーラーは未検証。 |
| R6 図・データの構文 | 既存 Mermaid 11.4.1 検証器で Mermaid（文字で図を定義する記法）34ブロックが再解析に合格。Mermaid 34件と TOON 44件はすべて r2 と同一。TOON は外部解析器の新規実行ではなく、r2 の独立解析の根拠を引き継ぎます。 |
| R7 文書検査の不足 | 明示された M1 範囲では解消。試験合格とフラグメント拒否の独立再現を確認。旧形式の例外と SHA 限定の抄録検査は明記を維持。SHA は版を識別する指紋で、抄録の任意項目の同一性は保証しません。 |
| R8 C4/core/M2 矛盾 | 解消を維持。JSON/TOON と SPEC-00/02/04 は不変で、`y_websocket` を `core` に含め、core/full とも C4 必須・スキップなし。 |

### 再現と CI の根拠

リポジトリルートで次を実行し、すべて終了0でした。

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
python3 -m unittest discover -s tools/tests -v
gh pr checks 19 -R RCOSDP/RDM-developer-guide
```

単体試験は **66件合格**。新規の未追跡 r3 記録を追加する前の文書検査は **46ファイル検査、8例外、合否を左右しない用語警告116件** でした。新規記録は `check_file` で別途検査し、まだ追跡ファイル件数には含めていません。

独立した拒否試験は、指定一時ディレクトリ配下の `scratchpad/rev-r3-toxvm83j/` のみで行いました。検査プログラムと実 manifest をコピーし、模擬禁止アドレスは実行時に組み立て、このリポジトリには一切書いていません。元の型不正4件は、TOON 無変更で個別に試験しました。拒否試験のために本体ファイルを変更していません。

GitHub の確認には `gh` だけを使い、PR 情報と両 run が head `413520e20a98862d7eb5b203bdda1900d49019ac` を指すと確認しました。MkDocs（文書を Web サイトにする道具）の構築、リンク、manifest/方針、gitleaks、Semgrep（ソースコードの危険な書き方の検査）、Trivy の6件すべてが合格です。[docs run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42014695527) と [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42014695443) はいずれも `success` でした。生成された SPEC-06 のサイトページも元文書とともに変更されています。非公開統合リポジトリ、セッションリンクの内容、画像全画素、導入済みインストーラーは新規監査していません。

### 所有者に残る判断

- **ADR-01 §5 の初回構築解釈:** 提案・所有者承認待ちのままです。この推奨で例外を承認したことにはなりません。所有者の決定を記録し、承認時は関連する規範記録を整合させてください。
- **Claude-Session リンク保持:** 共有範囲を確認したうえで、公開メタデータに保持するか判断してください。リンクの内容は閲覧・再掲載していません。
- **旧資料の Semgrep 延期:** 歴史的サンプルの指摘を M2/M3 へ延期する記録について、明示的に承認または却下してください。Semgrep 例外が残る領域も、公開方針検査は対象に含めます。

r3 はコード修正を要求しません。調整担当にはレビュー記録の取り込みと所有者判断の整理が残ります。レビュワはコミット、push、承認、マージを行っていません。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change awaiting review. | レビューを求める変更提案。 |
| CI | Automatic checks of changes. | 変更の自動検査。 |
| Exit code | The number a program returns on completion. | 処理終了時に返す結果の数。 |
| JSON / TOON | Text formats for structured data. | 構造化データを文字で書く形式。 |
| MC | A named manifest-validation rule. | manifest 検査規則の識別子。 |
| Anchor / fragment | A page bookmark and the link suffix naming it. | ページ内のしおりと、その場所を指すリンク末尾。 |
| SHA | A revision fingerprint. | 版を識別する指紋。 |
| Traceback | An internal error's call history. | 内部エラーの呼出し履歴。 |
| Bootstrap | The first construction before routine updates. | 通常更新を始める前の初回構築。 |
