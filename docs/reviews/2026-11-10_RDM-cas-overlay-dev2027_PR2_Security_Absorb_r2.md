# REV RDM-cas-overlay-dev2027 PR2 security absorption r2 / セキュリティ吸収レビュー r2

> **Summary:** Changes requested: the three r1 fixes are sound at source level, but another local OAuth path logs usable tokens and authorization codes. The unexplained real-CAS 503 is a tracked deployment prerequisite, not independently a source-absorption blocker.
> **概要:** 要修正。r1の3修正はソース上妥当だが、別のローカルOAuth経路が利用可能なトークンと認可コードをログに残す。原因不明の実CAS 503は配備前に追跡すべき課題で、それだけでソース吸収を止めるものではない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Masking token objects does not cover secrets embedded in redirect URLs; source absorption and deployment acceptance need separate verdicts. ／ トークンオブジェクトのマスクだけではリダイレクトURL内の秘密を保護できず、ソース吸収と配備受入れの判定を分ける必要がある。
- Applies to / 対象: RCOSDP/RDM-cas-overlay-dev2027 PR2, head `cb89a187dcf14a02d05eca63286e7e95b2c1ae72`, base `e3620a25dd45173f5c16a6cd68e1b8b6c37e26c6`.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-10_RDM-cas-overlay-dev2027_PR2_Security_Absorb_r1.md)
- Used by / 利用先: [Documentation index / 文書索引](../README.md), coordinator's absorption decision / 調整担当の吸収判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and remaining finding

**Changes requested. [P2] Remove raw OAuth callback URL logging.** In `cas-server-support-oauth/src/main/java/org/jasig/cas/support/oauth/web/OAuth20AuthorizeCallbackActionController.java:149–155`, the token response appends `accessToken.getId()` to the URL fragment and logs the entire URL. Lines 163–167 likewise log the authorization code in the query. `OAuth20WrapperController.java:144` routes to this controller. DEBUG logging therefore still exposes usable bearer tokens and authorization codes despite masking their creation in `CentralOAuthServiceImpl`. This is a pre-existing local application path, not a new regression or an unmodified dependency. It falls within the requested other-token-path audit and the token-log hardening scope. Root WARN suppresses it by default, but enabling DEBUG reintroduces the leak. Remove these URL log statements or log non-secret metadata, and add log-capture regression tests for both response types while preserving redirect behavior. Do not hash an entire URL as a substitute for reviewing which fields may be logged.

### r1 fixes verified

JSESSIONID: `SessionCookieSecurityListener.java:56–79` sets Secure unless the trimmed, case-insensitive value is exactly false. Missing keys, unrecognized values and caught file-read failures keep Secure enabled. `web.xml:90–94` registers the listener before Spring initialization and retains both Secure and HttpOnly in the cookie descriptor. The resource selector matches the `cas.properties.filepath` selector and default in `propertyFileConfigurer.xml`. Seven mock-context tests cover false, case/whitespace, true, absent key, invalid value, unreadable file and missing default resource. This resolves the hard-coded-cookie finding at source level; mock tests do not prove actual response headers or login continuity. Both TGC and JSESSIONID require explicit false for local HTTP.

Rate limiting: `loginRateLimiting.xml:27–29,43–44` supplies all five defaults: range 50 seconds, threshold 5, username parameter username, start delay 1000 ms and repeat interval 5000 ms. Omitted keys no longer create unresolved placeholders for these five properties. The failure interval remains 10 seconds, not five permitted attempts per 50 seconds. The new test checks source strings and the ratio; it is not a Spring startup or behavioral throttling test. Explicit weaker configuration still overrides defaults. The generated installer configuration remains insufficient for real CAS, as the PR body now discloses.

ORCiD: `OrcidClient.java:256–260` logs only `TokenIdMasker.mask(accessToken.getToken())`, never the Scribe object or secret. Its new capture test invokes the real method with a mocked network request, checks that token and secret are absent, requires the masked line, and verifies the unchanged Bearer header. Removing the credentials object log in `AbstractClientAuthenticationHandler` and replacing it with a client name in `ClientAction` closes the two r1 credential sites. Other modified OAuth token/code/ticket call sites use the masker and response-body redaction. Registry token-object logging alone is not evidence of leakage because the local token classes do not override toString. Remaining client/profile objects, ORCiD response bodies, exception text and dependency logs are not certified secret-free; the callback finding is directly demonstrated by local data flow without depending on their behavior.

### 503, integration follow-up and evidence limits

The author reports that complete properties removed unresolved placeholders but real CAS still returned 503 during context initialization; the cause is unknown. Real HTTP/HTTPS login and Set-Cookie checks were not run. Do not classify the 503 as harmless or attribute it to this PR without evidence. It does **not independently block source absorption**: the installer routes authentication to fakecas and the manifest pins a prebuilt CAS image, so this source merge neither switches the login provider nor deploys the fixes. This is also why current stack health cannot validate these fixes.

Track a real-CAS deployment follow-up before removing the prebuilt image or switching authentication: capture and resolve the first startup exception, compare base/head under the same complete configuration if needed, verify actual property mounts for dev and dist, then exercise complete HTTP development and HTTPS secure-default login, JSESSIONID/TGC Set-Cookie attributes and session continuity, and real throttling. Record image provenance and prove that the reviewed code is deployed. The PR body and this record track the gap; no separate issue was created under the one-comment authorization. The P2 callback leak, rather than the 503 alone, determines this review's changes-requested verdict. The owner's informed decision to absorb the proposal-only source PRs is accepted and is not a finding.

Reviewed a fresh scratch clone at the exact head, compared r1 and base, inspected listener wiring, tests, log data flows, installer routing and manifest. `git diff --check` passed; `gh pr checks` reports no checks. Local Maven is absent and Java reports no installed runtime, so no Java tests or CAS runtime checks were executed independently. The PR author reports OAuth 106 and OSF 32 passing tests and a successful WAR build; those are author evidence, not this reviewer's execution. No Docker operations, runtime/.env access, approval, merge, close, push or commit occurred. Only this uncommitted record and one PR review comment are produced.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と残存指摘

**要修正（changes requested）。[P2] OAuthのコールバックURLの生ログを除去する。** `cas-server-support-oauth/src/main/java/org/jasig/cas/support/oauth/web/OAuth20AuthorizeCallbackActionController.java:149–155`はtoken応答のURLフラグメントに`accessToken.getId()`を追加し、URL全体をログに出す。163–167行もクエリ内の認可コードをログに出す。`OAuth20WrapperController.java:144`からこのcontrollerへ到達する。`CentralOAuthServiceImpl`で生成時のログをマスクしても、DEBUGでは利用可能なBearerトークンと認可コードが残る。新規回帰でも未変更の依存ライブラリでもなく、既存のローカル実装経路である。依頼された他トークン経路の監査とログ保護の範囲に該当する。既定のRoot WARNでは出ないが、DEBUGを有効にすると漏れる。URLのログを削除するか秘密を含まない情報だけにし、両応答形式のログ捕捉回帰試験とリダイレクト維持を確認する。URL全体のハッシュ化だけで、ログ項目の精査を代替しない。

### r1修正の確認

JSESSIONID: `SessionCookieSecurityListener.java:56–79`は空白を除いた大文字小文字を問わないfalseだけでSecureを外す。キー欠落、不明な値、捕捉されたファイル読取り失敗ではSecureを維持する。`web.xml:90–94`はSpring初期化前にlistenerを登録し、CookieのSecureとHttpOnlyも維持する。読込み先と既定値は`propertyFileConfigurer.xml`の`cas.properties.filepath`に一致する。7件のmock試験はfalse、大文字・空白、true、キー欠落、不正値、読めないファイル、既定resource欠落を扱う。固定設定の指摘はソース上解消したが、mockでは実応答ヘッダーやログイン継続を証明できない。開発用HTTPにはTGCとJSESSIONID双方で明示的なfalseが必要である。

試行制限: `loginRateLimiting.xml:27–29,43–44`に5値すべての既定値がある。範囲50秒、閾値5、ユーザー名パラメーターusername、開始遅延1000ms、反復間隔5000msである。省略時、この5キーが未解決placeholderにはならない。失敗後の間隔は10秒であり、50秒に5回を許可する意味ではない。新試験はソース文字列と比率を調べ、Spring起動や実際の制限動作は調べない。明示した弱い設定は引き続き既定値を上書きできる。生成インストーラー設定だけでは実CASを起動できない点はPR本文で開示されている。

ORCiD: `OrcidClient.java:256–260`は`TokenIdMasker.mask(accessToken.getToken())`だけをログに渡し、Scribeオブジェクトやsecretを渡さない。追加試験は通信をmockにした実メソッドを呼び、tokenとsecretがログにないこと、マスク行の存在、Bearerヘッダーの維持を確認する。`AbstractClientAuthenticationHandler`の資格情報ログ削除と`ClientAction`のクライアント名への置換でr1の2経路も解消した。他の変更済みOAuthトークン・コード・チケットのログはマスクされ、応答本文は伏せられている。registryのtokenオブジェクトはローカルクラスがtoStringを上書きしていないため、それだけで漏えいとはしない。残るclient/profileオブジェクト、ORCiD応答本文、例外文字列、依存内部ログまで秘密がないと認定してはいない。今回のコールバック指摘は、それらに依存せずローカルの値の流れだけで確認できる。

### 503、統合の追跡事項、根拠の制限

著者報告では、必要propertiesを揃えると未解決placeholderはなくなったが、コンテキスト初期化で実CASが503になり、原因は不明である。実HTTP/HTTPSログインとSet-Cookieは未確認である。証拠なく無害ともPR起因とも判断しない。ただし**503だけではソース吸収の阻害要因としない**。インストーラーは認証をfakecasへ向け、manifestは事前ビルドCASイメージを固定しているため、このソースのマージだけでは認証先も稼働コードも切り替わらない。同じ理由で、現在のスタックの正常動作も今回の修正の検証にはならない。

事前ビルドイメージ廃止または認証先切替前の追跡事項として、最初の起動例外の採取と解決、必要なら同一完全設定によるbase/head比較、dev/distの実mountと読込み先確認、開発HTTPと安全な既定値のHTTPSでのログイン完了、JSESSIONID/TGCのSet-Cookie属性とセッション継続、実際の試行制限を実施する。使用イメージの由来とレビュー済みコードの配備も確認する。PR本文とこの記録に未完了事項を残し、コメント1件という許可範囲のため別Issueは作成していない。今回の要修正判定の理由は503単独ではなくP2のコールバック漏えいである。所有者が提案・マージ不可という題名を承知して吸収を決定した点は受け入れ、指摘にしない。

専用scratch cloneの正確なheadでr1/baseとの差分、listener登録、試験、ログの値の流れ、インストーラーの認証経路とmanifestを確認した。`git diff --check`は成功し、`gh pr checks`はチェックなしだった。ローカルMavenはなく、Javaもruntime未導入と返したため、Java試験とCAS実動作は独立実行していない。OAuth 106件・OSF 32件成功とWARビルド成功は著者報告であり、レビュワの実行結果ではない。Docker操作、runtime/.env参照、approve、merge、close、push、commitは行っていない。未コミットのこの記録とPRコメント1件のみを作成する。
