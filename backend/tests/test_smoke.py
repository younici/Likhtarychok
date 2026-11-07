import os

# Keep the app offline: no DB, Redis, bots or scheduled jobs are needed.
os.environ["DB_ONLINE"] = "false"
os.environ["REDIS_ONLINE"] = "false"
os.environ["ONLINE"] = "false"
os.environ["VAPID_PUBLIC_KEY"] = "test-public-key"
os.environ["NOTIFY_PASS"] = "my_notify_secret"
os.environ["ADMIN_STATS_PASSWORD"] = "secret_pass_123"

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from untils import stats_tracker  # noqa: E402

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


def test_admin_stats_auth_failure():
    resp = client.post("/api/admin/stats", json={"password": "wrong-password"})
    assert resp.status_code == 401
    assert resp.json()["ok"] is False


def test_admin_stats_auth_success_and_metrics():
    # Record a graph request
    stats_tracker.record_graph_request(11)

    # Auth via NOTIFY_PASS directly
    resp = client.post("/api/admin/stats", json={"password": "my_notify_secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    stats = data["stats"]
    assert "users" in stats
    assert "database" in stats
    assert "pushes_24h" in stats
    assert "pushes_ranking" in stats
    assert "graph_requests" in stats
    assert stats["graph_requests"]["total_requests"] >= 1
    assert "subscribers_ranking" in stats["users"]
