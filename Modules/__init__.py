import functools
import inspect

from .Logger import Logger
from .Logger import bot as global_bot
from .Logger import setup_logger


def log(**kwargs):
    """Decorator factory that creates a logger decorator"""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **func_kwargs):
            # Get bot instance from self (cog) or global
            bot = None
            if args and hasattr(args[0], "bot"):
                bot = args[0].bot

            if not bot:
                bot = global_bot

            if not bot:
                print("Warning: Logger not initialized - bot instance not found")
                return await func(*args, **func_kwargs)

            # Always get the singleton instance
            logger_instance = Logger(bot)

            # Apply logging directly
            user = None
            if len(args) > 1 and hasattr(args[1], "author"):
                user = args[1].author
            elif len(args) > 1 and hasattr(args[1], "user"):
                user = args[1].user

            command_name = func.__name__.replace("_", " ")
            log_text = kwargs.get("text", f"**/{command_name}** was executed")
            log_color = kwargs.get("color", 0x00FF00)
            log_type = kwargs.get(
                "type", args[0].__class__.__name__ if args else "Command"
            )

            # Execute logging before running the command
            await logger_instance.log(log_text, log_color, log_type, 0, user)

            # Execute the command
            return await func(*args, **func_kwargs)

        return wrapper if inspect.iscoroutinefunction(func) else func

    return decorator


__all__ = ["setup_logger", "log"]
