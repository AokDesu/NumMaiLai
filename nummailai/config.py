from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml

from nummailai.models import (
    AppConfig,
    BranchesConfig,
    DiscordConfig,
    KeywordsConfig,
    LocationConfig,
    MatchingConfig,
    PollingConfig,
    TelegramConfig,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"


def parse_dict_to_config(data: Dict[str, Any]) -> AppConfig:
    """Parse dictionary into typed AppConfig."""
    matching_data = data.get("matching", {})
    loc_data = matching_data.get("location", {})
    kw_data = matching_data.get("keywords", {})
    br_data = matching_data.get("branches", {})

    disc_data = data.get("notifications", {}).get("discord", {})
    tg_data = data.get("notifications", {}).get("telegram", {})
    poll_data = data.get("polling", {})

    location = LocationConfig(
        enabled=bool(loc_data.get("enabled", True)),
        latitude=float(loc_data.get("latitude", 0.0) or 0.0),
        longitude=float(loc_data.get("longitude", 0.0) or 0.0),
        radius_km=float(loc_data.get("radius_km", 5.0) or 5.0),
    )

    keywords_list = kw_data.get("terms", [])
    if isinstance(keywords_list, str):
        keywords_list = [k.strip() for k in keywords_list.split(",") if k.strip()]

    keywords = KeywordsConfig(
        enabled=bool(kw_data.get("enabled", True)),
        terms=keywords_list or [],
    )

    branches_list = br_data.get("names", [])
    if isinstance(branches_list, str):
        branches_list = [b.strip() for b in branches_list.split(",") if b.strip()]

    branches = BranchesConfig(
        enabled=bool(br_data.get("enabled", False)),
        names=branches_list or [],
    )

    matching = MatchingConfig(
        mode=str(matching_data.get("mode", "hybrid")),
        location=location,
        keywords=keywords,
        branches=branches,
    )

    discord = DiscordConfig(
        enabled=bool(disc_data.get("enabled", True)),
        webhook_url=str(disc_data.get("webhook_url", "") or ""),
        username=str(disc_data.get("username", "MWA Alert (น้ำไม่ไหล)")),
        avatar_url=str(
            disc_data.get(
                "avatar_url",
                "https://gisonline.mwa.co.th/GIS1125/SRC/resources/mwa-icon.png",
            )
        ),
    )

    telegram = TelegramConfig(
        enabled=bool(tg_data.get("enabled", False)),
        bot_token=str(tg_data.get("bot_token", "") or ""),
        chat_id=str(tg_data.get("chat_id", "") or ""),
    )

    polling = PollingConfig(
        interval_minutes=int(poll_data.get("interval_minutes", 15) or 15),
        state_file=str(poll_data.get("state_file", "data/state.json")),
    )

    return AppConfig(
        matching=matching,
        discord=discord,
        telegram=telegram,
        polling=polling,
    )


def apply_env_overrides(config: AppConfig) -> AppConfig:
    """Override configuration with environment variables if present."""
    if webhook := os.getenv("DISCORD_WEBHOOK_URL"):
        config.discord.webhook_url = webhook
        config.discord.enabled = True

    if lat := os.getenv("LATITUDE"):
        try:
            config.matching.location.latitude = float(lat)
        except ValueError:
            pass

    if lng := os.getenv("LONGITUDE"):
        try:
            config.matching.location.longitude = float(lng)
        except ValueError:
            pass

    if radius := os.getenv("RADIUS_KM"):
        try:
            config.matching.location.radius_km = float(radius)
        except ValueError:
            pass

    if keywords := os.getenv("KEYWORDS"):
        terms = [k.strip() for k in keywords.split(",") if k.strip()]
        if terms:
            config.matching.keywords.terms = terms
            config.matching.keywords.enabled = True

    if branches := os.getenv("BRANCHES"):
        names = [b.strip() for b in branches.split(",") if b.strip()]
        if names:
            config.matching.branches.names = names
            config.matching.branches.enabled = True

    if poll_min := os.getenv("POLLING_INTERVAL"):
        try:
            config.polling.interval_minutes = int(poll_min)
        except ValueError:
            pass

    return config


def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Load configuration from YAML file and apply environment variable overrides."""
    p = Path(config_path)
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if isinstance(data, dict):
                    config = parse_dict_to_config(data)
                    return apply_env_overrides(config)
        except Exception as e:
            logger.warning("Failed to load config file %s: %s. Using defaults.", config_path, e)

    config = AppConfig()
    return apply_env_overrides(config)


def config_to_dict(config: AppConfig) -> Dict[str, Any]:
    """Convert AppConfig to dictionary for YAML persistence."""
    return {
        "matching": {
            "mode": config.matching.mode,
            "location": {
                "enabled": config.matching.location.enabled,
                "latitude": config.matching.location.latitude,
                "longitude": config.matching.location.longitude,
                "radius_km": config.matching.location.radius_km,
            },
            "keywords": {
                "enabled": config.matching.keywords.enabled,
                "terms": config.matching.keywords.terms,
            },
            "branches": {
                "enabled": config.matching.branches.enabled,
                "names": config.matching.branches.names,
            },
        },
        "notifications": {
            "discord": {
                "enabled": config.discord.enabled,
                "webhook_url": config.discord.webhook_url,
                "username": config.discord.username,
                "avatar_url": config.discord.avatar_url,
            },
            "telegram": {
                "enabled": config.telegram.enabled,
                "bot_token": config.telegram.bot_token,
                "chat_id": config.telegram.chat_id,
            },
        },
        "polling": {
            "interval_minutes": config.polling.interval_minutes,
            "state_file": config.polling.state_file,
        },
    }


def save_config(config: AppConfig, config_path: str = DEFAULT_CONFIG_PATH) -> None:
    """Save AppConfig to YAML file."""
    p = Path(config_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    dict_data = config_to_dict(config)
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(dict_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
