# Screen Expansion Addon / 画面拡張アドオン

> **Summary:** Guide to creating RDM screen expansion addons with dashboard widgets and page tabs
> **概要:** ダッシュボードウィジェットとページタブを持つ RDM 画面拡張アドオンを作成する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/screen-expansion/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md) · [Skeleton Guide](../skeleton/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to create RDM screen expansion addons that add:

- **Dashboard widgets**: Small UI elements on the project dashboard
- **Page tabs**: New pages accessible from the project navigation bar

Screen expansion addons use Ember.js for the frontend and Django for the backend.

### Prerequisites

- Basic understanding of Python, Django, and JavaScript
- The development environment set up following the [Environment Guide](../environment/README.md)
- Completed the [Skeleton Addon Guide](../skeleton/README.md)

### Quick start

1. Create your addon using the skeleton as a base
2. Add widget template and configuration files
3. Add Ember.js page tab (route, controller, template)
4. Configure RDM to display your widget and tab
5. Test both the widget and page tab

### Legacy content

The legacy screen expansion addon instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、以下の機能を持つ RDM 画面拡張アドオンを作成する方法を示します:

- **ダッシュボードウィジェット**: プロジェクトダッシュボード上の小さな UI 要素
- **ページタブ**: プロジェクトのナビゲーションバーからアクセスできる新しいページ

画面拡張アドオンは、フロントエンドに Ember.js、バックエンドに Django を使用します。

### 前提条件

- Python, Django, JavaScript の基本的な理解
- [環境ガイド](../environment/README.md)に従って開発環境をセットアップしていること
- [スケルトンアドオンガイド](../skeleton/README.md)を完了していること

### クイックスタート

1. スケルトンをベースにアドオンを作成する
2. ウィジェットのテンプレートと設定ファイルを追加する
3. Ember.js のページタブ（ルート、コントローラー、テンプレート）を追加する
4. RDM を設定してウィジェットとタブを表示する
5. ウィジェットとページタブの両方をテストする

### 過去のコンテンツ

過去の画面拡張アドオンの手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Screen expansion addon | An addon that adds new UI elements and pages to RDM. | RDM に新しい UI 要素とページを追加するアドオン。 |
| Dashboard widget | A small UI element displayed on the project dashboard. | プロジェクトダッシュボードに表示される小さな UI 要素。 |
| Page tab | A new page accessible from the project navigation bar. | プロジェクトのナビゲーションバーからアクセスできる新しいページ。 |
| Ember.js | A JavaScript framework for building interactive web applications. | インタラクティブなウェブアプリケーションを構築するための JavaScript フレームワーク。 |

