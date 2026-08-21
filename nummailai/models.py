from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class OutageEvent:
    """Represents a single water supply outage or pipe maintenance event from MWA."""
    event_id: str
    start_date_raw: str
    finish_date_raw: str
    start_datetime: Optional[datetime]
    finish_datetime: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    impact_branch: str
    branch_code: str
    reason: str
    impact_area: str
    area_name: str
    pipe_size: str
    pipe_type: str
    work_person: str
    active: bool
    impact_branch_str: str

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def google_maps_url(self) -> str:
        if self.has_coordinates:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        return ""

    @property
    def is_urgent(self) -> bool:
        urgent_keywords = ["ท่อแตก", "ท่อรั่ว", "แตกรั่ว", "ฉุกเฉิน"]
        return any(k in self.reason for k in urgent_keywords) or (self.active and "ท่อ" in self.reason)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "start_date_raw": self.start_date_raw,
            "finish_date_raw": self.finish_date_raw,
            "start_datetime": self.start_datetime.isoformat() if self.start_datetime else None,
            "finish_datetime": self.finish_datetime.isoformat() if self.finish_datetime else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "impact_branch": self.impact_branch,
            "branch_code": self.branch_code,
            "reason": self.reason,
            "impact_area": self.impact_area,
            "area_name": self.area_name,
            "pipe_size": self.pipe_size,
            "pipe_type": self.pipe_type,
            "work_person": self.work_person,
            "active": self.active,
            "impact_branch_str": self.impact_branch_str,
            "google_maps_url": self.google_maps_url,
            "is_urgent": self.is_urgent,
        }


@dataclass
class MatchResult:
    """Result of evaluating an OutageEvent against user area criteria."""
    matched: bool
    matched_radius: bool = False
    distance_km: Optional[float] = None
    matched_keywords: List[str] = field(default_factory=list)
    matched_branch: bool = False
    matched_branch_name: Optional[str] = None
    summary_reasons: List[str] = field(default_factory=list)

    @property
    def reason_text(self) -> str:
        if not self.summary_reasons:
            return "ไม่ระบุเงื่อนไข"
        return " | ".join(self.summary_reasons)


@dataclass
class LocationConfig:
    enabled: bool = True
    latitude: float = 0.0
    longitude: float = 0.0
    radius_km: float = 5.0


@dataclass
class KeywordsConfig:
    enabled: bool = True
    terms: List[str] = field(default_factory=list)


@dataclass
class BranchesConfig:
    enabled: bool = False
    names: List[str] = field(default_factory=list)


@dataclass
class MatchingConfig:
    mode: str = "hybrid"  # hybrid, radius_only, keywords_only, branch_only
    location: LocationConfig = field(default_factory=LocationConfig)
    keywords: KeywordsConfig = field(default_factory=KeywordsConfig)
    branches: BranchesConfig = field(default_factory=BranchesConfig)


@dataclass
class DiscordConfig:
    enabled: bool = True
    webhook_url: str = ""
    username: str = "MWA Alert (น้ำไม่ไหล)"
    avatar_url: str = "https://gisonline.mwa.co.th/GIS1125/SRC/resources/mwa-icon.png"


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class PollingConfig:
    interval_minutes: int = 15
    state_file: str = "data/state.json"


@dataclass
class AppConfig:
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    discord: DiscordConfig = field(default_factory=DiscordConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    polling: PollingConfig = field(default_factory=PollingConfig)
