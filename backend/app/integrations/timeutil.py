"""Conversões de tempo usadas pelos adaptadores. Tudo sai em UTC com fuso explícito."""

from __future__ import annotations

from datetime import UTC, date, datetime, time


def parse_utc(value: str) -> datetime:
    """ISO 8601 com ou sem segundos/fuso ("2024-05-10T06:27Z", "2024-05-10 00:31:45").

    Sem fuso explícito, a fonte documenta UTC; o valor é marcado como UTC.
    """
    dt = datetime.fromisoformat(value.strip().replace(" ", "T", 1))
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def day_start(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


def day_end(d: date) -> datetime:
    return datetime.combine(d, time.max, tzinfo=UTC)
