#!/bin/bash

# DART to Elasticsearch 파이프라인 실행 스크립트

echo "🚀 DART to Elasticsearch 파이프라인 시작..."
echo "⏰ $(date)"
echo ""

# Docker Compose가 실행 중인지 확인
if ! docker-compose ps | grep -q "backend.*Up"; then
    echo "❌ backend 컨테이너가 실행되지 않았습니다."
    echo "다음 명령어로 먼저 컨테이너를 시작하세요:"
    echo "  docker-compose up -d"
    exit 1
fi

# Elasticsearch가 준비되었는지 확인
echo "🔍 Elasticsearch 연결 확인 중..."
if ! docker-compose exec backend curl -f http://elasticsearch:9200/_cluster/health &>/dev/null; then
    echo "❌ Elasticsearch가 준비되지 않았습니다. 잠시 기다린 후 다시 시도하세요."
    exit 1
fi

echo "✅ Elasticsearch 연결 확인 완료"
echo ""

# 파이프라인 실행
echo "🔄 DART 데이터 임베딩 및 Elasticsearch 인덱싱 시작..."
docker-compose exec backend python -m app.pipelines.dart_to_elastic

echo ""
echo "✅ 파이프라인 실행 완료!"
echo "⏰ $(date)"
