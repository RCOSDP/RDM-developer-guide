# REV PR #52 Ubuntu amd64 scan review r2 / Ubuntu amd64 走査レビュー r2

> **Summary:** Pass: R1-01 through R1-04 are closed in DEMO-22 English/Japanese and the PR description; the checkout correction and preserved version history are consistent, and all required checks passed.
> **概要:** pass（合格）。DEMO-22 の英日と PR 本文で R1-01〜R1-04 の解消を確認。checkout の訂正と保持された版履歴に矛盾はなく、必須検査はすべて合格。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-12. **Learned:** Publication must redact provenance locations and body artifact paths as well as link destinations; only these location labels changed, with judgments, findings, test results and earlier version lines preserved. ／ 公開時はリンク先だけでなく出典の場所と本文の成果物パスも秘匿する。場所の表記のみを変更し、判定、指摘、試験結果、過去の版行を保持した。
- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `2026-11-12_RDM-developer-guide_PR52_Amd64_Scan_r2.md`. Publication 0.3 redacts only original-file locations, local artifact paths and the guest checkout location to basenames or neutral artifact names; prior publication link changes remain. Judgments, findings, test results and earlier version lines are unchanged. ／ 公開版 0.3 では原本の場所、ローカル成果物のパス、ゲスト配置先のみをファイル名または中立的な成果物名に置換し、前公開版のリンク修正を維持する。判定、指摘、試験結果、過去の版行は変更しない。
- Version / 版: 0.1 — 2026-11-12. **Learned:** incomplete scan totals become reviewable when target kinds, successful outputs, failure diagnostics and provenance are stated separately; code and arithmetic can be verified without claiming to verify VM-local measurements. ／ 不完全な走査の合計は、対象の種類、成功した出力、失敗診断、出所を分けるとレビューできる。コードと算術の検証は、VM 内の測定を検証したとの主張を必要としない。
- Applies to: [PR #52](https://github.com/RCOSDP/RDM-developer-guide/pull/52), `docs/ubuntu-amd64-scan` → `develop`, head `0ea0bebfa76cd6819f51fbe96c112cad646a560b`, base `32e2344292abc5391bb27452a7c8a0022d585bff`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Delivered comment: [PR #52 round 2](https://github.com/RCOSDP/RDM-developer-guide/pull/52#issuecomment-6826813237).
- Related: [Round 1](2026-11-12_RDM-developer-guide_PR52_Amd64_Scan_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [Review index](../reviews/README.md).
- Used by: PR #52 author and coordinator for the round-2 decision. This local record is not committed; source links resolve into the retained clean review clone.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass. No remaining blocking findings in the assigned scope.** This is a documentation-review verdict, delivered as one PR comment, not a GitHub approval or a successful security-scan verdict. I inspected the requested head in a fresh scratch clone and compared the round-1 changes, DEMO-22 EN/JA, the current PR description, and the relevant implementation. The PR changes only DEMO-22 (+97/−3 against the base). Source files were not edited.

### Closure of round-1 findings

**R1-01 — Closed.** DEMO-22 lines 199/405 and 210/416 distinguish 58 allow-list entries, 177 matched findings (author-reported), and the M1 entry-count baseline of 0. The PR description states the same distinction. `scan.py:1201–1221` reads the baseline from milestone counts rather than deriving a match count; `manifest/allowlist.baseline.json` contains `counts.M1 = 0`. Both head and the corrected VM revision have 58 entries and the identical allow-list blob `bdd69e60b932ed8438aea4e4b69d67c47893c1b2`. One entry may match multiple findings.

**R1-02 — Closed.** Lines 205–206/411–412 describe the ember SBOM's manual deadline reproduction as an observation, with emulation/load/image-size explanations not established, and retain the unresolved cas-overlay failure despite its successful standalone rerun. Lines 212/418 make configurable `--timeout` a candidate requiring a rerun, without promising exit 0 or security. The remaining-work lists at 217/423 retain both missing ember outputs and the unexplained cas-overlay SBOM. Version 0.5 and the PR description use the same causal restraint. The M1 report-only pass remains distinct from scanner-incomplete exit 51, consistent with `scan.py:1227–1235`.

**R1-03 — Closed, including corrected counts.** Lines 184–195/390–401 separate image-only timing from the author-reported 22 total Trivy targets: 16 images + 5 integration checkouts + 1 repository. They now report 21 vulnerability-scan outputs and 20 SBOMs, hence 20/22 complete pairs, rather than treating the earlier 23-target DEMO-21 set as this run's denominator. Lines 207–208/413–414 explain that 5959 total findings (5931 Trivy + 28 ZAP) are incomplete, after allow-list matching, with 177 matches counted separately; the totals include three HIGH diagnostics for the failed ember scan/SBOM and cas-overlay SBOM. Ember vulnerabilities are absent while its diagnostics remain. The PR description agrees. Target construction and failure diagnostics match `scan.py:843–875`; aggregate semantics match lines 1247–1251. The complete-scan total is explicitly unknown. Arithmetic checks passed: severity sums give 5959, tool sums give 5931 + 28 = 5959, and critical + high gives 2024. These checks establish consistency, not the actual VM output.

**R1-04 — Closed.** The adjacent provenance notes at 170/376 cover start time, durations, exits, image size, installed versions, completion/target counts, findings, 177 matches, baseline exceptions, ZAP writes and manual reruns. They explicitly call these the author's transcription from VM-local output and explain that committed raw evidence does not permit independent verification of the measurements. The PR results heading makes the same attribution and its later paragraph says the reports/SBOMs remain uncommitted in the VM. The former dismissal of raw evidence is gone. No raw-report upload is necessary for this documentation correction.

### Checkout correction and history

The current EN/JA run-3 paragraphs at 172/378 now name `b81628f`, consistent with the setup, pins and remaining-work sections at 23/48/220 and 229/254/426. There is no `7ac6e5c` occurrence in current DEMO-22 or the captured PR body, whose review-response section explicitly discloses the correction. The historical round-1 review remains unchanged. `b81628f` resolves to `b81628f2e62b396db32abb8c6e509716c6f3782f`; its `scan.py`, the base's and the reviewed head's share blob `ef07e2576783310847a81a5da47b26db368293ab`. I verified this code identity, not the VM report's uncommitted `commit` field.

Version 0.5 is first. Automated comparison confirmed the text of entries 0.4, 0.3, 0.2 and 0.1 is preserved verbatim, with 0.4 moved to historical-entry formatting. The PR introduction describes the original 0.4 addition and its review-response section explicitly identifies the 0.5 correction. The old 0.4 lesson is retained history; 0.5 and the current body supply the corrected interpretation.

### Verification and limits

All four required commands ran in the clean detached clone with system/host `python3` (`/opt/homebrew/bin/python3`, Python 3.15.2), without a virtual environment. Exit codes were checked directly. The following TOON records observed review checks, not VM measurements.

```toon
checks[6]{check,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662 tests; 10 skipped; OK; 63.596 s"
  "python3 -m unittest discover -s tools/tests",0,"93 tests; OK; 3.346 s"
  "python3 tools/docs_check.py",0,"186 files checked; 8 exempt; 46 nonfatal warnings"
  "python3 tools/manifest_check.py",0,"manifest 0 findings; policy 0 findings; 763 scanned; 63 non-UTF-8 skipped"
  "tools.manifest_check.parse_toon on every DEMO-22 TOON block",0,"18 blocks parsed"
  "git diff --check 32e2344...HEAD",0,"no whitespace errors"
```

Logs: installer (`PR52_r2_installer_tests.log`), tools (`PR52_r2_tools_tests.log`), docs_check (`PR52_r2_docs_check.log`), manifest_check (`PR52_r2_manifest_check.log`); captured PR description: metadata (`PR52_r2_metadata.json`). Git status remained clean and the remote PR head was rechecked as the requested commit. Manual inspection of the change found no added secret, personal/disposable-account identity or scratch path; no `runtime/` files are tracked. The policy result excludes 63 non-UTF-8 files and does not audit VM-only artifacts.

No deployed `runtime/.env` was inspected. Tests use synthetic temporary fixtures; the real Docker Compose test calls read-only `config`, with no Docker state change or prune. No VM rerun was performed. The remaining runtime gaps are accurately disclosed: ember SBOM/vulnerability results and cas-overlay SBOM are incomplete, cas-overlay's cause is unresolved, and an uninterrupted native-amd64 run remains future work. They do not block this correction of the documented evidence. No merge, approval, close, push or commit was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**pass（合格）。担当範囲の阻害指摘は残っていない。** PR コメント 1 件で伝える文書レビュー判定であり、GitHub の approve やセキュリティ走査の成功を意味しない。新規 scratch clone の指定 head で、前回からの差分、DEMO-22 の英日、現在の PR 本文、関係する実装を照合した。PR の変更は DEMO-22 だけ（base 比で追加 97 行・削除 3 行）。ソースは編集していない。

### 前回指摘の解消

**R1-01 — 解消。** DEMO-22 の 199/405・210/416 行は、許容リスト 58 項目、177 指摘の一致（著者報告）、M1 の項目数基準 0 を区別する。PR 本文も同じ意味である。`scan.py:1201–1221` は一致数ではなく節目の記録から基準を読み、`manifest/allowlist.baseline.json` は `counts.M1 = 0` を持つ。head と訂正後の VM 版はどちらも 58 項目で、許容リストの blob は `bdd69e60b932ed8438aea4e4b69d67c47893c1b2` で同一。1 項目は複数の指摘に一致しうる。

**R1-02 — 解消。** 205–206/411–412 行は ember SBOM の手動実行での期限切れ再現を観察とし、エミュレーション・負荷・サイズによる説明を未確立とする。cas-overlay は単独再実行の成功と実行中の原因未解決を併記する。212/418 行の設定可能な `--timeout` は再実行を要する対策候補であり、終了 0 や安全性を約束しない。残件の 217/423 行には ember の欠けた両出力と原因不明の cas-overlay SBOM が残る。版 0.5 と PR 本文も原因を断定しない。M1 report-only の pass とスキャナー未完の終了 51 は区別され、`scan.py:1227–1235` と整合する。

**R1-03 — 件数訂正を含め解消。** 184–195/390–401 行は image 部分の時間と、著者報告の Trivy 全 22 対象（image 16＋統合 checkout 5＋リポジトリ 1）を分ける。脆弱性走査の出力は 21、SBOM は 20、両方揃うのは 20/22 とし、対象集合の異なる DEMO-21 の 23 を分母にしていない。207–208/413–414 行は、合計 5959（Trivy 5931＋ZAP 28）が許容リスト照合後の不完全な集計で、177 件の一致は別枠だと説明する。ember の scan/SBOM と cas-overlay の SBOM の失敗に対応する HIGH 診断 3 件を含み、ember の脆弱性結果は欠けても診断は残る。PR 本文も一致する。対象構成と失敗診断は `scan.py:843–875`、集計の意味は 1247–1251 行と整合。完全走査の合計は不明と明記される。重大度別の和は 5959、ツール別は 5931＋28＝5959、critical＋high は 2024 と算術も一致する。ただし実際の VM 出力の検証ではない。

**R1-04 — 解消。** 170/376 行の近接した出所注記は、開始時刻、時間、終了値、サイズ、導入版、完了・対象数、指摘数、177 件の一致、baseline 例外、ZAP 書込み、手動再実行を対象とする。VM 内の出力からの著者の転記であり、コミット済みの生の証跡から測定を独立検証できないと明記した。PR の結果見出しも同じ出典を示し、後段は報告・SBOM が VM 内にあり未コミットと説明する。生の証跡を不要とした説明は除かれた。この文書修正に raw report のアップロードは不要。

### checkout の訂正と履歴

現在の英日第 3 回の 172/378 行は `b81628f` とし、準備・pin・残件の 23/48/220・229/254/426 行と一致する。現在の DEMO-22 と保存した PR 本文に `7ac6e5c` は残らず、PR のレビュー対応節は訂正を明示している。過去の r1 レビュー記録は変更していない。`b81628f` は `b81628f2e62b396db32abb8c6e509716c6f3782f` に解決し、この版・base・今回 head の `scan.py` は blob `ef07e2576783310847a81a5da47b26db368293ab` で同一。検証したのはコードの同一性であり、VM 内の未コミット報告の `commit` 欄ではない。

版 0.5 は先頭にある。0.4・0.3・0.2・0.1 の文言がそのまま保持され、0.4 だけ過去の版行の形式へ移ったことを自動比較で確認した。PR 冒頭は当初の 0.4 追記を説明し、レビュー対応節では 0.5 の訂正を明示する。0.4 の教訓は履歴として保持され、0.5 と現本文が訂正後の解釈を示す。

### 検証と限界

必須 4 コマンドは clean な detached clone で、仮想環境を使わずシステム／ホストの `python3`（`/opt/homebrew/bin/python3`、Python 3.15.2）により実行し、終了コードを直接確認した。次の TOON はレビューで観察した検査結果であり、VM 測定値ではない。

```toon
checks[6]{check,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662 件、10 skip、OK、63.596 秒"
  "python3 -m unittest discover -s tools/tests",0,"93 件、OK、3.346 秒"
  "python3 tools/docs_check.py",0,"186 ファイル検査、8 除外、非致命的警告 46"
  "python3 tools/manifest_check.py",0,"manifest 0 件、policy 0 件、763 検査、非 UTF-8 の 63 除外"
  "DEMO-22 の全 TOON に tools.manifest_check.parse_toon",0,"18 ブロック解析成功"
  "git diff --check 32e2344...HEAD",0,"空白エラーなし"
```

ログ: installer (`PR52_r2_installer_tests.log`)、tools (`PR52_r2_tools_tests.log`)、docs_check (`PR52_r2_docs_check.log`)、manifest_check (`PR52_r2_manifest_check.log`)。保存した PR 本文は metadata (`PR52_r2_metadata.json`)。Git status は clean を保ち、リモート PR の head も指定 commit のままと再確認した。差分の目視で秘密・個人や使い捨てアカウントの識別情報・scratch パスの追加は見つからず、`runtime/` の追跡ファイルはない。policy 結果は非 UTF-8 の 63 ファイルを除外し、VM 内だけの成果物を監査したものではない。

配備環境の `runtime/.env` は読んでいない。単体テストは合成した一時 fixture を使い、実際の Docker Compose 呼出しは読取り専用の `config` で、Docker の状態変更や prune はしていない。VM の再実行もしていない。ember の SBOM・脆弱性結果、cas-overlay の SBOM と未解明の原因、中断しない native amd64 実行は引き続き残件として正しく開示されている。これらは今回の証拠の位置づけを直す文書修正を妨げない。merge・approve・close・push・commit は行っていない。
