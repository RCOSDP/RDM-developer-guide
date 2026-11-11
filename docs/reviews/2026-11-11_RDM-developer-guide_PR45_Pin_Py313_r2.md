# REV-45-r2 Python 3.13 pin re-review / Python 3.13 固定版再レビュー

> **Summary:** Changes requested for the altered r1 review record. R1-01, R1-02 and R1-03 are resolved; exact package matching and the unchanged rescan totals were independently verified.
> **概要:** r1 レビュー記録の改変について要修正。R1-01・R1-02・R1-03 は解消し、厳密なパッケージ照合と再検査の件数が変わらないことを独立に確認した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-11. **Learned:** REV changed only link destinations for publication (scratch-path evidence links replaced by repository-relative links or by plain-text references). ／ REV が公開用にリンク参照先のみを変更した（scratch パスの証跡リンクをリポジトリ相対リンクまたは平文参照に変更）。
- Publication provenance / 公開版の来歴: REV（担当レビュワ）issued this publication version from the unchanged original `/private/tmp/claude-501/-Users-komiyama-ai-development-GitHub-RDM-developer-guide/8baac84b-080f-4104-a2b5-7416702c57e1/scratchpad/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r2.md` (SHA-256: `a8bb94067af6b27028cbb7d111c5bd30fae9385dc9c1ca2d4681951fec11030f`); the original file and scratch evidence remain unchanged, and all text other than this version/provenance metadata and the explicitly stated publication references is verbatim. For r2, its existing repository-relative links already resolve and require no changes. ／ REV が上記原本から公開版を発行した。原本と scratch 証跡は未変更で、版・来歴の追記と明示した公開用参照以外の本文は原文どおり。r2 の既存のリポジトリ相対リンクは有効で変更不要。
- Version / 版: 0.1 — 2026-11-11. **Learned:** passing a link checker does not establish that a review record is verbatim; publication corrections require the reviewer's explicit provenance, even when the verdict is unchanged. ／ リンク検査の合格はレビュー記録が原文どおりであることを証明しない。判定が同じでも、公開用の訂正にはレビュワによる明示的な来歴が必要である。
- Applies to: RCOSDP/RDM-developer-guide [PR #45](https://github.com/RCOSDP/RDM-developer-guide/pull/45), head `339f4fa1e7415b82aaee61d090e3620c49047000`; delta after `3c5dd0c31944b9b3450ff34eb0808ad1e26f8728`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Posted review / 投稿: [PR comment](https://github.com/RCOSDP/RDM-developer-guide/pull/45#issuecomment-6798749424).
- Related: [review index](README.md), [r1 repository copy under review](2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md), [SPEC-03](../spec/03_security_gate.md), [SPEC-06 §8](../spec/06_documentation_conventions.md#english), [DEMO-20](../demo/20_core_install_mac_studio.md).
- Used by: [status board](../status/README.md) and the coordinator's PR #45 correction decision.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** The code and the three r1 findings pass this round. R2-01 remains a documentation-integrity blocker. This verdict is delivered as one PR comment, not a GitHub approval or request-changes review submission.

Reviewed the one new commit, `339f4fa`, in a fresh detached clone at `scratchpad/pr45-rev-r2`. Read the PR description through `gh` and the dated local scan reports. No source edits, commit, push, merge, approval, issue closure, live acceptance run or Docker state change was performed. The live `runtime/.env` was not accessed. The four requested checks used PATH system `python3`, `/opt/homebrew/bin/python3` 3.15.2, without a virtual environment. The clone remains clean.

### R2-01 — Medium: the imported r1 is not the reviewer's verbatim record

Location: `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md:12,55,127`; rule: `docs/spec/06_documentation_conventions.md:100,189` (§8).

Compared the committed copy directly with the original r1 in the coordinator's scratch review directory. There are three changed lines affecting nine link occurrences: five Related destinations were rebased, while four audit JSON/script links in the English and Japanese bodies were removed and changed to inline code. Thus “only nine link destinations” understates the change: four are no longer links. The findings and verdict are unchanged, but the Markdown record is not verbatim. It retains the same reviewer attribution and version 0.1 without a reviewer-authored publication correction.

SPEC-06 says review records “are kept verbatim.” Its exception covers only glossary warnings; it explicitly continues to check links. A successful `docs_check` therefore neither authorizes an author to edit a review nor proves compliance with the verbatim rule. The author disclosed the change in the commit and PR text, which is useful provenance, but it does not substitute for the reviewer's correction. I do not ratify this altered r1 as my original record.

**Required handling:** preserve the original r1 unchanged, with its original audit JSON and script available as evidence. Resolve the publication problem separately: ask REV to issue an explicitly versioned publication correction/addendum with repository-valid references and the original's identity/hash, and import that reviewer-issued text verbatim. A maintainer may add a separately attributed index or wrapper containing navigation and the relocation explanation; it must not masquerade as or overwrite r1. Do not delete evidence links, silently rewrite r1, or bypass the link check. If the original is placed under checked `docs/reviews/`, its original relative targets must genuinely resolve; otherwise retain it unchanged in an archival artifact and link the separate reviewer-issued publication record to that artifact. This report records the defect; it does not replace or amend r1.

SHA-256 comparison (full original and copied files):

```toon
r1_hashes:
  original: 7fc95a749e802996d83147b4c6b66c1403eff0ea4571d41287a7ad571e5e2a13
  repository_copy: 97b608128c5eacbe91e583ea661c5a2dd7f4632a76a3372980f3b2e2b8060326
```

### Closure of the r1 findings

| Finding | Assessment |
|---|---|
| R1-01, exact no-fix package scope | Resolved. `normalize_trivy` preserves package name, installed version, fix, status and class. `_entry_matches` requires the same CVE, one exact listed `name@version`, the named image's OS class, an empty `FixedVersion` and an allowed no-fix status. A fix, unknown status/class, different name/version, sibling image or language package stays open. Validation rejects wildcard entries and image entries without exact packages. Internal metadata is stripped from public findings. |
| R1-02, status board | Resolved in both languages. The row is now unmet, preserves historical counts, states 58 entries versus unchanged baseline 0, distinguishes M1 report-only from M2, and leaves the owner ceiling decision open. The cited earlier scan has the same counts as the rescan. |
| R1-03, provenance | Resolved. DEMO-20 distinguishes wiki `5985d18b` from osf.io base `8fc45de4` and combined tag `8fc45de461fd-5985d18b75da`; version 0.17 now limits unchanged totals to Trivy and states the extra ZAP MEDIUM. Manifest notes and all allow-list reasons separate the 2026-11-10 owner decision from 2026-11-11 application/addition. The current PR body has MFR `9771b8cf`, 12/12 acceptance and the successful rescan. |

Replayed all raw Trivy reports from both `20261111T132241Z` and `20261111T141449Z` through the committed normalizer and matcher. Each set yields 177 accepted findings using all 58 entries: WaterButler 47 HIGH, MFR 3 CRITICAL and 127 HIGH. Every match is an exact listed package and an `os-pkgs` / `debian` result with no fixed version. For every accepted finding, ten independent mutations (published fix, fixed/unknown status, language/missing class, sibling/unrelated package, changed version, sibling/other image) were rejected: 1,770 negative checks per report set, 3,540 total. The original r1 script was preserved; the r2 audit uses the normalizer because the new matcher deliberately rejects bare Trivy findings without metadata.

### Rescan evidence and limits

`scan_20261111T141804Z.json` matches the earlier `scan_20261111T132607Z.json` on totals, severity counts, allow-list counts, baseline and gate. Its findings array independently recounts to the summary. All scanners are `ok`; baseline and M1 report-only gate pass, exit 0. The report bundle contains the identical scan object and says `overall: complete`.

```toon
rescan:
  open_total: 10984
  critical: 726
  high: 3782
  medium: 4148
  low: 2322
  info: 6
  accepted_findings: 177
  allowlist_entries: 58
  baseline_entries: 0
  gate: M1 report-only pass
  exit_code: 0
```

This is stored evidence plus independent replay, not a new live scan. The rescan's `commit` field is `3c5dd0c`, reflecting execution before the fix commit; it cannot alone establish exact source provenance for `339f4fa`. The independent replay and unit tests establish the committed matcher's behavior. No claim is made that the report bundle's older plan is a fresh deployment inventory. The owner still needs to settle the ceiling and next-milestone expiry boundary; the API v2/ember preview remains an explicitly separate open item.

### Independent checks and artifacts

Commands run from `scratchpad/pr45-rev-r2`; all exited 0:

```sh
PYTHONPATH=installer python3 -m unittest discover -s installer/tests
python3 -m unittest discover -s tools/tests
python3 tools/docs_check.py
python3 tools/manifest_check.py
PYTHONPATH=installer python3 ../reviews/pr45-r2-audit.py
```

| Check | Result | Exit |
|---|---|---:|
| Installer tests | 655 tests, OK, 10 skipped | 0 |
| Tools tests | 93 tests, OK | 0 |
| docs_check | 155 checked, 8 exempt, 38 warnings | 0 |
| manifest_check | Passed | 0 |
| Independent replay and mutations | 58/58 entries, 177 findings in each set; all 3,540 mutations rejected | 0 |

The installer suite emits the existing Control Center port 5000 warning and Python 3.15 fork deprecation warning. Logs are saved beside this scratch report as `pr45-r2-installer.log`, `pr45-r2-tools.log`, `pr45-r2-docs.log`, `pr45-r2-manifest.log` and `pr45-r2-audit.log`. The audit script/JSON are `pr45-r2-audit.py` / `pr45-r2-audit.json`; the JSON includes input SHA-256 hashes and each match. `pr45-r2-r1-copy.diff` records the exact r1 differences. These scratch artifacts are not claimed to be committed. This r2's relative links are authored for its intended `docs/reviews/` destination and checked in that context; retain its text verbatim on publication.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**要修正（changes requested）。** コードと r1 の3指摘は今回合格。文書の完全性に関する R2-01 が残る。GitHub の承認・変更要求レビューではなく、PR コメント1件で判定を伝える。

新規の detached クローン `scratchpad/pr45-rev-r2` で、追加コミット `339f4fa` だけを確認した。`gh` で PR 本文、本体の保存済み日付付き報告を読み取った。ソース編集、コミット、push、マージ、承認、Issue 終了、実機受入、Docker 状態変更は行っていない。実スタックの `runtime/.env` は読んでいない。指定4検査は仮想環境を使わず PATH の system `python3`（`/opt/homebrew/bin/python3` 3.15.2）で実行し、クローンは変更なし。

### R2-01 — 中: 収録した r1 がレビュワの原文でない

対象: `docs/reviews/2026-11-11_RDM-developer-guide_PR45_Pin_Py313_r1.md:12,55,127`。規則: `docs/spec/06_documentation_conventions.md:100,189`（§8）。

調整役の scratch レビュー置き場にある元の r1 と直接比較した。変更は3行・リンク9か所で、Related の5リンクを付け替え、英和の監査 JSON／スクリプトへの4リンクを削除してインラインコードにしている。したがって「リンク先9か所だけ」より広く、4か所はリンク自体が無くなっている。指摘・判定は同じでも Markdown 原文は一致しない。レビュワ名・版0.1はそのままで、レビュワによる公開用訂正の記録もない。

SPEC-06 は「原文のまま残す」と定める。例外は用語注警告だけで、リンクは引き続き検査する。`docs_check` の合格は、作者によるレビューの編集を許可せず、原文保存の遵守も証明しない。作者がコミットと PR 本文で変更を明示したのは有用だが、レビュワ自身の訂正の代わりにはならない。この改変版を私の原本として追認しない。

**正しい扱い:** 元の r1 を変更せず保存し、元の監査 JSON とスクリプトも証跡として参照可能にする。公開用の問題は別に扱い、REV に、版・訂正理由・原本の識別情報／ハッシュ・リポジトリ内で有効な参照先を備えた公開用訂正版または追補を発行してもらい、その発行済み原文をそのまま取り込む。作者は別署名の索引・案内文に移設理由や導線を追加できるが、r1 本体と偽ったり上書きしたりしない。証跡リンクの削除、黙った書換え、リンク検査の回避はしない。原本を検査対象の `docs/reviews/` に置くなら原文の相対参照先も実在させる必要があり、それができなければ原本を変更しない保管成果物として残し、レビュワ発行の公開記録から参照する。今回の r2 は不備を記録するもので、r1 を訂正・置換してはいない。

原本 SHA-256 は `7fc95a749e802996d83147b4c6b66c1403eff0ea4571d41287a7ad571e5e2a13`、収録版は `97b608128c5eacbe91e583ea661c5a2dd7f4632a76a3372980f3b2e2b8060326` で異なる。

### r1 指摘の解消

| 指摘 | 判定 |
|---|---|
| R1-01、修正版なしの厳密な照合 | 解消。正規化で名前・導入版・修正版・状態・分類を保持し、同じ CVE、一覧中の正確な `name@version`、指定イメージの OS 分類、空の `FixedVersion`、許容された修正版なしの状態を求める。修正版あり、状態／分類不明、別名／別版、似た別イメージ、言語パッケージは未許容。ワイルドカードや正確な packages のない image 項目を不正とし、内部メタデータは公開報告から除く。 |
| R1-02、進捗表 | 英和とも解消。未達に直し、履歴を残して現行58項目と未変更の上限0を明示し、M1報告のみとM2を区別して、所有者の上限判断を残件にした。参照する前回報告の件数は再検査と同じ。 |
| R1-03、来歴 | 解消。DEMO-20 は wiki `5985d18b`、osf.io 基底 `8fc45de4`、結合タグを区別し、0.17 は Trivy の件数不変に限定して ZAP MEDIUM 1件増を明記。manifest の注記と許容理由全件は判断日2026-11-10と反映／追加日2026-11-11を区別。現在の PR 本文も MFR `9771b8cf`、受入12/12、再検査成功へ更新済み。 |

旧 `20261111T132241Z`・新 `20261111T141449Z` の Trivy 生報告全件をコミット済みの正規化・照合処理へ通した。両方とも58項目すべてを使って177件を許容し、WB は HIGH 47、MFR は CRITICAL 3・HIGH 127。すべて一覧と名前・版が一致し、`os-pkgs` / `debian`、修正版なしだった。各177件について10種類の変更（修正版あり、fixed／不明状態、言語／欠落分類、似た／無関係なパッケージ、別版、似た／別イメージ）を個別に与え、各報告1,770件、合計3,540件すべてを拒否した。元の r1 スクリプトは変更していない。新しい照合はメタデータのない Trivy 検出を意図的に拒否するため、r2 の監査は正規化処理を使う。

### 再検査の証跡と限界

`scan_20261111T141804Z.json` は前の `scan_20261111T132607Z.json` と合計・重要度別件数・許容件数・上限・門が一致する。検出配列の再集計も概要と一致した。未許容10,984件、CRITICAL/HIGH/MEDIUM/LOW/INFO は726/3782/4148/2322/6、別途177件許容、58項目、上限0。全スキャナー ok、基本対策と M1 報告のみの門は合格、終了0。report の bundle 内の scan は同一で、全体は complete。

保存証跡と独立再計算による確認であり、新しい実機スキャンではない。再検査の `commit` は `3c5dd0c` で、修正コミットより前の実行を示すため、この欄だけでは `339f4fa` の厳密なソース来歴を証明できない。コミット済み処理の挙動は独立再計算と単体試験で確認した。report bundle に含まれる古い plan を最新の配備一覧とは扱わない。上限と次の節目までの有効期限の境界は引き続き所有者の判断事項で、API v2/ember のプレビューは明記された別の残件である。

### 独立検査と成果物

英語版の5コマンドを `scratchpad/pr45-rev-r2` で実行し、終了コードを確認した。

| 検査 | 結果 | 終了 |
|---|---|---:|
| installer 単体試験 | 655件、OK、skip 10件 | 0 |
| tools 単体試験 | 93件、OK | 0 |
| docs_check | 155件検査、8件免除、38警告 | 0 |
| manifest_check | 合格 | 0 |
| 独立再計算・変更試験 | 両報告で58/58項目・177件、3,540変更すべて拒否 | 0 |

installer 試験は既存の Control Center 5000番ポート警告と Python 3.15 の fork 非推奨警告を出す。隣に `pr45-r2-installer.log`、`pr45-r2-tools.log`、`pr45-r2-docs.log`、`pr45-r2-manifest.log`、`pr45-r2-audit.log` を保存した。監査は `pr45-r2-audit.py`／`pr45-r2-audit.json` で、JSON に入力 SHA-256 と全照合を記録した。`pr45-r2-r1-copy.diff` は r1 の正確な差分。これらは scratch 成果物で、コミット済みとはしていない。r2 の相対リンクは予定の配置先 `docs/reviews/` 用にレビュワが作成し、その文脈で検査した。収録時はこの原文を維持する。
