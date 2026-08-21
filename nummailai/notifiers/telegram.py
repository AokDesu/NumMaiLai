from __future__ import annotations

import logging
from typing import Optional
import requests

from nummailai.models import MatchResult, OutageEvent, TelegramConfig
from nummailai.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Dispatches alerts to Telegram via Bot API."""

    def __init__(self, config: TelegramConfig):
        self.config = config

    def format_outage_message(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> str:
        """Format an outage alert in Telegram HTML format."""
        badge = "🚨 <b>ท่อประปาแตกรั่ว (ฉุกเฉิน)</b>" if event.is_urgent else "🔧 <b>ประกาศตัดบรรจบ/ซ่อมบำรุงท่อ</b>"
        status_tag = "🔴 กำลังดำเนินการ" if event.active else "🟡 มีแผนงาน"

        lines = [
            f"{badge} - สาขา{event.impact_branch or 'การประปา'}",
            f"<b>สถานะ:</b> {status_tag}",
            "",
            f"💧 <b>พื้นที่ได้รับผลกระทบ:</b>",
            f"{event.impact_area or 'โปรดตรวจสอบรายละเอียดเพิ่มเติม'}",
            "",
            f"⏱️ <b>ช่วงเวลา:</b> {event.start_date_raw} ถึง {event.finish_date_raw}",
            f"📍 <b>จุดปฏิบัติงาน:</b> {event.area_name or '-'}",
            f"🎯 <b>เงื่อนไขที่ตรงกับคุณ:</b> {match_result.reason_text}",
        ]

        if event.pipe_size and event.pipe_size != "0":
            lines.append(f"🛠️ <b>ขนาดท่อ:</b> {event.pipe_size} มม. ({event.pipe_type})")

        if event.has_coordinates:
            lines.append(f'🗺️ <a href="{event.google_maps_url}">เปิดดูบน Google Maps</a>')

        return "\n".join(lines)

    def send_message(self, text: str) -> bool:
        """Send message via Telegram Bot API."""
        if not self.config.enabled:
            return False

        token = self.config.bot_token.strip()
        chat_id = self.config.chat_id.strip()
        if not token or not chat_id:
            logger.warning("Telegram bot token or chat ID is missing.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            res = requests.post(url, json=payload, timeout=10)
            if res.status_code == 200:
                logger.info("Successfully sent Telegram notification.")
                return True
            else:
                logger.error("Telegram API returned %d: %s", res.status_code, res.text)
                return False
        except Exception as e:
            logger.error("Error sending Telegram message: %s", e)
            return False

    def send_outage_alert(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> bool:
        text = self.format_outage_message(event, match_result)
        return self.send_message(text)

    def send_test_message(self) -> bool:
        text = (
            "✅ <b>ทดสอบระบบแจ้งเตือนน้ำไม่ไหล (NumMaiLai)</b>\n"
            "การเชื่อมต่อ Telegram Bot สำเร็จเรียบร้อยแล้ว!"
        )
        return self.send_message(text)
