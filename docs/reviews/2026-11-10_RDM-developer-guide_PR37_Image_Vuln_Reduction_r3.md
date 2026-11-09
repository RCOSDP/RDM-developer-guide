# REV PR37 Image vulnerability reduction r3 / イメージ脆弱性削減レビュー r3

> **Summary:** Pass for 95bf10e..88e4268; R2-01 is resolved by pinning the reviewed ws update.
> **概要:** 95bf10e..88e4268 は合格。レビュー済み ws 更新の固定で R2-01 は解決した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** the dependency fix and the consuming manifest must name the same tested commit while preserving the browser's authentication contract. ／ 依存修正と利用側manifestは同じ試験済みコミットを指し、ブラウザの認証契約を維持する必要がある。
- Applies to: PR #37, head `88e4268b12dfdb14777840ca5c2db0c7c2880a09`, delta `95bf10e..88e4268` only; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2](2026-11-10_RDM-developer-guide_PR37_Image_Vuln_Reduction_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-04](../spec/04_acceptance_tests.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md).
- Used by: [PR #37](https://github.com/RCOSDP/RDM-developer-guide/pull/37).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Pass. R2-01 resolved; no new blocking findings in this delta.** The manifest pins `09eb0a9f4af623760a15e100790381560b9e8ce0`, whose only change from the authenticating parent is ws 6.2.6 in the lockfile. The expected image tag follows that SHA. The Docker recipe still uses `npm ci --omit=dev`. ADR-07's English and Japanese sections agree on the new SHA, reported 0/0 scan result and reason for keeping 4401 after upgrade. The r2 record is preserved.

Independent review of integration PR #4 found the same-major patch compatible with the used APIs and passed 25 authentication tests plus room-release on macOS Node v26.12.0. Invalid-token cases assert 4401 and zero document messages; valid providers converge and rejected sockets cannot write. SPEC-04 and the wiki recovery client require 4401. The [browser protocol contract](https://websockets.spec.whatwg.org/#feedback-from-the-protocol) does not expose failed HTTP handshake reasons, so moving rejection to HTTP 401 would require a coordinated contract/client change. This does not remove the unauthenticated handshake surface; the ws patch addresses the two reported advisories.

### Checks and remaining limits

Commands ran from the assigned checkout root. Observation record, not canonical manifest data:

```toon
checks[4]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493 tests; 10 skipped",0
  "python3 -m unittest discover -s tools/tests","93 tests",0
  "python3 tools/docs_check.py","109 checked; 8 exempt; 24 non-failing warnings",0
  "python3 tools/manifest_check.py","609 scanned; 63 skipped; zero findings",0
```

Both-platform image rebuilds, authentication probes and Trivy 0/0 are author-reported PR evidence, including new image IDs; this review did not repeat builds or scans. R1-05's accepted automation limitation remains: the workflow proposal is unapplied, and the fakecas curl form is unexecuted. Merge integration PR #4 before relying on its pin as integrated history; if merge changes its SHA, repin and revalidate. No other r1 findings were reopened outside the requested delta. No Docker state changes or `runtime/.env` access occurred. Only this uncommitted review record is added to the assigned checkout, checked separately with `docs_check.check_file` because it is untracked, with one Japanese PR comment and no approval, merge, close, push or commit.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Pass（合格）。R2-01解決。この差分に新たな阻害指摘なし。** manifest は `09eb0a9f4af623760a15e100790381560b9e8ce0` を固定し、認証実装済み親コミットからの変更はロックのws 6.2.6のみである。期待するイメージタグも同じSHAに追従する。Dockerレシピの `npm ci --omit=dev` は維持される。ADR-07の英和は新SHA、報告された走査0/0、upgrade後の4401を維持する理由で一致し、r2記録は保持される。

統合PR #4の独立確認で、同一メジャーパッチは使用APIと互換性があり、macOS Node v26.12.0で認証25件とroom-releaseに合格した。不正トークンのケースは4401・文書メッセージ0を検査し、正常なproviderは収束し、拒否接続は書き込めない。SPEC-04とwikiの回復クライアントは4401を必要とする。[ブラウザのプロトコル契約](https://websockets.spec.whatwg.org/#feedback-from-the-protocol)はHTTP handshake失敗の理由を公開しないため、HTTP401への変更には契約とクライアントの同時変更が必要となる。未認証handshake経路は残るが、指摘された2勧告にはwsパッチで対応している。

### 検査と残る限界

指定checkoutルートで実行した。正本manifestではなく観測記録である。

```toon
checks[4]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493件; 10件スキップ",0
  "python3 -m unittest discover -s tools/tests","93件",0
  "python3 tools/docs_check.py","109件確認; 8除外; 非失敗警告24件",0
  "python3 tools/manifest_check.py","609走査; 63除外; 指摘0件",0
```

両アーキテクチャの再ビルド、認証probe、Trivy0/0は新しいイメージIDを含む作者のPR証跡であり、レビュワによるビルド・走査再実行ではない。R1-05で受容した自動化の限界は継続し、workflow案は未適用、fakecasのcurl形式は未実行である。統合済み履歴として固定を利用する前に統合PR #4をmergeし、merge方式でSHAが変わる場合は再固定・再検証する。指定差分外のr1指摘は再審査していない。Docker状態変更や `runtime/.env` 参照は行っていない。指定checkoutへの追加は未commitのr3記録のみ。未追跡のため `docs_check.check_file` で別途検査し、日本語PRコメントを1件投稿する。approve・merge・close・push・commitは行わない。
