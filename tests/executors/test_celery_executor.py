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
import subprocess
import sys
import unittest
from multiprocessing import Pool

import mock
from celery.contrib.testing.worker import start_worker

from airflow.exceptions import AirflowException
from airflow.executors import celery_executor
from airflow.executors.celery_executor import (CeleryExecutor, celery_configuration,
                                               send_task_to_executor, execute_command)
from airflow.executors.celery_executor import app
from celery import states as celery_states
from airflow.utils.state import State

from airflow.configuration import conf

# leave this it is used by the test worker
import celery.contrib.testing.tasks  # noqa: F401 pylint: disable=ungrouped-imports


class CeleryExecutorTest(unittest.TestCase):
    @unittest.skipIf('sqlite' in conf.get('core', 'sql_alchemy_conn'),
                     "sqlite is configured with SequentialExecutor")
    def test_celery_integration(self):
        executor = CeleryExecutor()
        executor.start()
        with start_worker(app=app, logfile=sys.stdout, loglevel='debug'):
            success_command = ['airflow', 'run', 'true', 'some_parameter']
            fail_command = ['airflow', 'version']

            cached_celery_backend = execute_command.backend
            task_tuples_to_send = [('success', 'fake_simple_ti', success_command,
                                    celery_configuration['task_default_queue'],
                                    execute_command),
                                   ('fail', 'fake_simple_ti', fail_command,
                                    celery_configuration['task_default_queue'],
                                    execute_command)]

            chunksize = executor._num_tasks_per_send_process(len(task_tuples_to_send))
            num_processes = min(len(task_tuples_to_send), executor._sync_parallelism)

            send_pool = Pool(processes=num_processes)
            key_and_async_results = send_pool.map(
                send_task_to_executor,
                task_tuples_to_send,
                chunksize=chunksize)

            send_pool.close()
            send_pool.join()

            for key, command, result in key_and_async_results:
                # Only pops when enqueued successfully, otherwise keep it
                # and expect scheduler loop to deal with it.
                result.backend = cached_celery_backend
                executor.running[key] = command
                executor.tasks[key] = result
                executor.last_state[key] = celery_states.PENDING

            executor.running['success'] = True
            executor.running['fail'] = True

            executor.end(synchronous=True)

        self.assertTrue(executor.event_buffer['success'], State.SUCCESS)
        self.assertTrue(executor.event_buffer['fail'], State.FAILED)

        self.assertNotIn('success', executor.tasks)
        self.assertNotIn('fail', executor.tasks)

        self.assertNotIn('success', executor.last_state)
        self.assertNotIn('fail', executor.last_state)

    @unittest.skipIf('sqlite' in conf.get('core', 'sql_alchemy_conn'),
                     "sqlite is configured with SequentialExecutor")
    def test_error_sending_task(self):
        @app.task
        def fake_execute_command():
            pass

        # fake_execute_command takes no arguments while execute_command takes 1,
        # which will cause TypeError when calling task.apply_async()
        celery_executor.execute_command = fake_execute_command
        executor = CeleryExecutor()
        value_tuple = 'command', '_', 'queue', 'should_be_a_simple_ti'
        executor.queued_tasks['key'] = value_tuple
        executor.heartbeat()
        self.assertEqual(1, len(executor.queued_tasks))
        self.assertEqual(executor.queued_tasks['key'], value_tuple)

    def test_exception_propagation(self):
        @app.task
        def fake_celery_task():
            return {}

        mock_log = mock.MagicMock()
        executor = CeleryExecutor()
        executor._log = mock_log

        executor.tasks = {'key': fake_celery_task()}
        executor.sync()
        assert mock_log.error.call_count == 1
        args, kwargs = mock_log.error.call_args_list[0]
        # Result of queuing is not a celery task but a dict,
        # and it should raise AttributeError and then get propagated
        # to the error log.
        self.assertIn(celery_executor.CELERY_FETCH_ERR_MSG_HEADER, args[0])
        self.assertIn('AttributeError', args[1])

    @mock.patch('airflow.executors.celery_executor.CeleryExecutor.sync')
    @mock.patch('airflow.executors.celery_executor.CeleryExecutor.trigger_tasks')
    @mock.patch('airflow.settings.Stats.gauge')
    def test_gauge_executor_metrics(self, mock_stats_gauge, mock_trigger_tasks, mock_sync):
        executor = celery_executor.CeleryExecutor()
        executor.heartbeat()
        calls = [mock.call('executor.open_slots', mock.ANY),
                 mock.call('executor.queued_tasks', mock.ANY),
                 mock.call('executor.running_tasks', mock.ANY)]
        mock_stats_gauge.assert_has_calls(calls)

    @mock.patch('subprocess.check_call')
    def test_command_validation_incorrect_1(self, mock_check_call):
        # Check that we validate _on the receiving_ side, not just sending side
        with self.assertRaises(ValueError):
            celery_executor.execute_command(['true'])
        mock_check_call.assert_not_called()

    @mock.patch('subprocess.check_call')
    def test_command_validation_incorrect_2(self, mock_check_call):
        # Check that we validate _on the receiving_ side, not just sending side
        with self.assertRaises(ValueError):
            celery_executor.execute_command(['airflow', 'version'])
        mock_check_call.assert_not_called()

    @mock.patch('subprocess.check_call')
    def test_command_validation_success(self, mock_check_call):
        command=['airflow', 'run'];
        celery_executor.execute_command(command)
        mock_check_call.assert_called_once_with(
            command, stderr=mock.ANY, close_fds=mock.ANY, env=mock.ANY,
        )

    @mock.patch('subprocess.check_call')
    def test_execute_command_success(self, mock_check_call):
        fake_command = ['airflow', 'run']
        celery_executor.execute_command(fake_command, num_attempts=3)
        # Subprocess call should only happen once if successful the first time.
        mock_check_call.assert_called_once_with(
            fake_command, stderr=subprocess.STDOUT, close_fds=True,
            env=mock.ANY)

    @mock.patch('subprocess.check_call')
    @mock.patch('time.sleep')
    def test_execute_command_eventual_success(self, mock_sleep, mock_check_call):
        fake_command = ['airflow', 'run']
        fake_return_code = 1
        mock_check_call.side_effect = [
            subprocess.CalledProcessError(fake_return_code, fake_command),
            None,
        ]
        celery_executor.execute_command(fake_command, num_attempts=3)
        call = mock.call(
            fake_command, stderr=subprocess.STDOUT, close_fds=True,
            env=mock.ANY)
        mock_check_call.assert_has_calls([call, call])
        self.assertEqual(mock_sleep.call_count, 1)

    @mock.patch('subprocess.check_call')
    def test_execute_command_fail(self, mock_check_call):
        fake_command = ['airflow', 'run']
        fake_return_code = 1
        mock_check_call.side_effect = subprocess.CalledProcessError(
            fake_return_code, fake_command)

        with self.assertRaises(AirflowException):
            celery_executor.execute_command(fake_command, num_attempts=1)
        mock_check_call.assert_called_once_with(
            fake_command, stderr=subprocess.STDOUT, close_fds=True,
            env=mock.ANY)

    @mock.patch('subprocess.check_call')
    @mock.patch('time.sleep')
    def test_execute_command_fail_with_retries(self, mock_sleep, mock_check_call):
        fake_command = ['airflow', 'run']
        fake_return_code = 1
        mock_check_call.side_effect = subprocess.CalledProcessError(
            fake_return_code, fake_command)

        with self.assertRaises(AirflowException):
            celery_executor.execute_command(fake_command, num_attempts=3)
        call = mock.call(
            fake_command, stderr=subprocess.STDOUT, close_fds=True,
            env=mock.ANY)
        mock_check_call.assert_has_calls([call, call, call])
        # The last attempt should not wait after failing.
        self.assertEqual(mock_sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()
