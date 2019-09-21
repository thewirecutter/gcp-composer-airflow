# -*- coding: utf-8 -*-
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import unittest

from tests.gcp.utils.base_gcp_system_test_case import (
    SKIP_TEST_WARNING,
    TestDagGcpSystem,
)
from tests.gcp.utils.gcp_authenticator import GCP_GCS_KEY
from tests.gcp.operators.test_gcs_system_helper import GcsSystemTestHelper


@unittest.skipIf(TestDagGcpSystem.skip_check(GCP_GCS_KEY), SKIP_TEST_WARNING)
class GoogleCloudStorageExampleDagsTest(TestDagGcpSystem):
    def setUp(self):
        super().setUp()
        self.helper.create_test_file()

    def tearDown(self):
        self.gcp_authenticator.gcp_authenticate()
        self.helper.remove_test_files()
        self.helper.remove_bucket()
        self.gcp_authenticator.gcp_revoke_authentication()
        super().tearDown()

    def __init__(self, method_name="runTest"):
        super().__init__(method_name, dag_id="example_gcs", gcp_key=GCP_GCS_KEY)
        self.helper = GcsSystemTestHelper()

    def test_run_example_dag(self):
        self._run_dag()
