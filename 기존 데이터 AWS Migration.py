# Upload parquet file to S3 Bucket
import boto3
import os
import logging
import warnings ; warnings.filterwarnings(action='ignore')
import pandas as pd
import glob

def upload_to_s3():
    # S3 버킷 이름
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

    review_dir = './data/reviews'
    review_files = glob.glob(f"{review_dir}/*.parquet")
    for review_file in review_files:
        # S3에 업로드할 파일 이름
        s3_file_name = "reviews/" + os.path.basename(review_file)
        # S3에 업로드
        s3 = boto3.client('s3')
        s3.upload_file(review_file, S3_BUCKET_NAME, s3_file_name)
        logging.info(f"Upload file to S3 - {s3_file_name}")

def upload_to_dynamodb():
    # DynamoDB 클라이언트 생성
    dynamodb = boto3.resource('dynamodb')
    # DynamoDB 테이블 이름
    table_name = os.getenv("DYNAMODB_TABLE_NAME", "Oliveyoung_Meta")
    table = dynamodb.Table(table_name)

    df_meta = pd.read_parquet('./data/meta/meta.parquet')
    df_meta["review_page"] = df_meta.apply(lambda x: x["review_num"] if x["review_page"] is None else x["review_page"], axis=1)
    df_meta = df_meta.drop(columns=["review_num"])
    df_meta["review_page"].fillna(100, inplace=True)
    df_meta["review_page"] = df_meta["review_page"].astype(int)

    df_meta.rename(columns={"product_index": "index"}, inplace=True)
    for _, row in df_meta.iterrows():
        meta_data = row.to_dict()
        print(meta_data)
        # DynamoDB에 데이터 삽입
        try:
            table.put_item(Item=meta_data)
            logging.info(f"Put item to DynamoDB - {meta_data}")
        except Exception as e:
            logging.error(f"Failed to put item to DynamoDB, error: {e}")

if __name__ == "__main__":
    upload_to_dynamodb()