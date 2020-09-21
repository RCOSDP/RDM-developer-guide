# -*- coding: utf-8 -*-
"""
本パッケージによりロードすべき `AddonAppConfig`を定義する。
"""

# 本アドオンの識別名。スケルトンではパッケージ名と合致させる必要がある。
# 定義の簡便化のために用意している...
# `AddonAppConfig`の`short_name`等に個別に名前を定義しても良い。
SHORT_NAME = 'myskelton'

# `apps.py`に定義した`AddonAppConfig`クラス名の指定
# 特別な理由がなければ、 `addons.アドオン名.apps.AddonAppConfig`
default_app_config = 'addons.{}.apps.AddonAppConfig'.format(SHORT_NAME)
