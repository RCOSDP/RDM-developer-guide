# PR44 Per-OS installers review r2 / OS 別インストーラーレビュー r2

> **Summary:** REV requests changes: trailing newlines still bypass the shared-credential check, and a FIFO report blocks ZAP report validation.
> **概要:** REV は修正を要求する。共有パス末尾の改行で資格情報検査を回避でき、FIFO の ZAP 報告では検証が停止する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** decoding an escaped path is insufficient if command substitution then strips its trailing newlines; validating a file after opening it is insufficient if opening can block. ／ 復号してもコマンド置換が末尾改行を消せばパスは保たれず、open 自体が停止する場合は open 後のファイル種別検証では足りない。
- Applies to: [PR #44](https://github.com/RCOSDP/RDM-developer-guide/pull/44), diff `c2607e6..237387f`, head `237387f8767ddfc500e1ba71c1ab8fe50a4c42f2`.
- Reviewer / レビュワ: REV（担当レビュワ, Codex Astra）.
- Parent index / 親索引: [Reviews](README.md).
- Related: [r1](2026-11-10_RDM-developer-guide_PR44_Per_OS_Installers_r1.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by / 利用先: PR #44 revision and coordinator review / PR #44 の修正と統括レビュー。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and required changes

**Changes requested.** Reviewed the requested revision in a clean detached clone. R1 is only partially closed; R2's symlink fix passes the exercised cases; R3's permission and symlink protections pass, but its new regular-file reader has a blocking special-file case.

**R2-01 — P2: Preserve trailing newlines in decoded mount paths.** At `installer/install-ubuntu.sh:105`, `mnt="$(decode_mount_field ...)"` removes all trailing newline bytes from the decoded result. A real fixture directory named `host` followed by a newline, containing a dummy `.netrc`, is represented in the mount table as `host\012`. The script checks `host/.netrc` instead. A non-dry invocation under stub commands bypassed exit 10, reached stub sudo, and eventually exited 11 for all six supported filesystem names. Space, tab, interior newline and a literal backslash followed by `012` were correctly detected; one and two trailing newlines were not. Assign the decoded value without lossy command substitution, or append/remove a non-newline sentinel. Add regression cases for trailing `\012` and repeated trailing `\012`; decoding must remain single-pass for `\134012`.

**R2-02 — P2: Open special reports without blocking before checking their type.** At `installer/grdm_dev/scan.py:926`, `os.open(path, O_RDONLY | O_NOFOLLOW)` blocks indefinitely on a FIFO with no writer. The `fstat` regular-file check at lines 931–933 is never reached. An isolated child calling `_read_zap_report` on a temporary FIFO exceeded two seconds and was terminated by the test harness. A scanner-produced FIFO therefore stalls completion rather than reporting an incomplete scan, contrary to the updated SPEC-03 guarantee that nonregular reports are refused. Use a nonblocking, no-follow open followed by descriptor type validation, retaining refusal and cleanup; add a bounded FIFO test. This is a robustness defect, not a claim that another host user can cross the verified private parent.

### Closure evidence and boundary variants

R1 now correctly decodes spaces, tabs and backslashes and documents its four-name, mount-root-only scope. A synthetic shared-filesystem bind entry with a space in its mount point was refused with exit 10. The implementation reads `/proc/mounts`, not `/proc/self/mountinfo`; the fixtures used its actual four-field parsing contract.

R2 resolves HOME and an existing target with `pwd -P`, validates before cloning, and uses the canonical target thereafter. Nested links with both absolute and relative destinations into the simulated Windows root exited 10. Replacing the original logical checkout alias after validation still executed the original safe canonical checkout. The repository tests also cover direct and symlinked Ubuntu entry points and an accepted Linux destination. `-Directory` is restricted to one folder name, so a new target's parent is the validated physical HOME.

A physical-path prefix is not a filesystem-origin check: a Windows filesystem bind-mounted outside `/mnt` would retain that outside mount-point pathname under `pwd -P`. This is a static limitation, not an independently reproduced Linux bind-mount result or an additional proven regression. Actual bind mounts and WSL execution were unavailable on this Darwin host; no host mounts or Docker state were changed.

R3 rejects a 0755 runtime before creating any 0777 work directory or running ZAP, uses exclusive unpredictable directories, and rejects report symlinks. Absolute, relative, nested and dangling report symlinks all returned a refusal. Replacing a regular report with a symlink immediately at `os.open` was also refused by `O_NOFOLLOW`. Existing tests verify scan exit 51, cleanup and that planted report findings are not accepted.

A deliberate same-owner chmod from 0700 to 0755 between validation and use allowed creation of a 0777 work directory and a successful stubbed scan. Thus validation is a snapshot, not an invariant maintained against concurrent owner changes. No cross-user exploit is claimed: under the ordinary owner-controlled checkout and private runtime, an unrelated user cannot perform that chmod. Parent-path replacement by an actor able to rename checkout ancestors and bind aliases remain outside the demonstrated protection. Treat the owned checkout/ancestors as a precondition; do not claim general race-proof filesystem isolation.

### Validation and reproduction

System `/usr/bin/python3` 3.9.6 on Darwin was used. Results are observations, not a canonical dataset mirror. All scanner, installer and credential boundary probes used temporary fixtures and stub runners; no real credential file was inspected. No commit, push, approval, merge, close or grdm-dev stack mutation was performed. PowerShell was not installed, so its native parser and real WSL were not run.

```toon
checks[7]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","640 tests; 10 skipped; OK",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 tests; OK",0
  "/usr/bin/python3 tools/docs_check.py","152 files; 8 exempt; 38 warnings; passed before review",0
  "/usr/bin/python3 tools/manifest_check.py","694 tracked text files scanned; 63 skipped; zero findings",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","passed",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/variants.py","boundary observations including trailing-newline bypass and FIFO timeout",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/mount_variants.py","six filesystem bypasses; bind-table fixture refused",0
```

Scripts and full logs are retained in `/tmp/pr44-rev-r2-RXhzlP/`; clone root is `/tmp/pr44-rev-r2-RXhzlP/repo`. From that root, run the last two commands to reproduce the boundary observations; their exit 0 means the observation harness completed, not that every product case passed. Fix R2-01/R2-02 and rerun the focused probes. Real platform and bind-mount coverage remains outstanding.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と修正要求

**Changes requested（修正要求）。** 指定差分をクリーンな detached clone で確認した。R1 は部分解決、R2 の symlink 修正は今回の試験で合格、R3 の権限・symlink 防御も合格したが、新しい通常ファイル読込み処理には特殊ファイルで停止する問題がある。

**R2-01 — P2: 復号した mount パスの末尾改行を保持すること。** `installer/install-ubuntu.sh:105` の `mnt="$(decode_mount_field ...)"` は復号結果の末尾改行をすべて取り除く。`host` の後ろに改行がある実ディレクトリにダミーの `.netrc` を置き、mount 表に `host\012` と記すと、検査先は `host/.netrc` になってしまう。スタブ環境で dry run を付けずに実行すると、対応する全六種類の filesystem で終了 10 を回避し、sudo スタブへ進んで最終的に終了 11 となった。空白・タブ・途中の改行・文字どおりのバックスラッシュと `012` は検出できたが、末尾の改行一つ・二つは検出できなかった。値を直接代入するか、改行以外の番兵を付けてから除去し、末尾改行を保持すること。末尾 `\012` と連続する末尾 `\012` を回帰試験に加え、`\134012` を二重に復号しない性質も維持すること。

**R2-02 — P2: 特殊な報告ファイルを、種別検証前に停止せず開くこと。** `installer/grdm_dev/scan.py:926` の `os.open(path, O_RDONLY | O_NOFOLLOW)` は書き手のない FIFO で無期限に待つ。931–933 行の `fstat` による通常ファイル検証に到達しない。一時 FIFO を `_read_zap_report` に渡した隔離子プロセスは二秒を超え、試験側が終了させた。スキャナーが FIFO を残すと、不完全なスキャンとして報告せず停止するため、SPEC-03 の「通常ファイルでない報告は拒否」という追加保証を満たさない。nonblocking と no-follow で開いてから descriptor の種別を検証し、拒否と後片付けを維持すること。時間制限付きの FIFO 試験を加えること。これは堅牢性の問題であり、別のホスト利用者が private な親を越えられるという指摘ではない。

### 解決の証拠と境界ケース

R1 は空白・タブ・バックスラッシュを正しく復号し、mount 直下の四つの名前だけを調べる制限を明記した。mount 先に空白を含む共有 filesystem の bind 行を模した fixture は終了 10 で拒否された。実装は `/proc/self/mountinfo` ではなく `/proc/mounts` を読み、fixture も実際の四フィールド解析に合わせた。

R2 は HOME と既存の対象を `pwd -P` で解決し、clone 前に検査して以後は実体の対象を使う。疑似 Windows root に至る多段リンクは、絶対・相対の両方のリンク先で終了 10 となった。検査後に元の論理 checkout 別名を差し替えても、元の安全な実体 checkout が実行された。リポジトリの試験も Ubuntu の直接・リンク経由の起動と Linux 配置の許可を含む。`-Directory` は単一フォルダ名に制限されるため、新規対象の親は検証済みの実体 HOME となる。

ただし実体パスの接頭辞は filesystem の出自を示さない。Windows filesystem を `/mnt` 外に bind mount した場合、`pwd -P` は外側の mount 先を返す。これは静的な制限であり、独立に再現した Linux bind mount の結果や追加の確定した回帰ではない。Darwin ホストのため実 bind mount と WSL 実行はできず、ホスト mount や Docker の状態は変更していない。

R3 は 0755 の runtime を、0777 の作業ディレクトリ作成と ZAP 実行より前に拒否し、予測できない名前で排他的に作業場所を作り、報告 symlink を拒否する。絶対・相対・多段・リンク先のない報告 symlink はすべて拒否された。`os.open` の直前で通常ファイルを symlink に差し替えても `O_NOFOLLOW` が拒否した。既存試験は終了 51、後片付け、植えられた報告の検出結果を受け入れないことも確認している。

同一所有者が検査と使用の間で意図的に 0700 を 0755 に chmod する試験では、0777 の作業ディレクトリが作成され、スタブのスキャンは成功した。検証は一時点の確認であり、所有者の並行変更に対して条件を維持する仕組みではない。通常の所有者管理の checkout と private runtime では無関係な利用者が chmod できないため、利用者間の攻撃を実証したとは扱わない。checkout の祖先を rename できる主体による親パス差替えや bind 別名も、今回証明した保護の外にある。checkout と祖先を所有者が管理することを前提とし、一般的な競合に耐える filesystem 隔離とは主張しないこと。

### 検証と再現

Darwin 上のシステム `/usr/bin/python3` 3.9.6 を使った。以下は観測結果で、正本データの写しではない。境界検査は一時 fixture とスタブを使い、実際の資格情報ファイルは調べていない。commit・push・承認・merge・close・grdm-dev スタック変更はしていない。PowerShell は未導入で、ネイティブの構文解析と実 WSL は未実施である。

```toon
checks[7]{command,result,exit}:
  "PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests","640 件・10 skip・合格",0
  "/usr/bin/python3 -m unittest discover -s tools/tests","93 件・合格",0
  "/usr/bin/python3 tools/docs_check.py","レビュー追加前 152 ファイル・8 免除・38 警告・合格",0
  "/usr/bin/python3 tools/manifest_check.py","追跡対象テキスト 694 件検査・63 skip・検出ゼロ",0
  "bash -n installer/install-ubuntu.sh installer/install-macos.sh installer/prereq-lib.sh installer/install.sh","合格",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/variants.py","末尾改行回避と FIFO timeout を含む境界観測",0
  "/usr/bin/python3 /tmp/pr44-rev-r2-RXhzlP/mount_variants.py","六種類で回避・bind 表 fixture は拒否",0
```

再現スクリプトと全ログは `/tmp/pr44-rev-r2-RXhzlP/`、clone は `/tmp/pr44-rev-r2-RXhzlP/repo` にある。clone ルートから最後の二コマンドを実行すると観測を再現できる。終了 0 は観測用スクリプトが完了した意味であり、製品の全ケースが合格した意味ではない。R2-01/R2-02 の修正後に個別試験を再実行すること。実プラットフォームと bind mount の検証は残っている。
