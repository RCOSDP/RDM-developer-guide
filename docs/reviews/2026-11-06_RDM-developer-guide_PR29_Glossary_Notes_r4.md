# PR29 Glossary notes review r4 / 用語注レビュー r4

> **Summary:** Accepted for the r4 re-review: R3-01 is resolved in both languages, and all required checks pass.
> **概要:** r4 再レビューは受入可。R3-01 は両言語で解消し、必要な検査はすべて合格した。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-06. **Learned:** the existing first-use explanation needs its glossary link beside it in both language halves. ／ 既存の初出説明に添える用語集リンクは、両言語で確認する必要があると分かった。
- Applies to: RCOSDP/RDM-developer-guide PR #29, head `66add8ef9d391fc03c1ceb8ec1be1bbb660fa55a`.
- Related: [Review index](README.md) · [r3](2026-11-06_RDM-developer-guide_PR29_Glossary_Notes_r3.md) · [SPEC-06](../spec/06_documentation_conventions.md) · [REF-01](../reference/REF-01_Glossary.md) · [PR #29](https://github.com/RCOSDP/RDM-developer-guide/pull/29)
- Used by: the author and integration reviewer; [review index](README.md).

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Verdict and scope

**Accepted; no open findings in this re-review.** R3-01, the sole open r3 item, is resolved. This is REV's review verdict, not a GitHub approval. The review covers the two corrective commits `b3de101fef548e2d0450678be40e712db399af2c` and `66add8ef9d391fc03c1ceb8ec1be1bbb660fa55a` relative to r3's reviewed head `149513c699c0fbf8f69013d299d3921f19b50b72`.

[SPEC-01](../spec/01_manifest.md#english) line 26 now links REF-01 inside the existing explanation of pull requests (PRs: proposed changes waiting to be merged). Its [Japanese counterpart](../spec/01_manifest.md#japanese) at line 158 contains the same explanation and link. Both links resolve to the shared glossary at the first body-text use under the placement interpretation established in r3. Header metadata remains outside that interpretation. The later notes at lines 40/172 remain intact.

The cumulative correction changes only those two prose lines and adds the r3 record. Existing code spans, fenced examples and prior links are preserved; executable behavior is unchanged.

### Verification and limits

Run from the supplied worktree root; each command must finish successfully:

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

Observed results are recorded in TOON (a compact text form for structured data):

```toon
verification[3]{check,result,detail}:
  documentation,pass,81 checked / 8 exempt / 12 existing warnings
  unit-tests,pass,79 tests
  remote-ci,pass,8 checks at 66add8ef9d391fc03c1ceb8ec1be1bbb660fa55a
```

CI (automatic checks on changes) passed for site build, links, manifest policy, secret scan, static analysis, filesystem scan, and Python 3.11/3.12 unit tests. The remote head matches the local reviewed head. The 12 glossary warnings have the same locations and terms as r3; they are non-failing and unchanged by these corrections. Automated checks do not enforce Japanese glossary completeness or first-use glossary-link presence, so the two corrected prose locations were inspected manually.

The untracked r4 record is also checked directly with the documentation checker's per-file function because the normal command enumerates tracked files. Incorporating this record into the branch remains with the author. No commit, push, approval, merge, close or Docker state change is part of this review.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 判定と範囲

**受入可。この再レビューの未解決指摘はない。** r3 の唯一の未解決項目 R3-01 は解消した。これは REV のレビュー判定であり、GitHub の承認操作ではない。対象は r3 の確認先端 `149513c699c0fbf8f69013d299d3921f19b50b72` 以降の修正コミット `b3de101fef548e2d0450678be40e712db399af2c` と `66add8ef9d391fc03c1ceb8ec1be1bbb660fa55a`。

[SPEC-01 英語](../spec/01_manifest.md#english)26行は既存の PR（マージを待つ変更の提案）の説明内に REF-01 リンクが付いた。[日本語](../spec/01_manifest.md#japanese)158行にも同じ説明とリンクがある。リンク先は共通用語集に解決し、r3 で採用した配置解釈における本文初出に両方が置かれている。ヘッダのメタデータはこの解釈の対象外。後続の40/172行の注も保持されている。

修正全体はこの本文2行と r3 記録の追加だけ。既存コードスパン・コード例・既存リンクは保持され、実行時の動作変更はない。

### 検証と限界

指定 worktree のルートで実行し、各コマンドが成功終了することを確認する。

```sh
python3 tools/docs_check.py --all-warnings
python3 -m unittest discover -s tools/tests
gh pr checks 29 --repo RCOSDP/RDM-developer-guide
```

実測結果を TOON（構造のあるデータを短く書く文字形式）で記録する。

```toon
verification[3]{check,result,detail}:
  文書検査,合格,81件検査 / 8件除外 / 既存12警告
  単体テスト,合格,79件
  リモートCI,合格,66add8ef9d391fc03c1ceb8ec1be1bbb660fa55a の8チェック
```

CI（変更に対する自動検査）はサイト生成、リンク、manifest 方針、秘密スキャン、静的解析、ファイルシステムスキャン、Python 3.11/3.12 単体テストの全件が合格。リモート先端とローカルの確認先端は一致した。用語注12警告の位置と用語は r3 と同じで、今回の修正による変化はなく、不合格扱いではない。自動検査は日本語の用語注の完備や初出の用語集リンクを強制しないため、修正した本文2箇所は手動で確認した。

通常の文書検査は追跡済みファイルを列挙するため、未追跡の r4 記録は検査器のファイル単位関数でも直接確認する。記録のブランチへの収録は作者に残る。commit・push・approve・merge・close、Docker 状態変更はこのレビューでは行わない。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| PR | A proposed change awaiting review and merge; see [REF-01](../reference/REF-01_Glossary.md). | レビューとマージを待つ変更の提案。[REF-01](../reference/REF-01_Glossary.md)。 |
| CI | Automatic checks on changes; see [REF-01](../reference/REF-01_Glossary.md). | 変更に対する自動検査。[REF-01](../reference/REF-01_Glossary.md)。 |
| TOON | A compact text form for structured data. | 構造のあるデータを短く書く文字形式。 |
| Head | The latest commit being reviewed. | レビュー対象の先端コミット。 |
