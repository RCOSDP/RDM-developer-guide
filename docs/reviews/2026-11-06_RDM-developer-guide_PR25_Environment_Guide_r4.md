# REV Environment guide review r4 / 環境ガイドレビュー r4

> **Summary:** The remaining gate conditions and the requested first-use explanations are corrected in both languages. No outstanding findings in this re-review; recommended for acceptance.
> **概要:** 残っていた門の条件と、指摘対象の初出説明は日英とも修正済み。今回の再レビューに残件はなく、採用を推奨する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** separating automated checks from recorded acceptance evidence makes the staged security requirements understandable without claiming that a readiness check performs attack testing. ／ 自動検査と記録による受入証跡を分けることで、準備確認が攻撃検証を実施するかのように説明せず、段階別の安全要件を伝えられると分かった。
- Applies to: [PR #25](https://github.com/RCOSDP/RDM-developer-guide/pull/25) (a proposed change / 変更提案), revision `5bf1e59b7c55ab46268475679e5e140c35a3db9f`; reviewer REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r3 record](2026-11-06_RDM-developer-guide_PR25_Environment_Guide_r3.md) · [SPEC-03](../spec/03_security_gate.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Environment guide](../guides/environment/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Recommended for acceptance; no outstanding findings in the requested re-review scope.** R3-25-01 and R2-25-02 are resolved. This is a review recommendation, not a platform approval or permission to merge.

### Gate conditions and language comparison

The security gate (a checkpoint deciding whether a run passes) in §3.8 was compared line by line, including commands, explanatory notes, success wording and failure codes: English lines 197–217 and Japanese lines 552–572. The paragraphs at 213 / 568 agree clause by clause with [SPEC-03 §5](../spec/03_security_gate.md#english) and [ADR-03 §3](../decisions/ADR-03_Staged_Security_Gate.md#english):

| Condition checked | Result in both languages |
|---|---|
| Validity at every milestone (numbered stage), including M1 | Unreadable gate data and an allow-list entry missing a required field cause exit 50. The allow-list is the written list of findings accepted temporarily. |
| Baseline controls (minimum protections) | Violations cause exit 50 at every milestone. |
| M1–M3 findings | Reporting without severity failure is conditional on valid data and passing baseline controls; the next sentence retains the count restriction. |
| Allow-list count | Non-increase starts at M2 against the recorded baseline; M1 reports the count. |
| M4 | Unlisted HIGH or CRITICAL findings fail; the first real AI red-team run (authorized attack testing of isolated targets) must finish, with every path fixed or allow-listed. |
| Preflight | A readiness and isolation check is explicitly distinct from the actual red-team run. |
| M5 | Any HIGH or CRITICAL finding fails even if allow-listed; no entries at those severity levels may remain, and there must be zero unresolved intrusion paths. |
| Enforcement boundary | The scan enforces validity, baseline, count and severity; the owner records M4 completion and M5 zero-path evidence separately for milestone acceptance. |

The implementation agrees: [`scan.py`](../../installer/grdm_dev/scan.py), lines 52–57 map the milestones, lines 865–897 decide the gate, and lines 961–997 validate entries, separate accepted findings, select the baseline count and choose the exit code. The M5 check includes both HIGH/CRITICAL entries and accepted HIGH/CRITICAL findings. Scanner failures still take exit 51 precedence and an explicit dynamic scan with unhealthy services takes exit 52; §3.8 lists those separate execution failures. No claim is made that a successful scan proves the red-team outcome.

### First-use notes

The requested notes now appear at their actual first prose use: GakuNin (Japan's academic identity federation) in header lines 3 / 4; ember-osf-web (browser interface), Docker (the tool running program containers), container (a box holding a program and its dependencies), and manifest (the component and source-version list) in bilingual header line 8; port (a numbered listening endpoint) at 32 / 387; and profile (a named group of services) at 34 / 389. The malformed plural in troubleshooting is now ordinary “Ports” at line 320, with equivalent Japanese at 675.

The added Japanese notes match English for amd64 (a CPU type) at 39 / 394, Docker Compose (starting multiple containers from one file) at 48 / 403, CAS (the sign-in mechanism) at 137 / 492, modular-file-renderer (file previews) at 169 / 524, Trivy (known-weakness scanning) at 205 / 560, and non-root (running without administrator powers) at 302 / 657. The related shared-glossary links and the remaining §3.8 explanations also agree. This closes the specific first-use placement and translation issues from r3; a checker pass alone was not used to establish that agreement.

### Validation and limits

The local guide, SPEC-03, ADR-03 and `scan.py` were byte-compared against the remote files at the reviewed revision, retrieved using `gh api`; all four matched. Remote operations used `gh` only. From `/Users/komiyama/orca/workspaces/RDM-developer-guide/docs-env-guide`:

```sh
python3 tools/docs_check.py --all-warnings
gh pr checks 25 --repo RCOSDP/RDM-developer-guide
```

Before adding this record, the documentation check **passed: 61 files checked, 8 exempt, 156 warnings repository-wide, zero warnings for the guide**. All six CI (automatic checks on submitted changes) checks passed: site build, links, manifest/private-URL policy, secret scan, static analysis and filesystem vulnerability scan. Evidence: [documentation run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42100584655) and [security run](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42100584538).

The new, untracked review record was checked directly with `tools.docs_check.check_file` and `load_glossary_terms`: zero errors and zero warnings. The normal command only enumerates tracked files.

No live installation, scan, attack test or container state change was performed. Full startup remains unverified, as the guide already states. No approval, merge, close, commit or push was performed; the review record is left locally for the coordinator to integrate.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**採用推奨。指定された再レビュー範囲に残件なし。** R3-25-01 と R2-25-02 は解消した。これはレビュー上の推奨であり、プラットフォーム上の承認操作やマージ許可ではない。

### 門の条件と英和比較

§3.8 のセキュリティ門（実行の合否を判断する検査）を、コマンド・説明注・成功時の記述・失敗コードも含めて行ごとに比較した。英語197〜217行と日本語552〜572行が対象。213 / 568行の段落は節ごとに対応し、[SPEC-03 §5](../spec/03_security_gate.md#japanese) と [ADR-03 §3](../decisions/ADR-03_Staged_Security_Gate.md#japanese) に整合する。

| 確認条件 | 両言語での結果 |
|---|---|
| M1 を含む全節目（計画の番号付き段階）の有効性 | 読めない門データ、必須欄を欠く許容リスト項目は終了50。許容リストは検出を期限付きで受け入れる一覧。 |
| 基本対策（最低限の保護） | 違反は全節目で終了50。 |
| M1〜M3 の検出 | データ有効・基本対策合格を条件に、重大度による失敗なしで報告する。次の文で件数制約も維持する。 |
| 許容リスト件数 | 記録した基準からの非増加を M2 から要求し、M1 は件数報告のみ。 |
| M4 | 未許容の HIGH・CRITICAL は失敗。初回の実際の AI レッドチーム（隔離対象への許可された攻撃検証）を完了し、全経路を修正か許容登録する。 |
| 事前確認 | 準備と隔離の検査であり、実際の攻撃検証とは明確に区別する。 |
| M5 | 許容済みでも HIGH・CRITICAL の検出は失敗。その重大度の許容項目を残さず、未解決侵入経路もゼロにする。 |
| 強制範囲 | scan が有効性・基本対策・件数・重大度を検査し、所有者が M4 完了と M5 経路ゼロの証跡を節目受入のため別途記録する。 |

実装も一致する。[`scan.py`](../../installer/grdm_dev/scan.py) の52〜57行が段階を対応付け、865〜897行が門を判定し、961〜997行が項目検証・許容済み検出の分離・基準件数選択・終了コード決定を行う。M5 の検査は HIGH・CRITICAL の許容項目と許容済み検出の両方を含む。スキャナー実行失敗では終了51が優先し、明示的な動的検査でサービスが不健康なら終了52になる。§3.8 はこれら実行上の失敗を別に示している。scan 成功が攻撃検証の結果を証明するという記述はない。

### 初出注

指摘対象の注は実際の本文初出に移った。GakuNin（日本の学術認証連携）はヘッダ3 / 4行、ember-osf-web（ブラウザ画面）・Docker（プログラムの箱を動かす道具）・コンテナ（プログラムと必要なものを入れる箱）・manifest（部品とソース版の一覧）は二言語のヘッダ8行、ポート（待受の番号）は32 / 387行、プロファイル（サービスの名前付きの組）は34 / 389行。トラブルシューティングの不自然な複数形は320行で通常の “Ports” に修正され、日本語675行と対応する。

日本語の追加注は、amd64（CPU の種類）39 / 394行、Docker Compose（複数の箱を一つのファイルから起こす道具）48 / 403行、CAS（サインインの仕組み）137 / 492行、modular-file-renderer（ファイルのプレビュー）169 / 524行、Trivy（既知の弱点の検査）205 / 560行、非 root（管理者権限で動かさない）302 / 657行で英語と一致する。関連する共通用語集リンクと §3.8 の残りの説明も対応する。r3 の初出位置・翻訳の具体的な指摘は解消した。この一致の判定は文書検査器の成功だけに頼っていない。

### 検証と限界

指定作業コピーのガイド・SPEC-03・ADR-03・`scan.py` を、`gh api` で取得した対象版のリモートファイルとバイト比較し、4件とも一致した。リモート操作は `gh` のみ。英語側に示したディレクトリで同じ二つのコマンドを実行した。

この記録の追加前の文書検査は **合格、61ファイル確認、8除外、リポジトリ全体156警告、対象ガイドは0警告**。CI（変更を自動検査する仕組み）はサイト生成・リンク・部品一覧と非公開URL方針・秘密検査・静的解析・ファイル脆弱性検査の6件すべて成功。証跡は [文書検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42100584655) と [セキュリティ検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42100584538)。

新規の未追跡レビュー記録は `tools.docs_check.check_file` と `load_glossary_terms` で直接検査し、エラー0・警告0。通常のコマンドは追跡済みファイルだけを列挙する。

実導入・実スキャン・攻撃検証・コンテナ状態変更は未実施。完全起動はガイドの既存記述どおり未検証。承認・マージ・閉鎖・commit・push は行っておらず、レビュー記録は取り込みを行う調整役のためローカルに残す。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Severity | How serious a weakness is; HIGH and CRITICAL are the two upper levels discussed here. | 弱点の重大さ。HIGH と CRITICAL はここで扱う上位二段階。 |
| Acceptance evidence | Recorded results used to decide whether a stage is complete. | 段階の完了を判断するために記録した結果。 |
| Parity | Both language versions convey the same information. | 両言語が同じ情報を伝えること。 |
