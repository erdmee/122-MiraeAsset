import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import re
from dataclasses import dataclass

# 상대 import 수정
try:
    from app.graph.neo4j_graph_tool import Neo4jGraphTool
    from app.graph.entity_extractor import FinancialEntityExtractor
    from app.services.tools.elasticsearch_vector_tool import ElasticsearchVectorTool
except ImportError:
    # 테스트용 더미 클래스들
    class Neo4jGraphTool:
        def add_entities(self, entities): return True
        def add_relationships(self, relationships): return True

    class FinancialEntityExtractor:
        def extract_entities_from_text(self, text, doc_id): return [], []
        def process_document(self, doc_id, content, doc_type): return True

    class ElasticsearchVectorTool:
        def insert(self, docs): return True

logger = logging.getLogger(__name__)

@dataclass
class DARTDocument:
    """DART 문서 데이터 클래스"""
    corp_name: str
    corp_code: str
    report_name: str
    rcept_no: str
    flr_name: str
    rcept_dt: str
    rm: str
    content: str = ""
    url: str = ""

class DARTDataProcessor:
    """DART 공시 데이터를 Neo4j + Elasticsearch에 처리하는 클래스"""

    def __init__(self):
        self.graph_tool = Neo4jGraphTool()
        self.entity_extractor = FinancialEntityExtractor(use_llm=True)
        self.vector_tool = ElasticsearchVectorTool(index_name="dart_documents")

        # 공시 유형별 분류
        self.disclosure_types = {
            "사업보고서": "annual_report",
            "반기보고서": "semi_annual_report",
            "분기보고서": "quarterly_report",
            "투자설명서": "prospectus",
            "공정공시": "fair_disclosure",
            "주요사항보고서": "major_disclosure",
            "합병": "merger",
            "분할": "split",
            "영업양수도": "business_transfer"
        }

        # 중요 키워드 패턴
        self.important_patterns = {
            "투자": r'(투자|출자|지분|인수|매수).*?([0-9,]+(?:억|조)원?)',
            "매출": r'(매출|수익|영업수익).*?([0-9,]+(?:억|조)원?)',
            "이익": r'(영업이익|순이익|당기순이익).*?([0-9,]+(?:억|조)원?)',
            "계약": r'(계약|협약|MOU|양해각서).*?([가-힣A-Za-z]+(?:주식회사|㈜|\(주\))?)',
            "인사": r'(대표이사|사장|회장|부사장).*?([가-힣]{2,4})'
        }

    def classify_disclosure_type(self, report_name: str) -> str:
        """공시 유형 분류"""
        for keyword, category in self.disclosure_types.items():
            if keyword in report_name:
                return category
        return "general_disclosure"

    def extract_key_information(self, content: str) -> Dict[str, List[str]]:
        """공시 내용에서 핵심 정보 추출"""
        key_info = {}

        for info_type, pattern in self.important_patterns.items():
            matches = re.findall(pattern, content)
            if matches:
                key_info[info_type] = [f"{match[0]} {match[1]}" if len(match) > 1 else str(match) for match in matches]

        return key_info

    def create_vector_document(self, dart_doc: DARTDocument, key_info: Dict) -> Dict:
        """Elasticsearch용 벡터 문서 생성"""
        # 요약 생성 (첫 500자 + 핵심 정보)
        summary_parts = [dart_doc.content[:500]]

        for info_type, items in key_info.items():
            if items:
                summary_parts.append(f"{info_type}: {', '.join(items[:3])}")

        summary = " | ".join(summary_parts)

        # 더미 벡터 생성 (실제로는 sentence-transformers 사용)
        import random
        vector = [random.uniform(-1, 1) for _ in range(768)]

        return {
            "doc_id": dart_doc.rcept_no,
            "text": dart_doc.content,
            "title": f"{dart_doc.corp_name} - {dart_doc.report_name}",
            "summary": summary,
            "embedding": vector,
            "meta": {
                "source": "dart",
                "company": dart_doc.corp_name,
                "corp_code": dart_doc.corp_code,
                "disclosure_type": self.classify_disclosure_type(dart_doc.report_name),
                "report_date": dart_doc.rcept_dt,
                "reporter": dart_doc.flr_name,
                "category": "disclosure",
                "url": dart_doc.url,
                "key_info": key_info
            },
            "doc_type": "dart_disclosure",
            "date": dart_doc.rcept_dt,
            "timestamp": datetime.now().isoformat()
        }

    async def process_dart_document(self, dart_doc: DARTDocument) -> bool:
        """개별 DART 문서 처리"""
        try:
            logger.info(f"DART 문서 처리 시작: {dart_doc.corp_name} - {dart_doc.report_name}")

            # 1. 핵심 정보 추출
            key_info = self.extract_key_information(dart_doc.content)

            # 2. 엔티티/관계 추출 및 그래프 저장
            entities, relationships = self.entity_extractor.extract_entities_from_text(
                dart_doc.content,
                doc_id=dart_doc.rcept_no
            )

            # 회사명 엔티티 추가 (확실하게)
            from app.graph.neo4j_graph_tool import Entity
            company_entity = Entity(
                name=dart_doc.corp_name,
                type="COMPANY",
                properties={
                    "corp_code": dart_doc.corp_code,
                    "source": "dart",
                    "disclosure_count": 1
                }
            )
            entities.append(company_entity)

            # Neo4j에 저장
            if entities:
                success = self.graph_tool.add_entities(entities)
                if not success:
                    logger.warning(f"엔티티 저장 실패: {dart_doc.rcept_no}")

            if relationships:
                success = self.graph_tool.add_relationships(relationships)
                if not success:
                    logger.warning(f"관계 저장 실패: {dart_doc.rcept_no}")

            # 문서-엔티티 관계 추가
            entity_names = [e.name for e in entities]
            self.graph_tool.add_document_relations(
                doc_id=dart_doc.rcept_no,
                doc_type="dart_disclosure",
                entities=entity_names,
                content=dart_doc.content[:1000]
            )

            # 3. Elasticsearch 벡터 문서 생성 및 저장
            vector_doc = self.create_vector_document(dart_doc, key_info)
            success = self.vector_tool.insert([vector_doc])

            if success:
                logger.info(f"DART 문서 처리 완료: {dart_doc.corp_name}")
                return True
            else:
                logger.error(f"벡터 저장 실패: {dart_doc.rcept_no}")
                return False

        except Exception as e:
            logger.error(f"DART 문서 처리 실패: {dart_doc.corp_name}, {e}")
            return False

    async def process_dart_dataframe(self, df: pd.DataFrame, content_column: str = "content") -> Dict[str, Any]:
        """DART DataFrame 배치 처리"""
        try:
            logger.info(f"DART DataFrame 처리 시작: {len(df)}개 문서")

            results = {"success": 0, "failed": 0, "errors": []}

            for idx, row in df.iterrows():
                try:
                    # DataFrame 행을 DARTDocument로 변환
                    dart_doc = DARTDocument(
                        corp_name=row.get("corp_name", ""),
                        corp_code=row.get("corp_code", ""),
                        report_name=row.get("report_nm", ""),
                        rcept_no=row.get("rcept_no", f"doc_{idx}"),
                        flr_name=row.get("flr_nm", ""),
                        rcept_dt=row.get("rcept_dt", ""),
                        rm=row.get("rm", ""),
                        content=row.get(content_column, ""),
                        url=row.get("url", "")
                    )

                    # 내용이 있는 경우만 처리
                    if dart_doc.content and len(dart_doc.content.strip()) > 100:
                        success = await self.process_dart_document(dart_doc)
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                    else:
                        logger.warning(f"내용이 부족한 문서 건너뜀: {dart_doc.corp_name}")
                        results["failed"] += 1

                except Exception as e:
                    logger.error(f"행 {idx} 처리 실패: {e}")
                    results["failed"] += 1
                    results["errors"].append(f"행 {idx}: {str(e)}")

                # 진행 상황 로그 (100개마다)
                if (idx + 1) % 100 == 0:
                    logger.info(f"진행 상황: {idx + 1}/{len(df)} 처리됨")

            logger.info(f"DART DataFrame 처리 완료: 성공 {results['success']}개, 실패 {results['failed']}개")
            return results

        except Exception as e:
            logger.error(f"DataFrame 처리 중 오류: {e}")
            return {"success": 0, "failed": len(df), "errors": [str(e)]}

    def load_dart_csv(self, csv_path: str) -> pd.DataFrame:
        """CSV 파일에서 DART 데이터 로드"""
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"CSV 로드 완료: {len(df)}개 행, 컬럼: {list(df.columns)}")
            return df
        except Exception as e:
            logger.error(f"CSV 로드 실패: {e}")
            return pd.DataFrame()

    def get_processing_stats(self) -> Dict[str, Any]:
        """처리 통계 조회"""
        try:
            # Elasticsearch 통계
            es_stats = self.vector_tool.get_stats()

            # Neo4j 통계
            graph_stats = self.graph_tool.get_stats()

            return {
                "elasticsearch": {
                    "total_documents": es_stats.get("total_docs", 0),
                    "index_size": es_stats.get("index_size", 0),
                    "status": es_stats.get("status", "unknown")
                },
                "neo4j": {
                    "total_nodes": graph_stats.get("total_nodes", 0),
                    "total_relationships": graph_stats.get("total_relationships", 0),
                    "entity_types": graph_stats.get("entity_types", {}),
                    "status": "healthy" if "error" not in graph_stats else "error"
                },
                "last_updated": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {"error": str(e)}

    async def search_dart_documents(self, query: str, filters: Dict = None) -> Dict[str, Any]:
        """DART 문서 검색"""
        try:
            # Elasticsearch에서 검색
            vector_results = self.vector_tool.text_search(query, top_k=10, filters=filters)

            # Neo4j에서 관련 그래프 컨텍스트 조회
            graph_context = self.graph_tool.query_graph_context(query, limit=5)

            return {
                "query": query,
                "vector_results": vector_results,
                "graph_context": graph_context,
                "total_found": len(vector_results)
            }

        except Exception as e:
            logger.error(f"DART 문서 검색 실패: {e}")
            return {"query": query, "error": str(e)}


# 사용 예시 및 유틸리티 함수들
async def process_dart_csv_file(csv_path: str, content_column: str = "content"):
    """CSV 파일로부터 DART 데이터 처리"""
    processor = DARTDataProcessor()

    # CSV 로드
    df = processor.load_dart_csv(csv_path)
    if df.empty:
        logger.error("CSV 파일을 로드할 수 없습니다.")
        return False

    # 처리 실행
    results = await processor.process_dart_dataframe(df, content_column)

    # 결과 출력
    logger.info(f"최종 결과: {results}")

    # 통계 조회
    stats = processor.get_processing_stats()
    logger.info(f"처리 후 통계: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    return results["success"] > 0

async def test_dart_search(query: str = "삼성전자 투자"):
    """DART 검색 테스트"""
    processor = DARTDataProcessor()

    results = await processor.search_dart_documents(query)

    print(f"\n=== DART 검색 결과: '{query}' ===")
    print(f"총 {results['total_found']}개 문서 발견")

    for i, doc in enumerate(results.get('vector_results', [])[:3], 1):
        print(f"\n[{i}] {doc['source'].get('title', 'No Title')}")
        print(f"    회사: {doc['source']['meta'].get('company', 'Unknown')}")
        print(f"    점수: {doc['score']:.3f}")
        print(f"    요약: {doc['source']['summary'][:100]}...")

    if results.get('graph_context', {}).get('entities'):
        print(f"\n관련 엔티티: {', '.join(results['graph_context']['entities'])}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # 검색 테스트
            asyncio.run(test_dart_search())
        else:
            # CSV 파일 처리
            csv_path = sys.argv[1]
            content_col = sys.argv[2] if len(sys.argv) > 2 else "content"
            asyncio.run(process_dart_csv_file(csv_path, content_col))
    else:
        print("사용법:")
        print("  python dart_processor.py <csv_path> [content_column]")
        print("  python dart_processor.py test")
