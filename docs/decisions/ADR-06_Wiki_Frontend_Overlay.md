# ADR-06 Wiki Frontend Overlay / Wiki フロントエンドのオーバーレイ

> **Summary:** The `wiki-frontend` repository is not a service and not a runtime image. Its Dockerfile is a copy of osf.io's that COPYs osf.io paths the wiki-frontend checkout does not contain (so it cannot be built alone; real install run 4) and that skips every Python step, running only `yarn run webpack-prod` (so its image cannot replace the osf.io image either). We treat it as an *overlay*: its image is built from the osf.io checkout with the wiki-frontend files copied over it, tagged with both commits, and run **once** by the Compose service `wiki_assets`, which copies the webpack output into the named volume `wiki_static`; `web`, `api`, `admin` and `worker` mount that volume read-only. This is the pattern upstream osf.io's own `assets` service uses.
> **概要:** `wiki-frontend` リポジトリはサービスでも実行用イメージでもない。その Dockerfile は osf.io のものの写しで、wiki-frontend の checkout には無い osf.io のパスを COPY する（だから単独では組めない。実機第 4 回）うえ、Python の手順をすべて飛ばして `yarn run webpack-prod` だけを走らせる（だからそのイメージで osf.io のイメージを置き換えることもできない）。これを「オーバーレイ」として扱う。osf.io の checkout に wiki-frontend のファイルを重ねた木からイメージを組み、両コミットをタグに持たせ、Compose サービス `wiki_assets` が **一度だけ** 動かして webpack の出力を名前付きボリューム `wiki_static` へ写す。`web`・`api`・`admin`・`worker` はそのボリュームを読み取り専用で mount する。上流 osf.io 自身の `assets` サービスと同じ型である。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a repository with a Dockerfile is not necessarily a buildable component, and an image that builds is not necessarily a runtime: the fourth real install on Mac Studio failed at the first `COPY ./addons/*/requirements.txt` of the wiki-frontend Dockerfile, and reading that Dockerfile showed it is osf.io's with the Python steps commented out, so the image it would produce holds only a webpack bundle. The manifest needs `overlay_of` ("built from that component's tree plus my files"), and the installer needs one-shot services that move a build output into a volume. ／ Dockerfile があるリポジトリが必ず組める部品とは限らず、組めるイメージが必ず実行環境とも限らないと分かった。Mac Studio での第 4 回実導入は wiki-frontend の Dockerfile の最初の `COPY ./addons/*/requirements.txt` で止まり、その Dockerfile を読むと osf.io のものから Python の手順をコメントアウトした写しで、できるイメージは webpack の束しか持たない。manifest には「あの部品の木に自分のファイルを重ねて組む」を表す `overlay_of` が要り、インストーラーにはビルド成果をボリュームへ移す一回限りのサービスが要る。
- Status: Proposed for the owner's approval, 2026-11-06 (M2). Review date: start of M4, together with the `prebuilt_image` fallbacks.
- Records a decision for: [SPEC-01 §3](../spec/01_manifest.md#english) (`overlay_of`, image tag rule, MC-14) · [SPEC-02 §4](../spec/02_installer_cli.md#2-en-ports) (`wiki_assets`, volume `wiki_static`) · [SPEC-00 §2](../spec/00_overview.md#english)
- Related: [docs/README.md](../README.md) · [ADR-01 Integration repository placement](ADR-01_Integration_Repository_Placement.md) · [ADR-02 Network Model](ADR-02_Network_Model.md) · [SPEC-03 §3](../spec/03_security_gate.md#english) · [DEMO-20 Core install on Mac Studio](../demo/20_core_install_mac_studio.md) · [REF-01 Glossary](../reference/REF-01_Glossary.md) · `installer/grdm_dev/build.py` · `installer/grdm_dev/templates/wiki_assets.json` · `tools/manifest_check.py`

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

The manifest ([SPEC-01](../spec/01_manifest.md#english)) listed `wiki-frontend` as a core component with one Compose *service* (a container that Compose starts) named `wiki`, and the installer tried to build it like every other core: clone `RDM-wiki-frontend-dev2027` at the pinned commit and run `docker buildx build` on that checkout.

The fourth real install on Mac Studio (2026-11-06, [DEMO-20](../demo/20_core_install_mac_studio.md)) stopped at `build` with exit 30: *image build failed — component wiki-frontend: docker buildx build exited 1*. BuildKit reported, for dozens of `COPY` lines at once, `failed to calculate checksum ... "/addons/metadata/static": not found`, `"/addons/gitlab/requirements.txt": not found`, `"/addons/zotero/static": not found` and so on.

Reading the two repositories side by side explains it:

- The wiki-frontend checkout contains only `addons/wiki/static/` (the Milkdown editor: `wikiPageMilkdown.js`, `heading.js`, `image.js`, `link.js`, ...), `website/static/js/` (`wikiTree.js`, `fangorn.js`, `pages/wiki-edit-page.js`), `website/static/vendor/knockout-sortable`, `package.json`, `yarn.lock`, `webpack.common.config.js`, `webpack.prod.config.js`, `Dockerfile`, `.jshintrc`, `.travis.yml` and a one-line `README.md`: "This is RDM wiki code for bundle with webpack5".
- Its `Dockerfile` is osf.io's Dockerfile with small edits: `FROM node:21-alpine` instead of `node:12-alpine3.9`, every Python/`pip`/`collectstatic`/`pybabel` step commented out, the admin `yarn install` commented out, and `yarn run webpack-prod` left in. It still `COPY`s `./requirements.txt`, `./addons/<name>/requirements.txt` for twenty-odd add-ons, `./admin/package.json ./admin/yarn.lock`, `./website/settings/`, `./api/base/settings/`, and `./addons/<name>/static/` for every add-on. None of these exist in the wiki-frontend tree; all of them exist in `RDM-osf.io-dev2027`. Because the Python steps are gone, the image it produces has Node, the `node_modules` and the webpack output — and no Flask or Django that could serve `web`, `api`, `admin` or `worker`.
- Its `package.json` keeps the name `osf` and version `20.14.0` of osf.io and upgrades `webpack` from `3.8.1` to `^5.93.0` (plus `webpack-cli` 5, `terser-webpack-plugin` 5, `assets-webpack-plugin` 7 and the `@milkdown/*` 7.3.6 editor packages). `webpack.common.config.js` keeps a single entry, `wiki-edit-page`, where osf.io's config lists forty pages (and has `wiki-edit-page` commented out), and drops the add-on entry discovery; `webpack.prod.config.js` replaces `UglifyJsPlugin` and `CommonsChunkPlugin` (webpack 3) with `TerserPlugin` and `optimization.splitChunks` (webpack 5).
- Both configs write to the same place: `output.path = <repo>/website/static/public/js` (in the image, `/code/website/static/public/js/`), `filename: '[name].[chunkhash].js'` in production, a `vendor.[hash].js` split chunk, and `SaveAssetsJson()` writes `webpack-assets.json` to the working directory (`/code/webpack-assets.json`). So the overlay build produces `wiki-edit-page.<chunkhash>.js`, `vendor.<hash>.js`, their source maps and a `webpack-assets.json` with those two entries. In the osf.io image the very same directory holds osf.io's forty bundles and its own `webpack-assets.json` (read by `website/util/paths.py` for the `webpack_asset` Mako filter).

So `wiki-frontend` is a *bundle builder* for osf.io's tree: a newer Node base, webpack 5 and the Milkdown editor sources, meant to be laid over the osf.io source before webpack runs. It has no process of its own and its image cannot run the application. Its real-time counterpart, `y-websocket` (the Yjs WebSocket server for co-editing), is a separate repository with its own server and stays a service.

### 2. Options considered

```toon
options[4]{id,option,builds_today,honest_about_contents,runtime_correct,fits_spec01,verdict}:
  A,"Separate `wiki` service built from the wiki-frontend checkout (status quo)","no (COPY of osf.io paths fails on the first step)","no (there is no wiki server to run)",no,no,"impossible; rejected"
  B,"One image: build osf.io from the merged tree with the wiki-frontend Dockerfile, tag `grdm-dev/osf.io:<osf>-<wiki>`, run web/api/admin/worker from it","yes","yes (both commits in the tag)","no (the Dockerfile skips pip, collectstatic and pybabel: no Python runtime for web/api/admin/worker)","partly (one field)","rejected"
  C,"Prebuilt osf.io image from a registry, pinned by digest (like ember-osf-web and cas-overlay until M4)","yes","no (nobody can show which commits are inside; and the osf.io image is the one image we must build from source)",unknown,"no (bypasses the build-from-pinned-source guarantee for the central component)",rejected
  D,"Two images: osf.io built normally; the overlay built from the merged tree as `grdm-dev/wiki-frontend:<osf>-<wiki>` and run once by `wiki_assets` to copy the bundle into the volume `wiki_static`, mounted read-only by web/api/admin/worker (upstream osf.io's `assets` pattern)","yes","yes (both commits in the overlay tag; osf.io keeps its own)","yes (osf.io image unchanged; only static files added)","yes (`overlay_of` + one-shot service)",chosen
```

Option B was the first design of this record and is kept here because its rejection reason is the one that matters: the overlay Dockerfile is a build tool, not an application image. Option C would have hidden the problem: the whole point of the integration repositories ([ADR-01](ADR-01_Integration_Repository_Placement.md)) is that the central `osf.io` image is built from pinned commits that we can name.

### 3. Decision

1. **Manifest.** A component may carry `overlay_of: "<base id>"` ([SPEC-01 §3](../spec/01_manifest.md#english)). It keeps its own `integration_repo`, `integration_sha`, `upstreams[]` and PR lists, so the weekly integration PR and the upstream tracking ([SPEC-05](../spec/05_upstream_tracking.md)) work unchanged. Its `services[]` are one-shot services. `wiki-frontend` gets `overlay_of: "osf.io"`, `services: ["wiki_assets"]`, `profile: core` and a `note`.
2. **Checker.** `grdm-dev manifest check` adds MC-14: the base exists, is not `infra`, is not an overlay and has no `prebuilt_image`; the overlay is not `infra` and has no `prebuilt_image`; a base takes at most one overlay. The installer refuses an overlay service whose template is not `one_shot: true` (also reported as MC-14).
3. **Build.** `grdm-dev build` builds `osf.io` as before (`grdm-dev/osf.io:<osf_sha12>`). For the overlay it syncs the base checkout too (once per run), recreates `runtime/src/_overlay/wiki-frontend/` as a copy of the osf.io checkout without `.git` with the wiki-frontend files copied over it without `.git` (the overlay's version wins where both have a file: `Dockerfile`, `package.json`, `yarn.lock`, the webpack configs, `addons/wiki/static/*`), and runs `docker buildx build -f <context>/Dockerfile <context>` tagged `grdm-dev/wiki-frontend:<osf_sha12>-<wiki_sha12>` (with `--push`, `ghcr.io/rcosdp/wiki-frontend:<same>`), with the labels `org.gakunin-rdm.overlay-of=osf.io` and `org.gakunin-rdm.base-sha=<osf_sha12>`. The build report row carries `overlay_of`, `base_repo`, `base_sha12` and `image_tag`; `compose render` reads `image_tag`.
4. **Compose.** The template `wiki_assets.json` (profile `core`, `one_shot: true`, rendered with `restart: "no"`) runs the overlay image as user `1000:1000` with `cap_drop: [ALL]`, `no-new-privileges`, a read-only root filesystem and `/tmp` on tmpfs — the baseline controls of [SPEC-03 §3](../spec/03_security_gate.md#english), no hardening exception — and executes: copy `/code/website/static/public/js/.` with `cp -a` into the volume mounted at `/wiki_static` (after emptying it, so a stale bundle from an older commit disappears), copy `/code/webpack-assets.json` next to it, add the unhashed alias `wiki-edit-page.js` beside `wiki-edit-page.<chunkhash>.js` so a template can reference a stable path, list the result and exit 0. `web`, `api`, `admin` and `worker` mount `wiki_static` read-only at **`/code/website/static/public/js/wiki/`** and list `wiki_assets` in `depends_on` with `condition: service_completed_successfully` (Compose long form; plain dependencies become `condition: service_started`). In the `minimum` profile `wiki_assets` is absent and the dependency is dropped.
   **Why a subpath and not the directory itself.** The overlay's `output.path` is the same directory the osf.io image's own `webpack-prod` fills. Mounting the volume *at* `/code/website/static/public/js` would hide osf.io's forty bundles, and copying the overlay's `webpack-assets.json` over osf.io's would break the `webpack_asset` filter for every other page. The overlay image's directory contains only the overlay's output (its config has one entry), so copying it whole into a *subdirectory* is non-destructive: `/static/public/js/wiki/wiki-edit-page.js` is served by the existing static route, the vendor chunk resolves relative to it, and nothing of osf.io is shadowed.
5. **Health and plan.** `health` treats a service with `restart: "no"` as healthy once it has `exited` with code 0 (`health: completed`); still running or non-zero is a failure. `plan` and `compose render` show `wiki_assets` with origin `overlay` and `build_from: RDM-wiki-frontend-dev2027@<sha12> over RDM-osf.io-dev2027@<sha12> (overlay of osf.io)`. The `wiki` template is deleted; [SPEC-02 §4](../spec/02_installer_cli.md#2-en-ports) lists `wiki_assets` in `core`.

### 4. Consequences

- The osf.io image used by `web`, `api`, `admin` and `worker` is unchanged and still built from osf.io's own Dockerfile. The wiki editor bundle arrives as files in a volume, so a new wiki-frontend commit changes only the overlay tag and the volume contents.
- `wiki-frontend` contributes one one-shot service, no port and no hardening exception. The acceptance scenario C4 (Wiki collaborative edit, [SPEC-04 §4](../spec/04_acceptance_tests.md#english)) exercises `web`, `y_websocket` and `sharejs`, as before.
- `y-websocket` stays a separate service (`y_websocket`, profile `core`): it is a server, not a bundle.
- Open point for the next real install run: osf.io's `addons/wiki/templates/edit.mako` currently loads `/static/js/pages/wiki-edit-page.js` (the raw source), not a built bundle, and osf.io's own webpack config has the `wiki-edit-page` entry commented out. The page must be pointed at `/static/public/js/wiki/wiki-edit-page.js` (or `webpack_asset` taught the overlay's `webpack-assets.json`) in the integration repository; the overlay build itself (does `yarn run webpack-prod` succeed in the merged tree, is the `node:21-alpine` image multi-arch) is also confirmed there and recorded in [DEMO-20](../demo/20_core_install_mac_studio.md).
- Review at M4: when osf.io's Dockerfile is modernized, decide whether the wiki-frontend overlay is merged into the osf.io repository (one webpack build) or stays an overlay; the `overlay_of` and one-shot mechanisms remain available for any other repository of the same shape.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

manifest（[SPEC-01](../spec/01_manifest.md#japanese)）は `wiki-frontend` をコア部品とし、`wiki` という Compose の「サービス」（Compose が起動するコンテナ）を一つ持たせていた。インストーラーはほかのコアと同じに、`RDM-wiki-frontend-dev2027` を固定コミットで clone し、その checkout で `docker buildx build` を走らせようとした。

Mac Studio での第 4 回実導入（2026-11-06、[DEMO-20](../demo/20_core_install_mac_studio.md)）は `build` で終了 30 になった。「image build failed — component wiki-frontend: docker buildx build exited 1」。BuildKit は何十行もの `COPY` について一度に `failed to calculate checksum ... "/addons/metadata/static": not found`、`"/addons/gitlab/requirements.txt": not found`、`"/addons/zotero/static": not found` などを報告した。

二つのリポジトリを並べて読むと理由が分かる。

- wiki-frontend の checkout にあるのは `addons/wiki/static/`（Milkdown エディタ: `wikiPageMilkdown.js`、`heading.js`、`image.js`、`link.js` など）、`website/static/js/`（`wikiTree.js`、`fangorn.js`、`pages/wiki-edit-page.js`）、`website/static/vendor/knockout-sortable`、`package.json`、`yarn.lock`、`webpack.common.config.js`、`webpack.prod.config.js`、`Dockerfile`、`.jshintrc`、`.travis.yml`、そして一行の `README.md`「This is RDM wiki code for bundle with webpack5」だけである。
- その `Dockerfile` は osf.io の Dockerfile に小さな手を入れたものである。`FROM node:12-alpine3.9` を `node:21-alpine` に、Python・`pip`・`collectstatic`・`pybabel` の手順をすべてコメントアウト、admin の `yarn install` もコメントアウト、`yarn run webpack-prod` は残す。それでも `./requirements.txt`、二十数個のアドオンの `./addons/<name>/requirements.txt`、`./admin/package.json ./admin/yarn.lock`、`./website/settings/`、`./api/base/settings/`、全アドオンの `./addons/<name>/static/` を `COPY` する。どれも wiki-frontend の木には無く、すべて `RDM-osf.io-dev2027` にある。Python の手順が無いので、できるイメージには Node と `node_modules` と webpack の出力しか無く、`web`・`api`・`admin`・`worker` を動かす Flask も Django も入っていない。
- `package.json` は osf.io の名前 `osf` と版 `20.14.0` のまま、`webpack` を `3.8.1` から `^5.93.0` に上げている（`webpack-cli` 5、`terser-webpack-plugin` 5、`assets-webpack-plugin` 7、エディタの `@milkdown/*` 7.3.6 も）。`webpack.common.config.js` は osf.io 側の四十ページのエントリ（そこでは `wiki-edit-page` がコメントアウトされている）を `wiki-edit-page` 一つに絞り、アドオンのエントリ探索を外す。`webpack.prod.config.js` は webpack 3 の `UglifyJsPlugin`・`CommonsChunkPlugin` を webpack 5 の `TerserPlugin`・`optimization.splitChunks` に置き換える。
- 両設定の出力先は同じである。`output.path = <repo>/website/static/public/js`（イメージ内では `/code/website/static/public/js/`）、本番の `filename` は `[name].[chunkhash].js`、`vendor.[hash].js` の分割チャンク、`SaveAssetsJson()` が作業ディレクトリ（`/code/webpack-assets.json`）に `webpack-assets.json` を書く。つまりオーバーレイのビルドは `wiki-edit-page.<chunkhash>.js`、`vendor.<hash>.js`、その source map、二項目だけの `webpack-assets.json` を作る。osf.io のイメージでは同じディレクトリに osf.io の四十本の束と自前の `webpack-assets.json`（`website/util/paths.py` が Mako フィルタ `webpack_asset` のために読む）がある。

つまり `wiki-frontend` は osf.io の木のための「束を組む道具」である。新しい Node ベース、webpack 5、Milkdown エディタのソースを、webpack を走らせる前に osf.io のソースの上へ重ねるためのものだ。自分で動かすプロセスは無く、そのイメージでアプリケーションは動かない。共同編集の相方 `y-websocket`（Yjs の WebSocket サーバ）は独立したリポジトリで自分のサーバを持つので、サービスのままとする。

### 2. 検討した選択肢

```toon
options[4]{id,option,builds_today,honest_about_contents,runtime_correct,fits_spec01,verdict}:
  A,"wiki-frontend の checkout から組む独立サービス `wiki`（現状）","いいえ（osf.io のパスの COPY が最初の段で失敗）","いいえ（動かす wiki サーバが無い）",いいえ,いいえ,"不可能。却下"
  B,"イメージ一つ: 重ねた木から wiki-frontend の Dockerfile で osf.io を組み `grdm-dev/osf.io:<osf>-<wiki>` とし、web/api/admin/worker をそれで動かす","はい","はい（両コミットがタグに）","いいえ（Dockerfile が pip・collectstatic・pybabel を飛ばすので web/api/admin/worker の Python 実行環境が無い）","一部（項目一つ）","却下"
  C,"レジストリの事前ビルド済み osf.io イメージをダイジェスト固定で使う（M4 までの ember-osf-web・cas-overlay と同じ）","はい","いいえ（中のコミットを誰も示せない。しかも osf.io のイメージこそ元から組むべき唯一のもの）",不明,"いいえ（中心部品で「固定した元から組む」保証を外す）",却下
  D,"イメージ二つ: osf.io は通常どおり組む。オーバーレイは重ねた木から `grdm-dev/wiki-frontend:<osf>-<wiki>` として組み、`wiki_assets` が一度動かして束をボリューム `wiki_static` へ写し、web/api/admin/worker が読み取り専用で mount する（上流 osf.io の `assets` の型）","はい","はい（オーバーレイのタグに両コミット。osf.io は自分のタグを保つ）","はい（osf.io のイメージは不変。静的ファイルを足すだけ）","はい（`overlay_of` ＋ 一回限りのサービス）",採用
```

B はこの記録の最初の案で、却下理由こそが肝心なので残す。オーバーレイの Dockerfile はビルド道具であってアプリケーションのイメージではない。C は問題を隠すだけだった。統合リポジトリ（[ADR-01](ADR-01_Integration_Repository_Placement.md)）の眼目は、中心の `osf.io` イメージを名指しできる固定コミットから組むことにある。

### 3. 決定

1. **manifest。** 部品は `overlay_of: "<ベースの id>"` を持てる（[SPEC-01 §3](../spec/01_manifest.md#japanese)）。自分の `integration_repo`、`integration_sha`、`upstreams[]`、PR の一覧はそのまま持つので、週次統合 PR と上流追跡（[SPEC-05](../spec/05_upstream_tracking.md)）は変わらず動く。`services[]` は一回限りのサービスである。`wiki-frontend` には `overlay_of: "osf.io"`、`services: ["wiki_assets"]`、`profile: core`、`note` を書く。
2. **検査。** `grdm-dev manifest check` に MC-14 を足す。ベースが存在し、`infra` でなく、オーバーレイでなく、`prebuilt_image` を持たない。オーバーレイは `infra` でなく、`prebuilt_image` を持たない。ベース一つにオーバーレイは最大一つ。インストーラーはテンプレートが `one_shot: true` でないオーバーレイのサービスを拒む（これも MC-14 として報告）。
3. **build。** `grdm-dev build` は `osf.io` をこれまでどおり組む（`grdm-dev/osf.io:<osf の sha12>`）。オーバーレイについては、ベースの checkout も同期し（一回の実行で一度）、`runtime/src/_overlay/wiki-frontend/` を osf.io checkout の `.git` 抜きの写しとして作り直し、その上に wiki-frontend のファイルを `.git` 抜きで重ね（両方にあるファイル `Dockerfile`、`package.json`、`yarn.lock`、webpack 設定、`addons/wiki/static/*` はオーバーレイ側が勝つ）、`docker buildx build -f <context>/Dockerfile <context>` を `grdm-dev/wiki-frontend:<osf の sha12>-<wiki の sha12>`（`--push` では `ghcr.io/rcosdp/wiki-frontend:<同じ>`）のタグと、ラベル `org.gakunin-rdm.overlay-of=osf.io`・`org.gakunin-rdm.base-sha=<osf の sha12>` で走らせる。ビルド報告の行に `overlay_of`、`base_repo`、`base_sha12`、`image_tag` を持たせ、`compose render` は `image_tag` を読む。
4. **compose。** テンプレート `wiki_assets.json`（profile `core`、`one_shot: true`、`restart: "no"` で出力）は、オーバーレイのイメージを利用者 `1000:1000`、`cap_drop: [ALL]`、`no-new-privileges`、読み取り専用ルート、tmpfs の `/tmp` で動かす（[SPEC-03 §3](../spec/03_security_gate.md#japanese) の基本対策。hardening の例外は無い）。処理は、`/wiki_static` に mount したボリュームを空にしてから `/code/website/static/public/js/.` を `cp -a` で写し（古いコミットの束が残らないように）、`/code/webpack-assets.json` を隣に写し、`wiki-edit-page.<chunkhash>.js` の隣にハッシュ無しの別名 `wiki-edit-page.js` を置いて（テンプレートが固定パスを参照できるように）、結果を一覧して 0 で終了する。`web`・`api`・`admin`・`worker` は `wiki_static` を **`/code/website/static/public/js/wiki/`** に読み取り専用で mount し、`depends_on` に `wiki_assets` を `condition: service_completed_successfully` で載せる（Compose の長い形。普通の依存は `condition: service_started` になる）。`minimum` プロファイルでは `wiki_assets` が無く、依存は落とされる。
   **なぜディレクトリそのものでなく下位パスか。** オーバーレイの `output.path` は、osf.io のイメージ自身の `webpack-prod` が満たすディレクトリと同じである。ボリュームを `/code/website/static/public/js` に mount すると osf.io の四十本の束が隠れ、オーバーレイの `webpack-assets.json` で osf.io のものを上書きすれば他の全ページの `webpack_asset` フィルタが壊れる。オーバーレイのイメージのそのディレクトリにはオーバーレイの出力しか無い（設定のエントリは一つ）ので、丸ごと「下位ディレクトリ」へ写すのは非破壊である。`/static/public/js/wiki/wiki-edit-page.js` は既存の静的ルートで配信され、vendor チャンクはそれに相対で解決し、osf.io のものは何も隠れない。
5. **health と plan。** `health` は `restart: "no"` のサービスを、終了コード 0 の `exited` で健康（`health: completed`）とみなす。まだ動いている、または 0 以外なら失敗。`plan` と `compose render` は `wiki_assets` を origin `overlay`、`build_from: RDM-wiki-frontend-dev2027@<sha12> over RDM-osf.io-dev2027@<sha12> (overlay of osf.io)` で示す。テンプレート `wiki` は削除し、[SPEC-02 §4](../spec/02_installer_cli.md#2-ja-ports) は `core` に `wiki_assets` を載せる。

### 4. 結果

- `web`・`api`・`admin`・`worker` が使う osf.io のイメージは変わらず、osf.io 自身の Dockerfile から組まれる。Wiki エディタの束はボリュームのファイルとして届くので、wiki-frontend の新しいコミットが変えるのはオーバーレイのタグとボリュームの中身だけである。
- `wiki-frontend` が持ち込むのは一回限りのサービス一つで、ポートも hardening の例外も無い。受入シナリオ C4（Wiki 共同編集、[SPEC-04 §4](../spec/04_acceptance_tests.md#japanese)）はこれまでどおり `web`・`y_websocket`・`sharejs` を使う。
- `y-websocket` は独立サービス（`y_websocket`、profile `core`）のまま。サーバであって束ではない。
- 次の実導入での未確認点。osf.io の `addons/wiki/templates/edit.mako` は今 `/static/js/pages/wiki-edit-page.js`（生のソース）を読み込み、組んだ束ではない。osf.io 自身の webpack 設定でも `wiki-edit-page` のエントリはコメントアウトされている。統合リポジトリでページを `/static/public/js/wiki/wiki-edit-page.js` に向ける（または `webpack_asset` にオーバーレイの `webpack-assets.json` を読ませる）必要がある。オーバーレイのビルドそのもの（重ねた木で `yarn run webpack-prod` が通るか、`node:21-alpine` が多アーキテクチャか）もそこで確かめ、[DEMO-20](../demo/20_core_install_mac_studio.md) に記録する。
- M4 で見直す。osf.io の Dockerfile を近代化する時に、wiki-frontend のオーバーレイを osf.io のリポジトリに統合する（webpack ビルドを一つにする）かオーバーレイのまま置くかを決める。`overlay_of` と一回限りのサービスの仕組みは、同じ形のほかのリポジトリにも使える。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Overlay | A set of files laid over another repository's tree before the image is built; its image is a build tool, not a server. | イメージを組む前にほかのリポジトリの木の上に重ねるファイルの組。そのイメージはビルド道具でサーバではない。 |
| One-shot service | A Compose service whose container runs once, does its job and exits (`restart: "no"`); others wait for it with `service_completed_successfully`. | 一度動いて仕事を終えたら終了する Compose のサービス（`restart: "no"`）。ほかは `service_completed_successfully` でそれを待つ。 |
| Build context | The directory `docker buildx build` reads files from; every `COPY` source must be inside it. | `docker buildx build` がファイルを読む場所。`COPY` の元はすべてこの中に無ければならない。 |
| webpack | The tool that bundles many JavaScript files into the few files a browser downloads; osf.io uses version 3, the overlay version 5. | 多くの JavaScript をブラウザが読む少数のファイルに束ねる道具。osf.io は版 3、オーバーレイは版 5。 |
| Named volume | A directory Docker keeps outside any container (here under `runtime/volumes/<name>`) that several services can mount. | コンテナの外に Docker が保つディレクトリ（ここでは `runtime/volumes/<名前>`）。複数のサービスが mount できる。 |
| Milkdown | The Markdown editor component used by the GRDM wiki pages. | GRDM の Wiki ページが使う Markdown エディタ部品。 |
