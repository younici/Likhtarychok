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


def test_address_search_endpoint_and_smart_matching():
    # 1. Basic search in Ukrainian
    resp = client.get("/api/addresses/search?q=Київська")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["results"]) > 0
    first = data["results"][0]
    for key in ("queue", "queue_label", "street", "city", "houses"):
        assert key in first
    assert "Київська" in first["street"]

    # 2. Smart Russian query matching ("киевская" -> "Київська")
    resp_ru = client.get("/api/addresses/search?q=киевская")
    assert resp_ru.status_code == 200
    data_ru = resp_ru.json()
    assert data_ru["ok"] is True
    assert len(data_ru["results"]) > 0
    assert any("Київська" in r["street"] for r in data_ru["results"])

    # 3. Smart house matching ("Київська 21" prioritizes queue with house 21)
    resp_house = client.get("/api/addresses/search?q=Київська 21")
    assert resp_house.status_code == 200
    data_house = resp_house.json()
    assert data_house["ok"] is True
    top_result = data_house["results"][0]
    assert top_result["matched_house"] == "21"
    assert top_result["queue"] == "11"
    assert top_result["queue_label"] == "1.1"

    # 4. Russian query with house ("большая бердичевская 15")
    resp_bb = client.get("/api/addresses/search?q=большая бердичевская 15")
    assert resp_bb.status_code == 200
    data_bb = resp_bb.json()
    assert data_bb["ok"] is True
    assert len(data_bb["results"]) > 0
    assert "Велика Бердичівська" in data_bb["results"][0]["street"]
    assert data_bb["results"][0]["matched_house"] == "15"

    # 5. Non-Zhytomyr city with house ("Бердичів Житомирська 131")
    resp_berd = client.get("/api/addresses/search?q=Бердичів Житомирська 131")
    assert resp_berd.status_code == 200
    data_berd = resp_berd.json()
    assert data_berd["ok"] is True
    assert len(data_berd["results"]) > 0
    top_berd = data_berd["results"][0]
    assert "Бердичів" in top_berd["city"]
    assert "Житомирська" in top_berd["street"]
    assert top_berd["matched_house"] == "131"

    # 6. Meta endpoint verification
    meta_resp = client.get("/api/addresses/meta")
    assert meta_resp.status_code == 200
    meta = meta_resp.json()
    assert meta["ok"] is True
    assert meta["total_indexed"] > 0
    assert "source" in meta

    # 7. Root aliases
    assert client.get("/addresses/search?q=Київська").status_code == 200
    assert client.get("/addresses/meta").status_code == 200

