["/bin/bash", "-c", "/bin/sleep 30; /bin/mv {{params.source_location}}/{{ ti.xcom_pull('view_file') }} {{params.target_location}}; /bin/echo '{{params.target_location}}/{{ ti.xcom_pull('view_file') }}';"]
