# REV PR47 Review records review r1 / レビュー記録公開レビュー r1

> **Summary:** All three added records match REV's originals byte for byte, and the change contains only those additions. The PR description agrees with the records; its preliminary documentation-check count correction is resolved.
> **概要:** 追加された3件は REV の原本とバイト単位で一致し、変更はその3件の追加だけである。PR 本文は記録と整合し、事前に指摘した文書検査件数の訂正も解消している。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** Publication-ready originals can be preserved without rewriting, but the PR's validation count must reflect the committed additions. ／ 初めから公開可能な原本は書き換えず保存できるが、PR の検証件数はコミットされた追加ファイルを含む値でなければならない。
- Applies to / 対象: [PR #47](https://github.com/RCOSDP/RDM-developer-guide/pull/47), head `bbba31f93156a02b3e745286f7b3ca55cc6a47fb`, base `977872075537a7c1367c8df71ad313cad8c51ac6`, branch `docs/review-records-2026-11-12b`.
- PR title / PR 題名: docs(review): osf.io #12 r4・#14 r1 と ember-osf-web #3 r1 のレビュー記録（pass）を収める.
- Reviewer / 担当: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md).
- Used by / 利用先: PR #47 publication decision and [integration status / 統合状況](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**PASS at `bbba31f93156a02b3e745286f7b3ca55cc6a47fb`. All eight CI jobs succeeded. No unresolved finding.** This is a review verdict, not a GitHub approval or a merge action.

A fresh isolated clone was inspected at the full head in the header. The coordinator expanded the original two-record scope to include the osf.io PR #14 r1 record. The two-commit diff against the merge base contains exactly three added Markdown files under `docs/reviews/`: osf.io PR #12 r4 (156 lines), ember-osf-web PR #3 r1 (138 lines), and osf.io PR #14 r1 (262 lines). There are no other additions, modifications, deletions, or renames. All three committed files were compared directly with the supplied originals, without text normalization, and all are byte-identical. They retain version 0.1 dated 2026-11-12.

### Findings

**No remaining content finding. Preliminary R1-01 / P3 is resolved.** The original description reported 170 checked files, while the initial two-record head checked 172. The coordinator corrected that count and updated it to 173 when adding the third record. At the final reviewed head, the documentation checker confirms **173** files checked, 8 exempt, 38 existing warnings, and zero errors. All three additions are included and have no warnings. The final PR description accurately records those counts and the correction history.

### Publication and description checks

None of the three added records contains a private-repository URL or reviewer-machine absolute path. The PR #14 record retains `http://web:5000` and `http://wb:7777`, which are the documented development-service addresses, not private-repository links or credentials. Relative source paths, environment-variable names, commit identifiers, and evidence basenames are retained as review evidence; no secret value was detected. The manifest/private-URL policy checker passed with zero findings. Gitleaks scanned the complete review directory with zero findings; a separate scan of the three additions and the PR description also found zero secrets. The whitespace check passed, and the clone's tracked files remain unchanged.

The final PR description agrees with the records and the inspected history. The osf.io record says pass at `1ad2985080bf3ed4d85d85bacd4ce718f8cee919`, after incorporating Django 2.2 from develop, with 14 successful CI jobs; the ember-osf-web record says pass at `b1e2ad328c4dfed47b680c77500cb3deb638c935`, with successful push and pull-request runs. The added osf.io PR #14 record says pass at `35c6bcdde33bf85e8d9826e76693002b26e2977b`, incorporating Django 2.2 from develop, with 14 successful CI jobs. The pairing of osf.io PR #12 with y-websocket PR #5 and ember-osf-web PR #3 with osf.io PR #14 is preserved. The merged guide PR #46 contains the y-websocket PR #5 r3 pass record. ADR-04 requires a recorded REV pass for the M2 standing delegation, subject to its other conditions. The claim that these three originals needed no publication rewrite is confirmed by their byte identity and content inspection.

This publication review does not rerun historical application tests, reopen the underlying code reviews, or establish deployed-service acceptance. Their original limitations and remaining deployment checks remain in force. No merge, approval, close, push, commit, or modification of the submitted files was performed.

### Verification evidence

These are measured review results, not a machine-consumed canonical dataset. The file names are relative to `docs/reviews/`; each SHA-256 value identifies both the committed copy and its supplied original.

```toon
files[3]{file,bytes,lines,sha256,byte_identical}:
  2026-11-12_RDM-osf.io-dev2027_PR12_File_Editor_Yjs_r4.md,23950,156,c44009b09f547d8a8df2d184766de5e896687b655857af3186456c9b4130e2d5,true
  2026-11-12_RDM-ember-osf-web-dev2027_PR3_Render_Link_r1.md,18651,138,36674cdc255017b88ec702468a35eb71b08c2b025396fead2fb1f87cda424dbd,true
  2026-11-12_RDM-osf.io-dev2027_PR14_Render_URL_r1.md,35301,262,e7c0816d1ae6384920ef16e8cfa8dbb6dddf1b796f3855b6188ad3675086678c,true
local_checks[5]{check,result}:
  documentation,pass; 173 checked; 8 exempt; 38 existing warnings; zero errors
  manifest_and_private_URL_policy,pass; zero findings
  gitleaks_review_directory,pass; zero findings
  gitleaks_three_additions_and_PR_body,pass; zero findings
  diff_whitespace,pass
```

At 2026-11-11 21:13 UTC (2026-11-12 06:13 JST), all eight jobs and all three workflow runs completed successfully. The run metadata identifies the reviewed head, and the final PR read confirms that its head, three-file scope and description are unchanged. CI means GitHub's automated checks. Runs: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099843981), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099844078), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099843944).

```toon
ci_jobs[8]{run,job_id,job,result}:
  43099843981,130787510731,"Build MkDocs Site",success
  43099843981,130787508223,"Check Links",success
  43099844078,130787504619,"Manifest validation and private-URL policy",success
  43099844078,130787507307,"Secret scan (gitleaks)",success
  43099844078,130787507978,"Semgrep static analysis",success
  43099844078,130787509178,"Trivy filesystem scan (report only at M1)",success
  43099843944,130787505073,"Unit tests (installer, tools) (3.11)",success
  43099843944,130787503461,"Unit tests (installer, tools) (3.12)",success
```

The former head `4a5d4867` had three artifact-upload failures with a 404 workflow-run-not-found response; their build/scan steps succeeded. The coordinator requested reruns and then superseded that head with the third-record addition. Those old-head results are not acceptance evidence for the final head. All final-head checks, including artifact uploads, succeeded. Trivy retains its report-only role; a successful job does not constitute a separate vulnerability acceptance decision.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**`bbba31f93156a02b3e745286f7b3ca55cc6a47fb` を PASS と判定。CI 全8ジョブ成功。未解消の指摘なし。** これはレビュー判定であり、GitHub の approve や merge ではない。

ヘッダに記載した完全な head を新規の独立クローンで確認した。調整者の指示で当初の2件に osf.io PR #14 r1 を追加して対象を拡張した。共通祖先との差分は2コミットで、`docs/reviews/` に osf.io PR #12 r4（156行）、ember-osf-web PR #3 r1（138行）、osf.io PR #14 r1（262行）の Markdown 3件を追加するだけである。ほかの追加・変更・削除・改名はない。コミット内の3件を指定された原本と文字列の正規化をせず直接比較し、すべてバイト単位で一致した。全記録が2026-11-12付の版0.1を保持している。

### 指摘

**未解消の内容指摘なし。事前指摘 R1-01 / P3 は解消。** 当初の本文は文書検査170件と記載していたが、2件収録時の head での実測は172件だった。調整者は件数を訂正し、3件目の追加に伴い173件へ更新した。最終対象 head の検査は **173** 件、除外8件、既存警告38件、エラー0件となる。追加された3件も検査対象に入り、全記録の警告は0件である。最終の PR 本文はこの件数と訂正の経緯を正確に記載している。

### 公開適性と本文の確認

追加された3件には非公開リポジトリ URL とレビュワ端末の絶対パスがない。PR #14 の記録に残る `http://web:5000` と `http://wb:7777` は文書化された開発環境のサービスアドレスであり、非公開リポジトリへのリンクや資格情報ではない。ソースの相対パス、環境変数名、コミット識別子、証跡のファイル名はレビューの根拠として残り、秘密の値は検出されなかった。manifest・非公開 URL 方針の検査は指摘0件で合格した。Gitleaks はレビュー保管ディレクトリ全体を検査して検出0件であり、追加3件と PR 本文を対象にした別の検査でも秘密情報の検出は0件だった。空白差分検査も合格し、クローンの追跡対象ファイルは未変更である。

最終の PR 本文は、記録と確認した履歴に一致する。osf.io の記録は develop の Django 2.2 取り込み後の `1ad2985080bf3ed4d85d85bacd4ce718f8cee919` を pass とし、CI 14ジョブの成功を記録している。ember-osf-web の記録は `b1e2ad328c4dfed47b680c77500cb3deb638c935` を pass とし、push と pull_request の両実行の成功を記録している。追加された osf.io PR #14 の記録は、develop の Django 2.2 を取り込んだ `35c6bcdde33bf85e8d9826e76693002b26e2977b` を pass とし、CI 14ジョブの成功を記録している。osf.io PR #12 と y-websocket PR #5、ember-osf-web PR #3 と osf.io PR #14 の組合せも維持される。マージ済みのガイド PR #46 は y-websocket PR #5 r3 の pass 記録を含む。ADR-04 は M2 常設委任の条件として REV の合格記録を求め、ほかの条件も維持する。今回の原本3件は公開用に書き換える必要がなかったという説明を、バイト一致と内容確認で裏付けた。

今回の公開レビューでは過去のアプリ試験を再実行せず、元のコードレビューをやり直さず、配備済みサービスの受入を確認していない。元の記録にある制約と残る配備確認は引き続き有効である。merge、approve、close、push、commit、提出ファイルの変更は行っていない。

### 検証の証跡

[英語節の検証一覧](#verification-evidence)は今回実測した結果であり、機械が読む正本データではない。ファイル名は `docs/reviews/` からの相対名で、SHA-256 はコミット内と指定原本の両方に共通する。文書検査は173件、除外8件、既存警告38件、エラー0件。manifest・非公開 URL 方針、Gitleaks の両検査、空白差分検査も合格した。

2026-11-12 06:13 JST（2026-11-11 21:13 UTC）時点で、全8ジョブと全3ワークフローが成功して完了した。実行情報はレビュー対象 head を示し、最終の PR 読取りでも head・追加3件の範囲・本文が変わっていないことを確認した。CI は GitHub の自動検査を指す。実行記録: [Documentation Build and Check](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099843981), [Security Checks](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099844078), [Unit Tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/43099843944)。

[英語節のジョブ別一覧](#verification-evidence)に全8件の実行番号、ジョブ番号、成功結果を記録した。旧 head `4a5d4867` では、ビルド・スキャン本体は成功したが、成果物アップロード3件が workflow run not found の404で失敗した。調整者が再実行した後、3件目を追加する新 head に対象を切り替えた。旧 head の結果は最終対象の合格根拠に使っていない。最終 head は成果物アップロードも含めて全検査が成功した。Trivy は報告のみの役割を維持し、ジョブ成功を別途の脆弱性受容判断とは扱わない。
