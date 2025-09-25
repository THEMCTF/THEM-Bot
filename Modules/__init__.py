# /Users/starry/Desktop/Code/THEMc/bot/Modules/__init__.py

from .Logger import logger as global_logger
from .Logger import setup_logger

# The logger instance from Logger.py is already a callable decorator.
# We can just import it and alias it as 'log'.
log = global_logger

__all__ = ["setup_logger", "log"]
