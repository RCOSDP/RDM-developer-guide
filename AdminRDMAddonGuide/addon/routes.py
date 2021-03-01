"""
Routes associated with the jupyterhub addon
"""

from framework.routing import Rule, json_renderer
from . import SHORT_NAME
from . import views

api_routes = {
    'rules': [
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'get', views.myskelton_get_config, json_renderer),
        Rule([
            '/project/<pid>/{}/settings'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/settings'.format(SHORT_NAME),
        ], 'put', views.myskelton_set_config, json_renderer),
        # admin notes取得viewのルーティング設定
        Rule([
            '/project/<pid>/{}/adminnotes'.format(SHORT_NAME),
            '/project/<pid>/node/<nid>/{}/adminnotes'.format(SHORT_NAME),
        ], 'get', views.myskelton_get_admin_notes, json_renderer),
    ],
    'prefix': '/api/v1',
}
