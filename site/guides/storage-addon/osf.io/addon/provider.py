from addons.myminio import SHORT_NAME, FULL_NAME
from addons.myminio.serializer import MyMinIOSerializer


class MyMinIOProvider(object):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = FULL_NAME
    short_name = SHORT_NAME
    serializer = MyMinIOSerializer

    def __init__(self, account=None):
        super(MyMinIOProvider, self).__init__()

        # provide an unauthenticated session by default
        self.account = account

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.provider_id if self.account else 'anonymous'
        )
