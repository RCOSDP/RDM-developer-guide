from django.db import models

import addons.myminio.settings as settings
from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from addons.myminio import SHORT_NAME, FULL_NAME
from addons.myminio.provider import MyMinIOProvider
from addons.myminio.serializer import MyMinIOSerializer
from addons.myminio.utils import bucket_exists, get_bucket_names
from framework.auth.core import Auth
from osf.models.files import File, Folder, BaseFileNode


class MyMinIOFileNode(BaseFileNode):
    _provider = SHORT_NAME


class MyMinIOFolder(MyMinIOFileNode, Folder):
    pass


class MyMinIOFile(MyMinIOFileNode, File):
    version_identifier = 'version'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = MyMinIOProvider
    serializer = MyMinIOSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = MyMinIOProvider
    serializer = MyMinIOSerializer

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    folder_location = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    @property
    def folder_path(self):
        return self.folder_name

    @property
    def display_name(self):
        return u'{0}: {1}'.format(self.config.full_name, self.folder_id)

    def set_folder(self, folder_id, auth):
        host = settings.HOST
        if not bucket_exists(host,
                             self.external_account.oauth_key,
                             self.external_account.oauth_secret, folder_id):
            error_message = ('We are having trouble connecting to that bucket. '
                             'Try a different one.')
            raise exceptions.InvalidFolderError(error_message)

        self.folder_id = str(folder_id)
        self.folder_name = folder_id
        self.save()

        self.nodelogger.log(action='bucket_linked', extra={'bucket': str(folder_id)}, save=True)

    def get_folders(self, **kwargs):
        # This really gets only buckets, not subfolders,
        # as that's all we want to be linkable on a node.
        try:
            buckets = get_bucket_names(self)
        except Exception:
            raise exceptions.InvalidAuthError()

        return [
            {
                'addon': SHORT_NAME,
                'kind': 'folder',
                'id': bucket,
                'name': bucket,
                'path': bucket,
                'urls': {
                    'folders': ''
                }
            }
            for bucket in buckets
        ]

    @property
    def complete(self):
        return self.has_auth and self.folder_id is not None

    def authorize(self, user_settings, save=False):
        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=save)

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None
        self.folder_location = None

    def deauthorize(self, auth=None, log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.clear_auth()  # Also performs a save

        if log:
            self.nodelogger.log(action='node_deauthorized', save=True)

    def delete(self, save=True):
        self.deauthorize(log=False)
        super(NodeSettings, self).delete(save=save)

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

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider=SHORT_NAME)

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

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), log=True)
