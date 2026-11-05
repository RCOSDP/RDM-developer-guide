# Skeleton Addon / スケルトンアドオン

> **Summary:** Guide to creating your first RDM addon using the skeleton template
> **概要:** スケルトンテンプレートを使用して最初の RDM アドオンを作成する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/skeleton/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md) · [Environment Guide](../environment/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to create your first RDM addon using the skeleton template. A skeleton addon is a simple addon with basic features that you can customize to build your own functionality.

The skeleton addon has the following capabilities:

- Can be enabled in any project
- Has a parameter `param_1` that can be set differently for each project
- The `param_1` parameter can be configured in the project's addon settings page

### Prerequisites

- A fork of the [RDM-osf.io repository](https://github.com/RCOSDP/RDM-osf.io)
- The development environment set up following the [Environment Guide](../environment/README.md)

### Quick start

1. Copy the skeleton code to `addons/your-addon-name`
2. Update the addon name in all required files
3. Modify RDM code to register your addon (addons.json, Dockerfile, etc.)
4. Run migrations and restart services
5. Enable your addon in a project and test it

### Legacy content

The legacy skeleton addon instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、スケルトンテンプレートを使用して最初の RDM アドオンを作成する方法を示します。スケルトンアドオンは、カスタマイズして独自の機能を構築できる基本的な機能を持つシンプルなアドオンです。

スケルトンの機能は以下の通りです:

- 任意のプロジェクトで有効化可能
- `param_1` というパラメータを持ち、プロジェクトごとに異なる値を設定可能
- `param_1` パラメータはプロジェクトのアドオン設定画面で設定可能

### 前提条件

- [RDM-osf.io リポジトリ](https://github.com/RCOSDP/RDM-osf.io)をフォークしていること
- [環境ガイド](../environment/README.md)に従って開発環境をセットアップしていること

### クイックスタート

1. スケルトンコードを `addons/アドオン名` にコピーする
2. すべての必要なファイルでアドオン名を更新する
3. RDM のコードを修正してアドオンを登録する（addons.json, Dockerfile など）
4. マイグレーションを実行してサービスを再起動する
5. プロジェクトでアドオンを有効化してテストする

### 過去のコンテンツ

過去のスケルトンアドオンの手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Addon | A small program that adds new features to RDM. | RDM に新しい機能を追加する小さなプログラム。 |
| Skeleton | A template or sample code that you can customize to build your own program. | 独自のプログラムを構築するためにカスタマイズできるテンプレートやサンプルコード。 |
| Parameter | A value that you can change to modify how the addon works. | アドオンの動作を変更するために変更できる値。 |
| Migration | A script that updates the database when you change the data structure. | データ構造を変更したときにデータベースを更新するスクリプト。 |

