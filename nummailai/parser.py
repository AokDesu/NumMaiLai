from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Optional

from nummailai.models import OutageEvent

THAI_MONTHS: Dict[str, int] = {
    "ม.ค.": 1,
    "ก.พ.": 2,
    "มี.ค.": 3,
    "เม.ย.": 4,
    "พ.ค.": 5,
    "มิ.ย.": 6,
    "ก.ค.": 7,
    "ส.ค.": 8,
    "ก.ย.": 9,
    "ต.ค.": 10,
    "พ.ย.": 11,
    "ธ.ค.": 12,
    # Full names in case MWA changes format
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}


def parse_thai_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Parse Thai Buddhist Era datetime string into a standard datetime object.

    Example inputs:
      '20 ส.ค. 2569 13:30'
      '21 ส.ค. 2569 00:15'
    """
    if not date_str or not isinstance(date_str, str):
        return None

    cleaned = date_str.strip()
    # Pattern: Day Month Year_BE Hour:Minute
    match = re.match(
        r"^(\d{1,2})\s+([^\s]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", cleaned
    )
    if match:
        day_str, month_str, year_be_str, hour_str, min_str = match.groups()
        month = THAI_MONTHS.get(month_str)
        if not month:
            # Try partial match if month has dots or extra characters
            for th_m, m_num in THAI_MONTHS.items():
                if th_m in month_str or month_str in th_m:
                    month = m_num
                    break
        if month:
            year_be = int(year_be_str)
            year_ce = year_be - 543 if year_be > 2400 else year_be
            hour = int(hour_str) if hour_str is not None else 0
            minute = int(min_str) if min_str is not None else 0
            try:
                return datetime(year_ce, month, int(day_str), hour, minute)
            except ValueError:
                pass

    # Try ISO standard format as fallback
    try:
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        pass

    return None


def parse_float(val: Any) -> Optional[float]:
    """Parse float coordinate safely, returning None on empty or invalid values."""
    if val is None:
        return None
    try:
        val_str = str(val).strip()
        if not val_str or val_str.lower() in ("null", "none", "0", "0.0"):
            return None
        parsed = float(val_str)
        # Verify valid Bangkok/Thailand coordinate ranges (~5-21 lat, ~97-106 lng)
        if 5.0 <= parsed <= 106.0:
            return parsed
        return parsed
    except (ValueError, TypeError):
        return None


def generate_event_id(item: Dict[str, Any]) -> str:
    """Generate a deterministic SHA256 hash representing the unique incident.

    Uses primary incident attributes: branch, start/end dates, location coords, area name, and reason.
    """
    start = str(item.get("startdate", "")).strip()
    finish = str(item.get("finishdate", "")).strip()
    branch = str(item.get("branchcode") or item.get("impactbranch", "")).strip()
    lat = str(item.get("latitude", "")).strip()
    lng = str(item.get("longtitude", "")).strip()
    area = str(item.get("areaname", "")).strip()
    reason = str(item.get("reason", "")).strip()

    fingerprint = f"{branch}|{start}|{finish}|{lat}|{lng}|{area}|{reason}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]


def parse_raw_event(raw: Dict[str, Any]) -> OutageEvent:
    """Parse a single raw MWA dictionary into a validated OutageEvent dataclass."""
    start_raw = str(raw.get("startdate", "")).strip()
    finish_raw = str(raw.get("finishdate", "")).strip()
    lat = parse_float(raw.get("latitude"))
    lng = parse_float(raw.get("longtitude"))

    active_raw = str(raw.get("active", "0")).strip()
    is_active = active_raw == "1"

    event_id = generate_event_id(raw)

    return OutageEvent(
        event_id=event_id,
        start_date_raw=start_raw,
        finish_date_raw=finish_raw,
        start_datetime=parse_thai_datetime(start_raw),
        finish_datetime=parse_thai_datetime(finish_raw),
        latitude=lat,
        longitude=lng,
        impact_branch=str(raw.get("impactbranch", "")).strip(),
        branch_code=str(raw.get("branchcode", "")).strip(),
        reason=str(raw.get("reason", "")).strip(),
        impact_area=str(raw.get("impactarea", "")).strip(),
        area_name=str(raw.get("areaname", "")).strip(),
        pipe_size=str(raw.get("pipesize", "")).strip(),
        pipe_type=str(raw.get("pipetype", "")).strip(),
        work_person=str(raw.get("workperson", "")).strip(),
        active=is_active,
        impact_branch_str=str(raw.get("impactbranchstr", "")).strip(),
    )
