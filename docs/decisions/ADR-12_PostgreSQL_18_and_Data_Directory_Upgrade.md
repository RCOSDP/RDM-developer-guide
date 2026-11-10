# ADR-12 PostgreSQL 18 and the Data Directory Upgrade / PostgreSQL 18 とデータディレクトリの更新

> **Summary:** The developer environment moves from PostgreSQL 9.6 (end of life since 2021) to **PostgreSQL 18.6**, the newest released major, pinned by its index digest. osf.io's Django 1.11.28 with psycopg2 2.7.3 ran its migrations and 807 database tests on 18 with exactly the same outcome as on 9.6 (781 passed, the same 13 failed or erred on both), and CAS and fakecas logged in against it. CAS's JDBC driver 42.1.4 cannot answer SCRAM, so host authentication stays `md5` until CAS gets a newer driver. An existing 9.6 data directory is moved by a new command, `grdm-dev db upgrade`: a dump with the new major's `pg_dumpall` and a restore into a fresh directory, compared table by table, with the old directory kept beside it for `grdm-dev db rollback`; a durable journal and a lock shared with `up` and `reset` let the next command finish or roll back a process crash at any point (tested by injection at every boundary); durability across power loss rests on fsync ordering and was not tested physically. `up` refuses a data directory of another major (exit 15).
> **概要:** 開発環境の PostgreSQL を 9.6（2021 年に EOL）から、リリース済みで最新の **PostgreSQL 18.6** へ移し、インデックスのダイジェストで固定する。osf.io の Django 1.11.28 と psycopg2 2.7.3 は 18 の上で migration と 807 件のデータベース試験を実行し、結果は 9.6 とまったく同じだった（781 件合格、両方で同じ 13 件が失敗かエラー）。CAS と fakecas も 18 に対してログインできた。CAS の JDBC ドライバー 42.1.4 は SCRAM に応えられないので、ホスト認証は CAS が新しいドライバーを持つまで `md5` のままにする。既存の 9.6 のデータディレクトリは新しいコマンド `grdm-dev db upgrade` で移す。新しい版の `pg_dumpall` でダンプし、新しいディレクトリへ復元し、表ごとに突き合わせ、旧ディレクトリは `grdm-dev db rollback` のために隣に残す。永続的な操作記録と、`up`・`reset` と共有するロックにより、どの時点のプロセスのクラッシュも次のコマンドが完了か巻き戻しできる（すべての境界で注入して試験）。電源断をまたぐ永続性は fsync の順序に依り、物理的には試験していない。`up` は別の版のデータディレクトリを拒む（終了 15）。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-10. **Learned:** recovery has failure modes of its own: a compensation can fail too, a rename is not durable until its directory is synced, and a lock that only some commands take excludes nothing; the journal is now retired only on a verified state, every recovery rename is synced before the record, and `up` and `reset` take the same lock (PR #42 review r2). ／ 復旧にも固有の失敗がある。補償も失敗しうるし、改名はそのディレクトリを sync するまで永続ではなく、一部のコマンドしか取らないロックは何も排除しない。そこで操作記録は確かめた状態でだけ消し、復旧の改名はすべて記録の前に sync し、`up` と `reset` も同じロックを取るようにした（PR #42 レビュー r2）。
  0.2 — 2026-11-10. **Learned:** a verified restore says nothing about a crash between two renames or a server that was never stopped: the operation now owns its containers and directories through a durable journal and a lock, every later `db` command, `reset` and `up` finish or roll it back, and a major that cannot be read is a refusal (PR #42 review r1). ／ 照合済みの復元は、二つの改名の間のクラッシュや止まらなかったサーバーについて何も言わない。そこで操作は永続的な操作記録とロックでコンテナとディレクトリを所有し、後続の `db` コマンド・`reset`・`up` が完了か巻き戻しを行い、読めない版は拒否にした（PR #42 レビュー r1）。
  0.1 — 2026-11-10. **Learned:** a database upgrade is proven by the clients, not by the server starting: the server and Django were fine on 18, while the CAS driver failed only once the password was stored as SCRAM, and PostgreSQL 18 rejected a catalogue query that 9.6 accepted (`text || "char"`), so the verification query itself had to be tested on both majors. ／ データベースの更新は、サーバーが起動したことではなくクライアントで証明される。サーバーと Django は 18 で問題なかったが、CAS のドライバーはパスワードが SCRAM で保存されたときにだけ失敗した。また PostgreSQL 18 は 9.6 が受け付けたカタログの問い合わせ（`text || "char"`）を拒んだので、照合の問い合わせ自体も両方の版で試す必要があった。
- Status: Proposed (2026-11-10, M5 groundwork); the owner approves. Review date: when CAS moves to a JDBC driver with SCRAM, or when PostgreSQL 19 is released.
- Records a decision for: [SPEC-02 §3](../spec/02_installer_cli.md#english) (`db`, the `up` refusal) and §6 (exit 15) · `manifest/upstreams.json` (`postgres`) · `installer/grdm_dev/templates/postgres.json`
- Related: [docs/decisions/README.md](README.md) · [ADR-07 Native builds of EOL middleware](ADR-07_Native_Builds_of_EOL_Middleware.md) · [ADR-13 Retiring Elasticsearch 2 and MongoDB](ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md) · [Status board](../status/README.md#english) · [SPEC-03 §3.3](../spec/03_security_gate.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

The milestone M5 on the [status board](../status/README.md#english) asks for PostgreSQL 15 or later. The stack ran `postgres:9.6`, which its maker stopped fixing in November 2021. Three programs talk to it:

```toon
clients[3]{client,driver,measured_in}:
  "osf.io (web, api, admin, worker, osf_init)","Django 1.11.28, psycopg2 2.7.3 linked against libpq 11.11","grdm-dev/osf.io:fe90e5c39e66"
  "CAS (cas-overlay)","PostgreSQL JDBC 42.1.4 under Hibernate 4.3.10 and c3p0","WEB-INF/lib of grdm-dev/cas-overlay:22610b7681a2"
  "fakecas","Go lib/pq v1.10.9","installer/images/fakecas/go.mod"
```

Django 1.11 documents PostgreSQL 9.3 and later with no upper bound, so only a measurement can say which major works. PostgreSQL 19 is still a beta on Docker Hub (`19beta1`), so 18 is the newest released major.

### 2. Decision

1. **Image.** `postgres:18.6` pinned by its index digest (`base_image_digest` in the manifest), for `linux/arm64` and `linux/amd64`. The one-shots `volume_owner_init` and `volume_access_check_*` run the same image; its GNU coreutils pass their checks (measured).
2. **Template.** The 18 image moved `PGDATA` to `/var/lib/postgresql/18/docker` and declares a volume at `/var/lib/postgresql`. The template sets `PGDATA=/var/lib/postgresql/data`, the mount point of `postgres_data`, and puts a tmpfs on `/var/lib/postgresql` so that Compose creates no anonymous volume there (measured: the container has only the data volume and the init-script mount).
3. **Authentication stays md5.** `POSTGRES_INITDB_ARGS` keeps `--auth-host=md5`; with it, initdb also writes `password_encryption = md5`, and the entrypoint's catch-all line is `host all all all md5`. With `scram-sha-256` instead, CAS failed every connection with `The authentication type 10 is not supported` (measured). SCRAM becomes the default when CAS ships a JDBC driver of 42.2 or later — a change in the integration repository and an owner item. PostgreSQL 18 logs a deprecation warning when an md5 password is set; it still works. This is a temporary compatibility exception accepted for this isolated developer network only, not a claim about internal networks in general. The way out (review r1): separate login roles for CAS and osf.io (both use `postgres` today), a SCRAM verifier set anew for osf.io's role (osf.io's libpq 11 supports SCRAM; changing `password_encryption` does not convert an existing verifier), and a currently patched JDBC driver for CAS rather than the historical minimum 42.2.
4. **Moving existing data: `grdm-dev db upgrade`.** A server refuses a data directory of another major, so the data is dumped and restored, never changed in place. The operation owns everything it creates through a journal, so that a process crash at any point leaves either the old or the new cluster usable, or — when even a compensating rename fails — keeps the journal so that `up` refuses and `db recover` retries (review r1 R1-01, R1-02; r2 R2-01):
   1. **Checks, nothing started yet.** Every service stopped (`grdm-dev down`); the data major readable and known; free disk measured on the backups and the volumes filesystems (§5); a confirmation (`--yes` skips).
   2. **Journal and lock.** `runtime/db-operation.json` is written (fsync, atomic rename) before any container, volume or directory exists, and names all of them. An exclusive `flock` on `runtime/db-operation.lock` is held for the whole operation, including the service check and the confirmation; `up` takes the same lock from its checks until Compose has started the containers, and `reset` from its checks until the deletion ends, so none of them can run between another's checks and its action (R2-02); the kernel releases it when the process ends, however it ends, so a second `db` command waits for no dead process. SIGTERM and SIGHUP are handled like Ctrl-C.
   3. **Source.** The old major (`postgres:9.6`, pinned by digest) starts on the existing directory with no network and no TCP listener; its socket is in a throwaway Docker volume. The new major's `pg_dumpall` (the PostgreSQL rule: dump with the newer client) runs as the host user and writes `runtime/backups/postgres-<old>-to-<new>-<timestamp>/dumpall.sql` (0600 in a 0700 directory). Then the old server is stopped, removed, and proved gone with `docker ps -a` before anything else starts; a failure to prove it keeps the journal.
   4. **Target.** The new major initialises `runtime/volumes/postgres_data.pg<new>-<timestamp>.new` with the rendered initdb arguments, `PGDATA` and command; the superuser password reaches initdb through a 0600 file deleted as soon as the container exists. The dump is restored with `ON_ERROR_STOP`; the only line removed is `CREATE ROLE postgres;` (initdb made that role; its `ALTER ROLE` with the old verifier stays). `vacuumdb --analyze-only` follows and the derived `restore.sql` is deleted. Both servers run with `log_min_error_statement=panic`, so a failing statement — which may carry row data or a password verifier — is not written to the container log.
   5. **Verification, and its limit.** Per database: every table's row count, every sequence's `last_value` and `is_called`, and the extension names; across the cluster: every role's attributes and an MD5 of its password verifier (never the verifier). Databases and roles are separate namespaces, so a database called `roles` keeps its check. Any difference stops before a rename. Equal results do not prove equal row contents or extension versions (extensions are recreated at the new server's default version); `pg_dumpall` with `ON_ERROR_STOP` is what moves the data.
   6. **Swap.** The new server is removed and proved gone; the journal is marked `swap` (fsync) and only then `postgres_data` is renamed to `postgres_data.pg<old>-<timestamp>` and the new directory to `postgres_data`. A failed second rename is compensated by renaming the first back. Then `upgrade.json` is written and the journal deleted. The renames stay inside `runtime/volumes/`, because on Linux the data belongs to uid 999 and a host user may rename such a directory within its parent but not move it to another one.

   **Recovery** (`grdm-dev db recover`, and first in `db upgrade`, `db rollback`, `reset` and `up`): every container and volume named in the journal is removed and proved gone; if Docker cannot answer or a container cannot be removed, the journal stays and `up` refuses. Before the `swap` mark the old directory was never written by the new major, so the operation is rolled back and the half-built new directory is named for deletion. After the mark the directories are inspected and the swap is finished (the data was already verified); if it cannot be finished, the journal is retired only when the old directory is proved back in place with its major, otherwise it stays (R2-01). Every rename of a recovery is followed by an fsync of `runtime/volumes/` before the record is written and the journal deleted, and a failed directory fsync is an error (only a filesystem that cannot sync directories, EINVAL or ENOTSUP, is accepted) (R2-03). An empty `postgres_data` that `compose render` created during the gap is removed first, so `up` never starts a fresh cluster in place of a pending swap. `grdm-dev db status` shows both majors and any pending operation. `grdm-dev db rollback` runs under the same lock and journal and puts the kept directory back; the old revision of this repository must then be checked out and `compose render` run, and until then `up` stops with exit 15.
5. **`up` refuses a mismatch and fails closed.** After recovery and before Compose starts anything, `up` compares `PG_VERSION` with the major of the rendered image and stops with exit 15 when they differ, when `PG_VERSION` is unparseable or not ASCII (R2-04), when a non-empty directory has none, or when the version cannot be read at all — on Linux it is read by uid 999 in a throwaway container, and a failure of that container is a refusal, not a pass (R1-04). Only an absent or empty directory counts as "no cluster yet".
6. **Hardening.** The `postgres` exception in `manifest/hardening.json` stays: the official entrypoint still starts as root. Both servers of `db upgrade` run with exactly that exception's capabilities, a read-only root and no network.

### 3. Options considered

```toon
options[4]{option,what_it_does,why_not_or_why,chosen}:
  A,"pg_upgrade (in place or copy)","needs both majors' binaries in one image (only third-party images ship that); --link writes the old directory; text indexes built under glibc 2.24 (Debian 9, the 9.6 image) would be reused under glibc 2.41 (Debian 13, the 18 image) although the collation rules changed in glibc 2.28","no"
  B,"dump with the new pg_dumpall, restore into a new directory (this ADR)","two official images; the old directory is never written by the new major; indexes are rebuilt under the new glibc; a 290 MB development cluster moved in 37 seconds","yes"
  C,"discard the data (grdm-dev reset)","always possible, loses every project and user of the developer","offered, not the default"
  D,"stop at 15, 16 or 17","18 passed the same tests and is supported longest (to November 2030)","no"
```

### 4. Proof (2026-11-10, arm64, throwaway Compose projects `m5-*`)

The running stack `grdm-dev` was never touched. The projects were derived from a file rendered by `compose render` into a throwaway checkout under `.m5-tmp/`; the 9.6 cluster came from a full `osf_init` (migrate, `populate_institutions`, `register_oauth_scopes`) plus one user created through osf.io.

```toon
results[10]{check,result}:
  "osf_init on a new PostgreSQL 18.6 cluster","exit 0: 673 migrations, 68 institutions, OAuth scopes"
  "osf.io DB test modules on 18 and on 9.6 (test_node, test_user, test_guid, test_institution, test_analytics, api_tests/institutions/views, osfstorage test_models)","both: 781 passed, 3 failed, 10 errors, 13 skipped; the failing and erroring tests are the same set on both majors (ES6 metrics fixtures and three existing failures)"
  "CAS on 18 with md5","wrong password 200 without a ticket; right password 302 with a ticket; /p3/serviceValidate authenticationSuccess"
  "CAS on 18 with scram-sha-256","every connection: PSQLException The authentication type 10 is not supported"
  "fakecas on 18","known user and key 302 with a ticket; wrong key 404; unknown user 404"
  "up on a 9.6 directory with the 18 template","exit 15 before any docker compose call"
  "db upgrade 9.6 to 18 (real command, project renamed m5-pgup)","exit 0 in 37 s: 3 databases (osf 262 tables with 16030 rows, cas 9 tables), 531 tables, sequences and extensions equal before and after"
  "the stack on the upgraded directory","osf_init: No migrations to apply; CAS login of the user created on 9.6 (302, serviceValidate success); fakecas 302"
  "db rollback, then 9.6 on the directory","exit 0; PostgreSQL 9.6.24 starts, 68 institutions and 673 migrations, the user is there; up stops with exit 15 until the old revision is rendered"
  "failure path (first attempts)","initdb without a password, then a catalogue query PostgreSQL 18 rejects: both stopped with exit 15 with postgres_data untouched; both fixed. Recovery from crashes and interruptions is shown in §4.1"
```

The first run at 512 MiB, the limit `compose render --memory-gib 16` gives `osf_init`, had the migrating Python process killed twice for memory; `osf_init` retried and finished. That limit is independent of the PostgreSQL major and is left for a separate change.

#### 4.1 Recovery after review r1 (2026-11-10, a new 9.6 copy, the real command with the project renamed `m5-pgup`)

The 9.6 cluster was rebuilt with `osf_init` and one user, plus a database named `roles` and a sequence set with `setval('s', 5, false)`, so that both review cases are in real data.

```toon
recovery[7]{check,result}:
  "SIGKILL of grdm-dev while the 9.6 server ran","journal left (phase prepare), server still running; the next up removed it and its volume, rolled back, then stopped with exit 15 (9.6 data, 18 image); 0 helper containers or volumes left"
  "SIGTERM while the 18 server ran","exit 15 in process: interrupted, rolled back; 0 helper containers or volumes; journal deleted; postgres_data still 9.6"
  "db upgrade after both interruptions","exit 0; 524 objects equal across 4 databases (cas, osf, postgres, roles) and 1 role"
  "the stack on the upgraded directory","osf_init: No migrations to apply; CAS login of the user created on 9.6 (302, serviceValidate success); fakecas 302"
  "edge data","roles.t has 2 rows; sequence s keeps last_value 5 and is_called false, nextval returns 5"
  "db rollback","exit 0; the record is marked rolled_back_at; 9.6.24 starts on the directory with 673 migrations and the user; up stops with exit 15"
  "unit tests with injected failures","rc failure, KeyboardInterrupt and an uncatchable crash at each of 6 steps; both renames of upgrade and rollback (crash and EIO); each of 4 journal writes (ENOSPC); ENOSPC in dump, filter and restore; Docker not answering; a container that cannot be removed; a concurrent second process; an empty postgres_data created by compose render"
```

### 5. For developers

Run from the root of your checkout, after pulling this change. Expected results are in the comments.

```sh
grdm-dev compose render      # exit 0: the postgres service is now postgres:18.6
grdm-dev down                # exit 0
grdm-dev db status           # state: upgrade-needed, data_major: 9.6, image_major: 18
grdm-dev db upgrade          # asks first (--yes skips); exit 0, last line: PostgreSQL 9.6 → 18 done
grdm-dev up                  # exit 0, ready at the web URL
```

If `db upgrade` stops (exit 15) or the terminal dies, run `grdm-dev db status`, then `grdm-dev db recover` or simply `grdm-dev up`: both finish or roll back the operation and say which. A developer who does not need the data may run `grdm-dev reset` instead.

**Disk.** Before the old server starts, the command needs free space for twice the cluster plus 64 MiB on the filesystem of `runtime/backups/` (dump and its filtered copy) and twice the cluster plus 1 GiB on the filesystem of `runtime/volumes/` (the new cluster with rebuilt indexes, and WAL up to `max_wal_size`); on one filesystem, the sum. This is an estimate, not a guarantee: a logical dump can exceed the cluster (bytea is written as hex, compressed values are written expanded). A disk that fills anyway fails the step: before the swap the old cluster stays in place; after the swap (the record cannot be written) recovery finishes the new cluster and retries the record, keeping the journal until it is written. The kept directory and the dump may be deleted once the new cluster is trusted; `reset` deletes the kept directory with the rest of `runtime/volumes/`, and the dump under `runtime/backups/` survives it.

### 6. Not verified

An amd64 host; a Linux host where the data belongs to uid 999 (the container reads of `PG_VERSION` and of the size, and the in-parent renames, are unit-tested, not run there); a real crash between the two renames (unit-tested with an injected crash, not timed against a real kill); clusters with extensions other than `plpgsql`; SCRAM with a newer CAS driver. The production GRDM is not affected: this is the developer environment.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

[ステータスボード](../status/README.md#japanese)の節目 M5 は PostgreSQL 15 以降を求めている。スタックは `postgres:9.6` で動いており、これは 2021 年 11 月に作り手が修正をやめた版である。これに接続するプログラムは三つある。

```toon
clients[3]{client,driver,measured_in}:
  "osf.io（web・api・admin・worker・osf_init）","Django 1.11.28、libpq 11.11 にリンクした psycopg2 2.7.3","grdm-dev/osf.io:fe90e5c39e66"
  "CAS（cas-overlay）","Hibernate 4.3.10 と c3p0 の下の PostgreSQL JDBC 42.1.4","grdm-dev/cas-overlay:22610b7681a2 の WEB-INF/lib"
  "fakecas","Go の lib/pq v1.10.9","installer/images/fakecas/go.mod"
```

Django 1.11 の文書は PostgreSQL 9.3 以降を挙げ、上限を書いていない。そのため、どの版が動くかは測定でしか分からない。Docker Hub の PostgreSQL 19 はまだベータ（`19beta1`）なので、リリース済みで最新の版は 18 である。

### 2. 決定

1. **イメージ。** `postgres:18.6` をインデックスのダイジェストで固定する（manifest の `base_image_digest`）。`linux/arm64` と `linux/amd64` の両方。一回限りの `volume_owner_init` と `volume_access_check_*` も同じイメージで動き、その GNU coreutils で確認を通った（測定）。
2. **テンプレート。** 18 のイメージは `PGDATA` を `/var/lib/postgresql/18/docker` に移し、`/var/lib/postgresql` にボリュームを宣言している。テンプレートは `PGDATA=/var/lib/postgresql/data`（`postgres_data` のマウント先）を設定し、`/var/lib/postgresql` に tmpfs を置いて、Compose がそこに無名ボリュームを作らないようにする（測定: コンテナのマウントはデータのボリュームと初期化スクリプトだけ）。
3. **認証は md5 のまま。** `POSTGRES_INITDB_ARGS` は `--auth-host=md5` を保つ。これで initdb は `password_encryption = md5` も書き、entrypoint が加える包括の行は `host all all all md5` になる。代わりに `scram-sha-256` にすると、CAS はすべての接続で `The authentication type 10 is not supported` で失敗した（測定）。SCRAM を既定にするのは、CAS が 42.2 以降の JDBC ドライバーを持ったときである。これは統合リポジトリの変更で、所有者の判断事項である。PostgreSQL 18 は md5 のパスワードを設定すると非推奨の警告をログに出すが、動作はする。これはこの隔離された開発ネットワークに限って受け入れる暫定の互換性の例外であり、内部ネットワーク一般の安全性を言うものではない。抜け出す道（レビュー r1）: CAS と osf.io のログインロールを分け（今は両方が `postgres`）、osf.io のロールに SCRAM の検証子を設定し直し（osf.io の libpq 11 は SCRAM に対応する。`password_encryption` を変えても既存の検証子は変わらない）、CAS には歴史的な最低版 42.2 ではなく現在保守されている修正版の JDBC ドライバーを選ぶ。
4. **既存データの移行: `grdm-dev db upgrade`。** サーバーは別の版のデータディレクトリを拒むので、データはダンプして復元し、その場では決して変えない。操作は自分が作るものすべてを操作記録で所有し、どの時点でプロセスがクラッシュしても旧か新のどちらかのクラスタが使える状態に残る。補償の改名まで失敗したときは操作記録を残し、`up` は拒み `db recover` が再試行する（レビュー r1 R1-01、R1-02、r2 R2-01）。
   1. **確認（まだ何も起動しない）。** 全サービスが停止している（`grdm-dev down`）。データの版が読めて既知である。バックアップとボリュームのファイルシステムの空き容量を測る（§5）。確認を得る（`--yes` で省く）。
   2. **操作記録とロック。** コンテナ・ボリューム・ディレクトリを一つも作る前に `runtime/db-operation.json` を書き（fsync と原子的な改名）、そのすべての名前を記す。サービスの確認と確認の問いを含め、操作の間ずっと `runtime/db-operation.lock` の排他 `flock` を持つ。`up` は確認から Compose がコンテナを起動するまで、`reset` は確認から削除が終わるまで同じロックを取るので、どれも他の確認と実行の間に割り込めない（R2-02）。プロセスがどう終わってもカーネルがそれを解放するので、二つ目の `db` コマンドが死んだプロセスを待つことはない。SIGTERM と SIGHUP は Ctrl-C と同じに扱う。
   3. **移行元。** 旧版（ダイジェスト固定の `postgres:9.6`）を既存のディレクトリの上で、ネットワークなし・TCP の待ち受けなしで起動する。ソケットは使い捨ての Docker ボリュームに置く。新しい版の `pg_dumpall`（PostgreSQL の原則: 新しい方のクライアントでダンプする）をホストの利用者として動かし、`runtime/backups/postgres-<旧>-to-<新>-<時刻>/dumpall.sql`（0700 のディレクトリの中の 0600）に書く。次に旧サーバーを止めて削除し、他の何かを起動する前に `docker ps -a` で消えたことを証明する。証明できなければ操作記録を残す。
   4. **移行先。** 新しい版が、生成済みの initdb 引数・`PGDATA`・コマンドで `runtime/volumes/postgres_data.pg<新>-<時刻>.new` を初期化する。スーパーユーザーのパスワードは、コンテナができた時点で消す 0600 のファイルで initdb に渡す。ダンプは `ON_ERROR_STOP` で復元する。取り除く行は `CREATE ROLE postgres;` だけ（initdb がそのロールを作った。旧検証子を持つ `ALTER ROLE` は残る）。続けて `vacuumdb --analyze-only` を実行し、派生した `restore.sql` を消す。二つのサーバーは `log_min_error_statement=panic` で動くので、失敗した文（行のデータやパスワードの検証子を含みうる）はコンテナのログに書かれない。
   5. **照合とその限界。** データベースごとに全表の行数、全シーケンスの `last_value` と `is_called`、拡張の名前を、クラスタ全体で全ロールの属性とパスワード検証子の MD5（検証子そのものではない）を比べる。データベースとロールは別の名前空間なので、`roles` という名のデータベースも自分の照合を保つ。違いが一つでもあれば改名の前に止まる。一致しても行の中身や拡張の版の一致は証明しない（拡張は新しいサーバーの既定の版で作り直される）。データを移すのは `ON_ERROR_STOP` 付きの `pg_dumpall` である。
   6. **切替。** 新サーバーを削除して消えたことを証明し、操作記録に `swap` の印を付けて（fsync）から初めて、`postgres_data` を `postgres_data.pg<旧>-<時刻>` に、新しいディレクトリを `postgres_data` に改名する。二つ目の改名に失敗したら一つ目を戻して補償する。その後 `upgrade.json` を書き、操作記録を消す。改名は `runtime/volumes/` の中に留める。Linux ではデータが uid 999 の所有で、ホストの利用者はその種のディレクトリを同じ親の中では改名できても、別の親へは移せないからである。

   **復旧**（`grdm-dev db recover`。`db upgrade`・`db rollback`・`reset`・`up` も最初に行う）: 操作記録にあるコンテナとボリュームをすべて削除し、消えたことを証明する。Docker が答えないか削除できなければ操作記録は残り、`up` は拒む。`swap` の印の前は、旧ディレクトリに新しい版が一度も書いていないので巻き戻し、作りかけの新ディレクトリを削除してよいものとして示す。印の後はディレクトリを調べて切替を完了する（データは照合済み）。完了できなければ、旧ディレクトリが版とともに元の場所に戻ったと確かめたときだけ操作記録を消し、そうでなければ残す（R2-01）。復旧の改名のたびに、記録を書き操作記録を消す前に `runtime/volumes/` を fsync し、ディレクトリの fsync の失敗は誤りとする（ディレクトリを sync できないファイルシステムの EINVAL・ENOTSUP だけは受け入れる）（R2-03）。その間に `compose render` が作った空の `postgres_data` は先に取り除くので、`up` が保留中の切替の代わりに新しい空のクラスタを作ることはない。`grdm-dev db status` は両方の版と保留中の操作を表示する。`grdm-dev db rollback` は同じロックと操作記録のもとで残したディレクトリを戻す。その後は本リポジトリの以前の版を取り出して `compose render` を実行する必要があり、それまで `up` は終了 15 で止まる。
5. **`up` は不一致を拒み、閉じて失敗する。** 復旧の後、Compose が何かを起動する前に、`up` は `PG_VERSION` と生成済みイメージの版を比べ、違うとき、`PG_VERSION` が解析できないか ASCII でないとき（R2-04）、空でないディレクトリに `PG_VERSION` が無いとき、版がそもそも読めないときに終了 15 で止まる。Linux では使い捨てのコンテナの中で uid 999 が読み、そのコンテナの失敗は通過ではなく拒否である（R1-04）。「まだクラスタが無い」とみなすのは、ディレクトリが無いか空のときだけである。
6. **堅牢化。** `manifest/hardening.json` の `postgres` の例外は残る。公式の entrypoint は今も root で始まるからである。`db upgrade` の二つのサーバーはちょうどその例外の capability と読み取り専用ルートで、ネットワークなしで動く。

### 3. 検討した選択肢

```toon
options[4]{option,what_it_does,why_not_or_why,chosen}:
  A,"pg_upgrade（その場、または複写）","両方の版のバイナリが一つのイメージに要る（それを配るのは第三者のイメージだけ）。--link は旧ディレクトリに書く。glibc 2.24（Debian 9、9.6 のイメージ）で作った文字列の索引を、照合規則が glibc 2.28 で変わったのに glibc 2.41（Debian 13、18 のイメージ）の下でそのまま使うことになる","いいえ"
  B,"新しい pg_dumpall でダンプし新しいディレクトリへ復元（本 ADR）","公式イメージ二つ。旧ディレクトリに新しい版は一度も書かない。索引は新しい glibc の下で作り直される。290 MB の開発用クラスタが 37 秒で移った","はい"
  C,"データを捨てる（grdm-dev reset）","常に可能だが、開発者のプロジェクトと利用者をすべて失う","選べるが既定ではない"
  D,"15・16・17 で止める","18 は同じ試験に合格し、保守期間が最も長い（2030 年 11 月まで）","いいえ"
```

### 4. 実証（2026-11-10、arm64、使い捨ての Compose プロジェクト `m5-*`）

稼働中のスタック `grdm-dev` には一度も触れていない。プロジェクトは `.m5-tmp/` の下の使い捨てのチェックアウトで `compose render` が生成したファイルから導いた。9.6 のクラスタは完全な `osf_init`（migrate、`populate_institutions`、`register_oauth_scopes`）と、osf.io で作った利用者一人から成る。

```toon
results[10]{check,result}:
  "新しい PostgreSQL 18.6 のクラスタでの osf_init","終了 0: migration 673 件、機関 68、OAuth のスコープ"
  "18 と 9.6 での osf.io の DB 試験モジュール（test_node、test_user、test_guid、test_institution、test_analytics、api_tests/institutions/views、osfstorage の test_models）","両方とも 781 合格、3 失敗、10 エラー、13 スキップ。失敗とエラーの試験は両方の版で同じ集合（ES6 のメトリクスの準備と既存の失敗 3 件）"
  "md5 の 18 での CAS","誤ったパスワードは 200 でチケットなし。正しいパスワードは 302 でチケットあり。/p3/serviceValidate は authenticationSuccess"
  "scram-sha-256 の 18 での CAS","すべての接続で PSQLException The authentication type 10 is not supported"
  "18 での fakecas","既知の利用者と鍵で 302 とチケット。誤った鍵は 404。未知の利用者は 404"
  "18 のテンプレートで 9.6 のディレクトリに up","docker compose を一度も呼ばずに終了 15"
  "db upgrade 9.6 から 18（実際のコマンド、プロジェクト名を m5-pgup に変更）","37 秒で終了 0: データベース 3（osf は 262 表・16030 行、cas は 9 表）、表・シーケンス・拡張 531 件が前後で一致"
  "更新したディレクトリでのスタック","osf_init: No migrations to apply。9.6 で作った利用者の CAS ログイン（302、serviceValidate 成功）。fakecas は 302"
  "db rollback の後、そのディレクトリで 9.6","終了 0。PostgreSQL 9.6.24 が起動し、機関 68・migration 673 件・利用者がそろう。以前の版を生成するまで up は終了 15 で止まる"
  "失敗の経路（最初の試行）","パスワードなしの initdb、次に PostgreSQL 18 が拒むカタログの問い合わせ。どちらも postgres_data を変えずに終了 15 で止まり、両方とも修正した。クラッシュと中断からの復旧は §4.1"
```

最初の実行では、`compose render --memory-gib 16` が `osf_init` に与える 512 MiB の上限で、migrate する Python のプロセスがメモリ不足で 2 回止められ、`osf_init` が再試行して完了した。この上限は PostgreSQL の版と無関係なので、別の変更に回す。

#### 4.1 レビュー r1 の後の復旧（2026-11-10、新しい 9.6 の写し、プロジェクト名を `m5-pgup` にした実際のコマンド）

9.6 のクラスタを `osf_init` と利用者一人で作り直し、`roles` という名のデータベースと `setval('s', 5, false)` で設定したシーケンスを加え、レビューの二つの例が実データにあるようにした。

```toon
recovery[7]{check,result}:
  "9.6 サーバーの稼働中に grdm-dev を SIGKILL","操作記録（phase prepare）が残り、サーバーは動いたまま。次の up がそれとボリュームを削除して巻き戻し、終了 15（データ 9.6、イメージ 18）。補助のコンテナとボリュームは 0"
  "18 サーバーの稼働中に SIGTERM","プロセス内で終了 15: 中断、巻き戻し。補助のコンテナとボリュームは 0、操作記録は削除、postgres_data は 9.6 のまま"
  "二つの中断の後の db upgrade","終了 0。4 データベース（cas、osf、postgres、roles）とロール 1 で 524 件が一致"
  "更新したディレクトリでのスタック","osf_init: No migrations to apply。9.6 で作った利用者の CAS ログイン（302、serviceValidate 成功）。fakecas は 302"
  "境界のデータ","roles.t は 2 行。シーケンス s は last_value 5 と is_called false を保ち、nextval は 5 を返す"
  "db rollback","終了 0。記録に rolled_back_at が付く。9.6.24 がそのディレクトリで起動し、migration 673 件と利用者がそろう。up は終了 15 で止まる"
  "障害を注入した単体試験","6 段階それぞれで rc の失敗・KeyboardInterrupt・捕捉できないクラッシュ。更新と巻き戻しの両方の改名（クラッシュと EIO）。4 回の操作記録の書込みそれぞれ（ENOSPC）。ダンプ・加工・復元の ENOSPC。答えない Docker。削除できないコンテナ。同時に動く二つ目のプロセス。compose render が作った空の postgres_data"
```

### 5. 開発者へ

この変更を取り込んだ後、自分のチェックアウトのルートで実行する。期待する結果はコメントに書いた。

```sh
grdm-dev compose render      # 終了 0: postgres サービスは postgres:18.6 になる
grdm-dev down                # 終了 0
grdm-dev db status           # state: upgrade-needed、data_major: 9.6、image_major: 18
grdm-dev db upgrade          # 先に確認する（--yes で省く）。終了 0、最後の行: PostgreSQL 9.6 → 18 done
grdm-dev up                  # 終了 0、web の URL で準備完了
```

`db upgrade` が止まった（終了 15）か端末が落ちたときは、`grdm-dev db status` の後に `grdm-dev db recover`、または単に `grdm-dev up` を実行する。どちらも操作を完了か巻き戻しし、どちらにしたかを示す。データが要らない開発者は代わりに `grdm-dev reset` を使ってよい。

**容量。** 旧サーバーを起動する前に、`runtime/backups/` のファイルシステムにクラスタの 2 倍と 64 MiB（ダンプとその加工した写し）、`runtime/volumes/` のファイルシステムにクラスタの 2 倍と 1 GiB（索引を作り直した新しいクラスタと、`max_wal_size` までの WAL）の空きを求める。同じファイルシステムならその和。これは見積りであって保証ではない。論理ダンプはクラスタより大きくなりうる（bytea は 16 進で、圧縮された値は展開して書かれる）。それでも満杯になればその段階が失敗する。切替の前なら旧クラスタが元の場所に残り、切替の後（記録が書けない）なら復旧が新クラスタを完了させ、記録を書けるまで操作記録を残して再試行する。新しいクラスタを信頼できたら、残したディレクトリとダンプは消してよい。`reset` は残したディレクトリを `runtime/volumes/` の残りと一緒に消し、`runtime/backups/` の下のダンプは残す。

### 6. 未確認

amd64 のホスト。データが uid 999 の所有になる Linux のホスト（`PG_VERSION` と容量のコンテナでの読み取り、同じ親の中での改名は単体試験で確かめたが、そこでは動かしていない）。二つの改名の間の実際のクラッシュ（注入したクラッシュで単体試験したが、実際の kill で狙ってはいない）。`plpgsql` 以外の拡張を持つクラスタ。新しい CAS のドライバーでの SCRAM。本番の GRDM には影響しない。これは開発環境の話である。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Major version | The first number of a PostgreSQL release (9.6, 18); a server reads only data directories of its own major. | PostgreSQL のリリースの最初の番号（9.6、18）。サーバーは自分と同じ版のデータディレクトリしか読まない。 |
| Dump and restore | Writing every database out as SQL, then replaying it into a new server. | すべてのデータベースを SQL として書き出し、新しいサーバーで再生すること。 |
| SCRAM | The password exchange PostgreSQL uses by default since 14; older drivers only know md5. | PostgreSQL が 14 から既定で使うパスワードのやり取り。古いドライバーは md5 しか知らない。 |
| Data directory | The folder where PostgreSQL keeps a whole cluster; here `runtime/volumes/postgres_data`. | PostgreSQL がクラスタ全体を置くフォルダ。ここでは `runtime/volumes/postgres_data`。 |
