# ストレージアドオンの作成

具体的なストレージアドオンの例として、AWS S3互換の[MinIO](https://min.io/)と接続するストレージアドオンを実装します。このアドオンは特定のMinIOサーバーと接続するものとし、 My MinIOアドオンと名付けることとします。

基本的なアドオンの概要は[スケルトンの作成](../Skelton/README.md)を参照してください。

## 前提条件

[開発環境の準備](../Environment.md#開発環境でRDMを起動する)のガイドに従い、開発環境にてRDMを起動しているものとします。

# ストレージアドオンの設計

## サービスの構成

ストレージアドオンは以下の2つの要素から構成されます。

- OSF.ioサービスで動作するAddon: ユーザ・プロジェクト設定の管理
- WaterButlerサービスで動作するProvider: ストレージへのアクセスの仲介

Addonによりユーザからの認証情報の受領や各種設定を行い、Providerはこの認証情報・設定情報をAddonから譲渡してもらい、実際のストレージへのアクセスを行います。

## ファイルの構成

典型的なクラス構成とファイル配置は以下のようになります。

### OSF.io Addonのクラス構成とファイル構成

![OSF.io Addon クラス構成](images/osf_class.png)

`(*)`が付いているファイルはスケルトン アドオンには存在しないファイルです。

```
/addons/アドオン名/
├── __init__.py ... モジュールの定義
├── apps.py ... アプリケーションの定義
├── models.py ... モデルの定義
├── provider.py ... (*) 認証プロバイダの定義
├── requirements.txt ... 利用するPythonモジュールの定義
├── routes.py ... View(Routes)の定義
├── serializer.py ... (*) モデル-ビュー(JavaScript)間の情報交換用シリアライザの定義
├── settings ... 設定を定義するモジュール
│   ├── defaults.py ... デフォルト設定の定義
│   ├── __init__.py ... 設定の定義
│   └── local-dist.py ... (*) local.pyのサンプルファイル
├── static ... Webブラウザから読み込むことを想定した静的ファイル
│   ├── comicon.png ... アドオンのアイコン
│   ├── myminioAnonymousLogActionList.json ... (*) 変更履歴メッセージ定義
│   ├── myminioLogActionList.json ... (*) 変更履歴メッセージ定義
│   ├── myminioNodeConfig.js ... (*) Node設定の定義
│   ├── myminioUserConfig.js ... (*) User設定の定義
│   ├── node-cfg.js ... Node設定のエントリとなるJavaScriptファイル
│   └── user-cfg.js ... (*) User設定のエントリとなるJavaScriptファイル
├── templates ... テンプレートディレクトリ
│   ├── credentials_modal.mako ... (*) 認証情報の設定用ダイアログ
│   ├── node_settings.mako ... Node設定パネル
│   └── user_settings.mako ... (*) User設定パネル
├── tests ... テストコード
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   ├── test_model.py
│   ├── test_serializer.py ... (*)
│   ├── test_view.py
│   └── utils.py
├── utils.py ... (*) ユーティリティ関数の定義
└── views.py ... View(Views)の定義
```

### WaterButler Providerのクラス構成とファイル構成

![WaterButler Addon クラス構成](images/wb_class.png)

```
waterbutler/providers/アドオン名/
├── __init__.py ... Providerクラスの参照
├── metadata.py ... Metadataの定義
├── provider.py ... Providerの定義
└── settings.py ... デフォルト設定の定義

tests/providers/アドオン名/
├── __init__.py
└── provider.py ... Providerのテストコード
```

## OSF.io Addonのモジュール構成

スケルトン アドオンとの違いを中心に説明していきます。

### Modelの構成

`models.py` に、以下のModelを定義します。

- `UserSettings`: ユーザーに関する情報(認証情報等)
- `NodeSettings`: プロジェクトに関する情報
- `アドオン名FileNode`: ファイル・フォルダオブジェクトの親定義
- `アドオン名File`: ファイルオブジェクトの定義
- `アドオン名Folder`: ファイルオブジェクトの定義

`provider.py` に `アドオン名Provider` を、 `serializer.py` に `アドオン名Serializer` を定義します。OAuthを用いる場合は `osf.models.external.ExternalProvider` を継承し、必要なメンバを定義します。実装は [GitHubの例](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/github/models.py#L49) などを参考にしてください(GitHubアドオンは `アドオン名Provider` を `models.py` に定義しています)。
`アドオン名Serializer` にはビュー(JavaScript)にURLリストや接続先フォルダなどを渡すための関数を定義します。

OAuth認証をしない場合であっても、ストレージアドオンの `UserSettings` と `NodeSettings` は、 `BaseOAuthUserSettings` と `BaseOAuthNodeSettings` をそれぞれ継承して定義し、 `oauth_provider` に`アドオン名Provider` を指定します。こうすることで、統一的な構造で簡単に認証の仕組みを実装することができます。

My MinIOアドオンの場合は、以下のように定義します。

- [models.py](osf.io/addon/models.py)
- [provider.py](osf.io/addon/provider.py)
- [serializer.py](osf.io/addon/serializer.py)

### Viewの構成

`views.py`には、おおよそ以下の関数を定義します。

| 関数名 | 処理 |
|:------|:----|
| set_config | プロジェクトの設定を保存する。デフォルトでは接続先のフォルダとクライアント用のAPIのURLリストのみ。 |
| get_config | プロジェクトの設定を取得する。 |
| import_auth | ログイン中のユーザの認証情報をプロジェクトにインポートする。 |
| deauthorize_node | プロジェクトの認証情報を取り消す。 |
| add_user_account | ユーザの認証情報を追加する。 |
| account_list | ユーザの認証情報リストを取得する。 |
| create_folder | ストレージサービスにフォルダを追加する。プロジェクトのアドオン設定ページでフォルダを作る機能を提供しない場合は不要。 |
| folder_list | ストレージサービスのフォルダリストを取得する。 |

シリアライザ(`serializer.py`)を定義し、 `addons.base.generic_views` を利用することで、以下のように一部のView処理を簡単に定義することができます。

```
import_auth = addons.base.generic_views.import_auth(
    SHORT_NAME,
    Serializer
)
```

`generic_views` で提供していないView処理を追加したい場合や、View処理をカスタマイズしたい場合は、以下のように `views.py` に個別の関数を定義します。

```
@must_have_addon(SHORT_NAME, 'node')
@must_be_addon_authorizer(SHORT_NAME)
def folder_list(node_addon, **kwargs):
    return node_addon.get_folders()
```

フォルダの作成やフォルダリストの取得をするために、Addonでもストレージサービスへ接続する必要があります。

My MinIOアドオンの場合は、以下のように定義します。

- [routes.py](osf.io/addon/routes.py)
- [views.py](osf.io/addon/views.py)


### フレームワークによって提供されるView

アドオンが持つ利用者用設定画面(`user_settings.mako`)とプロジェクト用設定画面(`node_settings.mako`)のテンプレートをそれぞれ定義します。認証情報の設定用ダイアログ(`credentials_modal.mako`)はどちらの画面でも利用するので、別のファイルで定義し、それぞれから参照します。  
My MinIOアドオンの場合は、以下のように定義します。

- [user_settings.mako](osf.io/addon/templates/user_settings.mako)
- [node_settings.mako](osf.io/addon/templates/node_settings.mako)
- [credentials_modal.mako](osf.io/addon/templates/credentials_modal.mako)

利用者用設定画面のJavaScriptファイル(`user-cfg.js`, `myminioUserConfig.js`)と、プロジェクト用設定画面のJavaScriptファイル(`node-cfg.js`, `myminioNodeConfig.js`)をそれぞれ定義します。今回は、エントリとなるJavaScriptファイル(`*-cfg.js`)と定義ファイル(`myminio*Config.js`)を分けましたが、スケルトン アドオンのように `*-cfg.js` に定義を書いても構いません。  
My MinIOアドオンの場合は、以下のように定義します。

- [user-cfg.js](osf.io/addon/static/user-cfg.js)
- [node-cfg.js](osf.io/addon/static/node-cfg.js)
- [myminioUserConfig.js](osf.io/addon/static/myminioUserConfig.js)
- [myminioNodeConfig.js](osf.io/addon/static/myminioNodeConfig.js)

また、変更履歴メッセージの定義ファイルも追加します。  
My MinIOアドオンの場合は、以下のように定義します。

- [myminioAnonymousLogActionList.json](osf.io/addon/static/myminioAnonymousLogActionList.json)
- [myminioLogActionList.json](osf.io/addon/static/myminioLogActionList.json)

ストレージ操作UIであるFileViewerは[Fangorn](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/static/js/fangorn.js)を使って実装されています。アイテム選択時に表示するボタンをカスタマイズしたい場合は、 `Fangorn.config.アドオン名` を定義し、 `files.js` ファイルで読み込みます。
My MinIOアドオンではカスタマイズせずデフォルト動作を使用しています。カスタマイズ例は、[GitHubアドオン](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/github/static/githubFangornConfig.js)や[IQB-RIMSアドオン](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/iqbrims/static/iqbrimsFangornConfig.js)を参照してください。

### 設定モジュール

環境ごとの設定ファイル `local.py` の雛形として `local-dist.py` ファイルを定義します。サービス管理者は `local-dist.py` を `local.py` にコピーして、適宜設定値を書き換えます。

My MinIOアドオンの場合は、以下のように定義します。接続するMinIOサービスのホスト名を `HOST` プロパティに設定します。

- [local-dist.py](osf.io/addon/settings/local-dist.py)

### テストコード

シリアライザのテスト(`test_serializer.py`)を定義します。  
My MinIOアドオンの場合は、以下のように定義します。

- [test_serializer.py](osf.io/addon/tests/test_serializer.py)

## WaterButler Providerのモジュール構成

WaterButler Providerは、WaterButlerプロジェクトの中でPythonモジュールとして実装されます。

`metadata.py` には、フォルダやファイルのメタデータと、リビジョンを持つクラスを定義します。  
My MinIOアドオンの場合は、以下のように定義します。

- [metadata.py](waterbutler/provider/metadata.py)

`provider.py`には、ストレージサービスと接続しCRUD操作などを行うProviderクラスを定義します。

Providerが提供するメソッドには以下のようなものがあります。


| 関数名 | 引数 | 戻り値 | 処理 |
|:------|:----|:------|:-----|
| validate_v1_path | path, **kwargs | WaterButlerPath | 文字列で与えられたパス情報(`path`)を検証し、属性付きのWaterButlerPathオブジェクトを返す。 |
| validate_path | path, **kwargs | WaterButlerPath | 同上(廃止予定のv0仕様との互換性維持のため、2つのメソッドに分かれている)。 |
| download | path, accept_url=False, version=None, range=None, **kwargs | Stream | 指定されたパス(`path`)のデータをダウンロードする。戻り値にはデータアクセス用のStreamを返す。 |
| upload | stream, path, conflict='replace', **kwargs | Metadata | 指定されたパス(`path`)に指定されたデータ(`stream`)をアップロードする。戻り値にはアップロードしたファイルを示すMetadataを返す。 |
| delete | path, confirm_delete=0, **kwargs | なし | 指定されたパス(`path`)のファイル・フォルダを削除する。 |
| revisions | path, **kwargs | List(Revision) | 指定されたパス(`path`)のリビジョン情報を取得する。 |
| metadata | path, revision=None, **kwargs | Metadata or List(Metadata) | 指定されたパス(`path`)のメタデータを取得する。`path` がfileの場合 `Metadata` , directoryの場合 `List(Metadata)` を返す。 |
| create_folder | path, folder_precheck=True, **kwargs | Metadata | 指定されたパスにフォルダを作成する。戻り値には作成したフォルダを示すMetadataを返す。 |
| can_intra_copy | dest_provider, path=None | Bool | 指定された送信先Provider(`dest_provider`), パス(`path`)に対してintra_copy(内部コピー: ストレージサービス上でのコピー)が可能かどうかを判定する。これがFalseの場合、いったん一時ディレクトリにdownloadして、destにuploadするという操作となる。 |
| can_intra_move | dest_provider, path=None | Bool | 指定された送信先Provider(`dest_provider`), パス(`path`)に対してintra_move(内部移動: ストレージサービス中での移動)が可能かどうかを判定する。これがFalseの場合、いったん一時ディレクトリにdownloadして、destにupload、コピー元ファイルをdeleteするという操作となる。 |
| intra_copy | dest_provider, src_path, dest_path | Bool | 内部コピーを実施する。成功すればTrueを返す。 |
| intra_move | dest_provider, src_path, dest_path | Bool | 内部移動を実施する。成功すればTrueを返す。 |

My MinIOアドオンの場合は、以下のように定義します。

- [provider.py](waterbutler/provider/provider.py)


## OSF.io AddonとWaterButler Providerの認証情報の委譲

OSF.io Addonは、WaterButler Providerが必要なサービスに接続できるよう、認証情報を委譲します。この認証情報の形式はAddonにより異なるため、AddonとProviderのバージョンを合わせるなど依存関係に配慮する必要があります。

![認証情報などの委譲](images/crud.png)

Addonにおける委譲設定は、 `addons.アドオン名.models.NodeSettings.serialize_waterbutler_credentials()` 関数で設定します。接続先のフォルダなどの情報は、同クラスの `serialize_waterbutler_settings()` 関数で設定します。例えば [IQB-RIMSアドオンの `serialize_waterbutler_settings()` 関数](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/iqbrims/models.py#L226) では、フォルダごとの権限設定を渡します。

My MinIOアドオンの場合は、以下のように定義します。認証情報として、アクセス先のホスト名、アクセスキー、シークレットキーを渡します。設定情報として、接続先のバケットIDを渡します。

```
def serialize_waterbutler_credentials(self):
    if not self.has_auth:
        raise exceptions.AddonError('Cannot serialize credentials for {} addon'.format(FULL_NAME))
    return {
        'host': settings.HOST,
        'access_key': self.external_account.oauth_key,
        'secret_key': self.external_account.oauth_secret,
    }

def serialize_waterbutler_settings(self):
    if not self.folder_id:
        raise exceptions.AddonError('Cannot serialize settings for {} addon'.format(FULL_NAME))
    return {
        'bucket': self.folder_id
    }
```

Provider側では、認証情報と設定情報を `waterbutler.providers.アドオン名.アドオン名Provider` クラスのコンストラクタ(`__init__()`)の引数 `credentials` と `settings` にDictionary型でそれぞれ受け取ります。

My MinIOアドオンの場合は、以下のように定義します。認証情報を使ってMy MinIOサービスとの接続を確立し、設定情報を使って接続先バケットを取得します。

```
class MyMinIOProvider(provider.BaseProvider):
    def __init__(self, auth, credentials, settings):
        super().__init__(auth, credentials, settings)

        host = credentials['host']
        port = 443
        m = re.match(r'^(.+)\:([0-9]+)$', host)
        if m is not None:
            host = m.group(1)
            port = int(m.group(2))
        self.connection = MyMinIOConnection(credentials['access_key'],
                                            credentials['secret_key'],
                                            calling_format=OrdinaryCallingFormat(),
                                            host=host,
                                            port=port,
                                            is_secure=port == 443)
        self.bucket = self.connection.get_bucket(settings['bucket'], validate=False)
```

## Recent Activityの記録・表示

何らかのユーザ操作を契機としてアドオンに対して行われた操作は、Recent Activityという形で記録することができます。

### NodeLogモデルの追加

Recent Activityは[NodeLogモデル](https://github.com/RCOSDP/RDM-osf.io/blob/develop/osf/models/nodelog.py)により表現されます。
ログの追加はNode(プロジェクトに対応するモデル)の [add_logメソッド](https://github.com/RCOSDP/RDM-osf.io/blob/develop/osf/models/mixins.py#L84) により行うことができます。

[models.py](osf.io/addon/models.py#L127-L143)
```
self.owner.add_log(
    '{0}_{1}'.format(SHORT_NAME, action),
    auth=auth,
    params={
        'project': self.owner.parent_id,
        'node': self.owner._id,
        'path': metadata['materialized'],
        'bucket': self.folder_id,
        'urls': {
            'view': url,
            'download': url + '?action=download'
        }
    },
)
```

この例では、NodeSettingsモデルのowner(Node)に対してログの追加を指示しています。
パラメータには以下の値を指定することができます。

- `action` ... ログのアクション種別を示す名前。`アドオン名_アクション名`となる。本サンプルにより記録される`アクション名`には以下のものがある。
  - `node_authorized`, `node_deauthorized`, `node_deauthorized_no_user` ... プロジェクトに本アドオンが設定あるいは解除された場合に記録されるログ
  - `bucket_linked`, `bucket_unlinked` ... プロジェクト設定画面により、バケットが設定あるいは解除された場合に記録されるログ
  - `file_added`, `file_removed`, `file_updated`, `folder_created` ... WaterButlerによるファイル操作が行われた場合に記録されるログ
- `params` ... ログのパラメータ。任意のdictオブジェクトを指定することができる
- `auth` ... 操作を実施したユーザの情報。[framework.auth.Authクラス](https://github.com/RCOSDP/RDM-osf.io/blob/develop/framework/auth/core.py#L170)のインスタンスを与えることができる

### NodeLogモデルの表示

記録されたログをどのように表示するかは、以下のJSONファイルにより定義します。

[myminioLogActionList.json](osf.io/addon/static/myminioLogActionList.json#L2)
```
"myminio_bucket_linked" : "${user} linked the My MinIO bucket ${bucket} to ${node}",
```

[myminioAnonymousLogActionList.json](osf.io/addon/static/myminioAnonymousLogActionList.json#L2)
```
"myminio_bucket_linked" : "A user linked an My MinIO bucket to a project",
```

`アドオン名LogActionList.json`はログインした状態でのプロジェクト表示の際に利用され、`アドオン名AnonymousLogActionList.json`はパブリックなプロジェクト(RDMでは利用を想定していません)に利用されます。
どのメッセージがログ表示に利用されるかは、add_logメソッドの `action` 引数に与えられた文字列がキーとして使用されます。また、メッセージ定義中の `${パラメータ名}` にはadd_logメソッドの `params` 引数に与えられたパラメータ中のキーを指定することができます。

メッセージの国際化は[pybabelコマンド](http://babel.pocoo.org/en/latest/cmdline.html)を用いて行うことができます。定義したアドオンのメッセージ(英語で記載する)に対応する日本語メッセージの定義ファイルを生成するためには、
以下のコマンドを実行します。

```
# メッセージ定義JSONなどをJavaScriptファイルへと変換する
$ docker compose run --rm web invoke assets

# メッセージ定義テンプレートファイル website/translations/js_messages.pot を更新する
$ docker compose run --rm web pybabel extract -F ./website/settings/babel_js.cfg -o ./website/translations/js_messages.pot .

# メッセージ定義ファイル website/translations/ja/LC_MESSAGES/js_messages.po を更新する
$ docker compose run --rm web pybabel update -i ./website/translations/js_messages.pot -o ./website/translations/en/LC_MESSAGES/js_messages.po -l en
$ docker compose run --rm web pybabel update -i ./website/translations/js_messages.pot -o ./website/translations/ja/LC_MESSAGES/js_messages.po -l ja
```

すると、`website/translations/ja/LC_MESSAGES/js_messages.po`ファイルに、以下のような空の項目が追加されます。

```
#: website/static/js/logActionsList_extract.js:246
msgid "${user} linked the My MinIO bucket ${bucket} to ${node}"
msgstr ""
```

この `msgstr` に日本語によるメッセージ定義を追加することで、メッセージを国際化することができます。

```
#: website/static/js/logActionsList_extract.js:246
msgid "${user} linked the My MinIO bucket ${bucket} to ${node}"
msgstr "${user}が My MinIOバケット(${bucket})を接続しました"
```

`js_messages.po` を変更したら、`assets`サービスを再起動してください。最新の`js_messages.po`ファイルがメッセージの表示に使用されるようになります。

```
$ docker compose restart assets
```

## タイムスタンプの処理

RDMではユーザが任意のタイミングで、プロジェクト中のファイルに対してタイムスタンプを打つことができます。タイムスタンプは、ファイルに関してその時点での内容を証明するもので、研究の証跡としてのデータを考える上で非常に重要です。

なお、docker-composeで起動した状態では [FreeTSA Project](http://eswg.jnsa.org/sandbox/freetsa/) のサーバを用いてタイムスタンプを付与します。実環境への配備時は[UPKI電子証明書発行サービス](https://certs.nii.ac.jp/)によりタイムスタンプ付与することを想定しています。

### ユーザによるタイムスタンプの追加

タイムスタンプは、ファイルの内容から計算したハッシュ値を署名する形で作成されます。ハッシュの取得は以下のいずれかの方法でおこないます。

- `osf.models.files.File` サブクラスの `get_hash_for_timestamp`により取得する
- WaterButlerを経由してファイルをダウンロードし、ハッシュ計算を行う

`osf.models.files.File` サブクラスはアドオンのモデルとしてハッシュ値の取得方法を定義するものです。本サンプルでは [models.py](osf.io/addon/models.py) にあります。
ストレージにより容易にハッシュ相当の値を取得・管理する方法がある場合は、このモデルに`get_hash_for_timestamp(self)`メソッドを定義します。
タイムスタンプ処理はこのメソッドを通じてハッシュ値を取得することができます。
`get_hash_for_timestamp(self)`メソッドの実装は dropboxbusinessアドオンの [DropboxBusinessFileクラス](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/dropboxbusiness/models.py#L38) を参考にしてください。

`osf.models.files.File`モデルに`get_hash_for_timestamp(self)`が定義されていない場合は、タイムスタンプ処理はWaterButlerを経由してファイルをダウンロードする方法を試行します。

### RDM以外でのファイル変更によるタイムスタンプの追加

RDM以外でのファイル変更時に実施する場合も、ファイルが変更されたことを示すためにタイムスタンプを付加したい場合があります。
このような処理を実行するためには `website.util.timestamp` モジュールを使用します。
例えばDropbox Businessアドオンでは以下のように実装しています。

[dropboxbusiness/utils.py](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/dropboxbusiness/utils.py)
```
...
from website.util import timestamp

...

file_info = {
    'file_id': file_node._id,
    'file_name': attrs.get('name'),
    'file_path': attrs.get('materialized'),
    'size': attrs.get('size'),
    'created': attrs.get('created_utc'),
    'modified': attrs.get('modified_utc'),
    'file_version': '',
    'provider': PROVIDER_NAME
}
# verified by admin
verify_result = timestamp.check_file_timestamp(
    admin.id, node, file_info, verify_external_only=True)
```

`check_file_timestamp(uid, node, data, verify_external_only=False)`関数は以下のパラメータを指定することができます。

- `uid` ... タイムスタンプ操作を行うユーザを示すOSFUserのID
- `node` ... ファイルが所属するプロジェクトを示すNode
- `data` ... タイムスタンプにより署名検証するデータを示す辞書型データ
- `verify_external_only` ... タイムスタンプ検証情報の格納に`osf.models.RdmFileTimestamptokenVerifyResult`を使う場合はFalse, 使わない場合(`osf.models.files.File` サブクラスの`def set_timestamp(self, timestamp_data, timestamp_status, context)`に格納する場合)はTrueとする (デフォルトはFalse)

なお、`def set_timestamp(self, timestamp_data, timestamp_status, context)` の定義方法は dropboxbusinessアドオンの [DropboxBusinessFileクラス](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/dropboxbusiness/models.py#L38) を参考にしてください。

また、タイムスタンプの付加処理はストレージのAPI呼び出しやタイムスタンプの付加処理などI/Oを伴うため、viewsモジュール内の関数など、リクエストハンドラとして振る舞う関数中で処理を行ってしまうと、他のハンドラが待たされる要因になります。
このような状況に対応するため、RDMでは[Celery](https://docs.celeryproject.org/en/stable/)によるワーカーが用意されています。
関数をCeleryタスクとして定義することで、時間がかかる処理はワーカーに委譲することができます。
例えばDropbox Businessアドオンでは以下のように定義しています。

[dropboxbusiness/utils.py](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/dropboxbusiness/utils.py)
```
...
from framework.celery_tasks import app as celery_app

...

@celery_app.task(bind=True, base=AbortableTask)
def celery_check_updated_files(self, team_ids):
    ...
```

呼び出し側では以下のように関数を実行することで、ワーカーに処理を任せ、自身の処理を続行することができます。

[dropboxbusiness/views.py](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons/dropboxbusiness/views.py)
```
utils.celery_check_updated_files.delay(team_ids)
```

# My MinIOアドオンの実装

ここでは、 `myminio` という識別名のアドオンの実装を例に説明します。アドオンの完全名は `My MinIO` とします。

アドオン名は様々な場所に埋め込まれています。アドオン名を変更したい場合は、以降で追加・変更するファイル名やコードの `myminio` 、 `My MinIO` 、 `MyMinIO` という文字列を変更してください。

My MinIOアドオンは、AWS S3互換サービスと接続するアドオンなので、Amazon S3アドオンやS3 Compatible Storageアドオンを参考に実装することができます。Amazon S3アドオンやS3 Compatible Storageアドオンとの違いは以下の通りです。

- My MinIOアドオンは簡単のため、アップロードの暗号化機能を実装しない。
- Amazon S3アドオンやS3 Compatible Storageアドオンは、アカウントごとに接続するサービスやLocationなどを選択できるが、My MinIOはサービス側で指定した特定のMinIOサービスのみを扱う。

## OSF.ioへの実装

### addons.myminio モジュールの定義

スケルトン アドオンと同様に、[アドオンの実装例(`osf.io/addon/`)](osf.io/addon/)を `addons/myminio` ディレクトリにコピーします。

### RDMコードの変更

スケルトン アドオンと同様に、RDMのコードをいくつか変更します。

- [addons.json](https://github.com/RCOSDP/RDM-osf.io/blob/develop/addons.json)
  - 変更例のサンプル: [addons.json](osf.io/config/addons.json)
- [framework/addons/data/addons.json](https://github.com/RCOSDP/RDM-osf.io/blob/develop/framework/addons/data/addons.json)
  - 変更例のサンプル: [addons.json](osf.io/config/framework/addons/data/addons.json)
- [Dockerfile](https://github.com/RCOSDP/RDM-osf.io/blob/develop/Dockerfile)
  - 変更例のサンプル: [Dockerfile](osf.io/config/Dockerfile)
- [api/base/settings/defaults.py](https://github.com/RCOSDP/RDM-osf.io/blob/develop/api/base/settings/defaults.py)
  - 変更例のサンプル: [defaults.py](osf.io/config/api/base/settings/defaults.py)

`api/base/settings/defaults.py` は、 `INSTALLED_APPS` の他に、 `ADDONS_FOLDER_CONFIGURABLE` 、 `ADDONS_OAUTH` にもアドオン名を追加します。変更例サンプルでは、Amazon S3アドオンに合わせて、スケルトン アドオンとは異なる方法で設定しています。

```
INSTALLED_APPS += ('addons.myminio',)
ADDONS_FOLDER_CONFIGURABLE.append('myminio')
ADDONS_OAUTH.append('myminio')
```

他にもストレージアドオンでは、 [website/static/storageAddons.json](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/static/storageAddons.json) にも設定を追加する必要があります。

変更例は [storageAddons.json](osf.io/config/website/static/storageAddons.json) を参照してください。

```
    "myminio": {
        "fullName": "My MinIO",
        "externalView": false
    },
```

> `externalView` を `true` に設定すると、FileViewerでファイルの外部ページリンクボタンが表示されるようになります。リンクを正しく動作させるには、WaterButlerのProviderを修正する必要があります。詳細は[GoogleDriveの実装](https://github.com/RCOSDP/RDM-waterbutler/blob/develop/waterbutler/providers/googledrive/metadata.py#L116)などを参照してください。

> FileViewerで、フォルダの操作はできるがファイルの操作ができない場合は、 `storageAddons.json` の設定が漏れている可能性があります。


### Migrationsファイルの作成

`makemigrations` コマンドを実行して、Migrationsファイルを作成します。

```
$ docker compose run --rm web python3 manage.py makemigrations
```

上記の出力中に以下のような出力が現れれば成功です。ストレージアドオンの場合、 `osf/migrations` と `addons/myminio/migrations` の2つのディレクトリ内にPythonファイルが作成されます。

> `osf/migrations` 配下に作成されるファイル名は、作成日時やRDMのバージョンによって異なります。

```
Migrations for 'osf':
  osf/migrations/0214_auto_20201001_0007.py
    - Create proxy model MyMinIOFileNode
    - Alter field type on basefilenode
    - Create proxy model MyMinIOFile
    - Create proxy model MyMinIOFolder
Migrations for 'addons_myminio':
  addons/myminio/migrations/0001_initial.py
    - Create model NodeSettings
    - Create model UserSettings
    - Add field user_settings to nodesettings
```

### 国際化メッセージファイルの作成

国際化メッセージファイルの定義ファイルは以下のコマンドで生成することができます。

> このセクションの実施時は各サービスを停止状態にしてください。

```
# メッセージ定義JSONなどをJavaScriptファイルへと変換する。各サービスが停止している状態で実施する。
$ docker compose run --rm web invoke assets

# メッセージ定義テンプレートファイル website/translations/js_messages.pot を更新する
$ docker compose run --rm web pybabel extract -F ./website/settings/babel_js.cfg -o ./website/translations/js_messages.pot .

# メッセージ定義ファイル website/translations/ja/LC_MESSAGES/js_messages.po を更新する
$ docker compose run --rm web pybabel update -i ./website/translations/js_messages.pot -o ./website/translations/en/LC_MESSAGES/js_messages.po -l en
$ docker compose run --rm web pybabel update -i ./website/translations/js_messages.pot -o ./website/translations/ja/LC_MESSAGES/js_messages.po -l ja
```

変更例のサンプル [js_messages.po](osf.io/config/website/translations/ja/LC_MESSAGES/js_messages.po) を参考に日本語メッセージを追加してください。

```
#: website/static/js/logActionsList_extract.js:246
msgid "${user} linked the My MinIO bucket ${bucket} to ${node}"
msgstr "${user}がMy MinIOバケット(${bucket})を${node}にリンクしました"

#: website/static/js/logActionsList_extract.js:247
msgid "${user} unselected the My MinIO bucket ${bucket} in ${node}"
msgstr "${user}が${node}のMy MinIOバケット(${bucket})の選択を解除しました"

...
```

このメッセージを追加後、`assets`サービスの再起動時にメッセージ定義が反映されます。

### アドオンのテスト

以下のコマンドで、OSF.ioに追加したMy MinIOアドオンのユニットテストを実行できます。

```
$ docker compose run --rm web invoke test_module -m addons/myminio/tests/
```

## WaterButlerへの実装

### waterbutler.providers.myminio モジュールの定義

[Providerの実装例(`waterbutler/provider/`)](waterbutler/provider/) を `waterbutler/providers/myminio` にコピーします。また、[Providerのテストコード例(`waterbutler/tests`)](waterbutler/tests) を `tests/providers/myminio` にコピーします。

### RDMコードの変更

[setup.py](https://github.com/RCOSDP/RDM-waterbutler/blob/develop/setup.py) に、アドオンのエントリポイント定義を追加します。`setup()` 関数の引数 `entry_points` に指定するDictionaryの `waterbutler.providers` キーに指定する配列に、以下を追加します。

```
'myminio = waterbutler.providers.myminio:MyMinIOProvider',
```

変更例はサンプル [setup.py](waterbutler/config/setup.py) を参照してください。

### docker-compose.override.yml の追加

変更したコードを使うよう、RDMの `docker-compose.override.yml` で WaterButler のサービスの `volumes` を指定します。

例えば、以下のようなディレクトリ階層の場合は、

```
.
├── RDM-osf.io
│   ├── docker-compose.override.yml
│   └── docker-compose.yml
└── RDM-waterbutler
```

`RDM-osf.io/docker-compose.override.yml` の内容を以下のようにします。

```
version: "3.4"

services:
  wb:
    volumes:
      - ../RDM-waterbutler:/code
  wb_worker:
    volumes:
      - ../RDM-waterbutler:/code
  wb_requirements:
    volumes:
      - ../RDM-waterbutler:/code
```


### アドオンのテスト

以下のコマンドで、WaterButlerに追加したMy MinIOアドオン Providerのユニットテストを実行できます。

```
$ docker compose run --rm wb invoke test --provider myminio
```


# My MinIOアドオンの動作確認

My MinIOアドオンの動作確認をしてみましょう。

## MinIOサービスの起動

接続先のMinIOサービスを起動します。

```
docker run -p 9001:9000 \
  -e "MINIO_ACCESS_KEY=minioadmin" \
  -e "MINIO_SECRET_KEY=minioadmin" \
  minio/minio server /data
```

RDMと同じコンピュータで実行する場合、9000番ポートが競合してしまうので、MinIOサービスのホストへの割り当てポートは9001などに設定します。
`MINIO_ACCESS_KEY` と `MINIO_SECRET_KEY` は認証に使うキーです。適宜書き換えてください。

その他MinIOに関する詳しい説明は[MinIOのドキュメント](https://docs.min.io/)を参照してください。

## OSF.io Addonの設定

OSF.io Addonの設定をします。 `addons/myminio/settings/local-dist.py` を `addons/myminio/settings/local.py` にコピーし、 `HOST` プロパティに先ほど起動したMinIOサービスのホスト名を指定します。

```
HOST = '192.168.168.167:9001'
```

RDMとMinIOサービスを同じ環境で実行している場合は、ループバックエイリアスを指定します。

## DBマイグレーション

マイグレーションを実行し、Migrations定義をPostgreSQLサービスに反映します。

```
$ docker compose run --rm web python3 manage.py migrate
```

## サービスの再起動

WaterButlerに追加したProviderを有効にするために、 `wb_requirements` を起動します。

```
$ docker compose up wb_requirements
```

変更したファイルに関連するサービスを再起動します。

```
$ docker compose restart assets web api wb
```

これでサービスへの反映は完了です。

## ストレージアドオンを試す

My MinIOアドオンを試すには、以下のような操作を実施します。

1. RDM Web UIにアクセスする `http://localhost:5000`
1. ユーザ設定ページを開く
1. Configure add-on accountsページを開く
1. My MinIOアドオンの認証情報を設定をする
  ![Authorize Addon](images/authorize-addon.png)
  認証情報の設定ダイアログが表示されるので、MinIOサービスの `MINIO_ACCESS_KEY` と `MINIO_SECRET_KEY` を、それぞれ、`Access Key` と `Secret Key` フォームに入力して保存します。
  ![Filled Credential](images/filled-credential.png)
  成功すれば、切断ボタンと利用しているプロジェクトリストが表示されるエリアが表示されます。
  ![Successful Authorization Addon](images/successful-authorization-addon.png)
1. 適当なプロジェクトを作成する
1. Add-onsページを開く
1. My MinIOアドオンを有効化する
  ![Enable Addon](images/enable-addon.png)
1. My MinIOアドオンの設定をする
  ![Configure Addon](images/configure-addon.png)
  `Import Account from Profile`ボタンから、アドオンの設定を行います。
  接続に成功すると、ルート直下のフォルダリストが表示されるので、プロジェクトに紐付けるフォルダを選択し、保存します。このページでフォルダを作成することもできます。
  ![Select Current Folder](images/select-current-folder.png)

これで、作成したプロジェクトでMy MinIOアドオンが使えるようになりました。
プロジェクトページのFiles ウィジェットやFilesページから、My MinIOサービスに対してフォルダの作成やファイルのアップロード、削除、ダウンロードなどができるようになるはずです。

![Enabled Addon](images/enabled-addon.png)

以上でMy MinIOアドオンの動作確認は完了です！
