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

### 5. Web console (landing page + dashboard)

Add to `.env` before the first start (the server refuses to start without an admin):

```bash
AUTOJOB_ADMIN_EMAIL=you@example.com
AUTOJOB_ADMIN_PASSWORD=at-least-10-chars
AUTOJOB_DEMO=1   # optional: enables "Try the demo" with a sandboxed, resettable dataset
```

```bash
python main.py --mode ui        # http://127.0.0.1:8000
```

- `/` landing page, `/login` sign in (and demo cards), `/app/*` dashboard.
- Roles: **admin** (everything, incl. dossier edits, console, users), **operator** (run agent, draft, pre-fill, record applications), **viewer** (read-only). Enforced server-side in `src/auth/rbac.py`.
- Demo sessions use `data/demo.db` + `data/demo_profile.json`, never call Gemini, never launch a browser, and reset every 30 minutes.
- Light and dark mode follow your OS; the sun/moon button in the top bar overrides it (remembered per browser).
- Tests: `python -m pytest tests -q`

#### Sending applications and replies by email (optional)

Add SMTP settings to `.env` and restart. For Gmail, turn on 2-Step Verification and create an
[App Password](https://myaccount.google.com/apppasswords); your normal password will not work.

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587               # 465 for implicit SSL
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM=you@gmail.com     # optional, defaults to SMTP_USER
```

- **Opportunities → pick a role → Draft → Apply by email** sends the (editable) proposal to the recruiter and records the application.
- **Inbox → Test the auto-responder**: fill in *Client email* to email routine auto-replies. Escalations (NDAs, contracts, payments) are never emailed automatically.
- Demo sessions simulate sends; nothing leaves the machine.

---

## ⚠️ Important Operating Principles

- **Never bypass 2FA/KYC automatically**: Platforms require government ID verification (e.g., Upwork ID badge) and SMS 2FA. The agent runs in persistent/headful mode to allow you to complete these manual verification steps once.
- **Rate Limiting**: To prevent bans, the agent enforces randomized delays and daily application caps.
- **Client Holding Strategy**: When a client messages, speed is everything. AutoJob responds within 60-120 seconds to establish rapport and drive them to your booking calendar.
