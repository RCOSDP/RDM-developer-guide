# DEMO-20 Core Install on Mac Studio / Mac Studio でのコア導入記録

> **Summary:** What actually happened when `./installer/install.sh --yes --no-open --profile core` was run on the Mac Studio (Apple Silicon). One entry per run; nothing is edited after the fact.
> **概要:** Mac Studio（Apple Silicon）で `./installer/install.sh --yes --no-open --profile core` を実行したときに実際に起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.11 — 2026-11-06. **Learned:** the cold start passes once the one emulated service that could not start natively is built natively (ADR-07): 31 minutes from empty volumes to a scanned, reported environment, bounded by the ember build and the migrations. ／ ネイティブで起動できなかった唯一のエミュレーションのサービスをネイティブで組む（ADR-07）と、コールドスタートは通る。空のボリュームから検査・報告済みの環境まで 31 分で、上限は ember のビルドと migration。
  0.10 — 2026-11-06. **Learned:** a warm success is not a cold-start success: with fresh volumes the emulated Elasticsearch 2 took 38 minutes to open its port and the database initialisation gave up; the same program on a native arm64 JRE starts in 5 seconds, so EOL amd64-only middleware must be built natively instead of emulated (review r1 of PR #33 asked for the cold start). ／ 温まった状態の成功はコールドスタートの成功ではない。新しいボリュームではエミュレーション下の Elasticsearch 2 がポートを開くまで 38 分かかり、データベース初期化が諦めた。同じプログラムは arm64 ネイティブの JRE で 5 秒で起動するので、amd64 しか無い EOL ミドルウェアはエミュレーションでなくネイティブで組む（PR #33 のレビュー r1 がコールドスタートを求めた）。
  0.9 — 2026-11-06. **Learned:** the install command succeeds end to end on run 18; the scanners found what the staged gate (ADR-03) predicted for an EOL stack, so the number to beat at M4/M5 is now written down instead of guessed. ／ 第 18 回で導入コマンドが端から端まで成功した。スキャナーは段階化した門（ADR-03）が EOL スタックに予測したとおりの結果を出し、M4/M5 で下回るべき数が推測ではなく記録になった。
  0.8 — 2026-11-06. **Learned:** after the images, the application layer fails for installer reasons that only a real start reveals — settings keys read at import, Compose's stdin and tmpfs semantics, a memory budget larger than the Docker VM, and a database that nobody initialised; and an unhandled 500 in osf.io's development server leaks a database connection. ／ イメージの後、アプリケーション層は実際に起動しないと分からないインストーラー側の理由で失敗する。import 時に読まれる設定キー、Compose の stdin と tmpfs の意味、Docker VM より大きいメモリ予算、誰も初期化していないデータベース。そして osf.io の開発サーバーの未処理の 500 はデータベース接続を漏らす。
  0.7 — 2026-11-06. **Learned:** once every image builds, the next failures are per-image start-up facts under the hardening baseline and under Rosetta emulation; and a Docker Desktop bind directory lies about ownership (`chown` is a no-op, `test -w` fails, writes succeed), so a container must probe by doing, not by asking. ／ すべてのイメージが組めた後の失敗は、hardening 基準と Rosetta エミュレーションの下でのイメージごとの起動の事実である。また Docker Desktop の bind ディレクトリは所有権について嘘をつく（`chown` は無効、`test -w` は失敗、書込は成功）ので、コンテナは尋ねるのではなく実際に試して確かめなければならない。
  0.6 — 2026-11-06. **Learned:** when a component is an overlay, its dependency manifest can drift from the base it is applied to; the base's new modules then fail to resolve inside the overlay's lock file, so SPEC-05 integration must diff the two manifests every week. ／ 部品がオーバーレイのとき、その依存一覧は重ねる先の基底からずれうる。基底が新しく使うモジュールはオーバーレイ側のロックファイルの中で解決できなくなるため、SPEC-05 の統合では毎週二つの一覧の差分を取らなければならない。
  0.5 — 2026-11-06. **Learned:** a repository can be an overlay rather than a service; the installer must know the shape of each component (built, prebuilt, overlay) before it can build anything; and, independently, a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ リポジトリはサービスではなくオーバーレイであることがある。インストーラーは組む前に各部品の形（built・prebuilt・overlay）を知っていなければならない。また別に、用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
- Version / 版: 0.4 — 2026-11-06. **Learned:** a repository can be an overlay rather than a service; the installer must know the shape of each component (built, prebuilt, overlay) before it can build anything. ／ リポジトリはサービスではなくオーバーレイであることがある。インストーラーは組む前に各部品の形（built・prebuilt・overlay）を知っていなければならない。
- Version / 版: 0.4 — 2026-11-06. **Learned:** a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ 用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
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

Host (from `grdm-dev doctor`): macOS 27.2, arm64 (the CPU type of Apple Silicon, the chips Apple puts in its Macs since 2020; see [REF-01](../reference/REF-01_Glossary.md)), 128 GiB memory, Docker (the tool that builds images and runs containers; see [REF-01](../reference/REF-01_Glossary.md)) 29.5.2, Compose 5.6.0, buildx (Docker's helper that builds one image for several kinds of computer; see [REF-01](../reference/REF-01_Glossary.md)) present. Supported, Docker OK.

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
- The EOL (end-of-life: no longer fixed by their makers; see [REF-01](../reference/REF-01_Glossary.md)) base images (see [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)) are not only a security problem but a build problem on Apple Silicon.

Decision taken: components whose base cannot be built for arm64 (modular-file-renderer, ember-osf-web, cas-overlay) get `build_platform: linux/amd64` in the manifest ([SPEC-01](../spec/01_manifest.md)) and run under emulation until M4 modernizes them. Run 2 will be recorded below after the review fixes land.

### Run 2 — 2026-11-05, branch `feat/m2-installer` (after review fixes r1, commit 3149c76 + 1c2a925)

Same host. Changes since run 1: `build_platform: linux/amd64` for modular-file-renderer, ember-osf-web and cas-overlay; two networks (`grdm` internal, `grdm-edge` publishing); PostgreSQL (the main database; see [REF-01](../reference/REF-01_Glossary.md)) 9.6 `auth-host=md5`.

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

Decision taken: [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md). The manifest marks wiki-frontend as `overlay_of: osf.io`; `build` creates a merged context (osf.io checkout + overlay files) and builds a bundle-builder image; `compose render` adds a one-shot `wiki_assets` service that copies the bundle into a named volume mounted read-only by the osf.io services. The osf.io image itself stays built from its own Dockerfile. Run 5 is recorded below.

### Run 5 — 2026-11-06, develop 9b1b643 (after PR #30, wiki-frontend as overlay)

Same host. Changes since run 4: wiki-frontend is `overlay_of: osf.io` (ADR-06); `build` assembles the merged context and `compose render` adds `wiki_static_init` and `wiki_assets`.

```toon
run5:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 30 (image build failed)
  steps[5]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok (fakecas port 8080 held by another process; 8081 chosen)"
    build,30,failed
  images[6]{component,platform,status,note}:
    osf.io,linux/arm64,built,cached (356a997eb5fe)
    waterbutler,linux/arm64,built,cached (e9b1ac266374)
    modular-file-renderer,linux/amd64,built,cached (dac70e2209f9)
    ember-osf-web,linux/amd64,prebuilt,cached pull
    cas-overlay,linux/amd64,prebuilt,cached pull
    wiki-frontend,linux/arm64,build-failed,"overlay context assembled; failed at Dockerfile step 85 of 86: webpack 5.93.0 stopped with 2 errors: osfHelpers.js and comment.js require linkify-html, absent from the overlay's package.json"
```

What this proves:

- The overlay mechanism works up to the bundle step: the merged context (osf.io checkout + wiki-frontend files, wiki-frontend Dockerfile) is assembled, yarn installs from the overlay lock file, and webpack runs over the osf.io JavaScript.
- The remaining failure is an *integration drift* between two upstreams, not an installer defect: RDM-osf.io develop upgraded linkifyjs 2 → 4 and added linkify-html on 2026-11-01, while the wiki-frontend overlay's `package.json` / `yarn.lock` dated from 2025-06. Because the overlay's lock file wins, the osf.io code could not resolve the new module.

Decision taken: the fix belongs in the integration repository RDM-wiki-frontend-dev2027 (PR #2: linkify-html and sift added; linkifyjs, bootstrap-datepicker, highlight.js and less aligned with osf.io develop; yarn.lock regenerated inside node:21-alpine). Verified before the PR: the same overlay context with the synced files built on this host with `docker buildx build --platform linux/arm64` (webpack 5.93.0, 0 errors, 4 warnings: 1 about the unset `mode`, 3 performance recommendations) and the image holds `website/static/public/js/wiki-edit-page.<chunkhash>.js`, which is what `wiki_assets` copies. After the merge, the manifest `integration_sha` was updated (PR #31) and runs 6–8 are recorded below. Lesson for [SPEC-05](../spec/05_upstream_tracking.md#english): an overlay's dependency manifest must be diffed against its base at every weekly integration.

### Runs 6–8 — 2026-11-06, develop 757dc37 + PR #32 and PR #33 branches

Same host. Three short runs, each stopping one step later than the one before.

```toon
run6:
  branch: develop 757dc37 (wiki-frontend integration_sha cd96330f after RDM-wiki-frontend-dev2027 PR #2)
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 40 (docker compose up exited 1)
  build: "all six components passed for the first time (wiki-frontend overlay built; osf.io, waterbutler, mfr cached; ember and cas prebuilt)"
  up: "`elasticsearch:2` pull failed: no matching manifest for linux/arm64"
run7:
  branch: fix/infra-amd64-platform (PR #32: build_platform linux/amd64 on elasticsearch2, elasticsearch6, sharejs, unoconv, fakecas)
  result: exit 40 (docker compose up exited 1)
  up: "all nine infra images pulled (the five amd64-only ones under platform pinning); then the bind volumes failed to mount because this run was started from a worktree under /private/tmp, outside Docker Desktop's shared paths — an operator error, not an installer defect; torn down with `docker compose down -v`"
run8:
  branch: fix/infra-amd64-platform, started from the main checkout
  result: exit 40 (docker compose up exited 1)
  up: "16 of 21 services created; postgres, mongo, rabbitmq, redis, elasticsearch6, fakecas, wb, wb_worker, mfr up; four failures below; web/api/admin/worker never started because they wait for wiki_assets"
  failures[4]{service,symptom,cause,fix}:
    wiki_assets,"exit 1: /wiki_static is not writable by 1000","Docker Desktop for macOS presents a bind directory as root:root, ignores `chown`, yet lets any uid write; `test -w` is therefore a false negative","real write probe (create and delete a marker file) instead of `test -w` (PR #33)"
    cas,"restart loop: Could not create local repository at /root/.m2repo","the prebuilt distribution image starts `mvn jetty:run` with its Maven repository under /root (0700) and writes target/ at start; user 1000:1000 and read-only root block both","hardening exception for cas (user, read_only; no capability) until M4 bakes the war (PR #33)"
    elasticsearch,"restart loop: runtime: failed to create new OS thread (have 2 already; errno=22)","gosu in the EOL elasticsearch:2 image is an old Go binary that aborts under Rosetta (Docker Desktop's amd64 emulation on Apple Silicon)","run as the image's elasticsearch user (uid 101) so the entrypoint skips chown and gosu; the exception shrinks to read_only only (PR #33)"
    unoconv,"restart loop: chown: changing ownership of '/home': Operation not permitted","the entrypoint runs `chown -R www-data /home` as root with every capability dropped","CAP_CHOWN added to the unoconv exception (PR #33)"
```

What this proves:

- The build stage is done for the core profile on Apple Silicon: six components, three built locally, two prebuilt, one overlay.
- `up` now fails only on how individual EOL images start under two constraints they were never written for: the hardening baseline (non-root, read-only, no capabilities) and amd64 emulation through Rosetta. Each failure is an image-specific fact recorded in `manifest/hardening.json` with a review date and a modernization target.
- Docker Desktop's file sharing changes the meaning of ownership tests inside containers; a probe must try the real operation.

### Runs 9–12 — 2026-11-06, branch fix/run8-startup (PR #33), started from the main checkout

Same host. Each run fixed what the previous one exposed; `build` passed every time (all cached).

```toon
run9:
  fixes_applied: "wiki_assets write probe; elasticsearch as uid 101; unoconv CAP_CHOWN; cas exception"
  result: exit 40 (not healthy after 300s: web, api, admin, worker, ember_osf_web)
  state: "17 of 21 up; wiki_assets exited 0 (bundle copied); web KeyError EXTERNAL_EMBER_APPS['preprints']; api/admin/worker `OSError: [Errno 25] Not a tty` from invoke's stdin thread; ember still building"
run10:
  fixes_applied: "local.py gains preprints/reviews keys; stdin_open on web/api/admin/worker"
  result: exit 40 (not healthy after 300s)
  state: "web/api/worker `Read-only file system: /code/website/static/built/nodeCategories.json`; api/admin/worker `ModuleNotFoundError: debug_toolbar` (DEBUG_MODE=True imports a dev-only package the image lacks); ember OOM-killed twice at its 6.3 GiB limit; docker info shows the Docker VM has 47 GiB while the budget was scaled from the host's 128 GiB"
run11:
  fixes_applied: "tmpfs on website/static/built; DEBUG_MODE=False; ember weight 4, 8 GiB floor, JOBS=2; two-pass memory scaling capped by the Docker VM; up timeout 900 s"
  result: exit 40 (not healthy after 900s: web, api, admin, worker, ember_osf_web)
  state: "web/api/admin/worker `PermissionError` on the same file: Compose's short `tmpfs` entry mounts 0755 root-owned (docker run --tmpfs gives 1777); ember building without OOM"
run12:
  fixes_applied: "tmpfs entries rendered with :mode=1777"
  result: exit 40 (not healthy after 900s: web, api, admin, ember_osf_web)
  state: "worker healthy; web answers 500: `relation \"osf_institution\" does not exist` (fresh database, no migrations); each 500 leaked one postgres connection of the development server until `FATAL: too many clients already` (98 of 100 held by web); ember served HTTP 200 about 25 minutes after its start"
```

What this proves:

- Everything below the osf.io application starts on Apple Silicon under the hardening baseline: 17 services up, both wiki one-shots exited 0 with the bundle in the volume.
- Three classes of defect were in the installer, not in the images: generated settings missing keys upstream code reads at import; Compose details (stdin, tmpfs mode, memory budget vs Docker VM); and the absence of a database initialisation step that upstream's README leaves to the operator.
- The osf.io development server leaks a database connection on every request that ends in an unhandled error; `max_connections=500` is a safety margin, the real fix is to make `/` not fail.

Decisions taken (PR #33, [SPEC-02 §4 and §7](../spec/02_installer_cli.md#english)): a one-shot `osf_init` (migrate, institutions, OAuth scopes) that web/api/admin/worker wait for; ember-osf-web builds its `dist/` once into the named volume with a fingerprint of its URL settings and serves it with `ember serve --path` (first build 10–25 minutes under emulation, later starts seconds); ember's backend URLs come from the published loopback ports and `{{AUTH_URL}}`; `up` waits 900 s by default. Runs 13–18 are recorded below.

### Run 13 — 2026-11-06, branch fix/run8-startup with `osf_init`

```toon
run13:
  result: exit 40 (docker compose up exited 1: service "osf_init" didn't complete successfully)
  osf_init: "`manage.py migrate` and `scripts.populate_institutions -e test -a` succeeded at the first attempt (postgres and the emulated elasticsearch:2 were already up from run 12); `scripts.register_oauth_scopes` failed with `Read-only file system: /code/logs/register_oauth_scopes.py.<timestamp>.log` — scripts/utils.py adds a per-run file logger under /code/logs"
  fix: "tmpfs /code/logs on osf_init, web, api, admin and worker (run 14)"
```

### Run 14 — 2026-11-06, with tmpfs /code/logs

```toon
run14:
  result: exit 40 (not healthy after 900s: web, api, admin, ember_osf_web)
  osf_init: "exited 0 (migrate, institutions, OAuth scopes)"
  web: "HTTP 500 on `/`: PROXY_EMBER_APPS forwards the root page to ember_osf_web, which was still building (ConnectionError to ember_osf_web:4200); one postgres connection held, no leak"
  api_admin: "`DatabaseWrapper objects created in a thread can only be used in that same thread`, also without autoreload: api/base/wsgi.py monkey-patches gevent when website.settings.DEBUG_MODE is False (set so in run 11 to avoid debug_toolbar); SECURE_MODE = not DEBUG_MODE would also have switched the servers to TLS had local.py not pinned it to False"
  fix: "DEBUG_MODE back to True; Django DEBUG = False per project through api_local.py and a new admin_local.py (mounted at admin/base/settings/local.py); health probes web at /login/, which renders without ember (run 15)"
```

### Run 15 — 2026-11-06, DEBUG_MODE restored, per-project DEBUG off, web probed at /login/

```toon
run15:
  result: "exit 40 — `up` passed (0, ok) for the first time; `health --network` failed (40): not healthy web/api/admin, see below"
  ember_osf_web: "served HTTP 200 about 13 minutes after its start (dist built into the volume); web `/` then answered 200 as well"
  api: "the running container kept the failed process from run 14 because only a mounted file changed (Compose recreates nothing); after `docker restart` it answered 302 on `/`"
  admin: "still `ModuleNotFoundError: debug_toolbar`: admin/base/settings/defaults.py appends debug_toolbar and nplusone to INSTALLED_APPS and MIDDLEWARE at import, reading DEBUG_MODE before local.py runs, so `DEBUG = False` alone is too late; then `400 DisallowedHost` for 127.0.0.1"
  fix: "admin_local.py strips the two apps and middlewares and adds 127.0.0.1/localhost/admin to ALLOWED_HOSTS; after re-render and restart admin answered 302 (run 16 is the clean run)"
```

### Run 16 — 2026-11-06, clean run with every fix: `up` passes without manual repairs

```toon
run16:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 40 (stopped at `health --network`)
  steps[7]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok (memory budget uses the Docker VM's 47.0 GiB, not the host's 128.0 GiB; ember and fakecas keep their ports)"
    build,0,"ok (all cached)"
    up,0,"ok — ready: http://127.0.0.1:5000/ (22 services; the three one-shots exited 0)"
    "health --network",40,"failed: `ControlCe listens on *:5000 (not loopback; project port, owner not visible)`"
```

What this proves:

- The core profile starts end to end on Apple Silicon under the hardening baseline, and `up` declares it ready on the loopback URL. Milestone M2's "one command" now reaches the application.
- The `--network` check found a wildcard listener on port 5000 that is not ours: macOS's AirPlay Receiver (ControlCenter) binds `*:5000` and `*:7000`; our `web` is bound to `127.0.0.1:5000` beside it and answers (the kernel prefers the specific address). The check treated any non-loopback listener on a project port as a failure.

Decision taken: `health --network` keeps failing for listeners that belong to Docker (our published ports leaking to a non-loopback address, [ADR-02](../decisions/ADR-02_Network_Model.md)) and for a wildcard listener on a project port whose owner is not visible (fail closed); a *named* foreign process on a project port is reported as a warning row (`foreign-listener`) so the operator can move the port with `GRDM_PORT_<SERVICE>` if they want to. Run 17 is recorded below.

### Run 17 — 2026-11-06, foreign listeners reported as warnings: `up` and `health --network` pass, `scan` starts

```toon
run17:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 51 (stopped at `scan`: semgrep not found on PATH)
  steps[8]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok (all cached)"
    up,0,"ok — ready: http://127.0.0.1:5000/"
    "health --network",0,"ok with one warning: foreign-listener ControlCe on *:5000 (macOS AirPlay Receiver)"
    scan,51,"failed: semgrep not found on PATH; trivy 0.75.0 scanned 25 targets first"
  trivy_findings[4]{severity,count}:
    CRITICAL,1894
    HIGH,8620
    MEDIUM,10047
    LOW,3955
  trivy_problems: "sbom/scan of src/RDM-cas-overlay-dev2027 rc 1 (prebuilt component, no checkout); sbom/scan of the repository rc 1"
```

What this proves:

- The first two gates of M2 are passed on the real host: one command brings the core profile up and the loopback-only rule holds.
- The vulnerability count of the EOL images (Python 3.5/3.6, node 8/12, JDK 8, ES 2/6, mongo 3.4) is what [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) expected for M1–M3: report and allow-list now, HIGH stops at M4, zero CRITICAL/HIGH at M5.
- `scan` has two defects of its own: Semgrep (a tool that reads source code looking for dangerous patterns; see [REF-01](../reference/REF-01_Glossary.md)) is not installed by the bootstrap although SPEC-03 runs it locally, and Trivy (a scanner that reads our images and lists the holes it knows about; see [REF-01](../reference/REF-01_Glossary.md)) is pointed at a source directory that a prebuilt component never clones.

Decision taken: the bootstrap installs Semgrep into the same `.venv` as `grdm-dev` and `scan` looks for tools next to its own interpreter; Trivy skips the source directory of prebuilt components and reports why a target was skipped. Run 18 is recorded below (exit 0).

### Run 18 — 2026-11-06, Semgrep in `.venv`, Trivy offline and target-aware: **the whole command succeeds**

```toon
run18:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 0 — "GakuNin RDM developer environment is ready: http://127.0.0.1:5000/"
  steps[9]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok (ports kept; memory budget from the Docker VM's 47.0 GiB)"
    build,0,"ok (all cached)"
    up,0,"ok — 22 services, ready on the loopback URL"
    "health --network",0,"ok (warning: foreign-listener ControlCe on *:5000)"
    scan,0,"ok — gate report-only: pass"
    report,0,ok
  scan_tools[4]{tool,version,targets,result}:
    trivy,0.75.0,22,"ok (skipped: stale checkouts of the prebuilt cas-overlay and ember-osf-web, the assembled _overlay/ context)"
    semgrep,1.184.0,4,ok
    gitleaks,8.30.1,1,ok
    zap,stable,3,ok
  findings_by_severity[5]{severity,trivy,zap,total}:
    CRITICAL,1835,0,1835
    HIGH,8290,1,8291
    MEDIUM,9763,9,9772
    LOW,3886,13,3899
    INFO,0,5,5
  milestone_in_report: "M1 — manifest/milestone.json is owner-maintained (SPEC-03 §5.2) and still says M1; the gate rule is report-only either way"
  allow_list: "0 entries, 0 allow-listed; 10126 findings over the M4 threshold (HIGH or above) are reported, not blocking, at M2"
```

What this proves:

- **M2's one-command install works on the Mac Studio**: eighteen runs after the first attempt, `./installer/install.sh --yes --no-open --profile core` goes from a clean shell to a ready URL, through the loopback check, the scanners and the report, with exit 0.
- Every stop between run 1 and run 18 was a fact about an EOL image or an installer detail that only a real start could reveal; each is recorded above with its fix and its document.
- The vulnerability baseline of the EOL stack is now measured: Trivy alone reports 1835 CRITICAL and 8290 HIGH findings (ZAP adds 1 HIGH), almost all from the images (Python 3.5/3.6, node 8/12, JDK 8, Elasticsearch 2/6, mongo 3.4). This is the number M4 and M5 must drive to zero; the allow-list stays empty rather than hiding it.

Next on M2: the Playwright (a tool that drives a real browser to test web pages; see [REF-01](../reference/REF-01_Glossary.md)) acceptance suite (C1–C6) against this running stack, and the osf.io wiki editor page wiring (C4) in RDM-osf.io-dev2027.

### Run 19 — 2026-11-06, cold start after the review-r1 fixes (volumes removed, `runtime/` recreated)

```toon
run19:
  preparation: "`docker compose down -v`; runtime/ moved aside (images kept)"
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 40 (docker compose up exited 1: service "osf_init" didn't complete successfully)
  steps[6]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,"ok (new runtime/.env)"
    "compose render",0,"ok (fakecas 8080 busy → 8081; budget from the 47 GiB VM)"
    build,0,"ok (all cached)"
    up,40,"failed after 11 minutes"
  one_shots[4]{service,result}:
    elasticsearch_data_init,"exited 0 (chown 101:101; on Docker Desktop the chown is a no-op and the directory is writable anyway)"
    wiki_static_init,"exited 0"
    wiki_assets,"exited 0 (bundle copied)"
    osf_init,"exited 1: migrate ran all migrations on the empty database; populate_institutions then failed 30 times in 5 minutes — Elasticsearch 2 refused connections"
  elasticsearch2: "the container was running at 200 % CPU but had not opened port 9200: the EOL elasticsearch:2 image (JDK 8, linux/amd64) under Rosetta logged `initializing ...` at 03:31:52 and `started` at 04:09:57 — 38 minutes of start-up"
  native_trial: "the official elasticsearch-2.4.6 tarball (27.3 MB, sha256 5f7e4bb7…cfc6f) on an arm64 eclipse-temurin:8-jre container: `initialized` and `started` 5 seconds after launch"
```

What this proves:

- The cold start exposes the one remaining emulation cost that no timeout can hide: a JDK 8 service under Rosetta takes about 40 minutes to initialise, every time its data directory is new, and the whole stack waits for it.
- Run with a native arm64 JRE the same Elasticsearch 2.4.6 starts in seconds; the problem is the x86-64 image, not the program.

Decision taken: for this PR, `osf_init` waits up to 30 minutes for Elasticsearch and ember-osf-web no longer depends on web/api, so its own long build runs in parallel; run 20 continued the same cold start and passed `up` (below). For the next PR: build a multi-architecture `grdm-dev/elasticsearch2` image from the official tarball on a digest-pinned Temurin 8 JRE (checksum verified, non-root, no owner-init container) and record the rule in an ADR — EOL middleware that only ships amd64 images is built natively for arm64 until the milestone that retires it.

### Run 20 — 2026-11-06, the same cold start continued once Elasticsearch had started

```toon
run20:
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 51 (stopped at `scan`: semgrep incomplete)
  steps[8]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env from run 19)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok (cached)"
    up,0,"ok — ready: http://127.0.0.1:5000/ on the fresh volumes: osf_init completed (migrations already applied in run 19, institutions imported once Elasticsearch answered), ember built its dist into the new volume"
    "health --network",0,"ok (warning: foreign-listener ControlCe on *:5000)"
    scan,51,"semgrep reported 148 errors: per-file rule timeouts (default 5 s) — all of them in `runtime.run18-123040/`, the run-18 runtime moved aside inside the repository for this cold start (only `runtime/` was git-ignored, and Semgrep follows .gitignore); the scan is marked incomplete and the gate fails closed"
  rerun_after_fix: "`grdm-dev scan` and `grdm-dev report` on the same stack after moving that directory out of the repository, adding `runtime.*/` to .gitignore and letting Semgrep treat rule timeouts as coverage warnings: scan exit 0 (gate report-only: pass; trivy/semgrep/gitleaks/zap all ok; the same 1835/8291/9772/3899/5 totals as run 18), report exit 0"
```

What this proves:

- With Elasticsearch finally up, the cold start completes through `up` and the loopback check: the database initialisation, the wiki bundle and the ember build all work from empty volumes.
- The cold start therefore completes end to end: `up`, `health --network`, `scan` and `report` all exit 0 on fresh volumes once Elasticsearch has started. The `scan` stop was self-inflicted (an operator's copy of `runtime/` inside the repository) and exposed two hardening points that are now in place: `runtime.*/` is ignored, and a Semgrep rule timeout is recorded as a coverage warning instead of failing the gate closed.

### Run 21 — 2026-11-06, cold start with the native Elasticsearch 2 image (ADR-07): **30 minutes from empty volumes to ready, exit 0**

```toon
run21:
  preparation: "`docker compose down -v`; runtime/ moved out of the repository (images kept); branch feat/native-elasticsearch2-image on develop f37a029"
  command: ./installer/install.sh --yes --no-open --profile core
  result: exit 0 — "GakuNin RDM developer environment is ready: http://127.0.0.1:5000/" (04:53:51 → 05:24:34 UTC, 30 min 43 s)
  steps[9]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,"ok (new runtime/.env)"
    "compose render",0,ok
    build,0,"ok — grdm-dev/elasticsearch2:2.4.6-1 built natively from installer/images/elasticsearch2 (cached layers), the rest cached"
    up,0,"ok — containers created 04:54:40; elasticsearch `started` 04:54:49 (6 s after its container started); osf_init exited 0 at 04:59:45 (all migrations + institutions + OAuth scopes, 5 min); web/api/admin/worker started 04:59:46; ember served at 05:18:54 (24 min build, in parallel)"
    "health --network",0,"ok (warning: foreign-listener ControlCe on *:5000)"
    scan,0,"ok — gate report-only: pass; trivy 22 targets, semgrep 4, gitleaks 1, zap 3; no timeouts"
    report,0,ok
  trivy_totals_vs_run_18[4]{severity,run18_trivy,run21_trivy}:
    CRITICAL,1835,1769
    HIGH,8290,8030
    MEDIUM,9763,9550
    LOW,3886,3676
  elasticsearch2_image: "grdm-dev/elasticsearch2:2.4.6-1 — 59 findings (2 HIGH, 52 MEDIUM, 5 LOW) from the Elasticsearch 2.4.6 jars and the Temurin 8 base; the Docker Hub elasticsearch:2 image it replaces carried the bulk of the difference above"
```

What this proves:

- A **cold start works end to end**: with nothing but the images cached, one command reaches a ready, scanned, reported environment in 31 minutes on Apple Silicon. The remaining wall time is the ember build (24 min, now in parallel) and the osf.io migrations (5 min).
- The native Elasticsearch 2 starts in 6 seconds where the emulated one needed 38 minutes (run 19), runs as uid 1000 on a read-only root with no hardening exception and no owner-init container, and carries fewer known vulnerabilities than the official amd64 image.
- Milestone M2's install criterion ([status board](../status/README.md#english)) is met on the Mac Studio for the core profile, warm and cold. What remains for M2 is the Playwright acceptance.

Evidence (run 1): full log kept in the session scratchpad only (contains package download noise, no secrets). The `runtime/` directory on the Mac Studio holds `.env` (0600), the rendered Compose file and two built images; it is git-ignored.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 第 1 回 — 2026-11-05、ブランチ `feat/m2-installer`（PR #21、レビュー修正前）

ホスト（`grdm-dev doctor` より）: macOS 27.2、arm64（2020 年から Apple が Mac に入れているチップ Apple Silicon の CPU の種類。[REF-01](../reference/REF-01_Glossary.md)）、メモリ 128 GiB、Docker（イメージを作りコンテナを動かす道具。[REF-01](../reference/REF-01_Glossary.md)）29.5.2、Compose 5.6.0、buildx（一つのイメージを何種類かの計算機向けに作る Docker の助手。[REF-01](../reference/REF-01_Glossary.md)）あり。対応ホスト、Docker 正常。

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
- EOL（end of life。作った人がもう直さない。[REF-01](../reference/REF-01_Glossary.md)）のベースイメージ（[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)）は安全性の問題だけでなく、Apple Silicon ではビルドの問題でもある。

決めたこと: arm64 で組めない部品（modular-file-renderer、ember-osf-web、cas-overlay）は manifest に `build_platform: linux/amd64` を持たせ（[SPEC-01](../spec/01_manifest.md)）、M4 で近代化するまでエミュレーションで動かす。第 2 回はレビュー修正の反映後に下へ追記する。

### 第 2 回 — 2026-11-05、ブランチ `feat/m2-installer`（レビュー r1 対応後、コミット 3149c76 ＋ 1c2a925）

同じホスト。第 1 回からの変更: modular-file-renderer・ember-osf-web・cas-overlay に `build_platform: linux/amd64`、ネットワークを二つ（内部の `grdm` と公開用の `grdm-edge`）、PostgreSQL（主なデータベース。[REF-01](../reference/REF-01_Glossary.md)）9.6 の `auth-host=md5`。

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

決めたこと: [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md)。manifest で wiki-frontend を `overlay_of: osf.io` とし、`build` は重ねたコンテキスト（osf.io のチェックアウト＋オーバーレイ）から束を作るイメージを組み、`compose render` は一回限りの `wiki_assets` サービスを加えて束を名前付きボリュームへ写し、osf.io のサービスが読み取り専用でマウントする。osf.io のイメージ自体は従来どおり自分の Dockerfile で組む。第 5 回は下に記した。

### 第 5 回 — 2026-11-06、develop 9b1b643（PR #30 マージ後、wiki-frontend はオーバーレイ）

同じホスト。第 4 回からの変更: wiki-frontend は `overlay_of: osf.io`（ADR-06）。`build` が重ねたコンテキストを組み立て、`compose render` が `wiki_static_init` と `wiki_assets` を加える。

```toon
run5:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 30（イメージのビルド失敗）"
  steps[5]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok（fakecas の 8080 番は別プロセスが使用中のため 8081 番を選択）"
    build,30,failed
  images[6]{component,platform,status,note}:
    osf.io,linux/arm64,built,キャッシュ（356a997eb5fe）
    waterbutler,linux/arm64,built,キャッシュ（e9b1ac266374）
    modular-file-renderer,linux/amd64,built,キャッシュ（dac70e2209f9）
    ember-osf-web,linux/amd64,prebuilt,取得済みキャッシュ
    cas-overlay,linux/amd64,prebuilt,取得済みキャッシュ
    wiki-frontend,linux/arm64,build-failed,"オーバーレイのコンテキストは組み立てられ、Dockerfile 86 段のうち 85 段目で失敗: webpack 5.93.0 がエラー 2 件で停止: osfHelpers.js と comment.js が要求する linkify-html がオーバーレイ側の package.json にない"
```

これで分かったこと:

- オーバーレイの仕組みは束を作る段の直前まで端から端まで働く。重ねたコンテキスト（osf.io のチェックアウト＋wiki-frontend のファイル、wiki-frontend の Dockerfile）が組み立てられ、yarn はオーバーレイ側のロックファイルから導入し、webpack は osf.io の JavaScript を処理した。
- 残る失敗はインストーラーの欠陥ではなく、二つの上流の間の*統合のずれ*である。RDM-osf.io の develop は 2026-11-01 に linkifyjs を 2 系から 4 系へ更新し linkify-html を追加したが、wiki-frontend オーバーレイの `package.json` / `yarn.lock` は 2025-06 のままだった。オーバーレイ側のロックファイルが優先されるため、osf.io のコードが新しいモジュールを解決できなかった。

決めたこと: 修正は統合リポジトリ RDM-wiki-frontend-dev2027 側で行う（PR #2: linkify-html と sift を追加、linkifyjs・bootstrap-datepicker・highlight.js・less を osf.io develop に合わせ、yarn.lock を node:21-alpine 内で再生成）。PR の前に検証: 同期後のファイルを置いた同じオーバーレイのコンテキストを本ホストで `docker buildx build --platform linux/arm64` して成功（webpack 5.93.0、エラー 0、警告 4: `mode` 未設定 1 件、性能推奨 3 件）。イメージには `wiki_assets` が写す `website/static/public/js/wiki-edit-page.<chunkhash>.js` がある。マージ後に manifest の `integration_sha` を更新し（PR #31）、第 6〜8 回を下に記した。[SPEC-05](../spec/05_upstream_tracking.md#japanese) への教訓: オーバーレイの依存一覧は、週次の統合のたびに基底と差分を取らなければならない。

### 第 6〜8 回 — 2026-11-06、develop 757dc37 ＋ PR #32・PR #33 のブランチ

同じホスト。短い 3 回で、毎回ひとつ先の段で止まった。

```toon
run6:
  branch: develop 757dc37（RDM-wiki-frontend-dev2027 PR #2 後の wiki-frontend integration_sha cd96330f）
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 40（docker compose up が 1 で終了）"
  build: "6 部品すべてが初めて通過（wiki-frontend オーバーレイをビルド。osf.io・waterbutler・mfr はキャッシュ。ember・cas は prebuilt）"
  up: "`elasticsearch:2` の取得失敗: no matching manifest for linux/arm64"
run7:
  branch: fix/infra-amd64-platform（PR #32: elasticsearch2・elasticsearch6・sharejs・unoconv・fakecas に build_platform linux/amd64）
  result: "終了コード 40（docker compose up が 1 で終了）"
  up: "基盤イメージ 9 本すべて取得（amd64 専用の 5 本はプラットフォーム固定で）。その後、/private/tmp 配下の作業用 worktree から実行したため bind ボリュームが Docker Desktop の共有パス外になりマウント失敗。操作者の誤りでインストーラーの欠陥ではない。`docker compose down -v` で片付けた"
run8:
  branch: fix/infra-amd64-platform（本体チェックアウトから実行）
  result: "終了コード 40（docker compose up が 1 で終了）"
  up: "21 サービス中 16 を作成。postgres・mongo・rabbitmq・redis・elasticsearch6・fakecas・wb・wb_worker・mfr は起動。下の 4 件が失敗。web/api/admin/worker は wiki_assets を待つため起動せず"
  failures[4]{service,symptom,cause,fix}:
    wiki_assets,"exit 1: /wiki_static is not writable by 1000","macOS の Docker Desktop は bind ディレクトリを root:root として見せ `chown` を無視するが、どの uid でも書ける。したがって `test -w` は偽陰性","`test -w` の代わりに実際に目印ファイルを作って消す書込プローブ（PR #33）"
    cas,"再起動ループ: Could not create local repository at /root/.m2repo","配布イメージは起動時に `mvn jetty:run` を走らせ、Maven リポジトリは /root（0700）配下、target/ も起動時に書く。user 1000:1000 と読み取り専用ルートの両方が阻む","cas に hardening 例外（user・read_only。capability 追加なし）。M4 で war を焼き込むまで（PR #33）"
    elasticsearch,"再起動ループ: runtime: failed to create new OS thread (have 2 already; errno=22)","EOL の elasticsearch:2 イメージの gosu は古い Go バイナリで、Rosetta（Apple Silicon 上の Docker Desktop の amd64 エミュレーション）の下で異常終了する","イメージの elasticsearch ユーザー（uid 101）で直接動かし、entrypoint の chown と gosu を飛ばす。例外は read_only だけに縮小（PR #33）"
    unoconv,"再起動ループ: chown: changing ownership of '/home': Operation not permitted","entrypoint が全 capability を落とした root で `chown -R www-data /home` を実行する","unoconv の例外に CAP_CHOWN を追加（PR #33）"
```

これで分かったこと:

- Apple Silicon の core プロファイルで、ビルドの段は完了した。6 部品のうち 3 本はローカルでビルド、2 本は prebuilt、1 本はオーバーレイ。
- `up` の失敗は、EOL の各イメージが想定していなかった二つの制約、すなわち hardening の基準（非 root・読み取り専用・capability なし）と Rosetta による amd64 エミュレーションの下での起動の仕方だけに残った。各失敗はイメージ固有の事実として `manifest/hardening.json` に見直し日と近代化の目標とともに記録した。
- Docker Desktop のファイル共有はコンテナ内の所有権テストの意味を変える。プローブは実際の操作を試さなければならない。

### 第 9〜12 回 — 2026-11-06、ブランチ fix/run8-startup（PR #33）、本体チェックアウトから実行

同じホスト。毎回、前の回が露わにしたものを直した。`build` は毎回通過（すべてキャッシュ）。

```toon
run9:
  fixes_applied: "wiki_assets の書込プローブ。elasticsearch を uid 101 で。unoconv に CAP_CHOWN。cas の例外"
  result: "終了コード 40（300 秒で未健康: web, api, admin, worker, ember_osf_web）"
  state: "21 中 17 が起動。wiki_assets は 0 で終了（束を写した）。web は KeyError EXTERNAL_EMBER_APPS['preprints']。api/admin/worker は invoke の stdin スレッドの `OSError: [Errno 25] Not a tty`。ember はビルド中"
run10:
  fixes_applied: "local.py に preprints/reviews のキー。web/api/admin/worker に stdin_open"
  result: "終了コード 40（300 秒で未健康）"
  state: "web/api/worker は `Read-only file system: /code/website/static/built/nodeCategories.json`。api/admin/worker は `ModuleNotFoundError: debug_toolbar`（DEBUG_MODE=True がイメージに無い開発専用パッケージを import する）。ember は 6.3 GiB の上限で 2 回 OOM。docker info では Docker VM は 47 GiB なのに予算はホストの 128 GiB から算出していた"
run11:
  fixes_applied: "website/static/built に tmpfs。DEBUG_MODE=False。ember は weight 4・下限 8 GiB・JOBS=2。二段階のメモリ配分を Docker VM で上限化。up の待ち時間 900 秒"
  result: "終了コード 40（900 秒で未健康: web, api, admin, worker, ember_osf_web）"
  state: "web/api/admin/worker は同じファイルで `PermissionError`。Compose の短い `tmpfs` 記法は root 所有の 0755 で mount する（docker run --tmpfs は 1777）。ember は OOM なしでビルド中"
run12:
  fixes_applied: "tmpfs の項目を :mode=1777 付きで出力"
  result: "終了コード 40（900 秒で未健康: web, api, admin, ember_osf_web）"
  state: "worker は健康。web は 500: `relation \"osf_institution\" does not exist`（新しいデータベースで migration 未実施）。500 のたびに開発サーバーが postgres の接続を 1 本漏らし `FATAL: too many clients already` に至った（100 本中 98 本を web が保持）。ember は起動から約 25 分後に HTTP 200 を返した"
```

これで分かったこと:

- osf.io アプリケーションより下のものは、hardening の基準の下で Apple Silicon 上ですべて起動する。17 サービスが起動し、wiki の一回限り 2 本は束をボリュームに置いて 0 で終了した。
- 欠陥の三つの類はイメージではなくインストーラーにあった。上流コードが import 時に読むキーが生成設定に無いこと、Compose の細部（stdin・tmpfs のモード・Docker VM に対するメモリ予算）、そして上流 README が操作者に任せているデータベース初期化の段が無いこと。
- osf.io の開発サーバーは、未処理のエラーで終わる要求ごとにデータベース接続を 1 本漏らす。`max_connections=500` は安全余裕であり、本当の修正は `/` を失敗させないこと。

決めたこと（PR #33、[SPEC-02 §4・§7](../spec/02_installer_cli.md#japanese)）: web/api/admin/worker が待つ一回限りの `osf_init`（migrate・機関・OAuth スコープ）。ember-osf-web は URL 設定の指紋とともに `dist/` を名前付きボリュームへ一度だけ組み `ember serve --path` で配信（エミュレーション下の初回ビルドは 10〜25 分、以後は数秒）。ember のバックエンド URL は公開したループバックのポートと `{{AUTH_URL}}` から。`up` は既定で 900 秒待つ。第 13〜18 回は下に記す。

### 第 13 回 — 2026-11-06、`osf_init` 入りのブランチ fix/run8-startup

```toon
run13:
  result: "終了コード 40（docker compose up が 1: service \"osf_init\" didn't complete successfully）"
  osf_init: "`manage.py migrate` と `scripts.populate_institutions -e test -a` は初回で成功（postgres とエミュレーション下の elasticsearch:2 は第 12 回から起動していた）。`scripts.register_oauth_scopes` は `Read-only file system: /code/logs/register_oauth_scopes.py.<timestamp>.log` で失敗。scripts/utils.py が /code/logs に実行ごとのログファイルを作る"
  fix: "osf_init・web・api・admin・worker に tmpfs /code/logs（第 14 回）"
```

### 第 14 回 — 2026-11-06、tmpfs /code/logs 付き

```toon
run14:
  result: "終了コード 40（900 秒で未健康: web, api, admin, ember_osf_web）"
  osf_init: "0 で終了（migrate・機関・OAuth スコープ）"
  web: "`/` で HTTP 500: PROXY_EMBER_APPS がトップページを ember_osf_web へ転送するが、ember はまだビルド中（ember_osf_web:4200 への ConnectionError）。postgres 接続は 1 本のまま、漏れなし"
  api_admin: "`DatabaseWrapper objects created in a thread can only be used in that same thread`。autoreload を切っても同じ。api/base/wsgi.py は website.settings.DEBUG_MODE が False のとき gevent をモンキーパッチする（第 11 回で debug_toolbar を避けるため False にしていた）。local.py で False に固定していなければ SECURE_MODE = not DEBUG_MODE がサーバーを TLS に切り替えてもいた"
  fix: "DEBUG_MODE を True に戻す。Django の DEBUG はプロジェクトごとに api_local.py と新設の admin_local.py（admin/base/settings/local.py に mount）で False。health は web を ember 無しで描画できる /login/ で探査（第 15 回）"
```

### 第 15 回 — 2026-11-06、DEBUG_MODE を戻し、プロジェクトごとの DEBUG を切り、web は /login/ で探査

```toon
run15:
  result: "終了コード 40 — `up` は初めて通過（0, ok）、`health --network` が失敗（40）: web/api/admin が未健康。下記"
  ember_osf_web: "起動から約 13 分で HTTP 200（dist をボリュームへ組んだ）。web の `/` もその後 200"
  api: "mount したファイルだけが変わったため Compose は何も作り直さず、第 14 回で失敗したプロセスが残っていた。`docker restart` 後は `/` に 302"
  admin: "依然 `ModuleNotFoundError: debug_toolbar`。admin/base/settings/defaults.py は import 時に DEBUG_MODE を読んで debug_toolbar と nplusone を INSTALLED_APPS と MIDDLEWARE に加えるので、local.py の `DEBUG = False` だけでは遅い。続いて 127.0.0.1 に対する `400 DisallowedHost`"
  fix: "admin_local.py で二つのアプリとミドルウェアを外し、ALLOWED_HOSTS に 127.0.0.1/localhost/admin を加える。再描画と再起動の後、admin は 302（第 16 回がクリーンな実行）"
```

### 第 16 回 — 2026-11-06、全修正を適用したクリーンな実行: 手作業の修復なしで `up` が通った

```toon
run16:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 40（`health --network` で停止）"
  steps[7]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok（メモリ予算はホストの 128.0 GiB でなく Docker VM の 47.0 GiB を使う。ember と fakecas はポートを維持）"
    build,0,"ok（すべてキャッシュ）"
    up,0,"ok — ready: http://127.0.0.1:5000/（22 サービス。一回限りの 3 本は 0 で終了）"
    "health --network",40,"failed: `ControlCe listens on *:5000 (not loopback; project port, owner not visible)`"
```

これで分かったこと:

- core プロファイルは hardening の基準の下で Apple Silicon 上で端から端まで起動し、`up` はループバックの URL で準備完了を宣言する。節目 M2 の「一発導入」はアプリケーションに到達した。
- `--network` の検査は 5000 番の、我々のものでないワイルドカードの待ち受けを見つけた。macOS の AirPlay レシーバー（ControlCenter）は `*:5000` と `*:7000` を bind する。我々の `web` はその横で `127.0.0.1:5000` に bind して応答している（カーネルは具体的な番地を優先する）。検査はプロジェクトのポート上のループバック以外の待ち受けをすべて失敗と扱っていた。

決めたこと: `health --network` は、Docker に属する待ち受け（我々の公開ポートがループバック以外へ漏れている場合。[ADR-02](../decisions/ADR-02_Network_Model.md)）と、所有者の見えないプロジェクトのポート上のワイルドカードの待ち受け（安全側に失敗）は引き続き失敗にする。プロジェクトのポート上の*名前の分かる*他プロセスは警告の行（`foreign-listener`）として報告し、操作者が望めば `GRDM_PORT_<SERVICE>` でポートを移せるようにする。第 17 回は下へ追記する。

### 第 17 回 — 2026-11-06、他プロセスの待ち受けを警告に: `up` と `health --network` が合格、`scan` が始まる

```toon
run17:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 51（`scan` で停止: semgrep が PATH にない）"
  steps[8]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok（すべてキャッシュ）"
    up,0,"ok — ready: http://127.0.0.1:5000/"
    "health --network",0,"ok。警告 1 件: foreign-listener ControlCe on *:5000（macOS の AirPlay レシーバー）"
    scan,51,"failed: semgrep が PATH にない。その前に trivy 0.75.0 が 25 対象を検査"
  trivy_findings[4]{severity,count}:
    CRITICAL,1894
    HIGH,8620
    MEDIUM,10047
    LOW,3955
  trivy_problems: "src/RDM-cas-overlay-dev2027 の sbom/scan が rc 1（prebuilt 部品で checkout が無い）。リポジトリ自身の sbom/scan が rc 1"
```

これで分かったこと:

- M2 の最初の二つの門は実機で通った。一つのコマンドで core プロファイルが起動し、ループバック限定の規則が守られている。
- EOL イメージ群（Python 3.5/3.6、node 8/12、JDK 8、ES 2/6、mongo 3.4）の脆弱性件数は、[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) が M1〜M3 に想定したとおりである。今は報告と許容リスト、M4 で HIGH 停止、M5 で CRITICAL/HIGH ゼロ。
- `scan` 自体に欠陥が二つある。SPEC-03 はローカルでも Semgrep を動かすのにブートストラップが Semgrep を入れていないこと、prebuilt 部品が決して clone しないソースディレクトリに Trivy を向けていること。

決めたこと: ブートストラップは Semgrep を `grdm-dev` と同じ `.venv` に入れ、`scan` は自分のインタープリタの隣でも道具を探す。Trivy は prebuilt 部品のソースディレクトリを飛ばし、飛ばした理由を報告する。第 18 回は下に記した（終了コード 0）。

### 第 18 回 — 2026-11-06、Semgrep を `.venv` に、Trivy はオフラインで対象を選ぶ: **コマンド全体が成功**

```toon
run18:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 0 — GakuNin RDM developer environment is ready: http://127.0.0.1:5000/"
  steps[9]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env があるため）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,"ok（ポートは維持。メモリ予算は Docker VM の 47.0 GiB から）"
    build,0,"ok（すべてキャッシュ）"
    up,0,"ok — 22 サービス、ループバックの URL で準備完了"
    "health --network",0,"ok（警告: foreign-listener ControlCe on *:5000）"
    scan,0,"ok — 門は報告のみ: 合格"
    report,0,ok
  scan_tools[4]{tool,version,targets,result}:
    trivy,0.75.0,22,"ok（飛ばしたもの: prebuilt の cas-overlay と ember-osf-web の古い checkout、組み立てた _overlay/ の文脈）"
    semgrep,1.184.0,4,ok
    gitleaks,8.30.1,1,ok
    zap,stable,3,ok
  findings_by_severity[5]{severity,trivy,zap,total}:
    CRITICAL,1835,0,1835
    HIGH,8290,1,8291
    MEDIUM,9763,9,9772
    LOW,3886,13,3899
    INFO,0,5,5
  milestone_in_report: "M1 — manifest/milestone.json は所有者が保守し（SPEC-03 §5.2）まだ M1。門の規則はどちらでも報告のみ"
  allow_list: "0 件、許容 0 件。M4 の閾値（HIGH 以上）を超える 10126 件は M2 では報告のみで、停止させない"
```

これで分かったこと:

- **M2 の一発導入は Mac Studio で動く**。最初の試みから 18 回目で、`./installer/install.sh --yes --no-open --profile core` は素のシェルから準備完了の URL まで、ループバック検査・スキャナー・報告書を通して終了コード 0 で到達する。
- 第 1 回から第 18 回の間の停止はすべて、EOL イメージの事実か、実際に起動しないと分からないインストーラーの細部だった。それぞれ上に修正と文書とともに記録した。
- EOL スタックの脆弱性の基準値が測れた。Trivy 単独で CRITICAL 1835 件、HIGH 8290 件（ZAP が HIGH 1 件を加える）で、ほぼすべてがイメージ由来（Python 3.5/3.6、node 8/12、JDK 8、Elasticsearch 2/6、mongo 3.4）。これが M4 と M5 でゼロにすべき数であり、許容リストは隠すためには使わず空のままにする。

M2 の次: この起動したスタックに対する Playwright 受入（C1〜C6）と、RDM-osf.io-dev2027 側の Wiki エディタページの配線（C4）。

### 第 19 回 — 2026-11-06、レビュー r1 対応後のコールドスタート（ボリューム削除、`runtime/` 新規）

```toon
run19:
  preparation: "`docker compose down -v`。runtime/ を退避（イメージは保持）"
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 40（docker compose up が 1: service \"osf_init\" didn't complete successfully）"
  steps[6]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,"ok（新しい runtime/.env）"
    "compose render",0,"ok（fakecas の 8080 は使用中→8081。予算は 47 GiB の VM から）"
    build,0,"ok（すべてキャッシュ）"
    up,40,"11 分後に失敗"
  one_shots[4]{service,result}:
    elasticsearch_data_init,"0 で終了（chown 101:101。Docker Desktop では chown は無効だがどの uid でも書ける）"
    wiki_static_init,"0 で終了"
    wiki_assets,"0 で終了（束を写した）"
    osf_init,"1 で終了: migrate は空のデータベースに全 migration を適用。続く populate_institutions は 5 分間に 30 回失敗 — Elasticsearch 2 が接続を拒否"
  elasticsearch2: "コンテナは CPU 200 % で動いていたが 9200 番を開いていなかった。EOL の elasticsearch:2 イメージ（JDK 8、linux/amd64）は Rosetta 下で 03:31:52 に `initializing ...`、04:09:57 に `started` — 起動に 38 分"
  native_trial: "公式の elasticsearch-2.4.6 tarball（27.3 MB、sha256 5f7e4bb7…cfc6f）を arm64 の eclipse-temurin:8-jre コンテナで起動: 5 秒で `initialized`・`started`"
```

これで分かったこと:

- コールドスタートは、どんなタイムアウトでも隠せない最後のエミュレーションのコストを露わにした。JDK 8 のサービスは Rosetta 下で、データディレクトリが新しいたびに初期化に約 40 分かかり、スタック全体がそれを待つ。
- 同じ Elasticsearch 2.4.6 を arm64 ネイティブの JRE で動かすと数秒で起動する。問題は x86-64 のイメージであってプログラムではない。

決めたこと: 本 PR では `osf_init` が Elasticsearch を最長 30 分待ち、ember-osf-web は web/api に依存しなくして自身の長いビルドを並行させる。第 20 回は同じコールドスタートの続きで `up` を通した（下記）。次の PR では、公式 tarball からダイジェスト固定の Temurin 8 JRE 上にマルチアーキテクチャの `grdm-dev/elasticsearch2` イメージを組み（チェックサム検証、非 root、所有者初期化コンテナ不要）、その規則を ADR に記す — amd64 のイメージしか無い EOL ミドルウェアは、退役する節目まで arm64 向けにネイティブで組む。

### 第 20 回 — 2026-11-06、Elasticsearch が起動してから同じコールドスタートを続行

```toon
run20:
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 51（`scan` で停止: semgrep が不完全）"
  steps[8]{step,code,status}:
    "secrets init",0,"skipped（第 19 回の runtime/.env）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok（キャッシュ）"
    up,0,"ok — ready: http://127.0.0.1:5000/。新しいボリューム上で osf_init が完了（migration は第 19 回で適用済み、Elasticsearch が応答してから機関を投入）、ember は新しいボリュームへ dist を組んだ"
    "health --network",0,"ok（警告: foreign-listener ControlCe on *:5000）"
    scan,51,"semgrep がエラー 148 件を報告: ファイルごとのルールのタイムアウト（既定 5 秒）— すべて `runtime.run18-123040/`、このコールドスタートのためにリポジトリ内へ退避した第 18 回の runtime の中（git-ignore は `runtime/` だけで、Semgrep は .gitignore に従う）。検査は不完全と記録され、門は安全側に失敗"
  rerun_after_fix: "そのディレクトリをリポジトリ外へ移し、.gitignore に `runtime.*/` を加え、Semgrep のルールのタイムアウトを網羅性の警告として扱うようにした後、同じスタックで `grdm-dev scan` と `grdm-dev report`: scan 終了 0（門は報告のみ: 合格。trivy/semgrep/gitleaks/zap すべて ok。件数は第 18 回と同じ 1835/8291/9772/3899/5）、report 終了 0"
```

これで分かったこと:

- Elasticsearch がようやく起動すると、コールドスタートは `up` とループバック検査を通る。データベース初期化、wiki の束、ember のビルドはいずれも空のボリュームから動く。
- したがってコールドスタートは端から端まで完了する。Elasticsearch が起動した後は、新しいボリューム上で `up`・`health --network`・`scan`・`report` がすべて終了 0。`scan` の停止は自分で招いたもの（操作者がリポジトリ内に置いた `runtime/` の写し）で、いま入れた二つの堅牢化点を露わにした。`runtime.*/` を無視すること、Semgrep のルールのタイムアウトは門を安全側に落とすのでなく網羅性の警告として記録すること。

### 第 21 回 — 2026-11-06、ネイティブ Elasticsearch 2 イメージ（ADR-07）でのコールドスタート: **空のボリュームから準備完了まで 30 分、終了コード 0**

```toon
run21:
  preparation: "`docker compose down -v`。runtime/ をリポジトリ外へ退避（イメージは保持）。ブランチ feat/native-elasticsearch2-image（develop f37a029 上）"
  command: ./installer/install.sh --yes --no-open --profile core
  result: "終了コード 0 — GakuNin RDM developer environment is ready: http://127.0.0.1:5000/（04:53:51 → 05:24:34 UTC、30 分 43 秒）"
  steps[9]{step,code,status}:
    doctor,0,ok
    plan,0,ok
    "secrets init",0,"ok（新しい runtime/.env）"
    "compose render",0,ok
    build,0,"ok — grdm-dev/elasticsearch2:2.4.6-1 を installer/images/elasticsearch2 からネイティブに組む（層はキャッシュ）。他もキャッシュ"
    up,0,"ok — コンテナ作成 04:54:40。elasticsearch は 04:54:49 に `started`（コンテナ起動から 6 秒）。osf_init は 04:59:45 に 0 で終了（全 migration＋機関＋OAuth スコープ、5 分）。web/api/admin/worker は 04:59:46 に起動。ember は 05:18:54 に配信開始（24 分のビルド、並行）"
    "health --network",0,"ok（警告: foreign-listener ControlCe on *:5000）"
    scan,0,"ok — 門は報告のみ: 合格。trivy 22 対象、semgrep 4、gitleaks 1、zap 3。タイムアウトなし"
    report,0,ok
  trivy_totals_vs_run_18[4]{severity,run18_trivy,run21_trivy}:
    CRITICAL,1835,1769
    HIGH,8290,8030
    MEDIUM,9763,9550
    LOW,3886,3676
  elasticsearch2_image: "grdm-dev/elasticsearch2:2.4.6-1 — 59 件（HIGH 2・MEDIUM 52・LOW 5）。Elasticsearch 2.4.6 の jar と Temurin 8 ベース由来。置き換えた Docker Hub の elasticsearch:2 が上の差分の大半を抱えていた"
```

これで分かったこと:

- **コールドスタートが端から端まで動く**。イメージのキャッシュ以外は何も無い状態から、一つのコマンドで Apple Silicon 上 31 分で準備完了・検査済み・報告済みの環境に達する。残る所要時間は ember のビルド（24 分、いまは並行）と osf.io の migration（5 分）。
- ネイティブの Elasticsearch 2 はエミュレーションで 38 分かかったところ（第 19 回）を 6 秒で起動し、uid 1000・読み取り専用ルートで堅牢化の例外も所有者初期化コンテナも無く動き、公式の amd64 イメージより既知の脆弱性が少ない。
- 節目 M2 の導入基準（[進捗ボード](../status/README.md#japanese)）は、core プロファイルについて Mac Studio 上で温・冷ともに満たした。M2 に残るのは Playwright 受入。

証跡（第 1 回）: 全ログはセッションの作業領域にのみ保管（パッケージ取得の出力が大半で、秘密は含まない）。Mac Studio の `runtime/` には `.env`（0600）、生成した Compose ファイル、ビルド済みイメージ 2 つがあり、git では無視される。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| Wheel | A ready-made package of Python code for one CPU type; if none exists, pip must compile it. | ある CPU 向けにできあがった Python の部品の箱。無いと pip が自分で組み立てる。 |
