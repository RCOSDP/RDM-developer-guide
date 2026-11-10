# ADR-12 PostgreSQL 18 and the Data Directory Upgrade / PostgreSQL 18 とデータディレクトリの更新

> **Summary:** The developer environment moves from PostgreSQL 9.6 (end of life since 2021) to **PostgreSQL 18.6**, the newest released major, pinned by its index digest. osf.io's Django 1.11.28 with psycopg2 2.7.3 ran its migrations and 807 database tests on 18 with exactly the same outcome as on 9.6 (781 passed, the same 13 failed or erred on both), and CAS and fakecas logged in against it. CAS's JDBC driver 42.1.4 cannot answer SCRAM, so host authentication stays `md5` until CAS gets a newer driver. An existing 9.6 data directory is moved by a new command, `grdm-dev db upgrade`: a dump with the new major's `pg_dumpall` and a restore into a fresh directory, compared table by table, with the old directory kept beside it for `grdm-dev db rollback`. `up` refuses a data directory of another major (exit 15).
> **概要:** 開発環境の PostgreSQL を 9.6（2021 年に EOL）から、リリース済みで最新の **PostgreSQL 18.6** へ移し、インデックスのダイジェストで固定する。osf.io の Django 1.11.28 と psycopg2 2.7.3 は 18 の上で migration と 807 件のデータベース試験を実行し、結果は 9.6 とまったく同じだった（781 件合格、両方で同じ 13 件が失敗かエラー）。CAS と fakecas も 18 に対してログインできた。CAS の JDBC ドライバー 42.1.4 は SCRAM に応えられないので、ホスト認証は CAS が新しいドライバーを持つまで `md5` のままにする。既存の 9.6 のデータディレクトリは新しいコマンド `grdm-dev db upgrade` で移す。新しい版の `pg_dumpall` でダンプし、新しいディレクトリへ復元し、表ごとに突き合わせ、旧ディレクトリは `grdm-dev db rollback` のために隣に残す。`up` は別の版のデータディレクトリを拒む（終了 15）。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** a database upgrade is proven by the clients, not by the server starting: the server and Django were fine on 18, while the CAS driver failed only once the password was stored as SCRAM, and PostgreSQL 18 rejected a catalogue query that 9.6 accepted (`text || "char"`), so the verification query itself had to be tested on both majors. ／ データベースの更新は、サーバーが起動したことではなくクライアントで証明される。サーバーと Django は 18 で問題なかったが、CAS のドライバーはパスワードが SCRAM で保存されたときにだけ失敗した。また PostgreSQL 18 は 9.6 が受け付けたカタログの問い合わせ（`text || "char"`）を拒んだので、照合の問い合わせ自体も両方の版で試す必要があった。
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
3. **Authentication stays md5.** `POSTGRES_INITDB_ARGS` keeps `--auth-host=md5`; with it, initdb also writes `password_encryption = md5`, and the entrypoint's catch-all line is `host all all all md5`. With `scram-sha-256` instead, CAS failed every connection with `The authentication type 10 is not supported` (measured). SCRAM becomes the default when CAS ships a JDBC driver of 42.2 or later — a change in the integration repository and an owner item. PostgreSQL 18 logs a deprecation warning when an md5 password is set; it still works.
4. **Moving existing data: `grdm-dev db upgrade`.** A server refuses a data directory of another major, so the data is dumped and restored, never changed in place:
   1. with every service stopped (`grdm-dev down`) and after a confirmation, the old major (`postgres:9.6`, pinned by digest) starts on the existing directory with no network and no TCP listener; its socket is in a throwaway Docker volume;
   2. the new major's `pg_dumpall` (the PostgreSQL rule: dump with the newer client) runs as the host user and writes `runtime/backups/postgres-<old>-to-<new>-<timestamp>/dumpall.sql` (mode 0600 in a 0700 directory);
   3. per database, every table's row count, every sequence's last value and the extension names are recorded, with the roles;
   4. the new major initialises `runtime/volumes/postgres_data.pg<new>-<timestamp>.new` with the rendered initdb arguments, `PGDATA` and command; the superuser password reaches initdb through a 0600 file that is deleted as soon as the container exists, never through the command line. The dump is restored with `ON_ERROR_STOP`; the only line removed is `CREATE ROLE postgres;`, the bootstrap role initdb has already made (its `ALTER ROLE` with the old password hash stays). `vacuumdb --analyze-only` follows;
   5. the same numbers are taken on the new cluster; any difference stops the command before anything is renamed;
   6. `postgres_data` is renamed to `postgres_data.pg<old>-<timestamp>` and the new directory to `postgres_data`. The renames stay inside `runtime/volumes/`, because on Linux the data belongs to uid 999 and a host user may rename such a directory within its parent but not move it to another one.

   On a failure nothing is renamed, the containers are stopped but kept for `docker logs`, and the report lists what to remove. `grdm-dev db status` shows both majors and changes nothing. `grdm-dev db rollback` puts the kept directory back and sets the current one aside; the old revision of this repository must then be checked out and `compose render` run, and until then `up` stops with exit 15.
5. **`up` refuses a mismatch.** Before Compose starts anything, `up` compares `PG_VERSION` of the data directory with the major of the rendered image and stops with exit 15, naming `db upgrade`. On Linux the file is read by uid 999 in a throwaway container when the host user cannot read it.
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
  "failure path (first attempts)","initdb without a password, then a catalogue query PostgreSQL 18 rejects: both stopped with exit 15, postgres_data untouched, leftovers named; both fixed and covered by unit tests"
```

The first run at 512 MiB, the limit `compose render --memory-gib 16` gives `osf_init`, had the migrating Python process killed twice for memory; `osf_init` retried and finished. That limit is independent of the PostgreSQL major and is left for a separate change.

### 5. For developers

After pulling this change: `grdm-dev compose render`, `grdm-dev down`, `grdm-dev db status`, `grdm-dev db upgrade`, `grdm-dev up`. The upgrade needs free disk for the dump and the new cluster (twice the data). A developer who does not need the data may run `grdm-dev reset` instead. The kept directory and the dump may be deleted once the new cluster is trusted; `reset` deletes the kept directory with the rest of `runtime/volumes/`, and the dump under `runtime/backups/` survives it.

### 6. Not verified

An amd64 host; a Linux host where the data belongs to uid 999 (the container read of `PG_VERSION` and the in-parent renames are unit-tested, not run there); clusters with extensions other than `plpgsql`; SCRAM with a newer CAS driver. The production GRDM is not affected: this is the developer environment.

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
3. **認証は md5 のまま。** `POSTGRES_INITDB_ARGS` は `--auth-host=md5` を保つ。これで initdb は `password_encryption = md5` も書き、entrypoint が加える包括の行は `host all all all md5` になる。代わりに `scram-sha-256` にすると、CAS はすべての接続で `The authentication type 10 is not supported` で失敗した（測定）。SCRAM を既定にするのは、CAS が 42.2 以降の JDBC ドライバーを持ったときである。これは統合リポジトリの変更で、所有者の判断事項である。PostgreSQL 18 は md5 のパスワードを設定すると非推奨の警告をログに出すが、動作はする。
4. **既存データの移行: `grdm-dev db upgrade`。** サーバーは別の版のデータディレクトリを拒むので、データはダンプして復元し、その場では決して変えない。
   1. すべてのサービスを止め（`grdm-dev down`）、確認を得たうえで、旧版（ダイジェスト固定の `postgres:9.6`）を既存のディレクトリの上で、ネットワークなし・TCP の待ち受けなしで起動する。ソケットは使い捨ての Docker ボリュームに置く。
   2. 新しい版の `pg_dumpall`（PostgreSQL の原則: 新しい方のクライアントでダンプする）をホストの利用者として動かし、`runtime/backups/postgres-<旧>-to-<新>-<時刻>/dumpall.sql`（0700 のディレクトリの中の 0600）に書く。
   3. データベースごとに、全表の行数、全シーケンスの最終値、拡張の名前を記録し、ロールも記録する。
   4. 新しい版が、生成済みの initdb 引数・`PGDATA`・コマンドで `runtime/volumes/postgres_data.pg<新>-<時刻>.new` を初期化する。スーパーユーザーのパスワードはコマンド行を通らず、コンテナができた時点で消す 0600 のファイルで initdb に渡す。ダンプは `ON_ERROR_STOP` で復元する。取り除く行は initdb が既に作った初期ロールの `CREATE ROLE postgres;` だけで、旧パスワードのハッシュを持つ `ALTER ROLE` は残る。続けて `vacuumdb --analyze-only` を実行する。
   5. 新しいクラスタでも同じ数を取り、一つでも違えば名前を変える前に止まる。
   6. `postgres_data` を `postgres_data.pg<旧>-<時刻>` に、新しいディレクトリを `postgres_data` に名前を変える。名前の変更は `runtime/volumes/` の中に留める。Linux ではデータが uid 999 の所有で、ホストの利用者はその種のディレクトリを同じ親の中では改名できても、別の親へは移せないからである。

   失敗したときは何も改名せず、コンテナは止めるが `docker logs` のために残し、報告に消すべきものを並べる。`grdm-dev db status` は両方の版を表示し、何も変えない。`grdm-dev db rollback` は残したディレクトリを戻し、今のものを脇に置く。その後は本リポジトリの以前の版を取り出して `compose render` を実行する必要があり、それまで `up` は終了 15 で止まる。
5. **`up` は不一致を拒む。** Compose が何かを起動する前に、`up` はデータディレクトリの `PG_VERSION` と生成済みイメージの版を比べ、違えば `db upgrade` を示して終了 15 で止まる。Linux でホストの利用者がファイルを読めないときは、使い捨てのコンテナの中で uid 999 が読む。
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
  "失敗の経路（最初の試行）","パスワードなしの initdb、次に PostgreSQL 18 が拒むカタログの問い合わせ。どちらも終了 15 で止まり、postgres_data は無傷で、残ったものを報告した。両方とも修正し単体試験で押さえた"
```

最初の実行では、`compose render --memory-gib 16` が `osf_init` に与える 512 MiB の上限で、migrate する Python のプロセスがメモリ不足で 2 回止められ、`osf_init` が再試行して完了した。この上限は PostgreSQL の版と無関係なので、別の変更に回す。

### 5. 開発者へ

この変更を取り込んだら、`grdm-dev compose render`、`grdm-dev down`、`grdm-dev db status`、`grdm-dev db upgrade`、`grdm-dev up` の順に実行する。更新にはダンプと新しいクラスタのための空き容量（データの 2 倍）が要る。データが要らない開発者は代わりに `grdm-dev reset` を使ってよい。新しいクラスタを信頼できたら、残したディレクトリとダンプは消してよい。`reset` は残したディレクトリを `runtime/volumes/` の残りと一緒に消し、`runtime/backups/` の下のダンプは残す。

### 6. 未確認

amd64 のホスト。データが uid 999 の所有になる Linux のホスト（`PG_VERSION` のコンテナでの読み取りと、同じ親の中での改名は単体試験で確かめたが、そこでは動かしていない）。`plpgsql` 以外の拡張を持つクラスタ。新しい CAS のドライバーでの SCRAM。本番の GRDM には影響しない。これは開発環境の話である。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Major version | The first number of a PostgreSQL release (9.6, 18); a server reads only data directories of its own major. | PostgreSQL のリリースの最初の番号（9.6、18）。サーバーは自分と同じ版のデータディレクトリしか読まない。 |
| Dump and restore | Writing every database out as SQL, then replaying it into a new server. | すべてのデータベースを SQL として書き出し、新しいサーバーで再生すること。 |
| SCRAM | The password exchange PostgreSQL uses by default since 14; older drivers only know md5. | PostgreSQL が 14 から既定で使うパスワードのやり取り。古いドライバーは md5 しか知らない。 |
| Data directory | The folder where PostgreSQL keeps a whole cluster; here `runtime/volumes/postgres_data`. | PostgreSQL がクラスタ全体を置くフォルダ。ここでは `runtime/volumes/postgres_data`。 |
