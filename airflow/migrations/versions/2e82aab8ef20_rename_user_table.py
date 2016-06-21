# -*- coding: utf-8 -*-
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

"""rename user table

Revision ID: 2e82aab8ef20
Revises: 1968acfc09e3
Create Date: 2016-04-02 19:28:15.211915

"""

# revision identifiers, used by Alembic.
revision = '2e82aab8ef20'
down_revision = '1968acfc09e3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.rename_table('user', 'users')


def downgrade():
    op.rename_table('users', 'user')

