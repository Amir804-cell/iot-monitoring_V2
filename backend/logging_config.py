import logging
import sys

def configure_logging():
    """
    Configure structured logging for the FastAPI backend.

    Format is inspired by SPDLog:
    [timestamp] [level] [logger] message
    """
    root = logging.getLogger()
    if root.handlers:
        # Already configured
        return

    handler = logging.StreamHandler(sys.stdout)
    fmt = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    handler.setFormatter(formatter)

    root.setLevel(logging.INFO)
    root.addHandler(handler)
