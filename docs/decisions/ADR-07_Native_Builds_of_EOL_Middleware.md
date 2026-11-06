# ADR-07 Native Builds of EOL Middleware / EOL ミドルウェアのネイティブビルド

> **Summary:** Some middleware the current GakuNin RDM needs (Elasticsearch 2.4.6 first) is end of life and only ships `linux/amd64` images. Running such an image under emulation on Apple Silicon is not merely slow: Elasticsearch 2 took 38 minutes to open its port on a fresh data directory (real install run 19), and the same program on a native arm64 JRE starts in 5 seconds. We decide to **build such images ourselves, natively for both architectures, from the official release artefact on a digest-pinned base**, declared in the manifest as `image_build: {context, tag}` with a Dockerfile under `installer/images/<id>/`, until the milestone that retires the middleware (M5 for Elasticsearch 2). The native image also runs as the hardening default (non-root, read-only), so two hardening exceptions and one owner-init container disappear.
> **概要:** 現在の GakuNin RDM が必要とするミドルウェアの一部（まず Elasticsearch 2.4.6）は EOL で、`linux/amd64` のイメージしか配布されていない。Apple Silicon でそれをエミュレーションで動かすのは「遅い」で済まない。Elasticsearch 2 は新しいデータディレクトリでポートを開くまで 38 分かかり（実機第 19 回）、同じプログラムは arm64 ネイティブの JRE なら 5 秒で起動する。**公式のリリース成果物からダイジェスト固定のベース上に、両アーキテクチャ向けのイメージを自分たちでネイティブに組む**ことを決める。manifest では `image_build: {context, tag}` として宣言し、Dockerfile は `installer/images/<id>/` に置き、そのミドルウェアを退役させる節目（Elasticsearch 2 は M5）まで続ける。ネイティブのイメージは堅牢化の既定（非 root・読み取り専用）で動くので、堅牢化の例外二つと所有者初期化コンテナ一つが消える。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a cold start measures what a warm host hides: an emulated JDK 8 service spends tens of minutes initialising every time its data directory is new, and no timeout makes that acceptable; the program itself starts in seconds when it runs natively (real install run 19, PR #33 review r1). ／ コールドスタートは温まったホストが隠すものを測る。エミュレーションされた JDK 8 のサービスはデータディレクトリが新しいたびに数十分を初期化に費やし、どんなタイムアウトでもそれは許容できない。プログラム自体はネイティブで動かせば数秒で起動する（実機第 19 回、PR #33 レビュー r1）。
- Status: Proposed for the owner's approval, 2026-11-06 (M2). Review date: start of M5 (Elasticsearch 2 retired); the rule itself stays for any later EOL middleware.
- Records a decision for: [SPEC-01 §3](../spec/01_manifest.md#english) (`image_build`, MC-15) · [SPEC-02 §3](../spec/02_installer_cli.md#english) (`build` of repo-local images) · [SPEC-03 §3.3](../spec/03_security_gate.md#english) (exception list)
- Related: [docs/decisions/README.md](README.md) · [ADR-03 Staged security gate](ADR-03_Staged_Security_Gate.md) · [ADR-06 Wiki frontend overlay](ADR-06_Wiki_Frontend_Overlay.md) · [DEMO-20 run 19](../demo/20_core_install_mac_studio.md#english) · [PR #33 review r1](../reviews/2026-11-06_RDM-developer-guide_PR33_Startup_Fixes_r1.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

The development environment must start on Apple Silicon (arm64) and on amd64 (the CPU type of ordinary PCs and servers; see [REF-01](../reference/REF-01_Glossary.md)) hosts ([SPEC-00 §4](../spec/00_overview.md#english)). The osf.io (the main part of GRDM: the website and its API; see [REF-01](../reference/REF-01_Glossary.md)) of today still needs Elasticsearch (the search engine inside GRDM; see [REF-01](../reference/REF-01_Glossary.md)) 2.x (retired at M5 with ES 8, [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md#english)). The only official image, `elasticsearch:2` on Docker (the tool that builds images and runs containers; see [REF-01](../reference/REF-01_Glossary.md)) Hub, is `linux/amd64` only; PR (a pull request, a proposed change reviewed before it is merged; see [REF-01](../reference/REF-01_Glossary.md)) #32 made Compose run it under emulation (the `build_platform` of SPEC-01).

Real install run 19 — the first cold start, with fresh volumes — showed the cost: the container burned two CPU cores for 38 minutes between `initializing ...` and `started`, while `osf_init` gave up waiting for the search engine after 5 minutes and the whole `up` failed. A trial of the official `elasticsearch-2.4.6.tar.gz` (27.3 MB, SHA-256 verified) on an arm64 `eclipse-temurin:8-jre` container reached `started` in 5 seconds. The slowness is the x86-64 image under Rosetta (Docker Desktop's amd64 emulation on Apple Silicon; see [REF-01](../reference/REF-01_Glossary.md)), not the program.

The same shape — an EOL (end of life: software its maker no longer fixes; see [REF-01](../reference/REF-01_Glossary.md)) program that only ships amd64 images — exists for other infra components (unoconv, sharejs, fakecas until M4) and may recur before M5.

### 2. Decision

1. **Manifest** (the file that lists every component with its pinned commit; see [REF-01](../reference/REF-01_Glossary.md)). An `infra` component may carry `image_build: {"context": "<repo-relative directory>", "tag": "<recipe version>"}` ([SPEC-01 §3](../spec/01_manifest.md#english), rule MC-15): the directory holds a `Dockerfile`, the tag names the recipe (bump it when the Dockerfile changes), a `note` says why the official image cannot be used and until which milestone, and `prebuilt_image` / `build_platform` are excluded. `base_image` and `base_image_digest` name the digest-pinned base the Dockerfile starts from.
2. **Build.** `grdm-dev build` builds such a component from the repository directory for the host platform (or `--platform`), tags it `grdm-dev/<id>:<tag>`, records it in the build report with status `built`, and `--push` publishes `ghcr.io/rcosdp/<id>:<tag>`; `compose render` writes that reference as `image:`, `scan` scans it like any other image. No clone, no integration repository: the component stays `infra`.
3. **Dockerfile rules.** The artefact is the upstream's official release (tarball, deb or jar) fetched by URL with a checksum that is verified in the build; the base image is digest-pinned; the fetch runs in a `--platform=$BUILDPLATFORM` stage so that `curl`, `sha256sum` and `tar` never run under emulation (tar fails with "Function not implemented" under Rosetta); the final stage only copies files, runs as uid 1000 and needs no writable root except declared `tmpfs`/volumes. The image is a development artefact: no plugins, no site-specific configuration.
4. **Scope.** First applied to `elasticsearch2` (`installer/images/elasticsearch2/`, tag `2.4.6-1`). The elasticsearch hardening exception (`read_only`) and the one-shot `elasticsearch_data_init` of PR #33 are removed: the native image runs as uid 1000 on a read-only root, like elasticsearch 6. Other amd64-only infra images stay under emulation until they become a start-up problem or reach their modernization milestone; each switch is one PR with its own run record.
5. **Retirement.** `target_image` keeps naming the milestone that removes the middleware (ES 2 → M5). A native build is a bridge, not a reason to keep EOL software.

### 3. Options considered

```toon
options[4]{option,cold_start,hardening,maintenance,chosen}:
  A,"official elasticsearch:2 under emulation (PR #32)","38 minutes on Apple Silicon","root + chown step, exception","none","no"
  B,"wait longer / larger timeouts","unchanged, only hidden","unchanged","none","no"
  C,"third-party arm64 images of ES 2","unknown provenance, unpinnable","unknown","depends on a stranger","no"
  D,"build natively from the official tarball on a pinned JRE (this ADR)","5 seconds","uid 1000, read-only, no exception","one Dockerfile per image, checksum pinned","yes"
```

### 4. Consequences

- Cold starts on Apple Silicon are bounded by the osf.io migrations and the ember build, not by a 40-minute search engine.
- Two fewer entries in `manifest/hardening.json` and one fewer one-shot service; the baseline report shrinks ([SPEC-03 §3.3](../spec/03_security_gate.md#english)).
- The repository now holds a Dockerfile for third-party software. It is a build recipe, not a fork: the artefact is upstream's, verified by checksum; Trivy (a scanner that reads our images and lists the holes it knows about; see [REF-01](../reference/REF-01_Glossary.md)) scans the resulting image like any other.
- CI (continuous integration: the checks that run automatically on every pull request; see [REF-01](../reference/REF-01_Glossary.md)) must build `image_build` components for both platforms (amd64 on the GitHub runner, arm64 on the Mac Studio runner, SPEC-02 §10) so a recipe change is caught before a developer hits it.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

開発環境は Apple Silicon（arm64）と amd64 のホストの両方で起動しなければならない（[SPEC-00 §4](../spec/00_overview.md#japanese)）。現在の osf.io はまだ Elasticsearch 2.x を必要とする（M5 で ES 8 に替えて退役。[POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md#japanese)）。唯一の公式イメージ Docker Hub の `elasticsearch:2` は `linux/amd64` のみで、PR #32 は Compose にエミュレーションで動かさせた（SPEC-01 の `build_platform`）。

実機第 19 回 — 新しいボリュームでの最初のコールドスタート — がその代償を示した。コンテナは `initializing ...` から `started` まで 38 分間 CPU 2 コアを使い続け、一方 `osf_init` は 5 分で検索エンジンを待つのを諦めて `up` 全体が失敗した。公式の `elasticsearch-2.4.6.tar.gz`（27.3 MB、SHA-256 検証済み）を arm64 の `eclipse-temurin:8-jre` コンテナで試すと 5 秒で `started` に達した。遅いのは Rosetta（Apple Silicon 上の Docker Desktop の amd64 エミュレーション。[REF-01](../reference/REF-01_Glossary.md)）下の x86-64 イメージであって、プログラムではない。

同じ形 — amd64 のイメージしか配布されない EOL のプログラム — は他の基盤部品（M4 までの unoconv・sharejs・fakecas）にもあり、M5 までにまた現れうる。

### 2. 決定

1. **manifest。** `infra` の部品は `image_build: {"context": "<リポジトリ相対のディレクトリ>", "tag": "<レシピの版>"}` を持てる（[SPEC-01 §3](../spec/01_manifest.md#japanese)、規則 MC-15）。ディレクトリには `Dockerfile` があり、tag はレシピの版（Dockerfile を変えたら上げる）、`note` には公式イメージが使えない理由とどの節目までかを書き、`prebuilt_image` と `build_platform` は併用できない。`base_image` と `base_image_digest` は Dockerfile が出発点にするダイジェスト固定のベースを指す。
2. **ビルド。** `grdm-dev build` はその部品をリポジトリのディレクトリからホストのプラットフォーム（または `--platform`）向けに組み、`grdm-dev/<id>:<tag>` のタグを付け、ビルド報告に `built` として記録し、`--push` では `ghcr.io/rcosdp/<id>:<tag>` へ公開する。`compose render` はその参照を `image:` に書き、`scan` は他のイメージと同じに検査する。clone も統合リポジトリも無く、部品は `infra` のままである。
3. **Dockerfile の規則。** 成果物は上流の公式リリース（tarball・deb・jar）で、URL から取得しビルド中にチェックサムを検証する。ベースイメージはダイジェスト固定。取得は `--platform=$BUILDPLATFORM` の段で行い、`curl`・`sha256sum`・`tar` をエミュレーション下で動かさない（tar は Rosetta 下で「Function not implemented」で失敗する）。最終段はファイルを写すだけで、uid 1000 で動き、宣言した `tmpfs`/ボリューム以外に書込可能なルートを要しない。イメージは開発用の成果物であり、プラグインもサイト固有の設定も持たない。
4. **範囲。** まず `elasticsearch2`（`installer/images/elasticsearch2/`、tag `2.4.6-1`）に適用する。PR #33 の elasticsearch の堅牢化例外（`read_only`）と一回限りの `elasticsearch_data_init` は取り除く。ネイティブのイメージは elasticsearch 6 と同じく uid 1000・読み取り専用ルートで動く。他の amd64 のみの基盤イメージは、起動の問題になるか近代化の節目に達するまでエミュレーションのままとし、切り替えは一つずつ PR と実機記録を伴って行う。
5. **退役。** `target_image` は引き続きそのミドルウェアを除く節目を指す（ES 2 → M5）。ネイティブビルドは橋であり、EOL ソフトウェアを残す理由ではない。

### 3. 検討した選択肢

```toon
options[4]{option,cold_start,hardening,maintenance,chosen}:
  A,"公式 elasticsearch:2 をエミュレーション（PR #32）","Apple Silicon で 38 分","root＋chown の段、例外あり","なし","いいえ"
  B,"もっと長く待つ／タイムアウトを伸ばす","変わらず、隠れるだけ","変わらず","なし","いいえ"
  C,"第三者の arm64 版 ES 2 イメージ","出自不明、固定不可","不明","他人次第","いいえ"
  D,"公式 tarball から固定 JRE 上にネイティブで組む（本 ADR）","5 秒","uid 1000・読み取り専用・例外なし","イメージごとに Dockerfile 一つ、チェックサム固定","はい"
```

### 4. 影響

- Apple Silicon のコールドスタートの上限は osf.io の migration と ember のビルドで決まり、40 分の検索エンジンではなくなる。
- `manifest/hardening.json` の項目が二つ減り、一回限りのサービスが一つ減る。基本対策の報告が小さくなる（[SPEC-03 §3.3](../spec/03_security_gate.md#japanese)）。
- リポジトリに第三者ソフトウェアの Dockerfile が入る。これはフォークではなくビルドのレシピで、成果物は上流のものをチェックサムで検証したもの。Trivy はできたイメージを他と同じに検査する。
- CI は `image_build` の部品を両プラットフォームで組まなければならない（amd64 は GitHub ランナー、arm64 は Mac Studio ランナー。SPEC-02 §10）。レシピの変更を開発者が踏む前に捕まえるためである。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| EOL (end of life) | Software whose maker no longer fixes it. | 作った人がもう直さないソフトウェア。 |
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| Rosetta | Apple's translator that lets x86-64 programs run on Apple Silicon; Docker Desktop can use it for amd64 containers. | x86-64 のプログラムを Apple Silicon で動かす Apple の翻訳機。Docker Desktop は amd64 コンテナにこれを使える。 |
| Checksum | A short fingerprint of a file; if one byte changes, the fingerprint changes. | ファイルの短い指紋。1 バイトでも変わると指紋も変わる。 |
| Digest | A checksum of a container image, so the same image is pulled every time. | コンテナイメージのチェックサム。毎回同じイメージが取れる。 |
| JRE | The part of Java needed to run programs, without the compiler. | Java のプログラムを動かすために必要な部分。コンパイラは含まない。 |
| Cold start | Starting with empty data: nothing cached, nothing initialised. | 空のデータからの起動。キャッシュも初期化済みのものも無い。 |
