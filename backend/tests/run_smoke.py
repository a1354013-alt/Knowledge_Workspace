from __future__ import annotations

import importlib
import os
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_app():
    run_id = uuid.uuid4().hex
    os.environ['JWT_SECRET'] = 'smoke-secret-smoke-secret-smoke-secret-1234'
    os.environ['DEFAULT_OWNER_PASSWORD'] = 'OwnerPass123!'
    os.environ['DATABASE_PATH'] = ':memory:'
    os.environ['UPLOAD_DIR'] = f'uploads_smoke_{run_id}'
    os.environ['CHROMA_DB_PATH'] = f'chroma_smoke_{run_id}'
    os.environ['ALLOWED_ORIGINS'] = 'http://localhost:5173'

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
    assert response.status_code == 200, response.text
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def main() -> int:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    app_module = load_app()
    client = TestClient(app_module.app)

    ok = client.post('/api/login', json={'user_id': 'owner', 'password': 'OwnerPass123!'})
    bad = client.post('/api/login', json={'user_id': 'owner', 'password': 'wrong-pass'})
    assert ok.status_code == 200
    assert bad.status_code == 401
    print('PASS login success/failure')

    owner_headers = auth_headers(client, 'owner', 'OwnerPass123!')
    me = client.get('/api/me', headers=owner_headers)
    assert me.status_code == 200 and me.json()['user_id'] == 'owner'
    print('PASS /api/me')

    uploads_dir = Path(app_module.UPLOAD_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    doc_upload = client.post(
        '/api/docs/upload',
        headers=owner_headers,
        files={'file': ('manual.txt', b'content', 'text/plain')},
        data={'category': 'notes', 'tags': 'smoke'},
    )
    assert doc_upload.status_code == 200, doc_upload.text
    docs = client.get('/api/docs', headers=owner_headers)
    assert docs.status_code == 200 and len(docs.json()) == 1
    print('PASS document upload/list')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
