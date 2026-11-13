# REV PR #27 Legacy ports review r3 / 旧変更の移植レビュー r3

> **Summary:** The narrowly anchored exception resolves R1. Accept the implementation with minor documentation notes, with all eight hosted checks passing on the reviewed revision.
> **概要:** 行全体に限定した除外により R1 は解決した。軽微な文書上の注記を残して実装を受け入れる。対象の版で遠隔検査8本すべての成功も確認した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** an exact field-and-value line exception preserves detection of additional fields on the same line. ／ フィールドと値を行全体で限定すれば、同じ行に追加された別の欄を除外しない。
- Applies to: [PR #27](https://github.com/RCOSDP/RDM-developer-guide/pull/27) (a proposed change), head (reviewed revision) `abc7689352e65e757d0284bb408c2cc43c246c7e`.
- Reviewer: REV（担当レビュワ, Codex Astra）.
- Related: [Review index](README.md) · [r2](2026-11-06_RDM-developer-guide_PR27_Legacy_Ports_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [Shared glossary](../reference/REF-01_Glossary.md).
- Used by: [Status board](../status/README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Accept with minor notes — R1 resolved; no remaining blocking implementation findings.** All eight hosted checks pass, including the [full-history secret scan](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42105028993/job/127517449360), documentation build, links, private-URL policy, static analysis, report-only filesystem scan and both unit-test versions. This is a written review verdict, not a submitted approval or a merge action.

### Verification

The remote `.gitleaks.toml` now restricts the exception to a complete `recaptchaSiteKey` field line containing the exact public test value, with optional indentation and trailing comma. Gitleaks (a tool that searches for possible secrets) still uses `regexTarget = "line"` and its default rules. The exception retains its public-source explanation and does not exempt a file or a class of keys.

I parsed the configuration fetched at the reviewed revision and tested all allowlist expressions against six synthetic lines. The original field with and without its comma matched. A different field name, a different value, an appended second field and a prepended second field did not match any allowlist expression. This independently verifies that the r2 same-line bypass is closed. It is a direct expression test, not an independent rerun of the coordinator's reported scanner exit-1 experiment.

The two storage guide files and scanner configuration in the supplied worktree (separate working copy) matched the remote revision byte for byte. The legacy text has not changed since r2: its only difference from source #18 remains the documented site-key placeholder. The English “verbatim” sentence now explicitly acknowledges that exception. Earlier image, deletion, attribution and other port checks remain applicable because those files are unchanged.

Run from the supplied worktree root; the observed result is PASS, 75 checked files, 8 exemptions and 197 glossary warnings:

```sh
python3 tools/docs_check.py --all-warnings
```

### Minor notes and limits

The Japanese “legacy content” sentence still says the original is preserved as-is, although its “latest changes” section explains the exception. Align that short sentence with the corrected English sentence when polishing the guide. The wrapper also remains at version 0.2; a new learned-lesson version entry would complete the SPEC-06 §6 follow-up noted in r2. Neither note affects the exact-value security correction or conceals the already bilingual substitution explanation.

Application services were not run. No commits, pushes, approvals, merges, closures or container-state changes were performed. The coordinator retains integration responsibility and should retain the passing hosted-check evidence for this revision.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**軽微な注記付きで受入可能 — R1 は解決、実装の阻害指摘は残らない。** 遠隔検査8本すべての合格を確認した。[全履歴の秘密情報検査](https://github.com/RCOSDP/RDM-developer-guide/actions/runs/42105028993/job/127517449360)、文書ビルド、リンク、非公開 URL 方針、静的解析、報告専用のファイル検査、二つの版の単体テストを含む。文書上の判定であり、承認やマージの操作ではない。

### 検証

遠隔の `.gitleaks.toml` は、公開テスト値そのものを持つ `recaptchaSiteKey` 欄の一行全体に除外を限定した。字下げと末尾のカンマだけを任意に許す。Gitleaks（秘密情報の疑いを探す道具）は `regexTarget = "line"` と既定の検出規則を維持する。公開出典の説明も残り、ファイル全体や鍵の種類全体は除外していない。

対象の版から設定を取得・解析し、人工的な6行に対して全除外式を検証した。元の欄はカンマあり・なしの両方で一致した。異なる欄名、異なる値、同じ行の後方への別欄追加、前方への別欄追加はいずれの除外式にも一致しなかった。r2 の同一行での除外回避が解消したことを独立に確認した。これは式そのものの検証であり、調整者が報告した検査ツールの exit 1 実験を独立に再実行したものではない。

指定された作業ツリー（別の作業用コピー）のストレージ手引き2件と検査設定は、遠隔の対象版とバイト単位で一致した。旧本文は r2 以降変わっておらず、元の #18 との差は説明済みのサイトキー代替文字列だけである。英語の「原文のまま」の文は、この例外を明記するようになった。画像・削除・出典・他の移植については変更がないため、以前の検証が引き続き適用される。

指定された作業ツリーのルートで次を実行した結果、75件検査・8件対象外・用語警告197件で PASS となった。

```sh
python3 tools/docs_check.py --all-warnings
```

### 軽微な注記と限界

日本語の「過去のコンテンツ」の短い文はまだ「そのまま」となっているが、「最近の変更」には例外の説明がある。文書を整える際に、短い文も修正済みの英語に合わせるとよい。案内の版も0.2のままであり、学びを記した新しい版を追加すれば r2 の SPEC-06 §6 の指摘への対応が完了する。どちらも値を限定した秘密情報検査の修正には影響せず、すでに英和で書かれた置換理由を隠すものでもない。

アプリケーションのサービスは起動していない。コミット・プッシュ・承認・マージ・終了処理・コンテナ状態変更は行っていない。調整者が統合の責任を持ち、この版の遠隔検査合格の証拠を残すこと。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Anchored expression | A matching rule fixed to the start and end of a line. | 行頭から行末までを固定して一致させる規則。 |
| Allowlist | Explicit exceptions to a check. | 検査の対象から明示的に除く条件。 |
| Placeholder | Temporary text to replace with a suitable value before use. | 利用前に適切な値へ置き換える仮の文字列。 |
