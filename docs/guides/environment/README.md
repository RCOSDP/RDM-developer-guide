# Environment / 環境設定と開発環境

> **Summary:** Guide to setting up the development environment for GakuNin RDM using Docker Compose and the 2027 installer
> **概要:** GakuNin RDM の開発環境を Docker Compose と 2027 インストーラーで構築する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/environment/`
- Related: [SPEC-02 Installer CLI](../../spec/02_installer_cli.md) · [ADR-02 Network Model](../../decisions/ADR-02_Network_Model.md) · [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to set up the GakuNin RDM development environment.

> **Warning:** The loopback alias `192.168.168.167` and `docker-compose.override.yml` method described below are the OLD way. The 2027 installer uses a Compose internal network and `127.0.0.1` only. See [ADR-02 Network Model](../../decisions/ADR-02_Network_Model.md) and [SPEC-02 Installer CLI](../../spec/02_installer_cli.md).

For the current method, use the 2027 installer (`installer/install.sh`) which creates a self-contained environment under `runtime/` with no host network changes.

### Docker Compose services

The development environment uses Docker Compose to run multiple microservices:

- **Data storage & sharing services:** PostgreSQL, Elasticsearch, RabbitMQ, MongoDB
- **Core services:** web server, API server, admin interface, worker (RDM-osf.io), WaterButler file storage service
- **UI services:** Ember frontend, Modular File Renderer (MFR), Unoconv file converter
- **Test authentication service:** FakeCAS or CAS-Overlay for OAuth testing

> In GakuNin RDM, the `preprints` and `registries` services are not used.

### Quick start

1. Clone this repository
2. Run `./installer/install.sh --yes`
3. Open http://127.0.0.1:5000 in your browser

> This command is available from milestone M2.

### Legacy content

The legacy Docker Compose instructions (loopback alias, manual setup) are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、GakuNin RDM の開発環境を構築する方法を示します。

> **警告:** 以下に説明する ループバックエイリアス `192.168.168.167` と `docker-compose.override.yml` の方法は、昔の方法です。2027 インストーラーは Compose の内部ネットワークと `127.0.0.1` のみを使用します。詳細は [ADR-02 ネットワークモデル](../../decisions/ADR-02_Network_Model.md) と [SPEC-02 インストーラー CLI](../../spec/02_installer_cli.md) を参照してください。

現在の方法では、`installer/install.sh` コマンドを使用して、ホストのネットワーク設定を変更せずに `runtime/` ディレクトリ内に自己完結型の環境を作成します。

### Docker Compose サービス

開発環境は、複数のマイクロサービスを Docker Compose で実行します:

- **データ保存・共有サービス:** PostgreSQL, Elasticsearch, RabbitMQ, MongoDB
- **コアサービス:** Webサーバー、APIサーバー、管理画面、ワーカー (RDM-osf.io)、WaterButler ファイルストレージサービス
- **UI サービス:** Ember フロントエンド、Modular File Renderer (MFR)、Unoconv ファイル変換サービス
- **テスト認証サービス:** FakeCAS または CAS-Overlay (OAuth テスト用)

> GakuNin RDM では、`preprints` と `registries` サービスは使用しません。

### クイックスタート

1. このリポジトリを clone する
2. `./installer/install.sh --yes` を実行する
3. ブラウザで http://127.0.0.1:5000 を開く

> このコマンドは M2 マイルストーンから利用可能です。

### 過去のコンテンツ

過去の Docker Compose の手順（ループバックエイリアス、手動設定）は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Docker Compose | A tool that runs multiple containers together using one configuration file. | 1つの設定ファイルで複数のコンテナを一緒に実行するツール。 |
| Microservice | A small program that does one job and works with other programs over the network. | 1つの仕事をする小さなプログラムで、ネットワーク経由で他のプログラムと連携します。 |
| Loopback alias | A fake IP address added to your computer so programs can talk to each other. | プログラム同士が通信できるようにコンピュータに追加する仮の IP アドレス。 |
| Compose internal network | A private network created by Docker Compose so containers can talk without changing your computer. | Docker Compose が作るプライベートネットワークで、コンピュータを変更せずにコンテナ同士が通信できます。 |
