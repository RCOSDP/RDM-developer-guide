# REV Strict reconstruction review r1 / 厳密再構築レビュー r1

> **Summary:** Eight pull requests (proposed changes, PRs) were independently reviewed against the recorded upstream history. Three need changes; five pass the reconstruction checks.
> **概要:** 8件のプルリクエスト（変更の提案、PR）を上流履歴の記録と独立に照合しました。3件は要修正、5件は再構築検査合格です。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** identical file trees do not prove the required parent history, and reconstruction can drop a previously reviewed test correction. ／ ファイル内容が同一でも必要な親履歴は証明できず、再構築で以前の試験修正が脱落し得ると分かった。
- Applies to: the eight PRs listed in the comparison table; review date 2026-11-05; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [ADR-01 §5](../decisions/ADR-01_Integration_Repository_Placement.md#english) · [SPEC-01](../spec/01_manifest.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Manifest](../../manifest/upstreams.json) · [Previous osf.io review r2](2026-11-05_RDM-osf.io-dev2027_PR1_Public_Develop_Merge_r2.md).
- Used by: [Integration status](../status/README.md), QAE（QA担当）and the owner for the merge decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

Component notes: osf.io (the main web application), waterbutler (the file transfer service), modular-file-renderer (the file preview service), ember-osf-web (the browser interface), cas-overlay (the sign-in service), wiki-frontend (the wiki editor), and y-websocket (the shared-editing connection service). SHA (a saved change’s fingerprint), CI (automatic checks after changes), and QAE (Quality Assurance Engineer / QA担当) follow the [shared glossary](../reference/REF-01_Glossary.md).

**Needs changes overall:** osf.io #2, wiki-frontend #1, and Shibboleth-SP #1. The other five pass the requested history and content checks. These are review conclusions, not GitHub approvals. No merge, approval, close, push, or commit was performed.

All eight were open, created on 2026-11-05, and targeted `integrate/strict-20261105` → `develop`. Their shared title is a Japanese `merge(upstream):` strict-reconstruction subject. All new merge subjects use that scoped prefix and Japanese wording. Inherited upstream subjects are not new commits requiring translation.

A SHA is a fingerprint identifying a saved change. A parent is the preceding saved change; a two-parent merge joins two histories. A tree records the complete file contents. “Parents verified” means exactly two parents, ordered public tip then private tip, both equal to the relevant `sha` fields in the manifest. The fork/start requirement is verified by the merge's first parent, not by chronological order in a comparison result: the first new integration commit is the merge, while the public tip is its starting point.

| Repository / リポジトリ | PR | Parents verified / 親確認 | Files changed vs private tip / 非公開先端との差分 | Verdict / 判定 |
|---|---|---|---|---|
| `RDM-osf.io-dev2027` | #2 | yes | 2: `api/users/views.py`, `api_tests/users/views/test_user_detail.py` | Needs changes |
| `RDM-waterbutler-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | Reconstruction checks pass |
| `RDM-modular-file-renderer-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | Reconstruction checks pass |
| `RDM-ember-osf-web-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | Reconstruction checks pass |
| `RDM-cas-overlay-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | Reconstruction checks pass |
| `RDM-wiki-frontend-dev2027` | #1 | no | 0 (tree SHA equal / ツリー SHA 一致) | Needs changes |
| `RDM-y-websocket-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | Reconstruction checks pass |
| `RDM-Shibboleth-SP-dev2027` | #1 | no | 0 (tree SHA equal / ツリー SHA 一致) | Needs changes |

### Findings

1. **P2 / SR-01 — wiki-frontend #1 does not use either recorded tip as a parent.** Both manifest tips and both tracking branches are `203d32fab60aad8d78e9b743987519252f99b817`. Actual parents are `ed9f9d1c308b66f18c3875c4d761eda41edb1d76` and `90c8f680641616779af2ae6a3b2d224258704e17`. Comparing the recorded private tip to the head reports diverged, ahead 1 / behind 1, with merge base `90c8f680641616779af2ae6a3b2d224258704e17`. The tree is identical, but the recorded tip itself is absent from head ancestry. The body incorrectly claims the current tracking tips were merged. Because public and private tips are identical, an ordinary merge has nothing to join, even with `--no-ff`. Document an owner-accepted identical-tip procedure and correct the PR; do not substitute older ancestors to manufacture compliance or rewrite existing history.

2. **P2 / SR-02 — Shibboleth-SP #1 has no manifest-backed public parent.** The first parent and `upstream/public-main` are `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`; the second parent matches recorded private tip `218b07f4143834278e5289a2c95ee8fe6ff01cf1`. The manifest contains only the private upstream, and ADR-01 §3 explicitly describes this component as private-only. The first parent is an ancestor of the private tip (private ahead 3 / behind 0), and the resulting tree equals private. That proves content preservation, not public provenance. Either establish and record the genuine public upstream with its SHA, or document the private-only bootstrap exception and align the PR body. Do not certify the current generic public-first claim as manifest-verified.

3. **P2 / SR-03 — osf.io #2 drops the prior anonymous-test correction.** The reconstruction reproduces the public tip exactly in the two changed files, including the already-reviewed defect. At public-origin `api_tests/users/views/test_user_detail.py:261`, the API 2.10 request in `test_social_values_old_version_not_logged_in` still supplies `auth=user_one` while expecting 401; the API 2.9 request omits authentication. The prior PR #1 head `ef2be2c815e2432c86d89e0480e77674710f5912` had removed that argument. Restore the one-line correction as a separate history-preserving follow-up and run the targeted test when the environment is available. Keep the strict merge as the audited integration checkpoint; a follow-up fix naturally makes the final head a one-parent commit. PR #1 is closed, as expected.

### History and content evidence

GitHub access used only `gh`: `gh api` PR metadata, commit objects with parents/tree SHAs, tracking refs, and `compare/<private-tip>...<head>`, plus public-to-private and public-to-head comparisons. For osf.io, the reverse private-to-public comparison and exact-head file content were also read. Raw API responses and private patches were kept outside this public repository. The table lists the only changed paths, both independently confirmed as public-origin changes.

- **osf.io:** private is ahead 161 / behind 3 relative to public, so this is the sole genuine divergence among the seven manifest public/private pairs. The three public-only commits are `5f78e37d591986ace4d241c992c1454e8af0a632`, `3243fd7943428cb5e0c1f3a741b354dfa1369bdb`, and `bacfe64fdc002f09df47145fc17f57630772ac82`. The 260 private-side changed files and two public-side changed files do not overlap. Head differs from private in exactly those two public files, with identical blob SHAs (file fingerprints) to public; no additional resolution delta was found. This supports the body's conflict-free merge claim without relying on its uninspected local log. Parsing the test into Python's syntax tree independently confirmed that the two requests have different authentication arguments; this is structural verification, not execution of the application.
- **waterbutler, modular-file-renderer, ember-osf-web, cas-overlay, y-websocket:** private contains public, respectively ahead 18, 1, 2, 1, 1 and behind 0. Each head has the exact ordered manifest parents and the exact private tree SHA; the private-to-head comparison reports zero changed files. No content conflict resolution is present.
- **wiki-frontend:** manifest tips are identical, yet the actual merge joins older ancestors. A zero-file three-dot comparison alone would be insufficient because it compares from the merge base. Direct tree-SHA equality additionally proves content equality, while SR-01 remains a history defect.
- **Shibboleth-SP:** the actual first parent is already contained by private, so there is no divergent content to resolve. There is no manifest public tip for the requested comparison; SR-02 remains unresolved.

The following observed evidence is written in TOON (a compact row format); it records the actual heads and parents, including mismatches, rather than mirroring the manifest.

```toon
reviewed_heads[8]{repo,pr,head,parent1,parent2}:
  RDM-osf.io-dev2027,2,7401f769c308286f443a0aa42b841da61b8617b2,bacfe64fdc002f09df47145fc17f57630772ac82,3f4c9cd32e2e118f42a6b5aacbe2a5ff066a8a38
  RDM-waterbutler-dev2027,1,cf05d525717beaa48df952776b19013f9e47075e,004f407fefb071f1dc924d09f99916b1d5ea3561,722557612d3432fbbcd2b952f70660588dd7b4f4
  RDM-modular-file-renderer-dev2027,1,2743aaecbd2859e8443e0a8fb152851f510f94a2,8990b184e04ec8c9b83d25123187a7a2cfb32909,571b74fa17ea421f72d46f6e2136936c68bd8d73
  RDM-ember-osf-web-dev2027,1,9fe33ca153ab13be886449845cb920a1c7e301ca,13dab2e19ea4e083c91e87c1cb793cb206b8a119,79f4c2719e340ceb438bfbae1bfd356008fb6e91
  RDM-cas-overlay-dev2027,1,2761d6604b97f3cc4f0f69bcef0a8a43a0d514c3,ba95f6f87ddeb84bd990690199cd1d72d7e0c2a0,84d14baa130309e1a2b9447e75dba5e0c0fa0212
  RDM-wiki-frontend-dev2027,1,7f77c9b4e01153acb27baf99a09bb9eb7a584883,ed9f9d1c308b66f18c3875c4d761eda41edb1d76,90c8f680641616779af2ae6a3b2d224258704e17
  RDM-y-websocket-dev2027,1,8c5ef6820839467e15dbdfa2dbffff0af68523df,51eb21d35bd37b197514e6cc67409b7c8a2dc130,e16d995eb362fcc8c53e545ba39a835e5af853b9
  RDM-Shibboleth-SP-dev2027,1,e4b93ea528da9bb03a713ed9cd8ce630b8c09947,7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a,218b07f4143834278e5289a2c95ee8fe6ff01cf1
```

### Metadata, limits, and remaining work

No obvious credentials or private GitHub repository URLs were found in any PR body. All eight bodies do contain the same external AI-session reference. Its access control and contents were not inspected, so “no private URLs of any kind” cannot be certified. The prior osf.io r2 record treats this reference as retained report metadata for owner judgment; no secret exposure is asserted and the URL is not reproduced here. The owner still needs to settle that metadata handling.

Adopted PRs are explicitly deferred to later individual PRs by this assignment and the PR bodies; none is credited as reapplied here. ADR-01 §5 currently places their reapplication before opening the integration PR, so the staged delivery wording should be reconciled before claiming completion of the entire procedure. Five passing reconstruction checks do not establish completed adoption or runtime readiness. Builds, application tests, full secret scanning, and CI results were not validated. Current graph evidence does not prove the historical absence of force-push events. The author reports conflict-free automatic merges; API content checks found no manual resolution delta requiring further review.

Required next steps are SR-01/SR-02 policy and PR corrections, SR-03 test restoration, later adopted-PR reviews, QAE verification, and the owner's merge decision. Requested review comments are posted with the prefix `REV（担当レビュワ, Codex Astra）レビュー r1:`; the local record must be published by the coordinator's normal workflow.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

部品の用語注: osf.io（中心の Web アプリ）、waterbutler（ファイル転送）、modular-file-renderer（ファイルのプレビュー）、ember-osf-web（ブラウザ画面）、cas-overlay（ログイン）、wiki-frontend（Wiki 編集画面）、y-websocket（共同編集の通信）。SHA（保存した変更の指紋）、CI（変更後の自動検査）、QAE（Quality Assurance Engineer / QA担当）は[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

**総合判定は要修正:** osf.io #2、wiki-frontend #1、Shibboleth-SP #1。ほかの5件は依頼された履歴・内容の検査に合格です。これはレビュー判定であり、GitHub の承認操作ではありません。マージ・承認・クローズ・push・commit は実施していません。

8件とも2026-11-05作成で open、対象は `integrate/strict-20261105` → `develop` です。共通題名は日本語の `merge(upstream):` 厳密再構築で、新しいマージコミットの件名もこの接頭辞と日本語を用いています。継承した上流の件名を翻訳する必要はありません。

SHA は保存した変更の指紋、親はその前の変更、二親マージは二つの履歴を結ぶ変更、ツリーは全ファイルの内容を表します。「親確認 yes」は親がちょうど二つで、公開先端、非公開先端の順に manifest の `sha` と一致することです。起点は比較結果の時系列順ではなく、マージの第一親で検証しました。新しい統合コミットはマージ自体で、公開先端はその開始地点です。

| Repository / リポジトリ | PR | Parents verified / 親確認 | Files changed vs private tip / 非公開先端との差分 | Verdict / 判定 |
|---|---|---|---|---|
| `RDM-osf.io-dev2027` | #2 | yes | 2: `api/users/views.py`, `api_tests/users/views/test_user_detail.py` | 要修正 |
| `RDM-waterbutler-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | 再構築検査合格 |
| `RDM-modular-file-renderer-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | 再構築検査合格 |
| `RDM-ember-osf-web-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | 再構築検査合格 |
| `RDM-cas-overlay-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | 再構築検査合格 |
| `RDM-wiki-frontend-dev2027` | #1 | no | 0 (tree SHA equal / ツリー SHA 一致) | 要修正 |
| `RDM-y-websocket-dev2027` | #1 | yes | 0 (tree SHA equal / ツリー SHA 一致) | 再構築検査合格 |
| `RDM-Shibboleth-SP-dev2027` | #1 | no | 0 (tree SHA equal / ツリー SHA 一致) | 要修正 |

### 指摘

1. **P2 / SR-01 — wiki-frontend #1 の親は記録された先端ではありません。** manifest の公開・非公開先端と両追跡ブランチはすべて `203d32fab60aad8d78e9b743987519252f99b817`。実際の親は `ed9f9d1c308b66f18c3875c4d761eda41edb1d76` と `90c8f680641616779af2ae6a3b2d224258704e17` です。非公開先端から head の比較は diverged、ahead 1 / behind 1、共通祖先は `90c8f680641616779af2ae6a3b2d224258704e17` です。内容は同一でも、記録された先端自体が head の祖先にありません。現在の追跡先端をマージしたという本文は不正確です。公開・非公開の先端が同一なら `--no-ff` でも通常マージの対象がありません。同一先端の場合の手順を所有者判断として記録し、PR を修正してください。古い祖先の代用や既存履歴の書換えで適合扱いにしないでください。

2. **P2 / SR-02 — Shibboleth-SP #1 の公開親を manifest で裏付けられません。** 第一親と `upstream/public-main` は `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`、第二親は記録された非公開先端 `218b07f4143834278e5289a2c95ee8fe6ff01cf1` と一致します。manifest は非公開上流だけで、ADR-01 §3 も公開上流なしと記載しています。第一親は非公開先端の祖先（非公開側 ahead 3 / behind 0）で、結果のツリーも非公開先端と一致します。内容保持は証明できますが公開由来は証明できません。本物の公開上流と SHA を確認して記録するか、非公開専用の場合の初回手順を文書化し、PR 本文を整合させてください。

3. **P2 / SR-03 — osf.io #2 で未認証テストの修正が脱落しています。** 変更2ファイルは公開先端と同一で、既知の問題も再現しています。公開由来の `api_tests/users/views/test_user_detail.py:261` にある `test_social_values_old_version_not_logged_in` の API 2.10 要求は `auth=user_one` を渡しながら401を期待します。2.9要求には認証引数がありません。旧 PR #1 の head `ef2be2c815e2432c86d89e0480e77674710f5912` ではこの引数を除いていました。履歴を保持する独立した追加修正で1行を復元し、環境が用意できたら対象試験を実行してください。厳密マージは監査済みの統合地点として保持し、追加修正後の最終 head が一親になることは区別します。PR #1 は予定どおり closed でした。

### 履歴・内容の根拠

GitHub の操作には `gh` のみを使用しました。`gh api` で PR 情報、親とツリー SHA を含むコミット情報、追跡参照、`compare/<private-tip>...<head>`、公開から非公開・head の比較を取得しました。osf.io は非公開から公開の逆向き比較と head 固定のファイルも確認しました。生の応答と非公開パッチは公開リポジトリ外に置きました。表の変更2パスは、いずれも公開由来と独立確認済みです。

- **osf.io:** 公開に対して非公開は ahead 161 / behind 3。manifest に公開・非公開がある7件で唯一、本当に履歴が分岐しています。公開のみの3コミットは `5f78e37d591986ace4d241c992c1454e8af0a632`、`3243fd7943428cb5e0c1f3a741b354dfa1369bdb`、`bacfe64fdc002f09df47145fc17f57630772ac82`。非公開側260ファイルと公開側2ファイルの変更集合は重なりません。非公開先端から head の差分はその公開2ファイルのみで、blob SHA（ファイル内容の指紋）も公開と一致します。追加の競合解消差分はなく、未確認のローカルログに依存せず衝突なしという本文を裏付けます。Python の構文解析でも二つの試験要求の認証引数が異なると確認しました。アプリケーション試験の実行ではありません。
- **waterbutler、modular-file-renderer、ember-osf-web、cas-overlay、y-websocket:** 非公開は公開を含み、順に ahead 18、1、2、1、1、すべて behind 0。head の二親は manifest と順序まで一致し、ツリー SHA は非公開先端と一致、比較の変更ファイル数も0です。内容の競合解消はありません。
- **wiki-frontend:** manifest の両先端は同一なのに、実マージは古い祖先を結んでいます。三点比較は共通祖先からの差分なので0ファイルだけでは不十分です。直接のツリー SHA 一致でも内容同一を確認しましたが、SR-01 の履歴不備は残ります。
- **Shibboleth-SP:** 実際の第一親は非公開に含まれ、内容の分岐はありません。依頼された比較に使える公開先端が manifest にないため SR-02 は未解決です。

[英語節](#english)の TOON（行を短く書くデータ形式）は、8件の実 head と両親の全 SHA を記録しています。manifest の写しではなく、不一致も含む観測値です。

### 本文・検証限界・残作業

どの PR 本文にも明白な資格情報や非公開 GitHub リポジトリの URL は見つかりませんでした。ただし8件すべてに同じ外部 AI セッション参照があります。内容とアクセス制御は未確認のため、あらゆる非公開 URL がないとは保証できません。以前の osf.io r2 記録では、所有者判断用の帳票情報として保持されています。秘密漏えいとは断定せず、URL も転載しません。このメタデータの扱いは所有者判断として残ります。

採用 PR は今回の依頼と本文で後続の個別 PR に延期されており、今回は再適用済みと扱いません。ADR-01 §5 の現行記載は統合 PR 作成前に再適用する順序なので、手順全体の完了を宣言する前に段階的な実施との文言整合が必要です。5件の再構築検査合格は、採用完了や動作準備完了を意味しません。ビルド、アプリ試験、全体の秘密スキャン、CI 結果は検証していません。現在の履歴だけでは過去の force-push 不在も証明できません。作者は自動マージで衝突なしと報告し、API の内容確認でも追加検討が必要な手動解消差分は見つかりませんでした。

残作業は SR-01/SR-02 の規則・PR 修正、SR-03 のテスト修正復元、後続採用 PR のレビュー、QAE（QA担当）の検証、所有者のマージ判断です。指定コメントは `REV（担当レビュワ, Codex Astra）レビュー r1:` で投稿し、ローカル記録の公開は調整担当の通常手順に委ねます。
