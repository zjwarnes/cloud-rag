"""Synthesis app configuration."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.config import get_synthesis_settings

settings = get_synthesis_settings()
