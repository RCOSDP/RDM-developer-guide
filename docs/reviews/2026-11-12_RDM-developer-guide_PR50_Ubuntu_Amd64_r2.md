# REV-PR50-r2 Ubuntu amd64 installer review / Ubuntu amd64 インストーラーレビュー

> **Summary:** Pass at a34083b: R1–R6 are closed in the requested scope. The additional C4 evidence establishes two passing cases on a locally patched copy, not a clean full-suite pass or a completed uninterrupted installation.
> **概要:** a34083b の判定は pass。指定範囲の R1–R6 は解消した。追加 C4 証跡はローカルでパッチを当てたコピーの2ケース合格を示し、変更なしの全試験合格や中断しない導入完了を示すものではない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-12. **Learned:** Publication must redact provenance locations and body artifact paths as well as link destinations; only these location labels changed, with judgments, findings, test results and earlier version lines preserved. ／ 公開時はリンク先だけでなく出典の場所と本文の成果物パスも秘匿する。場所の表記のみを変更し、判定、指摘、試験結果、過去の版行を保持した。
- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `2026-11-12_RDM-developer-guide_PR50_Ubuntu_Amd64_r2.md`. Publication 0.3 redacts only original-file locations, local artifact paths and the guest checkout location to basenames or neutral artifact names; prior publication link changes remain. Judgments, findings, test results and earlier version lines are unchanged. ／ 公開版 0.3 では原本の場所、ローカル成果物のパス、ゲスト配置先のみをファイル名または中立的な成果物名に置換し、前公開版のリンク修正を維持する。判定、指摘、試験結果、過去の版行は変更しない。
- Version / 版: 0.1 — 2026-11-12. **Learned:** a passing rerun is interpretable only with its changed conditions and scope; parsing the actual data blocks also catches issues that the general documentation checker does not cover. ／ 再試験の合格は、変えた条件と対象範囲を併記して初めて解釈できる。またデータブロックを実際に解析すると、一般の文書検査が扱わない問題も見つかる。
- Applies to: RCOSDP/RDM-developer-guide PR #50, round 2; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](../reviews/README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md) · [Round 1](2026-11-12_RDM-developer-guide_PR50_Ubuntu_Amd64_r1.md).
- Used by: the coordinator's PR #50 review decision. Kept outside Git; relative source links resolve into the independent review clone. ／ コーディネーターの PR #50 判定に使用する。Git 外に保存し、ソースへの相対リンクは独立レビュー用クローンを指す。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and boundaries

**Pass. No blocking findings remain in R1–R6 or the added C4 evidence.** Reviewed a clean independent clone at `a34083bc19117b36e3265e70fd458e97f788130d`, against base `a005acfb5ec06064102170b038a58458d6a7d062`, with correction comparison against round-1 head `7ac6e5c6c162753ae1c02d7e1bcaac76863183cd`. GitHub still reported the assigned head and an open PR before posting the review comment. This verdict is a review result, not a GitHub approval or an acceptance certification for native amd64.

### Closure of round-1 findings

| Finding | Result | Evidence |
|---|---|---|
| R1: executed stages | Closed | DEMO-22 L119/L279 limits the executed sequence to `up`, `health --network`, and `accept`; explicitly excludes `scan` and `report`; disclaims proof of the single command or unrun stages. L90/L250 and L168/L328 exclude imported osf.io and wiki-frontend from the nine VM-built images. The version header now names the actual stages. |
| R2: evidence labels | Closed | DEMO-22 L108–115/L268–275 separates observed compile times from the unfinished whole-step extrapolation, the working-day/nine-hour estimate, and unmeasured native expectations. L164/L324 labels the DNS explanation an undiagnosed hypothesis. L162/L322 and SPEC-02 L187/L430 say `--timeout` applies only to `up`, not `build`; the environment guide removes the categorical working-day claim. |
| R3: attempts and skips | Closed | DEMO-22 L145–160/L305–320 includes all five runs, including the second unseeded attempt, and the ten unconditional `M3` skips. The five result files, collector counts, and JUnit totals agree. S1–S5 source modules retain unconditional `pytest.mark.skip(reason="M3")`. |
| R4: TOON row counts | Closed | Both `osf_compile` arrays declare four rows. Every one of DEMO-22's 16 fenced TOON blocks parses with `tools.manifest_check.parse_toon`. This is a DEMO-22 scope result; see the separate pre-existing SPEC-02 limitation below. |
| R5: zero timeout | Closed | `installer/grdm_dev/install.py` L50 uses `timeout is not None`; L73 forwards the parsed value. `test_preflight.py` L224–233 exercises the actual CLI parser and plan, asserts `['up', '--no-open', '--timeout', '0']`, and distinguishes omitted `None`. Both focused and full tests pass. |
| R6: macOS key absence | Closed | `host.py` L394–395 excludes macOS before the amd64 branch, and L498–499 removes inapplicable empty keys from `as_report`. `test_preflight.py` L303–310 asserts key absence for both arm64 and x86_64; L312–315 also covers no amd64 services. |

The English and Japanese corrections carry the same scope and limits. No new native execution was required to resolve the documentary findings.

### Acceptance evidence and added C4 run

The following is a review-local summary of the committed records, not a new acceptance execution. Detailed cross-checks are in the evidence audit (`pr50-r2-evidence-audit.json`).

```toon
runs[5]{run_id,seeded,passed,failed,error,skipped,pytest_exit}:
  acc-20261112T083417Z-f2b524,false,1,3,8,10,1
  acc-20261112T085656Z-c69ad2,true,11,1,0,10,1
  acc-20261112T092035Z-e4c24d,false,0,1,1,0,1
  acc-20261112T092701Z-876a61,true,1,1,0,0,1
  acc-20261112T095258Z-308ef1,true,2,0,0,0,0
```

All 25 files in the five run folders are tracked at the reviewed head. Each `results.toon` exactly matches the current encoder applied to its adjacent `results.json`; the collector statuses and JUnit totals match the JSON summary. Encoder equality is distinct from parsing arbitrary report TOON with the manifest-specific parser.

The [new run folder](../demo/runs/acc-20261112T095258Z-308ef1/results.toon) contains exactly `collector.json`, `junit.xml`, `pytest.log`, `results.json`, and `results.toon`. All five were read. It records only C4, seeded, two passes, exit 0: success 182550 ms (JUnit 182.551 s, reported as 182.6 s) with HTTP 200, and rejection 107832 ms with WebSocket close code 4401. Pytest took 290.86 s and printed two `record_property`/`xunit2` compatibility warnings; 745761 ms in the JSON is the whole acceptance-command duration, not C4 success time. The precheck reports 24 healthy services. There are no trace archives, screenshots, or evidence attachments.

DEMO-22 L160/L320 explicitly discloses the uncommitted VM-only patch: page/click/selector waits to 600 s, collaboration bound to 300 s, login waits to 300 s, and per-test timeout to 1500 s. It calls the result one rerun of one scenario on that patched copy, expressly rejects a clean 12/12 claim, and does not infer native performance. The committed acceptance sources are unchanged from the PR base and retain `COLLAB_BOUND_MS = 30_000`, 30/60-second page/login-related waits, and `TEST_TIMEOUT_S = 120`. The local patch itself was not supplied as a reproducible artifact; its exact content is author-reported, while the two passing results are directly recorded. The result is consistent with slow execution but does not isolate the cause.

Content review of the new five files and targeted searches across all 25 found no credential values, account identities, email addresses, personal home paths, or scratch paths. The new JUnit hostname is the documented generic VM name `lima-grdm-ubuntu2404-amd64`, not a personal/account identity. The four pattern hits in older files are redacted `token = ***` traceback lines. This is a bounded artifact-content audit, not a stack security scan.

### Validation and remaining limits

The four requested commands ran from the independent clone with the system PATH `python3` (Homebrew Python 3.15.2; resolved executable `/opt/homebrew/opt/python@3.15/bin/python3.15`), without a virtual environment. Actual subprocess return codes were retained in check results (`pr50-r2-checks.json`).

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662 tests; 10 skipped; 61.683 s"
  "python3 -m unittest discover -s tools/tests",0,"93 tests; 3.309 s"
  "python3 tools/docs_check.py",0,"177 checked; 8 exempt; 43 warnings"
  "python3 tools/manifest_check.py",0,"0 findings; 754 policy-scanned files; 63 non-UTF-8 files skipped"
```

Logs: installer tests (`pr50-r2-installer-tests.log`), tools tests (`pr50-r2-tools-tests.log`), docs check (`pr50-r2-docs-check.log`), manifest check (`pr50-r2-manifest-check.log`). The three focused regression tests also passed (0.076 s, exit 0). The installer log contains expected negative-path messages, a Python fork deprecation warning, and a foreign-listener warning; the final unittest status and process exit both indicate success. Skips and documentation warnings remain explicit limits.

An expanded parsing audit found two untouched SPEC-02 directory-layout blocks (L239/L482) that `parse_toon` rejects at slash-containing keys such as `installer/install.sh`. Both blocks are byte-identical to the PR base. Six other SPEC-02 blocks parse; the environment guide has no TOON blocks. The initial broad assertion therefore failed, and a separate scoped DEMO-22 check passed 16/16 with exit 0. This existing incompatibility does not reopen R4's two corrected DEMO-22 compile arrays, but a repository-wide “all TOON parses” claim would be false.

The earlier PR-body summary still contains superseded completion/native-time wording, followed by an explicit round-1 correction section. The review verdict applies to the committed corrections; aligning the earlier summary with that correction would improve clarity without changing the reviewed code.

An uninterrupted amd64 installation, native amd64 measurements, `scan`/`report` on this stack, and a clean full acceptance run remain unproven and are kept open in DEMO-22. No acceptance rerun, Docker/VM state changes, pruning, live `runtime/.env` access, source edits, commits, pushes, approval, merge, or close were performed. The clone's final Git status is clean. The only GitHub write is the single [Japanese PR conversation comment for round 2](https://github.com/RCOSDP/RDM-developer-guide/pull/50#issuecomment-6820832191).

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Pass（合格）。R1–R6 と追加 C4 証跡にブロッキング指摘は残らない。** 独立したクリーンクローンで head `a34083bc19117b36e3265e70fd458e97f788130d`、base `a005acfb5ec06064102170b038a58458d6a7d062` を確認し、修正は r1 の head `7ac6e5c6c162753ae1c02d7e1bcaac76863183cd` と比較した。コメント投稿前にも GitHub 上の head が割当どおりで、PR が open であることを確認した。この判定はレビュー結果であり、GitHub の approve 操作や実機 amd64 の受入認証ではない。

### r1 指摘の解消

| 指摘 | 結果 | 根拠 |
|---|---|---|
| R1: 実施工程 | 解消 | DEMO-22 L119/L279 は実施を `up`、`health --network`、`accept` に限定し、`scan`・`report` の未実施、単一コマンドや未実施工程の証明ではないことを明記。L90/L250・L168/L328 は VM で組んだ9イメージから輸入した osf.io・wiki-frontend を除外。版ヘッダも実際の工程を列挙。 |
| R2: 証拠の区別 | 解消 | DEMO-22 L108–115/L268–275 はコンパイルの観察、未完の手順全体・営業日・約9時間の外挿、実機の未測定の期待を区別。L164/L324 は DNS の原因説明を未診断の仮説とする。L162/L322、SPEC-02 L187/L430 は timeout が `up` のみで `build` には効かないことを明記。環境手引きも営業日の断言を除去。 |
| R3: 試行と skip | 解消 | DEMO-22 L145–160/L305–320 は seed なしの2回目を含む全5実行と、無条件の `M3` skip 10件を記載。5実行の JSON・collector・JUnit の件数は一致。S1–S5 のソースも無条件の `pytest.mark.skip(reason="M3")` を保持。 |
| R4: TOON 行数 | 解消 | 両方の `osf_compile` は4行宣言。DEMO-22 の全16 TOON ブロックが `tools.manifest_check.parse_toon` で解析成功。DEMO-22 の範囲の判定であり、既存 SPEC-02 の別件は後述。 |
| R5: timeout 0 | 解消 | `install.py` L50 は `timeout is not None`、L73 は parser の値を転送。`test_preflight.py` L224–233 は実 parser から plan へ通し、`['up', '--no-open', '--timeout', '0']` を確認、省略時の `None` と区別。個別・全体試験とも成功。 |
| R6: macOS のキー不在 | 解消 | `host.py` L394–395 は amd64 分岐前に macOS を除外、L498–499 は対象外の空キーを報告から除去。`test_preflight.py` L303–310 は arm64・x86_64 の両方でキー自体の不在を検査、L312–315 は amd64 サービス無しも検査。 |

英語と日本語は同じ範囲・限界を記載する。文書の指摘解消のために新しい実機実行を要求する必要は無かった。

### 受入証跡と追加 C4 実行

次はコミット済み記録のレビュー用集計であり、新たな受入実行ではない。詳細は証跡監査 (`pr50-r2-evidence-audit.json`)に保存した。

```toon
runs[5]{run_id,seeded,passed,failed,error,skipped,pytest_exit}:
  acc-20261112T083417Z-f2b524,false,1,3,8,10,1
  acc-20261112T085656Z-c69ad2,true,11,1,0,10,1
  acc-20261112T092035Z-e4c24d,false,0,1,1,0,1
  acc-20261112T092701Z-876a61,true,1,1,0,0,1
  acc-20261112T095258Z-308ef1,true,2,0,0,0,0
```

5フォルダの25ファイルはすべて対象 head の追跡対象。各 `results.toon` は隣接する `results.json` を現行 encoder に渡した結果と完全一致し、collector・JUnit の件数も JSON 集計と一致した。encoder 一致と、manifest 用 parser による任意の報告 TOON の解析は別の検査である。

[追加実行のフォルダ](../demo/runs/acc-20261112T095258Z-308ef1/results.toon)は `collector.json`、`junit.xml`、`pytest.log`、`results.json`、`results.toon` の5ファイルだけで、全内容を確認した。対象は seed ありの C4 のみ、2合格、終了0。success は182550 ms（JUnit は182.551秒、記載は182.6秒）・HTTP 200、rejection は107832 ms・WebSocket close code 4401。pytest は290.86秒、`record_property` と `xunit2` の互換性警告が2件。JSON の745761 msは受入コマンド全体であり、C4 success の時間ではない。precheck は24サービス healthy を記録。trace archive・スクリーンショット・証跡添付は無い。

DEMO-22 L160/L320 は未コミット・VM 作業コピーだけの変更を明記する。ページ・クリック・selector は600秒、collaboration bound は300秒、ログインは300秒、試験全体は1500秒。パッチ適用コピーの1シナリオ1再実行であり、変更なしの12/12ではなく、実機の速度も示さないと明記している。コミット済み受入ソースは PR base から変更されず、`COLLAB_BOUND_MS = 30_000`、ページ・ログイン関連の30/60秒、`TEST_TIMEOUT_S = 120` を保持。実際のローカルパッチは再現可能な artifact として提供されていないため、その詳細は執筆者の報告であり、2件合格は記録から直接確認した。結果は処理の遅さと整合するが、原因の切り分けまでは示さない。

新規5ファイルの内容確認と25ファイル全体の対象検索では、資格情報値、アカウント識別情報、メールアドレス、個人のホームパス、scratch パスを検出しなかった。新規 JUnit の hostname は記載済みの一般的な VM 名 `lima-grdm-ubuntu2404-amd64` で、個人・アカウント識別子ではない。旧記録のパターン一致4箇所は伏字の `token = ***`。これは artifact 内容の限定監査であり、stack のセキュリティ scan ではない。

### 検証と残る限界

指定4コマンドは独立クローンから、仮想環境を使わずシステム PATH の `python3`（Homebrew Python 3.15.2、実体 `/opt/homebrew/opt/python@3.15/bin/python3.15`）で実行した。実際の subprocess 終了コードを検査結果 (`pr50-r2-checks.json`)に保存した。

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"662件、10件skip、61.683秒"
  "python3 -m unittest discover -s tools/tests",0,"93件、3.309秒"
  "python3 tools/docs_check.py",0,"177ファイル検査、8除外、43警告"
  "python3 tools/manifest_check.py",0,"指摘0、policyは754ファイル検査、非UTF-8の63ファイル除外"
```

ログ: installer tests (`pr50-r2-installer-tests.log`)、tools tests (`pr50-r2-tools-tests.log`)、docs check (`pr50-r2-docs-check.log`)、manifest check (`pr50-r2-manifest-check.log`)。個別の回帰試験3件も成功した（0.076秒、終了0）。installer ログには否定系の想定メッセージ、Python の fork 非推奨警告、foreign-listener 警告があるが、最終 unittest 結果とプロセス終了コードはともに成功。skip と文書警告は限界として残す。

追加の広い解析監査では、SPEC-02 の未変更のディレクトリ一覧2ブロック（L239/L482）が `installer/install.sh` のようなスラッシュ入りキーで `parse_toon` に拒否された。両ブロックとも PR base と完全一致する。他の SPEC-02 の6ブロックは解析でき、環境手引きには TOON ブロックが無い。そのため最初の広い assertion は失敗し、別途 DEMO-22 に絞った検査は16/16、終了0だった。この既存の非互換は R4 の修正済みコンパイル配列2件を再オープンするものではないが、「リポジトリ全体の TOON がすべて解析成功」とは言えない。

PR 本文の前半には古い完了・実機所要時間の表現が残り、後半に明示的な r1 修正説明が追記されている。判定対象はコミット済みの修正である。前半も修正説明に揃えると、コードに影響せず読み違いを減らせる。

中断しない amd64 導入、実機 amd64 の測定、この stack の `scan`・`report`、変更なしの受入全件合格は未証明のままで、DEMO-22 も残件として維持する。受入再実行、Docker・VM 状態変更、prune、稼働中の `runtime/.env` へのアクセス、ソース編集、commit、push、approve、merge、close はしていない。クローンの最終 Git status は clean。GitHub への書き込みは [r2 の日本語 PR 会話コメント1件](https://github.com/RCOSDP/RDM-developer-guide/pull/50#issuecomment-6820832191)だけである。
