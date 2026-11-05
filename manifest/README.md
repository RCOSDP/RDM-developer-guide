# Upstream Manifest / 上流マニフェスト

> **Summary:** The manifest is the single source of truth for what the installer builds: every component, its upstream repositories pinned to exact commits, and the pull requests we adopt. This page explains how to read and update it.  
> **概要:** マニフェストは「インストーラーが何を組むか」の唯一の正本です。全部品、固定したコミットの上流、採用する PR を示します。読み方と更新方法を説明します。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 1.2 — 2026-11-06. **Learned:** a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ 用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
- Version / 版: 1.1 — 2026-11-05. **Learned:** an address quoted as a "never write this" example is still published; the rule has to be stated in words without the address. ／ 「書いてはいけない例」として載せたアドレスも公開になる。規則はアドレスを含めず言葉で書かなければならないと分かった。
- Version / 版: 1.0 — 2026-11-05. **Learned:** the manifest must be exact because "the latest" is ambiguous; only pinned SHAs define what "consistent" means. ／ 「最新」は曖昧なので、正確なマニフェストが必要です。SHA を固定して初めて「矛盾なく」が定義できます。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### What is upstreams.json?

`manifest/upstreams.json` is the canonical file that tells the installer exactly which repositories to combine and at which commit SHA each should be pinned (a commit is one saved step of changes with a message saying why; its SHA is the fingerprint that names that one commit; see [REF-01](../docs/reference/REF-01_Glossary.md)). It is JSON (UTF-8, two-space indent, keys sorted).

### What is upstreams.toon?

`manifest/upstreams.toon` is a human-readable excerpt of the manifest in TOON (a compact, indentation-based text form of JSON that both people and AI read easily; see [REF-01](../docs/reference/REF-01_Glossary.md)) format. It is generated automatically from `upstreams.json` by running:

```sh
grdm-dev manifest toon
```

The `toon` file must always match the JSON exactly.

### How do I change them?

The manifest is updated by opening a pull request (a proposed change waiting for someone to review and accept it; see [REF-01](../docs/reference/REF-01_Glossary.md)):

1. Update `upstreams.json` with the new SHA values for each upstream repository.
2. Run `grdm-dev manifest toon` to regenerate `upstreams.toon`.
3. Commit both files.
4. Open a PR (short for pull request; see [REF-01](../docs/reference/REF-01_Glossary.md)) with the changes.

Changes follow [SPEC-01](../docs/spec/01_manifest.md) rules.
Always run `tools/manifest_check.py` before committing to verify correctness.

### The "names and SHAs only" rule

This repository is public. The manifest contains **repository names and SHAs only**:

- Write the bare repository name, for example `RDM-osf.io-dev2027`.
- Do not write the address of a private repository in any form: no web address, no Git clone address, and not even as an example of what to avoid. Write only its name.
- Do not write access tokens, API keys, or passwords.

`tools/manifest_check.py` rejects a `repo` or `integration_repo` value that looks like an address ([SPEC-01 §4](../docs/spec/01_manifest.md#english), rule 5), and the CI (continuous integration: automatic checks on every change; see [REF-01](../docs/reference/REF-01_Glossary.md)) secret scanner (`gitleaks`) fails the PR if it finds secret-like content.

### How to run the validation tool

```sh
# Run from the repository root
python3 tools/manifest_check.py
```

Exit code:
- `0`: All checks passed.
- `1`: One or more validation errors were found.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### upstreams.json とは？

`manifest/upstreams.json` は、インストーラーに「どのリポジトリを、どのコミット SHA で組むか」を正確に伝える正本ファイルです（コミットは理由のメッセージ付きで保存した変更の一歩、SHA はそのコミット一つを指す指紋。[REF-01](../docs/reference/REF-01_Glossary.md)）。JSON（UTF-8、字下げ 2 つ、キーは並べ替え済み）で書きます。

### upstreams.toon とは？

`manifest/upstreams.toon` は、TOON 形式（JSON を人が読みやすい短い文字形式にしたもの。[SPEC-06 §4](../docs/spec/06_documentation_conventions.md#4-diagrams-and-data)）のマニフェスト抄録です。次のように自動生成されます：

```sh
grdm-dev manifest toon
```

`toon` ファイルは常に JSON と一致していなければなりません。

### どうやって更新する？

マニフェストはプルリクエスト（誰かが見て受け入れるのを待っている変更の提案。[REF-01](../docs/reference/REF-01_Glossary.md)）で更新します：

1. `upstreams.json` を上流リポジトリの新しい SHA で更新する。
2. `grdm-dev manifest toon` を実行して `upstreams.toon` を再生成する。
3. 両方のファイルをコミットする。
4. 変更内容の PR（プルリクエストの略。[REF-01](../docs/reference/REF-01_Glossary.md)）を開く。

変更は [SPEC-01](../docs/spec/01_manifest.md) の規則に従います。コミットする前に `tools/manifest_check.py` を実行して正しいか検証してください。

### 「名前と SHA だけ」の規則

このリポジトリは公開です。マニフェストには**リポジトリ名と SHA だけ**を書きます：

- リポジトリの裸の名前だけを書く。例: `RDM-osf.io-dev2027`。
- 非公開リポジトリのアドレスは、どんな形でも書かない。Web のアドレスも、Git のクローン用アドレスも、「書いてはいけない例」としても書かない。名前だけを書く。
- アクセストークン、API キー、パスワードを書かない。

`tools/manifest_check.py` はアドレスの形をした `repo` や `integration_repo` の値を不正とし（[SPEC-01 §4](../docs/spec/01_manifest.md#japanese) の規則 5）、CI（continuous integration。変更ごとに自動で走る検査。[REF-01](../docs/reference/REF-01_Glossary.md)）の秘密スキャナー（`gitleaks`）は秘密に見える内容を見つけると PR を不合格にします。

### 検査ツールの実行方法

```sh
# リポジトリルートで実行
python3 tools/manifest_check.py
```

終了コード：
- `0`: 全検査合格。
- `1`: 一つ以上の検証エラーあり。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Manifest | A packing list that says exactly what goes into the build. | ビルドに何が入るかを正確に書いた明細書。 |
| SHA | The 40-character fingerprint that names one commit. | 一つのコミットを指す 40 文字の指紋。 |
| TOON | A compact text form of JSON data, easy for people and AI to read. | JSON のデータを短く字下げで書いた形。人にも AI も読みやすい。 |
| Upstream | The original repository we copy code from. | コードを写してくる元のリポジトリ。 |
