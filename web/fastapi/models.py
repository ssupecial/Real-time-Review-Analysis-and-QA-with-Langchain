from pydantic import BaseModel
from typing import List, Dict

class Review(BaseModel):
    review_text: str
    score: str
    date: str
    review_sentiment: int
    similarity_score: float

class Metadata(BaseModel):
    name: str
    count: str
    score_distribution: Dict[str, str]  # 점수 분포
    keyword_distribution: Dict[str, Dict[str, str]]  # 키워드 분포

class QueryRequest(BaseModel):
    product_id: int
    question: str

class QueryResponse(BaseModel):
    product_id: int
    question: str
    similar_reviews: List[Review]
    generated_answer: str
    metadata: Metadata