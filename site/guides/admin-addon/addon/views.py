# -*- coding: utf-8 -*-
from django.db.models import Subquery
from rest_framework import status as http_status
from flask import request
import logging

# admin notes取得viewのためのimport
from osf.models import RdmAddonOption

from . import SHORT_NAME
from . import settings
from framework.exceptions import HTTPError
from website.project.decorators import (
    must_be_contributor_or_public,
    must_have_addon,
    must_be_valid_project,
    must_have_permission,
)

logger = logging.getLogger(__name__)


@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myskelton_get_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    return {'param_1': addon.get_param_1()}

@must_be_valid_project
@must_have_permission('admin')
@must_have_addon(SHORT_NAME, 'node')
def myskelton_set_config(**kwargs):
    node = kwargs['node'] or kwargs['project']
    addon = node.get_addon(SHORT_NAME)
    try:
        param_1 = request.json['param_1']
    except KeyError:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)
    logger.info('param_1: {}'.format(param_1))
    addon.set_param_1(param_1)
    return {}

# admin notes取得view
@must_be_valid_project
@must_have_addon(SHORT_NAME, 'node')
def myskelton_get_admin_notes(**kwargs):
    node = kwargs['node'] or kwargs['project']
    res = []
    for ins in node.affiliated_institutions.all():
        opt = RdmAddonOption.objects.filter(
            provider=SHORT_NAME,
            institution_id=ins.id,
            is_allowed=True
        ).first()
        if opt is not None:
            res.append({
                'institution': {
                    'id': ins.id,
                    'name': ins.name,
                },
                'value': opt.admin_notes
            })
    return res
