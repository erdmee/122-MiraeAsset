# Milvus(Vector DB) Tool 래퍼
from pymilvus import connections, Collection
import os

class VectorDBTool:
    def __init__(self, host=None, port=None):
        self.host = host or os.getenv('MILVUS_HOST', 'localhost')
        self.port = port or os.getenv('MILVUS_PORT', '19530')
        connections.connect(host=self.host, port=self.port)

    def search(self, collection_name, query_vectors, top_k=5):
        collection = Collection(collection_name)
        results = collection.search(query_vectors, "embedding", param={"metric_type": "L2", "params": {"nprobe": 10}}, limit=top_k)
        return results

# 사용 예시:
# tool = VectorDBTool()
# tool.search('my_collection', [[0.1, 0.2, ...]], top_k=3)
