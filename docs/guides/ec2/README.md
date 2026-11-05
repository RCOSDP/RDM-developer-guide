# EC2 Development Environment / EC2 での開発環境

> **Summary:** Guide to setting up the GakuNin RDM development environment on Amazon EC2
> **概要:** Amazon EC2 に GakuNin RDM の開発環境を構築する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-06. **Learned:** a glossary term is only explained for the reader when its note and REF-01 link sit at the first prose use, counting lower-case and plural forms, so first-use notes with links were added in both halves (SPEC-06 §3). ／ 用語注と REF-01 へのリンクは、小文字や複数形も含めた本文の初出に置かなければ読者に届かないと分かったため、英和両方の初出にリンク付きの用語注を補った（SPEC-06 §3）。
- Version / 版: 0.1 — 2026-11-05
- Normative for: `docs/guides/ec2/`
- Related: [SPEC-06 Documentation Conventions](../../spec/06_documentation_conventions.md)

---

<a id="english"></a>
## English

[→ 日本語版へ](#japanese)

### Overview

This guide shows how to set up the GakuNin RDM (GakuNin is Japan's academic network for logging in with a university account; see [REF-01](../../reference/REF-01_Glossary.md)) development environment on an Amazon EC2 instance.

### Prerequisites

- An AWS account
- Basic familiarity with Linux command-line tools
- SSH access to your EC2 instance

### Quick start on EC2

1. Launch an EC2 instance (Ubuntu 22.04 or Amazon Linux 2 recommended)
2. Install Docker (the tool that builds images and runs containers; see [REF-01](../../reference/REF-01_Glossary.md)) and Docker Compose (a tool that starts many containers together from one file; see [REF-01](../../reference/REF-01_Glossary.md))
3. Clone this repository
4. Run `./installer/install.sh --yes`
5. Configure your EC2 security group to allow HTTP (port 80) and SSH (port 22)
6. Open http://localhost:5000 (localhost means your own computer; see [REF-01](../../reference/REF-01_Glossary.md)) in your browser

> This command is available from milestone M2.

### Legacy content

The legacy EC2 setup instructions are kept verbatim in `README.legacy.md` for reference and will be rewritten per milestone.

---

<a id="japanese"></a>
## 日本語

[→ To English](#english)

### 概要

このガイドは、Amazon EC2 上に GakuNin RDM（GakuNin＝学認。大学のアカウントでログインするための日本の学術ネットワーク。[REF-01](../../reference/REF-01_Glossary.md)）の開発環境を構築する方法を示します。

### 前提条件

- AWS アカウント
- Linux コマンドラインツールの基本的な使い方の理解
- EC2 インスタンスへの SSH アクセス

### EC2 でのクイックスタート

1. EC2 インスタンスを起動する（Ubuntu 22.04 または Amazon Linux 2 を推奨）
2. Docker（イメージを作りコンテナを動かす道具。[REF-01](../../reference/REF-01_Glossary.md)）と Docker Compose（一つのファイルから多くのコンテナをまとめて起こす道具。[REF-01](../../reference/REF-01_Glossary.md)）をインストールする
3. このリポジトリを clone する
4. `./installer/install.sh --yes` を実行する
5. EC2 のセキュリティグループで HTTP (ポート 80) と SSH (ポート 22) を許可する
6. ブラウザで http://localhost:5000（localhost は自分の計算機のこと。[REF-01](../../reference/REF-01_Glossary.md)）を開く

> このコマンドは M2 マイルストーンから利用可能です。

### 過去のコンテンツ

過去の EC2 へのセットアップ手順は、参考のために `README.legacy.md` にそのまま残しており、マイルストーンごとに書き直す予定です。

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| EC2 (Elastic Compute Cloud) | Amazon's service to run virtual computers on the internet. | アマゾンがインターネット上で仮想コンピュータを実行するサービス。 |
| Security group | A virtual firewall that controls traffic to your EC2 instance. | EC2 インスタンスへのアクセスを制御する仮想のファイアウォール。 |
| SSH (Secure Shell) | A secure way to log in to your remote computer and run commands. | リモートのコンピュータに安全にログインしてコマンドを実行する方法。 |
