# 베이스 이미지를 설정 (Python 3.9 사용)
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 파일 복사
COPY requirements.txt .

# 필요한 Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 애플리케이션 실행 명령어
CMD ["python", "app.py"]
