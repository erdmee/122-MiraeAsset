#!/bin/bash

# DART API 데이터 수집 및 Milvus 임베딩 스크립트
echo "==============================================="
echo "DART API 데이터 수집 및 임베딩 작업을 시작합니다"
echo "==============================================="

# 필요한 패키지 설치
pip install pymilvus tqdm requests

# 데이터 디렉토리 준비
mkdir -p /app/data/crawled/dart_api

# 파이프라인 단계 1: 데이터 수집
echo "[1/2] DART API에서 데이터 수집 중..."
cd /app
python -m app.crawling.dart_pipeline collect --years 2025 2024

# 파이프라인 단계 2: Milvus 임베딩
echo "[2/2] 수집된 데이터를 Milvus에 임베딩 중..."
python -m app.crawling.dart_pipeline embed --create-collections --batch-size 50

echo "==============================================="
echo "모든 작업이 완료되었습니다!"
echo "==============================================="
