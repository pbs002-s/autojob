import json
from pathlib import Path
from typing import Dict, Any, Optional
from src.models import MasterProfile

class ProfileAgent:
    def __init__(self, profile_path: str = "config/profile.json"):
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            print(f"[ProfileAgent] Note: using example profile at {p_path}")
        
        with open(p_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.profile = MasterProfile(**data)

    def generate_upwork_profile(self) -> Dict[str, Any]:
        """Generates an optimized Upwork profile bundle."""
        p = self.profile
        skills_flat = [s for sublist in p.skills.values() for s in sublist][:15]
        
        overview = f"{p.bios.get('detailed_overview', p.bios['short_bio'])}\n\n"
        overview += "⭐ Highlighted Projects & Case Studies:\n"
        for cs in p.case_studies[:2]:
            overview += f"• {cs.title} ({cs.role}): {cs.summary}\n"
        
        overview += f"\nLet's schedule a call to discuss your goals!"

        return {
            "title": p.personal_info.professional_title,
            "hourly_rate_usd": p.preferences.rates.get("preferred_hourly_usd", 50),
            "overview": overview[:5000],
            "skills": skills_flat,
            "english_level": p.screening_answers.get("english_proficiency", "Fluent")
        }

    def generate_linkedin_profile(self) -> Dict[str, Any]:
        """Generates LinkedIn headline and about section."""
        p = self.profile
        headline = f"{p.personal_info.professional_title} | Helping companies build modern web apps & AI automations"[:220]
        
        about = f"{p.bios.get('detailed_overview', p.bios['short_bio'])}\n\n"
        about += f"📫 Reach me directly: {p.personal_info.email}\n"
        if p.personal_info.portfolio_url:
            about += f"🌐 Portfolio: {p.personal_info.portfolio_url}\n"
        if p.personal_info.calendar_booking_url:
            about += f"📅 Book a 15-min chat: {p.personal_info.calendar_booking_url}\n"

        return {
            "headline": headline,
            "about": about[:2600],
            "skills": [s for sublist in p.skills.values() for s in sublist][:50]
        }

    def generate_fiverr_gig(self, gig_category: str = "web_development") -> Dict[str, Any]:
        """Generates a high-converting Fiverr gig specification."""
        p = self.profile
        title = f"I will build high performance web applications and automation bots"[:80]
        description = (
            f"Looking for a reliable senior engineer to bring your project to life?\n\n"
            f"{p.bios['short_bio']}\n\n"
            f"What you will get:\n"
            f"- Clean, maintainable code\n"
            f"- Fast turnaround & clear communication\n"
            f"- Responsive, mobile-first design\n\n"
            f"Please message me before ordering so we can discuss the requirements!"
        )

        base_rate = p.preferences.rates.get("minimum_project_budget_usd", 200)

        packages = {
            "Basic": {
                "name": "Starter / Bug Fix / Script",
                "price": base_rate,
                "delivery_days": 2,
                "description": "Custom script, small feature integration, or single-page landing component."
            },
            "Standard": {
                "name": "Full Feature / Multi-page App",
                "price": base_rate * 2.5,
                "delivery_days": 5,
                "description": "Complete 3-5 page responsive web app or full browser automation pipeline."
            },
            "Premium": {
                "name": "Turnkey Full-Stack Solution",
                "price": base_rate * 5,
                "delivery_days": 10,
                "description": "Enterprise-ready full stack platform with database, authentication, and deployment."
            }
        }

        return {
            "gig_title": title,
            "category": "Programming & Tech",
            "search_tags": ["web application", "python automation", "full stack", "react", "nextjs"][:5],
            "description": description[:1200],
            "packages": packages
        }
