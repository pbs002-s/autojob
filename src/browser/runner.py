import asyncio
import random
from pathlib import Path
from typing import Optional

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    async_playwright = None

class BrowserRunner:
    """Manages persistent browser sessions for platform interactions and human-in-the-loop fallback."""
    
    def __init__(self, user_data_dir: str = "data/browser_profile", headless: bool = False):
        self.user_data_dir = Path(user_data_dir)
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None

    async def start(self):
        if async_playwright is None:
            raise RuntimeError("Playwright is not installed. Run `pip install playwright && playwright install chromium`.")
            
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.user_data_dir),
            headless=self.headless,
            slow_mo=50,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        print(f"[BrowserRunner] Persistent session active at {self.user_data_dir}")
        return self.context

    async def human_type(self, page: 'Page', selector: str, text: str):
        """Simulates human typing with random millisecond variations."""
        await page.wait_for_selector(selector)
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.04, 0.12))

    async def check_for_captcha_or_2fa(self, page: 'Page') -> bool:
        """Checks for common CAPTCHA/2FA indicators and pauses for manual human solving."""
        indicators = ["captcha", "challenge", "turnstile", "verify you are human", "enter code", "security check"]
        content = (await page.content()).lower()
        
        for indicator in indicators:
            if indicator in content:
                print("\n" + "="*60)
                print(f"🚨 [HITL ALERT] Security check/2FA detected: '{indicator}'")
                print("👉 Please solve the verification in the open browser window.")
                print("⏳ The agent is waiting up to 120 seconds...")
                print("="*60 + "\n")
                
                # Wait for user to solve
                for _ in range(24):
                    await asyncio.sleep(5)
                    new_content = (await page.content()).lower()
                    if indicator not in new_content:
                        print("✅ Verification cleared! Resuming automation...")
                        return True
                return False
        return True

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        print("[BrowserRunner] Browser session closed.")
