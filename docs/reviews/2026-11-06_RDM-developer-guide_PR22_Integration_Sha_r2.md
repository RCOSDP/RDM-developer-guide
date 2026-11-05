# REV PR22 integration revision review r2 / PR22 統合版レビュー r2

> **Summary:** Both r1 findings are resolved. The revised history agrees with GitHub, both languages agree, and all six automated checks pass; minor documentation navigation improvements remain.
> **概要:** r1 の二指摘は解決した。修正後の履歴は GitHub と一致し、日英の内容も対応し、自動検査六件は合格。軽微な文書案内の改善が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a closed proposal and a merged replacement need separate historical labels; passing automated checks does not prove complete document navigation. ／ 閉じた提案と統合された代替提案は履歴を分けて記す必要があり、自動検査の成功だけでは文書案内の完全性を保証できないと分かった。
- Applies to: [PR #22](https://github.com/RCOSDP/RDM-developer-guide/pull/22), a pull request (proposed change), titled `fix(manifest): dev2027 各 develop の先端を integration_sha に固定`; reviewer REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [SPEC-06 documentation rules](../spec/06_documentation_conventions.md) · [SPEC-01 component list](../spec/01_manifest.md) · [r1 for PR22/25](2026-11-06_RDM-developer-guide_PR22_PR25_r1.md) · [r1 for PR23/24](2026-11-06_RDM-developer-guide_PR23_PR24_r1.md) · [Shared glossary](../reference/REF-01_Glossary.md)
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Scope and verdict

**Pass with non-blocking documentation nits.** Findings 22-01 and 22-02 are resolved; no new blocking issue was found. This is a review recommendation, not a GitHub approval.

Reviewed head (latest saved revision) `00d370076c1ad4c42dc2d5d0a68ed61120fe3824`, from `fix/manifest-integration-sha` to `develop`, on 2026-11-06 JST (Japan time). GitHub CLI (the `gh` command-line client) supplied the proposal diff, files, proposal histories and automated-check results. This revision changes the status board and adds two historical r1 review records. The manifest (component list with fixed revisions) is unchanged from r1, so the eleven SHA (revision fingerprint) checks recorded in r1 were not all repeated. No local tests, approval, merge, close, commit, push or Docker state changes were performed.

### Resolution and evidence

- **22-01 resolved:** board lines 39 and 80 now identify RDM-wiki-frontend-dev2027 #1 as closed without merge because the source tips were identical. GitHub reports `CLOSED`, closure `2026-11-05T11:21:58Z`, and no merge time. The closing comment explains the identical tips and abandoned amended proposal. The public, private and integration develop tips queried during r2 all equal `203d32fab60aad8d78e9b743987519252f99b817`. Both languages preserve the seven-merge count without counting wiki as a merge.
- **22-02 resolved:** board line 8 advances to version 0.4 dated 2026-11-06 with a bilingual Learned statement, retaining earlier versions. Lines 42 and 83 mark osf.io #1 historical/superseded. GitHub reports #1 closed without merge at `2026-11-05T11:11:49Z`; its closing comment records rejection of the bootstrap interpretation and replacement by #2. Proposal #2 is merged at `2026-11-05T19:25:02Z`, or 2026-11-06 in Japan. The revised English and Japanese rows agree.
- **Added records:** both r1 files have one title, bilingual summaries, Jump, explicit language anchors, reciprocal links, version 0.1 with Learned, scope, parent/specification/Used-by links and a final bilingual glossary. Their findings, verdicts and limitations correspond between languages. They retain historical reviewed heads and do not claim that PR23–25 issues were resolved by PR22. Their earlier execution claims were read as historical evidence, not rerun in r2.

### Minor documentation follow-up

**22-r2-01 / P3 (minor, non-blocking):** SPEC-06 §5 requires the folder index to list its documents with bilingual descriptions. `docs/reviews/README.md` still has an empty section 3 and does not link either newly added record. Add both entries, a version update and Learned line during documentation upkeep. Also add the shared-glossary link to the PR22/25 record's first-use notes for SHA, manifest and TOON (compact structured text); the PR23/24 record already includes that link. The required page structure passes, but full editorial compliance should not be inferred from green checks.

### Automated checks and limits

CI (automated checks run by GitHub) has six passing checks: Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, and Trivy filesystem scan. Both the [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42096020326) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42096020278) report success for the exact reviewed head. Trivy is explicitly report-only at M1; success is not proof of a vulnerability-free runtime. No full startup or acceptance execution was assessed. The r2 record is a local handoff artifact and was not part of those CI runs.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 範囲と判定

**合格、軽微な文書改善あり（非阻害）。** 22-01 と 22-02 は解決し、新しい阻害事項は見つからなかった。レビュー上の推奨であり、GitHub の承認操作ではない。

2026-11-06 日本時間に、`fix/manifest-integration-sha` から `develop` への変更の先端（最新保存版）`00d370076c1ad4c42dc2d5d0a68ed61120fe3824` を確認した。GitHub CLI（端末から GitHub を操作する `gh`）で差分、ファイル、提案の履歴、自動検査結果を取得した。今回の版は進捗ボードを変更し、過去の r1 記録二件を追加する。manifest（部品と固定版の一覧）は r1 から無変更のため、r1 に記録した十一件の SHA（保存版の指紋）の照合すべては再実行していない。ローカル試験、承認、マージ、閉鎖、commit、push、Docker の状態変更は行っていない。

### 解決状況と根拠

- **22-01 解決:** ボード 39・80 行は RDM-wiki-frontend-dev2027 #1 を、取得元の両先端が同一のためマージせず閉鎖したと記す。GitHub は `CLOSED`、閉鎖時刻 `2026-11-05T11:21:58Z`、マージ時刻なしを返した。閉鎖コメントも同一先端と書き換えられた提案の不採用を説明する。r2 で確認した公開・非公開・統合先の develop はすべて `203d32fab60aad8d78e9b743987519252f99b817`。日英とも wiki をマージに数えず、七件という数を維持する。
- **22-02 解決:** ボード 8 行は日英 Learned 付きの版 0.4、2026-11-06 となり、旧版を残す。42・83 行は osf.io #1 を履歴・置き換え済みとする。GitHub の #1 は `2026-11-05T11:11:49Z` にマージせず閉鎖され、閉鎖コメントは初回構築解釈の却下と #2 への置き換えを記録する。#2 は `2026-11-05T19:25:02Z`、日本時間 2026-11-06 にマージ済み。修正行の日英は一致する。
- **追加記録:** 両 r1 ファイルは単一題名、日英概要、Jump、明示的な言語アンカー、相互リンク、Learned 付き版 0.1、対象範囲、親索引・仕様・Used-by リンク、末尾の日英用語集を備える。指摘・判定・限界は日英で対応する。過去のレビュー対象先端を保持し、PR23〜25 の問題を PR22 で解決したとは述べていない。過去の試験実行の記述は履歴の証拠として読み、r2 で再実行していない。

### 軽微な文書改善

**22-r2-01 / P3（軽微、非阻害）:** SPEC-06 §5 はフォルダ索引に各文書と日英の説明を求める。`docs/reviews/README.md` の第 3 節は空のままで、追加二記録へのリンクがない。文書整備時に両項目、版更新、Learned を追加する。また PR22/25 記録の SHA・manifest・TOON（構造化データを短く書く形式）の初出注に共通用語集リンクを補う。PR23/24 記録には既にリンクがある。必須ページ構造は満たすが、自動検査成功だけで編集規約全体の遵守を断定しない。

### 自動検査と限界

CI（GitHub が実行する自動検査）は Build MkDocs Site、Check Links、Manifest validation and private-URL policy、Secret scan (gitleaks)、Semgrep static analysis、Trivy filesystem scan の六件が合格。[文書実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42096020326)と[セキュリティ実行](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42096020278)の成功が対象先端そのものに対応することも確認した。Trivy は M1 では報告のみであり、成功は稼働環境に脆弱性がない証拠ではない。完全起動・受入実行は評価していない。r2 記録はローカルの引継ぎ成果物であり、この CI 実行には含まれない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change for review. | 点検するために提出する変更案。 |
| SHA | A fingerprint identifying a saved revision. | 保存版を特定する指紋。 |
| Manifest | A list of components and their fixed revisions. | 部品と固定する版の一覧。 |
| CI | Checks run automatically for a proposed change. | 変更案に対して自動実行する検査。 |
| Superseded | Replaced by a later proposal. | 後の提案に置き換えられた状態。 |
