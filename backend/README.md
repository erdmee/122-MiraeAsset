# 미래에셋 AI 금융 인사이트 시스템

## 개요
실시간 금융 데이터 수집 및 AI 기반 인사이트 생성 시스템

## 기능
- 실시간 금융 데이터 수집 (뉴스, 공시, 시장지수)
- AI 기반 인사이트 생성
- 엔티티 연관관계 분석 (Simple GraphRAG)
- RESTful API 제공

## 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에서 API 키 설정

# 서버 실행
uvicorn app.main:app --reload
```

## API 문서
서버 실행 후 http://localhost:8004/docs 에서 확인

## 기술 스택
- FastAPI + Python 3.11
- Simple GraphRAG
- OpenAI GPT API
- playwright 웹 크롤링
