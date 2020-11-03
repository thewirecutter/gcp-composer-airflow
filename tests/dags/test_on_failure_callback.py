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

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator

DEFAULT_DATE = datetime(2016, 1, 1)

args = {
    'owner': 'airflow',
    'start_date': DEFAULT_DATE,
}

dag = DAG(dag_id='test_om_failure_callback_dag', default_args=args)


def write_data_to_callback(*arg, **kwargs):  # pylint: disable=unused-argument
    with open(os.environ.get('AIRFLOW_CALLBACK_FILE'), "w+") as f:
        f.write("Callback fired")


task = DummyOperator(
    task_id='test_om_failure_callback_task', dag=dag, on_failure_callback=write_data_to_callback
)
