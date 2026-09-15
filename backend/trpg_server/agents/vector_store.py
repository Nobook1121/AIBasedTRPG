"""Optional Qdrant adapter; callers can always fall back to JSON indexes."""
from __future__ import annotations
from typing import Any, Iterable

class VectorStore:
    def upsert(self, collection: str, points: Iterable[dict[str, Any]]) -> bool: raise NotImplementedError
    def search(self, collection: str, vector: list[float], limit: int = 5) -> list[dict[str, Any]]: raise NotImplementedError
    def health(self) -> dict[str, Any]: return {"available": False}

class QdrantVectorStore(VectorStore):
    def __init__(self, url: str|None = None, path: str|None = None, api_key: str|None = None, dimensions: int|None = 256):
        self.url, self.path, self.api_key = url, path, api_key
        self.dimensions = int(dimensions) if dimensions else None
        self.client=None
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(url=url, path=path, api_key=api_key) if url else QdrantClient(path=path or "data/runtime/vector-db/qdrant")
        except Exception: self.client=None
    def health(self):
        if not self.client: return {"available": False, "backend": "qdrant"}
        try: self.client.get_collections(); return {"available": True, "backend": "qdrant"}
        except Exception: return {"available": False, "backend": "qdrant"}
    def upsert(self, collection, points):
        if not self.client: return False
        try:
            from qdrant_client.models import Distance, PointStruct, VectorParams
            points = list(points)
            if not points: return True
            vector_size = len(points[0].get("vector") or [])
            if not vector_size: return False
            if not self.client.collection_exists(collection):
                self.dimensions = vector_size
                self.client.create_collection(collection_name=collection, vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE))
            elif self.dimensions and vector_size != self.dimensions:
                return False
            self.client.upsert(collection_name=collection, points=[PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload",{})) for p in points]); return True
        except Exception: return False
    def search(self, collection, vector, limit=5):
        if not self.client: return []
        try: return [{"id":str(item.id),"score":item.score,"payload":item.payload or {}} for item in self.client.search(collection_name=collection, query_vector=vector, limit=limit)]
        except Exception: return []
