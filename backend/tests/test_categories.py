from sqlmodel import select

from app.models.audit import AuditEvent
from app.models.category import AssetCategory
from app.models.user import User
from app.security.passwords import hash_password
from app.security.permissions import Role


def _login(client, username="admin", password="Passw0rd!"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200


def test_create_category(client, seeded_user):
    _login(client)
    r = client.post("/api/categories", json={"name": "Vehicles", "description": "Fleet"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Vehicles"
    assert body["status"] == "ACTIVE"


def test_create_category_duplicate_name(client, seeded_user):
    _login(client)
    client.post("/api/categories", json={"name": "Vehicles"})
    r = client.post("/api/categories", json={"name": "Vehicles"})
    assert r.status_code == 409


def test_list_categories(client, seeded_user):
    _login(client)
    client.post("/api/categories", json={"name": "Furniture"})
    r = client.get("/api/categories")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert any(c["name"] == "Furniture" for c in r.json())


def test_get_category(client, seeded_user):
    _login(client)
    created = client.post("/api/categories", json={"name": "Machinery"}).json()
    r = client.get(f"/api/categories/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Machinery"


def test_update_category(client, seeded_user):
    _login(client)
    created = client.post("/api/categories", json={"name": "Old"}).json()
    r = client.patch(f"/api/categories/{created['id']}", json={"name": "New"})
    assert r.status_code == 200
    assert r.json()["name"] == "New"


def test_category_audit_event(client, seeded_user, db):
    _login(client)
    client.post("/api/categories", json={"name": "Audit Check"})
    events = db.exec(select(AuditEvent).where(AuditEvent.action == "CATEGORY_CREATED")).all()
    assert len(events) >= 1


def test_auditor_cannot_create_category(client, db):
    # Seed an auditor user
    auditor = User(
        username="auditor",
        email="auditor@example.com",
        full_name="Auditor User",
        password_hash=hash_password("Passw0rd!"),
        role=Role.AUDITOR.value,
        is_active=True,
    )
    db.add(auditor)
    db.commit()

    _login(client, username="auditor", password="Passw0rd!")
    r = client.post("/api/categories", json={"name": "Should Fail"})
    assert r.status_code == 403


def test_unauthenticated_cannot_list_categories(client):
    r = client.get("/api/categories")
    assert r.status_code == 401