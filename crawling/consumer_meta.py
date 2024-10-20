from kafka import KafkaConsumer
import json
import pandas as pd
from datetime import datetime
import os
import pyarrow.parquet as pq
import pyarrow as pa
import logging
import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# DynamoDB 클라이언트 생성
dynamodb = boto3.resource('dynamodb')
# DynamoDB 테이블 이름
table_name = os.getenv("DYNAMODB_TABLE_NAME", "Oliveyoung_Meta")
table = dynamodb.Table(table_name)


# Kafka Consumer 설정
consumer = KafkaConsumer(
    'oliveyoung_meta',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='meta-consumer',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Kafka 메시지를 처리하는 함수
def process_message(message):
    meta_data = {
        "index": message.value["product_index"],
        "count": message.value["count"],
        "eval": message.value["eval"],
        "keywords": message.value["keywords"],
        "name": message.value["name"],
        "ratio": message.value["ratio"],
        "ratio_cate": message.value["ratio_cate"],
        "review_page": int(message.value["review_page"]),
    }
    # DynamoDB에 데이터 삽입
    try:
        table.put_item(Item=meta_data)
        logging.info(f"Put item to DynamoDB - {meta_data}")
    except Exception as e:
        logging.error(f"Failed to put item to DynamoDB, error: {e}")

for message in consumer:
    process_message(message)

