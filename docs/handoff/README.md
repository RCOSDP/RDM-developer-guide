# Hand-off Records / 引継ぎ記録

> **Summary:** Requests to other teams or agents: each record is a dated file named YYYY-MM-DD_<Title>.md. Hand-offs may request review, merge approval, or other actions from external teams.
> **概要:** 他のチームやエージェントへの依頼：各記録は日付付きファイル、YYYY-MM-DD_<Title>.md の形式。引継ぎはレビュー、マージ承認、その他のアクションを外部チームに依頼することがあります。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** without a hand-off record, it was unclear what was requested of Codex Astra; naming convention makes the request searchable and trackable. ／ 引継ぎ記録がなければ、Codex Astra に何を依頼したか分からず、命名規則で要求が検索可能で追跡可能になると分かった。
- Normative for: Hand-off records naming convention, review record naming.
- Related: [../README.md](../README.md) · [reviews/](../reviews/README.md) · [status/](../status/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. What belongs here

A *hand-off* is a request to another team or agent. This folder contains:

| Type | Naming convention | Description |
|---|---|---|
| Hand-off | `YYYY-MM-DD_<Title>.md` | Request to external team (review, merge, deploy). |
| Review | `YYYY-MM-DD_<Title>_rN.md` | Review record written by REV (Codex Astra). |

### 2. Open items (no entries yet / まだありません)

| Date | Title | Requested by | Status |
|---|---|---|---|
| — | — | — | — |

### 3. Creating a new hand-off record

1. Name the file `YYYY-MM-DD_<Title>.md`.
2. Describe: what is ready, who should review, what decision is needed.
3. Link to related PRs and documents.
4. Assign the hand-off to the appropriate team (REV, owner, deployment).

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. ここに属するもの

「引継ぎ」は他のチームやエージェントへの依頼です。このフォルダには次が含まれます：

| 種別 | 命名規則 | 説明 |
|---|---|---|
| 引継ぎ | `YYYY-MM-DD_<Title>.md` | 外部チームへの依頼（レビュー、マージ、配備）。 |
| レビュー | `YYYY-MM-DD_<Title>_rN.md` | REV（Codex Astra）が書くレビュー記録。 |

### 2. 未解決項目（まだありません / no entries yet）

| 日付 | タイトル | 依頼者 | ステータス |
|---|---|---|---|
| — | — | — | — |

### 3. 新しい引継ぎ記録をつくるには

1. ファイル名を `YYYY-MM-DD_<Title>.md` にする。
2. 記述：いつ準備ができているか、誰がレビューすべきか、どのような決断が必要か。
3. 関連する PR と文書へリンクする。
4. 引継ぎを適切なチーム（REV、所有者、配備）に割り当てる。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Hand-off | A request to another team or agent. | 他のチームやエージェントへの依頼。 |
| Record | A document that captures an event or request. | イベントや要求を記録する文書。 |
| Review | An independent assessment of a pull request. | プルリクエストの独立した評価。 |
| Merge approval | Permission from the owner to merge a PR. | PR をマージするための所有者の承認。 |
| Deploy | Release a version to production. | 本番環境へのバージョンリリース。 |
