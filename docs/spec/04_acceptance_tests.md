# SPEC-04 Acceptance Tests / 受入試験

> **Summary:** How we prove that an installed GakuNin RDM developer environment really works: the three test tiers, the browser scenarios for the core and each subsystem, test data, evidence, and the pass criteria for each milestone.
> **概要:** 導入した GakuNin RDM 開発環境が本当に動くことを示す方法。三つの試験の段、コアと各サブシステムのブラウザシナリオ、試験データ、証跡、節目ごとの合格基準を定める。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-05. **Learned:** downloading a browser inside a test run would make the run depend on the network, so installation is a separate, explicit step and `accept` only checks for it. ／ 試験の実行中にブラウザをダウンロードすると実行がネットワークに依存するため、導入は別の明示的な手順にし、`accept` は有無を確かめるだけにする。
  0.2 — 2026-11-05. **Learned:** a case that may skip in the profile a milestone is judged on cannot be a pass criterion, and a diagram that renders in one language half must parse in the other too. ／ 節目を判定するプロファイルでスキップし得るケースは合格基準になれず、片方の言語で描ける図はもう片方でも解析できなければならないと分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** a scenario without a rejection case proves only that the happy path renders; permission and authentication bugs are found by the case that must fail. ／ 拒否ケースのないシナリオは画面が出ることしか示さず、権限と認証の不具合は「失敗しなければならないケース」で初めて見つかると分かった。
- Normative for: `installer/acceptance/`, `grdm-dev accept`, `docs/demo/` result files, CI workflow `acceptance-arm64`.
- Related: [SPEC-00 Overview](00_overview.md) · [SPEC-01 Manifest](01_manifest.md) · [SPEC-02 Installer CLI](02_installer_cli.md) · [SPEC-03 Security Gate](03_security_gate.md) · [SPEC-05 Upstream Tracking](05_upstream_tracking.md) · [SPEC-06 Documentation Conventions](06_documentation_conventions.md) · [ADR-02 Network Model](../decisions/ADR-02_Network_Model.md) · [ADR-03 Staged Security Gate](../decisions/ADR-03_Staged_Security_Gate.md) · [POL-01 Position](../policy/POL-01_Developer_Environment_2027_Position.md) · [docs/README.md](../README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Scope and tooling

Acceptance tests drive a real browser against the environment that [SPEC-02](02_installer_cli.md) installed, the way a researcher would use it. They are written in Python with **Playwright** (a library that opens a browser and clicks, types, and reads pages for you) through **pytest-playwright** (a plugin that lets the *pytest* test runner hand each test a ready browser page).

- Location: `installer/acceptance/`, one file per scenario, named `test_<scenario>.py`.
- Runner: `grdm-dev accept [--profile ...] [--only <scenario>] [--json]`. It runs `pytest` inside the same `.venv/` that `install.sh` created ([SPEC-02 §2.2](02_installer_cli.md#english)) and exits 60 if any test fails.
- Browsers: `grdm-dev accept` checks that Chromium is present under `PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright/` and, if not, exits 2 and prints the exact install command (`pip install -e "installer[accept]"` then `playwright install chromium` with that variable). The download is a one-time setup step, never part of a test run. Nothing is installed outside the venv.
- Target URL: always `http://127.0.0.1:<port>` as published by `compose render` ([ADR-02](../decisions/ADR-02_Network_Model.md); defaults in the ports table of [SPEC-02 §4](02_installer_cli.md#2-en-ports)). Tests read the ports from `runtime/.env` (`GRDM_PORT_<SERVICE>`); they never hard-code them.

### 2. Test tiers

| Tier | Where | Tool | Needs Docker | What it proves |
|---|---|---|---|---|
| Unit | `installer/tests/` | `unittest` | no | Each `grdm_dev` module and every exit code in [SPEC-02 §6](02_installer_cli.md#english) |
| Integration | `installer/acceptance/integration/` | `pytest` + `urllib` | yes | `compose up` reaches health, API answers over HTTP, loopback-only binding |
| Acceptance | `installer/acceptance/` | `pytest-playwright` | yes | A person can do the core tasks in a browser, and forbidden actions are refused |

`grdm-dev accept` runs integration first and stops before acceptance if integration fails, because a browser test against a half-started stack produces noise, not evidence.

### 3. Scenario rules

1. **Every scenario has a success case and a rejection case.** The rejection case is one of: an unauthenticated request, or a logged-in user doing something outside their permission. It asserts the HTTP status (`401`, `403`, or `404` as the product defines) *or* a visible error message, never "the page looked wrong".
2. **Deterministic.** No `sleep` for luck; wait for a selector, a network response, or a health state. A test that passes only on retry is a failed test.
3. **Time-boxed.** Each test has `timeout=120s`; the whole suite has 30 minutes. Exceeding either is a failure.
4. **No external network.** Tests set `PLAYWRIGHT_OFFLINE=1` semantics by routing: any request whose host is not `127.0.0.1` is aborted and the test fails. This also catches containers that try to call the internet.
5. **Disposable data only.** Every run creates a fresh user, project, and files under a run id (`acc-<timestamp>-<6 hex>`), and deletes them in teardown. No real names, emails, or files of real people, ever ([POL-01](../policy/POL-01_Developer_Environment_2027_Position.md)).
6. **One assertion target per test.** A test checks one scenario and one case; helpers live in `installer/acceptance/conftest.py`.

### 4. Core scenarios (M2)

```toon
core_scenarios[6]{id,scenario,success_case,rejection_case,services}:
  C1,Login via fakecas,test user signs in and sees dashboard,"GET /dashboard without session -> 302 to login; API GET /v2/users/me/ -> 401","web api fakecas"
  C2,Create project,new project appears with title and user as admin,"second user (contributor read-only) PATCH /v2/nodes/<id>/ -> 403","web api"
  C3,Upload and download file,upload via waterbutler then download bytes equal,"anonymous GET of private file -> 401/403; non-contributor PUT -> 403","wb wb_worker osfstorage"
  C4,Wiki collaborative edit,two browser contexts type and both see merged text,"logged-out context connecting to wiki websocket -> closed with 4401","web y_websocket sharejs"
  C5,File preview,uploaded PDF renders in mfr iframe,"preview URL of private file without session -> 401/403","mfr unoconv"
  C6,Institution admin screen,institution admin lists institution users,"ordinary user opens admin URL -> 403 or redirect; API -> 403","admin api"
```

Scenario C4 uses two independent Playwright *browser contexts* (two separate browsers in one test, with their own cookies) so that the second user's cursor and text appear in the first user's page through the `y-websocket` service. `y_websocket` is part of the `core` profile ([SPEC-02 §4](02_installer_cli.md#2-en-ports)) because collaborative editing is an M2 scenario, so C4 runs and must pass in both `core` and `full`; it never skips.

### 5. Subsystem scenarios (M3)

```toon
subsystem_scenarios[5]{id,subsystem,success_case,rejection_case}:
  S1,y-websocket,two contexts converge on same Wiki document within 5 s,"connection without valid token -> close code 4401, no document state leaked"
  S2,rdmcp (MCP endpoint),"authenticated MCP client lists tools and reads one project resource","request without token -> 401; token of user B reading project of user A -> 403"
  S3,aipf_mcp_data_grdm,"MCP data query returns the run's project metadata","query for a project id the user cannot see -> 403 or empty with explicit code"
  S4,OASys,"OASys page loads and shows the run's project linked from GRDM","unauthenticated OASys API call -> 401"
  S5,Shibboleth-SP via test IdP,"SP -> IdP login -> GRDM dashboard with institution attribute","IdP user without the eduPersonEntitlement required by SP -> SP error page, no GRDM session"
```

**MCP** (Model Context Protocol) is a standard way for an AI assistant to ask a service for tools and data; `rdmcp` and `aipf_mcp_data_grdm` expose GRDM through it. Their tests use an HTTP client in the same `pytest` session, not a browser.

#### 5.1 Shibboleth scenario

With `compose render --profile full --auth shibboleth` ([SPEC-02 §4](02_installer_cli.md#2-en-ports)) `fakecas` is removed and a bundled test *IdP* (identity provider: the server that checks who you are, like a university login page) answers for the *SP* (service provider: the part of GRDM that trusts the IdP). Mock attributes used by the test IdP (names like `Test User 01`, `test01@idp.test`) live only in `installer/acceptance/fixtures/idp/` and are clearly labeled `MOCK`; they never resemble real institution attributes, as [POL-01](../policy/POL-01_Developer_Environment_2027_Position.md) requires for separating mock and real data.

```mermaid
sequenceDiagram
  participant T as pytest-playwright
  participant W as web (GRDM)
  participant SP as shibboleth_sp
  participant IdP as test_idp
  T->>W: GET http://127.0.0.1:5000/login?campaign=institution
  W-->>T: 302 to SP /Shibboleth.sso/Login
  T->>SP: GET /Shibboleth.sso/Login
  SP-->>T: 302 to IdP SSO URL (SAML AuthnRequest)
  T->>IdP: POST username and password (mock user)
  IdP-->>T: HTML form with SAML Response
  T->>SP: POST /Shibboleth.sso/SAML2/POST
  SP->>W: forward with attributes (eppn, mail, institution)
  W-->>T: 302 to /dashboard, session cookie set
  T->>T: assert dashboard visible, assert institution name shown
  Note over T,IdP: Rejection: the mock user lacking entitlement stops at the SP error page and no GRDM cookie is set
```

### 6. Fixtures and test data

- `conftest.py` provides: `run_id`, `base_urls` (from `runtime/.env`), `admin_user`, `user_a`, `user_b` (created through the API with random passwords, deleted in teardown), `tmp_pdf` and `tmp_txt` (generated bytes, 1 KiB and 1 MiB).
- Users are created with the `--yes` helper `grdm-dev accept --seed`, which calls the Django management command inside the `web` container. The admin user is created only for C6 and removed after.
- Fixtures never read the host's home directory or environment beyond `runtime/.env`.

### 7. Evidence

Each run writes, under `docs/demo/runs/<run_id>/`:

```toon
evidence:
  results.toon: one line per test with id, case, status, duration_ms, http_status
  results.json: same data, canonical, consumed by grdm-dev report
  junit.xml: for CI and the GitHub checks tab
  screenshots/: <test>_<case>.png, taken only on failure
  trace/: Playwright trace zip, only on failure, kept 14 days in CI
```

`grdm-dev report` ([SPEC-02 §3](02_installer_cli.md#english)) copies `results.toon` into the bundle. The demo document for the milestone (`docs/demo/20_core_install_mac_studio.md` and similar) links to the run folder; the TOON in the document must agree with `results.json` (`docs check`).

### 8. Pass criteria per milestone

| Milestone | Required green | Host | Note |
|---|---|---|---|
| M2 | C1–C6, every success and rejection case | Mac Studio arm64 (self-hosted runner) | amd64: `grdm-dev build --platform linux/amd64` succeeds on a GitHub runner; no acceptance |
| M3 | M2 plus S1–S5 | Mac Studio arm64 | Shibboleth profile run separately from fakecas profile |
| M4 | M3, unchanged after Python 3.13 migration | Mac Studio arm64 | Acceptance is the regression gate for the port |
| M5 | M4 plus [SPEC-03](03_security_gate.md) final gate | Mac Studio arm64 and Ubuntu 24.04 amd64 | Full acceptance on both architectures |

A milestone is not passed by the author of the change. The QAE role runs `grdm-dev accept` and records the run id in `docs/status/`; the owner approves ([SPEC-00](00_overview.md)).

The Mac Studio self-hosted runner is registered only with the private `-dev2027` repositories, never with this public repository ([REF-01](../reference/REF-01_Glossary.md)). The `acceptance-arm64` workflow therefore runs there, and the QAE brings the run folder into `docs/demo/runs/` here through a PR.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 範囲と道具

受入試験は、[SPEC-02](02_installer_cli.md) で導入した環境に対して本物のブラウザを動かし、研究者が使うのと同じ操作で確かめます。Python で書き、**Playwright**（ブラウザを開いてクリック・入力・読み取りを代わりにしてくれるライブラリ）を **pytest-playwright**（試験の実行器 *pytest* が各試験に準備済みのブラウザ画面を渡せるようにする追加部品）経由で使います。

- 置き場: `installer/acceptance/`。シナリオごとに一ファイル、名前は `test_<シナリオ>.py`。
- 実行器: `grdm-dev accept [--profile ...] [--only <シナリオ>] [--json]`。`install.sh` が作った同じ `.venv/` の中で `pytest` を動かし（[SPEC-02 §2.2](02_installer_cli.md#japanese)）、一件でも失敗すれば終了 60。
- ブラウザ: `grdm-dev accept` は `PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright/` に Chromium があるかを確かめ、なければ終了コード 2 で導入コマンド（`pip install -e "installer[accept]"` のあと同じ変数を付けて `playwright install chromium`）をそのまま表示する。ダウンロードは一度だけの準備であり、試験の実行には含めない。venv の外には何も入れない。
- 対象 URL: 常に `compose render` が公開した `http://127.0.0.1:<ポート>`（[ADR-02](../decisions/ADR-02_Network_Model.md)。既定値は [SPEC-02 §4](02_installer_cli.md#2-ja-ports) のポート表）。ポートは `runtime/.env`（`GRDM_PORT_<SERVICE>`）から読み、決め打ちしない。

### 2. 試験の段

| 段 | 場所 | 道具 | Docker が要るか | 示すこと |
|---|---|---|---|---|
| 単体 | `installer/tests/` | `unittest` | 不要 | `grdm_dev` の各モジュールと [SPEC-02 §6](02_installer_cli.md#japanese) の全終了コード |
| 統合 | `installer/acceptance/integration/` | `pytest` + `urllib` | 要る | `compose up` が健康に達し、API が HTTP で応え、ループバックにだけ結び付いている |
| 受入 | `installer/acceptance/` | `pytest-playwright` | 要る | 人がブラウザでコアの作業をでき、禁止された操作が拒まれる |

`grdm-dev accept` は統合を先に動かし、統合が落ちたら受入の前で止まります。半分しか起動していない環境へのブラウザ試験は、証跡ではなく雑音になるからです。

### 3. シナリオの規則

1. **すべてのシナリオに成功ケースと拒否ケースを置く。** 拒否ケースは、未認証の要求か、ログイン済みの利用者が権限の外の操作をするもの。HTTP ステータス（製品の定義どおり `401`・`403`・`404`）**か**、画面に見えるエラー文言を assert する。「画面が変だった」では確かめない。
2. **決定的に動く。** 運に頼る `sleep` を使わず、セレクタ、ネットワーク応答、健康状態を待つ。再試行で通る試験は失敗した試験と見なす。
3. **時間を区切る。** 各試験は `timeout=120s`、全体は 30 分。超えたら失敗。
4. **外部ネットワークに出ない。** 経路の制御で、ホストが `127.0.0.1` でない要求はすべて中断し、その試験を失敗にする。これでインターネットへ出ようとするコンテナも見つかる。
5. **使い捨てのデータだけ。** 毎回、実行 ID（`acc-<時刻>-<6 桁の16進>`）の下に新しい利用者・プロジェクト・ファイルを作り、後片付けで消す。実在の人の名前・メール・ファイルは決して使わない（[POL-01](../policy/POL-01_Developer_Environment_2027_Position.md)）。
6. **一試験一対象。** 一つの試験は一つのシナリオの一つのケースだけを確かめる。共通処理は `installer/acceptance/conftest.py` に置く。

### 4. コアのシナリオ（M2）

```toon
core_scenarios[6]{id,scenario,success_case,rejection_case,services}:
  C1,fakecas でログイン,試験利用者がログインしダッシュボードを見る,"セッションなしで GET /dashboard -> ログインへ 302。API GET /v2/users/me/ -> 401","web api fakecas"
  C2,プロジェクト作成,題名付きの新プロジェクトができ利用者が管理者になる,"二人目（読取のみの共同研究者）が PATCH /v2/nodes/<id>/ -> 403","web api"
  C3,ファイルの上下載,waterbutler で上げたファイルを下ろしバイト列が一致,"匿名で非公開ファイルを GET -> 401/403。共同研究者でない人が PUT -> 403","wb wb_worker osfstorage"
  C4,Wiki 共同編集,二つのブラウザ文脈で入力し双方に統合された文が見える,"ログアウトした文脈が wiki の websocket に接続 -> 4401 で切断","web y_websocket sharejs"
  C5,ファイルプレビュー,上げた PDF が mfr の iframe に描かれる,"セッションなしで非公開ファイルのプレビュー URL -> 401/403","mfr unoconv"
  C6,機関管理画面,機関管理者が機関の利用者一覧を見る,"一般利用者が管理 URL を開く -> 403 か転送。API -> 403","admin api"
```

シナリオ C4 は独立した二つの Playwright の「ブラウザ文脈」（一つの試験の中にある、cookie を別々に持つ二つのブラウザ）を使い、二人目の文字が `y-websocket` サービスを通して一人目の画面に現れることを確かめます。共同編集は M2 のシナリオなので `y_websocket` は `core` プロファイルに含まれ（[SPEC-02 §4](02_installer_cli.md#2-ja-ports)）、C4 は `core` でも `full` でも実行して合格が必須です。スキップはしません。

### 5. サブシステムのシナリオ（M3）

```toon
subsystem_scenarios[5]{id,subsystem,success_case,rejection_case}:
  S1,y-websocket,二つの文脈が 5 秒以内に同じ Wiki 文書に収束する,"正しいトークンのない接続 -> 終了コード 4401。文書の内容は漏れない"
  S2,rdmcp（MCP の口）,"認証済みの MCP クライアントがツール一覧を得て一つのプロジェクト資源を読む","トークンなし -> 401。利用者 B のトークンで利用者 A のプロジェクトを読む -> 403"
  S3,aipf_mcp_data_grdm,"MCP のデータ問い合わせが実行中のプロジェクトのメタデータを返す","見えないプロジェクト ID の問い合わせ -> 403、または明示のコード付きの空"
  S4,OASys,"OASys の画面が開き、GRDM からリンクした実行中のプロジェクトが見える","未認証の OASys API 呼び出し -> 401"
  S5,テスト IdP 経由の Shibboleth-SP,"SP -> IdP ログイン -> 機関属性付きで GRDM ダッシュボード","SP が要求する eduPersonEntitlement のない IdP 利用者 -> SP のエラー画面。GRDM のセッションは作られない"
```

**MCP**（Model Context Protocol）は、AI アシスタントがサービスに道具とデータを尋ねるための共通の決まりです。`rdmcp` と `aipf_mcp_data_grdm` は GRDM をこの決まりで公開します。これらの試験はブラウザでなく、同じ `pytest` セッション内の HTTP クライアントで行います。

#### 5.1 Shibboleth のシナリオ

`compose render --profile full --auth shibboleth`（[SPEC-02 §4](02_installer_cli.md#2-ja-ports)）では `fakecas` を外し、同梱したテスト用 *IdP*（アイデンティティプロバイダ。大学のログイン画面のように「あなたが誰か」を確かめるサーバ）が *SP*（サービスプロバイダ。IdP を信頼する GRDM 側の部品）に応えます。テスト IdP の模擬属性（`Test User 01`、`test01@idp.test` のような名前）は `installer/acceptance/fixtures/idp/` にだけ置き、`MOCK` と明記します。実在の機関の属性に似せてはならず、模擬と実データの分離は [POL-01](../policy/POL-01_Developer_Environment_2027_Position.md) の要求どおりです。

```mermaid
sequenceDiagram
  participant T as pytest-playwright
  participant W as web（GRDM）
  participant SP as shibboleth_sp
  participant IdP as test_idp
  T->>W: GET http://127.0.0.1:5000/login?campaign=institution
  W-->>T: SP の /Shibboleth.sso/Login へ 302
  T->>SP: GET /Shibboleth.sso/Login
  SP-->>T: IdP の SSO URL へ 302（SAML AuthnRequest）
  T->>IdP: 利用者名とパスワードを POST（模擬利用者）
  IdP-->>T: SAML Response 入りの HTML フォーム
  T->>SP: POST /Shibboleth.sso/SAML2/POST
  SP->>W: 属性（eppn・mail・機関）を付けて転送
  W-->>T: /dashboard へ 302。セッション cookie を設定
  T->>T: ダッシュボードが見えること、機関名が表示されることを assert
  Note over T,IdP: 拒否: entitlement のない模擬利用者は SP のエラー画面で止まり、GRDM の cookie は作られない
```

### 6. フィクスチャと試験データ

- `conftest.py` が提供するもの: `run_id`、`base_urls`（`runtime/.env` から）、`admin_user`・`user_a`・`user_b`（API で乱数パスワード付きに作り、後片付けで消す）、`tmp_pdf`・`tmp_txt`（生成したバイト列。1 KiB と 1 MiB）。
- 利用者は `--yes` 付きの補助 `grdm-dev accept --seed` で作り、これは `web` コンテナ内の Django 管理コマンドを呼ぶ。管理者利用者は C6 のためだけに作り、終わったら消す。
- フィクスチャは `runtime/.env` 以外に、ホストのホームディレクトリや環境変数を読まない。

### 7. 証跡

毎回の実行は `docs/demo/runs/<run_id>/` の下に次を書きます。

```toon
evidence:
  results.toon: 試験ごとに一行。id・case・status・duration_ms・http_status
  results.json: 同じデータの正本。grdm-dev report が読む
  junit.xml: CI と GitHub の checks タブ向け
  screenshots/: <試験>_<ケース>.png。失敗時だけ撮る
  trace/: Playwright のトレース zip。失敗時だけ。CI では 14 日保持
```

`grdm-dev report`（[SPEC-02 §3](02_installer_cli.md#japanese)）が `results.toon` を束に写します。節目の実証文書（`docs/demo/20_core_install_mac_studio.md` およびその類）は実行フォルダへリンクし、文書内の TOON は `results.json` と一致していなければなりません（`docs check`）。

### 8. 節目ごとの合格基準

| 節目 | 全件合格が必要なもの | ホスト | 備考 |
|---|---|---|---|
| M2 | C1〜C6 の成功・拒否ケースすべて | Mac Studio arm64（セルフホストランナー） | amd64 は GitHub ランナーで `grdm-dev build --platform linux/amd64` が成功すること。受入は行わない |
| M3 | M2 に加え S1〜S5 | Mac Studio arm64 | Shibboleth プロファイルは fakecas プロファイルと別に実行 |
| M4 | M3 が Python 3.13 移植後も変わらず合格 | Mac Studio arm64 | 受入が移植の回帰判定の門になる |
| M5 | M4 に加え [SPEC-03](03_security_gate.md) の最終の門 | Mac Studio arm64 と Ubuntu 24.04 amd64 | 両アーキテクチャで全受入 |

節目の合格は変更の作者が判定しません。QAE（QA担当）の役割が `grdm-dev accept` を実行し、実行 ID を `docs/status/` に記録し、所有者が承認します（[SPEC-00](00_overview.md)）。

Mac Studio のセルフホストランナーは非公開の `-dev2027` リポジトリにだけ登録し、公開のこのリポジトリには登録しません（[REF-01](../reference/REF-01_Glossary.md)）。そのため `acceptance-arm64` ワークフローはそちらで動き、QAE が実行フォルダを PR でこのリポジトリの `docs/demo/runs/` へ持ち込みます。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Playwright | A library that opens a browser and clicks, types, and reads pages for you. | ブラウザを開き、クリック・入力・読み取りを代わりにしてくれるライブラリ。 |
| pytest | A Python tool that finds and runs test functions and reports which passed. | Python の試験関数を見つけて動かし、合否を報告する道具。 |
| Browser context | A separate browser session with its own cookies, inside one test. | 一つの試験の中にある、cookie を別々に持つ独立したブラウザのセッション。 |
| Fixture | Ready-made test data or setup that a test receives before it starts. | 試験が始まる前に受け取る、用意済みのデータや準備。 |
| IdP / SP | The server that checks who you are / the service that trusts that answer. | 「あなたが誰か」を確かめるサーバ／その答えを信頼するサービス。 |
| SAML | The message format an IdP and an SP use to pass a login result. | IdP と SP がログイン結果を渡し合うための文書の形式。 |
| MCP | A standard way for an AI assistant to ask a service for tools and data. | AI アシスタントがサービスに道具とデータを尋ねるための共通の決まり。 |
| JUnit XML | A common file format that CI systems read to show test results. | CI が試験結果を表示するために読む、よく使われるファイル形式。 |
