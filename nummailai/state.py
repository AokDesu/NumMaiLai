from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from nummailai.models import MatchResult, OutageEvent

logger = logging.getLogger(__name__)


class StateManager:
    """Manages persistent tracking of notified events to prevent duplicate spam."""

    def __init__(self, state_file_path: str = "data/state.json"):
        self.state_path = Path(state_file_path)
        self.state: Dict[str, Any] = {"notified_events": {}, "last_run_at": None}
        self.load()

    def load(self) -> None:
        """Load state from JSON file."""
        if not self.state_path.exists():
            self.state = {"notified_events": {}, "last_run_at": None}
            return

        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.state = data
                    if "notified_events" not in self.state:
                        self.state["notified_events"] = {}
                logger.debug(
                    "Loaded state with %d notified events from %s",
                    len(self.state.get("notified_events", {})),
                    self.state_path,
                )
        except Exception as e:
            logger.warning("Error reading state file %s, initializing fresh: %s", self.state_path, e)
            self.state = {"notified_events": {}, "last_run_at": None}

    def save(self) -> None:
        """Persist state to JSON file atomically."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.state_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            temp_file.replace(self.state_path)
            logger.debug("Successfully saved state to %s", self.state_path)
        except Exception as e:
            logger.error("Failed to save state to %s: %s", self.state_path, e)

    def is_already_notified(self, event_id: str) -> bool:
        """Check if an event ID has already been notified."""
        return event_id in self.state.get("notified_events", {})

    def mark_notified(
        self,
        event: OutageEvent,
        match_result: Optional[MatchResult] = None,
    ) -> None:
        """Record an event as notified with timestamp and metadata."""
        now_iso = datetime.now(timezone.utc).isoformat()
        if "notified_events" not in self.state:
            self.state["notified_events"] = {}

        self.state["notified_events"][event.event_id] = {
            "notified_at": now_iso,
            "reason": event.reason,
            "branch": event.impact_branch,
            "area_name": event.area_name,
            "start_date": event.start_date_raw,
            "finish_date": event.finish_date_raw,
            "active": event.active,
            "match_reasons": match_result.summary_reasons if match_result else [],
        }
        self.state["last_run_at"] = now_iso
        self.save()

    def update_last_run(self) -> None:
        """Update the last run timestamp in state."""
        self.state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        self.save()

    def clear(self) -> None:
        """Clear all stored state (useful for testing or reset)."""
        self.state = {"notified_events": {}, "last_run_at": None}
        self.save()
