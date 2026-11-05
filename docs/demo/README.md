# Demonstration Records / 実証記録

> **Summary:** Records of what was actually done: acceptance runs, integration test results. Each record lives under `demo/runs/` and includes results.toon, screenshots, and traces.
> **概要:** 実際にやったことの記録：受入試験、統合試験結果。各記録は `demo/runs/` の下にあり、results.toon、スクリーンショット、トレースを含みます。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** a milestone can only be called passed if the acceptance run that passed it is recorded with its evidence; this folder is where that evidence lives. ／ 節目を「合格」と呼べるのは、合格した受入実行が証跡とともに記録されているときだけであり、その置き場がこのフォルダだと分かった。
- Normative for: [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md), [SPEC-03 Security Gate](../spec/03_security_gate.md).
- Related: [../README.md](../README.md) · [status/](../status/README.md) · [demo/runs/](runs/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. What belongs here

A *demo* record documents what was actually done, including acceptance and integration tests. This folder contains:

| Subfolder | Purpose |
|---|---|
| [runs/](runs/README.md) | Individual run results: `acc-<timestamp>-<6 hex>/` with evidence. |

The record format is defined in [SPEC-04 §7](../spec/04_acceptance_tests.md):

```toon
evidence:
  results.toon: one line per test with id, case, status, duration_ms, http_status
  results.json: same data, canonical
  junit.xml: for CI and GitHub checks tab
  screenshots/: <test>_<case>.png, taken only on failure
  trace/: Playwright trace zip, only on failure, kept 14 days in CI
```

### 2. Open items (no entries yet / まだありません)

| Date | Title | Status |
|---|---|---|
| — | — | — |

### 3. Creating a new demo record

1. Run `grdm-dev accept` (acceptance) or `grdm-dev health --network` (integration).
2. The record is written to `docs/demo/runs/<run_id>/`.
3. Link the run folder from status reports or milestone documents.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. ここに属するもの

「実証」記録は、実際にやったこと（受入試験、統合試験）を文書化します。このフォルダには次が含まれます：

| サブフォルダ | 目的 |
|---|---|
| [runs/](runs/README.md) | 個別の実行結果：`acc-<時刻>-<6 桁の16進>/` に証跡が置かれる。 |

記録形式は [SPEC-04 §7](../spec/04_acceptance_tests.md) に定められています：

```toon
証跡:
  results.toon: 試験ごとに一行。id・case・status・duration_ms・http_status
  results.json: 同じデータの正本
  junit.xml: CI と GitHub の checks タブ向け
  screenshots/: <試験>_<ケース>.png。失敗時だけ撮る
  trace/: Playwright のトレース zip。失敗時だけ。CI では 14 日保持
```

### 2. 未解決項目（まだありません / no entries yet）

| 日付 | タイトル | ステータス |
|---|---|---|
| — | — | — |

### 3. 新しい実証記録をつくるには

1. `grdm-dev accept`（受入）または `grdm-dev health --network`（統合）を実行する。
2. 記録は `docs/demo/runs/<実行ID>/` に書かれる。
3. 状況報告や節目文書へ実行フォルダにリンクする。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Demo record | A document of what was actually done, including acceptance and integration tests. | 実際にやったこと（受入試験、統合試験）を文書化したもの。 |
| Evidence | Files that prove a test run: results, screenshots, traces. | 試験実行を証明するファイル：結果、スクリーンショット、トレース。 |
| Acceptance test | A check that the whole thing does what the user asked for. | 全体が利用者の望みどおりに動くかの確認。 |
| Integration test | A check that several pieces work together. | いくつかの部品が一緒に動くかの確認。 |
