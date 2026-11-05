# REV PR20 Manifest Shibboleth review r3 / Manifest Shibboleth レビュー r3

> **Summary:** The Shibboleth-SP tracking bullets are corrected and the manifest checks pass. Request changes because ADR-01 §5 still requires a public starting point for private-only components.
> **概要:** Shibboleth-SP の追跡記述は修正済みで manifest 検査も合格です。ADR-01 §5 が private 専用部品にも公開起点を要求するため、要修正とします。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** fixing tracking bullets does not resolve a conflicting universal bootstrap procedure. ／ 追跡の箇条書きを直しても、全対象に適用する初回構築手順の矛盾は解消しないと分かった。
- Applies to: [PR #20](https://github.com/RCOSDP/RDM-developer-guide/pull/20), reviewed by REV（担当レビュワ, Codex Astra）. A PR is a proposed change / PR は変更の提案です。
- Related: [Review index](README.md) · [r2](2026-11-05_dev2027_Strict_Reconstruction_PRs_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [SPEC-01](../spec/01_manifest.md) · [ADR-01](../decisions/ADR-01_Integration_Repository_Placement.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Integration status](../status/README.md), QAE and the owner for verification and acceptance / QAE（QA担当）と所有者の検証・採否判断。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Verdict: request changes.** R2-01's §3 correction is complete; its requested §5 scope correction remains open as R3-01 (P2, a correctness issue requiring a fix before acceptance).

A repository stores change history; a branch names a path through it. A commit is a saved change and its SHA is its fingerprint. A manifest is the component packing list, an upstream is its original source, and ADR is a decision record. See the [shared glossary](../reference/REF-01_Glossary.md).

Reviewed head `b4bfc9919c26df67544328fabd265fe424c3126f`, from `fix/manifest-shibboleth-public` to `develop`. Files were read through `gh api` at that exact head; the local `feat/m2-installer` checkout was not used as PR evidence. The correction is commit `488e61ca154910055cd2509c9af0fb9e9821b147`; the later head commit adds the r1/r2 review records. This is a written verdict, not a GitHub approval or request-changes review action.

### Resolved: Shibboleth-SP tracking and manifest

Both ADR-01 §1 halves identify public `RDM-Shibboleth-SP` on `main`. Both §3 bullets (lines 60 and 150) now explicitly add `upstream/public-main`, retain `upstream/private-main`, and limit the no-public-upstream statement to OASys, rdmcp and aipf_mcp_data_grdm. For Shibboleth-SP, §5's public-first construction agrees with those statements.

JSON (structured text data) and TOON (its compact text form) agree on the two Shibboleth-SP upstream rows, their order, and all seven fields. The public row names `RDM-Shibboleth-SP`, branch `main`, kind `public`, tracking branch `upstream/public-main`, status `merged`, SHA `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`, and date `2026-11-05`. The private row remains second, with SHA `218b07f4143834278e5289a2c95ee8fe6ff01cf1` and `upstream/private-main`.

### R3-01: §5 still includes components without a public upstream

At ADR-01 lines **96–99** (English) and **186–189** (Japanese), §5 says the procedure applies to every integration repository and directs the reader to start at `upstream/public-<branch>`, then merge the private branch. Yet §1 and §3 explicitly say OASys, rdmcp and aipf_mcp_data_grdm have only private upstreams and start at the private tip. Following §5 for these three components requires a nonexistent public starting point. The universal consequence at lines **104 / 194** also needs the same scope limitation.

**Required correction:** in both language halves, restrict the public-first §5 procedure and consequence to components with a public upstream. Explicitly refer private-only components to the §1 private-tip start rule. Preserve the public-first rule for Shibboleth-SP. This is the outstanding §5 request already recorded in r2, not a new manifest defect.

### Verification evidence and limits

CI means automatic checks after a change. All six checks returned pass: Build MkDocs Site, Check Links, Manifest validation and private-URL policy, Secret scan (gitleaks), Semgrep static analysis, and Trivy filesystem scan. Trivy remains report-only at M1 (the first delivery milestone).

The [manifest job log](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42019352111/job/127217919499) explicitly runs `python3 tools/manifest_check.py --manifest-only` and reports zero findings and PASSED, including JSON/TOON parity. This CI run belongs to head `b4bfc9919c26df67544328fabd265fe424c3126f`; it tested the proposed merge `3a7df1f`. The contents API confirms both manifest files have identical file fingerprints at the PR head and that merge: JSON `40d14dc2847028e126c4b485546af4a31f4f4f16`, TOON `93d34734b443001548a5374aed97e790149c3428`. Thus the parity result covers the reviewed files. No local checker execution is claimed.

GitHub access used only `gh`. No merge, approval, closure, push, or commit was performed. The local record was manually checked for bilingual structure, anchors, Jump, version, glossary and relative-link targets. The coordinator still needs to publish and index this record; the author needs to fix R3-01 and obtain re-review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**判定: request changes（要修正）。** R2-01 の §3 修正は完了しました。依頼済みの §5 の範囲修正は R3-01（P2、受け入れ前に直すべき正しさの問題）として残ります。

リポジトリは変更履歴の保管場所、ブランチは履歴の道筋の名前です。コミットは保存した変更、SHA はその指紋です。manifest は部品の梱包表、上流は元の取得先、ADR は決定の記録です。[共通用語集](../reference/REF-01_Glossary.md)も参照してください。

対象 head は `b4bfc9919c26df67544328fabd265fe424c3126f`、`fix/manifest-shibboleth-public` から `develop` への変更です。対象 head 固定の `gh api` で読み、ローカルの `feat/m2-installer` は PR の証拠に使っていません。修正は `488e61ca154910055cd2509c9af0fb9e9821b147`、後続の head コミットは r1/r2 記録の追加です。文章による判定であり、GitHub の承認・変更要求レビュー操作ではありません。

### 解決済み: Shibboleth-SP の追跡と manifest

ADR-01 §1 の両言語は公開 `RDM-Shibboleth-SP` の `main` を示します。§3 の両言語の箇条書き（60行と150行）は `upstream/public-main` を明記し、`upstream/private-main` も保持し、「公開上流なし」を OASys・rdmcp・aipf_mcp_data_grdm に限定しました。Shibboleth-SP については §5 の公開起点手順も一致します。

JSON（構造のある文字データ）と TOON（その短い表記）は、Shibboleth-SP の上流2行、順序、全7項目が一致します。公開行は `RDM-Shibboleth-SP`、branch `main`、kind `public`、tracking_branch `upstream/public-main`、status `merged`、SHA `7f1125bb2f5bccdce1b1fc55d1dcff602bc7d38a`、日付 `2026-11-05` です。非公開行は2番目で、SHA `218b07f4143834278e5289a2c95ee8fe6ff01cf1` と `upstream/private-main` を保持します。

### R3-01: §5 が公開上流のない部品も対象にしている

ADR-01 の **96〜99行**（英語）と **186〜189行**（日本語）は、全統合リポジトリに対し `upstream/public-<branch>` から始めて非公開ブランチを取り込むよう要求しています。しかし §1・§3 は OASys・rdmcp・aipf_mcp_data_grdm が private 専用であり、private の先端から始めると明記しています。この3部品で §5 に従うと、存在しない公開起点が必要になります。**104行 / 194行**の全対象に向けた結果の記述にも同じ範囲の限定が必要です。

**必要な修正:** 英日両方で §5 の公開起点手順と結果を、公開上流がある部品に限定してください。private 専用部品は §1 の private 先端からの開始規則を参照させてください。Shibboleth-SP の公開起点は維持します。r2 に記録済みの §5 修正依頼の残件であり、新しい manifest の不備ではありません。

### 検証証跡と限界

CI は変更後の自動検査です。6件すべて成功しました。MkDocs サイト構築、リンク、manifest と非公開 URL 規則、gitleaks、Semgrep、Trivy です。Trivy は M1（最初の開発到達点）では報告のみです。

[manifest 検査ログ](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42019352111/job/127217919499)には `python3 tools/manifest_check.py --manifest-only` の実行と、JSON/TOON 突合を含む指摘0件・PASSED が記録されています。head `b4bfc9919c26df67544328fabd265fe424c3126f` に対応する CI は仮のマージ `3a7df1f` を検査しました。contents API で両地点のファイル指紋を照合し、JSON は `40d14dc2847028e126c4b485546af4a31f4f4f16`、TOON は `93d34734b443001548a5374aed97e790149c3428` とそれぞれ一致しました。このため突合結果はレビュー対象にも適用できます。ローカルで検査を実行したとは主張しません。

GitHub へのアクセスは `gh` のみで、マージ・承認・クローズ・push・commit はしていません。ローカル記録の英日構成、アンカー、Jump、版、用語注、相対リンク先を手動確認しました。調整担当による記録の公開・索引追加と、作成者による R3-01 修正・再レビューが残ります。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change for review. | レビューする変更の提案。 |
| SHA | A saved change or file's fingerprint. | 保存した変更やファイルの指紋。 |
| Tracking branch | A named copy following a source branch. | 元のブランチを追いかける写し。 |
| Bootstrap | The first construction of an environment. | 環境を最初に組み立てること。 |
| CI | Checks that run automatically after changes. | 変更後に自動で動く検査。 |
| JSON / TOON | Structured text data and its compact notation. | 構造のある文字データとその短い表記。 |
| QAE | Quality Assurance Engineer. | QA担当。 |
