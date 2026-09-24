# AutoJob AI - Autonomous Remote Job & Client Acquisition Agent

**AutoJob AI** is an intelligent, autonomous multi-platform agent framework designed to automate the discovery of remote jobs, freelance gigs, and direct clients, handle profile setups, submit custom proposals, and engage in real-time lead retention through automated messaging and email handling.

---

## 🚀 Key Capabilities

1. **Multi-Platform Profile Builder**:
   - Synthesizes user experience, portfolio, and skills into platform-optimized profiles (LinkedIn, Upwork, Fiverr, Wellfound, Freelancer, RemoteOK, etc.).
   - Generates tailored bios, taglines, skill tags, and service packages.

2. **Automated Job & Client Discovery**:
   - Continuous scanning of job boards, direct client postings, and freelance platforms.
   - AI semantic scoring (0-100%) against your master portfolio and minimum rate criteria.

3. **Smart Proposal & Application Submitter**:
   - Tailors custom cover letters and answers application screening questions.
   - Fills application forms via browser automation.

4. **Client Retention & Auto-Responder ("Lead Holder")**:
   - Monitors incoming messages on platforms and email inboxes.
   - Instantly responds with context-aware, professional messages to acknowledge the client, qualify the scope, answer basic questions, and provide a scheduling link (e.g., Calendly/Cal.com) to lock in the client before competitors reply.

5. **Stealth Browser Engine & Human-in-the-Loop (HITL)**:
   - Uses persistent browser sessions (preserving logins and cookies).
   - Detects CAPTCHAs, 2FA, and identity verification gates, pausing gracefully for quick human approval to avoid account suspensions.

---

## 📂 Project Structure

```
autojob/
├── config/
│   ├── config.example.json      # Main app configuration (APIs, intervals, limits)
│   └── profile.example.json     # Master profile (skills, rates, portfolio, tone)
├── docs/
│   ├── ARCHITECTURE.md          # Multi-agent system design & workflows
│   ├── PLATFORM_GUIDE.md        # Supported platforms & automation feasibility
│   └── SAFETY_AND_COMPLIANCE.md # Bot detection avoidance & TOS guidelines
├── src/
│   ├── agents/                  # Autonomous agent logic (scorer, proposal, responder)
│   ├── browser/                 # Browser automation drivers & stealth runners
│   ├── scrapers/                # Job board & marketplace monitors
│   └── comms/                   # Email & messaging listeners
├── data/                        # Local database for leads, applications, and chat logs
├── requirements.txt             # Python dependencies
└── main.py                      # CLI orchestrator & agent manager
```

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.10+ installed
- Chromium/Chrome browser (or Antigravity browser automation)
- API key for an LLM (Gemini, OpenAI, or local model)

### 2. Setup
```bash
# Clone or navigate to the directory
cd c:/Users/Pritam/Downloads/autojob

# Create a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Your Profile
1. Copy `config/profile.example.json` to `config/profile.json`.
2. Fill in your experience, skills, case studies, hourly rate, and calendar link.
3. Copy `config/config.example.json` to `config/config.json` and add your API keys.

### 4. Run the Agent
```bash
# Run in interactive mode to test profile creation or job search
python main.py --mode scout

# Run client auto-responder listener
python main.py --mode responder
```

---

## ⚠️ Important Operating Principles

- **Never bypass 2FA/KYC automatically**: Platforms require government ID verification (e.g., Upwork ID badge) and SMS 2FA. The agent runs in persistent/headful mode to allow you to complete these manual verification steps once.
- **Rate Limiting**: To prevent bans, the agent enforces randomized delays and daily application caps.
- **Client Holding Strategy**: When a client messages, speed is everything. AutoJob responds within 60-120 seconds to establish rapport and drive them to your booking calendar.
