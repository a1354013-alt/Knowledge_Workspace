import uuid

import pytest
from fastapi.testclient import TestClient

from app.context import db
from app.main import app


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
    assert "failedDocuments" in data["documents"]
    assert "archivedDocuments" in data["documents"]

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


def test_dashboard_health_promoted_and_document_status_metrics(client, auth_headers):
    user_id = "owner"
    unique_suffix = uuid.uuid4().hex
    knowledge_id = f"test_promoted_knowledge_{unique_suffix}"
    logbook_id = f"test_promoted_logbook_{unique_suffix}"
    archived_doc_id = f"test_archived_doc_{unique_suffix}"

    before = client.get("/api/dashboard/health", headers=auth_headers)
    assert before.status_code == 200
    before_data = before.json()

    db.add_knowledge_entry(
        entry_id=knowledge_id,
        title="Promoted Knowledge",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        notes="",
        created_by=user_id,
        status="verified",
    )
    db.add_logbook_entry(
        entry_id=logbook_id,
        title="Promoted Logbook",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        run_id="",
        source_type="manual",
        created_by=user_id,
        status="reviewed",
    )
    assert db.add_link(f"logbook:{logbook_id}", f"knowledge:{knowledge_id}", link_type="produced")
    db.add_document(
        doc_id=archived_doc_id,
        filename="archived.txt",
        saved_filename="archived.txt",
        file_size=10,
        uploaded_by=user_id,
        category="notes",
        tags="",
        status="archived",
    )

    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["logbook"]["promoted_to_knowledge"] >= before_data["logbook"]["promoted_to_knowledge"] + 1
    assert data["documents"]["archivedDocuments"] >= before_data["documents"]["archivedDocuments"] + 1
    assert data["documents"]["failedDocuments"] == 0


def test_dashboard_health_promoted_metrics_are_scoped_to_current_user(client, auth_headers):
    before = client.get("/api/dashboard/health", headers=auth_headers)
    assert before.status_code == 200
    before_count = before.json()["logbook"]["promoted_to_knowledge"]

    owner_suffix = uuid.uuid4().hex
    other_suffix = uuid.uuid4().hex

    owner_logbook_id = f"owner_logbook_{owner_suffix}"
    owner_knowledge_id = f"owner_knowledge_{owner_suffix}"
    other_logbook_id = f"other_logbook_{other_suffix}"
    other_knowledge_id = f"other_knowledge_{other_suffix}"

    db.add_knowledge_entry(
        entry_id=owner_knowledge_id,
        title="Owner Knowledge",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        notes="",
        created_by="owner",
        status="verified",
    )
    db.add_logbook_entry(
        entry_id=owner_logbook_id,
        title="Owner Logbook",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        run_id="",
        source_type="manual",
        created_by="owner",
        status="reviewed",
    )
    db.add_knowledge_entry(
        entry_id=other_knowledge_id,
        title="Other Knowledge",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        notes="",
        created_by="teammate",
        status="verified",
    )
    db.add_logbook_entry(
        entry_id=other_logbook_id,
        title="Other Logbook",
        problem="Problem",
        solution="Solution",
        root_cause="",
        tags="",
        run_id="",
        source_type="manual",
        created_by="teammate",
        status="reviewed",
    )

    assert db.add_link(f"logbook:{owner_logbook_id}", f"knowledge:{owner_knowledge_id}", link_type="produced")
    assert db.add_link(f"logbook:{other_logbook_id}", f"knowledge:{other_knowledge_id}", link_type="produced")

    response = client.get("/api/dashboard/health", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["logbook"]["promoted_to_knowledge"] == before_count + 1
