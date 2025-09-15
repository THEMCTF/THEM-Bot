from .Logger import Logger, setup_logger


def log(**kwargs):
    """Decorator factory that creates a logger decorator"""

    def decorator(func):
        # Get the bot instance from the cog
        def get_logger_decorator(f):
            import inspect

            # Try to get bot from the function's context
            if hasattr(f, "__qualname__") and "." in f.__qualname__:
                # This is likely a method, we'll get the bot when it's actually called
                from functools import wraps

                @wraps(f)
                async def wrapper(*args, **func_kwargs):
                    # args[0] should be 'self' (the cog instance)
                    if args and hasattr(args[0], "bot"):
                        bot = args[0].bot
                        logger_instance = Logger(bot)
                        # Apply logger and call the function
                        logged_func = logger_instance(f, **kwargs)
                        return await logged_func(*args, **func_kwargs)
                    else:
                        # Fallback: just call the function
                        return await f(*args, **func_kwargs)

                return wrapper
            return f

        return get_logger_decorator(func)

    return decorator


__all__ = ["setup_logger", "log"]
