# REV PR49 Review records review r2 / レビュー記録公開レビュー r2

> **Summary:** The corrected PR description accurately distinguishes the resolved r6 findings from R6-05. R1-01 is closed; the seven records remain byte-identical to their originals and all eight CI checks are successful.
> **概要:** 訂正後の PR 本文は、r6 の解消済み指摘と R6-05 を正しく区別している。R1-01 は解消し、7件の記録は原本とバイト単位で一致したまま、CI 全8チェックも成功している。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** Correcting a publication summary can close a review finding without altering the archived reviewer's words or the reviewed commit. ／ 公開時の要約を訂正すれば、保存したレビュワの原文や対象コミットを変えずに指摘を解消できる。
- Applies to / 対象: [PR #49](https://github.com/RCOSDP/RDM-developer-guide/pull/49), branch `docs/review-records-2026-11-12c`, head `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71`, base `b81628f2e62b396db32abb8c6e509716c6f3782f`.
- Reviewer / 担当: REV（担当レビュワ, Codex Astra）.
- Review comment / レビューコメント: [6814384330](https://github.com/RCOSDP/RDM-developer-guide/pull/49#issuecomment-6814384330); one r2 comment posted and body verified / r2 コメント1件投稿・本文照合済み。
- Related / 関連: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1 review comment / r1 レビューコメント](https://github.com/RCOSDP/RDM-developer-guide/pull/49#issuecomment-6814237112) · [PR #8 r6 record / PR #8 r6 記録](2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r6.md).
- Used by / 利用先: PR #49 publication decision / PR #49 の公開判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and resolved finding

**PASS. R1-01 / P3 is closed. No unresolved finding remains.** This is a publication-review verdict, not a GitHub approval or merge action.

The PR description now says `要修正（R6-05 / P2 と、当時の CI 未完了。R6-03・R6-04 は解消済み）` for #8 r6. This agrees with the original record at lines 24 and 223: R6-03 was closed by `efee5aa47e`, R6-04 by `71e26d2751`, and R6-05 / P2 remained open while CI was incomplete at that historical cutoff. The previous grouping of resolved findings with outstanding corrections is removed. The only substantive body change since r1 is this row; the body also gained a final newline.

The remaining verdict rows are accurate and unchanged: #8 r7 requires the missing private-security CI job (R7-01); #10 r3 retains the global-admin-guard dependency on #8; #11 r5 and r6 pass; #15 r1 requires changes; #15 r2 passes. The #10 record still requires reintegration and verification after #8 merges. Publishing the historical records does not change their application-review verdicts or limitations.

### Scope, identity and publication checks

The full head and the seven-file PR scope are unchanged from r1. The existing isolated clone was checked against that head, and all seven committed blobs were compared directly with the supplied original bytes again. All match. The diff remains exactly seven added records under `docs/reviews/`, with 1,571 added lines and zero deletions, and no other file changes.

The seven records are osf.io PR #8 r6 and r7, #10 r3, #11 r5 and r6, and #15 r1 and r2. The r1 record, `2026-11-12_RDM-developer-guide_PR49_Review_Records_r1.md`, retains the per-file byte counts, line counts and SHA-256 evidence. Its evidence remains applicable to the unchanged commit.

The corrected PR body introduces no URL, local filesystem path or secret value. The r1 inspection of the unchanged records found no private-repository URL or reviewer-machine absolute path. A fresh Gitleaks scan of all seven additions and the corrected body found zero leaks. The existing r1 local results remain valid for this unchanged head: documentation check passed with 183 checked files, 8 exempt, 38 existing warnings, zero errors and no warning on the additions; manifest/private-URL policy check and whitespace check passed. Those unchanged-head checks were not rerun in r2. The body's reported validation count remains accurate.

### CI evidence and remaining work

At 2026-11-12 04:17 UTC (13:17 JST), the PR still pointed to `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71` and all eight CI checks were completed successfully. CI means GitHub's automated build, test and analysis checks. The same three successful runs were already verified in r1 to identify this exact head.

Runs: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532509), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532477), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532652).

The following are observed results, not a mirror of a canonical data file.

```toon
ci_jobs[8]{job,result}:
  "Build MkDocs Site",success
  "Check Links",success
  "Manifest validation and private-URL policy",success
  "Secret scan (gitleaks)",success
  "Semgrep static analysis",success
  "Trivy filesystem scan (report only at M1)",success
  "Unit tests (installer, tools) (3.11)",success
  "Unit tests (installer, tools) (3.12)",success
```

Trivy retains its report-only role; success is not a separate vulnerability-acceptance decision. No correction or CI work remains for this publication review. No historical application tests were rerun. No merge, approval, closure, push, commit or CI rerun was performed. The authorized GitHub write is exactly one r2 review comment; this bilingual record is saved without committing.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と解消した指摘

**PASS。R1-01 / P3 は解消。未解消の指摘なし。** これは記録公開のレビュー判定であり、GitHub の approve や merge ではない。

PR 本文の #8 r6 行は `要修正（R6-05 / P2 と、当時の CI 未完了。R6-03・R6-04 は解消済み）` へ訂正されている。これは原本の24行目・223行目と一致する。R6-03 は `efee5aa47e`、R6-04 は `71e26d2751` で解消し、当時の確定時点では R6-05 / P2 と未完了の CI が残っていた。解消済み指摘を未解消の修正とまとめた表現は除かれた。r1 以降の本文の実質的な変更はこの行だけであり、末尾には改行も追加されている。

ほかの判定行は正確で変更がない。#8 r7 は非公開セキュリティ CI ジョブ未追加の R7-01 が要修正、#10 r3 は #8 の管理画面全体ガードに依存、#11 r5・r6 は pass、#15 r1 は要修正、#15 r2 は pass である。#10 の記録では #8 のマージ後の再統合・検証も引き続き必要となる。過去の記録を公開しても、各アプリレビューの判定や制約は変わらない。

### 範囲・原本一致・公開適性

完全な head と PR の7ファイルの範囲は r1 から変わっていない。既存の独立クローンがその head を指すことを確認し、コミット内の7ファイルを指定原本のバイト列と再度直接比較した。全件一致した。差分は `docs/reviews/` の7記録追加のみで、1,571行追加、削除0行、ほかのファイル変更なしという状態を維持している。

対象7件は osf.io PR #8 r6・r7、#10 r3、#11 r5・r6、#15 r1・r2 である。r1 記録 `2026-11-12_RDM-developer-guide_PR49_Review_Records_r1.md` は各ファイルのバイト数・行数・SHA-256 の根拠を保持しており、変更のないコミットに引き続き適用できる。

PR 本文の訂正は URL、ローカルファイルシステムのパス、秘密の値を追加していない。変更のない記録7件について、r1 の確認では非公開リポジトリ URL とレビュワ端末の絶対パスは見つからなかった。追加7件と訂正後の本文を Gitleaks で再検査し、検出0件だった。同じ head に対する r1 のローカル検査結果を引き継ぐ。文書検査は183件、除外8件、既存警告38件、エラー0件、新規記録への警告0件で合格し、manifest・非公開 URL 方針と空白差分の検査も合格している。対象 head が不変のため、これらは r2 で再実行していない。本文の検査件数も正しいままである。

### CI の証跡と残作業

2026-11-12 13:17 JST（04:17 UTC）の確認でも PR は `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71` を指し、全8チェックが成功で完了していた。CI は GitHub の自動ビルド・試験・解析を指す。同じ3件の成功 run がこの完全な head を対象とすることは r1 で確認済みである。

実行記録: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532509)、[Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532477)、[Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532652)。[英語節の一覧](#ci-evidence-and-remaining-work)に全8ジョブと成功結果を記録した。これは観測結果であり、正本データファイルの複製ではない。

Trivy は報告のみの検査であり、成功を別途の脆弱性受容判断とは扱わない。今回の記録公開レビューに修正・CI の残作業はない。過去のアプリ試験は再実行していない。merge、approve、close、push、commit、CI 再実行は行っていない。許可された GitHub への書込みは r2 レビューコメント1件だけであり、二言語記録はコミットせず保存する。
