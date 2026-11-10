# Review: Origin allow-list / Origin 許可リスト

> **Summary:** Pass: exact matching works; installer configuration is required to enable it.
> **概要:** pass：完全一致は機能し、有効化にはinstaller設定が必要。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Recovery must preserve local state while each trust boundary is checked separately. ／ 復旧時はローカル状態を保持し、信頼境界ごとに検証する必要がある。
- Applies to: `RCOSDP/RDM-y-websocket-dev2027 PR #3`, head `61e5e35464e1c7a1bf8bb83afecf5016f37baee7`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [RDM-wiki-frontend-dev2027](2026-11-10_RDM-wiki-frontend-dev2027_PR3_JWT_Client_r2.md) · [RDM-osf.io-dev2027](2026-11-10_RDM-osf.io-dev2027_PR6_Wiki_Token_Refresh_r1.md).
- Used by / 利用先: [SPEC-04 acceptance / 受入](../spec/04_acceptance_tests.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and behavior

**Pass.** `bin/auth.cjs:37–50` splits a comma-separated setting, trims whitespace and drops empty entries. Nonempty lists use exact string matching without wildcard or substring acceptance. The allowed Origin does not bypass JWT verification. Missing Origin, an unrelated Origin, literal null and a different textual origin are rejected when enabled, with 4401 and no document frames. An explicit default port is not normalized; configure the serialized browser Origin, including scheme and any nondefault port, without a trailing slash. A non-browser caller can forge Origin, so it supplements rather than replaces token authentication.

Unset, empty, whitespace-only and comma-only settings produce an empty list and disable the check. This permissive default is documented and preserves the prior optional policy; it is not an enforced Origin boundary by default. Invalid nonempty entries simply fail to match. Rejecting syntactically nonempty-but-empty lists at startup would be a useful optional configuration safeguard.

### Deployment dependency

The requested `installer/grdm_dev/templates/y_websocket.json` contains HOST, PORT, JWT_SECRET and HOME, but no `Y_WEBSOCKET_ALLOWED_ORIGINS`. Therefore merging this PR alone does not activate Origin checks in that deployment. To enable them, the installer must supply the actual browser-facing OSF origin(s), not the websocket container address; account for HTTP/HTTPS and any external port. A configured list also rejects non-browser clients without Origin. This matches the PR's stated opt-in scope and is not a blocking regression. README also requests query-string suppression in proxy access logs; actual proxy redaction was not inspected.

### Evidence and limits

Private scratch npm ci with install scripts disabled completed. npm test passed lint/type checking, room-release and all 25 auth cases, including the four Origin additions. Independent parser probes checked empty/unset/comma-only inputs, trimming, multiple entries, missing Origin, hostile suffix, literal null and explicit-port mismatch. A real y-websocket 2.0.4 client recovered expired tokens against this server and retained offline edits; 403 renewal refusal stopped it. No live deployment, installer regeneration or browser C4 was performed.

Only private scratch files, this review record and one requested PR comment are changed. No commit, push, merge, approval, Docker state change or runtime/.env access was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と動作

**pass。** `bin/auth.cjs:37–50` はカンマ区切り設定を分割し、前後の空白と空項目を除く。非空リストは文字列の完全一致で、wildcardや部分一致はしない。Originが許可されてもJWT検証は省略しない。有効時はOriginなし・別Origin・文字列null・表記の異なるoriginを4401で拒否し、文書frameを返さない。明示的な既定portは正規化しないため、schemeと非既定portを含むブラウザのOrigin表記を末尾slashなしで設定する。ブラウザ以外はOriginを偽装できるため、トークン認証を補う機能である。

未設定・空・空白のみ・カンマのみは空リストになり検査を無効化する。この許容的な既定値は説明済みで既存の任意ポリシーを維持するが、既定でOrigin境界を強制するものではない。非空の不正値は一致せず拒否する。文字はあるが有効項目がゼロの設定を起動時に拒否する改善は任意の設定事故対策になる。

### 配備の依存関係

指定された`installer/grdm_dev/templates/y_websocket.json`にはHOST・PORT・JWT_SECRET・HOMEのみあり、`Y_WEBSOCKET_ALLOWED_ORIGINS`はない。その配備では本PRの統合だけでOrigin検査は有効にならない。有効化するにはinstallerがブラウザから見えるOSFのoriginを設定する必要があり、websocketコンテナのアドレスではない。HTTP/HTTPSと外部portを反映すること。設定後はOriginを送らない非ブラウザclientも拒否する。PRが説明する任意導入の範囲と一致し、阻害する回帰ではない。READMEはproxyアクセスログのquery string抑制も求めるが、実proxyの伏字化は未検査。

### 根拠と限界

独自scratchでinstall scriptを無効にしてnpm ciを実施。npm testはlint・型検査、room-release、Origin追加4件を含む認証25件すべて合格。独自parser試験で未設定・空・カンマのみ、空白除去、複数項目、Originなし、悪意あるsuffix、文字列null、明示port不一致を確認した。実y-websocket 2.0.4 clientは今回のサーバで期限切れから復旧し切断中編集を保持、更新403では停止した。実配備・installer再生成・ブラウザC4は実施していない。

変更対象は独自scratch、本レビュー記録、依頼されたPRコメント1件のみ。commit・push・merge・approve・Docker状態変更・runtime/.envへのアクセスは行っていない。
