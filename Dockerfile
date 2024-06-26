# 베이스 이미지 설정
FROM python:3.8-slim

# 작업 디렉터리 설정
WORKDIR /app

# 필요 파일 복사
COPY requirements.txt requirements.txt
COPY app app

# 필요한 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# FastAPI 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]