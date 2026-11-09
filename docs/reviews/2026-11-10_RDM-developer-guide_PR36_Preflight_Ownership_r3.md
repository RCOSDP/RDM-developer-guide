# PR36 Preflight and ownership review r3 / 事前検査と所有者設定のレビュー r3

> **Summary:** Changes requested at `46bccc0`: reset and mount rejection fixes are present, but the ownership exception still permits inaccessible descendants and the new write probe can truncate existing data.
> **概要:** `46bccc0` は要修正。reset と mount 拒否の修正を確認したが、所有者例外はアクセス不能な子孫を見逃し、新規書込検査は既存データを切り詰め得る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** writing at a volume root does not prove access to its descendants, and a probe must never reuse an existing filename. ／ ボリューム直下への書込みは子孫へのアクセスを証明せず、検査は既存のファイル名を再利用してはならない。
- Applies to: [PR #36](https://github.com/RCOSDP/RDM-developer-guide/pull/36), head `46bccc00b3c417580f5e7bf36652e97fb2195899`; REV（担当レビュワ, Codex Astra）.
- Related: [r2](2026-11-10_RDM-developer-guide_PR36_Preflight_Ownership_r2.md) · [Review index](README.md) · [SPEC-02](../spec/02_installer_cli.md) · [SPEC-06 §8](../spec/06_documentation_conventions.md#english).
- Used by: PR #36 remediation and subsequent review.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and findings

**Changes requested.** Read r2, reviewed `4cf3a22..46bccc0` and surrounding implementation, and confirmed the open PR head with `gh pr view`. Two code issues remain; unperformed hardware startup tests are not the reason for this verdict.

1. **R3-01 [MEDIUM; R2-03 partially open] The allowlist fallback checks only the root's usability.** [compose.py](../../installer/grdm_dev/compose.py) lines 443–444 returns before inspecting descendants whenever the top chown is ineffective and the filesystem name matches `virtiofs`, `fakeowner`, `fuse.grpcfuse`, `fuse.sshfs` or `9p`. Lines 458–461 test only a file directly under that root. An independent invocation of the existing shell/filesystem model used a root at `0:0` mode `0777`, a private child at `999:999` mode `0700`, and its file at `999:999` mode `0600`, with ineffective chown. `FS_TYPE=ext4` correctly exited 1; `FS_TYPE=9p` exited 0, left the private tree unchanged and delegated to the access check. A uid-1000 root write is allowed by `0777`, while that uid cannot traverse the child. Thus an incorrect allowlist assumption can pass both stages without detecting the unusable data; the logged exception is visible, but the access failure is silent. This is a model counterexample, not a claim to have measured a particular 9p backend. Verify required access to existing descendants as the actual writer without modifying their contents, or refuse the exception unless the backend/access contract is established sufficiently to exclude this case. Add the writable-root/inaccessible-child regression. An unlisted filesystem with an ineffective top chown now fails correctly, and normal file and directory hand-back results are read back correctly.

2. **R3-02 [MEDIUM; regression] The write probe may destroy pre-existing data.** [compose.py](../../installer/grdm_dev/compose.py) line 461 runs `: > "$v/.grdm-write-probe"` and then removes that fixed path. An existing regular file is truncated and removed; an existing symlink is followed and its writable target truncated before the link is removed. A temporary-directory probe executing the generated shell, changing only its `/volumes/` prefix to the temporary directory, placed this symlink onto a sentinel containing `KEEP`: the command exited 0, the sentinel became zero bytes, and the symlink disappeared. No Docker or application data was used. This also applies to a target in the same mounted volume and needs no concurrent attacker. Use exclusive creation of a fresh temporary file (for example `mktemp` in the volume) and cleanup only the newly created file; cover both existing regular files and symlinks.

### r2 closure assessment

- **R2-01: closed within the documented snapshot boundary.** `volume_root_identity` records device, inode and file type using `lstat`. `run_reset` compares identity and repeats path validation before down, after down before wiping, and after wiping before host removal. The substitution tests reject symlinks, changed directory identities and newly appearing mounts. If the root disappears after down, host deletion is skipped. SPEC-02 explicitly assumes no concurrent mutation and documents the remaining check/use race; same-inode directory replacement is not atomically excluded. No stronger atomic guarantee is claimed.
- **R2-02: closed for the stated host mount-table model.** Linux parses and decodes `/proc/self/mountinfo`; macOS parses `/sbin/mount` and accommodates the Data prefix. Mounts at runtime, volumes, and any depth below volumes are refused, including same-device binds. Read failure returns `None` and refuses. Tests cover depth, boundaries, escapes and unreadable tables. This reads the host process's mount namespace; no real mount experiment was performed.
- **R2-03: partially closed; R3-01 remains.** File verification and per-directory read-back catch silently ineffective chown, and a no-progress private-directory pass fails. The UID 1000/999 checks drop all capabilities and wait for ownership; current profile writers, including the shared-volume unoconv, wait for the relevant check. Unlisted/unknown filesystem mismatches fail. The allowlist's fallback is still insufficient when the root is writable but an existing descendant is inaccessible. The newly added check also introduces R3-02.
- **R2-04: closed for explicit mount-denial diagnostics.** Engine output matching mount denial, unshared paths, invalid mounts or a missing bind source is a prerequisite problem even on exit 125, and doctor returns 13. The denied-mount regression passes. Inconclusive image/network failures still warn, and the explicit override remains reported.

### Validation and limits

All required commands completed with exit **0**:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
PYTHONPATH=installer python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
```

Installer: 478 tests, 30.224 seconds, 10 skipped. Tools: 92 tests, 3.052 seconds. Documentation: 104 checked, 8 exempt, 22 warnings. Manifest/policy: zero findings, 598 scanned, 63 non-UTF-8 skipped. The new untracked r3 document is additionally checked directly with `tools.docs_check.check_file`, since the standard check enumerates tracked files.

Independent probes used only temporary files and the existing filesystem model. No grdm-dev stack mutation, Docker command, install/up/down/reset, credential-file access, commit, push, approval, merge or closure was performed. Real Linux, WSL2 and Docker Desktop startup remain unverified and are deferred to the later workflow_dispatch and owner hardware; that stated limit is not a blocker in this review. Fix R3-01 and R3-02 and add regressions before passing the code review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正（changes requested）。** r2、`4cf3a22..46bccc0` と周辺実装を読み、`gh pr view` で open の PR head を確認した。コード上の2点が残る。実機起動未検証を理由にした判定ではない。

1. **R3-01 [MEDIUM; R2-03 一部未解決] allowlist 例外は直下の使用可否しか確認しない。** [compose.py](../../installer/grdm_dev/compose.py) 443–444 行は最上位 chown が無効で filesystem 名が `virtiofs`、`fakeowner`、`fuse.grpcfuse`、`fuse.sshfs`、`9p` なら子孫を調べず戻り、458–461 行は直下のファイル作成だけを試す。既存のシェル/filesystem 模型を独立に呼び出し、root を `0:0`・`0777`、private 子ディレクトリを `999:999`・`0700`、そのファイルを `999:999`・`0600`、chown を無効にした。`FS_TYPE=ext4` は正しく1で終了したが、`FS_TYPE=9p` は0で終了し private ツリーを残してアクセス検査へ委ねた。uid1000 は `0777` の直下に作成できる一方、子へ入れない。allowlist の想定が誤っている場合、両段を通過して既存データのアクセス不能を見逃す。例外のログは出るがアクセス失敗は黙って通る。これは模型による反例であり、特定の9p実装を実測した主張ではない。実際の書き手として既存子孫に必要なアクセスを内容変更なしで検査するか、この場合を排除できる backend/access 契約が確立するまで例外を拒否する。直下は書込可・子はアクセス不可の回帰試験を追加する。未登録 filesystem の無効な最上位 chown は正しく失敗し、通常経路のファイルとディレクトリの返却も読み返している。

2. **R3-02 [MEDIUM; 新規退行] 書込検査が既存データを破壊し得る。** [compose.py](../../installer/grdm_dev/compose.py) 461 行は固定名に `: > "$v/.grdm-write-probe"` を実行し、そのパスを削除する。既存の通常ファイルなら切り詰めて削除し、symlink なら書込可能なリンク先を切り詰めてからリンクを消す。一時ディレクトリで生成シェルの `/volumes/` 接頭辞だけを変更し、`KEEP` を入れた sentinel へのリンクを置く独立検査を実行した。終了0で sentinel は0バイトになり、リンクも消えた。Docker やアプリの実データは使っていない。同じ volume 内のリンク先でも成立し、同時変更は不要。volume 内で `mktemp` などの排他的な新規作成を使い、自分が作成したファイルだけを片付ける。既存通常ファイルと symlink の両方を回帰試験する。

### r2 の解決状況

- **R2-01: 文書化した snapshot 境界内で解決。** `volume_root_identity` は `lstat` の device/inode/type を記録し、`run_reset` は down 前、down 後の wipe 前、wipe 後のホスト削除前に同一性とパスを再検証する。差し替え試験はリンク、別ディレクトリ、新しい mount を拒む。down 後に root が消えればホスト削除は省略する。SPEC-02 は同時変更をしない前提と検証から使用までの競合を明記しており、同じ inode を再利用するディレクトリ差し替えの原子的排除までは保証しない。
- **R2-02: 示したホスト mount 表モデル内で解決。** Linux は `/proc/self/mountinfo` と escape、macOS は `/sbin/mount` と Data 接頭辞を扱う。runtime/volumes 自体と volumes 以下の任意の深さの mount を、同じ device の bind を含め拒否する。読取失敗は `None` で拒否。深さ・境界・escape・読取不能の試験を確認した。ホストプロセスの mount namespace を読む実装であり、実 mount 実験はしていない。
- **R2-03: 一部解決、R3-01 が残る。** ファイル検査と各ディレクトリの読み返しは無効な chown を検知し、private ディレクトリの処理が進まない場合も失敗する。UID1000/999 の検査は capability をすべて除去して所有者設定を待ち、現 profile の書き手と共有 volume の unoconv は対応する検査を待つ。未登録/不明 filesystem の不一致は失敗する。ただし直下は書込可で既存子孫がアクセス不能なら例外は不十分。検査の追加は R3-02 も導入している。
- **R2-04: 明示的な mount 拒否診断について解決。** mount 拒否、非共有パス、不正 mount、bind 元不在を示す engine 出力は125でも前提失敗となり doctor は13を返す。拒否の回帰試験は合格。イメージ/ネットワークの判定不能は警告、明示 override は報告に残る。

### 検証と限界

英語側に記載した4コマンドはすべて終了 **0**。installer は478件・30.224秒・10 skip、tools は92件・3.052秒、文書は104件・8免除・22警告、manifest/方針は指摘0件・598走査・非UTF-8の63件を省略した。通常の検査は追跡済みファイルだけを列挙するため、新規未追跡 r3 も `tools.docs_check.check_file` で直接検査する。

独立検査は一時ファイルと既存模型だけを使用した。grdm-dev スタック変更、Docker コマンド、install/up/down/reset、資格情報ファイル参照、commit、push、approve、merge、close はしていない。実 Linux・WSL2・Docker Desktop の起動は未検証で、後続 workflow_dispatch と所有者の実機へ委ねる。この明示された限界自体はブロッカーにしない。コードレビュー合格には R3-01・02 の修正と回帰試験が残る。
