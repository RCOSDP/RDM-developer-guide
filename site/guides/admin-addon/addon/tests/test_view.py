# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema

# TestAdminNotesViews のために ExternalAccountFactory のimportを追加
from osf_tests.factories import ProjectFactory, ExternalAccountFactory

from .. import SHORT_NAME
from .. import settings
from .utils import BaseAddonTestCase
from website.util import api_url_for

# TestAdminNotesViews のためのimport追加
from admin_tests.rdm_addons import factories as rdm_addon_factories


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


# API の追加
class TestAdminNotesViews(BaseAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestAdminNotesViews, self).setUp()
        self.external_account = ExternalAccountFactory(provider=SHORT_NAME)

        self.rdm_addon_option = rdm_addon_factories.RdmAddonOptionFactory()
        self.rdm_addon_option.provider = self.external_account.provider
        self.rdm_addon_option.external_accounts.add(self.external_account)
        self.rdm_addon_option.save()

        self.project.affiliated_institutions.add(self.rdm_addon_option.institution)
        self.project.save()

    def tearDown(self):
        super(TestAdminNotesViews, self).tearDown()
        institution = self.rdm_addon_option.institution
        self.project.affiliated_institutions.remove(institution)
        if self.rdm_addon_option.external_accounts.filter(pk=self.external_account.id).exists():
            self.rdm_addon_option.external_accounts.remove(self.external_account)
        self.rdm_addon_option.delete()
        institution.delete()
        self.external_account.delete()

    def test_get(self, *args, **kwargs):
        self.rdm_addon_option.admin_notes = 'fake admin notes'
        self.rdm_addon_option.save()
        url = self.project.api_url_for('{}_get_admin_notes'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(len(res.json), 1)
        assert_in('institution', res.json[0])
        assert_in('id', res.json[0]['institution'])
        assert_equals(res.json[0]['institution']['id'], self.rdm_addon_option.institution.id)
        assert_in('value', res.json[0])
        assert_equals(res.json[0]['value'], 'fake admin notes')

    def test_get_with_empty_notes(self, *args, **kwargs):
        self.rdm_addon_option.admin_notes = None
        self.rdm_addon_option.save()
        url = self.project.api_url_for('{}_get_admin_notes'.format(SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equals(len(res.json), 1)
        assert_in('institution', res.json[0])
        assert_in('id', res.json[0]['institution'])
        assert_equals(res.json[0]['institution']['id'], self.rdm_addon_option.institution.id)
        assert_in('value', res.json[0])
        assert_equals(res.json[0]['value'], None)
