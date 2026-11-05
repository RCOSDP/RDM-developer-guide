# Upstream Manifest / 上流マニフェスト

> **Summary:** The manifest is the single source of truth for what the installer builds: every component, its upstream repositories pinned to exact commits, and the pull requests we adopt. This page explains how to read and update it.  
> **概要:** マニフェストは「インストーラーが何を組むか」の唯一の正本です。全部品、固定したコミットの上流、採用する PR を示します。読み方と更新方法を説明します。

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 1.0 — 2026-11-05. **Learned:** the manifest must be exact because "the latest" is ambiguous; only pinned SHAs define what "consistent" means. ／ 「最新」は曖昧なので、正確なマニフェストが必要です。SHA を固定して初めて「矛盾なく」が定義できます。

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### What is upstreams.json?

`manifest/upstreams.json` is the canonical file that tells the installer exactly which repositories to combine and at which commit SHA each should be pinned. It is JSON (UTF-8, two-space indent, keys sorted).

### What is upstreams.toon?

`manifest/upstreams.toon` is a human-readable excerpt of the manifest in TOON format (a compact, indentation-based text form of JSON that both people and AI read easily). It is generated automatically from `upstreams.json` by running:

```sh
grdm-dev manifest toon
```

The `toon` file must always match the JSON exactly.

### How do I change them?

The manifest is updated by opening a pull request:

1. Update `upstreams.json` with the new SHA values for each upstream repository.
2. Run `grdm-dev manifest toon` to regenerate `upstreams.toon`.
3. Commit both files.
4. Open a PR with the changes.

Changes follow [SPEC-01](../docs/spec/01_manifest.md) rules.
Always run `tools/manifest_check.py` before committing to verify correctness.

### The "names and SHAs only" rule

This repository is public. The manifest contains **repository names and SHAs only**:

- ✅ Write: `RDM-osf.io-dev2027`
- ❌ Never write: `https://github.com/rcosdp/RDM-osf.io-dev2027`
- ❌ Never write: `git@github.com:rcosdp/RDM-osf.io-dev2027.git`
- ❌ Never write: access tokens, API keys, or passwords

The CI secret scanner (`gitleaks`) will fail your PR if it finds any secret-like content.

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

`manifest/upstreams.json` は、インストーラーに「どのリポジトリを、どのコミット SHA で組むか」を正確に伝える正本ファイルです。JSON（UTF-8、字下げ 2 つ、キーは並べ替え済み）で書きます。

### upstreams.toon とは？

`manifest/upstreams.toon` は、TOON 形式（JSON を人が読みやすい短い文字形式にしたもの。[SPEC-06 §4](../docs/spec/06_documentation_conventions.md#4-diagrams-and-data)）のマニフェスト抄録です。次のように自動生成されます：

```sh
grdm-dev manifest toon
```

`toon` ファイルは常に JSON と一致していなければなりません。

### どうやって更新する？

マニフェストはプルリクエストで更新します：

1. `upstreams.json` を上流リポジトリの新しい SHA で更新する。
2. `grdm-dev manifest toon` を実行して `upstreams.toon` を再生成する。
3. 両方のファイルをコミットする。
4. 変更内容の PR を開く。

変更は [SPEC-01](../docs/spec/01_manifest.md) の規則に従います。コミットする前に `tools/manifest_check.py` を実行して正しいか検証してください。

### 「名前と SHA だけ」の規則

このリポジトリは公開です。マニフェストには**リポジトリ名と SHA だけ**を書きます：

- ✅ 書く: `RDM-osf.io-dev2027`
- ❌決して書かない: `https://github.com/rcosdp/RDM-osf.io-dev2027`
- ❌決して書かない: `git@github.com:rcosdp/RDM-osf.io-dev2027.git`
- ❌決して書かない: アクセストークン、API キー、パスワード

CI の秘密スキャナー（`gitleaks`）が秘密っぽい内容を見つけると、PR は不合格になります。

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
