# REV PR49 Review records review r1 / レビュー記録公開レビュー r1

> **Summary:** All seven additions are byte-identical to the supplied originals, and all eight checks passed on the reviewed head. The PR description needs one minor correction: the r6 record closes R6-03 and R6-04 and leaves only R6-05 open.
> **概要:** 追加7件はすべて指定原本とバイト単位で一致し、レビュー対象 head の全8チェックが成功した。PR 本文には軽微な訂正が1件必要である。r6 記録は R6-03・R6-04 を解消済みとし、R6-05 だけを未解消としている。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** A verbatim review archive can be correct while its publication summary confuses resolved findings with the remaining correction. ／ レビュー原文を正しく保存しても、公開時の要約では解消済み指摘と残る修正を混同し得る。
- Applies to / 対象: [PR #49](https://github.com/RCOSDP/RDM-developer-guide/pull/49), branch `docs/review-records-2026-11-12c`, head `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71`, base `b81628f2e62b396db32abb8c6e509716c6f3782f`.
- Reviewer / 担当: REV（担当レビュワ, Codex Astra）.
- Review comment / レビューコメント: [6814237112](https://github.com/RCOSDP/RDM-developer-guide/pull/49#issuecomment-6814237112); one comment posted and body verified / 1件投稿し本文を照合済み。
- Related / 関連: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [PR #8 r6 record / PR #8 r6 記録](2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r6.md).
- Used by / 利用先: PR #49 publication decision / PR #49 の公開判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested for PR-description accuracy: R1-01 / P3. No P1/P2 finding.** The seven committed records pass the publication checks; the requested correction is only to the PR description. P3 denotes a minor documentation correction. This verdict is not a GitHub approval or merge action.

A new isolated clone was inspected at the full head in the header. The merge-base diff contains exactly seven added files under `docs/reviews/`, totaling 1,571 added lines and zero deletions. There are no other added, modified, deleted or renamed files. Each committed blob was directly compared with its designated original as bytes, without text normalization; all seven match. The clone's tracked files remain unchanged.

### R1-01 — P3: distinguish resolved r6 findings in the verdict table

**Location:** PR description, verdict-table row `#8 r6`; supporting record `2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r6.md:24,223`.

The row reads `要修正（R6-03〜R6-05）`. In the final r6 record, R6-03 is already closed by `efee5aa47e`, R6-04 is closed by `71e26d2751`, and only R6-05 / P2 remains open. CI is incomplete at that historical cutoff. Grouping all three identifiers under the outstanding correction misstates the final disposition and can make resolved P1 findings appear open.

Replace that table entry with `要修正（R6-05 / P2、当時の最終 head の CI は未完了。R6-03・R6-04 は解消済み）` or equivalent wording. Preserve the seven original records verbatim. No source-file correction is requested.

The remaining table entries agree with the records: #8 r7 requires R7-01, the missing private-security CI job; #10 r3 retains the global-admin-guard dependency on #8; #11 r5 and r6 pass; #15 r1 requires changes; #15 r2 passes. The #10 dependency also requires reintegration and verification after #8 merges; the short table entry does not replace that original condition. These are historical verdicts at their recorded heads, not new acceptance decisions for those application PRs.

### Publication checks

Inspection of both language sections and URL/path searches found no private-repository URL or reviewer-machine absolute path in the seven additions. The only external URLs in those records are public Django and Django REST framework source links pinned to commits. Repository-relative code paths and endpoint paths are ordinary review evidence. No secret value was detected. Gitleaks scanned all seven additions and the PR description together and reported zero leaks; the manifest/private-URL policy check also passed with zero findings. The PR body contains public tool/session links but no detected private-repository URL, local filesystem path or secret value.

The documentation checker passed with **183 checked files, 8 exempt, 38 existing warnings and zero errors**, with no warning on the new records. The manifest checker and `git diff --check` passed. The PR body's reported count and successful checker results are therefore supported. Historical application tests were not rerun as part of this publication review, and their recorded limits remain in effect.

### Verification evidence

The following measured results are not a mirror of a canonical data file. File names are relative to `docs/reviews/`; each SHA-256 identifies both the committed file and its supplied original.

```toon
files[7]{file,bytes,lines,sha256,byte_identical}:
  2026-11-12_RDM-osf.io-dev2027_PR10_Admin_2FA_r3.md,25028,181,c5339f66b2e199f44b9fe0a528356140afee03aefb2f6644807c591ded005112,true
  2026-11-12_RDM-osf.io-dev2027_PR11_Search_ES8_r5.md,25628,225,e23460b7d014634549bf3086509c86af9e69ed8c44861003ac52e93fff6d78de,true
  2026-11-12_RDM-osf.io-dev2027_PR11_Search_ES8_r6.md,22551,227,9e3fe28010ebc1a7a37742f68b7febcfaab979fbc6c791b0bca5c95d879b0ec8,true
  2026-11-12_RDM-osf.io-dev2027_PR15_Runserver_Threading_r1.md,23790,155,dcaff2e1139d11e9544b46de3dec9879b15bd63d623cd7ba4fcb0071ac43e32f,true
  2026-11-12_RDM-osf.io-dev2027_PR15_Runserver_Threading_r2.md,21359,153,e8b825341705e04175e62b62a6949694041aadbf974082c2e9fc0c1e732186d9,true
  2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r6.md,74978,411,df686bb24f3d67394fea44ea9903aed3078a6b1d6732f422b17efa2006c986bb,true
  2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r7.md,31866,219,93368bf0fb584cc076c57e2f5a85cd27196c6e5834dacc87daad87c0baaf0a6a,true
```

At 2026-11-12 04:08 UTC (13:08 JST), the final PR snapshot retained the same head, seven-file scope and description. All three workflow runs had completed successfully, and each run's metadata identified `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71`. All eight CI jobs, meaning GitHub's automated checks, succeeded. CI was initially running and its completion was verified before this verdict.

Runs: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532509), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532477), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532652).

```toon
ci_jobs[8]{run,job_id,job,result}:
  43152532509,130964860707,"Build MkDocs Site",success
  43152532509,130964860961,"Check Links",success
  43152532477,130964861270,"Manifest validation and private-URL policy",success
  43152532477,130964860993,"Secret scan (gitleaks)",success
  43152532477,130964860979,"Semgrep static analysis",success
  43152532477,130964860737,"Trivy filesystem scan (report only at M1)",success
  43152532652,130964861094,"Unit tests (installer, tools) (3.11)",success
  43152532652,130964861252,"Unit tests (installer, tools) (3.12)",success
```

Trivy remains report-only; its successful job is not a separate vulnerability-acceptance decision. The only remaining requested action is correcting the r6 summary in the PR description. No merge, approval, closure, push, commit or CI rerun was performed. The authorized GitHub write is one review comment; the bilingual record remains uncommitted.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**PR 本文の正確性について要修正: R1-01 / P3。P1/P2 の指摘なし。** コミット内の7記録は公開検査に合格し、訂正対象は PR 本文だけである。P3 は軽微な文書訂正を表す。この判定は GitHub 上の approve や merge ではない。

新規の独立クローンで、ヘッダの完全な head を確認した。共通祖先との差分は `docs/reviews/` の7ファイル追加のみで、合計1,571行追加、削除0行である。ほかの追加・変更・削除・改名はない。コミット内の各ファイルと指定原本を、文字の正規化をせずバイト列で直接比較し、7件すべてが一致した。クローンの追跡対象ファイルは未変更である。

### R1-01 — P3: 判定表で r6 の解消済み指摘を区別する

**場所:** PR 本文の判定表 `#8 r6` 行。根拠は `2026-11-12_RDM-osf.io-dev2027_PR8_Mandatory_Auth_r6.md:24,223`。

表は `要修正（R6-03〜R6-05）` と記載している。確定した r6 記録では、R6-03 は `efee5aa47e`、R6-04 は `71e26d2751` で解消済みであり、未解消は R6-05 / P2 だけである。当時の確定時点では CI も未完了だった。3件をまとめて要修正の理由にすると、最終状態と食い違い、解消済みの P1 が未解消と読めてしまう。

表の記述を `要修正（R6-05 / P2、当時の最終 head の CI は未完了。R6-03・R6-04 は解消済み）` または同等の表現へ訂正する。7件の原本はそのまま保持する。ソースファイルの修正は求めない。

ほかの判定表は原本と一致する。#8 r7 は非公開セキュリティ CI ジョブ未追加の R7-01 が要修正、#10 r3 は #8 の管理画面全体ガードに依存、#11 r5・r6 は pass、#15 r1 は要修正、#15 r2 は pass である。#10 は #8 のマージ後にも再統合と検証が必要であり、表の短い説明は原本の条件を置き換えない。これらは各記録の head に対する過去の判定であり、対象アプリ PR の新たな受入判定ではない。

### 公開適性の確認

両言語節の内容と URL・パスの検索から、追加7件に非公開リポジトリ URL やレビュワ端末の絶対パスは見つからなかった。記録にある外部 URL は、コミットを固定した公開 Django・Django REST framework ソースへのリンクだけである。リポジトリ相対のコードパスとエンドポイントのパスは通常のレビュー根拠である。秘密の値は検出されなかった。Gitleaks で追加7件と PR 本文を一緒に検査し、検出0件だった。manifest・非公開 URL 方針の検査も指摘0件で合格した。PR 本文には公開のツール・セッションリンクがあるが、非公開リポジトリ URL、ローカルファイルシステムのパス、秘密の値は検出されなかった。

文書検査は **183件、除外8件、既存警告38件、エラー0件** で合格し、追加記録への警告もなかった。manifest 検査と `git diff --check` も合格した。したがって PR 本文の検査件数と成功結果は裏付けられる。今回の公開レビューでは過去のアプリ試験を再実行せず、元の記録にある制約を維持する。

### 検証の証跡

[英語節の検証一覧](#verification-evidence)は今回の実測であり、正本データファイルの複製ではない。ファイル名は `docs/reviews/` からの相対名で、各 SHA-256 はコミット内のファイルと指定原本の両方に共通する。全7件のバイト数・行数・SHA-256・一致結果、および全8ジョブの実行番号・ジョブ番号・成功結果を同一覧に記録した。

2026-11-12 13:08 JST（04:08 UTC）の最終 PR 確認でも、head・7ファイルの範囲・本文は変わっていなかった。全3ワークフローが成功で完了し、それぞれの実行情報が `cab89dd3eb56a2aacaf7ec903c1ed2e14de8ed71` を示した。GitHub の自動検査を指す CI は全8ジョブが成功した。最初は実行中だったため、完了を確認してから判定した。

実行記録: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532509)、[Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532477)、[Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43152532652)。

Trivy は報告のみの検査であり、ジョブ成功を別途の脆弱性受容判断とは扱わない。残る依頼事項は PR 本文の r6 要約の訂正だけである。merge、approve、close、push、commit、CI 再実行は行っていない。許可された GitHub への書込みはレビューコメント1件であり、二言語の記録は未コミットで保存する。
