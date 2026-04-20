from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_app(monkeypatch, tmp_path):
    monkeypatch.setenv('JWT_SECRET', 'test-secret-test-secret-test-secret-1234')
    monkeypatch.setenv('DEFAULT_OWNER_PASSWORD', 'OwnerPass123!')
    monkeypatch.setenv('DATABASE_PATH', str(tmp_path / 'test.db'))
    monkeypatch.setenv('UPLOAD_DIR', str(tmp_path / 'uploads'))
    monkeypatch.setenv('CHROMA_DB_PATH', str(tmp_path / 'chroma'))
    monkeypatch.setenv('ALLOWED_ORIGINS', 'http://localhost:5173')

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    main = importlib.import_module('app.main')
    main.delete_from_vector_db = lambda doc_id: True

    def fake_process_file(doc_id, file_path, filename, owner_user_id, status='reviewed', is_active=1):
        return doc_id

    async def fake_perform_qa(question, user_id):
        return (f'answer for {user_id}', [])

    main.process_file = fake_process_file
    main.perform_qa = fake_perform_qa
    return main


def auth_headers(client, user_id='owner', password='OwnerPass123!'):
    response = client.post('/api/login', json={'user_id': user_id, 'password': password})
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_login_success_and_failure(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)

    ok = client.post('/api/login', json={'user_id': 'owner', 'password': 'OwnerPass123!'})
    bad = client.post('/api/login', json={'user_id': 'owner', 'password': 'wrong-pass'})

    assert ok.status_code == 200
    assert 'access_token' in ok.json()
    assert bad.status_code == 401


def test_me_endpoint(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.get('/api/me', headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()['user_id'] == 'owner'


def test_document_upload_and_list(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    uploads_dir = Path(main.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    response = client.post(
        '/api/docs/upload',
        headers=headers,
        files={'file': ('manual.txt', b'hello world', 'text/plain')},
        data={'category': 'notes', 'tags': 'demo'},
    )
    assert response.status_code == 200, response.text

    docs = client.get('/api/docs', headers=headers)
    assert docs.status_code == 200
    payload = docs.json()
    assert len(payload) == 1
    assert payload[0]['filename'] == 'manual.txt'
    assert payload[0]['status'] == 'reviewed'


def test_global_search_filters(monkeypatch, tmp_path):
    main = load_app(monkeypatch, tmp_path)
    client = TestClient(main.app)
    headers = auth_headers(client)

    create = client.post(
        "/api/knowledge/entries",
        headers=headers,
        json={
            "title": "Search marker",
            "problem": "Problem ABC123",
            "root_cause": "",
            "solution": "Do X then Y",
            "tags": "alpha,beta",
            "notes": "",
            "status": "draft",
            "source_type": "manual",
            "source_ref": "",
            "related_item_ids": [],
        },
    )
    assert create.status_code == 200, create.text

    results = client.get(
        "/api/search",
        headers=headers,
        params={"q": "ABC123", "types": "knowledge", "status_filter": "draft", "tag": "alpha", "limit": 50},
    )
    assert results.status_code == 200, results.text
    items = results.json().get("items") or []
    assert any(item.get("item_id", "").startswith("knowledge:") for item in items)
