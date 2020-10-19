# -*- coding: utf-8 -*-
from framework.routing import Rule, json_renderer
from website.routes import notemplate
from . import SHORT_NAME
from . import views

# ember: ここから
# HTML endpoints
page_routes = {
    'rules': [
        # Home (Base) | GET
        Rule(
            [
                '/<pid>/{}'.format(SHORT_NAME),
                '/<pid>/node/<nid>/{}'.format(SHORT_NAME),
            ],
            'get',
            views.project_myscreen,
            notemplate
        ),

    ]
}
# ember: ここまで

# JSON endpoints
api_routes = {
    'rules': [
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'get', views.myscreen_get_config, json_renderer),
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'put', views.myscreen_set_config, json_renderer),

        # ember: ここから
        Rule([
            '/project/<pid>/{}/config'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/config'.format(SHORT_NAME),
        ], 'get', views.myscreen_get_config_ember, json_renderer),
        Rule([
            '/project/<pid>/{}/config'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/config'.format(SHORT_NAME),
        ], 'patch', views.myscreen_set_config_ember, json_renderer),
        # ember: ここまで
    ],
    'prefix': '/api/v1',
}
