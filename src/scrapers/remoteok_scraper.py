import requests
import json
from typing import List
from src.models import JobListing

class RemoteOKScraper:
    """Scrapes live remote jobs from RemoteOK without authentication barriers."""
    
    API_URL = "https://remoteok.com/api"
    
    def __init__(self, user_agent: str = "AutoJobBot/1.0 (contact: info@autojob.local)"):
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json"
        }

    def fetch_jobs(self, limit: int = 20) -> List[JobListing]:
        listings = []
        try:
            resp = requests.get(self.API_URL, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                print(f"[RemoteOK] Failed to fetch: status {resp.status_code}")
                return []
                
            data = resp.json()
            # The first element of RemoteOK API is usually a legal disclaimer object
            job_items = [item for item in data if isinstance(item, dict) and "id" in item]
            
            for item in job_items[:limit]:
                title = item.get("position", "Remote Opportunity")
                company = item.get("company", "Confidential")
                url = item.get("url", f"https://remoteok.com/remote-jobs/{item.get('id')}")
                description = item.get("description", "")
                tags = item.get("tags", [])
                location = item.get("location", "Remote")
                salary_min = item.get("salary_min")
                salary_max = item.get("salary_max")
                salary_str = f"${salary_min} - ${salary_max}" if salary_min and salary_max else None

                listing = JobListing(
                    platform="remoteok",
                    external_id=str(item.get("id")),
                    title=title,
                    company=company,
                    url=url,
                    description=description,
                    budget_or_salary=salary_str,
                    location=location,
                    tags=tags,
                    status="discovered"
                )
                listings.append(listing)
        except Exception as e:
            print(f"[RemoteOK] Error fetching jobs: {e}")
            
        return listings
