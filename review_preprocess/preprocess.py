#! /usr/bin/env python
import os
import boto3
import pandas as pd
import click
import logging
from pathlib import Path
import tempfile
from openai import OpenAI
import pandas as pd
import os
import io

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

logging.basicConfig(
    format="[%(asctime)-15s] %(levelname)s - %(message)s", level=logging.INFO
)

# S3 버킷 이름
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# S3 Client 생성
s3 = boto3.client("s3")

# HuggingFace 모델 불러오기
hf = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

# OpenAI API 키 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@click.command()
@click.option("--review_index", type=int, required=True)
@click.option("--is_sentiment", type=bool, default=False, help="리뷰 감정 분석을 수행할지 여부(OpenAI API 과금)")
def main(review_index, is_sentiment):
    # S3에서 파일을 메모리로 가져오기
    response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=f"reviews/product_{review_index}.parquet")
    logging.info(f"{review_index} 리뷰 데이터를 메모리로 다운로드 완료")

    # 메모리 상에서 데이터를 파싱하여 DataFrame으로 변환
    file_stream = io.BytesIO(response['Body'].read())
    df = pd.read_parquet(file_stream)

    if is_sentiment:
        df["review_sentiment"] = calculate_positivie_score(df.review_text)
        logging.info(f"{review_index} 리뷰 감정 분석 완료")

    save_as_vectorstore(
        df.review_text.values, df.to_dict(orient="records"), review_index
    )


def calculate_positivie_score(reviews):
    """각 리뷰에 대해 상품에 대한 긍정/부정 점수를 계산하는 함수"""
    scores = [sentiment_analysis(review) for review in reviews]
    return scores


def sentiment_analysis(review):
    """review 텍스트를 받아서 OpenAI API를 통해 상품에 대한 긍정/부정 점수를 도출하는 함수"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that classifies reviews of Olive Young basic skincare products "
                "as either positive or negative. "
                "Return only '1' for positive sentiment or '0' for negative sentiment. "
                "Do not include any other text in your response.",
            },
            {
                "role": "user",
                "content": f"Classify the sentiment of this review as '1' for positive or '0' for negative: {review}",
            },
        ],
        max_tokens=1,
    )

    # 감정 분석 결과 반환
    try:
        result = int(response.choices[0].message.content)
    except Exception as e:
        result = 0.5
    return result


def save_as_vectorstore(texts, metadatas, review_index):
    """
    리뷰 텍스트와 메타데이터를 받아서
    vector store로 임베딩한 후
    S3 버킷에 저장
    """
    vectorstore = FAISS.from_texts(texts, embedding=hf, metadatas=metadatas)
    logging.info(f"{review_index} 리뷰 벡터스토어로 변환 완료")

    s3 = boto3.client("s3")
    with tempfile.TemporaryDirectory() as tmpdir:
        vectorstore.save_local(folder_path=tmpdir)

        s3.upload_file(
            Filename=tmpdir + "/" + "index.faiss",
            Bucket=S3_BUCKET_NAME,
            Key=f"{review_index}/index.faiss",
        )
        s3.upload_file(
            Filename=tmpdir + "/" + "index.pkl",
            Bucket=S3_BUCKET_NAME,
            Key=f"{review_index}/index.pkl",
        )
        logging.info(f"{review_index} 리뷰 벡터스토어 S3에 업로드 완료")


if __name__ == "__main__":
    main()
