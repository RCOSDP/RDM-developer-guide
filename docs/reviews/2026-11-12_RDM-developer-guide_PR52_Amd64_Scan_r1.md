# REV PR #52 Ubuntu amd64 scan review r1 / Ubuntu amd64 走査レビュー r1

> **Summary:** Changes requested for four documentation issues: baseline semantics, causal overstatement, coverage/count semantics, and attribution of VM-only observations; all four required checks passed.
> **概要:** baseline の意味、原因の断定、対象・集計の意味、VM 内だけにある観察の出典表示の 4 点で修正を要請。必須の 4 検査はすべて合格。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-12. **Learned:** Publication must redact provenance locations and body artifact paths as well as link destinations; only these location labels changed, with judgments, findings, test results and earlier version lines preserved. ／ 公開時はリンク先だけでなく出典の場所と本文の成果物パスも秘匿する。場所の表記のみを変更し、判定、指摘、試験結果、過去の版行を保持した。
- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `2026-11-12_RDM-developer-guide_PR52_Amd64_Scan_r1.md`. Publication 0.3 redacts only original-file locations, local artifact paths and the guest checkout location to basenames or neutral artifact names; prior publication link changes remain. Judgments, findings, test results and earlier version lines are unchanged. ／ 公開版 0.3 では原本の場所、ローカル成果物のパス、ゲスト配置先のみをファイル名または中立的な成果物名に置換し、前公開版のリンク修正を維持する。判定、指摘、試験結果、過去の版行は変更しない。
- Version / 版: 0.1 — 2026-11-12. **Learned:** a passing documentation check cannot distinguish an observed timeout from an exclusive causal claim, or a milestone entry-count baseline from matched findings. ／ 文書検査の合格だけでは、観察されたタイムアウトと排他的な原因の断定、節目の項目数基準と一致した指摘件数を区別できない。
- Applies to: [PR #52](https://github.com/RCOSDP/RDM-developer-guide/pull/52), `docs/ubuntu-amd64-scan` → `develop`, head `989ff6e5f46993f75069cd2ec7bd858ec7787151`, base `32e2344292abc5391bb27452a7c8a0022d585bff`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Delivered comment: [PR #52 round 1](https://github.com/RCOSDP/RDM-developer-guide/pull/52#issuecomment-6826312305).
- Related: [SPEC-06](../spec/06_documentation_conventions.md) · [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [Review index](../reviews/README.md).
- Used by: PR #52 author and coordinator for round 1 corrections. This local review is not committed; relative source links resolve into the retained clean review clone.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested — four P2 findings.** P2 denotes a normal-priority correction needed before acceptance. This is the requested review verdict, delivered through one PR comment, not a GitHub approval or formal change-request review. No source files were edited.

### Findings

**R1-01 / P2 — Correct the meaning of `allowlist_baseline`.** DEMO-22 lines 202 and 401 say “none from the baseline allow-list” / “baseline の許容リスト由来は 0”. In `installer/grdm_dev/scan.py:1215–1221`, this field is the entry count recorded for the current or latest earlier milestone, read from `manifest/allowlist.baseline.json`; the committed value is `counts.M1 = 0`. It is not a count of findings matched by a second allow-list. Replace both sentences with “58 allow-list entries; 177 findings matched (author-reported); M1 entry-count baseline 0.” Also correct the PR description's equivalent wording. The numbers 58 and 177 are internally compatible: one entry can match several package findings, and `_entry_matches` / the loop at lines 1207–1214 do not limit each entry to one finding. All three inspected revisions (head, `7ac6e5c`, `32e2344`) contain 58 entries.

**R1-02 / P2 — Keep the cause and proposed timeout change conditional.** DEMO-22 lines 200/399 assert “emulation-only limit, not an installer fault”; lines 209/408 prescribe a longer limit or a non-emulated host for both outstanding cases. The reported manual ember timeout reproduces a deadline on this host; a previous successful DEMO-21 scan does not establish an exclusive cause. The same paragraph correctly says the cas-overlay cause was not captured and is unconfirmed, and reports that its standalone run succeeded in 3.6 seconds without the proposed change. State the observed timeout and describe emulation/load as an explanation under investigation. Keep cas-overlay's failure cause unresolved in the remaining-work list. Lines 204/403 may retain a decision item to consider passing configurable `--timeout`, but say it may address deadline-limited runs and requires a rerun; it does not guarantee exit 0 or prove security. Preserve the correct distinction between exit 51 and an M1 report-only gate result. Apply the same restraint to the header and PR description where they summarize the cause.

**R1-03 / P2 — Separate Trivy image timing, total targets, completed vulnerability scans, and failure findings.** Lines 181/380 label “22 of 23 targets” as Trivy images, while `scan.py:873–874` counts images plus integration source directories plus the repository itself. DEMO-21's “23 targets” does not prove 23 image targets. Identify which count the author observed; if 23 is the tool's target count, call it all Trivy targets and keep the image-only timing separate. Lines 200/399 also say the 22 targets “finished” although cas-overlay's SBOM failed. Distinguish successful vulnerability scans from complete SBOM-plus-scan coverage. Finally, `scan.py:850–858` adds HIGH `SBOM-FAILED` / `SCAN-FAILED` findings for failed calls, so the stated failures contribute three diagnostic findings (two ember, one cas-overlay) to the reported aggregate if the run behaved as described. The aggregate at lines 1247–1249 counts open findings after allow-list matching, not all raw vulnerabilities; 177 matched findings are separate. Clarify that ember vulnerability results are missing but its failure findings remain, and use “incomplete totals” instead of asserting a strictly smaller total than a hypothetical complete scan. The missing ember SBOM should remain explicit alongside its missing vulnerability scan.

**R1-04 / P2 — Explicitly attribute the run-3 measurements to the author.** Lines 169–203 / 368–402 present precise runtime results, then say the reports/SBOMs were not committed and are not evidence the page needs. The PR commits only this Markdown page; no run-3 report, scanner output or timing log is available in the committed evidence. Retaining bulky artifacts in the VM is acceptable, but add a clear EN/JA statement adjacent to the run-3 data that these are author-recorded observations transcribed from VM-local output, not independently verified from committed raw evidence. Scope that statement to start time, elapsed times, exit codes, image size, versions actually installed, tool completion/targets, findings, 177 matches, baseline exceptions, ZAP write success and manual reruns. Replace the dismissal of evidence with the actual limitation. No upload of raw reports or secrets is requested. The first-person cas-overlay hypothesis and the note that reports remain in the VM help, but do not clearly attribute the whole table or acknowledge what a repository-only reviewer can verify.

### Supported facts and limits

The severity arithmetic is consistent: `298 + 1726 + 2560 + 1369 + 6 = 5959`; Trivy's listed severities sum to 5931, ZAP's to 28, and `5931 + 28 = 5959`. The critical/high open count is `298 + 1726 = 2024`. This establishes internal arithmetic, not that the VM produced those observations. There is no mathematical conflict between the 58 manifest entries and 177 matched findings.

`scan.py` has identical Git blob `ef07e2576783310847a81a5da47b26db368293ab` at head, `7ac6e5c` and `32e2344`. Its Trivy calls supply no `--timeout`. Its code prioritizes scanner-incomplete exit 51 over gate pass; M1's report-only rule and Semgrep timeout warning behavior are supported by the committed implementation and SPEC-03/ADR-03. The document consistently qualifies its gate result as M1 report-only; it does not claim a strict security gate passed. The five-minute timeout and manual reproduction remain author observations for this review; no VM execution or external Trivy-version verification was performed.

The only changed file is DEMO-22 (+82/−3 lines). EN precedes JA, the additions correspond, version 0.4 is present and prior 0.3/0.2/0.1 entries are retained. All 18 TOON blocks parse. Manual review of the changed file found no added secrets, personal or disposable-account identities, or scratch paths; numeric uids are relevant ownership-test details. No `runtime/` paths are tracked. The policy scan found zero issues across 763 text files, with 63 non-UTF-8 files skipped; this is not a claim to have audited all binary assets or VM-only artifacts.

### Verification

Run from a fresh scratch clone detached at the requested head, using host `python3` (`/opt/homebrew/bin/python3`, Python 3.15.2), without a virtual environment. Unit-test temporary fixtures are synthetic; no deployed `runtime/.env` was inspected. The suite's real Docker Compose invocation is read-only `config`; no Docker state change or prune was performed.

```toon
checks[6]{check,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662 tests; 10 skipped; OK; 61.467 s"
  "python3 -m unittest discover -s tools/tests",0,"93 tests; OK; 3.309 s"
  "python3 tools/docs_check.py",0,"186 files checked; 8 exempt; 46 nonfatal warnings"
  "python3 tools/manifest_check.py",0,"manifest 0 findings; policy 0 findings; 763 scanned; 63 non-UTF-8 skipped"
  "tools.manifest_check.parse_toon on all DEMO-22 TOON blocks",0,"18 blocks parsed"
  "git diff --check origin/develop...HEAD",0,"no whitespace errors"
```

Logs: installer tests (`PR52_r1_installer_tests.log`), tools tests (`PR52_r1_tools_tests.log`), documentation check (`PR52_r1_docs_check.log`), manifest/policy check (`PR52_r1_manifest_check.log`). Git status remained clean after verification. Passing checks validate the committed code and document structure, not the VM measurements. The author must correct R1-01 through R1-04 in both languages and align the PR description; no implementation change or fresh VM run is required merely to label the existing evidence honestly.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Changes requested（修正要請）— P2 を 4 件。** P2 は受入前に直す通常優先度の指摘を指す。指定された PR コメント 1 件で伝えるレビュー判定であり、GitHub の approve や正式な request-changes review は行わない。ソースファイルは変更していない。

### 指摘

**R1-01 / P2 — `allowlist_baseline` の意味を修正する。** DEMO-22 の 202・401 行は「baseline の許容リスト由来は 0」と説明する。しかし `installer/grdm_dev/scan.py:1215–1221` では、`manifest/allowlist.baseline.json` から現在または直前の節目に記録した項目数を読み、コミット値は `counts.M1 = 0` である。別の許容リストに一致した指摘数ではない。英日とも「許容リスト 58 項目、177 指摘に一致（著者報告）、M1 の項目数基準は 0」とする。PR 本文の同じ表現も直す。58 と 177 自体は矛盾しない。1 項目で複数パッケージの指摘に一致でき、`_entry_matches` と 1207–1214 行の処理は 1 項目につき 1 指摘に制限しない。head・`7ac6e5c`・`32e2344` の全版で 58 項目を確認した。

**R1-02 / P2 — 原因と timeout 変更案を条件付きで記す。** 200・399 行は「インストーラーの不具合ではなく、エミュレーションだけの限界」と断定し、209・408 行は両残件に長い制限か非エミュレーションのホストが必要とする。著者報告の ember 手動再実行は、このホストの期限切れを再現したもの。以前の DEMO-21 の成功だけでは排他的な原因を証明できない。同じ段落は cas-overlay の原因未採取・仮説未確認を正しく明記し、変更案なしの単独再実行が 3.6 秒で成功したとも記す。タイムアウトの観察と、調査中のエミュレーション／負荷の説明を分ける。残件一覧でも cas-overlay の原因は未解明とする。204・403 行の判断項目は、設定可能な `--timeout` の受け渡しを検討する案として残してよいが、期限切れへの対策候補であり再実行が必要とする。終了 0 や安全性を保証しない。終了 51 と M1 report-only の gate pass の正しい区別は保つ。原因を要約する版ヘッダと PR 本文も同様に修正する。

**R1-03 / P2 — Trivy の image 時間、全対象数、完了した脆弱性走査、失敗診断を区別する。** 181・380 行は「23 対象のうち 22」を image と呼ぶが、`scan.py:873–874` の対象数は image・統合ソースのディレクトリ・このリポジトリの合計である。DEMO-21 の 23 対象も image 23 個の根拠にはならない。著者が観察した数の定義を明記し、tool の対象数なら Trivy の全対象と呼び、image だけの時間と分ける。200・399 行の「終わった 22 対象」も cas-overlay の SBOM 失敗と区別が必要であり、脆弱性走査の完了と SBOM を含む全体の完了を分ける。さらに `scan.py:850–858` は失敗した呼び出しごとに HIGH の `SBOM-FAILED` / `SCAN-FAILED` を加えるため、記載どおりの実行なら ember 2 件・cas-overlay 1 件の診断も集計される。1247–1249 行の合計は許容リスト照合後の未許容指摘であり、生の脆弱性全件ではない。177 件の一致は別枠である。ember の脆弱性結果は欠けても失敗診断は残ることを記し、完全走査より必ず小さいとの断定を「不完全な集計」に替える。ember の未完 SBOM も脆弱性走査と併記して残す。

**R1-04 / P2 — 第 3 回の測定値を著者報告と明示する。** 169–203・368–402 行は正確な実行結果を示した後、報告と SBOM は未コミットで「このページに要る証跡でもない」とする。この PR のコミットは Markdown 1 ファイルだけで、第 3 回の報告・スキャナー出力・時間ログは含まれない。大きな成果物を VM に残すことは許容できるが、第 3 回データの近くに「著者が VM 内の出力から転記した観察であり、コミット済みの生の証拠から独立検証したものではない」と英日で明示する。開始時刻、所要時間、終了コード、image サイズ、実際の導入版、tool の完了・対象、検出数、177 件の一致、基本対策の例外、ZAP の書込み成功、手動再実行をこの説明の対象とする。証跡不要との説明を、実際の検証限界に替える。生の報告や秘密のアップロードは要求しない。cas-overlay の一人称の仮説と VM 保管の記述は有用だが、表全体の出典やリポジトリだけのレビュワが確認できる範囲までは明確でない。

### 確認できた事実と限界

重大度の算術は一致する。`298 + 1726 + 2560 + 1369 + 6 = 5959`、Trivy の内訳は 5931、ZAP は 28、両者の合計は 5959。未許容の重大・高は `298 + 1726 = 2024`。これは内部の算術整合であり、VM が実際にこの観察を出したことの検証ではない。許容リスト 58 項目と一致した 177 指摘にも算術上の矛盾はない。

head・`7ac6e5c`・`32e2344` の `scan.py` は Git blob `ef07e2576783310847a81a5da47b26db368293ab` で同一。Trivy 呼び出しは `--timeout` を渡さない。実装は gate pass よりスキャナー未完の終了 51 を優先し、M1 の report-only と Semgrep timeout の警告扱いも、コミット済み実装と SPEC-03／ADR-03 に対応する。文書の gate pass は一貫して M1 report-only に限定され、厳格な安全性ゲートの合格とはしていない。5 分の制限と手動再現は本レビューでは著者の観察として扱い、VM 実行や外部の Trivy 版確認は行っていない。

変更ファイルは DEMO-22 だけ（追加 82 行・削除 3 行）。英語→日本語の順序と対応が保たれ、版 0.4 と過去の 0.3・0.2・0.1 を確認した。TOON 全 18 ブロックは解析できた。変更ファイルの目視では、秘密、個人・使い捨てアカウントの識別情報、scratch パスの追加は見つからない。数値 uid は所有者試験に必要な情報である。`runtime/` の追跡ファイルはない。policy 検査はテキスト 763 ファイルで検出 0、非 UTF-8 の 63 ファイルは除外。全バイナリや VM 内だけの成果物を監査したという意味ではない。

### 検証

指定 head に detach した新規 scratch clone で、仮想環境ではなくホストの `python3`（`/opt/homebrew/bin/python3`、Python 3.15.2）を使用。単体テストの一時 fixture は合成データで、配備環境の `runtime/.env` は読んでいない。suite が実際に呼ぶ Docker Compose は読取り専用の `config` で、Docker 状態変更や prune はしていない。

```toon
checks[6]{check,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662 件、10 skip、OK、61.467 秒"
  "python3 -m unittest discover -s tools/tests",0,"93 件、OK、3.309 秒"
  "python3 tools/docs_check.py",0,"186 ファイル検査、8 除外、非致命的警告 46"
  "python3 tools/manifest_check.py",0,"manifest 0 件、policy 0 件、763 検査、非 UTF-8 の 63 除外"
  "DEMO-22 全 TOON に tools.manifest_check.parse_toon",0,"18 ブロック解析成功"
  "git diff --check origin/develop...HEAD",0,"空白エラーなし"
```

ログ: installer tests (`PR52_r1_installer_tests.log`)、tools tests (`PR52_r1_tools_tests.log`)、docs_check (`PR52_r1_docs_check.log`)、manifest_check (`PR52_r1_manifest_check.log`)。検証後も Git status は clean。合格はコミット済みコードと文書構造の検証であり、VM 測定値の検証ではない。著者には R1-01〜R1-04 の英日修正と PR 本文の整合を求める。既存証拠の位置づけを正しく記すためだけに、実装変更や VM 再実行は要求しない。
