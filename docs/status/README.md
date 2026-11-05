# Status Board / 進捗ボード

> **Summary:** The single source of truth for milestone progress: M1–M5 status, open items, upstream tracking reports. The rules that define this board as the authoritative progress record.
> **概要:** 節目進捗の唯一の正本：M1〜M5 の進捗、未解決項目、上流追従報告。このボードが権威ある進行状況記録であることを定める規則。

**Jump:** [English](#english) · [日本語](#japanese)

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
| M1 | Docs skeleton, manifest, dev2027 repos exist; reviewed PRs merged to develop | Report + allow-list | **In progress** |
| M2 | Core 6 install with one command on Mac Studio; Playwright acceptance passes; amd64 builds | Report + allow-list (fewer entries than M1) | Planned |
| M3 | 5 subsystems start; one success + one rejection case each | Report + allow-list (fewer entries than M2) | Planned |
| M4 | Waterbutler, mfr, osf.io on Python 3.13 | Stop on HIGH or above; first AI red-team run | Planned |
| M5 | ES2 and mongo removed; ES8 + postgres 15 or later; distributable abroad | Zero CRITICAL/HIGH; zero open AI red-team paths | Planned |

### 2. Open items for M1

| Item | Status |
|---|---|
| docs skeleton (READMEs for all folders) | ✅ Written |
| manifest/upstreams.json | ✅ Created |
| dev2027 integration repos (11) | ✅ Created |
| Integration PR osf.io #1 | 🔄 Open |
| MkDocs site build (`site/`, strict build passes) | ✅ Built |
| Guides migration to `docs/guides/` (pointers kept at old paths) | ✅ Done |
| Codex Astra review of RDM-osf.io-dev2027 PR #1 | 🔄 r1/r2 done: request changes. R1 fixed; R2 awaits the owner's decision on ADR-01 §5; R3 is the owner's call |
| M1 skeleton PR to `develop` (this repository) | 🔄 Open, awaiting Codex Astra review and owner merge |
| GitHub Actions (docs, security) | ✅ Authored; first run happens on the M1 PR |

### 3. Rules

This board is the **single source of truth** for milestone progress:

1. Every document that mentions a milestone must link to this board.
2. The "Status" column above is authoritative; status updates require a PR with evidence (demo run or acceptance pass).
3. "Open items" lists only M1 at this time; future milestones will have their own tables.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 節目

| 節目 | ゴール | セキュリティ門 | ステータス |
|---|---|---|---|
| M1 | docs の骨格・manifest・dev2027 リポジトリ群がある。レビュー済み PR が develop にマージ | 報告＋許容リスト | **進行中** |
| M2 | コア 6 本が Mac Studio で一発導入。Playwright 受入合格。amd64 ビルド | 報告＋許容リスト（M1 より件数を減らす） | 計画中 |
| M3 | サブシステム 5 本が起動。各 1 本の正常系＋拒否ケース | 報告＋許容リスト（M2 より件数を減らす） | 計画中 |
| M4 | waterbutler・mfr・osf.io を Python 3.13 へ | HIGH 以上で停止。AI レッドチーム初回 | 計画中 |
| M5 | ES2・mongo 廃止。ES8＋postgres 15 以降。海外配布可 | CRITICAL/HIGH ゼロ。AI レッドチームの未解決経路ゼロ | 計画中 |

### 2. M1 の残件

| 項目 | ステータス |
|---|---|
| docs の骨格（全フォルダの README） | ✅ 作成済み |
| manifest/upstreams.json | ✅ 作成 |
| dev2027 統合リポジトリ（11） | ✅ 作成 |
| 統合 PR RDM-osf.io-dev2027 #1 | 🔄 作成済み（レビュー対応中） |
| MkDocs サイトのビルド（`site/`、strict ビルド合格） | ✅ 生成済み |
| ガイドの `docs/guides/` への移植（旧パスに誘導を残す） | ✅ 完了 |
| Codex Astra による RDM-osf.io-dev2027 PR #1 のレビュー | 🔄 r1/r2 完了: request changes。R1 修正済み、R2 は ADR-01 §5 の所有者判断待ち、R3 は所有者判断 |
| M1 骨格 PR（本リポジトリ、develop 向け） | 🔄 作成済み。Codex Astra レビューと所有者マージ待ち |
| GitHub Actions（docs, security） | ✅ 作成済み。初回実行は M1 PR で行う |

### 3. 規則

このボードは節目進行状況の**唯一の正本**です：

1. 節目を言及するすべての文書はこのボードへリンクしなければならない。
2. 上記の「ステータス」列が権威あるものである。ステータス更新には PR と証跡（実行結果または受入合格）が必要。
3. 「未解決項目」は現時点で M1 のみ。将来の節目にはそれぞれ専用の表が追加される。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Milestone | A checkpoint with a pass/fail test. | 合否の試験がある関門。 |
| Security gate | A checkpoint the build must pass before it is called good. | ビルドを導入してよいかを決める試験。 |
| Open item | A task or PR that has not been completed. | 完了していないタスクまたは PR。 |
| Status board | The single source of truth for milestone progress. | 節目進行状況の唯一の正本。 |
| Evidence | Proof that a test or check passed. | 試験または検査が合格した証拠。 |
