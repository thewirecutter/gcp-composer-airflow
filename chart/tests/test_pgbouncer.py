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

import base64
import unittest

import jmespath
from parameterized import parameterized

from tests.helm_template_generator import render_chart


class PgbouncerTest(unittest.TestCase):
    @parameterized.expand(["pgbouncer-deployment", "pgbouncer-service"])
    def test_pgbouncer_resources_not_created_by_default(self, yaml_filename):
        docs = render_chart(
            show_only=[f"templates/pgbouncer/{yaml_filename}.yaml"],
        )
        assert docs == []

    def test_should_create_pgbouncer(self):
        docs = render_chart(
            values={"pgbouncer": {"enabled": True}},
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )

        assert "Deployment" == jmespath.search("kind", docs[0])
        assert "RELEASE-NAME-pgbouncer" == jmespath.search("metadata.name", docs[0])
        assert "pgbouncer" == jmespath.search("spec.template.spec.containers[0].name", docs[0])

    def test_should_create_pgbouncer_service(self):
        docs = render_chart(
            values={"pgbouncer": {"enabled": True}},
            show_only=["templates/pgbouncer/pgbouncer-service.yaml"],
        )

        assert "Service" == jmespath.search("kind", docs[0])
        assert "RELEASE-NAME-pgbouncer" == jmespath.search("metadata.name", docs[0])
        assert "true" == jmespath.search('metadata.annotations."prometheus.io/scrape"', docs[0])
        assert "9127" == jmespath.search('metadata.annotations."prometheus.io/port"', docs[0])

        assert {"prometheus.io/scrape": "true", "prometheus.io/port": "9127"} == jmespath.search(
            "metadata.annotations", docs[0]
        )

        assert {"name": "pgbouncer", "protocol": "TCP", "port": 6543} in jmespath.search(
            "spec.ports", docs[0]
        )
        assert {"name": "pgbouncer-metrics", "protocol": "TCP", "port": 9127} in jmespath.search(
            "spec.ports", docs[0]
        )

    def test_pgbouncer_service_with_custom_ports(self):
        docs = render_chart(
            values={
                "pgbouncer": {"enabled": True},
                "ports": {"pgbouncer": 1111, "pgbouncerScrape": 2222},
            },
            show_only=["templates/pgbouncer/pgbouncer-service.yaml"],
        )

        assert "true" == jmespath.search('metadata.annotations."prometheus.io/scrape"', docs[0])
        assert "2222" == jmespath.search('metadata.annotations."prometheus.io/port"', docs[0])
        assert {"name": "pgbouncer", "protocol": "TCP", "port": 1111} in jmespath.search(
            "spec.ports", docs[0]
        )
        assert {"name": "pgbouncer-metrics", "protocol": "TCP", "port": 2222} in jmespath.search(
            "spec.ports", docs[0]
        )

    def test_pgbouncer_service_extra_annotations(self):
        docs = render_chart(
            values={
                "pgbouncer": {"enabled": True, "service": {"extraAnnotations": {"foo": "bar"}}},
            },
            show_only=["templates/pgbouncer/pgbouncer-service.yaml"],
        )

        assert {
            "prometheus.io/scrape": "true",
            "prometheus.io/port": "9127",
            "foo": "bar",
        } == jmespath.search("metadata.annotations", docs[0])

    def test_should_create_valid_affinity_tolerations_and_node_selector(self):
        docs = render_chart(
            values={
                "pgbouncer": {
                    "enabled": True,
                    "affinity": {
                        "nodeAffinity": {
                            "requiredDuringSchedulingIgnoredDuringExecution": {
                                "nodeSelectorTerms": [
                                    {
                                        "matchExpressions": [
                                            {"key": "foo", "operator": "In", "values": ["true"]},
                                        ]
                                    }
                                ]
                            }
                        }
                    },
                    "tolerations": [
                        {"key": "dynamic-pods", "operator": "Equal", "value": "true", "effect": "NoSchedule"}
                    ],
                    "nodeSelector": {"diskType": "ssd"},
                }
            },
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )

        assert "foo" == jmespath.search(
            "spec.template.spec.affinity.nodeAffinity."
            "requiredDuringSchedulingIgnoredDuringExecution."
            "nodeSelectorTerms[0]."
            "matchExpressions[0]."
            "key",
            docs[0],
        )
        assert "ssd" == jmespath.search(
            "spec.template.spec.nodeSelector.diskType",
            docs[0],
        )
        assert "dynamic-pods" == jmespath.search(
            "spec.template.spec.tolerations[0].key",
            docs[0],
        )

    def test_no_existing_secret(self):
        docs = render_chart(
            "TEST-PGBOUNCER-CONFIG",
            values={
                "pgbouncer": {"enabled": True},
            },
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )

        assert {
            "name": "pgbouncer-config",
            "secret": {"secretName": "TEST-PGBOUNCER-CONFIG-pgbouncer-config"},
        } == jmespath.search("spec.template.spec.volumes[0]", docs[0])

    def test_existing_secret(self):
        docs = render_chart(
            "TEST-PGBOUNCER-CONFIG",
            values={
                "pgbouncer": {"enabled": True, "configSecretName": "pgbouncer-config-secret"},
            },
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )

        assert {
            "name": "pgbouncer-config",
            "secret": {"secretName": "pgbouncer-config-secret"},
        } == jmespath.search("spec.template.spec.volumes[0]", docs[0])

    def test_pgbouncer_resources_are_configurable(self):
        docs = render_chart(
            values={
                "pgbouncer": {
                    "enabled": True,
                    "resources": {
                        "limits": {"cpu": "200m", 'memory': "128Mi"},
                        "requests": {"cpu": "300m", 'memory': "169Mi"},
                    },
                },
            },
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )
        assert "128Mi" == jmespath.search("spec.template.spec.containers[0].resources.limits.memory", docs[0])
        assert "169Mi" == jmespath.search(
            "spec.template.spec.containers[0].resources.requests.memory", docs[0]
        )
        assert "300m" == jmespath.search("spec.template.spec.containers[0].resources.requests.cpu", docs[0])

    def test_pgbouncer_resources_are_not_added_by_default(self):
        docs = render_chart(
            values={
                "pgbouncer": {"enabled": True},
            },
            show_only=["templates/pgbouncer/pgbouncer-deployment.yaml"],
        )
        assert jmespath.search("spec.template.spec.containers[0].resources", docs[0]) == {}


class PgbouncerConfigTest(unittest.TestCase):
    def test_config_not_created_by_default(self):
        docs = render_chart(
            show_only=["templates/secrets/pgbouncer-config-secret.yaml"],
        )

        assert docs == []

    def _get_pgbouncer_ini(self, values: dict) -> str:
        docs = render_chart(
            values=values,
            show_only=["templates/secrets/pgbouncer-config-secret.yaml"],
        )
        encoded_ini = jmespath.search('data."pgbouncer.ini"', docs[0])
        return base64.b64decode(encoded_ini).decode()

    def test_databases_default(self):
        ini = self._get_pgbouncer_ini({"pgbouncer": {"enabled": True}})

        assert (
            "RELEASE-NAME-metadata = host=RELEASE-NAME-postgresql.default dbname=postgres port=5432"
            " pool_size=10" in ini
        )
        assert (
            "RELEASE-NAME-result-backend = host=RELEASE-NAME-postgresql.default dbname=postgres port=5432"
            " pool_size=5" in ini
        )

    def test_databases_override(self):
        values = {
            "pgbouncer": {"enabled": True, "metadataPoolSize": 12, "resultBackendPoolSize": 7},
            "data": {
                "metadataConnection": {"host": "meta_host", "db": "meta_db", "port": 1111},
                "resultBackendConnection": {
                    "protocol": "postgresql",
                    "host": "rb_host",
                    "user": "someuser",
                    "pass": "someuser",
                    "db": "rb_db",
                    "port": 2222,
                    "sslmode": "disabled",
                },
            },
        }
        ini = self._get_pgbouncer_ini(values)

        assert "RELEASE-NAME-metadata = host=meta_host dbname=meta_db port=1111 pool_size=12" in ini
        assert "RELEASE-NAME-result-backend = host=rb_host dbname=rb_db port=2222 pool_size=7" in ini

    def test_config_defaults(self):
        ini = self._get_pgbouncer_ini({"pgbouncer": {"enabled": True}})

        assert "listen_port = 6543" in ini
        assert "stats_users = postgres" in ini
        assert "max_client_conn = 100" in ini
        assert "verbose = 0" in ini
        assert "log_disconnections = 0" in ini
        assert "log_connections = 0" in ini
        assert "server_tls_sslmode = prefer" in ini
        assert "server_tls_ciphers = normal" in ini

        assert "server_tls_ca_file = " not in ini
        assert "server_tls_cert_file = " not in ini
        assert "server_tls_key_file = " not in ini

    def test_config_overrides(self):
        values = {
            "pgbouncer": {
                "enabled": True,
                "maxClientConn": 111,
                "verbose": 2,
                "logDisconnections": 1,
                "logConnections": 1,
                "sslmode": "verify-full",
                "ciphers": "secure",
            },
            "ports": {"pgbouncer": 7777},
            "data": {"metadataConnection": {"user": "someuser"}},
        }
        ini = self._get_pgbouncer_ini(values)

        assert "listen_port = 7777" in ini
        assert "stats_users = someuser" in ini
        assert "max_client_conn = 111" in ini
        assert "verbose = 2" in ini
        assert "log_disconnections = 1" in ini
        assert "log_connections = 1" in ini
        assert "server_tls_sslmode = verify-full" in ini
        assert "server_tls_ciphers = secure" in ini

    def test_ssl_defaults_dont_create_cert_secret(self):
        docs = render_chart(
            values={"pgbouncer": {"enabled": True}},
            show_only=["templates/secrets/pgbouncer-certificates-secret.yaml"],
        )

        assert docs == []

    def test_ssl_config(self):
        values = {
            "pgbouncer": {"enabled": True, "ssl": {"ca": "someca", "cert": "somecert", "key": "somekey"}}
        }
        ini = self._get_pgbouncer_ini(values)

        assert "server_tls_ca_file = /etc/pgbouncer/root.crt" in ini
        assert "server_tls_cert_file = /etc/pgbouncer/server.crt" in ini
        assert "server_tls_key_file = /etc/pgbouncer/server.key" in ini

        docs = render_chart(
            values=values,
            show_only=["templates/secrets/pgbouncer-certificates-secret.yaml"],
        )

        for key, expected in [("root.crt", "someca"), ("server.crt", "somecert"), ("server.key", "somekey")]:
            encoded = jmespath.search(f'data."{key}"', docs[0])
            value = base64.b64decode(encoded).decode()
            assert expected == value
