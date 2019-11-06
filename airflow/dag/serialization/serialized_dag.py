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

"""DAG serialization with JSON."""

import json

from airflow.dag.serialization.enums import DagAttributeTypes as DAT, Encoding
from airflow.dag.serialization.json_schema import load_dag_schema
from airflow.dag.serialization.serialization import Serialization, safe_str
from airflow.models import DAG


class SerializedDAG(DAG, Serialization):
    """A JSON serializable representation of DAG.

    A stringified DAG can only be used in the scope of scheduler and webserver, because fields
    that are not serializable, such as functions and customer defined classes, are casted to
    strings.

    Compared with SimpleDAG: SerializedDAG contains all information for webserver.
    Compared with DagPickle: DagPickle contains all information for worker, but some DAGs are
    not pickable. SerializedDAG works for all DAGs.
    """
    # Stringified DAGs and operators contain exactly these fields.
    # FIXME: to customize included fields and keep only necessary fields.
    _included_fields = list(set(vars(DAG(dag_id='test')).keys()) - {
        '_comps', 'parent_dag', '_old_context_manager_dags', 'safe_dag_id', 'last_loaded',
        '_full_filepath', 'user_defined_filters', 'user_defined_macros', '_schedule_interval',
        'partial', 'default_view', '_pickle_id', 'template_searchpath', 'sla_miss_callback',
        'on_success_callback', 'on_failure_callback'})

    _json_schema = load_dag_schema()

    @classmethod
    def serialize_dag(cls, dag):
        """Serializes a DAG into a JSON object."""
        return cls._serialize_object(dag)

    @classmethod
    def deserialize_dag(cls, encoded_dag):
        """Deserializes a DAG from a JSON object."""
        dag = SerializedDAG(dag_id=encoded_dag['_dag_id'])
        cls._deserialize_object(encoded_dag, dag)
        setattr(dag, 'full_filepath', dag.fileloc)

        for task in dag.task_dict.values():
            task.dag = dag
            if task.subdag is not None:
                setattr(task.subdag, 'parent_dag', dag)
            if task.start_date is None:
                task.start_date = dag.start_date
        return dag

    @classmethod
    def to_json(cls, var):
        """Stringifies DAGs and operators contained by var and returns a JSON string of var."""
        json_str = json.dumps(cls._serialize(var), ensure_ascii=True)

        # ToDo: Verify if adding Schema Validation is the best approach or not
        # Validate Serialized DAG with Json Schema. Raises Error if it mismatches
        cls.validate_schema(json_str)
        return json_str

    @classmethod
    def to_dict(cls, var):
        """Stringifies DAGs and operators contained by var and returns a dict of var."""
        json_dict = cls._serialize(var)

        # Validate Serialized DAG with Json Schema. Raises Error if it mismatches
        cls.validate_schema(json_dict)
        return json_dict
