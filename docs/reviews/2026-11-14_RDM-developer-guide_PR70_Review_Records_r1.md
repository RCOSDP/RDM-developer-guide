# REV-PR70 Review record publication r1 / レビュー記録収録レビュー r1

> **Summary:** Both review records are byte-identical to their originals, the PR description accurately reports their verdicts, and all 13 checks passed. No new finding was identified.
> **概要:** 両レビュー記録は原本とバイト単位で同一で、PR本文の判定は正確であり、13件のチェックはすべて成功した。新規指摘はない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-14. **Learned:** Byte comparison preserves the distinction between an initial changes-required review and the later passing review without rewriting either record. ／ バイト比較により、初回の要修正判定と修正後の合格判定を、どちらの記録も書き換えずに保持できると確認した。
- Applies to / 対象: RDM-developer-guide PR #70, review r1.
- Related / 関連: [Review index / レビュー索引](README.md) · [SPEC-06 Documentation conventions / 文書規約](../spec/06_documentation_conventions.md) · [PR #70](https://github.com/RCOSDP/RDM-developer-guide/pull/70)
- Used by / 利用先: PR #70 integration decision / PR #70の統合判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

Reviewer: REV (assigned reviewer, Codex Astra). Verdict: **pass**. No new P1–P3 finding. The independent scratch clone and GitHub reads covered the complete base-to-head diff, both original records, the PR body, and the final CI results. This review verifies faithful publication; it does not repeat the underlying PR #23 workflow experiments or audit historical account settings.

```toon
revisions[2]{role,sha}:
  base,0df4640f42e965c4234fe67d1d01c0b957c83e30
  head,a990b215622b973ac21b8adc6882af7b42c9e49d
```

### Record integrity and description

The complete diff adds exactly [PR #23 r1](2026-11-14_RDM-osf.io-dev2027_PR23_CI_Dedupe_r1.md) and [PR #23 r2](2026-11-14_RDM-osf.io-dev2027_PR23_CI_Dedupe_r2.md) under `docs/reviews/`, with 145 and 159 added lines respectively. No other file is added, modified, or deleted. Direct byte comparison against the supplied originals passed for both files; SHA-256 values corroborate that comparison.

```toon
records[2]{revision,bytes,sha256}:
  r1,14590,ff52a9cf5d32e70c86bcc8959061d69cfa04b80d087a1cd8c56d86ba0f1672dc
  r2,16134,15d33334f5fabe08a4b27f5a2e55f2bbdfa4935011ad3535405f38b763fb93bb
```

The PR body's r1 row correctly reports changes required, the pending non-PR concurrency issue (P2), the missing target-branch qualification (P3), and nine successful checks. Its r2 row correctly reports pass at head `92ad287393`, resolution of both findings, nine successful checks, and one pull_request run each for Unit Tests and CodeQL with no push run. These are accurate summaries of the preserved records, including their distinction between CI success and behavioral evidence.

Manual reading and targeted pattern checks found no private-repository URL, local absolute path, or secret in either added record or the PR body. Private repositories are referred to by name only. The manifest policy scan and CI secret scan also passed; these checks are evidence of the reviewed content, not a universal guarantee against every possible secret format.

### Validation and final CI

In the independent clone at the reviewed head, `python3 tools/docs_check.py` exited 0: 202 files checked, eight exempt, 67 warnings, none for the two added records. `python3 tools/manifest_check.py` exited 0 with zero findings. The PR's local-check claims are consistent with these independent results.

At 2026-11-14 10:46 UTC, base and head still matched the identifiers recorded here. The reviewer waited for completion: all 13 checks were completed and successful, with none pending, failed, or canceled. A separate run query filtered by the full head confirmed four completed successful pull_request workflows.

```toon
runs[4]{workflow,id,conclusion}:
  Unit Tests,43586735539,success
  Documentation Build and Check,43586735508,success
  Installer prerequisite scripts (lint and dry run),43586735504,success
  Security Checks,43586735566,success
```

Exactly one [r1 review comment](https://github.com/RCOSDP/RDM-developer-guide/pull/70#issuecomment-6876121960) was posted with the required REV prefix. No merge, approval, close, push, commit, workflow rerun, or cancellation was performed. No correction remains requested by this review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と対象

レビュワ: REV（担当レビュワ, Codex Astra）。判定: **pass**。新規P1〜P3指摘はない。独立したscratch cloneとGitHubの読み取りで、baseからheadまでの全差分、両原本、PR本文、CI最終結果を確認した。忠実な収録の確認であり、元PR #23のワークフロー実験や過去のアカウント設定監査をやり直したものではない。

```toon
revisions[2]{role,sha}:
  base,0df4640f42e965c4234fe67d1d01c0b957c83e30
  head,a990b215622b973ac21b8adc6882af7b42c9e49d
```

### 記録の同一性と本文

全差分は`docs/reviews/`への[PR #23 r1](2026-11-14_RDM-osf.io-dev2027_PR23_CI_Dedupe_r1.md)と[PR #23 r2](2026-11-14_RDM-osf.io-dev2027_PR23_CI_Dedupe_r2.md)の追加だけで、それぞれ145行と159行である。他の追加・変更・削除はない。指定された原本との直接バイト比較は両方とも一致し、SHA-256値でも裏付けた。

```toon
records[2]{revision,bytes,sha256}:
  r1,14590,ff52a9cf5d32e70c86bcc8959061d69cfa04b80d087a1cd8c56d86ba0f1672dc
  r2,16134,15d33334f5fabe08a4b27f5a2e55f2bbdfa4935011ad3535405f38b763fb93bb
```

PR本文のr1行は、要修正、非PRの待機実行に関する同時実行制御の問題（P2）、宛先ブランチ条件の欠落（P3）、チェック9件成功を正しく記す。r2行もhead `92ad287393`でのpass、両指摘解消、チェック9件成功、Unit TestsとCodeQLがpull_request起動で各1本かつpush起動なしと正しく記す。CI成功と挙動の証拠を区別した保存記録の要約として正確である。

目視と対象を絞ったパターン検査で、追加された両記録とPR本文に非公開リポジトリURL・ローカル絶対パス・秘密情報は認めなかった。非公開リポジトリは名前だけで参照される。manifestの方針検査とCIの秘密情報検査も成功した。確認した内容の証拠であり、あらゆる秘密情報の形式を網羅する保証ではない。

### 検証とCI最終結果

独立cloneの対象headで`python3 tools/docs_check.py`は終了0だった。202件を検査し、8件は対象外、警告67件で、追加された2記録への警告はなかった。`python3 tools/manifest_check.py`も指摘0件・終了0だった。PR本文のローカル検査の説明は独立した結果と整合する。

2026-11-14 10:46 UTC時点でbaseとheadは記載した識別子のままだった。レビュワは完了を待ち、13チェックすべて完了・成功、待機・失敗・取り消しなしを確認した。完全なheadで絞った別の実行一覧でも、pull_request起動の4ワークフローがすべて完了・成功だった。

```toon
runs[4]{workflow,id,conclusion}:
  Unit Tests,43586735539,success
  Documentation Build and Check,43586735508,success
  Installer prerequisite scripts (lint and dry run),43586735504,success
  Security Checks,43586735566,success
```

指定のREV接頭辞を付けた[r1レビューコメント](https://github.com/RCOSDP/RDM-developer-guide/pull/70#issuecomment-6876121960)を1件だけ投稿した。マージ・承認・クローズ・push・コミット・ワークフロー再実行・取り消しは行っていない。本レビューが求める未解決の修正はない。
