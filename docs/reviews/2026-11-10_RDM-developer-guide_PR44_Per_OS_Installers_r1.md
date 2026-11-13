# PR44 Per-OS installers review r1 / OS 別インストーラーレビュー r1

> **Summary:** REV reviewed PR #44 at c2607e6. Changes are requested for path validation and the ZAP permission boundary.
> **概要:** REV は PR #44 の c2607e6 を確認した。パス検証と ZAP の権限境界について修正を求める。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** passing dry-run tests does not prove filesystem safety when mount names are escaped, paths are symlinks, or parent permissions differ from the assumed mode. ／ dry run の合格だけでは、mount 名のエスケープ、パスのシンボリックリンク、親の権限が想定と異なる場合の安全性は証明できない。
- Applies to: [PR #44](https://github.com/RCOSDP/RDM-developer-guide/pull/44), `feat/per-os-installers-split`, head `c2607e60d3b9459d8a9132c662a72d838acb6f17`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）; 2026-11-10.
- Parent index / 親索引: [Reviews](README.md).
- Related: [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-08](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md) · [DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md).
- Used by / 利用先: PR #44 revision and coordinator review / PR #44 の修正と統括レビュー。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** Reviewed the four prerequisite scripts, attributes, Python changes and their tests, ADR-08, SPEC-02/04, environment guidance and DEMO-21 evidence against `origin/develop`. Work used a clean scratch clone. No commit, push, approval, merge, stack operation or inspection of a real runtime credential file was performed. Tests used temporary fixtures; focused reproductions used dummy credentials and stub commands only.

### Required changes

**R1 — P2: Decode mount-table paths before testing credentials.** In `installer/install-ubuntu.sh:89–95`, `read -r` preserves the kernel's `\040` encoding, but the existence test treats it as literal filename characters. A shared home containing a space therefore bypasses exit 10. A fixture with a real dummy `.config/gh/hosts.yml` under `host home` and an escaped virtiofs mount entry continued into the stub apt actions and eventually exited 11, without the credential refusal. Decode the mount-field escapes safely and test spaces, backslashes and the supported filesystem types. Keep checking existence only. The check also covers only four names directly below a mount root; describe that limit rather than implying recursive detection of all credentials.

**R2 — P2: Resolve WSL destinations before cloning or invoking the installer.** `installer/install-windows.ps1:234–246` checks the textual HOME and accepts an existing target directory; `installer/prereq-lib.sh:22` computes a logical path with `pwd`, which `install-ubuntu.sh:77–79` compares with `/mnt/*`. A home or target symlink to `/mnt/c/...` passes these textual checks. A scratch alias confirmed that PREREQ_ROOT retains the symlink spelling while `pwd -P` points elsewhere. The Windows bootstrap can consequently clone on the Windows disk before a downstream permission probe rejects it. Resolve the physical home and existing target, validate the physical parent for a new target, and apply the same physical-path guard in Ubuntu. Add symlink cases; the current test only asserts that the guard text exists. This is static analysis plus a local path reproduction, not a Windows execution claim.

**R3 — P2: Enforce the parent permission boundary before making ZAP work directories world-writable.** `installer/grdm_dev/scan.py:905–917` uses `mkdir(exist_ok=True)` and `chmod(0777)` without checking that runtime is an owned, real 0700 directory. Normal `secrets init` establishes 0700, but `scan --dynamic` does not enforce it and an existing/copied runtime can be 0755. A direct stubbed run confirmed runtime remained 0755 while each work directory became 0777. Other local users can then write into a known work directory during the scan, substituting report contents or report symlinks. A genuine 0700 ancestor prevents this cross-user access; 0777 is acceptable only while that invariant actually holds. Validate ownership, physical directory identity and permissions before widening access; create work directories exclusively with unpredictable names and reject output symlinks. Add permissive-parent and pre-existing-symlink tests. The current `nosemgrep` rationale assumes rather than establishes the invariant.

### Other review observations

Consent precedes the planned sudo, administrator and package operations, with a separate root-equivalence warning for docker-group membership. `--yes` is explicit consent. Existing prerequisites are skipped, unsupported platforms fail, and downloads are not piped into a shell. Docker's apt key requires exactly one primary key and the pinned fingerprint; its source uses Signed-By. Scanner archives are checked against embedded SHA-256 values before extraction. macOS delegates verification to Homebrew and Windows uses Microsoft WSL distribution installation. Upstream artifact bytes and signatures were not independently downloaded during this review.

The binfmt image is digest-pinned identically in the script and doctor hint. The one-shot commands use `--rm`, install only amd64 and uninstall only qemu-x86_64, with no host-directory or Docker-socket mount. They still grant full privileged-container access and change a host-global kernel registration; this is not capability-minimal isolation. The plan explains sudo, the purpose, replacement and reboot lifetime, but should explicitly name the privileged-container trust and effect on other users' workloads. ADR-08 remains Proposed for owner approval. Clarify the environment guide's blanket privileged prohibition as applying to application services, with the narrowly documented host-setup exception.

The longer Linux arm64 timeout preserves explicit overrides and is limited to profiles with amd64 services. The libatomic1 addition and Linux Playwright dependency guidance match the documented failure. Tokens are only discussed as guidance; the shared-folder guard checks existence, not contents. The attributes explicitly protect Linux-executed files from CRLF conversion.

DEMO-21's final results record 12 passed, zero failed/error/skipped and pytest exit 0. Its earlier failed runs remain visible. The 531-object, uid-2001 database migration and successful installation are author-recorded VM evidence, not independently rerun here. Ubuntu amd64 and real Windows remain unverified; deferred workflows and their helper are explicitly documented as pending owner credentials. They are not credited as CI evidence. Bilingual layout and Proposed status are present; documentation checks pass with warnings.

### Validation

Commands ran from the scratch clone root using system `/usr/bin/python3` 3.9.6. Results are review observations, not a mirror of a canonical dataset.

```toon
checks[6]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","632 tests; 10 skipped; OK",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 tests; OK",0
  "/usr/bin/python3 tools/docs_check.py","151 files; 8 exempt; 38 warnings; passed before adding review",0
  "/usr/bin/python3 tools/manifest_check.py","passed; zero policy findings",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","passed",0
  "command -v shellcheck","not installed; not run",1
```

PowerShell was unavailable, so no live parser or WSL execution was claimed. Full logs are retained beside the clone in `/tmp/pr44-rev-DJJ5gv/`. Re-run focused tests and obtain owner-platform evidence after fixes; no runtime installation is required to reproduce R1–R3.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**Changes requested（修正要求）。** 四つの前提条件スクリプト、属性、Python の変更と試験、ADR-08、SPEC-02/04、環境手引き、DEMO-21 の証跡を `origin/develop` と比較した。作業は scratch のクリーンな clone で行った。commit・push・承認・merge・スタック操作・実際の runtime 資格情報ファイルの閲覧はしていない。試験は一時 fixture を使い、個別再現はダミーの資格情報とスタブだけを使った。

### 必要な修正

**R1 — P2: 資格情報を調べる前に mount 表のパスを復号する。** `installer/install-ubuntu.sh:89–95` の `read -r` はカーネルの `\040` を保持するが、存在検査はそれを文字どおりのファイル名として扱う。共有ホーム名に空白があると終了 10 を通過する。`host home` の下にダミーの `.config/gh/hosts.yml` を置き、virtiofs の mount 行をエスケープした fixture は、資格情報の拒否を出さずに apt のスタブへ進み、最終的に終了 11 になった。mount フィールドのエスケープを安全に復号し、空白・バックスラッシュ・対応するファイルシステムを試験すること。内容は読まず存在確認を維持すること。また検出対象は mount 直下の四つの名前だけなので、全資格情報を再帰的に検出するとの印象を避け、この制限を明記すること。

**R2 — P2: clone や実行の前に WSL の実際の配置先を解決する。** `installer/install-windows.ps1:234–246` は HOME の文字列を検査して既存の対象を受け入れる。`installer/prereq-lib.sh:22` は `pwd` で論理パスを作り、`install-ubuntu.sh:77–79` はそれを `/mnt/*` と比較する。ホームや対象が `/mnt/c/...` へのシンボリックリンクなら、この文字列検査を通る。scratch の別名で、PREREQ_ROOT はリンク名を維持し、`pwd -P` は別の実体を指すことを確認した。後段の権限検査が拒否する前に、Windows の起動処理が Windows ディスクへ clone できる。ホームと既存対象の実体を解決し、新規対象は親の実体を検査すること。Ubuntu 側も実体パスを検査し、リンクの試験を加えること。現在の試験は検査文字列の存在を assert するだけである。これは静的解析とローカルのパス再現であり、Windows 実機試験ではない。

**R3 — P2: ZAP 作業ディレクトリを全員書込み可にする前に親の権限境界を保証する。** `installer/grdm_dev/scan.py:905–917` は、runtime が実行者所有の実ディレクトリで 0700 かを確認せず、`mkdir(exist_ok=True)` と `chmod(0777)` を行う。通常の `secrets init` は 0700 にするが、`scan --dynamic` はそれを強制せず、既存・コピー済みの runtime は 0755 の場合がある。直接のスタブ実行で runtime が 0755 のまま各作業ディレクトリが 0777 になることを確認した。この場合、別のローカル利用者がスキャン中の既知の作業ディレクトリへ書込み、報告の内容や報告ファイルのリンクを差し替えられる。実際に 0700 の祖先があれば利用者間のアクセスを防げるので、0777 を許せるのはその条件が成立する間だけである。権限を広げる前に所有者・実体・モードを検証し、予測できない名前で排他的に作業ディレクトリを作り、出力リンクを拒否すること。親が公開モードの場合と既存リンクの試験を加えること。現在の `nosemgrep` の理由は条件を保証せず仮定している。

### その他の確認

予定された sudo・管理者・パッケージ操作の前に同意を求め、docker グループへの追加では管理者と同等になるとの警告を別に示す。`--yes` は明示的な同意である。既存の前提条件は飛ばし、未対応ホストは拒否し、ダウンロードをシェルへ流し込まない。Docker の apt 鍵は主鍵一つと固定指紋の一致を要求し、配布元は Signed-By を使う。スキャナーは展開前に固定 SHA-256 を検査する。macOS は Homebrew の検証を使い、Windows は Microsoft の WSL 配布機構を使う。今回は上流の配布物や署名を独立にダウンロードして照合していない。

binfmt のイメージはスクリプトと doctor の案内で同じダイジェストに固定されている。一時コマンドは `--rm` を使い、amd64 だけを登録し、qemu-x86_64 だけを解除する。ホストのディレクトリや Docker ソケットの mount はない。ただしコンテナには完全な privileged 権限を与え、ホスト全体のカーネル登録を変えるため、最小 capability による隔離ではない。計画は sudo・目的・置換・再起動までの寿命を説明するが、privileged コンテナを信頼することと他の利用者の処理への影響も明示すべきである。ADR-08 は所有者承認待ちの Proposed のままである。環境手引きの全面的な privileged 禁止はアプリケーションサービスへの規則と明確にし、ホスト準備の狭い例外を記録するとよい。

Linux arm64 の待ち時間延長は明示の上書きを維持し、amd64 サービスを持つプロファイルに限定される。libatomic1 と Linux 向け Playwright 依存関係の案内は記録された失敗に対応する。トークンは案内だけで扱い、共有フォルダの検査は内容を読まない。属性は Linux で実行するファイルを明示的に CRLF 変換から保護する。

DEMO-21 の最終結果は 12 件合格、失敗・エラー・skip がゼロ、pytest 終了 0 を記録している。以前の失敗も残されている。uid 2001・531 対象の DB 移行と導入成功は著者の VM 記録であり、今回再実行していない。Ubuntu amd64 と Windows 実機は未検証で、ワークフローと補助ファイルは所有者の資格情報待ちと明記されているため、CI の証拠には数えない。英和構成と Proposed 状態を確認し、文書検査は警告付きで合格した。

### 検証

clone のルートからシステムの `/usr/bin/python3` 3.9.6 で実行した。結果はレビュー時の観測であり、別の正本データの写しではない。

```toon
checks[6]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","632 件・10 skip・合格",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 件・合格",0
  "/usr/bin/python3 tools/docs_check.py","レビュー追加前 151 ファイル・8 免除・38 警告・合格",0
  "/usr/bin/python3 tools/manifest_check.py","合格・ポリシー検出ゼロ",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","合格",0
  "command -v shellcheck","未導入・実行せず",1
```

PowerShell も無く、パーサーや WSL の実行はしていない。ログは clone と同階層の `/tmp/pr44-rev-DJJ5gv/` に保存した。修正後は対象試験と所有者の実機検証を行うこと。R1〜R3 の再現に実環境の導入は不要である。
