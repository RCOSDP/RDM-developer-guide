# REV PR #27 Legacy ports review r2 / 旧変更の移植レビュー r2

> **Summary:** Accept the documented single-value substitution as a fidelity exception, but keep R1 open because the new exception can suppress other findings on the same line.
> **概要:** 明記された一つの値の置換は忠実性の例外として受け入れる。ただし新しい除外規則が同じ行の別の検出まで抑制し得るため、R1 は未解決とする。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** an exact public value used as a substring exception can still suppress unrelated findings when matching whole lines. ／ 公開値だけを指定しても、行を対象とした部分一致の除外では同じ行の別の検出まで抑制し得る。
- Applies to: [PR #27](https://github.com/RCOSDP/RDM-developer-guide/pull/27) (a proposed change), head (reviewed revision) `5bbd815bca91dfcd0eb75f28df6de73351334429` (including the replacement in `55c935f`).
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR27_Legacy_Ports_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Request changes — R1 / P2 remains open.** P2 denotes a normal-priority correction required before acceptance. The fidelity exception is acceptable; the security-check correction is incomplete. A concise r2 comment accompanies this report; no approval was submitted.

### Fidelity of the replacement

The replacement commit `55c935f` changes only the storage legacy guide and its bilingual wrapper. I fetched the new files through `gh` and verified that the supplied worktree (separate working copy) contains those exact bytes. Against the original source at `f65fac76da40674a15e39163c9f2331572fd1535`, the legacy guide equals exactly one substitution of the `recaptchaSiteKey` string value with `<recaptcha-site-key>`. No other source text differs. Its new size is 55,773 bytes; SHA-256 (a fingerprint of file contents) is `a20b29b7a9dd06ee527c21ba6de15b38b63889f3183c28e382b0ab7efe7a53c6`.

The change preserves the original authorship and describes the exception in both language halves. Consequently, describe the result as “faithful except for the documented site-key placeholder,” not byte-identical to the source. The nine assets, removed samples, other two source changes and supersession explanation were unchanged since r1; those earlier checks still apply. The placeholder is not a usable site key and requires a suitable value before anyone follows that legacy setup; this review does not establish runtime behavior.

### R1: constrain the new history exception to the complete field line

During review, the head advanced from `55c935f` to `5bbd815`. The latest revision adds a public-test-key exception and cites Google's FAQ in `.gitleaks.toml:28–31`. The [full-history secret scan now passes](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42104638730/job/127516113691). The earlier historical scan failure is therefore addressed, but the exception is broader than requested in r1.

The configuration uses `regexTarget = "line"`, while the new expression is only the literal test value, without anchors or a field name. Consequently, any detected secret on any source line containing that public value can be allowlisted. I parsed the remote configuration and confirmed that its expression also matches a synthetic JSON (structured text with named fields) line with both the public site-key field and an unrelated `other_secret` field. This verifies the matching weakness without using a real secret; it is not a fresh scanner execution.

Replace the substring exception with a complete-line expression restricted to the JSON `recaptchaSiteKey` field and that exact public value, allowing only indentation and the expected trailing comma. Keep the source explanation and default detection rules. This matches the existing configuration's explicit whole-line policy and the r1 requested correction. Rerun the full-history scan after that change. Do not exclude whole files or weaken scanning. The replacement alone in `55c935f` did not remove the original value from history; the additional exception in the latest head is what changed the scan result.

All eight hosted checks pass at `5bbd815`, including secret scanning, static analysis, the report-only filesystem scan, private-URL policy, documentation build, links and both unit-test versions. Passing checks do not test the overly broad exception described here.

### Document form and verification

The new explanation is bilingual and the existing anchors and Jump links remain. A minor SPEC-06 §6 issue is that the wrapper header stays at version 0.2 despite this separate edit; add a new learned-lesson version entry. Its “kept verbatim” wording should also explicitly allow the documented placeholder exception. These editorial notes do not change the single-value fidelity finding.

From the supplied worktree root, the following command completed with PASS: 73 checked files, 8 exemptions and 197 glossary warnings, the same counts as r1.

```sh
python3 tools/docs_check.py --all-warnings
```

The replacement files and unchanged workflow were verified at `55c935f`; the subsequent comparison and new scanner configuration were read at `5bbd815`. The latest revision also records r1 in the review folder. No application services were run. No commits, pushes, approvals, merges, closures or container-state changes were made. Remaining work is to narrow the exception, repeat the scan, correct the small document-form notes and request re-review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**修正要求 — R1 / P2 は未解決。** P2 は受入前に必要な通常優先度の修正を表す。忠実性の例外は受け入れるが、秘密情報検査の修正は未完了である。この報告に対応する短い r2 コメントを投稿し、承認操作は行っていない。

### 置換の忠実性

置換コミット `55c935f` では、ストレージの旧本文と英和の案内だけが変わっている。`gh` で新しいファイルを取得し、指定された作業ツリー（別の作業用コピー）とバイト単位で一致することを確認した。元の `f65fac76da40674a15e39163c9f2331572fd1535` の本文と比べると、`recaptchaSiteKey` の文字列値を `<recaptcha-site-key>` に置き換えた一か所だけが異なる。それ以外の原文は同一である。新しい大きさは55,773バイト、SHA-256（ファイル内容の指紋）は `a20b29b7a9dd06ee527c21ba6de15b38b63889f3183c28e382b0ab7efe7a53c6`。

元の作者表記を保ち、例外を両言語で説明している。このため「明記したサイトキーの代替文字列を除いて忠実」と評価できるが、「原文とバイト単位で一致」とは評価できない。素材9点、サンプル削除、他の二つの変更元、後の改訂による置換説明は r1 以降変更されておらず、前回の確認が引き続き適用される。代替文字列は利用できるサイトキーではなく、旧設定を実行するには適切な値への置換が必要である。実行時の動作は今回検証していない。

### R1: 履歴用の新しい除外をフィールド行全体に限定する

レビュー中に head が `55c935f` から `5bbd815` へ更新された。最新版は `.gitleaks.toml:28–31` に公開テストキーの除外と Google の FAQ の出典を追加し、[全履歴の秘密情報検査は合格した](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42104638730/job/127516113691)。前の履歴検査失敗には対処しているが、除外範囲は r1 の要求より広い。

設定は `regexTarget = "line"` で行を対象とする一方、新しい式はテスト値の文字列だけで、行頭・行末の指定やフィールド名がない。そのため、その公開値を含む任意のソース行では別の秘密情報の検出も除外され得る。遠隔の設定を読み取り、公開サイトキー欄と無関係な `other_secret` 欄を一行に含めた人工的な JSON でも、この式が一致することを確認した。実際の秘密情報を使わずに一致範囲の問題を確認したもので、検査ツールそのものの再実行ではない。

この部分一致の除外を、JSON の `recaptchaSiteKey` フィールドとその公開値だけに限定した行全体の式へ変更すること。字下げと必要な末尾のカンマ以外の追加内容は許さない。出典の説明と既定の検出規則は維持する。これは設定内の既存の行全体方針および r1 の要求に沿う。変更後に全履歴検査を再実行すること。ファイル全体の除外や走査の縮小は行わない。`55c935f` の置換だけでは元の値は履歴から消えず、最新版の追加除外によって検査結果が変わった点も区別する。

`5bbd815` の遠隔検査は8本すべて合格した。秘密情報検査、静的解析、報告専用のファイル検査、非公開 URL 方針、文書ビルド、リンク、二つの版での単体テストを含む。ただし合格した検査は、ここで指摘した除外範囲の広さを検証していない。

### 文書の形式と検証

追記の説明は英和で対応し、既存のアンカーと Jump リンクも維持する。軽微な SPEC-06 §6 の問題として、別の編集を加えたのに案内の版は0.2のままなので、学びを示す新しい版の行を追加すること。「そのまま保存」という表現にも、明記された代替文字列の例外を反映するとよい。これらの文章上の指摘は、一つの値だけが異なるという忠実性の判断を変えない。

指定された作業ツリーのルートで次を実行し、73件検査・8件対象外・用語警告197件で PASS した。件数は r1 と同じである。

```sh
python3 tools/docs_check.py --all-warnings
```

置換ファイルと不変の実行定義は `55c935f` で照合し、その後の差分と新しい検査設定は `5bbd815` で確認した。最新版は r1 の報告書もレビュー用フォルダに追加している。アプリケーションのサービスは起動していない。コミット・プッシュ・承認・マージ・終了処理・コンテナ状態変更も行っていない。除外範囲の限定、検査の再実行、軽微な文書形式の修正、再レビューの依頼が残る。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Placeholder | Text that must be replaced with a suitable value. | 適切な値に置き換えて使う仮の文字列。 |
| Fidelity exception | An explicitly recorded difference from the source. | 原文との違いを明記して認めること。 |
| Ancestor | An earlier saved revision included in later history. | 後の履歴に含まれる、過去に保存された版。 |
