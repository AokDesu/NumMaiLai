from __future__ import annotations

import math
import re
from typing import List, Optional

from nummailai.models import MatchResult, MatchingConfig, OutageEvent


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate geodesic distance in kilometers between two GPS coordinates using the Haversine formula."""
    earth_radius_km = 6371.0088

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return earth_radius_km * c


def normalize_text(text: Optional[str]) -> str:
    """Normalize Thai and English text for robust keyword matching."""
    if not text:
        return ""
    # Strip zero-width spaces and control characters
    cleaned = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", str(text))
    # Replace multiple whitespaces with single space and lowercase
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


class AreaMatcher:
    """Evaluates whether an OutageEvent falls within the user's targeted area."""

    def __init__(self, config: MatchingConfig):
        self.config = config

    def match(self, event: OutageEvent) -> MatchResult:
        """Evaluate event against configured radius, keyword, and branch rules."""
        matched_radius = False
        distance_km: Optional[float] = None
        matched_keywords: List[str] = []
        matched_branch = False
        matched_branch_name: Optional[str] = None
        reasons: List[str] = []

        mode = (self.config.mode or "hybrid").lower().strip()

        # 1. Evaluate Proximity / Radius Filter
        loc_cfg = self.config.location
        if (
            loc_cfg.enabled
            and loc_cfg.latitude != 0.0
            and loc_cfg.longitude != 0.0
            and event.has_coordinates
        ):
            distance_km = haversine_distance(
                loc_cfg.latitude,
                loc_cfg.longitude,
                event.latitude,  # type: ignore
                event.longitude,  # type: ignore
            )
            if distance_km <= loc_cfg.radius_km:
                matched_radius = True
                reasons.append(
                    f"📍 ห่างจากพิกัดของคุณ {distance_km:.2f} กม. (รัศมี {loc_cfg.radius_km:.1f} กม.)"
                )

        # 2. Evaluate Keyword Search Filter
        kw_cfg = self.config.keywords
        if kw_cfg.enabled and kw_cfg.terms:
            searchable_corpus = normalize_text(
                f"{event.impact_area} {event.area_name} {event.impact_branch} {event.reason}"
            )
            for term in kw_cfg.terms:
                clean_term = normalize_text(term)
                if clean_term and clean_term in searchable_corpus:
                    matched_keywords.append(term.strip())

            if matched_keywords:
                reasons.append(f"🔑 ตรงกับคำค้นหา: {', '.join(matched_keywords)}")

        # 3. Evaluate Branch Filter
        br_cfg = self.config.branches
        if br_cfg.enabled and br_cfg.names:
            event_branches = [
                b.strip().lower()
                for b in event.impact_branch.split(",")
                if b.strip()
            ]
            for target_branch in br_cfg.names:
                clean_target = target_branch.strip().lower()
                # Check branch name or branch code
                if (
                    clean_target in [b.lower() for b in event_branches]
                    or clean_target == event.branch_code.lower()
                    or any(clean_target in b for b in event_branches)
                ):
                    matched_branch = True
                    matched_branch_name = target_branch
                    break

            if matched_branch:
                reasons.append(f"🏢 ตรงกับสาขา: {matched_branch_name or event.impact_branch}")

        # 4. Mode Resolution Logic
        if mode == "radius_only":
            is_matched = matched_radius
        elif mode == "keywords_only":
            is_matched = len(matched_keywords) > 0
        elif mode == "branch_only":
            is_matched = matched_branch
        elif mode in ("all", "and"):
            # All enabled criteria must match
            active_checks = []
            if loc_cfg.enabled and loc_cfg.latitude != 0.0:
                active_checks.append(matched_radius)
            if kw_cfg.enabled and kw_cfg.terms:
                active_checks.append(len(matched_keywords) > 0)
            if br_cfg.enabled and br_cfg.names:
                active_checks.append(matched_branch)
            is_matched = all(active_checks) if active_checks else False
        else:
            # Default 'hybrid' / 'or' mode: Trigger if ANY active rule matches
            is_matched = matched_radius or len(matched_keywords) > 0 or matched_branch

        return MatchResult(
            matched=is_matched,
            matched_radius=matched_radius,
            distance_km=distance_km,
            matched_keywords=matched_keywords,
            matched_branch=matched_branch,
            matched_branch_name=matched_branch_name,
            summary_reasons=reasons,
        )
