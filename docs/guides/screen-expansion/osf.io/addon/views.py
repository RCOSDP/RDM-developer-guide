# -*- coding: utf-8 -*-
from rest_framework import status as http_status
from flask import request
import logging

from . import SHORT_NAME
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
)
from website.ember_osf_web.views import use_ember_app

logger = logging.getLogger(__name__)

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myscreen_get_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return {'param_1': addon.get_param_1()}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myscreen_set_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        param_1 = request.json['param_1']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    logger.info('param_1: {}'.format(param_1))
    addon.set_param_1(param_1)
    return {}

# ember: ここから
@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def project_myscreen(**kwargs):
    return use_ember_app()

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myscreen_get_config_ember(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return {'data': {'id': node._id, 'type': 'myscreen-config',
                     'attributes': {
                         'param1': addon.get_param_1()
                     }}}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myscreen_set_config_ember(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        config = request.json['data']['attributes']
        param_1 = config['param1']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    addon.set_param_1(param_1)
    return {'data': {'id': node._id, 'type': 'myscreen-config',
                     'attributes': {
                         'param1': param_1
                     }}}
# ember: ここまで
