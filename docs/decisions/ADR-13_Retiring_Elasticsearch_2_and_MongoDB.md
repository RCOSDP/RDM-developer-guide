# ADR-13 Retiring Elasticsearch 2 and MongoDB / Elasticsearch 2 と MongoDB の退役

> **Summary:** Measured findings and a proposal for the two remaining M5 removals. **Elasticsearch 2:** osf.io's search code cannot run on Elasticsearch 6.8 or OpenSearch 2.19, even after a shim for the missing Content-Type header: an index holds one mapping type only, and every query fails to parse. Turning search off (`SEARCH_ENGINE = None`) keeps writes working but makes five read endpoints answer 500 or `null`; a prototype patch of about 50 lines makes all of them answer well-formed empty results and moves contributor search to PostgreSQL with the same institution rule. A real port to Elasticsearch 8 or OpenSearch works on an affected code surface of about 5,300 lines in the integration repository. **MongoDB:** only sharejs uses it. osf.io's own reader (the `/draft/` route) resolves to `mongodb://postgres:5432/sharejs` in this environment and times out after 30 s. The only browser feature on sharejs is the file page's text editor, whose real-time co-editing is what retiring sharejs removes (since PR #40 sharejs is published on 127.0.0.1:7007; the editor was not exercised in a browser here); the exact steps are listed. On 2026-11-10 the owner chose the port to Elasticsearch 8 with full-text search, and the move of the file-page editor to y-websocket before sharejs and mongo are retired; both are in progress (§4).
> **概要:** M5 に残る二つの撤去について、測定した事実と提案をまとめる。**Elasticsearch 2:** osf.io の検索コードは、欠けている Content-Type ヘッダーを補う互換層を入れても、Elasticsearch 6.8 でも OpenSearch 2.19 でも動かない。一つのインデックスは一つのマッピング型しか持てず、すべての問い合わせが構文解析で失敗する。検索を切る（`SEARCH_ENGINE = None`）と書き込みは動くが、読み取りの五つの入口が 500 か `null` を返す。約 50 行の試作パッチで、そのすべてが形の整った空の結果を返し、協力者の検索は同じ機関の規則のまま PostgreSQL に移る。Elasticsearch 8 か OpenSearch への本当の移植は、統合リポジトリの約 5,300 行の影響範囲での作業になる。**MongoDB:** 使うのは sharejs だけである。osf.io 自身の読み手（`/draft/` 経路）はこの環境では `mongodb://postgres:5432/sharejs` を指して 30 秒で時間切れになる。sharejs に乗るブラウザの機能はファイルページのテキストエディタだけで、sharejs の退役で失われるのはその実時間の共同編集である（PR #40 以降 sharejs は 127.0.0.1:7007 で公開されている。ここではブラウザでエディタを試していない）。正確な手順を挙げる。2026-11-10 に所有者は、全文検索を保った Elasticsearch 8 への移植と、sharejs と mongo の退役に先立つファイルページのエディタの y-websocket への移行を選んだ。どちらも進行中である（§4）。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.4 — 2026-11-12. **Learned:** a retirement plan is finished when the consumer is gone, not when the replacement exists: sharejs and mongo could leave the installer only after osf.io's own reader (PR #12) was removed, and the ES 2 service only after osf.io's client moved (PR #11), so §6 records the order the installer followed and what is still left (Elasticsearch 6 for the metrics client). ／ 退役の計画は、置き換えができたときでなく、使う側がなくなったときに終わる。sharejs と mongo がインストーラーから消えてよいのは osf.io 自身の読み手（PR #12）が消えた後であり、ES 2 のサービスは osf.io のクライアントが移った後（PR #11）だった。§6 は、インストーラーが従った順序と、まだ残るもの（メトリクスのクライアントのための Elasticsearch 6）を記録する。
  0.3 — 2026-11-10. **Learned:** the header must say what the body records: once §4 held the owner's choices, "nothing yet" was wrong, while the record stays Proposed (PR #42 review r2). ／ 見出しは本文が記録するものを言わなければならない。§4 が所有者の選択を持った時点で「まだ無い」は誤りになったが、記録自体は提案中のまま（PR #42 レビュー r2）。
  0.2 — 2026-11-10. **Learned:** a finding is only as wide as its measurement: the drafts claim covered one reader, the line count is a code surface rather than work measured, and "every page" meant the probed entry points; and once the owner has chosen, the record keeps the options as the reasons for the choice (§4, PR #42 review r1). ／ 事実の広さは測定の広さまでである。下書きの主張は一つの読み手にしか及ばず、行数は作業量の実測ではなくコードの範囲で、「すべてのページ」は調べた入口のことだった。所有者が選んだ後は、選択肢を選んだ理由として記録に残す（§4、PR #42 レビュー r1）。
  0.1 — 2026-11-10. **Learned:** a setting that "disables" a backend is not a supported mode until every reader handles the empty answer: `SEARCH_ENGINE = None` was accepted by every write path and broke every read path, and a client library pinned to an old server fails on the first header before any real incompatibility shows. ／ バックエンドを「無効にする」設定は、すべての読み手が空の答えを扱えるまで、支えられた動作モードではない。`SEARCH_ENGINE = None` はすべての書き込みの経路に受け入れられ、すべての読み取りの経路を壊した。また古いサーバーに合わせたクライアントライブラリは、本当の非互換が見える前に最初のヘッダーで失敗する。
- Status: Proposed (2026-11-10, M5 groundwork); the owner approves the record. The owner chose the paths on 2026-11-10 (§4); the installer side of both is implemented in §6 (ADR-14 for Elasticsearch 8).
- Records a decision for: the owner's chosen direction of 2026-11-10 (§4) — the Elasticsearch 8 port and the move of the file-page editor to y-websocket before sharejs and mongo are retired. The record itself stays Proposed, and the implementations are other pull requests: this one removes nothing. It will change `manifest/upstreams.json` (`elasticsearch2`, `mongo`, `sharejs`), [SPEC-04](../spec/04_acceptance_tests.md#english) (C4 services) and the osf.io integration repository.
- Related: [docs/decisions/README.md](README.md) · [ADR-07 §5](ADR-07_Native_Builds_of_EOL_Middleware.md#english) (sharejs on Node 24) · [ADR-12 PostgreSQL 18](ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md) · [Status board](../status/README.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Context

The status board's M5 row says "ES2 and mongo removed; ES8". Elasticsearch 2.4.6 runs today as a native build (ADR-07), MongoDB 3.4 as the official image with a hardening exception. Both are end of life. All measurements below used osf.io image `grdm-dev/osf.io:fe90e5c39e66` (integration commit `fe90e5c39e660f464bb8fcc9ae4028119b958d19`) on PostgreSQL 18 in the throwaway project `m5-pg18a`, with a probe that creates a project through API v2 and calls the search entry points: `/api/v1/search/`, `/search/`, contributor search (`website.search.search.search_contributor`, the function behind `/api/v1/user/search/`), `/v2/search/`, `/v2/search/users/`, `/v2/search/projects/`.

### 2. Elasticsearch 2: findings

```toon
search_modes[7]{mode,create_index_and_writes,reads}:
  "ES 2.4.6 (today)","all succeed","all 200 with results"
  "search off (SEARCH_ENGINE = None)","project creation 201","/api/v1/search/ 500 TypeError; /v2/search/* 500 TypeError; contributor search returns null; /search/ page 200 but its requests fail"
  "ES 6.8.23, unchanged client","every call: Content-Type header [] is not supported","every call fails the same way"
  "ES 6.8.23 + Content-Type shim (8 lines)","index created; institutions indexed; projects and users rejected: Rejecting mapping update to [website] as the final mapping would have more than 1 type","every search 400: [query_string] cannot use [fields] parameter in conjunction with [default_field]"
  "OpenSearch 2.19.5, unchanged client","index created; indexing fails in the client: TypeError string indices must be integers","Content-Type header [] is not supported"
  "OpenSearch 2.19.5 + shim","same TypeError on indexing","every search 400 (same query error)"
  "search off + prototype patch (about 50 lines)","project creation 201","every entry point 200 with a well-formed empty result; contributor search returns the user from PostgreSQL"
```

The client is `elasticsearch2` 2.5.0 (the old Python client under a renamed package); the ES 6 client in the image (`elasticsearch` 6.3.1) is used only for metrics. Code bound to the ES 2 client and query language: `website/search/` (elastic_search.py 1,951 lines, util.py 626, search.py 223, views.py 422), `website/search_migration/` (1,293), `api/search/views.py` (711) and `addons/metadata/search.py` (123) — about 5,300 lines. It keeps twelve document types (project, component, registration, user, file, wiki, comment, institution, preprint, group, metadata, collectionSubmission) in one index `website`, uses `query_string` with both `fields` and `default_field`, and the old `filtered` query.

**Smallest supported path: search off with a patch.** The prototype replaces `website.search.search.search` with a function that returns `{'results': [], 'counts': {'total': 0}, 'aggs': {…: 0}, …}` (the API v2 paginator reads `aggs.total` and `counts.<type>`) and `search_contributor` with a PostgreSQL query: active, registered, not merged users whose full name contains every word or whose username equals the query, excluding the given users, and limited to the current user's institutions when the user has any (the rule of the ES query). The search page, API v2 search and the private-search features then return nothing. No core acceptance scenario (C1–C6) calls a search endpoint. `osf_init` no longer needs to wait for a search engine.

**Costs.**

```toon
paths[3]{path,where,cost,keeps}:
  "A: keep ES 2.4.6 (native build, ADR-07)","nothing","an EOL engine stays past M5; the M5 row is not met","full search"
  "B: search off + patch (prototype measured)","osf.io integration repository (about 50 lines in website/search, tests for the five entry points); installer: drop elasticsearch2, the osf_init wait loop and ELASTIC_URI","no full-text search of projects, files, wikis or metadata; contributor search becomes substring matching without kana normalisation or fuzziness","writes, contributor search with the institution rule; every probed entry point answers 200"
  "C: port to Elasticsearch 8 or OpenSearch","osf.io integration repository: work on an affected code surface of about 5,300 lines — a size of the code bound to ES 2, not a measured count of lines to change — (one index per document type or a type field, the query builders, the client, the Japanese analyzer setup, the search migration)","weeks of work and its own review; a new image and data volume","full search on a supported engine"
```

### 3. MongoDB and sharejs: findings

1. **Clients of mongo.** In the installer only `sharejs` connects (`SHAREJS_DB_URL=mongodb://mongo:27017/sharejs?ssl=true`). osf.io has a pymongo reader, `addons/wiki/utils.py` `share_db()`, but its URL is built from `DB_HOST` and `DB_PORT`, which this environment sets for PostgreSQL: it resolves to `mongodb://postgres:5432/sharejs`, and a read raised `ServerSelectionTimeoutError` after 30.3 s (measured).
2. **Callers of that reader.** `WikiVersion.get_draft` and `get_sharejs_content`, both only through `wiki_page_draft` (route `/project/<pid>/wiki/<wname>/draft/`). The current wiki editor (`wikiPageMilkdown.js` of RDM-wiki-frontend-dev2027 at `5985d18b75da4105a610ac041b838c45f295de7d`) stores `urls.draft` but never requests it; only the legacy `ShareJSDoc.js`/`WikiEditor.js` do. `delete_share_doc` and `migrate_uuid` have no callers outside tests. `broadcast_to_sharejs` (on wiki rename and delete) posts to `localhost:7007` and ignores a connection error.
3. **Browser.** The file page loads `//<sharejs>/text.js` and `share.js` (`view_file.mako`), and its Edit panel (`filepage/editor.js`, `ShareJSDocFile.js`, 350 lines) uses ShareJS. When these measurements were taken (installer at `03c7358`) the browser was given `localhost:7007` and sharejs published no port, so the panel showed only a spinner (ADR-07 §5). PR #40 published sharejs on `127.0.0.1:7007` and gives the browser that URL, so the panel can now reach sharejs; it was not exercised in a browser for this record.
4. **Acceptance.** SPEC-04 C4 lists `sharejs` among its services, but the scenario tests the wiki over `y_websocket` only.

**What the file page loses:** real-time co-editing of a text file in the Edit panel. Choice (a) below drops it; choice (b) rebuilds it on y-websocket like the wiki.

**Retirement plan (in this order).**

1. *osf.io integration repository, first PR.* Choose the file-page editor: (a) a plain editor that saves through WaterButler as today, without co-editing, or (b) a Yjs document per file on y-websocket, with a token from osf.io (`generate_y_websocket_token` with a file-scoped room and a WRITE check) and an editor binding. Remove the sharejs script tags from `view_file.mako`; remove `wiki_page_draft` and its route, `WikiVersion.get_draft`, `get_sharejs_content`, `delete_share_doc`, `migrate_uuid`, `share_db`, `broadcast_to_sharejs` with its calls, and `update_active_sharejs`; the `SHAREJS_*` settings; `pymongo==3.7.1` from `requirements.txt`; the sharejs parts of the tests in `addons/wiki/tests/` (5 files) and `tests/test_addons.py`. Keep `wiki_private_uuids` and `get_sharejs_uuid`: y-websocket room names come from them.
2. *Data.* Before removal, a developer who wants the drafts runs `mongoexport` of `sharejs.docs` into `runtime/backups/`; otherwise they are discarded. The measured wiki reader (`share_db`) cannot reach them here (item 1 above); that does not prove that no draft text reached a saved file, because the file page saves its text through its own HTTP PUT.
3. *This repository, second PR.* Remove the `mongo` and `sharejs` components, `templates/mongo.json`, `templates/sharejs.json`, `installer/images/sharejs/`, `sharejs.env`, the published port 7007 and the browser's `SHAREJS_URL` from `compose render` (PR #40), the volumes `mongo_data` and `mongo_tls`, the `mongo` entry of `manifest/hardening.json`, `SHAREJS_SECRET` from the templates and `secrets.py` once osf.io stops reading it, and `sharejs` from the C4 services in SPEC-04. Bump the osf.io pin to the commit of step 1.

### 4. Owner decisions (2026-11-10)

1. **Elasticsearch 2: path C now.** osf.io search is ported to Elasticsearch 8, keeping full-text search; the work is in progress in the osf.io integration repository. Path B stays recorded as the measured fallback, not the plan.
2. **File page: choice (b).** The file-page editor moves from sharejs to y-websocket; then sharejs and mongo are retired by the steps of §3 (in progress). The drafts question (step 2) follows from that work.
3. **Also decided for M4 (recorded here because it was decided the same day):** freecad is removed from MFR, and the remaining OS packages for which the distribution publishes no fix are allow-listed.

### 5. The prototype of path B (author-reported)

The measurement logs and the prototype were throwaway files; their numbers in §2 are as reported by the author. The prototype, for reproduction, was loaded before Django set up the search module:

```python
import math
from django.db.models import Q
from website.search import search as _search


def _empty(*args, **kwargs):
    counts = dict.fromkeys(('total', 'users', 'projects', 'components', 'registrations', 'files',
                            'institutions', 'collectionSubmissions'), 0)
    return {'results': [], 'counts': {'total': 0}, 'aggs': counts, 'tags': [], 'typeAliases': {}}


def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
    from osf.models import OSFUser
    from website.profile.utils import profile_image_url
    from website import settings
    qs = OSFUser.objects.filter(is_active=True, is_registered=True, merged_by__isnull=True)
    for word in (query or '').split():
        qs = qs.filter(Q(fullname__icontains=word) | Q(username__iexact=word))
    if exclude:
        qs = qs.exclude(id__in=[u.id for u in exclude])
    if current_user and current_user.affiliated_institutions.exists():
        qs = qs.filter(affiliated_institutions__in=current_user.affiliated_institutions.all()).distinct()
    total = qs.count()
    users = [{'fullname': u.fullname, 'id': u._id, 'employment': None, 'education': None, 'social': u.social_links,
              'n_projects_in_common': -1 if current_user and current_user._id == u._id
              else (current_user.n_projects_in_common(u) if current_user else 0),
              'profile_image_url': profile_image_url(settings.PROFILE_IMAGE_PROVIDER, u, use_ssl=True,
                                                     size=settings.PROFILE_IMAGE_MEDIUM),
              'profile_url': u.profile_url, 'registered': u.is_registered, 'active': u.is_active}
             for u in qs.order_by('fullname')[page * size:(page + 1) * size]]
    return {'users': users, 'total': total, 'pages': math.ceil(total / size), 'page': page}


_search.search = _empty
_search.search_contributor = search_contributor
```

### 6. Implementation in the installer (2026-11-12)

The order the installer followed, one consumer at a time:

1. *RDM-osf.io-dev2027 PR #12* (merged): the file page and the wiki edit on y-websocket and osf.io no longer reads MongoDB (`pymongo` stays only for `bson`). Only then were `sharejs`, `mongo`, `templates/sharejs.json`, `templates/mongo.json`, `installer/images/sharejs/`, `sharejs.env`, the loopback port 7007, `SHAREJS_URL`, the volumes `mongo_data` and `mongo_tls`, `SHAREJS_SECRET` and the mongo hardening exception removed. y-websocket gained a volume (`y_websocket_data`) and `YPERSISTENCE=/data` with `YPERSISTENCE_DOC_PREFIX=file-`, so drafts of file rooms survive a restart and the last user leaving (the question of step 2); wiki rooms stay in memory. osf.io receives `Y_WEBSOCKET_INTERNAL_URL` (it deletes the room of a replaced file version) and the shared secret.
2. *RDM-osf.io-dev2027 PR #11*: Elasticsearch 8, recorded in [ADR-14](ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md). The `elasticsearch2` component, `templates/elasticsearch.json` (kept as a pointer for review links) and the recipe `installer/images/elasticsearch2/` (kept as a pointer) are gone; the osf_init wait loop for the emulated ES 2 became `invoke search_ensure_index`.
3. *Left:* `elasticsearch6` (the metrics client), PostgreSQL 15 or later is done (ADR-12). M5's "ES2 and mongo removed" is therefore met in the installer; the rest of M5 (zero CRITICAL/HIGH, red team) is not part of this record.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 背景

ステータスボードの M5 の行は「ES2・mongo 廃止。ES8」と書く。Elasticsearch 2.4.6 は今ネイティブのビルド（ADR-07）で、MongoDB 3.4 は公式イメージと堅牢化の例外で動いている。どちらも EOL である。以下の測定はすべて、使い捨てのプロジェクト `m5-pg18a` の PostgreSQL 18 の上で osf.io のイメージ `grdm-dev/osf.io:fe90e5c39e66`（統合コミット `fe90e5c39e660f464bb8fcc9ae4028119b958d19`）を使った。調べる道具は API v2 でプロジェクトを作り、検索の入口を呼ぶ: `/api/v1/search/`、`/search/`、協力者の検索（`website.search.search.search_contributor`。`/api/v1/user/search/` の中身）、`/v2/search/`、`/v2/search/users/`、`/v2/search/projects/`。

### 2. Elasticsearch 2: 事実

```toon
search_modes[7]{mode,create_index_and_writes,reads}:
  "ES 2.4.6（現状）","すべて成功","すべて 200 で結果あり"
  "検索を切る（SEARCH_ENGINE = None）","プロジェクト作成は 201","/api/v1/search/ は 500 TypeError。/v2/search/* は 500 TypeError。協力者の検索は null。/search/ のページは 200 だが中の要求が失敗"
  "ES 6.8.23、クライアントは変更なし","すべての呼び出しが Content-Type header [] is not supported","すべて同じ理由で失敗"
  "ES 6.8.23 と Content-Type の互換層（8 行）","インデックス作成と機関の登録は成功。プロジェクトと利用者は Rejecting mapping update to [website] as the final mapping would have more than 1 type で拒否","すべての検索が 400: [query_string] cannot use [fields] parameter in conjunction with [default_field]"
  "OpenSearch 2.19.5、クライアントは変更なし","インデックス作成は成功。登録はクライアント内で TypeError string indices must be integers","Content-Type header [] is not supported"
  "OpenSearch 2.19.5 と互換層","登録は同じ TypeError","すべての検索が 400（同じ問い合わせの誤り）"
  "検索を切る＋試作パッチ（約 50 行）","プロジェクト作成は 201","すべての入口が 200 で形の整った空の結果。協力者の検索は PostgreSQL から利用者を返す"
```

クライアントは `elasticsearch2` 2.5.0（古い Python クライアントを別名のパッケージにしたもの）である。イメージにある ES 6 のクライアント（`elasticsearch` 6.3.1）はメトリクスにしか使われない。ES 2 のクライアントと問い合わせ言語に結びついたコードは、`website/search/`（elastic_search.py 1,951 行、util.py 626、search.py 223、views.py 422）、`website/search_migration/`（1,293）、`api/search/views.py`（711）、`addons/metadata/search.py`（123）で、約 5,300 行になる。一つのインデックス `website` に十二種類の文書型（project・component・registration・user・file・wiki・comment・institution・preprint・group・metadata・collectionSubmission）を置き、`query_string` に `fields` と `default_field` を両方渡し、古い `filtered` の問い合わせを使う。

**支えられる最小の道: 検索を切ってパッチを当てる。** 試作は `website.search.search.search` を `{'results': [], 'counts': {'total': 0}, 'aggs': {…: 0}, …}` を返す関数に置き換え（API v2 のページ分けは `aggs.total` と `counts.<型>` を読む）、`search_contributor` を PostgreSQL の問い合わせに置き換える。対象は有効・登録済み・未統合の利用者で、氏名がすべての語を含むか利用者名が問い合わせと一致するもの。指定された利用者を除き、今の利用者が機関に属していればその機関に限る（ES の問い合わせと同じ規則）。検索ページ、API v2 の検索、非公開検索の機能は何も返さなくなる。コアの受入シナリオ（C1〜C6）はどれも検索の入口を呼ばない。`osf_init` は検索エンジンを待つ必要がなくなる。

**代償。**

```toon
paths[3]{path,where,cost,keeps}:
  "A: ES 2.4.6 を残す（ネイティブのビルド、ADR-07）","なし","EOL のエンジンが M5 の後も残る。M5 の行を満たさない","検索のすべて"
  "B: 検索を切る＋パッチ（試作を測定済み）","osf.io の統合リポジトリ（website/search に約 50 行と、五つの入口の試験）。インストーラーでは elasticsearch2、osf_init の待ちの繰り返し、ELASTIC_URI を除く","プロジェクト・ファイル・wiki・メタデータの全文検索がなくなる。協力者の検索は部分一致になり、かなの正規化とあいまい一致がなくなる","書き込み、機関の規則つきの協力者の検索。調べた入口はすべて 200"
  "C: Elasticsearch 8 か OpenSearch へ移植","osf.io の統合リポジトリ: 約 5,300 行の影響範囲での作業（ES 2 に結びついたコードの大きさであり、変える行数の実測ではない）（文書型ごとのインデックスか型の欄、問い合わせの組み立て、クライアント、日本語の解析器の設定、検索の移行）","数週間の作業と独自のレビュー。新しいイメージとデータボリューム","支えられたエンジンでの検索のすべて"
```

### 3. MongoDB と sharejs: 事実

1. **mongo のクライアント。** インストーラーの中で接続するのは `sharejs` だけである（`SHAREJS_DB_URL=mongodb://mongo:27017/sharejs?ssl=true`）。osf.io には pymongo の読み手 `addons/wiki/utils.py` の `share_db()` があるが、その URL は `DB_HOST` と `DB_PORT` から作られ、この環境ではそれが PostgreSQL 向けに設定されている。結果は `mongodb://postgres:5432/sharejs` になり、読み取りは 30.3 秒後に `ServerSelectionTimeoutError` で失敗した（測定）。
2. **その読み手を呼ぶもの。** `WikiVersion.get_draft` と `get_sharejs_content` で、どちらも `wiki_page_draft`（経路 `/project/<pid>/wiki/<wname>/draft/`）からしか呼ばれない。今の wiki エディタ（RDM-wiki-frontend-dev2027 の `5985d18b75da4105a610ac041b838c45f295de7d` の `wikiPageMilkdown.js`）は `urls.draft` を保持するが要求はしない。要求するのは旧来の `ShareJSDoc.js` と `WikiEditor.js` だけである。`delete_share_doc` と `migrate_uuid` を試験の外で呼ぶものは無い。`broadcast_to_sharejs`（wiki の改名と削除のとき）は `localhost:7007` へ送り、接続の誤りは無視する。
3. **ブラウザ。** ファイルページは `//<sharejs>/text.js` と `share.js` を読み込み（`view_file.mako`）、その編集パネル（`filepage/editor.js`、`ShareJSDocFile.js`、350 行）は ShareJS を使う。測定の時点（インストーラーは `03c7358`）ではブラウザに `localhost:7007` が渡され、sharejs はポートを公開しなかったので、パネルはスピナーのままだった（ADR-07 §5）。PR #40 は sharejs を `127.0.0.1:7007` で公開し、ブラウザにその URL を渡すので、パネルは今は sharejs に届きうる。この記録のためにブラウザでは試していない。
4. **受入。** SPEC-04 の C4 はサービスに `sharejs` を挙げるが、シナリオが試すのは `y_websocket` 上の wiki だけである。

**ファイルページが失うもの:** 編集パネルでのテキストファイルの実時間の共同編集。下の (a) ではそれを手放し、(b) では wiki と同じく y-websocket の上に作り直す。

**退役の手順（この順で）。**

1. *osf.io の統合リポジトリ、最初の PR。* ファイルページのエディタを選ぶ。(a) 共同編集なしで今と同じく WaterButler を通して保存する素のエディタ、または (b) y-websocket 上のファイルごとの Yjs 文書。トークンは osf.io から出し（ファイル単位の部屋と WRITE の確認を加えた `generate_y_websocket_token`）、エディタの結び付けを使う。`view_file.mako` から sharejs の script タグを除く。`wiki_page_draft` とその経路、`WikiVersion.get_draft`、`get_sharejs_content`、`delete_share_doc`、`migrate_uuid`、`share_db`、`broadcast_to_sharejs` とその呼び出し、`update_active_sharejs` を除く。`SHAREJS_*` の設定、`requirements.txt` の `pymongo==3.7.1`、`addons/wiki/tests/` の試験（5 ファイル）と `tests/test_addons.py` の sharejs の部分も除く。`wiki_private_uuids` と `get_sharejs_uuid` は残す。y-websocket の部屋の名前がそこから作られるからである。
2. *データ。* 撤去の前に、下書きが欲しい開発者は `sharejs.docs` を `mongoexport` で `runtime/backups/` に書き出す。そうでなければ捨てる。測定した wiki の読み手（`share_db`）はここでは下書きに届かない（上の 1）。ただしファイルページは自分の HTTP PUT で本文を保存するので、下書きの文が保存済みのファイルに一度も届いていないことの証明にはならない。
3. *本リポジトリ、二つ目の PR。* 部品 `mongo` と `sharejs`、`templates/mongo.json`、`templates/sharejs.json`、`installer/images/sharejs/`、`compose render` の `sharejs.env`、公開ポート 7007、ブラウザ向けの `SHAREJS_URL`（PR #40）、ボリューム `mongo_data` と `mongo_tls`、`manifest/hardening.json` の `mongo` の項目を除く。`SHAREJS_SECRET` は osf.io が読まなくなった後でテンプレートと `secrets.py` から除く。SPEC-04 の C4 のサービスから `sharejs` を除く。osf.io の固定を手順 1 のコミットに上げる。

### 4. 所有者の判断（2026-11-10）

1. **Elasticsearch 2: 道 C を今行う。** osf.io の検索を全文検索を保ったまま Elasticsearch 8 へ移植する。作業は osf.io の統合リポジトリで進行中である。道 B は測定した代替として記録に残すが、計画ではない。
2. **ファイルページ: (b) を選ぶ。** ファイルページのエディタを sharejs から y-websocket へ移し、その後 §3 の手順で sharejs と mongo を退役させる（進行中）。下書きの扱い（手順 2）はその作業の中で決まる。
3. **M4 についても同日に決定（同じ日の決定なのでここに記録する）:** MFR から freecad を除き、配布元が修正を出していない残りの OS パッケージは許容リストに入れる。

### 5. 道 B の試作（著者の報告）

測定のログと試作は使い捨てのファイルだったので、§2 の数値は著者の報告による。再現のための試作を英語の節 §5 に載せた。Django が検索のモジュールを用意する前に読み込んだ。

### 6. インストーラーでの実施（2026-11-12）

インストーラーが従った順序。使う側を一つずつなくした。

1. *RDM-osf.io-dev2027 PR #12*（マージ済み）: ファイルページと wiki が y-websocket で編集され、osf.io は MongoDB を読まなくなった（`pymongo` は `bson` のためだけに残る）。それを待って初めて、`sharejs`、`mongo`、`templates/sharejs.json`、`templates/mongo.json`、`installer/images/sharejs/`、`sharejs.env`、ループバックのポート 7007、`SHAREJS_URL`、ボリューム `mongo_data` と `mongo_tls`、`SHAREJS_SECRET`、mongo の堅牢化の例外を外した。y-websocket にはボリューム（`y_websocket_data`）と `YPERSISTENCE=/data`、`YPERSISTENCE_DOC_PREFIX=file-` を与え、ファイルの部屋の下書きが再起動と最後の利用者の退出を越えて残るようにした（手順 2 の問い）。wiki の部屋はメモリのまま。osf.io には `Y_WEBSOCKET_INTERNAL_URL`（置き換えたファイル版の部屋を消すため）と共通の秘密を渡す。
2. *RDM-osf.io-dev2027 PR #11*: Elasticsearch 8（[ADR-14](ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md)）。部品 `elasticsearch2`、`templates/elasticsearch.json`（レビューのリンクのため指し示すだけのファイルとして残す）、レシピ `installer/images/elasticsearch2/`（同じく指し示すだけ）は無くなり、エミュレーションの ES 2 を待つ osf_init のループは `invoke search_ensure_index` になった。
3. *残り:* `elasticsearch6`（メトリクスのクライアント）。PostgreSQL 15 以降は済んでいる（ADR-12）。したがって M5 の「ES2・mongo 廃止」はインストーラーでは満たされ、M5 の残り（CRITICAL/HIGH ゼロ、レッドチーム）はこの記録の対象ではない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Mapping type | A kind of document inside an Elasticsearch index; from version 6 an index may hold only one. | Elasticsearch のインデックスの中の文書の種類。版 6 からは一つのインデックスに一つしか置けない。 |
| Compatibility shim | A small piece of code that makes an old client speak to a newer server. | 古いクライアントを新しいサーバーと話せるようにする小さなコード。 |
| ShareJS | The older real-time co-editing server; it keeps documents in MongoDB. | 旧来の実時間共同編集サーバー。文書を MongoDB に置く。 |
| y-websocket | The co-editing server the wiki uses now. | wiki が今使う共同編集サーバー。 |
