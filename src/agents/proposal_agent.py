import os
import json
from pathlib import Path
from typing import Dict, Any, Tuple
from src.models import MasterProfile, JobListing

class ProposalAgent:
    def __init__(self, profile_path: str = "config/profile.json"):
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            
        with open(p_path, "r", encoding="utf-8") as f:
            self.profile = MasterProfile(**json.load(f))
            
        self.api_key = os.getenv("GEMINI_API_KEY")

    def score_job_match(self, job: JobListing) -> float:
        """Calculates a match score from 0.0 to 100.0 between profile and job description."""
        content = (job.title + " " + job.description + " " + " ".join(job.tags)).lower()
        
        all_skills = [s.lower() for sublist in self.profile.skills.values() for s in sublist]
        matched_skills = [skill for skill in all_skills if skill in content]
        
        score = 0.0
        
        # Skill overlap (up to 60 points)
        if all_skills:
            overlap_ratio = len(matched_skills) / min(len(all_skills), 15)
            score += min(overlap_ratio * 60, 60)
            
        # Target role match in title (up to 30 points)
        for role in self.profile.preferences.target_roles:
            if any(part.lower() in job.title.lower() for part in role.split()):
                score += 30
                break
                
        # Remote match (10 points)
        if "remote" in content or "remote" in job.location.lower():
            score += 10
            
        return round(min(score, 100.0), 1)

    def generate_proposal(self, job: JobListing) -> str:
        """Generates a personalized, professional proposal addressing job requirements."""
        # Find the most relevant case study
        content = (job.title + " " + job.description).lower()
        relevant_study = self.profile.case_studies[0]
        for cs in self.profile.case_studies:
            if any(t.lower() in content for t in cs.tech_stack):
                relevant_study = cs
                break

        # Attempt to use Gemini LLM API if key is present
        if self.api_key:
            try:
                import requests
                prompt = (
                    f"You are a professional proposal writer crafting an application on behalf of {self.profile.personal_info.full_name}, "
                    f"a {self.profile.personal_info.professional_title}.\n\n"
                    f"TARGET JOB:\n"
                    f"Title: {job.title}\n"
                    f"Company: {job.company}\n"
                    f"Description: {job.description[:1500]}\n\n"
                    f"CANDIDATE PROFILE:\n"
                    f"Full Name: {self.profile.personal_info.full_name}\n"
                    f"Portfolio: {self.profile.personal_info.portfolio_url}\n"
                    f"GitHub: {self.profile.personal_info.github_url}\n"
                    f"LinkedIn: {self.profile.personal_info.linkedin_url}\n"
                    f"Calendly: {self.profile.personal_info.calendar_booking_url}\n"
                    f"Relevant Project: {relevant_study.title} ({relevant_study.summary}) Built with: {', '.join(relevant_study.tech_stack)}. Demo/Code: {relevant_study.live_url}\n\n"
                    f"REQUIREMENTS:\n"
                    f"1. Write in confident, professional first-person ('I'). Keep it under 200 words.\n"
                    f"2. Hook the hiring manager in the first 2 sentences by directly addressing their primary problem.\n"
                    f"3. Specifically cite your work in {relevant_study.title} as proof of capability.\n"
                    f"4. Propose 3 concise bullet points outlining how you will deliver results.\n"
                    f"5. End with a polite CTA referencing your portfolio ({self.profile.personal_info.portfolio_url}) and Calendly link ({self.profile.personal_info.calendar_booking_url}).\n"
                    f"Do NOT include placeholder brackets [like this]. Output only the final proposal text."
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
                resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        gen_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if gen_text.strip():
                            return gen_text.strip()
            except Exception:
                pass

        # High-converting structured fallback template
        proposal = (
            f"Hi there,\n\n"
            f"I came across your opening for \"{job.title}\" and was immediately drawn to it. "
            f"Given your focus on {', '.join(job.tags[:3]) if job.tags else 'modern engineering'}, "
            f"my background as a {self.profile.personal_info.professional_title} aligns directly with what you need.\n\n"
            f"In a recent project ({relevant_study.title}), {relevant_study.summary} "
            f"We leveraged {', '.join(relevant_study.tech_stack)}, solving similar technical challenges.\n\n"
            f"Here is how I can help your team:\n"
            f"1. Rapid onboarding and immediate delivery on key milestones.\n"
            f"2. Clean, well-documented, test-driven codebase.\n"
            f"3. Proactive, transparent communication throughout the engagement.\n\n"
            f"Feel free to review my live portfolio: {self.profile.personal_info.portfolio_url} (and GitHub: {self.profile.personal_info.github_url})\n"
            f"If you are available for a brief 10-15 minute sync, feel free to pick a time slot on my calendar: {self.profile.personal_info.calendar_booking_url}\n\n"
            f"Best regards,\n"
            f"{self.profile.personal_info.full_name}"
        )
        return proposal
