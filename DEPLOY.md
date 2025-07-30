# 미래에셋 AI 금융 인사이트 시스템 배포 안내서

## 1. 환경 설정

### 필수 환경 변수 설정
다음 API 키를 `.env` 파일에 설정해야 합니다:

```bash
# 네이버 CLOVA API 키 (필수)
NAVER_CLOVA_API_KEY=your_clova_api_key_here

# DART API 키 (필수)
DART_API_KEY=your_dart_api_key_here
```

### 시스템 요구사항
- Docker 및 Docker Compose가 설치되어 있어야 합니다
- 최소 8GB RAM 권장
- 최소 20GB 디스크 공간 권장

## 2. 배포 및 데이터 파이프라인 실행

준비된 배포 스크립트를 사용하여 시스템을 배포하고 데이터 파이프라인을 실행할 수 있습니다:

```bash
# 배포 스크립트 실행
./deploy.sh
```

이 스크립트는 다음 작업을 수행합니다:
1. Docker Compose로 모든 서비스(Backend, Frontend, Milvus, Neo4j) 시작
2. Milvus가 시작될 때까지 대기
3. DART API에서 금융 데이터 수집
4. 수집된 데이터를 CLOVA API를 사용하여 분석 및 임베딩
5. Milvus 벡터 데이터베이스에 임베딩 데이터 저장

## 3. 서비스 접속 정보

배포가 완료된 후 다음 URL로 서비스에 접속할 수 있습니다:

- **프론트엔드**: http://localhost:3001
- **백엔드 API**: http://localhost:8001/docs
- **Milvus UI**: http://localhost:9091
- **Neo4j Browser**: http://localhost:7474

## 4. 파이프라인 별도 실행 (선택사항)

데이터 파이프라인을 별도로 실행하려면:

```bash
# 백엔드 컨테이너에 접속
docker-compose exec backend bash

# 파이프라인 스크립트 실행
bash /app/scripts/run_dart_pipeline.sh
```

## 5. 문제 해결

- **Milvus 연결 오류**: Milvus 서비스가 완전히 시작되었는지 확인하세요
- **API 키 오류**: `.env` 파일에 필수 API 키가 올바르게 설정되었는지 확인하세요
- **메모리 부족 오류**: Docker에 할당된 메모리를 증가시키세요
- **파이프라인 실패**: 로그를 확인하고 필요한 패키지가 모두 설치되었는지 확인하세요

## 6. 배포 시간 최적화 (빠른 배포)

배포 시간이 제한된 경우 다음과 같이 파이프라인 파라미터를 조정하세요:

```bash
# scripts/run_dart_pipeline.sh 파일에서 다음 줄 수정:
python -m app.crawling.dart_pipeline pipeline --years 2025 --top-n 20 --batch-size 10
```

이렇게 하면 수집 데이터의 양을 줄여 배포 시간을 단축할 수 있습니다.
