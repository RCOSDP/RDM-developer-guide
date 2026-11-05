# PR29 Glossary notes review r1 / 用語注レビュー r1

> **Summary:** Changes requested: first-use placement and shared-glossary links remain incomplete, although tests and continuous checks pass.
> **概要:** 要修正。テストと継続検査は合格したが、初出への配置と共通用語集へのリンクに不足が残る。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** a case-sensitive glossary check can pass a later capitalized occurrence while missing an earlier lowercase or plural use. ／ 大文字小文字を区別する用語検査は、前にある小文字・複数形の使用を見落とし、後の大文字の使用だけで合格し得る。
- Applies to: RCOSDP/RDM-developer-guide PR #29, head `8ce2065d841f7e24f567da3100035ed5e00a3abc`.
- Related: [Review index](README.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [REF-01](../reference/REF-01_Glossary.md) · [PR #29](https://github.com/RCOSDP/RDM-developer-guide/pull/29)
- Used by: the PR author and the next review round.

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Changes requested.** R1-01 and R1-02 must be resolved before acceptance; R1-03 is a smaller readability improvement. Reviewed all 22 changed Markdown documents and the checker/test changes. All 24 local files match the remote head's Git blob hashes (fingerprints of file contents). No commit, push, approval, merge, or Docker state change was performed.

### R1-01 — P2: move notes to the first prose use

The new notes sometimes explain a later capitalized spelling rather than the first actual use. Examples at the reviewed head:

- [Manifest README](../../manifest/README.md): `commit` already appears at line 21, while its new explanation is at line 39; Japanese has the same gap at lines 75/93. English `pull request` at line 35 also precedes the new note at line 40.
- [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md): English `CVEs` at line 39 precedes the new `CVE` note at line 55. Japanese correctly explains it at line 114, in the corresponding first paragraph. The translations exist, but the first-use placement is not equivalent.
- [SPEC-03](../spec/03_security_gate.md): prose already uses `container` at line 65 before the new note at line 74. `allow-list` occurs at lines 24 and 54 before its explanation at line 137. The warning locations are headings only because the checker matches the capitalized glossary spellings.
- [Mac Studio demo](../demo/20_core_install_mac_studio.md): the newly added arm64 note introduces `Apple Silicon` at lines 24/120 before its explanation at lines 47/143. Explain new terms introduced inside notes too.

Move or consolidate the notes at the earliest prose occurrence in each language, considering case, plurals and expanded names. Recheck all changed notes under that rule. The existing case-sensitive warning implementation need not be redesigned in this PR, but eight warnings cannot be described as proof that only heading-first-use gaps remain.

### R1-02 — P2: supply the required shared-glossary links

[SPEC-06 §3](../spec/06_documentation_conventions.md#english) requires a short note **plus a link** for terms in the shared glossary. Most additions supply only parentheses. For example, the Docker notes in [installer README](../../installer/README.md) lines 30/50 and MkDocs notes in [docs README](../README.md) lines 55/99 have no REF-01 link at their first use. A link to another specification or a later glossary table does not give the promised first-use reference.

Add matching REF-01 links with the first-use notes in both languages, consistently across the changed documents. Keep them outside existing code spans and existing link labels/destinations.

### R1-03 — P3: explain roles and proposals, not just their expansions

Some new notes still presume technical knowledge: [SPEC-04](../spec/04_acceptance_tests.md) lines 134/136 says `QAE (QA engineer)` and `PR (pull request)`; the Japanese equivalents say `QA担当` and `プルリクエスト`. These are counterparts, but do not independently meet the primary-school-language goal. Prefer “the person who checks that the work is correct” and “a proposed change waiting for review,” with equivalent Japanese wording. The longer PR explanation already used elsewhere in the patch is suitable.

### Checks and accepted aspects

The new explanations generally agree with REF-01 and have English/Japanese counterparts; R1-01 and R1-03 qualify the placement/readability result. No unintended change to normative obligations was found. The intentional SPEC-06 §8 exception matches the implementation. Diff searches and comparison of code spans and Markdown link tokens found no injected notes inside existing code spans, links, headings or tables; version additions are learning records, not term-note injections.

Exempting review records from glossary warnings is justified by preserving the reviewer's words. The exception does not bypass anchors, Jump, version, links or data parity. The new unit test covers an exempt review, a non-exempt specification and the REF-01/index predicates. Additional temporary probes confirmed that missing anchors, Jump, version and broken links still fail for a review file while its glossary warning stays suppressed. Adding those negative cases to the committed test would strengthen regression protection. The directory-wide exemption also covers the review index and future records, as the updated specification states.

Commands were run from the supplied worktree root. These are recorded verification commands, not changes to the system:

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

The documentation check passed: 78 checked files, eight legacy/sample exemptions and eight warnings; review files produced no glossary warnings. All 78 unit tests passed. All eight remote checks passed: site build, links, manifest policy, secret scan, static analysis, filesystem scan and unit tests on Python 3.11/3.12.

The warning classification from manual inspection is recorded here as TOON (a compact text list of records; see [REF-01](../reference/REF-01_Glossary.md#english)). Paths are relative to the repository root.

```toon
warnings[8]{file,line,term,assessment}:
  docs/spec/03_security_gate.md,84,CI,heading precedes explained prose
  docs/spec/03_security_gate.md,72,Container,earlier unexplained prose at 65
  docs/spec/03_security_gate.md,84,Secret,already explained in prose at 58
  docs/spec/03_security_gate.md,133,Allow-list,earlier unexplained prose at 24 and 54
  docs/spec/03_security_gate.md,99,Semgrep,heading precedes explained prose
  docs/spec/03_security_gate.md,103,OWASP ZAP,heading precedes explained prose
  docs/spec/04_acceptance_tests.md,81,Shibboleth,heading precedes explained prose
  docs/spec/05_upstream_tracking.md,149,COS,heading precedes explained prose
```

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**要修正。** 合格には R1-01 と R1-02 の解消が必要。R1-03 は軽微な読みやすさの改善事項。変更された Markdown 22 文書と検査器・テストを確認した。ローカルの対象 24 ファイルは、リモート先端の Git blob ハッシュ（ファイル内容の指紋）と一致した。commit・push・approve・merge・Docker の状態変更は行っていない。

### R1-01 — P2: 本文の本当の初出へ注を移す

新しい注が、実際の初出ではなく、後に登場する大文字の表記を説明している場合がある。レビュー対象先端の例:

- [Manifest README](../../manifest/README.md): 英語は 21 行に `commit` があるが、新しい説明は 39 行。日本語も 75 行と 93 行で同じ問題がある。英語の `pull request` も 35 行にあり、注は 40 行。
- [ADR-03](../decisions/ADR-03_Staged_Security_Gate.md): 英語は 39 行の `CVEs` より後の 55 行に `CVE` の注がある。日本語は対応する最初の段落の 114 行で正しく説明している。訳はあるが初出への配置が対応していない。
- [SPEC-03](../spec/03_security_gate.md): 新しい注は 74 行だが、本文の `container` は 65 行に既にある。`allow-list` も 24 行・54 行にあり、説明は 137 行。警告位置が見出しになるのは、検査器が用語集の大文字表記に一致させるため。
- [Mac Studio 実証](../demo/20_core_install_mac_studio.md): 新しい arm64 注自体が 24 行・120 行で `Apple Silicon` を使い、その説明は 47 行・143 行。注の中で新たに使う用語にも説明が必要。

大文字小文字、複数形、略語の展開を考慮し、両言語で最初の本文使用へ注を移すかまとめること。変更した注全体をこの基準で再確認すること。この PR で既存の大小文字を区別する検査を作り直す必要はないが、「警告8件だから残るのは見出し初出だけ」とは結論できない。

### R1-02 — P2: 共通用語集への必須リンクを付ける

[SPEC-06 §3](../spec/06_documentation_conventions.md#japanese) は共通用語集の語に「短い注とリンク」を要求する。追加の多くは括弧だけである。例えば [installer README](../../installer/README.md) の 30 行・50 行の Docker 注、[docs README](../README.md) の 55 行・99 行の MkDocs 注には初出の REF-01 リンクがない。他の仕様へのリンクや後の用語表では、初出で約束された参照を提供できない。

変更対象全体で、両言語の初出注に対応する REF-01 リンクを追加すること。既存のコードスパンや既存リンクのラベル・リンク先の中には入れないこと。

### R1-03 — P3: 略語の展開だけでなく役割と提案を説明する

新しい注の一部はなお専門知識を前提とする。[SPEC-04](../spec/04_acceptance_tests.md) の 134 行・136 行は `QAE (QA engineer)`、`PR (pull request)`、日本語は `QA担当`、`プルリクエスト` となっている。対訳はあるが、それだけでは小学生にも分かる説明にならない。「作業が正しいか確かめる人」「レビューを待っている変更の提案」のように日英で説明するとよい。差分の他の箇所にある長めの PR 説明は適切。

### 検査と認められる点

新しい説明は概ね REF-01 と整合し、日英の対応がある。ただし配置と読みやすさには R1-01・R1-03 の留保がある。規範文の義務を意図せず変更した箇所は見つからなかった。意図的な SPEC-06 §8 の例外は実装と一致する。差分検索とコードスパン・Markdown リンクの比較では、既存のコード・リンク・見出し・表の中への注の混入はなかった。版の追加は学びの記録であり用語注の混入ではない。

レビュー記録の用語警告除外は、レビュワの原文を保つ理由で妥当。アンカー、Jump、版、リンク、データ一致の検査は迂回しない。追加テストは除外するレビュー、除外しない仕様、REF-01 と索引の判定を覆う。一時ファイルによる追加検証でも、レビューの用語警告は抑制しつつ、アンカー・Jump・版の欠落と壊れたリンクは失敗した。この異常系も正式なテストに入れると回帰防止が強くなる。フォルダ全体の除外は、更新後の仕様どおりレビュー索引と将来の記録も含む。

指定 worktree のルートで実行した確認コマンド:

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

文書検査は合格。検査 78 ファイル、旧資料・サンプルの除外 8、警告 8。レビュー記録の用語警告はゼロ。単体テスト 78 件はすべて合格。リモートのサイト生成・リンク・manifest 方針・秘密スキャン・静的解析・ファイルシステムスキャン・Python 3.11/3.12 の単体テストの計 8 チェックもすべて合格。

警告の手動判定を TOON（記録を短く書く文字の形。[REF-01](../reference/REF-01_Glossary.md#japanese)）で残す。パスはリポジトリのルートからの相対。

```toon
warnings[8]{file,line,term,assessment}:
  docs/spec/03_security_gate.md,84,CI,見出しの後の本文で説明済み
  docs/spec/03_security_gate.md,72,Container,65行の本文が先で未説明
  docs/spec/03_security_gate.md,84,Secret,58行の本文で既に説明済み
  docs/spec/03_security_gate.md,133,Allow-list,24行と54行の本文が先で未説明
  docs/spec/03_security_gate.md,99,Semgrep,見出しの後の本文で説明済み
  docs/spec/03_security_gate.md,103,OWASP ZAP,見出しの後の本文で説明済み
  docs/spec/04_acceptance_tests.md,81,Shibboleth,見出しの後の本文で説明済み
  docs/spec/05_upstream_tracking.md,149,COS,見出しの後の本文で説明済み
```

---

## Glossary / 用語

| Term | English | 日本語 |
|---|---|---|
| First prose use | The earliest use in readable body text, outside code, headings, tables and link labels. | コード・見出し・表・リンクラベル以外の、読む本文での最初の使用。 |
| False positive | A warning that reports a problem where the requirement is already met. | 要求を満たしているのに問題として出る警告。 |
| P2 / P3 | A required correction / a smaller improvement in this review. | このレビューでの要修正事項／軽微な改善事項。 |
| Regression test | A check that an earlier working behavior still works after a change. | 変更後も以前の正しい動きが保たれているかの検査。 |
