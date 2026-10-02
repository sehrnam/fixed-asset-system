from sqlmodel import select

from app.models.audit import AuditEvent


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client, seeded_user):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["username"] == "admin"
    assert body["user"]["role"] == "admin"
    assert "fas_session" in r.cookies


def test_login_wrong_password(client, seeded_user):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={"username": "ghost", "password": "x"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_after_login(client, seeded_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    r = client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_logout_revokes_session(client, seeded_user):
    client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_audit_login_failure_is_recorded(client, seeded_user, db):
    client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    events = db.exec(select(AuditEvent).where(AuditEvent.action == "LOGIN_FAILED")).all()
    assert len(events) >= 1
    assert events[-1].result == "FAILURE"


def test_audit_login_success_is_recorded(client, seeded_user, db):
    client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    events = db.exec(select(AuditEvent).where(AuditEvent.action == "LOGIN_SUCCESS")).all()
    assert len(events) >= 1
    assert events[-1].result == "SUCCESS"


def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"