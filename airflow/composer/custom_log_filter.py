# -*- coding: utf-8 -*-
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Custom log filter for Cloud Composer."""
import logging


def _is_redis_warning(record):
    """
    Method that detects using Redis as result backend warning.

    The concern with running Redis backend is that celery task messages may get
    lost across Redis restarts. Composer has provisioned Redis service using
    StatefulSet and saves a snapshot every 60 seconds to a persistent disk.
    So it's not a concern to use the Redis backend in Cloud Composer.

    From https://groups.google.com/g/cloud-composer-discuss/c/8SY2NdjjOS4
    """
    return record.getMessage().startswith(
        'You have configured a result_backend of redis://')


class ComposerFilter(logging.Filter):

    def filter(self, record):
        if _is_redis_warning(record):
            return False
        return True
