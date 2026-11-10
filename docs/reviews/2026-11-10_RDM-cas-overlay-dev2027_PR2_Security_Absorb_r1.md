# REV RDM-cas-overlay-dev2027 PR2 security absorption r1 / セキュリティ吸収レビュー r1

> **Summary:** Independent review of PR2 at `82a3a056ce7402f7c5f61a8bcb407c464bc474ce`. Verdict: Changes required / 要修正.
> **概要:** PR2の対象head `82a3a056ce7402f7c5f61a8bcb407c464bc474ce` を独立レビューした。判定: Changes required / 要修正。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Security defaults improve, but HTTP integration and remaining token logging prevent an unconditional absorption verdict. ／ 安全な既定値への改善はあるが、HTTP統合と残存トークンログのため無条件の吸収可とは判定できない。
- Applies to / 対象: RCOSDP/RDM-cas-overlay-dev2027 PR2, exact head recorded above; review only.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md)
- Used by / 利用先: [Documentation index / 文書索引](../README.md), coordinator's absorption decision / 調整担当の吸収判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Findings

[P1, integration regression] cas-server-webapp/src/main/webapp/WEB-INF/web.xml:253 hard-codes Secure for JSESSIONID, while installer/grdm_dev/compose.py:783 configures HTTP CAS. jsession.cookie.secure is not consumed by code; changing cas.properties cannot override the descriptor. On ordinary HTTP origins the session cookie will not be returned, breaking multi-request login/webflow. Browser-specific loopback exceptions are not a deployment contract. Provide a reproducible, explicit local HTTP override or HTTPS end to end, retain secure production defaults, and exercise a complete real-CAS login. README instructions to edit source manually are insufficient for the generated installer/image path. TGC also defaults to Secure.

[P1, existing integration prerequisite] compose.py:780–791 emits none of the five cas.rateLimiting.* values required without defaults by WEB-INF/spring-configuration/loginRateLimiting.xml:27–44. propertyFileConfigurer.xml:39–41 loads one properties resource; it does not merge shipped etc defaults. If the generated file is selected, unresolved placeholders prevent context creation; the new 50/5 policy is not inherited. Supply failureRangeInSeconds, failureThreshold, usernameParameter, startDelay and repeatInterval together, and test the rendered configuration. This omission predates the PR; it blocks claiming installer compatibility rather than being a new source regression. Also resolve the actual file path: the installer mounts /code/etc/cas.properties, while the dist Dockerfile CMD selects /etc/cas/cas.properties; the dev Maven path selects the former. The current manifest uses a prebuilt image, so source changes alone do not prove deployed behavior.

[P2, incomplete log hardening] cas-server-support-osf/src/main/java/org/pac4j/oauth/client/OrcidClient.java:254 still passes the complete Scribe accessToken object to DEBUG logging immediately before using its token in the Bearer header (:258). Scribe Token.toString exposes token and secret (upstream 1.3.6 source inspected via gh, matching pac4j 1.7.1 dependencies); OrcidToken in pac4j 1.7.1 does not override toString. Runtime logging was not executed locally. Remove this raw object logging or explicitly mask getToken(), and add an ORCiD log-capture test. This is a pre-existing residual path outside the modified OAuth module, not a newly introduced leak. Other credential-object logs in ClientAction:189 and AbstractClientAuthenticationHandler:97 also need dependency-aware audit. Do not claim all plaintext token paths are eliminated.

### Correct changes and test validity

TokenIdMasker hashes the entire identifier and retains only an allow-listed type prefix and 12 hex characters; unknown prefixes and Bearer inputs do not reveal credential substrings. Response-body logging in the modified controllers is redacted. JpaTokenRegistry:62,68 still logs token objects, but these repository token classes do not override toString; that alone is not evidence of a plaintext-token leak.

TotpUtils:105–115 compares fixed-length ASCII values using MessageDigest.isEqual and non-short-circuit |= across every configured interval. It removes early match exit and keeps leading-zero codes valid. Tests include fixed-time vectors, adjacent windows and invalid ranges. String.format and JVM behavior mean this is not a proof that the entire routine has identical timing; replay prevention remains explicitly out of scope.

CookieAndRateLimitDefaultsTests checks repository strings and a numeric ratio, not servlet behavior, Spring startup with rendered properties, forwarded-header spoofing or actual throttling. TokenIdMaskerTests tests the helper, not all logging call sites. The 50/5 interval is 10 seconds after a failure, including a following correct password; IP/username scoping and trusted proxy header handling remain prerequisites.

### Evidence, limits and remaining work

Compared the exact head against e3620a25dd45173f5c16a6cd68e1b8b6c37e26c6 in a fresh scratch clone. gh pr checks reports no checks for this branch. Maven/JDK were not available for local execution; Java tests and real HTTP login were not run. Findings derive from source and installer configuration, not a claim of observed stack failure. No Docker state was changed and runtime/.env was not read.

Resolve the three findings with an explicit installer contract, rendered-config startup test, real HTTP/HTTPS login test and log-capture regression. No approval, merge, push or commit was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 指摘

[P1・統合時の回帰] cas-server-webapp/src/main/webapp/WEB-INF/web.xml:253がJSESSIONIDのSecureを固定する一方、installer/grdm_dev/compose.py:783はHTTP CASを設定する。jsession.cookie.secureを読むコードはなく、cas.propertiesでは記述子を上書きできない。通常のHTTP originではセッションCookieが戻らず、複数リクエストにまたがるログイン・webflowが壊れる。ブラウザー依存のloopback例外を運用契約にしてはいけない。再現可能で明示的なローカルHTTP上書き、または全経路HTTPSを用意し、本番の安全な既定値を保ち、実CASのログイン完了まで試験する。READMEの手動ソース編集だけでは生成インストーラー・イメージの経路を満たさない。TGCもSecureが既定になる。

[P1・既存の統合前提不足] compose.py:780–791は、WEB-INF/spring-configuration/loginRateLimiting.xml:27–44が既定値なしで要求するcas.rateLimiting.*の5値を一つも出力しない。propertyFileConfigurer.xml:39–41は単一のpropertiesを読み、同梱etcの既定値を併合しない。生成ファイルが選ばれると未解決プレースホルダーでコンテキスト作成が止まり、新しい50/5の方針も継承しない。failureRangeInSeconds、failureThreshold、usernameParameter、startDelay、repeatIntervalをまとめて供給し、生成設定を試験する。この欠落はPR以前から存在し、新規ソース回帰ではなくインストーラー適合の主張を阻害する。実際の読込み先も解決が必要で、installerは/code/etc/cas.propertiesへmountするがdist DockerfileのCMDは/etc/cas/cas.propertiesを選び、dev Mavenは前者を選ぶ。現manifestは事前ビルドイメージを使うためソース変更だけで配備動作は保証できない。

[P2・ログ対策の不足] cas-server-support-osf/src/main/java/org/pac4j/oauth/client/OrcidClient.java:254は依然ScribeのaccessTokenオブジェクト全体をDEBUGへ渡し、直後の:258でそのtokenをBearerヘッダーに使う。Scribe Token.toStringはtokenとsecretを露出する（ghでpac4j 1.7.1の依存に一致する上流1.3.6のソースを確認）。pac4j 1.7.1のOrcidTokenはtoStringを上書きしない。ログの実動作はローカル未実行。生オブジェクトのログを削除するかgetToken()を明示的にマスクし、ORCiDのログ捕捉試験を追加する。変更したOAuthモジュール外に残る既存経路で、新規に導入された漏えいではない。ClientAction:189とAbstractClientAuthenticationHandler:97の資格情報オブジェクトのログも依存実装を含めて監査する。「全経路で平文トークンを除去済み」とは言えない。

### 正しい変更とテストの妥当性

TokenIdMaskerは識別子全体をハッシュ化し、許可した種別接頭辞と16進12文字だけを残す。不明な接頭辞とBearer入力から秘密文字列を残さない。変更したcontrollerの応答本文ログは伏せられる。JpaTokenRegistry:62,68はtokenオブジェクトをログに渡すが、このリポジトリのtokenクラスはtoStringを上書きしないため、それだけで平文漏えいと判断しない。

TotpUtils:105–115は固定長ASCIIをMessageDigest.isEqualで比較し、短絡しない|=で全時間区間を処理する。一致時の早期終了をなくし、先頭ゼロのコードも有効に保つ。固定時刻のベクトル、隣接区間、範囲外入力のテストがある。String.formatやJVMの動作があるため処理全体の時間一致の証明ではなく、再利用防止は明示的に範囲外である。

CookieAndRateLimitDefaultsTestsが調べるのはリポジトリ内の文字列と比率で、servlet動作、生成propertiesによるSpring起動、転送ヘッダー偽装、実際の試行制限は調べない。TokenIdMaskerTestsも補助関数の試験であり全ログ呼出しの検査ではない。50/5は失敗後10秒の間隔を意味し、その後の正しいパスワードも対象になる。IP・ユーザー名単位の制限と信頼できるプロキシのヘッダー処理が前提となる。

### 根拠・制限・残作業

新しいscratch cloneで対象headをe3620a25dd45173f5c16a6cd68e1b8b6c37e26c6と比較した。gh pr checksはこのブランチにチェックなしと返した。ローカルにMaven/JDKがなく、Javaテストと実HTTPログインは未実行。指摘はソースとインストーラー設定に基づき、実スタックの障害を観測したという主張ではない。Docker状態を変更せずruntime/.envも読んでいない。

3指摘を明示的なインストーラー契約、生成設定での起動試験、実HTTP/HTTPSログイン試験、ログ捕捉の回帰試験で解消する。承認、マージ、push、commitは行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR / head | Proposed change / exact version reviewed. | 変更案／調べた正確な版。 |
| P1 / P2 / P3 | High / medium / low review priority. | 高／中／低の修正優先度。 |
| Secret / token | A private value used to prove identity or sign data. | 本人確認や署名に使う秘密の値。 |
| Regression | A change that breaks previously working behavior. | 以前動いた機能が変更で壊れること。 |
| CI / mock | Automated checks / a substitute used in a test. | 自動検査／試験用の代役。 |
| Secure cookie | A browser value restricted to secure transport. | 安全な通信経路に送信を限定するブラウザーの値。 |
