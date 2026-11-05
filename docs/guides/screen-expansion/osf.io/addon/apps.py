# -*- coding: utf-8 -*-
import os
from addons.base.apps import BaseAddonAppConfig
from . import SHORT_NAME, FULL_NAME


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class AddonAppConfig(BaseAddonAppConfig):

    short_name = SHORT_NAME
    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)

    full_name = FULL_NAME

    owners = ['node']

    views = [
        # widget: ここから
        'widget',
        # widget: ここまで
        # ember: ここから
        'page'
        # ember: ここまで
    ]

    configs = ['node']

    categories = ['other']

    node_settings_template = os.path.join(TEMPLATE_PATH, 'myscreen_node_settings.mako')

    @property
    def routes(self):
        from . import routes
        return [
            # ember: ここから
            routes.page_routes,
            # ember: ここまで
            routes.api_routes
        ]

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
