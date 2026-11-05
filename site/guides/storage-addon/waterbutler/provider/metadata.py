import os

from waterbutler.core import metadata


class MyMinIOMetadata(metadata.BaseMetadata):

    @property
    def provider(self):
        return 'myminio'

    @property
    def name(self):
        return os.path.split(self.path)[1]


class MyMinIOFileMetadataHeaders(MyMinIOMetadata, metadata.BaseFileMetadata):

    def __init__(self, path, headers):
        self._path = path
        # Cast to dict to clone as the headers will
        # be destroyed when the request leaves scope
        super().__init__(dict(headers))

    @property
    def path(self):
        return '/' + self._path

    @property
    def size(self):
        return self.raw['Content-Length']

    @property
    def content_type(self):
        return self.raw['Content-Type']

    @property
    def modified(self):
        return self.raw['Last-Modified']

    @property
    def created_utc(self):
        return None

    @property
    def etag(self):
        return self.raw['Etag'].replace('"', '')

    @property
    def extra(self):
        return {
            'md5': self.raw['Etag'].replace('"', ''),
            'encryption': self.raw.get('X-Amz-Request-Id', '')
        }


class MyMinIOFileMetadata(MyMinIOMetadata, metadata.BaseFileMetadata):

    @property
    def path(self):
        return '/' + self.raw['Key']

    @property
    def size(self):
        return int(self.raw['Size'])

    @property
    def modified(self):
        return self.raw['LastModified']

    @property
    def created_utc(self):
        return None

    @property
    def content_type(self):
        return None

    @property
    def etag(self):
        return self.raw['ETag'].replace('"', '')

    @property
    def extra(self):
        return {
            'md5': self.raw['ETag'].replace('"', '')
        }


class MyMinIOFolderKeyMetadata(MyMinIOMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['Key'].split('/')[-2]

    @property
    def path(self):
        return '/' + self.raw['Key']


class MyMinIOFolderMetadata(MyMinIOMetadata, metadata.BaseFolderMetadata):

    @property
    def name(self):
        return self.raw['Prefix'].split('/')[-2]

    @property
    def path(self):
        return '/' + self.raw['Prefix']


class MyMinIORevision(metadata.BaseFileRevisionMetadata):

    @property
    def version_identifier(self):
        return 'version'

    @property
    def version(self):
        if self.raw['IsLatest'] == 'true':
            return 'Latest'
        return self.raw['VersionId']

    @property
    def modified(self):
        return self.raw['LastModified']

    @property
    def extra(self):
        return {
            'md5': self.raw['ETag'].replace('"', '')
        }
