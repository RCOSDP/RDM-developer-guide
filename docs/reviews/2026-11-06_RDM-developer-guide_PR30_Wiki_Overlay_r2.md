# PR30 Wiki Overlay Review r2 / Wiki オーバーレイレビュー r2

> **Summary:** Revision required: interpolation is fixed, but the ownership initializer cannot chmod after chown with CAP_CHOWN alone on Linux.
> **概要:** 要修正。変数展開は修正済みだが、Linux では CAP_CHOWN だけの初期化処理が chown 後の chmod に失敗する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** permission checks apply after each ownership change; a passing Compose parser does not execute those checks. ／ 所有者変更後の各操作には改めて権限検査があり、Compose の解析成功はその実行を検証しない。
- Applies to: PR #30, head `7b79e3e90193c08a7d8925687b88f6fd561bdd66`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR30_Wiki_Overlay_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-06](../decisions/ADR-06_Wiki_Frontend_Overlay.md).
- Used by: [DEMO-20](../demo/20_core_install_mac_studio.md) · [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and blocking finding

**Needs revision. R2-01 — P1: the initializer fails after changing ownership.** In `installer/grdm_dev/templates/wiki_static_init.json:9`, the command is `set -e; chown 1000:1000 /wiki_static; chmod 0755 /wiki_static; ls -ld /wiki_static`. The rendered service drops ALL capabilities and adds only CHOWN, with no user override (the intended root image user). After chown, root is no longer the directory owner. Linux chmod requires the owning filesystem UID or CAP_FOWNER; CAP_CHOWN does not grant this. Thus chmod returns EPERM on an ordinary Linux filesystem, even when the mode is already 0755, and `set -e` terminates the initializer. Both successful-completion dependencies then block `wiki_assets` and its four consumers. R1-02 remains unresolved.

The kernel's [v6.12 attribute check](https://github.com/torvalds/linux/blob/v6.12/fs/attr.c) calls `inode_owner_or_capable` for ATTR_MODE and returns EPERM on failure; the [owner check](https://github.com/torvalds/linux/blob/v6.12/fs/inode.c) accepts the owner or CAP_FOWNER. These sources were read through `gh api`. This is a source-based finding, not a claimed container reproduction: Docker state changes were prohibited. Remove the unnecessary chmod if provisioning guarantees suitable mode, or implement an explicit permission strategy (including the hardening exception if a further capability is needed). Merely moving chmod before chown is insufficient when the fresh directory belongs to a nonzero host UID. Add a Linux execution test for a fresh non-1000-owned directory and a repeat invocation.

### Rechecked fixes and remaining acceptance

- **R1-01 resolved:** `compose.py` doubles every dollar in command strings/list entries. A separate temporary core render used fake values for all 17 `secrets.SECRET_KEYS`; `REQUIRED_SECRETS` exactly equals that tuple. The generated command contains `$$src`, `$$dst`, `$$bundle`, `$$f`, `$$n`, and `$$(...)`. Docker Compose 5.6.0 `config --format json` returned zero with empty stderr and preserved these escapes in its round-trippable output; no empty-variable substitution occurred. The interpolation-model test and real parser test both pass.
- **R1-02 partially implemented, blocked by R2-01:** the generated init service has `cap_drop: [ALL]`, `cap_add: [CHOWN]`, `read_only: true`, `no-new-privileges:true`, and `restart: "no"`. Its hardening exception records a reason, review date 2027-01-31 and M4 target. `web → wiki_assets → wiki_static_init` uses `service_completed_successfully` at both edges; api/admin/worker also await wiki_assets. This ordering correctly propagates the init failure rather than bypassing it.
- **Copier improvements verified:** UID 1000 uses `cp -R`, rejects absence of `wiki-edit-page.*.js`, copies before pruning and checks the alias is nonempty. Copy-before-prune reduces the empty-directory window but does not make updates atomic or preserve old hashed chunks for already-open pages. Actual first-run copying and updates remain untested here.
- **R1-03 tracked, not functionally resolved:** ADR-06 §4, the manifest note and both status-board languages explicitly retain edit.mako integration wiring and browser/C4 acceptance as follow-up. This is adequate visibility for the separate integration work, not evidence that M2 works. The manifest/template phrase “verified in real install run 5” should be read as the planned verification; the status board still says open. Record the integration commit and browser results before declaring acceptance.

The additional r1 observations about empty overlay values and unknown one-shot exit codes are not closed by this targeted re-review. No approval, merge, commit, push or Docker state change was performed; only the requested review record and PR comment were written.

### Validation

Run from the review worktree root:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/manifest_check.py
python3 tools/docs_check.py
gh pr checks 30 --repo RCOSDP/RDM-developer-guide
```

The separate parser probe used the test helpers `make_root` and `render`, with a fake .env generated directly from SECRET_KEYS and an injected empty Compose-ps result. It ran `docker compose -f <temporary-root>/runtime/docker-compose.yml config --format json`; no daemon mutation was requested. Evidence counts before adding this record:

```toon
validation[5]{check,result,detail}:
  installer,pass,343 tests; 10 skipped
  tools,pass,89 tests
  manifest_check,pass,zero findings
  docs_check,pass,84 files; 8 exempt; 19 warnings
  github_checks,pass,all 8 checks including Python 3.11 and 3.12
```

The tracked-file documentation check was repeated: 84 files checked, eight exempt, 19 warnings, passed. The new untracked record was additionally checked directly with docs_check.check_file and passed. Green checks do not cover execution of the restricted-capability chmod.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と阻害指摘

**要修正。R2-01 — P1: 所有者変更後に初期化処理が失敗する。** `installer/grdm_dev/templates/wiki_static_init.json:9` は `set -e; chown 1000:1000 /wiki_static; chmod 0755 /wiki_static; ls -ld /wiki_static` を実行する。生成サービスは ALL を drop し CHOWN だけを追加し、user の上書きはない（想定はイメージ既定の root）。chown 後の root はディレクトリ所有者ではない。Linux の chmod は所有者の filesystem UID または CAP_FOWNER を要求し、CAP_CHOWN では許可されない。通常の Linux ファイルシステムでは元から 0755 でも EPERM になり、`set -e` で初期化が失敗する。成功終了を待つ二段の依存により wiki_assets と四つの利用サービスも起動できない。R1-02 は未解決。

カーネルの [v6.12 属性検査](https://github.com/torvalds/linux/blob/v6.12/fs/attr.c) は ATTR_MODE に `inode_owner_or_capable` を呼び、失敗時に EPERM を返す。[所有者検査](https://github.com/torvalds/linux/blob/v6.12/fs/inode.c) が許可するのは所有者または CAP_FOWNER。これらを `gh api` で確認した。Docker 状態変更は禁止なのでコンテナでの再現ではなく、ソースに基づく指摘である。準備段階で適切なモードを保証するなら不要な chmod を除くか、明示的な権限戦略を実装する（権限を追加するなら hardening の例外も更新）。新規ディレクトリが非 0 のホスト UID 所有なら、chmod を chown より前に移すだけでは不十分。非 1000 所有の新規ディレクトリと再実行を扱う Linux 実行試験を追加する。

### 修正の再確認と受入残件

- **R1-01 解決:** `compose.py` は command の文字列・配列要素のドル記号を二重化する。別途 core を一時生成し、全 17 個の `secrets.SECRET_KEYS` に偽値を設定した。`REQUIRED_SECRETS` はそのタプルと完全一致。生成コマンドに `$$src`・`$$dst`・`$$bundle`・`$$f`・`$$n`・`$$(...)` がある。Docker Compose 5.6.0 の `config --format json` は終了 0、stderr は空で、再読込可能な出力にもエスケープを保持し、空文字への展開は起きなかった。展開モデルと実パーサの試験は両方成功。
- **R1-02 部分実装、R2-01 が阻害:** 生成された init は `cap_drop: [ALL]`・`cap_add: [CHOWN]`・`read_only: true`・`no-new-privileges:true`・`restart: "no"`。hardening の例外には理由・見直し日 2027-01-31・M4 目標がある。`web → wiki_assets → wiki_static_init` の両段が `service_completed_successfully`。api/admin/worker も wiki_assets を待つ。この依存は初期化失敗を迂回せず正しく伝える。
- **コピー改善を確認:** UID 1000 で `cp -R` を使い、`wiki-edit-page.*.js` の不在を失敗とし、コピー後に間引き、別名ファイルが空でないことを検査する。先にコピーすれば空ディレクトリの時間は減るが、更新は不可分ではなく、開いたままのページ用の旧ハッシュ付きチャンクも保持しない。実際の初回コピーと更新は未検証。
- **R1-03 は追跡済み、機能としては未解決:** ADR-06 §4・manifest の note・進捗ボードの英和に edit.mako の統合側配線とブラウザ/C4 受入が残件として明記された。別の統合作業を可視化するには十分だが M2 動作の証拠ではない。manifest/template の “verified in real install run 5” は予定の検証として読む必要があり、進捗ボードは未着手。受入宣言前に統合コミットとブラウザ結果を記録する。

r1 の追加観察である空の overlay 値と one-shot 終了コード不明時の扱いは、今回の限定再レビューでは解決扱いにしない。approve・merge・commit・push・Docker 状態変更は行わず、指定のレビュー記録と PR コメントだけを書いた。

### 検証

実行コマンドは英語部のコードブロックのとおり。独立したパーサ確認は試験補助 `make_root` と `render` を利用し、SECRET_KEYS 全体から偽 .env を作り、Compose ps の空結果を注入した。`docker compose -f <一時ルート>/runtime/docker-compose.yml config --format json` を実行し、デーモンの変更は要求していない。

installer は 343 件成功（10 skip）、tools は 89 件成功、manifest は指摘 0。本記録追加前の docs_check は 84 ファイル・例外 8・警告 19 で成功。GitHub は Python 3.11/3.12 を含む八つの検査すべて成功。追跡済み文書の再検査は 84 ファイル・例外 8・警告 19 で成功。新規の未追跡レビュー記録は docs_check.check_file で個別に検査して成功。これらの成功は、権限を限定した chmod の実行を保証しない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Capability | A named Linux permission granted separately from other powers. | Linux の権限を機能ごとに分けたもの。 |
| CHOWN / FOWNER | Permission to change ownership / bypass ownership checks for operations such as chmod. | 所有者変更の権限／chmod などの所有者検査を越える権限。 |
| EPERM | An operation was rejected for lack of permission. | 権限不足で操作を拒否したことを示す結果。 |
| UID | Numeric user identity used for file access. | ファイルへのアクセスを決める利用者番号。 |
| Compose | Tool that reads service definitions and coordinates containers. | サービス定義を読んでコンテナを動かす道具。 |
| One-shot | A process that completes its work and exits. | 仕事を終えたら終了する処理。 |
| C4 | The Wiki collaborative-editing acceptance scenario. | Wiki 共同編集の受入試験。 |
