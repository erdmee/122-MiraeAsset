# app/api/routes/user_profile.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import logging
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

class UserProfileCreate(BaseModel):
    user_id: str
    name: Optional[str] = None  # 이름
    age: Optional[int] = None  # 나이
    investment_experience: str  # "초보자", "중급자", "고급자"
    risk_tolerance: str  # "안전형", "안정형", "위험중립형", "적극투자형", "공격투자형"
    investment_goals: List[str]  # ["단기수익", "장기성장", "배당수익", "자산보전"]
    investment_style: Optional[str] = None  # "가치투자", "성장투자", "배당투자", "기술주투자", "균형투자"
    preferred_sectors: List[str]  # ["IT/기술", "바이오/제약", "금융", "제조업", "에너지", "소비재"]
    investment_amount_range: Optional[str] = None  # "1천만원 미만", "1천-5천만원", "5천만원-1억원", "1억원 이상"
    news_keywords: List[str] = []  # 관심 키워드

class PortfolioHolding(BaseModel):
    symbol: str
    company_name: str
    shares: int
    avg_price: float
    sector: Optional[str] = None

class UserPortfolioCreate(BaseModel):
    user_id: str
    holdings: List[PortfolioHolding]

class UserProfileResponse(BaseModel):
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    investment_experience: str
    risk_tolerance: str
    investment_goals: List[str]
    investment_style: Optional[str] = None
    preferred_sectors: List[str]
    investment_amount_range: Optional[str] = None
    news_keywords: List[str]
    has_portfolio: bool
    portfolio_count: int

def get_db_path():
    """데이터베이스 경로 가져오기"""
    return getattr(settings, 'DB_PATH', 'data/financial_data.db')

def init_user_tables():
    """사용자 관련 테이블 초기화"""
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    
    # 사용자 프로필 테이블
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            investment_experience TEXT NOT NULL,
            risk_tolerance TEXT NOT NULL,
            investment_goals TEXT NOT NULL,  -- JSON 문자열로 저장
            investment_style TEXT,
            preferred_sectors TEXT NOT NULL,  -- JSON 문자열로 저장
            investment_amount_range TEXT,
            news_keywords TEXT DEFAULT '[]',  -- JSON 문자열로 저장
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 기존 테이블에 새 컬럼이 없다면 추가
    try:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN name TEXT")
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 존재함
    
    try:
        cursor.execute("ALTER TABLE user_profiles ADD COLUMN age INTEGER")
    except sqlite3.OperationalError:
        pass  # 컬럼이 이미 존재함
    
    # 사용자 포트폴리오 테이블 (기존 테이블이 있다면 업데이트)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            company_name TEXT NOT NULL,
            shares INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            sector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, symbol)
        )
    ''')
    
    conn.commit()
    conn.close()

# 서버 시작시 테이블 초기화
init_user_tables()

@router.post("/profile", response_model=Dict[str, Any])
async def create_user_profile(profile: UserProfileCreate):
    """사용자 프로필 생성/업데이트"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # JSON 문자열로 변환
        import json
        investment_goals_json = json.dumps(profile.investment_goals, ensure_ascii=False)
        preferred_sectors_json = json.dumps(profile.preferred_sectors, ensure_ascii=False)
        news_keywords_json = json.dumps(profile.news_keywords, ensure_ascii=False)
        
        # 기존 프로필이 있는지 확인
        cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (profile.user_id,))
        existing_profile = cursor.fetchone()
        
        if existing_profile:
            # 업데이트
            cursor.execute('''
                UPDATE user_profiles 
                SET name = ?, age = ?, investment_experience = ?, risk_tolerance = ?, investment_goals = ?,
                    investment_style = ?, preferred_sectors = ?, investment_amount_range = ?,
                    news_keywords = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (
                profile.name,
                profile.age,
                profile.investment_experience,
                profile.risk_tolerance,
                investment_goals_json,
                profile.investment_style,
                preferred_sectors_json,
                profile.investment_amount_range,
                news_keywords_json,
                profile.user_id
            ))
            action = "updated"
        else:
            # 새로 생성
            cursor.execute('''
                INSERT INTO user_profiles 
                (user_id, name, age, investment_experience, risk_tolerance, investment_goals,
                 investment_style, preferred_sectors, investment_amount_range, news_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.user_id,
                profile.name,
                profile.age,
                profile.investment_experience,
                profile.risk_tolerance,
                investment_goals_json,
                profile.investment_style,
                preferred_sectors_json,
                profile.investment_amount_range,
                news_keywords_json
            ))
            action = "created"
        
        conn.commit()
        conn.close()
        
        logger.info(f"사용자 프로필 {action}: {profile.user_id}")
        
        return {
            "success": True,
            "message": f"사용자 프로필이 성공적으로 {action}되었습니다",
            "user_id": profile.user_id,
            "action": action
        }
        
    except Exception as e:
        logger.error(f"사용자 프로필 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"프로필 저장 중 오류가 발생했습니다: {str(e)}")

@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """사용자 프로필 조회"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 프로필 조회
        cursor.execute('''
            SELECT name, age, investment_experience, risk_tolerance, investment_goals,
                   investment_style, preferred_sectors, investment_amount_range, news_keywords
            FROM user_profiles WHERE user_id = ?
        ''', (user_id,))
        
        profile_data = cursor.fetchone()
        
        if not profile_data:
            raise HTTPException(status_code=404, detail="사용자 프로필을 찾을 수 없습니다")
        
        # 포트폴리오 개수 조회
        cursor.execute("SELECT COUNT(*) FROM user_portfolios WHERE user_id = ?", (user_id,))
        portfolio_count = cursor.fetchone()[0]
        
        conn.close()
        
        # JSON 문자열 파싱
        import json
        investment_goals = json.loads(profile_data[4]) if profile_data[4] else []
        preferred_sectors = json.loads(profile_data[6]) if profile_data[6] else []
        news_keywords = json.loads(profile_data[8]) if profile_data[8] else []
        
        return UserProfileResponse(
            user_id=user_id,
            name=profile_data[0],
            age=profile_data[1],
            investment_experience=profile_data[2],
            risk_tolerance=profile_data[3],
            investment_goals=investment_goals,
            investment_style=profile_data[5],
            preferred_sectors=preferred_sectors,
            investment_amount_range=profile_data[7],
            news_keywords=news_keywords,
            has_portfolio=portfolio_count > 0,
            portfolio_count=portfolio_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 프로필 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"프로필 조회 중 오류가 발생했습니다: {str(e)}")

@router.post("/portfolio", response_model=Dict[str, Any])
async def create_user_portfolio(portfolio: UserPortfolioCreate):
    """사용자 포트폴리오 생성/업데이트"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 기존 포트폴리오 삭제
        cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (portfolio.user_id,))
        
        # 새 포트폴리오 입력
        for holding in portfolio.holdings:
            cursor.execute('''
                INSERT INTO user_portfolios 
                (user_id, symbol, company_name, shares, avg_price, sector)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                portfolio.user_id,
                holding.symbol,
                holding.company_name,
                holding.shares,
                holding.avg_price,
                holding.sector
            ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"사용자 포트폴리오 저장: {portfolio.user_id}, {len(portfolio.holdings)}개 종목")
        
        return {
            "success": True,
            "message": f"{len(portfolio.holdings)}개 종목이 포트폴리오에 저장되었습니다",
            "user_id": portfolio.user_id,
            "holdings_count": len(portfolio.holdings)
        }
        
    except Exception as e:
        logger.error(f"포트폴리오 저장 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 저장 중 오류가 발생했습니다: {str(e)}")

@router.get("/portfolio/{user_id}")
async def get_user_portfolio(user_id: str):
    """사용자 포트폴리오 조회"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT symbol, company_name, shares, avg_price, sector
            FROM user_portfolios WHERE user_id = ?
            ORDER BY company_name
        ''', (user_id,))
        
        holdings = cursor.fetchall()
        conn.close()
        
        portfolio_list = []
        for holding in holdings:
            portfolio_list.append({
                "symbol": holding[0],
                "company_name": holding[1],
                "shares": holding[2],
                "avg_price": holding[3],
                "sector": holding[4]
            })
        
        return {
            "user_id": user_id,
            "holdings": portfolio_list,
            "holdings_count": len(portfolio_list)
        }
        
    except Exception as e:
        logger.error(f"포트폴리오 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"포트폴리오 조회 중 오류가 발생했습니다: {str(e)}")

@router.delete("/profile/{user_id}")
async def delete_user_profile(user_id: str):
    """사용자 프로필 삭제"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 프로필과 포트폴리오 모두 삭제
        cursor.execute("DELETE FROM user_profiles WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM user_portfolios WHERE user_id = ?", (user_id,))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "사용자 데이터가 삭제되었습니다"}
        
    except Exception as e:
        logger.error(f"사용자 데이터 삭제 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"데이터 삭제 중 오류가 발생했습니다: {str(e)}")

@router.get("/check/{user_id}")
async def check_user_setup(user_id: str):
    """사용자 설정 완료 여부 확인"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 프로필 존재 여부 확인
        cursor.execute("SELECT user_id FROM user_profiles WHERE user_id = ?", (user_id,))
        has_profile = cursor.fetchone() is not None
        
        # 포트폴리오 존재 여부 확인
        cursor.execute("SELECT COUNT(*) FROM user_portfolios WHERE user_id = ?", (user_id,))
        portfolio_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "user_id": user_id,
            "has_profile": has_profile,
            "has_portfolio": portfolio_count > 0,
            "portfolio_count": portfolio_count,
            "setup_complete": has_profile  # 프로필만 있으면 기본 설정 완료로 간주
        }
        
    except Exception as e:
        logger.error(f"사용자 설정 확인 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"설정 확인 중 오류가 발생했습니다: {str(e)}")
