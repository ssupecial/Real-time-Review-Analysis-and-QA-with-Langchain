import datetime as dt
import os

from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.dummy import DummyOperator

from s3_sensor import S3NewFileSensor

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')


# DAG 정의
with DAG(
    dag_id='preprocess_reviews',
    start_date=days_ago(1),
    schedule_interval=dt.timedelta(minutes=1),
    catchup=False,
    max_active_runs=1,
) as dag:
    # S3NewFileSensor 인스턴스 생성
    s3_sensor = S3NewFileSensor(
        task_id='s3_sensor',
        bucket_name=S3_BUCKET_NAME,
        prefix='reviews/',
        poke_interval=60,
    )

    # s3_sensor 이후 실행될 태스크 정의
    preprocess_reviews = DummyOperator(task_id='preprocess_reviews')

    # Task 간 의존성 설정
    s3_sensor >> preprocess_reviews