# Reference / 参考

> **Summary:** External facts such as the shared glossary, tool versions, upstream metadata. Reference documents contain fixed information that other documents link to.
> **概要:** 共通用語集、道具の版、上流メタデータなどの外部事実。参考文書は他の文書がリンクする固定情報を持ちます。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** a shared glossary is needed because the same term (for example "upstream" or "port") appears in several specifications and must mean one thing everywhere. ／ 同じ用語（例:「上流」「ポート」）が複数の仕様に出てくるため、どこでも一つの意味になるよう共通の用語集が必要だと分かった。
- Normative for: [REF-01 Glossary](./REF-01_Glossary.md) and future reference documents.
- Related: [../README.md](../README.md) · [policy/](../policy/README.md) · [spec/](../spec/README.md) · [decisions/](../decisions/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. What belongs here

A *reference* document contains external facts that other documents link to. This folder contains:

| ID | File | Purpose |
|---|---|---|
| REF-01 | [REF-01_Glossary.md](./REF-01_Glossary.md) | The shared glossary: technical terms with one-line notes for everyone and precise meanings for engineers. |

Future reference documents may include:

| ID | Topic |
|---|---|
| REF-02 | Tool versions and compatibility matrix |
| REF-03 | Upstream repository metadata (default branches, tags) |

### 2. How reference documents are used

Reference documents are linked from other documents using relative links:

- Glossary terms: `[term](../reference/REF-01_Glossary.md#english)` (section anchor)
- Tool versions: `[docker](../reference/REF-02_Tool_Versions.md#english)` (file link)

### 3. Creating a new reference document

1. Name the file `REF-NN_<Title>.md` (two-digit number, next available).
2. Follow [SPEC-06 documentation conventions](../spec/06_documentation_conventions.md).
3. Include only fixed facts, not opinions or processes.
4. Link from documents that need the reference.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. ここに属するもの

「参考」文書は他の文書がリンクする外部事実を含みます。このフォルダには次が含まれます：

| ID | ファイル | 目的 |
|---|---|---|
| REF-01 | [REF-01_Glossary.md](./REF-01_Glossary.md) | 共通用語集：専門用語に、誰向けに一行の注と技術者向けの正確な意味を付ける。 |

今後の参考文書として以下が考えられます：

| ID | トピック |
|---|---|
| REF-02 | 道具の版と互換性マトリクス |
| REF-03 | 上流リポジトリメタデータ（既定ブランチ、タグ） |

### 2. 参考文書がどう使われるか

参考文書は他の文書から相対リンクで参照されます：

- 用語集の語: `[用語](../reference/REF-01_Glossary.md#japanese)`（節アンカー）
- 道具の版: `[docker](../reference/REF-02_Tool_Versions.md#japanese)`（ファイルリンク）

### 3. 新しい参考文書をつくるには

1. ファイル名を `REF-NN_<題>.md`（2 桁の番号、次に空いているもの）にする。
2. [SPEC-06 文書規約](../spec/06_documentation_conventions.md)に従う。
3. 意見やプロセスではなく、固定事実だけを含む。
4. 参考が必要な文書へリンクする。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Reference | A document containing external facts that other documents link to. | 他の文書がリンクする外部事実を含む文書。 |
| Glossary | A collection of technical terms with explanations. | 専門用語の集合。 |
| Link | A navigational element that jumps to another part of a document. | 文書の別の部分へ飛ぶナビゲーション要素。 |
| Anchor | A bookmark inside a page that a link can jump to. | ページの中の「しおり」。リンクで飛べる。 |
