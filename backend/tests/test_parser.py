import asyncio

from untils import tools


def _slot(off: bool, color_on: str = "#ffffff", color_off: str = "#ff3333") -> str:
    color = color_off if off else color_on
    return f'<td style="text-align:center; background: {color}"><a href="#">&nbsp;</a></td>'


def _page(
    days: list[tuple[str, int]],
    extra_table: bool = False,
    slots_per_day: int = 48,
    color_on: str = "#ffffff",
    color_off: str = "#ff3333",
) -> str:
    """days: [(date, shift)] - each day block gets a pattern shifted by `shift`."""
    header = "".join(f'<td colspan="{slots_per_day}"><b>{d}</b></td>' for d, _ in days)
    rows = []
    for q in range(1, 7):
        for sub in (1, 2):
            code = q * 10 + sub
            slots = "".join(
                _slot((i + code + shift) % 5 == 0, color_on=color_on, color_off=color_off)
                for _, shift in days
                for i in range(slots_per_day)
            )
            lead = f'<td rowspan="2" style="background: white">{q}</td>' if sub == 1 else ""
            rows.append(
                f'<tr>{lead}<td style="background: white">{q}.{sub}</td>'
                f'<td style="width:3pt"></td>{slots}</tr>'
            )
    pre = "<table><tr><td>banner</td></tr></table>" if extra_table else ""
    return (
        f"<html><body>{pre}<table><tr><td>wrapper</td></tr></table>"
        f'<table><tr><td rowspan="2">Черга</td><td rowspan="2">Підчерга</td>'
        f'<td style="width:3pt"></td>{header}</tr>{"".join(rows)}</table></body></html>'
    )


def _expected(code: int, shift: int) -> list[int]:
    return [1 if (i + code + shift) % 5 == 0 else 0 for i in range(48)]


def test_parse_schedule_single_day():
    res = tools.parse_schedule(_page([("22.11.2026", 0)]), "22.11.2026")
    assert res["date"] == "22.11.2026"
    assert len(res["queues"]) == 12
    for code, status in res["queues"].items():
        assert status == _expected(code, 0)


def test_parse_schedule_picks_today_when_two_days_and_extra_tables():
    html = _page([("22.11.2026", 0), ("23.11.2026", 2)], extra_table=True)
    today = tools.parse_schedule(html, "22.11.2026")
    tomorrow = tools.parse_schedule(html, "23.11.2026")
    assert all(today["queues"][c] == _expected(c, 0) for c in today["queues"])
    assert tomorrow["date"] == "23.11.2026"
    assert all(tomorrow["queues"][c] == _expected(c, 2) for c in tomorrow["queues"])


def test_parse_schedule_24_hourly_and_css_variants():
    html = _page(
        [("23.11.2026", 0)],
        slots_per_day=24,
        color_on="rgb(255, 255, 255) !important",
        color_off="#ff3333 !important",
    )
    res = tools.parse_schedule(html, "23.11.2026")
    assert res is not None
    assert len(res["queues"]) == 12
    for code, status in res["queues"].items():
        assert len(status) == 48
        expected_24 = [1 if (i + code) % 5 == 0 else 0 for i in range(24)]
        assert status == [v for v in expected_24 for _ in range(2)]


def test_parse_schedule_garbage_returns_none():
    assert tools.parse_schedule("<html><table><tr><td>x</td></tr></table></html>") is None


def test_get_schedule_falls_back_to_proxy_and_sticks(monkeypatch):
    valid_html = _page([(tools.today_str(), 0)])
    calls: list[str] = []

    async def fake_fetch(source: dict):
        calls.append(source["name"])
        if source["name"] == "direct_https":
            return None  # simulated datacenter IP block / timeout
        if source["name"] == "direct_http":
            return "<html><body>blocked</body></html>"  # HTTP 200 garbage
        if source["name"] == "jina_https":
            return valid_html
        return None

    monkeypatch.setattr(tools, "_fetch_source", fake_fetch)
    monkeypatch.setattr(tools, "_preferred_source", None)
    monkeypatch.setattr(tools, "_last_direct_probe", 0.0)

    res1 = asyncio.run(tools.get_schedule())
    assert res1 is not None
    assert len(res1["queues"]) == 12
    assert calls == ["direct_https", "direct_http", "jina_https"]
    assert tools._preferred_source == "jina_https"

    # Second call should immediately use sticky jina_https without hitting blocked direct sources.
    calls.clear()
    res2 = asyncio.run(tools.get_schedule())
    assert res2 is not None
    assert calls == ["jina_https"]
