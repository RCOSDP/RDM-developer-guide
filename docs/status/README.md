# Status Board / 進捗ボード

> **Summary:** The single source of truth for milestone progress: M1–M5 status, open items, upstream tracking reports. The rules that define this board as the authoritative progress record.
> **概要:** 節目進捗の唯一の正本：M1〜M5 の進捗、未解決項目、上流追従報告。このボードが権威ある進行状況記録であることを定める規則。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.22 — 2026-11-14. **Learned:** a row about publication is outdated by the publication itself, so the record of a publish is a small change of its own made right after it. ／ 公開についての行は、公開そのもので古くなる。だから公開の記録は、公開の直後の小さな独立の変更にする。
  0.21 — 2026-11-14. **Learned:** a board row that waits on an event goes stale the moment the event happens elsewhere: the PR #51 rows still said "merged after the re-verification" after the merge, so a row that names a pending event must be updated in the same change that records the event. ／ 出来事を待つ行は、その出来事がよそで起きた瞬間に古くなる。PR #51 の行はマージの後も「再検証の後にマージする」と書いていた。待っている出来事を名指す行は、その出来事を記録する変更の中で直す。
  0.20 — 2026-11-14. **Learned:** a blocker that is only a permission ends the day the permission arrives, so the rows that waited on it must move in the same change that uses it, not later. ／ 権限だけが障害だった項目は、権限が付いた日に終わる。だからそれを待っていた行は、後回しにせず、権限を使う変更の中で動かす。
  0.19 — 2026-11-14. **Learned:** an emulated VM can pass every stage of the final pins (14 of 14 with C4, a complete scan) and still not show the one thing the row asks for, an uninterrupted one-command install, so the row says both instead of turning green (DEMO-22 0.7). ／ エミュレーションの VM は最終の固定版のすべての段を通せても（C4 を含む 14 件中 14 件、完走した検査）、行が求める一つのこと、途切れない一つのコマンドでの導入は示せない。だから行は緑にせず、両方を書く（DEMO-22 0.7）。
  0.18 — 2026-11-13. **Learned:** a milestone can be closed by an owner decision without meeting every written criterion, and then the board has to list what was not met instead of turning the row green: M2 closed on 2026-11-13 (「一括で承認、M2 完了」) with 58 allow-list entries against a criterion of fewer than M1's 0, amd64 acceptance shown only on an emulated VM, and the `workflow`-scope CI still unpushed; the owner accepted 58 as the M2 exit count, so the M3 ceiling is 58, and the carried items moved to their own M3 table (§2d). ／ 節目は、書かれた条件をすべて満たさなくても所有者の判断で閉じられる。そのときボードは行を緑にするのでなく、満たさなかったことを列挙しなければならない。M2 は 2026-11-13 に閉じた（「一括で承認、M2 完了」）。許容リストは M1 の 0 より少なくという条件に対して 58 項目、amd64 の受入はエミュレーションの VM でしか示しておらず、`workflow` 権限の CI はまだ push していない。所有者は 58 を M2 の終了時の件数として受け入れたので M3 の上限は 58 になり、持ち越した項目は M3 専用の表（§2d）に移した。
  0.17 — 2026-11-13. **Learned:** a board row is only finished when it names the merge commit it was proven on: the osf.io pin moved from a local candidate to the merged develop tip `90b10661c8dc` (#8, #10, #11 merged), and the Mac stack was rebuilt on it with 14 of 14 acceptance and a complete scan; the rows that wait on the `workflow` token scope (R7-01, `images.yml`, per-OS workflows) say so instead of reading as done. ／ ボードの行は、確かめたマージコミットを名指して初めて完了になる。osf.io の固定版はローカルの候補からマージ後の develop 先端 `90b10661c8dc`（#8・#10・#11 マージ済み）に移り、Mac のスタックをそれで組み直して受入 14 件中 14 件と完走した検査を得た。`workflow` 権限を待つ行（R7-01、`images.yml`、per-OS のワークフロー）は、完了に見えないようそう書く。
  0.16 — **Learned:** an owner decision becomes a row of installer work only when each consumer of the old component is named: Elasticsearch 2 left when osf.io's client moved (PR #11), sharejs and mongo when its editor moved (PR #12), and what is not done (Elasticsearch 6, the admin Shibboleth `idp` mode, the pin to a real merge) is a row of its own, not a footnote. ／ 所有者の判断は、古い部品を使う側を一つずつ名指ししたとき初めて、インストーラーの作業の行になる。Elasticsearch 2 は osf.io のクライアントが移ったとき（PR #11）、sharejs と mongo は編集が移ったとき（PR #12）に消え、まだ済んでいないこと（Elasticsearch 6、管理者の Shibboleth の `idp` モード、実際のマージへの固定）は脚注でなく独立した行にする。
  0.15 — 2026-11-11. **Learned:** a row measured under the M1 report-only gate must not stay green once the condition it names changes: 58 allow-list entries against a baseline of 0 is an open M2 item until the owner decides the ceiling, whatever the scan exit code says ([PR #45 review r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-02). ／ M1 の報告のみの門の下で測った行は、行が名指す条件が変われば緑のままにしてはならない。上限 0 に対して許容リスト 58 項目は、検査の終了コードが何であれ、所有者が上限を決めるまで M2 の残件である（[PR #45 レビュー r1](../reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md) R1-02）。
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
| M2 | Core 6 install with one command on Mac Studio; Playwright acceptance passes; amd64 builds | Report + allow-list (fewer entries than M1) | ✅ **Done by owner decision of 2026-11-13** (「一括で承認、M2 完了」), with known limits, **not** by meeting every written criterion. Shown: on the Mac Studio, the one-command install succeeded in earlier real install runs on earlier pins; on the final merged pins the existing Mac environment was updated with separate commands, then acceptance passed 14 of 14 (run `acc-20261112T223428Z-fda84a`) and the scan completed (operator-recorded) ([DEMO-20](../demo/20_core_install_mac_studio.md#english)). On Ubuntu arm64 the final pins were installed with the one command into a new checkout (fifth attempt; the VM was not new) and acceptance passed 14 of 14 (run `acc-20261113T021549Z-92641d`, [DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#english)). **Not met or not shown:** (1) the allow-list holds 58 entries against the written criterion "fewer than M1" (M1: 0); the owner's decision accepts 58 as the M2 exit count in `manifest/allowlist.baseline.json`, it does not make the criterion met; (2) amd64: acceptance 11 of 12 recorded only on an emulated VM ([DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#english); C4 success failed at the suite's 30 s wait), `scan` exited 51 there (Trivy did not finish the ember-osf-web image), and osf.io and wiki-frontend were not built on amd64; `accept --wait-scale` and `scan --trivy-timeout` exist since PR #60 and a re-run on that VM is in progress, not yet recorded; (3) the CI that needs a token with the `workflow` scope (per-OS workflows, the `images.yml` smoke test, osf.io R7-01) is not pushed; the owner decided to grant that scope; (4) no authenticated ZAP scan: under mandatory sign-in `web` is skipped. Carried items: §2d |
| M3 | 5 subsystems start; one success + one rejection case each | Report + allow-list (fewer entries than M2) | **Current** since 2026-11-13: `manifest/milestone.json` says M3 (gate `count-not-growing`) and the allow-list ceiling is the M2 count, 58 (`manifest/allowlist.baseline.json`); the S1–S5 acceptance modules still carry an unconditional `skip(reason=M3)` ([DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#english)). Open items: §2d |
| M4 | Waterbutler, mfr, osf.io on Python 3.13 | Stop on HIGH or above; first AI red-team run | Planned |
| M5 | ES2 and mongo removed; ES8 + postgres 15 or later; distributable abroad | Zero CRITICAL/HIGH; zero open AI red-team paths | **Groundwork** (§2c): PostgreSQL 18 with `db upgrade` ([ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#english)); Elasticsearch 2, MongoDB and sharejs are gone from the installer and Elasticsearch 8 replaces ES 2 on the merged osf.io `develop` `90b10661c8dc`, 14 of 14 acceptance ([ADR-13 §6](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#english), [ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#english)); the integration branch awaits its pull request |

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
| Playwright acceptance C1–C7 | ✅ **14 of 14 pass** again on the merged final pins on 2026-11-12 (run `acc-20261112T223428Z-fda84a`, UTC; osf.io `90b10661c8dc` after #8, #10, #11 merged; scan exit 0, 6,264 open findings, [DEMO-20](../demo/20_core_install_mac_studio.md#english)). Before that, **14 of 14 pass** on 2026-11-12 (run `acc-20261111T230217Z-d8363c`, UTC) on the local osf.io candidate (develop `73ff43b3c2` + PR #8, #10, #11) with Elasticsearch 8, y-websocket only, mandatory sign-in and the admin second factor; C7 (file-page co-editing) is new ([DEMO-20](../demo/20_core_install_mac_studio.md#english)). Before that: **12 of 12 pass** on 2026-11-10 (run `acc-20261110T015520Z-ab4cc7`) with every merged security fix: HMAC unification, wiki WebSocket JWT (anonymous socket closed with 4401), MFR redirect credentials, admin assets served locally, Google Analytics removed ([DEMO-20](../demo/20_core_install_mac_studio.md#english)). Merges under the [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md#english) delegation with review records in `docs/reviews/`. After the Python 3.13 pins (PR #45), C5 broke and was fixed in MFR PR #7 (`9771b8cf`); 12 of 12 again in run `acc-20261111T132104Z-530071` |
| Trivy image scan and allow-list count (fewer than M1) | ⚠️ **Not met; M2 closed by the owner's decision of 2026-11-13** (「一括で承認、M2 完了」). Image scanning works, but the count condition is **not met**. History: run 18 (Trivy alone) measured 1835 CRITICAL / 8290 HIGH / 9763 MEDIUM / 3886 LOW over 22 targets. Run 21, with the native Elasticsearch 2, measured 1769 / 8030 / 9550 / 3676, and the allow-list then had 0 entries (M1: 0). Now: PR #45 adds **58 entries** for Debian 13 packages without a fixed version in the Python 3.13 WaterButler and MFR images. Since PR #45 review r1 (R1-01), each entry names its exact packages and stops matching once a fix exists. They cover 177 findings in `scan_20261111T132607Z` (open Trivy CRITICAL/HIGH 726 / 3,769), while `manifest/allowlist.baseline.json` said 0 and the scan passed only because `manifest/milestone.json` was M1 (report-only); under M2's count-not-growing rule 58 > 0 fails. At milestone exit (SPEC-03 §5.1 rule 5) the owner declared M2 complete without the criterion being met, and that decision is recorded as the M2 exit count: `counts` is `{M1: 0, M2: 58}` and `manifest/milestone.json` is M3, so the ceiling is 58 and a 59th entry exits 50 (unit test `test_m3_ceiling_is_the_m2_exit_count`). The review of the 58 entries (expiry 2026-12-31) is carried to §2d |
| Preview from the new ember UI (API v2) cannot reach the internal WaterButler — separate from C5, which uses the classic file page | ⏳ **Carried to M3** (§2d). History: the cause found by code reading (not reproduced in a browser) was that `api/files/serializers.py` built `links.render` as MFR `/render?url=<DOMAIN>/download/<guid>/?direct&mode=render`, a browser-facing URL the MFR container cannot reach, whose route also ignored `mode=render`. RDM-osf.io-dev2027 PR #14 (server side) and RDM-ember-osf-web-dev2027 PR #3 are both merged. Open: a check on the real ember screen after deployment; no acceptance scenario covers the ember preview yet, so success there is not shown. MFR's credential pair (`http://web:5000` → `http://wb:7777`, MFR PR #7) stays as it is |
| Default branch switched to `develop` (owner) | ⏳ **Carried to M3** (§2d): M2 is closed by owner decision, the switch itself is the owner's. PR #51 (`develop` → `master`) was merged on 2026-11-14 (merge commit `9ebb9e9`) by the owner's decision of 2026-11-13 |
| Ubuntu arm64, one command on the final pins | ✅ 2026-11-13: 14 of 14 including C7 (run `acc-20261113T021549Z-92641d`); `scan` and `report` exit 0 (operator-recorded, [DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#english)) |
| Ubuntu amd64 ("amd64 builds") | ⚠️ **Closed for M2 with known limits** by the owner's decision of 2026-11-13 (「既知の限界として記録」), on an emulated VM only ([DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#english)): prerequisites, `doctor`, nine images built natively, `up` and `health --network` healthy, core acceptance 11 of 12 (C4 success failed at the 30 s wait; it passed once with longer waits in an uncommitted patched copy), `scan` exit 51 (Trivy incomplete on the ember-osf-web image; the cas-overlay SBOM failure unexplained), `report` exit 0. osf.io and wiki-frontend were not built on amd64. (These are the results of 2026-11-12.) **Re-run of 2026-11-13/14 on the final pins** (DEMO-22 0.7, PR #62): with a new checkout on the same VM (not new: images, build cache and prerequisites from the day before), the one command did not reach exit 0 in one go (four attempts: a missing mirror rewrite, the volume guard after a 10 h 45 min build, an Elasticsearch 8 health window too short under emulation — fixed in PR #62 — and a ZAP rc 3 on admin that did not recur). After that, `health --network` 0, `accept --seed --wait-scale 10` **14 of 14** including C4 and C7 (run `acc-20261113T192132Z-1cf20d`, committed), `scan --trivy-timeout 45m` 0 and `report` 0 (operator-recorded). osf.io and wiki-frontend were built on amd64 this time. **Uninterrupted run of 2026-11-14** (DEMO-22 0.8, develop f005512): on the same VM with a warm Docker cache, `install-ubuntu.sh --yes --profile core` returned **0 in one run** (3 h 34 min, every step ok, scan gate pass), and the acceptance run afterwards passed **14 of 14** with `--wait-scale 10` (`acc-20261114T035503Z-461116`, committed). Not shown: a run from an empty Docker, real hardware. Real hardware: §2d |
| CI that needs a token with the `workflow` scope (per-OS workflows of ADR-08 §9, the `images.yml` smoke test) | 🔄 **Carried to M3** (§2d): the scope was granted on 2026-11-14 and the workflows are pushed in PR #65 |
| Authenticated ZAP scan | ⏳ **Not done in M2** (known limit): under mandatory sign-in ZAP records `web` as skipped and scans `admin` and `ember_osf_web` ([DEMO-20](../demo/20_core_install_mac_studio.md#english) 0.22). Carried to §2d |


### 2c. Open items for M5

| Item | Status |
|---|---|
| PostgreSQL 9.6 → 18.6, `grdm-dev db status/upgrade/rollback`, `up` refuses a mismatched major (exit 15) | 🔄 PR #42 (review r1 changes addressed) ([ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#english)): osf.io DB tests equal on 9.6 and 18 (781 passed, same 13 failed or erred); a 9.6 cluster upgraded in 37 s with 531 objects equal; CAS and fakecas log in; rollback measured; after review r1 a journal and a lock make a crash at any step recoverable (SIGKILL and SIGTERM measured, ADR-12 §4.1). PR #42. Not run on amd64 or on a Linux host |
| SCRAM for PostgreSQL | ⏳ Owner: CAS needs a JDBC driver ≥ 42.2 in RDM-cas-overlay-dev2027 (42.1.4 fails with `authentication type 10`) |
| Elasticsearch 2 retirement | 🔄 Installer side done on branch `feat/installer-osf-integration` ([ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#english)): `elasticsearch8` (TLS, authentication, `grdm_osf` limited to `website*`, no published port, read-only root) replaces `elasticsearch`; checked with search, the permission filter and `invoke migrate_search` on RDM-osf.io-dev2027 `develop` `90b10661c8dc` (#8, #10, #11 merged, pinned in the manifest); the branch awaits its pull request |
| MongoDB and sharejs retirement | ✅ RDM-osf.io-dev2027 PR #12 merged (file-page editor on y-websocket); sharejs, mongo, their volumes, port 7007 and `SHAREJS_SECRET` are removed from the installer, y-websocket keeps file-room drafts in `y_websocket_data`, and scenario C7 proves the editor without them ([ADR-13 §6](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#english)). The installer change is on a local branch and is not pushed until the osf.io pin is a merge commit |
| Elasticsearch 6 → 8 (metrics) | ⏳ Not started; `elasticsearch6` stays for django-elasticsearch-metrics (ADR-14) |
| Mandatory sign-in and admin two-step sign-in (RDM-osf.io-dev2027 PR #8, #10) | 🔄 Installer side done (`compose render --public-access`, default `false`; migrations 0006/0007 by `osf_init`; the seeded administrator is TOTP-enrolled for C6) and proven on the merged `develop` `90b10661c8dc` (#8 without its R7-01 CI job, tracked as RDM-osf.io-dev2027 issue #16 and waiting for the `workflow` token scope): C1–C7 pass signed in, an unenrolled administrator lands on the enrolment page, anonymous search answers 401. Admin Shibboleth `idp` mode is not enabled (it needs the web server to set an environment variable, which the proxy chain cannot do) |

### 2d. Open items for M3

M3 started on 2026-11-13, when the owner closed M2 (「一括で承認、M2 完了」). The items carried from M2 are recorded here with the owner's decision of the same day (「既知の限界として記録」).

| Item | Status |
|---|---|
| Real amd64 hardware: one uninterrupted one-command install, acceptance with the committed suite, a complete `scan` | ⏳ Open (owner decision 2026-11-13: recorded as a known limit, M3 or later). So far only an emulated VM ([DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#english)); on that VM the final pins later passed 14 of 14 with `--wait-scale 10` and a complete `scan`, but not in one uninterrupted command (DEMO-22 0.7); on 2026-11-14 the one command returned 0 in a single run there too (DEMO-22 0.8, warm Docker cache). Still open: the same on real hardware, from an empty Docker |
| WSL2 (Windows 11) | ⏳ Open (same decision). Not run; it needs a Windows 11 machine ([DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#english), [ADR-08 §5](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md#english)) |
| Reporting the search information-leak vulnerabilities upstream | ⏳ **Undecided** (owner decision 2026-11-13). A draft report will be prepared and the owner asked again before anything is sent. Nothing has been sent, and no draft is in this repository |
| CI that needs a token with the `workflow` scope: `installer-prereq-lint.yml`, `installer-full.yml` and their helper on branch `feat/per-os-installers` ([ADR-08 §9](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md#english)), and the `images.yml` smoke test | 🔄 Pushed in PR #65 (scope granted 2026-11-14); the `images.yml` smoke test now starts the Elasticsearch 8 image instead of the removed Elasticsearch 2 recipe. `installer-full.yml` still has to be started by hand once, with the repository secret `GRDM_INTEGRATION_READ_TOKEN` |
| osf.io R7-01: the private-search security CI job (RDM-osf.io-dev2027 issue #16) | ⏳ Open: PR #8 was merged with R7-01 deferred by the owner to issue #16 (review r8 in [docs/reviews/](../reviews/README.md)); with the scope granted, RDM-osf.io-dev2027 PR #22 (opened 2026-11-14) adds the `private_security` job and waits for its CI run and REV |
| Review of the 58 allow-list entries (expiry 2026-12-31) | ⏳ Due by 2026-12-31: an expired entry is ignored and its findings count again (SPEC-03 §5.1 rule 4). At M3 the ceiling is 58, so a new entry (for example for the Elasticsearch 8 image's Ubuntu packages, [ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#english)) needs a removal |
| Authenticated ZAP scan of `web` | ⏳ Not done; no owner decision on when |
| Preview from the new ember UI (API v2) | ⏳ Carried from §2b: the server-side change RDM-osf.io-dev2027 PR #14 is in osf.io `develop` ([DEMO-20](../demo/20_core_install_mac_studio.md#english)) and RDM-ember-osf-web-dev2027 PR #3 is merged; open: a check on the real ember screen after deployment — no acceptance scenario covers the ember preview yet, so success is not shown |
| Publication: PR #51 (`develop` → `master`) and the default-branch switch | 🔄 PR #51 was merged on 2026-11-14 (`9ebb9e9`). PR #64 to #66 were published to `master` by PR #67 on 2026-11-14 (merge commit `2950b72`, owner decision of the same day); the default-branch switch is the owner's |
| S1–S5 subsystem scenarios (the M3 goal) | ⏳ The modules still carry an unconditional `skip(reason=M3)` ([DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#english)) |

### 3. Rules

This board is the **single source of truth** for milestone progress:

1. Every document that mentions a milestone must link to this board.
2. The "Status" column above is authoritative; status updates require a PR with evidence (demo run or acceptance pass).
3. "Open items" has one table per milestone that has started (§2 for M1, §2b for M2, §2c for M5, §2d for M3); later milestones get their own tables when they start.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 節目

| 節目 | ゴール | セキュリティ門 | ステータス |
|---|---|---|---|
| M1 | docs の骨格・manifest・dev2027 リポジトリ群がある。レビュー済み PR が develop にマージ | 報告＋許容リスト | ✅ **完了**（PR #19 を 2026-11-05 にマージ） |
| M2 | コア 6 本が Mac Studio で一発導入。Playwright 受入合格。amd64 ビルド | 報告＋許容リスト（M1 より件数を減らす） | ✅ **2026-11-13 の所有者の判断で完了**（「一括で承認、M2 完了」）。書かれた条件をすべて満たしたのでは**なく**、既知の限界つきである。示したこと: Mac Studio では、以前の固定版で一発導入が以前の実機の回で成功した。マージ後の最終の固定版では、既存の Mac の環境を個別のコマンドで更新し、そのあと受入が 14 件中 14 件合格し（実行 `acc-20261112T223428Z-fda84a`）、検査が完走した（運用者の記録）（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）。Ubuntu arm64 では、最終の固定版を新しいチェックアウトへ一つのコマンドで導入し（5 回目の試行。VM は新品ではない）、受入が 14 件中 14 件合格した（実行 `acc-20261113T021549Z-92641d`、[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#japanese)）。**満たさなかったこと・示していないこと:** (1) 許容リストは 58 項目で、書かれた条件「M1 より少なく」（M1: 0）を満たさない。所有者の判断は 58 を `manifest/allowlist.baseline.json` の M2 の終了時の件数として受け入れたもので、条件を満たしたことにはしない。(2) amd64: 受入 12 件中 11 件はエミュレーションの VM でしか記録していない（[DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#japanese)。C4 の成功ケースは試験の 30 秒の待ちで失敗）。そこで `scan` は終了 51（Trivy が ember-osf-web のイメージを終えられなかった）。osf.io と wiki-frontend は amd64 で組んでいない。PR #60 から `accept --wait-scale` と `scan --trivy-timeout` があり、その VM での再実行は進行中で、まだ記録していない。(3) `workflow` スコープのトークンが要る CI（per-OS のワークフロー、`images.yml` のスモーク試験、osf.io の R7-01）は push していない。所有者はその権限を与えると判断した。(4) 認証した ZAP の検査はしていない。必須サインインの下で `web` は飛ばされる。持ち越し: §2d |
| M3 | サブシステム 5 本が起動。各 1 本の正常系＋拒否ケース | 報告＋許容リスト（M2 より件数を減らす） | 2026-11-13 から**現在の節目**: `manifest/milestone.json` は M3（門は `count-not-growing`）、許容リストの上限は M2 の件数 58（`manifest/allowlist.baseline.json`）。S1〜S5 の受入モジュールは無条件の `skip(reason=M3)` をまだ持つ（[DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#japanese)）。残件: §2d |
| M4 | waterbutler・mfr・osf.io を Python 3.13 へ | HIGH 以上で停止。AI レッドチーム初回 | 計画中 |
| M5 | ES2・mongo 廃止。ES8＋postgres 15 以降。海外配布可 | CRITICAL/HIGH ゼロ。AI レッドチームの未解決経路ゼロ | **下準備**（§2c）: `db upgrade` 付きの PostgreSQL 18（[ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#japanese)）。Elasticsearch 2・MongoDB・sharejs はインストーラーから消え、マージ後の osf.io `develop` `90b10661c8dc` で Elasticsearch 8 が ES 2 に替わり、受入 14 件中 14 件（[ADR-13 §6](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#japanese)、[ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#japanese)）。統合ブランチは PR を待つ |

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
| Playwright 受入 C1〜C7 | ✅ 2026-11-12 に、マージ後の最終の固定版で再び **14 件中 14 件合格**（実行 `acc-20261112T223428Z-fda84a`、UTC。osf.io `90b10661c8dc`＝#8・#10・#11 のマージ後。検査は終了 0、未解決 6,264 件。[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）。それ以前に 2026-11-12 に **14 件中 14 件合格**（実行 `acc-20261111T230217Z-d8363c`、UTC）。ローカルの osf.io 候補（develop `73ff43b3c2` ＋ PR #8・#10・#11）で、Elasticsearch 8、y-websocket のみ、必須サインイン、管理者の第二要素を使った。C7（ファイルページの共同編集）は新規（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）。それ以前: 2026-11-10 に **12 件中 12 件合格**（実行 `acc-20261110T015520Z-ab4cc7`）。マージ済みのセキュリティ修正をすべて含む: HMAC の統一、wiki の WebSocket の JWT（匿名ソケットは 4401 で切断）、MFR の転送時の資格情報、管理画面の資産のローカル配信、Google Analytics の削除（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）。マージは [ADR-04](../decisions/ADR-04_AI_Autonomy_and_Roles.md#japanese) の委任により、レビュー記録は `docs/reviews/`。Python 3.13 の固定版（PR #45）の後に C5 が壊れ、MFR PR #7（`9771b8cf`）で直した。実行 `acc-20261111T132104Z-530071` で再び 12 件中 12 件 |
| Trivy のイメージ検査と許容リスト件数（M1 より少なく） | ⚠️ **未達。M2 は 2026-11-13 の所有者の判断で閉じた**（「一括で承認、M2 完了」）。イメージの検査は動くが、件数の条件は**満たしていない**。履歴: 第 18 回（Trivy 単独）は 22 対象で CRITICAL 1835 / HIGH 8290 / MEDIUM 9763 / LOW 3886。ネイティブ Elasticsearch 2 の第 21 回は 1769 / 8030 / 9550 / 3676 で、許容リストはその時点で 0 件（M1: 0）だった。現在: PR #45 は、Python 3.13 の WaterButler と MFR のイメージで修正版の無い Debian 13 のパッケージについて **58 項目**を加える。PR #45 レビュー r1（R1-01）以降、各項目は正確なパッケージを名指しし、修正版が出れば当てはまらなくなる。これらは `scan_20261111T132607Z` で 177 件を許容する（未許容の Trivy の CRITICAL/HIGH は 726 / 3,769）。一方 `manifest/allowlist.baseline.json` は 0 で、検査が合格したのは `manifest/milestone.json` が M1（報告のみ）だったからにすぎない。M2 の「件数を増やさない」規則では 58 > 0 で失敗する。節目の終了時（SPEC-03 §5.1 規則 5）に、所有者は条件を満たさないまま M2 の完了を宣言し、その判断を M2 の終了時の件数として記録した。`counts` は `{M1: 0, M2: 58}`、`manifest/milestone.json` は M3 なので、上限は 58 で、59 項目目は終了 50 になる（単体試験 `test_m3_ceiling_is_the_m2_exit_count`）。58 項目（期限 2026-12-31）の見直しは §2d へ持ち越す |
| 新しい ember の画面（API v2）からのプレビューが内部の WaterButler に届かない（旧来のファイルのページを使う C5 とは別） | ⏳ **M3 へ持ち越し**（§2d）。経緯: コードを読んで分かった（ブラウザでは再現していない）原因は、`api/files/serializers.py` が `links.render` を MFR の `/render?url=<DOMAIN>/download/<guid>/?direct&mode=render` として作り、それが MFR のコンテナから届かないブラウザ向けの URL で、その経路も `mode=render` を見なかったことである。RDM-osf.io-dev2027 PR #14（サーバー側）と RDM-ember-osf-web-dev2027 PR #3 はどちらもマージ済み。残り: 配備後の ember の実画面での確認。ember のプレビューを試す受入シナリオはまだ無く、そこでの成功は示していない。MFR の資格情報の組（`http://web:5000` → `http://wb:7777`、MFR PR #7）は変えない |
| 既定ブランチを `develop` へ切替（所有者） | ⏳ **M3 へ持ち越し**（§2d）。M2 は所有者の判断で閉じたが、切替そのものは所有者が行う。PR #51（`develop` → `master`）は 2026-11-13 の所有者の判断により 2026-11-14 にマージした（マージコミット `9ebb9e9`） |
| Ubuntu arm64、最終の固定版で一つのコマンド | ✅ 2026-11-13: C7 を含め 14 件中 14 件（実行 `acc-20261113T021549Z-92641d`）。`scan` と `report` は終了 0（操作者の記録、[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#japanese)） |
| Ubuntu amd64（「amd64 ビルド」） | ⚠️ 2026-11-13 の所有者の判断（「既知の限界として記録」）で、**既知の限界つきで M2 としては閉じた**。エミュレーションの VM だけでの結果（[DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#japanese)）: 前提条件、`doctor`、ネイティブで組んだ 9 イメージ、`up` と `health --network` は健康、コアの受入 12 件中 11 件（C4 の成功ケースは 30 秒の待ちで失敗。コミットしていない手直しの複製で待ちを長くすると一度合格）、`scan` は終了 51（Trivy が ember-osf-web のイメージで未完。cas-overlay の SBOM の失敗は原因不明）、`report` は終了 0。osf.io と wiki-frontend は amd64 で組んでいない。（ここまでは 2026-11-12 の結果。） **最終の固定版での 2026-11-13〜14 の再実行**（DEMO-22 0.7、PR #62）: 同じ VM（新品ではない。前日のイメージ、ビルドキャッシュ、前提条件が残っていた）の新しいチェックアウトで、一つのコマンドは一度では終了 0 にならなかった（4 回。ミラーの転送の不足、10 時間 45 分のビルドのあとのボリュームの検査、エミュレーション下で短すぎた Elasticsearch 8 のヘルスチェックの窓 — PR #62 で修正 — 、再現しなかった ZAP の admin の rc 3）。そのあと `health --network` は 0、`accept --seed --wait-scale 10` は C4 と C7 を含め **14 件中 14 件**合格（実行 `acc-20261113T192132Z-1cf20d`、コミット済み）、`scan --trivy-timeout 45m` は 0、`report` は 0（運用者の記録）。今回は osf.io と wiki-frontend も amd64 で組んだ。**2026-11-14 の途切れない実行**（DEMO-22 0.8、develop f005512）: 同じ VM で Docker のキャッシュが温まった状態で、`install-ubuntu.sh --yes --profile core` は**一回の実行で終了 0**（3 時間 34 分、全工程 ok、scan の門は pass）。その後の受入試験は `--wait-scale 10` で **14 件中 14 件**合格（`acc-20261114T035503Z-461116`、コミット済み）。示していないこと: 空の Docker からの実行、実機。実機: §2d |
| `workflow` スコープのトークンが要る CI（ADR-08 §9 の per-OS のワークフロー、`images.yml` のスモーク試験） | 🔄 **M3 へ持ち越し**（§2d）。2026-11-14 に権限が付き、ワークフローは PR #65 で push した |
| 認証した ZAP の検査 | ⏳ **M2 では未実施**（既知の限界）。必須サインインの下で ZAP は `web` を飛ばしたと記録し、`admin` と `ember_osf_web` を検査する（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese) 0.22）。§2d へ持ち越す |


### 2c. M5 の残件

| 項目 | ステータス |
|---|---|
| PostgreSQL 9.6 → 18.6、`grdm-dev db status/upgrade/rollback`、`up` は版の不一致を拒む（終了 15） | 🔄 PR #42（レビュー r1 の指摘に対応）（[ADR-12](../decisions/ADR-12_PostgreSQL_18_and_Data_Directory_Upgrade.md#japanese)）: osf.io の DB 試験は 9.6 と 18 で同じ（781 合格、同じ 13 件が失敗かエラー）。9.6 のクラスタを 37 秒で更新し 531 件が一致。CAS と fakecas はログインできた。巻き戻しも測定。レビュー r1 の後、操作記録とロックでどの段階のクラッシュも復旧できる（SIGKILL と SIGTERM を測定、ADR-12 §4.1）。amd64 と Linux のホストでは未実行 |
| PostgreSQL の SCRAM | ⏳ 所有者: RDM-cas-overlay-dev2027 で CAS に 42.2 以降の JDBC ドライバーが要る（42.1.4 は `authentication type 10` で失敗） |
| Elasticsearch 2 の退役 | 🔄 インストーラー側はブランチ `feat/installer-osf-integration` で完了（[ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#japanese)）。`elasticsearch8`（TLS、認証、`website*` に限った `grdm_osf`、ポート非公開、読み取り専用ルート）が `elasticsearch` に替わった。検索、権限の絞り込み、`invoke migrate_search` を、RDM-osf.io-dev2027 の `develop` `90b10661c8dc`（#8・#10・#11 マージ済み。manifest に固定）で確認した。ブランチは PR を待つ。根拠は [ADR-13 §4](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#japanese)（2026-11-10 の所有者の判断） |
| MongoDB と sharejs の退役 | ✅ RDM-osf.io-dev2027 PR #12 がマージされた（ファイルページのエディタは y-websocket）。sharejs、mongo、そのボリューム、ポート 7007、`SHAREJS_SECRET` はインストーラーから消え、y-websocket はファイルの部屋の下書きを `y_websocket_data` に残し、シナリオ C7 がそれらなしのエディタを証明する（[ADR-13 §6](../decisions/ADR-13_Retiring_Elasticsearch_2_and_MongoDB.md#japanese)）。ブランチを push するまで、統合ブランチの固定には入らない |
| Elasticsearch 6 → 8（メトリクス） | ⏳ 未着手。`elasticsearch6` は django-elasticsearch-metrics のために残る（ADR-14） |
| 必須サインインと管理者の 2 段階サインイン（RDM-osf.io-dev2027 PR #8・#10） | 🔄 インストーラー側は完了（`compose render --public-access`、既定 `false`。`osf_init` による migration 0006・0007。C6 のため種データの管理者は TOTP 登録済み）、マージ後の `develop` `90b10661c8dc` で確認した（#8 は R7-01 の CI ジョブを除いてマージ。RDM-osf.io-dev2027 の issue #16 で追跡し、`workflow` 権限を待つ）。C1〜C7 はサインインして合格し、未登録の管理者は登録画面へ送られ、匿名の検索は 401。管理者の Shibboleth の `idp` モードは有効にしない（Web サーバーが環境変数を設定する必要があり、プロキシの連鎖ではできない） |

### 2d. M3 の残件

M3 は、所有者が M2 を閉じた 2026-11-13 に始まった（「一括で承認、M2 完了」）。M2 から持ち越した項目を、同じ日の所有者の判断（「既知の限界として記録」）とともにここに記録する。

| 項目 | ステータス |
|---|---|
| amd64 の実機: 途切れない一つのコマンドでの導入、コミットした試験での受入、完走した `scan` | ⏳ 未了（2026-11-13 の所有者の判断: 既知の限界として記録し、M3 以降）。これまではエミュレーションの VM だけ（[DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#japanese)）。その VM で最終の固定版は、のちに `--wait-scale 10` で 14 件中 14 件合格し `scan` も完走したが、途切れない一つのコマンドではなかった（DEMO-22 0.7）。2026-11-14 には、その VM で一つのコマンドも一回の実行で終了 0 になった（DEMO-22 0.8、Docker のキャッシュは温まった状態）。残り: 実機で、空の Docker からの同じ実行 |
| WSL2（Windows 11） | ⏳ 未了（同じ判断）。未実行で、Windows 11 の機械が要る（[DEMO-21](../demo/21_core_install_ubuntu_arm64_lima.md#japanese)、[ADR-08 §5](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md#japanese)） |
| 検索の情報漏えいの脆弱性を上流へ報告すること | ⏳ **未決**（2026-11-13 の所有者の判断）。報告の下書きを用意し、何かを送る前に所有者に改めて尋ねる。何も送っておらず、このリポジトリに下書きは無い |
| `workflow` スコープのトークンが要る CI: ブランチ `feat/per-os-installers` の `installer-prereq-lint.yml`・`installer-full.yml` とその補助（[ADR-08 §9](../decisions/ADR-08_Per_OS_Installer_Entry_Points.md#japanese)）、`images.yml` のスモーク試験 | 🔄 PR #65 で push した（2026-11-14 に権限が付いた）。`images.yml` のスモーク試験は、外した Elasticsearch 2 のレシピの代わりに Elasticsearch 8 のイメージを起動する。`installer-full.yml` は、リポジトリのシークレット `GRDM_INTEGRATION_READ_TOKEN` を用意して一度手で起動する必要がある |
| osf.io の R7-01: 非公開検索のセキュリティ CI ジョブ（RDM-osf.io-dev2027 の issue #16） | ⏳ 未了。PR #8 は、所有者が R7-01 を issue #16 へ繰り延べたうえでマージされた（[docs/reviews/](../reviews/README.md) のレビュー r8）。権限が付いたので、`private_security` ジョブを足す RDM-osf.io-dev2027 PR #22（2026-11-14）が CI の実行と REV を待つ |
| 許容リスト 58 項目の見直し（期限 2026-12-31） | ⏳ 2026-12-31 までに行う。期限切れの項目は無視され、その検出はまた数えられる（SPEC-03 §5.1 規則 4）。M3 の上限は 58 なので、新しい項目（たとえば Elasticsearch 8 のイメージの Ubuntu パッケージ、[ADR-14](../decisions/ADR-14_Elasticsearch_8_with_TLS_and_Authentication.md#japanese)）には別の項目の削除が要る |
| `web` の認証した ZAP の検査 | ⏳ 未実施。時期についての所有者の判断は無い |
| 新しい ember の画面（API v2）からのプレビュー | ⏳ §2b から持ち越し。サーバー側の変更 RDM-osf.io-dev2027 PR #14 は osf.io の `develop` にあり（[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）、RDM-ember-osf-web-dev2027 PR #3 はマージ済み。残り: 配備後の ember の実画面での確認。ember のプレビューを試す受入シナリオはまだ無く、成功は示していない |
| 公開: PR #51（`develop` → `master`）と既定ブランチの切替 | 🔄 PR #51 は 2026-11-14 にマージした（`9ebb9e9`）。PR #64〜#66 は、同日の所有者の判断により 2026-11-14 に PR #67 で `master` に公開した（マージコミット `2950b72`）。既定ブランチの切替は所有者が行う |
| S1〜S5 のサブシステムのシナリオ（M3 のゴール） | ⏳ モジュールは無条件の `skip(reason=M3)` をまだ持つ（[DEMO-22](../demo/22_core_install_ubuntu_amd64_lima.md#japanese)） |

### 3. 規則

このボードは節目進行状況の**唯一の正本**です：

1. 節目を言及するすべての文書はこのボードへリンクしなければならない。
2. 上記の「ステータス」列が権威あるものである。ステータス更新には PR と証跡（実行結果または受入合格）が必要。
3. 「残件」は着手した節目ごとに表を持つ（M1 は §2、M2 は §2b、M5 は §2c、M3 は §2d）。後の節目は着手時に専用の表を追加する。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Milestone | A checkpoint with a pass/fail test. | 合否の試験がある関門。 |
| Security gate | A checkpoint the build must pass before it is called good. | ビルドを導入してよいかを決める試験。 |
| Open item | A task or PR that has not been completed. | 完了していないタスクまたは PR。 |
| Status board | The single source of truth for milestone progress. | 節目進行状況の唯一の正本。 |
| Evidence | Proof that a test or check passed. | 試験または検査が合格した証拠。 |
