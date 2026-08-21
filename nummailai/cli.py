from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Optional

from nummailai.client import MWAClient
from nummailai.config import load_config
from nummailai.matcher import AreaMatcher
from nummailai.models import AppConfig
from nummailai.notifiers.console import ConsoleNotifier
from nummailai.notifiers.discord import DiscordNotifier
from nummailai.notifiers.telegram import TelegramNotifier
from nummailai.state import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("nummailai")


def run_check(config: AppConfig, dry_run: bool = False) -> int:
    """Run a single check against MWA GIS and send alerts for new matching events.

    Returns the count of new matched incidents notified.
    """
    logger.info("Connecting to MWA GIS API...")
    client = MWAClient()
    events = client.fetch_events()
    logger.info("Retrieved %d total outage/maintenance events from MWA.", len(events))

    matcher = AreaMatcher(config.matching)
    state = StateManager(config.polling.state_file)

    notifiers = []
    # Always include console output
    notifiers.append(ConsoleNotifier())

    if config.discord.enabled and config.discord.webhook_url:
        notifiers.append(DiscordNotifier(config.discord))
    if config.telegram.enabled and config.telegram.bot_token:
        notifiers.append(TelegramNotifier(config.telegram))

    new_notified_count = 0

    for event in events:
        match_result = matcher.match(event)
        if match_result.matched:
            # Check if this incident was already notified
            if not state.is_already_notified(event.event_id):
                logger.info(
                    "🎯 [MATCH] New incident in your area: %s | %s | %s",
                    event.reason,
                    event.impact_branch,
                    match_result.reason_text,
                )
                if not dry_run:
                    for notifier in notifiers:
                        try:
                            notifier.send_outage_alert(event, match_result)
                        except Exception as e:
                            logger.error("Notifier %s failed: %s", notifier, e)

                    state.mark_notified(event, match_result)
                else:
                    logger.info("[Dry Run] Skipped sending actual alert.")

                new_notified_count += 1
            else:
                logger.debug("Incident %s already notified. Skipping.", event.event_id)

    state.update_last_run()
    logger.info(
        "Check completed. %d new events notified (Total seen: %d).",
        new_notified_count,
        len(state.state.get("notified_events", {})),
    )
    return new_notified_count


def run_daemon(config: AppConfig, interval_minutes: Optional[int] = None) -> None:
    """Run continuous monitoring loop."""
    interval = interval_minutes or config.polling.interval_minutes or 15
    interval_seconds = interval * 60
    logger.info("Starting NumMaiLai Daemon (Polling every %d minutes)...", interval)
    print(f"\n💧 NumMaiLai Daemon active! Checking MWA every {interval} minutes. Press Ctrl+C to stop.\n")

    while True:
        try:
            run_check(config)
        except Exception as e:
            logger.exception("Error during scheduled check: %s", e)

        logger.info("Next check in %d minutes...", interval)
        try:
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\nShutting down daemon gracefully...")
            break


def run_list_events(branch: str = "", limit: int = 50) -> None:
    """List current MWA events in terminal."""
    client = MWAClient()
    events = client.fetch_events(branch_param=branch)
    print(f"\n=======================================================")
    print(f"💧 Current MWA Water Outages / Maintenance ({len(events)} events)")
    print(f"=======================================================\n")
    for i, ev in enumerate(events[:limit], 1):
        badge = "🔴 [กำลังดำเนินการ]" if ev.active else "🟡 [มีแผนงาน]"
        print(f"[{i:02d}] {ev.reason} (สาขา{ev.impact_branch}) {badge}")
        print(f"     ⏱️ {ev.start_date_raw} ถึง {ev.finish_date_raw}")
        print(f"     📍 {ev.area_name}")
        print(f"     💧 {ev.impact_area}")
        if ev.has_coordinates:
            print(f"     🗺️ {ev.google_maps_url}")
        print("-" * 55)


def run_test_discord(webhook_url: Optional[str], config: AppConfig) -> None:
    """Send a test embed to Discord Webhook."""
    if webhook_url:
        config.discord.webhook_url = webhook_url
        config.discord.enabled = True

    if not config.discord.webhook_url:
        print("❌ Error: Discord Webhook URL is not set in config.yaml or command argument.")
        sys.exit(1)

    print(f"Sending test alert to Discord Webhook: {config.discord.webhook_url[:40]}...")
    notifier = DiscordNotifier(config.discord)
    success = notifier.send_test_message()
    if success:
        print("✅ Discord Webhook test message sent successfully! Check your Discord channel.")
    else:
        print("❌ Failed to send Discord Webhook message. Check URL and logs.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="nummailai",
        description="NumMaiLai (น้ำไม่ไหล) - MWA Water Outage & Pipe Maintenance Notifier",
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="Path to configuration YAML file (default: config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: check
    check_parser = subparsers.add_parser("check", help="Run a single check and notify")
    check_parser.add_argument(
        "--dry-run", action="store_true", help="Match events without sending actual notifications"
    )

    # Command: daemon
    daemon_parser = subparsers.add_parser("daemon", help="Run in continuous monitoring background mode")
    daemon_parser.add_argument(
        "-i", "--interval", type=int, help="Polling interval in minutes (overrides config)"
    )

    # Command: web
    web_parser = subparsers.add_parser("web", help="Launch interactive Leaflet web map dashboard")
    web_parser.add_argument(
        "-p", "--port", type=int, default=8080, help="Web server port (default: 8080)"
    )

    # Command: list
    list_parser = subparsers.add_parser("list", help="List all current MWA outages in terminal")
    list_parser.add_argument("-b", "--branch", default="", help="Filter by branch code (e.g. 06, 56)")
    list_parser.add_argument("-n", "--limit", type=int, default=50, help="Maximum items to display")

    # Command: test-discord
    test_disc_parser = subparsers.add_parser("test-discord", help="Send a test message to Discord Webhook")
    test_disc_parser.add_argument("--url", help="Discord Webhook URL to test")

    # Command: reset-state
    subparsers.add_parser("reset-state", help="Reset notified events cache")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    config = load_config(args.config)

    if args.command == "check":
        run_check(config, dry_run=args.dry_run)
    elif args.command == "daemon":
        run_daemon(config, interval_minutes=args.interval)
    elif args.command == "web":
        from nummailai.web.app import run_web_server
        run_web_server(port=args.port, config_path=args.config)
    elif args.command == "list":
        run_list_events(branch=args.branch, limit=args.limit)
    elif args.command == "test-discord":
        run_test_discord(webhook_url=args.url, config=config)
    elif args.command == "reset-state":
        state = StateManager(config.polling.state_file)
        state.clear()
        print("✅ Notified events state cleared successfully.")
    else:
        # If no subcommand provided, show help
        parser.print_help()


if __name__ == "__main__":
    main()
