# REV PR37 Image vulnerability reduction r2 / イメージ脆弱性削減レビュー r2

> **Summary:** Changes requested at 95bf10e: reproducibility is fixed, but the locked ws version has two fixable HIGH vulnerabilities.
> **概要:** 95bf10e は要修正。再現性は改善したが、固定された ws に修正可能な HIGH が2件残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a reproducible lockfile can preserve fixable vulnerabilities, and JWT rejection does not bypass the WebSocket upgrade parser. ／ 再現可能なロックでも修正可能な脆弱性を固定しうる。JWT を拒否しても WebSocket の upgrade 処理は通る。
- Applies to: PR #37, head `95bf10e71ee926aeef58c5841f15b4820db4b813`, delta `a08e364..95bf10e`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-10_RDM-developer-guide_PR37_Image_Vuln_Reduction_r1.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)
- Used by: [PR #37](https://github.com/RCOSDP/RDM-developer-guide/pull/37).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested. R2-01 / P2: upgrade ws to 6.2.4 or a reviewed later compatible version in the integration lockfile, then pin that commit here.** Keep `npm ci`; do not restore floating installation. The exact pinned lock resolves runtime `ws` to 6.2.2. The maintainer advisories identify a header-count crash fixed in 6.2.3 ([GHSA-3h5v-q93c-6h6q](https://github.com/websockets/ws/security/advisories/GHSA-3h5v-q93c-6h6q)) and fragment-memory exhaustion fixed in 6.2.4 ([GHSA-96hv-2xvq-fx4p](https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p)). Both are HIGH. The server calls `handleUpgrade` even when authorization fails, before closing 4401; authentication is therefore not evidence that the handshake parser is unreachable. Payload limits alone do not establish immunity to both advisories. No exploit was run.

The current M1 gate is report-only, so 0 CRITICAL / 2 HIGH is not itself a mandatory gate failure. Nevertheless, retaining an available same-major patch solely because its lockfile belongs to another repository is inadequate for this vulnerability-reduction change. Upgrade the integration lock, rerun both-platform builds, JWT rejection/convergence checks and scans, and update the image IDs and ADR counts. This is a review change request, not a claim that the M1 scanner must fail.

### R1 disposition

1. **R1-01: resolved on source and reported image evidence.** Manifest now pins `bf2cd67051025416de028f6edd16c83d3fc8ba79`. Read-only GitHub API inspection confirms HS256 verification, required secret/expiry/subject, document binding and duplicate-token rejection. PR evidence reports seven rejected-token cases with close 4401 and zero frames, valid two-provider convergence, and missing-secret exit 1 on both server architectures.
2. **R1-02: resolved.** The recipe copies exact `go.mod`/`go.sum`, removes `@latest` and tidy, sets `GOTOOLCHAIN=local` and `GOFLAGS=-mod=readonly`, downloads/verifies modules and bumps the tag to `9a9ddd73b225-2`. Crypto/net/sys/text are 0.58.0/0.62.0/0.50.0/0.44.0. The PR records identical binary SHA-256 from two uncached builds; reproducibility was not independently rebuilt here.
3. **R1-03: mechanical fix resolved; security follow-up R2-01 remains.** The recipe copies the lock and uses `npm ci --omit=dev`. The new 0/2 replaces the earlier unlocked 0/0 honestly, but should be removed with the available ws patch.
4. **R1-04: resolved for the documented limited cluster.** ADR-07 §6 records writers stopped, verified pre-upgrade snapshot, disposable-copy upgrade, and restoration to clean 6.3.1. The reported three documents, template and aggregation survive both paths. Distribution, plugins and X-Pack metadata are recorded. ML/security-state clusters are explicitly untested; this is not general OSS migration approval. These are author-reported isolated tests, not reviewer-repeated recovery.
5. **R1-05: accepted with a stated automation limit.** Per this review's scope, equivalent local smoke evidence is sufficient while the owner's workflow token scope is pending. PR evidence names image IDs for all three images on arm64/amd64, hardened runtime controls, ES metrics-client operations, fakecas PostgreSQL fixture/login/ticket paths, and y-websocket authentication/convergence. Clients ran on arm64, including against amd64 servers. Existing image CI succeeded but still enumerates only `image_build` and smoke-tests ES2; it does not prove the new runtime checks or y-websocket build. The proposed workflow is not applied, and its fakecas curl form is explicitly unexecuted. Preserve this limitation until the owner applies and validates automation; it is not an additional blocker for r2.

### Validation and limits

The full delta and r1 record were read. GitHub reports all nine checks successful at the reviewed head. Private integration source was inspected through read-only API calls and is not reproduced here. No Docker command, live-stack change, `runtime/.env` read, build, scan or runtime authentication test was performed by this reviewer. The PR now supplies six image IDs, scan summaries and a binary hash; raw scan/probe logs are not attached in the delta. Runtime acceptance relies on the stated author evidence.

Commands run from the reviewed checkout root; this TOON is an observation record, not canonical manifest data:

```toon
checks[4]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493 tests; 10 skipped",0
  "python3 -m unittest discover -s tools/tests","93 tests",0
  "python3 tools/docs_check.py","108 checked; 8 exempt; 24 non-failing warnings",0
  "python3 tools/manifest_check.py","0 findings; policy 608 scanned and 63 skipped",0
```

The untracked r2 file is checked separately using `docs_check.check_file`, because the normal checker enumerates tracked files. Only r2 is added locally, without staging or commit, and one Japanese PR comment is posted. No approval, merge, close or push is performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Changes requested（要修正）。R2-01 / P2: 統合リポジトリのロックで ws を6.2.4以降の互換性を確認した版へ更新し、そのコミットをここで固定する。** `npm ci` は維持する。固定ロックの実行時 `ws` は6.2.2である。開発元の勧告では、ヘッダ数によるクラッシュは6.2.3（[GHSA-3h5v-q93c-6h6q](https://github.com/websockets/ws/security/advisories/GHSA-3h5v-q93c-6h6q)）、断片によるメモリ枯渇は6.2.4（[GHSA-96hv-2xvq-fx4p](https://github.com/websockets/ws/security/advisories/GHSA-96hv-2xvq-fx4p)）で修正され、両方 HIGH である。サーバーは認可失敗時も `handleUpgrade` を呼んでから4401で閉じるため、JWT 認証だけでは handshake 処理へ到達しない証明にならない。payload 制限だけでも両勧告への安全性は証明できない。攻撃実証は行っていない。

現在の M1 は報告のみで、0 CRITICAL / 2 HIGH 自体は必須ゲート違反ではない。ただし同一メジャーに修正版があり、ロックが別リポジトリにあるという理由だけでは、この脆弱性削減変更で据え置く根拠として不十分である。統合側のロック更新、両アーキテクチャのビルド、JWT 拒否と収束、走査を再実施し、イメージ ID と ADR の件数を更新する。これはレビュー上の修正要求であり、M1 のスキャナーが失敗すべきという主張ではない。

### r1 の確認結果

1. **R1-01: ソースと報告されたイメージ証跡で解決。** manifest は `bf2cd67051025416de028f6edd16c83d3fc8ba79` を固定した。GitHub API の読取で HS256、秘密鍵・期限・主体の必須化、文書との対応、重複トークンの拒否を確認した。PR は両サーバーアーキテクチャで7種の拒否が4401・フレーム0、有効トークンの2クライアント収束、秘密鍵無しの終了1を報告している。
2. **R1-02: 解決。** 厳密な `go.mod`/`go.sum` をコピーし、`@latest` と tidy を除去した。`GOTOOLCHAIN=local`、`GOFLAGS=-mod=readonly`、モジュール取得・検証を使用し、tag は `9a9ddd73b225-2`。crypto/net/sys/text は0.58.0/0.62.0/0.50.0/0.44.0。PR にキャッシュなし2回のバイナリ SHA-256 一致がある。独立再ビルドはしていない。
3. **R1-03: ロック使用の修正は解決。安全性は R2-01 が残る。** `npm ci --omit=dev` とロックのコピーを確認した。非固定時の0/0から0/2への訂正は適切だが、利用可能な ws 修正版で解消すべきである。
4. **R1-04: 記載の限定されたクラスタについて解決。** ADR-07 §6 に書込停止、更新前 snapshot の検証、使い捨てコピーの更新、空の6.3.1への復元がある。3文書・template・集計が両経路で保たれたと報告される。配布形態、プラグイン、X-Pack メタデータを記録し、ML・security 状態を持つクラスタは未試験と明示する。一般的な OSS 移行の承認ではない。作者の隔離試験報告であり、レビュワによる再実証ではない。
5. **R1-05: 自動化の限界を明記して受容。** 今回の依頼に従い、所有者の workflow 用 token scope 待ちの間は同等のローカル smoke 証跡を受容する。PR は3イメージ×arm64/amd64の ID、堅牢化、ES metrics クライアント操作、fakecas の PostgreSQL フィクスチャと login/ticket 経路、y-websocket 認証と収束を記録している。クライアントは amd64 サーバーに対しても arm64 上で動作した。既存 image CI は成功したが、`image_build` の列挙と ES2 の smoke だけで、新規 runtime 試験や y-websocket ビルドを証明しない。提案 workflow は未適用で、fakecas の curl 形式も未実行と明記されている。所有者による適用・検証までこの限界を残す。r2 の追加阻害要因とはしない。

### 検証と限界

差分全体と r1 を読み、対象 head の GitHub check 9件の成功を確認した。非公開の統合ソースは読取 API で確認し、転載していない。レビュワは Docker 操作、稼働スタック変更、`runtime/.env` 参照、ビルド、走査、実行時認証試験をしていない。PR には6イメージの ID、走査集計、バイナリ hash が追加されたが、差分には raw scan/probe log が無く、実行時の受容は作者の証跡による。

対象 checkout ルートで実行した観測記録。正本 manifest の抄録ではない。

```toon
checks[4]{command,result,exit}:
  "PYTHONPATH=installer python3 -m unittest discover -s installer/tests","493件、10件スキップ",0
  "python3 -m unittest discover -s tools/tests","93件",0
  "python3 tools/docs_check.py","108件確認、8除外、非失敗警告24件",0
  "python3 tools/manifest_check.py","指摘0件、policy 608走査・63除外",0
```

通常の docs_check は追跡ファイルだけを列挙するため、未追跡の r2 は `docs_check.check_file` で別途検査する。ローカル追加は r2 のみで、stage・commit せず、日本語 PR コメントを1件投稿する。approve・merge・close・push は行わない。
