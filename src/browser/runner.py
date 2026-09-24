import asyncio
import json
import os
import random
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any, List

try:
    from playwright.async_api import async_playwright, BrowserContext, Page
except ImportError:
    async_playwright = None

from src.models import MasterProfile

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
            slow_mo=40,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        print(f"[BrowserRunner] Persistent session active at {self.user_data_dir}")
        return self.context

    async def human_type(self, page: 'Page', selector: str, text: str):
        """Simulates human typing with random millisecond variations."""
        await page.wait_for_selector(selector, timeout=6000)
        await page.click(selector)
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.02, 0.08))

    async def check_for_captcha_or_2fa(self, page: 'Page') -> bool:
        """Checks for common CAPTCHA/2FA indicators and pauses for manual human solving."""
        indicators = ["captcha", "challenge", "turnstile", "verify you are human", "enter code", "security check"]
        try:
            content = (await page.content()).lower()
            for indicator in indicators:
                if indicator in content:
                    print("\n" + "="*60)
                    print(f"🚨 [HITL ALERT] Security check/2FA detected: '{indicator}'")
                    print("👉 Please solve the verification in the open browser window.")
                    print("⏳ The agent is waiting up to 120 seconds...")
                    print("="*60 + "\n")
                    
                    for _ in range(24):
                        await asyncio.sleep(5)
                        new_content = (await page.content()).lower()
                        if indicator not in new_content:
                            print("✅ Verification cleared! Resuming automation...")
                            return True
                    return False
        except Exception:
            pass
        return True

    async def stop(self):
        if self.context:
            try:
                await self.context.close()
            except Exception:
                pass
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception:
                pass
        print("[BrowserRunner] Browser session closed.")


class JobApplicationAssistant:
    """Autonomous application pre-filler and form assistant with Human-in-the-Loop review."""

    def __init__(self, profile_path: str = "config/profile.json", headless: bool = False):
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            
        with open(p_path, "r", encoding="utf-8") as f:
            self.profile = MasterProfile(**json.load(f))
            
        self.runner = BrowserRunner(headless=headless)

    async def auto_prefill_job(self, job_url: str, proposal_text: str = "") -> Dict[str, Any]:
        """
        Launches persistent Chromium session, navigates to job URL, detects application form fields,
        pre-fills candidate dossier + custom proposal, and keeps the page open for human verification.
        """
        filled_fields = []
        status = "opened"

        if async_playwright is None:
            print(f"[Assistant] Playwright not found; launching default system browser for {job_url}")
            webbrowser.open(job_url)
            return {
                "status": "fallback_opened",
                "message": "Opened in default system browser. Copy proposal text from Workbench.",
                "url": job_url,
                "filled_fields": []
            }

        try:
            context = await self.runner.start()
            page = await context.new_page()
            print(f"[Assistant] Navigating to opportunity: {job_url}")
            await page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(2)

            # Check for CAPTCHA/bot challenges
            await self.runner.check_for_captcha_or_2fa(page)

            # Heuristic: Check if there's an "Apply" button or link to click first
            apply_selectors = [
                'a:has-text("Apply for this job")',
                'a:has-text("Apply Now")',
                'button:has-text("Apply for this job")',
                'button:has-text("Apply Now")',
                'a[href*="apply"]',
                'a[href*="lever.co"]',
                'a[href*="greenhouse.io"]'
            ]
            for sel in apply_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        print(f"[Assistant] Navigating via entrypoint: {sel}")
                        await elem.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            # Candidate Profile mappings
            p_info = self.profile.personal_info
            name_parts = p_info.full_name.split()
            first_name = name_parts[0] if name_parts else ""
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else first_name

            mappings = [
                (['input[name*="name" i]:not([name*="first" i]):not([name*="last" i])', 'input[id*="name" i]:not([id*="first" i]):not([id*="last" i])', 'input[autocomplete="name"]'], p_info.full_name, "Full Name"),
                (['input[name*="first" i]', 'input[id*="first" i]'], first_name, "First Name"),
                (['input[name*="last" i]', 'input[id*="last" i]'], last_name, "Last Name"),
                (['input[type="email"]', 'input[name*="email" i]', 'input[id*="email" i]', 'input[autocomplete="email"]'], p_info.email, "Email"),
                (['input[type="tel"]', 'input[name*="phone" i]', 'input[id*="phone" i]'], p_info.phone or "", "Phone"),
                (['input[name*="location" i]', 'input[id*="location" i]', 'input[name*="city" i]'], p_info.location, "Location"),
                (['input[name*="linkedin" i]', 'input[id*="linkedin" i]', 'input[placeholder*="linkedin" i]'], p_info.linkedin_url or "", "LinkedIn"),
                (['input[name*="github" i]', 'input[id*="github" i]', 'input[placeholder*="github" i]'], p_info.github_url or "", "GitHub"),
                (['input[name*="portfolio" i]', 'input[name*="website" i]', 'input[id*="portfolio" i]', 'input[id*="website" i]'], p_info.portfolio_url or "", "Portfolio URL"),
            ]

            # Fill text inputs
            for selectors, val, label in mappings:
                if not val:
                    continue
                for sel in selectors:
                    try:
                        elem = await page.query_selector(sel)
                        if elem and await elem.is_visible():
                            curr_val = await elem.input_value()
                            if not curr_val:
                                await elem.fill(val)
                                filled_fields.append(label)
                                print(f"[Assistant] Pre-filled {label}: {val}")
                                break
                    except Exception:
                        continue

            # Fill Cover Letter / Proposal textarea
            if proposal_text:
                proposal_selectors = [
                    'textarea[name*="cover" i]',
                    'textarea[name*="letter" i]',
                    'textarea[name*="proposal" i]',
                    'textarea[name*="comments" i]',
                    'textarea[id*="cover" i]',
                    'textarea[id*="letter" i]',
                    'textarea'
                ]
                for p_sel in proposal_selectors:
                    try:
                        elem = await page.query_selector(p_sel)
                        if elem and await elem.is_visible():
                            curr_val = await elem.input_value()
                            if not curr_val:
                                await elem.fill(proposal_text)
                                filled_fields.append("Cover Letter / Proposal")
                                print(f"[Assistant] Injected tailored proposal into form")
                                break
                    except Exception:
                        continue

            # Check for Resume upload input if present in workspace
            resume_path = Path("data/resume.pdf")
            if not resume_path.exists():
                resume_path = Path("resume.pdf")

            if resume_path.exists():
                try:
                    file_input = await page.query_selector('input[type="file"]')
                    if file_input:
                        await file_input.set_input_files(str(resume_path.resolve()))
                        filled_fields.append("Resume PDF Attached")
                        print(f"[Assistant] Attached resume from {resume_path}")
                except Exception as e:
                    print(f"[Assistant] File upload notice: {e}")

            status = "ready_for_review"
            print(f"\n[Assistant] Automation completed! Pre-filled fields: {filled_fields}")
            print(f"[Assistant] Leaving browser window open for your final inspection & submission.\n")

            return {
                "status": status,
                "message": f"Pre-filled {len(filled_fields)} fields in browser.",
                "url": job_url,
                "filled_fields": filled_fields
            }

        except Exception as e:
            print(f"[Assistant] Browser automation notice: {e}")
            return {
                "status": "error",
                "message": str(e),
                "url": job_url,
                "filled_fields": filled_fields
            }
