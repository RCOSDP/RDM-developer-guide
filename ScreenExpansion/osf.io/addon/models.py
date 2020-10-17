import logging

from addons.base.models import BaseNodeSettings
from django.db import models
from . import settings

logger = logging.getLogger(__name__)


class NodeSettings(BaseNodeSettings):
    param_1 = models.TextField(blank=True, null=True)

    def get_param_1(self):
        if self.param_1 is None or self.param_1 == '':
            return settings.DEFAULT_PARAM_1
        return self.param_1

    def set_param_1(self, param_1):
        self.param_1 = param_1
        self.save()
