# PR42 PostgreSQL 18 review r1 / PostgreSQL 18 レビュー r1

> **Summary:** Changes requested. Failure recovery can leave the active data directory missing or a migration server running, and the version guard fails open when the version cannot be read.
> **概要:** 要修正。障害復旧で稼働用データディレクトリが消えた状態や移行用サーバーが動いた状態が残り、版を読めない場合は起動の防護も通過する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** successful restore checks do not establish recoverability across directory renames and process interruption. ／ 復元の検査が成功しても、ディレクトリの改名やプロセス中断をまたぐ復旧可能性は証明されない。
- Applies to: RCOSDP/RDM-developer-guide PR #42, head `2b6a02a741b68cdf4bedfc369801ccb2bb0a8d68`; REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-02](../spec/02_installer_cli.md) · [ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md) · [ADR-13](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md)
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** Review used a clean scratch clone and synthetic fake-runner probes. No real Docker stack, existing runtime secrets, main checkout, commits, pushes, approvals or merges were used. Both ADRs remain Proposed; this review does not approve the owner decisions. Real migration, Linux uid 999 ownership, amd64 execution, image registry contents and browser acceptance were not independently exercised.

### Required changes

1. **R1-01 · P1 — Make swap and rollback recoverable.** In [database.py](../../installer/grdm_dev/database.py), lines 458–474 rename the current directory away, rename the replacement in, and only then write `upgrade.json`. Failure of the second rename returns 15 while claiming the current directory is unchanged, but that directory is absent. A fault-injection probe reproduced exactly this state with no rollback record. A failure writing the record after both renames raises an uncaught `OSError` and leaves a completed swap without its rollback record. Rollback lines 501–506 have the same two-rename gap. A subsequent `up` can interpret an absent path as a fresh installation. Persist a durable operation journal before mutation, recover or refuse incomplete operations, compensate recoverable rename failures, and prevent `up` from initializing a missing path during pending recovery. Add failure tests at both renames and at each journal write, including rollback. Individual renames do not make the pair atomic.

2. **R1-02 · P1 — Verify shutdown and handle interruption before releasing migration ownership.** `_stop` (lines 280–283) ignores both return codes; lines 420–421 and 455–456 remove the server from tracking regardless. A probe returning failure for every stop/remove still completed the upgrade with exit 0 and a success record. The exception handler catches neither `KeyboardInterrupt` nor termination signals: interrupting dump left zero stop calls. The standalone migration servers are outside the Compose project checked by `_no_running_services`. Consequently a later command can start a second server against the same directory after interruption or failed shutdown, risking corruption. Require successful shutdown plus state verification before swapping; keep ownership tracking on failures; add cleanup for catchable interruption and a persistent lock/journal that blocks `up`, upgrade and rollback after a crash. Test interruption during source start, dump, destination start, restore, verification and swap. Forced termination needs recovery on the next invocation, not just a `finally` block.

3. **R1-03 · P2 — Check disk capacity before starting the source.** Lines 399–415 start the old cluster without a disk-space check. Both `dumpall.sql` and its near-identical `restore.sql` remain alongside the new cluster and the old directory. ADR-12 §4's “twice the data” wording does not account clearly for two logical dump copies, new indexes and WAL, or separate filesystems for backups and volumes. Exhaustion can also prevent the post-swap record write described in R1-01. Check both destination filesystems with a conservative margin before any source startup, explain the estimate and its limitations, and test ENOSPC in dumping, filtering, restore and journal writes. Do not promise that a fixed multiple of physical cluster size is sufficient for arbitrary data.

4. **R1-04 · P2 — Fail closed on an unreadable version.** `preflight` lines 157–159 treat `None` (failed inspection) like `''` (no cluster). A probe supplying an unreadable version returned `None`, permitting Compose instead of exit 15. This matters particularly for uid 999 directories when the helper container fails to run. Distinguish an established empty directory from an unknown version and refuse unknown/unparseable versions before Compose; test the fallback's failure as well as its success.

5. **R1-05 · P2 — Cover the promised sequence and database inventory.** `SNAPSHOT_SQL` lines 64–74 records only sequence `last_value`, not `is_called`, even though identical values with different `is_called` yield different next IDs. `snapshot` line 248 overwrites a real database named `roles` with the role-name list, removing its table/sequence checks completely. Separate the database and role namespaces and compare sequence state including `is_called`; test both cases. Counts, extension names and role names are useful checks but do not prove row-content equality, role attributes or extension versions. State that boundary accurately rather than claiming that snapshot equality means every row moved intact. Normal `pg_dumpall`/`ON_ERROR_STOP` restoration is a sound starting point; these findings concern the advertised verification guarantee.

### Authentication, hardening and documentation

**MD5 judgment:** acceptable only as a temporary, explicitly accepted compatibility exception for this isolated developer network, not as a general security claim about internal networks. PostgreSQL documents MD5 as weaker and deprecated; an MD5 HBA rule automatically negotiates SCRAM for roles whose stored verifier is SCRAM. Separate CAS and osf.io login roles therefore permit CAS MD5 and osf.io SCRAM concurrently, after verifying osf.io's actual libpq supports SCRAM and resetting its password with SCRAM encryption. Merely changing a role setting does not convert an existing verifier. Currently `compose.py` lines 878 and 963–967 give both clients the same `postgres` role, so separation and credential/configuration changes are prerequisites. JDBC 42.2 introduced SCRAM for Java 8+, but a supported patched driver should be selected rather than treating the historical minimum as the upgrade target. Sources: [PostgreSQL password authentication](https://www.postgresql.org/docs/18/auth-password.html), [JDBC 42.2 release](https://www.postgresql.org/about/news/jdbc-4220-released-1825/).

**Pinning and permissions:** the target manifest and source-image constant contain full SHA-256 pins. The template retains explicit PGDATA and the parent tmpfs. Migration servers use no network, no TCP listener, read-only roots, no-new-privileges and the five documented capabilities; the version helper uses uid 999 and a read-only mount. Backup mode 0700 and files 0600 are appropriate. The password is passed through an env file rather than argv, and the normal application report does not print it. These static checks do not verify registry digest provenance or Linux execution. Also test restoration failures for sensitive SQL/COPY data in PostgreSQL container logs: suppressing Python subprocess output alone cannot establish the requirement that secrets never reach logs.

**ADR-13 accuracy:** pinned osf.io source was read through GitHub at `fe90e5c39e660f464bb8fcc9ae4028119b958d19`. The search decorator returns `None` with search disabled, ES2 code uses typed documents and filtered queries, wiki defaults build the Mongo URL from PostgreSQL settings unless explicitly overridden, and the file editor uses ShareJS and independently saves text by HTTP PUT. These support the broad migration concerns. However, the failed wiki draft reader does not prove that no ShareJS draft content ever reached saved files: narrow that claim to the measured wiki reader. Treat about 5,300 lines as the affected code surface, not a measured requirement to rewrite every line, and “every page loads” as limited to the measured endpoints. The prototype patch, complete measurement logs and post-PR40 browser result were not available in this PR, so their numerical and universal claims remain author-reported. No Mongo or ES service is removed by this PR. The new ADRs have bilingual sections and Proposed status; docs_check passes. ADR-12's inline operational command sequence should become a fenced procedure with working directory and expected results under SPEC-06 §3, and its unconditional failure/unchanged-directory promises must be corrected with R1-01/R1-02.

### Validation evidence

These are review measurements, not canonical manifest data. System Python was `/usr/bin/python3` 3.9.6.

```toon
checks[5]{check,exit,result}:
  "full unit suite",1,"431 tests; 12 errors; 10 skipped"
  "database unit suite",0,"17 tests passed"
  "docs_check before review",0,"144 files; 8 exempt; 37 warnings"
  "manifest_check",0,"0 findings; 665 tracked files scanned"
  "synthetic failure probes",0,"second rename leaves current absent; stop failures report success; interruption skips cleanup; journal failure escapes; unknown version allowed"
```

All 12 suite errors arise from the Python 3.9-incompatible annotation in `test_compose.py:38` and dependent imports. That file is unchanged from base `48d0134347e681c00ebb95246eab26f9e7de3c92`; the full suite is nevertheless **not green** on system Python. The database tests do pass. Logs and the isolated probe script are in `/tmp/pr42-rev-yvCJXJ/`; they contain synthetic fixtures only.

Reproduce from the scratch clone root; expected exits are shown in the measurement block:

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests -p test_database.py
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-yvCJXJ/probe.py
```

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**要修正（changes requested）。** 作業用の独立クローンと疑似 runner による障害注入を使った。実 Docker スタック、既存の runtime の秘密情報、主チェックアウトには接触せず、コミット・push・承認・マージを行っていない。両 ADR は Proposed のままで、所有者の判断を承認していない。実移行、Linux の uid 999 所有、amd64 実行、レジストリ内のイメージ内容、ブラウザ受入は独立に実施していない。

### 必須修正

1. **R1-01 · P1 — 切替と巻戻しを復旧可能にする。** [database.py](../../installer/grdm_dev/database.py) 458–474 行は現行ディレクトリを退避し、新ディレクトリを移し、その後で初めて `upgrade.json` を書く。二回目の改名に失敗させると終了 15 だが、報告の「現行は無変更」に反して現行パスが消え、巻戻し記録も無かった。切替後の記録書込み失敗は未捕捉の `OSError` となる。巻戻しの 501–506 行にも二回の改名の隙間がある。後続の `up` が空の新規環境と解釈しかねない。変更前に永続的な操作記録を書き、不完全な操作を復旧するか拒否し、回復可能な改名失敗を補償すること。復旧待ちの `up` に初期化させないこと。両改名と各記録書込みの失敗を巻戻しも含めて試験する。一回ずつの改名が原子的でも、二回全体は原子的ではない。

2. **R1-02 · P1 — 停止を検証し、中断後も移行の占有を管理する。** `_stop`（280–283 行）は停止と削除の終了値を無視し、呼出し側は成功扱いで追跡対象から外す。すべての停止・削除を失敗させても移行は終了 0 と成功記録になった。ダンプ中の `KeyboardInterrupt` では停止呼出しが一度も無かった。例外処理はこれや終了シグナルを扱わず、単独起動した移行サーバーは Compose の稼働検査の外にいる。そのため次のコマンドが同じディレクトリに二つ目のサーバーを起動し、破損する危険がある。切替前に停止成功と状態確認を要求し、失敗時は追跡を保持すること。捕捉可能な中断の cleanup と、クラッシュ後に `up`・upgrade・rollback を止める永続ロック／操作記録が必要。旧版起動・ダンプ・新版起動・復元・照合・切替の各段階で中断試験を行うこと。強制終了には次回の復旧が必要で、`finally` だけでは足りない。

3. **R1-03 · P2 — 旧版起動前に空き容量を検査する。** 399–415 行には容量検査がない。新旧クラスタに加えて、ほぼ同じ内容の `dumpall.sql` と `restore.sql` の両方が残る。ADR-12 §4 の「データの二倍」では二つの論理ダンプ、新しい索引、WAL、バックアップとボリュームが別ファイルシステムの場合を明確に説明していない。容量不足は R1-01 の切替後の記録にも影響する。両保存先に保守的な余裕を見て事前検査し、見積りの限界を説明すること。ダンプ・加工・復元・記録の ENOSPC を試験し、物理サイズの固定倍率で任意のデータに十分とは約束しないこと。

4. **R1-04 · P2 — 版の読取り失敗を拒否する。** `preflight` 157–159 行は `None`（検査失敗）を空文字（クラスタなし）と同じ扱いにする。読取り不能を与えると拒否理由なしになり、終了 15 でなく Compose へ進めた。uid 999 所有のパスで補助コンテナが起動できない場合に問題となる。空であると確認できた場合と不明な場合を区別し、版不明・解析不能なら Compose 前に拒否すること。代替読取りの成功だけでなく失敗も試験すること。

5. **R1-05 · P2 — シーケンスと DB 一覧の検証範囲を補う。** 64–74 行は `last_value` のみを記録し、次に発行される ID を変える `is_called` を比較しない。248 行は実在する `roles` という DB の検査結果をロール名一覧で上書きし、その表とシーケンスの比較を失う。DB とロールの名前空間を分け、`is_called` を含めて比較し、両例を試験すること。行数・拡張名・ロール名の比較は有用だが、行内容、ロール属性、拡張の版の一致まで証明しない。比較一致が全行の完全な移行を意味するという表現を狭めること。通常の `pg_dumpall` と `ON_ERROR_STOP` は妥当な出発点で、この指摘は検証保証の範囲に対するもの。

### 認証・堅牢化・文書

**MD5 の判断:** この隔離された開発ネットワークに限定し、明示的に受容する暫定互換性例外としては許容できる。内部ネットワーク一般の安全性を保証するものではない。PostgreSQL は MD5 を弱く非推奨とし、MD5 の HBA 規則でも保存済み検証子が SCRAM なら SCRAM を選ぶ。従って CAS と osf.io のログインロールを分け、osf.io の実際の libpq の対応を確認して SCRAM 形式でパスワードを設定し直せば併存できる。ロールの設定値だけ変えても既存検証子は変換されない。現状は `compose.py` 878、963–967 行で両者が `postgres` を共用しているため、ロール分離と資格情報・設定変更が前提。JDBC 42.2 は Java 8 以降向けに SCRAM を導入したが、更新先は歴史的最低版でなく保守済み修正版を選ぶべきである。根拠: [PostgreSQL 認証仕様](https://www.postgresql.org/docs/18/auth-password.html)、[JDBC 42.2 リリース](https://www.postgresql.org/about/news/jdbc-4220-released-1825/)。

**固定と権限:** 移行先 manifest と移行元定数は完全な SHA-256 固定を持つ。テンプレートは明示的 PGDATA と親 tmpfs を維持する。移行サーバーはネットワーク・TCP なし、読取り専用 root、no-new-privileges、記録済みの五 capability を使う。版読取りは uid 999 と読取り専用 mount を使う。バックアップ 0700、ファイル 0600 は適切。通常経路では秘密値は argv でなく env file を通り、アプリケーションの報告に出ない。ただしレジストリの真正性や Linux 実行を確認したわけではない。復元失敗時に秘密を含む SQL/COPY データが PostgreSQL コンテナログへ出ないことも試験すべきで、Python 側の subprocess 出力を捨てるだけではログへの秘密流出禁止を証明できない。

**ADR-13 の正確さ:** osf.io の固定コミット `fe90e5c39e660f464bb8fcc9ae4028119b958d19` の関連ソースを GitHub 経由で読んだ。無効時に検索 decorator が `None` を返すこと、ES2 の型と filtered query、環境変数で上書きされなければ PostgreSQL 設定から Mongo URL を組み立てる wiki 設定、ShareJS を使いつつ HTTP PUT で保存するファイルエディタは、移行上の懸念を裏付ける。ただし wiki の draft reader の失敗から、ShareJS の下書き内容が保存済みファイルに一度も到達していないとは証明できない。測定した wiki reader に主張を限定すること。約 5,300 行は影響するコード範囲であり全行書直しの実測量ではない。「すべてのページが表示」は測定した入口に限るべきである。試作パッチ、完全な測定ログ、PR40 後のブラウザ結果は PR 内にないため、数値と普遍的な主張は著者報告のまま。今回 Mongo/ES の撤去はない。新 ADR は英和構成と Proposed を備え docs_check は通る。ADR-12 のインライン操作列は SPEC-06 §3 に従う実行場所・期待結果付き fenced 手順にし、無条件の「失敗時無変更」の約束は R1-01/R1-02 と一緒に修正すること。

### 検証結果

レビューでの測定であり manifest の正本データではない。システム Python は `/usr/bin/python3` 3.9.6。

```toon
checks[5]{check,exit,result}:
  "全単体試験",1,"431 件; エラー 12; スキップ 10"
  "database 単体試験",0,"17 件合格"
  "記録追加前 docs_check",0,"144 ファイル; 例外 8; 警告 37"
  "manifest_check",0,"指摘 0; 追跡ファイル 665 件走査"
  "疑似障害注入",0,"第二改名失敗で現行消失; 停止失敗でも成功; 中断で cleanup なし; 記録失敗は未捕捉; 版不明を許可"
```

全試験の 12 エラーは Python 3.9 で解釈できない `test_compose.py:38` の型注釈とその依存 import に由来する。このファイルは base `48d0134347e681c00ebb95246eab26f9e7de3c92` から無変更だが、システム Python で全試験合格とは報告しない。database の 17 件は合格した。ログと独立 probe は `/tmp/pr42-rev-yvCJXJ/` にあり、疑似データのみを扱う。

独立クローンのルートで再現する。期待する終了値は測定表の通り。

```sh
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests
PYTHONPATH=installer /usr/bin/python3 -m unittest discover -s installer/tests -p test_database.py
/usr/bin/python3 tools/docs_check.py
/usr/bin/python3 tools/manifest_check.py
/usr/bin/python3 /tmp/pr42-rev-yvCJXJ/probe.py
```
