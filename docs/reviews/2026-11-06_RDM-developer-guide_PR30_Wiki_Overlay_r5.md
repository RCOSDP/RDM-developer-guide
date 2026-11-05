# PR30 Wiki Overlay Review r5 / Wiki オーバーレイレビュー r5

> **Summary:** The normal provisioning and rerender lifecycle is corrected; revision is still required because Semgrep fails on the new regression test.
> **概要:** 通常の初期準備と再 render の不具合は修正済み。ただし新しい回帰試験で Semgrep が失敗しており、要修正。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a justified scanner exception in production code does not cover the same operation in regression fixtures. ／ 本体コードの根拠付き検査例外は、回帰試験の同じ操作には適用されない。
- Applies to: PR #30, head `b9a26c707b3798f1d569ba659826f4d689ee8c2b`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r4](2026-11-06_RDM-developer-guide_PR30_Wiki_Overlay_r4.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Needs revision: R5-01 — P2, failing Semgrep gate.** The [failed CI job](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42126552100/job/127592113223) reports exactly one finding: `installer/tests/test_compose.py:926`, `os.chmod(vol, 0o700)`, rule `python.lang.security.audit.insecure-file-permissions.insecure-file-permissions`. The production chmod's narrow annotation is effective; the regression fixture has no matching exception. Add a narrowly justified exception for this temporary directory fixture, or create its intended mode without triggering the rule, then obtain passing Semgrep on the new head. Do not change a directory to 0644 to satisfy this generic message: traversal needs execute permission. This is a gate failure, not evidence that an owner-only temporary directory is insecure.

**R2-01 is closed for the normal sequential lifecycle.** `_ensure_volume_dir()` returns before mkdir/chmod when the path exists. Its fresh-directory path sets 0755 while the host owns it. The existing-directory unit test asserts chmod is never called even when a call would raise PermissionError, and preserves 0700. An additional full-render probe under umask 077 verified fresh wiki_static mode 0755; rerender with every volume chmod forced to raise PermissionError succeeded, preserving uid, gid and mode. This is a control-flow regression, not a real Linux ownership-transfer test.

### First-run ordering and limits

Host render creates the bind directory before startup. `wiki_static_init` then performs only `chown 1000:1000 /wiki_static` with ALL capabilities dropped and CHOWN added. `wiki_assets`, running as 1000:1000, waits for successful initializer completion, copies with `cp -R`, and exits successfully before web/api/admin/worker can start through their completion dependencies. Those consumers mount only the wiki subdirectory read-only. The existing output assertions and read-only Compose parser check pass. Setting mode on the host before chown avoids the CAP_FOWNER issue; rerender now leaves transferred ownership and mode alone. Both ADR-06 language halves describe this change consistently.

The PermissionError handler on the fresh path tolerates a concurrent ownership change but does not guarantee 0755 if chmod actually fails. The exists/mkdir sequence is not atomic, and existing directories with unsuitable permissions are not repaired. These are limits of the supported sequential workflow, not a recurrence of unconditional rerender chmod. No concurrent provisioner, real Linux chown, container startup or browser/C4 acceptance was executed. Existing filesystem/namespace restrictions still apply; ADR's statement that rerender cannot fail should be read specifically as removal of this chmod failure.

### Validation

Commands run from the review worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer:installer/tests python3 -m unittest -v test_compose.ComposeRenderTests.test_docker_compose_config_accepts_the_rendered_file test_compose.ComposeRenderTests.test_idempotent_rerun_reports_unchanged test_compose.VolumeDirOwnershipTests
git diff --check
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
gh run view 42126552100 --repo RCOSDP/RDM-developer-guide --log-failed
```

Observed results, not canonical manifest data:

```toon
validation[7]{check,result,detail}:
  installer,pass,345 tests; 10 skipped
  tools,pass,89 tests
  manifest_check,pass,zero findings
  docs_check,pass,87 checked; 8 exempt; 19 warnings
  targeted_tests,pass,4 tests; none skipped; read-only compose config included
  render_probe,pass,umask 077; guarded rerender; uid/gid/mode preserved
  CI,fail,7 checks pass; Semgrep fails on test_compose.py:926
```

The untracked r5 record is also checked directly with `docs_check.check_file`; git diff whitespace checks pass. No approve, merge, close, commit, push or Docker state change was performed. Only the requested review record and PR comment were written.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正: R5-01 — P2、Semgrep ゲート失敗。** [失敗した CI ジョブ](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42126552100/job/127592113223) の指摘は一件で、`installer/tests/test_compose.py:926` の `os.chmod(vol, 0o700)`、規則は `python.lang.security.audit.insecure-file-permissions.insecure-file-permissions`。本体 chmod の限定注記は効いているが、回帰試験側には同じ例外が無い。一時ディレクトリの試験準備である根拠を付けた限定例外、または規則に抵触しないモード設定方法を採用し、新 head の Semgrep 成功を確認すること。この一般的な警告に合わせてディレクトリを 0644 にしてはいけない。探索には実行権限が必要である。所有者だけが使う一時ディレクトリが危険という指摘ではなく、検査ゲートの失敗である。

**通常の逐次実行における R2-01 は解決。** `_ensure_volume_dir()` は既存パスなら mkdir/chmod より前に戻る。新規パスだけ、ホストが所有する間に 0755 を設定する。既存ディレクトリの単体試験は、呼べば PermissionError になる chmod を呼ばないことと、0700 の維持を検証する。追加の full-render 検証では umask 077 でも新規 wiki_static が 0755 となり、全ボリュームへの chmod を PermissionError にする再 render も成功し、uid・gid・mode が維持された。これは制御フローの回帰試験で、Linux 上の実際の所有権移転試験ではない。

### 初回の順序と限界

ホストの render が起動前に bind ディレクトリを作る。次に `wiki_static_init` が ALL drop・CHOWN のみ追加で `chown 1000:1000 /wiki_static` だけを実行する。`wiki_assets` は 1000:1000 で初期化の成功終了を待ち、`cp -R` でコピーする。web/api/admin/worker はコピーの成功終了を待って起動し、wiki 下位ディレクトリだけを読取り専用で mount する。既存の生成内容検証と読取り専用 Compose parser 検査は成功。chown 前にホストで mode を設定するため CAP_FOWNER 問題を避け、再 render は移転後の所有者と mode に触れない。ADR-06 の英和両部もこの変更と一致する。

新規パスの PermissionError 捕捉は同時の所有権変更を許容するが、実際に chmod が失敗すれば 0755 は保証しない。exists/mkdir は不可分な操作ではなく、不適切な権限の既存ディレクトリも修復しない。これは対応する逐次実行の限界であり、無条件の再 render chmod の再発ではない。同時の準備処理、Linux での実 chown、コンテナ起動、ブラウザ/C4 受入は実施していない。ファイルシステム・名前空間の制約は残り、ADR の「再描画が失敗することはない」はこの chmod 失敗の解消に限定して読む必要がある。

### 検証

実行コマンドと結果一覧は英語部に記載。installer は 345 件成功（10 skip）、tools は 89 件成功、manifest は指摘 0。docs は 87 件検査・8 例外・19 警告で成功。個別四試験は skip 無しで成功し、読取り専用 compose config を含む。umask 077 と chmod 拒否を組み合わせた再 render の追加検証も成功。CI は七件成功、Semgrep だけが新規試験の行 926 で失敗した。

未追跡の r5 記録は `docs_check.check_file` で別途検査し、git diff の空白検査も成功。approve・merge・close・commit・push・Docker 状態変更は行わず、指定のレビュー記録と PR コメントのみを書く。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| CI | Automated checks run for a change. | 変更ごとに自動実行する検査。 |
| Semgrep | A scanner that matches source code against rules. | ソースを規則と照合する検査器。 |
| UID / GID | User / group numbers identifying an owner. | 所有者を表す利用者／グループ番号。 |
| Mode / umask | Permission bits / a filter on new permissions. | 権限ビット／新規権限を制限する値。 |
| Bind mount | A host path exposed inside a container. | ホストのパスをコンテナ内へ見せる仕組み。 |
| CAP_CHOWN / CAP_FOWNER | Ownership-changing power / ownership-check bypass. | 所有者変更の権限／所有者検査を越える権限。 |
| C4 | Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入試験。 |
