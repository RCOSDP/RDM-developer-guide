# View処理で使えるPythonデコレータ

`views.py` で定義される各View処理には、その処理の実行における前提をPythonのデコレータの形で記述することができます。

ここでは、よく使われているデコレータや、カスタムデコレータについて説明します。

## [framework.auth.decorators.must_be_logged_in](https://github.com/RCOSDP/RDM-osf.io/blob/develop/framework/auth/decorators.py#L174)
ユーザがログインしている状態である場合にのみ呼び出し可能であることを宣言します。

引数( `**kwargs` )には、以下のパラメータが追加されます。

- `auth` : 認証しているユーザに関する情報

## [website.project.decorators.must_be_valid_project](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/project/decorators.py#L80)
対象のnodeがプロジェクトとして認められるものであることを宣言します。

> プロジェクトとして認められないnodeとは、QuickFileNodeや撤回されたRegistrationなどがありますが、現在、RDMでは使用されていません。

引数( `**kwargs` )には、以下のパラメータが追加されます。

- `node` : 対象のプロジェクトに関する情報

## [website.project.decorators.must_have_addon(addon_name, model)](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/project/decorators.py#L314)
アドオンに関する情報を必要とすることを宣言します。第1引数( `addon_name` )にはアドオン名を、第2引数( `model` )には `'user'` か `'node'` のいずれかを指定します。 `'node'` を指定した場合は、パスは `/project/<pid>/` から始める必要があります。

引数( `**kwargs` )には、以下のパラメータが追加されます。

- 引数 `model` に `'user'` を指定した場合
  - `auth` : 認証しているユーザに関する情報
  - `user_addon` 指定したアドオンのUserSettings
- 引数 `model` に `'node'` を指定した場合
  - `node` : 対象のプロジェクトに関する情報
  - `node_addon` 指定したアドオンのNodeSettings

## [website.project.decorators.must_have_permission(permission)](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/project/decorators.py#L393)
必要なパーミッション( `permission` )を宣言します。パーミッションは [osf.utils.permissions](https://github.com/RCOSDP/RDM-osf.io/blob/develop/osf/utils/permissions.py#L4) に定義されており、 `'write'` , `'read'` , `'admin'` のいずれかを指定します。

引数( `**kwargs` )には、以下のパラメータが追加されます。

- `auth` : 認証しているユーザに関する情報
- `node` : 対象のプロジェクトに関する情報

## [website.project.decorators.must_be_addon_authorizer(addon_name)](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/project/decorators.py#L355)
プロジェクトにアドオンを追加したユーザーのみ呼び出し可能であることを宣言します。プロジェクトのアドオンの設定にのみ使われるView処理などに宣言します。

引数( `**kwargs` )には、以下のパラメータが追加されます。

- `node` : 対象のプロジェクトに関する情報

## [website.project.decorators.must_be_contributor_or_public](https://github.com/RCOSDP/RDM-osf.io/blob/develop/website/project/decorators.py#L309)
ユーザーがContributorであるか、プロジェクトが公開設定にされている場合のみ呼び出し可能であることを宣言します。

似たようなデコレータとして、以下のようなものがあります。

- `must_be_contributor`
- `must_be_contributor_or_public_but_not_anonymized`
- `must_be_contributor_and_not_group_member`

引数( `**kwargs` )には、以下のパラメータが追加されます。

- `auth` : 認証しているユーザに関する情報
- `node` : 対象のプロジェクトに関する情報

## [admin.rdm_addons.decorators.must_be_rdm_addons_allowed](https://github.com/RCOSDP/RDM-osf.io/blob/develop/admin/rdm_addons/decorators.py#L9)
ユーザーが所属する機関が、指定したアドオンを使うことを許可されている場合にのみ呼び出し可能であることを宣言します。この機能はAdminのRdm Addons機能により提供されています。
