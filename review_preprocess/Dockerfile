# 베이스 이미지 선택 (Python 3.9 사용)
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -qU click boto3 pyarrow pandas sentence-transformers faiss-cpu langchain langchain-community langchain-google-genai torch torchvision torchaudio numpy==1.26.0 openai
# 소스 코드 복사
COPY ./preprocess.py /app/preprocess.py

ENTRYPOINT ["python", "/app/preprocess.py"]
