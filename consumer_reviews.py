from kafka import KafkaConsumer
import json
import pandas as pd
from datetime import datetime
import os
import pyarrow.parquet as pq
import pyarrow as pa
import logging
import boto3
import io

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Kafka Consumer 설정
consumer = KafkaConsumer(
    'oliveyoung_reviews',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='review-consumer-group-test1',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# S3 버킷 이름
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# S3 클라이언트 생성
s3 = boto3.client('s3')
# Parquet 파일을 로컬에 저장하지 않고 바로 S3에 업로드하는 함수
def upload_parquet_to_s3(df, product_index):
    # 메모리 내 파일 객체 생성
    buffer = io.BytesIO()
    
    # pandas DataFrame을 Parquet 포맷으로 변환하여 메모리에 저장
    table = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    
    # 메모리 포인터를 처음으로 돌림
    buffer.seek(0)
    
    # S3에 업로드할 파일 이름 설정
    s3_file_name = f"reviews/product_{product_index}.parquet"
    
    # S3에 파일 업로드
    s3.upload_fileobj(buffer, S3_BUCKET_NAME, s3_file_name)
    logging.info(f"Uploaded parquet file to S3 - {s3_file_name}")


# 상품별 데이터를 저장할 딕셔너리
product_reviews = {}

for message in consumer:
    review_data = message.value
    product_index = review_data['product_index']
    finish = review_data.get('finish', False)

    # 리뷰 데이터를 딕셔너리에 추가
    if product_index not in product_reviews:
        product_reviews[product_index] = []
    
    # 해당 상품 리뷰 수집이 끝났으면 Parquet 파일로 저장
    if finish:
        reviews_df = pd.DataFrame(product_reviews[product_index])

        # 로컬 파일로 저장하지 않고 S3에 바로 업로드
        upload_parquet_to_s3(reviews_df, product_index)

        # 저장 후 딕셔너리에서 제거
        del product_reviews[product_index]
        continue

    review_data.pop('finish', None)
    product_reviews[product_index].append(review_data)
    logging.info(f"Get data - {len(product_reviews[product_index])}")
