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
from datetime import timedelta, time
import pytest

from airflow import DAG, exceptions, settings
from airflow.exceptions import AirflowException, AirflowSensorTimeout
from airflow.models import TaskInstance, DagBag
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.sensors.external_task_sensor import ExternalTaskMarker, ExternalTaskSensor
from airflow.sensors.time_sensor import TimeSensor
from airflow.utils.state import State
from airflow.utils.timezone import datetime

DEFAULT_DATE = datetime(2015, 1, 1)
TEST_DAG_ID = 'unit_test_dag'
TEST_TASK_ID = 'time_sensor_check'
DEV_NULL = '/dev/null'


class ExternalTaskSensorTests(unittest.TestCase):

    def setUp(self):
        self.dagbag = DagBag(
            dag_folder=DEV_NULL,
            include_examples=True
        )
        self.args = {
            'owner': 'airflow',
            'start_date': DEFAULT_DATE
        }
        self.dag = DAG(TEST_DAG_ID, default_args=self.args)

    def test_time_sensor(self):
        t = TimeSensor(
            task_id=TEST_TASK_ID,
            target_time=time(0),
            dag=self.dag
        )
        t.run(start_date=DEFAULT_DATE, end_date=DEFAULT_DATE, ignore_ti_state=True)

    def test_external_task_sensor(self):
        self.test_time_sensor()
        t = ExternalTaskSensor(
            task_id='test_external_task_sensor_check',
            external_dag_id=TEST_DAG_ID,
            external_task_id=TEST_TASK_ID,
            dag=self.dag
        )
        t.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True
        )

    def test_external_dag_sensor(self):

        other_dag = DAG(
            'other_dag',
            default_args=self.args,
            end_date=DEFAULT_DATE,
            schedule_interval='@once')
        other_dag.create_dagrun(
            run_id='test',
            start_date=DEFAULT_DATE,
            execution_date=DEFAULT_DATE,
            state=State.SUCCESS)
        t = ExternalTaskSensor(
            task_id='test_external_dag_sensor_check',
            external_dag_id='other_dag',
            external_task_id=None,
            dag=self.dag
        )
        t.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True
        )

    def test_templated_sensor(self):
        with self.dag:
            sensor = ExternalTaskSensor(
                task_id='templated_task',
                external_dag_id='dag_{{ ds }}',
                external_task_id='task_{{ ds }}'
            )

        instance = TaskInstance(sensor, DEFAULT_DATE)
        instance.render_templates()

        self.assertEqual(sensor.external_dag_id,
                         "dag_{}".format(DEFAULT_DATE.date()))
        self.assertEqual(sensor.external_task_id,
                         "task_{}".format(DEFAULT_DATE.date()))

    def test_external_task_sensor_fn_multiple_execution_dates(self):
        bash_command_code = """
{% set s=execution_date.time().second %}
echo "second is {{ s }}"
if [[ $(( {{ s }} % 60 )) == 1 ]]
    then
        exit 1
fi
exit 0
"""
        dag_external_id = TEST_DAG_ID + '_external'
        dag_external = DAG(
            dag_external_id,
            default_args=self.args,
            schedule_interval=timedelta(seconds=1))
        task_external_with_failure = BashOperator(
            task_id="task_external_with_failure",
            bash_command=bash_command_code,
            retries=0,
            dag=dag_external)
        task_external_without_failure = DummyOperator(
            task_id="task_external_without_failure",
            retries=0,
            dag=dag_external)

        task_external_without_failure.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE + timedelta(seconds=1),
            ignore_ti_state=True)

        session = settings.Session()
        TI = TaskInstance
        try:
            task_external_with_failure.run(
                start_date=DEFAULT_DATE,
                end_date=DEFAULT_DATE + timedelta(seconds=1),
                ignore_ti_state=True)
            # The test_with_failure task is excepted to fail
            # once per minute (the run on the first second of
            # each minute).
        except Exception as e:
            failed_tis = session.query(TI).filter(
                TI.dag_id == dag_external_id,
                TI.state == State.FAILED,
                TI.execution_date == DEFAULT_DATE + timedelta(seconds=1)).all()
            if len(failed_tis) == 1 and \
               failed_tis[0].task_id == 'task_external_with_failure':
                pass
            else:
                raise e

        dag_id = TEST_DAG_ID
        dag = DAG(
            dag_id,
            default_args=self.args,
            schedule_interval=timedelta(minutes=1))
        task_without_failure = ExternalTaskSensor(
            task_id='task_without_failure',
            external_dag_id=dag_external_id,
            external_task_id='task_external_without_failure',
            execution_date_fn=lambda dt: [dt + timedelta(seconds=i)
                                          for i in range(2)],
            allowed_states=['success'],
            retries=0,
            timeout=1,
            poke_interval=1,
            dag=dag)
        task_with_failure = ExternalTaskSensor(
            task_id='task_with_failure',
            external_dag_id=dag_external_id,
            external_task_id='task_external_with_failure',
            execution_date_fn=lambda dt: [dt + timedelta(seconds=i)
                                          for i in range(2)],
            allowed_states=['success'],
            retries=0,
            timeout=1,
            poke_interval=1,
            dag=dag)

        task_without_failure.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True)

        with self.assertRaises(AirflowSensorTimeout):
            task_with_failure.run(
                start_date=DEFAULT_DATE,
                end_date=DEFAULT_DATE,
                ignore_ti_state=True)

    def test_external_task_sensor_delta(self):
        self.test_time_sensor()
        t = ExternalTaskSensor(
            task_id='test_external_task_sensor_check_delta',
            external_dag_id=TEST_DAG_ID,
            external_task_id=TEST_TASK_ID,
            execution_delta=timedelta(0),
            allowed_states=['success'],
            dag=self.dag
        )
        t.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True
        )

    def test_external_task_sensor_fn(self):
        self.test_time_sensor()
        # check that the execution_fn works
        t = ExternalTaskSensor(
            task_id='test_external_task_sensor_check_delta',
            external_dag_id=TEST_DAG_ID,
            external_task_id=TEST_TASK_ID,
            execution_date_fn=lambda dt: dt + timedelta(0),
            allowed_states=['success'],
            dag=self.dag
        )
        t.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True
        )
        # double check that the execution is being called by failing the test
        t2 = ExternalTaskSensor(
            task_id='test_external_task_sensor_check_delta',
            external_dag_id=TEST_DAG_ID,
            external_task_id=TEST_TASK_ID,
            execution_date_fn=lambda dt: dt + timedelta(days=1),
            allowed_states=['success'],
            timeout=1,
            poke_interval=1,
            dag=self.dag
        )
        with self.assertRaises(exceptions.AirflowSensorTimeout):
            t2.run(
                start_date=DEFAULT_DATE,
                end_date=DEFAULT_DATE,
                ignore_ti_state=True
            )

    def test_external_task_sensor_fn_multiple_args(self):
        """Check this task sensor passes multiple args with full context. If no failure, means clean run."""
        self.test_time_sensor()

        def my_func(dt, context):
            assert context['execution_date'] == dt
            return dt + timedelta(0)

        op1 = ExternalTaskSensor(
            task_id='test_external_task_sensor_multiple_arg_fn',
            external_dag_id=TEST_DAG_ID,
            external_task_id=TEST_TASK_ID,
            execution_date_fn=my_func,
            allowed_states=['success'],
            dag=self.dag
        )
        op1.run(
            start_date=DEFAULT_DATE,
            end_date=DEFAULT_DATE,
            ignore_ti_state=True
        )

    def test_external_task_sensor_error_delta_and_fn(self):
        self.test_time_sensor()
        # Test that providing execution_delta and a function raises an error
        with self.assertRaises(ValueError):
            ExternalTaskSensor(
                task_id='test_external_task_sensor_check_delta',
                external_dag_id=TEST_DAG_ID,
                external_task_id=TEST_TASK_ID,
                execution_delta=timedelta(0),
                execution_date_fn=lambda dt: dt,
                allowed_states=['success'],
                dag=self.dag
            )

    def test_catch_invalid_allowed_states(self):
        with self.assertRaises(ValueError):
            ExternalTaskSensor(
                task_id='test_external_task_sensor_check',
                external_dag_id=TEST_DAG_ID,
                external_task_id=TEST_TASK_ID,
                allowed_states=['invalid_state'],
                dag=self.dag
            )

        with self.assertRaises(ValueError):
            ExternalTaskSensor(
                task_id='test_external_task_sensor_check',
                external_dag_id=TEST_DAG_ID,
                external_task_id=None,
                allowed_states=['invalid_state'],
                dag=self.dag
            )

    def test_external_task_sensor_waits_for_task_check_existence(self):
        t = ExternalTaskSensor(
            task_id='test_external_task_sensor_check',
            external_dag_id="example_bash_operator",
            external_task_id="non-existing-task",
            check_existence=True,
            dag=self.dag
        )

        with self.assertRaises(AirflowException):
            t.run(
                start_date=DEFAULT_DATE,
                end_date=DEFAULT_DATE,
                ignore_ti_state=True
            )

    def test_external_task_sensor_waits_for_dag_check_existence(self):
        t = ExternalTaskSensor(
            task_id='test_external_task_sensor_check',
            external_dag_id="non-existing-dag",
            external_task_id=None,
            check_existence=True,
            dag=self.dag
        )

        with self.assertRaises(AirflowException):
            t.run(
                start_date=DEFAULT_DATE,
                end_date=DEFAULT_DATE,
                ignore_ti_state=True
            )


@pytest.fixture
def dag_bag_ext():
    """
    Create a DagBag with DAGs looking like this. The dotted lines represent external dependencies
    set up using ExternalTaskMarker and ExternalTaskSensor.

    dag_0:   task_a_0 >> task_b_0
                             |
                             |
    dag_1:                   ---> task_a_1 >> task_b_1
                                                  |
                                                  |
    dag_2:                                        ---> task_a_2 >> task_b_2
                                                                       |
                                                                       |
    dag_3:                                                             ---> task_a_3 >> task_b_3
    """
    dag_bag = DagBag(dag_folder=DEV_NULL, include_examples=False)

    dag_0 = DAG("dag_0", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_0 = DummyOperator(task_id="task_a_0", dag=dag_0)
    task_b_0 = ExternalTaskMarker(task_id="task_b_0",
                                  external_dag_id="dag_1",
                                  external_task_id="task_a_1",
                                  recursion_depth=3,
                                  dag=dag_0)
    task_a_0 >> task_b_0

    dag_1 = DAG("dag_1", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_1 = ExternalTaskSensor(task_id="task_a_1",
                                  external_dag_id=dag_0.dag_id,
                                  external_task_id=task_b_0.task_id,
                                  dag=dag_1,
                                  mode="reschedule")
    task_b_1 = ExternalTaskMarker(task_id="task_b_1",
                                  external_dag_id="dag_2",
                                  external_task_id="task_a_2",
                                  recursion_depth=2,
                                  dag=dag_1)
    task_a_1 >> task_b_1

    dag_2 = DAG("dag_2", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_2 = ExternalTaskSensor(task_id="task_a_2",
                                  external_dag_id=dag_1.dag_id,
                                  external_task_id=task_b_1.task_id,
                                  dag=dag_2,
                                  mode="reschedule")
    task_b_2 = ExternalTaskMarker(task_id="task_b_2",
                                  external_dag_id="dag_3",
                                  external_task_id="task_a_3",
                                  recursion_depth=1,
                                  dag=dag_2)
    task_a_2 >> task_b_2

    dag_3 = DAG("dag_3", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_3 = ExternalTaskSensor(task_id="task_a_3",
                                  external_dag_id=dag_2.dag_id,
                                  external_task_id=task_b_2.task_id,
                                  dag=dag_3,
                                  mode="reschedule")
    task_b_3 = DummyOperator(task_id="task_b_3", dag=dag_3)
    task_a_3 >> task_b_3

    for dag in [dag_0, dag_1, dag_2, dag_3]:
        dag_bag.bag_dag(dag, None, dag)

    return dag_bag


def run_tasks(dag_bag, execution_date=DEFAULT_DATE):
    """
    Run all tasks in the DAGs in the given dag_bag. Return the TaskInstance objects as a dict
    keyed by task_id.
    """
    tis = {}

    for dag in dag_bag.dags.values():
        for task in dag.tasks:
            ti = TaskInstance(task=task, execution_date=execution_date)
            tis[task.task_id] = ti
            ti.run(ignore_all_deps=True, ignore_ti_state=True, mark_success=True)
            assert_ti_state_equal(ti, State.SUCCESS)

    return tis


def assert_ti_state_equal(task_instance, state):
    """
    Assert state of task_instances equals the given state.
    """
    task_instance.refresh_from_db()
    assert task_instance.state == state


def clear_tasks(dag_bag, dag, task, start_date=DEFAULT_DATE, end_date=DEFAULT_DATE):
    """
    Clear the task and its downstream tasks recursively for the dag in the given dagbag.
    """
    subdag = dag.sub_dag(task_regex="^{}$".format(task.task_id), include_downstream=True)
    subdag.clear(start_date=start_date, end_date=end_date, dag_bag=dag_bag)


# pylint: disable=redefined-outer-name
def test_external_task_marker_transitive(dag_bag_ext):
    """
    Test clearing tasks across DAGs.
    """
    tis = run_tasks(dag_bag_ext)
    dag_0 = dag_bag_ext.get_dag("dag_0")
    task_a_0 = dag_0.get_task("task_a_0")
    clear_tasks(dag_bag_ext, dag_0, task_a_0)
    ti_a_0 = tis["task_a_0"]
    ti_b_3 = tis["task_b_3"]
    assert_ti_state_equal(ti_a_0, State.NONE)
    assert_ti_state_equal(ti_b_3, State.NONE)


def test_external_task_marker_future(dag_bag_ext):
    """
    Test clearing tasks with no end_date. This is the case when users clear tasks with
    Future, Downstream and Recursive selected.
    """
    date_0 = DEFAULT_DATE
    date_1 = DEFAULT_DATE + timedelta(days=1)

    tis_date_0 = run_tasks(dag_bag_ext, execution_date=date_0)
    tis_date_1 = run_tasks(dag_bag_ext, execution_date=date_1)

    dag_0 = dag_bag_ext.get_dag("dag_0")
    task_a_0 = dag_0.get_task("task_a_0")
    # This should clear all tasks on dag_0 to dag_3 on both date_0 and date_1
    clear_tasks(dag_bag_ext, dag_0, task_a_0, end_date=None)

    ti_a_0_date_0 = tis_date_0["task_a_0"]
    ti_b_3_date_0 = tis_date_0["task_b_3"]
    ti_b_3_date_1 = tis_date_1["task_b_3"]
    assert_ti_state_equal(ti_a_0_date_0, State.NONE)
    assert_ti_state_equal(ti_b_3_date_0, State.NONE)
    assert_ti_state_equal(ti_b_3_date_1, State.NONE)


def test_external_task_marker_exception(dag_bag_ext):
    """
    Clearing across multiple DAGs should raise AirflowException if more levels are being cleared
    than allowed by the recursion_depth of the first ExternalTaskMarker being cleared.
    """
    run_tasks(dag_bag_ext)
    dag_0 = dag_bag_ext.get_dag("dag_0")
    task_a_0 = dag_0.get_task("task_a_0")
    task_b_0 = dag_0.get_task("task_b_0")
    task_b_0.recursion_depth = 2
    with pytest.raises(AirflowException, match="Maximum recursion depth 2"):
        clear_tasks(dag_bag_ext, dag_0, task_a_0)


@pytest.fixture
def dag_bag_cyclic():
    """
    Create a DagBag with DAGs having cyclic dependenceis set up by ExternalTaskMarker and
    ExternalTaskSensor.

    dag_0:   task_a_0 >> task_b_0
                  ^          |
                  |          |
    dag_1:        |          ---> task_a_1 >> task_b_1
                  |                               |
                  ---------------------------------

    """
    dag_bag = DagBag(dag_folder=DEV_NULL, include_examples=False)

    dag_0 = DAG("dag_0", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_0 = DummyOperator(task_id="task_a_0", dag=dag_0)
    task_b_0 = ExternalTaskMarker(task_id="task_b_0",
                                  external_dag_id="dag_1",
                                  external_task_id="task_a_1",
                                  recursion_depth=3,
                                  dag=dag_0)
    task_a_0 >> task_b_0

    dag_1 = DAG("dag_1", start_date=DEFAULT_DATE, schedule_interval=None)
    task_a_1 = ExternalTaskSensor(task_id="task_a_1",
                                  external_dag_id=dag_0.dag_id,
                                  external_task_id=task_b_0.task_id,
                                  dag=dag_1,
                                  mode="reschedule")
    task_b_1 = ExternalTaskMarker(task_id="task_b_1",
                                  external_dag_id="dag_0",
                                  external_task_id="task_a_0",
                                  recursion_depth=2,
                                  dag=dag_1)
    task_a_1 >> task_b_1

    for dag in [dag_0, dag_1]:
        dag_bag.bag_dag(dag, None, dag)

    return dag_bag


def test_external_task_marker_cyclic(dag_bag_cyclic):
    """
    Tests clearing across multiple DAGs that have cyclic dependencies. AirflowException should be
    raised.
    """
    run_tasks(dag_bag_cyclic)
    dag_0 = dag_bag_cyclic.get_dag("dag_0")
    task_a_0 = dag_0.get_task("task_a_0")
    with pytest.raises(AirflowException, match="Maximum recursion depth 3"):
        clear_tasks(dag_bag_cyclic, dag_0, task_a_0)


@pytest.fixture
def dag_bag_multiple():
    """
    Create a DagBag containing two DAGs, linked by multiple ExternalTaskMarker.
    """
    dag_bag = DagBag(dag_folder=DEV_NULL, include_examples=False)
    daily_dag = DAG("daily_dag", start_date=DEFAULT_DATE, schedule_interval="@daily")
    agg_dag = DAG("agg_dag", start_date=DEFAULT_DATE, schedule_interval="@daily")
    dag_bag.bag_dag(daily_dag, None, daily_dag)
    dag_bag.bag_dag(agg_dag, None, agg_dag)

    daily_task = DummyOperator(task_id="daily_tas", dag=daily_dag)

    start = DummyOperator(task_id="start", dag=agg_dag)
    for i in range(25):
        task = ExternalTaskMarker(task_id="{}_{}".format(daily_task.task_id, i),
                                  external_dag_id=daily_dag.dag_id,
                                  external_task_id=daily_task.task_id,
                                  execution_date="{{ macros.ds_add(ds, -1 * %s) }}" % i,
                                  dag=agg_dag)
        start >> task

    yield dag_bag


@pytest.mark.quarantined
@pytest.mark.backend("postgres", "mysql")
def test_clear_multiple_external_task_marker(dag_bag_multiple):
    """
    Test clearing a dag that has multiple ExternalTaskMarker.

    sqlite3 parser stack size is 100 lexical items by default so this puts a hard limit on
    the level of nesting in the sql. This test is intentionally skipped in sqlite.
    """
    agg_dag = dag_bag_multiple.get_dag("agg_dag")

    for delta in range(len(agg_dag.tasks)):
        execution_date = DEFAULT_DATE + timedelta(days=delta)
        run_tasks(dag_bag_multiple, execution_date=execution_date)

    # There used to be some slowness caused by calling count() inside DAG.clear().
    # That has since been fixed. It should take no more than a few seconds to call
    # dag.clear() here.
    assert agg_dag.clear(start_date=execution_date, end_date=execution_date, dag_bag=dag_bag_multiple) == 51
