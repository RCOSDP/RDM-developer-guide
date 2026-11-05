# PR30 Wiki Overlay Review r3 / Wiki オーバーレイレビュー r3

> **Summary:** Needs revision: moving chmod before chown does not fix host-owned bind directories or repeat initialization.
> **概要:** 要修正。chmod を chown より前に移しても、ホスト所有の bind ディレクトリと初期化の再実行は直らない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** UID 0 without CAP_FOWNER cannot chmod another user's directory; changing command order does not change the initial owner or make initialization repeatable. ／ CAP_FOWNER のない UID 0 は他ユーザー所有のディレクトリを chmod できず、順序変更は初期所有者も再実行の可否も変えない。
- Applies to: PR #30, head `bff97b61eae15034c7a0d79fec284526350d2af8`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2](2026-11-06_RDM-developer-guide_PR30_Wiki_Overlay_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Needs revision. R2-01 remains open — P1.** At `installer/grdm_dev/templates/wiki_static_init.json:9`, `set -e; chmod 0755 /wiki_static; chown 1000:1000 /wiki_static` still fails on an ordinary Linux host. The initializer drops ALL capabilities (separately granted Linux powers) and adds only CHOWN. `compose.py:859` creates the directory with the installer's host identity, and `compose.py:450` exposes it through a bind mount (a container path backed by an existing host directory). Mounting it does not transfer ownership to container root. For a host UID other than 0, including UID 1000, the initial chmod returns EPERM. `set -e` stops before chown, so the successful-completion dependency blocks wiki_assets and its four consumers.

Even if a fresh directory actually belongs to root, the order change only helps the first invocation: chown leaves it owned by 1000, and a subsequent invocation fails at chmod. Setting a mode already equal to 0755 does not bypass the ownership check. These conclusions assume ordinary non-idmapped, rootful Linux bind mounts; no Docker execution reproduction was performed.

### Kernel rule and correction required

Linux v6.12 [setattr_prepare in fs/attr.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/attr.c) checks `inode_owner_or_capable` for ATTR_MODE and returns `-EPERM` on failure. [inode_owner_or_capable in fs/inode.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/inode.c) accepts an inode owner matching `current_fsuid()`, accounting for mount ID mapping, or a mapped owner plus CAP_FOWNER in the current user namespace. There is no unconditional UID-0 exemption. CAP_CHOWN authorizes ownership changes, not chmod.

CAP_DAC_OVERRIDE is **not a substitute for CAP_FOWNER**. [generic_permission in fs/namei.c](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/namei.c) uses it for ordinary read/write/search permission failures; it does not satisfy the separate chmod ownership check. With searchable container ancestors and the intended 0755 directory, DAC override is not required for this owner/mode operation. More restrictive ancestors can separately require search permission; that is not the reported EPERM. The kernel files and tag-to-commit resolution were read through `gh api`.

Implement an explicit repeatable permission strategy. If keeping unconditional chmod, grant and document CAP_FOWNER alongside CHOWN, with a Linux execution test under the exact capability set. Alternatively, guarantee the intended mode during provisioning and remove the unnecessary chmod; account for existing directories and restrictive umasks rather than assuming mkdir always yields 0755. Test a fresh nonzero/non-1000 host owner, UID 1000, root ownership, and a second invocation. Update the template note and both ADR-06 halves: their explanation currently assumes root owns a directory that they also describe as host-user-owned.

The added assertion at `installer/tests/test_compose.py:730–732` verifies text order only. It cannot prove chmod is authorized and currently preserves the faulty command. This is the same unresolved R2-01, not a new independent blocker. The integration wiring and browser/C4 acceptance left open in r2 remain outside this targeted re-review.

### Validation

Commands run from the review worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
PYTHONPATH=installer:installer/tests python3 -m unittest -v test_compose.ComposeRenderTests.test_docker_compose_config_accepts_the_rendered_file
git diff --check
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
```

Observed results, not canonical manifest data:

```toon
validation[6]{check,result,detail}:
  installer,pass,343 tests; 10 skipped
  tools,pass,89 tests
  manifest_check,pass,zero findings
  docs_check,pass,85 files; 8 exempt; 19 warnings
  compose_parser,pass,read-only docker compose config; explicit test passed without skip
  github_checks,pass,all 8 checks including Python 3.11 and 3.12
```

`git diff --check` passed. The untracked r3 record was checked separately using `docs_check.check_file`. A first targeted test command used the nonexistent class name ComposeTests and failed to load; the corrected ComposeRenderTests command passed. Local HEAD matched the PR head. Green parser/unit/CI checks do not execute the restricted-capability initializer. No approval, merge, commit, push or Docker state change was performed; only the requested record and one PR comment were written.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**要修正。R2-01 は未解決 — P1。** `installer/grdm_dev/templates/wiki_static_init.json:9` の `set -e; chmod 0755 /wiki_static; chown 1000:1000 /wiki_static` は通常の Linux ホストで引き続き失敗する。初期化処理は capability（個別に与える Linux の権限）を ALL drop し CHOWN だけ追加する。`compose.py:859` は実行したホストユーザーの所有でディレクトリを作り、`:450` は bind mount（ホストの既存ディレクトリをコンテナ内に見せる仕組み）として公開する。mount しても所有者はコンテナの root に変わらない。ホスト UID が 0 以外なら、1000 も含めて最初の chmod が EPERM になる。`set -e` が chown より前に停止させ、成功終了待ちの依存により wiki_assets と四つの利用サービスも起動できない。

初期ディレクトリが本当に root 所有でも、順序変更が効くのは初回だけである。chown 後は UID 1000 所有なので、再実行の chmod が失敗する。既に 0755 でも所有者検査は省略されない。通常の ID マッピングを変更しない rootful Linux bind mount を前提とした判断であり、Docker 実行による再現は行っていない。

### カーネル規則と必要な修正

Linux v6.12 の [fs/attr.c の setattr_prepare](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/attr.c) は ATTR_MODE に対して `inode_owner_or_capable` を検査し、失敗なら `-EPERM` を返す。[fs/inode.c の inode_owner_or_capable](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/inode.c) が許すのは、mount の ID 対応を考慮した所有者と `current_fsuid()` の一致、または所有者の ID 対応があり現在のユーザー名前空間で CAP_FOWNER がある場合である。UID 0 の無条件な例外はない。CAP_CHOWN は所有者変更を許すが chmod は許さない。

**CAP_DAC_OVERRIDE は CAP_FOWNER の代わりにならない。** [fs/namei.c の generic_permission](https://github.com/torvalds/linux/blob/adc218676eef25575469234709c2d87185ca223a/fs/namei.c) は通常の読取り・書込み・経路探索の拒否を越えるために使うが、chmod の別の所有者検査は満たさない。コンテナ内の祖先パスを探索でき、想定どおり 0755 なら、この所有者・モード操作に DAC override は不要である。祖先の権限が厳しければ別途探索権限が必要になり得るが、今回の EPERM とは別問題。カーネル各ファイルとタグからコミットへの対応は `gh api` で確認した。

再実行できる権限戦略を実装する必要がある。無条件の chmod を残すなら CHOWN に加え CAP_FOWNER を与え、例外を記録し、実際と同じ権限構成で Linux 実行試験を行う。代案は準備段階でモードを保証し、不要な chmod を除くこと。ただし既存ディレクトリと厳しい umask を扱い、mkdir が必ず 0755 になると仮定しない。非 0・非 1000 のホスト所有、UID 1000 所有、root 所有、および再実行を試験する。テンプレートの注と ADR-06 の英和両方も修正する。現在の説明はホストユーザー所有と述べながら root 所有を前提にしている。

追加された `installer/tests/test_compose.py:730–732` の検査は文字列の順序しか確認しない。chmod の権限は検証できず、現在は誤ったコマンドを固定している。これは新たな独立指摘ではなく、同じ R2-01 の未解決である。r2 で残した統合側配線とブラウザ/C4 受入は、今回の限定再レビューでも未完了のまま。

### 検証

実行コマンドは英語部に記載した。installer は 343 件成功（10 skip）、tools は 89 件成功、manifest は指摘 0、docs_check は 85 ファイル・例外 8・警告 19 で成功。読み取り専用の docker compose config を使う個別試験も skip なしで成功。GitHub は Python 3.11/3.12 を含む八つの検査すべて成功し、ローカル HEAD と PR head は一致した。

`git diff --check` は成功。未追跡の r3 記録は `docs_check.check_file` で別途検査した。個別試験の最初の呼出しは存在しない ComposeTests クラスを指定して読込みに失敗したが、ComposeRenderTests に直した呼出しは成功した。解析・単体・CI の成功は権限を限定した初期化処理の実行を検証しない。approve・merge・commit・push・Docker 状態変更は行わず、指定記録と PR コメント一件のみを書いた。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| UID / fsuid | Numeric user identity / identity used for filesystem checks. | 利用者の番号／ファイル操作の検査に使う番号。 |
| Capability | A separately granted Linux power. | 個別に与える Linux の権限。 |
| CAP_CHOWN | Permits changing file ownership. | ファイル所有者の変更を許す。 |
| CAP_FOWNER | Bypasses ownership checks for operations such as chmod. | chmod などの所有者検査を越える。 |
| CAP_DAC_OVERRIDE | Bypasses ordinary file access permissions, not chmod's ownership check. | 通常のアクセス権限を越えるが chmod の所有者検査は越えない。 |
| EPERM | Operation rejected for lack of permission. | 権限不足による操作拒否。 |
| Bind mount | Exposes an existing host path inside a container. | 既存のホストパスをコンテナ内に見せる仕組み。 |
| C4 | Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入試験。 |
