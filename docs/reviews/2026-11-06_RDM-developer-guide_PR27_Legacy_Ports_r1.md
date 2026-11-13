# REV PR #27 Legacy ports review r1 / 旧変更の移植レビュー r1

> **Summary:** The historical changes were ported faithfully, with correct attribution and bilingual summaries. Request changes because the new storage guide makes the mandatory secret scan fail.
> **概要:** 旧変更の移植は原文に忠実で、出典と英和の要約も対応している。新しいストレージ手引きにより必須の秘密情報検査が失敗するため、修正を求める。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** byte-identical historical imports can introduce a new scanner finding even when documentation checks pass. ／ 原文とバイト単位で一致する移植でも、文書検査が通る一方で秘密情報検査の新しい検出を生むことがある。
- Applies to: [PR #27](https://github.com/RCOSDP/RDM-developer-guide/pull/27) (a proposed change), `docs/port-legacy-prs` → `develop`, head (reviewed revision) `b8594c363a990a3b43119a0a29229766e24b4a59`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and required correction

**Request changes — R1 / P2: resolve the failing secret scan before integration.** P2 means a normal-priority correction that blocks acceptance here. This is a written verdict, not a GitHub approval or formal change-request submission.

At `docs/guides/storage-addon/README.legacy.md:224`, the imported `recaptchaSiteKey` value triggers `generic-api-key` in gitleaks (a tool that searches for possible passwords and keys). The [failed job](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42103742174/job/127513010846) scanned 113 commits and found one match. Its downloaded report identifies this exact file, line and reviewed revision; this is introduced by the port, not an unrelated historical finding. [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) keeps secret scanning mandatory at every milestone.

The value is in a browser-facing reCAPTCHA site-key field and appears to be the standard public test value; the scanner finding alone does not establish a leaked credential. Confirm its public-test provenance and add a narrowly anchored, exact-value and field-specific false-positive exception with an explanation, following `.gitleaks.toml`'s existing pattern. Do not exempt the whole guide or all keys. This approach preserves the requested source-byte equality. Rerun the full-history scan and require a passing result; merely replacing the latest text does not remove the detected historical revision. No real secret was otherwise identified in the changed text, diagram sources or inspected screenshot, but an unconditional security PASS is not justified while this check fails.

### Fidelity, attribution and order

All 70 changed paths in the supplied `wt-legacy` worktree (separate checkout) matched the remote PR (proposed change) file blobs (stored file contents) or expected removals. GitHub access used `gh`; no fetch, commit, push, approval, merge, closure or Docker (a tool for running isolated programs) state change was performed.

For [PR #14](https://github.com/RCOSDP/RDM-developer-guide/pull/14), the added and removed hunk lines from `gh pr diff 14` match after mapping old paths to the new guide paths: both surviving legacy guides, both `apps.py` references and both unchanged-content template renames. For [PR #17](https://github.com/RCOSDP/RDM-developer-guide/pull/17), all nine added lines match `gh pr diff 17`: the same Metadata feature-switch command occurs immediately after migration in all three startup variants.

For [PR #18](https://github.com/RCOSDP/RDM-developer-guide/pull/18), the storage legacy text equals the file fetched through the contents API (a service for reading repository files) from `chiku-samugari/RDM-developer-guide` at `f65fac76da40674a15e39163c9f2331572fd1535`: 55,793 bytes, SHA-256 (a file-content fingerprint) `80575425bebff58ce5ffdb9de80c0c12e8ee93de4c78432c1a2047768d0a2ad5`. All 59 storage file changes match the source file list after path mapping, excluding only the newly edited bilingual wrapper. This includes nine additions, six old diagram removals and 43 old sample-code removals, plus the rewritten guide. All nine added assets also equal the source bytes.

Author logins match the source PR metadata: #14 `shun-nakazawa`, #17 `yacchin1205`, #18 `chiku-samugari`. Their original opening dates in UTC are 2023-10-24, 2025-08-09 and 2026-07-12. The attribution date `2026-11-06` is the incorporation date, not the original opening date; the port's timestamp `2026-11-05T20:27:23Z` falls on November 6 in Japan. Both language halves consistently use that incorporation date.

The commit message records #14 → #17 → #18. The resulting files are consistent with that order, and both halves of the storage wrapper explicitly explain that #18 supersedes #14's storage changes while the prefix rule survives in the skeleton and screen-expansion guides. Because this is a single squashed commit, intermediate execution order cannot independently be recovered from history; no stronger claim is made.

### Images, URLs and document checks

The additions are five valid PNG images (a standard raster image format) and four readable Mermaid (text that describes diagrams) sources. PNG signatures, every chunk checksum and the end of each file were valid, with no trailing payload. The four sources contain ordinary flow or sequence diagrams without executable directives. The administration screenshot shows service settings and empty connection fields, not passwords or tokens.

No private repository URL was found in added text. The two contributor plugin repositories are public according to GitHub metadata, and the hosted private-URL policy check passes. A literal private-address example does exist at legacy line 873: an HTTP URL using `192.168.168.167` on port 8081. Lines 30, 39 and 863 explicitly define it as a local loopback alias for development, not an undisclosed internal service. Thus “no private URLs” is satisfied for private repositories or undisclosed endpoints, not as a literal ban on private address space. The retained legacy instructions do modify a host alias; they remain historical material, not a verified 2027 installation procedure.

The four edited wrapper READMEs retain Summary/概要, Jump, language anchors, matching English/Japanese changes, version increments with learned lessons, and inline explanations for the new feature switch, template system and service names. `tools/docs_check.py --all-warnings` reports no warnings for those four files. Existing broader text and glossary conventions were not rewritten. SPEC-06 §8 exempts legacy text and sample assets from the new document format, so preserving the original PNG diagrams is appropriate here.

From the supplied worktree root, run the documentation check; the observed result is PASS:

```sh
python3 tools/docs_check.py --all-warnings
```

The following observed results use TOON (compact structured text); they do not mirror a canonical data file.

```toon
checks[4]{check,result,detail}:
  docs_check,PASS,73 checked / 8 exempt / 197 existing glossary warnings
  edited_wrappers,PASS,zero glossary warnings in the four edited READMEs
  hosted_checks,PARTIAL,seven pass / secret scan fails
  runtime,NOT_RUN,documentation review only / no Docker state changes
```

The storage wrapper already acknowledges its older two-part overview and defers alignment to a later milestone. This review accepts that explicit scope boundary and does not claim to validate the rewritten guide by running its services. The coordinator must resolve R1, record this report in version control and arrange the next review before integration.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と必要な修正

**修正要求 — R1 / P2: 統合前に秘密情報検査の失敗を解消すること。** P2 は通常優先度の修正で、今回は受入を妨げる。これは文書上の判定であり、GitHub の承認や正式な変更要求の操作ではない。

`docs/guides/storage-addon/README.legacy.md:224` の `recaptchaSiteKey` が gitleaks（パスワードや鍵の疑いがある文字列を探す道具）の `generic-api-key` に一致する。[失敗した検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42103742174/job/127513010846)は113件の変更履歴を走査し、1件を検出した。取得した報告はこのファイル・行・レビュー対象の版を指しており、無関係な過去の検出ではなく移植による追加である。[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)では秘密情報検査は全段階で必須となる。

ブラウザに渡す reCAPTCHA のサイトキー欄であり、標準の公開テスト値と考えられる。検出だけで認証情報の漏えいとは断定しない。公開テスト値である出典を確認し、`.gitleaks.toml` の既存方式に沿って、対象フィールドと完全一致する値だけを行全体で限定する誤検出除外を説明付きで追加すること。手引き全体や鍵全般を除外しない。この方法なら原文とのバイト一致を維持できる。全履歴の再検査を成功させる必要があり、最新版の本文だけを置き換えても検出済みの過去の版は消えない。変更本文・図のソース・確認した画面画像に、それ以外の実際の秘密情報は見つからなかったが、この検査が失敗した状態で無条件の安全合格とは判定できない。

### 忠実性・出典・順序

指定された `wt-legacy` 作業ツリー（別の作業用コピー）の変更70パスは、遠隔の変更提案に保存されたファイル内容または削除予定と一致した。GitHub へのアクセスには `gh` を使い、取得用の git fetch、コミット、プッシュ、承認、マージ、終了処理、Docker の状態変更は行っていない。

[PR #14](https://github.com/RCOSDP/RDM-developer-guide/pull/14) は `gh pr diff 14` の追加・削除行を旧パスから新パスへ対応付けて比較した。残存する旧ガイド2件、`apps.py` の参照2件、内容を維持したテンプレート名変更2件が一致した。[PR #17](https://github.com/RCOSDP/RDM-developer-guide/pull/17) は `gh pr diff 17` の追加9行が一致し、3通りすべての起動手順で同じ Metadata 機能スイッチ設定が移行処理の直後に置かれている。

[PR #18](https://github.com/RCOSDP/RDM-developer-guide/pull/18) は contents API（保存されたファイルを読む窓口）で `chiku-samugari/RDM-developer-guide` の `f65fac76da40674a15e39163c9f2331572fd1535` から本文を取得した。移植先の旧本文は55,793バイトで完全一致し、SHA-256（ファイル内容の指紋）は `80575425bebff58ce5ffdb9de80c0c12e8ee93de4c78432c1a2047768d0a2ad5`。新しく編集した英和の案内 README を除き、ストレージ関連59変更の一覧はパス対応後に一致した。内訳は9追加、旧図6削除、旧サンプル43削除、本文1改訂である。追加素材9点も原本とバイト単位で一致した。

作者のログイン名は元の提案情報と一致する。#14 は `shun-nakazawa`、#17 は `yacchin1205`、#18 は `chiku-samugari`。元の提案作成日は UTC でそれぞれ2023-10-24、2025-08-09、2026-07-12である。出典行の `2026-11-06` は元の提案日ではなく取込日を表す。移植の記録時刻 `2026-11-05T20:27:23Z` は日本時間では11月6日であり、英和とも取込日として整合する。

変更記録には #14 → #17 → #18 の順序が記され、最終ファイルもその順序と整合する。ストレージの案内 README は両言語で、#18 が #14 のストレージ変更を置き換えたことと、接頭辞の規則はスケルトン・画面拡張の手引きに残ることを明記している。変更履歴は一つにまとめられているため、中間の実行順そのものを履歴から独立に復元することはできない。

### 画像・URL・文書検査

追加は正しい PNG（標準的な画像形式）5点と、読める Mermaid（文字で図を表す方式）ソース4点。PNG の識別情報・全区画の検査値・終端を確認し、終端後の余分なデータはなかった。ソースは通常の構成図・手順図で、実行指示を含まない。管理画面の画像はサービス設定と空の接続欄を示し、パスワードやトークンを示していない。

追加本文に非公開リポジトリの URL は見つからなかった。作者のプラグイン用リポジトリ2件は GitHub の情報で公開を確認し、遠隔の非公開 URL 方針検査も合格している。ただし旧本文873行には、`192.168.168.167` の8081番ポートを指す HTTP の例がある。30・39・863行は、これを開発用に設定するローカルのループバック別名と説明しており、未知の内部サービスの公開ではない。「非公開 URL なし」は非公開リポジトリ・未公開の接続先という意味では満たすが、私用アドレス空間の文字列が一切ないという意味では満たさない。旧手順にはホストの別名設定が含まれるが、歴史資料であり、検証済みの2027年用導入手順ではない。

編集された案内 README 4件は Summary/概要、Jump、言語アンカー、対応する英和の変更節、学びを記した版更新、新しい機能スイッチ・テンプレート方式・サービス名の説明を維持する。`tools/docs_check.py --all-warnings` ではこの4件への警告はない。既存本文全体の文体・用語注は書き直していない。SPEC-06 §8 は旧本文とサンプル素材を新形式の対象外としているため、原本の PNG 図の保存はこの範囲で妥当である。

指定された作業ツリーのルートで次を実行し、PASS を確認した。

```sh
python3 tools/docs_check.py --all-warnings
```

検査結果は TOON（短い構造化テキスト）で記す。正本のデータファイルの写しではない。

```toon
checks[4]{check,result,detail}:
  docs_check,PASS,73件検査 / 8件対象外 / 既存用語警告197件
  edited_wrappers,PASS,編集した案内README4件の用語警告なし
  hosted_checks,PARTIAL,7件合格 / 秘密情報検査は失敗
  runtime,NOT_RUN,文書レビューのみ / Docker状態変更なし
```

ストレージの案内 README は、概要が旧二部構成のままであり後の段階で整合させると明記している。その範囲設定は受け入れるが、改訂手引きのサービスを実行して検証したとは判断しない。担当調整者には R1 の解消、報告書の履歴への記録、統合前の再レビュー手配が残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Fidelity | Keeping the source change intact when moving it. | 移植時に元の変更を保つこと。 |
| Attribution | Naming the original author and the source change. | 元の作者と変更元を記すこと。 |
| False positive | A harmless value reported as a possible problem. | 問題のない値を問題の疑いとして報告すること。 |
| Site key | A browser-visible identifier for a website integration. | Web サイトの連携を示す、ブラウザに見える識別子。 |
