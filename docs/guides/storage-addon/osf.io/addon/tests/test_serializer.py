# -*- coding: utf-8 -*-
"""Serializer tests for the My MinIO addon."""
import mock
import pytest

from addons.base.tests.serializers import StorageAddonSerializerTestSuiteMixin
from addons.myminio.tests.factories import MyMinIOAccountFactory
from addons.myminio.serializer import MyMinIOSerializer

from tests.base import OsfTestCase

pytestmark = pytest.mark.django_db

class TestMyMinIOSerializer(StorageAddonSerializerTestSuiteMixin, OsfTestCase):
    addon_short_name = 'myminio'
    Serializer = MyMinIOSerializer
    ExternalAccountFactory = MyMinIOAccountFactory
    client = None

    def set_provider_id(self, pid):
        self.node_settings.folder_id = pid

    def setUp(self):
        self.mock_can_list = mock.patch('addons.myminio.serializer.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        super(TestMyMinIOSerializer, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        super(TestMyMinIOSerializer, self).tearDown()
