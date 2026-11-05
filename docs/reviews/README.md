# Review Records / レビュー記録

> **Summary:** Independent assessment of pull requests: each record is a dated file named YYYY-MM-DD_<Title>_rN.md, written by REV (Codex Astra). Reviews are linked from the PR and stored here for auditability.
> **概要:** プルリクエストの独立した評価：各記録は日付付きファイル、YYYY-MM-DD_<Title>_rN.md の形式。REV（Codex Astra）が書く。レビューは PR からリンクされ、監査のためにここに保管される。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** every PR gets an independent review, and the review must be kept as its own record so that what was checked, and why, can be read later. ／ すべての PR は独立したレビューを受け、何をなぜ確かめたかを後から読めるよう、レビューは独自の記録として残す必要があると分かった。
- Normative for: [SPEC-04 Acceptance Tests](../spec/04_acceptance_tests.md) review section, [ADR-04 AI Autonomy and Roles](../decisions/ADR-04_AI_Autonomy_and_Roles.md) review section.
- Related: [../README.md](../README.md) · [handoff/](../handoff/README.md) · [status/](../status/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. What belongs here

A *review record* documents REV's (Codex Astra) independent assessment of a pull request. This folder contains:

| Type | Naming convention | Description |
|---|---|---|
| Review | `YYYY-MM-DD_<Title>_rN.md` | Review of PR #<N>; includes findings, approval/rejection, and suggestions. |

### 2. Review format

A review record includes:

- Date of review
- PR title and number
- Scope of review (files changed, lines affected)
- Findings: security issues, bugs, style issues
- Approval status: approved / rejected / needs revision
- Suggested changes (if rejection or revision needed)

### 3. Open items (no entries yet / まだありません)

| Date | Title | PR | Status |
|---|---|---|---|
| — | — | — | — |

### 4. Creating a new review record

1. Name the file `YYYY-MM-DD_<Title>_rN.md`.
2. Link to the PR number in the header.
3. Describe scope, findings, and approval decision.
4. Link from the PR as "reviewed by REV (Codex Astra)".

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. ここに属するもの

「レビュー記録」は REV（Codex Astra）がプルリクエストに対して行った独立した評価を文書化します。このフォルダには次が含まれます：

| 種別 | 命名規則 | 説明 |
|---|---|---|
| レビュー | `YYYY-MM-DD_<Title>_rN.md` | PR #<N> のレビュー。調査結果、承認／拒否、提案を含む。 |

### 2. レビューの形式

レビュー記録には次が含まれます：

- レビュー日
- PR の題名と番号
- レビュー範囲（変更ファイル、影響行）
- 調査結果：セキュリティ問題、バグ、スタイル問題
- 承認ステータス：承認／拒否／修正必要
- 提案される変更（拒否または修正が必要な場合）

### 3. 未解決項目（まだありません / no entries yet）

| 日付 | タイトル | PR | ステータス |
|---|---|---|---|
| — | — | — | — |

### 4. 新しいレビュー記録をつくるには

1. ファイル名を `YYYY-MM-DD_<Title>_rN.md` にする。
2. ヘッダに PR 番号へリンクする。
3. 範囲、調査結果、承認決定を記述する。
4. PR から「REV（Codex Astra）レビュー済み」としてリンクする。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Review record | A document of REV's independent assessment of a PR. | PR の REV の独立した評価を文書化したもの。 |
| Reviewer (REV) | Codex Astra, the independent PR reviewer. | 独立した PR レビュー担当者（Codex Astra）。 |
| Approval status | Whether the PR is approved, rejected, or needs revision. | PR が承認、拒否、または修正必要かどうか。 |
| Findings | Security issues, bugs, or style issues discovered during review. | レビュー中に発見したセキュリティ問題、バグ、スタイル問題。 |
| Auditability | The ability to verify that a process was done correctly. | プロセスが正しく行われたか検証できる能力。 |
