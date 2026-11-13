# REV PR5 Revocation and persistence review r2 / 失効・永続化レビュー r2

> **Summary:** Changes requested. Expiry, deletion cancellation, and types are fixed; queued writes still defeat the total quota.
> **概要:** 要修正。期限失効・削除の取消し・型は修正済みだが、未完了書込みが全体容量制限を破る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r2.md` (SHA-256: `d1cd417c84391480d43592900be8e05af8903fc36f60215452f78454d411c7f3`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-11. **Learned:** Disk measurements must retain reservations for writes not yet on disk. ／ ディスクの再計測時も、まだ書かれていない予約容量を保持する必要がある。
- Applies to / 対象: RCOSDP/RDM-y-websocket-dev2027 PR #5, head 67aae1d7efaa4bb002b60f572b15fd631b65d980
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Prior review / 前回レビュー](2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r1.md) · [Paired review / 対応レビュー](2026-11-11_RDM-osf.io-dev2027_PR12_File_Editor_Yjs_r3.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** Reviewed exact head `67aae1d7efaa4bb002b60f572b15fd631b65d980` against the prior `036ad406`. R1-01 (expiry), R1-02 (delete/load race), and R1-04 (type contracts) are closed. R1-03 remains open for queued writes; the per-room portion is fixed.

### R2-01 / P2 — preserve pending reservations when measuring the directory

`bin/persistence.cjs:104–107` replaces `used` with the current directory size whenever the next write does not fit. Previously reserved writes can still be waiting in the LevelDB queue and absent from that measurement. Their payload reservation is then forgotten, so more writes fit. Reserving each write synchronously does not make that reset safe.

An independent real-LevelDB probe first binds 20 empty rooms, then inserts 49,152 bytes of random hexadecimal text into each room without awaiting between updates. Every room stays below the configured 100,000-byte room limit. With a 65,536-byte total limit, the queued accounting reported 51,443 bytes plus 3,060 bytes of deletion reserve, while the settled directory held **986,958 bytes and all 20 rooms**. The prior probe that awaits each room's bind passes at 52,728 bytes; it drains earlier work and misses this case. This is queued payload accounting loss, not merely temporary compaction headroom.

Keep outstanding reservations separate from the measured disk baseline, or serialize measurement with completion of all reserved writes before rebasing. Add a regression with multiple already-bound rooms updated without yielding, then assert the bound after the queue settles and while idle.

### Verified fixes and evidence

The original non-cooperative socket probe receives 4401 and its subsequent update causes zero observer frames and no text change. Direct invocation of the actual revocation function with a controlled connection also removes room membership and awareness and releases the last-peer room. The expiry timer calls that function. The delayed-load DELETE probe records only `clear`, with no later `store`. The generation check survives document destruction. The room-limit regression clears a 1,080-byte state under a 1,000-byte limit.

```toon
checks[7]{check,result}:
  npm_test,passed lint and TypeScript; room-release; auth 25; session-persistence 13; storage-bounds 3
  original_expiry_probe,4401 then zero observer frames and empty text
  revocation_membership_probe,revoked and removed from room and awareness
  original_delete_load_probe,clear only; no post-delete store
  original_sequential_quota_probe,52728 bytes under 65536
  already_bound_rooms_burst,986958 bytes over 65536; 20 rooms retained
  deployment_and_browser_acceptance,not run
```

Run from scratch `rev-followup` (dependencies reused from the prior scratch installation; Node 26.12.0, macOS arm64):

```sh
(cd websocket && npm test)
node review-probes.cjs
node revoke-membership.cjs
node quota-burst.cjs
```

The first three commands succeed; the final probe prints the quota counterexample. It is an observational probe, so its exit code is zero even when it shows a violated bound. Sources and logs: original probes (REV scratch evidence (not published): `review-probes.cjs`), original results (REV scratch evidence (not published): `review-probes.log`), membership probe (REV scratch evidence (not published): `revoke-membership.cjs`), membership results (REV scratch evidence (not published): `revoke-membership.log`), burst probe (REV scratch evidence (not published): `quota-burst.cjs`), burst results (REV scratch evidence (not published): `quota-burst.log`), npm test (REV scratch evidence (not published): `websocket-tests.log`). An initial membership fixture lacked awareness metadata; it was corrected before the successful run.

The prior deployment limits still apply: persistence location/prefix and internal network reachability were not verified; tombstones remain in memory; overflow uses memory-only drafts. No Docker state or runtime/.env was accessed. Only scratch review artifacts and one PR conversation comment were written; no commit, push, approval, merge, or close. Used by: the paired OSF review and the coordinator's integration decision.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**changes requested（要修正）。** 正確な head `67aae1d7efaa4bb002b60f572b15fd631b65d980` を前回の `036ad406` と比較した。R1-01（期限失効）、R1-02（削除と読込みの競合）、R1-04（型宣言）は解消。R1-03 は待機中の書込みについて未解消で、部屋ごとの上限は修正済み。

### R2-01 / P2 — ディスク再計測で未完了の予約を忘れない

`bin/persistence.cjs:104–107` は次の書込みが収まらないと `used` を現在のディレクトリ容量で置き換える。既に予約した書込みがLevelDBの待ち行列にあり、まだディスクに現れていない場合、その容量予約が消え、さらに書込みを許可する。各予約が同期処理であるだけでは、この置換は安全にならない。

実LevelDBの独立試験で空の20部屋を先にbindし、部屋間で待たずに各部屋へ49,152 bytesの乱数の16進文字列を挿入した。各部屋は指定100,000 bytes未満。全体65,536 bytesに対して、待機中の計算は51,443 bytesと削除予約3,060 bytesだったが、書込み終了後のディレクトリは **986,958 bytes、20部屋すべて保持** となった。部屋ごとにbindを待つ前回試験は52,728 bytesで通るが、その待機で先行書込みが進むため今回の条件を見逃す。これは一時的な圧縮整理の余裕容量ではなく、未完了の本文容量を忘れる問題。

未完了の予約を実ディスク量と別に保持するか、予約済み書込みを全て完了させてから基準を再計測する必要がある。既にbind済みの複数部屋を待たずに更新し、待ち行列が空になった後と停止中の容量を確認する回帰試験を追加すること。

### 解消の確認と証跡

前回の切断応答を返さないソケット試験では4401を受信し、その後の更新による観測側フレームは0、本文変更もなし。実際の失効関数を制御した接続で呼ぶ試験でも、部屋への所属とawareness（参加者状態）が消え、最後の接続の部屋が解放された。期限タイマーはこの関数を呼ぶ。読込み遅延中のDELETE試験は `clear` のみで、その後の `store` はない。世代の検査は文書破棄後にも効く。部屋上限の回帰試験では上限1,000 bytesに対する1,080 bytesの状態を消去した。

```toon
checks[7]{check,result}:
  npm_test,lintとTypeScript成功; room-release成功; auth 25件; session-persistence 13件; storage-bounds 3件
  前回の期限試験,4401後の観測フレーム0と空の本文
  失効と所属の試験,失効済みで部屋とawarenessから除外
  前回の削除読込み試験,clearのみ; 削除後のstoreなし
  前回の順次容量試験,上限65536に対し52728 bytes
  bind済み部屋の一斉更新,上限65536に対し986958 bytes; 20部屋保持
  配備とブラウザ受入,未実行
```

scratchの `rev-followup` で実行する。依存は前回のscratch導入物を再利用し、Node 26.12.0、macOS arm64を使用。

```sh
(cd websocket && npm test)
node review-probes.cjs
node revoke-membership.cjs
node quota-burst.cjs
```

最初の3コマンドは成功し、最後は容量の反例を表示する。最後は観測用なので上限違反でも終了コード0。ソースと記録: 前回の試験 (REV scratch evidence (not published): `review-probes.cjs`)、その結果 (REV scratch evidence (not published): `review-probes.log`)、所属試験 (REV scratch evidence (not published): `revoke-membership.cjs`)、所属結果 (REV scratch evidence (not published): `revoke-membership.log`)、一斉更新試験 (REV scratch evidence (not published): `quota-burst.cjs`)、一斉更新結果 (REV scratch evidence (not published): `quota-burst.log`)、npm test (REV scratch evidence (not published): `websocket-tests.log`)。所属試験の初回の代役にはawarenessの付随情報が欠けていたため、補正してから成功を確認した。

前回の配備上の制約は残る。保存先・接頭辞・内部ネットワークの到達範囲は未確認で、削除済み記録はメモリのみ、容量超過時の下書きもメモリのみとなる。Dockerの状態とruntime/.envにはアクセスしていない。書込みはscratchのレビュー資料とPR会話コメント1件のみで、commit、push、approve、merge、closeはなし。Used by: 対応OSFレビューと調整者の統合判断。
