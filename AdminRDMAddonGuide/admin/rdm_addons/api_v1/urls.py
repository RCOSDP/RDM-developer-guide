# -*- coding: utf-8 -*-

from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^oauth/accounts/(?P<external_account_id>\w+)/(?P<institution_id>-?[0-9]+)/$', views.OAuthView.as_view(), name='oauth'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/$', views.SettingsView.as_view(), name='settings'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/accounts/$', views.AccountsView.as_view(), name='accounts'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/manage/$', views.ManageView.as_view(), name='manage'),
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/organization/$', views.OrganizationView.as_view(), name='organization'),
    # ルーティング追加
    url(r'^settings/(?P<addon_name>\w+)/(?P<institution_id>-?[0-9]+)/adminnotes/$', views.AdminNotesView.as_view(), name='adminnotes'),
]
