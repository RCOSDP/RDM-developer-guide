# -*- coding: utf-8 -*-
from nose.tools import (assert_equals, assert_true, assert_false)

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.myminio.tests.factories import MyMinIOAccountFactory
from addons.myminio.provider import MyMinIOProvider
from addons.myminio.serializer import MyMinIOSerializer
from addons.myminio import utils

class MyMinIOAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'myminio'
    ExternalAccountFactory = MyMinIOAccountFactory
    Provider = MyMinIOProvider
    Serializer = MyMinIOSerializer
    client = None
    folder = {
        'path': 'bucket',
        'name': 'bucket',
        'id': 'bucket'
    }

    def test_https(self):
        connection = utils.connect_myminio(host='securehost',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

        connection = utils.connect_myminio(host='securehost:443',
                                            access_key='a',
                                            secret_key='s')
        assert_true(connection.is_secure)
        assert_equals(connection.host, 'securehost')
        assert_equals(connection.port, 443)

    def test_http(self):
        connection = utils.connect_myminio(host='normalhost:80',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 80)

        connection = utils.connect_myminio(host='normalhost:8080',
                                            access_key='a',
                                            secret_key='s')
        assert_false(connection.is_secure)
        assert_equals(connection.host, 'normalhost')
        assert_equals(connection.port, 8080)
