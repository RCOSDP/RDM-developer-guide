# Status Board / 進捗ボード

> **Summary:** The single source of truth for milestone progress: M1–M5 status, open items, upstream tracking reports. The rules that define this board as the authoritative progress record.
> **概要:** 節目進捗の唯一の正本：M1〜M5 の進捗、未解決項目、上流追従報告。このボードが権威ある進行状況記録であることを定める規則。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.7 — 2026-11-06. **Learned:** the M2 open-items table needs the build row and the start-up row kept separate, because build finished at run 6 while start-up took seven more runs. ／ M2 の残件表はビルドの行と起動の行を分けておく必要がある。ビルドは第 6 回で終わり、起動にはさらに 7 回かかった。
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
| M2 | Core 6 install with one command on Mac Studio; Playwright acceptance passes; amd64 builds | Report + allow-list (fewer entries than M1) | **In progress**: one-command install of the core profile succeeded on the Mac Studio in real install run 18 (PR #33, [DEMO-20](../demo/20_core_install_mac_studio.md#english)): build, up, health --network, scan, report all exit 0; Playwright acceptance pending (see §2b) |
| M3 | 5 subsystems start; one success + one rejection case each | Report + allow-list (fewer entries than M2) | Planned |
| M4 | Waterbutler, mfr, osf.io on Python 3.13 | Stop on HIGH or above; first AI red-team run | Planned |
| M5 | ES2 and mongo removed; ES8 + postgres 15 or later; distributable abroad | Zero CRITICAL/HIGH; zero open AI red-team paths | Planned |

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
| edit.mako wiring in the integration repository — `RDM-osf.io-dev2027` `addons/wiki/templates/edit.mako` must load `/static/public/js/wiki/wiki-edit-page.js` (the bundle that `wiki_assets` copies into the volume `wiki_static`, [ADR-06 §4](../decisions/ADR-06_Wiki_Frontend_Overlay.md#english)) instead of `/static/js/pages/wiki-edit-page.js`; browser check of the editor and C4 once a real install reaches `up` | ⏳ Open (PR #30 review r1 R1-03); not changed in this repository; needed for the Wiki acceptance case, not for `health` |
| Playwright acceptance C1–C6 (selectors and seed data are `TODO(M2)`) | 🔄 First real run 2026-11-06 against the run-18 stack: seeding works (OSF accounts need a password different from the e-mail; the browser detection had to learn Playwright's newer Chromium layouts), 0 of 12 cases pass — a fixture name mismatch fails C1–C3/C5/C6 at setup and the fakecas password field is not visible for C4; next PR |
| Trivy image scan and allow-list count (fewer than M1) | ✅ Measured in run 18 (Trivy alone): 1835 CRITICAL / 8290 HIGH / 9763 MEDIUM / 3886 LOW over 22 targets; allow-list 0 entries (M1: 0). Semgrep, gitleaks and ZAP ran too (ZAP: 1 HIGH, 9 MEDIUM, 13 LOW to triage at M3) |
| Default branch switched to `develop` (owner) | ⏳ After M2 passes |

### 3. Rules

This board is the **single source of truth** for milestone progress:

1. Every document that mentions a milestone must link to this board.
2. The "Status" column above is authoritative; status updates require a PR with evidence (demo run or acceptance pass).
3. "Open items" has one table per milestone that has started (§2 for M1, §2b for M2); later milestones get their own tables when they start.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 節目

| 節目 | ゴール | セキュリティ門 | ステータス |
|---|---|---|---|
| M1 | docs の骨格・manifest・dev2027 リポジトリ群がある。レビュー済み PR が develop にマージ | 報告＋許容リスト | ✅ **完了**（PR #19 を 2026-11-05 にマージ） |
| M2 | コア 6 本が Mac Studio で一発導入。Playwright 受入合格。amd64 ビルド | 報告＋許容リスト（M1 より件数を減らす） | **進行中**: core プロファイルの一発導入が実機第 18 回で Mac Studio 上で成功（PR #33、[DEMO-20](../demo/20_core_install_mac_studio.md#japanese)）: build・up・health --network・scan・report がすべて終了 0。Playwright 受入は未実施（§2b 参照） |
| M3 | サブシステム 5 本が起動。各 1 本の正常系＋拒否ケース | 報告＋許容リスト（M2 より件数を減らす） | 計画中 |
| M4 | waterbutler・mfr・osf.io を Python 3.13 へ | HIGH 以上で停止。AI レッドチーム初回 | 計画中 |
| M5 | ES2・mongo 廃止。ES8＋postgres 15 以降。海外配布可 | CRITICAL/HIGH ゼロ。AI レッドチームの未解決経路ゼロ | 計画中 |

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
| 統合リポジトリ側の edit.mako 配線（M2 第 5 回で確認） — `RDM-osf.io-dev2027` の `addons/wiki/templates/edit.mako` が `/static/js/pages/wiki-edit-page.js` でなく `/static/public/js/wiki/wiki-edit-page.js`（`wiki_assets` がボリューム `wiki_static` へ写す束。[ADR-06 §4](../decisions/ADR-06_Wiki_Frontend_Overlay.md#japanese)）を読み込むこと。実機導入が `up` に達したらエディタと C4 をブラウザ確認 | ⏳ 未着手（PR #30 レビュー r1 R1-03）。本リポジトリでは変更しない。Wiki の受入ケースに必要で、`health` には不要 |
| Playwright 受入 C1〜C6（セレクタと種データは `TODO(M2)`） | 🔄 2026-11-06 に第 18 回のスタックへ初回実行: 種データ作成は動く（OSF アカウントのパスワードはメールと別にする必要。ブラウザ検出は Playwright の新しい Chromium 配置を学ぶ必要があった）、12 ケース中 0 合格 — fixture 名の不一致で C1〜C3/C5/C6 が setup で失敗、C4 は fakecas のパスワード欄が不可視。次の PR で対応 |
| Trivy のイメージ検査と許容リスト件数（M1 より少なく） | ✅ 第 18 回で計測（Trivy 単独）: 22 対象で CRITICAL 1835 / HIGH 8290 / MEDIUM 9763 / LOW 3886。許容リスト 0 件（M1: 0）。Semgrep・gitleaks・ZAP も実行（ZAP: HIGH 1・MEDIUM 9・LOW 13 は M3 で精査） |
| 既定ブランチを `develop` へ切替（所有者） | ⏳ M2 合格後 |

### 3. 規則

このボードは節目進行状況の**唯一の正本**です：

1. 節目を言及するすべての文書はこのボードへリンクしなければならない。
2. 上記の「ステータス」列が権威あるものである。ステータス更新には PR と証跡（実行結果または受入合格）が必要。
3. 「残件」は着手した節目ごとに表を持つ（M1 は §2、M2 は §2b）。後の節目は着手時に専用の表を追加する。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Milestone | A checkpoint with a pass/fail test. | 合否の試験がある関門。 |
| Security gate | A checkpoint the build must pass before it is called good. | ビルドを導入してよいかを決める試験。 |
| Open item | A task or PR that has not been completed. | 完了していないタスクまたは PR。 |
| Status board | The single source of truth for milestone progress. | 節目進行状況の唯一の正本。 |
| Evidence | Proof that a test or check passed. | 試験または検査が合格した証拠。 |
