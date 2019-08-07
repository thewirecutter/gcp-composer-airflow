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
This module contains various GCP Cloud Tasks operators
which allow you to perform basic operations using
Cloud Tasks queues/tasks.
"""

from airflow.contrib.hooks.gcp_tasks_hook import CloudTasksHook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class CloudTasksQueueCreateOperator(BaseOperator):
    """
    Creates a queue in Cloud Tasks.

    :param location: The location name in which the queue will be created.
    :type location: str
    :param task_queue: The task queue to create.
        Queue's name cannot be the same as an existing queue.
        If a dict is provided, it must be of the same form as the protobuf message Queue.
    :type task_queue: dict or class google.cloud.tasks_v2.types.Queue
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param queue_name: (Optional) The queue's name.
        If provided, it will be used to construct the full queue path.
    :type queue_name: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Queue
    """

    template_fields = (
        "task_queue",
        "project_id",
        "location",
        "queue_name",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        location,
        task_queue,
        project_id=None,
        queue_name=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.task_queue = task_queue
        self.project_id = project_id
        self.queue_name = queue_name
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.create_queue(
            location=self.location,
            task_queue=self.task_queue,
            project_id=self.project_id,
            queue_name=self.queue_name,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueueUpdateOperator(BaseOperator):
    """
    Updates a queue in Cloud Tasks.

    :param task_queue: The task queue to update.
        This method creates the queue if it does not exist and updates the queue if
        it does exist. The queue's name must be specified.
    :type task_queue: dict or class google.cloud.tasks_v2.types.Queue
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param location: (Optional) The location name in which the queue will be updated.
        If provided, it will be used to construct the full queue path.
    :type location: str
    :param queue_name: (Optional) The queue's name.
        If provided, it will be used to construct the full queue path.
    :type queue_name: str
    :param update_mask: A mast used to specify which fields of the queue are being updated.
        If empty, then all fields will be updated.
        If a dict is provided, it must be of the same form as the protobuf message.
    :type update_mask: dict or class google.cloud.tasks_v2.types.FieldMask
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Queue
    """

    template_fields = (
        "task_queue",
        "project_id",
        "location",
        "queue_name",
        "update_mask",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        task_queue,
        project_id=None,
        location=None,
        queue_name=None,
        update_mask=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.task_queue = task_queue
        self.project_id = project_id
        self.location = location
        self.queue_name = queue_name
        self.update_mask = update_mask
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.update_queue(
            task_queue=self.task_queue,
            project_id=self.project_id,
            location=self.location,
            queue_name=self.queue_name,
            update_mask=self.update_mask,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueueGetOperator(BaseOperator):
    """
    Gets a queue from Cloud Tasks.

    :param location: The location name in which the queue was created.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Queue
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.get_queue(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueuesListOperator(BaseOperator):

    """
    Lists queues from Cloud Tasks.

    :param location: The location name in which the queues were created.
    :type location: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param results_filter: (Optional) Filter used to specify a subset of queues.
    :type results_filter: str
    :param page_size: (Optional) The maximum number of resources contained in the
        underlying API response.
    :type page_size: int
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: list[google.cloud.tasks_v2.types.Queue]
    """

    template_fields = ("location", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        project_id=None,
        results_filter=None,
        page_size=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.project_id = project_id
        self.results_filter = results_filter
        self.page_size = page_size
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.list_queues(
            location=self.location,
            project_id=self.project_id,
            results_filter=self.results_filter,
            page_size=self.page_size,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueueDeleteOperator(BaseOperator):
    """
    Deletes a queue from Cloud Tasks, even if it has tasks in it.

    :param location: The location name in which the queue will be deleted.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        hook.delete_queue(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueuePurgeOperator(BaseOperator):
    """
    Purges a queue by deleting all of its tasks from Cloud Tasks.

    :param location: The location name in which the queue will be purged.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: list[google.cloud.tasks_v2.types.Queue]
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.purge_queue(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueuePauseOperator(BaseOperator):
    """
    Pauses a queue in Cloud Tasks.

    :param location: The location name in which the queue will be paused.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: list[google.cloud.tasks_v2.types.Queue]
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.pause_queue(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksQueueResumeOperator(BaseOperator):
    """
    Resumes a queue in Cloud Tasks.

    :param location: The location name in which the queue will be resumed.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: list[google.cloud.tasks_v2.types.Queue]
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.resume_queue(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksTaskCreateOperator(BaseOperator):
    """
    Creates a task in Cloud Tasks.

    :param location: The location name in which the task will be created.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param task: The task to add.
        If a dict is provided, it must be of the same form as the protobuf message Task.
    :type task: dict or class google.cloud.tasks_v2.types.Task
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param task_name: (Optional) The task's name.
        If provided, it will be used to construct the full task path.
    :type task_name: str
    :param response_view: (Optional) This field specifies which subset of the Task will
        be returned.
    :type response_view: google.cloud.tasks_v2.types.Task.View
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Task
    """

    template_fields = (
        "task",
        "project_id",
        "location",
        "queue_name",
        "task_name",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        task,
        project_id=None,
        task_name=None,
        response_view=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):  # pylint: disable=too-many-arguments
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.task = task
        self.project_id = project_id
        self.task_name = task_name
        self.response_view = response_view
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.create_task(
            location=self.location,
            queue_name=self.queue_name,
            task=self.task,
            project_id=self.project_id,
            task_name=self.task_name,
            response_view=self.response_view,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksTaskGetOperator(BaseOperator):
    """
    Gets a task from Cloud Tasks.

    :param location: The location name in which the task was created.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param task_name: The task's name.
    :type task_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param response_view: (Optional) This field specifies which subset of the Task will
        be returned.
    :type response_view: google.cloud.tasks_v2.types.Task.View
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Task
    """

    template_fields = (
        "location",
        "queue_name",
        "task_name",
        "project_id",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        task_name,
        project_id=None,
        response_view=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.task_name = task_name
        self.project_id = project_id
        self.response_view = response_view
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.get_task(
            location=self.location,
            queue_name=self.queue_name,
            task_name=self.task_name,
            project_id=self.project_id,
            response_view=self.response_view,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksTasksListOperator(BaseOperator):
    """
    Lists the tasks in Cloud Tasks.

    :param location: The location name in which the tasks were created.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param response_view: (Optional) This field specifies which subset of the Task will
        be returned.
    :type response_view: google.cloud.tasks_v2.types.Task.View
    :param page_size: (Optional) The maximum number of resources contained in the
        underlying API response.
    :type page_size: int
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: list[google.cloud.tasks_v2.types.Task]
    """

    template_fields = ("location", "queue_name", "project_id", "gcp_conn_id")

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        project_id=None,
        response_view=None,
        page_size=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.project_id = project_id
        self.response_view = response_view
        self.page_size = page_size
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.list_tasks(
            location=self.location,
            queue_name=self.queue_name,
            project_id=self.project_id,
            response_view=self.response_view,
            page_size=self.page_size,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksTaskDeleteOperator(BaseOperator):
    """
    Deletes a task from Cloud Tasks.

    :param location: The location name in which the task will be deleted.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param task_name: The task's name.
    :type task_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    template_fields = (
        "location",
        "queue_name",
        "task_name",
        "project_id",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        task_name,
        project_id=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.task_name = task_name
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        hook.delete_task(
            location=self.location,
            queue_name=self.queue_name,
            task_name=self.task_name,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudTasksTaskRunOperator(BaseOperator):
    """
    Forces to run a task in Cloud Tasks.

    :param location: The location name in which the task was created.
    :type location: str
    :param queue_name: The queue's name.
    :type queue_name: str
    :param task_name: The task's name.
    :type task_name: str
    :param project_id: (Optional) The ID of the  GCP project that owns the Cloud Tasks.
        If set to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param response_view: (Optional) This field specifies which subset of the Task will
        be returned.
    :type response_view: google.cloud.tasks_v2.types.Task.View
    :param retry: (Optional) A retry object used to retry requests.
        If None is specified, requests will not be retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: (Optional) The amount of time, in seconds, to wait for the request
        to complete. Note that if retry is specified, the timeout applies to each
        individual attempt.
    :type timeout: float
    :param metadata: (Optional) Additional metadata that is provided to the method.
    :type metadata: sequence[tuple[str, str]]]
    :param gcp_conn_id: (Optional) The connection ID used to connect to Google Cloud Platform.
    :type gcp_conn_id: str
    :rtype: google.cloud.tasks_v2.types.Task
    """

    template_fields = (
        "location",
        "queue_name",
        "task_name",
        "project_id",
        "gcp_conn_id",
    )

    @apply_defaults
    def __init__(
        self,
        location,
        queue_name,
        task_name,
        project_id=None,
        response_view=None,
        retry=None,
        timeout=None,
        metadata=None,
        gcp_conn_id="google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.queue_name = queue_name
        self.task_name = task_name
        self.project_id = project_id
        self.response_view = response_view
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context):
        hook = CloudTasksHook(gcp_conn_id=self.gcp_conn_id)
        return hook.run_task(
            location=self.location,
            queue_name=self.queue_name,
            task_name=self.task_name,
            project_id=self.project_id,
            response_view=self.response_view,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
