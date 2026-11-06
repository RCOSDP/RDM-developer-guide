# PR2 JS dependency sync review r1 / JS 依存同期レビュー r1

> **Summary:** Pass with one non-blocking correction to the verification description. All six dependency changes match osf.io develop, the webpack 5 stack is preserved, and the lock graph has no missing or stale selectors.
> **概要:** 検証説明に軽微な訂正事項1件を付して合格。依存変更6件は osf.io develop と一致し、webpack 5 系を維持し、ロックの依存グラフに欠落・不要な選択子はない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** dependency pruning is justified by graph reachability, while a successful build can still include a configuration warning alongside performance warnings. ／ 依存の削除はグラフの到達性で説明でき、成功したビルドでも性能警告に加えて設定警告が含まれる。
- Applies to: RCOSDP/RDM-wiki-frontend-dev2027 PR #2; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Pass with a non-blocking documentation nit (R1-01). No blocking code findings.** This is a review verdict, not a GitHub approval. Scope is only `package.json` and `yarn.lock`, base `203d32fab60aad8d78e9b743987519252f99b817` to head `ed6f6369efead0528538964fcfdedd3233c4e4b4`. GitHub reports exactly these two changed files. The local wiki base files match the base blobs byte for byte. The supplied local osf.io manifest matches remote develop `356a997eb5fe7d4aa49c05a0bbcf736a3cf1e31f` byte for byte.

### Dependency and lock review

Observed comparisons (review evidence, not canonical manifest data):

```toon
dependencies[6]{name,base,head_and_osfio,locked}:
  bootstrap-datepicker,1.9.0,1.10.1,1.10.1
  highlight.js,~8.4.0,~9.18.2,9.18.5
  less,^2.5.3,^2.7.3,2.7.3
  linkify-html,absent,^4.4.0,4.4.0
  linkifyjs,^2.0.3,^4.4.0,4.4.0
  sift,absent,^17.0.1,17.1.4
```

These are the only manifest changes. No dependency is removed, and all other fields, including development dependencies and scripts, are unchanged. Webpack `^5.93.0`, webpack-cli `^5.1.4`, terser-webpack-plugin `^5.3.10`, assets-webpack-plugin `^7.1.1`, file-loader `^6.2.0`, url-loader `^4.1.1`, the Milkdown packages, Yjs packages and browser shims remain. The six named build-tool lock blocks are identical to base.

A read-only Python inspection parsed every Yarn v1 block and traversed both `dependencies` and `optionalDependencies` from all 118 manifest roots, including development dependencies. All 1,468 selectors in 1,218 blocks are reachable, with zero missing selectors and zero stale selectors. The six new direct resolutions satisfy their declared ranges. The 48 removed selectors follow replacement of the old roots and pruning of their unused branches: linkifyjs 2's optional React/React DOM tree and less 2.7.2's request 2.83 branch. Less 2.7.3 uses the retained request 2.81.0 block. Datepicker now requires jQuery `>=3.4.0 <4.0.0`, satisfied by the retained 3.7.1 resolution; 3.5.1 becomes unused. The only shared selector with changed block contents is jQuery `>= 1.7.2`, which gains an integrity field without changing version or resolved URL.

Both Git dependency declarations and their complete lock blocks are unchanged: dropzone `aba21eb6b82cc823ac7a7a53d6e035791c082bae` and treebeard `d2bb8f6f8104fcac040402727f431c26722b269e`. No webpack-5-specific dependency loss was found.

### Build evidence and R1-01

The supplied `wiki-overlay-test-build.log` under `/private/tmp/claude-501/-Users-komiyama-ai-development-GitHub-RDM-developer-guide/8d9d37a4-fc91-4879-8396-0dc9a3134401/scratchpad/` supports the success claim: step #89 runs Yarn 1.22.19 with `--frozen-lockfile`, completes installation, emits `wiki-edit-page.86ca01eae33ec9d1a99b.js` (5.76 MiB) and `vendor.0da9662a5ff6f2b6b710.js` (2.65 MiB), and reports webpack 5.93.0 compiled with four warnings. Step #91 completes export and unpacking of `grdm-dev/wiki-frontend:deps-test`.

**R1-01 — low, non-blocking:** the PR body calls all four warnings performance recommendations. One is actually the missing webpack `mode` configuration; the other three concern asset size, entrypoint size and performance recommendations. Correct the description to “four webpack warnings: one mode configuration warning and three performance warnings.” Installation also reports peer-dependency warnings, and Docker reports legacy ENV syntax; the build nevertheless completes. No configuration change is requested in this dependency-only PR.

The build claim is plausible, but the log does not attest the exact input commits or explicitly show the requested platform, nor independently prove final filesystem contents. I did not rerun installation or build, inspect the image, change Docker state, or test browser/C4 acceptance. This review confirms static lock consistency and corroborates the supplied build evidence; it does not certify runtime behavior. Only the requested review record and one PR comment are written, without commit, push, approval, merge or closure.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**軽微な説明訂正（R1-01）を付して合格。コードの阻害指摘なし。** GitHub の承認操作ではなくレビュワの判定。対象は base `203d32fab60aad8d78e9b743987519252f99b817` から head `ed6f6369efead0528538964fcfdedd3233c4e4b4` の `package.json` と `yarn.lock` のみ。GitHub 上の変更ファイルもこの2件だけ。ローカル wiki base の両ファイルは base の内容とバイト単位で一致する。指定のローカル osf.io manifest も remote develop `356a997eb5fe7d4aa49c05a0bbcf736a3cf1e31f` とバイト単位で一致する。

### 依存とロックの検査

英語部の6件の比較が全 manifest 差分であり、すべて osf.io develop の指定値と一致する。依存削除はなく、開発依存・scripts を含む他のフィールドは不変。Webpack `^5.93.0`、webpack-cli `^5.1.4`、terser-webpack-plugin `^5.3.10`、assets-webpack-plugin `^7.1.1`、file-loader `^6.2.0`、url-loader `^4.1.1`、Milkdown、Yjs、ブラウザ用補完依存を維持している。列挙した6ビルドツールのロックブロックも base と同一。

読取り専用の Python 検査で Yarn v1 の全ブロックを解析し、開発依存を含む manifest の118起点から `dependencies` と `optionalDependencies` を走査した。1,218ブロックの1,468選択子すべてに到達し、欠落0・不要な選択子0。新しい直接依存6件の解決版も指定範囲内にある。削除された48選択子は、旧起点の置換と不要になった枝の除去で説明できる。linkifyjs 2 の任意依存 React/React DOM 系と、less 2.7.2 の request 2.83 系が主な対象。less 2.7.3 は残存する request 2.81.0 を使う。Datepicker の jQuery 要件は `>=3.4.0 <4.0.0` となり、既存の3.7.1で満たし、3.5.1は不要になる。共通選択子でブロック本文が変わるのは jQuery `>= 1.7.2` のみで、版・取得先を保って integrity を追加している。

Git 依存は宣言とロックの全ブロックがともに不変。dropzone は `aba21eb6b82cc823ac7a7a53d6e035791c082bae`、treebeard は `d2bb8f6f8104fcac040402727f431c26722b269e` のまま。webpack 5 固有依存の欠落は見つからなかった。

### ビルド証跡と R1-01

英語部にパスを記した指定ログは成功主張を裏付ける。#89 で Yarn 1.22.19 の `--frozen-lockfile` によるインストールが完了し、`wiki-edit-page.86ca01eae33ec9d1a99b.js`（5.76 MiB）と `vendor.0da9662a5ff6f2b6b710.js`（2.65 MiB）を出力、webpack 5.93.0 が警告4件で完了する。#91 では `grdm-dev/wiki-frontend:deps-test` の export と unpacking が完了している。

**R1-01 — 軽微・非阻害:** PR 本文は警告4件をすべて性能推奨とするが、1件は webpack の `mode` 未設定。残る3件が asset size、entrypoint size、performance recommendations。「webpack 警告4件（mode 未設定1件、性能関連3件）」へ説明を訂正してほしい。別途、インストール時の peer dependency 警告と Docker の旧 ENV 構文警告もあるが、ビルドは完了する。依存だけを変更するこの PR に設定修正は求めない。

ビルド成功主張は妥当と判断するが、ログだけでは入力コミットの完全一致、指定プラットフォームの明示、最終ファイルシステムの内容までは独立に証明できない。インストール・ビルドの再実行、イメージの調査、Docker 状態変更、ブラウザ/C4 受入試験は行っていない。静的なロック整合と提供ログの裏付けを確認したもので、実行時動作の保証ではない。指定レビュー記録と PR コメント1件だけを書き、commit・push・approve・merge・close は行わない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Overlay | Files placed over another source tree before building. | ビルド前に別のソースの木へ重ねるファイル。 |
| Lock selector | A package name and requested range identifying a locked resolution. | 固定した取得版を指すパッケージ名と要求範囲の組。 |
| Reachability | Whether following dependencies from the manifest can reach a lock entry. | manifest から依存をたどってロック項目へ到達できること。 |
| Frozen lockfile | Installation using the existing lock without rewriting it. | 既存ロックを書き換えず利用するインストール。 |
| Peer dependency | A package another package expects its caller to provide. | 呼び出す側に用意を求める依存パッケージ。 |
| C4 | Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入シナリオ。 |
