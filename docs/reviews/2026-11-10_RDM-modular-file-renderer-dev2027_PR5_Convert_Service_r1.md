# REV-PR5 Convert service review r1 / 変換サービスレビュー r1

> **Summary:** Changes requested for MFR PR #5 and its companion converter/sharejs recipes. A truncated response can be published as successful output, and service resource and trust boundaries need correction.
> **概要:** MFR PR #5 と関連する converter/sharejs レシピは changes requested。途中で切れた応答が正常な出力として確定され、サービスの資源制限と信頼境界にも修正が必要です。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Atomic renaming does not establish response completeness, and a conversion semaphore does not bound HTTP connections. ／ アトミックな名前変更だけでは応答の完全性は保証できず、変換のセマフォだけでは HTTP 接続数を制限できないと分かりました。
- Applies to: RCOSDP/RDM-modular-file-renderer-dev2027 PR #5; guide companion recipes at d30a054.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-03](../spec/03_security_gate.md) · [ADR-07](../decisions/ADR-07_Native_Builds_of_EOL_Middleware.md)
- Used by: PR #5 revision and companion recipe acceptance; no downstream document changed by this review.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** R1-01 is in the PR itself; R1-02 through R1-05 are in the companion guide recipes and must be resolved before deploying the pair. This is a review comment, not a GitHub approval or formal review submission.

Reviewed MFR head `95def1b47e59c37a990c8ad2764e297159ecd49b` against base `4514b1adcb66f2242e1a6cf103601fbe362ab04f`, and guide commit `d30a054248f069336b7960aea64d8927b794a5fd`. Recipe paths are relative to the guide root; exporter paths are relative to MFR. The clone and probes are in `/private/tmp/pr5-rev-a1e15b31`. Upstream livedb-mongo 0.4.1 source was read through GitHub at tag commit `2fc2764f75ff38d83d43a74eab9799e1abe8ecfd`.

### Required changes

**R1-01 — P1: Reject incomplete successful HTTP responses.** `mfr/extensions/unoconv/export.py:59–61` copies bounded reads to EOF and renames without comparing bytes received to `Content-Length`. A local HTTP server declared 100 bytes, sent `%PDF-short` (10 bytes), and closed; the actual exporter returned successfully and published those 10 bytes. This contradicts the stated protection against truncated output and can cache corrupt previews after a converter crash. Count bytes, enforce a response-size limit, reject premature EOF and protocol errors, and rename only after verified completion. Add regression coverage for short fixed-length and broken chunked responses, checking error translation and `.part` removal. `HTTPException` subclasses are not covered by the current `URLError/OSError` handler.

**R1-02 — P1: Bound connections and total request lifetime.** `installer/images/unoconv/convert_service.py:85–86,113–128,141–158,161–163` uses a thread per connection and an inactivity timeout. The two-job semaphore bounds conversions but is acquired only after headers, and holds a slot throughout upload and download. A peer sending bytes more often than the socket timeout can occupy both slots indefinitely; header-only peers can consume threads without taking any slot. The PID/memory limits eventually terminate or disable the service rather than providing admission control. Use a bounded connection/worker pool, a bounded queue, and monotonic deadlines covering headers, upload, conversion and response. Test slow senders/readers and overload recovery. MFR's `urlopen(timeout=60)` is also a socket timeout, not an overall deadline; add a bounded response and total deadline there.

**R1-03 — P2: Release slots when job-directory creation fails.** `installer/images/unoconv/convert_service.py:141–144` acquires a slot before calling `mkdtemp` outside the `try/finally`. Exhausting `/tmp` bytes or inodes leaks that slot permanently. Injecting `OSError` into `mkdtemp` twice left no available slot with the default two jobs. Put allocation inside a cleanup scope that always releases the semaphore, with an initially absent directory; return a controlled service error. Add an allocation-failure test and verify the next valid job can run. Output/profile expansion has no per-job limit, so the shared 1 GiB tmpfs makes this a reachable resource failure.

**R1-04 — P2: Authenticate MFR to the converter and narrow network access.** The POST request at `mfr/extensions/unoconv/export.py:55–58` sends no credential, and `installer/images/unoconv/convert_service.py:107–147` performs no authentication. The converter listens on all interfaces and joins the shared `grdm` network (`installer/grdm_dev/compose.py:593–595,670–671`). Any service on that network can consume the converter or submit exploit documents. An internal network is not caller authentication and does not block traffic to peer services. Authenticate before admitting/reading documents, preferably on a dedicated MFR–converter network with authenticated transport, and test missing/invalid credentials. Keep credentials out of URLs and error metadata.

**R1-05 — P2: Restore Mongo server certificate verification.** `installer/images/sharejs/vendor/mongoskin/index.js:82–84` automatically sets `tlsAllowInvalidCertificates=true` whenever the URL contains `ssl=true` or `tls=true`. TLS then does not establish the server's identity; an active internal-network attacker can impersonate Mongo and observe or modify editor data. Inheriting the old driver's behavior does not satisfy a hardened recipe. Trust a supplied CA and verify hostname/certificate, or explicitly document and obtain acceptance for a narrowly scoped development exception. Test a trusted certificate succeeds and an unrelated certificate fails. No live Mongo or TLS test was run in this review.

### Other requested checks

**URL/SSRF:** `CONVERT_URL` comes from deployment configuration, not from a document or request parameter; no direct document-controlled SSRF through that setting was found. Extension/format values are query-encoded. However, arbitrary configured destinations, default urllib redirects and proxy handling are not constrained, and URL query strings are appended naively. Validate the intended HTTP(S) origin/path, reject credentials/query/fragment as appropriate, and disable redirects/proxies or explicitly constrain them. Treat this as configuration trust hardening, not a demonstrated unauthenticated arbitrary-URL exploit.

**Filename and command injection:** The service discards incoming filenames, generates `input.<ext>`, checks the extension against an alphanumeric pattern, and allow-lists output format tokens. `Popen` receives an argument list without a shell, using an absolute generated source path. No traversal or soffice option-injection path was found. `EXT_RE` uses `$`, which permits a final newline in Python; use `fullmatch` for an exact token, although that newline does not enable traversal or argument splitting here.

**Size and timeout:** Input is limited to 128 MiB, conversion to 45 seconds, and queue wait to 10 seconds by default. The process group is killed in `finally`. The 1 GiB tmpfs and Compose memory/PID/CPU limits bound container resources, but there is no per-output limit and no total transfer deadline. R1-02/R1-03 describe the remaining availability defects.

**Cleanup and isolation:** Normal paths remove the job/profile directory; MFR removes `.part` in `finally`. The author discloses residual `/tmp/OSL_PIPE_*` sockets after timeout; these consume inodes even with zero-byte contents and need bounded cleanup or recycling. `remove_job_dir` silently gives up after retries. Separate directories do not isolate concurrent processes running under the same UID against a compromised document parser. No macro or parser exploit was executed.

**Macros and container controls:** `registrymodifications.xcu:3–7` sets `DisableMacrosExecution=true`, macro security level 3, and external-link update restrictions, and each profile receives the seed. Static controls are present; malicious-macro fixtures were not independently run. The recipe selects UID 1000, read-only root, all capabilities dropped, no-new-privileges, bounded tmpfs and tini. Compose defaults put the converter only on the internal network, preventing ordinary Internet routing, but this is not denial of all network traffic: peer services remain reachable, and a configured egress override would change the result. Do not describe this as a complete sandbox or cross-job confidentiality boundary.

**Sharejs shim correctness:** Compared every collection method used by livedb-mongo 0.4.1 with the shim. `writeSnapshot` supplies a replacement document, so `update → replaceOne` is appropriate for this caller; `writeOp` always sets `_id`, so replacement-upsert `save` fits that path. Projection versus sort handling, unique op indexes and cursor-returning query paths match the examined calls. This is not a general mongoskin replacement: modifier updates and `save` without `_id` are unsupported semantics. Connection failures retry forever without returning errors to waiting callbacks, and `close` waits for eventual connection; add bounded failure/shutdown behavior and outage tests. No evidence was found here to contradict the author's successful OT/persistence probes, but they were not repeated, and a real-driver compatibility test remains necessary. R1-05 is the concrete TLS blocker.

**Legacy and errors:** An unset URL still dispatches to the original UNO command. HTTP errors and ordinary transport/OS errors become `SubprocessError` with HTTP 400; service JSON details are discarded. Unexpected service exceptions currently terminate the request without a controlled JSON error. The legacy `TimeoutExpired` handling remains unchanged and is not claimed as a new regression.

### Validation and limits

Two independent local probes executed the actual exporter/service code with minimal dependency stubs: premature response EOF was accepted, and failed directory allocation leaked all semaphore slots. No LibreOffice, Docker, Mongo, full MFR test suite, production network or actual macro execution was used. The PR author's four tests and multi-architecture results are evidence supplied by the author, not independent results of this review. No stack state, runtime configuration or `.env` was read or changed. No commits, pushes, merges, approvals or issue closures were performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と対象

**Changes requested（要修正）。** R1-01 は PR 本体、R1-02〜R1-05 は関連する guide レシピの指摘です。組み合わせて配備する前に解決が必要です。投稿はレビューコメントであり、GitHub の承認や正式な review submission ではありません。

MFR head `95def1b47e59c37a990c8ad2764e297159ecd49b` と base `4514b1adcb66f2242e1a6cf103601fbe362ab04f`、guide commit `d30a054248f069336b7960aea64d8927b794a5fd` を確認しました。レシピのパスは guide、exporter のパスは MFR のルートを基準にしています。clone と再現コードは `/private/tmp/pr5-rev-a1e15b31` にあります。livedb-mongo 0.4.1 は GitHub のタグ commit `2fc2764f75ff38d83d43a74eab9799e1abe8ecfd` のソースを参照しました。

### 必須の修正

**R1-01 — P1: 不完全な HTTP 成功応答を拒否する。** `mfr/extensions/unoconv/export.py:59–61` は EOF まで読み、受信量と `Content-Length` を比較せず名前を変更します。ローカル HTTP サーバーが 100 bytes を宣言して `%PDF-short` の 10 bytes だけ送り切断すると、実際の exporter は成功し、その 10 bytes を出力として確定しました。変換サービスの異常終了時に壊れたプレビューを保存する可能性があり、「途中の切断で不完全な出力を残さない」という説明と矛盾します。受信量と上限を検査し、早期 EOF とプロトコル異常を拒否してから確定してください。短い固定長応答と壊れた chunked 応答について、エラー変換と `.part` 削除を試験してください。現状の `URLError/OSError` 捕捉は `HTTPException` の派生例外を扱いません。

**R1-02 — P1: 接続数と要求全体の時間を制限する。** `installer/images/unoconv/convert_service.py:85–86,113–128,141–158,161–163` は接続ごとのスレッドと無通信時間の制限を使います。2 枠のセマフォはヘッダー受信後に取得し、アップロードとダウンロード中も保持します。タイムアウトより短い間隔で送信する相手は両枠を占有し続けられ、ヘッダーだけ送る接続は枠を取らずスレッドを増やせます。PID・メモリ上限は最終的にサービスを停止・機能不全にするだけです。接続・ワーカー・待ち行列の上限と、ヘッダーから応答送信までの総時間制限を設け、低速送受信と過負荷後の復旧を試験してください。MFR の `urlopen(timeout=60)` も総時間ではなくソケットのタイムアウトなので、応答サイズと総時間を制限してください。

**R1-03 — P2: 一時ディレクトリ作成失敗時にも枠を返す。** `installer/images/unoconv/convert_service.py:141–144` は枠を取得した後、`try/finally` の外で `mkdtemp` を呼びます。`/tmp` の容量・inode 枯渇で枠が永久に失われます。`mkdtemp` に `OSError` を2回注入すると既定の2枠がすべて失われました。ディレクトリ未作成でも必ず枠を解放する構造にし、制御されたサービスエラーを返してください。作成失敗後に正常な要求が実行できる試験が必要です。出力やプロファイルの膨張にジョブ単位の上限がないため、共有 1 GiB tmpfs の枯渇は起こり得ます。

**R1-04 — P2: MFR と変換サービス間を認証し、通信範囲を狭める。** `mfr/extensions/unoconv/export.py:55–58` は資格情報を送らず、`installer/images/unoconv/convert_service.py:107–147` も認証しません。全インターフェースで待受け、共有 `grdm` ネットワークに参加します（`installer/grdm_dev/compose.py:593–595,670–671`）。同じネットワークの別サービスから資源を占有したり、攻撃文書を投入したりできます。内部ネットワークは呼出元の認証ではなく、隣接サービスへの通信も禁止しません。文書の受付・読取り前に認証し、可能なら MFR–converter 専用ネットワークと認証付き通信を使ってください。資格情報なし・不正の場合の拒否を試験し、秘密を URL やエラーメタデータに含めないでください。

**R1-05 — P2: Mongo サーバーの証明書検証を有効にする。** `installer/images/sharejs/vendor/mongoskin/index.js:82–84` は URL に `ssl=true` または `tls=true` があると自動的に `tlsAllowInvalidCertificates=true` を設定します。接続先の身元を検証しないため、内部ネットワークの能動的な攻撃者に Mongo を偽装されると、編集データの読取り・改変を許します。旧ドライバーの動作を引き継ぐだけでは堅牢化になりません。信頼する CA を渡して証明書・ホスト名を検証するか、開発専用の限定的な例外として明示的に受容してください。信頼する証明書の成功と無関係な証明書の拒否を試験してください。このレビューでは実 Mongo/TLS 試験はしていません。

### その他の確認項目

**URL と SSRF:** `CONVERT_URL` は文書や要求パラメーターではなく配備設定です。この設定を通じて文書から任意 URL を直接指定できる経路は見つかりませんでした。形式・拡張子は query エンコードされます。ただし設定先の制限、urllib の既定リダイレクト・プロキシの制限がなく、query も単純に追加します。意図した HTTP(S) 接続先・パスを検証し、資格情報・query・fragment を必要に応じて拒否し、リダイレクト・プロキシを禁止または制限してください。これは設定の信頼境界の補強であり、未認証で任意 URL を指定できると実証したものではありません。

**ファイル名とコマンド注入:** 元のファイル名は使わず `input.<ext>` を生成し、英数字の拡張子と許可された出力形式に制限します。`Popen` はシェルを介さない引数リストと、生成した絶対パスを使います。パストラバーサルや soffice オプション注入の経路は見つかりませんでした。Python の `$` は末尾改行を許すので `EXT_RE` は `fullmatch` が適切ですが、この改行でパス逸脱や引数分割は起きません。

**サイズと時間:** 既定値は入力 128 MiB、変換45秒、待ち10秒です。プロセスグループを `finally` で kill します。1 GiB tmpfs と Compose のメモリ・PID・CPU 制限はコンテナ全体を制限しますが、出力単位の上限と通信全体の期限はありません。残る可用性の問題は R1-02/R1-03 に記載しました。

**後始末と分離:** 通常はジョブ・プロファイルを削除し、MFR も `finally` で `.part` を削除します。作者が記したタイムアウト後の `/tmp/OSL_PIPE_*` 残留は 0 bytes でも inode を使うため、上限付きの掃除や再起動管理が必要です。`remove_job_dir` は再試行後の残留を通知しません。同じ UID の同時実行プロセスにとって別ディレクトリは、文書パーサーが侵害された場合の隔離にはなりません。マクロ・パーサーの攻撃は実行していません。

**マクロとコンテナ制御:** `registrymodifications.xcu:3–7` は `DisableMacrosExecution=true`、マクロセキュリティレベル3、外部リンクの更新制限を設定し、各プロファイルにコピーします。静的な設定は存在しますが、悪意あるマクロの試験は独立に実行していません。UID 1000、read-only root、全 capability 削除、no-new-privileges、上限付き tmpfs、tini を指定しています。Compose の既定値では内部ネットワークだけに参加して通常のインターネット経路を防ぎますが、隣接サービスへの通信は残り、egress の明示設定でも結果は変わります。完全なサンドボックスやジョブ間の機密性境界とは説明できません。

**Sharejs shim の正しさ:** livedb-mongo 0.4.1 が使う collection メソッドを照合しました。`writeSnapshot` は置換文書を渡すため `update → replaceOne` はその用途に合い、`writeOp` は必ず `_id` を設定するため置換 upsert の `save` もその経路に合います。projection/sort の振分け、op の unique index、cursor を返す query 経路も確認した呼出しと整合します。一般的な mongoskin の代替ではなく、modifier update や `_id` なしの `save` は同じ意味になりません。接続失敗は無限再試行され、待機 callback にエラーを返さず、`close` も接続成功を待ちます。有限の失敗・停止処理と障害試験が必要です。作者の OT 収束・永続化試験を覆す証拠は得ていませんが、再実行はしておらず、実ドライバーでの互換性試験は必要です。具体的な TLS の必須修正は R1-05 です。

**旧経路とエラー:** URL 未設定時は元の UNO コマンドを呼びます。HTTP エラーと通常の通信・OS エラーは HTTP 400 の `SubprocessError` になり、サービスの JSON 詳細は破棄されます。想定外のサービス例外は制御された JSON エラーにならず要求を終了します。旧経路の `TimeoutExpired` 処理は従来のままであり、新しい不具合とは判定していません。

### 検証と限界

最小限の依存スタブで実際の exporter/service コードを動かし、短い応答の成功扱いと、ディレクトリ作成失敗による全枠喪失を独立に再現しました。LibreOffice、Docker、Mongo、MFR 全試験、本番ネットワーク、実マクロは実行していません。PR の4試験と複数アーキテクチャの結果は作者の提示した証拠であり、このレビューの独立した結果ではありません。スタックの状態、runtime 設定、`.env` は読取りも変更もしていません。commit、push、merge、approve、issue close は行っていません。
