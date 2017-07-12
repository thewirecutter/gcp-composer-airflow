#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""add max tries column to task instance

Revision ID: cc1e65623dc7
Revises: 127d2bf2dfa7
Create Date: 2017-06-19 16:53:12.851141

"""

# revision identifiers, used by Alembic.
revision = 'cc1e65623dc7'
down_revision = '127d2bf2dfa7'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from airflow import settings
from airflow.models import DagBag, TaskInstance

BATCH_SIZE = 5000

def upgrade():
    op.add_column('task_instance', sa.Column('max_tries', sa.Integer,
        server_default="-1"))
    # Check if table task_instance exist before data migration. This check is
    # needed for database that does not create table until migration finishes.
    # Checking task_instance table exists prevent the error of querying
    # non-existing task_instance table.
    engine = settings.engine
    if engine.dialect.has_table(engine, 'task_instance'):
        # Get current session
        connection = op.get_bind()
        sessionmaker = sa.orm.sessionmaker()
        session = sessionmaker(bind=connection)
        dagbag = DagBag(settings.DAGS_FOLDER)
        query = session.query(sa.func.count(TaskInstance.max_tries)).filter(
            TaskInstance.max_tries == -1
        )
        # Separate db query in batch to prevent loading entire table
        # into memory and cause out of memory error.
        while query.scalar():
            tis = session.query(TaskInstance).filter(
                TaskInstance.max_tries == -1
            ).limit(BATCH_SIZE).all()
            for ti in tis:
                dag = dagbag.get_dag(ti.dag_id)
                if not dag or not dag.has_task(ti.task_id):
                    # task_instance table might not have the up-to-date
                    # information, i.e dag or task might be modified or
                    # deleted in dagbag but is reflected in task instance
                    # table. In this case we do not retry the task that can't
                    # be parsed.
                    ti.max_tries = ti.try_number
                else:
                    task = dag.get_task(ti.task_id)
                    ti.max_tries = task.retries
                session.merge(ti)
            session.commit()
        # Commit the current session.
        session.commit()


def downgrade():
    engine = settings.engine
    if engine.dialect.has_table(engine, 'task_instance'):
        connection = op.get_bind()
        sessionmaker = sa.orm.sessionmaker()
        session = sessionmaker(bind=connection)
        dagbag = DagBag(settings.DAGS_FOLDER)
        query = session.query(sa.func.count(TaskInstance.max_tries)).filter(
            TaskInstance.max_tries != -1
        )
        while query.scalar():
            tis = session.query(TaskInstance).filter(
                TaskInstance.max_tries != -1
            ).limit(BATCH_SIZE).all()
            for ti in tis:
                dag = dagbag.get_dag(ti.dag_id)
                if not dag or not dag.has_task(ti.task_id):
                    ti.try_number = 0
                else:
                    task = dag.get_task(ti.task_id)
                    # max_tries - try_number is number of times a task instance
                    # left to retry by itself. So the current try_number should be
                    # max number of self retry (task.retries) minus number of
                    # times left for task instance to try the task.
                    ti.try_number = max(0, task.retries - (ti.max_tries -
                        ti.try_number))
                ti.max_tries = -1
                session.merge(ti)
            session.commit()
        session.commit()
    op.drop_column('task_instance', 'max_tries')
