import os
import logging
from neo4j import GraphDatabase
from elasticsearch import Elasticsearch
from app.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnection:
    _driver = None

    @classmethod
    def get_driver(cls):
        if cls._driver is None:
            try:
                uri = settings.NEO4J_URI
                user = settings.NEO4J_USER
                password = settings.NEO4J_PASSWORD
                cls._driver = GraphDatabase.driver(uri, auth=(user, password))
                logger.info(f"Neo4j 연결 성공: {uri}")
            except Exception as e:
                logger.error(f"Neo4j 연결 실패: {e}")
                raise
        return cls._driver

    @classmethod
    def close(cls):
        if cls._driver:
            cls._driver.close()
            cls._driver = None
            logger.info("Neo4j 연결 종료")


class ElasticsearchConnection:
    _client = None
    _connection_failed = False

    @classmethod
    def get_client(cls):
        if cls._client is None and not cls._connection_failed:
            try:
                host = settings.ELASTICSEARCH_HOST
                port = settings.ELASTICSEARCH_PORT
                cls._client = Elasticsearch(
                    hosts=[f"http://{host}:{port}"],
                    timeout=settings.ELASTICSEARCH_TIMEOUT,
                    max_retries=settings.ELASTICSEARCH_MAX_RETRIES,
                    retry_on_timeout=True,
                )
                # 연결 테스트
                if cls._client.ping():
                    logger.info(f"Elasticsearch 연결 성공: {host}:{port}")
                else:
                    raise Exception("Elasticsearch ping 실패")
            except Exception as e:
                logger.error(f"Elasticsearch 연결 실패: {e}")
                cls._connection_failed = True
                cls._client = None
                # 더미 클라이언트 반환하는 대신 None 반환
                return None
        return cls._client

    @classmethod
    def is_available(cls):
        """Elasticsearch 연결 상태 확인"""
        try:
            client = cls.get_client()
            return client is not None and client.ping()
        except:
            return False

    @classmethod
    def close(cls):
        if cls._client:
            cls._client = None
            logger.info("Elasticsearch 연결 종료")
