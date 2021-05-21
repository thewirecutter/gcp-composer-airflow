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
import os
import random
import shutil
import string
import unittest
from unittest import mock

from google.auth.transport import requests

from airflow.configuration import WEBSERVER_CONFIG
from airflow.security import permissions
from airflow.www import app
from tests.test_utils.config import conf_vars
from tests.test_utils.fab_utils import create_user


class TestBase(unittest.TestCase):
    WEBSERVER_CONFIG_BACKUP = WEBSERVER_CONFIG + '.backup'
    COMPOSER_WEBSERVER_CONFIG = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "../../airflow/composer/webserver_config.py"
    )

    @classmethod
    def setUpClass(cls):
        # Override webserver config with Composer specific.
        shutil.copy(WEBSERVER_CONFIG, cls.WEBSERVER_CONFIG_BACKUP)
        shutil.copy(cls.COMPOSER_WEBSERVER_CONFIG, WEBSERVER_CONFIG)
        with conf_vars(
            {
                ("webserver", "google_oauth2_audience"): "audience",
                ("webserver", "jwt_public_key_url"): "",
                ("webserver", "rbac_user_registration_role"): "Viewer",
                ("webserver", "rbac_autoregister_per_folder_roles"): "True",
            }
        ):
            cls.app = app.create_app(testing=True)
        cls.sm = cls.app.appbuilder.sm  # pylint: disable=no-member

    @classmethod
    def tearDownClass(cls):
        # Return back original webserver config.
        shutil.copy(cls.WEBSERVER_CONFIG_BACKUP, WEBSERVER_CONFIG)

    def get_random_id(self):
        return ''.join(random.choice(string.ascii_letters) for _ in range(10))

    def setUp(self):
        self.client = self.app.test_client()

    def test_login_no_post(self):
        resp = self.client.post("/login/")
        assert resp.status_code == 404

    def test_login_incorrect_jwt(self):
        resp = self.client.get("/login/")
        assert resp.get_data() == b"Not authorized or account inactive"
        assert resp.status_code == 403

    @mock.patch("airflow.composer.security_manager.id_token", autospec=True)
    def test_login_user_auto_registered(self, id_token_mock):
        username = f"test-{self.get_random_id()}"
        email = f"test-{self.get_random_id()}@test.com"

        def id_token_mock_verify_token_side_effect(id_token, request, audience, certs_url):
            assert id_token == "jwt-test"
            assert isinstance(request, requests.Request)
            assert audience == "audience"
            assert certs_url == "https://www.gstatic.com/iap/verify/public_key"
            return {
                "sub": username,
                "email": email,
            }

        id_token_mock.verify_token.side_effect = id_token_mock_verify_token_side_effect

        resp = self.client.get("/login/", headers={"X-Goog-IAP-JWT-Assertion": "jwt-test"})
        assert resp.headers["Location"] == "http://localhost/"
        assert resp.status_code == 302
        assert self.sm.find_user(username=username).roles == [self.sm.find_role(name="Viewer")]

        # Test already logged in.
        resp = self.client.get("/login/", headers={"X-Goog-IAP-JWT-Assertion": "jwt-test"})
        assert resp.headers["Location"] == "http://localhost/"
        assert resp.status_code == 302

        # Test next parameter.
        self.client.get("/logout/")
        resp = self.client.get(
            "/login/?next=http%3A%2F%2Flocalhost%2Faaa", headers={"X-Goog-IAP-JWT-Assertion": "jwt-test"}
        )
        assert resp.headers["Location"] == "http://localhost/aaa"
        assert resp.status_code == 302

        # Test login user with existing email (registered above) but wrong username.
        def id_token_mock_verify_token_side_effect(
            id_token, request, audience, certs_url
        ):  # pylint: disable=function-redefined
            assert id_token == "jwt-test"
            assert isinstance(request, requests.Request)
            assert audience == "audience"
            assert certs_url == "https://www.gstatic.com/iap/verify/public_key"
            return {
                "sub": "wrong-username",
                "email": email,
            }

        id_token_mock.verify_token.side_effect = id_token_mock_verify_token_side_effect

        self.client.get("/logout/")
        resp = self.client.get("/login/", headers={"X-Goog-IAP-JWT-Assertion": "jwt-test"})
        assert resp.get_data() == b"Not authorized or account inactive"
        assert resp.status_code == 403

    @mock.patch("airflow.composer.security_manager.id_token", autospec=True)
    def test_login_user_preregistered(self, id_token_mock):
        username = f"test-{self.get_random_id()}"
        email = f"test-{self.get_random_id()}@test.com"

        # Preregister user.
        create_user(self.app, username=email, role_name="Test")
        assert self.sm.find_user(username=email)

        def id_token_mock_verify_token_side_effect(id_token, request, audience, certs_url):
            assert id_token == "jwt-test"
            assert isinstance(request, requests.Request)
            assert audience == "audience"
            assert certs_url == "https://www.gstatic.com/iap/verify/public_key"
            return {
                "sub": username,
                "email": email,
            }

        id_token_mock.verify_token.side_effect = id_token_mock_verify_token_side_effect

        resp = self.client.get("/login/", headers={"X-Goog-IAP-JWT-Assertion": "jwt-test"})
        assert not self.sm.find_user(username=email)
        assert self.sm.find_user(username=username)
        assert resp.headers["Location"] == "http://localhost/"
        assert resp.status_code == 302

    def test_nodags_role(self):
        self.assertIn(
            {
                "role": "NoDags",
                "perms": [
                    p
                    for p in self.sm.VIEWER_PERMISSIONS + self.sm.USER_PERMISSIONS
                    if p[1] != permissions.RESOURCE_DAG
                ],
            },
            self.sm.ROLE_CONFIGS,
        )
