# REV PR3 Real startup review r3 / 実起動レビュー r3

> **Summary:** Pass for the R2-01 remediation at b02e0b90f0. Shipped institution-login defaults are removed and mandatory runtime keys are validated without including their values in new errors.
> **概要:** b02e0b90f0 の R2-01 修正は pass。機関ログインの配布既定鍵が除去され、実行時の必須鍵を検査し、新しいエラーには値を含めません。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** removing defaults needs mandatory references and blank-value validation; source review and reported artifact checks provide different evidence. ／ 既定値除去には必須参照と空値検査も必要であり、ソース確認と報告された成果物検査は異なる証拠です。
- Applies to: RCOSDP/RDM-cas-overlay-dev2027 PR #3; delta `96de2b60f6d2a3568cb47fe37a325b631f286d36..b02e0b90f00def52fa5c47e479cc60d1085bff02`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r2](2026-11-10_RDM-cas-overlay-dev2027_PR3_Real_Startup_r2.md).
- Used by: PR #3 revision and [review integration](README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Pass — R2-01 addressed; no new blocking finding in this delta.** This is a scoped review verdict, not GitHub approval or authorization to deploy. R1-01 remains resolved as recorded in r2.

### Independent source evidence

`etc/cas.properties:104–107` now documents runtime environment injection without either JWE/JWT assignment. `cas-servlet.xml:359–360` retains mandatory placeholders without fallback. Its non-lazy action bean receives both values through setters; `propertyFileConfigurer.xml:41` does not ignore unresolved placeholders. Missing values therefore prevent normal context initialization rather than silently choosing a shared key.

`OpenScienceFrameworkPrincipalFromRequestRemoteUserNonInteractiveCredentialsAction.java:863–901` rejects null, empty, and whitespace-only values, requires exactly 32 bytes for JWE and at least 32 bytes for JWT, and assigns only after validation. The length calculation uses the same `getBytes()` conversion as the signer and encrypter at lines 722 and 729. New exception messages contain only property names and requirements; there is no new secret logging or generated fallback. Explicit UTF-8 would improve cross-host portability for non-ASCII keys, but this is not a blocker for removal of usable defaults.

`InstitutionAuthSecretValidationTests` covers the 31/32/33-byte boundaries, null/empty/blank rejection, and value-free errors. `CookieAndRateLimitDefaultsTests.shippedConfigurationCarriesNoInstitutionLoginSecrets` checks absence of both properties. These tests were inspected, not executed independently.

An independent tracked-file search found the old JWE/JWT literals only in `src/test/java/io/cos/cas/mock/MockOsfRemoteAuthenticateAction.java`. The distribution stages copy configuration and the production WAR, not the source tree or test JAR. Maven separates test resources; the webapp uses the normal OSF JAR. `.dockerignore` excludes Git history. The build-stage source tree, caches, and the `dev` target are outside the claim that final `dist` layers lack old test literals. No build-time secret arguments or environment defaults were added. `git diff --check` passed and the isolated clone remained clean.

### Author-reported runtime and artifact evidence

The PR body reports arm64 exit 254 for either missing key, empty keys, JWE lengths 31/33, and JWT length 31. With keys provided only through environment variables, startup, password login, ST validation, wrong-password rejection, and throttling succeeded; supplied values were absent from logs. The 31-byte rejection versus 32-byte startup supports the environment-to-setter wiring. Password login is not an institution-login end-to-end test.

The author reports successful oauth 109 / osf 41 tests and mutation failures for the three relevant regression tests. For both architecture images, all ten layers each, nested WAR/JAR contents, and configuration blobs were scanned: old JWE/JWT and TGC literals, assignment patterns, and four supplied keys had zero matches; a non-secret control matched twice. The reported local OCI index is `sha256:5a1799d930b77a339f62cdd0a5aff9e6a1dfea07d91444e12c7e9653d7a53a7d`. These results support closure together with the source changes, but were not independently reproduced or verified against image bytes by this reviewer.

### Limits and follow-up

No Docker operations, Maven/Java test runs, live startup, or image inspection were performed in this round. No grdm-dev state or runtime/.env was touched. The only GitHub write is one PR comment; there was no commit, push, merge, approval, or close. This record is uncommitted.

OSF receiver defaults remain outside this CAS delta: configure matching deployment-specific keys on both sides and never reuse historical examples. Actual institution login, real GRDM schema validation, TOTP, ORCiD, the dev target, and post-change amd64 startup remain unverified as previously recorded. TGC key-quality hardening remains a follow-up. The verdict does not broaden these claims or certify all possible logging configurations.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Pass — R2-01 は対応済み。この差分に新しい阻害事項はありません。** 範囲を限定したレビュー判定であり、GitHub の approve や配備の許可ではありません。R1-01 は r2 の記録どおり解決済みです。

### 独立したソース確認

`etc/cas.properties:104–107` は JWE/JWT の代入を除去し、実行時の環境変数注入を説明しています。`cas-servlet.xml:359–360` は代替値なしの必須参照を維持します。遅延生成でない action bean の setter に両値が渡され、`propertyFileConfigurer.xml:41` は未解決参照を無視しません。したがって未設定なら共通鍵を選ばず、コンテキストの正常初期化を拒否します。

`OpenScienceFrameworkPrincipalFromRequestRemoteUserNonInteractiveCredentialsAction.java:863–901` は null・空文字・空白のみを拒否し、JWE は正確に 32 バイト、JWT は 32 バイト以上を要求して検査後に代入します。長さ計算は 722・729 行の署名・暗号処理と同じ `getBytes()` を使います。新しい例外はプロパティ名と要件だけを含み、秘密のログ出力や自動生成の代替鍵は追加されていません。UTF-8 の明示は非 ASCII 鍵の環境間互換性を改善しますが、使用可能な既定値除去の blocker ではありません。

`InstitutionAuthSecretValidationTests` は 31／32／33 バイト境界、null・空文字・空白の拒否、エラーへの値の非出力を検査します。`CookieAndRateLimitDefaultsTests.shippedConfigurationCarriesNoInstitutionLoginSecrets` は両プロパティの不在を検査します。試験コードを確認しましたが、独立には実行していません。

追跡ファイルの独立検索では、旧 JWE/JWT 文字列は `src/test/java/io/cos/cas/mock/MockOsfRemoteAuthenticateAction.java` だけに残ります。配布ステージは設定と本番 WAR をコピーし、ソースツリーや試験 JAR はコピーしません。Maven は試験リソースを分離し、webapp は通常の OSF JAR を使います。`.dockerignore` は Git 履歴を除外します。ビルドステージのソース、キャッシュ、`dev` ターゲットは「最終 dist 層に旧試験値がない」という主張の対象外です。ビルド時の秘密引数や環境既定値は追加されていません。`git diff --check` は成功し、専用 clone に変更はありません。

### 作者報告の実行時・成果物の証拠

PR 本文は arm64 で、どちらかの鍵の未設定、空文字、JWE の 31／33 バイト、JWT の 31 バイトを exit 254 と報告しています。環境変数だけで鍵を与えた場合は起動、パスワードログイン、ST 検証、誤パスワード拒否、制限が成功し、指定値のログ出力はありませんでした。31 バイトで拒否、32 バイトで起動という結果は環境変数から setter への配線を裏付けます。パスワードログインは機関ログイン全体の試験ではありません。

作者は oauth 109 件／osf 41 件の成功と関連回帰試験 3 件の変異試験での失敗を報告しています。両アーキの各 10 層、内部 WAR／JAR、設定 blob を検索し、旧 JWE/JWT・TGC 文字列、代入パターン、指定した 4 鍵は検出 0 件、秘密でない対照値は 2 件でした。報告されたローカル OCI 索引は `sha256:5a1799d930b77a339f62cdd0a5aff9e6a1dfea07d91444e12c7e9653d7a53a7d` です。ソース修正と合わせて解決を支持しますが、レビュワはこれらを独立再現せず、イメージの実バイトも検証していません。

### 制限と後続事項

今回は Docker 操作、Maven／Java 試験、実起動、イメージ検査を実施していません。grdm-dev の状態と runtime/.env は操作していません。GitHub への書き込みは PR コメント 1 件のみで、commit・push・merge・approve・close はしていません。この記録は未コミットです。

OSF 受信側の既定値は CAS 差分の範囲外です。両側へ一致する環境固有鍵を設定し、履歴の例示値を再利用しないでください。実際の機関ログイン、実 GRDM スキーマ検証、TOTP、ORCiD、dev ターゲット、変更後の amd64 起動は従前どおり未確認です。TGC の鍵品質強化は後続事項です。この判定は未確認事項を確認済みにせず、あらゆるログ設定を保証しません。
