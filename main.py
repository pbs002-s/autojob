import argparse
import sys
import json
import os
from pathlib import Path

# Load .env file automatically
def _load_env():
    env_file = Path(".env")
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip('"').strip("'")
                        if k and k not in os.environ:
                            os.environ[k] = v

_load_env()

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from src.agents.profile_agent import ProfileAgent
from src.agents.proposal_agent import ProposalAgent
from src.agents.responder_agent import ResponderAgent
from src.scrapers.remoteok_scraper import RemoteOKScraper
from src.db import Database
from src.models import InboundMessage

def display_banner():
    print(r"""
===================================================================
     _         _          _       _          _    ___ 
    / \  _   _| |_ ___   | | ___ | |__      / \  |_ _|
   / _ \| | | | __/ _ \  | |/ _ \| '_ \    / _ \  | | 
  / ___ \ |_| | || (_) | |_| (_) | |_) |  / ___ \ | | 
 /_/   \_\__,_|\__\___/ \___/\___/|_.__/  /_/   \_\___|
 Autonomous Remote Jobs & Client Acquisition Framework
===================================================================
""")

def run_profile_mode():
    print("\n--- [1] Synthesizing Multi-Platform Profiles ---")
    agent = ProfileAgent()
    
    print("\n🔹 Generated Upwork Profile:")
    upwork = agent.generate_upwork_profile()
    print(f"Title: {upwork['title']}")
    print(f"Hourly Rate: ${upwork['hourly_rate_usd']}/hr")
    print(f"Skills: {', '.join(upwork['skills'][:8])}...")
    print(f"Overview Preview:\n{upwork['overview'][:250]}...\n")

    print("\n🔹 Generated LinkedIn Profile:")
    linkedin = agent.generate_linkedin_profile()
    print(f"Headline: {linkedin['headline']}")
    print(f"About Preview:\n{linkedin['about'][:250]}...\n")

    print("\n🔹 Generated Fiverr Gig:")
    fiverr = agent.generate_fiverr_gig()
    print(f"Gig Title: {fiverr['gig_title']}")
    print(f"Tags: {', '.join(fiverr['search_tags'])}")
    print(f"Basic Package: ${fiverr['packages']['Basic']['price']} - {fiverr['packages']['Basic']['name']}")

from src.scrapers.hunter import JobHunter

def run_scout_mode():
    print("\n--- [2] Scouting Live Opportunities Across 5 Remote Feeds ---")
    hunter = JobHunter()

    print("Querying RemoteOK, Remotive, Jobicy, WeWorkRemotely & Hacker News...")
    jobs = hunter.hunt_jobs(target_count=25)
    matched_count = sum(1 for j in jobs if j.match_score >= 70.0)
    print(f"\nSaved to database! {len(jobs)} opportunities evaluated ({matched_count} high matches >=70%).")

def run_proposal_mode(min_score: float = 40.0):
    print("\n--- [3] Generating Tailored Proposal for Top Job ---")
    db = Database()
    proposal_agent = ProposalAgent()

    unapplied = db.get_unapplied_jobs(min_score=min_score)
    if not unapplied:
        unapplied = db.get_unapplied_jobs(min_score=0.0)
    if not unapplied:
        print("No unapplied jobs found in the database. Run `python main.py --mode scout` first.")
        return

    top_job_data = unapplied[0]
    from src.models import JobListing
    top_job = JobListing(**{k: v for k, v in top_job_data.items() if k != 'tags'}, tags=json.loads(top_job_data['tags']))

    print(f"\nTarget Job: {top_job.title} at {top_job.company} (Score: {top_job.match_score}%)")
    print(f"Platform: {top_job.platform} | Location: {top_job.location}")
    print(f"URL: {top_job.url}")
    print("\n--- Generated Custom Proposal (Gemini 3.6 Flash) ---")
    proposal_text = proposal_agent.generate_proposal(top_job, tone="standard")
    print(proposal_text)
    print("-----------------------------------------------------")
    
    try:
        browser_choice = input("\nLaunch browser to pre-fill application form? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        browser_choice = 'n'
    if browser_choice == 'y':
        import asyncio
        from src.browser.runner import JobApplicationAssistant
        assistant = JobApplicationAssistant()
        asyncio.run(assistant.auto_prefill_job(top_job.url, proposal_text))

    try:
        confirm = input("\nMark this job as applied in the database? (y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        confirm = 'n'
    if confirm == 'y':
        db.record_application(top_job_data['id'], proposal_text)
        print("✅ Application recorded!")

def run_responder_mode():
    print("\n--- [4] Client Retention & Auto-Responder Simulation ---")
    responder = ResponderAgent()
    
    test_messages = [
        ("Sarah (Acme Corp)", "Hi! We saw your application for the Full-Stack role. What is your hourly rate and availability this week?"),
        ("Mark (Fintech Startup)", "Can you share any live samples or past projects where you used Next.js and web scrapers?"),
        ("David", "We'd like to schedule a 15-minute intro chat tomorrow. Are you free?"),
        ("Elena", "Please sign this mutual NDA before we share the specification.")
    ]

    for sender, msg_text in test_messages:
        msg = InboundMessage(platform="Upwork/Email", client_name=sender, message_text=msg_text)
        print(f"\n📥 Inbound Client Message from {sender}:")
        print(f"\"{msg_text}\"")
        
        reply, requires_escalation = responder.evaluate_and_respond(msg)
        status_tag = "⚠️ [REQUIRES HUMAN ESCALATION]" if requires_escalation else "🤖 [AUTO-REPLIED & HELD CLIENT]"
        print(f"\n{status_tag}")
        print("Generated Reply:\n" + reply)
        print("-" * 60)

def run_ui_mode():
    from src.server import start_server
    start_server()

def main():
    display_banner()
    parser = argparse.ArgumentParser(description="AutoJob AI CLI")
    parser.add_argument("--mode", choices=["profile", "scout", "proposal", "responder", "ui"], 
                        help="Operating mode")
    args = parser.parse_args()

    if args.mode == "profile":
        run_profile_mode()
    elif args.mode == "scout":
        run_scout_mode()
    elif args.mode == "proposal":
        run_proposal_mode()
    elif args.mode == "responder":
        run_responder_mode()
    elif args.mode == "ui":
        run_ui_mode()
    else:
        print("Choose an action:")
        print("1. Synthesize Profiles for Upwork / LinkedIn / Fiverr")
        print("2. Scout Live Remote Jobs & Score Matches")
        print("3. Generate Tailored Proposal for Top Match")
        print("4. Test Client Retention Auto-Responder")
        print("5. Launch Minimal Telemetry UI Dashboard")
        print("q. Exit")
        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            run_profile_mode()
        elif choice == "2":
            run_scout_mode()
        elif choice == "3":
            run_proposal_mode()
        elif choice == "4":
            run_responder_mode()
        elif choice == "5":
            run_ui_mode()
        else:
            print("Exiting.")

if __name__ == "__main__":
    main()
