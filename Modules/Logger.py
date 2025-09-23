import asyncio
import datetime
import inspect
import os
from functools import wraps
from time import time

import disnake
import yaml
from disnake.ext import commands

from .Database import Database

# Initialize defaults
LOGGING_CHANNEL = None
ENABLE_CHANNEL_LOGGING = False
ENABLE_LOG_TO_FILE = False


def load_config():
    """Load configuration from YAML file"""
    global LOGGING_CHANNEL, ENABLE_CHANNEL_LOGGING, ENABLE_LOG_TO_FILE
    try:
        config_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "config.yml")
        )
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            LOGGING_CHANNEL = data.get("logging_channel")  # Should be an integer
            ENABLE_CHANNEL_LOGGING = data.get("enable_channel_logging", False)
            ENABLE_LOG_TO_FILE = data.get("enable_log_to_file", False)
            # Removed invalid reference to 'self'
            rendition = data.get(
                "rendition", 0
            )  # TODO: the other parts of the code should be using this by default, no?
    except Exception as e:
        print(f"Error loading logger config: {e}")
        # Keep default values if loading fails


class Logger:
    _instance = None

    def __new__(cls, bot=None, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, bot=None, text=None, color=0x00FF00, type="INFO", priority=0):
        if not self._initialized and bot:
            self.bot = bot
            load_config()  # Ensure config is loaded
            self.rendition = yaml.safe_load(
                open(os.path.join(os.path.dirname(__file__), "..", "config.yml"), "r")
            ).get("rendition", 0)
            self.default_text = text
            self.default_color = color
            self.default_type = type
            self.default_priority = priority
            self._initialized = True

    async def log(self, text, color, type, priority, user=None):
        """The actual logging method"""
        if ENABLE_LOG_TO_FILE:
            try:
                query = """
                    INSERT INTO action_logs (user_id, username, message, type, priority, color)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """
                await Database.conn.execute(
                    query,
                    user.id if user else None,
                    str(user) if user else None,
                    text,
                    type,
                    priority,
                    color,
                )
            except Exception as e:
                print(f"Failed to write log to database: {e}")

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


async def setup_logger(bot_instance):
    global bot, logger
    bot = bot_instance

    # Create data directory if it doesn't exist
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Initialize logger
    logger = Logger(bot_instance)

    return logger


async def log(text, color, type, priority, user):
    """Logs a message with configurable parameters."""
    print(
        f"Logging: {text} with color {color}, type {type}, priority {priority}, and user {user}"
    )
    await logger.log(text, color, type, priority, user)


# Usage examples:

# Initialize logger (typically in your bot setup)
# bot = commands.Bot(...)
# logger = Logger(bot)


# Use as decorator with default settings:
# async def setup_logger_with_args(bot_instance):
#     global bot, logger
#     bot = bot_instance
#     logger = Logger(bot_instance)
#     return logger


# async def setup_logger_with_result(bot_instance):
#     global bot, logger
#     bot = bot_instance
#     logger = Logger(bot_instance)
#     return logger


# async def setup_logger_with_args_async(bot_instance):
#     global bot, logger
#     bot = bot_instance
#     logger = Logger(bot_instance)
#     return logger
