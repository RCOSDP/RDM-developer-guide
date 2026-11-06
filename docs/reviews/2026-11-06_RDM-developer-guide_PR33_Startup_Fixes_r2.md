# PR33 Startup fixes review r2 / 起動修正レビュー r2

> **Summary:** Changes requested: host-dependent memory tests fail in CI, and the new Semgrep timeout exemption can pass incomplete scans even at M4/M5. The R1 implementation fixes are substantially present, with regression evidence and small documentation corrections still outstanding.
> **概要:** 修正要求。ホスト依存のメモリ試験が CI で失敗し、新しい Semgrep 時間切れ例外は M4/M5 でも未完了の検査を合格にする。R1 の実装修正は概ね反映されたが、回帰試験の証跡と小さな文書訂正が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** local success can hide host-memory-dependent tests, and a timeout warning changes the security gate at every milestone unless explicitly bounded. ／ ローカル合格はホストメモリ依存の試験を隠し得る。時間切れの警告化は明示的に限定しなければ全節目の安全性判定を変える。
- Applies to: RCOSDP/RDM-developer-guide PR #33, head `abb89dc4b5ac5f0b6063857e12ce31838edf58f9`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [R1](2026-11-06_RDM-developer-guide_PR33_Startup_Fixes_r1.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Changes requested.** R2-01 and R2-02 are P2, R2-03 is P3. This is a review verdict, not GitHub approval. The supplied worktree and remote head matched; changes since `38768ab` and the R1 record were inspected. No implementation changes, commit, push, approval, merge, installation or Docker state changes were performed.

**R2-01 — P2: isolate host memory in the new VM tests.** [test_compose.py](../../installer/tests/test_compose.py), lines 283–323, stubs `docker info` but leaves `detect_memory_gib()` reading the real machine. Both `test_memory_budget_uses_docker_vm_when_smaller` and `test_sum_of_floors_fits_the_documented_minimum_vm` therefore fail on a host below the core floor even when the fake VM has 48/24 GiB. Both Python 3.11 and 3.12 jobs fail with `10 != 0` in [CI run 42165059610](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165059610). Independently setting the detected host to 7 GiB reproduced exit 10 for both fake VMs: the 23-service floor is 16,320 MiB but the selected budget is 5,017 MiB. Mock host memory to a known larger value and assert the selected VM value exactly; separately test a smaller host. Preserve production's smaller-of-host-and-engine rule. R1-04's production fix is correct, but its verification is not complete until these jobs pass.

**R2-02 — P2: retain an incomplete result for unbounded Semgrep timeouts.** [scan.py](../../installer/grdm_dev/scan.py), lines 784–799, removes all errors whose type starts with `Timeout` from scanner problems, regardless of milestone, affected file count or rule coverage. Lines 1044–1052 then allow exit 0. Using the existing fake runner with a valid baseline, empty findings and one timeout reproduced `gate=pass`, exit 0 at M1, M4 and M5. A security rule that never completed cannot establish a clean result; three timeouts can also drop the rest of a file. This weakens the previous fail-closed behavior beyond the run-20 operator-copy problem. Keep the 30-second timeout and runtime-copy exclusion, but make unresolved timeouts incomplete (51), or define an explicitly bounded early-milestone policy in SPEC-03/ADR-03 and keep strict milestones fail-closed, with regression tests for mixed errors and M4/M5. The module and function docstrings still promise that scanner errors mean incomplete. The inspected successful real report had Semgrep `ok` with no timeout warning, so it does not demonstrate a need to exempt timeouts at strict milestones.

**R2-03 — P3: finish the evidence/documentation reconciliation.** The PR body still says 352 installer tests after R1, although this head has 354, and its change summary still says the default `up` wait is 900 seconds although the implementation is 1800. Its tests should distinguish local success from the two failed CI jobs. The Japanese authoritative M2 row in [status/README.md](../status/README.md) says acceptance is unexecuted (`未実施`) while §2b records a first real run with 0/12 passing; use “not passed” in both languages. The historical run-18 wording can remain explicitly historical.

### R1 disposition

- **R1-01: implementation resolved; Linux execution evidence remains.** The new `elasticsearch_data_init.json` (template removed by ADR-07, PR #34) runs `chown 101:101 /data` once, with root and only CHOWN restored, read-only root and no-new-privileges retained. Elasticsearch depends on successful completion. This fixes ownership of a fresh host-owned directory without recursive ownership changes. Run 19 records init exit 0 on Docker Desktop; it does not test Linux ownership enforcement on a uid-1000 directory. No such Linux runtime validation was performed here.
- **R1-02: implementation resolved; requested regression test remains.** `SERVICE_IMAGE` is populated from `svc.image`, and Ember fingerprints `GRDM_IMAGE`, recipe version 1 and the existing URL inputs before deciding to reuse `dist`. The current prebuilt reference is digest-pinned. The changed tests contain no focused image-change/restart reuse test; add the requested test proving a changed digest rebuilds and unchanged inputs reuse output.
- **R1-03: resolved.** SPEC-03 §3.3 and ADR-03 §3.2 now explicitly distinguish bounded hardening exceptions from the vulnerability allow-list, name relaxed controls, reason, review date and removal milestone, and describe reporting/enforcement. Existing tests cover expired exceptions, root forms, matching capabilities and unconditional privileged/no-new-privileges failures. Milestone limits on exception growth/removal remain policy obligations, not a claim of a new automated count gate.
- **R1-04: implementation resolved; tests blocked by R2-01.** Infeasible floors raise `MemoryBudgetError` and return 10 before Compose output; explicit memory overrides permit documented overcommit. The 16,320 MiB core floor fits a 24 GiB budget. SPEC-02 §8 describes the override and minimum memory.
- **R1-05: substantially resolved, residual R2-03.** DEMO-20 corrects run 15 to `up=0`, network health failure; scanner totals now separate Trivy from ZAP and identify the report's M1 milestone. The PR body fixes scanner counts but its test count is stale.
- **R1-06: original corrections resolved, residual R2-03.** Both authoritative rows now report run-18 completion and DEMO-20 retains failure for unknown-owner wildcard listeners. The newer acceptance attempt requires the small Japanese row correction noted above.

### New changes and execution limits

Ember no longer waits for web/api, so its static build can run alongside database initialisation. `osf_init` now retries institution population 180 times with 10-second sleeps; the “30 minutes” is approximate because each attempt also takes time. The lifecycle wait is 1800 seconds. These reduce serial waiting but do not fix the recorded 38-minute emulated Elasticsearch start. That root cause is explicitly assigned to the follow-up native-image/ADR-07 work, not demanded in this PR. Run 20 continued run 19's state; it is not evidence of a new uninterrupted fresh-volume installation of this exact head. Browser acceptance and native Linux ownership validation remain outstanding.

The `.gitignore` addition excludes operator copies named `runtime.*/`. The Semgrep tests verify the new arguments and mixed-error failure, but intentionally encode the unbounded success behavior identified in R2-02. No actual scanner or Docker operation was rerun by this review.

### Evidence and checks

Observed results from the supplied worktree, not canonical manifest data:

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","PASS: 354 tests, 10 skipped"
  "python3 -m unittest discover -s tools/tests","PASS: 90 tests"
  "python3 tools/manifest_check.py","PASS: zero findings"
  "python3 tools/docs_check.py","PASS: 93 checked, 8 exempt, 21 non-failing warnings"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","FAIL: Python 3.11/3.12 unit jobs; other 6 checks pass"
```

Read the supplied scratchpad logs `install-run19-coldstart.log`, `install-run20-coldstart-continued.log` and `install-run20b-scan-report.log`: respectively exit 40 at `up`, exit 51 at `scan` after up/health success, and successful scan/report rerun. The main-checkout `runtime/reports/scan_latest.json` was readable at first inspection: M1, commit `5bde10e`, exit 0, Trivy/Semgrep/gitleaks/ZAP all `ok`, targets 22/4/1/3, no Semgrep warnings. It was absent at a second metadata read; it is mutable historical evidence, not an immutable run of `abb89dc`. The reviewer did not modify it. The new untracked review is checked separately with `tools.docs_check.check_file` because the normal checker lists tracked files only.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**修正要求。** R2-01・R2-02 は P2、R2-03 は P3。レビュー判定であり GitHub の承認ではない。指定 worktree とリモート先端の一致を確認し、`38768ab` 以降の変更と R1 記録を検査した。実装変更、commit、push、承認、merge、導入実行、Docker 状態変更は行っていない。

**R2-01 — P2: 新しい VM 試験のホストメモリを固定する。** [test_compose.py](../../installer/tests/test_compose.py) 283〜323 行は `docker info` だけを差し替え、`detect_memory_gib()` は実機を読む。そのため `test_memory_budget_uses_docker_vm_when_smaller` と `test_sum_of_floors_fits_the_documented_minimum_vm` は、模擬 VM が48／24 GiB でもホストが core の下限未満なら失敗する。[CI run 42165059610](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165059610) の Python 3.11・3.12 は両方とも `10 != 0` で失敗した。検出ホストを7 GiB に固定した独立再現でも両 VM は終了10となった。23サービスの下限合計16,320 MiB に対し選択予算は5,017 MiB。ホストメモリを既知の大きい値へ差し替え、選択された VM 値を等値で検査し、小さいホストの場合は別に試験すること。本番のホスト／engine の小さい方を採る規則は維持する。R1-04 の本番修正は正しいが、CI 合格まで検証は未完了。

**R2-02 — P2: 無制限の Semgrep 時間切れを未完了として残す。** [scan.py](../../installer/grdm_dev/scan.py) 784〜799 行は、節目・対象ファイル数・規則の検査範囲によらず、型が `Timeout` で始まる全エラーを問題一覧から除く。1044〜1052 行はその結果、終了0を許す。既存の模擬 runner に正常な基本対策、検出事項なし、時間切れ1件を与えると M1・M4・M5 のすべてで `gate=pass`、終了0を再現した。完了しなかった安全性規則から問題なしとは言えず、3回の時間切れでファイルの残りも除外され得る。第20回の操作者のコピー問題を超えて、従来の安全側に失敗する規則を弱めている。30秒への延長と runtime コピー除外は残し、未解決の時間切れを未完了（51）にするか、SPEC-03／ADR-03 に初期節目だけの限定方針を定め、厳格な節目は未完了として失敗させ、混在エラーと M4/M5 の回帰試験を追加すること。モジュールと関数の説明も依然としてスキャナ自身のエラーは未完了と約束している。確認した実機成功報告の Semgrep は時間切れ警告なしの `ok` で、厳格な節目で例外が必要という証拠にはならない。

**R2-03 — P3: 証跡と文書の整合を仕上げる。** PR 本文は R1 後の installer 試験352件とするが、本先端は354件で、変更要約の `up` 既定900秒も実装1800秒と異なる。検証欄はローカル成功と CI 2件失敗を区別すること。[status/README.md](../status/README.md) の日本語の正本 M2 行は受入「未実施」とする一方、§2b は実機初回0/12合格を記録しているため、両言語とも「未合格」とすること。第18回の記述は過去の記録と明示して残せる。

### R1 各項目の扱い

- **R1-01: 実装修正済み。Linux 実行証跡は残件。** 新しい `elasticsearch_data_init.json` (template removed by ADR-07, PR #34) は root と CHOWN だけで `chown 101:101 /data` を一度実行し、読取専用 root と no-new-privileges を維持する。Elasticsearch は成功終了を待つ。再帰変更をせず新規のホスト所有ディレクトリを修正する。第19回は Docker Desktop で init 終了0だが、Linux の uid 1000 所有ディレクトリでの権限検証ではなく、本レビューでも Linux 実行はしていない。
- **R1-02: 実装修正済み。要求した回帰試験は残件。** `SERVICE_IMAGE` は `svc.image` から入り、Ember は既存 URL に加えて `GRDM_IMAGE` と手順版1を指紋へ含めて dist 再利用を判定する。現在の prebuilt は digest 固定。変更した試験にはイメージ変更／再起動再利用の専用試験がないため、digest 変更で再構築し、同じ入力なら再利用する要求済み試験を追加すること。
- **R1-03: 解決。** SPEC-03 §3.3 と ADR-03 §3.2 が限定された堅牢化例外と脆弱性許容リストを区別し、緩める統制・理由・見直し日・除去節目・報告と検査を明示する。既存試験は期限切れ、root の各表記、capability の一致、privileged／no-new-privileges の無条件失敗を検査する。節目ごとの件数増加・除去制限は方針上の義務であり、新しい自動件数検査の実装を確認したという意味ではない。
- **R1-04: 実装修正済み。試験は R2-01 が未解決。** 下限超過は `MemoryBudgetError` で Compose 出力前に終了10となり、明示メモリ指定は文書化した過剰割当を許す。core の下限16,320 MiB は24 GiB の予算に収まる。SPEC-02 §8 は上書きと必要メモリを説明する。
- **R1-05: 概ね解決、R2-03 が残件。** DEMO-20 は第15回を `up=0`・network health 失敗へ訂正し、Trivy／ZAP の件数と報告の M1 節目を区別した。PR 本文もスキャナ件数は訂正したが試験件数が古い。
- **R1-06: 元の訂正は解決、R2-03 が残件。** 正本の英和両行は第18回完走を反映し、DEMO-20 は所有者不明のワイルドカードの失敗を維持した。新しい受入実行に合わせた日本語行の小修正が必要。

### 追加変更と実行の限界

Ember は web/api を待たず、静的ビルドを DB 初期化と並行できる。`osf_init` は機関投入を10秒間隔で180回まで再試行する。「30分」は各試行の実行時間もあるため概算である。lifecycle の待機は1800秒。直列待ちを減らすが、記録されたエミュレーション下の Elasticsearch 起動38分を解消しない。その根本原因は指定どおり後続の native image／ADR-07 作業に分離し、本 PR での修正を要求しない。第20回は第19回の状態を継続したため、この先端を新規ボリュームから中断なしで一度に導入できた証跡ではない。ブラウザ受入と Linux 所有権検証は残件。

`.gitignore` は操作者のコピー `runtime.*/` を除外する。Semgrep 試験は引数変更と混在エラーの失敗を検査するが、R2-02 の無制限の成功も意図的に固定している。本レビューでは実スキャナや Docker 操作を再実行していない。

### 証跡と検証

指定 worktree での観測結果であり、manifest の正本データではない。

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","合格: 354 件、10 skip"
  "python3 -m unittest discover -s tools/tests","合格: 90 件"
  "python3 tools/manifest_check.py","合格: 指摘 0"
  "python3 tools/docs_check.py","合格: 93 検査、8 除外、非失敗の警告 21"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","失敗: Python 3.11/3.12 unit jobs、他 6 checks は合格"
```

指定 scratchpad の `install-run19-coldstart.log`、`install-run20-coldstart-continued.log`、`install-run20b-scan-report.log` を確認した。順に up で終了40、up/health 成功後 scan で終了51、scan/report 再実行成功である。main checkout の `runtime/reports/scan_latest.json` は初回閲覧時に M1、記録コミット `5bde10e`、終了0、Trivy／Semgrep／gitleaks／ZAP はすべて `ok`、対象22/4/1/3、Semgrep 警告なしだった。2回目のメタデータ確認時にはファイルが存在しなかったため、変更可能な過去の証跡であり `abb89dc` の不変の実行記録ではない。レビュワは変更していない。通常の文書検査は追跡済みだけを列挙するので、新規未追跡のレビューは `tools.docs_check.check_file` で別途検査する。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| CI | Automated checks run on the hosted change. | 提案した変更をサーバー上で自動検査する仕組み。 |
| Fingerprint | Stored input identity used to decide whether output can be reused. | 成果を再利用してよいか判定する入力の識別値。 |
| Fail-closed | An incomplete safety check prevents success. | 安全性検査が未完了なら成功させない扱い。 |
| Memory floor | Minimum memory assigned to a service. | サービスへ割り当てるメモリの下限。 |
| Regression test | A repeatable check that prevents a fixed defect returning. | 修正した不具合の再発を防ぐ繰り返し可能な検査。 |
| P2 / P3 | Medium / low review priority. | 中／低のレビュー優先度。 |

Shared terminology: [REF-01](../reference/REF-01_Glossary.md).
