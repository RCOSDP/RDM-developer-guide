# REV M1 Skeleton PR Review r2 / M1 文書骨格 PR 再レビュー r2

> **Summary:** Request changes on PR #19 at bf320ed. Most r1 corrections are verified, but the publication-policy scan skips published files and the manifest validator accepts invalid types or crashes on malformed input.
> **概要:** PR #19 の bf320ed は修正要求。r1 の修正は大半を確認しましたが、公開ポリシー検査の公開ファイル除外と、manifest 検査の不正型受理・例外終了が残っています。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** green regression tests and workflows can coexist with an uncovered policy path and malformed-input failures; independent rejection cases exposed both. ／ 回帰試験と workflow が合格しても、方針検査の対象漏れと不正入力処理の不具合は残り得る。独立した拒否ケースで両方を確認した。
- Applies to: PR #19, `feat/m1-skeleton` → `develop`, head `bf320ede99936ee4987356b0b3fece1cb8844cda`.
- Related: [Review index](README.md) · [r1](2026-11-05_RDM-developer-guide_M1_Skeleton_PR_r1.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: the owner's merge decision and the author's next correction.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Request changes.** A PR (pull request) is a proposed change awaiting review. This is a recommendation, not a GitHub approval. CI (continuous integration) means automated checks; all current workflows pass, but the rejection cases below do not. P1 blocks merge for ineffective publication protection; P2 is a correctness defect; P3 is a documentation correction. Terms are also explained in the [shared glossary](../reference/REF-01_Glossary.md).

### Remaining findings

1. **R2-01 — P1: the private-URL policy excludes published material.** `tools/manifest_check.py:566–575,603–612` excludes all `site/`, `*.legacy.md`, and nested legacy sample files, then filters remaining files by suffix. The workflow at `.github/workflows/security.yml:110–113` describes an all-tracked-files policy. Temporary-directory tests placed the same synthetic prohibited address in `site/index.html`, `docs/guides/api/README.legacy.md`, and `docs/guides/api/addon/x.py`: `run_policy_scan(root, [path])` returned zero findings for each; the control `docs/README.md` returned one. A formatting or Semgrep legacy exception must not become an exception to public disclosure rules. Gitleaks default secret rules do not enforce private-repository URL policy. Remove these path exemptions from the publication-policy scan and inspect every tracked readable text file, including generated HTML/search data and legacy sources. Add positive detection tests for each previously excluded category. The independent full-tree scan found no current matching address/token; this finding concerns the ineffective gate, not a new demonstrated leak.

2. **R2-02 — P2: schema validation accepts invalid types and breaks its exit-code contract.** `tools/manifest_check.py:169–170` compares `schema_version` with `1` without requiring an integer distinct from boolean; `232–234` checks only the keys of `target_image`, not their values. Against temporary copies of the real JSON and unchanged TOON, `--manifest-only` returned **0** for `schema_version: true`, and separately for `target_image.M4: true`. Both violate SPEC-01's types. Also `components: "bad"` returned **1** with `AttributeError`, and a component `role: []` returned **1** with `TypeError`; invalid manifests must produce findings and exit **20**. Evidence: unguarded set membership at `204`, followed by unconditional TOON comparison at `629–631` and projection of unvalidated objects at `491–500`. Validate scalar and container types before set membership/projection, reject boolean schema versions, validate target-image values, and stop dependent checks when structural validation fails. Add subprocess tests asserting exit 20 with no traceback for malformed JSON shapes. Existing valid-file/TOON checks are substantially improved, but r1 R4 is only partially resolved.

3. **R2-03 — P3: the documented fragment-check behavior is stale.** `docs/spec/06_documentation_conventions.md:96,185` says fragments are not verified, while `tools/docs_check.py:212–249` verifies both same-file and Markdown-target anchors. Update both languages to describe the behavior actually implemented. The implementation is useful; weakening it is unnecessary.

### Disposition of r1 findings

| r1 | Result | Evidence / remaining scope |
|---|---|---|
| R1 private URLs in examples | Resolved for current tree | `manifest/README.md` uses prose; full tracked-text scan without exclusions found zero policy matches. |
| R2 gitleaks rules disabled | Resolved | `[extend] useDefault = true`; four whole-line patterns with `regexTarget = "line"`; no path exemption. Hosted scan reports 70 commits and no leaks. Author reports a synthetic-secret rejection; I did not independently rerun that container test. |
| R3 missing Trivy | Resolved | SHA-pinned filesystem scan and report artifact are present; M1 report-only scope is explicit in SPEC-03. Both Trivy steps and artifact upload succeed. |
| R4 manifest validation | Partially resolved | Required fields, TOON comparison and failure modes are implemented; R2-01 and R2-02 remain. |
| R5 ZAP loopback | Resolved at specification level | SPEC-03 uses Compose service names and container ports, separates host remapping, and updates both languages/diagrams. No running installer is delivered at M1, so runtime connectivity was not tested. |
| R6 Mermaid/TOON syntax | Resolved | All 34 Mermaid blocks and 44 TOON blocks parse independently. |
| R7 docs-check scope | Substantially resolved | All tracked Markdown is classified; legacy/pointer exceptions and the present SHA-only excerpt check are explicit; missing file plus fragment is checked; glossary warnings exist. R2-03 is the remaining wording correction. |
| R8 C4/M2/core conflict | Resolved | `y_websocket` belongs to `core` in SPEC-00/02 and manifest JSON/TOON; SPEC-04 requires C4 in both core/full without skipping. |

TOON is a compact notation for structured data; Mermaid is a notation that turns text into diagrams. The documentation excerpt check intentionally tests SHA membership only, as now disclosed in SPEC-06; it does not prove arbitrary excerpt-field equality. The manifest's standalone TOON comparison checks its prescribed fields.

### Verification and limits

From the repository root, these checks succeeded:

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
python3 -m unittest discover -s tools/tests -v
```

The documentation checker reported 45 checked files, 8 exempt files and 111 nonblocking glossary warnings. All 46 unit tests passed. The new untracked r2 file was separately checked directly through the checker API; it is not included in the tracked-file counts.

The independent parser harness from r1, outside the repository, used Mermaid 11.4.1 and TOON 4.4.0. All 34/44 blocks parsed; the JSON projection and standalone TOON were semantically equal. Negative cases used temporary files only and left the tracked source unchanged. The correction commit changes 69 files, with 5,755 insertions and 523 deletions relative to `1a01c3b`.

The authenticated GitHub connector confirmed the same PR head and successful [documentation workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42013224920) and [security workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42013224919), including all four security jobs. The gitleaks log confirms the Docker invocation scans 70 commits. Local `gh` could not reach the API in this session, so connected GitHub tools supplied remote evidence. Posting the review comment was attempted once but rejected because the tool requires approval while this session uses approval policy `never`; no r2 comment was posted. No new independent audit of all private integration repositories, image pixels, or deployed installer behavior was performed.

### Owner decisions

Fix R2-01/R2-02 before merge and update R2-03 in both languages. The earlier owner decisions remain: ADR-01 §5 bootstrap interpretation, public retention of the Claude session link, and acceptance of the documented legacy Semgrep deferral. The new `core` definition resolves the C4 ambiguity; retain that scope explicitly. M1 Trivy findings are reports, not a claim that vulnerabilities are absent. Regenerate `site/` after documentation changes and rerun rejection tests and CI.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Request changes（修正要求）。** PR（プルリクエスト）はレビューを待つ変更提案です。この判定は推奨であり GitHub の承認ではありません。CI（継続的インテグレーション）は変更を自動検査する仕組みです。現行 workflow は合格していますが、次の拒否ケースが不正です。P1 は公開保護が無効になるマージ阻害事項、P2 は正しさの不具合、P3 は文書の修正です。[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

### 残る指摘

1. **R2-01 — P1: 非公開 URL の方針検査が公開物を除外。** `tools/manifest_check.py:566–575,603–612` は `site/` 全体、`*.legacy.md`、旧サンプルの下位ファイルを除外し、残りも拡張子で絞ります。`.github/workflows/security.yml:110–113` は全追跡ファイルを対象と説明しています。一時ディレクトリで同じ模擬禁止アドレスを `site/index.html`、`docs/guides/api/README.legacy.md`、`docs/guides/api/addon/x.py` に置き、`run_policy_scan(root, [path])` が各0件、対照の `docs/README.md` は1件と再現しました。旧資料の形式・Semgrep 例外を公開禁止事項の例外にしてはいけません。gitleaks の既定秘密規則は非公開リポジトリ URL の公開方針を検査しません。公開方針検査のパス除外をなくし、生成 HTML・検索データ・旧資料も含め、追跡された読み取り可能なテキスト全体を対象にしてください。各除外カテゴリで検出する試験を追加してください。除外なしの独立検索では現在の該当アドレス・token は0件でした。新たな漏洩の実証ではなく、検査が漏洩を拒否できない指摘です。

2. **R2-02 — P2: 不正な型を受理し、終了コード契約も破る。** `tools/manifest_check.py:169–170` は `schema_version` を `1` と比較するだけで真偽値を整数から区別せず、`232–234` は `target_image` のキーだけを見て値の型を検査しません。現行 JSON の一時コピーと変更していない TOON で、`schema_version: true` と、別ケースの `target_image.M4: true` がいずれも `--manifest-only` で **終了0** になりました。ともに SPEC-01 の型に反します。また `components: "bad"` は `AttributeError`、部品の `role: []` は `TypeError` で **終了1** になります。不正 manifest は指摘を出し **終了20** にする契約です。根拠は204行の型未確認の集合所属判定、629–631行の無条件 TOON 比較、491–500行の未検証オブジェクトからの抄録生成です。集合判定・抄録生成の前に型を検査し、真偽値の schema version を拒否し、target-image の値も検証し、構造不正時には依存する検査を止めてください。不正な JSON 構造で traceback なし・終了20を確かめるサブプロセス試験が必要です。正常ファイル・TOON 検査は大幅に改善しましたが r1 R4 は一部未解決です。

3. **R2-03 — P3: フラグメント検査の説明が古い。** `docs/spec/06_documentation_conventions.md:96,185` はフラグメントを検査しないと説明しますが、`tools/docs_check.py:212–249` は同一ファイル・リンク先 Markdown のアンカーを検査しています。両言語を実装に合わせて更新してください。実装は有用なので弱める必要はありません。

### r1 各指摘の扱い

| r1 | 結果 | 根拠・残る範囲 |
|---|---|---|
| R1 禁止例の private URL | 現在のツリーでは解消 | `manifest/README.md` は散文化。除外なしの追跡テキスト検索で方針該当0件。 |
| R2 gitleaks 無効 | 解消 | `[extend] useDefault = true`、行全体に限定した4パターンと `regexTarget = "line"`、パス除外なし。hosted 検査は70コミットで検出なし。作者は模擬秘密の拒否も報告していますが、そのコンテナ試験は独立再実行していません。 |
| R3 Trivy 欠落 | 解消 | SHA 固定の filesystem 検査と報告 artifact があり、SPEC-03 に M1 報告のみの範囲を明示。Trivy の2ステップと artifact アップロードが成功。 |
| R4 manifest 検査 | 一部解消 | 必須項目、TOON 比較、拒否処理は実装。R2-01/R2-02 が残る。 |
| R5 ZAP loopback | 仕様上解消 | SPEC-03 は Compose サービス名・コンテナ側ポートを使用し、ホストの付け替えと分離。英和と図を更新。M1 は稼働インストーラーを提供しないため実接続は未検証。 |
| R6 Mermaid/TOON 構文 | 解消 | Mermaid 34件・TOON 44件が独立解析ですべて合格。 |
| R7 docs-check 範囲 | 大半を解消 | 全追跡 Markdown を分類し、旧資料・誘導の例外と現段階の SHA 限定抄録検査を明記。file#fragment の欠落ファイルを検査し、用語警告もある。説明修正 R2-03 が残る。 |
| R8 C4/M2/core 矛盾 | 解消 | SPEC-00/02 と manifest JSON/TOON が `y_websocket` を `core` に配置。SPEC-04 は core/full 双方で C4 必須・スキップなし。 |

TOON は構造を持つデータの短い記法、Mermaid は文字から図を作る記法です。文書の抄録検査は SPEC-06 に明示されたとおり SHA の存在確認のみであり、任意の項目の一致を証明するものではありません。manifest の独立した TOON 比較では規定された項目を比較します。

### 検証と限界

リポジトリルートで次の検査が成功しました。

```sh
python3 tools/manifest_check.py
python3 tools/docs_check.py
python3 -m unittest discover -s tools/tests -v
```

文書検査は45ファイル検査、8ファイル例外、合否を左右しない用語警告111件でした。単体試験46件はすべて合格です。未追跡の新規 r2 文書はチェッカー API で別途直接確認し、追跡ファイル件数には含まれません。

r1 で用意したリポジトリ外の独立パーサーは Mermaid 11.4.1 と TOON 4.4.0 を使用しました。34/44ブロックすべてが解析でき、JSON の規定抄録と独立 TOON は意味的に一致しました。拒否ケースは一時ファイルのみで行い、追跡ソースを変更していません。修正コミットは `1a01c3b` 比で69ファイル、追加5,755行、削除523行です。

認証済み GitHub コネクターで PR の同一 head と、[docs workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42013224920)・[security workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42013224919) の成功を確認し、security の4ジョブもすべて成功しています。gitleaks ログは Docker 呼び出しと70コミットの検査を確認できます。このセッションのローカル `gh` は API に接続できなかったため、接続済み GitHub ツールでリモート情報を確認しました。コメント投稿は1回試みましたが、ツールが承認を要求し、このセッションは approval policy が `never` のため拒否されました。r2 コメントは未投稿です。非公開統合リポジトリ全体、画像の画素、導入済みインストーラーの動作について新しい独立監査はしていません。

### 所有者の判断事項

マージ前に R2-01/R2-02 を修正し、R2-03 を両言語で直してください。従来の所有者判断事項である ADR-01 §5 の初回構築解釈、Claude セッションリンクの公開保持、旧資料の Semgrep 延期承認は残ります。新しい `core` 定義で C4 の曖昧さは解消したため、この範囲を明示的に維持してください。M1 の Trivy は報告であり、脆弱性ゼロの宣言ではありません。文書修正後は `site/` を再生成し、拒否ケースと CI を再実行してください。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A change proposed for review and merging. | レビューと統合を求める変更提案。 |
| CI | Automated checks of changes. | 変更に対する自動検査。 |
| Schema | The permitted fields and value types of data. | データに許す項目と値の型。 |
| TOON | A compact text notation for structured data. | 構造を持つデータを短く書く文字形式。 |
| Mermaid | Text notation rendered as diagrams. | 図として描画する文字の記法。 |
| SHA | A fingerprint identifying one commit. | 一つのコミットを指す指紋。 |
| Exit code | A number returned when a program finishes. | プログラムが終了時に返す数。 |
| Fragment / anchor | A link suffix and its destination within a page. | ページ内の場所を指すリンク末尾と、その行き先。 |
