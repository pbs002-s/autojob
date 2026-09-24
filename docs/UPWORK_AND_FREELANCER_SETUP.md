# Upwork & Freelancer High-Ticket Automation Guide

This guide details the exact step-by-step strategy for running AutoJob AI on **Upwork** and **Freelancer.com** without risking account bans or wasting valuable Connects/bids.

---

## 1. Upwork Setup & Execution

### Step 1: The Initial Authentication & KYC (Manual Once)
1. Upwork requires real-name photo ID verification (KYC), a selfie check, and SMS two-factor authentication (2FA).
2. Launch the AutoJob persistent browser in headful mode:
   ```bash
   python -c "import asyncio; from src.browser.runner import BrowserRunner; asyncio.run(BrowserRunner().start()); input('Press Enter once logged in...')"
   ```
3. In the opened browser window, sign into your Upwork account, complete your phone 2FA, and pass the ID verification badge.
4. Close the browser. All cookies, device signatures, and authentication tokens are now saved in `data/browser_profile/`.

### Step 2: Auto-Populating Your Upwork Profile
Run the profile synthesizer:
```bash
python main.py --mode profile
```
The agent outputs your customized Upwork profile:
- **Title**: `Full-Stack Engineer, AI Automation Architect & UI/UX Designer`
- **Rate**: `$75.00/hr`
- **Overview**: High-converting pitch outlining Full-Stack (Next.js/React), UI/UX design, and AI automation.
- **Skills**: Top 15 in-demand tags.

Copy or paste into your Upwork profile editor.

### Step 3: High-Match Proposal Strategy
Upwork proposals cost Connects. AutoJob AI enforces an **80%+ Match Rule**:
- Scans job requirements against your tech stack (Next.js, Python, Figma, Playwright).
- Only generates proposals for jobs that meet your minimum criteria ($50+/hr or $1,000+ fixed budget, high payment verification).
- Dynamically references past case studies in the cover letter.

### Step 4: The 15-Minute Client-Holding Responder
When an Upwork client sends you a direct message or invitation:
- Upwork awards a **Responsive Freelancer Badge** if you reply within 1 hour.
- AutoJob responds within 60–120 seconds acknowledging the scope, confirming availability, and sending your calendar link (`https://cal.com/pritam/15min`).
- If the client requests an NDA or asks complex contractual questions, AutoJob alerts you immediately for human escalation.

---

## 2. Freelancer.com Setup & Execution

### Strategic Difference:
Freelancer.com moves very fast; clients often award projects to the first 3–5 qualified bidders with relevant portfolios.

1. **Bid Timing**: AutoJob monitors new project listings in the Web Development and Automation categories.
2. **Instant Customized Bid**: Submits a structured bid within 2 minutes of the project being posted.
3. **Chat Retention**: Clients often open a chat to ask questions. AutoJob's `ResponderAgent` engages immediately with your portfolio samples (`https://pritam.dev`) and discovery call scheduling link.
