import requests
import json
from typing import List
from src.agents.proposal_agent import ProposalAgent
from src.models import JobListing
from src.db import Database

class JobHunter:
    """Multi-source remote and freelance job hunter targeting part-time and contract gigs."""

    def __init__(self):
        self.proposal_agent = ProposalAgent()
        self.db = Database()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

    def hunt_jobs(self, target_count: int = 20) -> List[JobListing]:
        all_candidates = []

        # 1. Source: RemoteOK API
        try:
            r = requests.get("https://remoteok.com/api", headers=self.headers, timeout=12)
            if r.status_code == 200:
                for item in r.json():
                    if not isinstance(item, dict) or "id" not in item:
                        continue
                    tags = item.get("tags", [])
                    is_contract = any(t in ["contract", "freelance", "part-time", "parttime"] for t in tags)
                    job_type = "Part-Time / Contract" if is_contract else "Remote"
                    all_candidates.append(JobListing(
                        platform="RemoteOK",
                        external_id=f"remoteok_{item.get('id')}",
                        title=item.get("position", "Remote Opportunity"),
                        company=item.get("company", "Confidential"),
                        url=item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id')}"),
                        description=item.get("description", "")[:1800],
                        budget_or_salary=f"${item.get('salary_min')} - ${item.get('salary_max')}" if item.get("salary_min") and item.get("salary_max") else None,
                        location=f"{item.get('location', 'Worldwide')} ({job_type})",
                        tags=tags,
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] RemoteOK notice: {e}")

        # 2. Source: Remotive Software & Tech API
        try:
            r = requests.get("https://remotive.com/api/remote-jobs?category=software-dev&limit=40", headers=self.headers, timeout=12)
            if r.status_code == 200:
                for item in r.json().get("jobs", []):
                    tags = item.get("tags", [])
                    raw_type = item.get("job_type", "remote")
                    type_clean = raw_type.replace("_", " ").title()
                    all_candidates.append(JobListing(
                        platform="Remotive",
                        external_id=f"remotive_{item.get('id')}",
                        title=item.get("title", ""),
                        company=item.get("company_name", "Tech Client"),
                        url=item.get("url", ""),
                        description=item.get("description", "")[:1800],
                        budget_or_salary=item.get("salary") or None,
                        location=f"{item.get('candidate_required_location', 'Remote Worldwide')} ({type_clean})",
                        tags=tags,
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] Remotive notice: {e}")

        # 3. Source: Jobicy API
        try:
            r = requests.get("https://jobicy.com/api/v2/remote-jobs?count=40", headers=self.headers, timeout=12)
            if r.status_code == 200:
                for item in r.json().get("jobs", []):
                    types = item.get("jobType", ["Remote"])
                    type_str = ", ".join(types) if isinstance(types, list) else str(types)
                    tags = item.get("jobIndustries", [])
                    all_candidates.append(JobListing(
                        platform="Jobicy",
                        external_id=f"jobicy_{item.get('id')}",
                        title=item.get("jobTitle", ""),
                        company=item.get("companyName", "Confidential"),
                        url=item.get("url", ""),
                        description=item.get("jobDescription", "")[:1800],
                        budget_or_salary=str(item.get("annualSalaryMin")) if item.get("annualSalaryMin") else None,
                        location=f"{item.get('jobGeo', 'Remote Worldwide')} ({type_str})",
                        tags=tags if isinstance(tags, list) else [tags],
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] Jobicy notice: {e}")

        # Score & prioritize part-time and contracts
        scored_jobs = []
        seen_urls = set()

        for job in all_candidates:
            if not job.title or job.url in seen_urls:
                continue
            seen_urls.add(job.url)

            score = self.proposal_agent.score_job_match(job)
            
            # Prioritize Part-time, Contract, and Freelance roles
            text_haystack = (job.title + " " + job.location + " " + " ".join(job.tags) + " " + job.description).lower()
            if any(term in text_haystack for term in ["part-time", "part time", "part_time", "contract", "freelance", "hourly"]):
                score = min(score + 15.0, 100.0)

            # Boost high-value tech keywords (FastAPI, React, Next.js, Python, AI, Full-Stack)
            if any(term in text_haystack for term in ["next.js", "react", "python", "ai", "fastapi", "full-stack", "typescript"]):
                score = min(score + 10.0, 100.0)

            job.match_score = round(score, 1)
            scored_jobs.append(job)

        # Sort descending by match score
        scored_jobs.sort(key=lambda x: x.match_score, reverse=True)
        top_selected = scored_jobs[:target_count]

        # Save to database
        saved_count = 0
        for job in top_selected:
            if self.db.save_job(job):
                saved_count += 1

        print(f"[Hunter] Hunted {len(all_candidates)} opportunities across 3 sources. Stored top {len(top_selected)} matches.")
        return top_selected

if __name__ == "__main__":
    hunter = JobHunter()
    results = hunter.hunt_jobs(target_count=20)
    for i, j in enumerate(results, 1):
        print(f"{i:2d}. [{j.match_score:4.1f}%] {j.title} | {j.company} | {j.location} | {j.url}")
