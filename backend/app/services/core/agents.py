import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# 새로운 통합 도구들 import
try:
    from app.services.core.elasticsearch_tool import (
        search_financial_documents,
        get_available_companies,
        get_document_types,
    )

    # graph_rag_tool은 더이상 존재하지 않으므로 더미 함수 사용
    def search_company_news(query, **kwargs):
        return f"회사 뉴스 검색: {query}"

    def find_related_companies(company, **kwargs):
        return f"{company}와 관련된 회사들"

    def get_market_trends(**kwargs):
        return "시장 트렌드 분석"

    def get_graph_statistics(**kwargs):
        return "그래프 통계"

except ImportError as e:
    print(f"새로운 도구 import 실패: {e}")

    # 더미 함수들
    def search_financial_documents(query, **kwargs):
        return f"Elasticsearch 검색: {query}"

    def get_available_companies():
        return "등록된 기업 목록을 가져올 수 없습니다."

    def get_document_types():
        return "문서 타입을 가져올 수 없습니다."

    def search_company_news(company_name, limit=5):
        return f"{company_name} 뉴스 검색 결과"

    def find_related_companies(company_name):
        return f"{company_name} 관련 기업 검색 결과"

    def get_market_trends(days=7):
        return f"최근 {days}일 시장 트렌드"

    def get_graph_statistics():
        return "그래프 통계 정보"


# 실제 웹 검색 및 크롤링 도구들 import
try:
    from app.services.tools.websearch_tool import WebSearchTool as RealWebSearchTool

    print("RealWebSearchTool import 성공")
    WebSearchTool = RealWebSearchTool
except ImportError as e:
    print(f"RealWebSearchTool import 실패 - 더미 클래스 사용: {e}")

    class WebSearchTool:
        def search(self, query):
            return f"웹 검색 더미 결과: {query}"


try:
    from app.services.tools.playwright_tool import PlaywrightTool as RealPlaywrightTool

    print("RealPlaywrightTool import 성공")
    PlaywrightTool = RealPlaywrightTool
except ImportError as e:
    print(f"RealPlaywrightTool import 실패 - 더미 클래스 사용: {e}")

    class PlaywrightTool:
        def scrape(self, url):
            return f"Playwright 더미 결과: {url}"


# 레거시 도구들 (하위 호환성)
try:
    from app.services.tools.graphdb_tool import Neo4jGraphTool as GraphQueryTool

    print("Neo4j GraphQueryTool import 성공")
except ImportError:
    print("Neo4j GraphQueryTool import 실패 - 더미 클래스 사용")

    class GraphQueryTool:
        def query(self, q):
            return f"GraphDB 결과: {q}"

        def query_graph_context(self, q, limit=10):
            return {"query": q, "entities": [], "relationships": []}


# GraphRAGProcessor는 별도로 정의
class GraphRAGProcessor:
    def query_with_graph_context(self, q):
        return {
            "query": q,
            "extracted_entities": [],
            "neighbors": [],
            "relationships": [],
        }

    def build_context_prompt(self, q, data):
        return f"질문: {q}"


try:
    from app.services.core.elasticsearch_tool import (
        ElasticsearchQueryTool as VectorQueryTool,
    )

    print("ElasticsearchQueryTool import 성공")
except ImportError:
    print("ElasticsearchQueryTool import 실패 - 더미 클래스 사용")

    class VectorQueryTool:
        def search(self, q):
            return f"Elasticsearch 결과: {q}"

    class GraphQueryTool:
        def query(self, q):
            return f"GraphDB 결과: {q}"

        def query_graph_context(self, q, limit=10):
            return {"query": q, "entities": [], "relationships": []}

    class GraphRAGProcessor:
        def query_with_graph_context(self, q):
            return {
                "query": q,
                "extracted_entities": [],
                "neighbors": [],
                "relationships": [],
            }

        def build_context_prompt(self, q, data):
            return f"질문: {q}"


try:
    from app.services.tools.sqlite_tool import SQLiteTool
except ImportError:
    print("SQLiteTool import 실패 - 더미 클래스 사용")

    class SQLiteTool:
        def query(self, q):
            return f"SQLite 결과: {q}"


try:
    from app.services.external.hyperclova_client import HyperClovaXClient
except ImportError:
    print("HyperClovaXClient import 실패 - 더미 클래스 사용")

    class HyperClovaXClient:
        def chat_completion(self, **kwargs):
            return {"content": "더미 응답입니다."}


class ClovaXLLM:
    """HyperCLOVA X 래퍼"""

    def __init__(self):
        try:
            from app.services.external.hyperclova_client import HyperClovaXClient

            self.client = HyperClovaXClient()
            print("ClovaXLLM: HyperCLOVA X 클라이언트로 초기화됨")
        except Exception as e:
            print(f"HyperCLOVA X 클라이언트 초기화 실패: {e}")
            print("ClovaXLLM: 더미 모드로 초기화됨")
            self.client = None

    def chat(self, prompt: str) -> str:
        """HyperCLOVA X를 사용한 응답 생성"""
        if self.client:
            try:
                response = self.client.chat_completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=2048,
                )
                if response:
                    # HyperClovaXResponse 객체에서 content 추출
                    if hasattr(response, "get_content"):
                        return response.get_content()
                    elif hasattr(response, "content"):
                        return response.content
                    elif hasattr(response, "get"):
                        return response.get("content", "응답을 생성할 수 없습니다.")
                    else:
                        return str(response)
                return "응답을 생성할 수 없습니다."
            except Exception as e:
                print(f"HyperCLOVA X API 호출 실패: {e}")
                # API 실패 시 더미 응답
                return self._dummy_response(prompt)
        else:
            return self._dummy_response(prompt)

    def _dummy_response(self, prompt: str) -> str:
        """개선된 더미 응답 생성 - 프롬프트 내용에 맞는 응답"""
        print(f"더미 LLM 호출: {prompt[:50]}...")

        prompt_lower = prompt.lower()

        # 질문 분류 관련
        if "classification" in prompt_lower and "simple" in prompt_lower:
            if any(
                word in prompt_lower
                for word in ["안녕", "하이", "hi", "hello", "시간", "날짜"]
            ):
                return '{"classification": "simple", "reason": "인사말 또는 일반적인 질문으로 간단한 응답이 적합합니다."}'
            else:
                return '{"classification": "complex", "reason": "투자 관련 전문 분석이 필요한 질문입니다."}'

        # 쿼리 분해 관련
        elif "분해" in prompt or "하위" in prompt or "쿼리" in prompt:
            return '["기업 최근 실적 및 재무 상태", "업계 시장 동향 및 전망", "주가 기술적 분석 및 목표가"]'

        # 도구 선택 관련
        elif "도구" in prompt or "tool" in prompt:
            if "뉴스" in prompt or "최신" in prompt:
                return '{"tool": "company_news", "reason": "최신 뉴스 정보가 필요하여 company_news 도구가 적합합니다."}'
            elif "재무" in prompt or "실적" in prompt or "공시" in prompt:
                return '{"tool": "financial_search", "reason": "재무 데이터 검색을 위해 financial_search 도구가 적합합니다."}'
            else:
                return '{"tool": "websearch", "reason": "일반적인 정보 검색을 위해 websearch 도구를 사용합니다."}'

        # 기업명 추출 관련
        elif "company" in prompt_lower and "추출" in prompt:
            if "삼성" in prompt:
                return '{"company": "삼성전자", "confidence": "높음"}'
            elif "lg" in prompt_lower:
                return '{"company": "LG전자", "confidence": "높음"}'
            else:
                return '{"company": "", "confidence": "낮음"}'

        # 정보 평가 관련
        elif "평가" in prompt or "sufficiency" in prompt_lower:
            return '{"sufficiency": true, "feedback": "수집된 정보가 투자 의사결정에 충분합니다."}'

        # 일반적인 투자 인사이트
        else:
            return """# 투자 분석 리포트

## 핵심 요약
현재 시장 상황을 종합적으로 분석한 결과, 다음과 같은 주요 포인트를 확인했습니다.

## 시장 동향
- 전반적으로 안정적인 흐름을 보이고 있습니다
- 거래량이 평소 대비 증가하는 추세입니다
- 기관투자자들의 관심이 높아지고 있습니다

## 투자 제안
- **단기**: 신중한 접근 권장
- **중장기**: 선별적 투자 검토 가능
- **리스크 관리**: 포트폴리오 분산 필수

## 주의사항
본 분석은 참고용이며, 실제 투자 결정 시에는 전문가와 상담하시기 바랍니다.

**면책조항**: 투자에는 원금 손실 위험이 있습니다."""


# SimpleAgent - 단순한 질문에 바로 응답
class SimpleAgent:
    def __init__(self, llm=None):
        self.llm = llm or ClovaXLLM()

    async def is_simple_query(self, query: str) -> bool:
        """LLM을 사용하여 단순한 질문인지 판단"""
        prompt = f"""당신은 질문 분류 전문가입니다. 사용자의 질문을 분석하여 단순한 질문인지 복잡한 투자 분석이 필요한 질문인지 판단해주세요.

**역할**: 질문 분류 전문가
**목표**: 질문을 Simple 또는 Complex로 분류

**분류 기준**:
- **Simple**: 인사말, 시간 문의, 기능 설명, 단순한 안부, 일반적인 대화
- **Complex**: 투자 분석, 기업 정보, 시장 동향, 재무 데이터, 종목 분석 등 전문적인 금융 질문

**사용자 질문**: "{query}"

**사고 과정**:
1. 질문의 의도 파악
2. 투자/금융 관련 키워드 존재 여부 확인
3. 전문적인 분석이 필요한지 판단
4. 최종 분류 결정

**응답 형식**: {{"classification": "simple" 또는 "complex", "reason": "분류 이유"}}

분석을 시작하세요:"""

        try:
            response = self.llm.chat(prompt)
            import re
            import json

            # JSON 패턴 찾기
            json_pattern = r'\{[^}]*"classification"[^}]*\}'
            matches = re.search(json_pattern, response)

            if matches:
                result = json.loads(matches.group())
                return result.get("classification", "complex").lower() == "simple"

            # JSON 파싱 실패 시 텍스트 분석
            response_lower = response.lower()
            return "simple" in response_lower and "complex" not in response_lower

        except Exception as e:
            print(f"질문 분류 실패: {e}")
            # 기본적으로 complex로 처리 (안전한 선택)
            return False

    async def generate_simple_response(self, query: str) -> str:
        """LLM을 사용한 단순 질문 응답 생성"""
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        current_weekday = datetime.now().strftime("%A")
        weekday_korean = {
            "Monday": "월요일",
            "Tuesday": "화요일",
            "Wednesday": "수요일",
            "Thursday": "목요일",
            "Friday": "금요일",
            "Saturday": "토요일",
            "Sunday": "일요일",
        }

        prompt = f"""당신은 친근하고 전문적인 AI 투자 어시스턴트입니다. 사용자의 간단한 질문에 자연스럽게 응답해주세요.

**역할**: 미래에셋 AI 투자 어시스턴트
**성격**: 친근하고 도움이 되는 전문가
**목표**: 사용자에게 유용하고 자연스러운 응답 제공

**현재 정보**:
- 현재 시간: {current_time}
- 오늘 날짜: {current_date} ({weekday_korean.get(current_weekday, current_weekday)})

**사용자 질문**: "{query}"

**응답 지침**:
1. 친근하고 전문적인 톤 유지
2. 필요시 현재 날짜/시간 정보 활용
3. 투자 어시스턴트로서의 역할과 기능 소개
4. 마크다운 형식 사용 (이모지 사용 금지)
5. 간결하면서도 도움이 되는 정보 제공

**사고 과정**:
1. 질문의 의도 파악
2. 적절한 응답 유형 결정 (인사, 시간, 기능 설명 등)
3. 사용자에게 도움이 될 추가 정보 고려
4. 자연스러운 대화 흐름 유지

응답을 생성하세요:"""

        try:
            return self.llm.chat(prompt)
        except Exception as e:
            print(f"Simple 응답 생성 실패: {e}")
            return f"""안녕하세요.

현재 시간은 **{current_time}**입니다.

저는 미래에셋 AI 투자 어시스턴트입니다. 다음과 같은 도움을 드릴 수 있습니다:

## 주요 기능
- **기업 분석**: 재무제표, 실적, 전망 분석
- **시장 동향**: 최신 뉴스와 시장 트렌드
- **투자 인사이트**: 맞춤형 투자 조언
- **종목 검색**: 관심 기업 정보 조회

궁금한 점이 있으시면 언제든 말씀해 주세요."""


# PlanningAgent - 지능적 쿼리 분해 및 도구 기반 계획
class PlanningAgent:
    def __init__(self, llm=None):
        self.llm = llm or ClovaXLLM()

        # 도구별 특화 쿼리 패턴
        self.tool_patterns = {
            "financial_search": [
                "재무",
                "실적",
                "영업이익",
                "매출",
                "공시",
                "사업보고서",
                "재무제표",
                "ROE",
                "PER",
                "PBR",
            ],
            "company_news": [
                "뉴스",
                "최신",
                "발표",
                "소식",
                "언론",
                "보도",
                "기사",
                "이슈",
            ],
            "websearch": [
                "전망",
                "분석",
                "의견",
                "시장",
                "업계",
                "동향",
                "트렌드",
                "환경",
            ],
            "graph_search": [
                "관계",
                "연관",
                "계열사",
                "파트너",
                "공급망",
                "관련 기업",
                "업종",
            ],
        }

    async def plan(
        self, query: str, critic_feedback: str = None
    ) -> List[Dict[str, str]]:
        """지능적 쿼리 분해 및 도구 기반 계획 수립"""
        print(f"Planning 시작: {query}")

        # 1. 기본 분해
        base_queries = await self._decompose_query(query, critic_feedback)

        # 2. 도구별 최적화
        optimized_plan = await self._optimize_for_tools(base_queries, query)

        # 3. 중요도 정렬
        prioritized_plan = self._prioritize_queries(optimized_plan, query)

        print(f"최종 계획: {prioritized_plan}")
        return prioritized_plan

    async def _decompose_query(
        self, query: str, critic_feedback: str = None
    ) -> List[str]:
        """기본 쿼리 분해"""
        try:
            feedback_section = ""
            if critic_feedback:
                feedback_section = f"\n\n**이전 피드백 반영**:\n{critic_feedback}"

            prompt = f"""투자 전문가로서 다음 질문을 분석하고 필요한 정보 수집을 위해 하위 쿼리로 분해하세요.

**원본 질문**: {query}{feedback_section}

**분해 지침**:
1. 질문의 핵심 의도 파악
2. 투자 의사결정에 필요한 정보 식별
3. 각 정보 수집을 위한 구체적 쿼리 생성
4. 논리적 순서로 배치 (기본 정보 → 상세 분석)

**도구별 정보 유형**:
- **재무/실적**: 재무제표, 영업실적, 수익성 지표
- **뉴스/이슈**: 최신 동향, 경영진 발표, 이슈
- **시장/업계**: 업종 분석, 경쟁사, 시장 환경
- **관계/연관**: 계열사, 파트너십, 공급망

**출력 형식**: ["하위쿼리1", "하위쿼리2", "하위쿼리3"]

**사고 과정**:
1. 질문 분석: {query}
2. 필요 정보 식별
3. 하위 쿼리 생성
4. 논리적 순서 배치

하위 쿼리들을 생성하세요:"""

            import asyncio

            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(self.llm.chat, prompt), timeout=30.0
                )
            except asyncio.TimeoutError:
                print("쿼리 분해 타임아웃 - 기본값 사용")
                return self._fallback_decompose(query)

            # JSON 추출
            queries = self._extract_queries_from_response(response)
            return queries if queries else self._fallback_decompose(query)

        except Exception as e:
            print(f"쿼리 분해 실패: {e}")
            return self._fallback_decompose(query)

    async def _optimize_for_tools(
        self, queries: List[str], original_query: str
    ) -> List[Dict[str, str]]:
        """각 쿼리에 최적 도구 배정"""
        optimized = []

        for query in queries:
            tool = await self._select_best_tool(query, original_query)
            optimized_query = await self._optimize_query_for_tool(query, tool)

            optimized.append(
                {"query": optimized_query, "tool": tool, "original": query}
            )

        return optimized

    async def _select_best_tool(self, query: str, context: str = "") -> str:
        """쿼리에 가장 적합한 도구 선택"""
        query_lower = query.lower()

        # 패턴 매칭으로 1차 선택
        tool_scores = {}
        for tool, patterns in self.tool_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            if score > 0:
                tool_scores[tool] = score

        # 최고 점수 도구 선택
        if tool_scores:
            best_tool = max(tool_scores, key=tool_scores.get)
            print(
                f"도구 선택: '{query}' → {best_tool} (점수: {tool_scores[best_tool]})"
            )
            return best_tool

        # LLM 기반 선택 (패턴 매칭 실패시)
        try:
            prompt = f"""다음 쿼리에 가장 적합한 도구를 선택하세요.

**쿼리**: {query}
**전체 맥락**: {context}

**도구 옵션**:
1. **financial_search**: 재무제표, 실적, 공시 정보
2. **company_news**: 최신 뉴스, 발표, 이슈
3. **websearch**: 일반 분석, 시장 동향, 전망
4. **graph_search**: 기업간 관계, 연관성 분석

**선택 기준**:
- 재무 데이터가 필요하면 → financial_search
- 최신 소식이 필요하면 → company_news
- 시장 분석이 필요하면 → websearch
- 기업 관계가 필요하면 → graph_search

**응답 형식**: {{"tool": "도구명", "reason": "선택 이유"}}

도구를 선택하세요:"""

            response = self.llm.chat(prompt)

            import re, json

            json_match = re.search(r'\{[^}]*"tool"[^}]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                tool = result.get("tool", "websearch")
                print(f"LLM 도구 선택: '{query}' → {tool}")
                return tool

        except Exception as e:
            print(f"도구 선택 실패: {e}")

        # 기본값
        return "websearch"

    async def _optimize_query_for_tool(self, query: str, tool: str) -> str:
        """도구에 최적화된 쿼리로 변환"""
        tool_instructions = {
            "financial_search": "재무 데이터 중심으로 구체적인 지표나 수치 포함",
            "company_news": "최신성을 강조하고 뉴스나 이슈 중심으로 표현",
            "websearch": "시장 분석이나 전망 중심으로 표현",
            "graph_search": "기업간 관계나 연관성 중심으로 표현",
        }

        if tool in tool_instructions:
            try:
                prompt = f"""다음 쿼리를 {tool} 도구에 최적화하여 개선하세요.

**원본 쿼리**: {query}
**대상 도구**: {tool}
**최적화 방향**: {tool_instructions[tool]}

**개선 원칙**:
1. 도구의 특성에 맞는 키워드 포함
2. 구체적이고 명확한 표현 사용
3. 의미 유지하면서 효율성 향상

**출력**: 최적화된 쿼리만 반환

최적화된 쿼리:"""

                response = self.llm.chat(prompt)
                optimized = response.strip().strip("\"'")

                if optimized and len(optimized) > 5:
                    print(f"쿼리 최적화: '{query}' → '{optimized}' ({tool})")
                    return optimized

            except Exception as e:
                print(f"쿼리 최적화 실패: {e}")

        return query

    def _prioritize_queries(
        self, queries: List[Dict[str, str]], original_query: str
    ) -> List[Dict[str, str]]:
        """쿼리 우선순위 정렬"""
        # 도구별 우선순위 (투자 의사결정 중요도 기준)
        tool_priority = {
            "financial_search": 1,  # 재무 데이터가 가장 중요
            "company_news": 2,  # 최신 이슈 중요
            "graph_search": 3,  # 관계 분석
            "websearch": 4,  # 일반 분석
        }

        # 우선순위 점수 계산
        for query_info in queries:
            tool = query_info["tool"]
            query = query_info["query"].lower()

            # 기본 우선순위
            priority = tool_priority.get(tool, 5)

            # 원본 질문과의 유사도 보정
            original_lower = original_query.lower()
            similarity_bonus = 0

            # 핵심 키워드 매칭
            if any(word in query for word in original_lower.split() if len(word) > 2):
                similarity_bonus = -0.5  # 우선순위 향상

            query_info["priority"] = priority + similarity_bonus

        # 우선순위순 정렬
        sorted_queries = sorted(queries, key=lambda x: x["priority"])

        print(
            f"우선순위 정렬 완료: {[(q['tool'], q['priority']) for q in sorted_queries]}"
        )
        return sorted_queries

    def _extract_queries_from_response(self, response: str) -> List[str]:
        """응답에서 쿼리 배열 추출"""
        import re, json

        # JSON 배열 패턴
        json_pattern = r"\[(.*?)\]"
        matches = re.search(json_pattern, response, re.DOTALL)

        if matches:
            try:
                queries = json.loads(f"[{matches.group(1)}]")
                if isinstance(queries, list) and queries:
                    return [
                        q for q in queries if isinstance(q, str) and len(q.strip()) > 5
                    ]
            except json.JSONDecodeError:
                pass

        # 텍스트에서 따옴표 추출
        quote_pattern = r'"([^"]{10,})"'
        quotes = re.findall(quote_pattern, response)
        if quotes:
            return quotes[:4]  # 최대 4개

        # 줄 단위 추출
        lines = [line.strip() for line in response.split("\n")]
        queries = []
        for line in lines:
            if line and not line.startswith("#") and len(line) > 10:
                # 번호나 기호 제거
                clean_line = re.sub(r"^[\d\.\-\*\+\s]+", "", line).strip()
                if clean_line and len(clean_line) > 5:
                    queries.append(clean_line)

        return queries[:4] if queries else []

    def _fallback_decompose(self, query: str) -> List[str]:
        """기본 분해 로직 (LLM 실패시)"""
        query_lower = query.lower()

        # 기업명 추출 시도
        company_patterns = ["삼성", "lg", "sk", "현대", "포스코", "네이버", "카카오"]
        company = None
        for pattern in company_patterns:
            if pattern in query_lower:
                company = pattern
                break

        queries = []

        if company:
            # 기업 특화 분해
            if any(word in query_lower for word in ["실적", "재무", "수익"]):
                queries.append(f"{company} 최근 분기 실적 및 재무 현황")
            if any(word in query_lower for word in ["뉴스", "소식", "발표"]):
                queries.append(f"{company} 최신 뉴스 및 주요 이슈")
            if any(word in query_lower for word in ["전망", "분석", "목표"]):
                queries.append(f"{company} 투자 전망 및 분석가 의견")
        else:
            # 일반적 분해
            queries = [
                "주요 기업 실적 및 재무 현황",
                "시장 동향 및 업계 분석",
                "투자 환경 및 전망",
            ]

        return queries[:3]


class RetrieverAgent:
    def __init__(self, tools: Dict[str, Any] = None, llm=None):
        self.llm = llm or ClovaXLLM()
        self.graph_rag = GraphRAGProcessor()

        # 새로운 통합 도구들 추가
        self.financial_search = search_financial_documents
        self.company_news_search = search_company_news
        self.related_companies_search = find_related_companies
        self.market_trends = get_market_trends
        self.graph_stats = get_graph_statistics
        self.get_companies = get_available_companies
        self.get_doc_types = get_document_types

        # 레거시 도구들 (하위 호환성)
        self.tools = tools or {
            "graphdb": GraphQueryTool(),
            "vectordb": VectorQueryTool(),
            "sqlite": SQLiteTool(),
            "websearch": WebSearchTool(),
            "playwright": PlaywrightTool(),
        }

    async def retrieve(self, query_plan: List[Dict[str, str]]) -> Dict[str, Any]:
        """향상된 계획 기반 정보 검색"""
        print(f"정보 검색 시작: {len(query_plan)}개 쿼리")

        all_results = {
            "financial_data": [],
            "news_data": [],
            "market_analysis": [],
            "graph_data": [],
            "metadata": {
                "total_queries": len(query_plan),
                "successful_queries": 0,
                "failed_queries": 0,
                "tools_used": set(),
            },
        }

        # 병렬 처리를 위한 태스크들
        import asyncio

        tasks = []

        for i, query_info in enumerate(query_plan):
            task = asyncio.create_task(self._execute_single_query(query_info, i))
            tasks.append(task)

        # 모든 쿼리 병렬 실행
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 결과 분류 및 집계
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"쿼리 {i} 실행 실패: {result}")
                    all_results["metadata"]["failed_queries"] += 1
                else:
                    self._categorize_result(result, all_results)
                    all_results["metadata"]["successful_queries"] += 1
                    all_results["metadata"]["tools_used"].add(
                        result.get("tool", "unknown")
                    )

        except Exception as e:
            print(f"병렬 검색 실패: {e}")
            # 순차 실행으로 폴백
            for query_info in query_plan:
                try:
                    result = await self._execute_single_query(query_info, 0)
                    self._categorize_result(result, all_results)
                    all_results["metadata"]["successful_queries"] += 1
                except Exception as ex:
                    print(f"순차 검색 실패: {ex}")
                    all_results["metadata"]["failed_queries"] += 1

        all_results["metadata"]["tools_used"] = list(
            all_results["metadata"]["tools_used"]
        )

        print(
            f"검색 완료: 성공 {all_results['metadata']['successful_queries']}, 실패 {all_results['metadata']['failed_queries']}"
        )
        return all_results

    async def _execute_single_query(
        self, query_info: Dict[str, str], index: int
    ) -> Dict[str, Any]:
        """단일 쿼리 실행"""
        query = query_info["query"]
        tool = query_info["tool"]

        print(f"쿼리 {index} 실행: {tool} - {query[:50]}...")

        try:
            # 도구별 실행
            if tool == "financial_search":
                result = await self._search_financial(query)
            elif tool == "company_news":
                result = await self._search_news(query)
            elif tool == "websearch":
                result = await self._search_web(query)
            elif tool == "graph_search":
                result = await self._search_graph(query)
            else:
                result = await self._search_web(query)  # 기본값

            return {
                "tool": tool,
                "query": query,
                "original": query_info.get("original", query),
                "data": result,
                "success": True,
                "index": index,
            }

        except Exception as e:
            print(f"쿼리 실행 실패 ({tool}): {e}")
            return {
                "tool": tool,
                "query": query,
                "data": f"검색 실패: {str(e)}",
                "success": False,
                "index": index,
            }

    async def _search_financial(self, query: str) -> Dict[str, Any]:
        """재무 데이터 검색"""
        try:
            # 기업명 추출
            company = await self._extract_company_name(query)

            if company:
                # 특정 기업 재무 검색
                financial_docs = self.financial_search(
                    query=query, company_filter=company, limit=10
                )

                return {
                    "type": "financial",
                    "company": company,
                    "documents": financial_docs,
                    "query": query,
                }
            else:
                # 일반 재무 검색
                financial_docs = self.financial_search(query=query, limit=5)
                return {
                    "type": "financial",
                    "documents": financial_docs,
                    "query": query,
                }

        except Exception as e:
            print(f"재무 검색 실패: {e}")
            return {"type": "financial", "error": str(e), "query": query}

    async def _search_news(self, query: str) -> Dict[str, Any]:
        """뉴스 검색"""
        try:
            # 기업명 추출
            company = await self._extract_company_name(query)

            if company:
                news_docs = self.company_news_search(
                    query=query, company_filter=company, limit=8
                )
            else:
                news_docs = self.company_news_search(query=query, limit=5)

            return {
                "type": "news",
                "company": company,
                "articles": news_docs,
                "query": query,
            }

        except Exception as e:
            print(f"뉴스 검색 실패: {e}")
            return {"type": "news", "error": str(e), "query": query}

    async def _search_web(self, query: str) -> Dict[str, Any]:
        """웹 검색"""
        try:
            web_tool = self.tools["websearch"]
            web_results = web_tool.search(query)

            return {"type": "web", "results": web_results, "query": query}

        except Exception as e:
            print(f"웹 검색 실패: {e}")
            return {"type": "web", "error": str(e), "query": query}

    async def _search_graph(self, query: str) -> Dict[str, Any]:
        """그래프 검색"""
        try:
            # 기업명 추출
            company = await self._extract_company_name(query)

            if company:
                # 관련 기업 검색
                related_companies = self.related_companies_search(
                    company=company,
                    relation_types=["계열사", "협력사", "공급업체"],
                    limit=10,
                )

                # 그래프 컨텍스트
                graph_context = self.graph_rag.query_with_graph_context(query)

                return {
                    "type": "graph",
                    "company": company,
                    "related_companies": related_companies,
                    "graph_context": graph_context,
                    "query": query,
                }
            else:
                # 일반 그래프 검색
                graph_context = self.graph_rag.query_with_graph_context(query)
                return {"type": "graph", "graph_context": graph_context, "query": query}

        except Exception as e:
            print(f"그래프 검색 실패: {e}")
            return {"type": "graph", "error": str(e), "query": query}

    async def _extract_company_name(self, query: str) -> str:
        """쿼리에서 기업명 추출"""
        try:
            prompt = f"""다음 텍스트에서 기업명을 추출하세요. 정확한 기업명만 반환하고, 확실하지 않으면 빈 문자열을 반환하세요.

**텍스트**: {query}

**추출 규칙**:
1. 정확한 기업명만 추출 (예: 삼성전자, LG전자, 현대자동차)
2. 업종명이나 일반명사는 제외
3. 확실하지 않으면 빈 문자열 반환

**응답 형식**: {{"company": "기업명", "confidence": "높음/낮음"}}

기업명을 추출하세요:"""

            response = self.llm.chat(prompt)

            import re, json

            json_match = re.search(r'\{[^}]*"company"[^}]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                company = result.get("company", "").strip()
                confidence = result.get("confidence", "낮음")

                if company and confidence == "높음":
                    return company

            # 패턴 매칭 폴백
            company_patterns = {
                "삼성": "삼성전자",
                "lg": "LG전자",
                "현대차": "현대자동차",
                "포스코": "포스코",
                "네이버": "네이버",
                "카카오": "카카오",
            }

            query_lower = query.lower()
            for pattern, company in company_patterns.items():
                if pattern in query_lower:
                    return company

            return ""

        except Exception as e:
            print(f"기업명 추출 실패: {e}")
            return ""

    def _categorize_result(self, result: Dict[str, Any], all_results: Dict[str, Any]):
        """결과를 카테고리별로 분류"""
        if not result.get("success", False):
            return

        data = result.get("data", {})
        tool = result.get("tool", "unknown")

        if tool == "financial_search":
            all_results["financial_data"].append(data)
        elif tool == "company_news":
            all_results["news_data"].append(data)
        elif tool == "graph_search":
            all_results["graph_data"].append(data)
        else:  # websearch 등
            all_results["market_analysis"].append(data)

    # 레거시 메소드 (하위 호환성)
    def retrieve(self, sub_queries: List[str]) -> List[Dict]:
        """LLM을 사용한 지능적 정보 검색"""
        results = []
        for q in sub_queries:
            prompt = f"""당신은 정보 검색 전문가입니다. 주어진 투자 관련 쿼리에 대해 최적의 정보 수집 도구를 선택하고 그 이유를 설명해주세요.

**역할**: 정보 검색 전략 전문가
**목표**: 쿼리에 가장 적합한 도구 선택 및 실행 계획 수립

**분석 대상 쿼리**: "{q}"

**사용 가능한 도구들**:
1. **financial_search**: DART 공시 정보 및 재무 데이터 검색 (Elasticsearch 기반)
   - 적합한 경우: 기업 재무제표, 공시 정보, 실적 데이터, 기업 기본 정보
   - 데이터 특성: 공식적, 정확한 재무 데이터, 과거 실적

2. **company_news**: 기업별 최신 뉴스 검색 (Graph RAG)
   - 적합한 경우: 특정 기업의 최신 동향, 뉴스, 이슈, 최근 발표사항
   - 데이터 특성: 실시간성, 시장 반응, 경영진 발언

3. **related_companies**: 관련 기업 및 경쟁사 검색 (Graph RAG)
   - 적합한 경우: 경쟁사 분석, 업계 생태계, 파트너사, 계열사 정보
   - 데이터 특성: 관계형 데이터, 업계 구조

4. **market_trends**: 시장 트렌드 및 산업 분석 (Graph RAG)
   - 적합한 경우: 업종별 동향, 시장 전망, 산업 이슈, 거시경제 영향
   - 데이터 특성: 트렌드 분석, 미래 전망

5. **websearch**: 실시간 웹 검색
   - 적합한 경우: 최신 주가 정보, 실시간 뉴스, 시장 반응, 속보성 정보
   - 데이터 특성: 실시간성, 다양한 출처

**분석 과정**:
1. **쿼리 의도 분석**: 어떤 종류의 정보를 찾고 있는가?
2. **정보 특성 파악**: 실시간성이 중요한가? 공식적 데이터가 필요한가?
3. **최적 도구 매칭**: 쿼리 특성과 도구 특성의 최적 조합 찾기
4. **대안 도구 고려**: 1차 도구 실패 시 백업 전략

**응답 형식**: {{"tool": "도구명", "reason": "상세한 선택 이유와 기대 결과"}}

분석을 시작하세요:"""

            try:
                # 도구 선택을 위한 LLM 호출
                response = self.llm.chat(prompt)

                # JSON 파싱
                import re
                import json

                json_pattern = r'\{[^}]*"tool"[^}]*\}'
                matches = re.search(json_pattern, response)
                if matches:
                    plan = json.loads(matches.group())
                    tool_name = plan.get("tool", "financial_search")
                    reason = plan.get("reason", "")

                    # 도구 실행
                    if tool_name == "financial_search":
                        result = self.financial_search(q)
                    elif tool_name == "company_news":
                        company_name = self._extract_company_name_llm(q)
                        result = (
                            self.company_news_search(company_name)
                            if company_name
                            else "기업명을 찾을 수 없습니다."
                        )
                    elif tool_name == "related_companies":
                        company_name = self._extract_company_name_llm(q)
                        result = (
                            self.related_companies_search(company_name)
                            if company_name
                            else "기업명을 찾을 수 없습니다."
                        )
                    elif tool_name == "market_trends":
                        result = self.market_trends()
                    elif tool_name == "websearch":
                        print(f"🔍 웹 검색 실행: {q}")
                        if "websearch" in self.tools:
                            print(f"📡 WebSearchTool로 검색 중...")
                            result = self.tools["websearch"].search(q)
                            print(f"✅ 웹 검색 완료: {str(result)[:200]}...")
                        else:
                            print(f"❌ WebSearchTool 없음 - 더미 결과 반환")
                            result = f"웹 검색: {q}"
                    else:
                        # 레거시 도구들
                        if tool_name in self.tools:
                            if hasattr(self.tools[tool_name], "search"):
                                result = self.tools[tool_name].search(q)
                            elif hasattr(self.tools[tool_name], "query"):
                                result = self.tools[tool_name].query(q)
                            elif hasattr(self.tools[tool_name], "crawl"):
                                result = self.tools[tool_name].crawl(q)
                            else:
                                result = f"{tool_name} 도구 실행: {q}"
                        else:
                            result = f"알 수 없는 도구: {tool_name}"

                    results.append(
                        {
                            "query": q,
                            "result": result,
                            "tool": tool_name,
                            "reason": reason,
                        }
                    )
                    continue

            except Exception as e:
                print(f"도구 실행 실패: {e}")

            # 실패 시 기본적으로 websearch 사용
            print(f"🔄 폴백: 웹 검색 실행 - {q}")
            if "websearch" in self.tools:
                result = self.tools["websearch"].search(q)
                print(f"✅ 폴백 웹 검색 완료: {str(result)[:200]}...")
            else:
                result = f"웹 검색 도구 없음: {q}"
                print(f"❌ 웹 검색 도구 없음")

            results.append(
                {
                    "query": q,
                    "result": result,
                    "tool": "websearch",
                    "reason": "도구 선택 실패로 인한 웹 검색 폴백",
                }
            )

        return results

    def _extract_company_name_llm(self, query: str) -> str:
        """LLM을 사용한 기업명 추출"""
        prompt = f"""당신은 텍스트 분석 전문가입니다. 주어진 쿼리에서 한국 기업명을 정확히 추출해주세요.

**역할**: 기업명 추출 전문가
**목표**: 쿼리에서 정확한 한국 기업명 식별

**분석 대상**: "{query}"

**추출 원칙**:
1. 완전한 기업명 우선 (예: "삼성전자", "LG화학")
2. 약어나 별명보다는 정식 명칭
3. 그룹명이 아닌 개별 기업명 (예: "삼성" → "삼성전자")
4. 존재하지 않는 기업명은 반환하지 않음

**주요 한국 기업 예시**:
- 삼성전자, LG전자, SK하이닉스, 현대자동차, 포스코
- NAVER, 카카오, 셀트리온, 현대중공업, 한국전력
- KT, LG화학, 아모레퍼시픽, LG생활건강

**응답 형식**: {{"company": "기업명" 또는 "", "confidence": "높음/보통/낮음"}}

분석을 시작하세요:"""

        try:
            response = self.llm.chat(prompt)
            import re
            import json

            json_pattern = r'\{[^}]*"company"[^}]*\}'
            matches = re.search(json_pattern, response)

            if matches:
                result = json.loads(matches.group())
                company = result.get("company", "")
                confidence = result.get("confidence", "낮음")

                if company and confidence in ["높음", "보통"]:
                    return company

            # JSON 파싱 실패 시 기본 패턴 매칭
            companies = [
                "삼성전자",
                "LG전자",
                "SK하이닉스",
                "현대자동차",
                "포스코",
                "NAVER",
                "카카오",
                "셀트리온",
                "현대중공업",
                "한국전력",
                "KT",
                "LG화학",
                "아모레퍼시픽",
                "LG생활건강",
            ]

            for company in companies:
                if company in query:
                    return company

            return ""

        except Exception as e:
            print(f"기업명 추출 실패: {e}")
            return ""


# CriticAgent1
class CriticAgent1:
    def __init__(self, llm=None):
        self.llm = llm or ClovaXLLM()

    async def evaluate(
        self, retrieved_results: Dict[str, Any], original_query: str
    ) -> Dict:
        """향상된 정보 평가 - 구조화된 데이터 기반"""
        print(f"Evaluating structured results for: {original_query}")

        # 데이터 요약 생성
        data_summary = self._summarize_retrieved_data(retrieved_results)

        prompt = f"""당신은 투자 정보 평가 전문가입니다. 수집된 정보가 투자자의 질문에 충분한 답변을 제공할 수 있는지 평가하세요.

**역할**: 투자 정보 충족도 평가 전문가
**목표**: 투자 의사결정에 필요한 정보의 완성도 판단

**원본 투자자 질문**: "{original_query}"

**수집된 정보 요약**:
{data_summary}

**검색 메타데이터**:
- 총 쿼리 수: {retrieved_results['metadata']['total_queries']}
- 성공한 검색: {retrieved_results['metadata']['successful_queries']}
- 실패한 검색: {retrieved_results['metadata']['failed_queries']}
- 사용된 도구: {', '.join(retrieved_results['metadata']['tools_used'])}

**평가 기준**:
1. **정보 완성도**: 질문에 답하기 위한 핵심 정보가 충분한가?
2. **정보 다양성**: 여러 관점(재무, 뉴스, 시장 분석)의 정보가 균형있게 수집되었는가?
3. **정보 품질**: 수집된 정보가 신뢰할 만하고 관련성이 높은가?
4. **최신성**: 투자 판단에 필요한 최신 정보가 포함되어 있는가?

**판단 기준**:
- **충분**: 투자 의사결정에 필요한 핵심 정보가 모두 포함되고 품질이 우수함
- **불충분**: 중요한 정보가 누락되었거나 정보의 품질이 미흡하여 추가 수집 필요

**응답 형식**: {{"sufficiency": true/false, "feedback": "구체적인 평가 내용 및 개선 방향", "missing_areas": ["부족한 영역1", "부족한 영역2"]}}

**피드백 작성 지침**:
- 불충분한 경우: 구체적으로 어떤 정보가 더 필요한지 명시하고 추가 검색 방향 제시
- 충분한 경우: 수집된 정보의 강점과 투자 판단에 도움이 되는 부분 요약

평가를 시작하세요:"""

        try:
            import asyncio

            response = await asyncio.to_thread(self.llm.chat, prompt)
            import re, json

            json_pattern = r'\{[^}]*"sufficiency"[^}]*\}'
            matches = re.search(json_pattern, response)

            if matches:
                result = json.loads(matches.group())
                if isinstance(result, dict) and "sufficiency" in result:
                    return result

            # JSON 파싱 실패 시 텍스트 분석
            response_lower = response.lower()
            if any(
                word in response_lower
                for word in ["불충분", "부족", "insufficient", "부족하"]
            ):
                sufficiency = False
                feedback = "수집된 정보가 투자 의사결정에 부족합니다. 추가 정보 수집이 필요합니다."
            else:
                sufficiency = True
                feedback = "수집된 정보가 투자 의사결정에 충분합니다."

            return {
                "sufficiency": sufficiency,
                "feedback": feedback,
                "missing_areas": [] if sufficiency else ["추가 분석 필요"],
            }

        except Exception as e:
            print(f"정보 평가 실패: {e}")
            # 안전한 기본값 (충분함으로 처리)
            return {
                "sufficiency": True,
                "feedback": "정보 평가 중 오류가 발생했지만, 수집된 정보로 진행합니다.",
                "missing_areas": [],
            }

    def _summarize_retrieved_data(self, retrieved_results: Dict[str, Any]) -> str:
        """수집된 데이터 요약"""
        summary_parts = []

        # 재무 데이터 요약
        if retrieved_results["financial_data"]:
            financial_count = len(retrieved_results["financial_data"])
            summary_parts.append(f"📊 재무 정보: {financial_count}개 문서 수집")
            for data in retrieved_results["financial_data"][:2]:  # 최대 2개만
                if "company" in data:
                    summary_parts.append(f"  - {data['company']} 관련 재무 데이터")

        # 뉴스 데이터 요약
        if retrieved_results["news_data"]:
            news_count = len(retrieved_results["news_data"])
            summary_parts.append(f"📰 뉴스 정보: {news_count}개 기사 수집")
            for data in retrieved_results["news_data"][:2]:  # 최대 2개만
                if "company" in data:
                    summary_parts.append(f"  - {data['company']} 관련 최신 뉴스")

        # 시장 분석 요약
        if retrieved_results["market_analysis"]:
            market_count = len(retrieved_results["market_analysis"])
            summary_parts.append(f"📈 시장 분석: {market_count}개 분석 자료")

        # 그래프 데이터 요약
        if retrieved_results["graph_data"]:
            graph_count = len(retrieved_results["graph_data"])
            summary_parts.append(f"🔗 관계 분석: {graph_count}개 관계 정보")

        return "\n".join(summary_parts) if summary_parts else "수집된 정보 없음"

    # 레거시 메소드 (하위 호환성)
    def evaluate(self, retrieved: List[Dict], original_query: str) -> Dict:
        print(f"Evaluating: {original_query}")

        prompt = f"""당신은 정보 평가 전문가입니다. 투자자의 질문에 대해 수집된 정보가 충분한지 엄격하게 평가해주세요.

**역할**: 정보 충족도 평가 전문가
**목표**: 투자 의사결정에 필요한 정보의 완성도 판단
**평가 기준**: 정확성, 완성도, 최신성, 관련성

**원본 투자자 질문**: "{original_query}"

**수집된 정보**:
{json.dumps(retrieved, ensure_ascii=False, indent=2)}

**평가 과정**:
1. **질문 요구사항 분석**: 투자자가 의사결정하기 위해 필요한 핵심 정보는 무엇인가?
2. **정보 커버리지 검토**: 수집된 정보가 핵심 요구사항을 얼마나 충족하는가?
3. **정보 품질 평가**: 수집된 정보의 신뢰성과 최신성은 어떤가?
4. **누락 정보 식별**: 투자 판단에 필요하지만 부족한 정보는 무엇인가?

**평가 기준**:
- **충분함**: 투자 의사결정에 필요한 핵심 정보가 모두 포함되고 품질이 우수함
- **불충분함**: 중요한 정보가 누락되었거나 정보의 품질이 미흡하여 추가 수집 필요

**응답 형식**: {{"sufficiency": true/false, "feedback": "구체적인 평가 내용 및 개선 방향"}}

**피드백 작성 지침**:
- 부족한 경우: 구체적으로 어떤 정보가 더 필요한지 명시
- 충분한 경우: 수집된 정보의 강점과 투자 판단에 도움이 되는 부분 요약

평가를 시작하세요:"""

        try:
            response = self.llm.chat(prompt)
            import re

            json_pattern = r'\{[^}]*"sufficiency"[^}]*\}'
            matches = re.search(json_pattern, response)

            if matches:
                result = json.loads(matches.group())
                if isinstance(result, dict) and "sufficiency" in result:
                    return result

            # JSON 파싱 실패 시 텍스트 분석
            response_lower = response.lower()
            if (
                "불충분" in response_lower
                or "부족" in response_lower
                or "insufficient" in response_lower
            ):
                sufficiency = False
            else:
                sufficiency = True

            return {"sufficiency": sufficiency, "feedback": "정보 평가를 완료했습니다."}

        except Exception as e:
            print(f"크리틱 평가 실패: {e}")
            return {
                "sufficiency": True,
                "feedback": f"평가 중 오류가 발생했습니다: {str(e)}",
            }


class ContextIntegratorAgent:
    def __init__(self, llm=None):
        self.llm = llm or ClovaXLLM()
        self.graph_rag = GraphRAGProcessor()

    def integrate(self, retrieved: List[Dict], user_context: Dict = None) -> str:
        """수집된 정보를 통합하여 구조화된 컨텍스트 생성"""

        # Graph RAG 컨텍스트 추출
        graph_contexts = []
        for item in retrieved:
            if item.get("tool") == "graphdb" and "graph_context" in item.get(
                "result", {}
            ):
                graph_contexts.append(item["result"]["graph_context"])

        # 그래프 컨텍스트 통합
        integrated_graph_context = ""
        if graph_contexts:
            all_entities = []
            all_relationships = []
            all_neighbors = []

            for ctx in graph_contexts:
                all_entities.extend(ctx.get("extracted_entities", []))
                all_relationships.extend(ctx.get("relationships", []))
                all_neighbors.extend(ctx.get("neighbors", []))

            # 중복 제거
            unique_entities = list(set(all_entities))
            unique_relationships = {
                f"{r.get('source', '')}-{r.get('relationship', '')}-{r.get('target', '')}": r
                for r in all_relationships
            }.values()

            if unique_entities or unique_relationships:
                integrated_graph_context = f"""
## 그래프 컨텍스트
- **핵심 엔티티**: {', '.join(unique_entities[:10])}
- **주요 관계**: {'; '.join([f"{r.get('source', '')} -[{r.get('relationship', '')}]-> {r.get('target', '')}" for r in list(unique_relationships)[:5]])}
- **연관 엔티티**: {', '.join([n.get('name', '') for n in all_neighbors[:8]])}
"""

        prompt = f"""
수집된 정보를 분석하고 통합하여 구조화된 투자 컨텍스트를 생성하세요.

{integrated_graph_context}

[수집된 정보]
{json.dumps(retrieved, ensure_ascii=False, indent=2)}

[사용자 정보]
{json.dumps(user_context, ensure_ascii=False, indent=2) if user_context else "사용자 정보 없음"}

[지시사항]
1. 수집된 정보를 주제별로 분류하고 구조화하세요:
   - 기업/산업 분석 (그래프 관계 포함)
   - 시장 동향
   - 재무/실적
   - 투자자 동향
   - 리스크 요인

2. 다음 요소들을 반드시 포함하세요:
   - 구체적인 수치 데이터
   - 정보의 출처와 시점
   - 엔티티 간 관계 분석
   - 신뢰도 평가

3. 그래프 데이터를 활용하여:
   - 엔티티 간 연관성 분석
   - 산업 생태계 관계 파악
   - 경쟁/협력 구조 이해

[응답]
투자 컨텍스트를 마크다운 형식으로 작성하세요.
"""
        try:
            return self.llm.chat(prompt)
        except Exception as e:
            print(f"컨텍스트 통합 실패: {e}")
            return (
                f"컨텍스트 통합 중 오류가 발생했습니다.\n\n{integrated_graph_context}"
            )


# ReportGeneratorAgent
class ReportGeneratorAgent:
    def __init__(self, llm=None):
        self.llm = llm or ClovaXLLM()

    def generate(self, context: str, user_context: Dict = None) -> str:
        print(f"Generating report")
        current_time = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")

        user_info = ""
        if user_context:
            user_info = f"""
**투자자 프로필**:
- 투자 성향: {user_context.get('risk_tolerance', '정보 없음')}
- 투자 목표: {user_context.get('investment_goal', '정보 없음')}
- 투자 경험: {user_context.get('experience_level', '정보 없음')}
- 관심 분야: {user_context.get('preferred_sectors', '정보 없음')}
"""

        prompt = f"""당신은 경험이 풍부한 투자 분석가이자 리포트 작성 전문가입니다. 수집된 정보를 바탕으로 투자자에게 도움이 되는 전문적인 투자 인사이트를 작성해주세요.

**역할**: 시니어 투자 분석가 & 리포트 작성 전문가
**목표**: 투자자의 의사결정을 돕는 실용적이고 전문적인 인사이트 제공
**전문 영역**: 기업 분석, 시장 동향, 투자 전략, 리스크 관리

**현재 시각**: {current_time}
{user_info}

**분석 자료**:
{context}

**리포트 작성 과정**:
1. **핵심 정보 추출**: 투자 의사결정에 가장 중요한 정보 식별
2. **트렌드 분석**: 시장 동향과 기업 상황의 연관성 파악
3. **기회와 위험 평가**: 투자 기회와 리스크 요인 균형적 분석
4. **실행 가능한 인사이트**: 구체적이고 실용적인 투자 조언 제공

**리포트 구성 원칙**:
- 투자자가 이해하기 쉬운 명확한 언어 사용
- 데이터 기반의 객관적 분석
- 균형잡힌 시각 (기회와 위험 모두 제시)
- 실행 가능한 구체적 제안
- 적절한 면책 조항 포함

**응답 형식**: 마크다운 형식의 전문 투자 리포트
- 이모지 사용 금지
- 구조화된 섹션 구성
- 핵심 포인트 강조 표시
- 표나 리스트 적극 활용

리포트 작성을 시작하세요:"""

        try:
            return self.llm.chat(prompt)
        except Exception as e:
            print(f"인사이트 생성 실패: {e}")
            return f"""# 투자 인사이트 리포트

## 분석 요약

현재 시점({current_time})에서의 분석을 완료했습니다.

### 주요 발견사항
- 시장 상황을 종합적으로 검토했습니다
- 관련 기업들의 현황을 파악했습니다
- 투자 기회와 리스크를 평가했습니다

### 투자 제안
- 신중한 접근을 권장합니다
- 충분한 정보 수집 후 의사결정하시기 바랍니다
- 전문가와의 상담을 고려해보세요

### 면책조항
본 분석은 참고용이며, 투자에는 원금 손실 위험이 있습니다. 실제 투자 결정 시에는 전문가와 상담하시기 바랍니다."""
