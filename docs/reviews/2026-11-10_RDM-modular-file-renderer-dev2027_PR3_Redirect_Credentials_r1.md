# MFR PR3 Redirect credentials review r1 / MFR転送資格情報レビュー r1

> **Summary:** Pass: explicit origin pairs grant credentials only on the intended OSF-to-WaterButler hop.
> **概要:** 合格。明示したoriginの組により、意図したOSFからWaterButlerへの転送だけへ資格情報を付与する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** A provider-host allowlist and permission to receive credentials are separate controls. ／ 接続先ホストの許可と資格情報を受け取る許可は別の制御である。
- Applies to: RDM-modular-file-renderer-dev2027 PR #3, head `f712fca39a5d2cab11c53e4f4dac355931281645`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: the coordinator's source-absorption decision and follow-up verification. ／ 調整担当のソース吸収判断と後続検証。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and behavior

**Pass.** Reviewed base-to-head changes and surrounding resolver, metadata, download and manual redirect code. No actionable regression was found in the requested scope.

`mfr/providers/osf/provider.py:290–311` grants a target only when the current source is the original request origin, the source is configured, and the target is configured. Scheme, lowercased host and effective port form the comparison key; this is not suffix matching. HTTPS-to-HTTP never grants even when configured. Every actual URL still passes the provider netloc allowlist and malformed/userinfo/invalid-port checks before requesting it. The configured source and target sets describe their Cartesian product, not individually zipped pairs; deployment must trust all such combinations.

The resolver grants the validated OSF redirect target so subsequent metadata/download requests can carry Authorization, cookies, `cookie` and `view_only`. Same-origin WaterButler redirects keep the grant. A hop onward to another origin drops these credentials, even another configured target cannot be granted by WaterButler, and the chain's false carry flag prevents reacquiring the grant after leaving. Returning to the **original** origin still restores its original credentials, matching existing behavior and the PR's explicit contract; this is not a new target grant. Both configured lists default to empty, preserving previous cross-origin stripping when deployment makes no opt-in.

Lookalike suffix/prefix hosts, wrong ports, invalid ports, malformed URLs, HTTP downgrade, untrusted derived URLs, storage-to-WaterButler chains and WaterButler-to-storage-to-WaterButler chains are covered by the supplied focused tests. The underlying provider URL allowlist remains distinct from the credential-grant list.

### Validation and limits

Independently ran all **36 focused provider tests, exit 0**, through `/private/tmp/rev-8275-oBBpKc/mfr_harness.py`. It loads the actual reviewed provider, base provider, metrics and exception source unchanged, uses installed furl, and stubs configuration and legacy transport/WaterButler dependencies; the tests themselves mock requests. Modern pytest required `-c /dev/null` to bypass the legacy `[pytest]` setup.cfg format. This validates provider decisions with mocks, not compatibility of the pinned 2016 aiohttp stack or real HTTP transfers. `git diff --check` passed. The PR author's 183 full-suite passes and lint success were inspected as author evidence, not repeated independently.

C5 still needs an image rebuild and explicit deployment values for `OSF_PROVIDER_CONFIG_CREDENTIAL_SOURCE_ORIGINS` and `OSF_PROVIDER_CONFIG_CREDENTIAL_TARGET_ORIGINS`; the PR documents internal `http://web:5000` to `http://wb:7777`. Actual preview success remains an acceptance prerequisite. No Docker command, stack or runtime credential-file access, source edit, commit, push, approval, merge or closure occurred. This uncommitted record and one Japanese comment are the deliverables.

GitHub reports passing image-build and MFR-test checks.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と動作

**合格（pass）。** baseからheadの差分と周辺のresolver、metadata、download、手動redirect処理を確認し、依頼範囲で修正を要する退行は見つからなかった。

`mfr/providers/osf/provider.py:290–311` は、現在の転送元が最初の要求originであり、転送元と転送先の両方が設定済みのときだけ付与する。比較キーはscheme、小文字host、実効portで、suffix比較ではない。設定済みでもHTTPSからHTTPには付与しない。実際の各URLは要求前にproviderのnetloc許可と、不正URL/userinfo/不正portの拒否を通る。転送元集合と転送先集合は個別の組のzipではなく直積なので、配備時は全組合せを信頼する必要がある。

resolverは検証したOSFの転送先へ付与し、後続metadata/downloadがAuthorization、cookies、`cookie`、`view_only`を送れる。同じWaterButler origin内の転送は維持する。別originへの転送では落とし、別の設定済みtargetでもWaterButlerからは付与できず、連鎖のcarryフラグがfalseになると離脱後に再付与しない。**元の**originに戻ると元の資格情報が戻る点は、既存動作とPRに明記された契約を維持するもので、新たなtarget付与ではない。両設定の既定値は空なので、配備側が選ばなければ従来どおりcross-originでは落とす。

類似suffix/prefixホスト、別port、範囲外port、不正URL、HTTPへの格下げ、未許可の解決先、storage→WaterButler、WaterButler→storage→WaterButlerの連鎖は追加された対象試験で扱う。接続先URLの許可一覧と資格情報付与の許可一覧は別に保たれる。

### 検証と限界

`/private/tmp/rev-8275-oBBpKc/mfr_harness.py` で **対象provider試験36件を独立実行し、0終了**した。レビュー対象のprovider、base provider、metrics、exceptionのソースを変更せず読み込み、導入したfurlを使い、設定と旧transport/WaterButler依存をstubにした。試験自体も要求をmockにする。現行pytestでは古いsetup.cfgの `[pytest]` を避けるため `-c /dev/null` が必要だった。providerの判定をmockで確認した結果であり、固定された2016年のaiohttpや実HTTP転送の互換性を証明するものではない。`git diff --check` は成功。著者の全体183件合格とlint成功は報告として確認し、独立再実行はしていない。

C5にはイメージ再ビルドと `OSF_PROVIDER_CONFIG_CREDENTIAL_SOURCE_ORIGINS` / `OSF_PROVIDER_CONFIG_CREDENTIAL_TARGET_ORIGINS` の明示設定が残る。PRは内部 `http://web:5000` → `http://wb:7777` を記載する。実preview成功は受入前提条件として残る。Dockerコマンド、スタック/runtime資格情報ファイル参照、ソース修正、commit、push、approve、merge、closeは行っていない。未コミット記録と日本語コメント1件を成果物とする。

GitHubのimage-buildとMFR-testチェックは成功している。
