"""
Configuration file for SMS CDR Bot
সব কাস্টমাইজেশন এখানে করুন
"""

# ============ BASE URL ============
BASE_URL = "http://65.109.111.158"

# ============ LOGIN CREDENTIALS ============
USERNAME = "Wizard6"
PASSWORD = "Wizard6"

# ============ USER AGENT ============
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

# ============ COMMON HEADERS (সব API এর জন্য) ============
HEADERS = {
    'Accept-Language': 'en-BD,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': USER_AGENT,
    'Connection': 'keep-alive',
}

# ============ TIMEOUT ============
REQUEST_TIMEOUT = 30

# ============ LOGGING ============
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"
