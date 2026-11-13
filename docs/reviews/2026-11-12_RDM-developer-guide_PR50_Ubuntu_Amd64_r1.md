# REV-PR50-r1 Ubuntu amd64 installer review / Ubuntu amd64 インストーラーレビュー

> **Summary:** Changes requested at head 7ac6e5c. All four required checks pass, but the completion claims, acceptance summary, TOON data and two installer edge cases need correction.
> **概要:** head 7ac6e5c の判定は changes requested。必須の4検査はすべて成功したが、完了の主張、受入集計、TOON データ、インストーラーの境界条件2件に修正が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only link destinations for publication: scratch-path links were replaced by repository-relative links or plain-text references. ／ REV は公開のためリンク先のみを変更し、作業用パスへのリンクをリポジトリ相対リンクまたは平文の参照に置き換えた。
- Provenance / 出典: Original file / 原本: `/private/tmp/claude-501/-Users-komiyama-ai-development-GitHub-RDM-developer-guide/8baac84b-080f-4104-a2b5-7416702c57e1/scratchpad/reviews/2026-11-12_RDM-developer-guide_PR50_Ubuntu_Amd64_r1.md`. All other original text is retained verbatim below, including the original version and review-time context. ／ 以下は元の版とレビュー時点の文脈を含め、それ以外の原文をそのまま保持する。
- Version / 版: 0.1 — 2026-11-12. **Learned:** passing repository checks does not establish that a narrative matches its committed evidence; an omitted failed attempt and an unparsed TOON row count survived those checks. ／ リポジトリの検査が成功しても、説明がコミット済み証跡と一致する証明にはならない。失敗した実行の集計漏れと TOON の行数不一致は検査を通過した。
- Applies to: RCOSDP/RDM-developer-guide PR #50, round 1; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](../reviews/README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md).
- Used by: the coordinator's PR #50 correction and re-review decision. This report remains outside Git; relative links resolve into the independent review clone.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** Reviewed the clean, independent clone at `7ac6e5c6c162753ae1c02d7e1bcaac76863183cd` against `a005acfb5ec06064102170b038a58458d6a7d062`. The ordinary positive timeout forwarding and Ubuntu amd64/Linux arm64 status paths work. The seeded acceptance evidence supports 11/12 core passes and two C4 success failures at the wiki page's 30-second `goto`; it does not establish a successful uninterrupted install or completion of every post-build step.

No source changes, commits, pushes, approval, merge, close, VM operations, Docker state changes, image/cache pruning, or access to the live `runtime/.env` were performed. Unit tests used their isolated temporary fixtures. Posted exactly one [Japanese PR conversation comment](https://github.com/RCOSDP/RDM-developer-guide/pull/50#issuecomment-6820295801) for this review.

### Findings

1. **R1 — P2: remove the claim that unexecuted stages ran.** [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md), L118 and L274, explicitly lists `scan` and `report` among the stages run and calls the result proof of everything after build. The same record says they were not run at L139/L164 and L295/L320; acceptance remains 11/12. Replace this with the actual sequence (`up`, `health --network`, acceptance attempts), explicitly retain the unrun stages and the failed test, and limit the header's “nothing behind build is specific to amd64” claim at L8. Also exclude imported wiki-frontend from “all the other images ... built natively” at L89/L245. These contradictions otherwise read as completion of an untested security gate.

2. **R2 — P2: distinguish measurements from extrapolation and untested causes.** DEMO-22 L114/L157/L159/L163 and L270/L313/L315/L319 assert native amd64 takes minutes, never needs a longer wait, and that transient DNS trouble is QEMU networking rather than an installer fault. No native amd64 comparison or DNS diagnosis is committed; the only added artifacts are acceptance outputs. The emulated build stopped after 5 h 12 min, so a full working-day failure and a roughly nine-hour completion time are estimates, not completed measurements. [SPEC-02](../spec/02_installer_cli.md) L8 and the [environment guide](../guides/environment/README.md) L8 repeat the categorical working-day statement; SPEC-02 also connects compile time to an option that only affects `up`. Keep the reported numpy 971/118 s, pandas 4298/411 s, unfinished scipy >6400 s and Rosetta image 64 min 11 s as author-recorded observations, label unsupported extrapolations/hypotheses, and say explicitly that `--timeout` cannot shorten or extend `build`. A new native run is not required merely to make this account honest.

3. **R3 — P2: account for all four attempts and the actual skip reason.** DEMO-22 L144–153 and L300–309 says three attempts / one omission and lists only three rows, although its own fourth link points to [acc-20261112T092035Z-e4c24d](../demo/runs/acc-20261112T092035Z-e4c24d/results.toon). That unseeded C4 attempt records 0 passed, 1 failed, 1 error. Add the row and correct the headings in both languages; describe the two wiki `goto` failures specifically as the seeded runs. The 10 skips are recorded as `M3` in the seeded [pytest log](../demo/runs/acc-20261112T085656Z-c69ad2/pytest.log), L108–117, and the S1–S5 modules have unconditional `pytest.mark.skip(reason="M3")`; they were not dynamically skipped because the core profile lacked those services. Preserve that distinction in the table note.

4. **R4 — P2: correct both invalid compile data blocks.** DEMO-22 L107 and L263 declares `osf_compile[3]` but provides four rows including the whole RUN step. The repository's `tools.manifest_check.parse_toon` rejects both blocks with `osf_compile[3] has more rows than declared`. Change the count to four or separate the total. `docs_check` currently checks only declared canonical SHA parity, so its success does not validate this syntax.

5. **R5 — P2: forward an explicitly supplied zero timeout.** [install.py](../../installer/grdm_dev/install.py), L50, tests `if timeout` rather than `if timeout is not None`. Reproduction with the real parser and `plan_steps` gives `['up', '--no-open']` for `install --timeout 0`, exactly the same as omission. Direct `up --timeout 0` performs its initial health check without polling, while the install wrapper silently falls back to 1800/5400 seconds. Preserve zero and add a focused parser-to-plan regression test. The existing 7200-second test passes but misses this boundary.

6. **R6 — P3: make the macOS report match the documented absence.** [host.py](../../installer/grdm_dev/host.py), L146/L394–396 and L490–496, leaves `amd64_emulation` in `asdict(info)` even when empty, so macOS arm64 emits an empty field; macOS amd64 takes the unconditional amd64 branch and emits “not needed”. SPEC-02 L128/L371 and DEMO-22 say the row is absent on macOS. Exclude macOS before setting the field and omit it during report serialization when not applicable, or explicitly revise the intended contract. The new test at [test_preflight.py](../../installer/tests/test_preflight.py), L292–295, only excludes two nonempty strings; assert key absence and cover both Mac architectures.

### Evidence audit and limits

All 20 files in the four `acc-20261112T*` directories are committed. All four referenced `results.toon` files exist at the reviewed head and exactly match the current encoder's output from their adjacent `results.json`; JUnit and collector status counts agree. The following is a review-local summary of those committed records, also captured in audit results (`pr50-r1-evidence-audit.json`).

```toon
runs[4]{run_id,seeded,passed,failed,error,skipped,pytest_exit}:
  acc-20261112T083417Z-f2b524,false,1,3,8,10,1
  acc-20261112T085656Z-c69ad2,true,11,1,0,10,1
  acc-20261112T092035Z-e4c24d,false,0,1,1,0,1
  acc-20261112T092701Z-876a61,true,1,1,0,0,1
```

The seeded full run's 1,288,938 ms is the overall acceptance-command duration (about 21 min 29 s); its pytest execution is 830.04 s. Both seeded C4 logs fail at `_open_editor` → `page.goto(...wiki/home/?edit&view&menu, wait_until="domcontentloaded")`, with `Timeout 30000ms exceeded`; both rejection cases pass with WebSocket close code 4401. The cause remains unresolved. No browser/acceptance rerun was performed.

Content inspection and targeted searches of all 20 UTF-8 files found no credential values, disposable test email/password values, or local scratch paths. Identity/password values shown in tracebacks are `***`; no GitHub token/private-key patterns or email addresses remain. The guest checkout path `/home/grdm/RDM-developer-guide` remains in some Playwright traceback callbacks; it is the documented guest path, not a scratch path. No trace archives or screenshots are included. This is a bounded content review, not a claim that the unexecuted stack `scan` passed.

Prerequisites, compile timings, image transfer, `up` duration and `health --network` exit zero are described in the narrative but have no corresponding new raw logs/reports in these four acceptance folders. Acceptance prechecks corroborate a healthy 24-service stack, not the loopback binding audit or the complete earlier sequence. The Rosetta-built osf.io/wiki-frontend import and interrupted single-command run are disclosed; a completed uninterrupted emulated/native amd64 install is not evidenced.

### Validation and documentation conventions

Commands ran from the clean clone using PATH `python3` (`/opt/homebrew/bin/python3`, Python 3.15.2), without a virtual environment. These are measured review results, not acceptance reruns.

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"660 tests; 10 skipped; 62.939 s"
  "python3 -m unittest discover -s tools/tests",0,"93 tests; 3.348 s"
  "python3 tools/docs_check.py",0,"177 checked; 8 exempt; 45 warnings"
  "python3 tools/manifest_check.py",0,"0 findings; policy scanned 749 files; 63 non-UTF-8 files skipped"
```

Logs: installer tests (`pr50-r1-installer-tests.log`), tools tests (`pr50-r1-tools-tests.log`), docs check (`pr50-r1-docs-check.log`), manifest check (`pr50-r1-manifest-check.log`). Ten skipped unit tests and the glossary warnings remain explicit limitations. Both existing documents preserve their previous version entries and add new versions; the three scoped documents retain English before Japanese, anchors and working relative links. TOON formatting is used, but R4 fails actual parsing. The general documentation checker reports seven glossary warnings in new DEMO-22 and does not prove semantic parity or the truth of completion claims. The clone's final Git status is clean.

### Required next action

Correct R1–R5 and reconcile R6's contract, preserving both language halves and previous version entries; rerun relevant checks and request round 2. Keep C4 success, stack scan/report and an uninterrupted amd64 installation explicitly open. No source fix or operational rerun is included in this review assignment.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Changes requested（要修正）。** 独立したクリーンクローンで、head `7ac6e5c6c162753ae1c02d7e1bcaac76863183cd` と base `a005acfb5ec06064102170b038a58458d6a7d062` を比較した。通常の正の timeout 引き渡しと Ubuntu amd64／Linux arm64 の状態表示は動作する。seed ありの証跡はコア11/12合格と C4 success の wiki ページ `goto` の30秒タイムアウト2回を裏付けるが、中断しない導入成功やビルド後全工程の完了は証明しない。

ソース変更、commit、push、approve、merge、close、VM 操作、Docker 状態変更、イメージ／キャッシュの prune、稼働環境の `runtime/.env` へのアクセスはしていない。単体試験は隔離された一時 fixture を利用した。外部への書き込みは[日本語の PR 会話コメント1件](https://github.com/RCOSDP/RDM-developer-guide/pull/50#issuecomment-6820295801)を投稿しただけである。

### 指摘

1. **R1 — P2: 未実施の工程を実行済みとする記載を訂正する。** [DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md) L118／L274 は `scan`・`report` を実行済み工程に含め、「ビルドより後ろ全体の証明」とする。同じ記録の L139／L164、L295／L320 は未実施とし、受入も11/12である。実際の `up`、`health --network`、受入試行に限定し、未実施工程と不合格を明記する。L8 の「build より後ろに amd64 に固有のことは無かった」も検証済み範囲に絞る。L89／L245 の「ほかのイメージはすべて VM でネイティブに組めた」から、輸入した wiki-frontend を除く。現状は未検証のセキュリティゲートまで完了したように読める。

2. **R2 — P2: 実測・推計・未検証の原因を区別する。** DEMO-22 L114／L157／L159／L163、L270／L313／L315／L319 は、実機 amd64 は数分、長い待ちは不要、一過性 DNS 障害は QEMU のネットワークでインストーラーの不具合ではない、と断言する。実機比較や DNS 原因分析の証跡はなく、新規 artifact は受入出力だけである。ビルドは5時間12分で中止しており、1営業日では終わらないことや約9時間の完了時間は完走実測ではなく推計である。[SPEC-02](../spec/02_installer_cli.md) L8 と[環境手引き](../guides/environment/README.md) L8 も営業日の断言を繰り返し、SPEC-02 はコンパイル時間と `up` 専用の待ちオプションを関連付ける。numpy 971／118秒、pandas 4298／411秒、scipy 6400秒超未完、Rosetta イメージ64分11秒は執筆者の観察記録として保持し、未検証の推計・仮説を明示する。`--timeout` は `build` を短縮も延長もしないことを明確にする。正直な記録への修正だけのために実機再試験を要求するものではない。

3. **R3 — P2: 4実行すべてと実際の skip 理由を集計する。** DEMO-22 L144–153／L300–309 は「3回、誤り1回」と3行の集計を掲げるが、4番目のリンク先 [acc-20261112T092035Z-e4c24d](../demo/runs/acc-20261112T092035Z-e4c24d/results.toon) は seed なしの C4 実行で、0 passed・1 failed・1 error を記録している。この行を追加し、両言語の見出しを直す。wiki `goto` の2回の失敗は seed ありの実行に限定した説明とする。10件の skip は seed ありの [pytest.log](../demo/runs/acc-20261112T085656Z-c69ad2/pytest.log) L108–117 で `M3` と記録され、S1–S5 の各モジュールは無条件の `pytest.mark.skip(reason="M3")` である。core にサービスが無いことを動的に判定して skip したわけではないため、表の注記も直す。

4. **R4 — P2: コンパイルの TOON 2ブロックを修正する。** DEMO-22 L107／L263 は `osf_compile[3]` と宣言するが、RUN 全体を含む4行がある。リポジトリの `tools.manifest_check.parse_toon` は両方を `osf_compile[3] has more rows than declared` で拒む。行数を4にするか全体値を分離する。現在の `docs_check` の TOON 検査は宣言された正本との SHA 対応に限られ、その成功は構文の妥当性を保証しない。

5. **R5 — P2: 明示された timeout 0 を引き渡す。** [install.py](../../installer/grdm_dev/install.py) L50 の `if timeout` は、`None` と `0` を同一視する。実 parser と `plan_steps` による再現では `install --timeout 0` が `['up', '--no-open']` となり、省略時と同じになる。直接の `up --timeout 0` は最初の health 確認後にポーリングしないが、install 経由では1800／5400秒に戻る。`is not None` で明示値を保持し、parser から plan までを通すゼロ値の回帰試験を加える。既存の7200秒の試験は成功するが、この境界を検証していない。

6. **R6 — P3: macOS では出さないという仕様と報告を一致させる。** [host.py](../../installer/grdm_dev/host.py) L146／L394–396、L490–496 は `asdict(info)` に空文字の `amd64_emulation` を残すため macOS arm64 も空の行を出し、macOS amd64 は OS 制約のない分岐で `not needed` を出す。SPEC-02 L128／L371 と DEMO-22 の「macOS では出さない」に一致しない。macOS を先に除外し、対象外のフィールドを報告時に省くか、意図する契約を明確に改定する。追加した [test_preflight.py](../../installer/tests/test_preflight.py) L292–295 は非空の2文字列だけを除外している。キー自体の不在と両 Mac アーキテクチャを確かめる必要がある。

### 証跡監査と限界

4つの `acc-20261112T*` 配下の20ファイルはすべてコミット済みで、参照した4つの `results.toon` は対象 head に存在する。隣接する `results.json` を現行 encoder で変換した結果と完全一致し、JUnit・collector の状態件数も一致した。次はレビュー用の集計であり、監査結果 (`pr50-r1-evidence-audit.json`) にも保存した。

```toon
runs[4]{run_id,seeded,passed,failed,error,skipped,pytest_exit}:
  acc-20261112T083417Z-f2b524,false,1,3,8,10,1
  acc-20261112T085656Z-c69ad2,true,11,1,0,10,1
  acc-20261112T092035Z-e4c24d,false,0,1,1,0,1
  acc-20261112T092701Z-876a61,true,1,1,0,0,1
```

seed あり全体実行の1,288,938 msは受入コマンド全体の約21分29秒であり、pytest 部分は830.04秒である。seed ありの C4 ログは2回とも `_open_editor` → `page.goto(...wiki/home/?edit&view&menu, wait_until="domcontentloaded")` で `Timeout 30000ms exceeded` となり、拒否系は2回とも WebSocket close code 4401で合格した。原因は未解決である。今回ブラウザ／受入試験の再実行はしていない。

20個すべての UTF-8 ファイルの内容確認と対象検索では、秘密値、使い捨て試験メール／パスワード値、ローカル scratch パスを検出しなかった。traceback の利用者・パスワード値は `***`、GitHub token／秘密鍵形式やメールアドレスも残っていない。一部 Playwright callback にゲストの `/home/grdm/RDM-developer-guide` は残るが、記載されたゲスト配置先であり scratch パスではない。trace archive やスクリーンショットは含まれない。この限定的な内容監査は、未実施の stack `scan` の成功を意味しない。

前提条件、ビルド時間、イメージ移送、`up` 所要時間、`health --network` の終了0は本文の記録であり、この4受入フォルダに対応する生ログ／報告は追加されていない。受入の precheck は24サービスが healthy だったことを裏付けるが、loopback bind の検査や前段すべての手順は証明しない。Rosetta 製 osf.io／wiki-frontend の輸入と単一コマンドの中断は開示されている。エミュレーション／実機 amd64 で中断しない完走の証跡は無い。

### 検証と文書規約

クリーンクローンのルートから、仮想環境を使わず PATH の `python3`（`/opt/homebrew/bin/python3`、Python 3.15.2）で実行した。次は今回測定したレビュー検査であり、受入再実行ではない。

```toon
checks[4]{command,exit,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests",0,"660件、10件skip、62.939秒"
  "python3 -m unittest discover -s tools/tests",0,"93件、3.348秒"
  "python3 tools/docs_check.py",0,"177ファイル検査、8除外、45警告"
  "python3 tools/manifest_check.py",0,"指摘0、policyは749ファイル検査、非UTF-8の63ファイル除外"
```

ログ: installer tests (`pr50-r1-installer-tests.log`)、tools tests (`pr50-r1-tools-tests.log`)、docs check (`pr50-r1-docs-check.log`)、manifest check (`pr50-r1-manifest-check.log`)。単体試験10件の skip と用語注警告は限界として明示する。既存2文書は過去の版行を保持して新版を追加し、対象3文書は英語→日本語、アンカー、解決する相対リンクを保持する。TOON を使っているが、R4 の構文不備がある。一般の文書チェッカーは新規 DEMO-22 に7つの用語注警告を出し、意味の対応や完了主張の真偽は検証しない。終了時のクローンの Git status は clean。

### 次の対応

R1–R5を修正し、R6の契約を整合させる。両言語と既存版行を保持し、関連検査を再実行して r2 を依頼する。C4 success、stack の scan／report、中断しない amd64 導入は未完として維持する。今回の割当にはソース修正や運用上の再実行は含まれない。
