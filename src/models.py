from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PersonalInfo(BaseModel):
    full_name: str
    professional_title: str
    email: str
    phone: Optional[str] = None
    location: str
    portfolio_url: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    calendar_booking_url: Optional[str] = None

class Preferences(BaseModel):
    target_roles: List[str]
    employment_types: List[str]
    rates: Dict[str, float]
    max_weekly_hours: int = 40

class CaseStudy(BaseModel):
    title: str
    role: str
    tech_stack: List[str]
    summary: str
    live_url: Optional[str] = None

class MasterProfile(BaseModel):
    personal_info: PersonalInfo
    preferences: Preferences
    bios: Dict[str, str]
    skills: Dict[str, List[str]]
    case_studies: List[CaseStudy]
    screening_answers: Dict[str, str]
    client_holding_templates: Dict[str, str]

class JobListing(BaseModel):
    id: Optional[int] = None
    platform: str
    external_id: str
    title: str
    company: str
    url: str
    description: str
    budget_or_salary: Optional[str] = None
    location: Optional[str] = "Remote"
    tags: List[str] = Field(default_factory=list)
    match_score: Optional[float] = 0.0
    status: str = "discovered"  # discovered, scored, applied, rejected, interviewing
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InboundMessage(BaseModel):
    platform: str
    client_name: str
    client_id: Optional[str] = None
    subject: Optional[str] = None
    message_text: str
    received_at: datetime = Field(default_factory=datetime.utcnow)
