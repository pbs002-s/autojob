import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.models import MasterProfile, JobListing

def _ensure_env():
    if not os.getenv("GEMINI_API_KEY"):
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip().strip('"').strip("'")

class ProposalAgent:
    """Intelligent proposal and cover letter synthesis powered by Google Gemini 3.6 Flash."""

    def __init__(self, profile_path: str = "config/profile.json"):
        _ensure_env()
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            
        with open(p_path, "r", encoding="utf-8") as f:
            self.profile = MasterProfile(**json.load(f))
            
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-3.6-flash"

    def score_job_match(self, job: JobListing) -> float:
        """Calculates a comprehensive match score (0.0 to 100.0) against candidate profile."""
        content = (job.title + " " + job.description + " " + " ".join(job.tags) + " " + (job.location or "")).lower()
        
        all_skills = [s.lower() for sublist in self.profile.skills.values() for s in sublist]
        matched_skills = [skill for skill in all_skills if skill in content]
        
        score = 0.0
        
        # 1. Skill overlap (up to 50 points)
        if all_skills:
            overlap_ratio = len(matched_skills) / min(len(all_skills), 12)
            score += min(overlap_ratio * 50.0, 50.0)
            
        # 2. Target role match in title (up to 25 points)
        for role in self.profile.preferences.target_roles:
            if any(part.lower() in job.title.lower() for part in role.split() if len(part) > 2):
                score += 25.0
                break
                
        # 3. Remote suitability (10 points)
        if "remote" in content or "worldwide" in content or "anywhere" in content:
            score += 10.0

        # 4. Employment type alignment (10 points for contract/part-time/freelance)
        if any(term in content for term in ["contract", "part-time", "part time", "freelance", "hourly", "c2c"]):
            score += 10.0

        # 5. Core tech stack bonus (5 points for primary strengths: React, Python, Next.js, FastAPI, AI)
        if any(k in content for k in ["python", "react", "next.js", "fastapi", "ai agent", "playwright"]):
            score += 5.0
            
        return round(min(score, 100.0), 1)

    def _select_relevant_case_studies(self, job: JobListing, max_studies: int = 2) -> List[Any]:
        """Ranks case studies by keyword relevance to the target job."""
        content = (job.title + " " + job.description + " " + " ".join(job.tags)).lower()
        
        scored_studies = []
        for cs in self.profile.case_studies:
            match_points = sum(1 for tech in cs.tech_stack if tech.lower() in content)
            if any(term in content for term in cs.title.lower().split()):
                match_points += 2
            scored_studies.append((match_points, cs))

        scored_studies.sort(key=lambda x: x[0], reverse=True)
        return [cs for _, cs in scored_studies[:max_studies]]

    def generate_proposal(self, job: JobListing, tone: str = "standard") -> str:
        """
        Generates a personalized proposal addressing job requirements.
        Tones:
          - 'standard': Balanced, confident, professional (150-180 words)
          - 'technical': Architecture, stack depth, and testing focus (200 words)
          - 'concise': Ultra-crisp, direct problem solver (<100 words)
        """
        relevant_studies = self._select_relevant_case_studies(job, max_studies=2)
        primary_study = relevant_studies[0] if relevant_studies else None

        studies_context = "\n".join([
            f"- Project: {cs.title} ({cs.role}). Summary: {cs.summary}. Built with: {', '.join(cs.tech_stack)}. Demo/Code: {cs.live_url or 'N/A'}"
            for cs in relevant_studies
        ])

        tone_instructions = {
            "standard": (
                "Write in a confident, professional first-person ('I') tone (150-180 words). "
                "Hook the hiring manager in the first 2 sentences by directly addressing their core objective. "
                "Cite concrete metrics or architectural decisions from your past projects as proof. "
                "Provide 3 crisp bullet points detailing your execution roadmap. "
                "Close with a professional call-to-action referencing portfolio and Calendly."
            ),
            "technical": (
                "Write in a deep, architecture-first technical tone (180-220 words). "
                "Discuss technical nuances, clean code practices, async performance, test-driven development, and rapid integration. "
                "Mention your hands-on experience solving similar problems in your past systems. "
                "Close with an invitation to discuss technical architecture on Calendly."
            ),
            "concise": (
                "Write an ultra-crisp, punchy proposal under 100 words. "
                "Sentence 1: Exact problem solved. "
                "Sentence 2: Proof of capability citing relevant project. "
                "Sentence 3: Immediate availability & link to portfolio and Calendly."
            )
        }.get(tone, "standard")

        # Attempt to use Gemini 3.6 Flash
        if self.api_key:
            try:
                import requests
                prompt = (
                    f"You are writing a tailored job application proposal on behalf of {self.profile.personal_info.full_name}, "
                    f"a {self.profile.personal_info.professional_title}.\n\n"
                    f"TARGET OPPORTUNITY:\n"
                    f"Title: {job.title}\n"
                    f"Company: {job.company}\n"
                    f"Location/Type: {job.location}\n"
                    f"Description: {job.description[:1800]}\n"
                    f"Tags: {', '.join(job.tags)}\n\n"
                    f"CANDIDATE DOSSIER:\n"
                    f"Full Name: {self.profile.personal_info.full_name}\n"
                    f"Email: {self.profile.personal_info.email}\n"
                    f"Portfolio: {self.profile.personal_info.portfolio_url}\n"
                    f"GitHub: {self.profile.personal_info.github_url}\n"
                    f"LinkedIn: {self.profile.personal_info.linkedin_url}\n"
                    f"Calendly: {self.profile.personal_info.calendar_booking_url}\n\n"
                    f"RELEVANT CASE STUDIES:\n{studies_context}\n\n"
                    f"TONE & STYLE GUIDELINES:\n{tone_instructions}\n\n"
                    f"STRICT RULES:\n"
                    f"1. Never output placeholders like [Company Name] or [Insert Link] - use the provided facts or omit.\n"
                    f"2. Output ONLY the ready-to-send proposal text, with no preamble or commentary.\n"
                )
                
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=18)
                
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        gen_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if gen_text and gen_text.strip():
                            return gen_text.strip()
            except Exception as e:
                print(f"[ProposalAgent] Gemini API notice: {e}, falling back to template")

        # High-converting structured fallback template
        study_cite = f"In a recent project ({primary_study.title}), {primary_study.summary} We leveraged {', '.join(primary_study.tech_stack)}." if primary_study else ""
        
        fallback = (
            f"Hi there,\n\n"
            f"I came across your opening for \"{job.title}\" and was immediately drawn to it. "
            f"Given your focus on {', '.join(job.tags[:3]) if job.tags else 'modern engineering'}, "
            f"my background as a {self.profile.personal_info.professional_title} aligns directly with what you need.\n\n"
            f"{study_cite}\n\n"
            f"Here is how I can help your team:\n"
            f"1. Rapid onboarding and immediate delivery on key technical milestones.\n"
            f"2. Clean, well-documented, test-driven codebase.\n"
            f"3. Proactive, transparent communication throughout the engagement.\n\n"
            f"Feel free to review my live portfolio: {self.profile.personal_info.portfolio_url} (and GitHub: {self.profile.personal_info.github_url})\n"
            f"If you are available for a brief 10-15 minute sync, feel free to pick a time slot on my calendar: {self.profile.personal_info.calendar_booking_url}\n\n"
            f"Best regards,\n"
            f"{self.profile.personal_info.full_name}"
        )
        return fallback
