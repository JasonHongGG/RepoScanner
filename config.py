import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MIN_PUSHED_DATE = os.getenv("MIN_PUSHED_DATE", "2024-01-01")
OUTPUT_FORMAT = os.getenv("OUTPUT_FORMAT", "csv").lower()
SEARCH_QUERY_LIMIT = 1000  # Safety limit

# Regex Patterns for Secrets
PATTERNS = {
    # Cloud / AI Providers
    "OPENAI_API_KEY": r"sk-[a-zA-Z0-9\-_]{20,}",
    "GEMINI_API_KEY": r"AIza[0-9A-Za-z\-_]{35}",
    "AWS_ACCESS_KEY": r"AKIA[0-9A-Z]{16}",
    
    # SaaS / Social
    "SLACK_BOT_TOKEN": r"xoxb-[0-9]{11,12}-[0-9]{12,}-[a-zA-Z0-9]{24,}",
    "SLACK_USER_TOKEN": r"xoxp-[0-9]{11,12}-[0-9]{11,12}-[0-9]{12,}-[a-zA-Z0-9]{24,}",
    "STRIPE_LIVE_KEY": r"(?:sk|rk)_live_[0-9a-zA-Z]{24}",
    "FACEBOOK_ACCESS_TOKEN": r"EAACEdEose0cBA[0-9A-Za-z]+",
    
    # Infrastructure / DB
    "PRIVATE_KEY_BLOCK": r"-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----",
    "GENERIC_PASSWORD": r"[\"']password[\"']\s*[:=]\s*[\"'](.*?)[\"']", 
    "POSTGRES_URI": r"postgres://[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
    "MONGO_URI": r"mongodb(\+srv)?:\/\/[a-zA-Z0-9_\-]+:[a-zA-Z0-9_\-]+@",
}

SUSPICIOUS_REPO_NAME_PATTERN = r'^[0-9a-fA-F]{30,}$'

# Search Configuration
MAX_STARS = 10  # We want low-star repos
