from __future__ import annotations

import json
import logging
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List
import urllib.parse

from nummailai.client import MWAClient
from nummailai.config import config_to_dict, load_config, save_config, parse_dict_to_config
from nummailai.matcher import AreaMatcher
from nummailai.models import AppConfig
from nummailai.notifiers.discord import DiscordNotifier
from nummailai.state import StateManager

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


class NumMaiLaiWebHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler for NumMaiLai Web Dashboard."""

    def __init__(self, *args, config_path: str = "config.yaml", **kwargs):
        self.config_path = config_path
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            self.serve_template("index.html")
        elif path.startswith("/static/"):
            self.serve_static(path[len("/static/"):])
        elif path == "/api/config":
            self.handle_get_config()
        elif path == "/api/events":
            self.handle_get_events()
        elif path == "/api/status":
            self.handle_get_status()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            payload = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {}

        if path == "/api/config":
            self.handle_save_config(payload)
        elif path == "/api/test-discord":
            self.handle_test_discord(payload)
        elif path == "/api/check-now":
            self.handle_check_now()
        else:
            self.send_error(404, "Not Found")

    def serve_template(self, filename: str) -> None:
        file_path = TEMPLATES_DIR / filename
        if not file_path.exists():
            self.send_error(404, f"Template {filename} not found")
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_static(self, rel_path: str) -> None:
        file_path = STATIC_DIR / rel_path
        if not file_path.exists():
            self.send_error(404, "File Not Found")
            return

        content_type = "text/plain"
        if rel_path.endswith(".css"):
            content_type = "text/css"
        elif rel_path.endswith(".js"):
            content_type = "application/javascript"
        elif rel_path.endswith(".png"):
            content_type = "image/png"
        elif rel_path.endswith(".svg"):
            content_type = "image/svg+xml"

        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, data: Any, status_code: int = 200) -> None:
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_get_config(self) -> None:
        config = load_config(self.config_path)
        self.send_json(config_to_dict(config))

    def handle_save_config(self, payload: Dict[str, Any]) -> None:
        try:
            config = parse_dict_to_config(payload)
            save_config(config, self.config_path)
            self.send_json({"status": "ok", "message": "บันทึกการตั้งค่าเรียบร้อยแล้ว (Configuration saved)"})
        except Exception as e:
            logger.exception("Error saving configuration: %s", e)
            self.send_json({"status": "error", "message": str(e)}, status_code=500)

    def handle_get_events(self) -> None:
        try:
            config = load_config(self.config_path)
            client = MWAClient()
            events = client.fetch_events()
            matcher = AreaMatcher(config.matching)

            enriched = []
            for ev in events:
                match_res = matcher.match(ev)
                item = ev.to_dict()
                item["matched"] = match_res.matched
                item["match_distance_km"] = match_res.distance_km
                item["match_reasons"] = match_res.summary_reasons
                enriched.append(item)

            self.send_json({"status": "ok", "total": len(enriched), "events": enriched})
        except Exception as e:
            logger.exception("Error fetching events: %s", e)
            self.send_json({"status": "error", "message": str(e)}, status_code=500)

    def handle_get_status(self) -> None:
        config = load_config(self.config_path)
        state = StateManager(config.polling.state_file)
        self.send_json({
            "status": "ok",
            "last_run_at": state.state.get("last_run_at"),
            "notified_count": len(state.state.get("notified_events", {})),
        })

    def handle_test_discord(self, payload: Dict[str, Any]) -> None:
        webhook_url = payload.get("webhook_url")
        config = load_config(self.config_path)
        if webhook_url:
            config.discord.webhook_url = webhook_url

        notifier = DiscordNotifier(config.discord)
        success = notifier.send_test_message()
        if success:
            self.send_json({"status": "ok", "message": "ส่งข้อความทดสอบไปยัง Discord สำเร็จ!"})
        else:
            self.send_json({"status": "error", "message": "ไม่สามารถส่งข้อความได้ โปรดตรวจสอบ Webhook URL"}, status_code=400)

    def handle_check_now(self) -> None:
        from nummailai.cli import run_check
        try:
            config = load_config(self.config_path)
            new_matches = run_check(config)
            self.send_json({
                "status": "ok",
                "message": f"ตรวจสอบสำเร็จ พบเหตุการณ์ใหม่ที่แจ้งเตือน: {new_matches} รายการ",
                "new_matches": new_matches,
            })
        except Exception as e:
            logger.exception("Error during check now: %s", e)
            self.send_json({"status": "error", "message": str(e)}, status_code=500)


def run_web_server(port: int = 8080, config_path: str = "config.yaml") -> None:
    """Start the interactive web server."""
    handler = lambda *args, **kwargs: NumMaiLaiWebHandler(*args, config_path=config_path, **kwargs)
    server = HTTPServer(("0.0.0.0", port), handler)
    print(f"\n=======================================================")
    print(f"🚀 NumMaiLai Web Dashboard is running at:")
    print(f"👉 http://localhost:{port}")
    print(f"=======================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        server.server_close()
