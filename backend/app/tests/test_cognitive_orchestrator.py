import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.cognitive.selector import SkillSelector
from app.services.cognitive.context import ContextBuilder
from app.services.cognitive.prompt import PromptBuilder
from app.services.cognitive.orchestrator import CognitiveOrchestrator
from app.models.database_models import CognitiveTrace, GoalTracker, Session
from app.services.skills.registry import SkillsRegistry
from app.schemas.skills import SkillManifest, ActivationRules, PromptOverlay
from app.services.knowledge.vector_store import ChromaDBClient


def test_skill_selector_deterministic():
    # Setup mock registry with 4 custom skills
    registry = MagicMock(spec=SkillsRegistry)
    
    skill_a = SkillManifest(
        name="Python Dev",
        description="Python coding support",
        activation_rules=ActivationRules(file_patterns=["*.py"], keywords=["python", "list"]),
        prompt_overlay=PromptOverlay(role="Python Guru", pedagogical_instructions="Simple explanations", technical_constraints=["No global variables"])
    )
    skill_b = SkillManifest(
        name="React Dev",
        description="React coding support",
        activation_rules=ActivationRules(file_patterns=["*.tsx", "*.jsx"], keywords=["react", "hooks", "component"]),
        prompt_overlay=PromptOverlay(role="React Guru", pedagogical_instructions="Component focus", technical_constraints=["Functional components only"])
    )
    skill_c = SkillManifest(
        name="Django Expert",
        description="Django specialist",
        activation_rules=ActivationRules(file_patterns=["models.py"], keywords=["django", "model", "query"]),
        prompt_overlay=PromptOverlay(role="Django Guru", pedagogical_instructions="ORM focus", technical_constraints=["Use select_related"])
    )
    skill_d = SkillManifest(
        name="Rust Dev",
        description="Rust specialist",
        activation_rules=ActivationRules(file_patterns=["*.rs"], keywords=["rust", "cargo"]),
        prompt_overlay=PromptOverlay(role="Rust Guru", pedagogical_instructions="Memory safety", technical_constraints=["No unsafe"])
    )

    registry.skills = {
        "Python Dev": skill_a,
        "React Dev": skill_b,
        "Django Expert": skill_c,
        "Rust Dev": skill_d
    }

    selector = SkillSelector(registry=registry)

    # 1. Trigger query matching
    results = selector.select_skills("How do I write a django model in python?")
    # "django" matches Django Expert (+2), "model" matches Django Expert (+2) = 4 points
    # "python" matches Python Dev (+2) = 2 points
    assert len(results) == 2
    assert results[0]["skill"] == "Django Expert"
    assert results[0]["score"] == 4
    assert results[1]["skill"] == "Python Dev"
    assert results[1]["score"] == 2

    # 2. Trigger workspace matching
    results_file = selector.select_skills("How do I hooks?", active_file="main.tsx")
    # "hooks" matches React Dev (+2)
    # "main.tsx" triggers *.tsx suffix match (+5)
    # Total = 7 points
    assert len(results_file) == 1
    assert results_file[0]["skill"] == "React Dev"
    assert results_file[0]["score"] == 7

    # 3. Trigger multi-skill top-3 limit
    # Query matching keywords for all 4 skills
    results_all = selector.select_skills("python react django rust hooks list")
    # Python Dev: python (+2), list (+2) = 4
    # React Dev: react (+2), hooks (+2) = 4
    # Django Expert: django (+2) = 2
    # Rust Dev: rust (+2) = 2
    # Sorted: Python Dev (4), React Dev (4), Django Expert (2), Rust Dev (2)
    # Alphabetical resolver for ties at score=2: Django Expert (D) then Rust Dev (R)
    # Top 3: Python Dev, React Dev, Django Expert
    assert len(results_all) == 3
    selected_names = [s["skill"] for s in results_all]
    assert "Python Dev" in selected_names
    assert "React Dev" in selected_names
    assert "Django Expert" in selected_names
    assert "Rust Dev" not in selected_names


def test_context_and_memory_budgets(db_session):
    # Mock Chroma client returning 10 chunks
    chroma = MagicMock(spec=ChromaDBClient)
    chroma.query_similarity.return_value = [
        {"chunk_id": f"chunk_{i}", "document_id": "doc1", "filepath": "Vision/doc.md", "content": f"Content {i}", "heading_hierarchy": ["Vision"]}
        for i in range(10)
    ]
    
    # Enable mock settings
    settings.MAX_KNOWLEDGE_CHUNKS = 4
    settings.MAX_RECENT_EVENTS = 3
    
    # Store dummy active goal
    goal = GoalTracker(description="Implement dynamic components")
    db_session.add(goal)
    db_session.commit()

    builder = ContextBuilder(chroma_client=chroma)
    
    # Add 5 events in sensory cache
    session_id = "test_session_abc"
    builder.memory_manager._sensory_cache[session_id] = [
        {"event_id": f"event_{i}", "primary_modality": "text", "summary": f"User query {i}"}
        for i in range(5)
    ]

    context = builder.build_context(
        db=db_session,
        query="test query",
        selected_skills=[],
        session_id=session_id
    )

    # Assert budgets are respected
    # Knowledge budget (MAX_KNOWLEDGE_CHUNKS = 4)
    assert len(context["knowledge"]) == 4
    # Memory events budget (MAX_RECENT_EVENTS = 3)
    assert len(context["sensory_memory"]) == 3
    # Verify latest items are taken (index 2, 3, 4)
    assert context["sensory_memory"][0]["event_id"] == "event_2"
    assert context["sensory_memory"][-1]["event_id"] == "event_4"


def test_prompt_builder():
    builder = PromptBuilder(version="v1-test")
    
    context = {
        "identity": "Socratic AI assistant.",
        "skills": [
            {
                "name": "Python Dev",
                "role": "Python Guru",
                "pedagogical_instructions": "Guide the student.",
                "technical_constraints": "- No global variables\n- Use type hints"
            }
        ],
        "knowledge": [
            {"filepath": "Vision/doc.md", "heading_hierarchy": ["Vision", "Intro"], "content": "Knowledge text."}
        ],
        "working_memory": {
            "active_goals": [{"description": "Finish coding"}],
            "active_context": {"active_file": "app.py", "cursor_line": 10, "selected_code": "def hello(): pass"}
        },
        "longterm_memory": {
            "lessons": [{"concept_name": "Loops", "mastery_score": 90}],
            "projects": [{"project_name": "Taksh", "tech_stack": ["FastAPI", "SQLite"]}]
        },
        "sensory_memory": [
            {"event_id": "evt1", "primary_modality": "text", "summary": "Initial greeting."}
        ]
    }

    prompt_pkg = builder.build_prompt_package("What is python?", context)
    
    assert prompt_pkg["prompt_version"] == "v1-test"
    assert "Socratic AI assistant." in prompt_pkg["system_prompt"]
    assert "Python Guru" in prompt_pkg["system_prompt"]
    
    assert "Active Goals: Finish coding" in prompt_pkg["user_prompt"]
    assert "app.py" in prompt_pkg["user_prompt"]
    assert "def hello(): pass" in prompt_pkg["user_prompt"]
    assert "Loops (Mastery: 90)" in prompt_pkg["user_prompt"]
    assert "Knowledge text." in prompt_pkg["user_prompt"]
    assert "What is python?" in prompt_pkg["user_prompt"]
    
    assert "Prompt Version: v1-test" in prompt_pkg["preview"]


def test_orchestrator_and_api(client, db_session):
    # Verify REST APIs
    # 1. Plan API
    payload = {
        "query": "How do I setup routing?",
        "session_id": None
    }
    response = client.post("/api/v1/orchestrator/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "prompt_package" in data
    assert "decision_trace" in data
    assert "prompt_version" in data["prompt_package"]
    
    # Verify trace is persisted
    trace = db_session.query(CognitiveTrace).first()
    assert trace is not None
    assert trace.query == "How do I setup routing?"
    
    # 2. Diagnostics Info API
    response = client.get("/api/v1/orchestrator/info")
    assert response.status_code == 200
    info = response.json()
    assert info["total_traces"] == 1
    assert info["avg_knowledge_chunks"] >= 0.0
    assert info["avg_memory_items"] >= 0.0
