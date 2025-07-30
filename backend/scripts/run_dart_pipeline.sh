#!/bin/bash

# DART 데이터 수집 및 Milvus 임베딩 파이프라인 스크립트

# 필요한 패키지 설치 확인
echo "필요한 패키지 설치 확인 중..."
pip install --no-cache-dir pymilvus requests tqdm

# 환경 변수 설정 확인
if [ -z "$DART_API_KEY" ]; then
  echo "ERROR: DART_API_KEY 환경변수가 설정되지 않았습니다."
  exit 1
fi

if [ -z "$NAVER_CLOVA_API_KEY" ]; then
  echo "ERROR: NAVER_CLOVA_API_KEY 환경변수가 설정되지 않았습니다."
  exit 1
fi

# 데이터 디렉토리 생성
mkdir -p /app/data/crawled/dart_api

# DART API로부터 데이터 수집 및 Milvus에 임베딩 실행
cd /app
echo "파이프라인 실행 시작: $(date)"

# 옵션 설명
# --years: 수집할 연도 (최신 데이터 기준)
# --top-n: 시가총액 상위 기업 수
# --batch-size: 임베딩 배치 처리 크기

python -m app.crawling.dart_pipeline pipeline --years 2025 2024 --top-n 50 --batch-size 20

echo "파이프라인 실행 완료: $(date)"
