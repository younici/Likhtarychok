from untils import tools


def _slot(off: bool) -> str:
    color = "#ff3333" if off else "#ffffff"
    return f'<td style="text-align:center; background: {color}"><a href="#">&nbsp;</a></td>'


def _page(days: list[tuple[str, int]], extra_table: bool = False) -> str:
    """days: [(date, shift)] - each day block gets a pattern shifted by `shift`."""
    header = "".join(f'<td colspan="48"><b>{d}</b></td>' for d, _ in days)
    rows = []
    for q in range(1, 7):
        for sub in (1, 2):
            code = q * 10 + sub
            slots = "".join(
                _slot((i + code + shift) % 5 == 0) for _, shift in days for i in range(48)
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


def test_parse_schedule_garbage_returns_none():
    assert tools.parse_schedule("<html><table><tr><td>x</td></tr></table></html>") is None
