# SPEC-06 Documentation Conventions / 文書規約

> **Summary:** How every document in this repository is written: bilingual layout, glossary notes, diagrams, data, versions, and links.
> **概要:** このリポジトリの全文書の書き方。英和二部構成、用語注、図、データ、版、リンクの規則。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.3 — 2026-11-05. **Learned:** the written description of a check drifts from the tool as soon as the tool improves, so §8 must be re-read against `tools/docs_check.py` on every change to either (review r2, R2-03). ／ 検査の説明は道具が良くなった瞬間に古くなるため、どちらかを変えるたびに §8 と `tools/docs_check.py` を突き合わせる必要があると分かった（レビュー r2、R2-03）。
  0.2 — 2026-11-05. **Learned:** a convention is only as strong as the check that enforces it, so the convention must name what the checker does today, what it leaves out, and which legacy files are exempt. ／ 規約の強さは、それを守らせる検査の強さまでしかない。だから規約は、検査が今日何を見て何を見ないか、どの旧資料を例外にするかを名指しで書く必要があると分かった。
- Version / 版: 0.1 — 2026-11-05. **Learned:** a shared convention must exist before any other document, or the English/Japanese halves and glossary notes drift from the first page onward. ／ 他の文書より先に共通規約を置かないと、初めの一枚から英和の対応と用語注がずれると分かった。
- Normative for: every `*.md` under this repository, including `README.md` at every directory level.
- Related: [SPEC-00 Overview](00_overview.md) · [POL-01 Position](../policy/POL-01_Developer_Environment_2027_Position.md) · [docs/README.md](../README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### 1. Scope

This specification governs the form of documents, not their content. It applies to all Markdown files in the repository: policies (`POL-nn`), specifications (`00`–`nn`), decisions (`ADR-nn`), references (`REF-nn`), demos, hand-offs, reviews, status boards, guides, and every `README.md`.

**Glossary notes.** A *specification* is a rule book that implementers must follow. A *policy* is the position we take. A *decision record* (ADR) is a note that explains why we chose one way and not another.

### 2. Page layout (mandatory order)

1. `# <ID> <Title in English> / <日本語題>` — one H1 only.
2. A blockquote with **Summary** (English, one or two sentences) and **概要** (Japanese).
3. A **Jump** line with two links: `[English](#english)` and `[日本語](#japanese)`.
4. A **Version / 版** line (see §6), **Normative for** or **Applies to**, and **Related** links.
5. `---`
6. `<a id="english"></a>` then `## English`, first line `[→ 日本語版へ](#japanese)`, then the English body.
7. `---`
8. `<a id="japanese"></a>` then `## 日本語`, first line `[→ To English](#english)`, then the Japanese body.
9. Optional `## Glossary / 用語` table at the end, bilingual.

The two halves say the same thing. The English half is the one translated into other languages later; the Japanese half is the one the GRDM team reviews. When they disagree, fix both in the same commit.

**Why HTML anchors?** GitHub and MkDocs generate heading anchors differently, and Japanese headings produce unstable ids. An explicit `<a id="...">` works in both. Anchor ids are lowercase ASCII with hyphens.

### 3. Writing style

- Target reader: a new employee on their first week. Assume they can use a terminal but have never seen GRDM.
- One idea per sentence. Prefer verbs. Avoid "etc." — list the items or say "and similar".
- **Every technical term gets a glossary note the first time it appears in a document**, in parentheses or as a bold-lead sentence, in words a primary-school child would understand. Example: "a *container* (a box that holds one program and everything it needs, so it runs the same on any computer)". Terms already explained in the shared glossary (`docs/reference/REF-01_Glossary.md`) still get a short note on first use, plus a link.
- Procedures are complete: every command the reader must type is in a fenced code block, with the directory it runs in and the expected result or how to check it.
- Follow the GitHub Docs style: sentence-case headings, bold for UI labels, `code` for file names, commands, and identifiers, admonitions as blockquotes starting with **Note:**, **Warning:**, or **Tip:**. Use emoji sparingly and only as section markers in README files (for example 🚀 Quick start, 🧭 Map, 📚 Documents, 🛡️ Security).
- Do not write "this document", "the above", "below"; link to the section instead.

### 4. Diagrams and data

- Diagrams are written in Markdown with **Mermaid** fenced blocks (```` ```mermaid ````). No binary images for architecture, flows, or sequences. Screenshots are allowed for UI guides and live under `images/` next to the document.
- Data shown in documents (lists of repositories, versions, test results, allow-lists) is written in **TOON** (Token-Oriented Object Notation: a compact, indentation-based text form of JSON that both people and AI read easily) in a ```` ```toon ```` fenced block. When a machine also needs the data, the canonical file is JSON or YAML next to it and the document says so; `grdm-dev manifest check` verifies that the TOON excerpt and the JSON agree.
- A ```` ```toon ```` block that mirrors a JSON file declares it with an HTML comment on the line before the block, for example `<!-- canonical: manifest/upstreams.json -->` (the path is relative to the repository root). A block that is only an illustrative example carries no declaration and the surrounding text says that it is an example, not canonical data.
- Tables are for comparisons with few columns. Long tabular data goes in TOON.

### 5. Links

- Links are relative paths within the repository. Never link to `master`; link to files on `develop` or to tagged versions.
- Each document links to: its parent index (`README.md` of its folder), the specification it implements or the decision it records, and the documents that depend on it ("Used by").
- Every folder has a `README.md` that lists its documents with one-line descriptions, in both languages. The root `README.md` is the table of contents of the whole repository and links to the HTML site at `site/index.html` (built by MkDocs, see [SPEC-02](02_installer_cli.md) for the `grdm-dev docs` command).
- Upstream GitHub links are allowed when they name a specific commit or PR; link to the private `-dev2027` repositories only by name, never by URL, in public-facing text.

### 6. Version header

- Versions live in the header, not in the file name (POL-02 §4). Format: `Version / 版: X.Y — YYYY-MM-DD. **Learned:** <what was discovered>. ／ <日本語>`.
- The newest version is first; older versions stay as one line each below it.
- The version line records **what was learned**, not what changed. Changing a document and bumping its version happen in the same commit.

### 7. File naming

| Kind | Name | Example |
|---|---|---|
| Specification | `nn_<topic>.md` (two digits) | `02_installer_cli.md` |
| Policy / Decision / Reference | `POL-nn_<Title>.md` / `ADR-nn_<Title>.md` / `REF-nn_<Title>.md` | `ADR-01_Integration_Repository_Placement.md` |
| Demo | `nn_<feature>.md`, sub-step `nn_m_<step>.md` | `20_core_install_mac_studio.md` |
| Hand-off / Review | `YYYY-MM-DD_<Title>.md`, reviews end with `_rN` | `2026-11-06_M1_Skeleton_Review_r1.md` |
| Guide | `docs/guides/<topic>/README.md` | `docs/guides/environment/README.md` |

### 8. Checks

`grdm-dev docs check` (and the `docs` GitHub Actions workflow) fails when a Markdown file:

- lacks the `english`/`japanese` anchors or the Jump line;
- has a relative link that does not resolve;
- has a ```` ```toon ```` block whose sibling JSON disagrees;
- has a glossary term from `REF-01` used without a note on first occurrence (warning, not failure, until M2);
- lacks a Version line in the header.

**What `tools/docs_check.py` checks today.** Until `grdm-dev docs check` exists ([SPEC-02 §3](02_installer_cli.md#english)), the helper `tools/docs_check.py`, run by the `docs` workflow, is the implementation. It checks exactly these points:

- the `english` and `japanese` anchors;
- the Jump line;
- the Version line;
- relative links: the file part before any `#fragment` must exist, and the fragment must resolve to an `<a id>` / `<a name>` anchor or a heading in the target file (same-file `#fragment` links are checked the same way);
- TOON SHA parity: when the line before a ```` ```toon ```` block carries `<!-- canonical: <path> -->`, every 40-character SHA in the block must appear in that JSON file (§4);
- the glossary-note warning: a `REF-01` term used without a note on first occurrence is reported as a warning, not a failure.

**Legacy-format exception.** Files kept in their historical form are not checked and are not rewritten to SPEC-06: `*.legacy.md`; sample code and sub-documents under `docs/guides/<topic>/` other than that guide's `README.md`; and the pointer files left at old paths (`Environment.md`, `SetupOsfOnEC2.md` and similar at the repository root), which only redirect to the new location. They are history, not current procedure. Every other Markdown file in the repository, including `manifest/README.md` and the installer README, is checked.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 1. 範囲

この規約は文書の「形」を定めるもので、内容は定めません。リポジトリ内のすべての Markdown に適用します。方針（`POL-nn`）、仕様（`00`〜`nn`）、決定の記録（`ADR-nn`）、参考（`REF-nn`）、実証、引継ぎ、レビュー、進捗、手引き、そして各フォルダの `README.md` です。

**用語注。** 「仕様」は、実装する人が必ず守るルールブックです。「方針」は、私たちの立場を書いたものです。「決定の記録」（ADR）は、なぜその道を選び、ほかを選ばなかったかを残すメモです。

### 2. ページの構成（この順番で必須）

1. `# <ID> <英語題> / <日本語題>` — H1 は一つだけ。
2. 引用ブロックに **Summary**（英語 1〜2 文）と **概要**（日本語）。
3. **Jump** 行に `[English](#english)` と `[日本語](#japanese)` の二つのリンク。
4. **Version / 版** 行（§6）、**Normative for** または **Applies to**、**Related** リンク。
5. `---`
6. `<a id="english"></a>` の次に `## English`、最初の行は `[→ 日本語版へ](#japanese)`、続いて英語本文。
7. `---`
8. `<a id="japanese"></a>` の次に `## 日本語`、最初の行は `[→ To English](#english)`、続いて日本語本文。
9. 末尾に任意で `## Glossary / 用語` の二言語の表。

英語と日本語は同じ内容を書きます。英語は後で他言語へ訳す元になり、日本語は GRDM チームがレビューする元になります。食い違ったら同じコミットで両方を直します。

**なぜ HTML のアンカーか。** GitHub と MkDocs は見出しの ID の作り方が違い、日本語見出しは不安定な ID になります。明示的な `<a id="...">` は両方で動きます。ID は小文字の ASCII とハイフンだけにします。

### 3. 文体

- 想定読者は入社一週目の新入社員。端末は使えるが GRDM は初めて、と考えます。
- 一文一義。動詞で書く。「など」は避け、項目を列挙するか「およびその類」と書く。
- **専門用語は、文書内で初めて出た箇所に必ず用語注を付ける。** 括弧または太字で始まる一文で、小学生にも分かる言葉で説明する。例:「コンテナ（一つのプログラムと必要なものを一箱に入れ、どのコンピュータでも同じように動かすための箱）」。共通用語集（`docs/reference/REF-01_Glossary.md`）にある語でも、初出では短い注とリンクを付ける。
- 手順は完結させる。読者が打つコマンドはすべてコードブロックに入れ、実行するディレクトリと、期待する結果か確認方法を添える。
- GitHub Docs のスタイルに従う。見出しは文頭のみ大文字（英語）、UI のラベルは太字、ファイル名・コマンド・識別子は `code`、注意書きは **Note:** / **Warning:** / **Tip:** で始まる引用ブロック。絵文字は README の節の目印に限って控えめに使う（例: 🚀 クイックスタート、🧭 地図、📚 文書、🛡️ セキュリティ）。
- 「本文書」「上記」「下記」は使わず、該当の節へリンクする。

### 4. 図とデータ

- 図は Markdown 内の **Mermaid** コードブロック（```` ```mermaid ````）で書く。構成図・流れ図・シーケンス図に画像ファイルを使わない。UI の手引きに限りスクリーンショットを許し、文書と同じ場所の `images/` に置く。
- 文書に載せるデータ（リポジトリ一覧、バージョン、試験結果、許容リスト）は **TOON**（Token-Oriented Object Notation。JSON を字下げで表した短い文字形式で、人も AI も読みやすい）で ```` ```toon ```` のブロックに書く。機械も読むデータは、隣に JSON か YAML の正本を置き、文書にそう記す。`grdm-dev manifest check` が TOON の抄録と JSON の一致を確かめる。
- JSON ファイルを写す ```` ```toon ```` ブロックは、その直前の行に HTML コメントで正本を宣言する。例: `<!-- canonical: manifest/upstreams.json -->`（パスはリポジトリのルートからの相対）。説明のための例にすぎないブロックには宣言を付けず、周りの文で「例であり正本ではない」と書く。
- 表は列の少ない比較に使う。長い表形式のデータは TOON にする。

### 5. リンク

- リンクはリポジトリ内の相対パス。`master` へはリンクせず、`develop` 上のファイルかタグ付きの版へリンクする。
- 各文書は次へリンクする: 親の索引（そのフォルダの `README.md`）、実装する仕様または記録する決定、そしてこの文書に依存する文書（「Used by」）。
- 各フォルダに `README.md` を置き、文書を一行説明付きで二言語で列挙する。ルートの `README.md` はリポジトリ全体の目次で、MkDocs が生成する HTML（`site/index.html`。コマンドは [SPEC-02](02_installer_cli.md) の `grdm-dev docs`）へリンクする。
- 上流 GitHub へのリンクは、特定のコミットか PR を指すときだけ許す。非公開の `-dev2027` リポジトリは、外向けの文章では名前だけを書き URL は書かない。

### 6. 版のヘッダ

- 版はファイル名でなくヘッダに持つ（POL-02 §4）。形式: `Version / 版: X.Y — YYYY-MM-DD. **Learned:** <分かったこと>. ／ <日本語>`。
- 最新の版を先頭に置き、過去の版は一行ずつ下に残す。
- 版の行には「何を変えたか」でなく **「何が分かったか」** を書く。文書の変更と版の更新は同じコミットで行う。

### 7. ファイル名

| 種別 | 命名 | 例 |
|---|---|---|
| 仕様 | `nn_<題>.md`（2 桁） | `02_installer_cli.md` |
| 方針・決定・参考 | `POL-nn_<題>.md` / `ADR-nn_<題>.md` / `REF-nn_<題>.md` | `ADR-01_Integration_Repository_Placement.md` |
| 実証 | `nn_<機能>.md`、枝番 `nn_m_<手順>.md` | `20_core_install_mac_studio.md` |
| 引継ぎ・レビュー | `YYYY-MM-DD_<題>.md`、レビューは末尾 `_rN` | `2026-11-06_M1_Skeleton_Review_r1.md` |
| 手引き | `docs/guides/<題>/README.md` | `docs/guides/environment/README.md` |

### 8. 検査

`grdm-dev docs check`（と GitHub Actions の `docs` ワークフロー）は、次の Markdown を不合格にする。

- `english` / `japanese` のアンカーか Jump 行がない。
- 解決できない相対リンクがある。
- ```` ```toon ```` ブロックと隣の JSON が一致しない。
- `REF-01` の用語が初出で注なしに使われている（M2 までは警告、以後は不合格）。
- ヘッダに Version 行がない。

**`tools/docs_check.py` が今日検査すること。** `grdm-dev docs check` ができるまで（[SPEC-02 §3](02_installer_cli.md#japanese)）、`docs` ワークフローが動かす補助ツール `tools/docs_check.py` が実装です。検査するのは次の点に限ります。

- `english` と `japanese` のアンカー。
- Jump 行。
- Version 行。
- 相対リンク。`#フラグメント` より前のファイル部分が存在し、フラグメントが相手のファイルの `<a id>` / `<a name>` アンカーか見出しに解決しなければならない（同じファイル内の `#フラグメント` も同様に確かめる）。
- TOON の SHA 一致。```` ```toon ```` ブロックの直前の行に `<!-- canonical: <パス> -->` の宣言があるとき、ブロック内の 40 文字の SHA がすべてその JSON に現れること（§4）。
- 用語注の警告。`REF-01` の用語が初出で注なしに使われていれば警告として報告する（不合格ではない）。

**旧形式の例外。** 歴史的な形のまま残すファイルは検査せず、SPEC-06 の形にも書き直さない。`*.legacy.md`、`docs/guides/<題>/` の下にあるその手引きの `README.md` 以外のサンプルコードと下位文書、そして旧パスに残した誘導ファイル（リポジトリのルートの `Environment.md`、`SetupOsfOnEC2.md` およびその類。新しい置き場へ案内するだけのもの）です。これらは歴史であり、現行の手順ではありません。それ以外のリポジトリ内の Markdown は、`manifest/README.md` と installer の README を含めてすべて検査します。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Markdown | A plain-text way of writing documents where `#` makes a heading and `-` makes a list. | `#` で見出し、`-` で箇条書きになる、文字だけで書く文書の書き方。 |
| Anchor | A bookmark inside a page that a link can jump to. | ページの中の「しおり」。リンクで飛べる。 |
| Mermaid | A way to draw diagrams by typing text instead of drawing with a mouse. | マウスで描く代わりに文字で図を描く仕組み。 |
| TOON | A compact text form of JSON data, easy for people and AI to read. | JSON のデータを短く字下げで書いた形。人にも AI にも読みやすい。 |
| MkDocs | A tool that turns Markdown files into a website. | Markdown のファイルを Web サイトに変える道具。 |
