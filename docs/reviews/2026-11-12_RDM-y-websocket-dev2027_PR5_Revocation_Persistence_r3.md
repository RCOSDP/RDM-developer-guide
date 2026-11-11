# REV PR5 Revocation and persistence review r3 / 失効・永続化レビュー r3

> **Summary:** Pass at the exact reviewed head. The unfinished-write reservation defect is fixed, all local tests pass, and no new findings were identified in the round-three diff.
> **概要:** 指定 head の判定は pass。未完了書込みの予約を失う問題は解消し、ローカル試験は全て成功、r3 差分の追加指摘はない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-12_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r3.md` (SHA-256: `be5a6c0adff01b2f789a87fa6414c00037efe71b40e265da2b27079cbccf3d34`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-12. **Learned:** A fresh disk measurement must retain both unfinished payload writes and unfinished deletion markers until their operations settle. ／ ディスクを再計測しても、未完了の本文書込みと削除マーカーの予約は処理完了まで保持する必要がある。
- Applies to / 対象: RCOSDP/RDM-y-websocket-dev2027 PR #5; `67aae1d7efaa4bb002b60f572b15fd631b65d980..5e7fe4a524c7cd970d44085b6f3eacd82e2fb425`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Round 2 / 前回レビュー](2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r2.md) · Machine-readable evidence / 機械可読の証跡 (REV scratch evidence (not published): `results.json`).
- PR comment / PRコメント: r3 verdict / r3 判定 (RDM-y-websocket-dev2027 PR #5, comment 6799671897) — exactly one comment posted / 投稿は1件のみ。
- Used by / 利用先: the coordinator's PR #5 integration decision / 調整者による PR #5 の統合判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**pass. No new R3 findings. R2-01 / P2 is closed**, also closing the remaining queued-write portion of R1-03. Reviewed the one-commit diff in `bin/persistence.cjs` and `test/storage-bounds.test.cjs`. The PR head was verified as `5e7fe4a524c7cd970d44085b6f3eacd82e2fb425`. This verdict applies to that head and scope.

At `bin/persistence.cjs:104–113`, `track` adds a reservation synchronously and removes it only when the operation settles. At line 126, remeasurement adds `inFlight` to the disk baseline. Both payload writes (line 139) and deletion markers (lines 175 and 244) pass through tracking. Therefore a new capacity check no longer forgets work still waiting in LevelDB (the on-disk store's queue). The new regression at `test/storage-bounds.test.cjs:75–101` binds 20 rooms before updating them without yielding, checks the settled quota and zero unfinished bytes, and checks retained room contents.

### Local test evidence

Fresh scratch clone: `REV scratch evidence (not published): rev-pr5-r3.qDbNJC websocket checkout`, detached at the exact head. Node `v26.12.0`, npm `11.20.0`, Darwin arm64. Dependencies were installed from the committed lockfile with `npm ci`. The three independent scripts were copied byte-for-byte from the prior `REV scratch evidence (not published): 8baac84b-080f-4104-a2b5-7416702c57e1 rev-followup` directory. Exact local commands and working directories:

```sh
cd "<REV scratch directory (not published): rev-pr5-r3.qDbNJC websocket checkout>"
npm ci > ../npm-ci.log 2>&1
npm test > ../npm-test.log 2>&1
cd "<REV scratch directory (not published): rev-pr5-r3.qDbNJC>"
node review-probes.cjs > review-probes.log 2>&1
node quota-burst.cjs > quota-burst.log 2>&1
node revoke-membership.cjs > revoke-membership.log 2>&1
```

Every command exited 0. The observational quota scripts do not themselves fail on overflow, so the emitted byte values were inspected rather than relying on exit codes alone. Test-result data (TOON is a compact text representation of tabular data):

```toon
checks[7]{check,result}:
  npm_ci,exit 0; 286 packages installed
  npm_test,exit 0; standard and TypeScript; room-release; auth 25; session-persistence 13; storage-bounds 4
  sequential_quota,52728 bytes <= 65536
  already_bound_rooms_burst,53202 bytes <= 65536; 1 room retained; settled inFlightBytes 0
  expiry_handshake,4401; subsequent observer frames 0; observer text empty
  delete_during_load,clear only; no subsequent store
  membership_revocation,revoked; room and awareness membership removed; last-peer room released
```

The burst used 20 already-bound rooms, each receiving 49,152 bytes of random hexadecimal text with no await between updates, and a 100,000-byte per-room limit. Queued accounting was `reservedBytes=52896`, `inFlightBytes=50736`, `tombstoneReserve=152`; measured disk at that point was 2,160 bytes. After the queue drained and 400 ms idle, disk held 53,202 bytes, versus the r2 counterexample's 986,958 bytes. The suite also verified retained content is complete and the 1,000-byte per-room limit drops a 1,080-byte state.

Evidence: installation log (REV scratch evidence (not published): `npm-ci.log`), npm test log (REV scratch evidence (not published): `npm-test.log`), original probes (REV scratch evidence (not published): `review-probes.cjs`) / output (REV scratch evidence (not published): `review-probes.log`), burst probe (REV scratch evidence (not published): `quota-burst.cjs`) / output (REV scratch evidence (not published): `quota-burst.log`), membership probe (REV scratch evidence (not published): `revoke-membership.cjs`) / output (REV scratch evidence (not published): `revoke-membership.log`). `git diff --check 67aae1d7..5e7fe4a5` exited 0; the checkout remained clean after testing.

### CI status and limits

No usable CI result exists for this head: `gh pr view 5 --repo RCOSDP/RDM-y-websocket-dev2027 --json statusCheckRollup` returned an empty list; the GitHub check-runs and commit-status endpoints each reported `total_count=0`. A legacy `.github/workflows/ci.yml` exists in Git, but the Actions workflows endpoint returned no registered workflows. The CI-less merge rule therefore has a **REV pass plus recorded successful local tests** for this head; no approval or merge was performed.

Installation reported 14 dependency audit vulnerabilities (4 low, 2 moderate, 8 high); dependencies did not change in this diff and no audit remediation was attempted. Node emitted an experimental localStorage warning without failing tests. Deployment, browser acceptance, persistent volume location/prefix, and internal network reachability were not verified. Prior limitations remain: deletion tombstones are in memory, overflow drafts stay in memory, and LevelDB compaction needs transient disk headroom. No Docker state changes or `runtime/.env` reads occurred. Only scratch artifacts and exactly one PR conversation comment were written; no source edit, commit, push, approval, merge, or close was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**pass。追加の R3 指摘なし。R2-01 / P2 は解消**し、R1-03 に残っていた待機中書込みの問題も解消した。対象は `bin/persistence.cjs` と `test/storage-bounds.test.cjs` の1コミット差分。PR head は `5e7fe4a524c7cd970d44085b6f3eacd82e2fb425` と一致した。判定はこの head と範囲に対するもの。

`bin/persistence.cjs:104–113` の `track` は同期的に予約を加え、処理完了時に減らす。126行の再計測では実ディスク量に `inFlight` を加える。本文書込み（139行）と削除マーカー（175・244行）の両方が追跡対象で、LevelDB（ディスク上の保存機構）の待ち行列にある予約を容量再検査で忘れなくなった。`test/storage-bounds.test.cjs:75–101` の追加回帰試験は、先に20部屋を bind し、待機せず更新して、処理終了後の容量上限・未完了量0・保持された部屋の本文一致を検査する。

### ローカル試験の証跡

専用の新規 clone は `REV scratch evidence (not published): rev-pr5-r3.qDbNJC websocket checkout` で、指定 head の detached 状態。環境は Node `v26.12.0`、npm `11.20.0`、Darwin arm64。依存はコミット済み lockfile から `npm ci` で導入した。独立試験3本は前回の `REV scratch evidence (not published): 8baac84b-080f-4104-a2b5-7416702c57e1 rev-followup` から内容を変えずにコピーした。実行した正確なコマンドと作業ディレクトリ:

```sh
cd "<REV scratch directory (not published): rev-pr5-r3.qDbNJC websocket checkout>"
npm ci > ../npm-ci.log 2>&1
npm test > ../npm-test.log 2>&1
cd "<REV scratch directory (not published): rev-pr5-r3.qDbNJC>"
node review-probes.cjs > review-probes.log 2>&1
node quota-burst.cjs > quota-burst.log 2>&1
node revoke-membership.cjs > revoke-membership.log 2>&1
```

全コマンドの終了コードは0。観測用の容量試験は容量超過でも失敗終了しないため、終了コードだけでなく出力値を確認した。結果を TOON（表形式のデータを短い文字で表す形式）で示す。

```toon
checks[7]{check,result}:
  npm_ci,終了0; 286パッケージ導入
  npm_test,終了0; standardとTypeScript; room-release; auth 25件; session-persistence 13件; storage-bounds 4件
  順次容量試験,52728 bytes <= 65536
  bind済み部屋の一斉更新,53202 bytes <= 65536; 1部屋保持; 完了後inFlightBytes 0
  期限と切断応答,4401; 期限後の観測フレーム0; 観測本文は空
  読込み中の削除,clearのみ; その後のstoreなし
  失効と所属,失効済み; 部屋とawarenessから除外; 最後の接続の部屋を解放
```

一斉更新は20部屋を先に bind し、各部屋へ49,152 bytesの乱数16進文字列を、部屋間で await せず挿入した。部屋ごとの上限は100,000 bytes。待機中の値は `reservedBytes=52896`、`inFlightBytes=50736`、`tombstoneReserve=152`、その時点の実ディスク量は2,160 bytesだった。待ち行列を処理し400 ms静止後は53,202 bytesで、r2の反例986,958 bytesから改善した。標準試験では保持された本文の完全一致と、1,000 bytesの部屋上限に対して1,080 bytesの状態が削除されることも確認した。

証跡: 導入ログ (REV scratch evidence (not published): `npm-ci.log`)、npm testログ (REV scratch evidence (not published): `npm-test.log`)、前回のプローブ (REV scratch evidence (not published): `review-probes.cjs`) / 出力 (REV scratch evidence (not published): `review-probes.log`)、一斉更新プローブ (REV scratch evidence (not published): `quota-burst.cjs`) / 出力 (REV scratch evidence (not published): `quota-burst.log`)、所属プローブ (REV scratch evidence (not published): `revoke-membership.cjs`) / 出力 (REV scratch evidence (not published): `revoke-membership.log`)。`git diff --check 67aae1d7..5e7fe4a5` は終了0。試験後も checkout に差分はない。

### CI の状態と限界

対象 head に利用できる CI 結果はない。`gh pr view 5 --repo RCOSDP/RDM-y-websocket-dev2027 --json statusCheckRollup` は空の一覧で、GitHub の check-runs と commit-status もそれぞれ `total_count=0`。Git 内には旧 `.github/workflows/ci.yml` があるが、Actions workflows API に登録済み workflow はなかった。従って CI なしの場合の条件である **REV pass と成功したローカル試験記録** はこの head について揃った。approve や merge は行っていない。

導入時の監査には依存の脆弱性14件（low 4・moderate 2・high 8）が表示された。今回の差分で依存は変更されておらず、監査の修正作業は行っていない。Node の実験的 localStorage 警告は出たが試験は成功した。配備・ブラウザ受入・永続ボリュームの場所と接頭辞・内部ネットワーク到達範囲は未確認。削除済み記録はメモリのみ、容量超過時の下書きもメモリのみ、LevelDB の圧縮整理には一時的なディスク余裕が必要という既知の制約は残る。Docker 状態の変更と `runtime/.env` の読取りはない。出力は scratch 資料と PR 会話コメント1件のみで、ソース変更・commit・push・approve・merge・close は行っていない。
