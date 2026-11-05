# Storage Addon / ストレージアドオン

> **Summary:** Guide to creating an RDM storage addon that connects to external storage services
> **概要:** 外部ストレージサービスに接続する RDM ストレージアドオンを作成する手引き

**Jump:** [English](#english) · [日本語](#japanese)

- Version / 版: 0.2 — 2026-11-06. **Learned:** the legacy guide was rewritten upstream for the GravyValet stack (PR #18), so the sample-code layout this overview assumed (Addon on osf.io + Provider on WaterButler, My MinIO sample) no longer exists in `README.legacy.md`; the overview must be realigned in a later milestone. ／ 旧ガイドが上流で GravyValet 構成向けに書き直された（PR #18）ため、この概要が前提にしていたサンプルコードの配置（osf.io 側 Addon + WaterButler 側 Provider、My MinIO 例）は `README.legacy.md` に存在しなくなった。概要は後のマイルストーンで合わせ直す必要があると分かった。
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

The legacy storage addon instructions are kept verbatim except the one `recaptchaSiteKey` placeholder in `README.legacy.md` for reference and will be rewritten per milestone.

### Latest changes

- 2026-11-06 (QAE): in the ported text the sample `recaptchaSiteKey` value was replaced by the placeholder `<recaptcha-site-key>`; the original was Google's public reCAPTCHA test key, but this public repository keeps no key-shaped literals (the secret scan rejects them).

- **2026-11-06 — Legacy guide rewritten for the GravyValet architecture (PR #18).** [`README.legacy.md`](README.legacy.md) now describes building a storage addon as an independent Python package (the worked example is a NextCloud addon, `nextcloud_plugin`) on the current OSF stack: osf.io, GravyValet (a new service that keeps addon connection settings and credentials on behalf of osf.io), WaterButler (the service that reads and writes files on the storage) and angular-osf (the new browser front end), tied together by a Caddy (a small web server used here as a *reverse proxy*: one front door at `http://localhost` that forwards each request to the right service) single-origin proxy. The former My MinIO sample code under `osf.io/` and `waterbutler/` was removed by that rewrite, and the class diagrams were replaced by Mermaid (a text format that is drawn as a diagram) sources and PNG renders in `images/`. The overview above still describes the two-part Addon/Provider model and will be aligned with the new text in a later milestone. Incorporated from PR #18 by chiku-samugari (2026-11-06).
- **2026-11-06 — Mako template file names get the addon name as a prefix (PR #14).** Mako (the template language used for the addon settings panels) caches templates by file name in some RDM run modes, so `user_settings.mako` must be named `<addon>_user_settings.mako`. The change was applied to the My MinIO legacy text and sample code first, and then superseded by the PR #18 rewrite above, which removed that sample; the rule itself is kept in the [Skeleton guide](../skeleton/README.md) and the [Screen Expansion guide](../screen-expansion/README.md). Incorporated from PR #14 by shun-nakazawa (2026-11-06).

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

### 最近の変更

- 2026-11-06（QAE）: 移植した本文のサンプル値 `recaptchaSiteKey` をプレースホルダー `<recaptcha-site-key>` に置き換えた。元の値は Google 公開の reCAPTCHA 試験用キーだが、公開リポジトリには鍵の形をしたリテラルを置かない（秘密スキャンが拒否する）。

- **2026-11-06 — 旧ガイドを GravyValet 構成向けに全面改訂（PR #18）。** [`README.legacy.md`](README.legacy.md) は、現在の OSF 構成（osf.io、GravyValet（アドオンの接続先・認証情報・設定を osf.io に代わって保管する新しいサービス）、WaterButler（ストレージ上のファイルを読み書きするサービス）、angular-osf（新しいブラウザ画面））の上で、ストレージアドオンを独立した Python パッケージとして作る手順（例は NextCloud アドオン `nextcloud_plugin`）を説明するようになりました。各サービスは Caddy（ここでは*リバースプロキシ*＝`http://localhost` という一つの入口で受けて各サービスへ振り分ける小さな Web サーバ）による単一オリジンのプロキシで束ねます。この改訂により `osf.io/`・`waterbutler/` 配下の旧 My MinIO サンプルコードは削除され、クラス図は `images/` の Mermaid（文字で書くと図として描かれる書式）のソースと PNG に置き換わりました。上の概要は従来の Addon/Provider 二部構成の説明のままであり、後のマイルストーンで新しい本文に合わせます。Incorporated from PR #18 by chiku-samugari (2026-11-06).
- **2026-11-06 — mako テンプレートのファイル名の先頭にアドオン名を付ける（PR #14）。** Mako（アドオン設定画面のテンプレート言語）は RDM の動作モードによってテンプレートをファイル名でキャッシュするため、`user_settings.mako` は `<アドオン名>_user_settings.mako` という名前にします。この変更は My MinIO の旧本文とサンプルコードに先に適用した後、上記 PR #18 の改訂でサンプルごと置き換えられました。規則そのものは[スケルトンガイド](../skeleton/README.md)と[画面拡張ガイド](../screen-expansion/README.md)に残っています。Incorporated from PR #14 by shun-nakazawa (2026-11-06).

---

## Glossary / 用語

| Term | English note | 日本語注 |
|---|---|---|
| Storage addon | An addon that connects RDM to external storage services like AWS S3. | AWS S3 のような外部ストレージサービスに RDM を接続するアドオン。 |
| Provider | A component that actually communicates with the storage service. | ストレージサービスと実際に通信するコンポーネント。 |
| Authentication | The process of verifying who you are (like a username and password). | あなたが誰であるかを確認するプロセス（ユーザー名とパスワードのようなもの）。 |
| Authorization | The process of checking what you are allowed to do after logging in. | ログインした後、あなたが何をできるかを確認するプロセス。 |

