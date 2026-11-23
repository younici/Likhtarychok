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


def test_status_rest_and_grpc_endpoints(monkeypatch):
    import asyncio
    from proto import status_pb2
    from untils import cache, tools

    today = tools.today_str()
    sample_slots = [1 if i % 4 == 0 else 0 for i in range(48)]

    async def fake_schedule():
        return {"date": today, "queues": {11: sample_slots, 12: [0] * 48}}

    monkeypatch.setattr(cache.tools, "get_schedule", fake_schedule)
    monkeypatch.setattr(cache, "_cache", None)
    monkeypatch.setattr(cache, "_refresh_task", None)
    monkeypatch.setattr(cache, "_last_on_demand", 0.0)
    monkeypatch.setattr(cache, "_first_boot", False)
    monkeypatch.setattr(cache, "_lock", asyncio.Lock())

    resp = client.get("/api/status?queue=11")
    assert resp.status_code == 200
    assert resp.json() == {"Status": sample_slots}

    req_bytes = status_pb2.StatusRequest(queue="11").SerializeToString()
    frame = b"\x00" + len(req_bytes).to_bytes(4, "big") + req_bytes
    grpc_resp = client.post(
        "/api/grpc/StatusService/GetStatus",
        content=frame,
        headers={"Content-Type": "application/grpc-web+proto"},
    )
    assert grpc_resp.status_code == 200
    msg_len = int.from_bytes(grpc_resp.content[1:5], "big")
    parsed = status_pb2.StatusResponse()
    parsed.ParseFromString(grpc_resp.content[5 : 5 + msg_len])
    assert list(parsed.status) == sample_slots


def test_admin_stats_pushes_all_time(monkeypatch, tmp_path):
    monkeypatch.setattr(stats_tracker, "STATS_DIR", str(tmp_path))
    monkeypatch.setattr(stats_tracker, "PUSH_STATS_FILE", str(tmp_path / "push_stats.json"))
    monkeypatch.setattr(stats_tracker, "GRAPH_STATS_FILE", str(tmp_path / "graph_stats.json"))
    monkeypatch.setattr(stats_tracker, "_push_events", [])
    monkeypatch.setattr(
        stats_tracker,
        "_push_all_time",
        {"total": 0, "web": 0, "tg": 0, "events_count": 0},
    )
    monkeypatch.setattr(stats_tracker, "_push_by_queue_all_time", {})
    monkeypatch.setattr(stats_tracker.redis_un, "get_redis_client", lambda: None)

    stats_tracker.record_push_event(web_sent=4, tg_sent=6, title="Оновлення 1.1", queue=11)
    stats_tracker.record_push_event(web_sent=2, tg_sent=3, title="Загальне сповіщення", queue=None)

    resp = client.post("/api/admin/stats", json={"password": "my_notify_secret"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True

    stats = data["stats"]
    assert stats["pushes_all_time"] == {
        "total": 15,
        "web": 6,
        "tg": 9,
        "events_count": 2,
    }
    assert stats["pushes_24h"]["total_24h"] == 15
    assert stats["pushes_24h"]["events_count_24h"] == 2

    q11 = next(item for item in stats["pushes_ranking"] if item["label"] == "1.1")
    assert q11["total_sent"] == 10
    assert q11["web_sent"] == 4
    assert q11["tg_sent"] == 6
    assert q11["events_count"] == 1


def test_sync_stats_from_redis_restores_after_restart(monkeypatch, tmp_path):
    import asyncio
    import json
    import time
    from datetime import datetime
    from untils.variebles import QUEUE_LABELS

    class FakeAsyncRedis:
        def __init__(self):
            self.kv: dict[str, str] = {}
            self.hashes: dict[str, dict[str, str]] = {}
            self.lists: dict[str, list[str]] = {}
            self.ttls: dict[str, int] = {}

        async def ping(self):
            return True

        async def dbsize(self):
            return len(self.kv) + len(self.hashes) + len(self.lists)

        async def get(self, key: str):
            return self.kv.get(key)

        async def set(self, key: str, value):
            self.kv[key] = str(value)
            return True

        async def incr(self, key: str):
            return await self.incrby(key, 1)

        async def incrby(self, key: str, amount: int):
            val = int(self.kv.get(key, 0)) + int(amount)
            self.kv[key] = str(val)
            return val

        async def expire(self, key: str, seconds: int):
            self.ttls[key] = int(seconds)
            return True

        async def hgetall(self, key: str):
            return dict(self.hashes.get(key, {}))

        async def hincrby(self, key: str, field: str, amount: int):
            bucket = self.hashes.setdefault(key, {})
            val = int(bucket.get(str(field), 0)) + int(amount)
            bucket[str(field)] = str(val)
            return val

        async def hset(self, key: str, field: str, value):
            bucket = self.hashes.setdefault(key, {})
            bucket[str(field)] = str(value)
            return 1

        async def rpush(self, key: str, *values):
            lst = self.lists.setdefault(key, [])
            lst.extend(str(v) for v in values)
            return len(lst)

        async def ltrim(self, key: str, start: int, end: int):
            lst = self.lists.get(key, [])
            n = len(lst)
            s = max(0, n + start) if start < 0 else start
            e = (n + end) if end < 0 else end
            self.lists[key] = lst[s : e + 1] if s <= e else []
            return True

        async def lrange(self, key: str, start: int, end: int):
            lst = self.lists.get(key, [])
            n = len(lst)
            if n == 0:
                return []
            s = max(0, n + start) if start < 0 else start
            e = (n + end) if end < 0 else end
            if s > e or s >= n:
                return []
            return lst[s : e + 1]

    monkeypatch.setattr(stats_tracker, "STATS_DIR", str(tmp_path))
    monkeypatch.setattr(stats_tracker, "PUSH_STATS_FILE", str(tmp_path / "push_stats.json"))
    monkeypatch.setattr(stats_tracker, "GRAPH_STATS_FILE", str(tmp_path / "graph_stats.json"))

    today = datetime.now().strftime("%Y-%m-%d")
    now_ts = time.time()

    fake_redis = FakeAsyncRedis()
    fake_redis.kv["graph_requests:total"] = "250"
    fake_redis.hashes["graph_requests:by_queue"] = {"11": "100", "22": "150"}
    fake_redis.kv[f"graph_requests:daily:{today}:total"] = "30"
    fake_redis.hashes[f"graph_requests:daily:{today}:by_queue"] = {"11": "12", "22": "18"}

    fake_redis.kv["push_stats:total"] = "500"
    fake_redis.kv["push_stats:web"] = "200"
    fake_redis.kv["push_stats:tg"] = "300"
    fake_redis.kv["push_stats:events"] = "40"
    fake_redis.hashes["push_stats:by_queue:total"] = {"1.1": "320", "Всі": "180"}
    fake_redis.hashes["push_stats:by_queue:web"] = {"1.1": "120", "Всі": "80"}
    fake_redis.hashes["push_stats:by_queue:tg"] = {"1.1": "200", "Всі": "100"}
    fake_redis.hashes["push_stats:by_queue:events"] = {"1.1": "25", "Всі": "15"}
    fake_redis.hashes["push_stats:by_queue:last_sent"] = {
        "1.1": "2026-11-23 12:00:00",
        "Всі": "2026-11-23 10:00:00",
    }

    ev1 = {
        "timestamp": now_ts - 120,
        "datetime": "2026-11-23 11:58:00",
        "web_sent": 10,
        "tg_sent": 15,
        "total_sent": 25,
        "title": "Графік 1.1",
        "queue": 11,
        "queue_label": "1.1",
    }
    ev2 = {
        "timestamp": now_ts - 60,
        "datetime": "2026-11-23 11:59:00",
        "web_sent": 5,
        "tg_sent": 8,
        "total_sent": 13,
        "title": "Оголошення",
        "queue": None,
        "queue_label": "Всі",
    }
    fake_redis.lists["push_events_history"] = [
        json.dumps(ev1, ensure_ascii=False),
        json.dumps(ev2, ensure_ascii=False),
    ]

    # Simulate container restart (empty in-memory state except 1 overlapping event to test dedup)
    monkeypatch.setattr(stats_tracker, "_push_events", [dict(ev1)])
    monkeypatch.setattr(
        stats_tracker,
        "_push_all_time",
        {"total": 0, "web": 0, "tg": 0, "events_count": 0},
    )
    monkeypatch.setattr(stats_tracker, "_push_by_queue_all_time", {})
    monkeypatch.setattr(
        stats_tracker,
        "_graph_stats",
        {
            "total": 0,
            "by_queue": {str(k): 0 for k in QUEUE_LABELS.keys()},
            "daily": {},
        },
    )
    monkeypatch.setattr(stats_tracker, "_graph_recent_timestamps", [])
    monkeypatch.setattr(stats_tracker.redis_un, "get_redis_client", lambda: fake_redis)

    ok = asyncio.run(stats_tracker.sync_stats_from_redis())
    assert ok is True

    # Graph stats restored from Redis
    graph_stats = stats_tracker.get_graph_requests_stats()
    assert graph_stats["total_requests"] == 250
    assert graph_stats["today_requests"] == 30
    assert graph_stats["by_queue"]["1.1"]["total_requests"] == 100
    assert graph_stats["by_queue"]["1.1"]["today_requests"] == 12
    assert graph_stats["by_queue"]["2.2"]["total_requests"] == 150
    assert graph_stats["by_queue"]["2.2"]["today_requests"] == 18

    # Push all-time stats restored from Redis
    assert stats_tracker.get_all_time_push_stats() == {
        "total": 500,
        "web": 200,
        "tg": 300,
        "events_count": 40,
    }

    # Push history deduplicated (2 unique events, not 3)
    assert len(stats_tracker._push_events) == 2

    # Push ranking reflects restored all-time counts
    ranking = stats_tracker.get_pushes_ranking()
    q11 = next(item for item in ranking if item["label"] == "1.1")
    assert q11["total_sent"] == 320
    assert q11["web_sent"] == 120
    assert q11["tg_sent"] == 200
    assert q11["events_count"] == 25
    assert q11["last_sent"] == "2026-11-23 12:00:00"

    q_all = next(item for item in ranking if item["code"] == 0)
    assert q_all["total_sent"] == 180

    # End-to-end via /api/admin/stats endpoint
    resp = client.post("/api/admin/stats", json={"password": "my_notify_secret"})
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["pushes_all_time"]["total"] == 500
    assert stats["graph_requests"]["total_requests"] == 250
    assert stats["redis"]["status"] == "online"

    # Legacy Redis migration: no push_stats:* keys yet, only push_events_history
    legacy_redis = FakeAsyncRedis()
    legacy_redis.lists["push_events_history"] = [
        json.dumps(ev1, ensure_ascii=False),
        json.dumps(ev2, ensure_ascii=False),
    ]
    monkeypatch.setattr(stats_tracker, "_push_events", [])
    monkeypatch.setattr(
        stats_tracker,
        "_push_all_time",
        {"total": 0, "web": 0, "tg": 0, "events_count": 0},
    )
    monkeypatch.setattr(stats_tracker, "_push_by_queue_all_time", {})
    monkeypatch.setattr(stats_tracker.redis_un, "get_redis_client", lambda: legacy_redis)

    assert asyncio.run(stats_tracker.sync_stats_from_redis()) is True
    assert stats_tracker.get_all_time_push_stats() == {
        "total": 38,
        "web": 15,
        "tg": 23,
        "events_count": 2,
    }
    assert legacy_redis.kv["push_stats:total"] == "38"




