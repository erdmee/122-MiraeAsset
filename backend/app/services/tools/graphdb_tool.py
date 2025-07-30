from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """엔티티 클래스"""

    name: str
    type: str  # COMPANY, PERSON, SECTOR, PRODUCT, etc.
    properties: Dict[str, Any]


@dataclass
class Relationship:
    """관계 클래스"""

    source: str
    target: str
    type: str  # COMPETES_WITH, OWNS, PARTNERS_WITH, etc.
    properties: Dict[str, Any]


class Neo4jGraphTool:
    """Neo4j 그래프 데이터베이스 도구"""

    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")

        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=30,
            )

            # 연결 테스트
            with self.driver.session() as session:
                session.run("RETURN 1")

            logger.info(f"Neo4j 연결 성공: {self.uri}")
            self._create_indexes()

        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Neo4j 연결 실패: {e}")
            self.driver = None

    def _create_indexes(self):
        """인덱스 생성"""
        if not self.driver:
            return

        try:
            with self.driver.session() as session:
                # 엔티티 인덱스
                indexes = [
                    "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                    "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
                    "CREATE INDEX company_name IF NOT EXISTS FOR (c:Company) ON (c.name)",
                    "CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.name)",
                    "CREATE INDEX sector_name IF NOT EXISTS FOR (s:Sector) ON (s.name)",
                    "CREATE INDEX product_name IF NOT EXISTS FOR (pr:Product) ON (pr.name)",
                    # 문서 인덱스
                    "CREATE INDEX document_id IF NOT EXISTS FOR (d:Document) ON (d.doc_id)",
                    "CREATE INDEX document_type IF NOT EXISTS FOR (d:Document) ON (d.type)",
                ]

                for index_query in indexes:
                    try:
                        session.run(index_query)
                    except Exception as e:
                        logger.debug(f"인덱스 생성 건너뜀: {e}")

                logger.info("Neo4j 인덱스 설정 완료")

        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")

    def add_entities(self, entities: List[Entity]) -> bool:
        """엔티티 추가"""
        if not self.driver:
            logger.warning("Neo4j 연결 없음")
            return False

        try:
            with self.driver.session() as session:
                for entity in entities:
                    # 엔티티 타입에 따른 라벨 결정
                    labels = ["Entity", entity.type.title()]

                    query = f"""
                    MERGE (e:{':'.join(labels)} {{name: $name}})
                    SET e += $properties
                    SET e.updated_at = datetime()
                    RETURN e
                    """

                    session.run(
                        query, {"name": entity.name, "properties": entity.properties}
                    )

                logger.info(f"{len(entities)}개 엔티티 추가 완료")
                return True

        except Exception as e:
            logger.error(f"엔티티 추가 실패: {e}")
            return False

    def add_relationships(self, relationships: List[Relationship]) -> bool:
        """관계 추가"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                for rel in relationships:
                    query = f"""
                    MATCH (a:Entity {{name: $source}})
                    MATCH (b:Entity {{name: $target}})
                    MERGE (a)-[r:{rel.type}]->(b)
                    SET r += $properties
                    SET r.updated_at = datetime()
                    RETURN r
                    """

                    session.run(
                        query,
                        {
                            "source": rel.source,
                            "target": rel.target,
                            "properties": rel.properties,
                        },
                    )

                logger.info(f"{len(relationships)}개 관계 추가 완료")
                return True

        except Exception as e:
            logger.error(f"관계 추가 실패: {e}")
            return False

    def query_entities(
        self, entity_name: str = None, entity_type: str = None, limit: int = 10
    ) -> List[Dict]:
        """엔티티 쿼리"""
        if not self.driver:
            return self._get_dummy_entities()

        try:
            with self.driver.session() as session:
                conditions = []
                params = {"limit": limit}

                if entity_name:
                    conditions.append("e.name CONTAINS $name")
                    params["name"] = entity_name

                if entity_type:
                    conditions.append("$type IN labels(e)")
                    params["type"] = entity_type.title()

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                query = f"""
                MATCH (e:Entity)
                {where_clause}
                RETURN e.name as name, labels(e) as types, properties(e) as properties
                LIMIT $limit
                """

                result = session.run(query, params)
                entities = []

                for record in result:
                    entities.append(
                        {
                            "name": record["name"],
                            "types": record["types"],
                            "properties": record["properties"],
                        }
                    )

                logger.info(f"엔티티 쿼리 완료: {len(entities)}개 결과")
                return entities

        except Exception as e:
            logger.error(f"엔티티 쿼리 실패: {e}")
            return self._get_dummy_entities()

    def query_relationships(
        self,
        source: str = None,
        target: str = None,
        rel_type: str = None,
        limit: int = 10,
    ) -> List[Dict]:
        """관계 쿼리"""
        if not self.driver:
            return self._get_dummy_relationships()

        try:
            with self.driver.session() as session:
                conditions = []
                params = {"limit": limit}

                if source:
                    conditions.append("a.name CONTAINS $source")
                    params["source"] = source

                if target:
                    conditions.append("b.name CONTAINS $target")
                    params["target"] = target

                if rel_type:
                    rel_pattern = f"-[r:{rel_type}]->"
                else:
                    rel_pattern = "-[r]->"

                where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

                query = f"""
                MATCH (a:Entity){rel_pattern}(b:Entity)
                {where_clause}
                RETURN a.name as source, type(r) as relationship, b.name as target,
                       properties(r) as properties
                LIMIT $limit
                """

                result = session.run(query, params)
                relationships = []

                for record in result:
                    relationships.append(
                        {
                            "source": record["source"],
                            "relationship": record["relationship"],
                            "target": record["target"],
                            "properties": record["properties"],
                        }
                    )

                logger.info(f"관계 쿼리 완료: {len(relationships)}개 결과")
                return relationships

        except Exception as e:
            logger.error(f"관계 쿼리 실패: {e}")
            return self._get_dummy_relationships()

    def find_path(
        self, start_entity: str, end_entity: str, max_depth: int = 3
    ) -> List[Dict]:
        """두 엔티티 간 경로 찾기"""
        if not self.driver:
            return []

        try:
            with self.driver.session() as session:
                query = f"""
                MATCH path = shortestPath((a:Entity {{name: $start}})-[*1..{max_depth}]-(b:Entity {{name: $end}}))
                RETURN path
                LIMIT 5
                """

                result = session.run(query, {"start": start_entity, "end": end_entity})
                paths = []

                for record in result:
                    path = record["path"]
                    path_info = {
                        "nodes": [node["name"] for node in path.nodes],
                        "relationships": [rel.type for rel in path.relationships],
                        "length": len(path.relationships),
                    }
                    paths.append(path_info)

                logger.info(f"경로 탐색 완료: {len(paths)}개 경로")
                return paths

        except Exception as e:
            logger.error(f"경로 탐색 실패: {e}")
            return []

    def get_neighbors(
        self, entity_name: str, depth: int = 1, rel_types: List[str] = None
    ) -> Dict:
        """엔티티의 이웃 노드들 조회"""
        if not self.driver:
            return {"neighbors": [], "relationships": []}

        try:
            with self.driver.session() as session:
                rel_filter = ""
                if rel_types:
                    rel_filter = f":{':'.join(rel_types)}"

                query = f"""
                MATCH (center:Entity {{name: $name}})
                MATCH (center)-[r{rel_filter}*1..{depth}]-(neighbor:Entity)
                RETURN DISTINCT neighbor.name as name, labels(neighbor) as types,
                       properties(neighbor) as properties
                LIMIT 20
                """

                result = session.run(query, {"name": entity_name})
                neighbors = []

                for record in result:
                    neighbors.append(
                        {
                            "name": record["name"],
                            "types": record["types"],
                            "properties": record["properties"],
                        }
                    )

                # 관계 정보도 가져오기
                rel_query = f"""
                MATCH (center:Entity {{name: $name}})
                MATCH (center)-[r{rel_filter}]-(neighbor:Entity)
                RETURN center.name as source, type(r) as relationship,
                       neighbor.name as target, properties(r) as properties
                LIMIT 20
                """

                rel_result = session.run(rel_query, {"name": entity_name})
                relationships = []

                for record in rel_result:
                    relationships.append(
                        {
                            "source": record["source"],
                            "relationship": record["relationship"],
                            "target": record["target"],
                            "properties": record["properties"],
                        }
                    )

                logger.info(
                    f"이웃 조회 완료: {len(neighbors)}개 이웃, {len(relationships)}개 관계"
                )
                return {"neighbors": neighbors, "relationships": relationships}

        except Exception as e:
            logger.error(f"이웃 조회 실패: {e}")
            return {"neighbors": [], "relationships": []}

    def add_document_relations(
        self, doc_id: str, doc_type: str, entities: List[str], content: str = None
    ) -> bool:
        """문서와 엔티티 간 관계 추가"""
        if not self.driver:
            return False

        try:
            with self.driver.session() as session:
                # 문서 노드 생성
                doc_query = """
                MERGE (d:Document {doc_id: $doc_id})
                SET d.type = $doc_type
                SET d.content = $content
                SET d.updated_at = datetime()
                RETURN d
                """

                session.run(
                    doc_query,
                    {"doc_id": doc_id, "doc_type": doc_type, "content": content},
                )

                # 엔티티와 관계 생성
                for entity_name in entities:
                    rel_query = """
                    MATCH (d:Document {doc_id: $doc_id})
                    MATCH (e:Entity {name: $entity_name})
                    MERGE (d)-[r:MENTIONS]->(e)
                    SET r.updated_at = datetime()
                    RETURN r
                    """

                    session.run(
                        rel_query, {"doc_id": doc_id, "entity_name": entity_name}
                    )

                logger.info(f"문서 관계 추가 완료: {doc_id}")
                return True

        except Exception as e:
            logger.error(f"문서 관계 추가 실패: {e}")
            return False

    def query_graph_context(self, query: str, limit: int = 10) -> Dict:
        """쿼리와 관련된 그래프 컨텍스트 조회"""
        if not self.driver:
            return self._get_dummy_context()

        try:
            # 쿼리에서 엔티티 이름 추출 (간단한 방식)
            entities = self._extract_entities_from_query(query)

            all_neighbors = []
            all_relationships = []

            # 각 엔티티의 이웃들 조회
            for entity in entities:
                neighbor_data = self.get_neighbors(entity, depth=2)
                all_neighbors.extend(neighbor_data["neighbors"])
                all_relationships.extend(neighbor_data["relationships"])

            # 중복 제거
            unique_neighbors = {n["name"]: n for n in all_neighbors}.values()
            unique_relationships = {
                f"{r['source']}-{r['relationship']}-{r['target']}": r
                for r in all_relationships
            }.values()

            return {
                "query": query,
                "entities": entities,
                "neighbors": list(unique_neighbors)[:limit],
                "relationships": list(unique_relationships)[: limit * 2],
            }

        except Exception as e:
            logger.error(f"그래프 컨텍스트 조회 실패: {e}")
            return self._get_dummy_context()

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """쿼리에서 엔티티 추출 (간단한 규칙 기반)"""
        # 한국 대기업 이름들
        companies = [
            "삼성",
            "LG",
            "현대",
            "SK",
            "롯데",
            "포스코",
            "한화",
            "두산",
            "GS",
            "CJ",
        ]

        # 섹터/업종 키워드
        sectors = [
            "반도체",
            "자동차",
            "화학",
            "제철",
            "금융",
            "통신",
            "바이오",
            "게임",
            "엔터테인먼트",
        ]

        found_entities = []
        query_upper = query.upper()

        for company in companies:
            if company in query:
                found_entities.append(company)

        for sector in sectors:
            if sector in query:
                found_entities.append(sector)

        return found_entities[:5]  # 최대 5개

    def get_stats(self) -> Dict:
        """그래프 통계"""
        if not self.driver:
            return {"error": "Neo4j 연결 없음"}

        try:
            with self.driver.session() as session:
                # 노드 수
                node_result = session.run("MATCH (n) RETURN count(n) as count")
                node_count = node_result.single()["count"]

                # 관계 수
                rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_count = rel_result.single()["count"]

                # 엔티티 타입별 수
                type_result = session.run(
                    """
                    MATCH (e:Entity)
                    RETURN labels(e) as types, count(e) as count
                    ORDER BY count DESC
                """
                )

                entity_types = {}
                for record in type_result:
                    types = [t for t in record["types"] if t != "Entity"]
                    if types:
                        entity_types[types[0]] = record["count"]

                return {
                    "total_nodes": node_count,
                    "total_relationships": rel_count,
                    "entity_types": entity_types,
                    "status": "healthy",
                }

        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {"error": str(e)}

    def _get_dummy_entities(self) -> List[Dict]:
        """더미 엔티티"""
        return [
            {
                "name": "삼성전자",
                "types": ["Entity", "Company"],
                "properties": {"sector": "반도체"},
            },
            {
                "name": "LG전자",
                "types": ["Entity", "Company"],
                "properties": {"sector": "가전"},
            },
            {
                "name": "반도체",
                "types": ["Entity", "Sector"],
                "properties": {"industry": "tech"},
            },
        ]

    def _get_dummy_relationships(self) -> List[Dict]:
        """더미 관계"""
        return [
            {
                "source": "삼성전자",
                "relationship": "COMPETES_WITH",
                "target": "LG전자",
                "properties": {},
            },
            {
                "source": "삼성전자",
                "relationship": "OPERATES_IN",
                "target": "반도체",
                "properties": {},
            },
        ]

    def _get_dummy_context(self) -> Dict:
        """더미 컨텍스트"""
        return {
            "query": "더미 쿼리",
            "entities": ["삼성전자"],
            "neighbors": self._get_dummy_entities(),
            "relationships": self._get_dummy_relationships(),
        }

    def close(self):
        """연결 종료"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j 연결 종료")


# 하위 호환성을 위한 별칭
GraphQueryTool = Neo4jGraphTool
