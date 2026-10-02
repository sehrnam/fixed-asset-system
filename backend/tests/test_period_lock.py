def _login(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "Passw0rd!"})
    assert r.status_code == 200


def test_lock_and_unlock_period(client, seeded_user, db):
    _login(client)
    # Create period by running depreciation
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})

    r = client.post("/api/periods/2024/lock")
    assert r.status_code == 200
    assert r.json()["status"] == "LOCKED"

    r = client.post("/api/periods/2024/unlock")
    assert r.status_code == 200
    assert r.json()["status"] == "OPEN"


def test_locked_period_blocks_journal_preparation(client, seeded_user, db):
    _login(client)
    client.post("/api/depreciation/run", json={"through_period": "2024", "asset_ids": None})
    client.post("/api/periods/2024/lock")

    r = client.post("/api/journals/depreciation", json={"period_label": "2024"})
    assert r.status_code == 409