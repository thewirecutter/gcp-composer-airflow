import logging
import time

from airflow.executors.base_executor import BaseExecutor
from airflow.configuration import conf
from airflow.utils import State

import subprocess

from celery import Celery
from celery import states as celery_states

'''
To start the celery worker, run the command:
airflow worker
'''


class CeleryConfig(object):
    BROKER_URL = conf.get('celery', 'BROKER_URL')
    CELERY_RESULT_BACKEND = conf.get('celery', 'CELERY_RESULT_BACKEND')
    CELERY_ACCEPT_CONTENT = ['json', 'pickle']

app = Celery(
    conf.get('celery', 'CELERY_APP_NAME'),
    config_source=CeleryConfig)


@app.task
def execute_command(command):
    logging.info("Executing command in Celery " + command)
    rc = subprocess.Popen(command, shell=True).wait()
    if rc:
        logging.error(rc)
        raise Exception('Celery command failed')


class CeleryExecutor(BaseExecutor):

    def start(self):
        self.tasks = {}
        self.last_state = {}

    def execute_async(self, key, command):
        self.tasks[key] = execute_command.delay(command)
        self.last_state[key] = celery_states.PENDING

    def heartbeat(self):
        for key, async in self.tasks.items():
            if self.last_state[key] != async.state:
                if async.state == celery_states.SUCCESS:
                    self.change_state(key, State.SUCCESS)
                elif async.state == celery_states.FAILURE:
                    self.change_state(key, State.FAILED)
                self.last_state[key] = async.state

    def end(self):
        print('entering end')
        while any([
                async.state not in celery_states.READY_STATES
                for async in self.tasks.values()]):
            print str([async.state for async in self.tasks.values()])
            time.sleep(5)
