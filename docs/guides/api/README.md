# API Guide / API ユーガイド

> **Summary:** Guide to using and exposing APIs in RDM addons
> **概要:** RDM アドオンで API を使用および公開する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/api/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md) · [Skeleton Guide](../skeleton/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide explains how to:

- **Expose your addon's functionality via API**: Allow other systems to access your addon
- **Use existing APIs in your addon**: Interact with RDM and other addons

RDM addons can be accessed via HTTP(S) RESTful APIs, enabling integration with external systems and other RDM addons.

### Prerequisites

- Basic understanding of Python, Django, and REST APIs
- The development environment set up following the [Environment Guide](../environment/README.md)
- Completed the [Skeleton Addon Guide](../skeleton/README.md)

### Quick start

1. Define Routes and Views in your addon to create API endpoints
2. Use decorators to control access (authentication, permissions)
3. Test your API with curl or Postman
4. Integrate with external systems using standard HTTP requests

### Legacy content

The legacy API guide instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドでは、以下の方法を説明します:

- **アドオンの機能を API で公開**: 他のシステムがアドオンにアクセスできるようにする
- **既存の API をアドオンで使用**: RDM や他のアドオンと連携する

RDM アドオンは HTTP(S) RESTful API でアクセス可能で、外部システムや他の RDM アドオンとの連携ができます。

### 前提条件

- Python, Django, REST API の基本的な理解
- [環境ガイド](../environment/README.md)に従って開発環境をセットアップしていること
- [スケルトンアドオンガイド](../skeleton/README.md)を完了していること

### クイックスタート

1. アドオンでルートとビューを定義して API エンドポイントを作成する
2. デコレーターを使用してアクセスを制御（認証、権限）
3. curl や Postman で API をテストする
4. 標準的な HTTP リクエストを使用して外部システムと連携する

### 過去のコンテンツ

過去の API ガイドの手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| API (Application Programming Interface) | A way for programs to talk to each other using HTTP requests. | プログラムが HTTP リクエストを使用して通信する方法。 |
| RESTful API | An API that follows standard HTTP methods (GET, POST, PUT, DELETE). | 標準的な HTTP メソッド（GET, POST, PUT, DELETE）に従った API。 |
| Decorator | A special marker that controls who can access an API endpoint. | API エンドポイントへのアクセスを制御する特別なマーク。 |
| Authentication | Verifying who is making the API request (like a username and password). | API リクエストを作成した人が誰かを確認すること（ユーザー名とパスワードのようなもの）。 |
| Authorization | Checking what the user is allowed to do after logging in. | ログインした後のユーザーが何をできるかを確認すること。 |

