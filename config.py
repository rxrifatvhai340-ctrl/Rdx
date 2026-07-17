"""
Configuration file for SMS CDR Bot
সব কাস্টমাইজেশন এখানে করুন
"""

# ============ LOGIN CREDENTIALS ============
LOGIN_URL = "http://65.109.111.158/ints/login"
SIGNIN_URL = "http://65.109.111.158/ints/signin"
SMS_CDR_URL = "http://65.109.111.158/ints/agent/res/data_smscdr.php"

USERNAME = "Wizard6"
PASSWORD = "Wizard6"

# ============ USER AGENT ============
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

# ============ HEADERS ============
COMMON_HEADERS = {
    'Accept-Language': 'en-BD,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': USER_AGENT,
    'Connection': 'keep-alive',
}

LOGIN_HEADERS = {
    **COMMON_HEADERS,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Cache-Control': 'max-age=0',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'http://65.109.111.158',
    'Referer': LOGIN_URL,
    'Upgrade-Insecure-Requests': '1',
}

SMS_CDR_HEADERS = {
    **COMMON_HEADERS,
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'http://65.109.111.158/ints/agent/SMSCDRStats',
}

# ============ TIMEOUT ============
REQUEST_TIMEOUT = 30

# ============ LOGGING ============
LOG_FILE = "bot.log"
LOG_LEVEL = "INFO"

# ============ SMS CDR PARAMS (Default) ============
DEFAULT_SMS_CDR_PARAMS = {
    'fdate1': '2026-07-17 00:00:00',
    'fdate2': '2026-07-17 23:59:59',
    'frange': '',
    'fclient': '',
    'fnum': '',
    'fcli': '',
    'fgdate': '',
    'fgmonth': '',
    'fgrange': '',
    'fgclient': '',
    'fgnumber': '',
    'fgcli': '',
    'fg': '0',
    'sesskey': '',  # এটি login এর পর পাবেন
    'sEcho': '2',
    'iColumns': '9',
    'sColumns': ',,,,,,,,',
    'iDisplayStart': '0',
    'iDisplayLength': '-1',
    'bSortable_0': 'true',
    'bSortable_1': 'true',
    'bSortable_2': 'true',
    'bSortable_3': 'true',
    'bSortable_4': 'true',
    'bSortable_5': 'true',
    'bSortable_6': 'true',
    'bSortable_7': 'true',
    'bSortable_8': 'false',
    'iSortCol_0': '0',
    'sSortDir_0': 'desc',
    'iSortingCols': '1',
}
