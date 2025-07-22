# app/api/routes/financial_data.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.enhanced_data_collector import EnhancedDataCollector
from app.models.responses import NewsItem, DisclosureItem
from app.models.user_models import StockPrice

router = APIRouter()
data_collector = EnhancedDataCollector()


@router.get("/news", response_model=List[dict])
async def get_financial_news(
    limit: int = Query(default=10, ge=1, le=50, description="뉴스 개수 (1-50)"),
    use_playwright: bool = Query(default=True, description="Playwright 사용 여부"),
):
    """실시간 금융 뉴스 수집"""
    try:
        news_data = data_collector.collect_comprehensive_news(
            limit=limit, use_playwright=use_playwright
        )

        return [
            {
                "title": news.title,
                "summary": news.summary,
                "source": news.source,
                "published_at": news.published_at,
                "entities": news.entities,
                "importance_score": news.importance_score,
            }
            for news in news_data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"뉴스 수집 실패: {str(e)}")


@router.get("/disclosures", response_model=List[dict])
async def get_disclosures(
    limit: int = Query(default=20, ge=1, le=100, description="공시 개수 (1-100)")
):
    """DART 공시 정보 수집"""
    try:
        disclosures = data_collector.collect_comprehensive_disclosures(limit=limit)

        return [
            {
                "company": disclosure.company,
                "title": disclosure.title,
                "date": disclosure.date,
                "type": disclosure.type,
                "importance_score": disclosure.importance_score,
            }
            for disclosure in disclosures
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공시 수집 실패: {str(e)}")


@router.get("/stocks", response_model=List[dict])
async def get_stock_data(
    symbols: Optional[str] = Query(default=None, description="종목 코드 (쉼표로 구분)")
):
    """주식 시세 데이터 수집"""
    try:
        symbol_list = None
        if symbols:
            symbol_list = [s.strip() for s in symbols.split(",")]

        stock_data = data_collector.collect_comprehensive_stock_data(symbol_list)

        return [
            {
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "price": stock.price,
                "change_amount": stock.change_amount,
                "change_percent": stock.change_percent,
                "volume": stock.volume,
                "market_cap": stock.market_cap,
                "date": stock.date,
            }
            for stock in stock_data
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 데이터 수집 실패: {str(e)}")


@router.get("/all")
async def get_all_financial_data(
    user_id: Optional[str] = Query(default=None, description="사용자 ID (개인화용)"),
    refresh_cache: bool = Query(default=False, description="캐시 새로고침 여부"),
    use_playwright: bool = Query(default=True, description="Playwright 사용 여부"),
):
    """전체 금융 데이터 수집 (뉴스 + 공시 + 주식)"""
    try:
        all_data = data_collector.collect_all_data(
            user_id=user_id, refresh_cache=refresh_cache, use_playwright=use_playwright
        )

        # 응답 데이터 변환
        response_data = {
            "news": [
                {
                    "title": news.title,
                    "summary": news.summary,
                    "source": news.source,
                    "published_at": news.published_at,
                    "entities": news.entities,
                    "importance_score": news.importance_score,
                }
                for news in all_data.get("news", [])
            ],
            "disclosures": [
                {
                    "company": disclosure.company,
                    "title": disclosure.title,
                    "date": disclosure.date,
                    "type": disclosure.type,
                    "importance_score": disclosure.importance_score,
                }
                for disclosure in all_data.get("disclosures", [])
            ],
            "stock_data": [
                {
                    "symbol": stock.symbol,
                    "company_name": stock.company_name,
                    "price": stock.price,
                    "change_amount": stock.change_amount,
                    "change_percent": stock.change_percent,
                    "volume": stock.volume,
                    "market_cap": stock.market_cap,
                    "date": stock.date,
                }
                for stock in all_data.get("stock_data", [])
            ],
            "personalized": all_data.get("personalized", {}),
            "collected_at": all_data.get("collected_at"),
            "data_sources": all_data.get("data_sources", {}),
        }

        return response_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 데이터 수집 실패: {str(e)}")


@router.get("/test")
async def test_data_collection():
    """데이터 수집 기능 테스트"""
    try:
        # 간단한 테스트 데이터 수집
        news = data_collector.collect_comprehensive_news(limit=3, use_playwright=False)

        return {
            "status": "success",
            "message": "데이터 수집 테스트 완료",
            "news_count": len(news),
            "sample_news": news[0].title if news else "뉴스 없음",
        }
    except Exception as e:
        return {"status": "error", "message": f"테스트 실패: {str(e)}"}
