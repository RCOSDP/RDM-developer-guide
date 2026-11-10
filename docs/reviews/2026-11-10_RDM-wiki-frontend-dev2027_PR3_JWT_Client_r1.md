# Review: JWT client / JWT クライアント

> **Summary:** Changes requested: an expired page token is reused indefinitely after a reconnect.
> **概要:** changes requested：再接続時に期限切れのページトークンを繰り返し使う。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** A valid initial token does not provide recovery for long-running editing sessions. ／ 初回のトークンが有効でも、長時間編集の復旧は保証されない。
- Applies to: `RCOSDP/RDM-wiki-frontend-dev2027` PR #3, head `377be42e2873589a22b0214c3d2cebf3e73612ce`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Chain review 1 / 関連レビュー 1](2026-11-10_RDM-y-websocket-dev2027_PR2_JWT_Auth_r1.md) · [Chain review 3 / 関連レビュー 3](2026-11-10_RDM-osf.io-dev2027_PR4_Wiki_Bundle_Path_r2.md).
- Used by / 利用先: [SPEC-04 acceptance / 受入](../spec/04_acceptance_tests.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested: R1-01 [P2].** Initial authentication wiring is correct, but expiry prevents recovery during long editing sessions. No GitHub approve or request-changes review event was submitted; this verdict is conveyed by one comment.

### R1-01 [P2]: refresh credentials and handle 4401 before retrying

Location: `addons/wiki/static/wikiPageMilkdown.js:383–390` and status handlers at `451–464`. The token comes from page-render-time `window.contextVars` and is copied into provider params once. Neither an existing provider nor a newly constructed one on the same page obtains fresh credentials. The issuer's default TTL is eight hours, and the server validates every new upgrade. After that interval, a network interruption, laptop sleep or restarting collaboration leads to repeated 4401 responses with the same expired token. The editor cannot resume shared synchronization without reloading the page. Unsynchronized local edits need preservation during recovery.

The client subscribes to `status` and `connection-error`, not `connection-close` with code 4401. Its locked y-websocket version is 2.0.4 (`yarn.lock:7786`), whose source was read through `gh api`: reconnect reuses `params`, and an HTTP 101/open resets its failed-connection counter before the server's 4401 close. Thus this server's intentional upgrade-then-close can also create rapid, roughly 100 ms retry loops rather than increasing backoff. A synthetic short-TTL run against PR #2 using its provider reproduced repeated 4401s and unchanged params; the corresponding 2.0.4 paths have the same behavior. The full frontend browser was not run.

Add a permission-checked token renewal route or a safe equivalent recovery flow. On 4401, pause retrying, obtain a fresh token only after checking current edit permission, update provider params, and reconnect while keeping the document's local state. If renewal is denied, stop and display an actionable authentication/permission message. Test expiry plus network loss, successful renewed synchronization, denied renewal and bounded retries. Do not solve this by removing expiry or accepting expired credentials.

### Other checks

The client delta exactly matches the client portion of upstream `c3bd5c5b0058`; the only additional file is a four-case construction test. `disableBc: true` remains, so the browser broadcast channel is not an unauthenticated alternative for this editor. `params.token` matches PR #2's single query token contract and osf.io's `edit.mako:525` serialization. The issuer uses matching room ID/subject/HS256 and issues only when `can_edit`. A synthetic token from its extracted real function with PyJWT 1.5.3 was accepted by PR #2.

The query-string token is a bearer credential in the upgrade URL; this patch does not log it directly. Proxy access logs need explicit redaction, as discussed in the server review; those logs were not inspected. Absence of an Origin check in the replacement server is a nonblocking defense-in-depth limitation, not a demonstrated cookie-based bypass.

Omitting `docker/y-websocket-auth/` is correct only when PR #2's authenticated entry point is deployed. The omitted wrapper is not needed for 4401 behavior and has weaker algorithm/expiry/secret handling. Its optional Origin allow-list is not reproduced. Existing connections may outlive expiry by the issuer's explicit policy; the defect here is recovery on a new connection.

### Evidence and limits

Checked exact heads and the upstream cherry-pick using gh reads and private scratch clones. `node addons/wiki/tests/websocket-token.test.cjs` passed all four tests; it checks extracted constructor statements, not expiry, a real editor or browser recovery. PR #2's 21 auth cases and the independent expiry probe support the chain analysis. No full frontend build, browser C4, Docker mutation, runtime/.env access, commit, push, merge or approval was performed. The review records and one comment per PR are the only intended shared changes.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**changes requested：R1-01［P2］。** 初回認証の受渡しは正しいが、長時間編集中の期限切れで復旧できない。GitHub の approve / request-changes イベントは送らず、コメント1件で判定を伝える。

### R1-01［P2］：再試行前に資格情報を更新し 4401 を扱う

対象：`addons/wiki/static/wikiPageMilkdown.js:383–390`、状態 handler `451–464`。トークンはページ描画時の `window.contextVars` から provider params に一度コピーするだけ。既存 provider の再利用でも、同じページでの再生成でも新しい資格情報を取得しない。発行側の既定期限は8時間で、サーバは接続ごとに検証する。その後の通信断、端末の sleep、共同編集の再開で同じ期限切れトークンを送り続け、4401 を繰り返す。ページ再読込なしに共有同期を再開できない。復旧時は未同期のローカル編集を保持する必要がある。

クライアントが購読するのは `status` と `connection-error` で、4401 を持つ `connection-close` ではない。固定された y-websocket は 2.0.4（`yarn.lock:7786`）で、`gh api` からソースを読んだ。再接続は `params` を再利用し、HTTP 101/open で失敗回数をリセットしてからサーバの 4401 close を受ける。そのため意図的な upgrade 後 close が、待機時間を増やさず約100 ms の再試行を生む。PR #2 の provider と短い有効期間を用いた追加試験で、params が変わらず 4401 が反復することを再現した。2.0.4 の該当経路も同じ動作。frontend 全体をブラウザでは動かしていない。

権限を再確認するトークン更新 API または同等の安全な復旧処理を追加すること。4401 では再試行を止め、編集権限を確認して新しいトークンを取得し、文書のローカル状態を保ったまま params を更新して再接続する。更新が拒否されたら停止し、認証・権限の状態と対処を表示する。期限切れと通信断、更新後の同期、更新拒否、再試行回数の制御を試験する。期限の削除や期限切れ資格情報の受理で回避しないこと。

### その他の確認

クライアント差分は上流 `c3bd5c5b0058` の client 部分と一致し、追加は構築試験4件のみ。`disableBc: true` が維持されるため、このエディタにブラウザ broadcast channel 経由の未認証経路はない。`params.token` は PR #2 の単一 query token と osf.io `edit.mako:525` の出力に一致する。発行側の部屋 ID・subject・HS256 が一致し、`can_edit` の場合のみ発行する。PyJWT 1.5.3 で実関数を抽出実行した架空のトークンは PR #2 に受理された。

query string の値は upgrade URL に入る bearer 資格情報。この差分に直接のログ出力はない。サーバレビューで記したとおり、プロキシのアクセスログは明示的に伏字化する必要があるが、実ログは未調査。代替サーバに Origin 検査がない点は追加防御の限界で、cookie を利用する迂回の実証ではない。

`docker/y-websocket-auth/` の省略は PR #2 の認証済み起動経路を配備する場合に妥当。旧ラッパーは 4401 に不要で、algorithm・expiry・秘密の扱いも弱い。ただし任意の Origin 許可リストは再現していない。既存接続が期限を超えることは発行側の明示的方針であり、今回の不具合は新しい接続での復旧にある。

### 根拠と限界

gh による読取りと独自 scratch clone で head と元 cherry-pick を確認した。`node addons/wiki/tests/websocket-token.test.cjs` は4件合格。これは抽出した constructor 文の試験で、期限、実エディタ、ブラウザ復旧を試験しない。PR #2 の認証21件と追加の期限試験を経路の根拠にした。frontend 全体の build、ブラウザ C4、Docker 変更、runtime/.env の参照、commit・push・merge・approve は行っていない。共有先の変更はレビュー記録と各 PR 1件のコメントのみ。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| JWT | A signed pass containing who may connect, to which document, and until when. | 誰がどの文書へいつまで接続できるかを署名した通行証。 |
| Bearer token | A pass usable by whoever holds its value. | 値を持つ人が使える通行証。 |
| Upgrade | Changing an HTTP connection into a WebSocket connection. | HTTP 接続を WebSocket 接続へ切り替える処理。 |
| Awareness | Shared presence and cursor information. | 参加者やカーソル位置の共有情報。 |
| Bundle / chunk | Browser-ready JavaScript and its separately loaded pieces. | ブラウザ用に組んだ JavaScript と分割された部品。 |
| Origin | The website address from which a browser opens a connection. | ブラウザが接続を開始したサイトのアドレス。 |
| P2 / P3 | Normal-priority required fix / nonblocking improvement. | 通常優先度の必須修正／承認を妨げない改善。 |
