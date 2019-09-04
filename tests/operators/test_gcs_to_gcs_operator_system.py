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
"""System tests for Google Cloud Build operators"""
import unittest

from tests.operators.test_gcs_to_gcs_system_helper import GcsToGcsTestHelper
from tests.contrib.utils.base_gcp_system_test_case import SKIP_TEST_WARNING, TestDagGcpSystem, \
    OPERATORS_EXAMPLES_DAG_FOLDER
from tests.contrib.utils.gcp_authenticator import GCP_GCS_KEY


@unittest.skipIf(TestDagGcpSystem.skip_check(GCP_GCS_KEY), SKIP_TEST_WARNING)
class GcsToGcsExampleDagsSystemTest(TestDagGcpSystem):
    """
    System tests for Google Cloud Storage to Google Cloud Storage transfer operators

    It use a real service.
    """

    def __init__(self, method_name="runTest"):
        super().__init__(
            method_name,
            dag_id="example_gcs_to_gcs",
            dag_name="example_gcs_to_gcs.py",
            example_dags_folder=OPERATORS_EXAMPLES_DAG_FOLDER,
            gcp_key=GCP_GCS_KEY,
        )
        self.helper = GcsToGcsTestHelper()

    def setUp(self):
        super().setUp()
        self.gcp_authenticator.gcp_authenticate()
        try:
            self.helper.create_buckets()
        finally:
            self.gcp_authenticator.gcp_revoke_authentication()

    def test_run_example_dag(self):
        self._run_dag()

    def tearDown(self):
        self.gcp_authenticator.gcp_authenticate()
        try:
            self.helper.delete_buckets()
        finally:
            self.gcp_authenticator.gcp_revoke_authentication()
        super().tearDown()
