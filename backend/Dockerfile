FROM python:3.10-slim

WORKDIR /app

# requirements.txt 먼저 복사하고 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 나머지 전체 복사
COPY . .

# CMD는 docker-compose에서 override
