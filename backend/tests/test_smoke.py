import os

# Keep the app offline: no DB, Redis, bots or scheduled jobs are needed.
os.environ["DB_ONLINE"] = "false"
os.environ["REDIS_ONLINE"] = "false"
os.environ["ONLINE"] = "false"
os.environ["VAPID_PUBLIC_KEY"] = "test-public-key"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402

# Not used as a context manager, so the lifespan (bots, scheduler) is not started.
client = TestClient(main.app)


def test_vapid_public_key():
    resp = client.get("/api/vapid_public_key")
    assert resp.status_code == 200
    assert resp.json() == {"key": "test-public-key"}


def test_subscribe_rejects_invalid_payload():
    resp = client.post("/api/subscribe", json={"subscription": "bad"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is False
