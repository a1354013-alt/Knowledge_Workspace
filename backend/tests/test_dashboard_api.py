import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.context import db

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers(client):
    # Seed owner user if not exists (usually handled by app init)
    # Login to get token
    response = client.post("/api/login", json={"user_id": "owner", "password": "password123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_dashboard_health_no_data(client, auth_headers):
    """Test dashboard API with no data."""
    # Ensure we are using a clean state or a user with no data
    # For simplicity, we just check if it returns 0s instead of crashing
    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "knowledge" in data
    assert "logbook" in data
    assert "autotest" in data
    assert "documents" in data
    assert "recent_activity" in data
    
    # Check resolution_rate and pass_rate are numbers
    assert isinstance(data["logbook"]["resolution_rate"], (int, float))
    assert isinstance(data["autotest"]["pass_rate"], (int, float))

def test_dashboard_health_calculation_logic(client, auth_headers):
    """Test dashboard API calculation logic with some seeded data."""
    user_id = "owner"
    
    # Seed some data directly into DB for testing
    db.add_knowledge_entry(
        entry_id="test_k1",
        title="Test Knowledge",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        notes="",
        created_by=user_id,
        status="verified"
    )
    
    db.add_logbook_entry(
        entry_id="test_l1",
        title="Test Logbook",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        run_id="",
        source_type="manual",
        created_by=user_id,
        status="draft"
    )
    
    # Add a second logbook without solution
    db.add_logbook_entry(
        entry_id="test_l2",
        title="Test Logbook 2",
        problem="Problem",
        solution="",
        root_cause="",
        tags="",
        run_id="",
        source_type="manual",
        created_by=user_id,
        status="draft"
    )
    
    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # 1 knowledge, 2 logbooks (1 with solution) -> 50% resolution rate
    assert data["knowledge"]["total"] >= 1
    assert data["logbook"]["total"] >= 2
    assert data["logbook"]["with_solution"] >= 1
    # Note: since other tests might have seeded data, we check if the rate is calculated correctly
    expected_rate = round((data["logbook"]["with_solution"] / data["logbook"]["total"]) * 100, 2)
    assert data["logbook"]["resolution_rate"] == expected_rate
