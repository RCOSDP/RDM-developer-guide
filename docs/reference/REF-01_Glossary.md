# REF-01 Glossary / 用語集

> **Summary:** The shared glossary that [SPEC-06 §3](../spec/06_documentation_conventions.md) refers to. Every technical term used in this project, with a one-line explanation a primary-school child could follow, the precise meaning for engineers, and where the term is used.
> **概要:** [SPEC-06 §3](../spec/06_documentation_conventions.md) が指す共通用語集。このプロジェクトで使う専門用語を、小学生にも分かる一行、技術者向けの正確な意味、使われる場所の三つで説明する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-10. **Learned:** a glossary row that names a version goes stale with the first upgrade, so the PostgreSQL row now names the record that set the version (ADR-12). ／ 版を書いた用語の行は最初の更新で古くなるので、PostgreSQL の行は版を決めた記録（ADR-12）を示す。
  0.1 — 2026-11-05. **Learned:** listing every term in one place showed that about a third of them (CAS, SAML, IdP/SP, Shibboleth, GakuNin) belong to one topic — login — and that newcomers stumble there first, so the login terms were written to read as one connected story. ／ 全部の語を一か所に並べてみると、約三分の一（CAS、SAML、IdP/SP、Shibboleth、GakuNin）が「ログイン」という一つの話題に属し、新入社員はまずそこでつまずくと分かった。そこでログインの語は一つの続いた話として読めるように書いた。
- Applies to: every document in this repository. Documents still add a short note on first use and link here ([SPEC-06 §3](../spec/06_documentation_conventions.md)). `grdm-dev docs check` uses the **Term** column of the English table as its word list.
- Related: [docs/README.md](../README.md) · [SPEC-00 Overview](../spec/00_overview.md) · [SPEC-01 Manifest](../spec/01_manifest.md) · [SPEC-02 Installer CLI](../spec/02_installer_cli.md) · [SPEC-03 Security Gate](../spec/03_security_gate.md) · [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md) · [SPEC-05 Upstream Tracking](../spec/05_upstream_tracking.md) · [POL-01](../policy/POL-01_Developer_Environment_2027_Position.md) · [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) · [ADR-02](../decisions/ADR-02_Network_Model.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### How to read the table

- **For everyone** is the one-line note that documents copy on first use.
- **For engineers** is the precise meaning. When the two differ in emphasis, the engineer column wins for implementation.
- **Where used** names the documents or commands where the term matters most. Links are relative; private `-dev2027` repositories are named, never linked.
- Terms are grouped by topic, then alphabetical inside the group. Add a term in both halves in the same commit.

### A. Git and GitHub

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| Repository | A folder that remembers every change, so you can always go back. | A Git object store plus working tree, hosted on GitHub under the RCOSDP organization. | everywhere |
| Branch | A separate line of work in a repository, like a side road that can rejoin the main road. | A movable pointer to a commit; `develop` is the integration branch, `upstream/*` are tracking branches. | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md), [SPEC-05](../spec/05_upstream_tracking.md) |
| Commit | One saved step of changes with a message saying why. | A snapshot of the tree with parent pointers, author, and message; subjects are Japanese here. | [SPEC-06 §6](../spec/06_documentation_conventions.md) |
| SHA | The fingerprint of one commit; no two are alike. | The SHA-1 (40 hex chars) identifying a commit; the manifest pins full SHAs. | [SPEC-01](../spec/01_manifest.md) |
| Fork | Your own copy of someone's repository that remembers where it came from. | A GitHub-side copy with an upstream link; impossible inside the same organization. | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) |
| Upstream | The original place a copy came from; changes flow down from it. | The source repository or branch we mirror and merge from; tracking branches are named `upstream/<kind>-<branch>` (for example `upstream/public-develop`, `upstream/private-master`, `upstream/cos-develop`). | [SPEC-01 §4](../spec/01_manifest.md), [SPEC-05](../spec/05_upstream_tracking.md) |
| Mirror | An identical copy that is refreshed automatically. | A branch kept equal to an upstream ref by a daily fetch and fast-forward; never edited directly. | [SPEC-05](../spec/05_upstream_tracking.md) |
| Pull request (PR) | A proposed change waiting for someone to review and accept it. | A GitHub review unit; every change to `develop` goes through one; reviewed by REV, checked by QAE, merged by the owner. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Merge | Accepting a change into the shared branch. | Creating a merge commit on the target branch; here only a human merges; no force-push. | [POL-01 §2](../policy/POL-01_Developer_Environment_2027_Position.md) |
| Manifest | The list of which repositories, at which SHA, we build from. | `manifest/upstreams.json` (canonical) with a TOON excerpt; names, branches, SHAs, dates, PR numbers only. | [SPEC-01](../spec/01_manifest.md) |
| GitHub Actions | GitHub's robot that runs checks whenever code changes. | GitHub's CI service; workflows under `.github/workflows/` run link checks, secret scans, MkDocs, Semgrep, amd64 builds, Trivy. | [SPEC-03](../spec/03_security_gate.md) |
| Self-hosted runner | Our own computer that GitHub's robot borrows to run checks. | A GitHub Actions runner on the Mac Studio for arm64 builds and Playwright acceptance; private repositories only. | [SPEC-04](../spec/04_acceptance_tests.md) |
| CI | Continuous integration: automatic checks on every change. | The set of required workflows that must pass before a PR can be merged. | [SPEC-03](../spec/03_security_gate.md) |

### B. Containers and platforms

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| Container | A box that holds one program and everything it needs, so it runs the same anywhere. | An isolated process group sharing the host kernel, created from an image; runs non-root here. | [SPEC-02](../spec/02_installer_cli.md) |
| Image | The recipe and ingredients a container is made from. | A layered, read-only filesystem built from a Dockerfile; built locally by default, optionally pushed to a private registry. | [SPEC-02](../spec/02_installer_cli.md) |
| Docker | The tool that builds images and runs containers. | Docker Engine 27 or newer (29.x on the Mac Studio) with the Compose and buildx plugins; the only container runtime supported by the installer. | [SPEC-02](../spec/02_installer_cli.md) |
| Docker Compose | A tool that starts many containers together from one file. | The `docker compose` plugin (v2 or newer; 5.x on the Mac Studio) reading the generated `runtime/docker-compose.yml`; provides the internal network and DNS. | [ADR-02](../decisions/ADR-02_Network_Model.md) |
| buildx | Docker's helper that builds one image for several kinds of computer at once. | The BuildKit-based builder; `--platform linux/amd64,linux/arm64` produces multi-architecture images. | [SPEC-02](../spec/02_installer_cli.md) |
| Multi-architecture (arm64 / amd64) | Making the same program run on both kinds of computer chip. | Building images for `linux/arm64` (Apple Silicon, ARM servers) and `linux/amd64` (Intel/AMD); the installer selects `platform` automatically. | [SPEC-02](../spec/02_installer_cli.md) |
| Apple Silicon | The chips Apple puts in its Macs since 2020. | arm64 CPUs (M-series); the primary development target on the Mac Studio. | [SPEC-00](../spec/00_overview.md) |
| WSL2 | A way to run Linux inside Windows. | Windows Subsystem for Linux 2; Docker Desktop with the WSL2 backend is the supported Windows 11 path. | [SPEC-02](../spec/02_installer_cli.md) |
| Loopback / localhost | The network path that leads back to your own computer. | The `lo` interface; `127.0.0.1` (IPv4) and `::1` (IPv6); the only publishing address allowed. | [ADR-02](../decisions/ADR-02_Network_Model.md) |
| Port | A numbered door on an address through which one program listens. | A TCP/UDP port; default host ports (`5000` web, `8000` api, `8001` admin, `7777` wb, `7778` mfr, `8080` fakecas, `4200` ember) are defined in the ports table of SPEC-02 §4. | [SPEC-02 §4](../spec/02_installer_cli.md#2-en-ports), [ADR-02](../decisions/ADR-02_Network_Model.md) |
| Non-root | Running as an ordinary user, not as the all-powerful administrator. | Containers run with a non-zero UID; no `sudo` anywhere in the installer. | [SPEC-03](../spec/03_security_gate.md) |
| venv | A private box of Python tools for one project so projects do not fight. | A Python virtual environment; the installer, `grdm-dev`, and Playwright tests share one venv. | [SPEC-02](../spec/02_installer_cli.md) |
| EOL | End of life: the makers no longer fix bugs or security holes. | A version past its vendor support date; all current upstream base images are EOL and are replaced in M4–M5. | [POL-01 §1](../policy/POL-01_Developer_Environment_2027_Position.md) |

### C. Security

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| Vulnerability | A weak spot an attacker could use to get in. | A security defect, typically tracked as a CVE with a severity rating. | [SPEC-03](../spec/03_security_gate.md) |
| CVE | A public ID number given to one known security hole. | Common Vulnerabilities and Exposures identifier (`CVE-YYYY-NNNNN`) with CVSS severity; gate thresholds are CRITICAL/HIGH. | [SPEC-03](../spec/03_security_gate.md), [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| SBOM | A full list of every ingredient inside our software. | Software Bill of Materials (CycloneDX or SPDX) produced per image by Trivy. | [SPEC-03](../spec/03_security_gate.md) |
| Secret | A password or key that must never be written where others can read it. | Credentials and tokens; generated as random values at install time, never committed; secret scanning is mandatory in CI. | [SPEC-03](../spec/03_security_gate.md) |
| Allow-list | A short list of known problems we have looked at and accept for now. | Accepted CVEs with reason, owner, and expiry in `manifest/allowlist.json`; the count must shrink at each milestone. | [SPEC-03 §5](../spec/03_security_gate.md), [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| Security gate | A checkpoint the build must pass before anyone may use it. | The staged policy: report-only (M1–M3), stop on HIGH (M4), zero CRITICAL/HIGH plus red-team pass (M5). | [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| Trivy | A scanner that reads our images and lists the holes it knows about. | Aqua Security's scanner for images and filesystems; produces SBOM and CVE reports; Grype is the alternative. | [SPEC-03](../spec/03_security_gate.md) |
| Semgrep | A tool that reads source code looking for dangerous patterns. | Static analysis (SAST) with rule packs; runs in CI on every PR; CodeQL is the alternative. | [SPEC-03](../spec/03_security_gate.md) |
| OWASP ZAP | A tool that pokes at a running website the way an attacker would. | Dynamic application security testing (DAST) proxy from OWASP; run against the local instance only. | [SPEC-03](../spec/03_security_gate.md) |
| Red team | People or programs that attack our own system on purpose to find holes first. | Approved AI red team working only against our own instance inside an isolated network; approval procedure in SPEC-03. | [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |

### D. Testing and quality

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| Unit test | A check that one small piece works on its own. | A test of a single function or class in isolation; Python `unittest`/pytest. | [SPEC-04](../spec/04_acceptance_tests.md) |
| Integration test | A check that several pieces work together. | A test across service boundaries (for example web calls wb through the Compose network). | [SPEC-04](../spec/04_acceptance_tests.md) |
| Acceptance test | A check that the whole thing does what the user asked for. | End-to-end scenarios through the browser: login, project creation, file up/download, wiki co-edit, preview, institution admin; each with a success and a rejection case. | [SPEC-04](../spec/04_acceptance_tests.md) |
| Regression test | A check that something that used to work still works. | Re-running earlier acceptance and unit suites after each change; required before merge. | [SPEC-04](../spec/04_acceptance_tests.md) |
| Playwright | A robot that drives a web browser to test a website. | Playwright for Python running in the shared venv against Chromium on `127.0.0.1`. | [SPEC-04](../spec/04_acceptance_tests.md) |

### E. Documents and data formats

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| MkDocs | A tool that turns Markdown files into a website. | MkDocs with the Material theme; `grdm-dev docs` builds `site/`; published on GitHub Pages. | [SPEC-06 §5](../spec/06_documentation_conventions.md) |
| Mermaid | A way to draw diagrams by typing text. | Fenced ```` ```mermaid ```` blocks rendered by GitHub and MkDocs; the only allowed form for architecture and flow diagrams. | [SPEC-06 §4](../spec/06_documentation_conventions.md) |
| TOON | A compact text form of JSON data that people and AI read easily. | Token-Oriented Object Notation; used for data in documents; canonical data stays in JSON/YAML and `grdm-dev manifest check` verifies they agree. | [SPEC-06 §4](../spec/06_documentation_conventions.md) |
| JSON | A plain-text way to write data with braces and quotes that programs read easily. | JavaScript Object Notation; canonical format for the manifest and reports. | [SPEC-01](../spec/01_manifest.md) |
| YAML | A plain-text way to write data with indentation that people read easily. | Used for Compose files, MkDocs, and GitHub Actions workflows. | [SPEC-02](../spec/02_installer_cli.md) |

### F. Login and identity

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| CAS | A login service that many websites share: log in once, use them all. | Central Authentication Service protocol; GRDM's `cas-overlay` implements it and OSF web/api trust it. | [SPEC-04](../spec/04_acceptance_tests.md) |
| fakecas | A pretend CAS for developers: any name logs in, no password. | A tiny Go service standing in for cas-overlay in development; mutually exclusive with Shibboleth in acceptance. | [ADR-02](../decisions/ADR-02_Network_Model.md), [SPEC-04](../spec/04_acceptance_tests.md) |
| SAML | A standard way for one website to tell another "yes, this person has logged in". | Security Assertion Markup Language 2.0; XML assertions between IdP and SP. | [SPEC-04](../spec/04_acceptance_tests.md) |
| IdP / SP | IdP is the place where you log in; SP is the website that trusts it. | Identity Provider and Service Provider in SAML; a test IdP container is bundled for acceptance. | [SPEC-04](../spec/04_acceptance_tests.md) |
| Shibboleth | Software that makes SAML login work for universities. | The Shibboleth SP (Apache module) in `RDM-Shibboleth-SP`; the subsystem that connects GRDM to GakuNin. | [SPEC-00](../spec/00_overview.md) |
| GakuNin | Japan's academic network for logging in with your university account. | The Japanese academic access management federation operated by NII; GRDM accepts GakuNin IdPs through Shibboleth. | [SPEC-00](../spec/00_overview.md) |

### G. GRDM components and upstream

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| OSF / COS | OSF is the website for sharing research that GRDM is built on; COS is the group in the US that makes it. | Open Science Framework by the Center for Open Science; `CenterForOpenScience/*` is tracked as `upstream/cos-develop`. | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) |
| osf.io | The main part of GRDM: the website and its API. | Django application (`RDM-osf.io`); services `web`, `api`, `admin`, `worker`. | [SPEC-00](../spec/00_overview.md) |
| waterbutler (wb) | The part that moves files in and out of storage. | Python/aiohttp file-access service (`RDM-waterbutler`); services `wb`, `wb_worker`. | [SPEC-00](../spec/00_overview.md) |
| modular-file-renderer (mfr) | The part that shows a preview of a file in the browser. | Python/aiohttp rendering service (`RDM-modular-file-renderer`); service `mfr`. | [SPEC-00](../spec/00_overview.md) |
| ember-osf-web | The newer web pages of GRDM. | Ember.js front end (`RDM-ember-osf-web`); service `ember_osf_web`. | [SPEC-00](../spec/00_overview.md) |
| cas-overlay | GRDM's real login server. | Apereo CAS overlay (`RDM-cas-overlay`, JDK); service `cas`. | [SPEC-00](../spec/00_overview.md) |
| wiki-frontend | The wiki editor pages. | Front end for the GRDM wiki (`RDM-wiki-frontend`), paired with y-websocket for live co-editing. | [SPEC-00](../spec/00_overview.md) |
| y-websocket | The helper that lets two people edit the same wiki page at once. | Yjs WebSocket server (`RDM-y-webocket-develop-private`; repository name carries the upstream spelling) for collaborative editing. | [SPEC-00](../spec/00_overview.md) |
| OASys | A GRDM subsystem (private) added in M3. | Subsystem from `RDM-OASys-main-private`; scope and tests defined in M3. | [SPEC-00](../spec/00_overview.md) |
| rdmcp / MCP | A way for AI assistants to talk to GRDM through a standard plug. | Model Context Protocol server for GRDM (`RDM-rdmcp-private`). | [SPEC-00](../spec/00_overview.md) |
| AIPF | A GRDM data connector for the AI platform (private). | `RDM-aipf_mcp_data_grdm-private`, an MCP data source for GRDM. | [SPEC-00](../spec/00_overview.md) |
| Elasticsearch | The search engine inside GRDM. | ES 2 and 6.3.1 today; consolidated on ES 8 in M5. | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| PostgreSQL | The main database where GRDM keeps its records. | PostgreSQL 18 (ADR-12); it was 9.6 until 2026-11. | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| MongoDB | An older database GRDM still uses for a few things. | MongoDB 3.4 (sharejs); retired in M5. | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| RabbitMQ | The message queue: a line where jobs wait for a worker. | AMQP broker used by Celery workers in osf.io. | [SPEC-00](../spec/00_overview.md) |
| Redis | A very fast memory store used for caching and sessions. | In-memory key-value store used by osf.io and wb/mfr. | [SPEC-00](../spec/00_overview.md) |

### H. AI tools and roles

| Term | For everyone | For engineers | Where used |
|---|---|---|---|
| LLM / local LLM | A large language model is an AI that reads and writes text; a local one runs on our own computer. | A local LLM (Qwen 3 Coder Next via LM Studio) powers AID workers; nothing from private code is sent to external models without the data-handling rules in POL-05. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Orca | The desk where our AI workers sit: it opens workspaces and terminals for them. | The orchestration tool that runs Open Code 2 and Codex workers in separate worktrees. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Open Code 2 | The AI program that writes the code (our AID worker). | The implementation agent running on the local LLM inside Orca. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Codex | The AI program that reviews every PR (our REV). | Codex Astra (`gpt-6-astra`) as an Orca worker; records reviews in `docs/reviews/` and PR comments. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Claude Code | The AI program that writes specifications and checks results (our QAE). | Claude Code (Fable) running this plan's QA, regression and acceptance judgement. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| AID | AI Developer: the role that writes code and documents to spec. | Role code from the team table; held by Open Code 2 workers. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| QAE | QA Engineer: the role that checks and judges. | Role code; held by Claude Code Fable. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| REV | Reviewer: the role that independently reviews each PR. | Role code; held by Codex Astra. | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 表の読み方

- **みんな向け** は、文書が初出で写す一行の注です。
- **技術者向け** は正確な意味です。重点が違うときは、実装では技術者向けの列が優先します。
- **使われる場所** は、その語が最も効く文書やコマンドです。リンクは相対で、非公開の `-dev2027` は名前だけを書きリンクしません。
- 語は話題で分け、その中では英語の表と同じ順です。語を足すときは、英和の両方を同じコミットで足します。

### A. Git と GitHub

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| リポジトリ（repository） | 変更を全部覚えているフォルダ。いつでも前に戻せる。 | Git のオブジェクト保存庫と作業ツリー。RCOSDP 組織の GitHub に置く。 | 全文書 |
| ブランチ（branch） | リポジトリの中の別の作業の道。脇道で、あとで本道に戻れる。 | コミットを指す動くポインタ。`develop` が統合ブランチ、`upstream/*` が追跡ブランチ。 | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md)、[SPEC-05](../spec/05_upstream_tracking.md) |
| コミット（commit） | 変更の一歩を、理由のメッセージ付きで保存したもの。 | ツリーのスナップショットに親・作者・メッセージが付いたもの。件名は日本語。 | [SPEC-06 §6](../spec/06_documentation_conventions.md) |
| SHA | コミット一つの指紋。同じものは二つない。 | コミットを識別する SHA-1（16 進 40 文字）。manifest は完全な SHA を固定する。 | [SPEC-01](../spec/01_manifest.md) |
| フォーク（fork） | 他人のリポジトリの自分用の写し。出どころを覚えている。 | GitHub 側の写しで upstream へのリンクを持つ。同じ組織内には作れない。 | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) |
| 上流（upstream） | 写しの元の場所。変更はそこから流れてくる。 | ミラーしマージする元のリポジトリやブランチ。追跡ブランチの名前は `upstream/<kind>-<branch>`（例: `upstream/public-develop`、`upstream/private-master`、`upstream/cos-develop`）。 | [SPEC-01 §4](../spec/01_manifest.md)、[SPEC-05](../spec/05_upstream_tracking.md) |
| ミラー（mirror） | 自動で更新される、そっくり同じ写し。 | 日次の fetch と fast-forward で上流の参照と等しく保つブランチ。直接編集しない。 | [SPEC-05](../spec/05_upstream_tracking.md) |
| プルリクエスト（PR） | 誰かが見て受け入れるのを待っている、変更の提案。 | GitHub のレビュー単位。`develop` への変更はすべて PR を通り、REV がレビュー、QAE が検査、所有者がマージ。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| マージ（merge） | 変更を共有のブランチへ受け入れること。 | 対象ブランチにマージコミットを作ること。ここでは人だけがマージし、force push はしない。 | [POL-01 §2](../policy/POL-01_Developer_Environment_2027_Position.md) |
| manifest | どのリポジトリのどの SHA から組み立てるかの一覧。 | `manifest/upstreams.json`（正本）と TOON 抄録。名前・ブランチ・SHA・日付・PR 番号のみ。 | [SPEC-01](../spec/01_manifest.md) |
| GitHub Actions | コードが変わるたびに検査を走らせる GitHub のロボット。 | GitHub の CI。`.github/workflows/` のワークフローがリンク検査・秘密スキャン・MkDocs・Semgrep・amd64 ビルド・Trivy を走らせる。 | [SPEC-03](../spec/03_security_gate.md) |
| セルフホストランナー | GitHub のロボットが検査のために借りる、私たちの計算機。 | Mac Studio 上の GitHub Actions ランナー。arm64 ビルドと Playwright 受入に使い、非公開リポジトリ限定。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| CI | continuous integration。変更ごとに自動で走る検査。 | PR をマージする前に合格が必須のワークフローの集まり。 | [SPEC-03](../spec/03_security_gate.md) |

### B. コンテナと実行環境

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| コンテナ（container） | 一つのプログラムと必要なものを一箱に入れ、どこでも同じように動かす箱。 | ホストのカーネルを共有する隔離されたプロセス群。イメージから作り、ここでは非 root で動かす。 | [SPEC-02](../spec/02_installer_cli.md) |
| イメージ（image） | コンテナを作るためのレシピと材料。 | Dockerfile から作る層状の読み取り専用ファイルシステム。既定はローカルビルド、任意で非公開レジストリへ。 | [SPEC-02](../spec/02_installer_cli.md) |
| Docker | イメージを作り、コンテナを動かす道具。 | Docker Engine 27 以上（Mac Studio では 29.x）と Compose・buildx プラグイン。インストーラーが対応する唯一のコンテナ実行基盤。 | [SPEC-02](../spec/02_installer_cli.md) |
| Docker Compose | 一つのファイルから多くのコンテナをまとめて起こす道具。 | 生成した `runtime/docker-compose.yml` を読む `docker compose` プラグイン（v2 以上。Mac Studio では 5.x）。内部ネットワークと DNS を提供する。 | [ADR-02](../decisions/ADR-02_Network_Model.md) |
| buildx | 一つのイメージを何種類かの計算機向けに一度に作る Docker の助手。 | BuildKit ベースのビルダー。`--platform linux/amd64,linux/arm64` で複数アーキテクチャのイメージを作る。 | [SPEC-02](../spec/02_installer_cli.md) |
| マルチアーキテクチャ（arm64 / amd64） | 同じプログラムを、二種類のチップの計算機で動かすこと。 | `linux/arm64`（Apple Silicon、ARM サーバ）と `linux/amd64`（Intel/AMD）向けのイメージを作る。インストーラーが `platform` を自動判定する。 | [SPEC-02](../spec/02_installer_cli.md) |
| Apple Silicon | 2020 年から Apple が Mac に入れているチップ。 | arm64 の CPU（M シリーズ）。Mac Studio 上の主な開発対象。 | [SPEC-00](../spec/00_overview.md) |
| WSL2 | Windows の中で Linux を動かす仕組み。 | Windows Subsystem for Linux 2。WSL2 バックエンドの Docker Desktop が Windows 11 で対応する経路。 | [SPEC-02](../spec/02_installer_cli.md) |
| ループバック / localhost | 自分の計算機へ戻ってくるネットワークの道。 | `lo` インタフェース。`127.0.0.1`（IPv4）と `::1`（IPv6）。公開を許す唯一のアドレス。 | [ADR-02](../decisions/ADR-02_Network_Model.md) |
| ポート（port） | アドレスに付いた番号付きの扉。プログラムはここで待つ。 | TCP/UDP のポート。既定のホスト側ポート（`5000` web、`8000` api、`8001` admin、`7777` wb、`7778` mfr、`8080` fakecas、`4200` ember）は SPEC-02 §4 のポート表で定める。 | [SPEC-02 §4](../spec/02_installer_cli.md#2-ja-ports)、[ADR-02](../decisions/ADR-02_Network_Model.md) |
| 非 root（non-root） | なんでもできる管理者ではなく、普通の利用者として動かすこと。 | コンテナは 0 以外の UID で動く。インストーラーのどこにも `sudo` がない。 | [SPEC-03](../spec/03_security_gate.md) |
| venv | プロジェクトごとの Python 道具箱。プロジェクト同士がけんかしない。 | Python の仮想環境。インストーラー、`grdm-dev`、Playwright 試験が一つの venv を共有する。 | [SPEC-02](../spec/02_installer_cli.md) |
| EOL | end of life。作った人がバグや穴を直してくれなくなった状態。 | ベンダーのサポート期限を過ぎた版。現在の上流の土台イメージはすべて EOL で、M4〜M5 で置き換える。 | [POL-01 §1](../policy/POL-01_Developer_Environment_2027_Position.md) |

### C. セキュリティ

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| 脆弱性（vulnerability） | 攻撃者が入り込める弱い場所。 | セキュリティ上の欠陥。多くは CVE として深刻度付きで追跡される。 | [SPEC-03](../spec/03_security_gate.md) |
| CVE | 既知の穴一つに付けられた公開の番号。 | Common Vulnerabilities and Exposures の識別子（`CVE-YYYY-NNNNN`）と CVSS 深刻度。門の閾値は CRITICAL/HIGH。 | [SPEC-03](../spec/03_security_gate.md)、[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| SBOM | ソフトウェアの中身の材料をすべて書いた一覧。 | Software Bill of Materials（CycloneDX か SPDX）。Trivy がイメージごとに出す。 | [SPEC-03](../spec/03_security_gate.md) |
| 秘密（secret） | 他人が読める場所に書いてはいけないパスワードや鍵。 | 資格情報とトークン。導入時に乱数で生成し、コミットしない。CI の秘密スキャンは必須。 | [SPEC-03](../spec/03_security_gate.md) |
| 許容リスト（allow-list） | 見た上で今は受け入れる、既知の問題の短い一覧。 | 理由・担当・期限付きで受け入れた CVE を `manifest/allowlist.json` に置く。件数は節目ごとに減らす。 | [SPEC-03 §5](../spec/03_security_gate.md)、[ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| セキュリティ門（security gate） | 通らないと使えない検問所。 | 段階方式: 報告のみ（M1〜M3）、HIGH で停止（M4）、CRITICAL/HIGH ゼロとレッドチーム合格（M5）。 | [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |
| Trivy | イメージを読んで、知っている穴を並べるスキャナ。 | Aqua Security のイメージ・ファイルシステム用スキャナ。SBOM と CVE 報告を出す。代替は Grype。 | [SPEC-03](../spec/03_security_gate.md) |
| Semgrep | ソースコードを読んで危ない書き方を探す道具。 | ルールパック付きの静的解析（SAST）。全 PR の CI で走る。代替は CodeQL。 | [SPEC-03](../spec/03_security_gate.md) |
| OWASP ZAP | 動いている Web サイトを、攻撃者のやり方でつつく道具。 | OWASP の動的アプリケーションセキュリティ試験（DAST）プロキシ。ローカルインスタンスだけに向ける。 | [SPEC-03](../spec/03_security_gate.md) |
| レッドチーム（red team） | 穴を先に見つけるために、わざと自分のシステムを攻める人やプログラム。 | 承認済み AI レッドチーム。隔離ネットワーク内の自環境だけを対象にする。承認手順は SPEC-03。 | [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) |

### D. 試験と品質

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| 単体試験（unit test） | 小さな部品一つが単独で動くかの確認。 | 関数やクラス一つを切り離して試す。Python の `unittest`/pytest。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| 統合試験（integration test） | いくつかの部品が一緒に動くかの確認。 | サービスの境界をまたぐ試験（例: web が Compose ネットワーク経由で wb を呼ぶ）。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| 受入試験（acceptance test） | 全体が利用者の望みどおりに動くかの確認。 | ブラウザを通した端から端までのシナリオ: ログイン、プロジェクト作成、ファイル上下載、Wiki 共同編集、プレビュー、機関管理。各シナリオに成功と拒否のケース。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| 回帰試験（regression test） | 前に動いていたものが、今も動くかの確認。 | 変更ごとに以前の受入・単体の一式を再実行する。マージ前に必須。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| Playwright | Web ブラウザを操作して Web サイトを試すロボット。 | Playwright for Python。共有 venv で、`127.0.0.1` の Chromium に対して走る。 | [SPEC-04](../spec/04_acceptance_tests.md) |

### E. 文書とデータ形式

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| MkDocs | Markdown のファイルを Web サイトに変える道具。 | Material テーマの MkDocs。`grdm-dev docs` が `site/` を作り、GitHub Pages で公開。 | [SPEC-06 §5](../spec/06_documentation_conventions.md) |
| Mermaid | 文字を打って図を描く仕組み。 | ```` ```mermaid ```` のコードブロック。GitHub と MkDocs が描画する。構成図・流れ図はこれだけを許す。 | [SPEC-06 §4](../spec/06_documentation_conventions.md) |
| TOON | JSON のデータを短く字下げで書いた形。人にも AI にも読みやすい。 | Token-Oriented Object Notation。文書内のデータに使う。正本は JSON/YAML に置き、`grdm-dev manifest check` が一致を確かめる。 | [SPEC-06 §4](../spec/06_documentation_conventions.md) |
| JSON | 波括弧と引用符でデータを書く、プログラムが読みやすい文字の形。 | JavaScript Object Notation。manifest と報告書の正本の形式。 | [SPEC-01](../spec/01_manifest.md) |
| YAML | 字下げでデータを書く、人が読みやすい文字の形。 | Compose ファイル、MkDocs、GitHub Actions のワークフローに使う。 | [SPEC-02](../spec/02_installer_cli.md) |

### F. ログインと身元

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| CAS | たくさんの Web サイトが共有するログイン係。一度ログインすれば全部使える。 | Central Authentication Service プロトコル。GRDM の `cas-overlay` が実装し、OSF の web/api がそれを信頼する。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| fakecas | 開発者向けの「にせもの CAS」。どんな名前でもパスワードなしで入れる。 | 開発で cas-overlay の代わりに立つ小さな Go のサービス。受入では Shibboleth と排他。 | [ADR-02](../decisions/ADR-02_Network_Model.md)、[SPEC-04](../spec/04_acceptance_tests.md) |
| SAML | ある Web サイトが別のサイトに「この人は確かにログインした」と伝える標準の方法。 | Security Assertion Markup Language 2.0。IdP と SP の間の XML アサーション。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| IdP / SP | IdP はログインする場所、SP はそれを信じる Web サイト。 | SAML の Identity Provider と Service Provider。受入のためにテスト用 IdP コンテナを同梱する。 | [SPEC-04](../spec/04_acceptance_tests.md) |
| Shibboleth | 大学向けに SAML ログインを動かすソフト。 | `RDM-Shibboleth-SP` の Shibboleth SP（Apache モジュール）。GRDM を GakuNin につなぐサブシステム。 | [SPEC-00](../spec/00_overview.md) |
| GakuNin（学認） | 大学のアカウントでログインするための日本の学術ネットワーク。 | NII が運営する日本の学術アクセス管理フェデレーション。GRDM は Shibboleth 経由で GakuNin の IdP を受け入れる。 | [SPEC-00](../spec/00_overview.md) |

### G. GRDM の部品と上流

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| OSF / COS | OSF は GRDM の土台になった研究共有の Web サイト。COS はそれを作る米国の団体。 | Center for Open Science の Open Science Framework。`CenterForOpenScience/*` を `upstream/cos-develop` として追跡する。 | [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) |
| osf.io | GRDM の中心。Web サイトと API。 | Django アプリケーション（`RDM-osf.io`）。サービスは `web`、`api`、`admin`、`worker`。 | [SPEC-00](../spec/00_overview.md) |
| waterbutler（wb） | ファイルを保管場所へ出し入れする部品。 | Python/aiohttp のファイルアクセスサービス（`RDM-waterbutler`）。サービスは `wb`、`wb_worker`。 | [SPEC-00](../spec/00_overview.md) |
| modular-file-renderer（mfr） | ファイルのプレビューをブラウザに見せる部品。 | Python/aiohttp の描画サービス（`RDM-modular-file-renderer`）。サービスは `mfr`。 | [SPEC-00](../spec/00_overview.md) |
| ember-osf-web | GRDM の新しい方の Web 画面。 | Ember.js のフロントエンド（`RDM-ember-osf-web`）。サービスは `ember_osf_web`。 | [SPEC-00](../spec/00_overview.md) |
| cas-overlay | GRDM の本物のログインサーバ。 | Apereo CAS のオーバーレイ（`RDM-cas-overlay`、JDK）。サービスは `cas`。 | [SPEC-00](../spec/00_overview.md) |
| wiki-frontend | Wiki の編集画面。 | GRDM Wiki のフロントエンド（`RDM-wiki-frontend`）。共同編集は y-websocket と組む。 | [SPEC-00](../spec/00_overview.md) |
| y-websocket | 二人が同じ Wiki ページを同時に編集できるようにする裏方。 | 共同編集のための Yjs WebSocket サーバ（`RDM-y-webocket-develop-private`。リポジトリ名は上流の綴りのまま）。 | [SPEC-00](../spec/00_overview.md) |
| OASys | M3 で加える GRDM のサブシステム（非公開）。 | `RDM-OASys-main-private` のサブシステム。範囲と試験は M3 で定める。 | [SPEC-00](../spec/00_overview.md) |
| rdmcp / MCP | AI アシスタントが標準の差し込み口で GRDM と話す仕組み。 | GRDM 向けの Model Context Protocol サーバ（`RDM-rdmcp-private`）。 | [SPEC-00](../spec/00_overview.md) |
| AIPF | AI 基盤向けの GRDM データ接続部品（非公開）。 | `RDM-aipf_mcp_data_grdm-private`。GRDM の MCP データソース。 | [SPEC-00](../spec/00_overview.md) |
| Elasticsearch | GRDM の中の検索エンジン。 | 現在は ES 2 と 6.3.1。M5 で ES 8 に集約。 | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| PostgreSQL | GRDM が記録を保存する主なデータベース。 | PostgreSQL 18（ADR-12）。2026-11 までは 9.6。 | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| MongoDB | GRDM が一部でまだ使っている古いデータベース。 | MongoDB 3.4（sharejs 用）。M5 で廃止。 | [POL-01 §4](../policy/POL-01_Developer_Environment_2027_Position.md) |
| RabbitMQ | メッセージの待ち行列。仕事が作業者を待つ列。 | osf.io の Celery ワーカーが使う AMQP ブローカー。 | [SPEC-00](../spec/00_overview.md) |
| Redis | キャッシュやセッションに使う、とても速いメモリの保管庫。 | osf.io と wb/mfr が使うインメモリのキー値ストア。 | [SPEC-00](../spec/00_overview.md) |

### H. AI の道具と役割

| 用語 | みんな向け | 技術者向け | 使われる場所 |
|---|---|---|---|
| LLM / ローカル LLM | 大規模言語モデルは文章を読み書きする AI。ローカル版は自分の計算機で動く。 | ローカル LLM（LM Studio 経由の Qwen 3 Coder Next）が AID ワーカーを動かす。非公開コード由来のものは、POL-05 のデータ取り扱い規則なしに外部モデルへ送らない。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Orca | AI ワーカーの作業机。作業場と端末を開いてあげる。 | Open Code 2 と Codex のワーカーを別々の worktree で動かすオーケストレーション道具。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Open Code 2 | コードを書く AI プログラム（私たちの AID ワーカー）。 | Orca の中でローカル LLM で動く実装エージェント。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Codex | 全 PR をレビューする AI プログラム（私たちの REV）。 | Orca ワーカーとしての Codex Astra（`gpt-6-astra`）。レビューを `docs/reviews/` と PR コメントに記録する。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| Claude Code | 仕様を書き、結果を検査する AI プログラム（私たちの QAE）。 | この計画の QA・回帰・受入の判定を担う Claude Code（Fable）。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| AID | AI開発担当者。仕様どおりにコードと文書を書く役割。 | チームの対応表の役割略称。Open Code 2 ワーカーが担う。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| QAE | QA担当。検査し判定する役割。 | 役割略称。Claude Code Fable が担う。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |
| REV | 担当レビュワ。各 PR を独立にレビューする役割。 | 役割略称。Codex Astra が担う。 | [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md) |

---

## Glossary / 用語

The tables above are the glossary. Documents that use a term from the **Term / 用語** column add a short note on first use and link to the matching section (for example `[REF-01 §C](../reference/REF-01_Glossary.md#english)`). ／ 上の表そのものが用語集です。**Term / 用語** 列の語を使う文書は、初出で短い注を付け、該当する節へリンクします。
