"""
SMS CDR Automation Bot - Single Script with Session Management
সব কিছু এক ফাইলে + 24/7 Session Keep Alive + Data Monitoring + Retry Logic
Exact parameters from curl requests
"""

import asyncio
import aiohttp
import re
import logging
import time
import json
from typing import Optional, Dict, List
from datetime import datetime
from urllib.parse import urlencode

# ============ CONFIGURATION ============
BASE_URL = "http://65.109.111.158"
USERNAME = "Wizard6"
PASSWORD = "Wizard6"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"

HEADERS = {
    'Accept-Language': 'en-BD,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
    'User-Agent': USER_AGENT,
    'Connection': 'keep-alive',
}

REQUEST_TIMEOUT = 30
LOG_FILE = "bot.log"
SESSION_CHECK_INTERVAL = 120  # 2 minutes
DATA_CHECK_INTERVAL = 15.5  # 15.5 seconds
MAX_RETRIES = 3
DATA_FETCH_MAX_RETRIES = 5
DATA_FETCH_RETRY_DELAY = 2  # seconds

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============ AUTHENTICATION CLASS ============
class SMSCDRBot:
    def __init__(self):
        self.base_url = BASE_URL
        self.username = USERNAME
        self.password = PASSWORD
        self.session: Optional[aiohttp.ClientSession] = None
        self.cookies = {}
        self.sesskey = None
        self.php_sessionid = None
        self.last_login_time = None
        self.session_active = False
        self.last_data_check = None
        self.previous_data = None
        self.data_check_count = 0
        self.successful_fetches = 0
        self.failed_fetches = 0

    async def __aenter__(self):
        """Context manager entry"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.session:
            await self.session.close()

    def solve_captcha(self, captcha_text: str) -> Optional[int]:
        """
        CAPTCHA solve করবে
        Example: "What is 5 + 5 = ?" -> 10
        """
        try:
            logger.info(f"🔍 Solving CAPTCHA: {captcha_text}")
            
            # Pattern: "What is X + Y = ?" or "What is X - Y = ?" etc.
            pattern = r'What is (\d+)\s*([\+\-\*/])\s*(\d+)\s*=\s*\?'
            match = re.search(pattern, captcha_text, re.IGNORECASE)
            
            if not match:
                logger.error(f"❌ CAPTCHA pattern not found: {captcha_text}")
                return None
            
            num1 = int(match.group(1))
            operator = match.group(2)
            num2 = int(match.group(3))
            
            # Calculate
            if operator == '+':
                result = num1 + num2
            elif operator == '-':
                result = num1 - num2
            elif operator == '*':
                result = num1 * num2
            elif operator == '/':
                result = int(num1 / num2)
            else:
                return None
            
            logger.info(f"✅ CAPTCHA solved: {num1} {operator} {num2} = {result}")
            return result
        except Exception as e:
            logger.error(f"❌ Error solving CAPTCHA: {e}")
            return None

    async def get_login_page(self) -> Optional[str]:
        """
        Login page fetch করবে CAPTCHA text পেতে
        """
        try:
            url = f"{self.base_url}/ints/login"
            headers = {
                **HEADERS,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Cache-Control': 'max-age=0',
            }
            
            logger.info(f"📄 Fetching login page...")
            async with self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, ssl=False) as resp:
                if resp.status == 200:
                    # Store cookies
                    self.cookies = dict(resp.cookies)
                    html = await resp.text()
                    logger.info(f"✅ Login page fetched successfully")
                    return html
                else:
                    logger.error(f"❌ Failed to fetch login page: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ Error fetching login page: {e}")
            return None

    def extract_captcha_text(self, html: str) -> Optional[str]:
        """
        HTML থেকে CAPTCHA text extract করবে
        """
        try:
            # CAPTCHA text খুঁজবে
            pattern = r'What is \d+ [\+\-\*/] \d+ = \?'
            match = re.search(pattern, html)
            
            if match:
                captcha_text = match.group(0)
                logger.info(f"🔐 CAPTCHA extracted: {captcha_text}")
                return captcha_text
            else:
                logger.error("❌ CAPTCHA pattern not found in HTML")
                return None
        except Exception as e:
            logger.error(f"❌ Error extracting CAPTCHA: {e}")
            return None

    def extract_session_key(self, html: str) -> Optional[str]:
        """
        HTML থেকে session key extract করবে
        """
        try:
            # Multiple patterns to find sesskey
            patterns = [
                r'sesskey=([A-Z0-9]+)',
                r'"sesskey":"([A-Z0-9]+)"',
                r"'sesskey':'([A-Z0-9]+)'",
                r'sesskey["\']?\s*:\s*["\']([A-Z0-9]+)["\']',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    sesskey = match.group(1)
                    logger.info(f"✅ Session key found: {sesskey}")
                    return sesskey
            
            # If not found in HTML, use PHPSESSID as fallback
            if 'PHPSESSID' in self.cookies:
                self.php_sessionid = self.cookies['PHPSESSID'].value
                logger.warning(f"⚠️ Session key not in HTML, using PHPSESSID: {self.php_sessionid}")
                return self.php_sessionid
            
            logger.error("❌ Session key not found")
            return None
        except Exception as e:
            logger.error(f"❌ Error extracting session key: {e}")
            return None

    async def login(self, retry_count=0) -> bool:
        """
        Login করবে with CAPTCHA solving
        """
        if retry_count >= MAX_RETRIES:
            logger.error(f"❌ Max retries ({MAX_RETRIES}) exceeded. Login failed.")
            return False
        
        try:
            logger.info(f"🔐 Login attempt #{retry_count + 1}/{MAX_RETRIES}")
            logger.info("=" * 60)
            
            # Step 1: Login page fetch করবে CAPTCHA পেতে
            logger.info("🔐 Step 1: Fetching login page...")
            html = await self.get_login_page()
            if not html:
                logger.error("❌ Failed to fetch login page. Retrying...")
                await asyncio.sleep(2)
                return await self.login(retry_count + 1)
            
            # Step 2: CAPTCHA extract এবং solve করবে
            logger.info("🔐 Step 2: Extracting CAPTCHA...")
            captcha_text = self.extract_captcha_text(html)
            if not captcha_text:
                logger.error("❌ Failed to extract CAPTCHA. Retrying...")
                await asyncio.sleep(2)
                return await self.login(retry_count + 1)
            
            logger.info("🔐 Step 3: Solving CAPTCHA...")
            captcha_answer = self.solve_captcha(captcha_text)
            if captcha_answer is None:
                logger.error("❌ Failed to solve CAPTCHA. Retrying...")
                await asyncio.sleep(2)
                return await self.login(retry_count + 1)
            
            # Step 4: Login করবে
            logger.info("🔐 Step 4: Logging in...")
            url = f"{self.base_url}/ints/signin"
            headers = {
                **HEADERS,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.base_url,
                'Referer': f"{self.base_url}/ints/login",
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            # Exact data from curl
            data = {
                'crlf': '',
                'username': self.username,
                'password': self.password,
                'capt': str(captcha_answer)
            }
            
            async with self.session.post(url, headers=headers, data=data, 
                                        cookies=self.cookies, timeout=REQUEST_TIMEOUT, ssl=False) as resp:
                # Update cookies
                self.cookies.update(dict(resp.cookies))
                
                if resp.status == 200:
                    html = await resp.text()
                    
                    # Check if login successful
                    if 'logout' in html.lower() or 'dashboard' in html.lower() or 'SMSCDRStats' in html:
                        logger.info("✅ Login successful!")
                        
                        # Extract session key
                        self.sesskey = self.extract_session_key(html)
                        
                        # Store PHPSESSID
                        if 'PHPSESSID' in self.cookies:
                            self.php_sessionid = self.cookies['PHPSESSID'].value
                            logger.info(f"✅ PHPSESSID: {self.php_sessionid}")
                        
                        self.last_login_time = datetime.now()
                        self.session_active = True
                        
                        logger.info("=" * 60)
                        logger.info(f"✅ Session established at {self.last_login_time}")
                        logger.info("=" * 60)
                        
                        return True
                    else:
                        logger.error("❌ Login failed - unknown error")
                        logger.debug(f"Response content (first 500 chars): {html[:500]}")
                        await asyncio.sleep(2)
                        return await self.login(retry_count + 1)
                else:
                    logger.error(f"❌ Login request failed: {resp.status}")
                    await asyncio.sleep(2)
                    return await self.login(retry_count + 1)
        except Exception as e:
            logger.error(f"❌ Error during login: {e}")
            import traceback
            logger.error(traceback.format_exc())
            await asyncio.sleep(2)
            return await self.login(retry_count + 1)

    async def check_session(self) -> bool:
        """
        Session check করবে - valid কিনা দেখবে
        """
        try:
            logger.info("🔍 Checking session validity...")
            
            # Try to access a protected page
            url = f"{self.base_url}/ints/agent/SMSCDRStats"
            headers = {
                **HEADERS,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            }
            
            async with self.session.get(url, headers=headers, cookies=self.cookies, 
                                       timeout=REQUEST_TIMEOUT, ssl=False) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    if 'logout' in html.lower() or 'SMSCDRStats' in html or 'dashboard' in html.lower():
                        logger.info(f"✅ Session is valid. Last login: {self.last_login_time}")
                        return True
                    else:
                        logger.warning("⚠️ Session appears to be invalid")
                        return False
                else:
                    logger.warning(f"⚠️ Session check returned status: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error checking session: {e}")
            return False

    async def fetch_sms_cdr_data(self, retry_count=0) -> Optional[List[Dict]]:
        """
        SMS CDR data fetch করবে - সাথে retry logic
        Exact parameters from curl
        """
        if retry_count >= DATA_FETCH_MAX_RETRIES:
            logger.error(f"❌ Max retries ({DATA_FETCH_MAX_RETRIES}) exceeded for data fetch")
            self.failed_fetches += 1
            return None
        
        try:
            self.data_check_count += 1
            logger.info(f"\n📊 Data Check #{self.data_check_count} at {datetime.now()} [Attempt {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}]")
            
            url = f"{self.base_url}/ints/agent/res/data_smscdr.php"
            
            # Exact parameters from curl request
            params = {
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
                'sesskey': self.sesskey or self.php_sessionid,
                'sEcho': '2',
                'iColumns': '9',
                'sColumns': ',,,,,,,,,',
                'iDisplayStart': '0',
                'iDisplayLength': '-1',
                'mDataProp_0': '0',
                'sSearch_0': '',
                'bRegex_0': 'false',
                'bSearchable_0': 'true',
                'bSortable_0': 'true',
                'mDataProp_1': '1',
                'sSearch_1': '',
                'bRegex_1': 'false',
                'bSearchable_1': 'true',
                'bSortable_1': 'true',
                'mDataProp_2': '2',
                'sSearch_2': '',
                'bRegex_2': 'false',
                'bSearchable_2': 'true',
                'bSortable_2': 'true',
                'mDataProp_3': '3',
                'sSearch_3': '',
                'bRegex_3': 'false',
                'bSearchable_3': 'true',
                'bSortable_3': 'true',
                'mDataProp_4': '4',
                'sSearch_4': '',
                'bRegex_4': 'false',
                'bSearchable_4': 'true',
                'bSortable_4': 'true',
                'mDataProp_5': '5',
                'sSearch_5': '',
                'bRegex_5': 'false',
                'bSearchable_5': 'true',
                'bSortable_5': 'true',
                'mDataProp_6': '6',
                'sSearch_6': '',
                'bRegex_6': 'false',
                'bSearchable_6': 'true',
                'bSortable_6': 'true',
                'mDataProp_7': '7',
                'sSearch_7': '',
                'bRegex_7': 'false',
                'bSearchable_7': 'true',
                'bSortable_7': 'true',
                'mDataProp_8': '8',
                'sSearch_8': '',
                'bRegex_8': 'false',
                'bSearchable_8': 'true',
                'bSortable_8': 'false',
                'sSearch': '',
                'bRegex': 'false',
                'iSortCol_0': '0',
                'sSortDir_0': 'desc',
                'iSortingCols': '1',
                '_': str(int(time.time() * 1000)),  # Current timestamp in milliseconds
            }
            
            headers = {
                **HEADERS,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{self.base_url}/ints/agent/SMSCDRStats',
            }
            
            async with self.session.get(url, params=params, headers=headers, 
                                       cookies=self.cookies, timeout=REQUEST_TIMEOUT, ssl=False) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type', '')
                    
                    # Check if response is JSON
                    if 'application/json' in content_type or 'text/javascript' in content_type:
                        data = await resp.json()
                        
                        if 'aaData' in data:
                            records = data['aaData']
                            logger.info(f"✅ Data fetched successfully - Total records: {len(records)}")
                            self.successful_fetches += 1
                            
                            # Print to terminal
                            print("\n" + "="*100)
                            print(f"📊 SMS CDR DATA - Check #{self.data_check_count} | Time: {datetime.now()}")
                            print(f"✅ SUCCESS | Total Records: {len(records)}")
                            print("="*100)
                            
                            if len(records) > 0:
                                print(f"{'Showing':<15} | First 5 records (total: {len(records)})")
                                print("-"*100)
                                
                                # Show first 5 records
                                for idx, record in enumerate(records[:5], 1):
                                    print(f"Record #{idx}: {record}")
                                
                                if len(records) > 5:
                                    print(f"... and {len(records) - 5} more records")
                            else:
                                print("ℹ️ No records found")
                            
                            print("="*100 + "\n")
                            
                            # Check if data changed
                            if self.previous_data and self.previous_data != records:
                                logger.info(f"🔔 NEW DATA DETECTED! ({len(records)} records)")
                            
                            self.previous_data = records
                            self.last_data_check = datetime.now()
                            
                            return records
                        else:
                            logger.warning("⚠️ No 'aaData' in JSON response, retrying...")
                            await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
                            return await self.fetch_sms_cdr_data(retry_count + 1)
                    else:
                        # HTML response received - session likely expired
                        logger.warning(f"⚠️ Received HTML instead of JSON (Content-Type: {content_type}) - Session may be expired")
                        self.session_active = False
                        return None
                
                elif resp.status == 503:
                    logger.warning(f"⚠️ Server Unavailable (503) - Retry {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}...")
                    await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
                    return await self.fetch_sms_cdr_data(retry_count + 1)
                else:
                    logger.error(f"❌ Data fetch failed: {resp.status} - Retry {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}...")
                    await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
                    return await self.fetch_sms_cdr_data(retry_count + 1)
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Request timeout - Retry {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}...")
            await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
            return await self.fetch_sms_cdr_data(retry_count + 1)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e} - Retry {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}...")
            await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
            return await self.fetch_sms_cdr_data(retry_count + 1)
        except Exception as e:
            logger.error(f"❌ Error fetching SMS CDR data: {e} - Retry {retry_count + 1}/{DATA_FETCH_MAX_RETRIES}...")
            import traceback
            logger.error(traceback.format_exc())
            await asyncio.sleep(DATA_FETCH_RETRY_DELAY)
            return await self.fetch_sms_cdr_data(retry_count + 1)

    async def keep_session_alive(self):
        """
        Session 24/7 keep alive রাখবে
        প্রতি 2 মিনিটে check করবে এবং প্রয়োজনে relogin করবে
        """
        logger.info("🔄 Starting session keep-alive monitor...")
        logger.info(f"📊 Session check interval: {SESSION_CHECK_INTERVAL} seconds")
        
        while True:
            try:
                await asyncio.sleep(SESSION_CHECK_INTERVAL)
                
                logger.info("-" * 60)
                logger.info(f"⏰ Session check at {datetime.now()}")
                
                # Check if session is still valid
                if not self.session_active or not await self.check_session():
                    logger.warning("⚠️ Session lost! Auto-relogging in...")
                    success = await self.login()
                    if success:
                        logger.info("✅ Session refreshed successfully")
                    else:
                        logger.error("❌ Failed to refresh session")
                else:
                    logger.info(f"✅ Session OK - Uptime: {datetime.now() - self.last_login_time}")
                
                logger.info("-" * 60)
                
            except asyncio.CancelledError:
                logger.info("🛑 Session monitor stopped")
                break
            except Exception as e:
                logger.error(f"❌ Error in keep_session_alive: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)  # Wait before retry

    async def monitor_data(self):
        """
        প্রতি 15.5 সেকেন্ডে নতুন data check করবে
        """
        logger.info("📡 Starting data monitoring...")
        logger.info(f"📊 Data check interval: {DATA_CHECK_INTERVAL} seconds\n")
        
        while True:
            try:
                await asyncio.sleep(DATA_CHECK_INTERVAL)
                
                if self.session_active:
                    await self.fetch_sms_cdr_data()
                else:
                    logger.warning("⚠️ Session not active, skipping data check")
                
            except asyncio.CancelledError:
                logger.info("🛑 Data monitor stopped")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitor_data: {e}")
                import traceback
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)

    def get_session_info(self) -> Dict:
        """Session information return করবে"""
        return {
            'active': self.session_active,
            'sesskey': self.sesskey,
            'phpsessid': self.php_sessionid,
            'last_login': self.last_login_time,
            'uptime': str(datetime.now() - self.last_login_time) if self.last_login_time else None,
            'data_checks': self.data_check_count,
            'successful_fetches': self.successful_fetches,
            'failed_fetches': self.failed_fetches,
            'last_data_check': self.last_data_check
        }


# ============ MAIN TEST FUNCTION ============
async def main():
    """Main function"""
    logger.info("\n" + "=" * 60)
    logger.info("🚀 SMS CDR Bot - Starting with Session Management + Data Monitoring")
    logger.info("=" * 60 + "\n")
    
    try:
        async with SMSCDRBot() as bot:
            # Initial login
            success = await bot.login()
            
            if not success:
                logger.error("❌ Initial login failed!")
                return
            
            logger.info("✅ Initial login successful!")
            logger.info(f"📊 Session Info: {bot.get_session_info()}\n")
            
            # Start background tasks
            keep_alive_task = asyncio.create_task(bot.keep_session_alive())
            monitor_task = asyncio.create_task(bot.monitor_data())
            
            try:
                # Keep running
                await asyncio.sleep(float('inf'))
            except KeyboardInterrupt:
                logger.info("\n⏹️ Stopping bot...")
                logger.info(f"📊 Final Stats: {bot.get_session_info()}")
                keep_alive_task.cancel()
                monitor_task.cancel()
                try:
                    await keep_alive_task
                except asyncio.CancelledError:
                    pass
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())


# ============ ENTRY POINT ============
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
