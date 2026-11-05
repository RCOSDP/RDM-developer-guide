# DEMO-20 Core Install on Mac Studio / Mac Studio でのコア導入記録

> **Summary:** What actually happened when `./installer/install.sh --yes --no-open --profile core` was run on the Mac Studio (Apple Silicon). One entry per run; nothing is edited after the fact.
> **概要:** Mac Studio（Apple Silicon）で `./installer/install.sh --yes --no-open --profile core` を実行したときに実際に起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.4 — 2026-11-06. **Learned:** a repository can be an overlay rather than a service; the installer must know the shape of each component (built, prebuilt, overlay) before it can build anything. ／ リポジトリはサービスではなくオーバーレイであることがある。インストーラーは組む前に各部品の形（built・prebuilt・overlay）を知っていなければならない。
  0.3 — 2026-11-06. **Learned:** CPU emulation can turn an EOL build into a silent hang rather than an error, so hung builds need an operator timeout and a prebuilt fallback until modernization. ／ CPU エミュレーションは EOL のビルドをエラーではなく無言のハングに変えうる。近代化までは、ハングしたビルドに操作者の打ち切りと配布済みイメージの代替が要る。
  0.2 — 2026-11-05. **Learned:** emulation solves missing arm64 wheels but not a base image that current Docker refuses outright; that needs a prebuilt fallback until the Dockerfile is modernized. ／ エミュレーションは arm64 の wheel 不足を解くが、現行 Docker が取得そのものを拒むベースイメージには効かない。Dockerfile を近代化するまでは配布済みイメージの代替が要る。
  0.1 — 2026-11-05. **Learned:** the first real run proved the stop-at-first-failure design and exposed that an EOL Python 3.5 image cannot be built for arm64, which the specifications had only predicted. ／ 最初の実行で「最初の失敗で止まる」設計が働くことと、EOL の Python 3.5 イメージは arm64 で組めないこと（仕様では予測だった）が実証された。
- Normative source: [SPEC-02 Installer CLI](../spec/02_installer_cli.md) · [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md)
- Related: [docs/demo/README.md](README.md) · [docs/status/README.md](../status/README.md) · [ADR-03 Staged Security Gate](../decisions/ADR-03_Staged_Security_Gate.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Run 1 — 2026-11-05, branch `feat/m2-installer` (PR #21, before review fixes)

Host (from `grdm-dev doctor`): macOS 27.2, arm64, 128 GiB memory, Docker 29.5.2, Compose 5.6.0, buildx present. Supported, Docker OK.

```toon
run1:
  command: ./installer/install.sh --yes --no-open --profile core
  env: GRDM_WITH_ACCEPT=1
  result: exit 30 (image build failed)
  steps[5]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"2.92 GB; Debian buster archive packages (EOL base)"
    waterbutler,linux/arm64,built,1.28 GB
    modular-file-renderer,linux/arm64,build-failed,"pip: no matching distribution for pandas==0.25.1 on Python 3.5 / arm64"
```

What this proves:

- The bootstrap (`install.sh` → `.venv/` → `grdm-dev install`) works end to end on a clean macOS shell.
- The sequence stops at the first failing step and returns that step's exit code (30), as [SPEC-02 §2.1](../spec/02_installer_cli.md) requires; nothing was started.
- The EOL base images (see [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)) are not only a security problem but a build problem on Apple Silicon.

Decision taken: components whose base cannot be built for arm64 (modular-file-renderer, ember-osf-web, cas-overlay) get `build_platform: linux/amd64` in the manifest ([SPEC-01](../spec/01_manifest.md)) and run under emulation until M4 modernizes them. Run 2 will be recorded below after the review fixes land.

### Run 2 — 2026-11-05, branch `feat/m2-installer` (after review fixes r1, commit 3149c76 + 1c2a925)

Same host. Changes since run 1: `build_platform: linux/amd64` for modular-file-renderer, ember-osf-web and cas-overlay; two networks (`grdm` internal, `grdm-edge` publishing); PostgreSQL 9.6 `auth-host=md5`.

```toon
run2:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 30 (image build failed)
  steps[5]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[4]{component,platform,status,note}:
    osf.io,linux/arm64,built,cached from run 1
    waterbutler,linux/arm64,built,cached from run 1
    modular-file-renderer,linux/amd64,built,"emulated build succeeded (pandas 0.25.1 has an amd64 wheel)"
    ember-osf-web,linux/amd64,build-failed,"base image quay.io/centerforopenscience/ember-base is a Docker manifest v2 schema 1 image; current Docker refuses to pull it"
```

What this proves:

- `build_platform` works: the component that could not be built for arm64 in run 1 now builds under emulation.
- `secrets init` is idempotent (kept the existing `runtime/.env`), and re-rendering did not move ports.
- The ember-osf-web Dockerfile cannot be built at all with current Docker, independent of CPU. This is a defect of the EOL base, to be fixed in the integration repository at M4.

Decision taken: add a documented, digest-pinned `prebuilt_image` fallback to the manifest ([SPEC-01](../spec/01_manifest.md)) for ember-osf-web until M4, using the distribution image the legacy guide relied on. Run 3 will be recorded below.

### Run 3 — 2026-11-05/06, branch `feat/m2-installer` (after review fixes r2, with `prebuilt_image` for ember-osf-web)

Same host (Docker via colima 29.5.2). Changes since run 2: ember-osf-web uses a digest-pinned `prebuilt_image`; run 1–2 images cached.

```toon
run3:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "exit 30 (image build failed) after the operator stopped a hung emulated build"
  steps[5]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[5]{component,platform,status,note}:
    osf.io,linux/arm64,built,cached
    waterbutler,linux/arm64,built,cached
    modular-file-renderer,linux/amd64,built,cached
    ember-osf-web,linux/amd64,prebuilt,"digest-pinned distribution image pulled as designed"
    cas-overlay,linux/amd64,build-failed,"maven:3.3-jdk-8 Dockerfile; Maven build under qemu emulation produced no output for 8 h 08 m at 0% CPU; stopped by the operator (buildx exit 130)"
```

What this proves:

- The `prebuilt_image` fallback works end to end: the digest-pinned reference is pulled for the component's platform, the build report row says `prebuilt`, and `compose render` writes that same reference as the service's `image:` (no local re-tagging).
- An EOL Java 8 / Maven 3.3 build under CPU emulation is not viable on this host: it hung rather than failed. The stop-at-first-failure rule still held (exit 30, nothing started).

Decision taken: cas-overlay also uses a digest-pinned `prebuilt_image` (the distribution image's `linux/amd64` manifest) until M4 modernizes its Dockerfile; recorded in the manifest note. Run 4 will be recorded below.

### Run 4 — 2026-11-06, develop after PR #28 (cas-overlay prebuilt)

Same host. Changes since run 3: cas-overlay uses a digest-pinned `prebuilt_image`.

```toon
run4:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 30 (image build failed)
  steps[5]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[6]{component,platform,status,note}:
    osf.io,linux/arm64,built,cached
    waterbutler,linux/arm64,built,cached
    modular-file-renderer,linux/amd64,built,cached
    ember-osf-web,linux/amd64,prebuilt,cached pull
    cas-overlay,linux/amd64,prebuilt,"digest-pinned distribution image pulled"
    wiki-frontend,linux/arm64,build-failed,"Dockerfile COPYs addons/*/requirements.txt, admin/yarn.lock, website/... that exist only in the osf.io tree"
```

What this proves:

- The cas-overlay fallback works; every remaining failure now comes from how a component is *shaped*, not from CPU or base-image age.
- wiki-frontend is not a standalone service: its repository holds only `website/static`, `addons/wiki`, webpack 5 configs and a Dockerfile derived from osf.io's. It is an overlay to be applied on the osf.io source tree and it produces a webpack bundle, not a runtime image.

Decision taken: [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md). The manifest marks wiki-frontend as `overlay_of: osf.io`; `build` creates a merged context (osf.io checkout + overlay files) and builds a bundle-builder image; `compose render` adds a one-shot `wiki_assets` service that copies the bundle into a named volume mounted read-only by the osf.io services. The osf.io image itself stays built from its own Dockerfile. Run 5 will be recorded below.

Evidence (run 1): full log kept in the session scratchpad only (contains package download noise, no secrets). The `runtime/` directory on the Mac Studio holds `.env` (0600), the rendered Compose file and two built images; it is git-ignored.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 第 1 回 — 2026-11-05、ブランチ `feat/m2-installer`（PR #21、レビュー修正前）

ホスト（`grdm-dev doctor` より）: macOS 27.2、arm64、メモリ 128 GiB、Docker 29.5.2、Compose 5.6.0、buildx あり。対応ホスト、Docker 正常。

```toon
run1:
  command: ./installer/install.sh --yes --no-open --profile core
  env: GRDM_WITH_ACCEPT=1
  result: "終了コード 30（イメージのビルド失敗）"
  steps[5]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"2.92 GB。Debian buster のアーカイブからパッケージ取得（EOL ベース）"
    waterbutler,linux/arm64,built,1.28 GB
    modular-file-renderer,linux/arm64,build-failed,"pip: Python 3.5 / arm64 向けの pandas==0.25.1 が存在しない"
```

これで分かったこと:

- ブートストラップ（`install.sh` → `.venv/` → `grdm-dev install`）は、素の macOS のシェルで端から端まで動く。
- 手順は最初に失敗した段階で止まり、その段階の終了コード（30）を返す。[SPEC-02 §2.1](../spec/02_installer_cli.md) のとおりで、サービスは何も起動していない。
- EOL のベースイメージ（[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)）は安全性の問題だけでなく、Apple Silicon ではビルドの問題でもある。

決めたこと: arm64 で組めない部品（modular-file-renderer、ember-osf-web、cas-overlay）は manifest に `build_platform: linux/amd64` を持たせ（[SPEC-01](../spec/01_manifest.md)）、M4 で近代化するまでエミュレーションで動かす。第 2 回はレビュー修正の反映後に下へ追記する。

### 第 2 回 — 2026-11-05、ブランチ `feat/m2-installer`（レビュー r1 対応後、コミット 3149c76 ＋ 1c2a925）

同じホスト。第 1 回からの変更: modular-file-renderer・ember-osf-web・cas-overlay に `build_platform: linux/amd64`、ネットワークを二つ（内部の `grdm` と公開用の `grdm-edge`）、PostgreSQL 9.6 の `auth-host=md5`。

```toon
run2:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 30（イメージのビルド失敗）"
  steps[5]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[4]{component,platform,status,note}:
    osf.io,linux/arm64,built,第 1 回のキャッシュ
    waterbutler,linux/arm64,built,第 1 回のキャッシュ
    modular-file-renderer,linux/amd64,built,"エミュレーションでのビルドに成功（pandas 0.25.1 に amd64 の wheel がある）"
    ember-osf-web,linux/amd64,build-failed,"ベースイメージ quay.io/centerforopenscience/ember-base が Docker の manifest v2 schema 1 形式で、現行 Docker は取得を拒否する"
```

これで分かったこと:

- `build_platform` は働く。第 1 回で arm64 向けに組めなかった部品が、エミュレーションで組めた。
- `secrets init` は冪等（既存の `runtime/.env` を保持）で、再描画でポートは動かなかった。
- ember-osf-web の Dockerfile は CPU に関係なく現行 Docker ではまったく組めない。EOL ベースの欠陥であり、M4 で統合リポジトリ側を直す。

決めたこと: M4 まで、ember-osf-web には manifest の記録付き・ダイジェスト固定の `prebuilt_image`（旧ガイドが頼っていた配布イメージ）を使う（[SPEC-01](../spec/01_manifest.md)）。第 3 回は下へ追記する。

### 第 3 回 — 2026-11-05/06、ブランチ `feat/m2-installer`（レビュー r2 対応後、ember-osf-web に `prebuilt_image`）

同じホスト（Docker は colima 29.5.2）。第 2 回からの変更: ember-osf-web はダイジェスト固定の `prebuilt_image`。第 1〜2 回のイメージはキャッシュ。

```toon
run3:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 30（イメージのビルド失敗）。ハングしたエミュレーションビルドを操作者が停止"
  steps[5]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[5]{component,platform,status,note}:
    osf.io,linux/arm64,built,キャッシュ
    waterbutler,linux/arm64,built,キャッシュ
    modular-file-renderer,linux/amd64,built,キャッシュ
    ember-osf-web,linux/amd64,prebuilt,"ダイジェスト固定の配布イメージを設計どおり取得"
    cas-overlay,linux/amd64,build-failed,"maven:3.3-jdk-8 の Dockerfile。qemu エミュレーション下の Maven ビルドが CPU 0% のまま 8 時間 08 分出力なし。操作者が停止（buildx 終了 130）"
```

これで分かったこと:

- `prebuilt_image` の代替は端から端まで働く: ダイジェスト固定の参照を部品のプラットフォームで取得し、ビルド報告の行は `prebuilt`、`compose render` はその同じ参照をサービスの `image:` に書く（ローカルでのタグ付け直しはしない）。
- EOL の Java 8 / Maven 3.3 を CPU エミュレーションで組むのはこのホストでは現実的でなく、失敗ではなくハングした。「最初の失敗で止まる」規則は守られた（終了 30、何も起動していない）。

決めたこと: cas-overlay も M4 で Dockerfile を近代化するまで、配布イメージの `linux/amd64` マニフェストをダイジェスト固定の `prebuilt_image` として使う。manifest の note に記録。第 4 回は下へ追記する。

### 第 4 回 — 2026-11-06、PR #28 マージ後の develop（cas-overlay は prebuilt）

同じホスト。第 3 回からの変更: cas-overlay はダイジェスト固定の `prebuilt_image`。

```toon
run4:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 30（イメージのビルド失敗）"
  steps[5]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,30,failed
  images[6]{component,platform,status,note}:
    osf.io,linux/arm64,built,キャッシュ
    waterbutler,linux/arm64,built,キャッシュ
    modular-file-renderer,linux/amd64,built,キャッシュ
    ember-osf-web,linux/amd64,prebuilt,取得済みキャッシュ
    cas-overlay,linux/amd64,prebuilt,"ダイジェスト固定の配布イメージを取得"
    wiki-frontend,linux/arm64,build-failed,"Dockerfile が osf.io の木にしかない addons/*/requirements.txt、admin/yarn.lock、website/… を COPY する"
```

これで分かったこと:

- cas-overlay の代替は働く。残る失敗はすべて部品の「形」に由来し、CPU やベースイメージの古さではない。
- wiki-frontend は独立したサービスではない。リポジトリには `website/static`、`addons/wiki`、webpack 5 の設定、osf.io 派生の Dockerfile しかなく、osf.io のソースツリーに重ねて webpack の束を作るオーバーレイである。実行用イメージは作らない。

決めたこと: [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)。manifest で wiki-frontend を `overlay_of: osf.io` とし、`build` は重ねたコンテキスト（osf.io のチェックアウト＋オーバーレイ）から束を作るイメージを組み、`compose render` は一回限りの `wiki_assets` サービスを加えて束を名前付きボリュームへ写し、osf.io のサービスが読み取り専用でマウントする。osf.io のイメージ自体は従来どおり自分の Dockerfile で組む。第 5 回は下へ追記する。

証跡（第 1 回）: 全ログはセッションの作業領域にのみ保管（パッケージ取得の出力が大半で、秘密は含まない）。Mac Studio の `runtime/` には `.env`（0600）、生成した Compose ファイル、ビルド済みイメージ 2 つがあり、git では無視される。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| Wheel | A ready-made package of Python code for one CPU type; if none exists, pip must compile it. | ある CPU 向けにできあがった Python の部品の箱。無いと pip が自分で組み立てる。 |
