# ADR-07 Native Builds of EOL Middleware / EOL ミドルウェアのネイティブビルド

> **Summary:** Some middleware the current GakuNin RDM needs (Elasticsearch 2.4.6 first) is end of life and only ships `linux/amd64` images. Running such an image under emulation on Apple Silicon is not merely slow: Elasticsearch 2 took 38 minutes to open its port on a fresh data directory (real install run 19), and the same program on a native arm64 JRE starts in 5 seconds. We decide to **build such images ourselves, natively for both architectures, from the official release artefact on a digest-pinned base**, declared in the manifest as `image_build: {context, tag}` with a Dockerfile under `installer/images/<id>/`, until the milestone that retires the middleware (M5 for Elasticsearch 2). The native image also runs as the hardening default (non-root, read-only), so the service's own hardening exception disappears (the owner-init one-shot stays, see §2.4).
> **概要:** 現在の GakuNin RDM が必要とするミドルウェアの一部（まず Elasticsearch 2.4.6）は EOL で、`linux/amd64` のイメージしか配布されていない。Apple Silicon でそれをエミュレーションで動かすのは「遅い」で済まない。Elasticsearch 2 は新しいデータディレクトリでポートを開くまで 38 分かかり（実機第 19 回）、同じプログラムは arm64 ネイティブの JRE なら 5 秒で起動する。**公式のリリース成果物からダイジェスト固定のベース上に、両アーキテクチャ向けのイメージを自分たちでネイティブに組む**ことを決める。manifest では `image_build: {context, tag}` として宣言し、Dockerfile は `installer/images/<id>/` に置き、そのミドルウェアを退役させる節目（Elasticsearch 2 は M5）まで続ける。ネイティブのイメージは堅牢化の既定（非 root・読み取り専用）で動くので、サービス自身の堅牢化の例外が消える（所有者初期化の一回限りサービスは残る。§2.4）。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.4 — 2026-11-10. **Learned:** a reproducible lockfile can preserve a fixable vulnerability, so the fix belongs in the lockfile of the component and is pinned here, and the upgrade path stays reachable before authentication because the browser client depends on the 4401 close (PR #37 review r2). ／ 再現可能なロックは修正可能な脆弱性も固定しうるので、修正はその部品のロックで行ってここで固定する。ブラウザのクライアントが 4401 の close に依存するため、upgrade の経路は認証の前でも到達できる（PR #37 レビュー r2）。
  0.3 — 2026-11-10. **Learned:** a rebuilt image is only as safe as the commit and dependency set it is built from, so the image must be tested at the authenticating commit with its lockfile and frozen modules, and a data-volume upgrade needs a restorable snapshot rather than an image reference to go back to (PR #37 review r1). ／ 組み直したイメージの安全性は、組む元のコミットと依存の組で決まる。認証を含むコミットとロックファイル、固定したモジュールでそのイメージを試験しなければならず、データボリュームの更新には戻る先のイメージ参照でなく復元できる snapshot が要る（PR #37 レビュー r1）。
  0.2 — 2026-11-10. **Learned:** a lower CVE count proves nothing about the client on the other end of a socket: a current LibreOffice scanned far cleaner yet could not serve MFR's 6.1 UNO client, so each image change needs its real client path proven. ／ CVE の件数が減ってもソケットの相手のクライアントについては何も証明しない。現行の LibreOffice は検出がはるかに少なかったが MFR の 6.1 の UNO クライアントには応えられなかった。イメージの変更ごとに実際のクライアントの経路を証明する必要がある。
  0.1 — 2026-11-06. **Learned:** a cold start measures what a warm host hides: an emulated JDK 8 service spends tens of minutes initialising every time its data directory is new, and no timeout makes that acceptable; the program itself starts in seconds when it runs natively (real install run 19, PR #33 review r1). ／ コールドスタートは温まったホストが隠すものを測る。エミュレーションされた JDK 8 のサービスはデータディレクトリが新しいたびに数十分を初期化に費やし、どんなタイムアウトでもそれは許容できない。プログラム自体はネイティブで動かせば数秒で起動する（実機第 19 回、PR #33 レビュー r1）。
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
3. **Dockerfile rules.** The artefact is the upstream's official release (tarball, deb or jar) fetched by URL with a checksum that is verified in the build; the base image is digest-pinned; the fetch runs in a `--platform=$BUILDPLATFORM` stage so that `curl`, `sha256sum` and `tar` never run under emulation (tar fails with "Function not implemented" under Rosetta); the final stage only copies files, runs as uid 1000 and needs no writable root except declared `tmpfs`/volumes. The image is a development artefact: no plugins, no site-specific configuration. `fakecas` is the recorded exception for a project with no release artefact: it is compiled from a checksum-verified commit archive with frozen `go.mod`/`go.sum`, and runs as uid 65534 as its service template always has.
4. **Scope.** First applied to `elasticsearch2` (`installer/images/elasticsearch2/`, tag `2.4.6-1`). The elasticsearch hardening exception (`read_only`) of PR #33 is removed: the native image runs as uid 1000 on a read-only root, like elasticsearch 6. The one-shot `elasticsearch_data_init` stays, now on the native image as an explicit root with `CAP_CHOWN` only, because the bind-mounted data directory belongs to the host user (or to uid 101 after PR #33) and image layers cannot change a mounted tree (review r1 R1-01); that step later became the generic `volume_owner_init` ([SPEC-03 §3.3](../spec/03_security_gate.md#english)). Other amd64-only infra images stay under emulation until they become a start-up problem or reach their modernization milestone; each switch is one PR with its own run record. `elasticsearch6` (`6.8.23-1`) and `fakecas` (`9a9ddd73b225-2`) moved on 2026-11-10 (§5); `elasticsearch6` also lost its `read_only` hardening entry.
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
- One fewer entry in `manifest/hardening.json` (the elasticsearch service itself); the baseline report shrinks ([SPEC-03 §3.3](../spec/03_security_gate.md#english)).
- The repository now holds a Dockerfile for third-party software. It is a build recipe, not a fork: the artefact is upstream's, verified by checksum; Trivy (a scanner that reads our images and lists the holes it knows about; see [REF-01](../reference/REF-01_Glossary.md)) scans the resulting image like any other.
- CI (continuous integration: the checks that run automatically on every pull request; see [REF-01](../reference/REF-01_Glossary.md)) must build `image_build` components for both platforms (amd64 on the GitHub runner, arm64 on the Mac Studio runner, SPEC-02 §10) so a recipe change is caught before a developer hits it.

### 5. Image vulnerability reduction (2026-11-10)

Counts are Trivy 0.75 `image --offline-scan` with the local database of 2026-11-05, CRITICAL/HIGH findings as reported, without the Python 3.13 port. "Before" images are amd64 except y-websocket and rabbitmq, which are arm64. Every "after" image was measured on both arm64 and amd64, with equal counts on each. The tested y-websocket (the real-time co-editing server for the Wiki; see [REF-01](../reference/REF-01_Glossary.md)) commit is `09eb0a9f4af623760a15e100790381560b9e8ce0`, the head of the integration repository's `security/ws-update` branch (`bf2cd67051025416de028f6edd16c83d3fc8ba79` plus `ws` 6.2.6 in the lockfile).

```toon
results[6]{image,before,after,outcome,proof}:
  elasticsearch6,37/236,2/50,"adopted: OSS 6.8.23 on Temurin 11 (image_build)","osf.io's django-elasticsearch-metrics wrote a template, documents and an aggregation on both architectures; a copy of a 6.3.1 data volume upgraded and validated; rollback demonstrated (§6)"
  fakecas,1/57,0/2,"adopted: pinned commit with current Go and frozen modules (image_build)","login form, ticket validation, login redirect, and 404 for an unknown ticket against postgres on both architectures; two uncached builds gave the same binary hash"
  y-websocket,1/12,0/0,"adopted: JWT-enforcing commit with ws 6.2.6, npm ci from its lockfile, no npm or yarn at run time, Node 24 LTS (build_dockerfile)","no, bad-signature, expired, wrong-document, no-exp, alg-none and duplicate tokens closed 4401 with zero frames; a valid token converged two Yjs providers; a missing secret refuses to start; both architectures"
  rabbitmq,0/7,0/7,"digest pinned; 3.13.7 is already the newest image of the 3-management tag","same image as the running one"
  unoconv,147/1140,147/1140,"blocked; candidate measured 1/73 was not adopted","see below"
  sharejs,394/1588,394/1588,"blocked; trial measured 3/51 was not adopted","see below"
```

A rejected y-websocket upgrade still passes `handleUpgrade` and is then closed with 4401, and this stays: a browser cannot read the reason of an HTTP 401 on a WebSocket upgrade, SPEC-04 C4 and S1 require 4401 with zero frames, and the wiki client's token recovery keys on that code. Refusing earlier would be a joint change to the client and SPEC-04; the two `ws` advisories on that path are fixed by 6.2.6. The two fakecas findings are `dgrijalva/jwt-go` and `labstack/echo` v3, which upstream's module requires and which have no fixed version in that line. The remaining elasticsearch6 findings are jars inside the 6.8.23 release (netty, jackson, snakeyaml, bouncycastle and Elasticsearch itself) plus `apt` in the JRE base; Elastic published no later 6.8 release (6.8.24 answers 404), and M5 removes this line.

**unoconv is blocked.** LibreOffice from Debian 12 (7.4) and Debian 13 (25.2) accepts MFR's connection, but every `loadComponentFromURL` from MFR's LibreOffice 6.1 UNO client ends with `Binary URP bridge disposed during call`, on arm64 and amd64, hardened or not, and even with no arguments. The same probe converts against the old image, and a client of the listener's own version converts against the hardened listener. The fix belongs to the client side (MFR on a newer LibreOffice, or the unoserver move planned for M4), so no recipe was added and the service keeps its image and its hardening entry.

**sharejs is blocked.** The unchanged dependency set installs on Node 22 and 24 and the HTTP/WebSocket server starts, but its mongodb 1.4.40 driver never calls back over TLS (`mongodb://…?ssl=true` against `requireSSL`): no connection error, no document written, no `sub` reply. The old image passes the same probe. Fixing it means replacing the driver underneath `livedb-mongo`, which is a code change rather than a rebuild; retirement remains a separate decision.

### 6. Upgrading an existing Elasticsearch 6.3.1 data volume

The data under `runtime/volumes/elasticsearch6_data` moves from 6.3.1 (default distribution) to 6.8.23 (OSS) when the new image starts on it. Reverting the image reference does not recover it: once 6.8.23 has written the directory, go back by restoring a snapshot taken before the upgrade ([Elastic 6.8 upgrade guide](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/setup-upgrade.html)). Metrics are development data, so a developer may also choose to discard the directory. Otherwise, with `E=http://<address of the node>:9200`:

1. **Record the old cluster.** `curl $E/` (version and `build_flavor`), `curl "$E/_cat/plugins?v"`, `curl "$E/_cat/templates?h=name"` and `curl "$E/_cluster/state/metadata?filter_path=metadata.licenses.license.type,metadata.ml.jobs,metadata.ml.datafeeds"`.
2. **Stop the writers.** Stop `web`, `api`, `admin` and `worker`, then `elasticsearch6`.
3. **Take and verify a snapshot.** Start a one-off `docker.elastic.co/elasticsearch/elasticsearch:6.3.1` with `--platform linux/amd64`, `--user 1000:1000`, the data directory mounted, an empty directory owned by uid 1000 mounted at `/snapshots`, and `-e discovery.type=single-node -e xpack.security.enabled=false -e path.repo=/snapshots`. Then `PUT $E/_snapshot/preupgrade` with `{"type":"fs","settings":{"location":"/snapshots/preupgrade"}}`, `POST $E/_snapshot/preupgrade/_verify`, and `PUT "$E/_snapshot/preupgrade/before-6-8?wait_for_completion=true"` with `{"indices":"*","include_global_state":true}`. Require `"state":"SUCCESS"` and `"failed":0`. Stop the container.
4. **Upgrade a disposable copy.** Copy the data directory to a new directory owned by uid 1000, start the 6.8.23 image on the copy as the `elasticsearch6` template does, and check the templates, the document counts and an aggregation. Only then start the real service on the real directory.
5. **On failure, restore to a clean 6.3.1.** Empty the data directory, start the one-off 6.3.1 container of step 3 on it, register the repository with `"readonly":true`, `POST "$E/_snapshot/preupgrade/before-6-8/_restore?wait_for_completion=true"` with `{"indices":"*","include_global_state":true}`, repeat the checks, and stay on the previous revision of this repository.

Demonstrated on 2026-11-10 with throwaway containers and volumes, never the running stack. The 6.3.1 cluster was the default distribution with x-pack modules, plugins `ingest-geoip` and `ingest-user-agent`, no ML jobs or datafeeds, and 15 X-Pack or Logstash templates beside the application's. Three documents written through osf.io's client were snapshotted (`SUCCESS`, 1 shard, 0 failed); a copy upgraded to 6.8.23 returned the template, 3 documents and the aggregation; a clean 6.3.1 restored from the snapshot returned the same. On 6.8.23 OSS the unknown `licenses` metadata is logged and skipped. The x-pack templates stay in the upgraded copy; nothing uses them. A cluster with ML jobs, security users or other X-Pack state was not tested, so step 1 decides whether this procedure applies.

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
3. **Dockerfile の規則。** 成果物は上流の公式リリース（tarball・deb・jar）で、URL から取得しビルド中にチェックサムを検証する。ベースイメージはダイジェスト固定。取得は `--platform=$BUILDPLATFORM` の段で行い、`curl`・`sha256sum`・`tar` をエミュレーション下で動かさない（tar は Rosetta 下で「Function not implemented」で失敗する）。最終段はファイルを写すだけで、uid 1000 で動き、宣言した `tmpfs`/ボリューム以外に書込可能なルートを要しない。イメージは開発用の成果物であり、プラグインもサイト固有の設定も持たない。`fakecas` はリリース成果物の無いプロジェクトとして記録した例外で、チェックサムを検証したコミットのアーカイブから、固定した `go.mod`/`go.sum` でコンパイルし、サービス定義のとおり uid 65534 で動く。
4. **範囲。** まず `elasticsearch2`（`installer/images/elasticsearch2/`、tag `2.4.6-1`）に適用する。PR #33 の elasticsearch の堅牢化例外（`read_only`）は取り除く。ネイティブのイメージは elasticsearch 6 と同じく uid 1000・読み取り専用ルートで動く。一回限りの `elasticsearch_data_init` は残し、ネイティブイメージを明示の root・`CAP_CHOWN` のみで動かす。bind マウントしたデータディレクトリはホストの利用者（PR #33 の後は uid 101）の所有で、イメージの層ではマウントした木を変えられないからである（レビュー r1 R1-01）。この段は後に汎用の `volume_owner_init` になった（[SPEC-03 §3.3](../spec/03_security_gate.md#japanese)）。他の amd64 のみの基盤イメージは、起動の問題になるか近代化の節目に達するまでエミュレーションのままとし、切り替えは一つずつ PR と実機記録を伴って行う。`elasticsearch6`（`6.8.23-1`）と `fakecas`（`9a9ddd73b225-2`）は 2026-11-10 に移行した（§5）。`elasticsearch6` の `read_only` の堅牢化項目も消えた。
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
- `manifest/hardening.json` の項目が一つ減る（elasticsearch サービス自身）。基本対策の報告が小さくなる（[SPEC-03 §3.3](../spec/03_security_gate.md#japanese)）。
- リポジトリに第三者ソフトウェアの Dockerfile が入る。これはフォークではなくビルドのレシピで、成果物は上流のものをチェックサムで検証したもの。Trivy はできたイメージを他と同じに検査する。
- CI は `image_build` の部品を両プラットフォームで組まなければならない（amd64 は GitHub ランナー、arm64 は Mac Studio ランナー。SPEC-02 §10）。レシピの変更を開発者が踏む前に捕まえるためである。

### 5. イメージの脆弱性削減（2026-11-10）

件数は Trivy 0.75 の `image --offline-scan`（ローカルのデータベースは 2026-11-05 版）による CRITICAL/HIGH の報告値で、Python 3.13 への移植は含まない。「前」のイメージは y-websocket と rabbitmq が arm64、それ以外は amd64。「後」のイメージはすべて arm64 と amd64 の両方で測り、件数は同じだった。試験した y-websocket のコミットは `09eb0a9f4af623760a15e100790381560b9e8ce0` で、統合リポジトリの `security/ws-update` ブランチの先頭である（`bf2cd67051025416de028f6edd16c83d3fc8ba79` にロックの `ws` 6.2.6 を加えたもの）。

```toon
results[6]{image,before,after,outcome,proof}:
  elasticsearch6,37/236,2/50,"採用: Temurin 11 上の OSS 6.8.23（image_build）","osf.io の django-elasticsearch-metrics が両アーキテクチャでテンプレート・文書・集計を実行。6.3.1 のデータボリュームの写しを更新して検証し、復旧も実証（§6）"
  fakecas,1/57,0/2,"採用: 固定コミットを現行の Go と固定したモジュールで組む（image_build）","両アーキテクチャで postgres に対しログイン画面、チケット検証、ログイン後の転送、未知のチケットの 404。キャッシュなしの 2 回のビルドでバイナリのハッシュが一致"
  y-websocket,1/12,0/0,"採用: ws 6.2.6 を含む JWT を強制するコミット、ロックファイルからの npm ci、実行時に npm・yarn 無し、Node 24 LTS（build_dockerfile）","トークン無し・署名不正・期限切れ・別文書・exp 無し・alg none・重複は 4401 で閉じフレーム 0。有効なトークンで 2 つの Yjs プロバイダが収束。秘密鍵無しでは起動拒否。両アーキテクチャ"
  rabbitmq,0/7,0/7,"ダイジェストを固定。3.13.7 は 3-management タグの最新イメージ","動作中のものと同じイメージ"
  unoconv,147/1140,147/1140,"阻害要因あり。候補の実測 1/73 は不採用","下記"
  sharejs,394/1588,394/1588,"阻害要因あり。試作の実測 3/51 は不採用","下記"
```

拒否された y-websocket の upgrade は `handleUpgrade` を通った後で 4401 で閉じ、この動作は維持する。ブラウザは WebSocket の upgrade に対する HTTP 401 の理由を読めず、SPEC-04 の C4 と S1 は 4401 とフレーム 0 を求め、wiki のクライアントのトークン回復はこのコードで動く。より前で拒否するにはクライアントと SPEC-04 を一緒に変える必要がある。その経路にある `ws` の勧告 2 件は 6.2.6 で修正した。fakecas の 2 件は上流のモジュールが要する `dgrijalva/jwt-go` と `labstack/echo` v3 で、その系統に修正版は無い。elasticsearch6 に残る検出は 6.8.23 のリリースに含まれる jar（netty・jackson・snakeyaml・bouncycastle・Elasticsearch 本体）と JRE ベースの `apt` である。Elastic は後続の 6.8 を出しておらず（6.8.24 は 404）、M5 でこの系統ごと除く。

**unoconv は阻害要因あり。** Debian 12（7.4）と Debian 13（25.2）の LibreOffice は MFR の接続を受けるが、MFR の LibreOffice 6.1 の UNO クライアントからの `loadComponentFromURL` はすべて `Binary URP bridge disposed during call` で終わる。arm64 でも amd64 でも、堅牢化の有無にかかわらず、引数が無くても同じである。同じ検証は旧イメージでは変換でき、リスナーと同じ版のクライアントは堅牢化したリスナーで変換できる。直す場所はクライアント側（MFR を新しい LibreOffice にするか、M4 予定の unoserver への移行）なので、レシピは追加せず、サービスのイメージと堅牢化の項目はそのままとする。

**sharejs は阻害要因あり。** 依存をそのままにすると Node 22 と 24 でインストールでき HTTP/WebSocket サーバーも起動するが、mongodb 1.4.40 ドライバーは TLS（`requireSSL` への `mongodb://…?ssl=true`）でコールバックを返さない。接続エラーも文書の書き込みも `sub` の応答も無い。旧イメージは同じ検証に合格する。直すには `livedb-mongo` の下のドライバーを置き換える必要があり、組み直しではなくコードの変更である。退役は別の判断として残す。

### 6. 既存の Elasticsearch 6.3.1 データボリュームの更新

新しいイメージを起動すると、`runtime/volumes/elasticsearch6_data` のデータは 6.3.1（default 配布）から 6.8.23（OSS）へ移る。イメージ参照を戻しても復旧にはならない。6.8.23 が一度ディレクトリに書いたら、戻るには更新前に取った snapshot を復元する（[Elastic 6.8 更新ガイド](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/setup-upgrade.html)）。メトリクスは開発用のデータなので、開発者はディレクトリを捨てることも選べる。そうしない場合は、`E=http://<ノードのアドレス>:9200` として次の手順による。

1. **旧クラスタを記録する。** `curl $E/`（版と `build_flavor`）、`curl "$E/_cat/plugins?v"`、`curl "$E/_cat/templates?h=name"`、`curl "$E/_cluster/state/metadata?filter_path=metadata.licenses.license.type,metadata.ml.jobs,metadata.ml.datafeeds"`。
2. **書き手を止める。** `web`・`api`・`admin`・`worker` を止め、次に `elasticsearch6` を止める。
3. **snapshot を取り確認する。** 一回限りの `docker.elastic.co/elasticsearch/elasticsearch:6.3.1` を `--platform linux/amd64`・`--user 1000:1000` で起動する。データディレクトリと、`/snapshots` に uid 1000 所有の空ディレクトリをマウントし、`-e discovery.type=single-node -e xpack.security.enabled=false -e path.repo=/snapshots` を渡す。`PUT $E/_snapshot/preupgrade` に `{"type":"fs","settings":{"location":"/snapshots/preupgrade"}}`、`POST $E/_snapshot/preupgrade/_verify`、`PUT "$E/_snapshot/preupgrade/before-6-8?wait_for_completion=true"` に `{"indices":"*","include_global_state":true}` を送り、`"state":"SUCCESS"` と `"failed":0` を確かめてコンテナを止める。
4. **使い捨ての写しを更新する。** データディレクトリを uid 1000 所有の新しいディレクトリへ写し、`elasticsearch6` のテンプレートと同じ設定で 6.8.23 のイメージを写しの上で起動し、テンプレート・文書数・集計を確かめる。その後で初めて本来のディレクトリでサービスを起動する。
5. **失敗したら空の 6.3.1 へ復元する。** データディレクトリを空にし、手順 3 の 6.3.1 のコンテナをその上で起動し、リポジトリを `"readonly":true` で登録し、`POST "$E/_snapshot/preupgrade/before-6-8/_restore?wait_for_completion=true"` に `{"indices":"*","include_global_state":true}` を送って同じ確認をし、本リポジトリの以前の版に留まる。

2026-11-10 に使い捨てのコンテナとボリュームで実証した。稼働中のスタックには触れていない。6.3.1 のクラスタは x-pack モジュールを持つ default 配布で、プラグインは `ingest-geoip` と `ingest-user-agent`、ML のジョブと datafeed は無く、アプリケーションのもののほかに X-Pack と Logstash のテンプレートが 15 個あった。osf.io のクライアントで書いた文書 3 件を snapshot し（`SUCCESS`、1 シャード、失敗 0）、6.8.23 へ更新した写しはテンプレート・文書 3 件・集計を返し、snapshot から復元した空の 6.3.1 も同じものを返した。6.8.23 OSS では未知の `licenses` メタデータはログに出て読み飛ばされる。x-pack のテンプレートは更新後の写しに残るが、使うものは無い。ML ジョブやセキュリティのユーザーなどの X-Pack の状態を持つクラスタは試験していないので、この手順が当てはまるかは手順 1 で判断する。

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
