# REV PR3 Real startup review r1 / 実起動レビュー r1

> **Summary:** Changes requested: the deterministic logging fix and native build layout are sound, but the distribution image still includes reusable TGC keys.
> **概要:** changes requested。ロギング修正とネイティブビルド構成は妥当ですが、配布イメージに再利用可能な TGC 鍵が残ります。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** runtime secret injection does not remove fixed keys copied into image layers. ／ 実行時に秘密を注入しても、イメージ層へコピーした固定鍵は消えません。
- Applies to: RCOSDP/RDM-cas-overlay-dev2027 PR #3, head `c488b319db226bf1f818fa687a23911c31242adb`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: PR #3 revision and coordinator integration decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and required change

**Changes requested — R1-01 (P2): remove usable fixed TGC keys from the shipped configuration.** `Dockerfile:35` copies `etc/cas.properties` into `dist-config`; lines 41–45 only rewrite paths, and line 51 copies that file into the final image. The source file contains nonempty 43-character encryption and 86-character signing keys. They are inherited examples, not evidence of leaked deployment credentials, but they remain usable shared cryptographic defaults. The comment requiring per-deployment generation and a runtime bind mount do not remove them from image layers. A deployment that omits its key injection can retain known keys once its other configuration is supplied.

Remove these usable defaults from the image input, require deployment-specific keys, and verify that missing keys fail closed without logging generated or supplied key material. Verify that the resulting image contains neither fixed keys nor deployment credentials and that an environment-only key configuration still starts. This finding concerns the changed distribution recipe carrying forward unsafe defaults; it does not claim the documented probe used those defaults.

### Checks and evidence

The listener choice is deterministic: `Log4jContextInitializer.java:49` directly constructs `Log4jServletContextListener`; no set iteration or reflection selects a listener. The overlay XML points its `log4jInitialization` bean to that class. Maven unpacks the support module into application classes and the local web resources supply the overlay. Four added tests cover lifecycle creation, the wrong listener's failure, repeat initialization, and unreadable resource handling. XML parsing passed for both new production XML files and the test logging configuration; unit tests and WAR packaging were not rerun in this review.

Both Maven and Jetty bases have explicit SHA-256 digest pins. Both executable build stages use `$BUILDPLATFORM`; the final target inherits the requested architecture and only copies artifacts. The same Jetty digest is used for configuration and runtime. This supports native build execution and preserves Java 8; it is not a claim of byte-reproducible Maven dependencies. Registry index contents and the reported unpublished output digest were not independently fetched or rebuilt under the read-only review scope.

The final stage sets `USER 1000:1000`, clears the inherited entrypoint, and sets the Java temporary directory to `/tmp`. The logging configuration uses console output. Read-only root and tmpfs are runtime options, not enforcement by the Dockerfile. PR evidence reports successful hardened startup; this review did not operate Docker. `throwUnavailableOnStartupException=true` is present; actual process exit is author-reported evidence.

The new logger emits the listener class name, not keys or passwords. No new secret build argument or environment assignment was introduced. This source inspection does not certify every upstream logging path or actual image layer. The fixed keys identified in R1-01 prevent an unconditional “no secrets baked in” conclusion.

The PR body documents `DATABASE_PASSWORD`, `OSF_DATABASE_PASSWORD`, `TGC_ENCRYPTION_KEY` (43 base64url characters / 32 bytes), and `TGC_SIGNING_KEY` (86 characters / 64 bytes), and explains that `CAS_TGC_*` does not map to the configured properties. It documents the read-only configuration mount, `/tmp`, migration completion ordering, and service allow-list changes. These are PR-level instructions; they have not been applied to the installer.

### Stated limits

Real GRDM schema validation, OAuth table matching, TOTP, ORCiD, institution login, the dev stage, and webapp module unit tests remain unverified. The minimal probe schema and author-reported successful login do not establish integration readiness. The first amd64 emulated startup exceeded 244 seconds and was stopped; a second reached HTTP 200 in 116 seconds. The cause remains unknown and must inform later timeout testing; it is not evidence that native Maven builds failed. These are accepted scope limits, not additional blockers for this startup change. The dev stage is not covered by the distribution stage's non-root guarantee. No Docker state, runtime/.env, commits, pushes, merges, or approvals were touched.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と必要な修正

**Changes requested — R1-01（P2）：配布設定から使用可能な固定 TGC 鍵を除去してください。** `Dockerfile:35` は `etc/cas.properties` を `dist-config` にコピーし、41〜45 行はパスだけを変更し、51 行で最終イメージへコピーします。元ファイルには 43 文字の暗号鍵と 86 文字の署名鍵が設定されています。既存のサンプル値であり、実環境の秘密漏えいを示すものではありませんが、共通の使用可能な暗号鍵として残ります。環境ごとに生成するよう求める注記や実行時マウントでは、イメージ層から鍵は消えません。他の設定を用意しても鍵の注入を忘れると、既知の鍵が残り得ます。

イメージ入力から使用可能な既定鍵を除き、環境固有の鍵を必須にしてください。鍵がない場合は安全に起動を拒否し、生成鍵や指定鍵をログへ出さないことを確認してください。完成イメージに固定鍵・実環境の秘密がなく、環境変数だけで鍵を指定した構成が起動することも確認してください。変更された配布レシピが危険な既定値を引き継ぐ点の指摘であり、報告された起動試験がその鍵を使ったという指摘ではありません。

### 確認事項と根拠

リスナー選択は決定的です。`Log4jContextInitializer.java:49` は `Log4jServletContextListener` を直接生成し、集合の順序やリフレクションで選びません。上書き XML の `log4jInitialization` bean は新クラスを参照します。Maven はサポートモジュールをアプリケーションクラスへ展開し、ローカルの Web リソースが上書き設定を供給します。追加試験 4 件はライフサイクル生成、誤ったリスナーの失敗、再初期化、読めないリソースを扱います。新規の本番 XML 2 件と試験用ログ設定の XML 構文解析は成功しました。単体試験と WAR 作成は再実行していません。

Maven と Jetty のベースは SHA-256 ダイジェストで固定されています。処理を実行する両ビルドステージは `$BUILDPLATFORM` を使い、最終ステージは要求されたアーキテクチャを継承して成果物だけをコピーします。設定作成と実行には同じ Jetty ダイジェストを使います。ネイティブビルドと Java 8 維持に整合しますが、Maven 依存物までバイト単位で再現可能との保証ではありません。読み取り中心のレビュー範囲では、レジストリ索引の内容や未公開の出力ダイジェストを独立に取得・再ビルドしていません。

最終ステージは `USER 1000:1000` を設定し、継承した entrypoint を解除し、Java 一時領域を `/tmp` に設定します。ログ設定は標準出力を使います。読み取り専用ルートと tmpfs は実行時の指定であり、Dockerfile による強制ではありません。PR は堅牢化条件での起動成功を報告していますが、レビュワは Docker を操作していません。`throwUnavailableOnStartupException=true` は存在し、実際のプロセス終了は作者の報告による証拠です。

新しいロガーが出力するのはリスナークラス名で、鍵やパスワードではありません。秘密のビルド引数や環境変数代入も追加していません。このソース確認は上流の全ログ経路や実イメージ層の安全性を保証しません。R1-01 の固定鍵により「秘密の焼き込みなし」とは無条件に判定できません。

PR 本文には `DATABASE_PASSWORD`、`OSF_DATABASE_PASSWORD`、`TGC_ENCRYPTION_KEY`（base64url 43 文字／32 バイト）、`TGC_SIGNING_KEY`（86 文字／64 バイト）が記載され、`CAS_TGC_*` が設定キーに対応しない点も明示されています。設定の読み取り専用マウント、`/tmp`、マイグレーション完了の起動順、サービス許可定義も記載されています。PR 上の手順であり、インストーラにはまだ反映されていません。

### 明示された制限

実 GRDM スキーマの validate、OAuth テーブル照合、TOTP、ORCiD、機関ログイン、dev ステージ、webapp モジュール単体試験は未検証です。最小試験スキーマと作者報告のログイン成功は、統合準備完了を意味しません。amd64 エミュレーションの初回起動は 244 秒を超えて打ち切られ、2 回目は 116 秒で HTTP 200 になりました。原因未特定として後続のタイムアウト試験に引き継ぐ事項であり、ネイティブ Maven ビルドの失敗を示すものではありません。これらは今回の範囲制限として扱い、追加の修正必須事項にはしません。dev ステージに配布ステージの非 root 保証は適用されません。Docker 状態、runtime/.env、コミット、push、merge、approve は操作していません。
