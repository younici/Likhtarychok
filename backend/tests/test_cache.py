import asyncio
import time

from untils import cache


def test_request_does_not_hang_when_source_hangs(monkeypatch):
    async def slow_schedule():
        await asyncio.sleep(60)

    monkeypatch.setattr(cache.tools, "get_schedule", slow_schedule)
    monkeypatch.setattr(cache, "REQUEST_WAIT_TIMEOUT", 0.3)
    monkeypatch.setattr(cache, "_cache", None)
    monkeypatch.setattr(cache, "_refresh_task", None)
    monkeypatch.setattr(cache, "_last_on_demand", 0.0)
    monkeypatch.setattr(cache, "_first_boot", False)
    monkeypatch.setattr(cache, "_lock", asyncio.Lock())

    async def run():
        t = time.monotonic()
        results = await asyncio.gather(*(cache.get_cache(11) for _ in range(5)))
        elapsed = time.monotonic() - t
        cache._refresh_task.cancel()
        return results, elapsed

    results, elapsed = asyncio.run(run())
    assert results == [None] * 5
    assert elapsed < 2
