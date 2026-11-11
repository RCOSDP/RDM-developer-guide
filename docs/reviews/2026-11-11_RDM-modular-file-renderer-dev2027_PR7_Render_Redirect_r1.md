# REV PR #7 render redirect review r1 / 描画転送レビュー r1

> **Summary:** Pass for the GakuNin RDM GUID rendering path at the reviewed head. Removing the COS URL rewrite preserves the existing credential boundary; the upstream change was a compatibility fix, not a security fix.
> **概要:** 対象headの学認RDMのGUID描画経路はpass。COSのURL書換えを削除しても既存の資格情報の境界は保たれ、上流変更はセキュリティ修正ではなく互換修正だった。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-11_RDM-modular-file-renderer-dev2027_PR7_Render_Redirect_r1.md` (SHA-256: `d593dbd32128c30c2eeafbe0b2319a39c8bad3bbcee2ddf456dff0e4b89c3b32`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-11. **Learned:** RDM selects its internal file-service address in the GUID view, so the COS download-route workaround changes network reachability without adding an authentication safeguard. ／ RDMはGUIDのビューで内部ファイルサービスのアドレスを選ぶため、COSのdownload経路への対処は認証保護の追加ではなく到達先を変えていた。
- Applies to / 対象: RCOSDP/RDM-modular-file-renderer-dev2027 PR #7, head `2c4a88a663ca2c659e2b8fe46a2f26e84f206ba9`, base `f9da1db3c253c27c2dbc1a728390cbb0e373c94c`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related: [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [COS upstream commit / 上流コミット](https://github.com/CenterForOpenScience/modular-file-renderer/commit/f34a1b84d57e19468dc101ced6d6572e520a6d90).
- Used by / 利用先: coordinator's review gate for PR #7 and the separate C5 acceptance record in RDM-developer-guide PR #45 / 連携調整のPR #7レビュー判断およびRDM-developer-guide PR #45の別途C5受入記録。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass. No blocking findings.** The change restores the RDM route that chooses the internal WaterButler address. WaterButler is the service that reads and writes stored files; GUID is the short identifier in the file URL. This verdict applies to RDM's existing GUID download/render flow, not to compatibility with COS Angular OSF or successful deployment acceptance.

The scratch clone is detached at the requested head. Only `mfr/providers/osf/provider.py` and `tests/providers/test_osf_provider.py` differ from the base. An AST comparison (a comparison of Python program structure) confirms that `_fetch_download_url` is the only changed provider method. Credential validation, forwarding and redirect handling are unchanged. The remote head was rechecked before reporting.

### Credential destinations

`provider.py:197–219` sends the original URL through `_make_request`, validates the returned Location through `_redirect_target`, then evaluates the existing credential grant. There is no direct request that bypasses validation. Automatic redirects remain disabled at `:238`; each later destination is checked before `send_request` at `:270`.

`_validated_url_origin` (`:374–384`) requires exact membership in `ALLOWED_PROVIDER_NETLOCS`, not suffix or substring matching. `_url_origin` (`:353–368`) rejects invalid schemes, missing hosts, user information, backslashes, control characters and invalid ports. Credential grants use the normalized origin, meaning the scheme, hostname and effective port together. `_hop_keeps_credentials` (`:307–329`) grants a cross-origin hop only from the original configured source to a configured target and refuses HTTPS-to-HTTP downgrade. The two configuration lists are empty by default and are not edited by this PR.

With the test configuration, only `http://web:5000` → `http://wb:7777` receives the four captured credentials: Authorization, session cookie, cookie query parameter and view-only token. Unlisted external hosts, lookalikes, other ports and omitted ports are rejected before contacting that destination. A destination separately added to the network allowlist still receives none of these credentials unless its exact origin is granted. This does not mean that every external address is universally forbidden: deployment configuration controls the existing allowlist, and the original allowed provider origin retains its existing credential privilege. The shared client uses `DummyCookieJar`, so response cookies are not implicitly remembered across users or redirect requests.

### Upstream purpose and regression boundary

I read the complete message and patch of COS `f34a1b84d57e19468dc101ced6d6572e520a6d90` (2026-04-28). It adds a five-character GUID path match, prepends `/download/`, updates the request/error URL, and records a metric. The message explains that COS GUID URLs stopped redirecting to a downloadable file. No permission check, credential restriction or destination validation is added. **The evidence identifies a compatibility fix, not a security fix.** PR #6 imported that workaround; reverting it does not remove an authentication safeguard.

RDM-osf.io-dev2027 at `8fc45de4`, `addons/base/views.py:1034–1045`, explicitly passes `_internal=extras.get('mode') == 'render'` when producing the file URL. The same file's `persistent_file_download` (`:1081–1110`) instead passes query parameters to `generate_waterbutler_url` without deriving `_internal` from `mode`. `website/routes.py:1445–1450` binds `/download/<fid_or_guid>/` to that latter view. The GUID view retains `must_be_contributor_or_public`; changing the route does not itself bypass file authorization.

The COS failure would recur if this fork were used against a COS server whose GUID URL no longer returns the required 302. That is a compatibility boundary, not a security regression, and is outside this RDM-specific correction. Already-supplied `/download/<guid>/` URLs are also unchanged: the API v2/Ember `links.render` issue identified in the PR remains separate.

### Tests and evidence

The new `TestRdmGuidUrl` has 18 parameterized cases: two success cases, twelve destination-rejection cases across metadata and download, and four allowed-but-ungranted destination cases. Exact original URL assertions include the query string and detect restoration of the old rewrite. Metadata checks HEAD to internal WaterButler; download checks its target and credentials. Rejection tests assert that only the initial OSF request occurred. The credential helper checks all four captured credential types.

Existing tests additionally cover an arbitrary external destination, malformed URLs, HTTPS downgrade, onward storage redirects, and returning to WaterButler after leaving the credential-bearing chain. A small optional improvement is to apply the allowed-but-ungranted matrix to metadata as well as download and assert `error is None` in its successful download cases; the current shared request implementation and existing tests make this non-blocking. These are mocked transport tests, so they do not prove the real OSF response or Compose reachability.

Observed evidence, not a substitute for the separate C5 run:

```toon
checks[6]{check,result}:
  provider_security_methods_AST_comparison,unchanged from base
  git_diff_check,pass
  GitHub_CI_unit_suite,268 passed / 12 skipped / 26 warnings
  GitHub_CI_browser_suite,2 passed
  GitHub_CI_lint,pass through invoke test calling flake8 first
  local_unit_or_Compose_run,not run
```

I retrieved the successful GitHub Actions job `130528247456` from run `43019579995`. It tested merge commit `0dd21ae690309f73171d83a07642231f022af201` with Python 3.13.18. GitHub commit metadata confirms that this merge and the reviewed head share tree `e5c8c0a3d0f5e9263d72edc01fc5b9dfc0b349d8`, so the CI source is identical. The log is preserved at CI log (REV scratch evidence (not published): `pr7-ci.log`). The full suite was not rerun locally: the available Python is 3.15.2 and lacks the project's test dependencies. The author's claim of six mutation-test failures is not independently reproduced and is not counted as reviewer-run evidence.

No runtime/.env was accessed and no Docker command was executed. No commit, push, approval, merge or close was performed. Remaining work is the separately owned real C5 acceptance and the separate API v2/Ember rendering issue.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Pass。必須修正なし。** RDMが内部WaterButlerのアドレスを選ぶ経路を復元する変更として妥当。WaterButlerは保存ファイルを読み書きするサービス、GUIDはファイルURLに含む短い識別子を指す。この判定はRDMの既存GUIDダウンロード・描画経路に限り、COS Angular OSFとの互換性や配備後の受入成功までは示さない。

scratchのcloneを指定headに固定した。baseからの差分は `mfr/providers/osf/provider.py` と `tests/providers/test_osf_provider.py` のみ。AST比較（Pythonのプログラム構造の比較）で、変更されたproviderメソッドは `_fetch_download_url` だけと確認した。資格情報の検証・転送・リダイレクト処理は不変。報告前にリモートheadも再確認した。

### 資格情報の送信先

`provider.py:197–219` は元のURLを `_make_request` 経由で要求し、Locationを `_redirect_target` で検証してから既存の資格情報付与判定を行う。検証を迂回する直接要求はない。`:238` で自動転送を無効にし、後続の送信先も `:270` の `send_request` より前に検査する。

`_validated_url_origin`（`:374–384`）は `ALLOWED_PROVIDER_NETLOCS` との完全一致を求め、末尾一致・部分一致は使わない。`_url_origin`（`:353–368`）は不正なscheme、host欠落、ユーザー情報、バックスラッシュ、制御文字、不正なポートを拒否する。資格情報の付与には正規化したorigin、つまりscheme・hostname・実効ポートの組を使う。`_hop_keeps_credentials`（`:307–329`）は元の設定済み送信元から設定済み送信先への転送だけに別originへの資格情報を許し、HTTPSからHTTPへの降格を拒否する。設定リストは既定で空であり、このPRは変更していない。

試験の設定では `http://web:5000` → `http://wb:7777` だけに、Authorization・セッションcookie・cookieクエリ引数・view-onlyトークンの4種が届く。許可外の外部host、似た名前、別ポート、ポート省略は、その送信先への要求前に拒否される。ネットワークの許可リストだけに別途追加しても、厳密なoriginへの付与がなければ4種とも渡らない。ただし全外部アドレスを一律拒否する意味ではない。既存の許可リストは配備設定が決め、元の許可済みprovider originには従来どおり資格情報が届く。共有クライアントは `DummyCookieJar` を使い、応答cookieを利用者間や後続要求へ暗黙に記憶しない。

### 上流の目的と回帰の境界

COS `f34a1b84d57e19468dc101ced6d6572e520a6d90`（2026-04-28）のメッセージと全差分を読んだ。5文字のGUIDパス判定、`/download/` の前置、要求・エラーURLの変更、メトリクスの追加である。メッセージはCOSのGUID URLがダウンロード先へ転送されなくなったと説明している。権限検査・資格情報制限・送信先検証の追加はない。**確認できた根拠からはセキュリティ修正ではなく互換修正と判断する。** PR #6が取り込んだこの対処を戻しても認証保護は削除されない。

RDM-osf.io-dev2027の `8fc45de4`、`addons/base/views.py:1034–1045` はファイルURL生成時に `_internal=extras.get('mode') == 'render'` を明示する。一方、同ファイルの `persistent_file_download`（`:1081–1110`）はクエリ引数を `generate_waterbutler_url` に渡すだけで、modeから_internalを導かない。`website/routes.py:1445–1450` は `/download/<fid_or_guid>/` を後者へ結ぶ。GUIDのビューには `must_be_contributor_or_public` が残り、経路変更自体はファイルの権限確認を迂回しない。

GUID URLが必要な302を返さないCOSサーバーにこのforkを使えば、COSで対処した不具合は再発する。それは互換性の境界であり、セキュリティ回帰ではなく、RDM向けの今回の修正範囲外である。既に `/download/<guid>/` として渡されたURLも変わらないため、PRが挙げるAPI v2/Emberの `links.render` 問題は別件として残る。

### テストと証拠

追加された `TestRdmGuidUrl` は、パラメータ展開後18件。成功2件、metadataとdownload両方での送信先拒否12件、ネットワーク許可済み・資格情報未付与の送信先4件である。元URLの完全一致にはクエリ文字列も含み、旧書換えが戻れば検出する。metadataは内部WaterButlerへのHEADを確認し、downloadは送信先と資格情報を確認する。拒否例は最初のOSF要求だけが発生したと検証する。資格情報の補助関数は4種すべてを見る。

既存試験では任意の外部送信先、不正URL、HTTPS降格、保存先への後続転送、資格情報を保持する経路から離れた後のWaterButlerへの戻りも扱う。任意の改善として、ネットワーク許可済み・資格情報未付与の表をmetadataにも広げ、そのdownload成功例で `error is None` を確認するとさらに明確になる。現状の共有要求実装と既存試験を踏まえ、必須修正とはしない。要求送信を模した単体試験なので、実OSFの応答やCompose内の到達性までは証明しない。

確認した証拠は次のとおりで、別途のC5実行の代わりではない。

```toon
checks[6]{check,result}:
  providerセキュリティメソッドのAST比較,baseと同一
  git_diff_check,成功
  GitHub_CI単体試験,268成功 / 12スキップ / 26警告
  GitHub_CIブラウザ試験,2成功
  GitHub_CI静的検査,invoke testが先にflake8を実行して成功
  ローカル単体試験またはCompose試験,未実施
```

GitHub Actionsの成功job `130528247456`（run `43019579995`）を取得した。Python 3.13.18でmerge commit `0dd21ae690309f73171d83a07642231f022af201` を試験している。GitHubのcommit情報により、このmergeと対象headのtreeはともに `e5c8c0a3d0f5e9263d72edc01fc5b9dfc0b349d8` と確認でき、CIが検査したソースは同一。CIログ (REV scratch evidence (not published): `pr7-ci.log`)を保存した。ローカルのPythonは3.15.2でプロジェクトの試験依存がないため、全試験は再実行していない。作者の「旧実装へ戻すと6件失敗」という記載は独立再現しておらず、レビュワ実行の証拠には数えない。

runtime/.envにアクセスせず、Dockerコマンドも実行していない。commit・push・approve・merge・closeは行っていない。残る作業は別担当の実機C5受入と、別件のAPI v2/Ember描画問題である。
