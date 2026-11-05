# PR30 Wiki Overlay Review r4 / Wiki オーバーレイレビュー r4

> **Summary:** Needs revision: the initializer is corrected, but host-side chmod breaks rendering after ownership transfer.
> **概要:** 要修正。初期化コンテナは直ったが、所有権移転後のホスト側 chmod が再 render を壊す。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** provisioning must distinguish newly created host-owned directories from existing container-owned directories. ／ 準備処理では、新規のホスト所有ディレクトリと既存のコンテナ所有ディレクトリを区別する必要がある。
- Applies to: PR #30, head `ae9c6f02ccf0cc666ec7aabfc8730534275d9906`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r3](2026-11-06_RDM-developer-guide_PR30_Wiki_Overlay_r3.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Needs revision. R2-01 remains open at the provisioning lifecycle level — P1.** The container command now correctly omits chmod, but `installer/grdm_dev/compose.py:857–863` runs `os.chmod(vol_dir, 0o755)` unconditionally for every volume, including existing directories. `mkdir(exist_ok=True)` does not establish ownership. On ordinary rootful Linux bind mounts, after wiki_static_init changes ownership to UID 1000, a non-root installer user with a different UID cannot chmod that directory on the next `compose render`. Even an unchanged 0755 mode requires ownership or CAP_FOWNER. The result is EPERM and an uncaught PermissionError. Other service-owned volume directories are also exposed to this unconditional operation.

Set the intended mode while a newly created directory is owned by the provisioning user; avoid chmod of existing foreign-owned directories that already have the required mode. Define validation and actionable recovery for an existing directory with an unsuitable mode, rather than silently ignoring errors. Restrict mode changes to directories whose permission policy actually requires them. Add a regression for render → initializer ownership transfer → render with a host UID other than 0 or 1000, plus restrictive umask and existing-directory cases. The current same-owner rerender test never transfers ownership and therefore cannot detect this regression. Both ADR-06 halves describe setting mode “when it creates” the directory, but implementation does it on every render; align that wording with the corrected lifecycle.

### Kernel reasoning and rendered output

Linux v6.12 [chown_ok and chgrp_ok in fs/attr.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/attr.c) accept `capable_wrt_inode_uidgid(..., CAP_CHOWN)` regardless of whether the caller owns the inode. With ordinary mapped UIDs/GIDs and a searchable path, root with CHOWN alone can change host ownership to 1000:1000 and repeat that same operation. `setattr_prepare` separately checks `inode_owner_or_capable` for ATTR_MODE; [fs/inode.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/inode.c) requires matching fsuid or mapped ownership plus CAP_FOWNER. CHOWN does not satisfy chmod. These kernel sources were retrieved with `gh api`; no Linux container execution or Docker state changes were performed. Namespace mapping, filesystem and security-module restrictions remain separate conditions.

The rendered command is `set -e; chown 1000:1000 /wiki_static; ls -ld /wiki_static`, with ALL dropped and only CHOWN added. Read-only root filesystem, no-new-privileges, completion dependency, and consumer read-only mounts remain covered by tests. Fresh rendering under umask 077 produced mode 0755; same-owner rendering twice succeeded. A targeted Python mock that raises Linux's expected EPERM only for chmod of the existing wiki_static directory confirmed that rerender propagates PermissionError; this is a control-flow test, not a real ownership-transfer execution test. The initializer itself is now repeatable by kernel reasoning; the complete host workflow is not.

### Validation

Commands were run from the review worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer:installer/tests python3 -m unittest -v test_compose.ComposeRenderTests.test_docker_compose_config_accepts_the_rendered_file test_compose.ComposeRenderTests.test_idempotent_rerun_reports_unchanged
git diff --check
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
```

Observed results, not canonical manifest data:

```toon
validation[5]{check,result,detail}:
  installer,pass,343 tests; 10 skipped at ae9c6f0
  tools,pass,89 tests
  manifest_check,pass,zero findings
  docs_check,pass,86 files; 8 exempt; 19 warnings
  targeted_tests,pass,read-only compose config and same-owner rerender; neither skipped
```

Tools/checker/parser results were obtained at c3bdd0d; the only subsequent change at ae9c6f0 replaces `self.root` with `root` in the new test, verified by diff. The installer suite was rerun successfully at ae9c6f0. The earlier AttributeError in local and Python 3.11/3.12 CI tests is fixed and is not an open finding. The r4 file is checked separately with `docs_check.check_file` because it is untracked. Final CI at ae9c6f0: seven checks pass, including both Python versions; Semgrep fails on the same line 863 finding. The new head’s failed-job log was checked. `git diff --check` and the r4 document check passed. The prior head's Semgrep job failed on the new 0755 chmod at line 863 (`python.lang.security.audit.insecure-file-permissions.insecure-file-permissions`); this is a real gate failure, not proof that directories should use 0644. Resolve the gate with the corrected implementation and a justified narrow exception if needed; directory traversal requires execute permission.

Integration wiring and browser/C4 acceptance remain outside this targeted re-review. No approve, merge, commit, push or Docker state change was performed; only this review record and the requested PR comment were written.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正。準備から再実行までを含めると R2-01 は未解決 — P1。** コンテナ内 chmod は正しく除去されたが、`installer/grdm_dev/compose.py:857–863` は既存も含む全ボリュームへ毎回 `os.chmod(vol_dir, 0o755)` を実行する。`mkdir(exist_ok=True)` は所有権を保証しない。通常の rootful Linux bind mount では wiki_static_init が UID 1000 に変更した後、別 UID の非 root ホスト利用者による次回の `compose render` は chmod できず、EPERM と未捕捉の PermissionError で失敗する。既に 0755 でも所有者または CAP_FOWNER が必要である。他サービスが所有するボリュームもこの無条件操作の対象になる。

新規作成してホスト利用者が所有する間にモードを設定し、必要なモードを満たす他者所有の既存ディレクトリには chmod しないこと。不適切なモードの既存ディレクトリには、エラーの握り潰しではなく検証と具体的な復旧方法を定義すること。モード変更はその権限方針が必要な対象に限定すること。ホスト UID が 0・1000 以外で render → 初期化による所有権移転 → render の回帰試験、および厳しい umask・既存ディレクトリの試験が必要。既存の再 render 試験は所有権を移さないので検出できない。ADR-06 の英和両方は「作るとき」と記すが、実装は毎回実行するため、修正後の動作と一致させる必要がある。

### カーネル規則と出力

Linux v6.12 の [fs/attr.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/attr.c) の chown_ok・chgrp_ok は `capable_wrt_inode_uidgid(..., CAP_CHOWN)` があれば所有者一致を必要としない。通常の ID 対応と探索可能なパスでは CHOWN のみを持つ root がホスト所有から 1000:1000 へ変更でき、同じ chown の再実行もできる。一方 ATTR_MODE は [fs/inode.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/inode.c) の inode_owner_or_capable により fsuid 一致または ID 対応と CAP_FOWNER を必要とする。CHOWN は chmod の権限にならない。ソースは gh api で確認し、Linux コンテナ実行・Docker 状態変更はしていない。名前空間の ID 対応、ファイルシステム、セキュリティ機構の制約は別条件である。

生成コマンドは `set -e; chown 1000:1000 /wiki_static; ls -ld /wiki_static`。ALL drop と CHOWN のみの追加、読取り専用 root filesystem、no-new-privileges、成功終了待ち、利用側の読取り専用 mount を試験で確認した。umask 077 でも新規ディレクトリは 0755 となり、同じ所有者での二回の render は成功した。既存 wiki_static への chmod だけで Linux 相当の EPERM を返す Python mock では PermissionError の伝播を確認した。これは制御フローの試験であり実際の所有権移転試験ではない。初期化コンテナの再実行はカーネル規則上正しいが、ホストを含む一連の処理は再実行できない。

### 検証

コマンドは英語部に記載。最新版 ae9c6f0 の installer は 343 件成功（10 skip）。tools 89 件、manifest 指摘 0、docs 86 ファイル・例外 8・警告 19、個別の読取り専用 compose config と同一所有者再 render は成功し、個別試験は skip なし。tools・checker・parser は c3bdd0d で検証し、その後の変更がテストの `self.root` → `root` 一箇所のみであることを差分確認した。旧 head の AttributeError は修正済みで未解決指摘に含めない。未追跡の r4 文書は docs_check.check_file で別途検査する。

最新版 ae9c6f0 の CI は Python 両版を含む七件成功、Semgrep 一件失敗。最新版の失敗ログも同じ行 863 の指摘と確認した。git diff --check と r4 文書の個別検査は成功。旧 head の Semgrep は新規 chmod 0755 の行 863 を insecure-file-permissions として拒否した。これは検査ゲートの失敗だが、ディレクトリを 0644 にすべきという根拠ではない。修正実装と、必要なら理由を明示した限定例外で解決すること。ディレクトリ探索には実行権限が必要である。

統合側配線とブラウザ/C4 受入は限定再レビューの対象外。approve・merge・commit・push・Docker 状態変更は行わず、指定記録と依頼された PR コメントのみを書く。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID / fsuid | User number / identity used for filesystem checks. | 利用者番号／ファイル操作の検査に使う番号。 |
| Capability | A separately granted Linux power. | 個別に与える Linux の権限。 |
| CAP_CHOWN | Permits changing ownership. | 所有権の変更を許す。 |
| CAP_FOWNER | Bypasses ownership checks such as chmod's. | chmod などの所有者検査を越える。 |
| EPERM | Operation rejected for insufficient permission. | 権限不足による操作拒否。 |
| umask | Removes permissions from newly created files or directories. | 新規ファイル・ディレクトリの権限を制限する値。 |
| Bind mount | Exposes an existing host path inside a container. | ホストの既存パスをコンテナ内に見せる仕組み。 |
| C4 | Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入試験。 |
