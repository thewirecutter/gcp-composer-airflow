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

import re
from contextlib import contextmanager

from sqlalchemy import event

from airflow.settings import engine


def assert_equal_ignore_multiple_spaces(case, first, second, msg=None):
    def _trim(s):
        return re.sub(r"\s+", " ", s.strip())
    return case.assertEqual(_trim(first), _trim(second), msg)


class CountQueriesResult:
    def __init__(self):
        self.count = 0


class CountQueries:
    """
    Counts the number of queries sent to Airflow Database in a given context.

    Does not support multiple processes. When a new process is started in context, its queries will
    not be included.
    """
    def __init__(self):
        self.result = CountQueriesResult()

    def __enter__(self):
        event.listen(engine, "after_cursor_execute", self.after_cursor_execute)
        return self.result

    def __exit__(self, type_, value, traceback):
        event.remove(engine, "after_cursor_execute", self.after_cursor_execute)

    def after_cursor_execute(self, *args, **kwargs):
        self.result.count += 1


count_queries = CountQueries  # pylint: disable=invalid-name


@contextmanager
def assert_queries_count(expected_count, message_fmt=None):
    with count_queries() as result:
        yield None
    message_fmt = message_fmt or "The expected number of db queries is {expected_count}. " \
                                 "The current number is {current_count}."
    message = message_fmt.format(current_count=result.count, expected_count=expected_count)
    assert expected_count == result.count, message
