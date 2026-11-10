# PR42 PostgreSQL 18 review r4 / PostgreSQL 18 レビュー r4

> **Summary:** Pass. R3-01 is closed: recovery filesystem errors return 15 through every relevant command entry point, and pending recovery remains recoverable.
> **概要:** 合格。R3-01 は解決。復旧中のファイルシステム障害は関連する全コマンド入口から終了 15 となり、保留操作は再復旧できる。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** the initial recovery needs the same error boundary as the migration itself; checking actual command entry points confirms the exit contract. ／ 初回復旧にも移行本体と同じ例外境界が必要であり、実コマンド入口の試験で終了値の契約を確認できる。
- Applies to: RCOSDP/RDM-developer-guide PR #42, diff `7e61df3..d49945c`, head `d49945c78bd5d87efc5c7985142c0ecb5520a025`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r3](2026-11-10_RDM-developer-guide_PR42_PostgreSQL18_r3.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Pass; R3-01 closed.** No blocking regression found in the scoped diff. `run_upgrade` now catches OSError around the entire locked operation, including its initial recovery. The common filesystem-error message distinguishes a remaining journal from no pending operation; recover and rollback use it too. The fallback recovery message avoids reporting `None` after an operation has already retired its journal.

The r3 reproduction now returns 15 from actual `cli.main`, retains the pending journal and current PostgreSQL 18 directory, then completes recovery after fault removal. Persistent fsync EIO was also injected through all five entry points: `db upgrade`, `db rollback`, `db recover`, `up --no-open`, and `reset`. Every entry returns 15 and retains the pending journal; later recovery succeeds. Unit tests separately inject the exact volumes-parent synchronization fault at those five entries.

Every observed fsync on successful upgrade, rollback and pending-upgrade recovery was individually failed once with EIO: 10, 6 and 4 sites respectively. All return 15 through the CLI, mention the injected error, and permit later recovery with a readable current major, no journal and no tracked temporary server. Journal retention applies to unfinished recovery: a fault before initial journal publication or after journal unlink need not leave a journal. The patch accurately reports that distinction; these tests do not claim unconditional retention after completed retirement.

The unchanged 162-point crash matrix passes (128 upgrade, 34 rollback). The r3 double-rename failures, lock-only refusal, non-ASCII version, recovery parent synchronization, rollback confirmation race and lifecycle interleavings also pass. The r3 extra probe was updated only to require exit 15 instead of expecting the former uncaught exception, and to import the new clone.

### Validation and limits

Clean clone: `/tmp/pr42-rev-r4/repo`; system Python: `/usr/bin/python3` 3.9.6. Logs and probe scripts: `/tmp/pr42-rev-r4/`. Results are review measurements, not canonical manifest data.

```toon
checks[8]{check,exit,result}:
  "installer units",0,"587 tests; 10 skipped"
  "tools units",0,"93 tests"
  "docs_check",0,"147 files; 8 exempt; 36 warnings"
  "manifest_check",0,"0 findings; 668 scanned; 63 skipped"
  "r3 probes",0,"162 crash boundaries and regression probes pass"
  "r3 extra",0,"R3-01 closed; lifecycle interleavings pass"
  "EIO probes",0,"20 fsync sites; 5 persistent-error entry points pass"
  "diff whitespace",0,"no errors"
```

Commands run from the clone root:

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
/usr/bin/python3 -m unittest discover -s tools/tests
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-r4/probe.py
/usr/bin/python3 /tmp/pr42-rev-r4/extra.py
/usr/bin/python3 /tmp/pr42-rev-r4/eio.py
git diff --check 7e61df3..d49945c
```

This untracked report was checked directly using `docs_check.check_file`: 0 errors and 0 warnings. The only clone addition is this report; no commit, push, approval, merge or closure is performed. One Japanese PR comment reports the verdict. Existing runtime/.env and the grdm-dev Docker stack were not accessed or changed. Synthetic fixtures and fake Docker runners do not validate real PostgreSQL migration, Linux ownership, amd64, browser acceptance or physical power-loss durability.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**合格（pass）、R3-01 解決。** 対象差分に必須修正となる回帰は見つからなかった。`run_upgrade` は初回復旧を含むロック内の操作全体で OSError を捕捉する。共通の障害メッセージは journal が残る場合と保留操作がない場合を区別し、recover と rollback も利用する。操作記録を削除済みの復旧結果が `None` と表示されることも防ぐ。

r3 の再現は実際の `cli.main` から終了 15 となり、保留 journal と現行 PostgreSQL 18 を保持し、障害除去後の復旧に成功した。継続する fsync EIO を `db upgrade`、`db rollback`、`db recover`、`up --no-open`、`reset` の五つの入口へ注入し、すべて終了 15、保留 journal の保持、後続復旧の成功を確認した。提供単体試験は、この五入口で volumes 親ディレクトリ同期の元の障害も個別に検証する。

正常経路で観測した fsync の全箇所へ一度ずつ EIO を注入した。upgrade 10、rollback 6、保留 upgrade の recover 4 箇所で、すべて CLI から 15 を返し、注入した障害を表示した。その後の復旧では現行版が読め、journal と追跡する一時サーバーが残らない。journal 保持は未完了の復旧に対するもので、最初の記録公開前や記録 unlink 後の障害では記録が残るとは限らない。修正後の表示はこの違いを正しく伝える。完了済み操作の記録が常に残ると主張する試験ではない。

既存の 162 箇所の中断行列（upgrade 128、rollback 34）は同じ件数で合格した。r3 の二重 rename 失敗、記録なしロック拒否、非 ASCII 版番号、復旧時の親同期、rollback 確認中の競合、lifecycle との競合も合格した。r3 の追加プローブは新 clone の import と、旧未捕捉例外の期待を終了 15 の期待へ置き換えた箇所のみ更新した。

### 検証と限界

クリーン clone は `/tmp/pr42-rev-r4/repo`、システム Python は `/usr/bin/python3` 3.9.6。ログとプローブは `/tmp/pr42-rev-r4/`。結果は manifest 正本ではなくレビュー測定である。

```toon
checks[8]{check,exit,result}:
  "installer units",0,"587 tests; 10 skipped"
  "tools units",0,"93 tests"
  "docs_check",0,"147 files; 8 exempt; 36 warnings"
  "manifest_check",0,"0 findings; 668 scanned; 63 skipped"
  "r3 probes",0,"162 crash boundaries and regression probes pass"
  "r3 extra",0,"R3-01 closed; lifecycle interleavings pass"
  "EIO probes",0,"20 fsync sites; 5 persistent-error entry points pass"
  "diff whitespace",0,"no errors"
```

実行コマンドは英語節に記載した。未追跡の記録は `docs_check.check_file` で直接検査し、エラー 0・警告 0 を確認した。clone への追加は本記録のみで commit・push・approve・merge・close は行わず、日本語 PR コメント一件で判定を報告する。既存 runtime/.env と grdm-dev Docker 状態にはアクセスも変更もしていない。疑似 fixture と Docker runner の試験では、実 PostgreSQL 移行、Linux 所有権、amd64、ブラウザ受入、物理電源断の永続化は検証していない。
