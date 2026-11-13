# ADR-08 Per-OS Installer Entry Points / OS ごとのインストーラーの入口

> **Summary:** `installer/install.sh` assumes that Python, git, Docker and the scanners already exist, and Windows has no entry point at all. We decide to add three thin, consent-based prerequisite scripts, one per OS, that prepare the host and always end by running `install.sh`, so there is still one decision path. This relaxes "never needs `sudo`" for those scripts only.
> **概要:** `installer/install.sh` は Python・git・Docker・スキャナーが既にあることを前提にしており、Windows には入口そのものがない。OS ごとに一つ、同意に基づく薄い前提条件スクリプトを三つ加え、ホストを準備したうえで必ず `install.sh` を実行して終わることを決める。判断の道筋は一つのままである。「`sudo` を必要としない」という規則は、これらのスクリプトに限って緩める。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.4 — 2026-11-13. **Learned:** approval does not wait for every row of §5: the owner accepted this record on 2026-11-13 ("一括で承認、M2 完了") while real amd64 hardware and WSL2 (Windows 11) are still unrun and the §9 workflows still wait for a token with the `workflow` scope, so those stay open as M3 items on the [status board](../status/README.md#english) instead of blocking the decision. ／ 承認は §5 のすべての行を待たない。所有者は 2026-11-13 にこの記録を承認した（「一括で承認、M2 完了」）。amd64 の実機と WSL2（Windows 11）は未実行で、§9 のワークフローは `workflow` スコープのトークンをまだ待つので、それらは決定を止めず、[進捗ボード](../status/README.md#japanese)の M3 の残件として開いたまま残す。
  0.3 — 2026-11-10. **Learned:** the decision can land before its CI: the workflows of §9 need a token with the `workflow` scope, so they wait on branch `feat/per-os-installers` and the per-OS scripts are checked by hand and by DEMO-21 until then. ／ 決定は CI より先に入れられる。§9 のワークフローには `workflow` スコープのトークンが要るので、ブランチ `feat/per-os-installers` で待ち、それまで OS ごとのスクリプトは手と DEMO-21 で確かめる。
  0.2 — 2026-11-10. **Learned:** the first real run of `install-ubuntu.sh`, on an Ubuntu 24.04 arm64 virtual machine, settled two rows of §5 and showed that a distribution's own emulator package is not a safe prerequisite: it crashed inside a build, so emulation now comes from a digest-pinned image ([DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)). ／ `install-ubuntu.sh` の最初の実際の実行（Ubuntu 24.04 arm64 の仮想マシン）で §5 の二行が決着し、ディストリビューション自身のエミュレーターのパッケージは安全な前提条件ではないと分かった。ビルドの中で落ちたので、エミュレーションはダイジェストで固定したイメージから入れる（[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)）。
  0.1 — 2026-11-10. **Learned:** "the installer checks each prerequisite" only moved the first failure later: without Trivy and gitleaks an otherwise perfect install still stops with exit 51 at its `scan` step, so prerequisites are everything the whole sequence needs, not only what its first step needs. ／ 「インストーラーが各前提条件を確認する」は最初の失敗を後ろへずらしただけだった。Trivy と gitleaks が無いと、ほかが完璧でも導入は `scan` の段で終了 51 になる。前提条件とは最初の段に要るものではなく、一連の手順全体に要るものである。
- Status: Accepted by the owner, 2026-11-13 (proposed 2026-11-10, M2). Review date: after the first recorded run of each script on owner hardware.
- Records a decision for: [SPEC-02 §1, §2.3, §8, §9, §10](../spec/02_installer_cli.md#english)
- Parent index / 親索引: [Decision records](README.md)
- Related: [ADR-03 Staged security gate](ADR-03_Staged_Security_Gate.md) · [ADR-07 Native builds of EOL middleware](ADR-07_Native_Builds_of_EOL_Middleware.md) · [SPEC-04 §8](../spec/04_acceptance_tests.md#english) · [Environment guide](../guides/environment/README.md#english)
- Used by: [SPEC-02](../spec/02_installer_cli.md#english) · [Environment guide](../guides/environment/README.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

An audit of the branch on 2026-11-10 found these gaps. Each was checked against the files.

- Windows has no entry point, although [SPEC-02 §8](../spec/02_installer_cli.md#english) requires Windows 11 to work.
- No script installs Docker (the tool that builds images and runs containers; see [REF-01](../reference/REF-01_Glossary.md)), Python, buildx (Docker's helper that builds one image for several kinds of computer; see [REF-01](../reference/REF-01_Glossary.md)) or git. `install.sh` only prints a hint for Python.
- `grdm-dev install` stops with exit 51 at its `scan` step when `trivy` or `gitleaks` is missing, and nothing installs them.
- The repository had no `.gitattributes`. A clone with `core.autocrlf=true` turns the first line of `install.sh` into `#!/usr/bin/env bash` plus a CR (carriage return, the extra character Windows puts at the end of a line). The kernel then fails to find the interpreter, so the script's own CRLF guard never runs. The guard's hint also used `sed -i ""`, which only BSD `sed` accepts.
- No workflow runs `install.sh`, Compose (the Docker tool that starts many containers from one file; see [REF-01](../reference/REF-01_Glossary.md)), macOS, Windows or arm runners. The Windows CI (continuous integration: the checks that run automatically; see [REF-01](../reference/REF-01_Glossary.md)) build of SPEC-02 §8 and the amd64 (the CPU type of ordinary PCs and servers; see [REF-01](../reference/REF-01_Glossary.md)) build of SPEC-04 §8 did not exist.

### 2. Decision

1. **Three scripts, one decision path.** `installer/install-ubuntu.sh`, `installer/install-macos.sh` and `installer/install-windows.ps1` only prepare the host. Each ends by running `installer/install.sh`, passing other arguments unchanged. Windows reaches it through `install-ubuntu.sh` inside WSL2 (a way to run Linux inside Windows; see [REF-01](../reference/REF-01_Glossary.md)). No OS difference moves into `grdm-dev`.
2. **`sudo` is allowed here and only here.** `install.sh` and `grdm-dev` keep the rule that they never need `sudo` (a way to run a command as the computer's administrator). The prerequisite scripts may use it, after consent.
3. **Consent.** Detection is read-only. Each script lists its changes first and asks once; joining the `docker` group has its own question, because that group is equivalent to administrator rights. `--yes` (`-Yes` on Windows) gives consent up front. With no terminal and no `--yes` the script stops with exit 2. `--dry-run` (`-DryRun`) prints the plan and changes nothing.
4. **Exit codes.** The scripts reuse 2, 10 and 11 of `messages.tsv`. No number is added.
5. **Trusted sources only; nothing is piped into a shell.**
   - Ubuntu: Docker's apt (Ubuntu's package installer) repository. The signing key is accepted only when its fingerprint is `9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBF CD88`. Trivy (a scanner that reads our images and lists the holes it knows about; see [REF-01](../reference/REF-01_Glossary.md)) 0.75.0 and gitleaks 8.21.2 come from their GitHub releases and must match a SHA-256 (a file's fingerprint) pinned in the script, then go to `~/.local/bin`.
   - macOS: Homebrew (a package manager for macOS) formulae, whose bottles Homebrew checks. Homebrew itself is not installed by the script, because its official one-line installer pipes a download into a shell; the script points to the signed `.pkg`.
   - Windows: `wsl.exe` from Microsoft. Docker Desktop is detected, never installed, because its licence is the user's decision. The same applies on macOS.
6. **The clone stays out of `/mnt/c`.** `install-windows.ps1` accepts only one folder name under the WSL home directory, and `install-ubuntu.sh` refuses a checkout under `/mnt/` inside WSL.
7. **Tokens.** The integration repositories are private. The scripts say how to give git access (`gh auth login`, then `gh auth setup-git`) and never ask for, read or store a token.
8. **Line endings.** `.gitattributes` forces LF for shell scripts, Dockerfiles and the files that run in Linux containers. It is an explicit list, because `* text=auto` would rewrite legacy files. The CRLF hint now uses `perl -pi -e`, which works on macOS, Ubuntu and WSL.
9. **CI.** `installer-prereq-lint.yml` runs on every pull request: `bash -n`, shellcheck (a tool that finds mistakes in shell scripts), the PowerShell parser on `windows-latest`, and each script's dry run. `installer-full.yml` is `workflow_dispatch` only (started by hand) and does a full `minimum` install on `ubuntu-24.04` and `ubuntu-24.04-arm`. It reads the repository secret `GRDM_INTEGRATION_READ_TOKEN`, a read-only token that the owner creates, and passes it to git through a credential helper in one step's environment, so it is never written to disk. This workflow is what fulfils SPEC-04 §8's amd64 build, by hand. **Pending:** both workflows and `.github/scripts/Test-PowerShellSyntax.ps1` wait on branch `feat/per-os-installers` for a push with a token that has the `workflow` scope.

### 3. Options considered

```toon
options[4]{option,decision_path,risk,chosen}:
  A,"only print better hints (today)",one,"every new user repeats the same manual steps; Windows stays unserved",no
  B,"put OS bootstrap inside grdm-dev",one but mixed,"grdm-dev would need sudo and would break SPEC-02 §1; Python must exist first",no
  C,"one cross-platform script",one,"PowerShell and bash cannot share a file; Windows must drive WSL from outside anyway",no
  D,"thin per-OS scripts that end at install.sh (this ADR)",one,"three small scripts to keep working; only owner hardware proves them fully",yes
```

### 4. Consequences

- A new developer on a supported OS needs one command, plus any manual step that the script names.
- The Docker signing-key fingerprint and four SHA-256 values must be updated by hand when those versions change. That is deliberate.
- The manual workflow must exist on the default branch before GitHub lets anyone start it.

<a id="en-limits"></a>
### 5. What hosted runners cannot prove

| Claim | Status on GitHub-hosted runners |
|---|---|
| Docker Engine installed from Docker's apt repository | Not exercised when the runner image already has Docker 27 or newer, because the script then skips it. **Proven on a clean Ubuntu 24.04 arm64 virtual machine** ([DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)); amd64 still needs a clean machine. |
| WSL2 on `windows-latest` | **Unverified.** Nested virtualization (a virtual machine inside a virtual machine, which WSL2 needs) is doubtful on these runners, and no full run has been attempted. CI only parses the script and does a dry run. |
| UAC prompt, restart after enabling WSL, first-user creation, Docker Desktop's WSL integration | Need a person and real Windows 11 hardware. UAC is the Windows prompt that asks for administrator rights. |
| macOS with Docker Desktop | Hosted macOS runners provide no Docker engine, so CI is dry-run only. M2 acceptance on the Mac Studio remains the evidence. |
| amd64 emulation on arm64 Ubuntu | **Proven on a virtual machine** ([DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)): Ubuntu's `qemu-user-static` 8.2.2 crashed, so the script registers QEMU from a digest-pinned `tonistiigi/binfmt` image. Not persistent across reboots. |

The SPEC-02 §8 phrase "checked in CI as build-only" for Windows is withdrawn: CI checks the Windows script's syntax and dry run only.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

2026-11-10 にこのブランチを監査し、次の不足を見つけた。いずれもファイルと突き合わせて確かめた。

- [SPEC-02 §8](../spec/02_installer_cli.md#japanese) は Windows 11 で動くことを求めているのに、Windows の入口がない。
- Docker（イメージを作りコンテナを動かす道具。[REF-01](../reference/REF-01_Glossary.md)）、Python、buildx（一つのイメージを何種類かの計算機向けに作る Docker の助手。[REF-01](../reference/REF-01_Glossary.md)）、git を入れるスクリプトがない。`install.sh` は Python の案内を表示するだけである。
- `trivy` か `gitleaks` が無いと `grdm-dev install` は `scan` の段で終了 51 になるが、それらを入れるものがない。
- `.gitattributes` が無かった。`core.autocrlf=true` で clone すると `install.sh` の 1 行目は `#!/usr/bin/env bash` の後に CR（Windows が行末に足す余分な文字）が付く。すると OS がインタープリタを見つけられず、スクリプト自身の CRLF 検査は動かない。その検査の案内も BSD の `sed` だけが受け付ける `sed -i ""` だった。
- `install.sh`、Compose（一つのファイルから多くのコンテナを起こす Docker の道具。[REF-01](../reference/REF-01_Glossary.md)）、macOS、Windows、arm のランナーを動かすワークフローがなかった。SPEC-02 §8 の Windows の CI（自動で動く検査。[REF-01](../reference/REF-01_Glossary.md)）ビルドと SPEC-04 §8 の amd64（普通の PC やサーバーの CPU の種類。[REF-01](../reference/REF-01_Glossary.md)）ビルドは存在しなかった。

### 2. 決定

1. **スクリプトは三つ、判断の道筋は一つ。** `installer/install-ubuntu.sh`・`installer/install-macos.sh`・`installer/install-windows.ps1` はホストの準備だけを行う。どれも最後に `installer/install.sh` を実行し、ほかの引数はそのまま渡す。Windows は WSL2（Windows の中で Linux を動かす仕組み。[REF-01](../reference/REF-01_Glossary.md)）の中の `install-ubuntu.sh` を通ってそこへ至る。OS の違いを `grdm-dev` に持ち込まない。
2. **`sudo` はここだけで認める。** `install.sh` と `grdm-dev` は引き続き `sudo`（コンピュータの管理者としてコマンドを動かす仕組み）を必要としない。前提条件スクリプトは同意の後に使ってよい。
3. **同意。** 判定は読むだけである。各スクリプトは変更点を先に示し、一度尋ねる。`docker` グループへの追加は管理者権限と同等なので、別に尋ねる。`--yes`（Windows は `-Yes`）は同意を先に与える。端末が無く `--yes` も無ければ終了 2 で止まる。`--dry-run`（`-DryRun`）は予定を表示するだけで何も変えない。
4. **終了コード。** `messages.tsv` の 2・10・11 を使い回し、番号を増やさない。
5. **信頼できる配布元だけを使い、ダウンロードをシェルへ流し込まない。**
   - Ubuntu: Docker の apt（Ubuntu のパッケージ導入の道具）リポジトリ。署名鍵は指紋が `9DC8 5822 9FC7 DD38 854A E2D8 8D81 803C 0EBF CD88` のときだけ受け入れる。Trivy 0.75.0 と gitleaks 8.21.2 は GitHub のリリースから取り、スクリプトに固定した SHA-256（ファイルの指紋）との一致を確かめて `~/.local/bin` に置く。
   - macOS: Homebrew（macOS のパッケージ管理の道具）の formula を使い、bottle の検証は Homebrew が行う。Homebrew 自体はスクリプトでは入れない。公式の一行の導入方法がダウンロードをシェルへ流し込むからであり、署名付きの `.pkg` を案内する。
   - Windows: Microsoft の `wsl.exe`。Docker Desktop は検出するだけで入れない。ライセンスは利用者が判断することだからである。macOS も同じである。
6. **clone を `/mnt/c` に置かない。** `install-windows.ps1` は WSL のホームの下のフォルダ名一つだけを受け付け、`install-ubuntu.sh` は WSL の中で `/mnt/` の下のチェックアウトを拒む。
7. **トークン。** 統合リポジトリは非公開である。スクリプトは git に権限を与える方法（`gh auth login` の後に `gh auth setup-git`）を案内するだけで、トークンを尋ねず、読まず、保存しない。
8. **改行。** `.gitattributes` はシェルスクリプト、Dockerfile、Linux コンテナで動くファイルの改行を LF に固定する。`* text=auto` は旧いファイルを書き換えてしまうので、明示の一覧にする。CRLF の案内は macOS・Ubuntu・WSL で動く `perl -pi -e` に改めた。
9. **CI。** `installer-prereq-lint.yml` はすべての PR で動く。`bash -n`、shellcheck（シェルスクリプトの誤りを見つける道具）、`windows-latest` での PowerShell パーサー、各スクリプトの dry run である。`installer-full.yml` は `workflow_dispatch` のみ（手で起動する）で、`ubuntu-24.04` と `ubuntu-24.04-arm` で `minimum` の完全な導入を行う。リポジトリのシークレット `GRDM_INTEGRATION_READ_TOKEN`（所有者が作る読み取り専用のトークン）を読み、一つの段の環境に置いた認証ヘルパーで git に渡すので、ディスクには書かれない。SPEC-04 §8 の amd64 ビルドは、このワークフローを手で動かすことで満たす。**保留中:** 二つのワークフローと `.github/scripts/Test-PowerShellSyntax.ps1` は、`workflow` スコープを持つトークンでの push をブランチ `feat/per-os-installers` で待つ。

### 3. 検討した選択肢

```toon
options[4]{option,decision_path,risk,chosen}:
  A,"案内を良くするだけ（現状）",一つ,"新しい利用者が毎回同じ手作業を繰り返す。Windows は対応しないまま",いいえ
  B,"OS の準備を grdm-dev に入れる",一つだが混在,"grdm-dev に sudo が要り SPEC-02 §1 を破る。Python が先に要る",いいえ
  C,"全 OS 共通のスクリプト一つ",一つ,"PowerShell と bash は一つのファイルを共有できない。Windows はどのみち外から WSL を動かす",いいえ
  D,"install.sh で終わる OS ごとの薄いスクリプト（本 ADR）",一つ,"小さなスクリプト三つの保守が要る。完全な証明は所有者の実機だけができる",はい
```

### 4. 影響

- 対応 OS の新しい開発者は、コマンド一つと、スクリプトが名指しする手作業だけで済む。
- Docker の署名鍵の指紋と四つの SHA-256 は、版を変えるときに手で更新する。これは意図したことである。
- 手動のワークフローは、既定のブランチに入ってからでないと GitHub で起動できない。

<a id="ja-limits"></a>
### 5. ホスト型ランナーでは証明できないこと

| 主張 | GitHub ホスト型ランナーでの状況 |
|---|---|
| Docker の apt リポジトリからの Docker Engine の導入 | ランナーのイメージに Docker 27 以上があると、スクリプトは飛ばすので試されない。**まっさらな Ubuntu 24.04 arm64 の仮想マシンで実証済み**（[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)）。amd64 はまだまっさらな機械が要る。 |
| `windows-latest` での WSL2 | **未検証。** WSL2 に要る入れ子の仮想化（仮想マシンの中の仮想マシン）はこのランナーでは疑わしく、完全な実行は試していない。CI はスクリプトの解析と dry run だけを行う。 |
| UAC の確認、WSL 有効化後の再起動、最初の利用者の作成、Docker Desktop の WSL 連携 | 人と実機の Windows 11 が要る。UAC は管理者権限を求める Windows の確認画面である。 |
| macOS と Docker Desktop | ホスト型の macOS ランナーには Docker エンジンが無いので、CI は dry run のみ。証拠は引き続き Mac Studio での M2 受入である。 |
| arm64 の Ubuntu での amd64 エミュレーション | **仮想マシンで実証済み**（[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md)）。Ubuntu の `qemu-user-static` 8.2.2 は落ちたので、スクリプトはダイジェストで固定した `tonistiigi/binfmt` イメージから QEMU を登録する。再起動をまたいでは残らない。 |

SPEC-02 §8 の Windows の「CI ではビルド確認のみ」という記述は取り下げる。CI が確かめるのは Windows のスクリプトの構文と dry run だけである。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Prerequisite | Something that must already be in place before a step can work. | ある段が動く前に揃っていなければならないもの。 |
| Consent | The user saying yes before a change is made. | 変更の前に利用者が「はい」と言うこと。 |
| Dry run | A practice run that only says what would happen. | 何が起きるかを言うだけの予行演習。 |
| Fingerprint | A short value that identifies one key or file exactly. | 一つの鍵やファイルを正確に見分ける短い値。 |
| CRLF / LF | The two ways of ending a line: Windows uses CRLF, Linux and macOS use LF. | 行の終わり方の二種類。Windows は CRLF、Linux と macOS は LF。 |
| BOM | Invisible bytes at the start of a file that say how its text is encoded. | ファイルの先頭にある、文字の符号化を示す見えないバイト。 |
| Hosted runner | A temporary machine that GitHub lends to run CI. | CI を動かすために GitHub が貸してくれる一時的な計算機。 |
