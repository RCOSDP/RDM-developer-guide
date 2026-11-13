# REV PR4 ws update r1 / ws 更新レビュー r1

> **Summary:** Pass at 09eb0a9f4a: the compatible patch preserves authentication rejection and document isolation.
> **概要:** 09eb0a9f4a は合格。互換パッチで認証拒否と文書の隔離が維持される。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a browser-visible authentication close requires a completed upgrade, while document access can remain denied. ／ ブラウザに認証拒否の close を伝えるには upgrade が必要だが、文書アクセスは拒否したままにできる。
- Applies to: RDM-y-websocket-dev2027 PR #4, head `09eb0a9f4af623760a15e100790381560b9e8ce0`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: [PR #37](https://github.com/RCOSDP/RDM-developer-guide/pull/37).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and reasoning

**Pass. No blocking findings.** The only change is the ws lock entry, from 6.2.2 to 6.2.6, plus license metadata. It satisfies the existing `^6.2.1` range. The maintainer's [header advisory](https://github.com/websockets/ws/security/advisories/GHSA-3h5v-q93c-6h6q) and [fragment advisory](https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p) identify fixes in 6.2.3 and 6.2.4 respectively. The upstream 6.2.4..6.2.6 source comparison confirms stricter chunk/fragment defaults and corrected fragment accounting; [6.2.6](https://github.com/websockets/ws/releases/tag/6.2.6) resets the counter per message. No incompatible API change was found in the paths this server uses. Extreme fragmentation now has intentional limits; the tests do not establish compatibility for every possible fragmented workload.

**The author's reason for retaining post-upgrade rejection holds.** The [WebSocket standard](https://websockets.spec.whatwg.org/#feedback-from-the-protocol) hides failed opening-handshake details from browser scripts, which cannot consume HTTP 401 as an application close code. SPEC-04 C4 requires 4401; S1 additionally requires zero document frames. Read-only inspection of `wikiWebsocketAuth.js` in RDM-wiki-frontend-dev2027 at `5985d18b75da4105a610ac041b838c45f295de7d` confirms token renewal is triggered only by close 4401. HTTP rejection would bypass that recovery. The server evaluates authorization before `handleUpgrade`, but completes the upgrade before closing rejected sockets; it never calls `setupWSConnection` for them. Zero frames means zero document/data messages, not zero wire frames: the close control frame is required. This preserves the contract, not immunity of the handshake parser to unauthenticated input; patching ws remains necessary.

### Validation and limits

Commands ran in the reviewer's scratch clone `/private/tmp/rev-task-ac1bae/yws`, detached at the reviewed head, with macOS Node v26.12.0. Observation record, not canonical manifest data:

```toon
checks[4]{command,result,exit}:
  "npm ci --ignore-scripts --no-audit --no-fund","286 packages installed",0
  "node test/auth.test.cjs","25 passed; rejection 4401 and zero document frames; valid bidirectional convergence; rejected write isolation; missing-secret startup refusal",0
  "node test/room-release.test.cjs","passed",0
  "npm ls ws","ws@6.2.6",0
```

The clone remained clean. Node 24 and both image architectures are author-reported evidence, not independently rebuilt here. No Docker operations, vulnerability scan, live-stack changes, or `runtime/.env` access were performed. One Japanese PR comment is posted; no approval, merge, close, push or commit is performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と理由

**Pass（合格）。阻害指摘なし。** 変更は ws のロック6.2.2→6.2.6と license メタデータのみで、既存の `^6.2.1` に適合する。開発元の[ヘッダ勧告](https://github.com/websockets/ws/security/advisories/GHSA-3h5v-q93c-6h6q)は6.2.3、[断片勧告](https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p)は6.2.4を修正版とする。上流6.2.4..6.2.6のソース差分で chunk・fragment の既定上限引下げと断片計数の修正を確認した。[6.2.6](https://github.com/websockets/ws/releases/tag/6.2.6)ではメッセージごとにカウンタを戻す。使用経路の非互換 API 変更は見当たらない。極端な断片化には意図した上限があり、すべての断片化負荷への互換性を試験したわけではない。

**upgrade 後の拒否を残す作者の理由は妥当。** [WebSocket 標準](https://websockets.spec.whatwg.org/#feedback-from-the-protocol)は opening handshake 失敗の詳細をブラウザのスクリプトに渡さず、HTTP 401 をアプリ用 close code として受け取れない。SPEC-04 C4 は4401、S1は加えて文書フレーム0を要求する。RDM-wiki-frontend-dev2027 の `5985d18b75da4105a610ac041b838c45f295de7d` にある `wikiWebsocketAuth.js` を読取確認し、トークン更新が close 4401 のみで起動することを確認した。HTTP拒否にするとこの回復処理を通らない。サーバーは `handleUpgrade` 前に認可判定し、upgrade 後に拒否接続を閉じ、拒否時に `setupWSConnection` を呼ばない。フレーム0は文書・データメッセージ0を意味し、close制御フレームは必要である。これは契約維持の根拠であり、未認証入力がhandshake解析に届かないという意味ではなく、ws更新は必要である。

### 検証と限界

レビュー用の `/private/tmp/rev-task-ac1bae/yws` を対象headで detached checkoutし、macOS Node v26.12.0で実行した。正本manifestではなく観測記録である。

```toon
checks[4]{command,result,exit}:
  "npm ci --ignore-scripts --no-audit --no-fund","286パッケージ導入",0
  "node test/auth.test.cjs","25件合格; 4401・文書フレーム0; 正常時双方向収束; 拒否接続の書込隔離; 秘密鍵なし起動拒否",0
  "node test/room-release.test.cjs","合格",0
  "npm ls ws","ws@6.2.6",0
```

clone に変更は残らなかった。Node24と両イメージアーキテクチャは作者の報告を参照し、独立再ビルドはしていない。Docker操作、脆弱性走査、稼働スタック変更、`runtime/.env` 参照は行っていない。日本語PRコメントを1件投稿し、approve・merge・close・push・commitは行わない。
