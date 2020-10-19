# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory

from .. import SHORT_NAME
from .. import settings
from .utils import BaseAddonTestCase
from website.util import api_url_for


class TestViews(BaseAddonTestCase, OsfTestCase):

    def test_empty_param_1(self):
        self.node_settings.set_param_1('')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['param_1'], settings.DEFAULT_PARAM_1)

    def test_param_1(self):
        self.node_settings.set_param_1('PARAM_1')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['param_1'], 'PARAM_1')

    # ember: ここから
    def test_ember_empty_param_1(self):
        self.node_settings.set_param_1('')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.node_settings._id)
        assert_equals(res.json['data']['type'], 'myscreen-config')
        assert_equals(res.json['data']['attributes']['param1'], settings.DEFAULT_PARAM_1)

    def test_ember_param_1(self):
        self.node_settings.set_param_1('PARAM_1')
        self.node_settings.save()
        url = self.project.api_url_for('{}_get_config_ember'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(res.json['data']['id'], self.node_settings._id)
        assert_equals(res.json['data']['type'], 'myscreen-config')
        assert_equals(res.json['data']['attributes']['param1'], 'PARAM_1')
    # ember: ここまで
