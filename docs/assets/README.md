# Site Assets / サイト用の部品

> **Summary:** Third-party and local files that the MkDocs site loads. Kept in the repository so the HTML version works without any external network.
> **概要:** MkDocs のサイトが読み込む外部・自作のファイル。外部ネットワークなしで HTML 版が動くよう、リポジトリに同梱する。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05. **Learned:** loading Mermaid from a CDN made every generated page depend on an external host (Semgrep flagged 43 pages for missing integrity), so the library is vendored here instead. ／ Mermaid を CDN から読み込むと生成ページ全部が外部ホストに依存する（Semgrep が 43 ページを integrity 欠落として検出）と分かり、ここに同梱に変えた。
- Related: [docs/README.md](../README.md) · [SPEC-06 §4](../spec/06_documentation_conventions.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

| File | Origin | License | Note |
|---|---|---|---|
| `mermaid.min.js` | mermaid 11.4.1, `https://unpkg.com/mermaid@11.4.1/dist/mermaid.min.js` | MIT | Draws diagrams written as text (Mermaid). Do not edit. Update by replacing the file and this row. |
| `mermaid-init.js` | written here | MIT (this repository) | Starts Mermaid on page load. |

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

| ファイル | 出所 | ライセンス | 備考 |
|---|---|---|---|
| `mermaid.min.js` | mermaid 11.4.1、`https://unpkg.com/mermaid@11.4.1/dist/mermaid.min.js` | MIT | 文字で書いた図（Mermaid）を描く。編集しない。更新はファイルとこの行を差し替える。 |
| `mermaid-init.js` | 本リポジトリで作成 | MIT（本リポジトリ） | ページ読み込み時に Mermaid を起動する。 |
