import requests
import json
import re
import html
import xml.etree.ElementTree as ET
from typing import List, Set
from src.agents.proposal_agent import ProposalAgent
from src.models import JobListing
from src.db import Database

class JobHunter:
    """Multi-source remote, contract, and freelance opportunity hunter across 5 high-yield feeds."""

    def __init__(self):
        self.proposal_agent = ProposalAgent()
        self.db = Database()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/xml, application/xml"
        }

    def _clean_html(self, raw_html: str) -> str:
        """Strips HTML tags and unescapes entities."""
        if not raw_html:
            return ""
        unescaped = html.unescape(raw_html)
        text = re.sub(r'<[^>]+>', ' ', unescaped)
        return " ".join(text.split())

    def _extract_hn_jobs(self, limit: int = 15) -> List[JobListing]:
        """Scrapes direct founder/CTO listings from the latest monthly YC 'Ask HN: Who is hiring?' thread."""
        hn_jobs = []
        try:
            # 1. Fetch latest hiring thread ID
            r = requests.get(
                "https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&hitsPerPage=2",
                headers=self.headers,
                timeout=10
            )
            if r.status_code != 200:
                return []
            
            stories = r.json().get("hits", [])
            hiring_story = next((s for s in stories if "who is hiring" in s.get("title", "").lower()), None)
            if not hiring_story:
                return []
                
            story_id = hiring_story.get("objectID")
            
            # 2. Fetch top-level comments (direct job postings)
            cr = requests.get(
                f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=60",
                headers=self.headers,
                timeout=12
            )
            if cr.status_code != 200:
                return []

            for hit in cr.json().get("hits", []):
                # Only consider top-level parent comments from the hiring companies
                if hit.get("parent_id") != int(story_id):
                    continue

                raw_text = self._clean_html(hit.get("comment_text", ""))
                lines = [line.strip() for line in raw_text.split(" | ") if line.strip()]
                
                # Check for remote or contract keywords
                text_lower = raw_text.lower()
                is_remote = any(term in text_lower for term in ["remote", "worldwide", "anywhere"])
                is_contract = any(term in text_lower for term in ["contract", "freelance", "part-time", "part time", "hourly", "c2c"])
                
                if not (is_remote or is_contract):
                    continue

                # Parse company and title from standard HN format: "Company | Title | Location | ..."
                company = "YC / Tech Founder"
                title = "Software Engineer / AI Builder"
                if len(lines) >= 2:
                    company = lines[0][:40]
                    title = lines[1][:60]
                elif lines:
                    title = lines[0][:60]

                # Extract URLs
                urls = re.findall(r'https?://[^\s()<>"]+', raw_text)
                target_url = urls[0] if urls else f"https://news.ycombinator.com/item?id={hit.get('objectID')}"

                job_type = "Part-Time / Contract" if is_contract else "Remote"
                hn_jobs.append(JobListing(
                    platform="Hacker News (YC)",
                    external_id=f"hn_{hit.get('objectID')}",
                    title=title,
                    company=company,
                    url=target_url,
                    description=raw_text[:1800],
                    budget_or_salary="Competitive / Equity",
                    location=f"Remote ({job_type})",
                    tags=["YC", "startup", "python", "fullstack", "ai"],
                    status="discovered"
                ))
                if len(hn_jobs) >= limit:
                    break
        except Exception as e:
            print(f"[Hunter] Hacker News notice: {e}")
            
        return hn_jobs

    def _extract_wwr_jobs(self, limit: int = 15) -> List[JobListing]:
        """Scrapes curated listings from WeWorkRemotely RSS feeds."""
        wwr_jobs = []
        feeds = [
            "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        ]
        
        for feed_url in feeds:
            try:
                r = requests.get(feed_url, headers=self.headers, timeout=12)
                if r.status_code != 200:
                    continue
                root = ET.fromstring(r.content)
                for item in root.findall(".//item"):
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    desc_elem = item.find("description")
                    guid_elem = item.find("guid")

                    if title_elem is None or link_elem is None:
                        continue

                    full_title = title_elem.text or ""
                    # WWR format is typically: "Company Name: Job Title"
                    company = "Remote Company"
                    job_title = full_title
                    if ":" in full_title:
                        parts = full_title.split(":", 1)
                        company = parts[0].strip()
                        job_title = parts[1].strip()

                    desc_text = self._clean_html(desc_elem.text if desc_elem is not None else "")
                    ext_id = f"wwr_{guid_elem.text if guid_elem is not None else link_elem.text}"

                    wwr_jobs.append(JobListing(
                        platform="WeWorkRemotely",
                        external_id=ext_id,
                        title=job_title[:80],
                        company=company[:60],
                        url=link_elem.text.strip(),
                        description=desc_text[:1800],
                        budget_or_salary=None,
                        location="Remote Worldwide",
                        tags=["remote", "fullstack", "backend", "software-eng"],
                        status="discovered"
                    ))
                    if len(wwr_jobs) >= limit:
                        break
            except Exception as e:
                print(f"[Hunter] WeWorkRemotely notice: {e}")
        return wwr_jobs

    def hunt_jobs(self, target_count: int = 30) -> List[JobListing]:
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
                        description=self._clean_html(item.get("description", ""))[:1800],
                        budget_or_salary=f"${item.get('salary_min')} - ${item.get('salary_max')}" if item.get("salary_min") and item.get("salary_max") else None,
                        location=f"{item.get('location', 'Worldwide')} ({job_type})",
                        tags=tags,
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] RemoteOK notice: {e}")

        # 2. Source: Remotive Software & Tech API
        try:
            r = requests.get("https://remotive.com/api/remote-jobs?category=software-dev&limit=30", headers=self.headers, timeout=12)
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
                        description=self._clean_html(item.get("description", ""))[:1800],
                        budget_or_salary=item.get("salary") or None,
                        location=f"{item.get('candidate_required_location', 'Remote Worldwide')} ({type_clean})",
                        tags=tags,
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] Remotive notice: {e}")

        # 3. Source: Jobicy API
        try:
            r = requests.get("https://jobicy.com/api/v2/remote-jobs?count=30", headers=self.headers, timeout=12)
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
                        description=self._clean_html(item.get("jobDescription", ""))[:1800],
                        budget_or_salary=str(item.get("annualSalaryMin")) if item.get("annualSalaryMin") else None,
                        location=f"{item.get('jobGeo', 'Remote Worldwide')} ({type_str})",
                        tags=tags if isinstance(tags, list) else [tags],
                        status="discovered"
                    ))
        except Exception as e:
            print(f"[Hunter] Jobicy notice: {e}")

        # 4. Source: WeWorkRemotely RSS
        all_candidates.extend(self._extract_wwr_jobs(limit=20))

        # 5. Source: Hacker News YC Direct Hiring
        all_candidates.extend(self._extract_hn_jobs(limit=15))

        # Deduplication & Scoring
        scored_jobs = []
        seen_urls: Set[str] = set()
        seen_slugs: Set[str] = set()

        for job in all_candidates:
            if not job.title or not job.url:
                continue

            # Normalized slug deduplication
            norm_slug = re.sub(r'[^a-z0-9]', '', (job.company + " " + job.title).lower())
            if job.url in seen_urls or (norm_slug and norm_slug in seen_slugs):
                continue
            seen_urls.add(job.url)
            if norm_slug:
                seen_slugs.add(norm_slug)

            score = self.proposal_agent.score_job_match(job)
            
            # Prioritize Part-time, Contract, and Freelance roles
            text_haystack = (job.title + " " + (job.location or "") + " " + " ".join(job.tags) + " " + job.description).lower()
            if any(term in text_haystack for term in ["part-time", "part time", "part_time", "contract", "freelance", "hourly"]):
                score = min(score + 15.0, 100.0)

            # Boost high-value tech keywords (FastAPI, React, Next.js, Python, AI, Full-Stack, Autonomous)
            if any(term in text_haystack for term in ["next.js", "react", "python", "ai", "fastapi", "full-stack", "typescript", "autonomous agent"]):
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

        print(f"[Hunter] Scouted {len(all_candidates)} candidates across 5 feeds. Saved {saved_count} new opportunities (top {len(top_selected)} matches).")
        return top_selected

if __name__ == "__main__":
    hunter = JobHunter()
    results = hunter.hunt_jobs(target_count=20)
    for i, j in enumerate(results, 1):
        print(f"{i:2d}. [{j.match_score:4.1f}%] {j.platform:16} | {j.title[:35]:35} | {j.company[:18]:18} | {j.url}")
