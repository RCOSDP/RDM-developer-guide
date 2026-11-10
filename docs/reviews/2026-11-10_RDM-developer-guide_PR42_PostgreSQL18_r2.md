# PR42 PostgreSQL 18 review r2 / PostgreSQL 18 レビュー r2

> **Summary:** Changes requested. Ordinary interruption recovery improves substantially, but recovery can discard its journal after failed compensation, and lifecycle operations do not share the migration lock throughout their critical sections.
> **概要:** 要修正。通常の中断復旧は大きく改善したが、補償失敗後に復旧記録を捨てる経路があり、起動・リセットとの排他も完結していない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** recovery itself needs failure tests and durability ordering; a journal and a lock are insufficient when a recovery error deletes the journal or another command bypasses the lock. ／ 復旧自身にも障害試験と永続化の順序が要る。復旧の失敗で記録を削除したり、別コマンドがロックを迂回したりすると、記録とロックがあるだけでは守れない。
- Applies to: RCOSDP/RDM-developer-guide PR #42, diff `2b6a02a..5780b16`, head `5780b16e1592c070f62de6a56832b50c1914e649`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-10_RDM-developer-guide_PR42_PostgreSQL18_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md) · [ADR-13](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and required changes

**Changes requested.** All supplied unit suites pass on system Python, but the independent probes reproduce two unsafe recovery/concurrency cases. References are to [database.py](../../installer/grdm_dev/database.py) and [lifecycle.py](../../installer/grdm_dev/lifecycle.py) at the reviewed head.

1. **R2-01 · P1 — Keep the journal if compensation also fails (R1-01 remains open).** `recover` lines 576–581 and 589–594 catch every `OSError` from `_swap` and delete the journal while claiming the current directory is unchanged. `_swap` lines 606–611 can raise because both the replacement rename and the compensating rename failed, leaving the current directory absent. Reproduction: crash before the first swap rename, then recover with the first rename successful and the next two returning EIO. Both upgrade and rollback recovery return **0**, with **no current directory and no journal**. A later `up` can treat that missing directory as a new installation. Distinguish a verified compensated result from an incomplete swap; preserve the journal and return 15 unless the actual directory state establishes a safe completed outcome. Cover repeat failures during recovery, including failed compensation.

2. **R2-02 · P1 — Serialize lifecycle changes with migration, including the period before journal creation (R1-02 remains open).** `recover_pending` lines 627–631 bypasses the lock when no journal exists, and releases it before `up` starts Compose or `reset` deletes volumes. Upgrade/rollback check running services before confirmation and before writing the journal. A second `up` can therefore start PostgreSQL after rollback checked for stopped services but before rollback swaps its data directories. An injected interleaving at `Context.confirm` reproduced a Compose `up` call while rollback held its lock; rollback then returned 0 and replaced the current 18 directory with 9.6. A simpler held-lock/no-journal probe also reached Compose. The fake health result was exit 40, not a DB refusal; no real server was started. Make lifecycle and DB commands use the same lock even when no journal exists, and hold it through the start/deletion operation and necessary checks. Test both directions of the race and `reset`.

3. **R2-03 · P1 — Persist recovered renames before retiring the journal (R1-01 remains open).** Recovery's direct renames at lines 571, 573 and 596 never sync the volumes parent before writing the record and deleting the journal. The normal `_swap` path does sync it, showing the intended ordering. A probe recovering a crash between the two renames observed exit 0 and no volumes-parent sync for both upgrade and rollback. On a power loss, the record/journal deletion can survive without the recovered directory rename; process-exception tests cannot prove power-loss durability. Also `_fsync_dir` lines 284–294 silently ignores open/fsync errors, so even the initial write-ahead journal may be treated as durable after EIO. Sync every affected directory before declaring recovery complete, propagate unexpected durability errors while retaining recoverability, and test sync failures and ordering. No physical power-loss test was performed; the missing ordering is established by code inspection and call instrumentation.

4. **R2-04 · P2 — Convert invalid encoding in PG_VERSION into exit 15 (R1-04 partially open).** `data_major` line 184 reads ASCII but catches only filesystem exceptions. A PG_VERSION containing byte `0xff` raises an uncaught `UnicodeDecodeError` through `up`; it does not return the documented refusal code 15. Compose is not reached, so this is an error-contract defect rather than a fail-open start. Treat decoding failures as an unknown version and add a test through the command entry point.

### R1 closure and owner decisions

**R1-03 closed for the reviewed scope:** disk capacity is checked before source startup; same/different filesystem budgets include both dump copies, the replacement cluster and margins; the documentation states the estimate is not a guarantee. Supplied low-space and ENOSPC tests pass. **R1-05 closed:** the SQL includes `is_called`, database snapshots use a separate namespace from roles, and tests detect a changed `roles` database and sequence state. Snapshot equality is correctly limited to counts/state/names/selected role attributes, not row-content equality. R1-01/R1-02 remain open for the findings above; R1-04 is otherwise improved and fails closed for ordinary unreadable, missing-in-nonempty and malformed ASCII cases.

ADR-13 now records the owner's choices: Elasticsearch 8 with full-text search; the file-page editor on y-websocket before retiring sharejs/mongo; MFR freecad removal and allow-listing distribution packages without fixes. These are recorded choices, not implementations validated by PR #42. The draft export/discard decision remains for the migration work. The narrower claims about affected code size, probed endpoints and the wiki draft reader address r1; prototype measurements are explicitly author-reported. Minor editorial inconsistency: the header still says “Records a decision for: nothing yet” although §4 records choices; align that line while retaining the distinction between chosen direction and the Proposed record. No further owner approval is inferred by this review.

ADR-12's unconditional claim that a crash at any point is recoverable is premature until R2-01–03 are resolved. Its disk paragraph also says a full disk leaves the old cluster in place, while the supplied post-swap ENOSPC tests intentionally finish the new cluster; describe both safe recovery outcomes.

### Validation and limits

Clean clone: `/tmp/pr42-rev-r2/repo`; system interpreter: `/usr/bin/python3` 3.9.6. These are review measurements, not canonical manifest data.

```toon
checks[5]{check,exit,result}:
  "installer unit suite",0,"573 tests; 10 skipped"
  "tools unit suite",0,"93 tests passed"
  "docs_check before report",0,"145 files; 8 exempt; 36 warnings"
  "manifest_check",0,"0 findings; 666 tracked files scanned; 63 skipped"
  "independent synthetic probes",0,"single-crash boundaries recover; repeated rename failure, lock bypass, missing directory sync and decode exception reproduced"
```

The independent script exercised 162 injected crash boundaries (128 upgrade, 34 rollback), all recovered under the single-crash model. It wraps both sides of every observed Docker call, durable JSON write, rename/replace, fsync, mkdir/unlink, snapshot, readiness check, restore-file construction and journal removal in successful upgrade and rollback traces. Each injected uncatchable exception is followed by recovery and checks for a readable current major, no pending journal, no tracked server and an upgrade record when current is 18. It also probes repeated recovery failures and the lifecycle interleaving. This is a synthetic process-crash model, not emulated filesystem persistence or a real kill of Docker. Supplied tests additionally cover catchable interruption, SIGTERM, stop/removal failures, a competing DB process, disk checks and inventory comparisons.

Logs and runnable probe are `/tmp/pr42-rev-r2/{units,tools-units,docs,manifest,probe}.log` and `/tmp/pr42-rev-r2/probe.py`. Reproduce from the clone root; expected exits are 0 (probe exit 0 means the reported behavior was reproduced, not that the implementation passed review):

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
/usr/bin/python3 -m unittest discover -s tools/tests
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-r2/probe.py
```

No real grdm-dev Docker state or existing runtime/.env was accessed; unit fixtures use temporary synthetic credentials. No commit, push, approval, merge or closure was performed. Real migration, SQL execution on both PostgreSQL versions, Linux ownership, amd64 execution, power-loss persistence and browser acceptance were not independently exercised. The real-operation evidence in ADR-12 remains author-reported. The untracked report was also checked directly with `docs_check.check_file` (0 errors). Only this review file is added to the clone; the probe and logs are outside it.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と必須修正

**要修正（changes requested）。** システム Python で提供された単体試験はすべて合格したが、独立試験で復旧と競合の危険な経路を再現した。行番号は対象 head の [database.py](../../installer/grdm_dev/database.py) と [lifecycle.py](../../installer/grdm_dev/lifecycle.py) を指す。

1. **R2-01 · P1 — 補償も失敗した場合は記録を保持する（R1-01 未解決）。** `recover` 576–581、589–594 行は `_swap` の全 `OSError` を捕捉し、現行は無変更と報告して記録を削除する。しかし `_swap` 606–611 行は、置換の改名と補償の改名が両方失敗し、現行が消えた場合にも例外を送出する。最初の改名前にクラッシュさせ、次の復旧で一回目だけ成功、二・三回目を EIO にすると、upgrade と rollback の両方で **終了 0、現行パスなし、記録なし** となった。後続 `up` は新規環境として扱い得る。補償成功を実際のディレクトリ状態で確認し、不完全なら記録を保持して終了 15 にすること。復旧中の再障害・補償失敗を試験すること。

2. **R2-02 · P1 — 記録作成前も含め、起動・リセットと移行を排他にする（R1-02 未解決）。** `recover_pending` 627–631 行は記録がなければロックを取らず、記録があっても Compose 起動やボリューム削除前に解放する。upgrade/rollback は停止検査後に確認を求め、その後で記録を書く。この間に別の `up` が起動すると、rollback は使用中のデータを改名する。`Context.confirm` で割り込ませると、rollback がロック保持中にも Compose `up` に到達し、rollback は終了 0 で現行を 18 から 9.6 へ替えた。ロックだけを保持する試験でも起動に到達した。疑似 health の終了値は 40 であり DB 拒否ではない。実サーバーは起動していない。記録の有無によらず共通ロックを取り、必要な検査から起動・削除まで保持すること。逆順の競合と `reset` も試験すること。

3. **R2-03 · P1 — 復旧改名を永続化してから記録を捨てる（R1-01 未解決）。** 復旧の直接改名（571、573、596 行）には volumes 親の同期がなく、記録更新・削除へ進む。通常の `_swap` は同期している。二回の改名の間でクラッシュさせた後の復旧では、upgrade/rollback とも終了 0 だが volumes 親の同期は一度もなかった。電源断で記録更新・削除だけが残り、改名が残らない可能性がある。さらに `_fsync_dir` 284–294 行は open/fsync の失敗を無視し、先行記録の EIO でも永続化済み扱いになる。影響する親を同期してから完了とし、予期しない永続化失敗を返して復旧可能性を残すこと。同期の失敗と順序を試験すること。物理的な電源断は行っておらず、コードと呼出し記録で順序の欠落を確認した。

4. **R2-04 · P2 — PG_VERSION の文字コード不正も終了 15 にする（R1-04 一部未解決）。** `data_major` 184 行は ASCII で読むが、捕捉するのはファイルシステムの例外だけである。`0xff` を含む PG_VERSION では `up` から未捕捉の `UnicodeDecodeError` が出る。Compose には到達しないため、誤起動ではなく終了値の契約違反である。版不明として扱い、コマンド入口から終了 15 を試験すること。

### R1 の解決状況と所有者の判断

**R1-03 は今回の範囲で解決。** 旧サーバー起動前に容量を検査し、同一／別ファイルシステムで二つのダンプ・新クラスタ・余裕を計算する。固定倍率は保証ではないと明示され、空き不足・ENOSPC の試験も合格した。**R1-05 は解決。** SQL は `is_called` を含み、DB とロールの名前空間を分け、`roles` DB とシーケンスの変化を検出する。比較は行数・状態・名前・一部ロール属性までで、行内容の同一性は保証しないと明記した。R1-01/R1-02 は前記の理由で未解決。R1-04 は通常の読取り不能・非空ディレクトリの版欠落・不正な ASCII については拒否するよう改善した。

ADR-13 は所有者の選択として、全文検索を維持した Elasticsearch 8、sharejs/mongo 退役前のファイルエディタの y-websocket 移行、MFR freecad 撤去と配布元の修正がない OS パッケージの許容を記録した。PR #42 が実装・検証した結果ではない。下書きの書出し／破棄は移行作業で決める事項として残る。影響コード量・測定した入口・wiki の下書き reader へ主張を狭め、試作の測定を著者報告とした点は r1 に対応する。軽微な文言として、§4 に選択を記録しながらヘッダは “Records a decision for: nothing yet” のままなので、方向の決定と記録の Proposed 状態を区別して整合させたい。このレビューが追加の所有者承認を与えるものではない。

ADR-12 の「どの時点のクラッシュも復旧」は R2-01–03 解決前には強すぎる。また容量不足なら旧クラスタがそのまま残るとの記述に対し、切替後 ENOSPC の単体試験は新版への復旧完了を期待する。安全な二つの復旧結果を説明すること。

### 検証と限界

独立クローンは `/tmp/pr42-rev-r2/repo`、システム Python は `/usr/bin/python3` 3.9.6。次はレビュー測定であり manifest の正本ではない。

```toon
checks[5]{check,exit,result}:
  "installer 単体試験",0,"573 件; 10 件スキップ"
  "tools 単体試験",0,"93 件合格"
  "記録追加前 docs_check",0,"145 ファイル; 例外 8; 警告 36"
  "manifest_check",0,"指摘 0; 追跡 666 ファイル走査; 63 件スキップ"
  "独立疑似試験",0,"単発クラッシュから復旧; 連続改名失敗・ロック迂回・親同期欠落・デコード例外を再現"
```

独立スクリプトは 162 箇所（upgrade 128、rollback 34）にクラッシュを注入し、単発クラッシュモデルでは全件復旧した。成功する upgrade/rollback の全観測 Docker 呼出し、永続 JSON 書込み、rename/replace、fsync、mkdir/unlink、snapshot、起動待ち、復元ファイル作成、記録削除の前後に捕捉不能の例外を注入した。次回復旧で現行版が読めること、記録と追跡サーバーが残らないこと、現行 18 なら upgrade 記録があることを検査した。復旧の連続障害と起動の割込みも試した。これは疑似プロセスクラッシュであり、ファイルシステム永続化の模擬や実 Docker の kill ではない。提供試験では通常の中断、SIGTERM、停止・削除失敗、別 DB プロセス、容量、照合も検証した。

ログは `/tmp/pr42-rev-r2/{units,tools-units,docs,manifest,probe}.log`、再現用スクリプトは `/tmp/pr42-rev-r2/probe.py`。クローンのルートで次を実行すると全コマンドの期待終了値は 0。probe の 0 は問題の再現成功であり、レビュー合格ではない。

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
/usr/bin/python3 -m unittest discover -s tools/tests
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-r2/probe.py
```

実 grdm-dev の Docker 状態と既存 runtime/.env には触れていない。単体試験の資格情報は一時ディレクトリの疑似値である。コミット・push・承認・マージ・close は行っていない。実移行、両 PostgreSQL 版での SQL 実行、Linux 所有権、amd64、電源断の永続化、ブラウザ受入は独立検証していない。ADR-12 の実運用測定は著者報告として扱う。未追跡のレビュー記録も `docs_check.check_file` で直接検査し、エラー 0 を確認した。クローン内への追加はこのレビューのみで、probe とログは外に置いた。
