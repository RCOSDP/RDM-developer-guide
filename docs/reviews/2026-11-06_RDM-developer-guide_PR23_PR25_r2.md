# REV PR23 and PR25 review r2 / PR23・PR25 レビュー r2

> **Summary:** PR #23 resolves U1–U4; the requested regression checks pass. PR #25 fixes the unsafe command examples but still needs an accurate staged security-gate explanation.
> **概要:** PR #23 は U1〜U4 を解消し、指定の回帰検査に合格。PR #25 は危険なコマンド例を修正したが、段階別セキュリティ門の説明に修正が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** replacing a partial scan command is insufficient when its new explanation omits enforced milestone rules; retry tests must compare published state rather than local state. ／ 部分検査のコマンドを置き換えても、説明が実際に強制する節目の規則を省けば不十分であり、再試行の試験はローカル状態ではなく公開済み状態と比較する必要があると分かった。
- Applies to: RCOSDP/RDM-developer-guide PR #23 and #25; reviewer REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-05](../spec/05_upstream_tracking.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md).
- Used by: [Environment guide](../guides/environment/README.md) · [Upstream status](../status/upstream/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Scope and verdicts

A PR (pull request) is a proposed change. A SHA is the fingerprint of a saved revision. A worktree is a separate working copy. A security gate is a checkpoint that determines whether an installation may pass ([shared glossary](../reference/REF-01_Glossary.md)).

- **PR #23: U1–U4 resolved; acceptable for the requested r2 scope.** Reviewed SHA `58f0d4d7dc374b1c24fd8d4d4337b28a624d46dd`.
- **PR #25: changes requested, P2 remaining.** Reviewed SHA `82f102ba844bdd7d5ea5144b62d2fda5c2894062`.

These are review recommendations, not GitHub approvals. Remote reads used `gh`; no approval, merge, close, commit, push, or Docker state change was performed. The r1 records were read from the supplied sibling `wt-isha` checkout because they were not yet available through the develop contents API. File and line evidence below refers to the reviewed worktrees. The principal #23 implementation, tests, workflow and SPEC-02, and the #25 guide were byte-compared against GitHub contents at the stated SHAs and matched.

Comments posted: [PR #23 r2](https://github.com/RCOSDP/RDM-developer-guide/pull/23#issuecomment-6667810457) · [PR #25 r2](https://github.com/RCOSDP/RDM-developer-guide/pull/25#issuecomment-6667810925). The repository documentation check including this record passed: 62 files, 8 exempt, 184 warnings.

### PR #23: U1–U4 verification

1. **U1 resolved.** `installer/grdm_dev/upstream.py`, `mirror_component`, takes `previous` and `to_publish` from origin (the published repository), resets local tracking references to that value, and deletes stale local references when origin lacks them. Independent FakeGit probes (a simulated Git command runner) with origin containing only develop produced: dry-run → real exits 0 → 0, one push, five origin references; failed first push → retry exits 70 → 0, two push attempts, five origin references. This explicitly covers the initially absent branch case as well as the submitted retry test with existing branches.
2. **U2 resolved.** `integrate_component` refuses both existing remote and local integration branches and uses `switch -c`, which cannot reset an existing branch. An independently injected local branch retained its SHA, returned 70, and caused no switch, checkout, merge or push call. Dry-run (a preview with the documented local operations) used detached HEAD, created no integration branch, and a subsequent real invocation succeeded. Detached HEAD means working at a revision without attaching changes to a named branch; local fetches, merge objects and reports remain permitted by SPEC-05.
3. **U3 resolved by source inspection.** The workflow template prepares a separate `status/` checkout before report generation and writes reports directly into that checkout. Existing reports on a second run therefore do not precede a branch switch. Upload uses `always()` and status publication uses `always() && inputs.dry_run != true`; a failed mirror can publish its failure report while the job remains failed. This was a control-flow review, not execution of a hosted Actions job or authenticated publication. Multiple components still share latest/archive destinations; aggregation and cross-repository publication races remain deployment limitations already noted in r1.
4. **U4 resolved.** `UPSTREAM_FAILED = 70`, both language messages in `messages.tsv`, `_fail`, SPEC-02 §6 and both SPEC-05 halves agree. Each SPEC-02 TOON block (a compact structured-text table) declares **14 rows and contains 14 rows**. English/Japanese code sequences match the 14 canonical message rows exactly; the new meanings correspond in both languages. Failure probes returned 70 with the canonical message; conflict and other failure cases passed the submitted tests.

Run from the supplied `wt-upstream` root; bytecode creation was disabled to avoid incidental checkout writes:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=installer python3 -m unittest discover -s installer/tests
```

```toon
validation[2]{check,total,skipped,result}:
  installer-unit-tests,312,10,OK
  spec02-exit-code-rows-per-language,14,0,match
```

The independent probes imported `FakeGit`, `UpstreamBase` and fixtures from `installer/tests/test_upstream.py`, used temporary directories and asserted command calls and final references. They did not contact or modify integration repositories. Unit tests do not prove live startup, authentication or hosted workflow execution.

### PR #25: disposition of every r1 finding

Both English and Japanese halves were checked against SPEC-02/03/04, ADR-02/03, `install.py`, `compose.py`, `health.py`, `scan.py`, `accept.py` and `README.legacy.md` in the supplied guide worktree.

| r1 finding | r2 result in both languages |
|---|---|
| 25-01 | Partial: §3.8 now correctly uses unfiltered `scan`, labels subset flags, and gives 51/52; the new milestone explanation remains incomplete (R2-25-01). |
| 25-02 | Resolved: §3.7, security notes and troubleshooting distinguish plain health from `health --network`; installation uses the latter. |
| 25-03 | Resolved: doctor uses 10/11 correctly; render lists success 0 and failures 20/2/12, matching `compose.py:740–784`. |
| 25-04 | Resolved: §3 lists the actual nine-step sequence, conditionally initializes secrets, puts acceptance outside it, and shows doctor-only execution. |
| 25-05 | Resolved: §3.9 installs the acceptance extra and Chromium in the existing venv, then runs `accept --seed`; users live within that invocation, matching `accept.py:574–636`. Cleanup failure remains an implementation limitation, not a persistent preparatory seed step. |
| 25-06 | Resolved: §5 explains per-service hardening exceptions and links `manifest/hardening.json`; read-only roots are no longer promised universally. |
| 25-07 | Resolved: quick start and up use the reported URL; §6 starts the +100 port search from requested/saved values and preserves owned bindings, matching `compose.py:210–235`. |
| 25-08 | Resolved: header, quick-start caveat, build and troubleshooting agree that the digest-pinned fallback already exists until M4; full startup remains explicitly unverified. |
| 25-09 | Resolved: §7 uses the legacy guide's alias, local settings, overrides and image/module-volume setup, distinguishes internal/external URLs, and attributes default credentials to upstream Compose/SPEC-03 rather than legacy prose. |
| 25-10 | Substantially resolved: old version retained, parent/Used-by links supplied, one final bilingual glossary, macOS 14 corrected, new term explanations, seven-service outbound access and full-profile/`--egress none` examples corrected; first-use placement remains a P3 note (R2-25-02). |

### Remaining findings for PR #25

**R2-25-01 / P2 — Complete the gate rule in §3.8 (guide lines 213 / 568).** Both halves say M4 fails on unlisted HIGH and M1–M3 findings are report-only with exit 0. ADR-03 §3 points 3–5 and SPEC-03 §5 require unlisted **CRITICAL as well as HIGH** to fail M4, and a non-growing allow-list at M2/M3. An allow-list is the recorded set of temporarily accepted findings. `scan.py:864–892` implements those constraints and also rejects malformed gate data. Independent calls to `gate_decision` rejected (a) M4 with one unlisted CRITICAL and (b) each of M2 and M3 with count 2 against baseline 1. These failed gates map to exit 50 when scanners run successfully. State both severities, the count constraint and the validity requirement; qualify the early-stage exit-0 statement. SPEC-02's short M4 row also says HIGH only, so copying that summary does not resolve its disagreement with ADR-03, SPEC-03 and the implementation.

**R2-25-02 / P3 — Move short definitions to actual first use.** The quick-start caveats use profile and manifest at lines 34 / 389, while their explanations arrive in §3.2 at lines 123 / 478. The header also uses manifest earlier. SPEC-06 §3 asks for a first-use note. Put the short definitions at the early occurrence or link directly to a nearby explanation. This is a documentation polish item; the glossary now exists and the structural corrections are effective.

Run from the supplied `docs-env-guide` worktree root:

```sh
python3 tools/docs_check.py
```

Result: **PASSED, 59 files checked, 8 exempt, 165 warnings**. Warnings were not silently treated as zero findings. The checker does not establish semantic correctness of the gate explanation. No complete install, live scan, browser acceptance run or Docker operation was performed; those remain separate execution evidence.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 範囲と判定

PR は変更提案、SHA は保存した版を識別する指紋、worktree は別の作業コピー、セキュリティ門は導入を合格にできるか判断する検査である（[共通用語集](../reference/REF-01_Glossary.md)）。

- **PR #23: U1〜U4 解消。指定の r2 範囲では採用可能。** 対象 SHA は `58f0d4d7dc374b1c24fd8d4d4337b28a624d46dd`。
- **PR #25: P2 が残り、修正要求。** 対象 SHA は `82f102ba844bdd7d5ea5144b62d2fda5c2894062`。

判定はレビュー上の推奨であり GitHub 承認ではない。リモートの読取は `gh` を使用し、承認・マージ・閉鎖・commit・push・Docker の状態変更はしていない。r1 記録は develop の contents API にまだ無かったため、指定場所の隣にある `wt-isha` から読んだ。根拠のファイル・行番号は対象 worktree に対応する。#23 の主要実装・試験・workflow・SPEC-02 と #25 のガイドは、明記した SHA の GitHub contents とバイト単位で一致した。

投稿済みコメント: [PR #23 r2](https://github.com/RCOSDP/RDM-developer-guide/pull/23#issuecomment-6667810457) · [PR #25 r2](https://github.com/RCOSDP/RDM-developer-guide/pull/25#issuecomment-6667810925)。この記録を含むリポジトリ文書検査も合格（62 ファイル、8 除外、184 警告）。

### PR #23: U1〜U4 の確認

1. **U1 解消。** `upstream.py` の `mirror_component` は公開先 origin の状態で `previous` と `to_publish` を決める。ローカル参照を公開済みの値に合わせ、公開先に無い参照は古いローカル値を削除する。FakeGit（Git コマンドを模擬する実行器）で origin を develop のみにした独立検査では、dry-run→本実行が終了 0→0、push 1 回、origin の参照 5 本。初回 push 失敗→再試行は終了 70→0、push 試行 2 回、参照 5 本。提出された既存ブランチの再試行試験に加え、初回の未作成ブランチでも確認した。
2. **U2 解消。** `integrate_component` はリモート・ローカル双方の既存統合ブランチを拒否し、既存ブランチを戻せない `switch -c` を使う。独立検査で注入したローカルブランチの SHA は変わらず、終了 70、switch・checkout・merge・push は 0 回だった。dry-run（許可されたローカル操作を伴う予行）は detached HEAD（名前付きブランチに結び付けず版を作業対象にする状態）を使い、統合ブランチを作らず、その後の本実行は成功した。ローカル fetch、マージの保存物、報告の書込は SPEC-05 が許す操作として残る。
3. **U3 はソース確認で解消。** workflow は報告生成前に独立した `status/` を用意し、その中へ直接報告を書く。二回目の既存報告がブランチ切替より前に生成される構造はなくなった。成果物保存は `always()`、status 公開は `always() && inputs.dry_run != true` なので、ミラー失敗時も報告を公開でき、ジョブは失敗のままになる。制御フローの確認であり、Actions 本番ジョブや認証付き公開の実行ではない。複数部品が latest/archive を共有する集約とリポジトリをまたぐ同時公開は、r1 で挙げた導入上の制約として残る。
4. **U4 解消。** `UPSTREAM_FAILED = 70`、`messages.tsv` の英和メッセージ、`_fail`、SPEC-02 §6、SPEC-05 両言語が整合する。SPEC-02 の TOON（構造化データを短く書く形式）は英和とも **宣言 14 行、実数 14 行**。コード列は正本のメッセージ 14 行と完全一致し、新しい意味も英和で対応する。独立した失敗検査は正本文言付き終了 70、衝突を含む提出試験も成功した。

指定の `wt-upstream` のルートで実行した。付随する書込を避けるため Python バイトコード作成を無効にした。

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=installer python3 -m unittest discover -s installer/tests
```

結果は **312 件、10 件スキップ、OK**。終了コードの照合は両言語とも 14 行一致。独立検査は `installer/tests/test_upstream.py` の FakeGit、UpstreamBase、試験データを読み込み、一時ディレクトリでコマンド呼出と最終参照を検査した。統合リポジトリには接続・変更していない。単体試験は実起動・認証・本番 workflow の証明ではない。

### PR #25: r1 全指摘の処置

英語と日本語の両方を、指定 worktree の SPEC-02/03/04、ADR-02/03、`install.py`、`compose.py`、`health.py`、`scan.py`、`accept.py`、`README.legacy.md` と照合した。

| r1 指摘 | 両言語の r2 結果 |
|---|---|
| 25-01 | 一部解消。§3.8 はフラグなし scan、限定フラグ、51/52 を正しく記述。ただし新しい段階別規則に不足（R2-25-01）。 |
| 25-02 | 解消。§3.7、注意点、障害対処で通常 health と health --network を区別し、自動導入は後者。 |
| 25-03 | 解消。doctor の 10/11、render の成功 0 と失敗 20/2/12 が compose.py:740–784 と整合。 |
| 25-04 | 解消。実際の 9 段、条件付き秘密生成、別手順の受入試験、doctor 単独実行を記載。 |
| 25-05 | 解消。§3.9 は既存 venv に追加依存と Chromium を準備して accept --seed を実行。利用者は同じ実行内で作成・削除され accept.py:574–636 と整合。削除失敗は実装上の制約であり、永続的な事前 seed 手順ではない。 |
| 25-06 | 解消。§5 はサービス別の堅牢化例外と hardening.json を示し、全サービスの読み取り専用ルートを約束しない。 |
| 25-07 | 解消。開始手順と up は報告 URL、§6 は要求値・保存値から +100 と自分の待受維持を説明し compose.py:210–235 と整合。 |
| 25-08 | 解消。ヘッダ・開始時の注意・ビルド・対処が、代替は設定済みで M4 まで維持と一致。完全起動の未検証も明示。 |
| 25-09 | 解消。§7 は旧ガイドにある別名、設定コピー、override、配布イメージとモジュールのボリュームを根拠に比較。内部/外部 URL を区別し、既定認証情報は上流 Compose/SPEC-03 に帰属。 |
| 25-10 | 概ね解消。旧版、親/Used-by リンク、末尾の用語集一つ、macOS 14、用語注、公開 7 サービスの外向き通信、full と --egress none の例を修正。初出位置は P3 として残る（R2-25-02）。 |

### PR #25 の残る指摘

**R2-25-01 / P2 — §3.8 の門の規則を補完する（ガイド 213 / 568 行）。** 両言語は M4 を許容リスト外の HIGH、M1〜M3 を報告のみ・終了 0 と説明する。しかし ADR-03 §3 の 3〜5 項と SPEC-03 §5 は、M4 で **CRITICAL と HIGH の両方**、M2/M3 で許容リスト件数が増えないことを要求する。許容リストとは、一時的に認めた検出の記録一覧である。`scan.py:864–892` はこれらを実装し、門のデータが不正な場合も拒否する。`gate_decision` の独立検査では、M4 に許容外 CRITICAL 1 件、M2 と M3 それぞれに基準 1 件に対し 2 件を渡し、すべて不合格となった。スキャナーが正常に実行できた場合は終了 50 に対応する。両重大度、件数制約、データの有効性を記載し、初期段階の終了 0 を条件付きにする。SPEC-02 の短い M4 行も HIGH のみなので、その要約のコピーでは ADR-03・SPEC-03・実装との不一致は解消しない。

**R2-25-02 / P3 — 短い用語説明を本当の初出へ移す。** 開始時の注意 34 / 389 行に profile・manifest が登場するが、説明は §3.2 の 123 / 478 行までない。ヘッダにも manifest が先にある。SPEC-06 §3 は初出注を求めるため、先の位置に短い説明を置くか、近くの説明へ直接リンクする。文書の仕上げに関する指摘であり、用語集と構造の修正自体は有効である。

指定 `docs-env-guide` worktree のルートで実行した。

```sh
python3 tools/docs_check.py
```

結果は **PASSED、59 ファイル検査、8 除外、165 警告**。警告を指摘ゼロと扱ってはいない。この検査は門の説明の意味的な正しさを保証しない。完全導入・実スキャン・ブラウザ受入・Docker 操作は実施せず、別の実行証跡として残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Regression probe | A small check that repeats a previously failing situation. | 以前失敗した状況を繰り返す小さな検査。 |
| P2 / P3 | P2 needs correction before accepting; P3 is documentation polish. | P2 は採用前の修正、P3 は文書の仕上げ。 |
| Canonical | The authoritative source other copies must match. | 他の写しが一致すべき正本。 |
| CRITICAL / HIGH | Two separate severity categories for known weaknesses. | 既知の弱点の重大さを示す、別々の二段階。 |
