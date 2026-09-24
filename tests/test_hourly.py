"""Timestamps for the hourly forecast, reconstructed from labels only.

The expected values for both clock changes are the tables in docs/API.md
("Zeitumstellung: was die API tatsächlich tut"), confirmed by the API's
operator on 17.09.2026. If one of these fails, check the docs before the code.
"""

from __future__ import annotations

from datetime import datetime
from itertools import pairwise

import pytest

from custom_components.kraichtal_wetter.weather import _hourly_datetimes, _label_hour


def _iso(times: list[datetime]) -> list[str]:
    return [moment.isoformat() for moment in times]


def _assert_strictly_increasing(times: list[datetime]) -> None:
    assert all(a < b for a, b in pairwise(times)), _iso(times)


@pytest.mark.parametrize(
    ("label", "hour"),
    [
        ("00:00", 0),
        ("07:00", 7),
        ("23:00", 23),
        ("Jetzt", None),
        ("24:00", None),
        ("07:30", None),
        ("7", None),
        ("", None),
        (None, None),
        (7, None),
    ],
)
def test_label_hour(label: object, hour: int | None) -> None:
    assert _label_hour(label) == hour


def test_recorded_response() -> None:
    """The series from 24.09.2026, 07:51 — "Jetzt" is the hour before 08:00."""
    labels = ["Jetzt"] + [f"{hour:02d}:00" for hour in range(8, 19)]
    times = _hourly_datetimes(datetime.fromisoformat("2026-09-24T07:51:05+02:00"), labels)

    assert _iso(times) == [f"2026-09-24T{hour:02d}:00:00+02:00" for hour in range(7, 19)]


def test_generated_in_another_zone() -> None:
    """`generated` only picks the day; its own offset must not matter."""
    labels = ["Jetzt", "08:00", "09:00"]
    berlin = _hourly_datetimes(datetime.fromisoformat("2026-09-24T07:51:05+02:00"), labels)
    utc = _hourly_datetimes(datetime.fromisoformat("2026-09-24T05:51:05+00:00"), labels)

    assert berlin == utc


def test_past_midnight() -> None:
    labels = ["Jetzt", "23:00", "00:00", "01:00"]
    times = _hourly_datetimes(datetime.fromisoformat("2026-09-24T22:10:00+02:00"), labels)

    assert _iso(times) == [
        "2026-09-24T22:00:00+02:00",
        "2026-09-24T23:00:00+02:00",
        "2026-09-25T00:00:00+02:00",
        "2026-09-25T01:00:00+02:00",
    ]


def test_first_label_already_tomorrow() -> None:
    """Generated at 23:50, the first labelled hour is 00:00 of the next day."""
    times = _hourly_datetimes(
        datetime.fromisoformat("2026-09-24T23:50:00+02:00"), ["Jetzt", "00:00", "01:00"]
    )

    assert _iso(times) == [
        "2026-09-24T23:00:00+02:00",
        "2026-09-25T00:00:00+02:00",
        "2026-09-25T01:00:00+02:00",
    ]


def test_october_one_label_for_the_repeated_hour() -> None:
    """25.10.2026: exactly one "02:00", then "03:00" (table in docs/API.md)."""
    labels = ["Jetzt", "00:00", "01:00", "02:00", "03:00", "04:00"]
    times = _hourly_datetimes(datetime.fromisoformat("2026-10-24T23:10:00+02:00"), labels)

    assert _iso(times) == [
        "2026-10-24T23:00:00+02:00",
        "2026-10-25T00:00:00+02:00",
        "2026-10-25T01:00:00+02:00",
        "2026-10-25T02:00:00+02:00",  # first pass through the repeated hour
        "2026-10-25T03:00:00+01:00",  # two real hours later: the jump in the data
        "2026-10-25T04:00:00+01:00",
    ]
    _assert_strictly_increasing(times)


def test_march_missing_hour() -> None:
    """29.03.2026: "02:00" does not exist, "01:00" is followed by "03:00"."""
    labels = ["Jetzt", "00:00", "01:00", "03:00", "04:00"]
    times = _hourly_datetimes(datetime.fromisoformat("2026-03-28T23:10:00+01:00"), labels)

    assert _iso(times) == [
        "2026-03-28T23:00:00+01:00",
        "2026-03-29T00:00:00+01:00",
        "2026-03-29T01:00:00+01:00",
        "2026-03-29T03:00:00+02:00",  # one real hour later
        "2026-03-29T04:00:00+02:00",
    ]
    _assert_strictly_increasing(times)


def test_now_in_the_repeated_hour() -> None:
    """Fetched during the second pass through 02:00 in October.

    "Jetzt" has no label to correct it, so this is where stepping back in UTC
    matters: on the wall clock, one hour before 03:00 would be the *first*
    02:00 — two real hours earlier.
    """
    times = _hourly_datetimes(
        datetime.fromisoformat("2026-10-25T02:30:00+01:00"), ["Jetzt", "03:00", "04:00"]
    )

    assert _iso(times) == [
        "2026-10-25T02:00:00+01:00",
        "2026-10-25T03:00:00+01:00",
        "2026-10-25T04:00:00+01:00",
    ]


def test_now_after_the_missing_hour() -> None:
    times = _hourly_datetimes(datetime.fromisoformat("2026-03-29T03:20:00+02:00"), ["Jetzt", "04:00"])

    assert _iso(times) == ["2026-03-29T03:00:00+02:00", "2026-03-29T04:00:00+02:00"]


def test_gap_follows_the_label() -> None:
    """A skipped hour outside the clock changes: the label wins over the step."""
    times = _hourly_datetimes(
        datetime.fromisoformat("2026-09-24T07:51:05+02:00"), ["Jetzt", "08:00", "10:00", "11:00"]
    )

    assert _iso(times)[1:] == [
        "2026-09-24T08:00:00+02:00",
        "2026-09-24T10:00:00+02:00",
        "2026-09-24T11:00:00+02:00",
    ]


def test_unreadable_label_follows_the_hour_before() -> None:
    times = _hourly_datetimes(
        datetime.fromisoformat("2026-09-24T07:51:05+02:00"), ["Jetzt", "08:00", None, "xx", "11:00"]
    )

    assert [moment.hour for moment in times] == [7, 8, 9, 10, 11]


def test_no_label_at_all() -> None:
    """Without any readable label the series starts at the hour of `generated`."""
    times = _hourly_datetimes(datetime.fromisoformat("2026-09-24T07:51:05+02:00"), ["Jetzt", None])

    assert _iso(times) == ["2026-09-24T07:00:00+02:00", "2026-09-24T08:00:00+02:00"]


def test_empty() -> None:
    assert _hourly_datetimes(datetime.fromisoformat("2026-09-24T07:51:05+02:00"), []) == []
