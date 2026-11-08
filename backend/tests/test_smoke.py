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
    from untils import addresses

    # Seed test index (simulating data loaded from Redis / ZTOE)
    test_items = [
        {
            "id": 1,
            "rem": "Житомирський",
            "city": "місто Житомир",
            "street": "вул. Київська",
            "houses": ["1", "61", "63", "63-А", "65", "69", "71", "73", "79", "84", "122"],
            "queue": 11,
            "queue_label": "1.1",
        },
        {
            "id": 2,
            "rem": "Житомирський",
            "city": "місто Житомир",
            "street": "вул. Київська",
            "houses": ["1", "5", "9", "11", "14", "15", "16", "17", "17/1", "19", "21", "59"],
            "queue": 12,
            "queue_label": "1.2",
        },
        {
            "id": 3,
            "rem": "Житомирський",
            "city": "місто Житомир",
            "street": "вул. Велика Бердичівська",
            "houses": ["15", "15/1", "17", "28", "30", "32"],
            "queue": 62,
            "queue_label": "6.2",
        },
        {
            "id": 4,
            "rem": "Бердичівський",
            "city": "місто Бердичів",
            "street": "вул. Житомирська",
            "houses": ["94/2", "131", "135", "137", "139", "141"],
            "queue": 11,
            "queue_label": "1.1",
        },
    ]
    addresses._set_indexed_addresses(test_items, updated_at="2026-11-08 04:00:00", source="redis_cache")

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

    # 3. Smart house matching ("Київська 21" prioritizes queue 1.2 with house 21 and filters out non-matching queues of that street)
    resp_house = client.get("/api/addresses/search?q=Київська 21")
    assert resp_house.status_code == 200
    data_house = resp_house.json()
    assert data_house["ok"] is True
    top_result = data_house["results"][0]
    assert top_result["matched_house"] == "21"
    assert top_result["queue"] == "12"
    assert top_result["queue_label"] == "1.2"
    # Other queues of місто Житомир, вул. Київська without house 21 are filtered out
    zhytomyr_kyivska = [
        r
        for r in data_house["results"]
        if r["city"] == "місто Житомир" and r["street"] == "вул. Київська"
    ]
    assert len(zhytomyr_kyivska) == 1

    # 3b. House with hyphenated letter ("Київська 63-а" -> queue 1.1)
    resp_h63 = client.get("/api/addresses/search?q=Київська 63-а")
    assert resp_h63.status_code == 200
    top_63 = resp_h63.json()["results"][0]
    assert top_63["queue"] == "11"
    assert top_63["matched_house"] == "63-А"

    # 4. Russian query with house ("большая бердичевская 15" -> queue 6.2)
    resp_bb = client.get("/api/addresses/search?q=большая бердичевская 15")
    assert resp_bb.status_code == 200
    data_bb = resp_bb.json()
    assert data_bb["ok"] is True
    assert len(data_bb["results"]) > 0
    assert "Велика Бердичівська" in data_bb["results"][0]["street"]
    assert data_bb["results"][0]["matched_house"] == "15"
    assert data_bb["results"][0]["queue"] == "62"

    # 5. Non-Zhytomyr city with house ("Бердичів Житомирська 131" -> queue 1.1)
    resp_berd = client.get("/api/addresses/search?q=Бердичів Житомирська 131")
    assert resp_berd.status_code == 200
    data_berd = resp_berd.json()
    assert data_berd["ok"] is True
    assert len(data_berd["results"]) > 0
    top_berd = data_berd["results"][0]
    assert "Бердичів" in top_berd["city"]
    assert "Житомирська" in top_berd["street"]
    assert top_berd["matched_house"] == "131"
    assert top_berd["queue"] == "11"

    # 5b. Filtering by REM and settlement across Zhytomyr Oblast
    resp_loc = client.get("/api/addresses/locations")
    assert resp_loc.status_code == 200
    loc_data = resp_loc.json()
    assert loc_data["ok"] is True
    assert len(loc_data["rems"]) >= 1
    assert "Житомирський" in loc_data["rems"]

    resp_filter = client.get(
        "/api/addresses/search?rem=Бердичівський&city=місто Бердичів&q=Житомирська"
    )
    assert resp_filter.status_code == 200
    filter_results = resp_filter.json()["results"]
    assert len(filter_results) > 0
    assert all(r["rem"] == "Бердичівський" for r in filter_results)

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


def test_redis_cache_and_ztoe_fallback_lifecycle(monkeypatch):
    import asyncio
    from datetime import datetime, timedelta
    from untils import addresses

    sample_redis_items = [
        {
            "id": 10,
            "rem": "Коростенський",
            "city": "місто Коростень",
            "street": "вул. Грушевського",
            "houses": ["1", "3", "5"],
            "queue": 12,
            "queue_label": "1.2",
        }
    ]

    # Case A: Fresh Redis cache (< 12h) -> loads from Redis, does NOT call ZTOE
    fresh_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ztoe_called = {"count": 0}

    async def fake_load_fresh():
        return sample_redis_items, fresh_ts

    async def fake_sync_fail():
        ztoe_called["count"] += 1
        return False

    monkeypatch.setattr(addresses, "_load_from_redis", fake_load_fresh)
    monkeypatch.setattr(addresses, "sync_addresses_from_ztoe", fake_sync_fail)
    asyncio.run(addresses.ensure_addresses_loaded())
    assert ztoe_called["count"] == 0
    assert addresses.get_meta()["source"] == "redis_cache"
    assert addresses.get_meta()["total_indexed"] == 1

    # Case B: Outdated Redis cache (> 12h) -> tries ZTOE; if ZTOE is down, keeps Redis cache!
    old_ts = (datetime.now() - timedelta(hours=15)).strftime("%Y-%m-%d %H:%M:%S")

    async def fake_load_old():
        return sample_redis_items, old_ts

    monkeypatch.setattr(addresses, "_load_from_redis", fake_load_old)
    asyncio.run(addresses.ensure_addresses_loaded())
    assert ztoe_called["count"] == 1
    assert addresses.get_meta()["source"] == "redis_cache"
    assert addresses.get_meta()["total_indexed"] == 1

    # Case C: Empty Redis cache -> immediately calls ZTOE sync
    async def fake_load_empty():
        return None, None

    monkeypatch.setattr(addresses, "_load_from_redis", fake_load_empty)
    asyncio.run(addresses.ensure_addresses_loaded())
    assert ztoe_called["count"] == 2


