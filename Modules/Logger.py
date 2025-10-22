import asyncio
import functools
import time
from datetime import datetime, timezone

import disnake


class Logger:
    def __init__(self):
        print("[Logger] Initialized (bot=None, config=None)")
        self.bot = None
        self.config = None
        self.logging_level = 1
        self.log_channel = None

    def configure(self, bot, config, logging_level=1):
        print("[Logger] Configuring logger...")
        print(f"[Logger] Bot: {bot}")
        print(f"[Logger] Config: {config}")
        print(f"[Logger] Logging level: {logging_level}")
        self.bot = bot
        self.config = config
        self.logging_level = logging_level
        self.log_channel = config.get("logging_channel")
        print(f"[Logger] Log channel set to: {self.log_channel}")

    async def send_to_channel(
        self, func_name, inter, message, class_name, color, importance
    ):
        print(f"[Logger] send_to_channel called with:")
        print(f"  func_name={func_name}")
        print(f"  inter={inter}")
        print(f"  message={message}")
        print(f"  class_name={class_name}")
        print(f"  color={hex(color)}")
        print(f"  importance={importance}")

        if not self.bot:
            print("[Logger] Bot is None → Skipping sending message to channel.")
            return

        if importance < self.logging_level:
            print(f"[Logger] Importance {importance} < {self.logging_level}, skipping.")
            return

        embed = disnake.Embed(
            color=color,
            title=func_name,
            description=message,
            timestamp=datetime.now(timezone.utc),
        )

        author_name = getattr(inter.author, "display_name", "Unknown User")
        author_icon = getattr(
            getattr(inter.author, "avatar", None), "url", disnake.Embed.Empty
        )
        embed.set_author(name=author_name, icon_url=author_icon)
        embed.set_footer(text=class_name)

        log_channel = self.bot.get_channel(self.log_channel)
        print(f"[Logger] Resolved log channel: {log_channel}")

        if not log_channel:
            print(f"[Logger] Log channel {self.log_channel} not found.")
            return

        try:
            await log_channel.send(embed=embed)
            print("[Logger] Successfully sent embed to channel.")
        except Exception as e:
            print(f"[Logger] Failed to send log to channel: {e}")

    def __call__(
        self,
        func=None,
        *,
        message="Command executed successfully",
        color=0x78B159,
        importance=1,
    ):
        def decorator(f):
            @functools.wraps(f)
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                if args:
                    class_name = args[0].__class__.__name__
                elif "self" in kwargs:
                    class_name = kwargs["self"].__class__.__name__
                else:
                    class_name = "Unknown"

                print(f"[Logger] Executing {f.__name__} (sync) in {class_name}")
                print(f"[Logger] Executing {f.__name__} (sync) in {class_name}")
                print(f"[Logger] Args: {args}")
                print(f"[Logger] Kwargs: {kwargs}")
                try:
                    result = f(*args, **kwargs)
                    duration = (time.perf_counter() - start_time) * 1000
                    print(f"[Logger] Finished {f.__name__} in {duration:.2f}ms")
                    print(f"[Logger] Result: {result}")
                    return result
                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    print(
                        f"[Logger] Failed {f.__name__} in {duration:.2f}ms with error: {e}"
                    )
                    raise

            @functools.wraps(f)
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                # Determine class name for logging
                if args:
                    class_name = args[0].__class__.__name__
                elif "self" in kwargs:
                    class_name = kwargs["self"].__class__.__name__
                else:
                    class_name = "Unknown"

                print(f"[Logger] Executing {f.__name__} (async) in {class_name}")
                print(f"[Logger] Args: {args}")
                print(f"[Logger] Kwargs: {kwargs}")

                inter = next(
                    (
                        arg
                        for arg in list(args) + list(kwargs.values())
                        if isinstance(arg, disnake.ApplicationCommandInteraction)
                    ),
                    None,
                )
                print(f"[Logger] Found inter: {inter}")

                try:
                    result = await f(*args, **kwargs)
                    duration = (time.perf_counter() - start_time) * 1000
                    print(f"[Logger] Finished {f.__name__} in {duration:.2f}ms")
                    print(f"[Logger] Result: {result}")

                    if inter:
                        await self.send_to_channel(
                            f.__name__, inter, message, class_name, color, importance
                        )

                    return result

                except Exception as e:
                    duration = (time.perf_counter() - start_time) * 1000
                    print(
                        f"[Logger] Failed {f.__name__} in {duration:.2f}ms with error: {e}"
                    )

                    if inter:
                        await self.send_to_channel(
                            f.__name__,
                            inter,
                            f"**Error:**\n```{e}```",
                            class_name,
                            0xDD2E44,
                            2,
                        )
                    raise

            return async_wrapper if asyncio.iscoroutinefunction(f) else sync_wrapper

        return decorator if func is None else decorator(func)


logger = Logger()
