"""
Thali & Pulse — package entry point.
Loads .env at import time so every sub-module sees the environment variables.
"""

from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env", override=False)
except ImportError:
    pass  # dotenv is optional in production environments
