# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

from airflow.contrib.hooks.redis_hook import RedisHook
from airflow.operators.sensors import BaseSensorOperator
from airflow.utils.decorators import apply_defaults


class RedisKeySensor(BaseSensorOperator):
    """
    Checks for the existence of a key in a Redis database
    """
    template_fields = ('key',)
    ui_color = '#f0eee4'

    @apply_defaults
    def __init__(self, key, redis_conn_id, *args, **kwargs):
        """
        Create a new RedisKeySensor

        :param key: The key to be monitored
        :type key: string
        :param redis_conn_id: The connection ID to use when connecting to Redis DB.
        :type redis_conn_id: string
        """
        super(RedisKeySensor, self).__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)
        self.redis_conn_id = redis_conn_id
        self.key = key

    def poke(self, context):
        self.logger.info('Sensor check existence of key: %s', self.key)
        return RedisHook(self.redis_conn_id).key_exists(self.key)
