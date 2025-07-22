from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    """위험 수준"""

    LOW = "저위험"
    MEDIUM = "중위험"
    HIGH = "고위험"


class InvestmentStyle(str, Enum):
    """투자 스타일"""

    GROWTH = "성장형"
    VALUE = "가치형"
    DIVIDEND = "배당형"
    BALANCED = "균형형"
    MOMENTUM = "모멘텀형"


class InvestmentPeriod(str, Enum):
    """투자 기간"""

    SHORT_TERM = "단기"  # 3개월 이하
    MEDIUM_TERM = "중기"  # 3개월 - 1년
    LONG_TERM = "장기"  # 1년 이상


class StockHolding(BaseModel):
    """보유 주식 정보"""

    symbol: str = Field(..., description="종목 코드")
    company_name: str = Field(..., description="회사명")
    shares: int = Field(..., description="보유 주식 수")
    avg_price: int = Field(..., description="평균 매입가")
    sector: Optional[str] = Field(None, description="섹터")
    purchase_date: Optional[datetime] = Field(None, description="매입일")
    target_price: Optional[int] = Field(None, description="목표가")
    stop_loss_price: Optional[int] = Field(None, description="손절가")


class UserPreferences(BaseModel):
    """사용자 투자 선호도"""

    preferred_sectors: List[str] = Field(default_factory=list, description="선호 섹터")
    risk_level: RiskLevel = Field(RiskLevel.MEDIUM, description="위험 수준")
    investment_style: InvestmentStyle = Field(
        InvestmentStyle.BALANCED, description="투자 스타일"
    )
    investment_period: InvestmentPeriod = Field(
        InvestmentPeriod.MEDIUM_TERM, description="투자 기간"
    )
    news_keywords: List[str] = Field(
        default_factory=list, description="관심 뉴스 키워드"
    )
    budget_range: Optional[str] = Field(None, description="투자 예산 범위")
    excluded_sectors: List[str] = Field(default_factory=list, description="제외 섹터")


class UserProfile(BaseModel):
    """사용자 프로필"""

    user_id: str = Field(..., description="사용자 ID")
    name: Optional[str] = Field(None, description="사용자 이름")
    email: Optional[str] = Field(None, description="이메일")
    age: Optional[int] = Field(None, description="나이")
    investment_experience: Optional[str] = Field(None, description="투자 경험")
    portfolio: List[StockHolding] = Field(
        default_factory=list, description="포트폴리오"
    )
    preferences: UserPreferences = Field(
        default_factory=UserPreferences, description="투자 선호도"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="생성일")
    updated_at: datetime = Field(default_factory=datetime.now, description="수정일")


class PortfolioAnalysis(BaseModel):
    """포트폴리오 분석 결과"""

    total_value: int = Field(..., description="총 평가액")
    total_cost: int = Field(..., description="총 투자금")
    total_return: int = Field(..., description="총 수익")
    total_return_percent: float = Field(..., description="총 수익률")
    best_performer: Optional[Dict] = Field(None, description="최고 수익 종목")
    worst_performer: Optional[Dict] = Field(None, description="최저 수익 종목")
    sector_distribution: Dict[str, float] = Field(
        default_factory=dict, description="섹터별 비중"
    )
    holdings_count: int = Field(..., description="보유 종목 수")


class PersonalizedNews(BaseModel):
    """개인화된 뉴스"""

    title: str = Field(..., description="뉴스 제목")
    summary: str = Field(..., description="뉴스 요약")
    source: str = Field(..., description="뉴스 소스")
    published_at: str = Field(..., description="발행 시간")
    entities: List[str] = Field(default_factory=list, description="관련 엔티티")
    importance_score: float = Field(..., description="중요도 점수")
    relevance_score: float = Field(..., description="개인화 관련성 점수")
    reasons: List[str] = Field(default_factory=list, description="관련성 이유")
    sentiment_score: float = Field(0.0, description="감정 점수")


class InvestmentOpportunity(BaseModel):
    """투자 기회"""

    symbol: str = Field(..., description="종목 코드")
    company_name: str = Field(..., description="회사명")
    current_price: int = Field(..., description="현재가")
    change_percent: float = Field(..., description="변동률")
    volume: int = Field(..., description="거래량")
    market_cap: int = Field(..., description="시가총액")
    opportunity_score: float = Field(..., description="기회 점수")
    reasons: List[str] = Field(default_factory=list, description="추천 이유")
    risk_level: str = Field(..., description="위험 수준")
    expected_return: Optional[float] = Field(None, description="예상 수익률")


class PersonalizedInsight(BaseModel):
    """개인화된 인사이트"""

    user_id: str = Field(..., description="사용자 ID")
    script: str = Field(..., description="인사이트 스크립트")
    analysis_method: str = Field(..., description="분석 방법")
    portfolio_analysis: PortfolioAnalysis = Field(..., description="포트폴리오 분석")
    personalized_news: List[PersonalizedNews] = Field(
        default_factory=list, description="개인화된 뉴스"
    )
    investment_opportunities: List[InvestmentOpportunity] = Field(
        default_factory=list, description="투자 기회"
    )
    graph_analysis: Dict = Field(default_factory=dict, description="Graph RAG 분석")
    token_usage: int = Field(0, description="토큰 사용량")
    model_used: str = Field(..., description="사용된 모델")
    generated_at: datetime = Field(
        default_factory=datetime.now, description="생성 시간"
    )
    confidence_score: float = Field(..., description="신뢰도 점수")
    personalization_level: str = Field(..., description="개인화 수준")
    script_length: int = Field(..., description="스크립트 길이")
    estimated_reading_time: str = Field(..., description="예상 읽기 시간")


class UserAction(BaseModel):
    """사용자 행동 로그"""

    user_id: str = Field(..., description="사용자 ID")
    action_type: str = Field(..., description="행동 유형")
    action_data: Dict = Field(default_factory=dict, description="행동 데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="시간")


class StockPrice(BaseModel):
    """주식 가격 정보"""

    symbol: str = Field(..., description="종목 코드")
    company_name: str = Field(..., description="회사명")
    price: int = Field(..., description="현재가")
    change_amount: int = Field(..., description="변동금액")
    change_percent: float = Field(..., description="변동률")
    volume: int = Field(..., description="거래량")
    market_cap: int = Field(..., description="시가총액")
    date: str = Field(..., description="날짜")


class MarketSector(BaseModel):
    """시장 섹터 정보"""

    sector_name: str = Field(..., description="섹터명")
    sector_code: str = Field(..., description="섹터 코드")
    performance: float = Field(..., description="섹터 성과")
    top_stocks: List[str] = Field(default_factory=list, description="주요 종목")
    market_cap: int = Field(..., description="섹터 시가총액")


class AIPersona(BaseModel):
    """AI 페르소나 설정"""

    persona_type: str = Field(..., description="페르소나 유형")
    tone: str = Field(..., description="말투")
    focus_areas: List[str] = Field(default_factory=list, description="집중 영역")
    risk_tolerance: str = Field(..., description="위험 허용도")
    communication_style: str = Field(..., description="소통 스타일")
