import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from untils import notifier


@pytest.fixture(autouse=True)
def clear_notified_slots():
    notifier.notified_slots.clear()
    yield
    notifier.notified_slots.clear()


def test_power_on_notification_48_slots():
    """
    Test 1: When in a 48-slot schedule at 13:30 (slot 27) status is 1 (off)
    and at 14:00 (slot 28) status is 0 (on), _process_queue_schedule sends
    a power-on warning for queue 31 (label 3.1) at 14:00.
    """
    status = [0] * 48
    status[27] = 1
    status[28] = 0

    now = datetime(2026, 11, 8, 13, 30)

    with patch("untils.notifier.send_push_all", new_callable=AsyncMock) as mock_send:
        asyncio.run(notifier._process_queue_schedule(31, status, now))

        mock_send.assert_awaited_once_with(
            title="Скоро увімкнуть світло",
            body="Світло увімкнуть через пів години у 14:00 по черзі 3.1.",
            queue=31,
        )


def test_power_on_deduplication():
    """
    Test 2: Repeated call for the same slot on the same day does not send a duplicate.
    """
    status = [0] * 48
    status[27] = 1
    status[28] = 0

    now = datetime(2026, 11, 8, 13, 30)

    with patch("untils.notifier.send_push_all", new_callable=AsyncMock) as mock_send:
        asyncio.run(notifier._process_queue_schedule(31, status, now))
        assert mock_send.await_count == 1

        # Second call with the same slot and date should be ignored
        asyncio.run(notifier._process_queue_schedule(31, status, now))
        assert mock_send.await_count == 1


def test_power_off_notification_still_works():
    """
    Test 3: Power-off notification (0 -> 1) continues to work as before.
    """
    status = [0] * 48
    status[26] = 0
    status[27] = 1

    now = datetime(2026, 11, 8, 13, 0)

    with patch("untils.notifier.send_push_all", new_callable=AsyncMock) as mock_send:
        asyncio.run(notifier._process_queue_schedule(31, status, now))

        mock_send.assert_awaited_once_with(
            title="Скоро відключать світло",
            body="По графіку (черга 3.1) світло відключать в 13:30.",
            queue=31,
        )


def test_power_on_notification_24_slots():
    """
    Test 4: 24-slot schedule power-on warning at half-past hour (13:30).
    """
    status = [0] * 24
    status[13] = 1
    status[14] = 0

    now = datetime(2026, 11, 8, 13, 30)

    with patch("untils.notifier.send_push_all", new_callable=AsyncMock) as mock_send:
        asyncio.run(notifier._process_queue_schedule(31, status, now))

        mock_send.assert_awaited_once_with(
            title="Скоро увімкнуть світло",
            body="Світло увімкнуть через пів години у 14:00 по черзі 3.1.",
            queue=31,
        )


def test_power_on_24_slots_not_triggered_before_half_hour():
    """
    Test 5: 24-slot schedule does not trigger power-on notification if minute < 30.
    """
    status = [0] * 24
    status[13] = 1
    status[14] = 0

    now = datetime(2026, 11, 8, 13, 15)

    with patch("untils.notifier.send_push_all", new_callable=AsyncMock) as mock_send:
        asyncio.run(notifier._process_queue_schedule(31, status, now))

        mock_send.assert_not_called()
