# Admin Addon Guide / 管理者アドオンガイド

> **Summary:** Guide to creating administrator-level RDM addons with institutional management features
> **概要:** 機関管理機能を持つ管理者レベルの RDM アドオンを作成する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/admin-addon/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md) · [Skeleton Guide](../skeleton/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to create administrator-level RDM addons that include:

- **Institutional management**: Control addon availability per institution
- **Admin Notes**: Display special messages to users from administrators

The administrator interface runs on a separate port (default 8001) and allows institutional administrators to manage addon settings.

### Prerequisites

- Basic understanding of Python, Django, and Django admin interface
- The development environment set up following the [Environment Guide](../environment/README.md)
- Completed the [Skeleton Addon Guide](../skeleton/README.md) and [API Guide](../api/README.md)

### Quick start

1. Create your addon using the skeleton as a base
2. Add institutional management features to your addon
3. Create admin templates and JavaScript configurations
4. Deploy with admin services (`admin`, `admin_assets`)
5. Configure institutional administrators' access

### Legacy content

The legacy admin addon instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、以下の機能を持つ管理者レベルの RDM アドオンを作成する方法を示します:

- **機関管理**: 機関ごとにアドオンの利用可否を制御
- **管理者ノート**: 管理者からユーザーに特別なメッセージを表示

管理者画面は別のポート（デフォルト 8001）で実行され、機関管理者がアドオン設定を管理できます。

### 前提条件

- Python, Django, Django 管理画面の基本的な理解
- [環境ガイド](../environment/README.md)に従って開発環境をセットアップしていること
- [スケルトンアドオンガイド](../skeleton/README.md)と [API ガイド](../api/README.md)を完了していること

### クイックスタート

1. スケルトンをベースにアドオンを作成する
2. アドオンに機関管理機能を追加する
3. 管理者テンプレートと JavaScript 設定を作成する
4. admin サービス（admin, admin_assets）でデプロイする
5. 機関管理者のアクセスを設定する

### 過去のコンテンツ

過去の管理者アドオンの手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Institutional management | Controlling which addons are available to each institution. | 各機関に対してどのアドオンを利用可能にするかを制御すること。 |
| Admin interface | A separate page where institutional administrators manage settings. | 機関管理者が設定を管理するための別のページ。 |
| Admin Notes | Special messages that administrators can display to users. | 管理者がユーザーに表示できる特別なメッセージ。 |
| Institution | An organization (like a university or company) that uses RDM. | RDM を使用する組織（大学や会社など）。 |

