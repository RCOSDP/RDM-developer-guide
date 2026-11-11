# REV-PR3 Render link review r1 / render リンクのレビュー r1

> **Summary:** Review of RDM-ember-osf-web-dev2027 PR #3 at b1e2ad32, covering URL construction, the renderer trust boundary, compatibility, regression tests, and CI.
> **概要:** RDM-ember-osf-web-dev2027 PR #3 の b1e2ad32 を対象に、URL の組み立て、表示サービスの信頼境界、互換性、回帰試験、CI を確認した記録。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** Preserving the API-selected renderer and encoding only added values keeps the internal download destination intact; renderer configuration remains a security trust boundary. ／ API が選ぶ表示サービスを保ち、追加する値だけを符号化すれば、内部の取得先を変えずに済む。表示サービスの設定は引き続きセキュリティの信頼境界となる。
- Applies to / 対象: RDM-ember-osf-web-dev2027 PR #3, review r1.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Related / 関連: SPEC-06 Documentation Conventions; RDM-osf.io-dev2027 PR #14; [English evidence](#evidence-english) / [日本語の証拠](#evidence-japanese).
- Used by / 利用先: PR #3 integration decision and the combined PR #14 deployment check / PR #3 の統合判断と PR #14 と合わせた配備確認。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Scope and decision

**PASS.** No blocking code finding. Both required CI runs completed successfully for the unchanged reviewed head. CI means the automated checks run by GitHub. The pull-request run was awaited through completion; the final green result was verified on 2026-11-12 JST.

The review covered all seven changed files and the PR description. Server code was read only to establish the contract consumed by this client; this record does not replace the separate review of RDM-osf.io-dev2027 PR #14. No merge, approval, close, push, or commit was performed. No running development-stack container was changed, and `runtime/.env` was not read.

```toon
review:
  repository: RDM-ember-osf-web-dev2027
  pull_request: 3
  branch: fix/file-renderer-render-link
  head: b1e2ad328c4dfed47b680c77500cb3deb638c935
  base_implementation: d3caa8a
  round: r1
  blocking_code_findings: 0
```

### URL construction and trust

`lib/osf-components/addon/components/file-renderer/component.ts`, lines 34–53 and 101–106, preserves the API-provided MFR address. MFR is the service that turns a file into a browser preview. The client does not check its host against an allow-list and does not reject a scheme in the helper. A deliberately supplied foreign `links.render` therefore remains foreign and receives `view_only`. This is an explicit trust boundary, not proof that an ordinary file owner can supply such a link.

On the server, `api/files/serializers.py` constructs `links.render` using `get_mfr_url`; `addons/base/utils.py` selects the configured `MFR_SERVER_URL` or `Region.mfr_url`. The region field is a server URL setting, the region API exposes list/retrieve operations, and the region administration is in `addons/osfstorage/admin.py`. The reviewed construction does not use a file name, the caller's host, or a caller-supplied `url` to choose MFR. No ordinary-user path to replace that host was found. The classic server-rendered UI already trusts the same region setting, including loading its MFR script. An API or privileged renderer-configuration compromise is outside this client's protection.

The ordinary Ember `src` binding is retained, with no HTML-safe string bypass. The installed Ember 3.16 runtime includes `IFRAME`/`src` in URL sanitization and prefixes `javascript:` and `vbscript:` with `unsafe:`. An independent browser test confirmed that the actual iframe `src` becomes `unsafe:javascript:window.__reviewProbe=1`. A second browser test confirmed that a crafted token remains one outer query value without changing the nested destination. This does not constitute a general host allow-list or validation of every URL scheme.

The added token is encoded by jQuery `param`; the added version suffix is encoded before it joins the existing `url` value. A token containing ampersands, a second `url`, `javascript:`, a fragment marker, quotes, and angle brackets stayed one outer query value in the independent probes. It did not change either destination or create another `url` parameter.

### View-only access and versions

A view-only token is a secret that grants read access through a shared link. Sending it to a configured, trusted MFR is necessary for MFR to retrieve a private shared file. The old API download link already included the request's `view_only`, so the old nested download URL could disclose the token to the configured MFR as well. The new code puts it explicitly on MFR's outer query, preserves an existing outer token, and can send it to a region-specific MFR instead of the single client-configured MFR. The disclosure is acceptable under the existing trusted-renderer model; it is not byte-for-byte identical to the old behavior. Actual view-only rendering against the combined deployed services remains untested here.

For the server's single-encoded download URL, `/\?|%3F/i` detects the query separator without decoding the entire value. It handles literal `?`, uppercase/lowercase `%3F`, no existing query, and a literal encoded question mark in a path (`%253F` in the outer value). An invalid percent sequence does not throw `URIError`. Existing outer parameters and the outer fragment remain unchanged. The version is added only inside `url`, and changing the selected version recomputes from the original render link rather than accumulating old versions.

The helper is not a general URL normalizer. A pre-existing inner version is not replaced, and an inner fragment would put an appended version after that fragment. The file-detail API contract used by this caller supplies a fragment-free, unversioned render target, so neither case is a demonstrated regression in this PR. The implementation also preserves the old truthy-version behavior.

### Compatibility and test quality

When `links.render` is absent, the original `links.download` plus `?direct=&mode=render` construction remains intact. That includes the old limitation for a download URL that already contains a query; this PR does not repair it. A string or `{ href }` render link works, a render link alone creates the iframe, and neither link creates no iframe. Delaying `src` until the iframe load event remains unchanged. The Mirage serializer supplies render links for files and omits them for folders.

The committed additions contain seven component tests and one acceptance test. The acceptance test exercises the actual page-to-component binding using Mirage's render link, while the component tests cover selecting the internal target, the link object, version changes, token encoding and preservation, fallback, and the absent-link state. With the added tests and Mirage serializer retained, reverting only the component and both templates to the parent implementation made exactly six of the added tests fail: five component tests and one acceptance test. Three failures showed the wrong download-based URL and three showed the missing render-only iframe. The fallback and absent-link compatibility tests still passed.

Non-blocking follow-up: add the no-query, lowercase encoding, malformed-percent, and dangerous-scheme cases to the committed tests. The independent checks cover them for this review, but the new regex's malformed-percent motivation is not itself locked down by a committed test.

<a id="evidence-english"></a>
### Evidence and remaining work

The unmodified head passed all 26 focused tests in `tests/integration/components/file-renderer/component-test.ts` and `tests/acceptance/guid-file/file-detail-test.ts`. The old-implementation comparison completed 26 tests with six expected failures. Two additional scratch-only browser security tests passed. Twelve independent probes executed the actual TypeScript helper and URL utilities after transpilation, with the locked jQuery dependency; all passed. The scratch-only test file was removed and tracked source files were restored to the reviewed head. The push workflow log confirms that the final head, including the regex change, completed the full 986-test suite successfully, resolving the PR description's earlier full-suite caveat. The completed pull-request log also records 986 tests complete, with 393 Node-side tests passing.

```toon
ci[2]{event,run,head,result,completed_utc}:
  push,43054327572,b1e2ad328c4dfed47b680c77500cb3deb638c935,success,2026-11-11T16:17:32Z
  pull_request,43054392861,b1e2ad328c4dfed47b680c77500cb3deb638c935,success,2026-11-11T16:41:24Z
```

The local checks ran in an independent scratch clone with Node 26.12.0, Yarn 1.22.22, and Chrome 157.0.8103.50; the remote workflow used Node 24.22.2 for build/test through the repository wrapper. No local result is presented as a live-stack test. After PR #14 and this client change are deployed together, verify a public file, a private view-only file, and a selected historical version in the real Ember UI.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 範囲と判定

**PASS。** 阻害するコード上の指摘はない。対象 head が変わっていないことを確認し、必要な CI の両実行が成功して完了した。CI は GitHub が自動で行う検査である。pull_request の実行は完了まで待ち、2026-11-12 JST に全緑を確認した。

変更された 7 ファイルと PR 本文を確認した。サーバーのコードは、このクライアントが受け取る契約を確認する範囲で読んだ。RDM-osf.io-dev2027 PR #14 の別のレビューを置き換える記録ではない。merge、approve、close、push、commit は実行していない。稼働中の開発スタックのコンテナを変更せず、`runtime/.env` も読んでいない。

```toon
review:
  repository: RDM-ember-osf-web-dev2027
  pull_request: 3
  branch: fix/file-renderer-render-link
  head: b1e2ad328c4dfed47b680c77500cb3deb638c935
  base_implementation: d3caa8a
  round: r1
  blocking_code_findings: 0
```

### URL の組み立てと信頼境界

`lib/osf-components/addon/components/file-renderer/component.ts` の 34–53 行と 101–106 行は、API が返した MFR のアドレスを保つ。MFR は、ファイルをブラウザで見られる形に変えるサービスである。クライアントにはホストの許可リストとの照合がなく、補助関数も URL のスキームを拒否しない。意図的に外部ホストの `links.render` を渡せば、そのホストが保たれ、`view_only` も送られる。これは明示的な信頼境界であり、通常のファイル所有者がそのリンクを指定できることを意味しない。

サーバーの `api/files/serializers.py` は `get_mfr_url` で `links.render` を組み立てる。`addons/base/utils.py` は、設定済みの `MFR_SERVER_URL` または `Region.mfr_url` を選ぶ。リージョンの値はサーバー側の URL 設定で、リージョン API は一覧・取得のみを公開し、その管理画面は `addons/osfstorage/admin.py` にある。確認した生成処理は、ファイル名、呼出元のホスト、呼出元が渡した `url` で MFR を選ばない。通常利用者がホストを置き換える経路は見つからなかった。従来のサーバー側画面も、同じリージョン設定を信頼し、その MFR スクリプトまで読み込んでいる。API または権限のある表示サービス設定が侵害された場合、このクライアントは防御境界にならない。

通常の Ember の `src` バインディングが維持され、HTML 安全文字列として検査を迂回する処理はない。導入される Ember 3.16 の実装は `IFRAME`/`src` を URL 検査の対象にし、`javascript:` と `vbscript:` に `unsafe:` を付ける。独立したブラウザ試験で、実際の iframe の `src` が `unsafe:javascript:window.__reviewProbe=1` になることを確認した。もう一つのブラウザ試験では、細工したトークンが外側の一つのクエリ値に収まり、内側の取得先を変えないことを確認した。 これは一般的なホスト許可リストや、あらゆるスキームの検証ではない。

追加するトークンは jQuery の `param` で符号化される。追加する版の接尾辞も、既存の `url` 値へつなぐ前に符号化される。独立検査では、アンパサンド、二つ目の `url`、`javascript:`、フラグメント記号、引用符、山括弧を含むトークンが、外側の一つのクエリ値に収まった。取得先を変えたり、二つ目の `url` パラメーターを作ったりすることはなかった。

### 閲覧専用アクセスと版

閲覧専用トークンは、共有リンクからの読み取りを許す秘密の値である。MFR が非公開の共有ファイルを取得するには、信頼する設定済み MFR に送る必要がある。旧 API の download リンクにもリクエストの `view_only` が入るため、旧実装でも入れ子の取得 URL を通して、設定済み MFR にトークンが渡り得た。新実装は MFR の外側のクエリに明示して置き、既存の外側のトークンを保ち、クライアントに設定した一つの MFR の代わりにリージョン別 MFR へ送る場合がある。既存の「信頼する表示サービス」という前提では妥当だが、旧動作と完全に同一ではない。組み合わせて配備した実サービスでの閲覧専用表示は、ここでは検証していない。

サーバーが一重に符号化する取得 URL について、`/\?|%3F/i` は値全体を復号せずクエリ区切りを検出する。生の `?`、大小文字の `%3F`、既存クエリのない場合、パスに含まれる符号化済み疑問符（外側の値では `%253F`）に対応する。不正なパーセント列でも `URIError` は発生しない。外側の既存パラメーターとフラグメントは変わらない。版は `url` の中だけに加わり、選択する版を変えると元の render リンクから再計算され、古い版が累積しない。

この補助関数は、汎用の URL 正規化処理ではない。内側の既存の版を置換せず、内側にフラグメントがあれば追加した版はその後ろに入る。この呼出元が使うファイル詳細 API の契約では、版もフラグメントもない取得先を渡すため、どちらもこの PR の回帰とは確認できない。版の真偽値で追加の有無を決める従来動作も維持される。

### 互換性と試験の質

`links.render` がなければ、旧来の `links.download` と `?direct=&mode=render` を組み合わせる処理を維持する。download URL に既にクエリがある場合の旧来の制約も残り、この PR はそこを修正しない。文字列と `{ href }` の render リンクに対応し、render リンクだけでも iframe を作り、両方のリンクがなければ iframe を作らない。iframe の load イベントまで `src` を遅延させる動作も変わらない。Mirage の serializer はファイルに render リンクを返し、フォルダーには返さない。

追加された試験は component 7 件と受入 1 件である。受入試験は Mirage の render リンクを使い、実際の画面から component への受け渡しを確認する。component 試験は、内部の取得先の選択、リンクオブジェクト、版の変更、トークンの符号化・維持、フォールバック、両リンクのない状態を確認する。追加試験と Mirage の serializer を残し、component と二つの template だけを親の実装に戻すと、追加試験のうちちょうど 6 件（component 5 件、受入 1 件）が失敗した。3 件は download 由来の誤った URL、3 件は render リンクだけの場合に iframe がないことを検出した。フォールバックと両リンクなしの互換性試験は成功した。

非阻害の改善案として、クエリなし、小文字の符号化、不正なパーセント列、危険なスキームのケースを、コミットされる試験に加えるとよい。今回の独立検査では確認したが、正規表現に変更した理由である不正なパーセント列は、追加された試験自体では固定されていない。

<a id="evidence-japanese"></a>
### 証拠と残る作業

未変更の対象 head で、`tests/integration/components/file-renderer/component-test.ts` と `tests/acceptance/guid-file/file-detail-test.ts` の対象試験 26 件がすべて成功した。旧実装との比較は 26 件を完了し、想定どおり 6 件が失敗した。scratch だけに追加したブラウザ安全性試験 2 件も成功した。独立検査 12 件では、実際の TypeScript の補助関数と URL ユーティリティを変換して実行し、固定された jQuery 依存を使い、すべて成功した。scratch 専用の試験ファイルを削除し、追跡対象のソースはレビュー対象 head に戻した。push workflow のログで、正規表現への変更を含む最終 head の全体試験 986 件が成功して完了したことを確認できたため、PR 本文にあった直前版だけの全体試験という留保は解消している。完了した pull_request のログでも、全体試験 986 件の完了と Node 側試験 393 件の成功を確認した。

```toon
ci[2]{event,run,head,result,completed_utc}:
  push,43054327572,b1e2ad328c4dfed47b680c77500cb3deb638c935,success,2026-11-11T16:17:32Z
  pull_request,43054392861,b1e2ad328c4dfed47b680c77500cb3deb638c935,success,2026-11-11T16:41:24Z
```

ローカル検査は独立した scratch clone で、Node 26.12.0、Yarn 1.22.22、Chrome 157.0.8103.50 を使った。リモートの workflow は、リポジトリのラッパー経由で build/test に Node 24.22.2 を使った。ローカル検査を実スタックの検証として扱っていない。PR #14 とこの変更を合わせて配備した後、公開ファイル、非公開ファイルの閲覧専用リンク、選択した過去版を実際の Ember 画面で確認する必要がある。
