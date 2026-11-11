# Status Board / 進捗ボード

> **Summary:** The single source of truth for milestone progress: M1–M5 status, open items, upstream tracking reports. The rules that define this board as the authoritative progress record.
> **概要:** 節目進捗の唯一の正本：M1〜M5 の進捗、未解決項目、上流追従報告。このボードが権威ある進行状況記録であることを定める規則。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.15 — 2026-11-11. **Learned:** a row measured under the M1 report-only gate must not stay green once the condition it names changes: 58 allow-list entries against a baseline of 0 is an open M2 item until the owner decides the ceiling, whatever the scan exit code says ([PR #45 review r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-02). ／ M1 の報告のみの門の下で測った行は、行が名指す条件が変われば緑のままにしてはならない。上限 0 に対して許容リスト 58 項目は、検査の終了コードが何であれ、所有者が上限を決めるまで M2 の残件である（[PR #45 レビュー r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-02）。
  0.14 — 2026-11-11. **Learned:** passing C5 proves only the preview path of the classic page; the new ember UI builds its preview URL through API v2, a different osf.io route, so it gets its own open row until a scenario covers it. ／ C5 の合格が示すのは旧来のページのプレビュー経路だけである。新しい ember の画面は API v2 という osf.io の別の経路でプレビューの URL を作るので、それを試すシナリオができるまで専用の残件行を置く。
  0.13 — 2026-11-10. **Learned:** an owner decision changes a waiting row into a working row the same day, so the M5 rows now name the chosen paths, and a merged-looking row keeps its review state (PR #42 review r1). ／ 所有者の判断は待ちの行をその日のうちに作業中の行に変えるので、M5 の行は選ばれた道を書き、マージ済みに見える行もレビューの状態を保つ（PR #42 レビュー r1）。
  0.12 — 2026-11-10. **Learned:** M5 work started before M2 closed, so M5 gets its own open-items table now (rule 3): one part is done and measured (PostgreSQL 18), the other two wait for owner decisions (ADR-13). ／ M5 の作業は M2 が閉じる前に始まったので、M5 にも今から専用の残件表を置く（規則 3）。一つは完了して測定済み（PostgreSQL 18）、残る二つは所有者の判断待ち（ADR-13）。
  0.11 — 2026-11-10. **Learned:** an open row that a later all-green row depends on must be closed in the same change, or the board contradicts itself (PR #40 review r1 R1-03). ／ 後の全件合格の行が前提にしている未完了の行は、同じ変更で閉じなければボードが自己矛盾する（PR #40 レビュー r1 R1-03）。
  0.10 — 2026-11-10. **Learned:** a scenario that passes only on a stack built from the pinned commits is evidence; a pass on a stack still running older images is not, because Compose kept the tags recorded by the previous build. ／ 固定した版から組んだスタックで通った試験だけが証拠になる。古いイメージのままのスタックでの合格は証拠にならない。Compose は前回のビルドが記録したタグを使い続けたからである。
  0.9 — 2026-11-10. **Learned:** acceptance counts per scenario belong on the board, because a single pass count hides which link is broken. ／ 受入の件数はシナリオごとにボードへ書く。合格数だけでは、どの連携が壊れているか分からない。
  0.8 — 2026-11-06. **Learned:** a warm success and a cold-start success are two different rows: the cold start needed one more architecture decision (ADR-07) before it passed. ／ 温まった状態の成功とコールドスタートの成功は別の行である。コールドスタートは通るまでにもう一つ設計判断（ADR-07）を要した。
  0.7 — 2026-11-06. **Learned:** the M2 open-items table needs the build row and the start-up row kept separate, because build finished at run 6 while start-up took seven more runs. ／ M2 の残件表はビルドの行と起動の行を分けておく必要がある。ビルドは第 6 回で終わり、起動にはさらに 7 回かかった。
  0.6 — 2026-11-06. **Learned:** the M2 row still said "awaiting owner merge" nine PRs later; a board row must be updated in the same PR that changes what it describes, and a milestone in progress needs its own open-items table (§2b). ／ M2 の行は 9 本の PR を経ても「所有者マージ待ち」のままだった。ボードの行は、その記述の対象を変える PR と同じ PR で更新しなければならず、進行中の節目には専用の残件表（§2b）が要る。
  0.5 — 2026-11-06. **Learned:** an installer change that depends on a matching change in an integration repository must leave an open item here, or the dependency is only visible in an ADR (PR #30 review r1 R1-03: the wiki editor page must load the new bundle path). ／ 統合リポジトリ側の対応する変更に依存するインストーラーの変更は、ここに残件を残さなければ ADR の中にしか見えないと分かった（PR #30 レビュー r1 R1-03: Wiki エディタのページが新しい束のパスを読む必要がある）。
  0.4 — 2026-11-06. **Learned:** a board row must state what happened to a closed pull request (closed without merge, superseded) rather than "no PR", or the history reads wrong (review r1 of PR #22). ／ 閉じた PR は「PR なし」ではなく「マージせず閉鎖」「置き換え」と書かないと履歴が誤って読まれる（PR #22 レビュー r1）。
  0.3 — 2026-11-05. **Learned:** a milestone is marked done only when its PR is merged, so M1 flipped to done at the merge of PR #19 and not when the documents were written. ／ 節目は PR がマージされたときにだけ完了にする。M1 は文書を書いた時点ではなく PR #19 のマージで完了になった。
  0.2 — 2026-11-05. **Learned:** the board must say what a CI check covers at the current milestone (Trivy: file system, report-only), or a green run is read as full coverage. ／ ボードは CI の検査が今の節目で何を対象にしているか（Trivy はファイルシステムに対する報告のみ）を書かなければ、緑の結果が全範囲の合格と読まれてしまうと分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** without a single source of truth, it was unclear whether M1 completion meant "docs written" or "PR merged"; the board's explicit rules resolve ambiguity. ／ 単一の正本がなければ、M1 完了が「文書を書いた」か「PR をマージした」か分からず、ボードの明示的な規則で曖昧さを解消すると分かった。
- Normative for: [status/upstream/](upstream/README.md) and all milestone progress tracking.
- Related: [../README.md](../README.md) · [demo/](../demo/README.md) · [spec/00_overview.md#5-milestone-ladder](./../spec/00_overview.md#english)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Milestones

| Milestone | Goal | Security gate | Status |
|---|---|---|---|
| M1 | Docs skeleton, manifest, dev2027 repos exist; reviewed PRs merged to develop | Report + allow-list | ✅ **Done** (PR #19 merged 2026-11-05) |
| M2 | Core 6 install with one command on Mac Studio; Playwright acceptance passes; amd64 builds | Report + allow-list (fewer entries than M1) | **In progress**: one-command install of the core profile succeeded on the Mac Studio in real install run 18 (PR #33, [DEMO-20](../demo/20_core_install_mac_studio.md#english)): build, up, health --network, scan, report all exit 0; Playwright acceptance not passed yet (first run 0 of 12, see §2b) |
| M3 | 5 subsystems start; one success + one rejection case each | Report + allow-list (fewer entries than M2) | Planned |
| M4 | Waterbutler, mfr, osf.io on Python 3.13 | Stop on HIGH or above; first AI red-team run | Planned |
| M5 | ES2 and mongo removed; ES8 + postgres 15 or later; distributable abroad | Zero CRITICAL/HIGH; zero open AI red-team paths | **Groundwork** (§2c): PostgreSQL 18 with `db upgrade` proposed ([ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#english)); ES2 and mongo findings await owner decisions ([ADR-13](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#english)) |

### 2. Open items for M1

| Item | Status |
|---|---|
| docs skeleton (READMEs for all folders) | ✅ Written |
| manifest/upstreams.json | ✅ Created |
| dev2027 integration repos (11) | ✅ Created |
| dev2027 strict reconstruction PRs (7 merged 2026-11-06; RDM-wiki-frontend-dev2027 #1 was closed without merge because both tips were identical) | ✅ Merged; `integration_sha` pinned in the manifest |
| MkDocs site build (`site/`, strict build passes) | ✅ Built |
| Guides migration to `docs/guides/` (pointers kept at old paths) | ✅ Done |
| Codex Astra review of RDM-osf.io-dev2027 PR #1 (historical) | ✅ Superseded: #1 closed 2026-11-05 after the owner rejected the bootstrap interpretation; #2 (strict reconstruction) merged 2026-11-06 |
| M1 skeleton PR to `develop` (this repository, PR #19) | 🔄 Open; review r1 of 2026-11-05 asked for changes (R1–R8); corrections in progress, then owner merge |
| GitHub Actions (docs, security) | ✅ Running on PR #19 (docs, gitleaks, manifest pass) |
| Trivy in CI (`security.yml`) | ⏳ At M1 report-only over the repository file system, because no image exists yet ([SPEC-03 §4.1](../spec/03_security_gate.md#english)); image scanning starts with the first build (M2) |
| Semgrep findings in legacy guide sample code (6: raw HTML in templates ×4, exec ×1, path join ×1) | ⏳ Deferred to the guide rewrite (M2/M3); paths listed in `.semgrepignore` with reasons |

### 2b. Open items for M2

| Item | Status |
|---|---|
| Installer CLI and templates (SPEC-02), overlay support (ADR-06) | ✅ Merged (PR #21–#30) |
| Real install on Mac Studio reaches `build` for all six components | ✅ Run 6 (2026-11-06): three built locally, two prebuilt, one overlay |
| `up` → `health --network` → `scan` → `report` on Mac Studio | ✅ Run 18 (2026-11-06, PR #33): exit 0, ready at the loopback URL; runs 6–17 fixed one start-up fact each (DEMO-20) |
| Cold start (empty volumes, new `runtime/`) on Mac Studio | ✅ Run 21 (2026-11-06, PR #34, ADR-07): exit 0 in 31 minutes; run 19 had shown the emulated Elasticsearch 2 needing 38 minutes to start, replaced by a native image |
| edit.mako wiring in the integration repository — `RDM-osf.io-dev2027` `addons/wiki/templates/edit.mako` must load `/static/public/js/wiki/wiki-edit-page.js` (the bundle that `wiki_assets` copies into the volume `wiki_static`, [ADR-06 §4](../decisions/ADR-06_Wiki_Frontend_Overlay.md#english)) instead of `/static/js/pages/wiki-edit-page.js`; browser check of the editor and C4 once a real install reaches `up` | ✅ Done: `RDM-osf.io-dev2027` PR #4 merged on 2026-11-09 (`7acc9abf9e`); C4 passes 2 of 2 in run `acc-20261110T015520Z-ab4cc7` (PR #40 review r1 R1-03) |
| Playwright acceptance C1–C6 | ✅ **12 of 12 pass** on 2026-11-10 (run `acc-20261110T015520Z-ab4cc7`) with every merged security fix: HMAC unification, wiki WebSocket JWT (anonymous socket closed with 4401), MFR redirect credentials, admin assets served locally, Google Analytics removed ([DEMO-20](../demo/20_core_install_mac_studio.md#english)). Merges under the [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md#english) delegation with review records in `docs/reviews/`. After the Python 3.13 pins (PR #45), C5 broke and was fixed in MFR PR #7 (`9771b8cf`); 12 of 12 again in run `acc-20261111T132104Z-530071` |
| Trivy image scan and allow-list count (fewer than M1) | ⏳ Image scanning works, but the count condition is **not met**. History: run 18 (Trivy alone) measured 1835 CRITICAL / 8290 HIGH / 9763 MEDIUM / 3886 LOW over 22 targets. Run 21, with the native Elasticsearch 2, measured 1769 / 8030 / 9550 / 3676, and the allow-list then had 0 entries (M1: 0). Now: PR #45 adds **58 entries** for Debian 13 packages without a fixed version in the Python 3.13 WaterButler and MFR images. Since PR #45 review r1 (R1-01), each entry names its exact packages and stops matching once a fix exists. They cover 177 findings in `scan_20261111T132607Z` (open Trivy CRITICAL/HIGH 726 / 3,769), while `manifest/allowlist.baseline.json` still says 0. The scan passes only because `manifest/milestone.json` is still M1 (report-only). Under M2's count-not-growing rule, 58 > 0 fails, so M2 is not complete until the owner decides the ceiling at milestone exit (SPEC-03 §5.1 rule 5). The baseline is not raised in this PR |
| Preview from the new ember UI (API v2) cannot reach the internal WaterButler — separate from C5, which uses the classic file page | ⏳ Open, not covered by any scenario yet. Root cause, from code reading and not reproduced in a browser: `api/files/serializers.py` builds `links.render` as MFR `/render?url=<DOMAIN>/download/<guid>/?direct&mode=render`. That URL carries the browser-facing `DOMAIN` (`http://127.0.0.1:<port>`), which the MFR container cannot reach. Its route `/download/<guid>/` (`persistent_file_download`) also ignores `mode=render` and redirects to the browser-facing WaterButler URL. The fix belongs in `RDM-osf.io-dev2027`, for example by building that link from `INTERNAL_DOMAIN` and the `/<guid>/` route as the classic page does. It must not widen MFR's credential pair (`http://web:5000` → `http://wb:7777`, MFR PR #7) |
| Default branch switched to `develop` (owner) | ⏳ After M2 passes |


### 2c. Open items for M5

| Item | Status |
|---|---|
| PostgreSQL 9.6 → 18.6, `grdm-dev db status/upgrade/rollback`, `up` refuses a mismatched major (exit 15) | 🔄 PR #42 (review r1 changes addressed) ([ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#english)): osf.io DB tests equal on 9.6 and 18 (781 passed, same 13 failed or erred); a 9.6 cluster upgraded in 37 s with 531 objects equal; CAS and fakecas log in; rollback measured; after review r1 a journal and a lock make a crash at any step recoverable (SIGKILL and SIGTERM measured, ADR-12 §4.1). PR #42. Not run on amd64 or on a Linux host |
| SCRAM for PostgreSQL | ⏳ Owner: CAS needs a JDBC driver ≥ 42.2 in RDM-cas-overlay-dev2027 (42.1.4 fails with `authentication type 10`) |
| Elasticsearch 2 retirement | 🔄 Owner decision 2026-11-10: port osf.io search to Elasticsearch 8, keeping full-text search; in progress in the osf.io integration repository ([ADR-13 §4](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#english)) |
| MongoDB and sharejs retirement | 🔄 Owner decision 2026-11-10: the file-page editor moves from sharejs to y-websocket, then sharejs and mongo are retired by ADR-13 §3; in progress |
| Elasticsearch 6 → 8 (metrics) | ⏳ Not started |

### 3. Rules

This board is the **single source of truth** for milestone progress:

1. Every document that mentions a milestone must link to this board.
2. The "Status" column above is authoritative; status updates require a PR with evidence (demo run or acceptance pass).
3. "Open items" has one table per milestone that has started (§2 for M1, §2b for M2, §2c for M5); later milestones get their own tables when they start.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 節目

| 節目 | ゴール | セキュリティ門 | ステータス |
|---|---|---|---|
| M1 | docs の骨格・manifest・dev2027 リポジトリ群がある。レビュー済み PR が develop にマージ | 報告＋許容リスト | ✅ **完了**（PR #19 を 2026-11-05 にマージ） |
| M2 | コア 6 本が Mac Studio で一発導入。Playwright 受入合格。amd64 ビルド | 報告＋許容リスト（M1 より件数を減らす） | **進行中**: core プロファイルの一発導入が実機第 18 回で Mac Studio 上で成功（PR #33、[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）: build・up・health --network・scan・report がすべて終了 0。Playwright 受入は未合格（初回 12 中 0、§2b 参照） |
| M3 | サブシステム 5 本が起動。各 1 本の正常系＋拒否ケース | 報告＋許容リスト（M2 より件数を減らす） | 計画中 |
| M4 | waterbutler・mfr・osf.io を Python 3.13 へ | HIGH 以上で停止。AI レッドチーム初回 | 計画中 |
| M5 | ES2・mongo 廃止。ES8＋postgres 15 以降。海外配布可 | CRITICAL/HIGH ゼロ。AI レッドチームの未解決経路ゼロ | **下準備**（§2c）: `db upgrade` 付きの PostgreSQL 18 を提案（[ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#japanese)）。ES2 と mongo の事実は所有者の判断待ち（[ADR-13](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#japanese)） |

### 2. M1 の残件

| 項目 | ステータス |
|---|---|
| docs の骨格（全フォルダの README） | ✅ 作成済み |
| manifest/upstreams.json | ✅ 作成 |
| dev2027 統合リポジトリ（11） | ✅ 作成 |
| dev2027 の厳密再構築 PR（7 本を 2026-11-06 にマージ。RDM-wiki-frontend-dev2027 #1 は両先端が同一のためマージせず閉鎖） | ✅ マージ済み。manifest に `integration_sha` を固定 |
| MkDocs サイトのビルド（`site/`、strict ビルド合格） | ✅ 生成済み |
| ガイドの `docs/guides/` への移植（旧パスに誘導を残す） | ✅ 完了 |
| Codex Astra による RDM-osf.io-dev2027 PR #1 のレビュー（履歴） | ✅ 置き換え済み: 所有者が初回構築の解釈を退け #1 は 2026-11-05 に閉鎖、#2（厳密再構築）を 2026-11-06 にマージ |
| M1 骨格 PR（本リポジトリ、develop 向け、PR #19） | 🔄 作成済み。2026-11-05 のレビュー r1 が修正要求（R1〜R8）。修正中、その後に所有者マージ |
| GitHub Actions（docs, security） | ✅ PR #19 で稼働（docs・gitleaks・manifest 合格） |
| CI の Trivy（`security.yml`） | ⏳ M1 ではイメージがまだないため、リポジトリのファイルシステムに対する報告のみ（[SPEC-03 §4.1](../spec/03_security_gate.md#japanese)）。イメージの検査は最初のビルド（M2）から |
| 旧ガイドのサンプルコードに対する Semgrep 指摘（6 件: テンプレートの生 HTML ×4、exec ×1、path join ×1） | ⏳ ガイド書き直し（M2/M3）で対応。対象パスと理由は `.semgrepignore` に記載 |

### 2b. M2 の残件

| 項目 | ステータス |
|---|---|
| インストーラー CLI とテンプレート（SPEC-02）、オーバーレイ対応（ADR-06） | ✅ マージ済み（PR #21〜#30） |
| Mac Studio の実機導入で 6 部品すべてが `build` を通過 | ✅ 第 6 回（2026-11-06）: 3 本はローカルビルド、2 本は prebuilt、1 本はオーバーレイ |
| Mac Studio で `up` → `health --network` → `scan` → `report` | ✅ 第 18 回（2026-11-06、PR #33）: 終了コード 0、ループバックの URL で準備完了。第 6〜17 回は起動の事実を毎回 1 件ずつ修正（DEMO-20） |
| Mac Studio でのコールドスタート（空のボリューム、新しい `runtime/`） | ✅ 第 21 回（2026-11-06、PR #34、ADR-07）: 31 分で終了コード 0。第 19 回でエミュレーションの Elasticsearch 2 が起動に 38 分かかることが分かり、ネイティブイメージに置き換えた |
| 統合リポジトリ側の edit.mako 配線（M2 第 5 回で確認） — `RDM-osf.io-dev2027` の `addons/wiki/templates/edit.mako` が `/static/js/pages/wiki-edit-page.js` でなく `/static/public/js/wiki/wiki-edit-page.js`（`wiki_assets` がボリューム `wiki_static` へ写す束。[ADR-06 §4](../decisions/ADR-06_Wiki_Frontend_Overlay.md#japanese)）を読み込むこと。実機導入が `up` に達したらエディタと C4 をブラウザ確認 | ✅ 完了: `RDM-osf.io-dev2027` PR #4 を 2026-11-09 にマージ（`7acc9abf9e`）。実行 `acc-20261110T015520Z-ab4cc7` で C4 は 2 件中 2 件合格（PR #40 レビュー r1 R1-03） |
| Playwright 受入 C1〜C6 | ✅ 2026-11-10 に **12 件中 12 件合格**（実行 `acc-20261110T015520Z-ab4cc7`）。マージ済みのセキュリティ修正をすべて含む: HMAC の統一、wiki の WebSocket の JWT（匿名ソケットは 4401 で切断）、MFR の転送時の資格情報、管理画面の資産のローカル配信、Google Analytics の削除（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）。マージは [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md#japanese) の委任により、レビュー記録は `docs/reviews/`。Python 3.13 の固定版（PR #45）の後に C5 が壊れ、MFR PR #7（`9771b8cf`）で直した。実行 `acc-20261111T132104Z-530071` で再び 12 件中 12 件 |
| Trivy のイメージ検査と許容リスト件数（M1 より少なく） | ⏳ イメージの検査は動くが、件数の条件は**満たしていない**。履歴: 第 18 回（Trivy 単独）は 22 対象で CRITICAL 1835 / HIGH 8290 / MEDIUM 9763 / LOW 3886。ネイティブ Elasticsearch 2 の第 21 回は 1769 / 8030 / 9550 / 3676 で、許容リストはその時点で 0 件（M1: 0）だった。現在: PR #45 は、Python 3.13 の WaterButler と MFR のイメージで修正版の無い Debian 13 のパッケージについて **58 項目**を加える。PR #45 レビュー r1（R1-01）以降、各項目は正確なパッケージを名指しし、修正版が出れば当てはまらなくなる。これらは `scan_20261111T132607Z` で 177 件を許容する（未許容の Trivy の CRITICAL/HIGH は 726 / 3,769）。一方 `manifest/allowlist.baseline.json` は 0 のままである。検査が合格するのは `manifest/milestone.json` がまだ M1（報告のみ）だからにすぎない。M2 の「件数を増やさない」規則では 58 > 0 で失敗するので、節目の終了時に所有者が上限を決めるまで M2 は完了しない（SPEC-03 §5.1 規則 5）。この PR では上限を引き上げない |
| 新しい ember の画面（API v2）からのプレビューが内部の WaterButler に届かない（旧来のファイルのページを使う C5 とは別） | ⏳ 未解決で、どのシナリオもまだ試していない。原因はコードを読んで分かったもので、ブラウザでは再現していない。`api/files/serializers.py` は `links.render` を MFR の `/render?url=<DOMAIN>/download/<guid>/?direct&mode=render` として作る。この URL はブラウザ向けの `DOMAIN`（`http://127.0.0.1:<port>`）を含み、MFR のコンテナからは届かない。また経路 `/download/<guid>/`（`persistent_file_download`）は `mode=render` を見ず、ブラウザ向けの WaterButler の URL へ転送する。直す場所は `RDM-osf.io-dev2027` で、たとえば旧来のページと同じく `INTERNAL_DOMAIN` と `/<guid>/` の経路でリンクを作る。MFR の資格情報の組（`http://web:5000` → `http://wb:7777`、MFR PR #7）は広げない |
| 既定ブランチを `develop` へ切替（所有者） | ⏳ M2 合格後 |


### 2c. M5 の残件

| 項目 | ステータス |
|---|---|
| PostgreSQL 9.6 → 18.6、`grdm-dev db status/upgrade/rollback`、`up` は版の不一致を拒む（終了 15） | 🔄 PR #42（レビュー r1 の指摘に対応）（[ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#japanese)）: osf.io の DB 試験は 9.6 と 18 で同じ（781 合格、同じ 13 件が失敗かエラー）。9.6 のクラスタを 37 秒で更新し 531 件が一致。CAS と fakecas はログインできた。巻き戻しも測定。レビュー r1 の後、操作記録とロックでどの段階のクラッシュも復旧できる（SIGKILL と SIGTERM を測定、ADR-12 §4.1）。amd64 と Linux のホストでは未実行 |
| PostgreSQL の SCRAM | ⏳ 所有者: RDM-cas-overlay-dev2027 で CAS に 42.2 以降の JDBC ドライバーが要る（42.1.4 は `authentication type 10` で失敗） |
| Elasticsearch 2 の退役 | 🔄 2026-11-10 の所有者の判断: 全文検索を保ったまま osf.io の検索を Elasticsearch 8 へ移植する。osf.io の統合リポジトリで進行中（[ADR-13 §4](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#japanese)） |
| MongoDB と sharejs の退役 | 🔄 2026-11-10 の所有者の判断: ファイルページのエディタを sharejs から y-websocket へ移し、その後 ADR-13 §3 の手順で sharejs と mongo を退役させる。進行中 |
| Elasticsearch 6 → 8（メトリクス） | ⏳ 未着手 |

### 3. 規則

このボードは節目進行状況の**唯一の正本**です：

1. 節目を言及するすべての文書はこのボードへリンクしなければならない。
2. 上記の「ステータス」列が権威あるものである。ステータス更新には PR と証跡（実行結果または受入合格）が必要。
3. 「残件」は着手した節目ごとに表を持つ（M1 は §2、M2 は §2b、M5 は §2c）。後の節目は着手時に専用の表を追加する。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Milestone | A checkpoint with a pass/fail test. | 合否の試験がある関門。 |
| Security gate | A checkpoint the build must pass before it is called good. | ビルドを導入してよいかを決める試験。 |
| Open item | A task or PR that has not been completed. | 完了していないタスクまたは PR。 |
| Status board | The single source of truth for milestone progress. | 節目進行状況の唯一の正本。 |
| Evidence | Proof that a test or check passed. | 試験または検査が合格した証拠。 |
