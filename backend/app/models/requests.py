from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class DataCollectionRequest(BaseModel):
    """데이터 수집 요청"""
    source: str = Field(..., description="데이터 소스 (news, disclosures, market)")
    limit: Optional[int] = Field(10, description="수집할 데이터 개수")
    refresh_cache: bool = Field(False, description="캐시 새로고침 여부")

class InsightGenerationRequest(BaseModel):
    """인사이트 생성 요청"""
    include_news: bool = Field(True, description="뉴스 데이터 포함 여부")
    include_disclosures: bool = Field(True, description="공시 데이터 포함 여부")
    include_market: bool = Field(True, description="시장 데이터 포함 여부")
    use_graph_rag: bool = Field(True, description="GraphRAG 사용 여부")
    max_entities: int = Field(10, description="최대 엔티티 수")
    analysis_depth: str = Field("standard", description="분석 깊이 (basic, standard, deep)")

class EntityAnalysisRequest(BaseModel):
    """엔티티 분석 요청"""
    entities: List[str] = Field(..., description="분석할 엔티티 목록")
    analysis_type: str = Field("relations", description="분석 유형 (relations, importance, trends)")
    depth: int = Field(2, description="관계 탐색 깊이")

class CustomPromptRequest(BaseModel):
    """사용자 정의 프롬프트 요청"""
    prompt: str = Field(..., description="사용자 정의 프롬프트")
    include_context: bool = Field(True, description="수집된 데이터 컨텍스트 포함 여부")
    max_tokens: int = Field(500, description="최대 토큰 수")
