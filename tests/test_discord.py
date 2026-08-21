from __future__ import annotations

import unittest

from nummailai.models import DiscordConfig, MatchResult, OutageEvent
from nummailai.notifiers.discord import DiscordNotifier, get_embed_color_and_badge


class TestDiscordNotifier(unittest.TestCase):

    def setUp(self):
        self.config = DiscordConfig(
            enabled=True,
            webhook_url="https://discord.com/api/webhooks/12345/abcdef",
            username="MWA Alert (น้ำไม่ไหล)",
        )
        self.notifier = DiscordNotifier(self.config)

    def test_get_embed_color_and_badge(self):
        color_urgent, badge_urgent = get_embed_color_and_badge("ท่อแตกรั่ว", active=True)
        self.assertEqual(color_urgent, 0xE74C3C)
        self.assertIn("ฉุกเฉิน", badge_urgent)

        color_valve, badge_valve = get_embed_color_and_badge("ปิดประตูน้ำท่อประธาน", active=False)
        self.assertEqual(color_valve, 0xE67E22)

        color_conn, badge_conn = get_embed_color_and_badge("ตัดบรรจบท่อประปา", active=False)
        self.assertEqual(color_conn, 0x3498DB)

    def test_build_outage_embed(self):
        event = OutageEvent(
            event_id="abc12345",
            start_date_raw="20 ส.ค. 2569 13:30",
            finish_date_raw="21 ส.ค. 2569 00:15",
            start_datetime=None,
            finish_datetime=None,
            latitude=13.8240,
            longitude=100.4478,
            impact_branch="มหาสวัสดิ์",
            branch_code="56",
            reason="ท่อแตกรั่ว",
            impact_area="ถนนประชาอุทิศ ซอยคอกวัว น้ำไม่ไหล",
            area_name="ถนนประชาอุทิศ จุดงาน",
            pipe_size="200",
            pipe_type="PVC",
            work_person="ช่างธีรชัย",
            active=True,
            impact_branch_str="56",
        )
        match_result = MatchResult(
            matched=True,
            matched_radius=True,
            distance_km=1.85,
            summary_reasons=["📍 ห่างจากพิกัดของคุณ 1.85 กม."],
        )

        embed = self.notifier.build_outage_embed(event, match_result)
        self.assertIn("ฉุกเฉิน", embed["title"])
        self.assertIn("มหาสวัสดิ์", embed["title"])
        self.assertEqual(embed["color"], 0xE74C3C)

        field_names = [f["name"] for f in embed["fields"]]
        self.assertTrue(any("ช่วงเวลา" in n for n in field_names))
        self.assertTrue(any("จุดปฏิบัติงาน" in n for n in field_names))
        self.assertTrue(any("เหตุผลที่แจ้งเตือน" in n for n in field_names))
        self.assertTrue(any("แผนที่" in n for n in field_names))


if __name__ == "__main__":
    unittest.main()
