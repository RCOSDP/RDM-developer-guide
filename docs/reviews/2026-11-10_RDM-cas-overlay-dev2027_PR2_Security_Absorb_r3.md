# CAS PR2 Security absorption review r3 / CASセキュリティ吸収レビュー r3

> **Summary:** Pass for source absorption: callback and profile ticket logs are masked; real-CAS deployment remains a tracked prerequisite.
> **概要:** ソース吸収は合格。コールバックとprofileのticketログ対策を確認し、実CAS配備は追跡する前提条件として残す。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** Removing generated callback URLs from logs closes the demonstrated leak without changing redirects. ／ 生成したコールバックURLをログから除くと、転送を変えずに実証済み漏えいを解消できる。
- Applies to: RDM-cas-overlay-dev2027 PR #2, head `0b89ae8a898112230ce7c81b1665f0e4c7d997bd`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r2](2026-11-10_RDM-cas-overlay-dev2027_PR2_Security_Absorb_r2.md).
- Used by: the coordinator's source-absorption decision and follow-up verification. ／ 調整担当のソース吸収判断と後続検証。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and closure

**Pass for source absorption.** Reviewed the fresh scratch clone, r2, the final commit and the OAuth/OSF module log call sites, including multiline arguments. No remaining directly demonstrated raw OAuth token/code/ticket logging was found in the audited local paths. This verdict does not certify all dependencies or deployment behavior.

`OAuth20AuthorizeCallbackActionController.java:153–171` now logs `redirectUri`, not the callback URL containing the generated access token fragment or authorization-code query. Both redirect return values still use the unchanged callback URL. Line 114 masks `loginTicketId`. `OAuth20ProfileController.java:162–166` masks both the service ticket and access token in its ERROR branch; earlier inbound Bearer/token logs also use `TokenIdMasker`. The masker retains only known type prefixes and a truncated SHA-256 fingerprint, with no clear-ID fallback. The r2 callback finding is closed.

The three new `OAuth20TokenLoggingTests` execute token/code callbacks and profile validation failure with captured DEBUG/ERROR output, reject four secret sentinel IDs, and require useful log output. Callback tests also assert that redirects still contain their required token/code. These are meaningful regressions, not just source-string assertions. Their test setup uses mocks and does not prove a live login.

The other local OAuth grant, refresh, revoke, metadata and callback identifier logs use masking; sensitive response-body logs are redacted. The r1 ORCiD request-token masking and removal of direct credential-object logging remain intact. `JpaTokenRegistry` logs token objects, but the local token classes have no `toString` override exposing their IDs, so this alone is not a demonstrated token leak. Remaining `userProfile`, SAML attribute/credential objects, state, registered redirect URI, ORCiD response bodies and exception/dependency logs are not certified secret-free. No new concrete usable-token path was established there; broader logging/privacy hardening remains outside this closure.

### Evidence and deployment prerequisite

`git diff --check` passed. Maven is absent and `java -version` exits 1 with no installed runtime, so this reviewer did not independently execute Java tests or a WAR build. The PR body reports OAuth 109 and OSF 32 tests passing and mutation checks that fail when these log protections are reverted; those remain author evidence. The independent evidence is source/data-flow review and test inspection.

Real CAS still returning 503 is a **tracked prerequisite before deploying this source or switching authentication**, not an additional source-absorption blocker. Resolve the first startup exception, verify complete configuration and dev/dist mounts, prove image provenance, and exercise real HTTP/HTTPS login, JSESSIONID/TGC Secure/HttpOnly behavior, session continuity and throttling. The prebuilt image/fakecas arrangement cannot prove these source changes are running. The PR body and r2/r3 records track this gap; no separate issue was created under the one-comment authorization.

No Docker command, grdm-dev stack change, runtime credential-file read, commit, push, approval, merge or closure occurred. The record remains uncommitted; one Japanese PR comment carries this verdict.

GitHub reports no checks (gh pr checks exit 1); this is absence of CI evidence, not a failed test.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と解決状況

**ソース吸収は合格（pass）。** 専用scratch clone、r2、最終コミット、OAuth/OSF両モジュールの複数行を含むログ引数を確認した。監査したローカル経路では、OAuth token/code/ticketの生ログが残ると直接実証できる箇所は見つからなかった。依存ライブラリ全体や配備動作を認定する判定ではない。

`OAuth20AuthorizeCallbackActionController.java:153–171` は、生成したaccess tokenのfragmentや認可codeのqueryを含むcallback URLではなく `redirectUri` を記録する。戻り値の転送先は従来のcallback URLのまま。114行の `loginTicketId` もマスクする。`OAuth20ProfileController.java:162–166` はERROR分岐のservice ticketとaccess token双方をマスクし、入口のBearer/tokenログも `TokenIdMasker` を使う。マスクは既知の型接頭辞と短縮SHA-256指紋だけを残し、生IDへのfallbackはない。r2のコールバック指摘は解決した。

新規 `OAuth20TokenLoggingTests` 3件はtoken/code callbackとprofile検証失敗を実行し、DEBUG/ERRORを捕捉して4種の秘密IDがないことと有用なログの存在を検査する。callback試験は転送先に必要なtoken/codeが残ることも確認する。単なるソース文字列検査ではない有効な回帰試験である。ただしmockによる試験であり実ログインの証明ではない。

他のローカルOAuth発行・更新・失効・metadata・callbackのIDログはマスクし、秘密を含む応答本文ログは伏せている。r1のORCiD要求tokenのマスクと直接の資格情報オブジェクトログの除去も維持している。`JpaTokenRegistry` はtokenオブジェクトを記録するが、ローカルtokenクラスにIDを露出する `toString` 上書きはなく、それだけで漏えいとはしない。残る `userProfile`、SAML属性/資格情報オブジェクト、state、登録redirect URI、ORCiD応答本文、例外/依存内部のログが秘密を含まないとは認定しない。そこから新たな利用可能tokenの具体的経路は実証しておらず、広範なログ/プライバシー強化は今回の解決確認の範囲外である。

### 根拠と配備前提条件

`git diff --check` は成功。Mavenはなく、`java -version` はruntime未導入で1終了したため、レビュワはJava試験とWARビルドを独立実行していない。PR本文はOAuth109件・OSF32件合格と、保護を戻すと失敗するmutation検査を報告しているが、これらは著者の証跡である。独立した根拠はソースと値の流れのレビュー、試験内容の確認である。

実CASの503は、**今回のソース配備または認証切替の前に追跡する前提条件**であり、追加のソース吸収阻害要因にはしない。最初の起動例外を解消し、完全な設定とdev/distのmount、イメージ由来を確認し、実HTTP/HTTPSログイン、JSESSIONID/TGCのSecure/HttpOnly、セッション継続、試行制限を検証すること。prebuiltイメージ/fakecas構成の正常動作は今回のソースが稼働している証拠にはならない。PR本文とr2/r3で追跡し、コメント1件という許可範囲のため別Issueは作っていない。

Dockerコマンド、grdm-devスタック変更、runtime資格情報ファイル参照、commit、push、approve、merge、closeは行っていない。記録は未コミットのまま残し、日本語PRコメント1件で判定を伝える。

GitHubはチェックなし（gh pr checks終了1）と報告した。試験失敗ではなくCI証跡がないという意味である。
