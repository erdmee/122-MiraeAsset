#!/bin/bash

# 뉴스 크롤링 및 Graph RAG 구축 파이프라인

echo "🗞️ 금융 뉴스 크롤링 및 Graph RAG 구축 시작..."
echo "⏰ $(date)"
echo ""

# Docker Compose가 실행 중인지 확인
if ! docker compose ps | grep -q "backend.*Up"; then
    echo "❌ backend 컨테이너가 실행되지 않았습니다."
    echo "다음 명령어로 먼저 컨테이너를 시작하세요:"
    echo "  docker compose up -d"
    exit 1
fi

# Neo4j가 준비되었는지 확인
echo "🔍 Neo4j 연결 확인 중..."
if ! docker compose exec backend python -c "from app.services.db import Neo4jConnection; Neo4jConnection.get_driver().verify_connectivity()" &>/dev/null; then
    echo "❌ Neo4j가 준비되지 않았습니다. 잠시 기다린 후 다시 시도하세요."
    exit 1
fi

echo "✅ Neo4j 연결 확인 완료"
echo ""

# 뉴스 크롤링 및 Graph 구축 실행
echo "🔄 뉴스 크롤링 및 엔티티/관계 추출 시작..."
docker compose exec backend python -c "
import asyncio
from app.services.news_graph_crawler import run_news_crawling_pipeline
asyncio.run(run_news_crawling_pipeline())
"

echo ""
echo "✅ 뉴스 크롤링 파이프라인 실행 완료!"
echo "⏰ $(date)"

# Graph 통계 출력
echo ""
echo "📊 Graph 통계:"
docker compose exec backend python -c "
from app.services.graph_rag_tool import get_graph_statistics
print(get_graph_statistics())
"
