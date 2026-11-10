# REV-PR5 Convert service review r2 / 変換サービスレビュー r2

> **Summary:** Pass for MFR PR #5 and the reviewed companion recipes: all five r1 findings are closed within this scope. Existing installations still require credential provisioning before rollout, and osf.io's separate Mongo client remains outside the fix.
> **概要:** MFR PR #5 と確認した関連レシピは pass。r1 の5件はこの範囲で解決しました。既存環境は配備前の鍵追加が必要で、osf.io の別の Mongo クライアントは修正対象外に残ります。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Closing a component's trust-boundary defect does not establish verification for every client of the same database. ／ コンポーネントの信頼境界を修正しても、同じデータベースを使う全クライアントの検証を保証するわけではありません。
- Applies to: RCOSDP/RDM-modular-file-renderer-dev2027 PR #5 and guide companion recipes.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-10_RDM-modular-file-renderer-dev2027_PR5_Convert_Service_r1.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)
- Used by: PR #5 and companion recipe acceptance; no downstream document changed.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass.** All five required r1 changes are closed for MFR head `f78f49aa84c271f3370c6605d4c24b3d9d292788` and guide commit `0bc331fa0065fbc8541915f301263595acc8c813`. This is a reviewer comment, not a GitHub approval. MFR was cloned into `/private/tmp/pr5-rev-r2-NHqNhk/mfr`; the companion guide was read at the assigned local path. Recipe paths are relative to guide and exporter paths to MFR.

### Finding disposition

**R1-01 — Closed.** `mfr/extensions/unoconv/export.py` requires a numeric Content-Length, checks the response-size ceiling, counts received bytes, rejects premature EOF, catches HTTPException and removes `.part` in finally. Atomic replacement occurs only after completion checks. Short fixed-length, malformed chunked, missing-length and oversized responses pass the rejection tests. Chunked responses without a declared length are intentionally unsupported.

**R1-02 — Closed for the reviewed service and transfer paths.** `installer/images/unoconv/convert_service.py` replaces per-connection threads with fixed workers and a bounded pending queue. Socket shutdown timers enforce header and authenticated-request deadlines despite trickling input or a blocked output write. The conversion wait and subprocess timeout use the remaining request budget. Upload/download do not hold conversion slots. Independent tests cover header-only connections, trickled headers, slow upload, slow reader, overload rejection and recovery. MFR's socket watchdog bounds upload/response transfer; its slow-response regression passes. Precision limit: MFR starts that watchdog after `connection.connect()`, so platform DNS resolution and sequential address connection attempts are not strictly covered by one wall-clock deadline. The fixed internal converter destination makes this a nonblocking configuration/resolver follow-up, not a remaining peer-driven transfer leak. Service queue time and header time are separate bounded budgets, not part of the authenticated-request 58 seconds.

**R1-03 — Closed.** Job-directory allocation occurs before slot acquisition and inside the cleanup scope. Allocation failure returns 503 `storage_unavailable`; conversion slot acquisition has unconditional release in finally. Four injected allocation failures preserve the slots and a subsequent valid conversion succeeds. Unexpected conversion failure also releases its slot. The tests use a stub converter; physical tmpfs exhaustion reported by the author was not repeated.

**R1-04 — Closed.** Authorization uses constant-time comparison before job allocation or body reading. An independent raw-socket probe sent only headers declaring a 100000-byte body; missing and invalid bearer credentials both received 401 without sending any body. MFR sends the secret in Authorization, never the URL, and refuses HTTP conversion when it is absent. `UNOCONV_CONVERT_SECRET` is generated through the installer secret inventory and mapped to both MFR and the converter. Compose tests verify only mfr and unoconv join internal `grdm-convert`; unoconv leaves the shared grdm network. This is bearer authentication over the dedicated local network, not encrypted transport or isolation between compromised same-UID conversion jobs.

**R1-05 — Closed for sharejs.** `installer/images/sharejs/vendor/mongoskin/index.js` now requires `MONGO_TLS_CA_FILE` for the configured TLS URL, loads its public certificate as `sslCA`, and enables `sslValidate` and hostname checking. The automatic invalid-certificate allowance is removed. Mongo retains its private key in mongo_data, publishes only its certificate to mongo_tls, and sharejs mounts that volume read-only. Compose tests confirm the trust-file wiring. The PR author reports successful real-driver OT/persistence tests and rejection of unrelated certificates and wrong hostnames on both architectures; these live TLS results were reviewed as author evidence, not independently rerun.

### Remaining work and blocking status

**osf.io's pymongo `ssl_cert_reqs=CERT_NONE`: nonblocking for this PR/recipe review, but an unresolved security issue.** ADR-07 and the PR explicitly disclose this separate client in `addons/wiki/utils.py`. It was not introduced or fixed by this pair. Sharejs verification must not be represented as database-wide verification; correcting the osf.io client needs a separate change and validation. This review does not approve a production-wide TLS security claim.

**Existing runtime/.env missing `UNOCONV_CONVERT_SECRET`: not a code-review blocker; a deployment prerequisite.** `compose.py` rejects rendering with missing required secrets rather than silently deploying unauthenticated conversion. Provision a matching secret for MFR/converter before rollout and follow the established integration/image switch order. The renderer's suggested `secrets init --force` or rotation can affect other secrets, so the operator must plan that migration deliberately; this review did not execute it. No runtime/.env was read or modified.

### Independent validation and limits

The command `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=installer python3 -m unittest installer.tests.test_convert_service installer.tests.test_compose installer.tests.test_secrets -q`, run from the assigned guide checkout, passed 76 tests. The unchanged PR exporter test file passed 16 tests in a scratch virtual environment with minimal BaseExporter, settings and SubprocessError stubs; actual exporter/network code ran, but full MFR dependency integration was not tested. The separate raw-socket authentication probe passed. Harnesses are in `/private/tmp/pr5-rev-r2-NHqNhk`.

No Docker commands, live LibreOffice/Mongo tests, stack changes, runtime configuration access, commits, pushes, merges, approvals or closures were performed. One Japanese PR comment records this verdict. The review record is uncommitted.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と対象

**Pass（合格）。** MFR head `f78f49aa84c271f3370c6605d4c24b3d9d292788` と guide commit `0bc331fa0065fbc8541915f301263595acc8c813` について、r1 の必須修正5件は解決しました。これはレビューコメントであり、GitHub の承認ではありません。MFR は `/private/tmp/pr5-rev-r2-NHqNhk/mfr` に clone し、関連 guide は指定されたローカルパスで読みました。レシピのパスは guide、exporter のパスは MFR を基準にしています。

### 各指摘の判定

**R1-01 — 解決。** `mfr/extensions/unoconv/export.py` は数値の Content-Length を必須にし、応答サイズ上限・受信量を検査して早期 EOF を拒否します。HTTPException を捕捉し、finally で `.part` を削除します。完全性検査後だけ出力を確定します。短い固定長、不正 chunked、長さなし、上限超過の拒否試験が通りました。長さを宣言しない chunked 応答は意図的に非対応です。

**R1-02 — 確認したサービスと通信経路では解決。** `installer/images/unoconv/convert_service.py` は固定ワーカーと有限待ち行列を使います。ソケットを shutdown するタイマーにより、細切れ入力や送信の停止でもヘッダー期限と認証後の要求期限を強制します。変換待ちと子プロセスの時間制限は要求の残り時間以内です。アップロード・ダウンロード中は変換枠を保持しません。ヘッダーだけの接続、細切れヘッダー、低速アップロード、低速読取り、過負荷拒否と復旧を独立に試験しました。MFR の watchdog は送受信を制限し、低速応答の回帰試験も通りました。ただし watchdog の開始は `connection.connect()` の後なので、OS の名前解決と複数アドレスへの順次接続を単一の総期限では制限していません。固定の内部接続先を使う範囲では非阻害の設定・resolver 側の追跡課題とし、通信相手による転送枠の無期限占有が残ったとは判定しません。サービスの待ち行列・ヘッダーには別の有限予算があり、認証後58秒には含まれません。

**R1-03 — 解決。** ジョブディレクトリは枠取得前かつ cleanup 範囲内で作成します。作成失敗は503 `storage_unavailable` になり、変換枠は finally で必ず返します。作成失敗を4回注入しても枠数は維持され、その後の正常変換が成功しました。想定外の変換失敗でも枠が返りました。試験の変換器はスタブであり、作者が報告した実 tmpfs 枯渇は再実行していません。

**R1-04 — 解決。** ディレクトリ作成・本文読取り前に定数時間比較で認証します。独立した生ソケット試験では100000 bytes の本文を宣言するヘッダーだけを送り、資格情報なし・不正の両方で本文送信前に401を受けました。MFR は秘密を URL ではなく Authorization に送り、秘密がなければ HTTP 変換を拒否します。installer の鍵一覧に `UNOCONV_CONVERT_SECRET` があり、MFR と変換側の双方へ対応付けます。Compose 試験で内部 `grdm-convert` の参加者が mfr と unoconv だけで、unoconv が共有 grdm から離れることを確認しました。専用ローカルネットワーク上の bearer 認証であり、暗号化通信や、侵害された同一 UID の変換ジョブ間の隔離を保証しません。

**R1-05 — sharejs について解決。** `installer/images/sharejs/vendor/mongoskin/index.js` は設定された TLS URL に `MONGO_TLS_CA_FILE` を必須とし、公開証明書を `sslCA` に読み、`sslValidate` とホスト名検証を有効にします。不正証明書の自動許可は削除されました。Mongo の秘密鍵は mongo_data に残り、公開証明書だけを mongo_tls に出し、sharejs は読み取り専用でマウントします。Compose 試験で配線を確認しました。作者は両アーキテクチャで実ドライバーの OT・永続化成功と、無関係な証明書・異なるホスト名の拒否を報告しています。この実 TLS 結果は作者の証拠として確認したもので、独立に再実行していません。

### 残作業と阻害の有無

**osf.io の pymongo `ssl_cert_reqs=CERT_NONE`: 今回の PR・レシピ審査は阻害しませんが、未解決のセキュリティ課題です。** ADR-07 と PR は `addons/wiki/utils.py` の別クライアントとして明記しています。今回導入した問題でも今回修正した問題でもありません。sharejs の検証をデータベース全利用者の検証として説明してはいけません。osf.io 側は別途修正と検証が必要で、本レビューは本番全体の TLS 安全性を承認しません。

**既存 runtime/.env の `UNOCONV_CONVERT_SECRET` 欠落: コードレビューの阻害ではなく、配備前の必須作業です。** `compose.py` は必須鍵がないと render を拒否し、未認証の変換へ暗黙に切り替えません。配備前に MFR・converter に一致する鍵を用意し、既定の integration・イメージ切替順序を守る必要があります。render が案内する `secrets init --force` や rotation は他の鍵に影響し得るため、運用者が移行を計画してください。本レビューでは実行せず、runtime/.env の読取りも変更もしていません。

### 独立した検証と限界

指定 guide checkout で `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=installer python3 -m unittest installer.tests.test_convert_service installer.tests.test_compose installer.tests.test_secrets -q` を実行し、76件が成功しました。scratch の仮想環境で PR の exporter 試験ファイルを変更せず実行し、16件が成功しました。BaseExporter・settings・SubprocessError は最小スタブで、実際の exporter・通信コードを動かしましたが、MFR 全依存との統合試験ではありません。別途、生ソケットの認証試験も成功しました。検証コードは `/private/tmp/pr5-rev-r2-NHqNhk` にあります。

Docker コマンド、実 LibreOffice・Mongo 試験、スタック変更、runtime 設定へのアクセス、commit、push、merge、approve、close は行っていません。この判定を日本語の PR コメント1件で記録します。レビュー記録は未コミットです。
