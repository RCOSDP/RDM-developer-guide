# DEMO-22 Core Install on Ubuntu 24.04 amd64 under QEMU / Ubuntu 24.04 amd64（QEMU 上）でのコア導入記録

> **Summary:** What happened when `installer/install-ubuntu.sh --yes --profile core` was run on a fresh Ubuntu 24.04 amd64 virtual machine that is fully emulated by QEMU on an Apple Silicon Mac, as an ordinary user whose uid is not 1000. One entry per run; nothing is edited after the fact.
> **概要:** Apple Silicon の Mac 上で QEMU が全体をエミュレーションする新しい Ubuntu 24.04 amd64 の仮想マシンで、uid が 1000 でない一般利用者として `installer/install-ubuntu.sh --yes --profile core` を実行したときに起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-12. **Learned:** a virtual machine that emulates a whole amd64 computer on Apple Silicon is a good test of the Ubuntu amd64 prerequisites and of every image that builds from binary packages, but not of an image that compiles scientific Python from source: osf.io's numpy, pandas and scipy take about ten times as long as under Rosetta, so the one command cannot finish in a working day, and `install` could not even be told to wait longer. ／ Apple Silicon 上で amd64 のコンピュータ全体をエミュレーションする仮想マシンは、Ubuntu amd64 の前提条件と、バイナリのパッケージから組むイメージの試験には向く。しかし科学計算の Python をソースから組むイメージには向かない。osf.io の numpy・pandas・scipy は Rosetta の約 10 倍かかり、一つのコマンドは 1 営業日で終わらず、`install` に待ち時間を延ばすよう伝える手段すらなかった。
- Normative source: [SPEC-02 Installer CLI](../spec/02_installer_cli.md) · [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md)
- Related: [DEMO-21 Core install on Ubuntu arm64](21_core_install_ubuntu_arm64_lima.md) · [DEMO-20 Core install on Mac Studio](20_core_install_mac_studio.md) · [ADR-08 Per-OS installer entry points](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md) · [docs/demo/README.md](README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Setup — 2026-11-12, branch `fix/ubuntu-amd64` on develop b81628f

The host is the Mac Studio (Apple M1 Ultra, 20 cores, 128 GiB) of [DEMO-20](20_core_install_mac_studio.md). The test machine is a Lima virtual machine (Lima runs Linux inside macOS; a *virtual machine* is a whole computer simulated by software) named `grdm-ubuntu2404-amd64`. Unlike the arm64 machine of [DEMO-21](21_core_install_ubuntu_arm64_lima.md), which Apple's virtualization runs at nearly native speed, an amd64 machine on Apple Silicon can only be emulated: QEMU (a free CPU emulator) translates every amd64 instruction, in software, for the whole machine including its kernel.

```toon
vm:
  name: grdm-ubuntu2404-amd64
  tool: "limactl 2.3.0 (brew pulled it in as a dependency of lima-additional-guestagents), QEMU 11.1.3"
  vmType: qemu
  arch: x86_64
  image: ubuntu-24.04-server-cloudimg-amd64 (release-20261017), Ubuntu 24.04.5 LTS
  cpus: 8
  memory: 32 GiB
  disk: 160 GiB
  user: "grdm, uid 2002 gid 2002 (set with the user: key of the Lima configuration), passwordless sudo, not root"
  checkout: "/home/grdm/RDM-developer-guide on the VM's own disk, cloned from a git bundle of branch fix/ubuntu-amd64"
  shared_from_host: "/mnt/mirrors only, read-only (9p): bare mirrors of the six integration repositories, refreshed with git fetch on the host"
  git_config: "url.file:///mnt/mirrors/<repo>.git.insteadOf https://github.com/RCOSDP/<repo>.git; no token in the VM"
  boot: "limactl create about 2.5 min (image download), first start 1 min 45 s"
```

Two host tools were missing: `brew install qemu lima-additional-guestagents` (Lima's amd64 guest agent is a separate package). The arm64 VM `grdm-ubuntu2404` was not started, changed or deleted; it stayed stopped while Lima moved from 2.2.1 to 2.3.0.

> **Warning:** Lima merged the template's home mount into the configuration again: `limactl create` printed a configuration whose `mounts:` still ended with `- location: "~"`. It was removed from `~/.lima/grdm-ubuntu2404-amd64/lima.yaml` before the first start. Inside the VM `mount | grep -E 'virtiofs|9p|sshfs'` lists only `/mnt/mirrors`, and `~/.config` does not exist.

The pins are those of develop b81628f (nothing was changed by hand; osf.io is being merged by another coordinator, so a later develop may differ):

```toon
pins[8]{component,pin}:
  osf.io,8fc45de461fd
  waterbutler,3319c1067916
  modular-file-renderer,9771b8cfb352
  cas-overlay,22610b7681a2
  wiki-frontend,"5985d18b75da on osf.io 8fc45de461fd"
  y-websocket,d4d1cfaed2e4
  ember-osf-web,"prebuilt niicloudoperation/rdm-ember-osf-web@sha256:65ee1fae52a3..."
  postgres,"18.6 (digest pinned)"
```

### Run 1 — fresh VM, the one command

```toon
run1:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-12T00:21:12Z
  result: stopped by hand 5 h 27 min after the start (5 h 12 min inside build), no exit code of its own
  prerequisites[5]{step,result}:
    "apt: python3-venv libatomic1",installed
    "Docker apt key",fingerprint 9DC858229FC7DD38854AE2D88D81803C0EBFCD88 verified
    "Docker Engine",29.9.3 with Compose 5.7.1 and buildx
    "trivy 0.75.0, gitleaks 8.21.2",SHA-256 verified into ~/.local/bin
    "docker group","usermod, then this run continued under sg docker"
  steps[6]{step,code,status}:
    doctor,0,"ok: ubuntu 24.04 amd64, 31.3 GiB, 150.7 GiB free, official, no problems"
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,-,"osf.io still compiling after 5 h 12 min (started 00:35:54Z, stopped 05:48Z)"
    "up ... report",-,not reached
```

What this proves:

- The prerequisite script needs no emulation step on amd64: the plan lists apt packages, Docker's signed repository, two scanners and the docker group, and nothing about QEMU or binfmt. This is the first run on amd64.
- The private repositories were read from the read-only mirrors through `insteadOf`; `doctor`'s `git ls-remote` check passed without any token.
- **Finding 1 (doctor is silent):** `doctor` printed no line about amd64 emulation, so a reader could not tell "not needed" from "not checked". **Fix 1** (`fix(installer)`): the report carries `amd64_emulation: not needed (host is amd64)` on an amd64 host, `ready (a binfmt handler is registered)` on Linux arm64 with a working handler, and nothing on macOS.

### Failure 2 — an emulation-only limit: osf.io's scientific Python

The `osf.io` image (Python 3.6 on Alpine, whose C library has no ready-made wheels) compiles numpy 1.15.4, pandas 1.1.0 and scipy from source in one `RUN` step. All the other images of the profile built natively in the VM, and are not the problem:

```toon
native_builds_in_the_vm[9]{component,minutes}:
  y-websocket,3.2
  sharejs,1.9
  elasticsearch2,4.0
  elasticsearch6,4.9
  fakecas,6.6
  waterbutler,13.6
  cas-overlay,12.1
  modular-file-renderer,16.7
  unoconv,9.5
```

(They ran four and five at a time, started by hand with `grdm-dev build --component`, so the times include contention; all exited 0.) The compile step of osf.io, measured three ways:

```toon
osf_compile[3]{step,qemu_system_vm,rosetta_vm,ratio}:
  "numpy 1.15.4 (setup.py install)","971 s","118 s","8.2x"
  "pandas 1.1.0 (wheel)","4298 s","411 s","10.5x"
  "scipy (wheel)","more than 6400 s, not finished when stopped","about 1000 s","6x or more"
  "whole RUN step","not finished after 5 h 12 min","3298 s (55 min)","about 10x expected"
```

The *rosetta_vm* column is a second, temporary Lima VM (`vmType: vz`, arm64 Ubuntu with Rosetta registered, the same read-only mirror, no home mount) that built the same commit with `docker buildx build --platform linux/amd64`: the whole osf.io image took 64 min 11 s there. On real amd64 hardware the step takes minutes. So the limit belongs to full-system emulation, not to the installer or the image: **no timeout of the installer applies to `build`, and none was changed for it.**

### Run 2 — the same VM, osf.io and wiki-frontend images built under Rosetta and loaded

To test everything after `build`, the two images that cannot be built here were produced in the Rosetta VM from the same pinned commits (`osf.io` with `docker buildx build`, `wiki-frontend` with `grdm-dev build --component wiki-frontend --platform linux/amd64`), moved with `docker save | gzip`, `limactl cp` and `docker load`, and carry the tags the installer would give them. The remaining steps were then run one by one: `grdm-dev up`, `health --network`, `scan`, `report` and `accept`. This is **not** a proof of the one command; it is a proof of everything behind the build.

The ember-osf-web container had been started earlier with `docker compose up -d ember_osf_web` so that its first build ran in parallel with the image work (it has no `depends_on`, as the manifest note says):

```toon
ember_first_build:
  container_start: 2026-11-12T04:14:00Z
  built: 2026-11-12T05:58:42Z
  serving_4200: 2026-11-12T06:00:05Z
  duration: "1 h 44 min 42 s to the build, 1 h 46 min to the port (QEMU system emulation, one core busy); 44 min 15 s under user-mode QEMU on arm64 (DEMO-21)"
```

All the other services started from the loaded and the natively built images: `grdm-dev up` (run with `--timeout 7200`) created the containers of the profile and reached `osf_init`, whose Django migrations (497 of them in the `osf` app alone) ran at about 3 per minute under emulation (osf.0106 at 06:29Z). Their end and everything after it (`up` health, `health --network`, `scan`, `report`, `accept`) are recorded in the next entry of this page; this version of the page was written while `osf_init` was still running, and says nothing about them.

**Fix 2** (`fix(installer)`): `grdm-dev install` accepts `--timeout SECONDS` and passes it to `up`, so a slow host can use the one command (`./installer/install-ubuntu.sh --yes --profile core --timeout 14400`). Before, `install` had no way to extend the 1800 s wait of `up`, and an install that was merely slow ended with exit 40 and had to be continued by hand. The default is unchanged: 1800 s on macOS and amd64, 5400 s on Linux arm64 with amd64 services, because real amd64 hardware does not need more.

**Observation (no fix):** while `playwright install-deps` ran during the heavy start, the guest's name resolution timed out for a while (`apt` printed `Ign:` for every repository; `curl` failed with `Resolving timed out`); the same commands worked a minute later, and the command was successful. This is the user-mode network of QEMU under full load, not an installer fault.

### What remains

- **One uninterrupted run of the one command on Ubuntu amd64:** not done. It needs real amd64 hardware (a cloud virtual machine or a PC), where the compile takes minutes, or about 9 hours here. Everything else that is specific to amd64 is now checked: prerequisites, `doctor`, `git` access through mirrors, uid 2002, and all images except osf.io and wiki-frontend building natively.
- **WSL2:** not run ([DEMO-21](21_core_install_ubuntu_arm64_lima.md) lists why).
- **Pins:** these runs used develop b81628f; osf.io's pin will change when the other coordinator's merge lands.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 準備 — 2026-11-12、develop b81628f 上のブランチ `fix/ubuntu-amd64`

ホストは [DEMO-20](20_core_install_mac_studio.md) の Mac Studio（Apple M1 Ultra、20 コア、128 GiB）。試験機は Lima の仮想マシン `grdm-ubuntu2404-amd64` である（Lima は macOS の中で Linux を動かす道具。*仮想マシン* はソフトウェアで模した一台のコンピュータ）。Apple の仮想化機能がほぼ本来の速度で動かす [DEMO-21](21_core_install_ubuntu_arm64_lima.md) の arm64 の機械と違い、Apple Silicon 上の amd64 の機械はエミュレーションしかできない。QEMU（無償の CPU エミュレーター）が、カーネルを含む機械全体の amd64 の命令を一つずつソフトウェアで翻訳する。

```toon
vm:
  name: grdm-ubuntu2404-amd64
  tool: "limactl 2.3.0（lima-additional-guestagents の依存として brew が入れた）、QEMU 11.1.3"
  vmType: qemu
  arch: x86_64
  image: ubuntu-24.04-server-cloudimg-amd64（release-20261017）、Ubuntu 24.04.5 LTS
  cpus: 8
  memory: 32 GiB
  disk: 160 GiB
  user: "grdm、uid 2002・gid 2002（Lima の設定の user: キーで指定）、パスワードなしの sudo、root ではない"
  checkout: "VM 自身のディスク上の /home/grdm/RDM-developer-guide。ブランチ fix/ubuntu-amd64 の git bundle から clone"
  shared_from_host: "/mnt/mirrors だけを読み取り専用（9p）で共有: 統合リポジトリ 6 本の bare ミラー。ホストで git fetch して更新"
  git_config: "url.file:///mnt/mirrors/<repo>.git.insteadOf https://github.com/RCOSDP/<repo>.git。VM にトークンは置かない"
  boot: "limactl create 約 2.5 分（イメージの取得）、最初の起動 1 分 45 秒"
```

ホストに足りない道具が二つあった。`brew install qemu lima-additional-guestagents`（Lima の amd64 用ゲストエージェントは別のパッケージ）。arm64 の VM `grdm-ubuntu2404` は、起動も変更も削除もしていない。Lima が 2.2.1 から 2.3.0 に上がる間も停止したままだった。

> **Warning:** Lima はテンプレートのホームの mount をまた併合した。`limactl create` が出した設定の `mounts:` の末尾に `- location: "~"` が残っていた。最初の起動の前に `~/.lima/grdm-ubuntu2404-amd64/lima.yaml` から外した。VM の中で `mount | grep -E 'virtiofs|9p|sshfs'` に出るのは `/mnt/mirrors` だけで、`~/.config` は存在しない。

固定（pin）は develop b81628f のもので、手では何も変えていない（osf.io は別の担当が統合中なので、後の develop では変わりうる）：

```toon
pins[8]{component,pin}:
  osf.io,8fc45de461fd
  waterbutler,3319c1067916
  modular-file-renderer,9771b8cfb352
  cas-overlay,22610b7681a2
  wiki-frontend,"osf.io 8fc45de461fd の上の 5985d18b75da"
  y-websocket,d4d1cfaed2e4
  ember-osf-web,"ビルド済み niicloudoperation/rdm-ember-osf-web@sha256:65ee1fae52a3..."
  postgres,"18.6（ダイジェスト固定）"
```

### 第 1 回 — 新しい VM で一つのコマンド

```toon
run1:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-12T00:21:12Z
  result: 開始の 5 時間 27 分後（build の中で 5 時間 12 分後）に手で止めた。自分の終了コードは無い
  prerequisites[5]{step,result}:
    "apt: python3-venv libatomic1",導入
    "Docker の apt 鍵",指紋 9DC858229FC7DD38854AE2D88D81803C0EBFCD88 を検証
    "Docker Engine",29.9.3、Compose 5.7.1 と buildx
    "trivy 0.75.0、gitleaks 8.21.2",SHA-256 を検証して ~/.local/bin へ
    "docker グループ","usermod の後、この実行は sg docker の下で続行"
  steps[6]{step,code,status}:
    doctor,0,"ok: ubuntu 24.04 amd64、31.3 GiB、空き 150.7 GiB、公式、問題なし"
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,-,"osf.io が 5 時間 12 分後もコンパイル中（開始 00:35:54Z、停止 05:48Z）"
    "up ... report",-,未到達
```

分かったこと:

- amd64 の前提条件スクリプトにエミュレーションの手順は要らない。計画には apt のパッケージ、Docker の署名付きリポジトリ、二つのスキャナー、docker グループだけが並び、QEMU も binfmt も出ない。amd64 での最初の実行である。
- 非公開リポジトリは `insteadOf` で読み取り専用のミラーから読めた。`doctor` の `git ls-remote` の確認はトークン無しで通った。
- **所見 1（doctor が黙る）:** `doctor` は amd64 エミュレーションについて一行も出さず、読む人は「要らない」と「確かめていない」を区別できなかった。**修正 1**（`fix(installer)`）: 報告に、amd64 のホストでは `amd64_emulation: not needed (host is amd64)`、動く handler のある Linux arm64 では `ready (a binfmt handler is registered)` を載せる。macOS では何も載せない。

### 失敗 2 — エミュレーションだけの限界: osf.io の科学計算 Python

`osf.io` イメージ（Alpine 上の Python 3.6。Alpine の C ライブラリには出来合いの wheel が無い）は、numpy 1.15.4、pandas 1.1.0、scipy を一つの `RUN` 手順でソースからコンパイルする。このプロファイルのほかのイメージは VM の中でネイティブに組め、問題ではない：

```toon
native_builds_in_the_vm[9]{component,minutes}:
  y-websocket,3.2
  sharejs,1.9
  elasticsearch2,4.0
  elasticsearch6,4.9
  fakecas,6.6
  waterbutler,13.6
  cas-overlay,12.1
  modular-file-renderer,16.7
  unoconv,9.5
```

（手で `grdm-dev build --component` を 4 本・5 本ずつ同時に動かしたので、時間には競合が入る。すべて終了 0。）osf.io のコンパイル手順を 3 通りで測った：

```toon
osf_compile[3]{step,qemu_system_vm,rosetta_vm,ratio}:
  "numpy 1.15.4（setup.py install）","971 秒","118 秒","8.2 倍"
  "pandas 1.1.0（wheel）","4298 秒","411 秒","10.5 倍"
  "scipy（wheel）","6400 秒超、止めた時点で未完","約 1000 秒","6 倍以上"
  "RUN 手順全体","5 時間 12 分後も未完","3298 秒（55 分）","約 10 倍の見込み"
```

*rosetta_vm* の列は、同じコミットを `docker buildx build --platform linux/amd64` で組んだ、もう一つの一時的な Lima VM（`vmType: vz`、Rosetta を登録した arm64 の Ubuntu、同じ読み取り専用ミラー、ホームの mount なし）の値で、osf.io のイメージ全体が 64 分 11 秒だった。実際の amd64 の機械ではこの手順は数分で終わる。つまり限界は機械全体のエミュレーションのものであり、インストーラーでもイメージでもない。**`build` に効くインストーラーのタイムアウトは無く、変えてもいない。**

### 第 2 回 — 同じ VM、Rosetta で組んだ osf.io と wiki-frontend のイメージを読み込む

`build` より後のすべてを試すため、ここで組めない 2 つのイメージを、同じ固定コミットから Rosetta の VM で作った（`osf.io` は `docker buildx build`、`wiki-frontend` は `grdm-dev build --component wiki-frontend --platform linux/amd64`）。`docker save | gzip`、`limactl cp`、`docker load` で運び、インストーラーが付けるのと同じタグにした。残りの手順は一つずつ実行した: `grdm-dev up`、`health --network`、`scan`、`report`、`accept`。これは一つのコマンドの証明では**ない**。ビルドより後ろ全体の証明である。

ember-osf-web のコンテナは先に `docker compose up -d ember_osf_web` で起動し、初回ビルドをイメージ作りと並行させた（マニフェストの注記のとおり `depends_on` が無い）：

```toon
ember_first_build:
  container_start: 2026-11-12T04:14:00Z
  built: 2026-11-12T05:58:42Z
  serving_4200: 2026-11-12T06:00:05Z
  duration: "ビルドまで 1 時間 44 分 42 秒、ポートまで 1 時間 46 分（QEMU の機械全体のエミュレーション、使うのは 1 コア）。arm64 のユーザーモード QEMU では 44 分 15 秒（DEMO-21）"
```

ほかのサービスは、読み込んだイメージとネイティブに組んだイメージから起動した。`grdm-dev up`（`--timeout 7200` で実行）がプロファイルのコンテナを作り、`osf_init` まで進んだ。その Django の migration は `osf` アプリだけで 497 件あり、エミュレーション下で 1 分に約 3 件の速さで進んだ（osf.0106 が 06:29Z）。その終わりと、以後のすべて（`up` の health、`health --network`、`scan`、`report`、`accept`）はこのページの次の記録に書く。この版は `osf_init` が動いている間に書いたので、それらについては何も言わない。

**修正 2**（`fix(installer)`）: `grdm-dev install` が `--timeout 秒` を受け取って `up` に渡す。遅い機械でも一つのコマンドが使える（`./installer/install-ubuntu.sh --yes --profile core --timeout 14400`）。以前の `install` には `up` の 1800 秒の待ちを延ばす手段が無く、単に遅いだけの導入が終了 40 で終わり、手で続けるしかなかった。既定は変えない: macOS と amd64 は 1800 秒、amd64 のサービスがある Linux arm64 は 5400 秒。実際の amd64 の機械はそれ以上を要しないからである。

**観察（修正なし）:** 重い起動の最中に `playwright install-deps` を実行したとき、ゲストの名前解決がしばらくタイムアウトした（`apt` がすべてのリポジトリに `Ign:` と出し、`curl` が `Resolving timed out` で失敗した）。一分後には同じコマンドが通り、コマンドは成功した。全負荷の QEMU のユーザーモードネットワークの挙動で、インストーラーの不具合ではない。

### 残っていること

- **Ubuntu amd64 で中断しない一つのコマンドの実行:** 未実施。コンパイルが数分で済む実際の amd64 の機械（クラウドの仮想マシンや PC）が要る。ここでは約 9 時間かかる。amd64 に固有のほかのことは確かめた: 前提条件、`doctor`、ミラー経由の `git` の読み取り、uid 2002、osf.io と wiki-frontend 以外のすべてのイメージのネイティブビルド。
- **WSL2:** 未実施（理由は [DEMO-21](21_core_install_ubuntu_arm64_lima.md)）。
- **pin:** この実行は develop b81628f のもの。別の担当の統合が入ると osf.io の pin は変わる。
