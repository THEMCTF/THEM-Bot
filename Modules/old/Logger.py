import asyncio
import functools
import inspect
import time

import disnake
from disnake.ext import commands


def Logger(func):
    """A decorator that logs information about function calls."""

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        """Synchronous wrapper for logging."""
        # --- Pre-execution logging ---
        start_time = time.perf_counter()
        class_name = None
        if args and hasattr(args[0], "__class__"):
            instance = args[0]
            class_name = instance.__class__.__name__

        print(f"Executing {func.__name__} (sync) in class {class_name or 'Unknown'}")

        # --- Execute original function ---
        result = func(*args, **kwargs)

        # --- Post-execution logging ---
        duration = (time.perf_counter() - start_time) * 1000
        print(f"Finished {func.__name__} in {duration:.2f}ms")
        return result

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        """Asynchronous wrapper for logging."""
        # --- Pre-execution logging ---
        start_time = time.perf_counter()
        caller_frame = inspect.stack()[1]
        caller_function_name = caller_frame.function
        class_name = None
        if args and hasattr(args[0], "__class__"):
            instance = args[0]
            class_name = instance.__class__.__name__

        print(f"Executing before {func.__name__}:")
        print(f"  - Called from function: {caller_function_name}")
        if class_name:
            print(f"  - Inside class: {class_name}")

        # --- Execute original function ---
        result = await func(*args, **kwargs)

        # --- Post-execution logging ---
        duration = (time.perf_counter() - start_time) * 1000
        print(f"Finished {func.__name__} in {duration:.2f}ms")
        return result

    # Return the correct wrapper based on whether the decorated function is async or not.
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper
