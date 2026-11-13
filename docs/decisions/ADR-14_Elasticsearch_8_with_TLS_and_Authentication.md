# ADR-14 Elasticsearch 8 with TLS and Authentication / TLS と認証つきの Elasticsearch 8

> **Summary:** osf.io's full-text search runs on Elasticsearch 8.19.24 (RDM-osf.io-dev2027 PR #11), so the installer replaces the Elasticsearch 2 service with `elasticsearch8`: the official multi-architecture image pinned by its index digest plus the two Japanese-analysis plugins, TLS with a certificate authority of the installation's own, authentication on, scripts off, no published port, and a role-limited user for osf.io (`grdm_osf`, every privilege on `website*` and `private__website*` only) created by a one-shot step. The root filesystem stays read-only: the official entrypoint writes a keystore into `config/`, so `config/` is a tmpfs that our entrypoint fills. The record also names what this change does not do: the ES 2 data is not migrated (`invoke migrate_search` rebuilds the index), and Elasticsearch 6 stays for the metrics client.
> **概要:** osf.io の全文検索は Elasticsearch 8.19.24 で動く（RDM-osf.io-dev2027 PR #11）ので、インストーラーは Elasticsearch 2 のサービスを `elasticsearch8` に替える。インデックスのダイジェストで固定した公式のマルチアーキテクチャイメージに日本語解析の二つのプラグインを足し、導入ごとの認証局による TLS、認証あり、スクリプトなし、ポート非公開とし、osf.io には権限を絞った利用者（`grdm_osf`。`website*` と `private__website*` にだけすべての権限）を一回きりの手順で作る。読み取り専用のルートは保つ。公式の entrypoint が `config/` にキーストアを書くので、`config/` は tmpfs にして自前の entrypoint が中身を入れる。この記録は、この変更がしないことも示す。ES 2 のデータは移さず（`invoke migrate_search` が索引を作り直す）、Elasticsearch 6 はメトリクスのクライアントのために残す。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-13. **Learned:** acceptance closes the decision, not its open points: the owner accepted this record on 2026-11-13 ("一括で承認、M2 完了") after the merged osf.io pin `90b10661c8dc` passed 14 of 14, while `elasticsearch6` for metrics and the allow-list review of the image's Ubuntu packages stay open, and from M3 any new allow-list entry must be balanced by a removal because the ceiling is the M2 count of 58. ／ 承認は決定を閉じるが、その未了の点は閉じない。所有者は、マージ後の osf.io の固定版 `90b10661c8dc` が 14 件中 14 件に合格した後の 2026-11-13 にこの記録を承認した（「一括で承認、M2 完了」）。メトリクスのための `elasticsearch6` と、イメージの Ubuntu パッケージの許容リストの見直しは未了のまま残る。M3 からは上限が M2 の件数 58 なので、許容リストに項目を足すには別の項目を外す必要がある。
  0.2 — 2026-11-13. **Learned:** an upgrade instruction has to be checked against the order the installer actually enforces, not against what each command does alone: `secrets rotate` changes every credential, drops a retired key and recreates containers from the Compose file as it was last rendered, so putting it before `compose render` is an unnecessary credential change that can fail or roll back before the new configuration exists; the upgrade that keeps the existing values is `secrets init --missing`, then render, build, render, up (PR #56 review r1 R1-02). ／ 更新の手順は、各コマンド単体の働きでなく、インストーラーが実際に求める順序に照らして確かめなければならない。`secrets rotate` はすべての資格情報を替え、廃止したキーを捨て、最後に生成した Compose ファイルのままコンテナを再作成するので、`compose render` の前に置くのは不要な資格情報の変更で、新しい設定ができる前に失敗や巻き戻しを起こしうる。既存の値を保つ更新は `secrets init --missing`、そのあと render、build、render、up である（PR #56 レビュー r1 R1-02）。
  0.1 — 2026-11-12. **Learned:** a "read-only root" claim for a service is only true when its entrypoint has been run that way: Elasticsearch 8's official entrypoint writes a keystore into `config/` and its security layer reads TLS files only from `config/`, so both the tmpfs and the copy of the certificate into it had to be found by starting the image under the real hardening, not by reading its documentation. ／ サービスが「読み取り専用のルート」で動くという主張は、その entrypoint を実際にその条件で動かして初めて本当になる。Elasticsearch 8 の公式 entrypoint は `config/` にキーストアを書き、セキュリティ層は TLS のファイルを `config/` からしか読まないので、tmpfs と証明書の複写の両方は、文書を読むのでなく、実際の堅牢化の下でイメージを起動して初めて分かった。
- Status: Accepted by the owner, 2026-11-13 (proposed 2026-11-12, M5). Review date: when django-elasticsearch-metrics supports Elasticsearch 8 (then `elasticsearch6` goes), or at the next Elasticsearch 8 minor.
- Records a decision for: `manifest/upstreams.json` (`elasticsearch8` replaces `elasticsearch2`) · `installer/images/elasticsearch8/` · `installer/grdm_dev/templates/elasticsearch8.json`, `elasticsearch8_setup.json` and the osf.io templates · [SPEC-02](../spec/02_installer_cli.md#english) (services, secrets, volumes) · [SPEC-01](../spec/01_manifest.md#english)
- Related: [ADR-13 Retiring Elasticsearch 2 and MongoDB](ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md) (path C of its §2 is this record's change) · [ADR-07 Native builds of EOL middleware](ADR-07_Native_Builds_of_EOL_Middleware.md) · [ADR-02 Network model](ADR-02_Network_Model.md) · [Status board](../status/README.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

[ADR-13](ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md) measured that osf.io's search cannot run on Elasticsearch 6.8 or OpenSearch and left three paths; the owner chose the port to Elasticsearch 8 with full-text search (path C, 2026-11-10). The osf.io side is RDM-osf.io-dev2027 PR #11: the client is `elasticsearch7` 7.17.13 in compatibility mode, one index `website_v1` with the alias `website` and a `doc_type` field, the `_all` field replaced by `all_text`, a Japanese analyzer built on `analysis-kuromoji`, and a permission filter that keeps private content out of the answers. It connects with `ELASTIC_URI`, `ELASTIC_USERNAME`, `ELASTIC_PASSWORD` and `ELASTIC_CA_CERTS` and refuses to send credentials over anything but https.

The installer has to give it a server it can use under the baseline every other service meets (non-root, read-only root, no added capabilities, no published port, secrets only in `runtime/.env`).

### 2. Decision

1. **One image, `grdm-dev/elasticsearch8:8.19.24-1`** (`image_build`, as ADR-07 does for the other infra recipes). The base is the official `docker.elastic.co/elasticsearch/elasticsearch:8.19.24` pinned by its index digest (`sha256:d6dfe6626d64…`), which has native arm64 and amd64 variants, so nothing is compiled or emulated. The recipe adds `analysis-kuromoji` and `analysis-icu` and nothing else.
2. **Two services from it.** `elasticsearch8` is the node. `elasticsearch8_setup` is a one-shot that waits for a yellow cluster with the bootstrap superuser, then creates, by idempotent `PUT`, the role `grdm_osf` (cluster `monitor`; all privileges on `website*` and `private__website*`) and the user `grdm_osf`. osf.io receives only that user's password. The superuser's password reaches only the two elasticsearch8 services.
3. **TLS with the installation's own CA.** At first start the entrypoint creates a CA and a server certificate for `elasticsearch8`, `localhost` and `127.0.0.1`, keeps the server key in the data volume and discards the CA key. Only the public `ca.crt` is published, into the small volume `elasticsearch8_ca`, which osf.io mounts read-only as `ELASTIC_CA_CERTS`. This replaces the mongo pattern of ADR-07 and PR #43 (a certificate made once, trusted by exact file), and the trust is again by file, never by disabling verification.
4. **Security settings that ES 2 did not have.** `xpack.security` on, TLS on the REST port (the transport port is not reachable on a single node), `script.allowed_types: none` (ES 8 enables Painless by default; the search never needs it), machine learning and the GeoIP download off, `action.destructive_requires_name`, and disk watermarks given in bytes so that a large disk that is nearly full does not stop writes while a small one still does.
5. **Read-only root.** `config/` is a tmpfs because the official entrypoint creates `elasticsearch.keystore` there (it holds the bootstrap password); our `grdm-entrypoint.sh` copies the image's pristine `config.dist/` into it (plain `cp -R`: the tmpfs root belongs to root, so a times-preserving copy fails), copies the TLS files into `config/tls/` (Elasticsearch 8.19 reads SSL files only under `config/`) and execs the official entrypoint. Logs and `/tmp` are tmpfs, data is the named volume `elasticsearch8_data`. No hardening exception.
6. **Health.** The Compose health check accepts HTTP 401 on the TLS port: the server answers over TLS with a certificate that chains to the CA while it holds no credential. `elasticsearch8_setup` then waits for the cluster with the credential.
7. **Memory.** Heap 768 MiB, floor 1536 MiB. With the setup one-shot (64 MiB) it replaces ES 2 (1024), mongo (256) and sharejs (128): the core floors add up to 8512 MiB, a lower bound of 11.9 GiB (SPEC-02 §8).
8. **osf_init.** Before `populate_institutions` it runs `invoke search_ensure_index`, which creates `website_v1` and the alias with the full mapping. Without it the first write creates the index with a dynamic mapping and `doc_type` becomes a text field, which breaks aggregations (PR #11).
9. **What is not done.** The ES 2 data is not migrated: after the first `up` on an existing installation, `invoke migrate_search` rebuilds the index from PostgreSQL. `elasticsearch6` stays: django-elasticsearch-metrics speaks the ES 6 protocol, and its removal waits for that client. The old directory `runtime/volumes/elasticsearch_data` is left in place (`grdm-dev` never deletes data it does not manage); it can be removed by hand.

### 3. Options considered

```toon
options[4]{option,reason_for_not_choosing}:
  "ES 8 with security off","one flag, but a search server that accepts any client on the internal network is the exposure ADR-02 exists to avoid; the password and the CA cost one script and one volume"
  "Certificates made by the host (the installer, openssl on the host)","adds a host prerequisite (openssl) and a way for key files to be wrong on Windows; the image already has openssl and unzip"
  "elasticsearch-certutil in an init one-shot with its own volume for the key","the key would be readable by whoever mounts the volume; keeping it in the data volume that only the node mounts is simpler"
  "Writable root for the keystore","one hardening exception for a file that is a few hundred bytes; a tmpfs removes the exception"
```

### 4. Consequences

- A new secret pair, `ELASTIC8_PASSWORD` and `ELASTIC8_OSF_PASSWORD`; `SHAREJS_SECRET` is retired (ADR-13). An installation whose `runtime/.env` predates them runs `grdm-dev secrets init --missing` (it adds only the absent keys, keeps every existing value including the PostgreSQL and RabbitMQ passwords, drops `SHAREJS_SECRET` and needs no running stack), then `compose render`, `build`, `compose render` again and `up`, and once `invoke migrate_search`; the canonical order is in [the environment guide §8](../guides/environment/README.md#english). `secrets rotate` is not part of this upgrade: it changes every credential and recreates containers from the Compose file as it was last rendered, which at that point still names the retired key and services (SPEC-02 §3: render before any rotate).
- Three images change at once for an existing installation (osf.io, y-websocket, ember-osf-web), and the volumes `elasticsearch8_data`, `elasticsearch8_ca` and `y_websocket_data` appear.
- The ES 2 image recipe (`installer/images/elasticsearch2/`) is kept only as a pointer file, because review records link to it (SPEC-06 §8).
- Open: the scan allow-list for the new image's Ubuntu packages is not yet reviewed (SPEC-03 §5.1). The scans after this change have recorded the image's findings (2 HIGH and 30 MEDIUM from Trivy, listed per package and not allow-listed; [DEMO-20](../demo/20_core_install_mac_studio.md#english)); no entry has been proposed or reviewed yet.

---

<a id="japanese"></a>
## 日本語

[→ English version](#english)

### 1. 背景

[ADR-13](ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md) は、osf.io の検索が Elasticsearch 6.8 でも OpenSearch でも動かないことを測り、三つの道を残した。所有者は全文検索を保った Elasticsearch 8 への移植（道 C）を 2026-11-10 に選んだ。osf.io 側は RDM-osf.io-dev2027 の PR #11 である。クライアントは `elasticsearch7` 7.17.13 の互換モードで、索引は一つ（`website_v1`、別名 `website`）に `doc_type` 欄を持たせ、`_all` は `all_text` に替え、日本語の解析器は `analysis-kuromoji` で作り、非公開の内容を答えに出さない権限の絞り込みを保つ。接続は `ELASTIC_URI`・`ELASTIC_USERNAME`・`ELASTIC_PASSWORD`・`ELASTIC_CA_CERTS` で行い、https 以外では認証情報を送らない。

インストーラーは、ほかのすべてのサービスが満たす基準（非 root、読み取り専用のルート、capability を足さない、ポートを公開しない、秘密は `runtime/.env` だけ）の下で使えるサーバーをこれに与えなければならない。

### 2. 決定

1. **イメージは一つ、`grdm-dev/elasticsearch8:8.19.24-1`**（ADR-07 がほかの infra のレシピに行うのと同じ `image_build`）。ベースは公式の `docker.elastic.co/elasticsearch/elasticsearch:8.19.24` をインデックスのダイジェスト（`sha256:d6dfe6626d64…`）で固定したもの。arm64 と amd64 のネイティブ版があるので、組むものも、エミュレーションするものもない。レシピが足すのは `analysis-kuromoji` と `analysis-icu` だけである。
2. **そこから二つのサービス。** `elasticsearch8` はノード。`elasticsearch8_setup` は一回きりの手順で、ブートストラップの管理者で cluster が yellow になるのを待ち、冪等な `PUT` でロール `grdm_osf`（cluster は `monitor`、`website*` と `private__website*` にすべての権限）と利用者 `grdm_osf` を作る。osf.io が受け取るのはその利用者のパスワードだけで、管理者のパスワードは二つの elasticsearch8 サービスにしか届かない。
3. **導入ごとの認証局による TLS。** 初回起動で entrypoint が認証局と、`elasticsearch8`・`localhost`・`127.0.0.1` のサーバー証明書を作り、サーバー鍵をデータボリュームに残し、認証局の鍵は捨てる。公開するのは公開の `ca.crt` だけで、小さなボリューム `elasticsearch8_ca` に置き、osf.io が `ELASTIC_CA_CERTS` として読み取り専用で mount する。これは ADR-07 と PR #43 の mongo の型（一度だけ作った証明書をファイルそのもので信頼する）を引き継ぐもので、信頼は今回もファイルであり、検証を切ることはない。
4. **ES 2 に無かったセキュリティ設定。** `xpack.security` を有効にし、REST のポートを TLS にし（単一ノードなので transport のポートには届かない）、`script.allowed_types: none`（ES 8 は Painless を既定で有効にするが、検索には要らない）、機械学習と GeoIP のダウンロードを切り、`action.destructive_requires_name` を有効にし、ディスクの watermark をバイトで与える（大きなディスクがほぼ満杯でも書き込みが止まらず、小さなディスクなら止まる）。
5. **読み取り専用のルート。** 公式の entrypoint が `elasticsearch.keystore`（ブートストラップのパスワードを持つ）を `config/` に作るので、`config/` は tmpfs にする。自前の `grdm-entrypoint.sh` がイメージの元のままの `config.dist/` をそこへ写し（`cp -R`。tmpfs の根は root のものなので、時刻を保つ複写は失敗する）、TLS のファイルを `config/tls/` へ写し（Elasticsearch 8.19 は SSL のファイルを `config/` の下からしか読まない）、公式の entrypoint を exec する。ログと `/tmp` は tmpfs、データは名前つきボリューム `elasticsearch8_data`。堅牢化の例外はない。
6. **ヘルス。** Compose のヘルスチェックは TLS のポートでの HTTP 401 を受け入れる。認証情報を持たない相手に、認証局に連なる証明書で TLS の応答をする、という意味である。そのあと `elasticsearch8_setup` が認証情報つきで cluster を待つ。
7. **メモリ。** ヒープ 768 MiB、下限 1536 MiB。setup の一回きりの手順（64 MiB）と合わせて ES 2（1024）・mongo（256）・sharejs（128）に替わり、core の下限の合計は 8512 MiB、下限値は 11.9 GiB になる（SPEC-02 §8）。
8. **osf_init。** `populate_institutions` の前に `invoke search_ensure_index` を実行し、`website_v1` と別名を完全なマッピングで作る。これが無いと最初の書き込みが動的マッピングで索引を作り、`doc_type` が text になって集計が壊れる（PR #11）。
9. **しないこと。** ES 2 のデータは移さない。既存の導入では、最初の `up` のあと `invoke migrate_search` が PostgreSQL から索引を作り直す。`elasticsearch6` は残す。django-elasticsearch-metrics が ES 6 のプロトコルを話すので、撤去はそのクライアントを待つ。古い `runtime/volumes/elasticsearch_data` はそのまま残す（`grdm-dev` は自分が管理しないデータを消さない）。手で消してよい。

### 3. 検討した選択肢

```toon
options[4]{option,reason_for_not_choosing}:
  "セキュリティを切った ES 8","フラグ一つで済むが、内部ネットワークのどのクライアントも受け入れる検索サーバーは ADR-02 が避けようとする露出である。パスワードと認証局のための費用はスクリプト一つとボリューム一つ"
  "ホスト（インストーラー、ホストの openssl）が証明書を作る","ホストに openssl という前提を足し、Windows で鍵ファイルが壊れる道を作る。イメージにはすでに openssl と unzip がある"
  "init の一回きりの手順で elasticsearch-certutil を動かし、鍵を専用ボリュームに置く","そのボリュームを mount した者に鍵が読める。ノードだけが mount するデータボリュームに置くほうが簡単"
  "キーストアのためにルートを書き込み可にする","数百バイトのファイルのために堅牢化の例外を一つ作る。tmpfs なら例外が要らない"
```

### 4. 結果

- 秘密が二つ増える（`ELASTIC8_PASSWORD`、`ELASTIC8_OSF_PASSWORD`）。`SHAREJS_SECRET` は退役する（ADR-13）。これらより前に作られた `runtime/.env` の導入は、`grdm-dev secrets init --missing`（足りないキーだけを足し、PostgreSQL と RabbitMQ のパスワードを含む既存の値はすべて保ち、`SHAREJS_SECRET` を捨てる。稼働中のスタックは要らない）を実行し、続けて `compose render`、`build`、もう一度 `compose render`、`up`、そして一度だけ `invoke migrate_search` を実行する。正本の順序は[環境ガイド §8](../guides/environment/README.md#japanese)にある。`secrets rotate` はこの更新に含めない。すべての資格情報を替え、最後に生成した Compose ファイルのままコンテナを再作成するが、その時点のファイルはまだ廃止したキーとサービスを名指ししている（SPEC-02 §3: rotate の前に render）。
- 既存の導入では三つのイメージ（osf.io、y-websocket、ember-osf-web）が同時に変わり、ボリューム `elasticsearch8_data`・`elasticsearch8_ca`・`y_websocket_data` が現れる。
- ES 2 のイメージのレシピ（`installer/images/elasticsearch2/`）は、レビュー記録がそれにリンクするため、指し示すだけのファイルとして残す（SPEC-06 §8）。
- 未了: 新しいイメージの Ubuntu パッケージに対する検査の許容リストはまだ見直していない（SPEC-03 §5.1）。この変更のあとの検査はイメージの検出を記録済み（Trivy の HIGH 2 件と MEDIUM 30 件。パッケージごとに列挙し、許容はしていない。[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）で、項目の提案も見直しもまだ行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Keystore | A small file where Elasticsearch keeps secret settings such as the bootstrap password. | Elasticsearch が、ブートストラップのパスワードのような秘密の設定を入れておく小さなファイル。 |
| Certificate authority (CA) | The party whose signature makes a certificate trusted; here one made per installation, with its private key discarded. | 署名によって証明書を信頼できるものにする主体。ここでは導入ごとに作り、秘密鍵は捨てる。 |
| Tmpfs | A memory-backed folder inside a container; it vanishes when the container stops. | コンテナの中のメモリ上のフォルダ。コンテナが止まると消える。 |
| One-shot | A container that does one job and exits; Compose treats exit code 0 as success. | 一つの仕事をして終了するコンテナ。Compose は終了コード 0 を成功として扱う。 |
