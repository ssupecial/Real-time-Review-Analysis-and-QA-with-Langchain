from fastapi import FastAPI
from pydantic import BaseModel
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import boto3
import os
import logging
import tempfile
from pathlib import Path
from typing import List
from openai import OpenAI

# S3 버킷 이름
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
# S3 Client 생성
s3 = boto3.client("s3")

# OpenAI API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# HuggingFace 모델 불러오기
hf = HuggingFaceEmbeddings(model_name="jhgan/ko-sroberta-multitask")

app = FastAPI()

class Review(BaseModel):
    review_text: str
    score: str
    date: str
    review_sentiment: int
    similarity_score: float

class QueryRequest(BaseModel):
    product_id: int
    question: str

class QueryResponse(BaseModel):
    product_id: int
    question: str
    similar_reviews: List[Review]
    generated_answer: str

@app.post("/ask")
def get_answer(request: QueryRequest):
    product_id = request.product_id
    question = request.question

    similar_reviews = get_similar_reviews(product_id, question)
    if similar_reviews:
        generated_answer = generate_answer(question, similar_reviews)
        return QueryResponse(
            product_id=product_id,
            question=question,
            similar_reviews=similar_reviews,
            generated_answer=generated_answer
        )

    return QueryResponse(
        product_id=product_id,
        question=question,
        similar_reviews=similar_reviews,
        generated_answer="유사한 리뷰를 찾을 수 없습니다."
    )

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
                "content": "다음 리뷰들을 바탕으로 사용자 질문에 대해 적절한 답변을 작성하세요."
                f"질문: {question}"
                f"리뷰들: {reviews_text}"

            },
        ],
        max_tokens=150,
    )

    return response.choices[0].message.content.strip()