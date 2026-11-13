# PR40 Acceptance review r3 / 受入全件合格のレビュー r3

> **Summary:** Pass for the final Semgrep exclusion change. It documents a prose-only exception without removing executable sources or secret-scanning coverage.
> **概要:** 最終コミットの Semgrep 除外変更は合格。散文に限定した例外の理由があり、実行ソースや秘密情報検査の対象を減らしていない。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-10. **Learned:** generic source matching can flag verbatim review prose, so an exclusion must be judged separately from executable coverage and secret detection. ／ 汎用のソース照合は原文保存するレビューの散文も検出するため、除外は実行コードの網羅性と秘密情報検査を分けて評価する必要がある。
- Applies to: RCOSDP/RDM-developer-guide PR #40; REV（担当レビュワ, Codex Astra）; head `36ac2e4ae0110d2daef95ca31ce73f0f653700c7`; delta `8c9de2d..36ac2e4` only.
- Related: [Review index](README.md) · [Review r2](2026-11-10_RDM-developer-guide_PR40_Acceptance_All_Pass_r2.md) · [SPEC-03](../spec/03_security_gate.md) · [SPEC-06](../spec/06_documentation_conventions.md).
- Used by: [Status board](../status/README.md) · [DEMO-20](../demo/20_core_install_mac_studio.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Pass. No required changes in the reviewed delta.** The clean clone is `/tmp/rev-task_af4f588ae569/RDM-developer-guide`. The last commit changes only `.semgrepignore`: three reason lines and `docs/reviews/*.md`. The reason identifies verbatim review records, SPEC-06 §8 and generic matches of quoted WebSocket prose. SPEC-03 §4.2 targets source-code analysis; §3.5 separately requires blocking secret detection and reasoned false-positive handling. SPEC-06 preserves records verbatim; it is not itself blanket permission to disable scanners. This bounded exception is acceptable on the inspected content and independent secret coverage.

The failed parent security run `42742048792` reports exactly two insecure-WebSocket findings in r2 prose, at lines 34 and 84. These describe existing C4 annotations; they do not create connections. All 91 tracked files in `docs/reviews/` are Markdown, mode `100644`, with no symlinks or executable-mode files. A search found no script or iframe tags. The inspected installer, tools, workflows and MkDocs configuration show no path that executes these review records or their fenced snippets; MkDocs renders documentation. Executable Python, JavaScript, shell, workflow and template paths are outside the new pattern. Markdown is not intrinsically safe: adding executable embedded content or an execution mechanism here would require revisiting the exception.

Secret coverage remains independent. `.gitleaks.toml` enables default rules and has no path allowlist; the unchanged CI job scans full Git history. Trivy still includes its secret scanner and skips only `site`; it is report-only. The blocking private-URL/token policy scans all tracked text without path exemptions. The new Semgrep pattern does not affect these paths or configurations. Local `python3 tools/manifest_check.py --policy-only` passed: 659 scanned, 63 non-UTF-8 skipped, zero findings. This is policy validation, not a substitute for gitleaks.

### Narrower alternatives and evidence limits

An exact r2 filename would fix today's two findings with the smallest coverage loss. A dated `*_r*.md` pattern would also retain the review index. Either is a reasonable optional refinement, but not a required correction: the present directory is dedicated to review prose and the same immutable-record issue applies to subsequent rounds. Inline suppression would edit the preserved record. A rule-specific path exception would preserve other Semgrep checks but requires maintaining rule configuration around the remote packs. Disabling the WebSocket rule globally would weaken executable coverage and is worse. The existing directory-plus-extension boundary and explicit reason are proportionate; this is not an exception for secrets or future executable material.

GitHub reports security run `42743153258` successful at the exact reviewed head, including Semgrep, gitleaks, Trivy and the policy job. Docs and both unit-test jobs also passed; the image-build job was pending when inspected. This verdict is limited to the final exclusion change and does not assert that every PR job has finished. Semgrep and gitleaks were not rerun locally; CI evidence was read through `gh`. No Docker commands, live credential access, application edits, commits, pushes, approvals, merges or closures were performed. This record remains uncommitted, and one Japanese PR comment accompanies it.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**Pass（合格）。対象差分に必須修正なし。** クリーンクローンは `/tmp/rev-task_af4f588ae569/RDM-developer-guide`。最終コミットは `.semgrepignore` に理由三行と `docs/reviews/*.md` だけを追加する。理由は原文保存するレビュー記録、SPEC-06 §8、引用した WebSocket の散文への汎用照合を具体的に挙げる。SPEC-03 §4.2 はソースコードの静的解析を扱い、§3.5 は失敗を伴う秘密情報検査と理由付きの誤検出対応を別途要求する。SPEC-06 の原文保存規定そのものが検査の包括的無効化を許すわけではないが、確認した内容と独立した秘密情報検査に照らし、この限定例外は妥当。

親コミットの失敗した security 実行 `42742048792` は r2 の散文 34・84 行だけに平文 WebSocket の指摘二件を出している。既存の C4 抑止を説明する文章であり、接続を実行しない。`docs/reviews/` の追跡済み 91 ファイルはすべて Markdown、mode `100644` で、実行属性もシンボリックリンクもない。script・iframe タグは検索で見つからなかった。確認した installer・tools・workflow・MkDocs 設定に、記録やコードブロックを実行する経路はなく、MkDocs は文書を描画する。Python・JavaScript・shell・workflow・template の実行経路は新しいパターンの対象外。Markdown 自体が安全を保証するわけではなく、実行される埋込内容や実行機構を導入する際には例外の再評価が必要となる。

秘密情報検査は独立して維持される。`.gitleaks.toml` は既定規則を有効にし、パス単位の許容指定がなく、変更のない CI は Git 全履歴を検査する。Trivy も secret 検査を含み、除外は `site` だけで、報告のみの位置付け。失敗を伴う private URL/token ポリシー検査はパス例外なしで追跡済みテキストを調べる。新しい Semgrep パターンはこれらの設定・経路に影響しない。ローカルの `python3 tools/manifest_check.py --policy-only` は 659 件検査・非 UTF-8 の 63 件をスキップ・指摘ゼロで合格した。これはポリシー確認であり、gitleaks の代用ではない。

### より狭い代案と証拠の限界

r2 のファイル名を個別指定すれば、今日の二件に対する除外範囲は最小になる。日付付き `*_r*.md` に絞ればレビュー索引も検査に残せる。どちらも任意の改善として合理的だが、現在のディレクトリはレビューの散文専用で、以後の記録にも原文保存の事情が共通するため、必須修正ではない。行内の抑止追記は保存記録を書き換える。規則別のパス除外なら他の Semgrep 検査を残せる一方、遠隔の規則パックを扱う設定の保守が必要になる。WebSocket 規則の全体無効化は実行ソースの検査を弱めるため劣る。ディレクトリと拡張子を限定し理由を明示する現状は相応であり、秘密情報や将来の実行内容を許容する例外ではない。

GitHub の security 実行 `42743153258` は対象 head で成功し、Semgrep・gitleaks・Trivy・ポリシーの各 job が合格した。docs と単体試験の両 job も合格し、確認時のイメージビルドは pending だった。判定は最終の除外変更に限定し、全 PR job の完了を意味しない。Semgrep と gitleaks はローカルで再実行せず、CI の証拠を `gh` で読んだ。Docker 操作、稼働環境の資格情報参照、アプリ変更、commit・push・approve・merge・close は行っていない。記録は未コミットで、日本語 PR コメント一件を添える。
