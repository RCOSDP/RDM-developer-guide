# Review: JWT client recovery / JWT クライアント復旧

> **Summary:** Pass: the r1 expiry/retry blocker is resolved.
> **概要:** pass：r1 の期限切れ・再試行の阻害事項は解消。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Recovery must preserve local state while each trust boundary is checked separately. ／ 復旧時はローカル状態を保持し、信頼境界ごとに検証する必要がある。
- Applies to: `RCOSDP/RDM-wiki-frontend-dev2027 PR #3`, head `ec4af739e0c8bfd84a1f10107688700506b2eecf`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [RDM-osf.io-dev2027](2026-11-10_RDM-osf.io-dev2027_PR6_Wiki_Token_Refresh_r1.md) · [RDM-y-websocket-dev2027](2026-11-10_RDM-y-websocket-dev2027_PR3_Origin_Allowlist_r1.md).
- Used by / 利用先: [SPEC-04 acceptance / 受入](../spec/04_acceptance_tests.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass.** R1-01 is resolved at this head, when deployed with osf.io PR #6 and the authenticated y-websocket server. This is a comment verdict, not a GitHub approval event.

### Recovery and editor state

`wikiWebsocketAuth.js:20–108` disconnects on 4401 before renewing. Three attempts use 1/2/4-second delays; 401/403 and other permanent 4xx terminate immediately, while transient failures and repeated rejection of refreshed tokens exhaust the same budget. Only an authorized sync resets the budget, not a WebSocket open. A mismatched room or empty token terminates. Stop cancels a pending timer and ignores an outstanding renewal result. No token logging was found.

`wikiPageMilkdown.js:141–151,398–418,790–818` uses the supplied same-origin renewal URL, updates both provider params and page metadata, and displays a persistent failed/denied status plus instructions to copy unsaved text before reload. It does not destroy the Y.Doc, clear IndexedDB, or make the editor read-only on refusal. Continued local editing is therefore possible; saving after permission revocation still depends on server authorization. Explicit Close/discard and reload are separate existing flows, not a durable backup guarantee.

### Evidence and limits

The five construction tests and twelve recovery tests pass. An independent scratch probe used the actual locked y-websocket 2.0.4 provider, real Y.Doc objects and PR #3 server: an expired token refreshed once; edits made while disconnected survived and reached a second provider after recovery; a 403 ended renewal after one call and retained local text. Synthetic credentials and a stub renewal callback were used, not the live OSF API. The full Milkdown UI, browser messages, frontend bundle build and live-stack C4 were not executed. The prior record remains unchanged.

The chain remains subject to the API caching/CSRF improvements and optional Origin deployment configuration in the companion records. No newly demonstrated blocking defect was found.

Only private scratch files, this review record and one requested PR comment are changed. No commit, push, merge, approval, Docker state change or runtime/.env access was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**pass。** osf.io PR #6 と認証済み y-websocket サーバを併用する条件で、この head は R1-01 を解消する。GitHub の approve イベントではなくコメントによる判定。

### 復旧とエディタ状態

`wikiWebsocketAuth.js:20–108` は 4401 で切断してから更新する。試行は最大3回、待機は1・2・4秒。401/403など恒久的な4xxは直ちに終了し、一時障害と更新後の反復拒否は同じ試行枠を消費する。接続が開いただけでは回数を戻さず、認証後の同期でのみ戻す。部屋の不一致と空トークンも終了する。stopは待機を取り消し、処理中の更新結果も無視する。トークンのログ出力は見つからなかった。

`wikiPageMilkdown.js:141–151,398–418,790–818` は渡された同一サイトの更新URLを使い、provider paramsとページ情報を更新する。拒否・失敗状態を保持して表示し、再読込前に未保存テキストをコピーするよう案内する。拒否時にY.Docを破棄せず、IndexedDBを消さず、エディタを読取専用にもしないため、ローカル編集を続けられる。権限取消後の保存はサーバ側の認可に依存する。明示的なClose・破棄・再読込は別の既存経路で、永続バックアップを保証するものではない。

### 根拠と限界

構築試験5件と復旧試験12件が合格。独自scratch試験で固定版y-websocket 2.0.4、実Y.Doc、今回のサーバを使用し、期限切れから1回の更新、切断中編集の保持と第2providerへの同期、403で1回だけ更新して停止しローカルテキストを保持する動作を確認した。架空の資格情報と更新callbackを使用し、実OSF APIには接続していない。Milkdown画面全体、ブラウザの表示、frontend build、実スタックC4は未実施。前回記録は変更していない。

関連記録のAPIキャッシュ・CSRF改善と任意のOrigin設定は引き続き考慮する。新たな阻害不具合は確認しなかった。

変更対象は独自scratch、本レビュー記録、依頼されたPRコメント1件のみ。commit・push・merge・approve・Docker状態変更・runtime/.envへのアクセスは行っていない。
