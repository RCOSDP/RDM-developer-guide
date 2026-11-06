# PR33 Startup fixes review r3 / 起動修正レビュー r3

> **Summary:** Pass with documentation nits: the two functional R2 findings are resolved and all eight CI checks pass. Test-count and version metadata still need correction.
> **概要:** 文書の軽微な残件付きで合格。R2 の機能面の指摘2件は解決し、CI 8件はすべて合格。試験件数と版の記録には訂正が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** passing automated checks does not ensure that review evidence counts and specification versions match the reviewed revision. ／ 自動検査の合格だけでは、証跡の試験件数と仕様の版がレビュー対象に一致するとは限らない。
- Applies to: RCOSDP/RDM-developer-guide PR #33, head `ee61da1f27a0ad2fa03d2f4148f5acaaf31f5fa6`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [R1](2026-11-06_RDM-developer-guide_PR33_Startup_Fixes_r1.md) · [R2](2026-11-06_RDM-developer-guide_PR33_Startup_Fixes_r2.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: [Status board](../status/README.md) · [DEMO-20](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and R2 disposition

**Pass with nits. No blocking functional finding in the R2 follow-up.** This is a review verdict, not GitHub approval. Local HEAD and the remote PR head matched. The review inspected the new commit against R2 and ran the requested checks.

- **R2-01 resolved.** [test_compose.py](../../installer/tests/test_compose.py) patches `detect_memory_gib` inside the VM-render helper. The 128/48 GiB and 64/24 GiB host/VM cases assert exactly 48 and 24 GiB. The new 16/48 GiB case checks exit 10 and the 16 GiB budget diagnostic. Production's smaller-of-host-and-VM rule is preserved. Both hosted Python jobs now pass.
- **R2-02 resolved functionally.** [scan.py](../../installer/grdm_dev/scan.py) passes `strict` from the milestone policy: timeout-only results warn at M1–M3 and become incomplete/exit 51 at M4–M5. SPEC-03 §4.2 states that boundary in both languages. The regression test exercises all five milestones, and the existing mixed-error case remains. An additional reviewer probe supplied mixed timeout/ordinary errors with scanner exit 0 at each of M1–M5; all five returned 51, proving ordinary errors cannot be hidden by a successful process exit. The function docstring is updated; the module docstring still needs the early-milestone exception.
- **R2-03 partly resolved.** Both M2 rows now say acceptance has not passed, first run 0/12. The PR body correctly says 1800 seconds and explains the earlier failed CI jobs. Its current test total remains stale (see R3-01).

### Nonblocking documentation findings

**R3-01 — P3: correct the current installer test count.** The requested discovery command ran **356 tests, 10 skipped**, not the PR body's “354 after r2” or the head commit message's 357. The new commit adds two test methods to the prior 354; milestone subtests do not add separately discovered tests. Correct the editable PR verification paragraph to 356 and retain historical counts with their revisions; no history rewrite is requested.

**R3-02 — P3: finish policy metadata and explanatory text.** SPEC-03 §4.2 contains the new policy, but its header is still **0.6**, not the requested 0.7. Add the 0.7 learned/version entry per SPEC-06 §6. Update scan.py's module-level statement that every scanner error is incomplete to mention the documented M1–M3 timeout exception. The PR summary's SPEC-03 0.5 label is also stale if intended as the current version. These are documentation mismatches, not a failure of strict-milestone enforcement.

### Evidence and limits

Observed results in the supplied worktree; this is review evidence, not canonical manifest data.

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","PASS: 356 tests, 10 skipped"
  "python3 -m unittest discover -s tools/tests","PASS: 90 tests"
  "python3 tools/manifest_check.py","PASS: zero findings"
  "python3 tools/docs_check.py","PASS: 94 checked, 8 exempt, 21 non-failing warnings"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","PASS: all 8, including Python 3.11 and 3.12 unit-test jobs"
```

CI evidence: [unit tests](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776059), [documentation](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776076), [security and manifest](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776130). The new untracked review is checked separately with `tools.docs_check.check_file` because the normal checker enumerates tracked files.

R1's remaining Linux ownership execution evidence, focused Ember image-change/reuse regression test, browser acceptance, and fresh uninterrupted cold-start evidence are not supplied by this rerun. They remain as recorded in R2; no claim of completed M2 acceptance is made. No installation, real scanner, Docker state change, implementation edit, commit, push, approval or merge was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と R2 の対応状況

**軽微な文書残件付きで合格。R2 対応に機能面の阻害事項なし。** GitHub の承認ではなくレビュー判定である。ローカル HEAD と PR の先端は一致した。新しいコミットを R2 と照合し、指定検査を実行した。

- **R2-01 解決。** [test_compose.py](../../installer/tests/test_compose.py) の VM 描画補助内で `detect_memory_gib` を差し替えている。ホスト／VM が128/48 GiB と64/24 GiB の場合に選択値48、24 GiB を等値で検査する。新しい16/48 GiB の場合は終了10と16 GiB の予算診断を確認する。本番のホスト／VM の小さい方を選ぶ規則は維持され、CI の Python 両ジョブも合格した。
- **R2-02 機能面は解決。** [scan.py](../../installer/grdm_dev/scan.py) は節目の方針から `strict` を渡し、時間切れのみなら M1〜M3 は警告、M4〜M5 は不完全／終了51になる。SPEC-03 §4.2 は英和とも境界を明記した。回帰試験は全5節目を通り、既存の混在エラー試験も維持される。追加のレビュワ検査では、時間切れと通常エラーの混在をスキャナ終了0で M1〜M5 それぞれに与え、全5件が終了51となった。プロセスの成功で通常エラーが隠れないことを確認した。関数の説明は更新されたが、モジュールの説明には初期節目の例外追記が残る。
- **R2-03 一部解決。** M2 の両行は受入未合格・初回0/12となった。PR 本文は1800秒と以前の CI 失敗の経緯を正しく記す。ただし現在の試験総数は古い（R3-01）。

### 阻害しない文書指摘

**R3-01 — P3: 現在の installer 試験件数を訂正する。** 指定の discovery コマンドは **356件、10 skip** だった。PR 本文の「r2 対応後354件」でも先端コミット本文の357件でもない。新コミットは従来354件に試験メソッド2件を追加し、節目ごとの subtest は独立した検出試験数に加算されない。編集可能な PR 検証段落を356件へ訂正し、過去の件数は対象版とともに残すこと。履歴の書換えは要求しない。

**R3-02 — P3: 方針の版情報と説明を仕上げる。** SPEC-03 §4.2 に新方針はあるが、ヘッダは指定された0.7ではなく **0.6** のままである。SPEC-06 §6 に従い0.7の学び・版の行を追加すること。scan.py のモジュール冒頭の「スキャナ自身の全エラーは不完全」という説明にも M1〜M3 の時間切れ例外を追記すること。PR 要約の SPEC-03 0.5 も現行版を指すなら古い。厳格な節目の強制処理の失敗ではなく文書上の不一致である。

### 証跡と限界

指定 worktree での観測結果であり、manifest の正本データではない。

```toon
checks[5]{command,result}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","合格: 356件、10 skip"
  "python3 -m unittest discover -s tools/tests","合格: 90件"
  "python3 tools/manifest_check.py","合格: 指摘0"
  "python3 tools/docs_check.py","合格: 94検査、8除外、非失敗の警告21"
  "gh pr checks 33 --repo RCOSDP/RDM-developer-guide","合格: 全8件、Python 3.11・3.12の単体試験ジョブを含む"
```

CI 証跡: [単体試験](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776059)・[文書](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776076)・[安全性と manifest](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42165776130)。通常の検査は追跡済みファイルを列挙するため、新規未追跡のレビューは `tools.docs_check.check_file` で別途確認する。

R1 から残る Linux 所有権の実行証跡、Ember のイメージ変更／再利用の専用回帰試験、ブラウザ受入、新規状態から中断なしのコールドスタート証跡は今回の再検査では得ていない。R2 に記録したままの残件であり、M2 受入完了を主張しない。導入、実スキャナ、Docker 状態変更、実装修正、commit、push、承認、merge は行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| CI | Automated checks on the hosted change. | サーバー上で変更を自動検査する仕組み。 |
| VM | A virtual computer with its own memory budget. | 独自のメモリ予算を持つ仮想のコンピュータ。 |
| Coverage gap | A part of the intended scan that did not finish. | 予定した検査のうち完了していない部分。 |
| Regression test | A repeatable check against a defect returning. | 不具合の再発を防ぐ繰り返し可能な検査。 |
| P3 / nit | A low-priority, nonblocking correction. | 阻害しない軽微な訂正。 |

Shared terminology: [REF-01](../reference/REF-01_Glossary.md).
