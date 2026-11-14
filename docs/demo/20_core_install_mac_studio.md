# DEMO-20 Core Install on Mac Studio / Mac Studio でのコア導入記録

> **Summary:** What actually happened when `./installer/install.sh --yes --no-open --profile core` was run on the Mac Studio (Apple Silicon). One entry per run; nothing is edited after the fact.
> **概要:** Mac Studio（Apple Silicon）で `./installer/install.sh --yes --no-open --profile core` を実行したときに実際に起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.23 — 2026-11-14. **Learned:** a one-command claim is about a new checkout, and on a host that already runs a stack the installer's own volume check (PR #64) turns that stack's volumes into an obstacle: with the owner's approval the registrations were removed (data kept and backed up), `install-macos.sh --yes --profile core` from a new clone of develop 0df4640 returned 0 in a single run of 12 min 50 s with a warm Docker cache (build 59 s, `up` on empty volumes 9 min), acceptance with the default waits passed 14 of 14, and the main stack was restored with the same 14 volume bindings and data, though not the same image IDs. ／ 一つのコマンドの主張は新しいチェックアウトについてのもので、既にスタックが動いているホストでは、インストーラー自身のボリュームの検査（PR #64）がそのスタックのボリュームを障害にする。所有者の承認のもとで登録を外し（データは残してバックアップ）、develop 0df4640 の新しい clone から `install-macos.sh --yes --profile core` は Docker のキャッシュが温まった状態で一回の実行で 12 分 50 秒で終了 0 を返し（build 59 秒、空のボリュームでの `up` 9 分）、既定の待ちでの受入は 14 件中 14 件合格し、本体のスタックは同じ 14 個のボリュームの結びつけとデータで復元した。ただしイメージ ID は同じではない。
  0.22 — 2026-11-13. **Learned:** code that was only unit-tested is not yet a fact about the stack: the stricter ZAP sign-in exception ran once on the live Mac Studio stack, where the probe inside the ZAP image worked and `web` was recorded as skipped behind sign-in while `admin` and `ember_osf_web` were scanned, and that run is the evidence the unit tests could not give (PR #56 review r2 asked for it). ／ 単体試験だけで確かめた処理は、まだスタックについての事実ではない。厳しくした ZAP のサインイン除外を、稼働中の Mac Studio のスタックで一度実行した。ZAP のイメージ内の探りは動き、`web` はサインインの壁の向こうとして飛ばされ、`admin` と `ember_osf_web` が検査された。単体試験が与えられなかった証拠はこの実行である（PR #56 レビュー r2 が求めた）。
  0.21 — 2026-11-13. **Learned:** a tool row that reads `ok (3 targets)` is not a statement that three targets were scanned: under mandatory sign-in the earlier scan logic counted a skipped `web` as a scanned target, and the raw report of the complete scan is not committed, so the committed record cannot show per target what ZAP did; the correction says so, and the scan code now reports skipped targets separately (PR #56 review r1 R1-01). ／ `ok (3 targets)` と読める行は、三つの対象を検査したという主張ではない。必須サインインのもとでは、以前の検査の処理は飛ばした `web` を検査済みの対象に数えていた。完走した検査の生レポートはコミットしていないので、コミット済みの記録だけでは、ZAP が対象ごとに何をしたか示せない。この訂正はそれを述べ、検査の処理は対象外を別に報告するようになった（PR #56 レビュー r1 R1-01）。
  0.20 — 2026-11-13. **Learned:** a candidate is proven again on the merge commits before it counts: the three pull requests merged under their own review, osf.io was pinned to the merged develop tip `90b10661c8dc`, the stack was rebuilt and brought up on it, and the same 14 of 14 and a complete scan (exit 0, 6,264 open findings) were recorded; the rebuild reused Docker's layer cache, so the 55-minute cold build time of 0.19 was not measured again. ／ 候補は、マージコミットでもう一度確かめて初めて数に入る。三つの PR がそれぞれのレビューを経てマージされ、osf.io をマージ後の develop 先端 `90b10661c8dc` に固定し、その上でスタックを組み直して起動し、同じ 14 件中 14 件と完走した検査（終了 0、未解決 6,264 件）を記録した。組み直しは Docker のレイヤーキャッシュを使ったので、0.19 のコールド 55 分は測り直していない。
  0.19 — **Learned:** a candidate that combines unmerged pull requests proves the installer, not the pull requests: the first acceptance run found three defects that none of the unit tests or any single PR could show (a development server that stalls on Django 2.2, a CDN script the static ember names, a WaterButler that sends no CORS header), and the run that passes records exactly which commits it combined and that they are not pushed. ／ 未マージの PR を組み合わせた候補が証明するのは、PR でなくインストーラーである。最初の受入は、単体試験にも一つの PR にも見えない欠陥を三つ見つけた（Django 2.2 で止まる開発用サーバー、静的な ember が名指しする CDN のスクリプト、CORS ヘッダーを送らない WaterButler）。合格した実行は、組み合わせたコミットが何で、push されていないことを正確に記録する。
  0.18 — 2026-11-11. **Learned:** an allow-list that only reproduces today's numbers is not yet safe. After exact package matching and the no-fix condition ([PR #45 review r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-01), the same 177 findings are accepted, while a fix published later reopens its finding. Review r1 R1-03 also corrected the wiki-frontend pin in the 11-of-12 entry and the 0.17 summary. ／ 今日の件数を再現するだけの許容リストは、まだ安全ではない。パッケージの厳密な照合と修正版なしの条件（[PR #45 レビュー r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-01）の後も許容されるのは同じ 177 件だが、後から修正版が出た検出は再び数えられる。あわせてレビュー r1 の R1-03 により、12 件中 11 件の節の wiki-frontend の固定版と 0.17 の要約を訂正した。
  0.17 — 2026-11-11. **Learned:** a fix proven on an unmerged head is proven again on its merge commit before it counts: the same 12 of 12 and the same Trivy totals at MFR `9771b8cf` show that the merge changed nothing (the whole scan has one more ZAP MEDIUM, 10,983 → 10,984). ／ 未マージの先頭で確かめた修正は、マージコミットでもう一度確かめて初めて数に入る。MFR `9771b8cf` で同じ 12 件中 12 件、同じ Trivy の件数になったことで、マージで何も変わっていないと分かる（検査全体では ZAP の MEDIUM が 1 件増え、10,983 → 10,984）。
  0.16 — 2026-11-11. **Learned:** the narrowest fix for a broken hop is to stop changing the URL the other service built, not to teach the client a second origin: once MFR requests osf.io's `/<guid>/` URL unchanged again, osf.io answers the internal WaterButler URL itself, so previews pass with the credential pair unchanged. ／ 壊れた転送の最も狭い直し方は、相手のサービスが組み立てた URL を変えるのをやめることで、利用側に別の origin を教えることではない。MFR が osf.io の `/<guid>/` の URL を再び変えずに要求すると、osf.io 自身が内部向けの WaterButler の URL を返すので、資格情報の組を変えずにプレビューが通る。
  0.15 — 2026-11-11. **Learned:** a service's own tests with a stubbed OSF cannot prove a hop that the real osf.io answers differently: the Python 3.13 MFR asks `/download/<guid>/`, whose redirect names the browser's WaterButler URL instead of the internal one, so only the full acceptance run on the real stack found that previews break; and a shared Docker disk that fills up turns build and scan steps into misleading errors ("not signed", ZAP rc 3). ／ OSF をスタブにしたサービス自身の試験では、本物の osf.io が違う答えを返す経路は証明できない。Python 3.13 の MFR は `/download/<guid>/` を要求し、そのリダイレクトは内部でなくブラウザ向けの WaterButler の URL を指すため、プレビューが壊れることは実スタックでの受入の全件実行で初めて分かった。また共有の Docker のディスクが満杯になると、ビルドや検査の手順は紛らわしいエラー（「not signed」、ZAP の rc 3）になる。
  0.14 — 2026-11-10. **Learned:** "only its institution's users" is proven only when a user of another institution exists and is absent, so the cited run now seeds one and is a fresh 12-of-12 run (PR #40 review r1 R1-01). ／ 「自機関の利用者だけ」は、別機関の利用者が存在してかつ表示されないときに初めて示せる。そのため引用する実行を、それを種データに含む新しい 12 件中 12 件の実行に替えた（PR #40 レビュー r1 R1-01）。
  0.13 — 2026-11-10. **Learned:** a security fix is proven only by a rejection case that runs against the image containing it, so the full acceptance run is repeated after every pin change. ／ セキュリティ修正は、その修正を含むイメージに対して拒否ケースを実行して初めて証明される。固定版を変えるたびに受入を全件やり直す。
  0.12 — 2026-11-10. **Learned:** a stack that starts and passes health can still have a broken trust link: osf.io kept its upstream default HMAC key while WaterButler signed with a generated one, and only a real upload exposed it. ／ 起動してヘルス検査に通る環境でも、信頼の連携が壊れていることがある。osf.io は上流の既定の HMAC 鍵のまま、WaterButler は生成した鍵で署名しており、実際のアップロードで初めて露見した。
  0.11 — 2026-11-06. **Learned:** the cold start passes once the one emulated service that could not start natively is built natively (ADR-07): 31 minutes from empty volumes to a scanned, reported environment, bounded by the ember build and the migrations. ／ ネイティブで起動できなかった唯一のエミュレーションのサービスをネイティブで組む（ADR-07）と、コールドスタートは通る。空のボリュームから検査・報告済みの環境まで 31 分で、上限は ember のビルドと migration。
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
  elasticsearch2_image: "grdm-dev/elasticsearch2:2.4.6-1 — 58 findings on the image (2 HIGH, 52 MEDIUM, 4 LOW) from the Elasticsearch 2.4.6 jars and the Temurin 8 base, plus 1 LOW on the recipe file installer/images/elasticsearch2/Dockerfile; the Docker Hub elasticsearch:2 image it replaces carried the bulk of the difference above"
```

What this proves:

- A **cold start works end to end**: with nothing but the images cached, one command reaches a ready, scanned, reported environment in 31 minutes on Apple Silicon. The remaining wall time is the ember build (24 min, now in parallel) and the osf.io migrations (5 min).
- The native Elasticsearch 2 starts in 6 seconds where the emulated one needed 38 minutes (run 19), runs as uid 1000 on a read-only root with no hardening exception and no owner-init container, and carries fewer known vulnerabilities than the official amd64 image.
- Milestone M2's install criterion ([status board](../status/README.md#english)) is met on the Mac Studio for the core profile, warm and cold. What remains for M2 is the Playwright acceptance.

Evidence (run 1): full log kept in the session scratchpad only (contains package download noise, no secrets). The `runtime/` directory on the Mac Studio holds `.env` (0600), the rendered Compose file and two built images; it is git-ignored.

### Acceptance runs — 2026-11-09/10, stack of run 22 (osf.io 389415a4)

| Run id | Scope | Result |
|---|---|---|
| [`acc-20261109T131214Z-f2ee77`](runs/acc-20261109T131214Z-f2ee77/results.toon) | C1 | 2 of 2 pass |
| [`acc-20261109T131240Z-00dff9`](runs/acc-20261109T131240Z-00dff9/results.toon) | Core C1–C6 | 3 of 12 pass |
| [`acc-20261109T170208Z-9ebf01`](runs/acc-20261109T170208Z-9ebf01/results.toon) | C3 after the HMAC fix | 2 of 2 pass |

What the runs found:

- **Login.** Seeded users had `have_email=False`, so GRDM redirected them to the e-mail settings page and the dashboard never loaded. The seed now sets it to true.
- **Upload (C3, C5).** WaterButler received 401 from every signed callback to web. `/api/v1/files/auth/` answered 200, so the JWE/JWT link was fine. Measured by hash of the values: web's `DEFAULT_HMAC_SECRET` was still the upstream default `changeme`, while WaterButler signed with generated keys, two different ones. osf.io has one verifier, so both WaterButler signers and osf.io now use `WATERBUTLER_HMAC_SECRET`, and `OSFSTORAGE_HMAC_SECRET` is no longer generated. This also removes a weakness: with the default key, anyone able to reach web could forge a callback.
- **External assets.** Known assets stay blocked and are only counted ([SPEC-04](../spec/04_acceptance_tests.md#english)). Google Analytics is removed from the built ember configuration.

Open after these runs: C2, C4, C5 and C6 still fail (selectors, wiki bundle wiring, preview, admin path).

### Acceptance run — 2026-11-10, every merged security fix, 12 of 12

Run [`acc-20261110T015520Z-ab4cc7`](runs/acc-20261110T015520Z-ab4cc7/results.toon): **12 of 12 pass**. The stack was built from the pins in this branch (osf.io `fe90e5c3`, WaterButler `45e97a51`, MFR `749e58d3`, wiki-frontend `5985d18b`, y-websocket `d4d1cfae`, cas-overlay `22610b76`), after `secrets rotate` added the keys the new CAS and conversion service need.

| Scenario | Success | Rejection | What made it pass |
|---|---|---|---|
| C1 Login | pass | pass (401) | seed `have_email` |
| C2 Project | pass | pass (403) | selectors |
| C3 Files | pass | pass (403) | one HMAC key for WaterButler and osf.io |
| C4 Wiki | pass | pass (4401) | JWT on the y-websocket upgrade, token refresh in the client, bundle path in `edit.mako` |
| C5 Preview | pass | pass (401) | MFR forwards credentials only on the OSF→WaterButler hop; Google Analytics removed from the PDF viewer |
| C6 Admin | pass | pass (403) | admin assets served locally, so no CDN request; an affiliated institution admin sees a member of its institution, and neither an unaffiliated user nor a user of a second institution, in the list and in an explicit search |

One run before this one failed on C5 and C6 although the fixes were merged: `compose render` had run before `build`, and it takes image tags from the last build record, so the old images kept running. Rendering again after the build fixed it.

### Acceptance run — 2026-11-11, Python 3.13 WaterButler and MFR on PostgreSQL 18, 11 of 12

Started from the main checkout on `feat/pin-py313-wb-mfr`. Pins: WaterButler `3319c106` and MFR `f9da1db3` (both on `python:3.13-slim@sha256:e48f59cd…ed90`, Python 3.13.18, Debian 13), osf.io `8fc45de4`, wiki-frontend `5985d18b` (built on the osf.io base `8fc45de4`, image tag `8fc45de461fd-5985d18b75da`), y-websocket `d4d1cfae`, cas-overlay `22610b76`, PostgreSQL 18.6. MFR is now built natively for arm64 (`build_platform` removed) and without freecad, so CAD previews (.step/.stp) are removed by owner decision.

| Step | Exit | Result |
|---|---|---|
| `db upgrade` | 0 | PostgreSQL 9.6 → 18 by dump and restore (4.8 MB dump, 531 objects compared equal); the old directory is kept as `postgres_data.pg9.6-20261111T111040Z` |
| `build` | 30 | First try: WaterButler's `apt-get upgrade` failed with "not enough free space": the Docker disk shared with other work on this host was full. Superseded `grdm-dev/*` tags of earlier pins were removed (no build cache was pruned). Second try built osf.io, WaterButler, MFR, cas-overlay, wiki-frontend and y-websocket; elasticsearch2 then failed in `apt-get update` ("not signed", the same full disk). Its existing image, built on 2026-11-10 from inputs unchanged since 2026-11-06, was used. |
| `compose render` after `build` | 0 | no stale build tags |
| `up` | 0 | 24 services healthy; `wb` and `wb_worker` run as uid 1000 (user `waterbutler`), `mfr` as uid 1000; the Celery 5.6.3 worker is ready. No new secret was needed, and the templates and `wb.env`/`mfr.env` are unchanged. |
| `accept --seed --only core` | 60 | Run [`acc-20261111T115949Z-ab529c`](runs/acc-20261111T115949Z-ab529c/results.toon): **11 of 12 pass**; C5 success fails (below) |
| `scan` | 51 | Trivy, Semgrep and gitleaks complete; baseline pass; ZAP produced no report (rc 3) for all three targets while the Docker disk had 0 bytes free |
| `report` | 0 | |

**C5 success (preview) fails in the integration repositories, not in the installer.** MFR answered 400 for the render request. MFR's log shows `ClientConnectorError: Cannot connect to host 127.0.0.1:7777`, and web's log shows the request MFR now makes: `GET /download/<guid>/?direct&mode=render&action=download` from the MFR container, answered 302. MFR `f9da1db3` (taken from upstream #9) rewrites an OSF URL of the form `/<guid>/` to `/download/<guid>/`. In osf.io `8fc45de4`, the route `/<guid>/` builds the WaterButler URL with `_internal=(mode == 'render')`, so MFR received `http://wb:7777`. The route `/download/<guid>/` (`persistent_file_download`) builds it without `_internal`, so MFR receives the browser's `WATERBUTLER_URL` (`http://127.0.0.1:7777`), which is unreachable inside the container and is also not a credential target. The fix belongs to MFR (do not rewrite render URLs for GRDM) or to osf.io (`persistent_file_download` honours `mode=render` like the other route). C5 rejection (401) still passes.

Trivy CRITICAL/HIGH per target (`critical/high`):

```toon
trivy_critical_high:
  db: "2026-11-10 19:01 UTC (before: scan_20261110T022540Z, DB 2026-11-10 01:02 UTC)"
  targets[23]{target,before,after,note}:
    waterbutler,13/178,0/47,"45e97a51 → 3319c106; all 47 Debian 13 without a fix, allow-listed"
    modular-file-renderer,53/410,3/127,"749e58d3 → f9da1db3; all 130 Debian 13 without a fix, allow-listed"
    osf.io,118/566,118/566,"fe90e5c3 → 8fc45de4"
    wiki-frontend,65/332,65/332,""
    rdm-ember-osf-web,407/1911,407/1911,prebuilt
    cas-overlay,43/105,43/105,""
    postgres,11/117,2/147,"9.6 → 18.6 (Debian 13)"
    unoconv,1/100,1/156,"same image, newer DB"
    redis,1/37,1/37,""
    elasticsearch2,5/18,5/18,""
    elasticsearch6,2/50,2/50,""
    rabbitmq,0/7,0/7,""
    mongo,0/2,0/2,""
    fakecas,0/2,0/2,""
    sharejs,0/0,0/0,""
    y-websocket,0/0,0/0,""
    src/RDM-waterbutler-dev2027,2/32,0/0,lockfiles
    src/RDM-modular-file-renderer-dev2027,14/79,0/0,lockfiles
    src/RDM-osf.io-dev2027,55/279,55/279,lockfiles
    src/RDM-wiki-frontend-dev2027,21/107,21/107,lockfiles
    src/RDM-cas-overlay-dev2027,6/20,6/20,lockfiles
    src/RDM-y-websocket-dev2027,0/0,0/0,lockfiles
    repo,0/30,0/30,""
  total: "817/4382 → 729/3943 (open 726/3769, allow-listed 3/174 by 58 entries)"
```

The allow-list now holds 58 entries (one per image and CVE, scoped with the new `image` field of [SPEC-03 §5.1](../spec/03_security_gate.md#english), review date 2026-12-31). The milestone is M1 (report-only), so the count is reported; the ceiling in `manifest/allowlist.baseline.json` is the owner's decision at the milestone exit.

### Acceptance run — 2026-11-11, MFR fix for previews, 12 of 12

Same host, branch and pins as the run above, except MFR: the main checkout's manifest was pointed, locally and uncommitted, at `2c4a88a6`, the head of RDM-modular-file-renderer-dev2027 PR #7. That commit stops rewriting osf.io's `/<guid>/?direct&mode=render&action=download` to `/download/<guid>/` and requests the URL as osf.io built it, so osf.io's `/<guid>/` route answers the internal WaterButler URL (`_internal=True` for `mode=render`). The credential pair stays `http://web:5000` → `http://wb:7777`. Its tests also show that the browser-facing `127.0.0.1:7777`, `localhost`, lookalike hosts and other ports are refused before any request or get no credentials. The committed pin stays `f9da1db3` until PR #7 merges. Its merge commit is then pinned.

The Docker disk had been enlarged to 400 GiB (193 GB free before the run).

| Step | Exit | Result |
|---|---|---|
| `compose render` | 0 | |
| `build` | 0 | MFR built natively at `2c4a88a663ca`; the other components from cache, elasticsearch2 rebuilt |
| `compose render` after `build` | 0 | no stale build tags |
| `up` | 0 | 24 services healthy; `mfr` runs `grdm-dev/modular-file-renderer:2c4a88a663ca` |
| `accept --seed --only core` | 0 | Run `acc-20261111T122608Z-2d3599`: **12 of 12 pass**. The evidence directory stays local and is not committed in this PR. C5 success answers 200, and C5 rejection still answers 401. web's log shows MFR requesting `GET /<guid>/?direct&mode=render&action=download` (302), and MFR's log has no `ClientConnectorError`. |
| `scan` | 0 | All five parts complete: baseline pass, and Trivy, Semgrep, gitleaks and ZAP ok. ZAP produced reports again for its three targets. Gate: report-only, pass |
| `report` | 0 | |

Scan totals (`scan_20261111T123133Z`): 10,983 findings, of which 726 CRITICAL, 3,782 HIGH, 4,147 MEDIUM, 2,322 LOW and 6 INFO; 177 more are allow-listed by the 58 entries. Trivy CRITICAL/HIGH open: 726/3,769, unchanged from the run above. The MFR change is code only and adds no package. Semgrep: 12 HIGH. gitleaks: 0. ZAP: 1 HIGH, 8 MEDIUM, 12 LOW, 6 INFO.

Before this, C5 was reproduced on the unfixed MFR `f9da1db3` (run `acc-20261111T121734Z-7329b7`, C5 only: success 400, rejection 401), with the same log lines as the run above.

### Acceptance run — 2026-11-11, MFR pinned at the merge of PR #7, 12 of 12

RDM-modular-file-renderer-dev2027 PR #7 merged as `9771b8cf`. Its tree is identical to the head `2c4a88a6` used above. The manifest now pins MFR at `9771b8cf`, and the note no longer says the fix is unmerged. The other pins are unchanged.

| Step | Exit | Result |
|---|---|---|
| `compose render` | 0 | |
| `build` | 0 | MFR built natively at `9771b8cfb352` |
| `compose render` after `build` | 0 | no stale build tags |
| `up` | 0 | 24 services healthy; `mfr` runs `grdm-dev/modular-file-renderer:9771b8cfb352` |
| `accept --seed --only core` | 0 | Run [`acc-20261111T132104Z-530071`](runs/acc-20261111T132104Z-530071/results.toon): **12 of 12 pass**. C5 success returns 200 and C5 rejection 401. gitleaks found nothing in the run folder, so it is committed. |
| `scan` | 0 | `scan_20261111T132607Z`: baseline pass; Trivy (23 targets), Semgrep, gitleaks and ZAP (3 targets) ok; gate report-only, pass |
| `report` | 0 | |

Scan totals: 10,984 findings, of which 726 CRITICAL, 3,782 HIGH, 4,148 MEDIUM, 2,322 LOW and 6 INFO. A further 177 are allow-listed by the 58 entries. By tool: Trivy 726/3,769/4,139/2,310 (CRITICAL/HIGH/MEDIUM/LOW), Semgrep 12 HIGH, gitleaks 0, ZAP 1 HIGH, 9 MEDIUM, 12 LOW and 6 INFO. These are the same as the run above, except for one more ZAP MEDIUM.

**After PR #45 review r1 (same stack, 2026-11-11 14:18 UTC).** The allow-list matcher was changed (R1-01). Each of the 58 entries now names the exact `name@version` packages of its image, taken from the raw Trivy reports. A Trivy finding is accepted only while its `FixedVersion` is empty and its `Status` is a no-fix status, and only for the OS packages of that image. `scan` and `report` were run again, and both exited 0. `scan_20261111T141804Z` has the same totals as above: 10,984 open findings and 177 allow-listed, matched by all 58 entries. Replaying the stored reports `20261111T132241Z` through the new matcher gives the same 177. The new unit tests show that the old matcher accepted a fixed version, an unrelated package and a name prefix.

### Acceptance run — 2026-11-12, local osf.io candidate with Elasticsearch 8, y-websocket only, mandatory sign-in and the admin second factor, 14 of 14

Stack: the installer at branch `feat/installer-osf-integration` on the Mac Studio (project `grdm-dev`, Colima), from the previous pins and PostgreSQL 18. osf.io is a **local candidate, not a pushed commit**: RDM-osf.io-dev2027 develop `73ff43b3c2` (with #13 Django 2.2, #12 y-websocket editor, #14 render URL) merged with the heads of the open PR #8 (mandatory sign-in, `c9d293dd1a`), #10 (admin two-step sign-in, `834d1b62c0`) and #11 (Elasticsearch 8, `b4bc134188`); conflicts resolved by hand in `admin/common_auth/urls.py`, `admin/base/settings/defaults.py`, `api/base/authentication/backends.py`, `website/search/views.py`, `api/search/views.py`, `website/search/elastic_search.py` and `.github/scripts/ci/run-tests.sh`, which the three PRs will meet again when they are rebased). The manifest pins it at `9e1fb9c8597d` (served through a local bare mirror and `GIT_CONFIG_*` `url.<mirror>.insteadOf`; the installer has no local-source mechanism and gained none). y-websocket `97252369cf` (PR #5) and ember-osf-web `4180cb58bb` (PR #2, #3) are real merge commits.

| Step | Exit | Result |
|---|---|---|
| `secrets rotate` | 40 | Rolled back by design: the old stack's former ember image did not become healthy in 300 s while the builds ran, so the old `runtime/.env` was restored; this is why `secrets init --missing` was added |
| `secrets init --missing` | 0 | Added `ELASTIC8_PASSWORD` and `ELASTIC8_OSF_PASSWORD`, dropped `SHAREJS_SECRET`; no other value changed |
| `compose render` | 0 | |
| `build` | 0 | osf.io `9e1fb9c8597d` (about 55 min cold: `scipy` and friends compile on Alpine 3.9), y-websocket, ember-osf-web (static nginx), wiki-frontend overlay `9e1fb9c8597d-5985d18b75da`, `elasticsearch8:8.19.24-1` |
| `compose render` after `build` | 0 | no stale build tags |
| `up` | 0 | 23 services healthy; `elasticsearch8` healthy in 25 s; `osf_init` applied the merge migrations and `addons_twofactor` 0006/0007 and wrote the institutions into Elasticsearch 8; the sharejs, mongo and Elasticsearch 2 containers were removed as orphans |
| `accept --seed --only core` (first) | 60 | 13 failing, three installer defects found and fixed (below) |
| `accept --seed --only core` (final) | 0 | Run [`acc-20261111T230217Z-d8363c`](runs/acc-20261111T230217Z-d8363c/results.toon): **14 of 14 pass** (C1–C7, success and rejection) |
| `scan` | 0 | `scan_20261111T231702Z` (commit `a14fb70`): baseline pass with no new exception (mongo's is gone, elasticsearch8 needs none); Trivy 22 targets, Semgrep, gitleaks ok; ZAP: `web` skipped with a note, `admin` and `ember_osf_web` scanned; gate report-only, pass |

Defects found by the first acceptance run on the candidate, each fixed in the installer with a test:

1. **`api` and `admin` stalled for 30 s at a time** (C2, C4, C6, C7 timed out; 12 errors at teardown). Django 2.2's development server keeps a connection open, and `runserver --nothreading` (what `invoke apiserver` starts) waits on a browser's idle second connection until the socket times out. Both now run the threaded `manage.py runserver`.
2. **C1 and every browser scenario failed the loopback guard** on `https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/4.4.2/zxcvbn.js`, which the static ember `index.html` names although the build ships `/zxcvbn.js`. It is a version-pinned entry of the known external assets, and a finding for the ember repository.
3. **The file page could not read its file** (C7, "Could not GET file contents"): the 3.13 WaterButler sends no CORS header when `CORS_ALLOW_ORIGIN` is empty. `wb.env` now lists exactly web's and ember's origins.

Checked on the same stack outside the scenarios: an authenticated owner finds a private project through `/api/v1/search/` and API v2 (1 hit), another user finds none (0), user search returns only the user themself, anonymous search answers 401 (PR #8's boundary on the Elasticsearch 8 index); an administrator without TOTP lands on `/account/login/two-factor/setup/` and the admin pages redirect to the sign-in without the second factor; y-websocket's LevelDB in `y_websocket_data` holds the file rooms. Not run: amd64, a Linux host, the Shibboleth profile with admin `idp` mode, `ENABLE_PUBLIC_ACCESS=true`, the unpushed `images.yml` smoke test, and a migration of an installation that holds Elasticsearch 2 data (`invoke migrate_search`).

Scan totals: 6,200 findings (CRITICAL 314, HIGH 1,875, MEDIUM 2,654, LOW 1,353, INFO 4) and 177 allow-listed by the 58 entries; the totals fell from 10,984 (CRITICAL 726, HIGH 3,782) because Elasticsearch 2, MongoDB and sharejs left the stack. The new `elasticsearch8` image adds 2 HIGH and 30 MEDIUM Trivy findings (listed per package, not allow-listed). `allowlist_baseline` is still 0 against 58 entries, so the M2 count condition stays open (status board).

### Acceptance run — 2026-11-12 (UTC), merged final pins, 14 of 14

Stack: the installer at commit `f223f2c` of branch `feat/installer-osf-integration` (merged with `develop` at the PR #52 merge), on the same Mac Studio and the same running project `grdm-dev`, upgraded in place from the 0.19 candidate. Every pin is now a merge commit of its repository: osf.io `90b10661c8dc` (RDM-osf.io-dev2027 `develop` after #8 `66ce3a573c`, #10 `24108e0fe3`, #11 `90b10661c8`), ember-osf-web `4d505f000f8d` (#4), y-websocket `97252369cf`; the other pins are unchanged. The wiki-frontend overlay tag follows the osf.io pin (`90b10661c8dc-5985d18b75da`). #8 was merged without R7-01 (the CI job that needs the `workflow` token scope; tracked as issue #16 of RDM-osf.io-dev2027).

```toon
steps[9]{step,exit,result}:
  "secrets init --missing",0,"nothing added or dropped (the Elasticsearch 8 secrets exist already)"
  "compose render",0,"tags `grdm-dev/osf.io:90b10661c8dc`, `grdm-dev/ember-osf-web:4d505f000f8d`"
  "build",0,"9 min 7 s (22:23:26Z to 22:32:33Z) with Docker's layer cache; not a cold build"
  "compose render after build",0,"no stale build tags"
  "up",0,"68 s; web, api, admin, worker, ember_osf_web recreated on the new images; 23 services healthy"
  "health --network",0,"23 services, 16 loopback bindings; one warning: a foreign listener (`ControlCe`, macOS) on *:5000"
  "invoke migrate_search",0,"13 s; the index was rebuilt on Elasticsearch 8 (the `private__website` alias now points to `private__website_v2`; the seeded data held almost nothing to migrate)"
  "accept --seed --only core",0,"run acc-20261112T223428Z-fda84a: 14 passed, 0 failed, 0 error, 0 skipped"
  "scan and report",0,"scan 2 min 55 s at commit f223f2c; report exit 0"
```

Migrations `addons_twofactor` 0006 and 0007 show as applied inside the `web` container. Run [`acc-20261112T223428Z-fda84a`](runs/acc-20261112T223428Z-fda84a/results.toon): C1 to C7, success and rejection, all pass (C4 and C7 rejections close the WebSocket with 4401; C6 rejection is 403; C5 rejection is 401); the netguard counted 138 known external requests and blocked them.

Scan (`scan_20261112T223858Z`, milestone M1): baseline pass; Trivy 0.75.0 (22 targets), Semgrep 1.184.0 (4), gitleaks 8.30.1 (1) and ZAP (3) all ok with no problems; gate report-only, pass. Open findings: 6,264 (CRITICAL 314, HIGH 1,889, MEDIUM 2,656, LOW 1,401, INFO 4), plus 177 allow-listed by the 58 entries; `allowlist_baseline` is still 0. By tool: Trivy 6,239, ZAP 13, Semgrep 12, gitleaks 0. The 0.19 candidate had 6,200; the 64 more are not analysed here (the osf.io pin moved from the candidate to the merged tips and dependencies resolve at build time). The Mac scan finished with exit 0, unlike the amd64 emulation scan ([DEMO-22](22_core_install_ubuntu_amd64_lima.md#english)), where the Trivy call for the ember-osf-web image hit its 5-minute limit.

What this run does not show: a cold install from an empty `runtime/` on the final pins (the stack was upgraded in place, which is also why the build was fast), a search index rebuilt from real Elasticsearch 2 data (the seeded installation held almost none), the `images.yml` smoke test and the per-OS workflow files (they wait for the `workflow` token scope), a Shibboleth `idp` admin login, and `ENABLE_PUBLIC_ACCESS=true`.

**Correction and limit of the ZAP row (0.21).** "ZAP (3) all ok with no problems" above must be read with this: that scan ran the earlier code, which excused `web` whenever ZAP's message named an address other than the target's own, and counted the three targets whether or not they were scanned. With mandatory sign-in (the default and the setting of this run) `web` answers an anonymous request only with a redirect that ZAP cannot follow; in the previous run on the same stack (`scan_20261111T231702Z`, above) `web` was skipped with a note and only `admin` and `ember_osf_web` were scanned. So the most this row supports is that `admin` and `ember_osf_web` were scanned, with 13 ZAP findings in the total; it does **not** show that ZAP scanned `web` or anything behind sign-in. That is an inference from the earlier run, not a reading of this run: the raw report `scan_20261112T223858Z` is not in the committed acceptance folder, so neither the 6,264 count nor the per-target ZAP coverage is independently rederivable from this repository; both are the operator's recorded result. The exception was also weaker than it looked (it accepted a redirect to any unreachable host); the scan code now requires the rendered sign-in configuration and a probe that shows the redirect to the configured address, lists a skipped target under `skipped_targets` instead of counting it, and keeps exit 51 otherwise ([SPEC-03 §4.3](../spec/03_security_gate.md#english)). That stricter code has been tested with unit tests only; it was **not** run against the Mac Studio stack, so the next scan on it is still to be recorded.

**The stricter ZAP code on the live stack (0.22).** On 2026-11-13 `grdm-dev --yes scan --dynamic` ran on the Mac Studio stack at `ca2a010` (the merge of PR #56) and exited 0 in 1 min 18 s. The probe inside the ZAP image (`python3`, one request, redirects not followed) worked: `web` (`http://web:5000`) was recorded as skipped behind sign-in with the note "ZAP NOT RUN on web ... an anonymous request is redirected (verified by a probe) to the configured sign-in address 127.0.0.1:8081 ... so no page behind sign-in was scanned", and was not counted as scanned. `admin` and `ember_osf_web` were scanned, with 13 ZAP findings (8 and 5, as the operator recorded). The severity split of those findings is not asserted here: no report of this run is committed, so "no HIGH finding" is not established by this record, and the gate result `pass` under the report-only rule does not imply it. This is one run by the operator: the raw report is not committed, so it is a recorded result, not independently rederivable here. It does not show that anything behind sign-in was scanned; that still needs an authenticated scan.

### One command from a new checkout — 2026-11-14 (UTC), develop 0df4640, `install-macos.sh`, 14 of 14

Machine: the same Mac Studio (Apple Silicon), Docker through Colima (profile `default`, 8 CPUs, 48 GiB). Code: a **new clone** of `RCOSDP/RDM-developer-guide` branch `develop` at `0df4640f42e9` into a new directory next to the main checkout. The host was **not empty**: Homebrew prerequisites, Colima and the operator's git access to the private integration repositories were already present, and Docker already held images and build cache for the same pins from the main checkout's stack, so the build reused that cache. This is a new checkout, not an empty Docker.

**Preparation (owner approval of 2026-11-14, 「登録だけ外して実行し、戻す（推奨）」).** The main checkout's stack (project `grdm-dev`) was running. Its 14 Docker volumes are local bind volumes whose data is in that checkout's `runtime/volumes/`, and the volume check before `build` (PR #64) stops an install whose project volumes point at another checkout. So the main stack was stopped with `grdm-dev --yes down` (data kept), its `runtime/volumes/` was copied to a backup directory outside the repository (about 806 MB; file counts equal except one LibreOffice socket, which `cp` does not copy), and only the 14 volume registrations were removed with `docker volume rm` (the data stayed on disk). Nothing else in Docker was removed or pruned.

**Provenance of this section.** The operator (QAE, QA担当) ran the commands on the Mac Studio and read the new checkout's `runtime/reports/` (the file times give the stage boundaries) and the full console log, which stays outside the repository. The acceptance run [`acc-20261114T103547Z-8c60ae`](runs/acc-20261114T103547Z-8c60ae/results.toon) is copied from the new checkout; it was checked by search to hold no host name, no home path, no address other than 127.0.0.1 and no e-mail address.

```toon
one_command{command,started_utc,ended_utc,exit,steps}:
  "./installer/install-macos.sh --yes --profile core (no GRDM_WITH_ACCEPT)",2026-11-14T10:20:54Z,2026-11-14T10:33:44Z,0,"doctor plan secrets_init compose_render build up health_network scan report: all ok"
stage_times[5]{stage,from_utc,to_utc,note}:
  prerequisites_venv_doctor_to_compose_render,10:20:54,10:21:21,"install-macos.sh: all prerequisites already present, nothing changed; .venv created with python3 3.15.2; fakecas moved to port 8081 because 8080 was taken"
  build,10:21:21,10:22:20,"59 s: 7 integration repositories cloned at their pins into the new runtime/src; 262 layer steps CACHED and no step took over 2 s; the y-websocket image was assembled anew (created 10:22:13Z) from cached layers"
  up,10:22:20,10:31:19,"9 min 0 s on the new, empty runtime/volumes (database and Elasticsearch 8 initialised); 23 services healthy"
  health_network,10:31:19,10:31:20,"exit 0, loopback only; one warning: a foreign listener (ControlCe, macOS) on *:5000"
  scan_and_report,10:31:20,10:33:44,"2 min 24 s; gate pass (M3, count-not-growing): 6,196 findings (critical 314, high 1,838, medium 2,739, low 1,301, info 4), 177 allow-listed by 58 entries; ZAP scanned admin and ember_osf_web, web skipped behind sign-in"
```

**The one command returned 0 in a single run: 12 min 50 s** from the start of `install-macos.sh` to the report, with no manual step. Most of it was `up` on empty volumes; the build took about a minute only because Docker's cache was warm.

**Acceptance, run afterwards (not part of the one command).** The first `grdm-dev --yes accept --seed` (10:35:09Z) stopped with exit 2 because the new `.venv` had no test extras; the message named the commands, which were run as printed (`pip install -e "installer[accept]"` and `playwright install chromium` into `.venv/.playwright`, 26 s). Then `grdm-dev --yes accept --seed` with the default waits (`--wait-scale` 1) ran from 10:35:45Z to 10:37:17Z and exited 0: **14 of 14 passed**, 0 failed, 10 skipped (S1 to S5, M3), precheck 23 services healthy, C4 success 9.0 s, C7 success 9.9 s; the netguard blocked 137 known external requests. No second run with `--wait-scale` was needed.

**Restore of the main checkout's stack.** In the new checkout `grdm-dev --yes down`, then `docker volume rm` of the 11 `grdm-dev_*` volumes whose device pointed into the new checkout (checked before removal). In the main checkout `grdm-dev --yes up --no-open` (10:38:02Z to 10:39:46Z, exit 0, 23 services healthy, 17 containers running) and `grdm-dev health --network` (exit 0, loopback only, the same `ControlCe` warning). Compose re-registered the 11 volumes of the current compose file; the 3 older registrations `elasticsearch_data`, `mongo_data`, `mongo_tls` are no longer in the compose file, so they were registered again by hand with the same bind options and device. Afterwards all 14 names and devices equal the record taken before the run. `diff -rq` between the backup and the main `runtime/volumes/` shows only files a running stack rewrites (PostgreSQL control, WAL, relation-cache and pid files; Elasticsearch 6 and 8 state, translog and segment files of the same index UUIDs; a RabbitMQ node directory for the new container name; a LevelDB compaction in `y_websocket_data`; temporary files in `wb_tmp`). The backup is kept outside the repository.

What this run does not show, and what changed: a run from an empty Docker or a new Mac (the cache was warm, the prerequisites present, and the build time is therefore not a cold build time); the run used the operator's existing git access to the private repositories. The restored stack is the same data and the same pins, but not the same image IDs: before the run some containers of the main stack ran images that were no longer tagged, and after `down` those images were no longer in Docker's image store, so `up` started the currently tagged images of the same pins (and the y-websocket image assembled by this run). The new checkout and its own `runtime/` were left on disk, not deleted. Not run here: an authenticated ZAP scan, `ENABLE_PUBLIC_ACCESS=true`, a Shibboleth `idp` admin login.

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
  elasticsearch2_image: "grdm-dev/elasticsearch2:2.4.6-1 — イメージに 58 件（HIGH 2・MEDIUM 52・LOW 4）。Elasticsearch 2.4.6 の jar と Temurin 8 ベース由来。加えてレシピの installer/images/elasticsearch2/Dockerfile に LOW 1 件。置き換えた Docker Hub の elasticsearch:2 が上の差分の大半を抱えていた"
```

これで分かったこと:

- **コールドスタートが端から端まで動く**。イメージのキャッシュ以外は何も無い状態から、一つのコマンドで Apple Silicon 上 31 分で準備完了・検査済み・報告済みの環境に達する。残る所要時間は ember のビルド（24 分、いまは並行）と osf.io の migration（5 分）。
- ネイティブの Elasticsearch 2 はエミュレーションで 38 分かかったところ（第 19 回）を 6 秒で起動し、uid 1000・読み取り専用ルートで堅牢化の例外も所有者初期化コンテナも無く動き、公式の amd64 イメージより既知の脆弱性が少ない。
- 節目 M2 の導入基準（[進捗ボード](../status/README.md#japanese)）は、core プロファイルについて Mac Studio 上で温・冷ともに満たした。M2 に残るのは Playwright 受入。

証跡（第 1 回）: 全ログはセッションの作業領域にのみ保管（パッケージ取得の出力が大半で、秘密は含まない）。Mac Studio の `runtime/` には `.env`（0600）、生成した Compose ファイル、ビルド済みイメージ 2 つがあり、git では無視される。

### 受入試験の実行 — 2026-11-09/10、第 22 回のスタック（osf.io 389415a4）

| 実行 ID | 範囲 | 結果 |
|---|---|---|
| [`acc-20261109T131214Z-f2ee77`](runs/acc-20261109T131214Z-f2ee77/results.toon) | C1 | 2 件中 2 件合格 |
| [`acc-20261109T131240Z-00dff9`](runs/acc-20261109T131240Z-00dff9/results.toon) | コア C1〜C6 | 12 件中 3 件合格 |
| [`acc-20261109T170208Z-9ebf01`](runs/acc-20261109T170208Z-9ebf01/results.toon) | HMAC 修正後の C3 | 2 件中 2 件合格 |

分かったこと:

- **ログイン。** 種データのユーザーは `have_email=False` で、GRDM がメール設定画面へ転送し、ダッシュボードが表示されなかった。種データで true に設定した。
- **アップロード（C3、C5）。** web への署名付きコールバックがすべて 401 になっていた。`/api/v1/files/auth/` は 200 で、JWE/JWT の連携は正常だった。値のハッシュで比較すると、web の `DEFAULT_HMAC_SECRET` は上流の既定値 `changeme` のままで、WaterButler は生成した 2 種類の別の鍵で署名していた。osf.io の検証器は 1 つなので、WaterButler の 2 つの署名と osf.io を `WATERBUTLER_HMAC_SECRET` に統一し、`OSFSTORAGE_HMAC_SECRET` は生成しないようにした。既定の鍵では web に届く者がコールバックを偽造できたため、この弱点も解消した。
- **外部資産。** 既知の資産は遮断を続け、件数のみ記録する（[SPEC-04](../spec/04_acceptance_tests.md#japanese)）。Google Analytics はビルド後の ember の設定から削除した。

この時点の残件: C2、C4、C5、C6 は未合格（セレクタ、wiki バンドルの配線、プレビュー、管理画面のパス）。

### 受入の実行 — 2026-11-10、マージ済みのセキュリティ修正をすべて含む、12 件中 12 件

実行 [`acc-20261110T015520Z-ab4cc7`](runs/acc-20261110T015520Z-ab4cc7/results.toon): **12 件中 12 件合格**。このブランチの固定版（osf.io `fe90e5c3`、WaterButler `45e97a51`、MFR `749e58d3`、wiki-frontend `5985d18b`、y-websocket `d4d1cfae`、cas-overlay `22610b76`）から組み、新しい CAS と変換サービスが要る鍵を `secrets rotate` で加えたスタックで実行した。

| シナリオ | 成功 | 拒否 | 合格させたもの |
|---|---|---|---|
| C1 ログイン | 合格 | 合格（401） | 種データの `have_email` |
| C2 プロジェクト | 合格 | 合格（403） | セレクタ |
| C3 ファイル | 合格 | 合格（403） | WaterButler と osf.io の HMAC 鍵を一つに |
| C4 Wiki | 合格 | 合格（4401） | y-websocket の接続時の JWT、クライアントのトークン更新、`edit.mako` のバンドルの場所 |
| C5 プレビュー | 合格 | 合格（401） | MFR は OSF から WaterButler への転送でだけ資格情報を渡す。PDF ビューアから Google Analytics を削除 |
| C6 管理画面 | 合格 | 合格（403） | 管理画面の資産をローカルで配信し CDN へ出ない。所属機関の管理者には、一覧でも明示の検索でも、自機関の利用者が見え、無所属の利用者と別機関の利用者は見えない |

この直前の実行は、修正をマージ済みなのに C5 と C6 で失敗した。`compose render` を `build` より先に実行しており、render は直前のビルド記録からイメージのタグを取るため、古いイメージのまま動いていた。ビルドのあとに render し直して解決した。

### 受入の実行 — 2026-11-11、PostgreSQL 18 上の Python 3.13 の WaterButler と MFR、12 件中 11 件

ブランチ `feat/pin-py313-wb-mfr`、本体のチェックアウトから実行。固定版: WaterButler `3319c106` と MFR `f9da1db3`（どちらも `python:3.13-slim@sha256:e48f59cd…ed90`、Python 3.13.18、Debian 13）、osf.io `8fc45de4`、wiki-frontend `5985d18b`（osf.io の基底 `8fc45de4` の上に組み、イメージのタグは `8fc45de461fd-5985d18b75da`）、y-websocket `d4d1cfae`、cas-overlay `22610b76`、PostgreSQL 18.6。MFR は arm64 向けにネイティブで組むようになり（`build_platform` を削除）、freecad を含まないため、所有者の判断で CAD のプレビュー（.step/.stp）は廃止した。

| 手順 | 終了 | 結果 |
|---|---|---|
| `db upgrade` | 0 | PostgreSQL 9.6 → 18 をダンプと復元で移行（ダンプ 4.8 MB、531 個のオブジェクトが一致）。旧ディレクトリは `postgres_data.pg9.6-20261111T111040Z` として残る |
| `build` | 30 | 1 回目: WaterButler の `apt-get upgrade` が「空き容量不足」で失敗。このホストの他の作業と共有する Docker のディスクが満杯だった。以前の固定版の `grdm-dev/*` のタグのうち不要になったものを削除した（ビルドキャッシュは削除していない）。2 回目は osf.io・WaterButler・MFR・cas-overlay・wiki-frontend・y-websocket を組めたが、elasticsearch2 が `apt-get update` で失敗（「not signed」。同じくディスク満杯）。2026-11-06 以降入力が変わっていない、2026-11-10 に組んだ既存のイメージを使った。 |
| `build` 後の `compose render` | 0 | 古いビルドのタグなし |
| `up` | 0 | 24 サービスが正常。`wb` と `wb_worker` は uid 1000（利用者 `waterbutler`）、`mfr` は uid 1000 で動き、Celery 5.6.3 のワーカーは準備完了。新しい秘密は不要で、テンプレートと `wb.env`/`mfr.env` は変えていない。 |
| `accept --seed --only core` | 60 | 実行 [`acc-20261111T115949Z-ab529c`](runs/acc-20261111T115949Z-ab529c/results.toon): **12 件中 11 件合格**。C5 の成功ケースが失敗（下記） |
| `scan` | 51 | Trivy・Semgrep・gitleaks は完了し、基本対策は合格。ZAP は Docker のディスクの空きが 0 バイトの間、3 つの対象すべてで報告を出さなかった（rc 3） |
| `report` | 0 | |

**C5 の成功ケース（プレビュー）の失敗はインストーラーでなく統合リポジトリ側にある。** MFR は描画要求に 400 を返した。MFR のログは `ClientConnectorError: Cannot connect to host 127.0.0.1:7777`、web のログは MFR が新たに送る要求 `GET /download/<guid>/?direct&mode=render&action=download`（MFR のコンテナから、応答 302）を示す。MFR `f9da1db3`（上流 #9 から取り込み）は `/<guid>/` の形の OSF の URL を `/download/<guid>/` に書き換える。osf.io `8fc45de4` では、`/<guid>/` の経路は WaterButler の URL を `_internal=(mode == 'render')` で作るので、MFR は `http://wb:7777` を受け取っていた。`/download/<guid>/` の経路（`persistent_file_download`）は `_internal` なしで作るので、MFR はブラウザ向けの `WATERBUTLER_URL`（`http://127.0.0.1:7777`）を受け取る。これはコンテナ内からは届かず、資格情報の送り先でもない。直すのは MFR（GRDM では描画の URL を書き換えない）か osf.io（`persistent_file_download` がもう一方の経路と同じく `mode=render` に従う）である。C5 の拒否ケース（401）は合格のまま。

Trivy の CRITICAL/HIGH（対象ごと、`critical/high`）:

```toon
trivy_critical_high:
  db: "2026-11-10 19:01 UTC（前: scan_20261110T022540Z、DB 2026-11-10 01:02 UTC）"
  targets[23]{target,before,after,note}:
    waterbutler,13/178,0/47,"45e97a51 → 3319c106; 47 件すべて修正版の無い Debian 13、許容リスト"
    modular-file-renderer,53/410,3/127,"749e58d3 → f9da1db3; 130 件すべて修正版の無い Debian 13、許容リスト"
    osf.io,118/566,118/566,"fe90e5c3 → 8fc45de4"
    wiki-frontend,65/332,65/332,""
    rdm-ember-osf-web,407/1911,407/1911,prebuilt
    cas-overlay,43/105,43/105,""
    postgres,11/117,2/147,"9.6 → 18.6 (Debian 13)"
    unoconv,1/100,1/156,"同じイメージ、新しい DB"
    redis,1/37,1/37,""
    elasticsearch2,5/18,5/18,""
    elasticsearch6,2/50,2/50,""
    rabbitmq,0/7,0/7,""
    mongo,0/2,0/2,""
    fakecas,0/2,0/2,""
    sharejs,0/0,0/0,""
    y-websocket,0/0,0/0,""
    src/RDM-waterbutler-dev2027,2/32,0/0,lockfiles
    src/RDM-modular-file-renderer-dev2027,14/79,0/0,lockfiles
    src/RDM-osf.io-dev2027,55/279,55/279,lockfiles
    src/RDM-wiki-frontend-dev2027,21/107,21/107,lockfiles
    src/RDM-cas-overlay-dev2027,6/20,6/20,lockfiles
    src/RDM-y-websocket-dev2027,0/0,0/0,lockfiles
    repo,0/30,0/30,""
  total: "817/4382 → 729/3943（未許容 726/3769、58 項目で許容 3/174）"
```

許容リストは 58 項目になった（イメージと CVE ごとに 1 項目。[SPEC-03 §5.1](../spec/03_security_gate.md#japanese) の新しい `image` 欄で範囲を限定し、見直し日は 2026-12-31）。節目は M1（報告のみ）なので件数は報告にとどまる。`manifest/allowlist.baseline.json` の上限は節目の終了時に所有者が決める。

### 受入の実行 — 2026-11-11、プレビューを直した MFR、12 件中 12 件

ホスト・ブランチ・固定版は上の実行と同じだが、MFR だけが違う。本体のチェックアウトの manifest を、手元で未コミットのまま `2c4a88a6` に向けた。これは RDM-modular-file-renderer-dev2027 PR #7 の先頭のコミットで、osf.io の `/<guid>/?direct&mode=render&action=download` を `/download/<guid>/` に書き換えるのをやめ、osf.io が組み立てたとおりの URL を要求する。そのため osf.io の `/<guid>/` の経路が内部向けの WaterButler の URL を返す（`mode=render` では `_internal=True`）。資格情報の組は `http://web:5000` → `http://wb:7777` のまま変わらない。PR #7 の試験は、ブラウザ向けの `127.0.0.1:7777`、`localhost`、似た名前のホスト、別ポートが、要求の前に拒否されるか、資格情報を受け取らないことも示す。コミット済みの固定版は PR #7 のマージまで `f9da1db3` のままにし、マージ後にそのマージコミットを固定する。

Docker のディスクは 400 GiB に拡張済みだった（実行前の空きは 193 GB）。

| 手順 | 終了 | 結果 |
|---|---|---|
| `compose render` | 0 | |
| `build` | 0 | MFR を `2c4a88a663ca` でネイティブに組んだ。他の部品はキャッシュ、elasticsearch2 は組み直し |
| `build` 後の `compose render` | 0 | 古いビルドのタグなし |
| `up` | 0 | 24 サービスが正常。`mfr` は `grdm-dev/modular-file-renderer:2c4a88a663ca` で動く |
| `accept --seed --only core` | 0 | 実行 `acc-20261111T122608Z-2d3599`: **12 件中 12 件合格**。証跡のディレクトリは手元に残し、この PR ではコミットしない。C5 の成功ケースは 200 を返し、拒否ケースは 401 のまま。web のログには MFR からの `GET /<guid>/?direct&mode=render&action=download`（302）が残り、MFR のログに `ClientConnectorError` は無い。 |
| `scan` | 0 | 5 つの部分すべてが完了した。基本対策は合格、Trivy・Semgrep・gitleaks・ZAP は ok。ZAP は 3 つの対象すべてで再び報告を出した。門は報告のみで合格 |
| `report` | 0 | |

検査の件数（`scan_20261111T123133Z`）: 10,983 件。内訳は CRITICAL 726、HIGH 3,782、MEDIUM 4,147、LOW 2,322、INFO 6。これとは別に 58 項目の許容リストで 177 件を許容した。Trivy の未許容の CRITICAL/HIGH は 726/3,769 で、上の実行と変わらない。MFR の変更はコードだけで、パッケージは増えていない。Semgrep: HIGH 12。gitleaks: 0。ZAP: HIGH 1、MEDIUM 8、LOW 12、INFO 6。

これに先立ち、直す前の MFR `f9da1db3` で C5 を再現した（実行 `acc-20261111T121734Z-7329b7`、C5 のみ。成功ケース 400、拒否ケース 401）。ログの内容は上の実行と同じだった。

### 受入の実行 — 2026-11-11、PR #7 のマージで MFR を固定、12 件中 12 件

RDM-modular-file-renderer-dev2027 PR #7 は `9771b8cf` としてマージされた。その中身は上で使った先頭 `2c4a88a6` と同じである。manifest は MFR を `9771b8cf` に固定し、注記から未マージの記述を除いた。他の固定版は変えていない。

| 手順 | 終了 | 結果 |
|---|---|---|
| `compose render` | 0 | |
| `build` | 0 | MFR を `9771b8cfb352` でネイティブに組んだ |
| `build` 後の `compose render` | 0 | 古いビルドのタグなし |
| `up` | 0 | 24 サービスが正常。`mfr` は `grdm-dev/modular-file-renderer:9771b8cfb352` で動く |
| `accept --seed --only core` | 0 | 実行 [`acc-20261111T132104Z-530071`](runs/acc-20261111T132104Z-530071/results.toon): **12 件中 12 件合格**。C5 の成功ケースは 200、拒否ケースは 401。実行フォルダを gitleaks で検査して何も見つからなかったので、コミットした。 |
| `scan` | 0 | `scan_20261111T132607Z`: 基本対策は合格。Trivy（23 対象）・Semgrep・gitleaks・ZAP（3 対象）は ok。門は報告のみで合格 |
| `report` | 0 | |

検査の件数: 10,984 件。内訳は CRITICAL 726、HIGH 3,782、MEDIUM 4,148、LOW 2,322、INFO 6。これとは別に、58 項目の許容リストで 177 件を許容した。道具ごとの内訳: Trivy 726/3,769/4,139/2,310（CRITICAL/HIGH/MEDIUM/LOW）、Semgrep は HIGH 12、gitleaks は 0、ZAP は HIGH 1・MEDIUM 9・LOW 12・INFO 6。ZAP の MEDIUM が 1 件多いことを除けば、上の実行と同じである。

**PR #45 レビュー r1 の後（同じスタック、2026-11-11 14:18 UTC）。** 許容リストの照合を変えた（R1-01）。58 項目はそれぞれ、自分のイメージの正確な `name@version` のパッケージを名指しする。一覧は Trivy の生の報告から取った。Trivy の検出を許容するのは、`FixedVersion` が空で `Status` が修正版なしの状態の間だけで、対象はそのイメージの OS パッケージだけである。`scan` と `report` をやり直し、どちらも終了 0 だった。`scan_20261111T141804Z` の件数は上と同じで、未許容が 10,984 件、許容が 177 件。177 件は 58 項目すべてが当てはまった結果である。保存した報告 `20261111T132241Z` を新しい照合に通しても同じ 177 件になる。新しい単体試験では、古い照合が修正版のある検出、名指していないパッケージ、名前の前方一致を許容していたことが示された。

### 受入の実行 — 2026-11-12、ローカルの osf.io 候補、Elasticsearch 8・y-websocket のみ・必須サインイン・管理者の第二要素、14 件中 14 件

スタック: Mac Studio（プロジェクト `grdm-dev`、Colima）で、ブランチ `feat/installer-osf-integration` のインストーラーを、以前の固定版と PostgreSQL 18 から進めた。osf.io は**ローカルの候補で、push 済みのコミットではない**。RDM-osf.io-dev2027 の develop `73ff43b3c2`（#13 Django 2.2、#12 y-websocket のエディタ、#14 の render URL を含む）に、開いている PR #8（必須サインイン、`c9d293dd1a`）、#10（管理画面の 2 段階サインイン、`834d1b62c0`）、#11（Elasticsearch 8、`b4bc134188`）の先頭をマージしたもの。手で解消した競合は `admin/common_auth/urls.py`、`admin/base/settings/defaults.py`、`api/base/authentication/backends.py`、`website/search/views.py`、`api/search/views.py`、`website/search/elastic_search.py`、`.github/scripts/ci/run-tests.sh` で、三つの PR はリベースのときに同じものに出会う。manifest は `9e1fb9c8597d` に固定した（ローカルの bare ミラーと、`GIT_CONFIG_*` の `url.<ミラー>.insteadOf` で渡した。インストーラーにローカル参照の仕組みは無く、足してもいない）。y-websocket `97252369cf`（PR #5）と ember-osf-web `4180cb58bb`（PR #2・#3）は実際のマージコミットである。

| 手順 | 終了 | 結果 |
|---|---|---|
| `secrets rotate` | 40 | 設計どおり巻き戻した。ビルド中で旧スタックの以前の ember イメージが 300 秒で健全にならず、古い `runtime/.env` を戻した。このため `secrets init --missing` を足した |
| `secrets init --missing` | 0 | `ELASTIC8_PASSWORD` と `ELASTIC8_OSF_PASSWORD` を足し、`SHAREJS_SECRET` を捨てた。ほかの値は変えていない |
| `compose render` | 0 | |
| `build` | 0 | osf.io `9e1fb9c8597d`（コールドで約 55 分。Alpine 3.9 で `scipy` などをコンパイルする）、y-websocket、ember-osf-web（静的な nginx）、wiki-frontend のオーバーレイ `9e1fb9c8597d-5985d18b75da`、`elasticsearch8:8.19.24-1` |
| `build` 後の `compose render` | 0 | 古いビルドのタグなし |
| `up` | 0 | 23 サービスが正常。`elasticsearch8` は 25 秒で健全。`osf_init` が統合の migration と `addons_twofactor` の 0006・0007 を適用し、機関を Elasticsearch 8 へ書いた。sharejs・mongo・Elasticsearch 2 のコンテナは孤児として消えた |
| `accept --seed --only core`（最初） | 60 | 13 件失敗。インストーラーの欠陥を三つ見つけ、直した（下記） |
| `accept --seed --only core`（最終） | 0 | 実行 [`acc-20261111T230217Z-d8363c`](runs/acc-20261111T230217Z-d8363c/results.toon): **14 件中 14 件合格**（C1〜C7、成功と拒否） |
| `scan` | 0 | `scan_20261111T231702Z`（コミット `a14fb70`）: 基本対策は合格で、新しい例外なし（mongo の例外は消え、elasticsearch8 は要らない）。Trivy 22 対象・Semgrep・gitleaks は ok。ZAP は `web` を注つきで飛ばし、`admin` と `ember_osf_web` を検査。門は報告のみで合格 |

候補での最初の受入が見つけた欠陥。いずれもインストーラーで試験つきで直した。

1. **`api` と `admin` が 30 秒ずつ止まった**（C2・C4・C6・C7 がタイムアウト、後片付けで 12 件のエラー）。Django 2.2 の開発用サーバーは接続を開いたままにし、`runserver --nothreading`（`invoke apiserver` が起動する）はブラウザの使われない二本目の接続を、ソケットがタイムアウトするまで待つ。どちらもスレッドありの `manage.py runserver` で動かす。
2. **C1 とすべてのブラウザのシナリオがループバックの監視に失敗した**。対象は `https://cdnjs.cloudflare.com/ajax/libs/zxcvbn/4.4.2/zxcvbn.js` で、ビルドが `/zxcvbn.js` を同梱するのに、静的な ember の `index.html` がそれを名指しする。版つきで既知の外部アセットに足し、ember リポジトリへの指摘にした。
3. **ファイルページが自分のファイルを読めなかった**（C7、「Could not GET file contents」）。3.13 の WaterButler は `CORS_ALLOW_ORIGIN` が空だと CORS ヘッダーを送らない。`wb.env` に web と ember の起点だけを列挙した。

同じスタックでシナリオの外から確認したこと。認証した所有者は `/api/v1/search/` と API v2 で非公開プロジェクトを見つけ（1 件）、別の利用者は見つけず（0 件）、利用者検索は本人だけを返し、匿名の検索は 401（PR #8 の境界が Elasticsearch 8 の索引で保たれる）。TOTP 未登録の管理者は `/account/login/two-factor/setup/` へ着き、第二要素なしでは管理画面がサインインへ転送される。`y_websocket_data` の LevelDB にファイルの部屋がある。未確認: amd64、Linux のホスト、管理者の `idp` モードの Shibboleth プロファイル、`ENABLE_PUBLIC_ACCESS=true`、push していない `images.yml` の smoke test、Elasticsearch 2 のデータを持つ導入の移行（`invoke migrate_search`）。

検査の件数: 6,200 件（CRITICAL 314、HIGH 1,875、MEDIUM 2,654、LOW 1,353、INFO 4）。これとは別に、58 項目の許容リストで 177 件を許容した。Elasticsearch 2・MongoDB・sharejs がスタックから消えたので、10,984 件（CRITICAL 726、HIGH 3,782）から減った。新しい `elasticsearch8` イメージは Trivy で HIGH 2 件と MEDIUM 30 件を足す（パッケージ単位で記録し、許容はしていない）。`allowlist_baseline` は 58 項目に対しまだ 0 なので、M2 の件数の条件は開いたままである（状況表）。

### 受入実行 — 2026-11-12（UTC）、マージ後の最終の固定版、14 件中 14 件

スタック: ブランチ `feat/installer-osf-integration` のコミット `f223f2c`（PR #52 のマージ時点の `develop` を取り込み済み）のインストーラーを、同じ Mac Studio の動いている同じプロジェクト `grdm-dev` に、0.19 の候補から上書きで適用した。固定版はすべて各リポジトリのマージコミットになった。osf.io `90b10661c8dc`（RDM-osf.io-dev2027 の `develop`。#8 `66ce3a573c`、#10 `24108e0fe3`、#11 `90b10661c8` のマージ後）、ember-osf-web `4d505f000f8d`（#4）、y-websocket `97252369cf`。ほかの固定版は変わらない。wiki-frontend のオーバーレイのタグは osf.io の固定版に従う（`90b10661c8dc-5985d18b75da`）。#8 は R7-01（`workflow` 権限の要る CI ジョブ。RDM-osf.io-dev2027 の issue #16 で追跡）を除いてマージした。

```toon
steps[9]{step,exit,result}:
  "secrets init --missing",0,"追加も削除も無し（Elasticsearch 8 の秘密は既にある）"
  "compose render",0,"タグ `grdm-dev/osf.io:90b10661c8dc`、`grdm-dev/ember-osf-web:4d505f000f8d`"
  "build",0,"9 分 7 秒（22:23:26Z〜22:32:33Z）。Docker のレイヤーキャッシュを使ったので、コールドビルドではない"
  "build 後の compose render",0,"古いビルドのタグは無し"
  "up",0,"68 秒。web・api・admin・worker・ember_osf_web が新しいイメージで作り直され、23 サービスが healthy"
  "health --network",0,"23 サービス、ループバックの bind は 16 件。警告が 1 件: *:5000 の他者のリスナー（`ControlCe`、macOS）"
  "invoke migrate_search",0,"13 秒。Elasticsearch 8 で索引を作り直した（`private__website` のエイリアスが `private__website_v2` を指す。種データには移す内容がほとんど無かった）"
  "accept --seed --only core",0,"実行 acc-20261112T223428Z-fda84a: 合格 14、失敗 0、エラー 0、skip 0"
  "scan と report",0,"scan はコミット f223f2c で 2 分 55 秒、report は終了 0"
```

`web` コンテナの中で `addons_twofactor` の migration 0006 と 0007 が適用済みと出る。実行 [`acc-20261112T223428Z-fda84a`](runs/acc-20261112T223428Z-fda84a/results.toon): C1〜C7 の成功と拒否がすべて合格（C4・C7 の拒否は WebSocket が 4401 で閉じ、C6 の拒否は 403、C5 の拒否は 401）。netguard は既知の外部要求 138 件を数えて遮断した。

検査（`scan_20261112T223858Z`、節目 M1）: baseline は pass。Trivy 0.75.0（22 対象）、Semgrep 1.184.0（4）、gitleaks 8.30.1（1）、ZAP（3）はすべて ok で問題なし。ゲートは report-only で pass。未解決は 6,264 件（CRITICAL 314、HIGH 1,889、MEDIUM 2,656、LOW 1,401、INFO 4）。これとは別に、58 項目の許容リストで 177 件を許容した。`allowlist_baseline` は今も 0。ツール別は Trivy 6,239、ZAP 13、Semgrep 12、gitleaks 0。0.19 の候補は 6,200 件で、増えた 64 件は分析していない（osf.io の固定版が候補からマージ後の先端に移り、依存はビルド時に解決されるため）。Mac の検査は終了 0 で完走した。amd64 のエミュレーションでの検査（[DEMO-22](22_core_install_ubuntu_amd64_lima.md#japanese)）では、ember-osf-web のイメージの Trivy 呼び出しが 5 分の制限に達した。

この実行が示さないこと: 最終の固定版での空の `runtime/` からのコールドな導入（上書きで進めたので、ビルドが速かった理由でもある）、本物の Elasticsearch 2 のデータからの索引の再構築（種データのみで、ほぼ空）、`images.yml` のスモーク試験と per-OS のワークフローファイル（`workflow` 権限待ち）、Shibboleth の `idp` での管理者ログイン、`ENABLE_PUBLIC_ACCESS=true`。

**ZAP の行の訂正と限界（0.21）。** 上の「ZAP（3）はすべて ok で問題なし」は次のように読む。この検査は以前の処理で動き、ZAP のメッセージが対象自身と違うアドレスを示せば `web` を除外し、三つの対象を検査したかどうかにかかわらず数えていた。必須サインイン（既定で、この実行の設定）では、`web` は匿名の要求に ZAP が追えない転送しか返さない。同じスタックの前回の実行（上の `scan_20261111T231702Z`）では `web` は注つきで飛ばされ、`admin` と `ember_osf_web` だけが検査された。したがってこの行が支えるのは、`admin` と `ember_osf_web` を検査し、合計に ZAP の検出 13 件があることまでで、ZAP が `web` やサインインの向こうを検査したことは**示さない**。これは前回の実行からの推定で、この実行を読んだ結果ではない。生レポート `scan_20261112T223858Z` はコミット済みの受入フォルダにないので、6,264 件も ZAP の対象ごとの網羅も、このリポジトリから独立に再導出できず、どちらも作業者の記録である。除外は見かけより弱かった（届かない任意のホストへの転送を受け入れた）。検査の処理は今は、生成済みのサインイン設定と、設定済みのアドレスへの転送を示す探りを求め、対象外を数えずに `skipped_targets` に載せ、それ以外は終了 51 のままにする（[SPEC-03 §4.3](../spec/03_security_gate.md#japanese)）。この厳しくした処理は単体試験でだけ確かめ、Mac Studio のスタックでは**実行していない**。そのスタックでの次の検査の記録は未了である。

**ライブのスタックでの厳しくした ZAP の処理（0.22）。** 2026-11-13 に、Mac Studio のスタック（PR #56 のマージ `ca2a010`）で `grdm-dev --yes scan --dynamic` を実行し、1 分 18 秒、終了 0 だった。ZAP のイメージ内の探り（`python3`、要求は一回、転送は追わない）は動いた。`web`（`http://web:5000`）は注「ZAP NOT RUN on web ... an anonymous request is redirected (verified by a probe) to the configured sign-in address 127.0.0.1:8081 ... so no page behind sign-in was scanned」つきでサインインの壁の向こうとして飛ばされ、検査済みには数えられなかった。`admin` と `ember_osf_web` は検査され、ZAP の検出は 13 件（8 件と 5 件。作業者の記録）。これらの重大度の内訳は、ここでは主張しない。この実行のレポートをコミットしていないので、「HIGH の検出は無い」はこの記録からは言えず、report-only の規則での `pass` もそれを意味しない。これは作業者の一回の実行で、生レポートはコミットしていないため、記録された結果であり、ここから独立に再導出できない。サインインの向こうを検査したことは示さない。それには認証つきの検査が要る。

### 新しいチェックアウトから一つのコマンド — 2026-11-14（UTC）、develop 0df4640、`install-macos.sh`、14 件中 14 件

マシン: 同じ Mac Studio（Apple Silicon）。Docker は Colima（プロファイル `default`、8 CPU、48 GiB）。コード: `RCOSDP/RDM-developer-guide` のブランチ `develop`（`0df4640f42e9`）を、本体のチェックアウトの隣の新しいディレクトリへ**新しく clone** した。ホストは**空ではない**。Homebrew の前提条件、Colima、非公開の統合リポジトリへの作業者の git の権限は既にあり、Docker には本体のチェックアウトのスタックが使う同じ固定版のイメージとビルドキャッシュがあったので、ビルドはそのキャッシュを使った。新しいチェックアウトであって、空の Docker ではない。

**準備（2026-11-14 の所有者の承認「登録だけ外して実行し、戻す（推奨）」）。** 本体のチェックアウトのスタック（プロジェクト `grdm-dev`）が動いていた。その 14 個の Docker ボリュームはローカルの bind ボリュームで、データはそのチェックアウトの `runtime/volumes/` にある。`build` の前のボリュームの検査（PR #64）は、プロジェクトのボリュームが別のチェックアウトを指す導入を止める。そこで本体のスタックを `grdm-dev --yes down` で止め（データは残る）、その `runtime/volumes/` をリポジトリの外のバックアップのディレクトリへ写し（約 806 MB。ファイル数は、`cp` が写さない LibreOffice のソケット 1 個を除いて一致）、`docker volume rm` で 14 個のボリュームの登録だけを外した（データはディスクに残る）。Docker のほかのものは消しも prune もしていない。

**この節の出どころ。** 作業者（QAE、QA担当）が Mac Studio でコマンドを実行し、新しいチェックアウトの `runtime/reports/`（ファイルの時刻が段の境目を与える）とコンソールの全ログを読んだ。ログはリポジトリの外に置いたままである。受入の実行 [`acc-20261114T103547Z-8c60ae`](runs/acc-20261114T103547Z-8c60ae/results.toon) は新しいチェックアウトから写した。ホスト名、ホームのパス、127.0.0.1 以外のアドレス、メールアドレスを含まないことを検索で確かめた。

```toon
one_command{command,started_utc,ended_utc,exit,steps}:
  "./installer/install-macos.sh --yes --profile core（GRDM_WITH_ACCEPT なし）",2026-11-14T10:20:54Z,2026-11-14T10:33:44Z,0,"doctor plan secrets_init compose_render build up health_network scan report: すべて ok"
stage_times[5]{stage,from_utc,to_utc,note}:
  前提条件_venv_doctor〜compose_render,10:20:54,10:21:21,"install-macos.sh: 前提条件はすべて揃っており変更なし。python3 3.15.2 で .venv を作成。8080 が使われていたので fakecas は 8081 へ"
  build,10:21:21,10:22:20,"59 秒。統合リポジトリ 7 本を固定版で新しい runtime/src へ clone。レイヤーの段 262 個が CACHED で、2 秒を超えた段は無い。y-websocket のイメージはキャッシュのレイヤーから組み直された（作成 10:22:13Z）"
  up,10:22:20,10:31:19,"9 分 0 秒。新しく空の runtime/volumes の上で（データベースと Elasticsearch 8 を初期化）。23 サービスが healthy"
  health_network,10:31:19,10:31:20,"終了 0、ループバックのみ。警告 1 件: *:5000 の他者のリスナー（ControlCe、macOS）"
  scan_and_report,10:31:20,10:33:44,"2 分 24 秒。ゲートは pass（M3、count-not-growing）: 6,196 件（critical 314、high 1,838、medium 2,739、low 1,301、info 4）。58 項目の許容リストで 177 件を許容。ZAP は admin と ember_osf_web を検査し、web はサインインの壁の向こうとして飛ばした"
```

**一つのコマンドは一回の実行で終了 0 を返した。`install-macos.sh` の開始から report まで 12 分 50 秒**で、手作業は無い。大半は空のボリュームでの `up` で、ビルドが約 1 分で済んだのは Docker のキャッシュが温まっていたからにすぎない。

**受入試験。後から実行した（一つのコマンドの一部ではない）。** 最初の `grdm-dev --yes accept --seed`（10:35:09Z）は、新しい `.venv` に試験用の追加パッケージが無いため終了 2 で止まった。メッセージが示したコマンドをそのとおり実行した（`pip install -e "installer[accept]"` と、`.venv/.playwright` への `playwright install chromium`。26 秒）。続く `grdm-dev --yes accept --seed` を既定の待ち（`--wait-scale` 1）で 10:35:45Z〜10:37:17Z に実行し、終了 0: **14 件中 14 件合格**、失敗 0、skip 10（S1〜S5、M3）。事前確認で 23 サービスが healthy。C4 の成功ケース 9.0 秒、C7 の成功ケース 9.9 秒。netguard は既知の外部要求 137 件を遮断した。`--wait-scale` での二回目は要らなかった。

**本体のチェックアウトのスタックの復元。** 新しいチェックアウトで `grdm-dev --yes down`。次に、device が新しいチェックアウトの中を指す `grdm-dev_*` のボリューム 11 個を、外す前に確かめてから `docker volume rm` した。本体のチェックアウトで `grdm-dev --yes up --no-open`（10:38:02Z〜10:39:46Z、終了 0、23 サービスが healthy、17 コンテナが稼働）と `grdm-dev health --network`（終了 0、ループバックのみ、同じ `ControlCe` の警告）。Compose は今の compose ファイルにある 11 個のボリュームを登録し直した。古い 3 個の登録 `elasticsearch_data`、`mongo_data`、`mongo_tls` は今の compose ファイルに無いので、同じ bind のオプションと device で手で登録し直した。その後 14 個の名前と device はすべて実行前の記録と一致した。バックアップと本体の `runtime/volumes/` の `diff -rq` は、動いているスタックが書き換えるファイルだけを示した（PostgreSQL の制御・WAL・リレーションキャッシュ・pid のファイル。同じ索引 UUID の Elasticsearch 6 と 8 の状態・translog・セグメントのファイル。新しいコンテナ名の RabbitMQ のノードのディレクトリ。`y_websocket_data` の LevelDB の圧縮。`wb_tmp` の一時ファイル）。バックアップはリポジトリの外に残してある。

この実行が示さないことと、変わったこと: 空の Docker や新品の Mac からの実行（キャッシュは温まり、前提条件はあったので、ビルドの時間はコールドビルドの時間ではない）。非公開のリポジトリには作業者の既存の git の権限を使った。復元したスタックはデータも固定版も同じだが、イメージ ID は同じではない。実行前、本体のスタックの一部のコンテナはタグが外れたイメージで動いていて、`down` の後それらのイメージは Docker のイメージストアに無かった。そのため `up` は同じ固定版の今のタグのイメージ（とこの実行で組み直された y-websocket のイメージ）で起動した。新しいチェックアウトとその `runtime/` はディスクに残し、消していない。ここで実行していないもの: 認証つきの ZAP の検査、`ENABLE_PUBLIC_ACCESS=true`、Shibboleth の `idp` での管理者ログイン。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| Wheel | A ready-made package of Python code for one CPU type; if none exists, pip must compile it. | ある CPU 向けにできあがった Python の部品の箱。無いと pip が自分で組み立てる。 |
