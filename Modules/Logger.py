import asyncio
import datetime
import inspect
import os
from functools import wraps
from time import time

import disnake
import json5
from disnake.ext import commands

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go one folder up and join with config.json5
config_path = os.path.join(current_dir, "..", "config.json5")
# Normalize the path (resolves "..")
config_path = os.path.normpath(config_path)

with open(config_path, "r") as f:
    data = json5.load(f)  # make this use yml later

LOGGING_CHANNEL = data.get("LOGGING_CHANNEL", [])
ENABLE_CHANNEL_LOGGING = data.get("ENABLE_CHANNEL_LOGGING", [])
ENABLE_LOG_TO_FILE = data.get("ENABLE_LOG_TO_FILE", [])


class Logger:
    def __init__(self, bot, text=None, color=0x00FF00, type="INFO", priority=0):
        self.bot = bot
        self.rendition = 0  # this words just sounds cool, it's not really related -starry [9/10/2025]
        # Default decorator parameters
        self.default_text = text
        self.default_color = color
        self.default_type = type
        self.default_priority = priority

    async def log(self, text, color, type, priority, user=None):
        """The actual logging method"""
        if ENABLE_LOG_TO_FILE == True:
            # Log to file in proper JSON format
            log_entry = {
                "timestamp": datetime.datetime.now().isoformat(),
                "user_id": user.id if user else None,
                "username": str(user) if user else None,
                "message": text,
                "type": type,
                "priority": priority,
                "color": color,
            }

            # Write JSON to file (append mode)
            log_file = os.path.join(current_dir, "bot_logs.json")
            try:
                # Read existing logs if file exists
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        try:
                            logs = json5.load(f)
                            if not isinstance(logs, list):
                                logs = []
                        except:
                            logs = []
                else:
                    logs = []

                # Append new log entry
                logs.append(log_entry)

                # Write back to file
                with open(log_file, "w") as f:
                    json5.dump(logs, f, indent=2)
            except Exception as e:
                print(f"Error writing to log file: {e}")

        if ENABLE_CHANNEL_LOGGING == False:
            print(f"{type}: {text}; {user}")
            return

        if priority < self.rendition:
            return

        channel = self.bot.get_channel(LOGGING_CHANNEL)
        if channel:
            embed = disnake.Embed(
                description=text,
                color=color,
                timestamp=datetime.datetime.now(),
            )
            embed.set_footer(text=type)
            if user != None:
                embed.set_author(
                    name=user.display_name,
                    icon_url=user.display_avatar,
                )
            await channel.send(embed=embed)
        else:
            print(f"Error: Logger channel with ID {LOGGING_CHANNEL} not found.")

    def __call__(
        self,
        func=None,
        *,
        text=None,
        color=None,
        type=None,
        priority=None,
        log_args=False,
        log_result=False,
    ):
        """Decorator implementation"""
        # If called without arguments, return a decorator
        if func is None:
            return lambda f: self.__call__(
                f,
                text=text,
                color=color,
                type=type,
                priority=priority,
                log_args=log_args,
                log_result=log_result,
            )

        # Use provided parameters or fall back to defaults
        log_color = color or self.default_color
        log_priority = priority or self.default_priority

        # Auto-detect cog name if type not provided
        if type:
            log_type = type
        elif self.default_type != "INFO":
            log_type = self.default_type
        else:
            # Try to get the cog name from the function's qualname
            if hasattr(func, "__qualname__") and "." in func.__qualname__:
                cog_name = func.__qualname__.split(".")[0]
                log_type = cog_name
            else:
                log_type = "404"

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get user from context if available (for Discord commands)
                user = None
                # Handle disnake ApplicationCommandInteraction (slash commands)
                if args and hasattr(args[0], "author"):  # Regular command context
                    user = args[0].author
                elif args and hasattr(args[1], "author"):  # Cog method (self, inter)
                    user = args[1].author
                elif args and hasattr(args[0], "user"):  # Slash command interaction
                    user = args[0].user
                elif args and hasattr(
                    args[1], "user"
                ):  # Cog slash command (self, inter)
                    user = args[1].user
                elif "ctx" in kwargs and hasattr(kwargs["ctx"], "author"):
                    user = kwargs["ctx"].author
                elif "inter" in kwargs and hasattr(kwargs["inter"], "user"):
                    user = kwargs["inter"].user

                # Generate log text
                if text or self.default_text:
                    call_text = text or self.default_text
                else:
                    if args or kwargs:
                        call_text = (
                            f"**/{func.__name__}** was ran with the context: {args}"
                        )
                    else:
                        call_text = f"**/{func.__name__}** was ran"

                # Add additional args info if log_args is enabled
                if log_args and (args or kwargs):
                    call_text += f" with args: {args}, kwargs: {kwargs}"

                await self.log(call_text, log_color, log_type, log_priority, user)

                # Execute the original function
                result = await func(*args, **kwargs)

                # Log result if requested
                if log_result:
                    result_text = f"Function {func.__name__} returned: {result}"
                    await self.log(
                        result_text, log_color, f"{log_type}_RESULT", log_priority, user
                    )

                return result

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Get user from context if available
                user = None
                if args and hasattr(args[0], "author"):
                    user = args[0].author
                elif args and hasattr(args[1], "author"):  # Cog method
                    user = args[1].author
                elif args and hasattr(args[0], "user"):  # Slash command
                    user = args[0].user
                elif args and hasattr(args[1], "user"):  # Cog slash command
                    user = args[1].user
                elif "ctx" in kwargs and hasattr(kwargs["ctx"], "author"):
                    user = kwargs["ctx"].author
                elif "inter" in kwargs and hasattr(kwargs["inter"], "user"):
                    user = kwargs["inter"].user

                # Generate log text
                if text or self.default_text:
                    call_text = text or self.default_text
                else:
                    if args or kwargs:
                        call_text = (
                            f"**/{func.__name__}** was ran with the context: {args}"
                        )
                    else:
                        call_text = f"**/{func.__name__}** was ran"

                # Add additional args info if log_args is enabled
                if log_args and (args or kwargs):
                    call_text += f" with args: {args}, kwargs: {kwargs}"

                # Schedule the async logging
                asyncio.create_task(
                    self.log(call_text, log_color, log_type, log_priority, user)
                )

                # Execute the original function
                result = func(*args, **kwargs)

                # Log result if requested
                if log_result:
                    result_text = f"Function {func.__name__} returned: {result}"
                    asyncio.create_task(
                        self.log(
                            result_text,
                            log_color,
                            f"{log_type}_RESULT",
                            log_priority,
                            user,
                        )
                    )

                return result

            return sync_wrapper


bot = None
logger = None


def setup_logger(bot_instance):
    global bot, logger
    bot = bot_instance
    logger = Logger(bot_instance)
    return logger


# Usage examples:

# Initialize logger (typically in your bot setup)
# bot = commands.Bot(...)
# logger = Logger(bot)

# Use as decorator with default settings:
# @logger
# async def some_command(ctx):
#     await ctx.send("Hello!")

# Use as decorator with custom parameters:
# @logger(text="Custom command executed", color=0xff0000, type="COMMAND", priority=1, log_args=True)
# async def another_command(ctx, arg1, arg2):
#     await ctx.send(f"Args: {arg1}, {arg2}")

# Use directly for manual logging:
# await logger.log("Manual log message", 0x00ff00, "MANUAL", 0, user=ctx.author)
