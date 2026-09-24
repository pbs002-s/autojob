import json
import re
from pathlib import Path
from typing import Dict, Any, Tuple
from src.models import MasterProfile, InboundMessage

class ResponderAgent:
    """Agent dedicated to rapidly responding to client messages & emails to hold lead interest."""
    
    def __init__(self, profile_path: str = "config/profile.json"):
        p_path = Path(profile_path)
        if not p_path.exists():
            p_path = Path("config/profile.example.json")
            
        with open(p_path, "r", encoding="utf-8") as f:
            self.profile = MasterProfile(**json.load(f))

    def evaluate_and_respond(self, msg: InboundMessage) -> Tuple[str, bool]:
        """
        Evaluates inbound message and generates an immediate holding reply.
        Returns: (reply_text, requires_human_escalation)
        """
        text = msg.message_text.lower()
        requires_escalation = False
        client_name = msg.client_name or "there"
        booking_url = self.profile.personal_info.calendar_booking_url or "my calendar"
        hourly_rate = self.profile.preferences.rates.get("preferred_hourly_usd", 50)
        
        # Check if client asks about pricing/rates
        if any(w in text for w in ["rate", "price", "cost", "how much", "budget", "quote"]):
            reply = (
                f"Hi {client_name},\n\n"
                f"Thanks for reaching out! Depending on project scope, my standard rate is ${hourly_rate}/hr, "
                f"or we can structure this as a fixed-price milestone agreement if you have a defined specification.\n\n"
                f"I'd be glad to jump on a quick 10-15 minute call to review the details and provide an exact estimate: {booking_url}.\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )

        # Check if client asks for portfolio / samples
        elif any(w in text for w in ["portfolio", "sample", "past work", "examples", "github", "live site"]):
            portfolio = self.profile.personal_info.portfolio_url or "https://github.com"
            reply = (
                f"Hi {client_name},\n\n"
                f"Absolutely! You can explore my live projects, code repositories, and case studies here: {portfolio}\n\n"
                f"Does your project require similar features? Let's connect directly: {booking_url}\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )

        # Check if client asks for an interview / call / availability
        elif any(w in text for w in ["call", "meet", "interview", "zoom", "google meet", "chat", "available", "schedule"]):
            reply = (
                f"Hi {client_name},\n\n"
                f"I would be delighted to speak with you! My schedule is open this week. "
                f"Please feel free to choose any time slot that works best for you here: {booking_url}\n\n"
                f"Looking forward to learning more about your project.\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )

        # If it's a contract negotiation or complex terms, flag for human review
        elif any(w in text for w in ["nda", "contract", "payment terms", "down payment", "agreement", "dispute"]):
            requires_escalation = True
            reply = (
                f"Hi {client_name},\n\n"
                f"Thank you for sharing this! I have received your message and will review the specifics right away. "
                f"I'll get back to you shortly today with next steps.\n\n"
                f"Best,\n{self.profile.personal_info.full_name}"
            )

        # General acknowledgment / holding response
        else:
            reply = (
                f"Hi {client_name},\n\n"
                f"Thank you for reaching out! I've received your message and I'm very interested in assisting with this. "
                f"Let me know if you would like to jump on a brief discovery call to discuss: {booking_url}\n\n"
                f"Best regards,\n{self.profile.personal_info.full_name}"
            )

        return reply, requires_escalation
