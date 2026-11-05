# ADR-06 Wiki Frontend Overlay / Wiki フロントエンドのオーバーレイ

> **Summary:** The `wiki-frontend` repository is not a service. Its Dockerfile is a copy of osf.io's that COPYs osf.io paths which the wiki-frontend checkout does not contain, so building it alone fails (real install run 4). We treat it as an *overlay*: its files are copied over the osf.io checkout and the osf.io image is built from the overlay's Dockerfile, which bundles the wiki editor with webpack 5. One image, tagged with both commits; no `wiki` Compose service.
> **概要:** `wiki-frontend` リポジトリはサービスではない。その Dockerfile は osf.io のものの写しで、wiki-frontend の checkout には無い osf.io のパスを COPY するため、単独では組めない（実機第 4 回）。これを「オーバーレイ」として扱う。ファイルを osf.io の checkout の上に重ね、オーバーレイ側の Dockerfile で osf.io のイメージを組む。その Dockerfile は Wiki エディタを webpack 5 で束ねる。イメージは一つで、両方のコミットをタグに持つ。Compose サービス `wiki` は無い。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a repository with a Dockerfile is not necessarily a buildable component: the fourth real install on Mac Studio failed at the first `COPY ./addons/*/requirements.txt` of the wiki-frontend Dockerfile, because that file is osf.io's Dockerfile with the Python steps commented out and the checkout contains only `addons/wiki`, `website/static`, `package.json`, `yarn.lock`, two webpack configs and the Dockerfile. The manifest needs a way to say "this repository is applied on top of that one" (`overlay_of`), and the installer must build one image from the merged tree. ／ Dockerfile があるリポジトリが必ず組める部品とは限らないと分かった。Mac Studio での第 4 回実導入は wiki-frontend の Dockerfile の最初の `COPY ./addons/*/requirements.txt` で止まった。そのファイルは osf.io の Dockerfile から Python の手順をコメントアウトした写しで、checkout には `addons/wiki`、`website/static`、`package.json`、`yarn.lock`、webpack 設定 2 本、Dockerfile しか無い。manifest には「このリポジトリはあのリポジトリの上に重ねる」と書く手段（`overlay_of`）が要り、インストーラーは重ねた木から一つのイメージを組まねばならない。
- Status: Proposed for the owner's approval, 2026-11-06 (M2). Review date: start of M4, together with the `prebuilt_image` fallbacks.
- Records a decision for: [SPEC-01 §3](../spec/01_manifest.md#english) (`overlay_of`, image tag rule, MC-14) · [SPEC-02 §4](../spec/02_installer_cli.md#2-en-ports) (no `wiki` service) · [SPEC-00 §2](../spec/00_overview.md#english)
- Related: [docs/README.md](../README.md) · [ADR-01 Integration repository placement](ADR-01_Integration_Repository_Placement.md) · [ADR-02 Network Model](ADR-02_Network_Model.md) · [DEMO-20 Core install on Mac Studio](../demo/20_core_install_mac_studio.md) · [REF-01 Glossary](../reference/REF-01_Glossary.md) · `installer/grdm_dev/build.py` · `tools/manifest_check.py`

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

The manifest ([SPEC-01](../spec/01_manifest.md#english)) listed `wiki-frontend` as a core component with one Compose *service* (a container that Compose starts) named `wiki`, and the installer tried to build it like every other core: clone `RDM-wiki-frontend-dev2027` at the pinned commit and run `docker buildx build` on that checkout.

The fourth real install on Mac Studio (2026-11-06, [DEMO-20](../demo/20_core_install_mac_studio.md)) stopped at `build` with exit 30: *image build failed — component wiki-frontend: docker buildx build exited 1*. BuildKit reported, for dozens of `COPY` lines at once, `failed to calculate checksum ... "/addons/metadata/static": not found`, `"/addons/gitlab/requirements.txt": not found`, `"/addons/zotero/static": not found` and so on.

Reading the two repositories side by side explains it:

- The wiki-frontend checkout contains only `addons/wiki/static/` (the Milkdown editor: `wikiPageMilkdown.js`, `heading.js`, `image.js`, `link.js`, ...), `website/static/js/` (`wikiTree.js`, `fangorn.js`, `pages/wiki-edit-page.js`), `website/static/vendor/knockout-sortable`, `package.json`, `yarn.lock`, `webpack.common.config.js`, `webpack.prod.config.js`, `Dockerfile`, `.jshintrc`, `.travis.yml` and a one-line `README.md`: "This is RDM wiki code for bundle with webpack5".
- Its `Dockerfile` is osf.io's Dockerfile with small edits: `FROM node:21-alpine` instead of `node:12-alpine3.9`, every Python/`pip`/`collectstatic`/`pybabel` step commented out, the admin `yarn install` commented out, and `yarn run webpack-prod` left in. It still `COPY`s `./requirements.txt`, `./addons/<name>/requirements.txt` for twenty-odd add-ons, `./admin/package.json ./admin/yarn.lock`, `./website/settings/`, `./api/base/settings/`, and `./addons/<name>/static/` for every add-on. None of these exist in the wiki-frontend tree; all of them exist in `RDM-osf.io-dev2027`.
- Its `package.json` keeps the name `osf` and version `20.14.0` of osf.io and upgrades `webpack` from `3.8.1` to `^5.93.0` (plus `webpack-cli` 5, `terser-webpack-plugin` 5, `assets-webpack-plugin` 7 and the `@milkdown/*` 7.3.6 editor packages). `webpack.common.config.js` keeps a single entry, `wiki-edit-page`, where osf.io's config lists forty pages, and drops the add-on entry discovery; `webpack.prod.config.js` replaces `UglifyJsPlugin` and `CommonsChunkPlugin` (webpack 3) with `TerserPlugin` and `optimization.splitChunks` (webpack 5).

So `wiki-frontend` is a *patch set* for the osf.io source tree: a newer Node base, webpack 5 and the Milkdown editor files, meant to be laid over osf.io before the image is built. It has no process of its own to run; the resulting image is the osf.io image whose wiki editor bundle was built with webpack 5. The `wiki` service that the installer invented (port 3000, `NODE_ENV=development`) had nothing to start. Its real-time counterpart, `y-websocket` (the Yjs WebSocket server for co-editing), is a separate repository with its own server and stays a service.

### 2. Options considered

```toon
options[3]{id,option,builds_today,honest_about_contents,fits_spec01,verdict}:
  A,"Separate `wiki` service built from the wiki-frontend checkout (status quo)","no (COPY of osf.io paths fails on the first step)","no (there is no wiki server to run)",no,"impossible; rejected"
  B,"Overlay: copy the wiki-frontend files over the osf.io checkout, build the osf.io image from the overlay's Dockerfile, tag with both commits","yes (the merged tree has every COPY source)","yes (image = osf.io@sha + wiki-frontend@sha, both pinned)","yes (one new field `overlay_of`, build from pinned source kept)",chosen
  C,"Prebuilt osf.io image from a registry, pinned by digest (like ember-osf-web and cas-overlay until M4)","yes","no (nobody can show which commits are inside; and the osf.io image is the one image we must build from source)","no (bypasses the build-from-pinned-source guarantee for the central component)",rejected
```

Option C would have hidden the problem: the whole point of the integration repositories ([ADR-01](ADR-01_Integration_Repository_Placement.md)) is that the central `osf.io` image is built from pinned commits that we can name. A prebuilt fallback is tolerable for a login server or an Ember front end until M4; it is not acceptable for `osf.io` itself.

### 3. Decision

1. **Manifest.** A component may carry `overlay_of: "<base id>"` ([SPEC-01 §3](../spec/01_manifest.md#english)). It keeps its own `integration_repo`, `integration_sha`, `upstreams[]` and PR lists, so the weekly integration PR and the upstream tracking ([SPEC-05](../spec/05_upstream_tracking.md)) work unchanged. Its `services[]` is empty; its `profile` equals the base's, because the overlay is inside every base image. `wiki-frontend` gets `overlay_of: "osf.io"`, `services: []`, `profile: minimum` and a `note`.
2. **Checker.** `grdm-dev manifest check` adds MC-14: the base exists, is not `infra`, is not an overlay and has no `prebuilt_image`; the overlay is not `infra`, has no `prebuilt_image` or `build_platform` of its own, has no services and shares the base's profile; a base takes at most one overlay. MC-03 allows an empty `services[]` only for an overlay.
3. **Build.** `grdm-dev build` never builds the overlay alone and never builds the base without it. After both checkouts are synced at their pinned commits, `runtime/src/_overlay/<overlay id>/` is recreated as a copy of the base checkout without `.git`, the overlay checkout's files are copied over it without `.git` (the overlay's version wins where both have a file: `Dockerfile`, `package.json`, `yarn.lock`, the webpack configs, `addons/wiki/static/*`), and one `docker buildx build -f <context>/Dockerfile <context>` runs. `--component wiki-frontend` builds `osf.io` with the overlay and says so.
4. **Image tag.** The base image is `grdm-dev/<base>:<base_sha12>-<overlay_sha12>` (with `--push`, `ghcr.io/rcosdp/<base>:<same tag>`). Both commits are visible in the tag and in the labels `org.gakunin-rdm.overlay` and `org.gakunin-rdm.overlay-sha`. The build report row of the base carries `overlay`, `overlay_repo`, `overlay_sha12` and `image_tag`; `compose render` reads `image_tag`.
5. **Compose and plan.** `web`, `api`, `admin` and `worker` run the overlay-tagged image. `plan` and `compose render` show `origin: overlay` and `build_from: RDM-osf.io-dev2027@<sha12> + RDM-wiki-frontend-dev2027@<sha12> (overlay of osf.io: wiki-frontend)` for them. The `wiki` service template is deleted; [SPEC-02 §4](../spec/02_installer_cli.md#2-en-ports) no longer lists `wiki` in `core` and says that the wiki editor is part of the osf.io image.

### 4. Consequences

- The osf.io image used by `web`, `api`, `admin` and `worker` is always the overlay build. Changing either repository changes the tag, so `compose render` picks up a new wiki editor the same way it picks up a new osf.io commit.
- The `wiki-frontend` component contributes no Compose service, no port and no hardening exception; the acceptance scenario C4 (Wiki collaborative edit, [SPEC-04 §4](../spec/04_acceptance_tests.md#english)) exercises `web`, `y_websocket` and `sharejs`, as before.
- `y-websocket` stays a separate service (`y_websocket`, profile `core`): it is a server, not a patch set.
- The build takes the osf.io image through the wiki-frontend Dockerfile, which skips the Python installation and `collectstatic`. Whether the resulting image serves `api`/`admin`/`worker` correctly, or whether the legacy guide ran the overlay build only as a front-end step, is checked in the next real install run and recorded in [DEMO-20](../demo/20_core_install_mac_studio.md); the M4 Dockerfile modernization (`target_image.M4`) is the place to fold the overlay into osf.io's own build if that proves necessary.
- Review at M4: when osf.io's Dockerfile is modernized, decide whether `wiki-frontend` stays an overlay or is merged into the osf.io repository; the `overlay_of` mechanism remains available for any other repository of the same shape.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

manifest（[SPEC-01](../spec/01_manifest.md#japanese)）は `wiki-frontend` をコア部品とし、`wiki` という Compose の「サービス」（Compose が起動するコンテナ）を一つ持たせていた。インストーラーはほかのコアと同じに、`RDM-wiki-frontend-dev2027` を固定コミットで clone し、その checkout で `docker buildx build` を走らせようとした。

Mac Studio での第 4 回実導入（2026-11-06、[DEMO-20](../demo/20_core_install_mac_studio.md)）は `build` で終了 30 になった。「image build failed — component wiki-frontend: docker buildx build exited 1」。BuildKit は何十行もの `COPY` について一度に `failed to calculate checksum ... "/addons/metadata/static": not found`、`"/addons/gitlab/requirements.txt": not found`、`"/addons/zotero/static": not found` などを報告した。

二つのリポジトリを並べて読むと理由が分かる。

- wiki-frontend の checkout にあるのは `addons/wiki/static/`（Milkdown エディタ: `wikiPageMilkdown.js`、`heading.js`、`image.js`、`link.js` など）、`website/static/js/`（`wikiTree.js`、`fangorn.js`、`pages/wiki-edit-page.js`）、`website/static/vendor/knockout-sortable`、`package.json`、`yarn.lock`、`webpack.common.config.js`、`webpack.prod.config.js`、`Dockerfile`、`.jshintrc`、`.travis.yml`、そして一行の `README.md`「This is RDM wiki code for bundle with webpack5」だけである。
- その `Dockerfile` は osf.io の Dockerfile に小さな手を入れたものである。`FROM node:12-alpine3.9` を `node:21-alpine` に、Python・`pip`・`collectstatic`・`pybabel` の手順をすべてコメントアウト、admin の `yarn install` もコメントアウト、`yarn run webpack-prod` は残す。それでも `./requirements.txt`、二十数個のアドオンの `./addons/<name>/requirements.txt`、`./admin/package.json ./admin/yarn.lock`、`./website/settings/`、`./api/base/settings/`、全アドオンの `./addons/<name>/static/` を `COPY` する。どれも wiki-frontend の木には無く、すべて `RDM-osf.io-dev2027` にある。
- `package.json` は osf.io の名前 `osf` と版 `20.14.0` のまま、`webpack` を `3.8.1` から `^5.93.0` に上げている（`webpack-cli` 5、`terser-webpack-plugin` 5、`assets-webpack-plugin` 7、エディタの `@milkdown/*` 7.3.6 も）。`webpack.common.config.js` は osf.io 側の四十ページのエントリを `wiki-edit-page` 一つに絞り、アドオンのエントリ探索を外す。`webpack.prod.config.js` は webpack 3 の `UglifyJsPlugin`・`CommonsChunkPlugin` を webpack 5 の `TerserPlugin`・`optimization.splitChunks` に置き換える。

つまり `wiki-frontend` は osf.io のソースツリーに対する「パッチの束」である。新しい Node ベース、webpack 5、Milkdown エディタのファイルを、イメージを組む前に osf.io の上へ重ねるためのものだ。自分で動かすプロセスは無く、できあがるのは「Wiki エディタの束を webpack 5 で組んだ osf.io のイメージ」である。インストーラーが作っていた `wiki` サービス（ポート 3000、`NODE_ENV=development`）には起動するものが無かった。共同編集の相方 `y-websocket`（Yjs の WebSocket サーバ）は独立したリポジトリで自分のサーバを持つので、サービスのままとする。

### 2. 検討した選択肢

```toon
options[3]{id,option,builds_today,honest_about_contents,fits_spec01,verdict}:
  A,"wiki-frontend の checkout から組む独立サービス `wiki`（現状）","いいえ（osf.io のパスの COPY が最初の段で失敗）","いいえ（動かす wiki サーバが無い）",いいえ,"不可能。却下"
  B,"オーバーレイ: wiki-frontend のファイルを osf.io の checkout に重ね、オーバーレイ側の Dockerfile で osf.io のイメージを組み、両コミットでタグ付け","はい（重ねた木に全 COPY 元がある）","はい（イメージ = osf.io@sha + wiki-frontend@sha、両方固定）","はい（新項目 `overlay_of` 一つ。固定した元から組む保証は保つ）",採用
  C,"レジストリの事前ビルド済み osf.io イメージをダイジェスト固定で使う（M4 までの ember-osf-web・cas-overlay と同じ）","はい","いいえ（中のコミットを誰も示せない。しかも osf.io のイメージこそ元から組むべき唯一のもの）","いいえ（中心部品で「固定した元から組む」保証を外す）",却下
```

C は問題を隠すだけだった。統合リポジトリ（[ADR-01](ADR-01_Integration_Repository_Placement.md)）の眼目は、中心の `osf.io` イメージを名指しできる固定コミットから組むことにある。ログインサーバや Ember の画面なら M4 までの事前ビルド済み代替を許容できるが、`osf.io` 本体には許されない。

### 3. 決定

1. **manifest。** 部品は `overlay_of: "<ベースの id>"` を持てる（[SPEC-01 §3](../spec/01_manifest.md#japanese)）。自分の `integration_repo`、`integration_sha`、`upstreams[]`、PR の一覧はそのまま持つので、週次統合 PR と上流追跡（[SPEC-05](../spec/05_upstream_tracking.md)）は変わらず動く。`services[]` は空。`profile` はベースと同じ（オーバーレイはベースの全イメージの中にある）。`wiki-frontend` には `overlay_of: "osf.io"`、`services: []`、`profile: minimum`、`note` を書く。
2. **検査。** `grdm-dev manifest check` に MC-14 を足す。ベースが存在し、`infra` でなく、オーバーレイでなく、`prebuilt_image` を持たない。オーバーレイは `infra` でなく、自分の `prebuilt_image`・`build_platform` を持たず、サービスが無く、ベースと同じ profile を持つ。ベース一つにオーバーレイは最大一つ。MC-03 は空の `services[]` をオーバーレイにだけ許す。
3. **build。** `grdm-dev build` はオーバーレイを単独で組まず、ベースをオーバーレイ無しで組むこともない。両 checkout を固定コミットで同期した後、`runtime/src/_overlay/<オーバーレイ id>/` をベース checkout の `.git` 抜きの写しとして作り直し、その上にオーバーレイ checkout のファイルを `.git` 抜きで重ね（両方にあるファイル `Dockerfile`、`package.json`、`yarn.lock`、webpack 設定、`addons/wiki/static/*` はオーバーレイ側が勝つ）、`docker buildx build -f <context>/Dockerfile <context>` を一回だけ走らせる。`--component wiki-frontend` は `osf.io` をオーバーレイ付きで組み、そう告げる。
4. **イメージのタグ。** ベースのイメージは `grdm-dev/<ベース>:<ベース sha12>-<オーバーレイ sha12>`（`--push` では `ghcr.io/rcosdp/<ベース>:<同じタグ>`）。両コミットがタグと、ラベル `org.gakunin-rdm.overlay`・`org.gakunin-rdm.overlay-sha` に見える。ビルド報告のベースの行に `overlay`、`overlay_repo`、`overlay_sha12`、`image_tag` を持たせ、`compose render` は `image_tag` を読む。
5. **compose と plan。** `web`・`api`・`admin`・`worker` はオーバーレイのタグのイメージで動く。`plan` と `compose render` はそれらに `origin: overlay` と `build_from: RDM-osf.io-dev2027@<sha12> + RDM-wiki-frontend-dev2027@<sha12> (overlay of osf.io: wiki-frontend)` を示す。サービステンプレート `wiki` は削除し、[SPEC-02 §4](../spec/02_installer_cli.md#2-ja-ports) は `core` に `wiki` を載せず、Wiki エディタが osf.io のイメージの一部だと書く。

### 4. 結果

- `web`・`api`・`admin`・`worker` が使う osf.io のイメージは常にオーバーレイ付きのビルドになる。どちらのリポジトリが変わってもタグが変わるので、`compose render` は新しい osf.io のコミットと同じ仕組みで新しい Wiki エディタを拾う。
- `wiki-frontend` 部品は Compose のサービス、ポート、hardening の例外を一つも持たない。受入シナリオ C4（Wiki 共同編集、[SPEC-04 §4](../spec/04_acceptance_tests.md#japanese)）はこれまでどおり `web`・`y_websocket`・`sharejs` を使う。
- `y-websocket` は独立サービス（`y_websocket`、profile `core`）のまま。サーバであってパッチの束ではない。
- ビルドは osf.io のイメージを wiki-frontend の Dockerfile で通す。その Dockerfile は Python の導入と `collectstatic` を飛ばす。できたイメージが `api`・`admin`・`worker` を正しく動かすか、あるいは旧ガイドがオーバーレイのビルドをフロントエンドの一段としてだけ使っていたのかは、次の実導入で確かめて [DEMO-20](../demo/20_core_install_mac_studio.md) に記録する。必要なら M4 の Dockerfile 近代化（`target_image.M4`）でオーバーレイを osf.io 自身のビルドに取り込む。
- M4 で見直す。osf.io の Dockerfile を近代化する時に、`wiki-frontend` をオーバーレイのまま置くか osf.io のリポジトリに統合するかを決める。`overlay_of` の仕組みは同じ形のほかのリポジトリにも使える。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Overlay | A set of files laid over another repository's tree before the image is built; it has no image or service of its own. | イメージを組む前にほかのリポジトリの木の上に重ねるファイルの組。自分のイメージもサービスも持たない。 |
| Build context | The directory `docker buildx build` reads files from; every `COPY` source must be inside it. | `docker buildx build` がファイルを読む場所。`COPY` の元はすべてこの中に無ければならない。 |
| webpack | The tool that bundles many JavaScript files into the few files a browser downloads; osf.io uses version 3, the overlay version 5. | 多くの JavaScript をブラウザが読む少数のファイルに束ねる道具。osf.io は版 3、オーバーレイは版 5。 |
| Milkdown | The Markdown editor component used by the GRDM wiki pages. | GRDM の Wiki ページが使う Markdown エディタ部品。 |
