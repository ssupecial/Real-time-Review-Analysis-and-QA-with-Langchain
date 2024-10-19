# Base image (Airflow)
FROM apache/airflow:2.10.2

# Set build arguments for UID and GID (use default 50000 if not provided)
ARG AIRFLOW_UID

# Set environment variables (if needed)
ENV AIRFLOW_HOME=/opt/airflow

USER root

# Modify airflow user and group to match the provided UID and GID
RUN usermod -u $AIRFLOW_UID -g 0 airflow

# Create required directories with appropriate permissions
RUN mkdir -p /opt/airflow/logs /opt/airflow/dags /opt/airflow/config /opt/airflow/plugins && \
    chown -R airflow: /opt/airflow/logs /opt/airflow/dags /opt/airflow/config /opt/airflow/plugins

# Set user to airflow (with modified UID and GID)
USER airflow
