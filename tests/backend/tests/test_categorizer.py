import categorizer


def test_categorize_note_programming_domain():
    programs = [
        {"key": "ai_pipeline", "title": "AI Pipeline", "domain": "programming", "keywords": ["vector", "embedding", "api"]},
        {"key": "ops", "title": "Operations", "domain": "operations"},
    ]
    text = "Need to refactor the FastAPI endpoint and update the embedding vector cache."
    result = categorizer.categorize_note(text, "FastAPI refactor", programs)
    data = result.as_dict()
    assert data["domain"] == "programming"
    assert data["confidence"] >= 0.25
    assert data["program"] == "ai_pipeline"
    assert data["program_confidence"] is not None
    assert "fastapi" in data["rationale"].lower()


def test_categorize_note_general_fallback():
    programs = [{"key": "ops", "title": "Operations", "domain": "operations"}]
    text = "Thinking about weekend travel plans and family time."
    result = categorizer.categorize_note(text, None, programs)
    data = result.as_dict()
    assert data["domain"] == "personal"
    assert data["program"] is None
    assert data["confidence"] >= 0.2
