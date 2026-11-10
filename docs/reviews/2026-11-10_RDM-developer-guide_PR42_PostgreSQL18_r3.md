# PR42 PostgreSQL 18 review r3 / PostgreSQL 18 レビュー r3

> **Summary:** Changes requested: the four r2 reproductions are fixed, but a durability error during pending recovery escapes the `db upgrade` command instead of returning 15.
> **概要:** 要修正。r2 の四つの再現事象は修正済みだが、保留中の復旧で同期に失敗すると `db upgrade` は終了 15 を返さず例外を外へ出す。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** propagating durability errors also requires every command that invokes recovery to translate them into its documented exit code. ／ 永続化の失敗を伝える修正には、復旧を呼ぶすべてのコマンドで、その失敗を規定の終了値へ変換する必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #42, diff `5780b16..7e61df3`, head `7e61df3c84207c9342745f5c80d18ac708f0bb63`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2](2026-11-10_RDM-developer-guide_PR42_PostgreSQL18_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and finding

**Changes requested. R3-01 · P2: translate recovery OSError in `db upgrade` to exit 15.** In [database.py](../../installer/grdm_dev/database.py), `run_upgrade` (lines 751–760) catches only `UpgradeError`, but `_upgrade_locked` calls `recover` at line 765 before entering its later error handler. With a pending swap whose two renames have finished, an EIO from `_fsync_dir(current.parent)` in `recover` (line 608) escapes through the actual `cli.main` entry point as an uncaught `OSError`. The CLI catches only KeyboardInterrupt. The new strict fsync behavior exposes this route; `run_recover` and `run_rollback` already catch both exception types.

Independent reproduction: create a valid pending upgrade at the swap boundary, perform its two renames without retiring its journal (the state after a crash before record creation), inject EIO for the volumes-parent sync, then call `cli.main(['--root', fixture_root, '--yes', 'db', 'upgrade'])` with a fake Docker runner. It raises OSError rather than returning 15. Current remains PostgreSQL 18 and the journal remains; a later fault-free `db recover` succeeds. This is an error-contract defect, not observed data loss or a fail-open start. Catch OSError around the complete locked upgrade including initial recovery, retain the journal, and add an entry-point test for this state.

### R2 closure and regression checks

- **R2-01 closed:** both upgrade and rollback recovery return 15 and retain the journal when replacement and compensation renames both fail. Persistent subsequent failures also refuse `up` and recovery; removing the fault permits recovery to finish with the expected major and no journal.
- **R2-02 closed:** the common lock excludes `up` even without a journal and throughout rollback confirmation. Independent callbacks during Compose start, reset shutdown and reset deletion reject all three DB actions with 15. Supplied tests also check the reverse reset direction and a competing process. No real Docker command was executed by these probes.
- **R2-03 original reproduction fixed; R3-01 remains:** recovered upgrade/rollback renames sync the volumes parent before journal removal, and EIO is no longer swallowed. Supplied ordering and persistent-sync-error tests pass. The documented EINVAL/ENOTSUP exceptions remain intentional; process-crash tests do not prove power-loss durability.
- **R2-04 closed:** non-ASCII PG_VERSION now returns 15 through `up`, without starting Compose; supplied tests also cover unreadable helper output.

The original 162-point matrix (128 upgrade, 34 rollback) passes unchanged in boundary count. It injects an uncatchable exception before and after every observed Docker call, durable JSON write, rename/replace, fsync, mkdir/unlink, snapshot, readiness wait, restore-file construction and journal removal. Recovery checks a readable current major, absence of a pending journal and tracked servers, and an upgrade record when current is 18. Double failures and lifecycle interleavings are separate probes. ADR-12 now distinguishes pre-swap and post-swap disk-full outcomes; ADR-13 aligns its header with the recorded owner choices. No other blocking regression was found in the scoped diff.

### Validation and limits

Clean clone: `/tmp/pr42-rev-r3/repo`; system Python: `/usr/bin/python3` 3.9.6. Results are review measurements, not canonical manifest data.

```toon
checks[6]{check,exit,result}:
  "installer unit suite",0,"583 tests; 10 skipped"
  "tools unit suite",0,"93 tests"
  "docs_check",0,"146 files; 8 exempt; 36 warnings"
  "manifest_check",0,"0 findings; 667 tracked files scanned; 63 skipped"
  "independent r2 probes",0,"162 crash boundaries plus double failures, lock, sync and encoding checks pass"
  "extra probes",0,"concurrency passes; R3-01 uncaught exception reproduced; later recovery passes"
```

Run from the clone root; all listed script exits are 0. The extra probe's exit 0 means the defect was reproduced, not review approval. Logs and scripts are outside the clone in `/tmp/pr42-rev-r3/`.

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
/usr/bin/python3 -m unittest discover -s tools/tests
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-r3/probe.py
/usr/bin/python3 /tmp/pr42-rev-r3/extra.py
```

The untracked review was checked directly with `docs_check.check_file` (0 errors). Only this report is added to the clone; no commit, push, merge, approval or closure is performed. One Japanese PR comment reports the verdict. Existing runtime/.env and the grdm-dev Docker stack were not accessed or changed; fixtures use temporary synthetic credentials. Real PostgreSQL migration, Linux ownership, amd64, physical power loss and browser acceptance were not independently exercised. The matrix models process interruptions, not filesystem persistence or live Docker kills.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と指摘

**要修正（changes requested）。R3-01 · P2: `db upgrade` の復旧中の OSError を終了 15 にする。** [database.py](../../installer/grdm_dev/database.py) の `run_upgrade`（751–760 行）は `UpgradeError` だけを捕捉するが、`_upgrade_locked` は後段の例外処理より前（765 行）で `recover` を呼ぶ。二つの改名が完了し操作記録が残っている状態で、`recover` の `_fsync_dir(current.parent)`（608 行）が EIO になると、実際の `cli.main` から未捕捉の OSError が出る。CLI が捕捉するのは KeyboardInterrupt だけである。今回の fsync 失敗を伝える修正でこの経路が表面化した。`run_recover` と `run_rollback` は両例外を捕捉済みである。

独立再現では、切替直前の有効な操作記録を作り、二つの改名だけを完了させた（記録作成前のクラッシュ後に相当）。volumes 親の同期へ EIO を注入し、疑似 Docker を使って `cli.main(['--root', fixture_root, '--yes', 'db', 'upgrade'])` を呼ぶと、15 を返さず OSError が出た。現行は PostgreSQL 18、操作記録も残り、障害を除いた後の `db recover` は成功する。観測したのは終了値の契約違反であり、データ喪失や誤起動ではない。ロック内の初回復旧を含む全体で OSError を捕捉し、操作記録を保持して 15 を返すこと。この状態をコマンド入口から試験すること。

### R2 の解決と回帰確認

- **R2-01 解決。** upgrade/rollback とも置換・補償の改名が二重に失敗すると終了 15 で記録を保持した。障害が続く間は `up` と復旧を拒否し、除去後は期待する版へ復旧して記録が消える。
- **R2-02 解決。** 記録なしでも共通ロックが `up` を拒否し、rollback の確認中も排他が続く。Compose 起動、reset の停止・削除中に三つの DB 操作を割り込ませる独立試験はすべて 15 で拒否した。提供試験は逆向きの reset と別プロセスの競合も検証する。独立試験で実 Docker コマンドは実行していない。
- **R2-03 元の再現は修正済み、R3-01 が残る。** upgrade/rollback の復旧改名で記録削除前に volumes 親を同期し、EIO も無視しなくなった。提供された順序・同期失敗の試験も合格した。文書にある EINVAL/ENOTSUP の例外扱いは意図的である。プロセスクラッシュ試験は電源断の永続化を証明しない。
- **R2-04 解決。** 非 ASCII の PG_VERSION は `up` から終了 15 になり Compose は起動しない。提供試験は補助コンテナ出力のデコード失敗も確認する。

元の 162 箇所（upgrade 128、rollback 34）の試験は同じ件数で全件合格した。観測した Docker 呼出し、永続 JSON 書込み、rename/replace、fsync、mkdir/unlink、snapshot、起動待ち、復元ファイル作成、記録削除の前後で捕捉不能な例外を注入する。復旧後に現行版が読めること、記録と追跡サーバーが残らないこと、現行 18 なら upgrade 記録があることを検査した。二重障害と競合は別途試験した。ADR-12 は容量不足の切替前後の結果を区別し、ADR-13 は見出しを所有者の選択記録に合わせた。対象差分に他の必須修正は見つからなかった。

### 検証と限界

クリーン clone は `/tmp/pr42-rev-r3/repo`、システム Python は `/usr/bin/python3` 3.9.6。次はレビュー測定であり manifest の正本ではない。

```toon
checks[6]{check,exit,result}:
  "installer 単体試験",0,"583 件; 10 件スキップ"
  "tools 単体試験",0,"93 件"
  "docs_check",0,"146 ファイル; 例外 8; 警告 36"
  "manifest_check",0,"指摘 0; 追跡 667 ファイル走査; 63 件スキップ"
  "独立 r2 試験",0,"162 クラッシュ箇所と二重障害・排他・同期・文字コード試験に合格"
  "追加試験",0,"競合試験合格; R3-01 の例外を再現; 後続復旧は成功"
```

再現コマンドは英語節と同じで clone のルートから実行する。各スクリプトの終了値は 0。追加試験の 0 は不具合の再現成功であり、レビュー合格ではない。ログとスクリプトは clone 外の `/tmp/pr42-rev-r3/` に置いた。

未追跡のレビューは `docs_check.check_file` で直接検査し、エラー 0 を確認した。clone 内への追加はこの記録のみで、commit・push・merge・approve・close は行わない。日本語の PR コメント一件で判定を報告する。既存 runtime/.env と grdm-dev の Docker 状態にはアクセスも変更もしておらず、試験の資格情報は一時ディレクトリの疑似値である。実 PostgreSQL 移行、Linux 所有権、amd64、物理電源断、ブラウザ受入は独立検証していない。この行列はプロセス中断の模擬であり、ファイルシステム永続化や実 Docker の kill ではない。
