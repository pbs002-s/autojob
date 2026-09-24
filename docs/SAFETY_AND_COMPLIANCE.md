# AutoJob AI - Safety, Compliance & Anti-Ban Guide

To run continuous job hunting and client retention without getting banned, flagged, or shadowbanned on major platforms, the following safety architecture and rules must be observed.

---

## 1. Anti-Bot Detection Strategies

Modern platforms (LinkedIn, Upwork, Fiverr) use sophisticated bot-detection services (Cloudflare, PerimeterX, Datadome, Kasada). The following techniques are built into AutoJob AI's browser runner:

### A. Persistent Headful Browser Profile
- **Never use blank headless browsers** (e.g., standard Puppeteer/Playwright `headless: true` without stealth plugins).
- AutoJob AI uses `chromium.launch_persistent_context()` pointing to a dedicated user data folder (e.g., `data/browser_profile/`).
- This preserves:
  - Session cookies and Auth tokens
  - Browser cache and IndexedDB state
  - Real browser hardware signatures (WebGL, Canvas, AudioContext)

### B. Human-Mimicking Behavior
- **Typing Cadence**: Rather than setting input field values directly (`input.value = "text"`), keystrokes are typed sequentially with randomized intervals (50ms - 180ms per character).
- **Mouse Trajectory**: Smooth, curved mouse movements with jitter instead of instant teleportation coordinates.
- **Scroll Simulation**: Gradual viewport scrolling with pause-and-read behavior before clicking buttons.

### C. Randomized Intervals
- Operations are spaced using Gaussian/Normal distribution delays:
  - Page navigation: 4 to 8 seconds delay.
  - Form field transitions: 1 to 3 seconds delay.
  - Interval between job applications: 5 to 20 minutes (never burst-apply).

---

## 2. Daily Application Quotas & Limits

Over-applying is the #1 trigger for account restrictions. AutoJob enforces strict daily ceilings:

| Platform | Recommended Daily Limit | Safe Interval Between Actions |
| :--- | :--- | :--- |
| **LinkedIn Easy Apply** | 15 - 20 applications/day | 8 - 15 minutes |
| **Upwork Proposals** | 5 - 10 proposals/day | 20 - 45 minutes |
| **Direct Email Outreach** | 20 - 30 emails/day | 5 - 10 minutes |
| **Fiverr Inbound Replies** | Unlimited (Inbound) | 1 - 3 minutes after trigger |

---

## 3. Human-in-the-Loop (HITL) Triggers

The system automatically halts and alerts you when:
1. **CAPTCHA Encountered**: Audio chime triggers, runner waits up to 180 seconds for you to solve the CAPTCHA in the open browser window.
2. **2FA / OTP Required**: Runner pauses and requests SMS / Authenticator code.
3. **Identity Verification / Selfie Check**: System suspends browser execution until you complete the verification.
4. **Contract / Payment Offer**: Client offers a contract or asks to make an off-platform payment; bot will never accept agreements without your explicit authorization.

---

## 4. Credential & Privacy Security

- **Local Storage Only**: All credentials, session cookies, and conversation histories are stored strictly locally in your workspace (`data/`).
- **No Third-Party Analytics**: No telemetry or scraped data is shared outside your chosen LLM API provider.
- **Environment Isolation**: Sensitive keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, email passwords/app passwords) must stay in `.env` (which is excluded from Git via `.gitignore`).
