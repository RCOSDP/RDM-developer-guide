# REV-PR2-R2 Static build review / 静的ビルド再レビュー

> **Summary:** Pass for the four follow-up commits of RDM-ember-osf-web-dev2027 PR #2 and the supplied installer patch. The previous required findings are resolved within the reviewed scope.
> **概要:** RDM-ember-osf-web-dev2027 PR #2 の追加四コミットと指定 installer patch は pass。確認した範囲では前回の必須指摘は解消しています。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** REV changed only what publication requires: private-repository URLs become named plain-text references; local guide links become repository-relative links; unpublished scratch references become named plain text or quoted command-path placeholders; public review links absent from develop point to the reviewed public commit. ／ REV が公開に必要な変更のみを行った。非公開リポジトリの URL は名称付き平文参照、ローカルのガイドへのリンクはリポジトリ相対リンク、未公開 scratch の参照は名称付き平文またはコマンドの引用符付きパス代替表示とし、develop に未収録の公開レビューへのリンクは確認済みの公開コミットを指す。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `2026-11-11_RDM-ember-osf-web-dev2027_PR2_Static_Build_r2.md` (SHA-256: `790fb530ad02a2d9e8965091c1ace448aa2a94a4dc34481091de07e73ec1e919`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. Quoted scratch command-path placeholders identify retained unpublished evidence and must be replaced with its local location before execution. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。コマンド内の引用符付き scratch パス代替表示は保持された未公開証跡を識別するもので、実行にはそのローカルの場所への置換が必要。
- Version / 版: 0.1 — 2026-11-11. **Learned:** Safe rendering and safe shipped dependencies need separate checks; a clean runtime image alone proves neither. ／ 安全な描画と配信される依存コードは別々に確かめる必要があり、実行イメージの検査結果だけではどちらも証明できない。
- **Applies to:** REV（担当レビュワ）r2; RDM-ember-osf-web-dev2027 PR #2, `898e753a5baf` → `0246b5a3b34ba8dbf6341d2193ea27ae9f47cf0e`; supplied installer patch based on RDM-developer-guide `eb8c4e9`.
- **Related:** [Review index / レビュー索引](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · Installer patch / インストーラーパッチ (REV scratch evidence (not published): `grdm-dev-ember-static.patch`)
- **Used by / 利用先:** PR #2 review decision and the coordinator's installer integration decision / PR #2 のレビュー判定と調整担当の installer 統合判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**PASS. No new required changes found.** R1-01 (HTML injection), R1-02 (shipped dependency assessment), and R1-03 (installer/specification mismatch) are resolved for the reviewed default static build. This is a review verdict, not GitHub approval or merge authorization.

The four reviewed commits are `4602cd081` (renderer), `1cadf7e33` (Node wrapper), `fd3d57554` (security backports), and `0246b5a3b` (test target). The installer patch SHA-256 is `3b206cfa31988ca0a0bf37b17a695bee000ec496168031b426c20ae390983999`.

### Renderer and regression checks

`docker/static/render.sh` validates each complete environment value before rendering. The ASCII allow-lists reject control characters, Unicode separators, quotes, markup and percent escapes; field-specific patterns and lengths then constrain URLs and the cookie domain. All seven substituted values are URI-encoded (characters are represented safely inside the HTML attribute). `entrypoint.sh` stops when rendering fails, before starting nginx.

An independent harness applied U+2028/U+2029, U+0085, nonbreaking space, fullwidth quote, encoded/double-encoded CR/LF, both quotes, `</script>`, JavaScript schemes, control characters and overlong values across the six URL variables, cookie domain and both CSP settings. All 199 invalid cases returned 1 and left a pre-existing output tree byte-for-byte unchanged. Three accepted URL cases round-tripped exactly, including length 2000 and ports 00001/65535. Existing renderer tests separately cover rejection before initial files are created.

Seven independent postbuild fixtures checked valid input, raw/encoded placeholders outside the configuration, placeholders in another asset, missing placeholders, and duplicate configuration tags. All behaved as expected. The actual production output passed postbuild and then rendered successfully; its configuration contained the expected default backend URLs and no Google Analytics adapter. This also resolves the previous concern about rendering files nginx would never serve.

### Shipped dependencies and upstream comparison

The reviewer installed the frozen lockfile in a fresh scratch clone and built production output using Node 24.22.2. Only webpack's `optimization.namedModules` was enabled in the scratch copy to retain package names for inventory; the result is an instrumented production build, not a byte-identical release image. Thirty JavaScript files exposed 18 named packages. None of the package names in the supplied 2 CRITICAL / 51 HIGH lockfile report appeared directly in those named modules; vendor imports and nested prebuilt bundles were inspected separately.

- **sanitize-html 1.20.0:** `ember-cli-sanitize-html` imports `dist/sanitize-html.js` into vendor.js, and collections passes provider descriptions through it. The backported loop is semantically identical to [upstream 2.7.1 at b4682c12](https://github.com/apostrophecms/sanitize-html/blob/b4682c12fd30e12e82fa2d9b766de91d7d2cd23c/index.js#L615). The emitted vendor file contains the new indexOf loop and no old comment regex. Direct execution of the browser bundle removes disguised JavaScript URLs; 50,000 unclosed comment openers (200,000 characters) took about 9.4 ms in this run.
- **d3-color inside keen-dataviz 2.0.10:** both numeric patterns match [upstream 3.1.0 at 7a1573ed](https://github.com/d3/d3-color/blob/7a1573ed260de4fd97d061975244841132adde92/src/color.js#L8). The analytics engine vendor output contains two fixed patterns and zero old patterns. The regression suite covers representative valid colors and long invalid input.
- **js-cookie 2.1.0 inside keen-tracking 2.0.10:** it remains shipped, so it is an accepted risk, not a fixed package. The emitted configuration has `Keen.environments: []`. Application code does not call the library's cookie or auto-tracking API; its cookie use is through Ember's cookie service. The stated acceptance boundary, Keen removal or the Ember 3.28 migration PR, is reasonable for this default artifact. Enabling Keen or introducing cookie/auto-tracking calls requires renewed assessment.
- **PostCSS inside sanitize-html:** it is browser code, not categorically build-only. Its bundled `fs` module is empty, and the source-map file-read branches guard `existsSync`; the reported filesystem-read advisories are therefore unreachable in this browser bundle. The other reported tooling packages were not found in the reviewed browser import paths. The lockfile findings remain; no claim of a clean dependency scan is made.

The five patched dependency files were unchanged by a second run of the backport script. The browser fixes and renderer tests passed locally. Upstream sources were obtained with read-only GitHub API calls.

### CI, test target and installer

Both checks on the specified PR head report success. The independently fetched log for run `43017266950` shows Node 8.17.0 triggering the pinned 24.22.2 download, a successful SHA-256 verification, 393 node tests passing with 265 pending, and 978 Ember tests complete with four skip markers. The wrapper also passed a local Node 24 smoke check for the util shim and preservation of an argument containing spaces. Updating the workflow itself to Node 24 remains sensible follow-up work.

The Docker test CMD removes all seven placeholder environment variables. Executing its `env -u` sequence against configuration loading restored the same test OSF configuration as a clean environment. The Docker test image itself was not rebuilt by this reviewer.

The installer patch applied cleanly to an isolated clone at `eb8c4e9`. It preserves the static entrypoint, uses uid 101, `/tmp` tmpfs, no writable dist volume and a `/healthz` probe that requires HTTP 200. SPEC-01, SPEC-02 and the environment guide agree in both languages. Recalculation including initialization services gives core 8320 MiB (11.607 GiB at a 70% budget), full/fakecas 9344 MiB (13.036 GiB), and full/shibboleth 9664 MiB (13.482 GiB). These are computed floors, not measured build or runtime peaks. The temporary PR-head pin must move to the integration commit after merge, as the patch already states.

Review observations:

```toon
checks[10]{check,result}:
  independent_invalid_inputs,199 rejected without writes
  independent_valid_roundtrips,3 passed
  independent_postbuild_fixtures,7 passed
  renderer_and_security_tests,172 passed
  instrumented_production_build,passed on Node 24.22.2
  actual_output_postbuild_and_render,passed
  installer_tests,639 run with 10 skipped and no failures
  tools_tests,93 passed
  manifest_check,passed
  docs_check,154 checked with 8 exempt and 38 warnings
```

### Evidence and limits

Injection harness (REV scratch evidence (not published): `injection.py`) · Injection results (REV scratch evidence (not published): `injection-results.json`) · Focused tests (REV scratch evidence (not published): `focused-tests.log`) · Production build (REV scratch evidence (not published): `build.log`) · Inventory (REV scratch evidence (not published): `inventory.json`) · CI log (REV scratch evidence (not published): `ci.log`) · Installer tests (REV scratch evidence (not published): `installer-tests.log`) · Tools tests (REV scratch evidence (not published): `tools-tests.log`)

The initial installer test invocation lacked `PYTHONPATH=installer` and failed imports; the corrected complete run produced the recorded 639-test result. An early focused Node test invocation preceded completion of dependency installation; the recorded 172-test run was performed after installation completed.

No Docker command or grdm-dev stack change, runtime/.env access, push, commit, merge, approval or closure was performed. Image vulnerability counts, arm64 image startup/memory measurements and Docker browser smoke results remain author evidence. The reviewer independently checked source, upstream patches, an instrumented local production build, fixtures, installer tests and GitHub CI logs. The pre-existing collections engine's localhost URL remains outside this four-commit scope.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**PASS。新たな修正必須事項は見つかりませんでした。** R1-01（HTML 注入）、R1-02（配信依存の評価）、R1-03（installer と仕様の不一致）は、確認した既定の静的ビルドについて解消しています。この判定はレビュー結果であり、GitHub の approve やマージ許可ではありません。

対象は `4602cd081`（描画）、`1cadf7e33`（Node ラッパー）、`fd3d57554`（セキュリティ修正移植）、`0246b5a3b`（test ターゲット）の四コミットです。installer patch の SHA-256 は `3b206cfa31988ca0a0bf37b17a695bee000ec496168031b426c20ae390983999` です。

### 描画と回帰確認

`docker/static/render.sh` は描画前に各環境変数の値全体を検査します。ASCII 許可集合で制御文字、Unicode の区切り、引用符、markup、percent escape を拒否し、項目別の形式と長さで URL と cookie domain を制限します。置換する七つの値はすべて URI エンコード（HTML 属性内で安全に表せる文字列への変換）されます。描画に失敗すると `entrypoint.sh` は nginx を起動せず終了します。

独立した試験では、U+2028/U+2029、U+0085、改行しない空白、全角引用符、符号化・二重符号化した CR/LF、両引用符、`</script>`、JavaScript scheme、制御文字、長すぎる値を、六つの URL 変数、cookie domain、二つの CSP 設定に与えました。不正入力 199 件はすべて終了 1 で拒否され、既存出力の全バイトが維持されました。正常 URL 三件は、2000 文字境界と port 00001/65535 を含めて完全に復元できました。既存 renderer テストは初回出力が作られないことも確認しています。

postbuild の独立 fixture 七件では、正常入力、設定の外にある raw/encoded placeholder、別 asset 内の placeholder、placeholder 不足、重複設定タグを確認し、すべて期待どおりでした。実際の本番出力も postbuild と描画を通過し、既定 backend URL と Google Analytics adapter の不在を確認しました。nginx が配信しない別ファイルだけを描画するという前回の懸念も解消しています。

### 配信依存と上流比較

新しい scratch clone に frozen lockfile で依存を入れ、Node 24.22.2 で本番出力を作りました。棚卸し用の名前を残すため、scratch 内だけで webpack の `optimization.namedModules` を有効にしました。これは検査用の本番ビルドであり、リリースイメージとバイト単位で同一の成果物ではありません。JavaScript 30 ファイルから名前付きパッケージ 18 個を抽出しました。提供された lockfile 報告の CRITICAL 2 / HIGH 51 のパッケージ名は、その名前付きモジュールには直接現れませんでした。vendor import と事前に束ねられた内部依存は別途調べました。

- **sanitize-html 1.20.0:** `ember-cli-sanitize-html` が `dist/sanitize-html.js` を vendor.js に入れ、collections が provider description を渡します。移植ループは [上流 2.7.1 の b4682c12](https://github.com/apostrophecms/sanitize-html/blob/b4682c12fd30e12e82fa2d9b766de91d7d2cd23c/index.js#L615) と同じ処理です。配信 vendor には新しい indexOf ループがあり、旧コメント正規表現はありません。ブラウザ版を直接実行して偽装 JavaScript URL の除去を確認し、未終端コメント開始を五万回繰り返す二十万文字の入力は今回約 9.4 ms でした。
- **keen-dataviz 2.0.10 内の d3-color:** 二つの数値パターンは [上流 3.1.0 の 7a1573ed](https://github.com/d3/d3-color/blob/7a1573ed260de4fd97d061975244841132adde92/src/color.js#L8) と一致します。analytics engine の vendor 出力では新パターン二件、旧パターン零件でした。回帰試験は正常な色と長い不正入力も確認しています。
- **keen-tracking 2.0.10 内の js-cookie 2.1.0:** 配信物に残るので、修正済みではなくリスク受容です。出力設定の `Keen.environments` は空配列でした。アプリは同ライブラリの cookie / auto-tracking API を呼ばず、cookie 操作には Ember のサービスを使います。Keen 除去または Ember 3.28 移行 PR までという受容範囲は、この既定成果物について妥当です。Keen の有効化や cookie / auto-tracking 呼出の追加時には再評価が必要です。
- **sanitize-html 内の PostCSS:** ブラウザコードであり、一律にビルド専用とは扱いません。同梱 `fs` は空で、source map のファイル読取分岐は `existsSync` を検査するため、報告されたファイル読取の脆弱性はこのブラウザ版では到達しません。その他のツール依存は確認したブラウザ import 経路に見つかりませんでした。lockfile の指摘は残り、依存スキャンが無指摘になったとは判定していません。

修正対象の依存五ファイルは移植スクリプトを再実行しても変わりませんでした。ブラウザ修正と描画のテストもローカルで成功しました。上流コードは GitHub API の読取で取得しました。

### CI・test ターゲット・installer

指定 head の二つの CI check は成功です。独立取得した run `43017266950` のログで、Node 8.17.0 から固定版 24.22.2 の取得、SHA-256 検証成功、node-tests 393 件成功・265 件 pending、Ember 978 件完了・skip 記号四件を確認しました。Node 24 のローカル確認では util shim と空白を含む引数の保持も通りました。workflow 自体を Node 24 に変更することは後続作業として妥当です。

Docker test の CMD は七つの placeholder 環境変数をすべて外します。その `env -u` 列で設定読込を実行し、環境変数のない状態と同じ test 用 OSF 設定に戻ることを確認しました。レビュワ自身は Docker test image を再ビルドしていません。

installer patch は `eb8c4e9` の隔離 clone に正常適用できました。静的 entrypoint を維持し、uid 101、`/tmp` tmpfs、書込 dist volume なし、HTTP 200 を要求する `/healthz` 検査となります。SPEC-01、SPEC-02、環境ガイドは英和で整合しています。初期化サービス込みで再計算すると core 8320 MiB（70% 予算で 11.607 GiB）、full/fakecas 9344 MiB（13.036 GiB）、full/shibboleth 9664 MiB（13.482 GiB）でした。これは計算上の下限であり、ビルド・実行時のピーク実測値ではありません。マージ後に一時的な PR head の固定先を統合コミットへ移す必要は、パッチ自身に記載されています。

レビューでの確認結果:

```toon
checks[10]{check,result}:
  独立不正入力,199件を出力変更なしで拒否
  独立正常値往復,3件成功
  独立postbuild_fixture,7件成功
  rendererと修正移植テスト,172件成功
  検査用本番ビルド,Node24.22.2で成功
  実成果物postbuildと描画,成功
  installerテスト,639件実行でskip10と失敗0
  toolsテスト,93件成功
  manifest_check,合格
  docs_check,154件検査と例外8件と警告38件
```

### 証拠と限界

Injection harness (REV scratch evidence (not published): `injection.py`) · Injection results (REV scratch evidence (not published): `injection-results.json`) · Focused tests (REV scratch evidence (not published): `focused-tests.log`) · Production build (REV scratch evidence (not published): `build.log`) · Inventory (REV scratch evidence (not published): `inventory.json`) · CI log (REV scratch evidence (not published): `ci.log`) · Installer tests (REV scratch evidence (not published): `installer-tests.log`) · Tools tests (REV scratch evidence (not published): `tools-tests.log`)

最初の installer テスト実行は `PYTHONPATH=installer` が無く import に失敗しました。修正した全件実行が記載の 639 件です。また、初回の対象 Node テストは依存導入の完了前に実行されました。記載の 172 件は導入完了後の再実行結果です。

Docker コマンド、grdm-dev stack の変更、runtime/.env の参照、push、commit、merge、approve、close は行っていません。イメージの脆弱性件数、arm64 イメージの起動・メモリ実測、Docker ブラウザ smoke の結果は作者の証拠として扱います。レビュワが独立確認したのは、ソース、上流修正、検査用ローカル本番ビルド、fixture、installer 試験、GitHub CI ログです。既存の collections engine の localhost 固定 URL は、この四コミットの対象外です。
