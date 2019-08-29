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

"""
Example Airflow DAG that uses Google AutoML services.
"""
import os

import airflow
from airflow import models
from airflow.gcp.hooks.automl import CloudAutoMLHook
from airflow.gcp.operators.automl import (
    AutoMLCreateDatasetOperator, AutoMLDeleteDatasetOperator, AutoMLDeleteModelOperator,
    AutoMLImportDataOperator, AutoMLTrainModelOperator,
)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")
GCP_AUTOML_LOCATION = os.environ.get("GCP_AUTOML_LOCATION", "us-central1")
GCP_AUTOML_TEXT_BUCKET = os.environ.get(
    "GCP_AUTOML_TEXT_BUCKET", "gs://cloud-ml-data/NL-entity/dataset.csv"
)

# Example values
DATASET_ID = ""

# Example model
MODEL = {
    "display_name": "auto_model_1",
    "dataset_id": DATASET_ID,
    "text_extraction_model_metadata": {},
}

# Example dataset
DATASET = {"display_name": "test_text_dataset", "text_extraction_dataset_metadata": {}}

IMPORT_INPUT_CONFIG = {"gcs_source": {"input_uris": [GCP_AUTOML_TEXT_BUCKET]}}

default_args = {"start_date": airflow.utils.dates.days_ago(1)}
extract_object_id = CloudAutoMLHook.extract_object_id

# Example DAG for AutoML Natural Language Entities Extraction
with models.DAG(
    "example_automl_text",
    default_args=default_args,
    schedule_interval=None,  # Override to match your needs
    user_defined_macros={"extract_object_id": extract_object_id},
) as example_dag:
    create_dataset_task = AutoMLCreateDatasetOperator(
        task_id="create_dataset_task", dataset=DATASET, location=GCP_AUTOML_LOCATION
    )

    dataset_id = (
        '{{ task_instance.xcom_pull("create_dataset_task", key="dataset_id") }}'
    )

    import_dataset_task = AutoMLImportDataOperator(
        task_id="import_dataset_task",
        dataset_id=dataset_id,
        location=GCP_AUTOML_LOCATION,
        input_config=IMPORT_INPUT_CONFIG,
    )

    MODEL["dataset_id"] = dataset_id

    create_model = AutoMLTrainModelOperator(
        task_id="create_model", model=MODEL, location=GCP_AUTOML_LOCATION
    )

    model_id = "{{ task_instance.xcom_pull('create_model', key='model_id') }}"

    delete_model_task = AutoMLDeleteModelOperator(
        task_id="delete_model_task",
        model_id=model_id,
        location=GCP_AUTOML_LOCATION,
        project_id=GCP_PROJECT_ID,
    )

    delete_datasets_task = AutoMLDeleteDatasetOperator(
        task_id="delete_datasets_task",
        dataset_id=dataset_id,
        location=GCP_AUTOML_LOCATION,
        project_id=GCP_PROJECT_ID,
    )

    create_dataset_task >> import_dataset_task >> create_model >> \
        delete_model_task >> delete_datasets_task
