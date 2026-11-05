# PR29 Glossary notes review r3 / 用語注レビュー r3

> **Summary:** Changes requested: the five requested additions are present and bilingual, but the PR glossary link in SPEC-01 remains after its first body-text use.
> **概要:** 要修正。指定5箇所の補完と日英の対応は確認できたが、SPEC-01 の PR の用語集リンクは本文初出より後にある。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** checking the location named in an earlier finding is insufficient; the first body-text occurrence must also be checked in each language. ／ 前回指摘の位置だけでは不十分で、両言語の本文初出も確認する必要があると分かった。
- Applies to: RCOSDP/RDM-developer-guide PR #29, head `149513c699c0fbf8f69013d299d3921f19b50b72`, correction `32ccdf2000c5c1ac9921bcdb44d444f04f5ed61a`.
- Related: [Review index](README.md) · [r2](2026-11-06_RDM-developer-guide_PR29_Glossary_Notes_r2.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [REF-01](../reference/REF-01_Glossary.md) · [PR #29](https://github.com/RCOSDP/RDM-developer-guide/pull/29)
- Used by: the author and the next reviewer; [review index](README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** R2-01 is resolved. All four additions explicitly requested by R2-02 are present, but its PR link placement needs one further correction under SPEC-06 §3. No executable behavior was changed by the corrective commit. This is REV's review verdict, not a GitHub approval.

### Verified corrections

[SPEC-03 §3.5](../spec/03_security_gate.md#english) line 86 explains CI as automatic checks on every change and links REF-01, matching Japanese line 314. This is the first body-text CI occurrence in each half; the heading at line 84 may remain unannotated under the placement interpretation used in r1/r2. R2-01 is resolved even though the automated warning remains.

[SPEC-04](../spec/04_acceptance_tests.md#japanese) line 255 now explains QAE as the role checking that work is correct and links REF-01, matching English line 134. [ADR-05](../decisions/ADR-05_Test_IdP_for_Shibboleth.md#japanese) line 120 links its SAML explanation to REF-01, matching English line 24. [Manifest README](../../manifest/README.md#japanese) line 79 adds REF-01 alongside the existing SPEC-06 link and explains TOON consistently with English line 25. These notes are at the first body-text uses in both halves, excluding headings, header metadata, tables, code and link labels as in the preceding reviews.

[SPEC-01](../spec/01_manifest.md#japanese) line 172 now explains PR as a proposed change awaiting review and links REF-01, matching English line 40. This satisfies the specific r2 request at the warning paragraph, but not the first-use link requirement described in R3-01.

### R3-01 — P2: put the PR glossary link at the first body-text use in both halves

[SPEC-01](../spec/01_manifest.md#english) line 26 already explains “pull requests (*PRs*, proposed changes waiting to be merged)” without a REF-01 link. Its Japanese counterpart at line 158 likewise explains PR without that link. These are ordinary prose in §1, before the linked notes at lines 40/172 in §2. SPEC-06 §3 requires a short note **plus a link at first use**. Add a REF-01 link beside the existing explanation at lines 26 and 158; keep the explanations outside existing code and link tokens. No wording change to executable examples is needed.

This omission predates `32ccdf2`; it is not a regression introduced by that commit. The r2 review named only the later warning paragraph and missed these earlier occurrences. That oversight is corrected here rather than treating the successful requested edit as sufficient evidence of placement compliance.

### Verification and limits

Run from the supplied worktree root; all commands completed successfully:

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

The checker passed with 80 files checked, eight exempt and the same 12 warnings recorded in r2. The CI warning now has a valid explanation in the following paragraph; the other eleven warning locations are unchanged by the correction. All 79 unit tests passed. All eight remote checks passed at the reviewed head: site build, links, manifest policy, secret scan, static analysis, filesystem scan, and Python 3.11/3.12 unit tests. The first remote observation had static analysis pending; the final observation confirmed its pass. These checks do not enforce Japanese glossary completeness or first-use glossary-link presence.

The corrective diff changes only the five requested prose lines, preserving existing code spans, fenced blocks and links. The new untracked review record is checked separately with the documentation checker's per-file function because the normal command enumerates tracked files. Only this r3 record is written locally, and one Japanese PR comment is posted; no commit, push, approval, merge, close or Docker state change is performed. The author still needs to address R3-01 and include the review record in the branch.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**要修正。** R2-01 は解消。R2-02 が明示した4箇所の補完もあるが、PR のリンク配置には SPEC-06 §3 に基づく追加修正が必要。修正コミットは実行時の動作を変えていない。これは REV（担当レビュワ）の判定であり、GitHub の承認操作ではない。

### 確認した修正

[SPEC-03 §3.5](../spec/03_security_gate.md#english) 86行は CI を変更ごとの自動検査と説明し、REF-01 にリンクしており、日本語314行と対応する。両言語とも本文初出にある。84行の見出しは r1/r2 と同じ配置解釈により注を付けなくてよい。自動警告は残るが R2-01 は解消した。

[SPEC-04](../spec/04_acceptance_tests.md#japanese) 255行は QAE を「成果が正しいか検査する役割」と説明し、REF-01 にリンクして英語134行と対応する。[ADR-05](../decisions/ADR-05_Test_IdP_for_Shibboleth.md#japanese) 120行の SAML 注には REF-01 リンクが付き、英語24行と対応する。[manifest README](../../manifest/README.md#japanese) 79行は既存 SPEC-06 リンクに REF-01 を加え、TOON の説明も英語25行と整合する。先行レビューと同様、見出し・ヘッダのメタデータ・表・コード・リンクラベルを除くと、これらは両言語の本文初出に置かれている。

[SPEC-01](../spec/01_manifest.md#japanese) 172行は PR をレビュー待ちの変更の提案と説明し、REF-01 にリンクして英語40行と対応する。r2 が警告段落に求めた修正は満たすが、R3-01 の本文初出リンク要件は満たしていない。

### R3-01 — P2: PR の用語集リンクを両言語の本文初出に置く

[SPEC-01](../spec/01_manifest.md#english) 26行には既に “pull requests (*PRs*, proposed changes waiting to be merged)” という説明があるが、REF-01 リンクがない。日本語158行も PR の説明はあるがリンクがない。いずれも §1 の通常の本文で、リンクを付けた §2 の40/172行より前にある。SPEC-06 §3 は初出に短い注とリンクの両方を求める。26行と158行の既存の説明に REF-01 リンクを添えること。既存のコードやリンクの内部には注を入れない。実行例の変更は不要。

これは `32ccdf2` より前からある不足で、同コミットが生んだ退行ではない。r2 は後の警告段落だけを名指しし、それ以前の出現を見落としていた。要求どおりの修正が済んだことだけで配置規則も満たしたとはせず、その見落としをここで訂正する。

### 検証と限界

指定 worktree のルートで次を実行し、すべて成功した。

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

文書検査は80ファイルを検査、8件を除外し、r2 と同じ12警告で合格。CI の警告は直後の本文に説明が存在する状態になり、ほかの11警告位置は今回の修正で変わらない。単体テスト79件は全件合格。対象先端のリモート8チェック（サイト生成、リンク、manifest 方針、秘密スキャン、静的解析、ファイルシステムスキャン、Python 3.11/3.12 単体テスト）も全件合格。初回確認では静的解析が実行中だったが、最終確認では合格を確認した。これらの検査は日本語の用語注の完備や初出での用語集リンクの存在を強制しない。

修正差分は指定5箇所の本文行だけで、既存コードスパン・コードブロック・リンクは保持されている。通常の文書検査は追跡済みファイルを列挙するため、未追跡の新規レビュー記録は検査器のファイル単位の関数で別途確認する。ローカルにはこの r3 記録だけを書き、日本語の PR コメントを1件投稿する。commit・push・approve・merge・close、Docker 状態変更は行わない。作者による R3-01 の修正とレビュー記録のブランチへの収録が残る。

---

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| CI | Automatic checks on each change. | 変更ごとに自動で走る検査。 |
| PR | A proposed change awaiting review. | レビュー待ちの変更の提案。 |
| QAE | The role checking that work is correct. | 成果が正しいか検査する役割。 |
| SAML | A format for passing login results. | ログイン結果を渡し合う文書の形式。 |
| TOON | A compact text form of structured data. | 構造のあるデータを短く書く文字形式。 |
| P2 | A correction required before review acceptance. | レビューの受入前に必要な修正。 |
