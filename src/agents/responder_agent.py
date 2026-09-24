import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple
from src.models import MasterProfile, InboundMessage

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

class ResponderAgent:
    """Intelligent lead-retention and auto-responder agent powered by Gemini 3.6 Flash."""
    
    def __init__(self, profile_path: str = "config/profile.json"):
        _ensure_env()
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            
        with open(p_path, "r", encoding="utf-8") as f:
            self.profile = MasterProfile(**json.load(f))

        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-3.6-flash"

    def evaluate_and_respond(self, msg: InboundMessage) -> Tuple[str, bool]:
        """
        Evaluates inbound message and generates an immediate holding reply.
        Returns: (reply_text, requires_human_escalation)
        """
        text = msg.message_text.lower()
        client_name = msg.client_name or "there"
        booking_url = self.profile.personal_info.calendar_booking_url or "https://calendly.com"
        portfolio_url = self.profile.personal_info.portfolio_url or "https://github.com"
        hourly_rate = self.profile.preferences.rates.get("preferred_hourly_usd", 65)

        # 1. Critical Escalation Check: Legal, Contracts, Banking, Disputes
        escalation_patterns = [
            r"\bnda\b", r"\bnon-disclosure\b", r"\bsign (the|a|this)? ?contract\b",
            r"\bcontract (agreement|terms|clause|review)\b", r"\bpayment terms\b",
            r"\bdown payment\b", r"\bdispute\b", r"\bwire transfer\b",
            r"\bbank (details|account|routing)\b", r"\bw-?9\b", r"\btax (form|id)\b",
            r"\bidentity (check|verification)\b", r"\bpassport\b", r"\bid card\b"
        ]
        if any(re.search(pat, text) for pat in escalation_patterns):
            reply = (
                f"Hi {client_name},\n\n"
                f"Thank you for sharing this! I have received your message regarding {msg.platform} and will personally review the documentation/specifics right away.\n\n"
                f"I'll follow up shortly today with the confirmed details.\n\n"
                f"Best regards,\n{self.profile.personal_info.full_name}"
            )
            return reply, True

        # 2. Generative AI Response with Gemini 3.6 Flash
        if self.api_key:
            try:
                import requests
                case_studies_summary = "; ".join([
                    f"{cs.title}: {cs.summary} ({', '.join(cs.tech_stack)})" for cs in self.profile.case_studies[:2]
                ])

                prompt = (
                    f"You are {self.profile.personal_info.full_name}, a {self.profile.personal_info.professional_title}.\n"
                    f"An interested client or recruiter has sent you a message on {msg.platform}.\n\n"
                    f"CLIENT MESSAGE from {client_name}:\n"
                    f"\"{msg.message_text}\"\n\n"
                    f"YOUR DOSSIER & CONTEXT:\n"
                    f"- Preferred Rate: ${hourly_rate}/hr (or structured milestone pricing for clear specs)\n"
                    f"- Portfolio & Live Work: {portfolio_url}\n"
                    f"- Calendar for 15-min discovery call: {booking_url}\n"
                    f"- Highlighted Projects: {case_studies_summary}\n\n"
                    f"OBJECTIVES:\n"
                    f"1. Respond directly to the client's specific inquiry (answer questions about stack, rate, or availability warmly and concisely).\n"
                    f"2. Maintain a warm, highly competent, professional tone.\n"
                    f"3. Keep the reply under 100 words.\n"
                    f"4. Proactively encourage booking a brief 15-minute call using your calendar link ({booking_url}).\n"
                    f"5. Output ONLY the response text with greeting and sign-off. Do not include placeholder brackets."
                )

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
                resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=12)

                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        gen_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        if gen_text and gen_text.strip():
                            return gen_text.strip(), False
            except Exception as e:
                print(f"[ResponderAgent] Gemini API notice: {e}, falling back to heuristics")

        # 3. Heuristic Fallback Templates
        if any(w in text for w in ["rate", "price", "cost", "how much", "budget", "quote"]):
            reply = (
                f"Hi {client_name},\n\n"
                f"Thanks for reaching out! Depending on project scope, my standard rate is ${hourly_rate}/hr, "
                f"or we can structure this as a fixed-price milestone agreement if you have a defined specification.\n\n"
                f"I'd be glad to jump on a quick 10-15 minute call to review the details and provide an exact estimate: {booking_url}.\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )
        elif any(w in text for w in ["portfolio", "sample", "past work", "examples", "github", "live site"]):
            reply = (
                f"Hi {client_name},\n\n"
                f"Absolutely! You can explore my live projects, code repositories, and case studies here: {portfolio_url}\n\n"
                f"Does your project require similar features? Let's connect directly: {booking_url}\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )
        elif any(w in text for w in ["call", "meet", "interview", "zoom", "google meet", "chat", "available", "schedule"]):
            reply = (
                f"Hi {client_name},\n\n"
                f"I would be delighted to speak with you! My schedule is open this week. "
                f"Please feel free to choose any time slot that works best for you here: {booking_url}\n\n"
                f"Looking forward to learning more about your project.\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )
        else:
            reply = (
                f"Hi {client_name},\n\n"
                f"Thank you for reaching out! I've received your message and I'm very interested in assisting with this. "
                f"Let me know if you would like to jump on a brief discovery call to discuss: {booking_url}\n\n"
                f"Best regards,\n{self.profile.personal_info.full_name}"
            )

        return reply, False
