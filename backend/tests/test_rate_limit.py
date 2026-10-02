def test_login_rate_limit_blocks_after_threshold(client, seeded_user):
    # Default limit is 10 attempts per 60s window.
    for _ in range(10):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code in (401,)

    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 429