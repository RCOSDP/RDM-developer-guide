# REV PR3 Real startup review r2 / 実起動レビュー r2

> **Summary:** Changes requested: R1-01 is addressed for TGC, but usable fixed institution-login JWE/JWT secrets remain in the distribution image.
> **概要:** changes requested。TGC の R1-01 は対応済みですが、機関ログイン用の使用可能な固定 JWE/JWT 秘密が配布イメージに残ります。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** removing cookie keys does not remove other usable shared authentication secrets from the same image. ／ Cookie 鍵の除去だけでは、同じイメージの別の使用可能な共通認証秘密は除去できません。
- Applies to: RCOSDP/RDM-cas-overlay-dev2027 PR #3; delta `c488b319db226bf1f818fa687a23911c31242adb..96de2b60f6d2a3568cb47fe37a325b631f286d36`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [r1](2026-11-10_RDM-cas-overlay-dev2027_PR3_Real_Startup_r1.md).
- Used by: PR #3 revision and [review integration](README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and blocker

**Changes requested — R2-01 (P2): remove usable default institution-login JWE/JWT secrets.** `etc/cas.properties:105–106` still supplies fixed values, each exactly 32 ASCII bytes. `Dockerfile:35,51` copies them into the final image without removal. `cas-server-webapp/src/main/webapp/WEB-INF/cas-servlet.xml:359–360` injects them into the institution-login action. In `OpenScienceFrameworkPrincipalFromRequestRemoteUserNonInteractiveCredentialsAction.java:718–726`, they are passed directly as bytes to HS256 `MACSigner` and direct A256GCM `DirectEncrypter`. The setters at lines 854–859 only assign values. These are usable cryptographic defaults, not inert placeholders. Supplying the other deployment settings while omitting these overrides leaves known keys in use. Whether a particular OSF receiver accepts the resulting token depends on its matching configuration; this review does not claim a demonstrated deployed authentication bypass.

This is the same class as R1-01 and remains within review of the new distribution recipe and its remediation. Remove these values from shipped configuration, require deployment-specific secrets for the enabled institution-login path, and fail closed when absent or empty. An explicitly disabled path may instead refuse all institution authentication without a fallback. Verify missing-secret behavior, runtime-only injection, absence from image layers, and no secret logging. Add regression coverage for these defaults as well as TGC.

### R1-01 verification and remaining-item decisions

**R1-01: addressed for TGC.** The new commit removes both assignments and adds `shippedConfigurationCarriesNoTicketGrantingCookieKeys`, which asserts their absence from the parsed source properties. An independent tracked-file scan found neither old TGC literal at the reviewed head. `ticketGrantingTicketCookieGenerator.xml:47–48` retains mandatory placeholders without fallback. This supports refusal when keys are absent. The test checks source configuration, not startup, layers, or key quality.

The author reports arm64 exit 254 for both keys missing, signing key missing, and both empty; successful environment-only login and ticket validation; no supplied keys in logs; and no old TGC literals in either architecture's layers, including nested archives. These runtime and artifact results were not independently reproduced. The source change and reported evidence resolve the TGC-specific finding, not a broader claim that the image carries no usable fixed secrets.

| Remaining item | Blocks this revision? | Reason |
|---|---|---|
| Short supplied TGC keys accepted | No; follow-up hardening | Requires explicit operator-supplied weak values, unlike omission selecting a known shared default. The documented 43/86-character requirement remains; add decoded-length/format validation and tests before broader deployment. Startup with `abc` does not demonstrate successful login. |
| Old TGC keys in Git history | No | They must be treated as compromised examples and never reused; rotate any deployment that used them. `.dockerignore` excludes `.git`, and the head no longer contains the literals. History rewriting is not required to fix this image. |
| Default JWE/JWT values in image | **Yes: R2-01** | Both are usable 32-byte keys consumed by the active crypto code, with no explicit override required. |
| ORCiD example values in image | No on available evidence | `etc/cas.properties:87–88` contains descriptive client-ID/secret placeholders, passed to the external provider by `authenticationDelegation.xml:29–30`. No evidence shows these are registered, working credentials; they are not locally accepted symmetric authentication keys. Remove or require explicit configuration when enabling ORCiD, and never describe these placeholders as verified credentials. |
| No post-change amd64 startup | No | This delta only removes configuration values and adds a source test; it changes no architecture-specific runtime code. Both-architecture builds/layer checks and arm64 startup are author-reported. Post-change amd64 startup remains unverified; r1's emulation timeout uncertainty remains. |

### Scope and evidence limits

Reviewed one new commit, the PR body, and relevant consumers in an isolated scratch clone at the exact head. No Java unit tests, Maven build, Docker operation, image inspection, or live startup was independently run. No grdm-dev state or runtime/.env was touched. No commit, push, merge, approval, or close was performed; the only GitHub write is one review comment. The r1 limits on real GRDM schema, TOTP, ORCiD, institution-login integration, and dev stage remain. This record is uncommitted.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と修正必須事項

**Changes requested — R2-01（P2）：使用可能な機関ログイン用 JWE/JWT 既定秘密を除去してください。** `etc/cas.properties:105–106` には、それぞれ正確に ASCII 32 バイトの固定値が残ります。`Dockerfile:35,51` は除去せず最終イメージへコピーします。`cas-server-webapp/src/main/webapp/WEB-INF/cas-servlet.xml:359–360` が機関ログイン処理へ注入します。`OpenScienceFrameworkPrincipalFromRequestRemoteUserNonInteractiveCredentialsAction.java:718–726` は、そのバイト列を HS256 の `MACSigner` と direct A256GCM の `DirectEncrypter` に直接渡します。854〜859 行の setter は代入だけです。これは無効な仮文字列ではなく、使用可能な暗号鍵の既定値です。他の配備設定を与えてこの上書きを省略すると、既知の鍵を使用します。OSF 側がトークンを受理するかは相手の設定との一致に依存し、実環境での認証迂回を実証したという主張ではありません。

R1-01 と同じ問題であり、新しい配布レシピとその修正のレビュー範囲内です。配布設定から値を除去し、有効な機関ログイン経路には環境固有の秘密を必須とし、未設定・空文字で安全に拒否してください。明示的に無効化した経路なら、代替鍵を使わず機関認証をすべて拒否する方式でも構いません。未設定時の挙動、実行時のみの注入、イメージ層からの除去、秘密のログ非出力を確認し、TGC に加えてこれらの既定値にも回帰試験を追加してください。

### R1-01 の確認と残存事項の判定

**R1-01：TGC について対応済み。** 新コミットは両代入を除去し、読み込んだソース設定にキーが存在しないことを検査する `shippedConfigurationCarriesNoTicketGrantingCookieKeys` を追加しています。独立した追跡ファイル検索では、対象 head に旧 TGC 鍵の文字列はありませんでした。`ticketGrantingTicketCookieGenerator.xml:47–48` は代替値なしの必須参照を維持しており、鍵がない場合の起動拒否と整合します。追加試験が確認するのはソース設定であり、実起動・イメージ層・鍵の品質ではありません。

作者は arm64 で両鍵未設定・署名鍵未設定・両鍵空文字が exit 254、環境変数のみでログインとチケット検証が成功、指定鍵のログ出力なし、両アーキテクチャの全層と内部アーカイブに旧 TGC 鍵なしと報告しています。実行時および成果物の結果は独立に再現していません。ソース変更と報告された証拠により TGC 固有の指摘は解決しますが、「イメージに使用可能な固定秘密がない」という広い主張は成立しません。

| 残存事項 | 今回の修正を阻害するか | 理由 |
|---|---|---|
| 短い指定 TGC 鍵を受理 | しない。後続の強化事項 | 明示的に弱い値を指定した場合であり、省略による既知の共通鍵の選択とは異なります。43／86 文字の要件を維持し、広い配備の前にデコード後の長さ・形式検証と試験を追加すべきです。`abc` での起動成功はログイン成功を示しません。 |
| Git 履歴の旧 TGC 鍵 | しない | 公開済みの例として再利用禁止とし、使用した環境では交換が必要です。`.dockerignore` は `.git` を除外し、head に旧文字列はありません。イメージ修正のための履歴書換えは不要です。 |
| イメージ内の JWE/JWT 既定値 | **する：R2-01** | 使用可能な 32 バイト鍵を暗号処理が使い、明示的な上書きは必須ではありません。 |
| ORCiD 例示値 | 現在の証拠ではしない | `etc/cas.properties:87–88` は説明的な client-ID／secret の仮値で、`authenticationDelegation.xml:29–30` から外部プロバイダに渡されます。登録済みで動作する資格情報という証拠はなく、ローカルに受理する対称認証鍵とは異なります。ORCiD 有効化時には除去または明示設定必須とし、有効性確認済みの資格情報と扱わないでください。 |
| 変更後の amd64 未起動 | しない | 差分は設定値除去とソース試験だけで、アーキテクチャ固有の実行コードを変更しません。両アーキのビルド・層検査と arm64 起動は作者報告です。変更後の amd64 起動は未確認で、r1 のエミュレーション起動遅延の不確実性も残ります。 |

### 範囲と証拠の制限

専用 scratch clone の正確な head で、新規 1 コミット、PR 本文、関連する利用箇所を確認しました。Java 単体試験、Maven ビルド、Docker 操作、イメージ検査、実起動は独立に実行していません。grdm-dev の状態と runtime/.env は操作していません。commit、push、merge、approve、close は行わず、GitHub への書き込みはレビューコメント 1 件だけです。実 GRDM スキーマ、TOTP、ORCiD、機関ログイン統合、dev ステージについて r1 の制限が残ります。この記録は未コミットです。
