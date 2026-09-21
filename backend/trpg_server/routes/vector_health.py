from flask import Blueprint, current_app, session
from trpg_server.responses import error_response
bp = Blueprint("vector_health", __name__)
@bp.get("/api/vector/health")
def health():
    if not session.get("user_id"):
        return error_response("Authentication required", 401, "Authentication required")
    vector = current_app.extensions.get("vector_store")
    embedding = current_app.extensions.get("embedding_provider")
    ocr = current_app.extensions.get("ocr_provider")
    embedding_health = embedding.health() if embedding and hasattr(embedding, "health") else {"configured": bool(embedding and embedding.configured), "loaded": False}
    return {"success": True, "data": {"vector": vector.health() if vector else {"available": False}, "embedding": embedding_health, "ocr": {"enabled": bool(ocr), "available": bool(ocr and ocr.available)}}}
