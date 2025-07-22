from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str = Field(..., description="시스템 상태")
    timestamp: datetime = Field(..., description="응답 시간")
    version: str = Field(..., description="API 버전")
    environment: str = Field(..., description="실행 환경")
    services: Dict[str, bool] = Field(..., description="서비스 상태")

class NewsItem(BaseModel):
    """뉴스 아이템"""
    title: str = Field(..., description="뉴스 제목")
    link: Optional[str] = Field(None, description="뉴스 링크")
    source: str = Field(..., description="뉴스 소스")
    published_at: Optional[str] = Field(None, description="발행 시간")
    summary: Optional[str] = Field(None, description="요약")
    entities: List[str] = Field(default_factory=list, description="추출된 엔티티")
    importance_score: float = Field(0.0, description="중요도 점수")

class DisclosureItem(BaseModel):
    """공시 아이템"""
    company: str = Field(..., description="회사명")
    title: str = Field(..., description="공시 제목")
    date: str = Field(..., description="공시 날짜")
    type: str = Field(..., description="공시 유형")
    link: Optional[str] = Field(None, description="공시 링크")
    importance_score: float = Field(0.0, description="중요도 점수")

class MarketData(BaseModel):
    """시장 데이터"""
    index_name: str = Field(..., description="지수명")
    current_value: str = Field(..., description="현재 값")
    change: Optional[str] = Field(None, description="변화량")
    change_percent: Optional[str] = Field(None, description="변화율")
    updated_at: datetime = Field(..., description="업데이트 시간")

class EntityInfo(BaseModel):
    """엔티티 정보"""
    name: str = Field(..., description="엔티티명")
    type: str = Field(..., description="엔티티 유형")
    importance_score: float = Field(..., description="중요도 점수")
    related_entities: List[str] = Field(default_factory=list, description="관련 엔티티")
    mentioned_count: int = Field(0, description="언급 횟수")

class GraphRAGAnalysis(BaseModel):
    """GraphRAG 분석 결과"""
    entities: List[EntityInfo] = Field(..., description="추출된 엔티티")
    relationships: List[Dict[str, Any]] = Field(..., description="엔티티 관계")
    top_entities: List[Dict[str, Any]] = Field(..., description="상위 엔티티")
    network_stats: Dict[str, Any] = Field(..., description="네트워크 통계")

class InsightResponse(BaseModel):
    """인사이트 응답"""
    id: str = Field(..., description="인사이트 ID")
    content: str = Field(..., description="인사이트 내용")
    summary: str = Field(..., description="인사이트 요약")
    confidence_score: float = Field(..., description="신뢰도 점수")
    generated_at: datetime = Field(..., description="생성 시간")
    data_sources: List[str] = Field(..., description="사용된 데이터 소스")
    entities_analyzed: List[str] = Field(..., description="분석된 엔티티")
    graph_rag_analysis: Optional[GraphRAGAnalysis] = Field(None, description="GraphRAG 분석 결과")
    processing_time: float = Field(..., description="처리 시간(초)")

class DataCollectionResponse(BaseModel):
    """데이터 수집 응답"""
    source: str = Field(..., description="데이터 소스")
    count: int = Field(..., description="수집된 데이터 수")
    collected_at: datetime = Field(..., description="수집 시간")
    from_cache: bool = Field(..., description="캐시에서 가져온 여부")
    data: List[Dict[str, Any]] = Field(..., description="수집된 데이터")

class ErrorResponse(BaseModel):
    """에러 응답"""
    error: str = Field(..., description="에러 유형")
    message: str = Field(..., description="에러 메시지")
    timestamp: datetime = Field(..., description="에러 발생 시간")
    request_id: Optional[str] = Field(None, description="요청 ID")
