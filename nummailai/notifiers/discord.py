from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests

from nummailai.models import DiscordConfig, MatchResult, OutageEvent
from nummailai.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


def get_embed_color_and_badge(reason: str, active: bool) -> tuple[int, str]:
    """Return Discord embed decimal color and emoji badge based on reason and status."""
    reason_clean = reason.lower()
    if any(k in reason_clean for k in ["ท่อแตก", "แตกรั่ว", "ท่อรั่ว", "ฉุกเฉิน"]):
        return 0xE74C3C, "🚨 ฉุกเฉิน: ท่อประปาแตกรั่ว"  # Red
    elif "ปิดประตูน้ำ" in reason_clean:
        return 0xE67E22, "⚠️ ปิดประตูน้ำท่อประธาน"  # Orange
    elif "ตัดบรรจบ" in reason_clean:
        return 0x3498DB, "🔧 งานตัดบรรจบท่อประปา"  # Blue
    elif any(k in reason_clean for k in ["step test", "dma", "ติดตั้งมาตร"]):
        return 0xF1C40F, "📋 ตรวจสอบและบำรุงรักษาระบบ"  # Yellow
    else:
        return 0x95A5A6, "ℹ️ ประกาศน้ำไม่ไหล/งานบำรุงรักษา"  # Grey


class DiscordNotifier(BaseNotifier):
    """Dispatches water outage alerts to Discord via Webhook with rich embeds."""

    def __init__(self, config: DiscordConfig):
        self.config = config

    def build_outage_embed(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> Dict[str, Any]:
        """Construct a Discord Rich Embed for an outage event."""
        color, badge = get_embed_color_and_badge(event.reason, event.active)

        status_tag = "🔴 [กำลังดำเนินการ]" if event.active else "🟡 [มีแผนงาน/นัดหมาย]"
        title = f"{badge} - สาขา{event.impact_branch or 'การประปา'}"

        fields: List[Dict[str, Any]] = []

        # Time range field
        start_str = event.start_date_raw or "ไม่ระบุ"
        finish_str = event.finish_date_raw or "ไม่ระบุ"
        fields.append({
            "name": "⏱️ ช่วงเวลาที่ได้รับผลกระทบ",
            "value": f"**ตั้งแต่:** {start_str}\n**ถึง:** {finish_str}\n**สถานะงาน:** {status_tag}",
            "inline": False,
        })

        # Match reason
        fields.append({
            "name": "🎯 เหตุผลที่แจ้งเตือนคุณ",
            "value": f"{match_result.reason_text}",
            "inline": False,
        })

        # Work area
        if event.area_name:
            fields.append({
                "name": "📍 จุดปฏิบัติงาน",
                "value": event.area_name[:250],
                "inline": True,
            })

        # Pipe specs
        pipe_info = []
        if event.pipe_size and event.pipe_size != "0":
            pipe_info.append(f"{event.pipe_size} มม.")
        if event.pipe_type:
            pipe_info.append(f"({event.pipe_type})")
        if pipe_info:
            fields.append({
                "name": "🛠️ ขนาดและชนิดท่อ",
                "value": " ".join(pipe_info),
                "inline": True,
            })

        # Branch
        if event.impact_branch:
            fields.append({
                "name": "🏢 สาขาที่รับผิดชอบ",
                "value": f"สาขา{event.impact_branch}",
                "inline": True,
            })

        # Map navigation link
        if event.has_coordinates:
            fields.append({
                "name": "🗺️ แผนที่พิกัดจุดงาน",
                "value": f"[คลิกเพื่อเปิดดูบน Google Maps]({event.google_maps_url})",
                "inline": False,
            })

        if event.work_person:
            fields.append({
                "name": "👷 ผู้ประสานงาน/ช่าง",
                "value": event.work_person,
                "inline": True,
            })

        description = (
            f"**💧 พื้นที่น้ำไม่ไหล / น้ำไหลอ่อน:**\n"
            f"> {event.impact_area or 'โปรดตรวจสอบรายละเอียดเพิ่มเติม'}"
        )
        if len(description) > 2000:
            description = description[:1995] + "..."

        embed = {
            "title": title,
            "description": description,
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"MWA GIS 1125 • NumMaiLai ID: {event.event_id}",
                "icon_url": self.config.avatar_url,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return embed

    def send_webhook(self, payload: Dict[str, Any]) -> bool:
        """Send JSON payload to Discord Webhook with retry on rate limit."""
        if not self.config.enabled:
            logger.info("Discord notifications are disabled in configuration.")
            return False

        webhook_url = self.config.webhook_url.strip()
        if not webhook_url or not webhook_url.startswith("http"):
            logger.warning("Discord webhook URL is missing or invalid.")
            return False

        headers = {"Content-Type": "application/json"}
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                )
                if response.status_code in (200, 204):
                    logger.info("Successfully dispatched Discord notification.")
                    return True
                elif response.status_code == 429:
                    retry_after = response.json().get("retry_after", 2)
                    logger.warning("Discord rate limited. Sleeping for %.2f seconds.", retry_after)
                    time.sleep(retry_after)
                else:
                    logger.error(
                        "Discord Webhook returned status %d: %s",
                        response.status_code,
                        response.text,
                    )
                    return False
            except Exception as e:
                logger.error("Error posting to Discord webhook (attempt %d/3): %s", attempt, e)
                time.sleep(1)

        return False

    def send_outage_alert(
        self,
        event: OutageEvent,
        match_result: MatchResult,
    ) -> bool:
        """Send a formatted Discord embed for an outage event."""
        embed = self.build_outage_embed(event, match_result)
        payload = {
            "username": self.config.username,
            "avatar_url": self.config.avatar_url,
            "embeds": [embed],
        }
        return self.send_webhook(payload)

    def send_test_message(self) -> bool:
        """Send a test message to verify the Discord webhook configuration."""
        embed = {
            "title": "✅ ทดสอบการเชื่อมต่อระบบแจ้งเตือนน้ำไม่ไหล (NumMaiLai)",
            "description": (
                "การเชื่อมต่อ Discord Webhook สำเร็จเรียบร้อยแล้ว!\n"
                "ระบบจะส่งการแจ้งเตือนทันทีเมื่อตรวจพบเหตุน้ำประปาไม่ไหลหรือการซ่อมท่อในพื้นที่ที่คุณกำหนด"
            ),
            "color": 0x2ECC71,  # Green
            "fields": [
                {
                    "name": "🔧 สถานะระบบ",
                    "value": "พร้อมใช้งาน (Online)",
                    "inline": True,
                },
                {
                    "name": "⏱️ เวลาทดสอบ",
                    "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "inline": True,
                },
            ],
            "footer": {
                "text": "NumMaiLai (น้ำไม่ไหล) • Test Notification",
                "icon_url": self.config.avatar_url,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        payload = {
            "username": self.config.username,
            "avatar_url": self.config.avatar_url,
            "embeds": [embed],
        }
        return self.send_webhook(payload)
