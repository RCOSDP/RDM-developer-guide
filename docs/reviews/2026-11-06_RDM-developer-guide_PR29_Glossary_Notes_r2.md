# PR29 Glossary notes review r2 / 用語注レビュー r2

> **Summary:** Changes requested: most first-use corrections are sound, but English CI and several Japanese explanations or glossary links remain incomplete.
> **概要:** 要修正。初出の修正は概ね妥当だが、英語の CI と日本語の説明・用語集リンクに不足が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a warning located at a heading is not harmless unless the following prose actually explains the term, and English-only checks cannot establish bilingual completeness. ／ 警告が見出しを指していても本文に説明がなければ無害ではなく、英語だけの検査では日英の完備を確認できないと分かった。
- Applies to: RCOSDP/RDM-developer-guide PR #29, head `3a29f28a441662d748f908ccf31a2d1c853bf519`, correction `ffd64c016f89f98184d19d0bf339b735cf583bcd`.
- Related: [Review index](README.md) · [r1](2026-11-06_RDM-developer-guide_PR29_Glossary_Notes_r1.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [REF-01](../reference/REF-01_Glossary.md) · [PR #29](https://github.com/RCOSDP/RDM-developer-guide/pull/29)
- Used by: the PR author and the next review round; [review index](README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict

**Changes requested.** R1-01's named placement problems are resolved, but R1-02 and R1-03 are not fully resolved in both languages. Reviewed the 22 existing Markdown documents changed by the PR, the checker and tests, and the r1 record. The following findings concern documentation completeness, not executable behavior.

### R2-01 — P2: CI is still unexplained in English

[SPEC-03](../spec/03_security_gate.md#english) line 84 is a heading containing CI, but its first body-text use at line 101 and later use at line 241 have no explanation or REF-01 link. The Japanese counterpart at line 314 has both. Add an English explanation such as “automatic checks on every change” with the glossary link, preferably in §3.5 to match Japanese. This warning is not merely a heading false positive: the claimed explanation does not exist. The r1 warning assessment was too generous on this point and is corrected here.

### R2-02 — P2: finish the Japanese counterparts and links

[SPEC-04](../spec/04_acceptance_tests.md#japanese) line 255 still says only `QAE（QA担当）`, with no REF-01 link; English line 134 now explains the role and links it. This is the exact R1-03 example, and leaves R1-02 unresolved too. Use “成果が正しいか検査する役割” and the matching link in Japanese.

Other counterparts missed by the link sweep are [ADR-05](../decisions/ADR-05_Test_IdP_for_Shibboleth.md#japanese) line 120 (SAML has an explanation but no REF-01 link, unlike English line 24), [SPEC-01](../spec/01_manifest.md#japanese) line 172 (PR has neither the English line 40 explanation nor its glossary link), and [manifest README](../../manifest/README.md#japanese) line 79 (TOON still links only to SPEC-06, unlike English line 25). Add the matching glossary references and the missing PR explanation. These Japanese omissions existed before the corrective commit, but are within r1's request to complete both halves; this review does not claim they are new regressions.

### Verified corrections and remaining warnings

The named R1-01 examples now have explanations and REF-01 links at the first body-text use in both halves: manifest commit/SHA at 21/75 and pull request at 35/89; ADR-03 CVEs/CVE at 39/114; SPEC-03 allow-list at 24/252 and container at 65/293; demo arm64 and Apple Silicon together at 24/120. SPEC-03 image is explained at 74/302. ADR-01 merge/pull requests at 66/158 and SPEC-05 merge at 125/272 also precede the later capitalized uses. These locations exclude headings, tables, code, link labels, and header metadata, consistently with r1.

The revised REV/QAE notes in ADR-01, AID notes in the policy index and SPEC-05, QAE notes in the specification index, and Shibboleth notes in the root README, SPEC-00 and SPEC-04 give roles or behavior in both languages. The SPEC-04 Japanese QAE exception is R2-02. Installer Docker and docs-index MkDocs links are present in both halves; ADR-01's component list has a shared sentence-end REF-01 link in both halves. The link sweep is substantial but not complete.

All 12 warning locations were inspected individually. The claimed split of eight heading locations and four later capitalized prose locations is mechanically accurate, but does not prove that all twelve are harmless. The following is review data in TOON (a compact text record format; see [REF-01](../reference/REF-01_Glossary.md)). Line numbers refer to the reviewed head.

```toon
warnings[12]{file,line,term,assessment}:
  ADR-01,103,Merge,explained at 66 and Japanese 158
  SPEC-03,84,CI,heading but English prose lacks explanation R2-01
  SPEC-03,72,Container,explained earlier at 65 and Japanese 293
  SPEC-03,97,Image,explained earlier at 74 and Japanese 302
  SPEC-03,84,Secret,earlier explanation at 58 and Japanese 286
  SPEC-03,133,Allow-list,explained earlier at 24 and Japanese 252
  SPEC-03,99,Semgrep,explained at 101 and Japanese 329
  SPEC-03,103,OWASP ZAP,explained at 105 and Japanese 333
  SPEC-04,81,Shibboleth,explained at 83 and Japanese 204
  SPEC-05,126,Merge,explained earlier at 125 and Japanese 272
  SPEC-05,149,COS,explained at 151 and Japanese 298
  manifest README,39,Commit,explained earlier at 21 and Japanese 75
```

### Verification and limits

From the supplied worktree root, these commands passed:

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

The documentation checker checked 79 files, exempted eight legacy/sample files, and emitted 12 warnings. All 79 unit tests passed. All eight remote checks passed at the requested head: site build, links, manifest policy, secret scan, static analysis, filesystem scan, and Python 3.11/3.12 unit tests. The checker only checks English glossary occurrences and does not enforce glossary-link presence, so these passes do not resolve R2-01/R2-02.

Comparison against both the PR base `5975c43` and r1 head `8ce2065` found no removed or altered existing inline-code spans, fenced blocks, or Markdown link tokens in the 22 existing documents. New notes and links remain outside those existing tokens. The review-record exemption is limited to glossary warnings; the added negative test asserts failures for a missing Japanese anchor, Version and broken link. It does not explicitly assert a missing Jump line, although that check remains enabled in the implementation. No checker redesign is required for acceptance.

Only this r2 record was written locally, and one Japanese review comment is to be posted. No source fixes, commit, push, approval, merge, close, or Docker state changes are part of this review. The author must finish R2-01/R2-02 before acceptance.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定

**要修正。** R1-01 で名指しした配置の問題は解消したが、R1-02・R1-03 は両言語で完了していない。PR が変更する既存 Markdown 22 文書、検査器とテスト、r1 記録を確認した。以下は実行時の動作ではなく文書の完備性の指摘である。

### R2-01 — P2: 英語の CI が未説明

[SPEC-03](../spec/03_security_gate.md#english) の 84 行は CI を含む見出しだが、本文の初出 101 行と後出 241 行にも説明・REF-01 リンクがない。日本語の 314 行には両方ある。「変更ごとに自動で走る検査」に相当する英語の説明と用語集リンクを、できれば日本語と同じ §3.5 に加える。この警告は単なる見出し由来の誤検出ではなく、説明自体が存在しない。r1 のこの警告への判定は甘かったため、ここで訂正する。

### R2-02 — P2: 日本語の対訳とリンクを仕上げる

[SPEC-04](../spec/04_acceptance_tests.md#japanese) 255 行は今も `QAE（QA担当）` だけで REF-01 リンクがない。英語の 134 行には役割の説明とリンクが加わった。これは R1-03 で挙げた箇所そのもので、R1-02 も未解消である。日本語にも「成果が正しいか検査する役割」と対応するリンクを加える。

リンク補完で漏れた他の対訳は、[ADR-05](../decisions/ADR-05_Test_IdP_for_Shibboleth.md#japanese) 120 行の SAML（説明はあるが英語 24 行と異なり REF-01 リンクなし）、[SPEC-01](../spec/01_manifest.md#japanese) 172 行の PR（英語 40 行にある説明も用語集リンクもなし）、[manifest README](../../manifest/README.md#japanese) 79 行の TOON（英語 25 行と異なり SPEC-06 へのリンクだけ）。対応する用語集参照と、PR の説明を補う。これらの日本語側の不足は修正コミット以前からあるが、r1 の「両言語を完成させる」という要求の範囲内であり、新規の退行と主張するものではない。

### 確認できた修正と残る警告

R1-01 の名指し箇所には両言語の本文初出に説明と REF-01 リンクがある。manifest の commit/SHA は 21/75 行、pull request は 35/89 行、ADR-03 の CVEs/CVE は 39/114 行、SPEC-03 の allow-list は 24/252 行、container は 65/293 行、実証の arm64 と Apple Silicon は同じ注の 24/120 行。SPEC-03 の image は 74/302 行。ADR-01 の merge/pull requests は 66/158 行、SPEC-05 の merge は 125/272 行で後の大文字表記より前にある。r1 と同様に見出し・表・コード・リンクラベル・ヘッダのメタデータは本文初出の対象から除いている。

ADR-01 の REV/QAE、方針索引と SPEC-05 の AID、仕様索引の QAE、ルート README・SPEC-00・SPEC-04 の Shibboleth は両言語で役割や動作を説明している。SPEC-04 の日本語 QAE の例外が R2-02。installer の Docker と docs 索引の MkDocs にも両言語のリンクがあり、ADR-01 の部品一覧には両言語で文末の共通 REF-01 リンクがある。リンク補完は大幅に進んだが完了ではない。

12 警告を一つずつ確認した。「見出しの位置が8件、後出の大文字本文が4件」という位置の分類自体は正しいが、12件とも無害という意味にはならない。手動判定を TOON（記録を短く書く文字形式。[REF-01](../reference/REF-01_Glossary.md)）で残す。行番号はレビュー対象先端のもの。

```toon
warnings[12]{file,line,term,assessment}:
  ADR-01,103,Merge,66行と日本語158行で説明済み
  SPEC-03,84,CI,見出しだが英語本文にも説明なし R2-01
  SPEC-03,72,Container,前の65行と日本語293行で説明済み
  SPEC-03,97,Image,前の74行と日本語302行で説明済み
  SPEC-03,84,Secret,前の58行と日本語286行に説明あり
  SPEC-03,133,Allow-list,前の24行と日本語252行で説明済み
  SPEC-03,99,Semgrep,101行と日本語329行で説明済み
  SPEC-03,103,OWASP ZAP,105行と日本語333行で説明済み
  SPEC-04,81,Shibboleth,83行と日本語204行で説明済み
  SPEC-05,126,Merge,前の125行と日本語272行で説明済み
  SPEC-05,149,COS,151行と日本語298行で説明済み
  manifest README,39,Commit,前の21行と日本語75行で説明済み
```

### 検証と限界

指定 worktree のルートで以下が合格した。

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

文書検査は79ファイルを検査、旧資料・サンプル8件を除外し、12警告。単体テスト79件は全件合格。指定先端のリモート8チェック（サイト生成、リンク、manifest 方針、秘密スキャン、静的解析、ファイルシステムスキャン、Python 3.11/3.12 単体テスト）もすべて合格した。用語検査は英語だけを見ており、用語集リンクの存在は強制しないため、合格しても R2-01/R2-02 は解消しない。

PR の基点 `5975c43` と r1 先端 `8ce2065` の両方との比較で、既存22文書のコードスパン・コードブロック・Markdown リンクの削除や改変はなかった。新しい注とリンクは既存のそれらの外に置かれている。レビュー記録の例外は用語警告だけで、追加の異常系テストは日本語アンカー・Version の欠落と壊れたリンクの失敗を確認する。Jump 行欠落の明示的な検証はこのテストにないが、実装では検査が有効なまま。この PR の受入に検査器の再設計は不要。

ローカルにはこの r2 記録だけを作成し、日本語コメントを1件投稿する。本文の修正、commit・push・approve・merge・close、Docker の状態変更はレビュー作業に含めない。受入前に作者による R2-01/R2-02 の完了が必要。

---

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| P2 | A correction required before this review accepts the change. | このレビューが受け入れる前に必要な修正。 |
| False positive | A warning even though the requirement is already satisfied. | 要求を満たしているのに出る警告。 |
| Regression | Previously correct behavior that a change breaks. | 変更によって以前の正しい動きが壊れること。 |
| CI | Automatic checks that run when a change is proposed or saved. | 変更を提案・保存したときに自動で走る検査。 |
