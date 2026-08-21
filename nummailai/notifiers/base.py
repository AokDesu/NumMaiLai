from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from nummailai.models import MatchResult, OutageEvent


class BaseNotifier(ABC):
    """Abstract base class for notification dispatchers."""

    @abstractmethod
    def send_outage_alert(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> bool:
        """Send a notification for an outage event."""
        pass

    @abstractmethod
    def send_test_message(self) -> bool:
        """Send a test message to verify the notification channel."""
        pass
