# app/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from app.api.routes import financial_data, insights, users
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행
    print(">> FastAPI 서버 시작")
    yield
    # 애플리케이션 종료 시 실행
    print(">> FastAPI 서버 종료")


# FastAPI 앱 인스턴스 생성
app = FastAPI(
    title="미래에셋 AI 투자 인사이트 API",
    description="실시간 금융 데이터 수집 및 개인화된 AI 투자 인사이트 제공 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 설정 (프론트엔드 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중에는 모든 도메인 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(
    financial_data.router, prefix="/api/financial-data", tags=["Financial Data"]
)
app.include_router(insights.router, prefix="/api/insights", tags=["Insights"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])


@app.get("/")
async def root():
    """API 서버 상태 확인"""
    return {
        "message": "미래에셋 AI 투자 인사이트 API 서버",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=8004, reload=True, log_level="info"
    )
