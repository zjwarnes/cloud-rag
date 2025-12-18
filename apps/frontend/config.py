"""Frontend app configuration."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from common.config import get_frontend_settings

settings = get_frontend_settings()
