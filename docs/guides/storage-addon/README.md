# Storage Addon / ストレージアドオン

> **Summary:** Guide to creating an RDM storage addon that connects to external storage services
> **概要:** 外部ストレージサービスに接続する RDM ストレージアドオンを作成する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/storage-addon/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md) · [Skeleton Guide](../skeleton/README.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to create an RDM storage addon that connects to external storage services like AWS S3 or MinIO. Storage addons consist of two parts:

- **Addon** (runs on OSF.io): Manages user and project settings
- **Provider** (runs on WaterButler): Handles actual storage access

The Addon receives authentication credentials and settings from users, while the Provider uses this information to communicate with the actual storage service.

### Prerequisites

- Basic understanding of Python and Django
- The development environment set up following the [Environment Guide](../environment/README.md)
- Completed the [Skeleton Addon Guide](../skeleton/README.md)

### Quick start

1. Create your addon using the skeleton as a base
2. Implement the Provider class for your storage service
3. Configure authentication and authorization between Addon and Provider
4. Test file operations (upload, download, delete)
5. Deploy and test with your storage service

### Legacy content

The legacy storage addon instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、AWS S3 や MinIO のような外部ストレージサービスに接続する RDM ストレージアドオンを作成する方法を示します。ストレージアドオンは以下の2つの部分から構成されます:

- **アドオン** (OSF.io 上で実行): ユーザーとプロジェクトの設定を管理
- **プロバイダ** (WaterButler 上で実行): 実際のストレージアクセスを処理

アドオンがユーザーから認証情報と設定を受け取り、プロバイダがその情報を使用して実際のストレージサービスと通信します。

### 前提条件

- Python と Django の基本的な理解
- [環境ガイド](../environment/README.md)に従って開発環境をセットアップしていること
- [スケルトンアドongaon ガイド](../skeleton/README.md)を完了していること

### クイックスタート

1. スケルトンをベースにアドオンを作成する
2. ストレージサービス用のプロバイダクラスを実装する
3. アドオンとプロバイダ間の認証と認可を設定する
4. ファイル操作（アップロード、ダウンロード、削除）をテストする
5. デプロイしてストレージサービスでテストする

### 過去のコンテンツ

過去のストレージアドオンの手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Storage addon | An addon that connects RDM to external storage services like AWS S3. | AWS S3 のような外部ストレージサービスに RDM を接続するアドオン。 |
| Provider | A component that actually communicates with the storage service. | ストレージサービスと実際に通信するコンポーネント。 |
| Authentication | The process of verifying who you are (like a username and password). | あなたが誰であるかを確認するプロセス（ユーザー名とパスワードのようなもの）。 |
| Authorization | The process of checking what you are allowed to do after logging in. | ログインした後、あなたが何をできるかを確認するプロセス。 |

