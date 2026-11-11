# REV-45-r3 Publication provenance re-review / 公開版の来歴の再レビュー

> **Summary:** Pass for the documentation-only change at a6f9eee. Both committed records exactly match the REV-issued publication versions; R2-01 is closed. CI remains incomplete.
> **概要:** a6f9eee の文書のみの変更は合格。収録された両記録はREV発行の公開版と完全一致し、R2-01 は解消した。CI は未完了。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-12_RDM-developer-guide_PR45_Pin_Py313_r3.md` (SHA-256: `a827d940e92feb473da4cad277dd60675440047f891475c01f1f9fcf8fffa85b`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-12. **Learned:** byte comparison and an explicit original-to-publication transformation establish reviewer provenance; passing documentation checks alone does not. ／ バイト比較と原本から公開版への明示的な変換確認によってレビュワの来歴を検証でき、文書検査の合格だけでは証明できないと分かった。
- Applies to: RCOSDP/RDM-developer-guide [PR #45](https://github.com/RCOSDP/RDM-developer-guide/pull/45), head `a6f9eeef29052b593f2752566c018f5dc59291a9`, delta after `339f4fa1e7415b82aaee61d090e3620c49047000`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Posted review / 投稿: [r3 PR comment](https://github.com/RCOSDP/RDM-developer-guide/pull/45#issuecomment-6799636262).
- Related: [review index](README.md), [r1 publication](https://github.com/RCOSDP/RDM-developer-guide/blob/a6f9eeef29052b593f2752566c018f5dc59291a9/docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md), [r2 publication](https://github.com/RCOSDP/RDM-developer-guide/blob/a6f9eeef29052b593f2752566c018f5dc59291a9/docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r2.md), [SPEC-06](../spec/06_documentation_conventions.md#english), [r2 PR comment](https://github.com/RCOSDP/RDM-developer-guide/pull/45#issuecomment-6798749424).
- Used by: [status board](../status/README.md) and the coordinator's PR #45 decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Pass. R2-01 (medium) is closed. No new R3 findings.** This verdict covers the assigned change and is delivered as a PR comment. It is not a GitHub approval, merge decision, or claim that every CI check passed.

Location of closure evidence: `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md:8–10,14,57,129` and `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r2.md:8–10`. Each committed file is byte-identical to its REV-issued version 0.2 in the prior scratch `pr45-records/` directory. Each provenance line names its original file and contains the SHA-256 hash (a fingerprint of the file's bytes) independently recomputed from that original.

The original-to-publication comparison is precise: r1 changes five Related link destinations and converts four audit links into named plain-text references, plus two version/provenance lines. Thus “only link destinations” is shorthand, not a literal description of the Markdown changes; the publication header explicitly discloses the plain-text conversions. r2 only adds the two metadata lines. Removing those lines and applying exactly the declared reference changes to the originals reproduces the committed text. No verdict, finding, evidence claim, command, or other body text changes. The original files remain available and were not modified during this review.

The root for the earlier originals and issued publications is `REV scratch evidence (not published): 8baac84b-080f-4104-a2b5-7416702c57e1 scratchpad`; originals are in `reviews/`, publications in `pr45-records/`. This closes the missing reviewer-issued correction identified in r2; it does not relabel the earlier version 0.1 alteration as the original.

```toon
identity:
  r1_original_sha256: 7fc95a749e802996d83147b4c6b66c1403eff0ea4571d41287a7ad571e5e2a13
  r1_issued_and_committed_sha256: 7447126f1eab673fb63f522d591228d8f76282948b63032c29784dc28015ed1b
  r2_original_sha256: a8bb94067af6b27028cbb7d111c5bd30fae9385dc9c1ca2d4681951fec11030f
  r2_issued_and_committed_sha256: 81214eaf19bc2381d1cccbfe981c093371ed0c19204236c886b1ff66831c8597
```

### Regression checks and CI

A fresh detached clone at `REV scratch evidence (not published): pr45-rev-r3` contains the exact assigned head. The complete delta from `339f4fa` is one commit touching only the two review files: r1 adds two lines, and r2 is a new 154-line file. All other tracked contents and modes are unchanged, including installer code, tests, manifests, workflows and prior scan evidence. The r2 closure of R1-01 through R1-03 therefore has no changed implementation to reassess. No new live scan, container build or acceptance run was performed.

The documentation checker passed: 156 checked files, 8 exempt files, 38 warnings, matching the earlier warning count. Both changed records individually have zero errors and zero warnings. The whitespace check passed, and the clone remained clean. Local unit suites were not rerun for this documentation-only delta.

CI (automatic checks run by GitHub) was inspected with `gh pr checks 45`; the recorded snapshot is 2026-11-12 00:14 JST. The PR head and the unit workflow's head both equal the full assigned SHA. Python 3.12 unit tests passed; the remaining eight checks were queued. No failure was reported, but the overall CI result is pending and requires coordinator follow-up before integration. The [unit workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43043457912), [documentation workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43043457756), [security workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43043457778) and [image-build workflow](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43043458023) identify the checked runs.

```toon
ci_checks[9]{name,state}:
  Unit tests Python 3.12,SUCCESS
  Unit tests Python 3.11,QUEUED
  Check Links,QUEUED
  Build MkDocs Site,QUEUED
  Manifest validation and private-URL policy,QUEUED
  Secret scan gitleaks,QUEUED
  Semgrep static analysis,QUEUED
  Trivy filesystem scan,QUEUED
  Build image_build recipes amd64 and arm64,QUEUED
```

### Reproduction and boundaries

Run from `REV scratch evidence (not published): pr45-rev-r3`; expected results are successful assertions, the documentation counts stated in [Regression checks and CI](#regression-checks-and-ci), an empty whitespace report, and an empty status report:

```sh
python3 "<REV scratch evidence (not published): pr45-r3-verify.py>"
python3 tools/docs_check.py
git diff --check 339f4fa HEAD
git status --porcelain
```

Evidence is saved beside this scratch record: `pr45-r3-verify.py`, `pr45-r3-verification.json`, `pr45-r3-identity.json`, `pr45-r3-original-r1.diff`, `pr45-r3-original-r2.diff`, `pr45-r3-docs.log`, `pr45-r3-ci.json`, and `pr45-r3-head-ci.json`. Relative document links are authored and validated for the intended `docs/reviews/` publication location. The report and supporting evidence are not committed. Only the authorized PR comment is posted; no commit, push, merge, approval, issue closure, Docker state change, or access to `runtime/.env` was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**合格（pass）。R2-01（中）は解消。新規のR3指摘はない。** 判定は指定差分に対するもので、PRコメントとして投稿する。GitHubの承認、マージ判断、CI全件合格の宣言ではない。

解消根拠の位置は `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md:8–10,14,57,129` と `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r2.md:8–10`。両収録ファイルは前回scratchの `pr45-records/` にあるREV発行版0.2とバイト単位で一致した。各来歴行は原本のパスを示し、原本から独立に再計算したSHA-256（ファイルのバイト列を識別する指紋）を正しく記載している。

原本との差分は、r1がRelatedの5リンク先変更、監査証跡の4リンクの名前付き平文参照化、版・来歴の2行追加のみ。したがって「リンク先のみ」は略記であり、Markdown差分の厳密な表現ではない。平文参照化は公開版のヘッダに明記されている。r2は版・来歴の2行追加のみ。追加2行を除き、原本に明示された参照変更だけを適用すると、収録本文を完全に再現できる。判定・指摘・証跡の主張・コマンド・その他本文の変更はない。原本は引き続き存在し、今回のレビューでは変更していない。

原本と発行版の起点は `REV scratch evidence (not published): 8baac84b-080f-4104-a2b5-7416702c57e1 scratchpad`。原本は `reviews/`、公開版は `pr45-records/` にある。[英語版の照合結果](#verdict-and-findings)に全ハッシュ値を掲載した。r2で求めたREV発行の訂正版の欠落は解消した。以前の版0.1の改変物を原本と追認したものではない。

### 回帰確認とCI

新規の独立クローン `REV scratch evidence (not published): pr45-rev-r3` を指定の先頭版に固定した。`339f4fa` 以降の全差分は1コミット、レビュー2ファイルだけ。r1は2行追加、r2は154行の新規ファイルである。インストーラー・試験・manifest・ワークフロー・既存検査証跡を含め、その他の追跡内容とファイルモードは不変。r2で解消済みのR1-01〜03について再審査が必要な実装変更はない。新しい実機スキャン、コンテナビルド、受入試験は実行していない。

文書検査は156件検査・8件除外・38警告で合格し、警告数は前回と同じ。変更2記録の個別検査はエラー・警告とも0件。空白検査も合格し、クローンに変更は残っていない。文書のみの差分なので、ローカル単体試験一式は再実行していない。

CI（GitHubが自動実行する検査）は `gh pr checks 45` で確認した。保存時点は2026-11-12 00:14 JST。PRと単体試験ワークフローの先頭版は指定の完全SHAに一致した。Python 3.12単体試験は成功し、残り8件は待機中だった。失敗の報告はないが、CI全体は未完了であり、統合前の追跡確認は調整担当の残件。[英語版のCI一覧と実行リンク](#regression-checks-and-ci)に各状態を記録した。

### 再現と作業範囲

再現コマンド・実行ディレクトリ・期待結果は[英語版の再現手順](#reproduction-and-boundaries)と同一。検証スクリプト、比較JSON、原本との差分2件、文書検査ログ、CI JSONをこのscratch記録と同じフォルダに保存した。文書の相対リンクは将来の公開先 `docs/reviews/` を基準に作成・検証した。記録と証跡は未コミット。許可されたPRコメントだけを投稿し、コミット・push・マージ・承認・Issue閉鎖・Docker状態変更・`runtime/.env` の参照は行っていない。
