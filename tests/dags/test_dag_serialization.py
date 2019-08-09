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

"""Unit tests for stringified DAGs."""

import json
import mock
import multiprocessing
import unittest
from datetime import datetime

from airflow import example_dags
from airflow.contrib import example_dags as contrib_example_dags
from airflow.dag.serialization import Serialization, SerializedBaseOperator, SerializedDAG
from airflow.dag.serialization.enums import Encoding
from airflow.hooks.base_hook import BaseHook
from airflow.models import BaseOperator, Connection, DAG, DagBag
from airflow.operators.bash_operator import BashOperator


# FIXME: to remove useless fields.
serialized_simple_dag_ground_truth = (
    '{"__type": "dag", "__var": {'
    '"schedule_interval": {"__var": 86400.0, "__type": "timedelta"}, '
    '"default_view": "tree", '
    '"max_active_runs": 16, '
    '"partial": false, '
    '"orientation": "LR", '
    '"_description": "", '
    '"is_subdag": false, '
    '"safe_dag_id": "simple_dag", '
    '"fileloc": null, '
    '"_concurrency": 16, '
    '"catchup": true, '
    '"last_loaded": null, '
    '"params": {"__var": {}, "__type": "dict"}, '
    '"_schedule_interval": {"__var": 86400.0, "__type": "timedelta"}, '
    '"timezone": {"__var": "UTC", "__type": "timezone"}, '
    '"default_args": {"__var": {}, "__type": "dict"}, '
    '"_dag_id": "simple_dag", '
    '"_full_filepath": "", '
    '"task_dict": {"__var": {"simple_task": {"__var": {'
    '"_downstream_task_ids": {"__var": [], "__type": "set"}, '
    '"trigger_rule": "all_success", '
    '"ui_color": "#fff", '
    '"inlets": [], '
    '"retry_exponential_backoff": false, '
    '"owner": "airflow", '
    '"email_on_retry": true, '
    '"weight_rule": "downstream", '
    '"adhoc": false, '
    '"params": {"__var": {}, "__type": "dict"}, '
    '"_task_type": "BaseOperator", '
    '"ui_fgcolor": "#000", '
    '"priority_weight": 1, '
    '"start_date": {"__var": "2019-08-01T00:00:00+00:00", "__type": "datetime"}, '
    '"resources": null, '
    '"wait_for_downstream": false, '
    '"_inlets": {"__var": {"task_ids": [], "auto": false, "datasets": []}, "__type": "dict"}, '
    '"outlets": [], '
    '"template_fields": [], '
    '"email_on_failure": true, '
    '"retry_delay": {"__var": 300.0, "__type": "timedelta"}, '
    '"executor_config": {"__var": {}, "__type": "dict"}, '
    '"retries": 0, '
    '"_outlets": {"__var": {"datasets": []}, "__type": "dict"}, '
    '"task_id": "simple_task", '
    '"_upstream_task_ids": {"__var": [], "__type": "set"}, '
    '"queue": "default", '
    '"depends_on_past": false, '
    '"_dag": {"__type": "dag", "__var": "simple_dag"}'
    '}, "__type": "operator"}}, '
    '"__type": "dict"}}}')


def make_example_dags(module):
    """Loads DAGs from a module for test."""
    dagbag = DagBag(module.__path__[0])
    return dagbag.dags


def make_simple_dag():
    """Make very simple DAG to verify serialization result."""
    dag = DAG(dag_id='simple_dag')
    _ = BaseOperator(task_id='simple_task', dag=dag, start_date=datetime(2019, 8, 1))
    return {'simple_dag': dag}


def make_user_defined_macro_filter_dag():
    """ Make DAGs with user defined macros and filters using locally defined methods.

    The examples here test:
        (1) functions can be successfully displayed on UI;
        (2) templates with function macros have been rendered before serialization.
    """
    def compute_next_execution_date(dag, execution_date):
        return dag.following_schedule(execution_date)

    default_args = {
        'start_date': datetime(2019, 7, 10)
    }
    dag = DAG(
        'user_defined_macro_filter_dag',
        default_args=default_args,
        user_defined_macros={
            'next_execution_date': compute_next_execution_date,
        },
        user_defined_filters={
            'hello': lambda name: 'Hello %s' % name
        },
        catchup=False
    )
    _ = BashOperator(
        task_id='echo',
        bash_command='echo "{{ next_execution_date(dag, execution_date) }}"',
        dag=dag,
    )
    return {dag.dag_id: dag}


def collect_dags():
    """Collects DAGs to test."""
    dags = {}
    dags.update(make_simple_dag())
    dags.update(make_user_defined_macro_filter_dag())
    dags.update(make_example_dags(example_dags))
    dags.update(make_example_dags(contrib_example_dags))
    return dags


def serialize_subprocess(queue):
    """Validate pickle in a subprocess."""
    dags = collect_dags()
    for dag in dags.values():
        queue.put(Serialization.to_json(dag))
    queue.put(None)


class TestStringifiedDAGs(unittest.TestCase):
    """Unit tests for stringified DAGs."""

    def setUp(self):
        super(TestStringifiedDAGs, self).setUp()
        BaseHook.get_connection = mock.Mock(
            return_value=Connection(
                extra=('{'
                       '"project_id": "mock", '
                       '"location": "mock", '
                       '"instance": "mock", '
                       '"database_type": "postgres", '
                       '"use_proxy": "False", '
                       '"use_ssl": "False"'
                       '}')))

    def test_serialization(self):
        """Serailzation and deserialization should work for every DAG and Operator."""
        dags = collect_dags()
        serialized_dags = {}
        for _, v in dags.items():
            dag = Serialization.to_json(v)
            serialized_dags[v.dag_id] = dag

        # Verify JSON schema of serialized DAGs.
        for json_str in serialized_dags.values():
            json_object = json.loads(json_str)
            task_dict = json_object['__var']['task_dict']['__var']

            # Verify JSON schema of serialized operators.
            for task in task_dict.values():
                SerializedBaseOperator.validate_json(json.dumps(task, ensure_ascii=True))

            SerializedDAG.validate_json(json_str)

        # Compares with the ground truth of JSON string.
        self.validate_serialized_dag(
            serialized_dags['simple_dag'],
            serialized_simple_dag_ground_truth)

    def validate_serialized_dag(self, json_dag, ground_truth_dag):
        """Verify serialized DAGs match the ground truth."""
        json_dag = json.loads(json_dag)
        self.assertTrue(
            json_dag[Encoding.VAR]['last_loaded'][Encoding.TYPE] == 'datetime')
        json_dag[Encoding.VAR]['last_loaded'] = None
        self.assertTrue(
            json_dag[Encoding.VAR]['fileloc'].split('/')[-1] == 'test_dag_serialization.py')
        json_dag[Encoding.VAR]['fileloc'] = None
        json_dag[Encoding.VAR]['task_dict'][Encoding.VAR]['simple_task'][Encoding.VAR]['resources'] = None
        self.assertTrue(json.dumps(json_dag) == ground_truth_dag)

    def test_deserialization(self):
        """A serialized DAG can be deserialized in another process."""
        queue = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=serialize_subprocess, args=(queue,))
        proc.daemon = True
        proc.start()

        stringified_dags = {}
        while True:
            v = queue.get()
            if v is None:
                break
            dag = Serialization.from_json(v)
            self.assertTrue(isinstance(dag, DAG))
            stringified_dags[dag.dag_id] = dag

        dags = collect_dags()
        self.assertTrue(set(stringified_dags.keys()) == set(dags.keys()))

        # Verify deserialized DAGs.
        example_skip_dag = stringified_dags['example_skip_dag']
        skip_operator_1_task = example_skip_dag.task_dict['skip_operator_1']
        self.validate_deserialized_task(
            skip_operator_1_task, 'DummySkipOperator', '#e8b7e4', '#000')

    def validate_deserialized_task(self, task, task_type, ui_color, ui_fgcolor):
        """Verify non-airflow operators are casted to BaseOperator."""
        self.assertTrue(isinstance(task, SerializedBaseOperator))
        # Verify the original operator class is recorded for UI.
        self.assertTrue(task.task_type == task_type)
        self.assertTrue(task.ui_color == ui_color)
        self.assertTrue(task.ui_fgcolor == ui_fgcolor)


if __name__ == '__main__':
    unittest.main()
