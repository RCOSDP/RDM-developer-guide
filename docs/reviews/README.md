# Review Records / レビュー記録

> **Summary:** Independent assessment of pull requests: each record is a dated file named YYYY-MM-DD_<Title>_rN.md, written by REV (Codex Astra). Reviews are linked from the PR and stored here for auditability.
> **概要:** プルリクエストの独立した評価：各記録は日付付きファイル、YYYY-MM-DD_<Title>_rN.md の形式。REV（Codex Astra）が書く。レビューは PR からリンクされ、監査のためにここに保管される。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-12. **Learned:** a review record that was never saved cannot be recreated truthfully, so the gap is stated and the posted pull-request comment is the reference. ／ 保存されなかったレビュー記録は、後から正確に作り直せない。欠落を明記し、投稿済みの PR コメントを参照先とする。
  0.1 — 2026-11-05. **Learned:** every PR gets an independent review, and the review must be kept as its own record so that what was checked, and why, can be read later. ／ すべての PR は独立したレビューを受け、何をなぜ確かめたかを後から読めるよう、レビューは独自の記録として残す必要があると分かった。
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

### 5. Missing records and the pull-request comments that stand in for them

Nine review records written on 2026-11-10 were never saved in this folder: they lived only in a scratch directory of a session that ended. They are **not recreated**, because a record rebuilt from memory would not say what REV actually checked. Each one was posted as a comment on its pull request by REV (Codex Astra), and that comment is the reference. The repositories are private; they are named here by name and number only. The comment ID is the number at the end of the comment's address on the pull request page.

| Repository | PR | Round | REV comment ID | Posted (UTC) | Verdict | Head reviewed |
|---|---|---|---|---|---|---|
| RDM-osf.io-dev2027 | #8 | r1 | 6757009993 | 2026-11-10 02:12 | changes requested（要修正） | `e7f23e13141f` |
| RDM-osf.io-dev2027 | #8 | r2 | 6758141691 | 2026-11-10 03:28 | changes requested（要修正） | `8bb07f17c2` |
| RDM-osf.io-dev2027 | #8 | r3 | 6759472716 | 2026-11-10 05:03 | pass（R2 の差分） | `49e5521451` |
| RDM-osf.io-dev2027 | #10 | r1 | 6759171742 | 2026-11-10 04:41 | changes requested（要修正） | `5355858363b6` |
| RDM-osf.io-dev2027 | #11 | r1 | 6759274738 | 2026-11-10 04:48 | changes requested（要修正） | `75ceaf5cb492` |
| RDM-osf.io-dev2027 | #11 | r2 | 6760403905 | 2026-11-10 06:08 | changes requested（要修正） | `58ba83af4b7c` |
| RDM-osf.io-dev2027 | #11 | r3 | 6763524193 | 2026-11-10 09:13 | pass（差分 58ba83a..3eb4042） | `3eb4042` |
| RDM-osf.io-dev2027 | #12 | r1 | 6763575801 | 2026-11-10 09:16 | changes requested（要修正） | `aa30a37d` |
| RDM-osf.io-dev2027 | #13 | r1 | 6763600948 | 2026-11-10 09:17 | changes requested（要修正） | `ef9e64261b` |

The owner decided on 2026-11-12 to note the gap and refer to these comments. From now on a review record is placed in this folder as soon as REV finishes it.

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

### 5. 欠落した記録と、代わりの PR コメント

2026-11-10 に書かれたレビュー記録 9 件は、この場所に保存されませんでした。終了したセッションの作業用ディレクトリにだけあったためです。記憶から作り直した記録は REV が実際に何を調べたかを語れないので、**作り直しません**。各記録は、REV（Codex Astra）が PR へのコメントとして投稿しており、そのコメントを参照先とします。リポジトリは非公開なので、ここでは名前と番号だけを書きます。コメント ID は、PR のページにあるコメントのアドレスの末尾の数字です。

| リポジトリ | PR | 回 | REV のコメント ID | 投稿（UTC） | 判定 | 対象の先頭 |
|---|---|---|---|---|---|---|
| RDM-osf.io-dev2027 | #8 | r1 | 6757009993 | 2026-11-10 02:12 | changes requested（要修正） | `e7f23e13141f` |
| RDM-osf.io-dev2027 | #8 | r2 | 6758141691 | 2026-11-10 03:28 | changes requested（要修正） | `8bb07f17c2` |
| RDM-osf.io-dev2027 | #8 | r3 | 6759472716 | 2026-11-10 05:03 | pass（R2 の差分） | `49e5521451` |
| RDM-osf.io-dev2027 | #10 | r1 | 6759171742 | 2026-11-10 04:41 | changes requested（要修正） | `5355858363b6` |
| RDM-osf.io-dev2027 | #11 | r1 | 6759274738 | 2026-11-10 04:48 | changes requested（要修正） | `75ceaf5cb492` |
| RDM-osf.io-dev2027 | #11 | r2 | 6760403905 | 2026-11-10 06:08 | changes requested（要修正） | `58ba83af4b7c` |
| RDM-osf.io-dev2027 | #11 | r3 | 6763524193 | 2026-11-10 09:13 | pass（差分 58ba83a..3eb4042） | `3eb4042` |
| RDM-osf.io-dev2027 | #12 | r1 | 6763575801 | 2026-11-10 09:16 | changes requested（要修正） | `aa30a37d` |
| RDM-osf.io-dev2027 | #13 | r1 | 6763600948 | 2026-11-10 09:17 | changes requested（要修正） | `ef9e64261b` |

所有者は 2026-11-12 に、欠落を明記してこれらのコメントを参照することに決めました。以後、REV のレビュー記録は完了したらすぐにこの場所へ収めます。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Review record | A document of REV's independent assessment of a PR. | PR の REV の独立した評価を文書化したもの。 |
| Reviewer (REV) | Codex Astra, the independent PR reviewer. | 独立した PR レビュー担当者（Codex Astra）。 |
| Approval status | Whether the PR is approved, rejected, or needs revision. | PR が承認、拒否、または修正必要かどうか。 |
| Findings | Security issues, bugs, or style issues discovered during review. | レビュー中に発見したセキュリティ問題、バグ、スタイル問題。 |
| Auditability | The ability to verify that a process was done correctly. | プロセスが正しく行われたか検証できる能力。 |
