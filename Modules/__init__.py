import functools

from .Logger import setup_logger


def log(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        from .Logger import logger

        if logger:
            # Apply the logger decorator
            decorated_func = logger(func)
            return await decorated_func(*args, **kwargs)
        else:
            # If logger not ready, just run the function
            return await func(*args, **kwargs)

    return wrapper


__all__ = ["setup_logger", "log"]
