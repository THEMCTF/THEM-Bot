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

LOGGING_CHANNEL = None
ENABLE_CHANNEL_LOGGING = False
ENABLE_LOG_TO_FILE = False


def load_config():
    global LOGGING_CHANNEL, ENABLE_CHANNEL_LOGGING, ENABLE_LOG_TO_FILE
    try:
        config_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "config.yml")
        )
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
            LOGGING_CHANNEL = data.get("logging_channel")
            ENABLE_CHANNEL_LOGGING = data.get("enable_channel_logging", False)
            ENABLE_LOG_TO_FILE = data.get("enable_log_to_file", False)
            rendition = data.get("rendition", 0)
    except Exception as e:
        print(f"Error loading logger config: {e}")


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
            load_config()
            self.rendition = yaml.safe_load(
                open(os.path.join(os.path.dirname(__file__), "..", "config.yml"), "r")
            ).get("rendition", 0)
            self.default_text = text
            self.default_color = color
            self.default_type = type
            self.default_priority = priority
            self._initialized = True

    async def log(self, text, color, type, priority, user=None):
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

        if not ENABLE_CHANNEL_LOGGING:
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
            if user:
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

        log_color = color or self.default_color
        log_priority = priority or self.default_priority

        if type:
            log_type = type
        elif self.default_type != "INFO":
            log_type = self.default_type
        else:
            if hasattr(func, "__qualname__") and "." in func.__qualname__:
                log_type = func.__qualname__.split(".")[0]
            else:
                log_type = "404"

        def get_user_from_args(*args, **kwargs):
            for arg in args:
                if isinstance(arg, (disnake.ApplicationCommandInteraction, commands.Context)):
                    return arg.author
            for kwarg in kwargs.values():
                if isinstance(kwarg, (disnake.ApplicationCommandInteraction, commands.Context)):
                    return kwarg.author
            return None

        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                user = get_user_from_args(*args, **kwargs)

                if text or self.default_text:
                    call_text = text or self.default_text
                else:
                    call_text = f"**/{func.__name__}** was ran"
                    if args or kwargs:
                        call_text += f" with the context: {args}, {kwargs}"

                if log_args and (args or kwargs):
                    call_text += f" with args: {args}, kwargs: {kwargs}"

                await self.log(call_text, log_color, log_type, log_priority, user)

                result = await func(*args, **kwargs)

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
                user = get_user_from_args(*args, **kwargs)

                if text or self.default_text:
                    call_text = text or self.default_text
                else:
                    call_text = f"**/{func.__name__}** was ran"
                    if args or kwargs:
                        call_text += f" with the context: {args}"

                if log_args and (args or kwargs):
                    call_text += f" with args: {args}, kwargs: {kwargs}"

                asyncio.create_task(
                    self.log(call_text, log_color, log_type, log_priority, user)
                )

                result = func(*args, **kwargs)

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
_logger: Logger | None = None


async def setup_logger(bot_instance):
    global bot, _logger
    bot = bot_instance

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    _logger = Logger(bot_instance)

    return _logger
