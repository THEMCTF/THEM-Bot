import asyncio
import functools
import time
from datetime import datetime, timezone

import disnake


class Logger:
    """A decorator that logs command execution to a Discord channel."""

    def __init__(self):
        """Initialize the Logger."""
        self.bot = None
        self.config = None
        self.logging_level = 1
        self.log_channel = None

    def configure(self, bot, config, logging_level=1):
        """Configure the logger with bot and config."""
        self.bot = bot
        self.config = config
        self.logging_level = logging_level
        self.log_channel = config.get("logging_channel")

    async def send_to_channel(
        self,
        func_name,
        inter,
        message,
        class_name,
        color,
        importance,
    ):
        """Send a log embed to the configured logging channel."""
        if self.bot is None:
            print("Logger not configured, skipping sending message to channel.")
            return

        if importance < self.logging_level:
            return

        embed = disnake.Embed(
            color=color,
            title=func_name,
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

    def __call__(
        self,
        func=None,
        *,
        message="Command executed successfully",
        color=0x78B159,
        importance=1,
    ):
        """Make the instance callable as a decorator with optional parameters."""

        def decorator(f):
            @functools.wraps(f)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                class_name = args[0].__class__.__name__ if args else "Unknown"
                print(f"Executing {f.__name__} (sync) in {class_name}")
                result = f(*args, **kwargs)
                duration = (time.perf_counter() - start_time) * 1000
                print(f"Finished {f.__name__} in {duration:.2f}ms")
                return result

            @functools.wraps(f)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                class_name = args[0].__class__.__name__ if args else "Unknown"
                inter = next(
                    (
                        arg
                        for arg in args
                        if isinstance(arg, disnake.ApplicationCommandInteraction)
                    ),
                    None,
                )

                try:
                    result = await f(*args, **kwargs)
                    duration = (time.perf_counter() - start_time) * 1000
                    print(f"Finished {f.__name__} in {duration:.2f}ms")

                    if inter:
                        try:
                            await self.send_to_channel(
                                f.__name__,
                                inter,
                                message,
                                class_name,
                                color,
                                importance,
                            )
                        except Exception as log_e:
                            print(f"Logger failed to send success message: {log_e}")

                    return result

                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    print(f"Failed {f.__name__} in {duration:.2f}ms with error: {e}")

                    if inter:
                        try:
                            await self.send_to_channel(
                                f.__name__,
                                inter,
                                f"**Error:**\n```{e}```",
                                class_name,
                                0xDD2E44,
                                2,
                            )
                        except Exception as log_e:
                            print(f"Logger failed to send error message: {log_e}")
                    raise

            return async_wrapper if asyncio.iscoroutinefunction(f) else sync_wrapper

        if func is None:
            # Called with arguments: @logger(message="...", color=0xFF0000)
            return decorator
        else:
            # Called without arguments: @logger
            return decorator(func)


logger = Logger()
