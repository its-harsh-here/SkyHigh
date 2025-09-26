# utils/timeutils.py
from datetime import datetime, timedelta, timezone

ISO_FMT_Z = "%Y-%m-%dT%H:%M:%SZ"

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def clamp_past_future_window(dt: datetime, max_past_days: int, max_future_hours: int):
    n = now_utc()
    if dt > n + timedelta(hours=max_future_hours):
        raise ValueError(f"Departure time cannot be more than {max_future_hours} hours in the future.")
    if dt < n - timedelta(days=max_past_days):
        raise ValueError(f"Departure time cannot be more than {max_past_days} days in the past.")

def isoformat_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO_FMT_Z)
