# Review: JWT authentication / JWT 認証

> **Summary:** Pass for the server patch; the integrated editing chain still needs client token renewal. No unauthenticated document or awareness path was found.
> **概要:** サーバ差分は pass。編集経路全体にはクライアントのトークン更新が必要。未認証の文書・参加情報への経路は見つからなかった。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Closing after upgrade is safe for document confidentiality when rejected sockets never reach room setup. ／ upgrade 後の close でも、拒否ソケットを部屋の初期化へ渡さなければ文書の秘密性を保てる。
- Applies to: `RCOSDP/RDM-y-websocket-dev2027` PR #2, head `35cc9de1fa87b5e58c565137011c8c2311fa4620`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Chain review 2 / 関連レビュー 2](2026-11-10_RDM-wiki-frontend-dev2027_PR3_JWT_Client_r1.md) · [Chain review 3 / 関連レビュー 3](2026-11-10_RDM-osf.io-dev2027_PR4_Wiki_Bundle_Path_r2.md).
- Used by / 利用先: [SPEC-04 acceptance / 受入](../spec/04_acceptance_tests.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Pass for PR #2.** No blocking defect in the reviewed server change. This is a written verdict, not a GitHub approval. The three-PR chain is **changes requested** because of frontend R1-01 (P2).

**R1-01 [P3, advisory]: document the boundary for Origin and request logs.** `bin/auth.cjs:36–61` ignores `request.headers.origin`; a local probe accepted a valid token from `https://foreign.example`. The omitted wrapper offered optional `Y_WEBSOCKET_ALLOWED_ORIGINS`, which this replacement does not implement. Consider carrying over an explicit allow-list and documenting missing-Origin policy. This is defense in depth: an unrelated website cannot obtain the page's token merely by opening a socket, and cookies are not the credential here. No unauthenticated cross-site bypass was demonstrated.

`?token=` necessarily places the bearer value in the upgrade request URL (`src/y-websocket.js:385–388`). `bin/server.cjs:37–42` logs a fixed rejection reason or document/user identifiers, not the URL or token. The test checks this application's captured stdout/stderr only. No reverse-proxy access-log configuration was supplied or verified; a proxy logging the full request target would retain the token. Document query redaction or disabled request-target logging at every proxy and use TLS for remote deployments. This is an unverified deployment requirement, not evidence of a currently leaking access log. Document/user IDs remain in application logs by design.

### Security and compatibility checks

`bin/auth.cjs:8,25,51–61` pins HS256, uses jsonwebtoken verification (including expiry), requires numeric `exp` and a nonempty string `sub`, and exactly matches `doc_id` against the raw path-derived room. Missing, empty or duplicate token parameters fail closed. The same validated room is passed to setup, avoiding a second interpretation. The issuer generates UUID room strings, so path encoding does not change the normal contract. Missing/empty `JWT_SECRET` exits before listening.

`bin/server.cjs:31–43` authorizes before upgrade and only emits `connection` for success. Rejection completes the handshake for observable 4401, then closes without calling `setupWSConnection`. Even a frame buffered with the handshake cannot reach the room handler. Document creation, persistence binding, update/callback listeners and awareness are downstream of `bin/utils.cjs:306–352`; rejected sockets never enter them. The HTTP handler returns only `okay`, not document data. Exported utils remain an embedding API and do not authenticate arbitrary third-party servers; the shipped Dockerfile runs the protected `npm start` entry point.

The real osf.io `generate_y_websocket_token` function was extracted with Python AST and executed with PyJWT 1.5.3 using synthetic values. PR #2 accepted the result. The issuer supplies HS256, string `sub`, UUID `doc_id`, and `exp`, with default TTL eight hours (`addons/wiki/settings/defaults.py:11–14`). Minting is restricted to `can_edit` in `addons/wiki/views.py:328–336`. Server `JWT_SECRET` must match issuer `Y_WEBSOCKET_SECRET`; the current, already modified guide workspace's `web.json:27` contains the alias, but that workspace observation is not proof of a committed or deployed configuration.

Expiry is explicitly an admission-time rule in the issuer settings. A socket staying open past expiry is therefore not reported as a new bug. Reconnection after expiry does fail, requiring the client fix in the companion review. Revocation during an existing connection is not implemented.

### Omitted wrapper

Read upstream frontend commit `c3bd5c5b0058` through `gh api`. Omitting `docker/y-websocket-auth/` is appropriate when deploying this server head: that wrapper used custom HMAC comparison, optional expiry, fail-open behavior without its secret, and HTTP 401 instead of 4401. The library-based, mandatory-secret server supersedes those mechanisms. The optional Origin policy is the one relevant feature not carried over. Merely merging frontend PR #3 while still running an old unauthenticated server is insufficient.

### Evidence and limits

Cloned only into `/private/tmp/rev-task-7b6692ec/ws` and confirmed the exact head. `npm ci --ignore-scripts` followed by `npm test` passed lint/type checking, room release, and all 21 authentication cases on the host. Cases cover invalid algorithms/claims, valid bidirectional providers, rejected writes and captured application logs. A separate synthetic short-TTL probe confirmed continued open-session access, 4401 reconnects and foreign-Origin acceptance. Its assertions completed; its remaining Y.Doc timer required terminating that scratch probe process. No grdm-dev Docker state, runtime/.env, application commits, pushes, approval or merge state was touched. No browser C4, production logging or live deployment was verified.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**PR #2 は pass。** サーバ差分に必須修正は見つからなかった。これは記録上の判定であり、GitHub の approve ではない。3 PR 全体は frontend R1-01（P2）のため **changes requested**。

**R1-01［P3、助言］：Origin とリクエストログの境界を文書化する。** `bin/auth.cjs:36–61` は `request.headers.origin` を見ない。ローカル試験で有効なトークンと `https://foreign.example` の組合せを受理した。省略されたラッパーには任意の `Y_WEBSOCKET_ALLOWED_ORIGINS` があったが、代替サーバには無い。許可リストと Origin 無しの場合の方針を検討すること。これは追加の防御であり、別サイトがソケットを開くだけでページのトークンを取得できるわけではない。認証には cookie を使っていない。未認証のクロスサイト迂回は実証していない。

`?token=` により bearer 値は upgrade URL に入る（`src/y-websocket.js:385–388`）。`bin/server.cjs:37–42` のログは固定の拒否理由または文書・利用者 ID で、URL やトークンではない。試験が検査するのはこのプロセスの stdout/stderr のみ。プロキシのアクセスログ設定は提供・確認されていない。完全なリクエスト先を記録するプロキシならトークンが残る。全プロキシでクエリの伏字化またはリクエスト先記録の無効化を文書化し、遠隔配備には TLS を用いること。これは未検証の配備条件で、現にアクセスログへ漏洩したという指摘ではない。文書・利用者 ID は設計どおりアプリケーションログに残る。

### セキュリティと互換性

`bin/auth.cjs:8,25,51–61` は HS256 に固定し、jsonwebtoken に署名と期限を検証させる。数値 `exp`、空でない文字列 `sub`、生のパスから得た部屋名と完全一致する `doc_id` を要求する。トークン無し・空・重複を拒否する。同じ検証済み部屋名を setup に渡すため再解釈の不一致はない。発行側は UUID を使うため、通常経路でパスの符号化による相違はない。秘密無し・空なら listen 前に終了する。

`bin/server.cjs:31–43` は upgrade 前に認証し、成功時のみ `connection` を発火する。拒否時は 4401 をブラウザに届けるため handshake を完了するが、`setupWSConnection` を呼ばず close する。handshake と一緒に届いたフレームも部屋の handler に到達しない。文書生成、永続化、更新/callback、awareness は `bin/utils.cjs:306–352` の先にあり、拒否ソケットは到達しない。HTTP handler は `okay` だけを返す。公開 utils は組込み用 API であり、他者が作るサーバまで自動認証するものではない。同梱 Dockerfile は保護された `npm start` を起動する。

osf.io の実 `generate_y_websocket_token` 関数を Python AST で抽出し、PyJWT 1.5.3 と架空の値で実行した。PR #2 はその結果を受理した。発行側は HS256、文字列 `sub`、UUID `doc_id`、`exp` を持ち、既定有効期間は8時間（`addons/wiki/settings/defaults.py:11–14`）。発行は `can_edit` に制限される（`addons/wiki/views.py:328–336`）。サーバの `JWT_SECRET` と発行側の `Y_WEBSOCKET_SECRET` を一致させる必要がある。既に変更中の guide 作業領域の `web.json:27` には別名設定があるが、コミット・配備済みの証拠ではない。

発行側設定は期限を接続時の条件と明記している。接続中の期限超過は新規不具合とは判定しない。期限後の再接続は拒否されるため、関連クライアントレビューの修正が必要。既存接続に対する途中の権限取消しは実装されていない。

### 省略されたラッパー

上流 frontend コミット `c3bd5c5b0058` を `gh api` で読んだ。このサーバ head を配備するなら `docker/y-websocket-auth/` の省略は妥当。旧ラッパーは自作 HMAC 比較、任意の期限、秘密無しでの認証省略、4401 ではなく HTTP 401 を使用していた。必須の秘密とライブラリ検証を使う今回のサーバが代替する。任意の Origin 制限は引き継がれていない。旧未認証サーバを動かしたまま frontend PR #3 だけを統合しても不十分。

### 根拠と限界

独自 scratch `/private/tmp/rev-task-7b6692ec/ws` に clone して head を確認した。ホストで `npm ci --ignore-scripts` 後の `npm test` は lint・型検査、room release、認証21件に合格。異なるアルゴリズム・不正 claims、有効な双方向同期、拒否接続の書込み、アプリケーションログを検査した。短い期限の追加試験で、接続継続、4401 再接続、別 Origin の受理を確認した。assertion は完了したが Y.Doc の timer が残り scratch の試験プロセスを終了させた。grdm-dev の Docker、runtime/.env、アプリケーションの commit・push・approve・merge は変更していない。ブラウザ C4、本番ログ、実配備は未検証。

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
