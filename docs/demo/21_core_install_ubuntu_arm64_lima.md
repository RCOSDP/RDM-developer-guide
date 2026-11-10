# DEMO-21 Core Install on Ubuntu 24.04 arm64 / Ubuntu 24.04 arm64 でのコア導入記録

> **Summary:** What actually happened when `installer/install-ubuntu.sh --yes --profile core` was run on a fresh Ubuntu 24.04 arm64 virtual machine, as an ordinary user whose uid is not 1000. One entry per run; nothing is edited after the fact.
> **概要:** 新しい Ubuntu 24.04 arm64 の仮想マシンで、uid が 1000 でない一般利用者として `installer/install-ubuntu.sh --yes --profile core` を実行したときに実際に起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-10. **Learned:** the first Linux run of `grdm-dev db upgrade`, as uid 2001, moved PostgreSQL 9.6 to 18 in 12 seconds with 531 objects verified, and with develop's acceptance fixes the core suite passes 12 of 12 on Linux arm64 too; and the setup record had understated an exposure: the host's `~/.config/gh` was readable in the VM until the home mount was removed, so `install-ubuntu.sh` now stops when it finds credentials on a shared folder. ／ uid 2001 での `grdm-dev db upgrade` の Linux での最初の実行は、PostgreSQL 9.6 を 18 へ 12 秒で移し、531 個の対象を照合した。develop の受入試験の修正を入れると、コアの試験は Linux arm64 でも 12 件中 12 件合格する。また準備の記録は露出を小さく書いていた。ホームの mount を外すまで、ホストの `~/.config/gh` は VM から読めた。そこで `install-ubuntu.sh` は共有フォルダに資格情報を見つけると止まる。
  0.2 — 2026-11-10. **Learned:** a Linux host user whose uid is not 1000 is the case that finds ownership bugs the Mac hides: after the volumes (PR #36) it was the ZAP report directory, and only the full sequence through `scan` and `report` (run 4, exit 0) shows that none is left on this host. ／ uid が 1000 でない Linux のホスト利用者こそ、Mac が隠す所有者の不具合を見つける。ボリューム（PR #36）の次は ZAP の報告ディレクトリだった。この機械に残りが無いと示せるのは、`scan` と `report` まで通した一連の実行（第 4 回、終了 0）だけである。
  0.1 — 2026-11-10. **Learned:** the dry runs of [ADR-08](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md) could not show three Linux facts that a real run did: Ubuntu's own amd64 emulator crashes inside a long build, QEMU makes the first ember build twice as slow as on the Mac, and the cloud image lacks a library that the acceptance browser's driver needs. ／ [ADR-08](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md) の dry run では分からず、実際の実行で分かった Linux の事実が三つあった。Ubuntu 自身の amd64 エミュレーターは長いビルドの中で落ち、QEMU では ember の初回ビルドが Mac の 2 倍遅く、クラウドイメージには受入試験のブラウザのドライバーが要るライブラリが無い。
- Normative source: [SPEC-02 Installer CLI](../spec/02_installer_cli.md) · [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md)
- Related: [docs/demo/README.md](README.md) · [DEMO-20 Core install on Mac Studio](20_core_install_mac_studio.md) · [ADR-08 Per-OS installer entry points](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Setup — 2026-11-10, branch `feat/per-os-installers` rebased onto develop 03c7358

The host is the Mac Studio of [DEMO-20](20_core_install_mac_studio.md) (128 GiB). The test machine is a Lima virtual machine (Lima runs Linux inside macOS with Apple's virtualization; a *virtual machine* is a whole computer simulated by software) named `grdm-ubuntu2404`:

```toon
vm:
  name: grdm-ubuntu2404
  tool: limactl 2.2.1, vmType vz, no Rosetta
  image: ubuntu-24.04-server-cloudimg-arm64 (release-20260926), Ubuntu 24.04.5 LTS
  cpus: 8
  memory: 40 GiB
  disk: 120 GiB
  user: "grdm, uid 2001 gid 2001, passwordless sudo (a developer with sudo, not root)"
  checkout: "/home/grdm/RDM-developer-guide on the VM's own disk (cloned from a git bundle, so Linux owners and modes are real)"
  shared_from_host: "/mnt/mirrors only, read-only: bare mirrors of the six integration repositories (git clone --mirror on the host)"
  git_config: "url.file:///mnt/mirrors/<repo>.git.insteadOf https://github.com/RCOSDP/<repo>.git; no token in the VM"
```

> **Warning:** Lima's Ubuntu template also mounts the host home directory read-only, even when the configuration lists its own mounts, because the template's list is merged in. That would have shown the host's GitHub credentials inside the VM. The home mount was removed from the instance configuration before any repository was copied, and the VM restarted with only `/mnt/mirrors`.

On arm64 (the CPU type of Apple Silicon and many servers; see [REF-01](../reference/REF-01_Glossary.md)), Linux runs the two amd64-only components (amd64 is the CPU type of most PCs and cloud servers; see [REF-01](../reference/REF-01_Glossary.md)), modular-file-renderer (the file preview service) and ember-osf-web (the newer web pages of GRDM), under emulation (running a program built for one kind of CPU on another, slower but working). Docker (the tool that builds images and runs containers; see [REF-01](../reference/REF-01_Glossary.md)) Desktop on the Mac emulates with Rosetta; plain Linux uses QEMU (a free CPU emulator) registered in the kernel's binfmt_misc table.

### Run 1 — fresh VM, the one command

```toon
run1:
  command: ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T11:24+09:00
  result: exit 30 (image build failed) after 2868 s
  prerequisites[6]{step,result}:
    "apt: python3-venv",installed
    "Docker apt key",fingerprint 9DC858229FC7DD38854AE2D88D81803C0EBFCD88 verified
    "Docker Engine",29.9.3 with Compose 5.7.0 and buildx
    "amd64 emulation","apt qemu-user-static 1:8.2.2+ds-0ubuntu1.18 (flags OPF)"
    "trivy 0.75.0, gitleaks 8.21.2",SHA-256 verified into ~/.local/bin
    "docker group","usermod, then this run continued under sg docker"
  steps[5]{step,code,status}:
    doctor,0,"ok: ubuntu 24.04 arm64, 39.1 GiB, 111.9 GiB free, official, no problems"
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"about 30 min: pandas and scipy compiled from source on Alpine"
    waterbutler,linux/arm64,built,""
    modular-file-renderer,linux/amd64,build-failed,"libgvc6 post-install: x86_64-binfmt-P: QEMU internal SIGSEGV, exit 139"
```

What this proves:

- The prerequisite script works on a fresh Ubuntu 24.04 arm64 machine: signed Docker repository, pinned scanners, the docker group question, and the hand-over to `install.sh` inside `sg docker`.
- The private repositories were read from read-only mirrors through `insteadOf`; `doctor`'s `git ls-remote` check passed without any token.
- **Failure 1:** Ubuntu 24.04's `qemu-user-static` crashes inside modular-file-renderer's build, 48 minutes into the run.

Isolation test, one minute each: `apt-get install libgvc6` in a `debian:buster-slim` amd64 container.

```toon
qemu_isolation[4]{emulator,result}:
  "Ubuntu qemu-user-static 8.2.2 (apt)","QEMU internal SIGSEGV, apt exit 100"
  "tonistiigi/binfmt qemu-v8.1.5",installed
  "tonistiigi/binfmt qemu-v9.2.2",installed
  "tonistiigi/binfmt qemu-v10.2.3-68",installed
```

The crash belongs to Ubuntu's 8.2.2 build, not to a QEMU version range, so only that build is refused.

**Fix 1** (`fix(installer)`): `install-ubuntu.sh` no longer installs `qemu-user-static`; it registers QEMU from `tonistiigi/binfmt:qemu-v10.2.3-68`, pinned by digest, and replaces a registered Ubuntu 8.2.2 handler (`--uninstall qemu-x86_64`, then `--install amd64`). `doctor` reads the registered interpreter's `--version` and stops with exit 13 before the build when it is the measured-bad build, printing the replacement command.

### Run 2 — same VM, QEMU 10.2.3 registered by hand

```toon
run2:
  command: ./installer/install.sh --yes --profile core
  result: exit 40 (health) after 3929 s
  steps[6]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok: 12 components, modular-file-renderer built under QEMU 10.2.3"
    up,40,"not healthy after 1800s: ember_osf_web"
  ownership: "volume_owner_init, volume_access_check_1000 and volume_access_check_999 completed with host uid 2001"
  ember_first_build: "container start 03:43:05Z, port 4200 answered 04:27:20Z: 44 min 15 s, one core busy"
  health_after_ember: "grdm-dev health exit 0, 24 services ok"
```

What this proves:

- The ownership handling of PR (pull request: a proposed change waiting for review; see [REF-01](../reference/REF-01_Glossary.md)) #36 works for a host user whose uid is not 1000: every writer could use its volume, and the volumes stay owned by the container uids.
- **Failure 2:** QEMU builds ember about twice as slowly as Rosetta (13–25 minutes in DEMO-20). The single-threaded build cannot use more CPUs, so `up`'s 1800 s wait stopped an install that would have become healthy.

**Fix 2** (`fix(installer)`): on Linux arm64, when the profile has amd64 services, `up` waits 5400 s by default (about twice the measurement); `--timeout` still overrides it. macOS and amd64 keep 1800 s.

### Acceptance attempt 1 — stack of run 2

`grdm-dev health` exited 0. Installing the browser failed before any test: `playwright install --with-deps chromium` exited 127 because the Node.js driver of Playwright (a robot that drives a web browser to test a website; see [REF-01](../reference/REF-01_Glossary.md)) could not load `libatomic.so.1`, which the Ubuntu 24.04 cloud image does not contain. `grdm-dev accept` then exited 2 (no Chromium).

**Failure 3, fix 3** (`fix(installer)`): `install-ubuntu.sh` adds `libatomic1` to its apt packages when `GRDM_WITH_ACCEPT=1`, and on Linux `grdm-dev accept` prints `sudo apt-get install -y libatomic1` before, and `playwright install-deps chromium` after, the existing install command. With `libatomic1` installed by hand, `playwright install --with-deps chromium` exited 0.

### Acceptance run — stack of run 2 (osf.io 389415a4)

| Run ID | Scope | Result |
|---|---|---|
| [`acc-20261110T043053Z-5c5dae`](runs/acc-20261110T043053Z-5c5dae/results.toon) | Core C1–C6 | 5 of 12 passed |

C1 and C3 pass in both cases, C2's rejection passes. The other seven fail for the reasons DEMO-20 recorded on develop (project-name selector, wiki bundle wiring, preview, admin path, and ShareJS assets on port 7007); they are fixed on the separate branch `fix/accept-c2-c6`, which this branch does not contain. No failure here is specific to Linux.

### Run 3 — the fixed scripts from the broken state, cold start

Before the run: the checkout moved to commit 48859d7 (fixes 1–3), Ubuntu's 8.2.2 handler was registered again (`systemctl restart systemd-binfmt`), `libatomic1` was removed, and `grdm-dev reset --yes` emptied `runtime/volumes/` (exit 0; the files belonged to container uids). With Ubuntu's handler registered, `grdm-dev doctor` exited 13 and printed the replacement command.

```toon
run3:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T04:40:11Z
  result: exit 51 (scanner incomplete) after 2828 s
  plan[2]:
    "sudo: install apt packages: libatomic1"
    "sudo: replace the registered amd64 emulator (qemu-x86_64 version 8.2.2 ...) with QEMU from tonistiigi/binfmt:qemu-v10.2.3-68@sha256:400a4873..."
  steps[8]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok (cached)"
    up,0,"ok within the 5400 s wait; ember's first build again about 40 min"
    "health --network",0,"ok, every port on 127.0.0.1"
    scan,51,"semgrep incomplete; zap incomplete"
```

What this proves: fixes 1–3 work end to end, and the reset of PR #36 works for uid 2001. Two new failures stop `scan`:

- **Failure 4a:** ZAP (the OWASP website scanner, which runs as uid 1000 in its container) could not write its report into `runtime/reports/`, owned by uid 2001; `zap-baseline` exited 0 without a report for all three targets. Docker Desktop's bind mounts ignore owners, so the Mac never showed it.
- **Failure 4b:** Semgrep (a tool that reads source code looking for dangerous patterns; see [REF-01](../reference/REF-01_Glossary.md)) 1.184.0 reported four "Internal matching error"s on `.github/workflows/installer-prereq-lint.yml`, a file this branch adds. Semgrep reads `run:` blocks as shell; the inline PowerShell of the Windows job breaks its engine (removing that job alone made the errors disappear).

**Fix 4** (`fix(installer)`, commit 0c46a82): each ZAP target gets its own work directory under `runtime/reports/`, mode 0777 inside the 0700 `runtime/`, removed after the masked copy is saved; the PowerShell parse moved to `.github/scripts/Test-PowerShellSyntax.ps1`, and each PowerShell `run:` is a one-line call. Semgrep's `p/default` and `p/github-actions` then report no error on the workflows.

### Acceptance run — stack of run 3

| Run ID | Scope | Result |
|---|---|---|
| [`acc-20261110T052932Z-f1da54`](runs/acc-20261110T052932Z-f1da54/results.toon) | Core C1–C6 | 5 of 12 passed (same cases as above) |

Chromium was installed with the command that `grdm-dev accept` now prints on Linux: `playwright install chromium` exited 0 and `playwright install-deps chromium` exited 0.

### Run 4 — commit 0c46a82, the one command: **exit 0**

```toon
run4:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T05:34:32Z
  result: exit 0 after 204 s (images cached, volumes kept from run 3)
  prerequisites: "All prerequisites are already present; nothing to change."
  steps[9]{step,code,status}:
    "secrets init",0,"skipped (runtime/.env exists)"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,ok
    up,0,ok
    "health --network",0,ok
    scan,0,"ok: trivy 23 targets, semgrep 4 packs, gitleaks, zap 3 targets; gate report-only, pass"
    report,0,ok
  url: "http://127.0.0.1:5000/"
  health_after: "grdm-dev health exit 0"
```

Findings by severity (report-only at M1, [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)): 817 critical, 4355 high, 4392 medium, 2164 low, 5 info.

### Correction to the setup — the home mount did expose the credentials

The warning in the setup says the home mount "would have shown" the host's GitHub credentials. That understates it. The VM's first boot mounted `/Users/komiyama` read-only, and a directory listing confirmed it, so `~/.config/gh/hosts.yml` was readable inside the VM from the first boot until the mount was removed from `lima.yaml` and the VM restarted, a few minutes later. Nothing read the file, and no repository or tool had been copied into the VM by then. Since commit 45b49be, `install-ubuntu.sh` stops with exit 10 when a shared folder (virtiofs, 9p, sshfs and similar) holds `.config/gh/hosts.yml`, `.git-credentials`, `.netrc` or `.docker/config.json`. The environment guide now has the Lima steps: delete the `"~"` mount before the first start, then check `mount`.

### Run 5 — rebased onto develop 50740b1 (PR #40–#43), database upgrade

PostgreSQL (the main database where GRDM keeps its records; see [REF-01](../reference/REF-01_Glossary.md)) moved from 9.6 to 18.6 on develop (PR #42, [ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md)), so the existing data had to be upgraded before `up`. The branch was rebased twice; the commits named above became 8538324 (fixes 1–3, was 48859d7) and 05ff502 (fix 4, was 0c46a82). The host mirrors were refreshed with `git fetch`. The manifest now pins osf.io 8fc45de4; WaterButler (45e97a51) and modular-file-renderer (749e58d3) stay at their pinned commits.

```toon
run5:
  head: 45b49be
  steps[10]{step,code,seconds,note}:
    down,0,3,""
    doctor,0,0,""
    "compose render",0,1,""
    build,0,14,"images already built from the same pins"
    "db status",0,10,"data 9.6, image 18 (postgres:18.6, digest pinned): upgrade-needed"
    "db upgrade",0,12,"see below"
    "db status",0,0,"data 18: current"
    up,0,296,"healthy; ember's built pages were kept in their volume"
    "secrets rotate",0,293,"every secret regenerated, containers recreated, healthy"
    health,0,0,""
  db_upgrade:
    user: "grdm, uid 2001 (the data directory belongs to uid 999)"
    steps: "start-old, count-old, dump, stop-old, init-new, restore, verify, stop-new, swap: all ok"
    dump_bytes: 4546929
    verified: "531 objects compared (row counts per table, sequences, extensions) in 3 databases (cas, osf, postgres) and 1 role"
    kept: "runtime/volumes/postgres_data.pg9.6-20261110T055459Z"
```

### Acceptance run — stack of run 5: **12 of 12**

| Run ID | Scope | Result |
|---|---|---|
| [`acc-20261110T060511Z-80ee06`](runs/acc-20261110T060511Z-80ee06/results.toon) | Core C1–C6 | **12 of 12 passed**, exit 0 |

### Run 6 — the one command on the same stack

`GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core` exited 0 after 273 s: every step through `scan` (Trivy, Semgrep, gitleaks and ZAP all `ok`) and `report`. `grdm-dev health` exited 0 afterwards. Findings by severity: 808 critical, 4328 high, 4470 medium, 2267 low, 6 info.

### What remains

- **Ubuntu 24.04 amd64:** not run. No emulation is needed there, so failures 1, 2 and the arm64 part of 3 do not apply; failure 4a (ZAP as uid 1000) and the PR #36 ownership path do, and need a clean amd64 machine.
- **WSL2** (a way to run Linux inside Windows; see [REF-01](../reference/REF-01_Glossary.md)): not run. Docker comes from Docker Desktop, whose bind mounts behave like the Mac's, so 4a is not expected there; the checkout must be inside WSL. It needs Windows 11 hardware ([ADR-08 §5](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md)).
- **Emulation after a reboot:** the QEMU registration is not persistent. While Ubuntu's `qemu-user-static` is installed, its 8.2.2 handler returns at boot; `doctor` then stops with exit 13, and running `install-ubuntu.sh` again replaces it.
- **Acceptance:** done in run 5 (12 of 12) after develop took the fixes of PR #40.
- **Cold start time:** with images already built, `up` from empty volumes took about 40 minutes on this VM, nearly all of it ember's first build under QEMU. Building the images from nothing took about 60 minutes more (runs 1 and 2).

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 準備 — 2026-11-10、develop 03c7358 へ rebase したブランチ `feat/per-os-installers`

ホストは [DEMO-20](20_core_install_mac_studio.md) の Mac Studio（128 GiB）。試験機は Lima の仮想マシン `grdm-ubuntu2404` である（Lima は Apple の仮想化機能で macOS の中に Linux を動かす道具。*仮想マシン* はソフトウェアで模した一台のコンピュータ）：

```toon
vm:
  name: grdm-ubuntu2404
  tool: limactl 2.2.1、vmType vz、Rosetta なし
  image: ubuntu-24.04-server-cloudimg-arm64（release-20260926）、Ubuntu 24.04.5 LTS
  cpus: 8
  memory: 40 GiB
  disk: 120 GiB
  user: "grdm、uid 2001・gid 2001、パスワードなしの sudo（root ではなく sudo を持つ開発者）"
  checkout: "VM 自身のディスク上の /home/grdm/RDM-developer-guide（git bundle から clone。Linux の所有者とモードが本物になる）"
  shared_from_host: "/mnt/mirrors だけを読み取り専用で共有: 統合リポジトリ 6 本の bare ミラー（ホストで git clone --mirror）"
  git_config: "url.file:///mnt/mirrors/<repo>.git.insteadOf https://github.com/RCOSDP/<repo>.git。VM にトークンは置かない"
```

> **Warning:** Lima の Ubuntu テンプレートは、設定に独自の mount を書いてもテンプレート側の一覧が併合されるため、ホストのホームディレクトリを読み取り専用で mount する。そのままではホストの GitHub 資格情報が VM から見えてしまう。リポジトリを入れる前にインスタンスの設定からホームの mount を外し、`/mnt/mirrors` だけで VM を再起動した。

arm64（Apple Silicon や多くのサーバーの CPU の種類。[REF-01](../reference/REF-01_Glossary.md)）の Linux では、amd64 専用の部品 modular-file-renderer と ember-osf-web をエミュレーション（ある CPU 向けのプログラムを別の CPU で動かすこと。遅いが動く）で動かす。Mac の Docker Desktop は Rosetta でエミュレーションするが、素の Linux はカーネルの binfmt_misc 表に登録した QEMU（無償の CPU エミュレーター）を使う。

### 第 1 回 — 新しい VM で一つのコマンド

```toon
run1:
  command: ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T11:24+09:00
  result: 2868 秒後に終了 30（イメージのビルド失敗）
  prerequisites[6]{step,result}:
    "apt: python3-venv",導入
    "Docker の apt 鍵",指紋 9DC858229FC7DD38854AE2D88D81803C0EBFCD88 を検証
    "Docker Engine",29.9.3、Compose 5.7.0 と buildx
    "amd64 エミュレーション","apt の qemu-user-static 1:8.2.2+ds-0ubuntu1.18（flags OPF）"
    "trivy 0.75.0、gitleaks 8.21.2",SHA-256 を検証して ~/.local/bin へ
    "docker グループ","usermod の後、この実行は sg docker の下で続行"
  steps[5]{step,code,status}:
    doctor,0,"ok: ubuntu 24.04 arm64、39.1 GiB、空き 111.9 GiB、公式、問題なし"
    plan,0,ok
    "secrets init",0,ok
    "compose render",0,ok
    build,30,failed
  images[3]{component,platform,status,note}:
    osf.io,linux/arm64,built,"約 30 分: Alpine で pandas と scipy をソースから組む"
    waterbutler,linux/arm64,built,""
    modular-file-renderer,linux/amd64,build-failed,"libgvc6 の post-install: x86_64-binfmt-P: QEMU internal SIGSEGV、終了 139"
```

分かったこと:

- 前提条件スクリプトは新しい Ubuntu 24.04 arm64 で動く。署名付きの Docker リポジトリ、固定したスキャナー、docker グループの確認、`sg docker` の中での `install.sh` への引き継ぎ。
- 非公開リポジトリは `insteadOf` で読み取り専用のミラーから読めた。`doctor` の `git ls-remote` の確認はトークン無しで通った。
- **失敗 1:** Ubuntu 24.04 の `qemu-user-static` が、実行開始から 48 分後、modular-file-renderer のビルドの中で落ちる。

切り分け（各 1 分）: amd64 の `debian:buster-slim` コンテナで `apt-get install libgvc6`。

```toon
qemu_isolation[4]{emulator,result}:
  "Ubuntu の qemu-user-static 8.2.2（apt）","QEMU internal SIGSEGV、apt 終了 100"
  "tonistiigi/binfmt qemu-v8.1.5",導入できた
  "tonistiigi/binfmt qemu-v9.2.2",導入できた
  "tonistiigi/binfmt qemu-v10.2.3-68",導入できた
```

落ちるのは QEMU の版の範囲ではなく Ubuntu の 8.2.2 のビルドなので、拒むのはそのビルドだけにした。

**修正 1**（`fix(installer)`）: `install-ubuntu.sh` は `qemu-user-static` を入れず、ダイジェストで固定した `tonistiigi/binfmt:qemu-v10.2.3-68` から QEMU を登録し、登録済みの Ubuntu 8.2.2 は置き換える（`--uninstall qemu-x86_64` の後に `--install amd64`）。`doctor` は登録済みインタープリターの `--version` を読み、落ちると実測したビルドならビルドの前に終了 13 で止まり、置き換えのコマンドを表示する。

### 第 2 回 — 同じ VM、QEMU 10.2.3 を手で登録

```toon
run2:
  command: ./installer/install.sh --yes --profile core
  result: 3929 秒後に終了 40（health）
  steps[6]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env あり）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok: 12 部品。modular-file-renderer は QEMU 10.2.3 で組めた"
    up,40,"1800 秒後も ember_osf_web が健康でない"
  ownership: "volume_owner_init、volume_access_check_1000、volume_access_check_999 がホストの uid 2001 で完了"
  ember_first_build: "コンテナ起動 03:43:05Z、4200 番が応答 04:27:20Z: 44 分 15 秒、使うのは 1 コア"
  health_after_ember: "grdm-dev health 終了 0、24 サービスが ok"
```

分かったこと:

- PR #36 の所有者処理は uid が 1000 でないホストの利用者でも働く。書き手はすべて自分のボリュームを使え、ボリュームはコンテナの uid の所有のままである。
- **失敗 2:** QEMU は ember の組み立てに Rosetta（DEMO-20 で 13〜25 分）のおよそ 2 倍かかる。単一スレッドのビルドなので CPU を増やしても速くならず、`up` の 1800 秒の待ちが、健康になるはずの導入を止めた。

**修正 2**（`fix(installer)`）: Linux arm64 でプロファイルに amd64 のサービスがあるとき、`up` の既定の待ちは 5400 秒（実測のおよそ 2 倍）。`--timeout` で上書きできる。macOS と amd64 は 1800 秒のまま。

### 受入試験の試み 1 — 第 2 回のスタック

`grdm-dev health` は終了 0。試験の前にブラウザの導入で失敗した。Playwright の Node.js ドライバーが `libatomic.so.1` を読めず、`playwright install --with-deps chromium` は終了 127 だった。Ubuntu 24.04 のクラウドイメージにはこのライブラリが無い。続く `grdm-dev accept` は終了 2（Chromium が無い）。

**失敗 3・修正 3**（`fix(installer)`）: `install-ubuntu.sh` は `GRDM_WITH_ACCEPT=1` のとき apt パッケージに `libatomic1` を加え、Linux の `grdm-dev accept` は既存の導入コマンドの前に `sudo apt-get install -y libatomic1`、後に `playwright install-deps chromium` を表示する。`libatomic1` を手で入れると `playwright install --with-deps chromium` は終了 0 だった。

### 受入試験の実行 — 第 2 回のスタック（osf.io 389415a4）

| 実行 ID | 範囲 | 結果 |
|---|---|---|
| [`acc-20261110T043053Z-5c5dae`](runs/acc-20261110T043053Z-5c5dae/results.toon) | コア C1〜C6 | 12 件中 5 件合格 |

C1 と C3 は両方のケースで合格し、C2 の拒否も合格した。残る 7 件の失敗は、DEMO-20 が develop で記録した理由と同じ（プロジェクト名のセレクタ、wiki バンドルの配線、プレビュー、管理画面のパス、7007 番の ShareJS の資産）で、このブランチが含まない別ブランチ `fix/accept-c2-c6` で直している。Linux に固有の失敗は無い。

### 第 3 回 — 壊れた状態から修正後のスクリプトで、コールドスタート

実行前に、チェックアウトをコミット 48859d7（修正 1〜3）へ移し、Ubuntu の 8.2.2 を再登録し（`systemctl restart systemd-binfmt`）、`libatomic1` を削除し、`grdm-dev reset --yes` で `runtime/volumes/` を空にした（終了 0。ファイルはコンテナの uid の所有だった）。Ubuntu の登録がある状態で `grdm-dev doctor` は終了 13 となり、置き換えのコマンドを表示した。

```toon
run3:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T04:40:11Z
  result: 2828 秒後に終了 51（スキャナーが不完全）
  plan[2]:
    "sudo: apt パッケージを入れる: libatomic1"
    "sudo: 登録済みの amd64 エミュレーター（qemu-x86_64 version 8.2.2 ...）を tonistiigi/binfmt:qemu-v10.2.3-68@sha256:400a4873... の QEMU に置き換える"
  steps[8]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env あり）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,"ok（キャッシュ）"
    up,0,"5400 秒の待ちの中で ok。ember の初回ビルドは今回も約 40 分"
    "health --network",0,"ok。すべてのポートが 127.0.0.1"
    scan,51,"semgrep が不完全、zap が不完全"
```

分かったこと: 修正 1〜3 は端から端まで働き、PR #36 の reset も uid 2001 で働く。新しい失敗が二つ `scan` を止めた。

- **失敗 4a:** ZAP（OWASP のウェブサイト検査器。コンテナの中では uid 1000 で動く）が、uid 2001 の所有の `runtime/reports/` に報告を書けず、`zap-baseline` は三つの対象すべてで報告なしに終了 0 だった。Docker Desktop の bind mount は所有者を無視するので、Mac では表に出なかった。
- **失敗 4b:** Semgrep 1.184.0 が、このブランチで加えた `.github/workflows/installer-prereq-lint.yml` に「Internal matching error」を 4 件出した。Semgrep は `run:` をシェルとして読み、Windows のジョブのインラインの PowerShell でエンジンが壊れる（そのジョブだけを除くとエラーが消えた）。

**修正 4**（`fix(installer)`、コミット 0c46a82）: ZAP の対象ごとに `runtime/reports/` の下に専用の作業ディレクトリを作り、0700 の `runtime/` の中で 0777 にし、マスクした写しを保存した後に消す。PowerShell の構文確認は `.github/scripts/Test-PowerShellSyntax.ps1` に移し、PowerShell の `run:` は一行の呼び出しにした。その後、Semgrep の `p/default` と `p/github-actions` はワークフローにエラーを出さない。

### 受入試験の実行 — 第 3 回のスタック

| 実行 ID | 範囲 | 結果 |
|---|---|---|
| [`acc-20261110T052932Z-f1da54`](runs/acc-20261110T052932Z-f1da54/results.toon) | コア C1〜C6 | 12 件中 5 件合格（上と同じケース） |

Chromium は、Linux の `grdm-dev accept` が今は表示するコマンドで入れた。`playwright install chromium` は終了 0、`playwright install-deps chromium` も終了 0。

### 第 4 回 — コミット 0c46a82、一つのコマンド: **終了 0**

```toon
run4:
  command: GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core
  started: 2026-11-10T05:34:32Z
  result: 204 秒後に終了 0（イメージはキャッシュ、ボリュームは第 3 回のまま）
  prerequisites: "前提条件はすべて揃っています。変更するものはありません。"
  steps[9]{step,code,status}:
    "secrets init",0,"skipped（runtime/.env あり）"
    doctor,0,ok
    plan,0,ok
    "compose render",0,ok
    build,0,ok
    up,0,ok
    "health --network",0,ok
    scan,0,"ok: trivy 23 対象、semgrep 4 パック、gitleaks、zap 3 対象。門は report-only で合格"
    report,0,ok
  url: "http://127.0.0.1:5000/"
  health_after: "grdm-dev health 終了 0"
```

重大度ごとの検出数（M1 では報告のみ、[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)）: critical 817、high 4355、medium 4392、low 2164、info 5。

### 準備の訂正 — ホームの mount は資格情報を実際に見せていた

準備の Warning は、ホームの mount がホストの GitHub 資格情報を「見せてしまうところだった」と書いたが、それは小さく書きすぎである。VM の最初の起動で `/Users/komiyama` が読み取り専用で mount され、ディレクトリの一覧で確かめた。最初の起動から、`lima.yaml` から mount を外して VM を再起動するまでの数分間、`~/.config/gh/hosts.yml` は VM の中から読めた。そのファイルを読んだものは無く、その時点で VM にはリポジトリも道具も入れていなかった。コミット 45b49be 以降、`install-ubuntu.sh` は共有フォルダ（virtiofs・9p・sshfs など）に `.config/gh/hosts.yml`・`.git-credentials`・`.netrc`・`.docker/config.json` があると終了 10 で止まる。環境ガイドには Lima の手順（最初の起動の前に `"~"` の mount を消し、`mount` で確かめる）を加えた。

### 第 5 回 — develop 50740b1（PR #40〜#43）へ rebase、PostgreSQL 18

develop で PostgreSQL（GRDM が記録を保つ主なデータベース。[REF-01](../reference/REF-01_Glossary.md)）が 9.6 から 18.6 に上がった（PR #42、[ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md)）ので、`up` の前に既存のデータを移す必要があった。ブランチを 2 度 rebase したので、上に書いたコミットは 8538324（修正 1〜3、旧 48859d7）と 05ff502（修正 4、旧 0c46a82）になった。ホストのミラーは `git fetch` で更新した。manifest は osf.io を 8fc45de4 に固定し、WaterButler（45e97a51）と modular-file-renderer（749e58d3）は固定したコミットのまま。

```toon
run5:
  head: 45b49be
  steps[10]{step,code,seconds,note}:
    down,0,3,""
    doctor,0,0,""
    "compose render",0,1,""
    build,0,14,"同じ固定から組んだイメージが既にある"
    "db status",0,10,"データ 9.6、イメージ 18（postgres:18.6、ダイジェスト固定）: upgrade-needed"
    "db upgrade",0,12,"下を参照"
    "db status",0,0,"データ 18: current"
    up,0,296,"健康。ember の組み上がったページはボリュームに残っていた"
    "secrets rotate",0,293,"秘密をすべて作り直し、コンテナを再作成して健康"
    health,0,0,""
  db_upgrade:
    user: "grdm、uid 2001（データディレクトリは uid 999 の所有）"
    steps: "start-old、count-old、dump、stop-old、init-new、restore、verify、stop-new、swap: すべて ok"
    dump_bytes: 4546929
    verified: "3 つのデータベース（cas、osf、postgres）と 1 つのロールで 531 個の対象（表ごとの行数、シーケンス、拡張）を照合"
    kept: "runtime/volumes/postgres_data.pg9.6-20261110T055459Z"
```

### 受入試験の実行 — 第 5 回のスタック: **12 件中 12 件**

| 実行 ID | 範囲 | 結果 |
|---|---|---|
| [`acc-20261110T060511Z-80ee06`](runs/acc-20261110T060511Z-80ee06/results.toon) | コア C1〜C6 | **12 件中 12 件合格**、終了 0 |

### 第 6 回 — 同じスタックで一つのコマンド

`GRDM_WITH_ACCEPT=1 ./installer/install-ubuntu.sh --yes --profile core` は 273 秒で終了 0。`scan`（Trivy・Semgrep・gitleaks・ZAP がすべて `ok`）と `report` まですべての段が通った。その後の `grdm-dev health` も終了 0。重大度ごとの検出数: critical 808、high 4328、medium 4470、low 2267、info 6。

### 残っていること

- **Ubuntu 24.04 amd64:** 未実行。エミュレーションが要らないので、失敗 1・2 と 3 の arm64 の部分は当てはまらない。失敗 4a（uid 1000 の ZAP）と PR #36 の所有者処理は当てはまるので、まっさらな amd64 の機械が要る。
- **WSL2:** 未実行。Docker は Docker Desktop から来て、その bind mount は Mac と同じく振る舞うので 4a は起きないと見込む。チェックアウトは WSL の中に置く。Windows 11 の実機が要る（[ADR-08 §5](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md)）。
- **再起動後のエミュレーション:** QEMU の登録は残らない。Ubuntu の `qemu-user-static` が入っている間は起動時に 8.2.2 が戻り、`doctor` が終了 13 で止まる。`install-ubuntu.sh` をもう一度実行すると置き換える。
- **受入試験:** develop が PR #40 の修正を取り込んだ後、第 5 回で完了（12 件中 12 件）。
- **コールドスタートの時間:** イメージが組めている状態で、空のボリュームからの `up` はこの VM で約 40 分。ほぼすべてが QEMU での ember の初回ビルドである。何も無い状態からのイメージのビルドには、さらに約 60 分かかった（第 1・2 回）。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Virtual machine | A whole computer simulated by software, inside a real one. | 本物のコンピュータの中でソフトウェアが模した、一台のコンピュータ。 |
| Emulation | Running a program built for one kind of CPU on another kind, slower but working. | ある種類の CPU 向けに作ったプログラムを別の CPU で動かすこと。遅いが動く。 |
| QEMU | A free program that emulates a CPU; Linux uses it to run amd64 programs on arm64. | CPU を模す無償のプログラム。Linux は arm64 で amd64 のプログラムを動かすのに使う。 |
| binfmt_misc | The Linux table that says which program runs a file of a foreign CPU type. | 別の CPU 向けのファイルをどのプログラムで動かすかを決める Linux の表。 |
| Mirror | An identical copy of a repository, here read-only and made on the host. | リポジトリの同一の写し。ここではホストで作った読み取り専用のもの。 |
