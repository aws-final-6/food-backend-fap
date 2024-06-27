# 베이스 이미지 설정
FROM python:3.12-alpine

# 작업 디렉터리 설정
WORKDIR /code

# 필요 파일 복사
COPY ./requirements.txt /code/requirements.txt

# 필요한 패키지 설치
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 애플리케이션 파일 복사
COPY ./app /code/app

# FastAPI 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
