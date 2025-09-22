import os
from functools import wraps
from typing import Optional

import yaml
from disnake.ext import commands


class CooldownManager:
    _instance = None
    _cooldowns = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load_cooldowns(cls):
        """Load cooldown configuration from config.yml"""
        if cls._cooldowns is None:
            try:
                config_path = os.path.normpath(
                    os.path.join(os.path.dirname(__file__), "..", "config.yml")
                )
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f)
                    cls._cooldowns = data.get("cooldowns", {"default": 60})
            except Exception as e:
                print(f"Error loading cooldowns config: {e}")
                cls._cooldowns = {"default": 60}

    @classmethod
    def get_cooldown(cls, cog_name: str, command_name: str) -> int:
        """Get cooldown value for a specific command

        Args:
            cog_name: Name of the cog containing the command
            command_name: Name of the command

        Returns:
            Cooldown duration in seconds
        """
        cls.load_cooldowns()

        # Get cog-specific cooldowns
        cog_cooldowns = cls._cooldowns.get(cog_name, {})

        # First try command-specific cooldown
        if isinstance(cog_cooldowns, dict):
            # Check for command-specific cooldown
            if command_name in cog_cooldowns:
                return cog_cooldowns[command_name]
            # Check for cog default
            if "default" in cog_cooldowns:
                return cog_cooldowns["default"]

        # If cog_cooldowns is an integer, it's a flat cooldown for all commands
        elif isinstance(cog_cooldowns, (int, float)):
            return int(cog_cooldowns)

        # Fall back to global default
        return cls._cooldowns.get("default", 60)


def dynamic_cooldown():
    """Decorator to apply dynamic cooldowns from config"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cog name and command name
            cog_name = args[0].__class__.__name__ if args else None
            command_name = func.__name__

            # Get cooldown value
            cooldown_seconds = CooldownManager.get_cooldown(cog_name, command_name)

            # Skip cooldown if it's 0
            if cooldown_seconds == 0:
                return await func(*args, **kwargs)

            # Apply cooldown using commands.cooldown
            if not hasattr(func, "__commands_cooldown__"):
                cooldown = commands.Cooldown(1, cooldown_seconds)
                bucket = commands.BucketType.user
                func.__commands_cooldown__ = commands.CooldownMapping(cooldown, bucket)

            # The rest of the cooldown logic is handled by discord.py
            return await func(*args, **kwargs)

        return wrapper

    return decorator
