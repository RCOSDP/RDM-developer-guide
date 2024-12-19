import os

from addons.base.apps import BaseAddonAppConfig, generic_root_folder
from addons.myminio import SHORT_NAME, FULL_NAME
from addons.myminio import settings

myminio_root_folder = generic_root_folder('myminio')

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(
    HERE,
    'templates'
)


class MyMinIOAddonAppConfig(BaseAddonAppConfig):

    name = 'addons.{}'.format(SHORT_NAME)
    label = 'addons_{}'.format(SHORT_NAME)
    full_name = FULL_NAME
    short_name = SHORT_NAME

    owners = ['user', 'node']
    configs = ['accounts', 'node']
    categories = ['storage']

    has_hgrid_files = True

    max_file_size = settings.MAX_FILE_SIZE

    node_settings_template = os.path.join(TEMPLATE_PATH, 'myminio_node_settings.mako')
    user_settings_template = os.path.join(TEMPLATE_PATH, 'myminio_user_settings.mako')

    BUCKET_LINKED = 'myminio_bucket_linked'
    BUCKET_UNLINKED = 'myminio_bucket_unlinked'
    FILE_ADDED = 'myminio_file_added'
    FILE_REMOVED = 'myminio_file_removed'
    FILE_UPDATED = 'myminio_file_updated'
    FOLDER_CREATED = 'myminio_folder_created'
    NODE_AUTHORIZED = 'myminio_node_authorized'
    NODE_DEAUTHORIZED = 'myminio_node_deauthorized'
    NODE_DEAUTHORIZED_NO_USER = 'myminio_node_deauthorized_no_user'
    actions = (
        BUCKET_LINKED,
        BUCKET_UNLINKED,
        FILE_ADDED,
        FILE_REMOVED,
        FILE_UPDATED,
        FOLDER_CREATED,
        NODE_AUTHORIZED,
        NODE_DEAUTHORIZED,
        NODE_DEAUTHORIZED_NO_USER
    )

    @property
    def get_hgrid_data(self):
        return myminio_root_folder

    @property
    def routes(self):
        from . import routes
        return [routes.api_routes]

    @property
    def user_settings(self):
        return self.get_model('UserSettings')

    @property
    def node_settings(self):
        return self.get_model('NodeSettings')
