"""Office hours calculation and timing utilities."""

import os
from datetime import datetime, timezone, timedelta, time as dtime
import zoneinfo

def is_office_hours(
    now: datetime | None = None,
    tz_name: str | None = None,
    start_hour: int | None = None,
    end_hour: int | None = None,
    weekdays_only: bool | None = None,
) -> tuple[bool, int, str]:
    """Check if current time is within business office hours (default: 8:00 AM - 5:00 PM CST, Mon-Fri).

    Returns:
        (is_open: bool, wait_seconds: int, status_message: str)
        If is_open is False, wait_seconds is seconds until the next 8:00 AM opening window.
        If is_open is True, wait_seconds is seconds until 5:00 PM closing.
    """
    if now is None and os.environ.get("SCOUT_FORCE_OFFICE_HOURS", "").lower() == "true":
        return True, 3600, "Office hours forced active by configuration"

    tz_str = tz_name or os.environ.get("SCOUT_TIMEZONE", "US/Central")
    try:
        tz = zoneinfo.ZoneInfo(tz_str)
    except Exception:
        try:
            tz = zoneinfo.ZoneInfo("US/Central")
            tz_str = "US/Central"
        except Exception:
            # Resilient fallback when tzdata is missing on slim Linux environments
            tz = timezone(timedelta(hours=-5), name="US/Central")
            tz_str = "US/Central"

    sh = int(start_hour if start_hour is not None else os.environ.get("SCOUT_OFFICE_HOURS_START", "8"))
    eh = int(end_hour if end_hour is not None else os.environ.get("SCOUT_OFFICE_HOURS_END", "17"))
    wd_only = (
        weekdays_only
        if weekdays_only is not None
        else os.environ.get("SCOUT_WEEKDAYS_ONLY", "true").lower() == "true"
    )

    current = now or datetime.now(tz)
    if current.tzinfo is None:
        current = current.replace(tzinfo=tz)
    else:
        current = current.astimezone(tz)

    weekday = current.weekday()  # 0 = Monday, ..., 6 = Sunday
    is_weekday = weekday < 5

    in_time_window = (current.hour > sh or (current.hour == sh and current.minute >= 0)) and (current.hour < eh)

    if (not wd_only or is_weekday) and in_time_window:
        close_time = current.replace(hour=eh, minute=0, second=0, microsecond=0)
        remaining_seconds = max(60, int((close_time - current).total_seconds()))
        return True, remaining_seconds, f"Office hours active (8:00 AM - 5:00 PM {tz_str})"

    # If outside office hours, compute next opening window
    candidate_date = current.date()
    if current.hour >= eh or (wd_only and not is_weekday) or (current.hour < sh and wd_only and not is_weekday):
        candidate_date += timedelta(days=1)

    while True:
        candidate_dt = datetime.combine(candidate_date, dtime(sh, 0), tzinfo=tz)
        candidate_weekday = candidate_dt.weekday()
        if not wd_only or candidate_weekday < 5:
            if candidate_dt > current:
                wait_sec = max(60, int((candidate_dt - current).total_seconds()))
                return False, wait_sec, f"Standing by for office hours ({sh}:00 AM - {eh}:00 PM {tz_str}). Resumes at {sh}:00 AM."
        candidate_date += timedelta(days=1)
