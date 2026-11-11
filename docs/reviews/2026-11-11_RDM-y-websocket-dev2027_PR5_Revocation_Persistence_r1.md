# REV PR5 Revocation and persistence review r1 / 失効・永続化レビュー r1

> **Summary:** Changes requested. Independent probes found writes after expiry, post-delete re-persistence, and ineffective storage bounds; npm test also fails type checking.
> **概要:** 要修正。期限後の書込み、削除後の再永続化、容量上限の不徹底を独立再現し、npm testの型検査も失敗した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-11_RDM-y-websocket-dev2027_PR5_Revocation_Persistence_r1.md` (SHA-256: `1ebc875af4482436a19608afa6b5ccca2d73200663333ed53e63bf6ef2e2f5c5`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-11. **Learned:** Sending a close frame is not immediate revocation, and asynchronous persistence needs cancellation and write accounting. ／ 切断フレーム送信だけでは即時失効にならず、非同期永続化には取消しと書込み容量の管理が必要。
- Applies to / 対象: RCOSDP/RDM-y-websocket-dev2027 PR #5, head 036ad4067fa1bffcf12c8c87a5496f1991786ad4
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [OSF integration review / OSF連携レビュー](2026-11-11_RDM-osf.io-dev2027_PR12_File_Editor_Yjs_r2.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** Compared with base `d4d1cfaed2e4b10362237df1f3424b2a076a56fb`. Four findings require correction before the expiry, deletion and bounded-storage claims can pass.

### Required changes

**R1-01 / P1 — reject incoming frames immediately at expiry.** `bin/server.cjs:52–55` calls `ws.close(4401)` but `bin/utils.cjs:348` continues to dispatch messages while the transport is CLOSING. The installed ws 6 receiver still emits messages until its peer completes the close handshake. A client that suppresses the close reply received 4401, sent a valid Yjs update, and caused a second client's text to become `AFTER-EXPIRY`. This is a write after expiry, not merely an already-buffered server frame. Mark the session unauthorized and detach/guard its message handler and room membership at the expiry boundary, preserving the 4401 close reason. Test a non-cooperative peer as well as normal expiry. Ordinary invalid/expired upgrade tests pass with zero document frames; the newly observed defect concerns an established session.

**R1-02 / P1 — cancel an in-flight bind before destroying/deleting a room.** `bin/utils.cjs:335–338` destroys the document before calling `clearDocument`. Its destroy listener at `bin/persistence.cjs:81` removes the state entry, so `clearDocument:121–122` cannot set that bind's `dropped` flag. A pending `getYDoc` resumes at lines 102–116 and writes the full document after the deletion. A deterministic delayed-read probe observed `clear(file-delete-race)` followed by `store(file-delete-race,25 bytes)`. It uses the real persistence adapter and document lifecycle with a recording storage double. Cancel/await outstanding binds before clearing, and test delayed hydration plus DELETE and disk contents after restart. The normal already-loaded-room DELETE test does pass.

**R1-03 / P2 — account for pending writes to enforce storage limits.** `bin/persistence.cjs:57–62,96–100` reuses a directory size for 10 seconds, does not reserve projected writes, and checks before writing. A real LevelDB probe with a 65,536-byte total limit wrote 20 rooms below the per-room limit and left 986,600 bytes in the directory, about 15 times the limit. No further event forces removal when traffic stops. `clearDocument` deletes keys, not physical database files; compaction is another part of enforcing a disk budget. The per-room check at lines 86–94 also waits for another quarter-limit worth of updates, so it is not a strict bound. Use serialized accounting/reservations with an explicit compaction/headroom policy or enforce a true storage quota, and test bursts and quiescence, not only a directory already over a one-byte threshold.

**R1-04 / P2 — repair type contracts so the required test command runs.** `npm test` fails before runtime tests with TS2322 at `bin/auth.cjs:76`, TS2339 at `bin/server.cjs:78`, and two TS2339 errors at `bin/utils.cjs:337–338`. The authorizeUpgrade return type omits `exp`; persistence type annotations omit `clearDocument`. Update the declared contracts and run `npm test` successfully.

### Deletion authorization, network exposure, and paths

`authorizeDelete` verifies HS256 using `JWT_SECRET`, numeric unexpired `exp`, exact `doc_id`, and `purpose: delete`. It rejects missing credentials, normal room tokens, wrong-room tokens, bad signatures, and expired tokens. Upgrade rejects any token carrying `purpose`. No `sub` identity or source IP is required for DELETE: any bearer of a correctly signed purpose-specific credential can call it wherever the HTTP listener is reachable. The same listener handles WebSocket upgrades; `Y_WEBSOCKET_ALLOWED_ORIGINS` is only consulted for upgrades. Default bind is localhost, but deployment may override HOST. The OSF helper sends the token to configured `Y_WEBSOCKET_INTERNAL_URL` with a 60-second lifetime; this code does not prove an internal-only network boundary. No authentication bypass was found in normal room tokens.

The LevelDB directory is exactly `YPERSISTENCE`; relative paths resolve from process cwd (`/home/node/app` in the supplied Dockerfile). It is disabled when that environment variable is absent. No durable volume or deployment path is established by PR #5. The prefix defaults to empty, so all rooms persist unless the deployer explicitly sets `file-`. Room names are encoded database keys in one LevelDB database, not filesystem path components; inspection of `y-leveldb` found no room-name traversal into another directory. The OSF helper URL-quotes room names; DELETE also rejects literal slashes. Storage configuration is trusted operator input.

Tombstones last 24 hours by default, live only in memory, and disappear on restart. Oversized rooms fall back to memory and lose unsaved edits on last departure. The paired OSF review records the renewal/cleanup limitation. These accepted-by-code behaviors still need explicit deployment/retention decisions; no runtime/.env or Docker state was accessed.

### Independent tests and reproducibility

```toon
checks[7]{check,result}:
  auth.test.cjs,25 passed
  room-release.test.cjs,passed
  session-persistence.test.cjs,12 passed
  npm_test,failed with four new TypeScript errors
  expiry_adversarial_probe,4401 then peer text AFTER-EXPIRY
  delete_load_race_probe,clear then store of 25 bytes
  total_disk_limit_probe,65536 configured and 986600 observed
```

Tests ran on macOS arm64 with Node 26.12.0 in scratch only. The first persistence test attempt could not load the native leveldown module after an install with scripts disabled; `npm rebuild leveldown` resolved that local setup issue, and all 12 cases then passed. No Docker or full browser acceptance was run.

From `REV scratch evidence (not published): rev-work websocket checkout`, with installed dependencies, the first command is expected to fail with the four type errors, while the direct runtime tests pass:

```sh
npm test
node test/auth.test.cjs
node test/room-release.test.cjs
node test/session-persistence.test.cjs
```

From scratch `rev-work`, run the independent probes. Expected output includes the three counterexamples:

```sh
node review-probes.cjs
```

Evidence: probe source (REV scratch evidence (not published): `review-probes.cjs`), probe results (REV scratch evidence (not published): `review-probes.log`), npm test output (REV scratch evidence (not published): `websocket-tests.log`). The delete-race probe is deterministic with a storage double; the expiry and disk-size probes use real sockets and real LevelDB respectively. No commit, push, approval, merge, or issue closure was performed. Used by: the paired OSF review and the coordinator's integration decision.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**changes requested（要修正）。** base `d4d1cfaed2e4b10362237df1f3424b2a076a56fb` と比較した。期限失効、削除、容量上限の主張を合格とするには、4件の修正が必要。

### 必要な修正

**R1-01 / P1 — 期限切れ時点で受信フレームを直ちに拒否する。** `bin/server.cjs:52–55` は `ws.close(4401)` を呼ぶが、`bin/utils.cjs:348` はCLOSING中も受信を処理する。導入したws 6の受信側は相手が切断手順を完了するまでメッセージを通知する。切断応答を止めたクライアントが4401を受け取った後、有効なYjs更新を送ると、別クライアントの本文が `AFTER-EXPIRY` になった。これは既に送信済みだったフレームではなく期限後の書込み。4401の理由を保ちつつ、失効時点で認可状態を解除し、受信ハンドラと部屋への参加を解除または拒否する必要がある。通常の期限試験に加えて、切断に協力しない相手を試験する。無効・期限切れトークンによるupgradeは文書フレーム0で通過しており、今回の問題は接続済みセッションにある。

**R1-02 / P1 — 部屋を破棄・削除する前に読み込み途中のbindを取り消す。** `bin/utils.cjs:335–338` は `clearDocument` より先に文書を破棄する。`bin/persistence.cjs:81` の破棄リスナーが状態の対応を消すため、`clearDocument:121–122` でそのbindの `dropped` を立てられない。待機中の `getYDoc` が102–116行で再開し、削除後に全文を書き戻す。読み込みを遅延させた決定的な試験で `clear(file-delete-race)` の後に `store(file-delete-race,25 bytes)` を確認した。実際の永続化アダプターと文書ライフサイクルに、操作を記録するストレージ代役を使っている。未完了bindを取り消し・待機してから消し、読み込み遅延とDELETE、再起動後のディスク内容を試験する必要がある。通常の読み込み済み部屋のDELETE試験は通る。

**R1-03 / P2 — 未完了の書込みも数えて容量制限を実施する。** `bin/persistence.cjs:57–62,96–100` はディレクトリ容量を10秒間使い回し、書込み予定量を予約せず、書く前にしか検査しない。実LevelDBで全体65,536 bytesを指定し、個別上限未満の20部屋を書いたところ、986,600 bytes、約15倍が残った。その後通信が止まると削除の契機もない。`clearDocument` はキーを消すだけで物理DBファイルを直接縮めず、ディスク上限には圧縮整理も関わる。86–94行の個別検査も上限の4分の1相当の更新を待つため厳密な上限ではない。直列化した容量計算・予約と圧縮整理・余裕容量の方針、または実際のストレージ割当上限を用意し、既に1 byteを超えた領域だけでなく、一斉書込みと停止後を試験する必要がある。

**R1-04 / P2 — 型宣言を直して標準試験を通す。** `npm test` は実行試験へ進む前に、`bin/auth.cjs:76` のTS2322、`bin/server.cjs:78` のTS2339、`bin/utils.cjs:337–338` のTS2339二つで失敗した。authorizeUpgradeの戻り値型に `exp`、永続化の型宣言に `clearDocument` がない。宣言を更新し、`npm test` を通す必要がある。

### 削除認証、到達範囲、パス

`authorizeDelete` は `JWT_SECRET` によるHS256、数値で有効期限内の `exp`、一致する `doc_id`、`purpose: delete` を検証する。資格情報なし、通常の部屋用トークン、別の部屋、署名不正、期限切れを拒否する。upgradeは `purpose` を持つトークンを拒否する。DELETEには `sub` の身元や接続元IPの条件がなく、専用の正しく署名された資格情報を持つ者はHTTP待受へ到達できる場所から呼べる。WebSocketと同じ待受であり、`Y_WEBSOCKET_ALLOWED_ORIGINS` の参照はupgradeだけ。既定待受はlocalhostだがHOSTで変更できる。OSFのヘルパーは60秒のトークンを設定済み `Y_WEBSOCKET_INTERNAL_URL` へ送るが、このコードだけでは内部ネットワーク限定を保証しない。通常の部屋用トークンによる認証迂回は見つからなかった。

LevelDBの場所は `YPERSISTENCE` そのもの。相対パスはプロセスの作業ディレクトリ基準で、付属Dockerfileでは `/home/node/app`。変数がなければ永続化は無効。PR #5は永続ボリュームや実配備の場所を確定していない。接頭辞の既定は空なので、配備側で `file-` を明示しないと全部屋を保存する。部屋名は一つのLevelDB内の符号化されたキーであり、ファイルシステムのパス部品にはならない。`y-leveldb` の確認では、部屋名から別ディレクトリへのパス逸脱は見つからなかった。OSFヘルパーは部屋名をURL符号化し、DELETEは文字どおりのスラッシュも拒否する。保存先設定は運用者の信頼された入力となる。

削除済み記録の既定寿命は24時間で、メモリのみのため再起動で消える。超過した部屋はメモリだけとなり、最後の利用者が離れると未保存編集を失う。対応OSF記録には更新・掃除の制約を記載した。コードが許容するこれらの挙動についても、配備・保管方針の明示が必要。runtime/.envとDockerの状態にはアクセスしていない。

### 独立試験と再現方法

```toon
checks[7]{check,result}:
  auth.test.cjs,25件成功
  room-release.test.cjs,成功
  session-persistence.test.cjs,12件成功
  npm_test,新しいTypeScriptエラー4件で失敗
  改造クライアントの期限試験,4401後に相手の本文がAFTER-EXPIRY
  削除と読込み競合試験,clearの後に25 bytesのstore
  ディスク全体上限試験,設定65536に対し実測986600
```

scratch内だけでmacOS arm64、Node 26.12.0を使用した。スクリプト無効の依存導入後、初回の永続化試験はleveldownのネイティブモジュールを読めなかった。`npm rebuild leveldown` でローカル環境の問題を解消後、12件すべて通った。Dockerと全体ブラウザ受入は実行していない。

依存導入済み `REV scratch evidence (not published): rev-work websocket checkout` で実行する。最初のコマンドは型エラー4件で失敗し、直接の実行試験は成功する。

```sh
npm test
node test/auth.test.cjs
node test/room-release.test.cjs
node test/session-persistence.test.cjs
```

scratchの `rev-work` で独立試験を実行する。期待出力は3件の反例。

```sh
node review-probes.cjs
```

証跡: 独立試験ソース (REV scratch evidence (not published): `review-probes.cjs`)、試験結果 (REV scratch evidence (not published): `review-probes.log`)、npm test出力 (REV scratch evidence (not published): `websocket-tests.log`)。削除競合試験はストレージの代役を使った決定的な試験、期限試験と容量試験はそれぞれ実ソケットと実LevelDBを使う。commit、push、approve、merge、Issue closeは行っていない。Used by: 対応OSFレビューおよび調整者の統合判断。
