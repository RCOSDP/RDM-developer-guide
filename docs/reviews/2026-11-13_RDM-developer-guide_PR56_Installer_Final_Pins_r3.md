# REV PR56 Installer final pins review r3 / インストーラー最終固定版レビュー r3

> **Summary:** Pass. R2-01 is closed: invalid sign-in evidence yields exit 51 and a written incomplete report, without skipped coverage. Earlier R1-01 and R1-02 fixes remain intact.
> **概要:** 合格。不正なサインイン証拠は終了 51 と保存済みの未完報告になり、対象外にはならないため R2-01 は解消した。R1-01 と R1-02 の修正も維持されている。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-13. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `/private/tmp/claude-501/-Users-komiyama-ai-development-GitHub-RDM-developer-guide/8baac84b-080f-4104-a2b5-7416702c57e1/scratchpad/reviews/2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r3.md`. All other original text is retained verbatim below, including the original version and review-time context. ／ 以下は元の版とレビュー時点の文脈を含め、それ以外の原文をそのまま保持する。
- Version / 版: 0.1 — 2026-11-13. **Learned:** a narrowly placed evidence-validation exception handler preserves failure reporting without granting an exemption; reverting only that handler proves the regression test detects the original defect. ／ 証拠の検証だけを囲む例外処理は除外を認めず失敗報告を維持でき、その処理だけを戻すことで回帰試験が元の欠陥を検出すると確かめられる。
- Applies to: RCOSDP/RDM-developer-guide PR #56, `cb93d48a855dbb894575c1efa815b65668dbaecc..5fca0b56f5207c1f59d87aa81e9781b6a54edb58`; REV round 3.
- Related: [PR #56](https://github.com/RCOSDP/RDM-developer-guide/pull/56) · [review index](../reviews/README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r1.md) · [r2](2026-11-13_RDM-developer-guide_PR56_Installer_Final_Pins_r2.md).
- Reviewer: REV（担当レビュワ, Codex Astra）. Used by: PR #56 integration decision / 統合判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass; no remaining blocking finding.** R2-01 is closed. Review used the clean detached clone `/private/tmp/rev-pr56-r3-clone`; `gh pr view` confirmed the requested head both before and after verification. Exactly one commit follows r2, changing only `installer/grdm_dev/scan.py` and `installer/tests/test_scan.py`.

The new `zap_behind_sign_in` wrapper at line 1089 catches `ValueError` (including `UnicodeDecodeError`) and `OSError` only around the sign-in evidence helper. It returns `None`, which makes `run_zap` retain its ordinary missing-report problem. It cannot create a verified destination or increment skipped coverage on that failure. Actual scanning, report reading, findings, and report saving remain outside the wrapper. The helper body, including all positive evidence requirements and the accepted-redirect success path, is otherwise unchanged.

### R2-01 evidence

The added regression passes for malformed Location (`http://[broken` and `http://[::1`), malformed ZAP-message host, malformed configured CAS address, and undecodable `osf.env`. An independent temporary script also exercised the four categories separately and opened each generated `runtime/reports/scan_latest.json`: exit 51, incomplete ZAP result, no `skipped_targets`, and saved tool rows matching the emitted report. All files belonged to synthetic temporary fixtures.

The script additionally injected a configuration `PermissionError`, and probe-runner `ValueError` and `OSError`; each stayed incomplete with exit 51. A `RuntimeError` inside the helper propagated, as did a `ValueError` from `_read_zap_report` outside the wrapper. Thus the catch does not swallow unrelated failures elsewhere or convert missing evidence into success. Existing tests also retain scanner error handling when an actual report exists. The verified redirect test still returns 0 with zero scanned targets, one explicit skipped target, a `ZAP NOT RUN` note, and exactly one probe.

After the full suites finished, only `scan.py` was temporarily replaced with its `cb93d48` content while retaining the new test. That test exited 1 with `ValueError: Invalid IPv6 URL` at the old line 1103. Restoring `scan.py` from HEAD and rerunning all 25 `ScannerRobustnessTests` exited 0. The clone ends with no tracked changes; no commit was made.

### Earlier verified points

R1-01 remains closed: tests reject an arbitrary host, changed host spelling or port, changed seed, public access or conflicting settings, missing configuration, another service, missing/failed probes, relative Location, and a wrong destination. Skipped coverage is explicit and excluded from scanned target counts. R1-02 remains closed: ADR-14 in both languages uses `secrets init --missing`, render/build/render/up, then once-only `invoke migrate_search`, with a canonical guide link; rotate is not the upgrade step.

Comparison with the r1 head confirms that all files outside the previously reviewed seven-file correction are unchanged. Therefore earlier source-based checks of pins, rendered isolation and ES8 security, secret preservation, upstream build/migration definitions, and committed 14/14 acceptance evidence remain applicable, with their original limitations. These were not fresh live integration tests. The five changed documents preserve every earlier Learned entry, checked by script. DEMO-20 still discloses that the raw full-scan report is uncommitted, per-target coverage and 6,264 findings are operator records or inference, and the stricter scanner has not been run on the Mac Studio stack.

### Checks and boundaries

Commands ran from `/private/tmp/rev-pr56-r3-clone`; each process exit was checked. The following is this review's observed result record, not a mirror of repository JSON.

```toon
checks[7]{command,exit,result}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests",0,"678 tests; 10 skipped; 82.221 seconds"
  "/usr/bin/python3 -m unittest discover -s tools/tests",0,"93 tests; 5.233 seconds"
  "/usr/bin/python3 tools/docs_check.py",0,"193 files; 8 exempt; 58 warnings"
  "/usr/bin/python3 tools/manifest_check.py",0,"0 manifest findings; 0 policy findings; 780 scanned; 63 non-UTF-8 skipped"
  "PYTHONPATH=installer:installer/tests /usr/bin/python3 /private/tmp/rev-pr56-r3-extra.py",0,"written reports and exception boundaries verified"
  "PYTHONPATH=installer:installer/tests /usr/bin/python3 -m unittest test_scan.ScannerRobustnessTests.test_zap_malformed_evidence_is_no_evidence_and_the_scan_still_reports_incomplete (scan.py temporarily reverted)",1,"expected ERROR: Invalid IPv6 URL"
  "PYTHONPATH=installer:installer/tests /usr/bin/python3 -m unittest test_scan.ScannerRobustnessTests (HEAD restored)",0,"25 tests; 0.430 seconds"
```

Logs: `/private/tmp/rev-pr56-r3-{installer,tools,docs,manifest,extra,reverted,restored}.log`. The independent script is `/private/tmp/rev-pr56-r3-extra.py`. Historical-version preservation and final `git diff --check` also exited 0. Git status was clean. No live Docker operations, live `runtime/.env` access, merge, approval, close, push, commit or prune occurred. Exactly one concise Japanese PR comment accompanies this review. Nothing remains to fix in this review's scope; actual Docker-image probe execution and a new live stack scan remain unverified, as in r2.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Pass（合格）。統合を止める残件なし。** R2-01 は解消した。隔離した `/private/tmp/rev-pr56-r3-clone` の detached clone を使い、検証の前後に `gh pr view` で指定 head を確認した。r2 後は一コミットだけで、変更は `installer/grdm_dev/scan.py` と `installer/tests/test_scan.py` に限られる。

1089 行の `zap_behind_sign_in` は、サインインの証拠を判定する処理だけで `ValueError`（`UnicodeDecodeError` を含む）と `OSError` を捕捉する。返すのは `None` なので、`run_zap` は通常の報告欠落の問題を保つ。失敗から確認済みの宛先を作ったり、対象外の数を増やしたりしない。検査本体、報告の読込み、検出結果、保存はこの捕捉の外にある。肯定的な証拠の全条件と、正当な転送を認める経路は変更されていない。

### R2-01 の確認

追加試験は、不正な Location（`http://[broken` と `http://[::1`）、ZAP メッセージ中の不正ホスト、設定された CAS の不正アドレス、文字として読めない `osf.env` で通過した。独立した一時スクリプトでも四分類を個別に実行し、生成した `runtime/reports/scan_latest.json` を開いた。終了 51、ZAP 未完、`skipped_targets` なし、保存した tool の行と出力した報告の一致を確認した。すべて合成値を持つ一時試験のファイルである。

さらに設定読込みの `PermissionError`、探りを実行する runner の `ValueError` と `OSError` を与え、すべて未完・終了 51 を確認した。判定内の `RuntimeError` は伝播し、捕捉の外にある `_read_zap_report` の `ValueError` も伝播した。したがって別の場所の無関係な失敗を握りつぶしたり、証拠欠落を成功に変えたりしない。実報告がある場合の検査エラーも既存試験で維持される。正当な転送の試験は引き続き終了 0、検査済み 0、明示した対象外 1、`ZAP NOT RUN` 注、探り一回となる。

全体試験が終了してから、新しい試験を残したまま `scan.py` だけを一時的に `cb93d48` の内容に戻した。新試験は旧 1103 行の `ValueError: Invalid IPv6 URL` により終了 1 になった。HEAD の内容を復元し `ScannerRobustnessTests` の全 25 件を実行すると終了 0。clone の追跡ファイルに変更は残っておらず、commit はしていない。

### 以前の確認点

R1-01 は解消を維持する。任意ホスト、ホスト表記やポートの変更、種 URL の変更、公開アクセスや矛盾する設定、設定欠落、別サービス、探りの欠落・失敗、相対 Location、別宛先を試験が拒否する。対象外は明示し、検査済みの数から除く。R1-02 も維持する。ADR-14 は英和とも `secrets init --missing`、render/build/render/up、一度だけの `invoke migrate_search` と正本ガイドへのリンクを示し、rotate を更新手順にしていない。

r1 head との比較で、既にレビューした七ファイルの訂正以外は変更がない。固定版、生成した構成の分離と ES8 の安全設定、既存秘密の保持、上流のビルド・移行定義、コミット済み 14/14 受入証拠について、以前のソースに基づく確認と限界は引き続き適用できる。実環境の統合試験を新たに行ったわけではない。変更された五文書の過去の Learned 行は、スクリプトで全保持を確認した。DEMO-20 は引き続き、全検査の生報告が未コミット、対象ごとの網羅と 6,264 件は作業者の記録または推定であり、厳格化した検査は Mac Studio 上で未実行と開示している。

### 検査と境界

コマンドと個別の終了値は英語部の TOON に記録した。システム `/usr/bin/python3` を使い、installer は 678 件・10 skip・82.221 秒、tools は 93 件・5.233 秒、docs_check は 193 ファイル・8 例外・58 警告、manifest_check は manifest/policy とも指摘 0（780 検査、非 UTF-8 の 63 を除外）。四検査とも終了 0。追加スクリプトも終了 0、意図した修正前再現は終了 1、復元後は 25 件・0.430 秒で終了 0。

ログとスクリプトは英語部のパスに保存した。過去の版の保持確認と最後の `git diff --check` も終了 0、Git status は clean。実 Docker 操作、実環境の `runtime/.env` 参照、merge、approve、close、push、commit、prune は行っていない。簡潔な日本語 PR コメントを一件だけ付ける。今回の範囲に修正残件はない。Docker イメージ内での探りの実行と、新しい実スタック検査は r2 同様に未検証である。
