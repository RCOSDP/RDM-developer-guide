# -*- coding: utf-8 -*-
"""
本アドオンの各種プロパティを定義する
"""

import os
from addons.base.apps import BaseAddonAppConfig
from . import SHORT_NAME


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


# `__init__.py` の `default_app_config` により本ファイル内の`AddonAppConfig`が参照される
class AddonAppConfig(BaseAddonAppConfig):

    short_name = SHORT_NAME
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)

    full_name = 'My Skelton'

    owners = ['node']

    views = []
    configs = ['node']

    categories = ['other']

    include_js = {}

    include_css = {}

    node_settings_template = os.path.join(TEMPLATE_PATH, 'node_settings.mako')

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
