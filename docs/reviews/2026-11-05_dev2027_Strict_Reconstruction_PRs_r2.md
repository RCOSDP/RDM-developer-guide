# REV Strict reconstruction review r2 / 厳密再構築レビュー r2

> **Summary:** The restored test preserves the strict merge, and the proposed manifest proves the public Shibboleth-SP parent. The guide still needs a bilingual correction in ADR-01 §3; wiki-frontend develop retains its original tip.
> **概要:** 復元した試験修正は厳密マージを保持し、提案中の manifest は Shibboleth-SP の公開親を裏付けます。ガイドの ADR-01 §3 は英日とも修正が必要です。wiki-frontend の develop は元の先端を保持しています。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** correcting the context and manifest does not correct a contradictory decision paragraph; an unchanged merge can safely receive a separate test fix. ／ 背景と manifest を直しても矛盾する決定節は直らず、既存マージを保ったまま独立した試験修正を追加できると分かった。
- Applies to: the three follow-up pull requests (PRs, proposed changes) and wiki-frontend closure check; REV（担当レビュワ, Codex Astra）, 2026-11-05.
- Related: [Review index](README.md) · [r1](2026-11-05_dev2027_Strict_Reconstruction_PRs_r1.md) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Integration status](../status/README.md), QAE（QA担当）and the owner for subsequent verification and merge decisions.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdicts

A repository stores change history; a branch names a line of that history. A commit is one saved change and its SHA is its fingerprint. A parent is the preceding commit; a merge joins histories. A manifest is the component packing list, an upstream is its original source, and ADR means decision record. See the [shared glossary](../reference/REF-01_Glossary.md).

| Item | Verdict | r1 finding |
|---|---|---|
| RDM-developer-guide #20 | Needs changes: R2-01 | SR-02 documentation correction incomplete |
| RDM-osf.io-dev2027 #2 | Requested history and one-line fix checks pass | SR-03 code correction resolved; execution pending |
| RDM-Shibboleth-SP-dev2027 #1 | Parent/manifest consistency passes against proposed #20 | SR-02 provenance proved; guide correction and landing pending |
| RDM-wiki-frontend-dev2027 #1 | Closure and unchanged develop confirmed | SR-01 avoided by abandoning the PR, not by certifying its history |

These are review verdicts, not GitHub approval actions. GitHub access used only `gh`. No merge, approval, closure, push, commit, deletion, or source change was performed by this reviewer.

### R2-01: ADR-01 §3 still denies the public Shibboleth-SP upstream (P2)

At guide #20 head `04997aa4ce0daba6e3d4cbc6c850f60d6256044c`, the complete three-file change was reviewed. The branch is `fix/manifest-shibboleth-public` → `develop`, and the PR is open. The added public manifest entry passes the SPEC-01 schema checks: bare repository name `RDM-Shibboleth-SP`, branch `main`, kind `public`, tracking branch `upstream/public-main`, status `merged`, full 40-character SHA, and fetched date `2026-11-05`. Public precedes private. JSON formatting and all seven added upstream fields agree with the TOON excerpt (compact text data); its upstream count changes from one to two. Running the existing manifest checker against the exact-head downloaded JSON and TOON returned no findings, including parity checks.

The ADR version advances from 0.3 to 0.4 with bilingual learning and preserved history. Both language halves update **§1 Context**, explaining public y-websocket and Shibboleth-SP, and private-only OASys, rdmcp and aipf_mcp_data_grdm. Contrary to the PR description and requested fix, **§3 Decision is unchanged**. At lines **60 and 150**, it still includes Shibboleth-SP among components with “no public upstream and only this branch.” The adjacent public-branch list also omits `upstream/public-main` for Shibboleth-SP. A reader implementing the decision would omit the newly required mirror.

**Required correction:** in both §3 language halves, explicitly list Shibboleth-SP's public-main mirror and separate it from the three private-only components while retaining its private-main mirror. Keep §1, §3 and the manifest consistent. The generic §5 procedure still assumes a public upstream for every repository; scope it to components that have one, consistent with the newly stated private-only start rule. Re-run documentation and manifest checks after the correction. This is a documentation defect; the added manifest data itself is valid.

The requested `gh pr checks 20 -R RCOSDP/RDM-developer-guide` returned six passes: Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, and Trivy filesystem scan. Trivy is explicitly report-only at M1 (the first delivery checkpoint). CI (automatic checks) cannot detect the contradictory prose here.

### osf.io #2: SR-03 restoration is append-only

The exact current head is `bfcff220b447dd45123a448f75d06aa2eb22ab3c`. Its sole parent is the unchanged strict merge `7401f769c308286f443a0aa42b841da61b8617b2` recorded in r1. That merge still has ordered parents `bacfe64fdc002f09df47145fc17f57630772ac82` (public) and `3f4c9cd32e2e118f42a6b5aacbe2a5ff066a8a38` (private). Identical commit identity preserves the merge's contents, parents and message.

The old-head-to-new-head comparison is ahead 1 / behind 0, with only `bfcff220…`. Its only changed file is `api_tests/users/views/test_user_detail.py`, one deletion and one addition: removal of the authentication argument from the API 2.10 anonymous-request test. The patch is identical to `ef2be2c815e2432c86d89e0480e77674710f5912`; the commit message carries the matching cherry-pick `-x` origin trailer (a record of where the copied change came from). No other code change was introduced. This proves an append-only transition from the r1 checkpoint, not the historical absence of every possible force-push event.

The copied message also retains PR #1's obsolete private-first interpretation. Treat that as inherited historical text, not current policy: PR #2's body and the verified parent graph describe public-first construction. Do not amend the preserved commits to clean up this wording. The targeted application test was not executed in this review; QAE still needs execution evidence when the environment is available. No runtime or CI verdict is inferred for this private PR.

### Shibboleth-SP #1: public parent is established

The head remains `e4b93ea528da9bb03a713ed9cd8ce630b8c09947`. Its first parent is `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`, exactly the added #20 public entry. The second parent is the unchanged private entry `218b07f4143834278e5289a2c95ee8fe6ff01cf1`. GitHub reports `RCOSDP/RDM-Shibboleth-SP` as public with default branch `main`; its current `main` and the integration repository's `upstream/public-main` both equal that first parent. The integration `develop` exists at the private tip. Thus the public source is independently established, not inferred from a tracking-branch name.

SR-02's missing provenance is addressed by the proposed manifest. Full documentation resolution remains dependent on fixing R2-01 and landing #20; this review does not treat an open guide PR as already canonical on develop. The reconstruction commit does not need to be rewritten.

### wiki-frontend: develop remains intact

PR #1 is closed and unmerged. The QAE closing comment says the equal-tip script amended the original tip's message and the resulting branch will remain unused under the no-delete rule. Independently, `develop` is still `203d32fab60aad8d78e9b743987519252f99b817`; the retained `integrate/strict-20261105` branch is `7f77c9b4e01153acb27baf99a09bb9eb7a584883`. Both commits have the same two parents and the same file-tree fingerprint `5d71d0f5ea8bf2092e1bcbd743de986460a207f9`, consistent with the reported amendment. The abandoned PR is not credited as a valid strict reconstruction. Current develop identity is confirmed; no claim is made about every historical ref movement.

### Remaining work

Fix R2-01 and re-review #20 before owner acceptance; execute the targeted osf.io test through QAE. The r1 reservations about later adopted-PR work, ADR-01 §5 ordering, and external session-reference handling remain outside this narrow follow-up. Publish and index this local record through the coordinator's normal workflow. Private repository URLs and raw private patches are not included in this public record. The exact new file was checked directly with the documentation checker (zero errors; glossary warnings remain) and the publication-policy scanner (zero findings). One Japanese r2 comment was posted to each requested PR; comment IDs are 6656821579 (guide #20), 6656822217 (osf.io #2), and 6656822926 (Shibboleth-SP #1).

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

リポジトリは変更履歴の保管場所、ブランチはその履歴の道筋の名前です。コミットは保存した変更、SHA はその指紋、親は直前の変更、マージは履歴を結ぶ操作です。manifest は部品の梱包表、上流は元の取得先、ADR は決定の記録です。[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

| 対象 | 判定 | r1 の指摘 |
|---|---|---|
| RDM-developer-guide #20 | 要修正: R2-01 | SR-02 の文書修正が未完 |
| RDM-osf.io-dev2027 #2 | 依頼された履歴・1行修正の検査合格 | SR-03 のコード修正は解決、実行は未確認 |
| RDM-Shibboleth-SP-dev2027 #1 | 提案中の #20 に対する親・manifest 整合は合格 | SR-02 の公開由来は確認、ガイド修正・統合待ち |
| RDM-wiki-frontend-dev2027 #1 | クローズと develop 保持を確認 | PR の放棄で SR-01 を回避、履歴の適合認定ではない |

レビュー判定であり、GitHub の承認操作ではありません。GitHub へのアクセスは `gh` のみです。レビュワによるマージ・承認・クローズ・push・commit・削除・ソース変更は行っていません。

### R2-01: ADR-01 §3 に「Shibboleth-SP は公開上流なし」が残る（P2）

ガイド #20 の head `04997aa4ce0daba6e3d4cbc6c850f60d6256044c` の全3ファイルを確認しました。`fix/manifest-shibboleth-public` → `develop` の open PR です。追加項目は SPEC-01 の形に適合します。名前は `RDM-Shibboleth-SP`、branch は `main`、kind は `public`、tracking_branch は `upstream/public-main`、status は `merged`、SHA は完全な40文字、取得日は `2026-11-05`。公開項目は非公開項目の前にあります。JSON の書式と追加7フィールドは TOON（データを短く書く形式）と一致し、上流件数も1から2になります。head 固定で取得した JSON/TOON に既存 manifest 検査を実行し、突合を含め指摘0件でした。

ADR は版0.3から0.4へ更新され、英日の学びと過去の版を保持しています。英日とも **§1 背景**で y-websocket と Shibboleth-SP の公開上流、および OASys・rdmcp・aipf_mcp_data_grdm の private 専用を説明しました。しかし依頼と PR 本文が示す **§3 決定は未修正**です。**60行と150行**は今も Shibboleth-SP を「公開の上流がないのでこの一本だけ」に含めています。直前の公開追跡ブランチ一覧も Shibboleth-SP の `upstream/public-main` を欠きます。決定節に従う読者は必要なミラーを作り損ねます。

**必要な修正:** §3 の英日両方に Shibboleth-SP の public-main を明記し、private-main も保持しつつ private 専用3部品と区別してください。§1・§3・manifest を一致させてください。§5 も全リポジトリに公開上流がある前提なので、公開上流を持つ部品への手順であると範囲を明確にし、新たに示した private 専用の開始規則と揃えてください。修正後に文書・manifest 検査を再実行します。追加した manifest データ自体の不備ではなく文書上の不整合です。

指定の `gh pr checks 20 -R RCOSDP/RDM-developer-guide` は全6件成功でした。MkDocs サイト構築、リンク、manifest と非公開 URL 規則、gitleaks、Semgrep、Trivy です。Trivy は M1（最初の開発到達点）では報告のみです。CI（自動検査）の成功ではこの文章の矛盾を検出できません。

### osf.io #2: SR-03 は履歴を保持して復元

現在の head は `bfcff220b447dd45123a448f75d06aa2eb22ab3c`。唯一の親は r1 で記録した厳密マージ `7401f769c308286f443a0aa42b841da61b8617b2` です。その親は公開 `bacfe64fdc002f09df47145fc17f57630772ac82`、非公開 `3f4c9cd32e2e118f42a6b5aacbe2a5ff066a8a38` の順で不変です。コミットの同一性により内容・親・メッセージの保持を確認できます。

旧 head からの比較は ahead 1 / behind 0、追加は `bfcff220…` のみです。変更は `api_tests/users/views/test_user_detail.py` の1行削除・1行追加だけで、API 2.10 の未認証要求から認証引数を外しています。パッチは `ef2be2c815e2432c86d89e0480e77674710f5912` と同一で、メッセージの cherry-pick `-x`（変更のコピー元を残す記録）もその SHA を指します。他のコード変更はありません。r1 地点から追記だけの履歴であることを確認しましたが、過去の全 force push 不在まで証明するものではありません。

コピーされたメッセージには PR #1 当時の古い private 起点解釈も残ります。これは過去から継承した文章であり、現在の規則ではありません。PR #2 本文と親関係は公開起点を示します。文章整理のために保存済みコミットを amend しないでください。対象アプリ試験は今回実行しておらず、環境が用意できた時点で QAE（QA担当）の実行証跡が必要です。この非公開 PR の実行結果や CI 判定を推定していません。

### Shibboleth-SP #1: 公開親を確認

head は `e4b93ea528da9bb03a713ed9cd8ce630b8c09947` のままです。第一親 `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a` は #20 の追加公開項目と完全一致し、第二親 `218b07f4143834278e5289a2c95ee8fe6ff01cf1` も既存の非公開項目と一致します。GitHub は `RCOSDP/RDM-Shibboleth-SP` を公開、既定ブランチを `main` と返しました。その `main` と統合先の `upstream/public-main` は第一親と同一です。統合先 `develop` は非公開先端に存在します。追跡ブランチ名からの推測でなく、公開元そのものを確認しました。

提案 manifest により SR-02 の公開由来不足は解消できます。ただし文書全体の解決は R2-01 の修正と #20 の統合に依存します。open のガイド PR を develop の正本へ反映済みとは扱いません。再構築コミットの書換えは不要です。

### wiki-frontend: develop は元のまま

PR #1 は closed、未マージです。QAE の終了コメントは、同一先端のときスクリプトが元コミットのメッセージを amend し、削除禁止のためブランチを残して使わないと説明しています。独立確認でも `develop` は `203d32fab60aad8d78e9b743987519252f99b817` のまま、残存する `integrate/strict-20261105` は `7f77c9b4e01153acb27baf99a09bb9eb7a584883` です。両コミットは同じ二親と同じファイルツリーの指紋 `5d71d0f5ea8bf2092e1bcbd743de986460a207f9` を持ち、amend の説明と整合します。放棄した PR を適合する厳密再構築とは認定しません。現在の develop の同一性を確認したもので、過去の全参照移動を保証するものではありません。

### 残作業

R2-01 を修正して #20 を再レビュー後、所有者が採否を判断します。QAE による osf.io 対象試験の実行が残ります。後続の採用 PR、ADR-01 §5 の順序、外部セッション参照の扱いについての r1 の留保は、今回の限定した追跡レビューで解決していません。ローカル記録の公開と索引追加は調整担当の通常手順で進めてください。公開記録には非公開リポジトリ URL や生の非公開パッチを含めていません。新規ファイルを文書検査へ直接渡してエラー0件（用語注の警告は残存）、公開規則スキャンで指摘0件でした。指定3 PR に日本語 r2 コメントを各1件投稿しました。コメント ID は 6656821579（ガイド #20）、6656822217（osf.io #2）、6656822926（Shibboleth-SP #1）です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change for review. | レビューする変更の提案。 |
| SHA | Fingerprint of a saved change. | 保存した変更の指紋。 |
| Parent | Commit directly preceding another commit. | ある変更の直前の変更。 |
| Append-only | Add changes without replacing existing history. | 既存履歴を置換せず変更を足すこと。 |
| CI | Checks run automatically after changes. | 変更後の自動検査。 |
| QAE | Quality Assurance Engineer. | QA担当。 |
| TOON | Compact text notation for structured data. | 構造のあるデータを短く書く形式。 |
