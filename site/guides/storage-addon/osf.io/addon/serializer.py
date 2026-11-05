from addons.base.serializer import StorageAddonSerializer
from addons.myminio import SHORT_NAME
from addons.myminio import settings
from addons.myminio import utils
from website.util import web_url_for


class MyMinIOSerializer(StorageAddonSerializer):
    addon_short_name = SHORT_NAME

    REQUIRED_URLS = []

    @property
    def addon_serialized_urls(self):
        node = self.node_settings.owner
        user_settings = self.node_settings.user_settings or self.user_settings

        result = {
            'accounts': node.api_url_for('{}_account_list'.format(SHORT_NAME)),
            'createBucket': node.api_url_for('{}_create_bucket'.format(SHORT_NAME)),
            'importAuth': node.api_url_for('{}_import_auth'.format(SHORT_NAME)),
            'create': node.api_url_for('{}_add_user_account'.format(SHORT_NAME)),
            'deauthorize': node.api_url_for('{}_deauthorize_node'.format(SHORT_NAME)),
            'folders': node.api_url_for('{}_folder_list'.format(SHORT_NAME)),
            'config': node.api_url_for('{}_set_config'.format(SHORT_NAME)),
            'files': node.web_url_for('collect_file_trees'),
        }
        if user_settings:
            result['owner'] = web_url_for('profile_view_id',
                                          uid=user_settings.owner._id)
        return result

    def serialized_folder(self, node_settings):
        return {
            'path': node_settings.folder_id,
            'name': node_settings.folder_name
        }

    def credentials_are_valid(self, user_settings, client=None):
        if user_settings:
            for account in user_settings.external_accounts.all():
                if utils.can_list(settings.HOST,
                                  account.oauth_key, account.oauth_secret):
                    return True
        return False
