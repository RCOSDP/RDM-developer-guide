# DEMO-22 Core Install on Ubuntu 24.04 amd64 under QEMU / Ubuntu 24.04 amd64（QEMU 上）でのコア導入記録

> **Summary:** What happened when `installer/install-ubuntu.sh --yes --profile core` was run on a fresh Ubuntu 24.04 amd64 virtual machine that is fully emulated by QEMU on an Apple Silicon Mac, as an ordinary user whose uid is not 1000. One entry per run; nothing is edited after the fact.
> **概要:** Apple Silicon の Mac 上で QEMU が全体をエミュレーションする新しい Ubuntu 24.04 amd64 の仮想マシンで、uid が 1000 でない一般利用者として `installer/install-ubuntu.sh --yes --profile core` を実行したときに起きたこと。実行ごとに 1 節。後から書き換えない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.5 — 2026-11-12. **Learned:** a result must carry its provenance and its limits: the run-3 numbers are the author's transcription of VM-local output, not committed raw evidence; an exit 51 and an M1 report-only "pass" are both true and say different things; and a repeatable Trivy deadline on one image is an observation whose cause (emulation, load, image size) is still being investigated, not a finding about the installer. ／ 結果は、出所と限界を添えなければならない。第 3 回の数値は VM 内の出力を著者が書き写したもので、コミットした生の証跡ではない。終了 51 と M1 の report-only の「pass」はどちらも真で、言うことが違う。また 1 つのイメージでの Trivy の期限切れが再現したのは観察であり、その原因（エミュレーション、負荷、イメージの大きさ）は調査中で、インストーラーについての所見ではない。
  0.4 — 2026-11-12. **Learned:** the security gate is the part of the install that is hardest on an emulated machine and still the part that must be shown: `scan` ran to its end in 1 h 13 min 30 s and exited 51 (a scanner was incomplete), because Trivy's fixed 5-minute limit stopped on the 7 GB ember image, which was scanned in DEMO-21 on a machine without full-system emulation; the gate itself said pass at M1 because it is report-only, so an exit 51 and a "pass" can both be true and a reader must read both. ／ セキュリティゲートは、エミュレーションの機械で最も重い工程だが、それでも示さなければならない工程である。`scan` は 1 時間 13 分 30 秒で最後まで走り、終了 51（スキャナーの一部が未完）で終わった。Trivy の固定の 5 分の制限が 7 GB の ember イメージで切れたためで、DEMO-21 では機械全体のエミュレーションでない機械で走査できた。ゲート自体は M1 の report-only なので pass と言った。つまり終了 51 と「pass」は両立し、読者は両方を読まなければならない。
  0.3 — 2026-11-12. **Learned:** a record must say what each statement is: the compile times are observations, "a working day" and "about nine hours" are extrapolations, the explanation of the DNS stall is a hypothesis, and the stages that were not run (`scan`, `report`) must never sit in a list of stages that were; the wiki page's 30-second `goto` is the only acceptance failure, and a rerun with waits about ten times longer passed, in a patched copy only. ／ 記録は、各文が何かを言わなければならない。コンパイル時間は観察、「1 営業日」と「約 9 時間」は外挿、DNS の停止の説明は仮説であり、実行していない工程（`scan`・`report`）を実行した工程の一覧に入れてはならない。wiki ページの 30 秒の `goto` が受入の唯一の失敗で、待ちを約 10 倍にした再実行は（パッチを当てたコピーだけで）合格した。
  0.2 — 2026-11-12. **Learned:** once the images exist, the stages that were run behind `build` (`up`, `health --network`, acceptance) showed nothing specific to amd64: `up` was healthy and `health --network` exited 0 with all 24 services on `127.0.0.1`, and the core acceptance suite passed 11 of 12 on a machine where every browser page takes about ten times longer; the one failure is a 30-second page-load timeout, which cannot be told from a real wiki fault on emulation alone, so only real amd64 hardware can settle it. And the acceptance runner needs `--seed` and its own browser folder, which a reader who follows an older record by memory forgets. ／ イメージさえあれば、`build` より後ろで実行した工程（`up`、`health --network`、受入）に amd64 に固有のことは見えなかった。`up` は健康になり、`health --network` は 24 サービスすべてが `127.0.0.1` で終了 0、コアの受入試験は、ブラウザの表示が約 10 倍遅い機械で 12 件中 11 件合格した。失敗の 1 件は 30 秒のページ読み込みのタイムアウトで、エミュレーションだけでは本物の wiki の不具合と区別できず、決着できるのは実際の amd64 の機械だけである。また受入試験の実行には `--seed` と専用のブラウザ置き場が要り、古い記録を記憶で追う読者は忘れる。
  0.1 — 2026-11-12. **Learned:** a virtual machine that emulates a whole amd64 computer on Apple Silicon is a good test of the Ubuntu amd64 prerequisites and of every image that builds from binary packages, but not of an image that compiles scientific Python from source: osf.io's numpy, pandas and scipy took about ten times as long as under Rosetta (an extrapolation of that ratio puts the one command at about nine hours, not measured to the end), and `install` could not even be told to wait longer in `up`. ／ Apple Silicon 上で amd64 のコンピュータ全体をエミュレーションする仮想マシンは、Ubuntu amd64 の前提条件と、バイナリのパッケージから組むイメージの試験には向く。しかし科学計算の Python をソースから組むイメージには向かない。osf.io の numpy・pandas・scipy は Rosetta の約 10 倍かかり（この比の外挿では一つのコマンドは約 9 時間。最後までは測っていない）、`install` に `up` の待ちを延ばすよう伝える手段すらなかった。
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

The `osf.io` image (Python 3.6 on Alpine, whose C library has no ready-made wheels) compiles numpy 1.15.4, pandas 1.1.0 and scipy from source in one `RUN` step. Nine other images of the profile built natively in the VM and are not the problem (ember-osf-web is prebuilt; wiki-frontend builds on the osf.io image, so it was not built in the VM but imported from the Rosetta VM, see Run 2):

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
osf_compile[4]{step,qemu_system_vm,rosetta_vm,ratio}:
  "numpy 1.15.4 (setup.py install)","971 s","118 s","8.2x"
  "pandas 1.1.0 (wheel)","4298 s","411 s","10.5x"
  "scipy (wheel)","more than 6400 s, not finished when stopped","about 1000 s","6x or more"
  "whole RUN step","not finished after 5 h 12 min","3298 s (55 min)","about 10x is an extrapolation, not measured"
```

The *rosetta_vm* column is a second, temporary Lima VM (`vmType: vz`, arm64 Ubuntu with Rosetta registered, the same read-only mirror, no home mount) that built the same commit with `docker buildx build --platform linux/amd64`: the whole osf.io image took 64 min 11 s there. The first three rows are observations. Everything about the whole step, a working day, or "about nine hours" is an extrapolation of the ratio (3298 s times roughly ten), because the emulated step was stopped. I did not run the step on real amd64 hardware, so how long it takes there is not measured; I expect it to be no slower than the Rosetta figure, which is an expectation, not a result. The limit seen here therefore belongs to full-system emulation, not to the installer or the image. **No timeout of the installer applies to `build`: `--timeout` belongs to `up` alone and neither shortens nor extends `build`, and nothing was changed for it.**

### Run 2 — the same VM, osf.io and wiki-frontend images built under Rosetta and loaded

To test everything after `build`, the two images that cannot be built here were produced in the Rosetta VM from the same pinned commits (`osf.io` with `docker buildx build`, `wiki-frontend` with `grdm-dev build --component wiki-frontend --platform linux/amd64`), moved with `docker save | gzip`, `limactl cp` and `docker load`, and carry the tags the installer would give them. The steps that were then run one by one are `grdm-dev up`, `health --network` and `accept`; `scan` and `report` were **not** run. This is **not** a proof of the one command, and it proves nothing about the stages not run: it shows only that, with these two imported images, the stack came up healthy and passed most of the core acceptance suite.

The ember-osf-web container had been started earlier with `docker compose up -d ember_osf_web` so that its first build ran in parallel with the image work (it has no `depends_on`, as the manifest note says):

```toon
ember_first_build:
  container_start: 2026-11-12T04:14:00Z
  built: 2026-11-12T05:58:42Z
  serving_4200: 2026-11-12T06:00:05Z
  duration: "1 h 44 min 42 s to the build, 1 h 46 min to the port (QEMU system emulation, one core busy); 44 min 15 s under user-mode QEMU on arm64 (DEMO-21)"
```

```toon
run2:
  command: "grdm-dev --yes --profile core up --no-open --timeout 7200, then health --network, then accept"
  up:
    started: 2026-11-12T06:03:36Z
    finished: 2026-11-12T08:23:03Z
    result: "exit 0 after 2 h 19 min 27 s, healthy: true (the wait was 7200 s)"
    osf_init: "about 2 h 15 min: 650 migration files and the registration-schema data migrations, one core busy; osf_init: done at 08:18:49Z"
  health_network: "exit 0, loopback_only: true, 9 project ports (1234, 4200, 5000, 7007, 7777, 7778, 8000, 8001, 8080) on 127.0.0.1, 24 services"
  not_run: "scan and report (see What remains)"
```

`up` takes 2 h 19 min here (it was 296 s on an already migrated arm64 stack in [DEMO-21](21_core_install_ubuntu_arm64_lima.md) run 5); nearly all of it is `osf_init`'s Django migrations. The default wait (1800 s) would have stopped it with exit 40, which is the case fix 2 is for. The checkout's volumes were created by uid 2002 and the containers' uids, with no ownership error (`volume_owner_init` and both `volume_access_check` services exited 0).

### Acceptance — five runs, two of them without `--seed` (my omission)

```toon
accept[5]{run_id,scope,seeded,passed,failed,error,skipped,note}:
  acc-20261112T083417Z-f2b524,"all, core C1-C6 and S1-S5",no,1,3,8,10,"the test users did not exist: fakecas printed 'User ... not found'; my omission, grdm-dev accept needs --seed on a fresh stack"
  acc-20261112T085656Z-c69ad2,"all",yes,11,1,0,10,"core C1-C6: 11 of 12 passed; the 10 skipped are S1-S5, whose modules carry an unconditional skip(reason=M3), so they are skipped whatever the profile"
  acc-20261112T092035Z-e4c24d,"C4 only",no,0,1,1,0,"again without --seed: the users did not exist, so C4 success failed and C4 rejection errored; this run says nothing about the wiki page"
  acc-20261112T092701Z-876a61,"C4 only",yes,1,1,0,0,"C4 rejection passed again, C4 success failed again at the same 30 s goto"
  acc-20261112T095258Z-308ef1,"C4 only, longer waits",yes,2,0,0,0,"both C4 cases passed; the waits were lengthened only in the VM's working copy, see below"
```

Evidence: [`acc-20261112T083417Z-f2b524`](runs/acc-20261112T083417Z-f2b524/results.toon) (no seed), [`acc-20261112T085656Z-c69ad2`](runs/acc-20261112T085656Z-c69ad2/results.toon) (core 11 of 12 in 21 min 29 s), [`acc-20261112T092035Z-e4c24d`](runs/acc-20261112T092035Z-e4c24d/results.toon) (C4 only, no seed) [`acc-20261112T092701Z-876a61`](runs/acc-20261112T092701Z-876a61/results.toon) (C4 only, seeded) and [`acc-20261112T095258Z-308ef1`](runs/acc-20261112T095258Z-308ef1/results.toon) (C4 only, seeded, longer waits). Chromium was installed with the command `grdm-dev accept` prints: `PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install chromium` (my first install used Playwright's default folder, and `accept` refused with exit 2 until the command above was run).

The one failure that is about the product, C4 success, is `Page.goto: Timeout 30000ms exceeded` while opening `/<node>/wiki/home/?edit&view&menu` with `domcontentloaded`, in both seeded runs, in the same place. Every other seeded C-scenario takes 30–119 s here; a Mac run takes seconds, so the suite's hard-coded waits (30 s for a page, 60 s for the login, 120 s for a test, SPEC-04 §3.3) are tight on this machine. Whether the wiki page needs more than 30 s only because of emulation or because of a fault was not known at the first write-up. **This is not claimed as an emulation-only limit.** The C4 rejection case, which uses the same page, passed in both seeded runs.

**Rerun with longer waits (review r1).** The VM's working copy of the acceptance suite was patched, and the patch was **not** committed and is not in this branch: the page-load, click and selector waits of `test_c4_wiki_collab.py` from 30/60 s to 600 s, `COLLAB_BOUND_MS` from 30 s to 300 s, the login waits of `conftest.py` to 300 s, and `TEST_TIMEOUT_S` from 120 s to 1500 s. With that, `accept --seed --only C4` passed both cases (exit 0): C4 success took 182.6 s, where the unpatched run gave up at 30 s on the first page, and the rejection case took 107.8 s. So on this machine the failure goes away when the waits are about ten times longer, which fits a slow page rather than a broken one. It is one rerun of one scenario on a patched copy, not a clean 12 of 12 of the committed suite, and it does not show how long the wiki page takes on real hardware; the fixed waits of SPEC-04 §3.3 stay as they are and nothing was changed for this.

**Fix 2** (`fix(installer)`): `grdm-dev install` accepts `--timeout SECONDS` and passes it to `up`, so a slow host can use the one command (`./installer/install-ubuntu.sh --yes --profile core --timeout 14400`). It affects `up` only: it neither shortens nor extends `build`. Before, `install` had no way to extend the 1800 s wait of `up`, and an install that was merely slow in `up` ended with exit 40 and had to be continued by hand. An explicit `--timeout 0` is passed on as 0 (review r1 R5). The default is unchanged: 1800 s on macOS and amd64, 5400 s on Linux arm64 with amd64 services; no measurement here shows that a native amd64 host needs more.

**Observation (no fix):** while `playwright install-deps` ran during the heavy start, the guest's name resolution timed out for a while (`apt` printed `Ign:` for every repository; `curl` failed with `Resolving timed out`); the same commands worked a minute later, and the command was successful. I did not diagnose it. My hypothesis is that it is the user-mode network of QEMU under full load rather than an installer fault; nothing was captured that would confirm it.

### Run 3 — `scan` and `report` on the stack of run 2

> **Note on provenance:** every number in this section (start time, elapsed times, exit codes, image size, installed tool versions, tool completion and target counts, findings, the 177 allow-list matches, the baseline exceptions, the ZAP write success and the manual reruns) is an observation the author transcribed from output in the VM. It was not verified independently from raw evidence in this repository: the scan reports, SBOMs and timing logs stayed in the VM's `runtime/reports/` and are not committed, so a reviewer who has only this repository can check the arithmetic and the code paths in `installer/grdm_dev/scan.py`, but not the measurements themselves.

The stack of run 2 was still healthy (19 containers) after PR #50 was merged (develop 32e2344). The VM's checkout is at b81628f (the `commit` field of the scan report), whose `installer/grdm_dev/scan.py` is identical to develop's at 32e2344. Both commands were run as the ordinary user (uid 2002), with the scanners installed by `install-ubuntu.sh` (Trivy 0.75.0, gitleaks 8.21.2, Semgrep 1.185.0 from the venv, ZAP `ghcr.io/zaproxy/zaproxy:stable` in Docker).

```toon
run3:
  commands: "grdm-dev --yes --profile core scan, then report"
  started: 2026-11-12T12:50:52Z
  scan:
    exit: "51 (scanner incomplete) after 1 h 13 min 30 s"
    gate: "pass (report-only at M1, ADR-03)"
    parts[5]: baseline, trivy, semgrep, gitleaks, zap
  report: "exit 0 after 5 s"
  durations[5]{tool,duration,note}:
    "trivy, the image part","about 38 min","the image targets ran first; two calls on the ember-osf-web image and one on cas-overlay exited 1"
    "trivy fs + semgrep","about 5 min","Semgrep 2 min 41 s, 4 packs"
    gitleaks,"1 min 47 s","ok"
    zap,"30 min 53 s","web 24 min, admin 3 min 47 s, ember_osf_web 3 min 8 s; the reports were written by uid 1000 into the uid-2002 checkout (DEMO-21 failure 4a does not recur)"
    "baseline controls",seconds,"pass with 10 accepted exceptions (postgres, volume_owner_init, mongo, rabbitmq)"
  tools[4]{tool,version,result}:
    trivy,0.75.0,"incomplete: sbom and scan of the ember-osf-web image, and the sbom of cas-overlay, exited 1"
    semgrep,1.185.0,"ok, 1 rule timeout on installer/tests/test_compose.py (a coverage warning at M1)"
    gitleaks,8.21.2,ok
    zap,stable,"ok, 3 targets (web, admin, ember_osf_web)"
  trivy_targets: "22 in all: 16 images, 5 integration source checkouts, 1 repository (scan.py counts all three kinds)"
  trivy_outputs: "21 vulnerability-scan outputs (all but the ember image) and 20 SBOMs (all but the ember image and cas-overlay)"
  findings_total: "5959, an incomplete total (see below)"
  findings_by_severity: "critical 298, high 1726, medium 2560, low 1369, info 6"
  by_tool: "trivy 5931 (critical 298, high 1725, medium 2551, low 1357); zap 28 (high 1, medium 9, low 12, info 6); semgrep 0; gitleaks 0"
  allowlist: "58 entries in manifest/allowlist.json; 177 findings matched (author-reported); M1 entry-count baseline 0 (allowlist_baseline); over_threshold 2024"
  gate_rule: report-only
```

How to read it:

- **Exit 51 is an observed, repeatable result for one image.** Trivy has a fixed default limit of 5 minutes per call (`scan.py` passes no `--timeout`). The ember-osf-web image (about 7 GB, prebuilt) did not finish its SBOM or its vulnerability scan inside it, and a manual rerun of the SBOM ended with `FATAL ... context deadline exceeded` after 5 min 3 s. What I observed ends there. That this is caused by emulation, by load or by the image's size is an explanation I am investigating, **not established**: the same image was scanned in [DEMO-21](21_core_install_ubuntu_arm64_lima.md) on a machine without full-system emulation (23 targets there, a different set, so the 22 here is not a count of missing ones). I have not shown it to be an installer fault either.
- **The cas-overlay SBOM** also exited 1 during the run; its vulnerability scan did not fail. Run alone afterwards, the same SBOM took 3.6 s and exited 0. `scan` hides Trivy's message (`--quiet`), so I did not capture why it failed during the run. Its cause is **unresolved** and stays in the remaining work.
- **What is covered and what is not.** Of 22 Trivy targets, 21 have a vulnerability-scan result; the ember image has none, so its vulnerabilities are missing. 20 have an SBOM; the ember image and cas-overlay do not. Complete SBOM-plus-scan coverage is therefore 20 of 22.
- **The totals are an incomplete total.** The 5959 findings (and the Trivy 5931) are findings left after allow-list matching (the 177 matched findings are counted separately), over 21 of 22 targets, plus **three** HIGH diagnostic findings that `scan` adds for the failed calls (`SCAN-FAILED` for ember, `SBOM-FAILED` for ember and for cas-overlay, `scan.py` lines 850–858). The ember image's vulnerabilities are not in the totals; the diagnostics are. The true total for a complete scan is not known and is not "larger by a known amount".
- **Semgrep, gitleaks and ZAP completed** on the amd64 VM; Semgrep and gitleaks reported nothing, ZAP reported 28 alerts on three targets.
- **The gate said pass** because the milestone is M1 and the rule is report-only ([ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)): 2024 critical and high findings are over the threshold and are counted, not blocking. `scan` still exits 51 when a scanner is incomplete, whatever the gate says. The allow-list has 58 entries and 177 findings matched (one entry can match several findings); `allowlist_baseline` is not a count of matches but the entry-count baseline recorded for M1 in `manifest/allowlist.baseline.json`, which is 0.
- `report` exited 0 and bundles the `doctor`, `plan`, `health`, `scan` and `accept` reports of this stack. They stay in the VM and are not committed, which is the limit described at the top of this section.
- A decision to consider, not changed here: passing a configurable Trivy `--timeout` from `scan` may reduce the deadline-limited runs; it needs a rerun to show that, and it guarantees neither an exit 0 nor any security conclusion.

### What remains

- **One uninterrupted run of the one command on Ubuntu amd64:** not done. It needs real amd64 hardware (a cloud virtual machine or a PC); on this machine it is estimated at about 9 hours (an extrapolation of the 10x ratio, not measured to the end), and the time on real hardware is not measured. Checked on amd64 so far: prerequisites, `doctor`, `git` access through mirrors, uid 2002, and nine images built natively. Not built on amd64 here: osf.io and wiki-frontend (imported from the Rosetta VM).
- **`scan` and `report`:** run in run 3 (exit 51 and 0, see above; the numbers are the author's transcription, not committed evidence). Still open from it: the ember-osf-web image's Trivy SBOM and vulnerability scan, which reproducibly passed the 5-minute limit here and whose cause is not established (a longer limit, a host without full-system emulation or something else); and the cas-overlay SBOM, whose failure in the run is **unexplained**. The ZAP report directory of DEMO-21 failure 4a is shown on an amd64 host (the ZAP reports were written).
- **C4 success:** failed twice at the suite's 30 s wait and passed once with waits about ten times longer (patched copy, not committed); a clean run of the committed suite on real amd64 hardware, or a decision to make the waits configurable, is still open.
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

`osf.io` イメージ（Alpine 上の Python 3.6。Alpine の C ライブラリには出来合いの wheel が無い）は、numpy 1.15.4、pandas 1.1.0、scipy を一つの `RUN` 手順でソースからコンパイルする。このプロファイルのほかの 9 つのイメージは VM の中でネイティブに組め、問題ではない（ember-osf-web はビルド済み。wiki-frontend は osf.io のイメージの上に組むので VM では組まず、Rosetta の VM から輸入した。第 2 回を参照）：

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
osf_compile[4]{step,qemu_system_vm,rosetta_vm,ratio}:
  "numpy 1.15.4（setup.py install）","971 秒","118 秒","8.2 倍"
  "pandas 1.1.0（wheel）","4298 秒","411 秒","10.5 倍"
  "scipy（wheel）","6400 秒超、止めた時点で未完","約 1000 秒","6 倍以上"
  "RUN 手順全体","5 時間 12 分後も未完","3298 秒（55 分）","約 10 倍は外挿で、実測ではない"
```

*rosetta_vm* の列は、同じコミットを `docker buildx build --platform linux/amd64` で組んだ、もう一つの一時的な Lima VM（`vmType: vz`、Rosetta を登録した arm64 の Ubuntu、同じ読み取り専用ミラー、ホームの mount なし）の値で、osf.io のイメージ全体が 64 分 11 秒だった。最初の 3 行は観察である。手順全体、1 営業日、「約 9 時間」はいずれも、エミュレーションの手順を途中で止めたため、比（3298 秒の約 10 倍）からの外挿である。実際の amd64 の機械ではこの手順を実行しておらず、そこでの所要時間は測っていない。Rosetta の値より遅くはならないと期待するが、これは期待であり結果ではない。したがってここで見えた限界は、機械全体のエミュレーションのものであり、インストーラーでもイメージでもない。**`build` に効くインストーラーのタイムアウトは無い。`--timeout` は `up` だけのもので、`build` を短くも長くもせず、そのための変更もしていない。**

### 第 2 回 — 同じ VM、Rosetta で組んだ osf.io と wiki-frontend のイメージを読み込む

`build` より後のすべてを試すため、ここで組めない 2 つのイメージを、同じ固定コミットから Rosetta の VM で作った（`osf.io` は `docker buildx build`、`wiki-frontend` は `grdm-dev build --component wiki-frontend --platform linux/amd64`）。`docker save | gzip`、`limactl cp`、`docker load` で運び、インストーラーが付けるのと同じタグにした。その後に一つずつ実行した工程は `grdm-dev up`、`health --network`、`accept` で、`scan` と `report` は実行して**いない**。これは一つのコマンドの証明では**なく**、実行していない工程については何も証明しない。この 2 つの輸入したイメージで、stack が健康に起動し、コアの受入試験の大半に合格したことを示すだけである。

ember-osf-web のコンテナは先に `docker compose up -d ember_osf_web` で起動し、初回ビルドをイメージ作りと並行させた（マニフェストの注記のとおり `depends_on` が無い）：

```toon
ember_first_build:
  container_start: 2026-11-12T04:14:00Z
  built: 2026-11-12T05:58:42Z
  serving_4200: 2026-11-12T06:00:05Z
  duration: "ビルドまで 1 時間 44 分 42 秒、ポートまで 1 時間 46 分（QEMU の機械全体のエミュレーション、使うのは 1 コア）。arm64 のユーザーモード QEMU では 44 分 15 秒（DEMO-21）"
```

```toon
run2:
  command: "grdm-dev --yes --profile core up --no-open --timeout 7200、続いて health --network、続いて accept"
  up:
    started: 2026-11-12T06:03:36Z
    finished: 2026-11-12T08:23:03Z
    result: "2 時間 19 分 27 秒後に終了 0、healthy: true（待ちは 7200 秒）"
    osf_init: "約 2 時間 15 分: migration ファイル 650 個と登録スキーマのデータ migration、使うのは 1 コア。osf_init: done は 08:18:49Z"
  health_network: "終了 0、loopback_only: true、プロジェクトのポート 9 個（1234、4200、5000、7007、7777、7778、8000、8001、8080）が 127.0.0.1、24 サービス"
  not_run: "scan と report（残っていること を参照）"
```

ここでは `up` に 2 時間 19 分かかった（[DEMO-21](21_core_install_ubuntu_arm64_lima.md) の第 5 回の、移行済みの arm64 の stack では 296 秒）。ほとんどが `osf_init` の Django の migration である。既定の待ち（1800 秒）なら終了 40 で止まっていた。修正 2 はこの場合のためにある。ボリュームは uid 2002 とコンテナの uid が作り、所有者のエラーは無かった（`volume_owner_init` と二つの `volume_access_check` が終了 0）。

### 受入試験 — 5 回、うち 2 回は `--seed` なし（私の漏れ）

```toon
accept[5]{run_id,scope,seeded,passed,failed,error,skipped,note}:
  acc-20261112T083417Z-f2b524,"全部、コア C1-C6 と S1-S5",なし,1,3,8,10,"試験用の利用者が無く、fakecas が 'User ... not found' と出した。私の漏れ。新しい stack の grdm-dev accept には --seed が要る"
  acc-20261112T085656Z-c69ad2,"全部",あり,11,1,0,10,"コア C1-C6: 12 件中 11 件合格。skipped の 10 件は S1-S5 で、そのモジュールは無条件の skip(reason=M3) を持つので、プロファイルによらず skip される"
  acc-20261112T092035Z-e4c24d,"C4 のみ",なし,0,1,1,0,"またも --seed なし: 利用者が無く、C4 の success は failed、rejection は error。この実行は wiki ページについて何も言わない"
  acc-20261112T092701Z-876a61,"C4 のみ",あり,1,1,0,0,"C4 の rejection はまた合格、C4 の success はまた同じ 30 秒の goto で失敗"
  acc-20261112T095258Z-308ef1,"C4 のみ、待ちを延ばした",あり,2,0,0,0,"C4 の 2 ケースとも合格。待ちを延ばしたのは VM の作業コピーだけ。下を参照"
```

証跡: [`acc-20261112T083417Z-f2b524`](runs/acc-20261112T083417Z-f2b524/results.toon)（seed なし）、[`acc-20261112T085656Z-c69ad2`](runs/acc-20261112T085656Z-c69ad2/results.toon)（コア 12 件中 11 件、21 分 29 秒）、[`acc-20261112T092035Z-e4c24d`](runs/acc-20261112T092035Z-e4c24d/results.toon)（C4 のみ、seed なし）、[`acc-20261112T092701Z-876a61`](runs/acc-20261112T092701Z-876a61/results.toon)（C4 のみ、seed あり）、[`acc-20261112T095258Z-308ef1`](runs/acc-20261112T095258Z-308ef1/results.toon)（C4 のみ、seed あり、待ちを延ばした）。Chromium は `grdm-dev accept` が表示するコマンド `PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install chromium` で入れた（最初は Playwright の既定の置き場に入れたため、このコマンドを実行するまで `accept` は終了 2 で拒んだ）。

製品に関わる失敗は C4 の success の 1 件で、`/<node>/wiki/home/?edit&view&menu` を `domcontentloaded` まで開くときの `Page.goto: Timeout 30000ms exceeded` である。seed ありの 2 回とも同じ場所で起きた。seed ありのほかの C のシナリオはここで 30〜119 秒かかる。Mac なら数秒である。試験の固定の待ち（ページ 30 秒、ログイン 60 秒、1 件 120 秒、SPEC-04 §3.3）はこの機械では短い。wiki のページが 30 秒を超えるのがエミュレーションのためだけか、不具合のためかは、最初の書き込みの時点では分からなかった。**エミュレーションだけの限界とは主張しない。** 同じページを使う C4 の rejection は seed ありの 2 回とも合格した。

**待ちを延ばした再実行（レビュー r1）。** VM の中の受入試験の作業コピーにパッチを当てた。このパッチはコミット**しておらず**、このブランチには無い。`test_c4_wiki_collab.py` のページ読み込み・クリック・セレクターの待ちを 30／60 秒から 600 秒へ、`COLLAB_BOUND_MS` を 30 秒から 300 秒へ、`conftest.py` のログインの待ちを 300 秒へ、`TEST_TIMEOUT_S` を 120 秒から 1500 秒へ。これで `accept --seed --only C4` は 2 ケースとも合格した（終了 0）。C4 の success は 182.6 秒で、パッチなしの実行は最初のページで 30 秒で諦めた。rejection は 107.8 秒だった。つまりこの機械では、待ちを約 10 倍にすると失敗が消え、壊れたページではなく遅いページと整合する。ただしこれはパッチを当てたコピーでの 1 シナリオの 1 回の再実行であり、コミットした試験の 12 件中 12 件という意味ではなく、実機で wiki ページがどれだけかかるかも示さない。SPEC-04 §3.3 の固定の待ちは変えておらず、この件のための変更もしていない。

**修正 2**（`fix(installer)`）: `grdm-dev install` が `--timeout 秒` を受け取って `up` に渡す。遅い機械でも一つのコマンドが使える（`./installer/install-ubuntu.sh --yes --profile core --timeout 14400`）。効くのは `up` だけで、`build` を短くも長くもしない。以前の `install` には `up` の 1800 秒の待ちを延ばす手段が無く、`up` が単に遅いだけの導入が終了 40 で終わり、手で続けるしかなかった。明示した `--timeout 0` は 0 のまま渡す（レビュー r1 R5）。既定は変えない: macOS と amd64 は 1800 秒、amd64 のサービスがある Linux arm64 は 5400 秒。ネイティブの amd64 がそれ以上を要することを示す測定は、ここには無い。

**観察（修正なし）:** 重い起動の最中に `playwright install-deps` を実行したとき、ゲストの名前解決がしばらくタイムアウトした（`apt` がすべてのリポジトリに `Ign:` と出し、`curl` が `Resolving timed out` で失敗した）。一分後には同じコマンドが通り、コマンドは成功した。原因は調べていない。仮説は、全負荷の QEMU のユーザーモードネットワークの挙動でありインストーラーの不具合ではない、というものだが、それを裏付ける記録は取っていない。

### 第 3 回 — 第 2 回の stack での `scan` と `report`

> **出所についての注記:** この節のすべての数値（開始時刻、所要時間、終了コード、イメージの大きさ、導入したツールの版、ツールの完了と対象数、指摘、許容リストの 177 件の一致、baseline の例外、ZAP の書き込みの成功、手動の再実行）は、著者が VM の中の出力から書き写した観察である。このリポジトリの生の証跡からは独立に検証していない。`scan` の報告、SBOM、時間のログは VM の `runtime/reports/` に残してコミットしていないので、このリポジトリだけを持つレビュワに確かめられるのは、算術と `installer/grdm_dev/scan.py` のコードの経路で、測定そのものではない。

PR #50 のマージ後（develop 32e2344）も、第 2 回の stack はまだ健康だった（コンテナ 19 個）。VM の checkout は b81628f（`scan` の報告の `commit` 欄）で、その `installer/grdm_dev/scan.py` は 32e2344 の develop と同一である。どちらのコマンドも一般利用者（uid 2002）で実行し、スキャナーは `install-ubuntu.sh` が入れたもの（Trivy 0.75.0、gitleaks 8.21.2、venv の Semgrep 1.185.0、Docker の ZAP `ghcr.io/zaproxy/zaproxy:stable`）。

```toon
run3:
  commands: "grdm-dev --yes --profile core scan、続いて report"
  started: 2026-11-12T12:50:52Z
  scan:
    exit: "51（スキャナー未完）、1 時間 13 分 30 秒後"
    gate: "pass（M1 の report-only、ADR-03）"
    parts[5]: baseline, trivy, semgrep, gitleaks, zap
  report: "終了 0、5 秒"
  durations[5]{tool,duration,note}:
    "trivy の image の部分","約 38 分","image の対象が先に走った。ember-osf-web イメージの 2 回と cas-overlay の 1 回の呼び出しが終了 1"
    "trivy fs と semgrep","約 5 分","Semgrep は 2 分 41 秒、4 パック"
    gitleaks,"1 分 47 秒","ok"
    zap,"30 分 53 秒","web 24 分、admin 3 分 47 秒、ember_osf_web 3 分 8 秒。uid 1000 が uid 2002 の checkout に報告を書けた（DEMO-21 の失敗 4a は再発しない）"
    "baseline controls",数秒,"pass、承認済みの例外 10 件（postgres、volume_owner_init、mongo、rabbitmq）"
  tools[4]{tool,version,result}:
    trivy,0.75.0,"未完: ember-osf-web イメージの sbom と scan、cas-overlay の sbom が終了 1"
    semgrep,1.185.0,"ok、installer/tests/test_compose.py でルールのタイムアウト 1 件（M1 では網羅の警告）"
    gitleaks,8.21.2,ok
    zap,stable,"ok、3 対象（web、admin、ember_osf_web）"
  trivy_targets: "全部で 22: image 16、統合ソースの checkout 5、リポジトリ 1（scan.py は 3 種類すべてを数える）"
  trivy_outputs: "脆弱性走査の出力 21（ember イメージ以外すべて）、SBOM 20（ember イメージと cas-overlay 以外すべて）"
  findings_total: "5959。不完全な合計（下を参照）"
  findings_by_severity: "critical 298、high 1726、medium 2560、low 1369、info 6"
  by_tool: "trivy 5931（critical 298、high 1725、medium 2551、low 1357）、zap 28（high 1、medium 9、low 12、info 6）、semgrep 0、gitleaks 0"
  allowlist: "manifest/allowlist.json に 58 項目、177 件の指摘が一致（著者報告）、M1 の項目数基準 0（allowlist_baseline）、over_threshold 2024"
  gate_rule: report-only
```

読み方:

- **終了 51 は、1 つのイメージで観察された再現する結果である。** Trivy には 1 回の呼び出しにつき既定で 5 分の固定の制限がある（`scan.py` は `--timeout` を渡さない）。ember-osf-web のイメージ（約 7 GB、ビルド済み）は、その中で SBOM も脆弱性の走査も終わらず、SBOM の手動の再実行は 5 分 3 秒後に `FATAL ... context deadline exceeded` で終わった。観察はここまでである。原因がエミュレーションか、負荷か、イメージの大きさかは、私が調べている説明であり、**確立していない**。同じイメージは、機械全体のエミュレーションでない機械の [DEMO-21](21_core_install_ubuntu_arm64_lima.md) では走査できた（そこは 23 対象で、集合が違うので、ここの 22 は欠けた数ではない）。インストーラーの不具合だとも示していない。
- **cas-overlay の SBOM** も実行中は終了 1 だった。脆弱性の走査は失敗していない。後で単独で実行すると、同じ SBOM は 3.6 秒で終了 0 だった。`scan` は Trivy のメッセージを隠す（`--quiet`）ので、実行中になぜ失敗したかは記録していない。原因は**未解決**で、残りの作業に残る。
- **何が対象で何がそうでないか。** Trivy の 22 対象のうち、21 に脆弱性の走査結果があり、ember イメージには無いので、その脆弱性は欠けている。SBOM があるのは 20 で、ember イメージと cas-overlay には無い。SBOM と走査の両方が揃うのは 22 のうち 20 である。
- **合計は不完全な合計である。** 5959 件（と Trivy の 5931 件）は、許容リストとの照合の後に残った指摘（一致した 177 件は別に数える）で、22 対象のうち 21 のもの、に、失敗した呼び出しのために `scan` が足す **3 件**の HIGH の診断（ember の `SCAN-FAILED`、ember と cas-overlay の `SBOM-FAILED`。`scan.py` の 850〜858 行）を加えたものである。ember イメージの脆弱性は合計に入っておらず、診断は入っている。完全な走査での真の合計は分からず、「既知の量だけ多い」とも言えない。
- **Semgrep、gitleaks、ZAP は amd64 VM で完走した。** Semgrep と gitleaks は何も報告せず、ZAP は 3 対象で 28 件の警告を出した。
- **ゲートは pass と言った。** 節目が M1 で規則が report-only だからである（[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md)）。重大と高の 2024 件はしきい値を超えて数えられるが、止めはしない。ゲートが何と言っても、スキャナーが未完なら `scan` は終了 51 で終わる。許容リストは 58 項目で 177 件の指摘が一致した（1 項目が複数の指摘に一致しうる）。`allowlist_baseline` は一致の数ではなく、`manifest/allowlist.baseline.json` に M1 について記録された項目数の基準で、0 である。
- `report` は終了 0 で、この stack の `doctor`・`plan`・`health`・`scan`・`accept` の報告をまとめた。それらは VM に残してコミットしていない。これがこの節の冒頭に書いた限界である。
- 検討する価値があるが、ここでは変えない判断: `scan` が設定可能な Trivy の `--timeout` を渡すと、期限で切れる実行が減る可能性がある。それを示すには再実行が要り、終了 0 も、安全性の結論も保証しない。

### 残っていること

- **Ubuntu amd64 で中断しない一つのコマンドの実行:** 未実施。実際の amd64 の機械（クラウドの仮想マシンや PC）が要る。この機械では約 9 時間と見積もる（10 倍の比の外挿で、最後までは測っていない）。実機での時間は測っていない。amd64 でこれまでに確かめたこと: 前提条件、`doctor`、ミラー経由の `git` の読み取り、uid 2002、9 つのイメージのネイティブビルド。ここで amd64 では組んでいないもの: osf.io と wiki-frontend（Rosetta の VM から輸入）。
- **`scan` と `report`:** 第 3 回で実施した（終了 51 と 0。上記。数値は著者の書き写しで、コミットした証跡ではない）。残っているのは、ここで 5 分の制限を再現して超えた ember-osf-web イメージの Trivy の SBOM と脆弱性の走査（原因は確立していない。長い制限か、機械全体のエミュレーションでないホストか、別の理由か）と、実行中に失敗した原因が**不明**の cas-overlay の SBOM である。DEMO-21 の失敗 4a の ZAP の報告ディレクトリは、amd64 のホストでも示せた（ZAP の報告が書かれた）。
- **C4 の success:** 試験の 30 秒の待ちで 2 回失敗し、待ちを約 10 倍にして 1 回合格した（パッチを当てたコピー、未コミット）。コミットした試験を実際の amd64 の機械で素のまま実行すること、または待ちを設定可能にする判断は、まだ残っている。
- **WSL2:** 未実施（理由は [DEMO-21](21_core_install_ubuntu_arm64_lima.md)）。
- **pin:** この実行は develop b81628f のもの。別の担当の統合が入ると osf.io の pin は変わる。
