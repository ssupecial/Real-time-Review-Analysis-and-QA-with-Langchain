import datetime as dt
import os

from airflow import DAG
from docker.types import Mount
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.python_operator import PythonOperator

from utils import S3NewFileSensor

S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')


# DAG 정의
with DAG(
    dag_id='preprocess_reviews',
    start_date=days_ago(1),
    schedule_interval=dt.timedelta(hours=2),
    catchup=False,
    max_active_runs=1,
) as dag:
    # S3NewFileSensor 인스턴스 생성
    s3_sensor = S3NewFileSensor(
        task_id='s3_sensor',
        bucket_name=S3_BUCKET_NAME,
        prefix='reviews/',
        poke_interval=60*2, # 2분 간격으로 체크
        timeout=60*60,      # 60분 타임아웃
    )

    # review를 전처리하는 DockerOperator 생성
    preprocess_reviews = DockerOperator(
        task_id='preprocess_reviews',
        image='review_preprocess:latest',
        command='--review_index {{ ti.xcom_pull(task_ids="s3_sensor", key="new_file_index") }} --is_sentiment True',
        auto_remove="force",
        network_mode='airflow',
        container_name='preprocess_reviews_{{ ti.xcom_pull(task_ids="s3_sensor", key="new_file_index") }}',
        environment={
            "S3_BUCKET_NAME": os.getenv("S3_BUCKET_NAME"),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")
        },
        mounts=[Mount(source=f"{os.getenv('HOME_PATH')}/.aws/credentials", target="/root/.aws/credentials", type="bind")],
    )

    def add_review_index(new_file_index, **kwargs):
        processed_list = Variable.get("s3_file_list", default_var=[], deserialize_json=True)
        processed_list.append(int(new_file_index))
        Variable.set("s3_file_list", processed_list, serialize_json=True)

    # 전처리 완료된 Review index Variable에 추가해주기
    add_review_index = PythonOperator(
        task_id='add_review_index',
        python_callable=add_review_index,
        op_args=['{{ ti.xcom_pull(task_ids="s3_sensor", key="new_file_index") }}'],
    )


    s3_sensor >> preprocess_reviews >> add_review_index