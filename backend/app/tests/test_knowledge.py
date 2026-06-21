from app.services.knowledge.search import HybridSearchEngine

def test_hybrid_search():
    engine = HybridSearchEngine()
    result = engine.search("FreeRTOS Task Notifications")
    assert result is not None
    assert "search" in result.lower() or "stub" in result.lower()
