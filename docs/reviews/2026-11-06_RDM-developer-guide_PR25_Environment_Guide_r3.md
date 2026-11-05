# REV Environment guide review r3 / 環境ガイドレビュー r3

> **Summary:** The two requested milestone thresholds are corrected in both languages, but the gate explanation still omits mandatory validity and red-team conditions. Changes requested; first-use notes remain a minor issue.
> **概要:** 指摘した二つの段階別しきい値は日英とも修正されたが、門の説明には必須のデータ有効性・攻撃検証の条件が残る。修正要求。初出注も軽微な残件。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** correct severity thresholds alone do not describe all mandatory gate conditions, and a passing text checker does not prove first-use placement or translation parity. ／ 重大度のしきい値だけ正しくても必須条件を網羅できず、文書検査の成功だけでは初出位置と翻訳の対応を証明できないと分かった。
- Applies to: [PR #25](https://github.com/RCOSDP/RDM-developer-guide/pull/25) (a proposed change / 変更提案), revision `8b73ff0615dbdd5c5705c534bfb89de1870cd557`; reviewer REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2 record](2026-11-06_RDM-developer-guide_PR23_PR25_r2.md) · [SPEC-03](../spec/03_security_gate.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Environment guide](../guides/environment/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and evidence

**Changes requested (P2: correct before acceptance).** The security gate (the checkpoint deciding whether a run passes) in guide §3.8, lines 213 and 568, now names both HIGH and CRITICAL (two levels of weakness severity) at M4 and the non-increasing allow-list (temporary accepted findings) count. These two parts of R2-25-01 are resolved and agree between English and Japanese and with SPEC-03 §5 / ADR-03 §3.

**R3-25-01 / P2 — Complete the remaining gate conditions in both paragraphs.** R2-25-01 explicitly requested a validity condition, which is still absent. SPEC-03 §5.1 rule 1 requires malformed entries to fail with exit 50 even at M1; `installer/grdm_dev/scan.py:868–881` also rejects unreadable gate data. Qualify early-stage exit 0 on valid gate data and passing baseline controls. State that count enforcement starts at M2 (SPEC-03 §5.2; `scan.py:52–57,881`), rather than making the current M1 count behavior ambiguous. Also distinguish the AI red team (authorized attack testing of an isolated system) from its preflight (a readiness check): SPEC-03 §5.2 requires an actual first run and fixed or accepted paths at M4, and zero unresolved intrusion paths plus no HIGH/CRITICAL allow-list entries at M5; ADR-03 §3.5 confirms the M5 requirements. The guide mentions only a passing M5 preflight and current findings, which cannot establish those outcomes. Add the conditions or explicitly separate the implemented scan checks from milestone acceptance requirements.

**R2-25-02 / P3 (minor wording issue) remains.** The English body adds useful explanations for the requested terms, but profile and manifest are still unexplained at lines 34 / 389 (manifest also occurs in header line 8), with definitions deferred to lines 123 / 478. GakuNin (Japan's academic identity federation) and ember-osf-web (the browser interface) also occur in the header before the new body notes. Port (a numbered listening endpoint) first occurs at line 32, while its note appears at line 320 as the malformed phrase `Port (a numbered door a program listens on)s`. Container (a box holding a program and its dependencies) is explained at line 302, after earlier plural uses. Move notes to actual first use and fix that plural. Most added English explanations have no matching Japanese note; for example lines 24/379, 39/394, 48/403, 137/492 and 169/524. Operational gate wording has parity; explanatory notes do not yet have full parity under SPEC-06 §2–3.

### Validation and limits

The local guide was byte-compared with the remote file at the reviewed revision using `gh api` and matched. Remote access used `gh` only. Run from `/Users/komiyama/orca/workspaces/RDM-developer-guide/docs-env-guide`:

```sh
python3 tools/docs_check.py --all-warnings
```

Before adding this record: **PASSED**, 60 files checked, 8 exempt, 158 warnings. Exactly two warnings remain for the guide: line 34, `Docker` (the tool that runs program containers), and line 318, `Port`. These are checker results, not a complete inventory of first-use issues; the checker examines the English half with a heuristic.

```sh
gh pr checks 25 --repo RCOSDP/RDM-developer-guide
```

All six CI (automatic checks on submitted changes) checks passed: site build, links, manifest/private-URL policy, secret scan, static analysis, and filesystem vulnerability scan. Evidence: [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098734680) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098734830). No live installation, scan, attack test, or container state change was performed. This verdict is a review recommendation, not a platform approval; no approval, merge, close, commit or push was performed.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と根拠

**修正要求（P2：採用前に修正）。** ガイド §3.8、213 / 568 行のセキュリティ門（実行を合格にするか判断する検査）は、M4 の HIGH と CRITICAL（弱点の重大さの二段階）、許容リスト（一時的に認めた検出の一覧）の件数非増加を明記した。R2-25-01 のこの二点は解消し、英和および SPEC-03 §5 / ADR-03 §3 と整合する。

**R3-25-01 / P2 — 両段落に残る門の必須条件を補完する。** R2-25-01 が明示的に求めたデータ有効性の条件は未記載。SPEC-03 §5.1 第1項は不正な項目を M1 でも終了50とし、`installer/grdm_dev/scan.py:868–881` も読めない門データを拒否する。初期段階の終了0を、データが有効で基本対策に合格した場合に限定する。件数の強制は M2 からと明記し、現行 M1 の動作を曖昧にしない（SPEC-03 §5.2、`scan.py:52–57,881`）。さらに AI レッドチーム（隔離環境で許可を受けて行う攻撃検証）と事前確認（実施準備の検査）を区別する。SPEC-03 §5.2 は M4 で初回の実検証と発見経路の修正または許容、M5 で未解決侵入経路ゼロと HIGH/CRITICAL の許容項目ゼロを要求し、ADR-03 §3.5 も M5 の条件を確認している。ガイドは M5 の事前確認合格と現在の検出だけを挙げ、それだけでは要求結果を証明できない。条件を補記するか、実装済み scan の検査と節目の受入条件を明確に分ける。

**R2-25-02 / P3（軽微な文言課題）は継続。** 英語本文の用語説明は増えたが、34 / 389 行の profile・manifest は未説明（manifest はヘッダ8行にも登場）で、定義は123 / 478行までない。GakuNin（日本の学術認証連携）と ember-osf-web（ブラウザ画面）も本文注より前にヘッダに登場する。Port（プログラムが待ち受ける番号）は32行が初出だが、320行の注は `Port (a numbered door a program listens on)s` と不自然な複数形になっている。Container（プログラムと必要なものを入れる箱）の説明は302行で、それ以前に複数形がある。実際の初出へ移し、複数形を直す。追加された英語の注の多くは対応する日本語注を欠く（例：24/379、39/394、48/403、137/492、169/524行）。門の動作説明は英和一致するが、説明注は SPEC-06 §2–3 の完全な対応に至っていない。

### 検証と限界

指定作業コピーのガイドは、対象版のリモートファイルを `gh api` で取得し、バイト単位で一致した。リモート操作は `gh` のみ。英語側に示した作業ディレクトリで `python3 tools/docs_check.py --all-warnings` を実行し、この記録の追加前は **合格、60ファイル、8除外、158警告**。対象ガイドの警告は34行 `Docker`（プログラムの箱を動かす道具）、318行 `Port` の **2件**。これは検査器の結果であり、初出問題の全件数ではない。検査器は英語部分を簡易的な判定で調べる。

`gh pr checks 25 --repo RCOSDP/RDM-developer-guide` では CI（変更を自動検査する仕組み）の6件すべて成功。サイト生成、リンク、部品一覧・非公開URL方針、秘密検査、静的解析、ファイル脆弱性検査を確認した。証跡は [文書検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098734680) と [セキュリティ検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42098734830)。実導入・実スキャン・攻撃検証・コンテナ状態変更は未実施。判定はレビュー上の推奨であり、承認操作ではない。承認・マージ・閉鎖・commit・push は行っていない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Milestone | A numbered stage of the plan. | 計画の番号付きの節目。 |
| Baseline controls | Minimum protections required at every stage. | 全段階で必要な最低限の保護。 |
| Preflight | A readiness check before an actual test. | 実検証の前に準備を確認する検査。 |
| Parity | Both language versions convey the same information. | 両言語が同じ情報を伝えること。 |
