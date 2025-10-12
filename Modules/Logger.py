import asyncio
import functools
import inspect
import time
from datetime import datetime, timezone

import disnake
from disnake.ext import commands


class Logger:
    """
    A class-based decorator that logs information about command calls.
    It can be initialized with logging configuration and then used to decorate
    command functions.
    """

    def __init__(self, bot, config, logging_level=1):
        self.bot = bot
        self.config = config
        self.logging_level = logging_level
        self.log_channel = config.get("logging_channel")

    async def send_to_channel(
        self, function_name, inter, message, class_name, color, importance
    ):
        if importance >= self.logging_level:
            embed = disnake.Embed(
                color=color,
                title=function_name,
                description=message,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_author(
                name=inter.author.display_name, icon_url=inter.author.avatar.url
            )
            embed.set_footer(text=class_name)
            log_channel = self.bot.get_channel(self.log_channel)
            if log_channel:
                await log_channel.send(embed=embed)

    def __call__(self, func):
        """This makes the class instance callable, to be used as a decorator."""

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            """Synchronous wrapper for logging."""
            start_time = time.perf_counter()
            class_name = (
                args[0].__class__.__name__
                if args and hasattr(args[0], "__class__")
                else "Unknown"
            )

            print(f"Executing {func.__name__} (sync) in class {class_name}")

            result = func(*args, **kwargs)

            duration = (time.perf_counter() - start_time) * 1000
            print(f"Finished {func.__name__} in {duration:.2f}ms")
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            """Asynchronous wrapper for logging."""
            start_time = time.perf_counter()
            class_name = (
                args[0].__class__.__name__
                if args and hasattr(args[0], "__class__")
                else "Unknown"
            )

            # The interaction object is usually the second argument in a command method (after self)
            inter = (
                args[1]
                if len(args) > 1
                and isinstance(args[1], disnake.ApplicationCommandInteraction)
                else None
            )

            # --- Execute original function ---
            try:
                result = await func(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                print(f"Finished {func.__name__} in {duration:.2f}ms")
                if kwargs:
                    message = kwargs.get("message", "No message")
                    color = kwargs.get("color", 0x78B159)
                    importance = kwargs.get("importance", 1)
                else:
                    message = args
                    color = 0x78B159
                    importance = 1
                await self.send_to_channel(
                    func.__name__,
                    inter,
                    message,
                    class_name,
                    color,
                    importance,
                )
                return result
            except Exception as e:
                duration = (time.perf_counter() - start_time) * 1000
                print(f"Failed {func.__name__} in {duration:.2f}ms with error: {e}")
                if inter:
                    f"**Error:**\n```{e}```",
                    class_name,
                    0xDD2E44,
                    2,
                return result
            except Exception as e:
                duration = (time.perf_counter() - start_time) * 1000
                print(f"Failed {func.__name__} in {duration:.2f}ms with error: {e}")
                if inter:
                    await self.send_to_channel(
                        func.__name__,
                        inter,
                        f"**Error:**\n```{e}```",
                        class_name,
                        0xDD2E44,
                        2,
                    )
                raise  # Re-raise the exception so disnake's error handlers can catch it

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
