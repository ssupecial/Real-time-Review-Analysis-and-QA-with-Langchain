from fastapi import FastAPI
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import boto3
import os
import logging
import tempfile
from pathlib import Path
from typing import List
import json
from openai import OpenAI
from boto3.dynamodb.conditions import Key
from models import Review, Metadata, QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

'''AWS'''
# S3 버킷 이름
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# S3 Client 생성
s3 = boto3.client("s3")
# DynamoDB 테이블 이름
DYANMODB_TABLE_NAME = os.getenv("DYANMODB_TABLE_NAME")
# DynamoDB Client 생성
dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
# DynamoDB 테이블 객체 가져오기
table = dynamodb.Table(DYANMODB_TABLE_NAME)

# OpenAI API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# HuggingFace 모델 불러오기
hf = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

app = FastAPI()

@app.post("/ask")
def get_answer(request: QueryRequest):
    product_id = request.product_id
    question = request.question

    # 상품 메타데이터 조회
    product_metadata = query_table(product_id)
    # 상품 메타데이터가 없는 경우
    if not product_metadata:
        return QueryResponse(
            product_id=product_id,
            question=question,
            similar_reviews=[],
            generated_answer="상품 메타데이터를 찾을 수 없습니다.",
            metadata=None
        )
    
    product_metadata = process_metadata(product_metadata[0])

    # 질문에 대한 유사한 리뷰 탐색 및 답변을 생성
    similar_reviews = get_similar_reviews(product_id, question)
    if similar_reviews:
        generated_answer = generate_answer(question, similar_reviews)
        return QueryResponse(
            product_id=product_id,
            question=question,
            similar_reviews=similar_reviews,
            generated_answer=generated_answer,
            metadata=product_metadata
        )

    return QueryResponse(
        product_id=product_id,
        question=question,
        similar_reviews=similar_reviews,
        generated_answer="유사한 리뷰를 찾을 수 없습니다.",
        metadata=product_metadata
    )

# 유사한 리뷰 찾기 함수
def get_similar_reviews(product_id: int, question: str):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            faiss_path = Path(tmpdir) / "index.faiss"
            s3.download_file(S3_BUCKET_NAME, f"{product_id}/index.faiss", str(faiss_path))

            pkl_path = Path(tmpdir, "index.pkl")
            s3.download_file(S3_BUCKET_NAME, f"{product_id}/index.pkl", str(pkl_path))

            # FAISS 인덱스 로드
            vectorstore = FAISS.load_local(
                tmpdir, hf, allow_dangerous_deserialization=True
            )

            # 질문에 대한 답변을 찾기 위해 가장 유사한 리뷰를 찾음
            search_results = vectorstore.similarity_search_with_score(question, k=10)
            
            # 리뷰와 메타데이터 변환
            similar_reviews = []
            for result, score in search_results:
                metadata = result.metadata                
                review = Review(
                    review_text=result.page_content,
                    score=metadata["score"],
                    date=metadata["date"],
                    review_sentiment=metadata["review_sentiment"],
                    similarity_score=score
                )
                similar_reviews.append(review)
                
            return similar_reviews
        
        except Exception as e:
            logging.error(f"FAISS 인덱스를 로드하는 중 오류가 발생했습니다: {e}")
            return

# 유사한 리뷰를 기반으로 OpenAI API를 사용하여 답변 생성
def generate_answer(question: str, similar_reviews: List[Review]):
    reviews_text = "\n".join([f"{review.review_text} (Score: {review.score}, Date: {review.date}, Sentiment: {review.review_sentiment})" for review in similar_reviews])
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "당신은 올리브영 기본 스킨케어 제품에 대한 리뷰를 통해 사용자의 질문에 대한 답변을 하는 챗봇입니다.",
            },
            {
                "role": "user",
                "content": "다음 리뷰들을 바탕으로 사용자 질문에 대해 3~4줄의 적절한 답변을 작성하세요."
                f"질문: {question}"
                f"리뷰들: {reviews_text}"

            },
        ],
        max_tokens=200,
    )

    return response.choices[0].message.content.strip()

# DynamoDB 테이블 조회 함수 (메타데이터 조회)
def query_table(key_value: int):
    try:
        response = table.query(
            KeyConditionExpression=Key('index').eq(key_value)
        )
        return response['Items']  # 조건에 맞는 항목 반환
    except Exception as e:
        logging.error(f"데이터 조회 중 오류 발생: {e}")
        return None

# 상품 메타데이터 처리 
def process_metadata(metadata: dict):
    ratio_arr = metadata['ratio'].split('\n')
    score_distribution = {}
    for i in range(0, len(ratio_arr), 2):
        score_distribution[ratio_arr[i+1]] = ratio_arr[i]

    keyword_arr = metadata['ratio_cate'].split('\n')
    keyword_distribution = {"피부타입": {}, "피부고민": {}, "자극도": {}}
    keyword_distribution["피부타입"] = {
        keyword_arr[1]: keyword_arr[2],
        keyword_arr[3]: keyword_arr[4],
        keyword_arr[5]: keyword_arr[6],
    }
    keyword_distribution["피부고민"] = {
        keyword_arr[8]: keyword_arr[9],
        keyword_arr[10]: keyword_arr[11],
        keyword_arr[12]: keyword_arr[13],
    }
    keyword_distribution["자극도"] = {
        keyword_arr[15]: keyword_arr[16],
        keyword_arr[17]: keyword_arr[18],
        keyword_arr[19]: keyword_arr[20],
    }

    product_metadata = Metadata(
        name=metadata['name'],
        count=metadata['count'],
        score_distribution=score_distribution,
        keyword_distribution=keyword_distribution
    )
    return product_metadata