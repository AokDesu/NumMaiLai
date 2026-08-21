from __future__ import annotations

import logging
from nummailai.models import MatchResult, OutageEvent
from nummailai.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class ConsoleNotifier(BaseNotifier):
    """Outputs alerts directly to terminal console with formatting."""

    def send_outage_alert(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> bool:
        badge = "🚨 [ฉุกเฉิน: ท่อแตกรั่ว]" if event.is_urgent else "🔧 [งานซ่อม/ตัดบรรจบท่อ]"
        status = "กำลังดำเนินการ" if event.active else "มีแผนงาน"
        
        print("\n" + "=" * 60)
        print(f"{badge} สาขา{event.impact_branch}")
        print(f"สถานะ: {status} | เหตุผล: {event.reason}")
        print(f"ช่วงเวลา: {event.start_date_raw} ถึง {event.finish_date_raw}")
        print(f"จุดงาน: {event.area_name}")
        print(f"พื้นที่ผลกระทบ: {event.impact_area}")
        print(f"เงื่อนไขที่ตรงกับคุณ: {match_result.reason_text}")
        if event.has_coordinates:
            print(f"พิกัด: {event.latitude}, {event.longitude} ({event.google_maps_url})")
        print("=" * 60 + "\n")
        return True

    def send_test_message(self) -> bool:
        print("\n[Console Notifier] ✅ Test message successful.\n")
        return True
