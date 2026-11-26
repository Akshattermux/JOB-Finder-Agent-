import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DB_PATH = os.getenv("JOB_AGENT_DB_PATH", str(BASE_DIR / "data" / "jobs.db"))

# Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# Default model for free tier
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Rate limiting for Gemini Free Tier (e.g., 15 RPM, 1M TPM)
GEMINI_RPM_LIMIT = int(os.getenv("GEMINI_RPM_LIMIT", "14"))  # conservative margin
GEMINI_RETRY_ATTEMPTS = int(os.getenv("GEMINI_RETRY_ATTEMPTS", "3"))

# Playwright browser configuration
HEADLESS_MODE = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() in ("true", "1", "yes")
BROWSER_TIMEOUT_MS = int(os.getenv("BROWSER_TIMEOUT_MS", "30000"))

# User profile path
PROFILE_PATH = os.getenv("USER_PROFILE_PATH", str(BASE_DIR / "config" / "user_profile.yaml"))
