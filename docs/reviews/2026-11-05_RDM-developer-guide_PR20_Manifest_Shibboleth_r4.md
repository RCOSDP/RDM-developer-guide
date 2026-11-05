# REV PR20 Manifest Shibboleth review r4 / Manifest Shibboleth レビュー r4

> **Summary:** R3-01 is resolved in both languages. The scope, starting points and manifest agree, and all six automatic checks pass.
> **概要:** R3-01 は英日とも解消しました。適用範囲・起点・manifest は整合し、自動検査6件はすべて成功です。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** an explicit scope and equal-tip exception make the public-first rule usable without inventing a public source for private-only components. ／ 適用範囲と先端同一の例外を明記すれば、private 専用部品に架空の公開元を要求せず公開起点の規則を運用できると分かった。
- Applies to: [PR #20](https://github.com/RCOSDP/RDM-developer-guide/pull/20), REV（担当レビュワ, Codex Astra）. PR means a proposed change / PR は変更の提案。
- Related: [Review index](README.md) · [r3](2026-11-05_RDM-developer-guide_PR20_Manifest_Shibboleth_r3.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-01](../spec/01_manifest.md) · [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) · [Manifest](../../manifest/upstreams.json) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Integration status](../status/README.md), QAE (quality assurance reviewer / QA担当) and the owner for acceptance / 所有者の採否判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Verdict: pass; R3-01 resolved. No blocking finding remains in this re-review.** This is a written assessment, not a GitHub approval action.

A repository stores change history; a branch names a path through it. A commit is a saved change, its SHA is its fingerprint, and its tip is the latest commit on a branch. A manifest is the component packing list, an upstream is an original source, and ADR is a decision record. See the [shared glossary](../reference/REF-01_Glossary.md).

Reviewed head `d50de429baa799cea924b4520e799c9c13047a52`, from `fix/manifest-shibboleth-public` to `develop`. Evidence came from `gh pr diff 20`, the base64-decoded contents API for ADR-01 at the requested branch, head-pinned contents, and the previous r3 record. The local checkout was not used as evidence of the proposed change.

### R3-01 resolution and language parity

ADR-01 §5 Scope at lines **97 / 189** now limits public-first reconstruction to the six cores, y-websocket and Shibboleth-SP. Both language halves explicitly start OASys, rdmcp and aipf_mcp_data_grdm at the private tip without reconstruction. Both also defer an integration PR when public and private tips are identical until they diverge. Procedure headings at **99 / 191** and Consequence at **107 / 199** carry the same scope restriction. Version **0.5** records the lesson in both languages and preserves prior versions.

This agrees with §1's private-only start rule and §3's source classification. Shibboleth-SP retains both `upstream/public-main` and `upstream/private-main`; its public-first procedure remains applicable. The general public-first order in §3 is read with the explicit §5 exceptions. Existing history-preservation and owner-merge steps remain intact.

### Manifest consistency

JSON (structured text data) and TOON (its compact notation) agree on the two Shibboleth-SP entries, their order and all seven fields. Public `RDM-Shibboleth-SP`, branch `main`, kind `public`, tracking branch `upstream/public-main`, status `merged`, SHA `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`, and fetched date `2026-11-05` precede the unchanged private entry with SHA `218b07f4143834278e5289a2c95ee8fe6ff01cf1` and `upstream/private-main`.

The six cores and y-websocket also have public entries. OASys, rdmcp and aipf_mcp_data_grdm have only private entries. Both wiki-frontend entries record `203d32fab60aad8d78e9b743987519252f99b817`, supporting the dated equal-tip example. This review checks the bootstrap exception; it does not certify completion of separately adopted PR work.

### Verification and remaining work

CI means checks run automatically after a change. `gh pr checks 20` returned six passes. Both the [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42020131602) and [security and manifest run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42020131555) report the reviewed head and conclusion `success`.

Results are recorded in TOON (compact text data):

```toon
checks[6]{name,result}:
  Build MkDocs Site,pass
  Check Links,pass
  Manifest validation and private-URL policy,pass
  Secret scan (gitleaks),pass
  Semgrep static analysis,pass
  Trivy filesystem scan (report only at M1),pass
```

Trivy remains report-only at M1, the first delivery milestone. No local checker execution is claimed. The review record was manually checked for bilingual parity, anchors, Jump, version, glossary and relative links against the PR tree. GitHub access used only `gh`; no merge, approval, closure, push or commit was performed. Publication and indexing of this local record, QAE verification and the owner's merge decision remain with the coordinator's workflow. Other integration PRs are outside this verdict.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**判定: pass（合格）。R3-01 は解消し、今回の再レビューで阻害指摘は残りません。** 文章による判定であり、GitHub の承認操作ではありません。

リポジトリは変更履歴の保管場所、ブランチは履歴の道筋の名前です。コミットは保存した変更、SHA はその指紋、先端はブランチの最新コミットです。manifest は部品の梱包表、上流は元の取得先、ADR は決定の記録です。[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

対象 head は `d50de429baa799cea924b4520e799c9c13047a52`、`fix/manifest-shibboleth-public` から `develop` への変更です。`gh pr diff 20`、指定ブランチの contents API から base64 復号した ADR-01、head 固定のファイル、前回 r3 記録を根拠にしました。ローカルの作業状態は提案変更の証拠に使っていません。

### R3-01 の解消と英日対応

ADR-01 §5 の適用範囲（**97行 / 189行**）は公開起点の再構築をコア6本・y-websocket・Shibboleth-SP に限定しました。英日とも OASys・rdmcp・aipf_mcp_data_grdm は private の先端から始め、再構築しないと明記しています。公開と private の先端が同一なら分岐まで統合 PR を出さない例外も一致します。手順見出し（**99行 / 191行**）と結果（**107行 / 199行**）も同じ範囲に限定されています。版 **0.5** は両言語で学びを記録し、過去の版を保持しています。

§1 の private 専用の開始規則、§3 の取得元の分類と一致します。Shibboleth-SP は `upstream/public-main` と `upstream/private-main` の両方を保持し、公開起点の手順の対象です。§3 の一般的な公開起点の順序は §5 の明示的な例外と合わせて読めます。既存履歴の保持と所有者によるマージの手順は維持されています。

### Manifest の整合性

JSON（構造のある文字データ）と TOON（その短い表記）は、Shibboleth-SP の上流2件、順序、全7項目が一致します。公開 `RDM-Shibboleth-SP`、branch `main`、kind `public`、tracking_branch `upstream/public-main`、status `merged`、SHA `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`、取得日 `2026-11-05` が先で、SHA `218b07f4143834278e5289a2c95ee8fe6ff01cf1` と `upstream/private-main` の非公開項目は不変です。

コア6本と y-websocket にも公開項目があり、OASys・rdmcp・aipf_mcp_data_grdm は非公開項目だけです。wiki-frontend の両項目は `203d32fab60aad8d78e9b743987519252f99b817` を記録し、日付付きの先端同一の例と整合します。今回は初回構築の例外を確認したもので、別途採用する PR の作業完了を認定するものではありません。

### 検証と残作業

CI は変更後の自動検査です。`gh pr checks 20` は6件すべて成功でした。[文書検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42020131602)と[セキュリティ・manifest 検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42020131555)は、いずれも対象 head と結論 `success` を返しました。

結果を TOON（データの短い文字表記）で記録します。

```toon
checks[6]{name,result}:
  Build MkDocs Site,pass
  Check Links,pass
  Manifest validation and private-URL policy,pass
  Secret scan (gitleaks),pass
  Semgrep static analysis,pass
  Trivy filesystem scan (report only at M1),pass
```

Trivy は M1（最初の開発到達点）では報告のみです。ローカルで検査を実行したとは主張しません。レビュー記録の英日対応、アンカー、Jump、版、用語注、相対リンク先を PR のファイル一覧と手動照合しました。GitHub へのアクセスは `gh` のみで、マージ・承認・クローズ・push・commit はしていません。ローカル記録の公開・索引追加、QAE の検証、所有者のマージ判断は調整担当の手順に委ねます。他の統合 PR は今回の判定範囲外です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change for review. | レビューする変更の提案。 |
| SHA | Fingerprint of a saved change. | 保存した変更の指紋。 |
| Tip | Latest commit on a branch. | ブランチの最新の変更。 |
| Reconstruction | Rebuilding combined history from the stated starting point. | 指定した起点から統合履歴を組み直すこと。 |
| CI | Checks run automatically after changes. | 変更後の自動検査。 |
| JSON / TOON | Structured text data and its compact notation. | 構造のある文字データとその短い表記。 |
| QAE | Quality assurance reviewer. | QA担当。 |
