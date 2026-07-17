"""
SMS CDR Automation Bot - Single Script
সব কিছু এক ফাইলে
"""

import asyncio
import aiohttp
import re
import logging
from typing import Optional, Dict

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

    async def login(self) -> bool:
        """
        Login করবে with CAPTCHA solving
        """
        try:
            # Step 1: Login page fetch করবে CAPTCHA পেতে
            logger.info("🔐 Step 1: Fetching login page...")
            html = await self.get_login_page()
            if not html:
                return False
            
            # Step 2: CAPTCHA extract এবং solve করবে
            logger.info("🔐 Step 2: Extracting CAPTCHA...")
            captcha_text = self.extract_captcha_text(html)
            if not captcha_text:
                return False
            
            logger.info("🔐 Step 3: Solving CAPTCHA...")
            captcha_answer = self.solve_captcha(captcha_text)
            if captcha_answer is None:
                return False
            
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
            }
            
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
                        
                        # Extract sesskey from HTML or URL
                        sesskey_pattern = r'sesskey=([A-Z0-9]+)'
                        match = re.search(sesskey_pattern, html)
                        if match:
                            self.sesskey = match.group(1)
                            logger.info(f"✅ Session key extracted: {self.sesskey}")
                        else:
                            logger.warning("⚠️ Session key not found in HTML")
                        
                        return True
                    else:
                        logger.error("❌ Login failed - unknown error")
                        logger.debug(f"Response content (first 500 chars): {html[:500]}")
                        return False
                else:
                    logger.error(f"❌ Login request failed: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error during login: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_session_key(self) -> Optional[str]:
        """Session key return করবে"""
        return self.sesskey

    def get_cookies(self) -> Dict:
        """Cookies return করবে"""
        return self.cookies


# ============ TEST FUNCTION ============
async def test_login():
    """Login test করবে"""
    logger.info("=" * 50)
    logger.info("🚀 Starting Login Test...")
    logger.info("=" * 50)
    
    try:
        async with SMSCDRBot() as bot:
            success = await bot.login()
            
            logger.info("=" * 50)
            if success:
                logger.info("✅ LOGIN SUCCESSFUL!")
                logger.info(f"Session Key: {bot.get_session_key()}")
                logger.info(f"Cookies: {bot.get_cookies()}")
            else:
                logger.info("❌ LOGIN FAILED!")
            logger.info("=" * 50)
            
            return success
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


# ============ MAIN ============
if __name__ == "__main__":
    print("\n" + "="*50)
    print("SMS CDR Bot - Login Test")
    print("="*50 + "\n")
    
    result = asyncio.run(test_login())
    
    if result:
        print("\n✅ Bot is ready for use!")
    else:
        print("\n❌ Bot failed to login. Check logs for details.")
