# app/api/routes/users.py
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from pydantic import BaseModel
from app.services.personalized_insight_generator import PersonalizedInsightGenerator

router = APIRouter()
insight_generator = PersonalizedInsightGenerator()


# Pydantic 모델 정의
class StockHolding(BaseModel):
    symbol: str
    company_name: str
    shares: int
    avg_price: int
    sector: str = None


class UserPreferences(BaseModel):
    preferred_sectors: List[str] = []
    risk_level: str = "중위험"
    investment_style: str = "균형형"
    news_keywords: List[str] = []


@router.post("/portfolio/{user_id}")
async def save_user_portfolio(user_id: str, portfolio: List[StockHolding]):
    """사용자 포트폴리오 저장"""
    try:
        portfolio_data = [holding.dict() for holding in portfolio]
        insight_generator.save_user_portfolio(user_id, portfolio_data)

        return {
            "message": "포트폴리오가 성공적으로 저장되었습니다",
            "user_id": user_id,
            "portfolio_count": len(portfolio_data),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"포트폴리오 저장 실패: {str(e)}")


@router.post("/preferences/{user_id}")
async def save_user_preferences(user_id: str, preferences: UserPreferences):
    """사용자 투자 선호도 저장"""
    try:
        insight_generator.save_user_preferences(user_id, preferences.dict())

        return {
            "message": "투자 선호도가 성공적으로 저장되었습니다",
            "user_id": user_id,
            "preferences": preferences.dict(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"선호도 저장 실패: {str(e)}")


@router.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    """사용자 프로필 조회 (포트폴리오 + 선호도)"""
    try:
        from app.services.enhanced_data_collector import EnhancedDataCollector

        data_collector = EnhancedDataCollector()

        personalized_data = data_collector.get_personalized_data(user_id)

        # 포트폴리오 데이터 포맷팅
        portfolio = []
        for holding in personalized_data.get("portfolio", []):
            portfolio.append(
                {
                    "symbol": holding[0],
                    "company_name": holding[1],
                    "shares": holding[2],
                    "avg_price": holding[3],
                    "sector": holding[4] if len(holding) > 4 else None,
                }
            )

        return {
            "user_id": user_id,
            "portfolio": portfolio,
            "preferences": personalized_data.get("preferences", {}),
            "portfolio_count": len(portfolio),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"사용자 프로필 조회 실패: {str(e)}"
        )


@router.post("/demo-data/{user_id}")
async def create_demo_user_data(user_id: str):
    """데모용 사용자 데이터 생성"""
    try:
        # 데모 포트폴리오
        demo_portfolio = [
            {
                "symbol": "005930",
                "company_name": "삼성전자",
                "shares": 10,
                "avg_price": 70000,
                "sector": "반도체",
            },
            {
                "symbol": "000660",
                "company_name": "SK하이닉스",
                "shares": 5,
                "avg_price": 120000,
                "sector": "반도체",
            },
            {
                "symbol": "035420",
                "company_name": "NAVER",
                "shares": 3,
                "avg_price": 200000,
                "sector": "IT",
            },
        ]

        # 데모 선호도
        demo_preferences = {
            "preferred_sectors": ["AI", "반도체", "IT", "소프트웨어"],
            "risk_level": "고위험",
            "investment_style": "성장형",
            "news_keywords": ["AI", "인공지능", "ChatGPT", "NVIDIA", "반도체"],
        }

        # 데이터 저장
        insight_generator.save_user_portfolio(user_id, demo_portfolio)
        insight_generator.save_user_preferences(user_id, demo_preferences)

        return {
            "message": "데모 사용자 데이터가 생성되었습니다",
            "user_id": user_id,
            "portfolio": demo_portfolio,
            "preferences": demo_preferences,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데모 데이터 생성 실패: {str(e)}")


@router.delete("/profile/{user_id}")
async def delete_user_profile(user_id: str):
    """사용자 프로필 삭제"""
    try:
        import sqlite3
        from app.config import settings

        conn = sqlite3.connect(settings.DB_PATH)
        cursor = conn.cursor()

        # 포트폴리오 및 선호도 삭제
        cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))

        portfolio_deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return {
            "message": "사용자 프로필이 삭제되었습니다",
            "user_id": user_id,
            "deleted_records": portfolio_deleted,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 삭제 실패: {str(e)}")


@router.get("/test")
async def test_user_management():
    """사용자 관리 기능 테스트"""
    try:
        # 테스트용 사용자 ID
        test_user_id = "test_user_001"

        # 데모 데이터 생성
        demo_portfolio = [
            {
                "symbol": "005930",
                "company_name": "삼성전자",
                "shares": 1,
                "avg_price": 70000,
                "sector": "반도체",
            }
        ]

        insight_generator.save_user_portfolio(test_user_id, demo_portfolio)

        return {
            "status": "success",
            "message": "사용자 관리 테스트 완료",
            "test_user_id": test_user_id,
        }

    except Exception as e:
        return {"status": "error", "message": f"테스트 실패: {str(e)}"}
