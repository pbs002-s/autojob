# AutoJob AI - Platform Automation Matrix & Implementation Guide

This guide breaks down each target platform, outlining what can be 100% automated, what requires Human-in-the-Loop (HITL), and the recommended strategy to avoid account penalties.

---

## 1. Platform Matrix Overview

| Platform | Account Creation | Profile Auto-Fill | Job Scouting | Auto-Apply | Message Auto-Responder | Anti-Bot Strictness |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **LinkedIn** | Assisted (SMS/Email) | High | High | High (Easy Apply) | High | High (Cloudflare / Account Limits) |
| **Upwork** | Assisted (ID KYC) | High | Very High (RSS/API/Web) | Medium (Connects cost) | Very High (Fast response = badge) | Very High (Requires manual KYC badge) |
| **Fiverr** | Assisted (Phone/W-9) | High (Gigs) | N/A (Inbound Leads) | N/A | Very High (Maintains 1hr metric) | High |
| **Wellfound (AngelList)**| Assisted (Email) | High | Very High | High | Medium | Medium |
| **RemoteOK / WWR** | None (Direct apply)| N/A | High | High (Direct Email/URL)| High (Email) | Low |
| **Freelancer.com** | Assisted (SMS/KYC) | High | High | High | High | Medium |

---

## 2. Platform Breakdown & Tactics

### 1. Upwork
- **Best Use**: High-ticket freelance contracts, remote hourly projects.
- **Account Creation & KYC**:
  - Upwork requires government photo ID verification, selfie verification, and phone 2FA.
  - *Strategy*: Set up the base account with your verified credentials once in the persistent browser profile. AutoJob AI then takes over profile completion, portfolio imports, and project catalog entries.
- **Proposal Automation**:
  - Connects are limited. The Proposal Scorer must only apply to jobs with a match score of **80%+**.
  - Must answer the 2-3 custom screening questions dynamically using your past case studies.
- **Client Auto-Responder ("Lead Holder")**:
  - Upwork heavily rewards freelancers who respond within 5-15 minutes (Responsive Freelancer badge).
  - When an invite or inquiry arrives, the agent sends an instant, polite acknowledgment, confirms project availability, and offers a discovery call.

---

### 2. LinkedIn
- **Best Use**: Direct client outreach, recruiter inquiries, full-time/part-time remote roles.
- **Profile Optimization**:
  - Agent populates Headline, About section, Experience bullet points, and Skill endorsements.
- **Application Automation**:
  - Targets **Easy Apply** roles matching filters: `Remote`, `Past 24 Hours`, `Under 10 Applicants`.
  - Automatically uploads appropriate resume PDF and completes standard questions (years of experience, work authorization).
- **InMail / Message Responder**:
  - Polls LinkedIn messaging periodically.
  - Automatically identifies recruiters or client inquiries and responds with contact info, availability, and scheduling link.

---

### 3. Fiverr
- **Best Use**: Productized services (e.g., "I will build a full-stack Next.js app in 3 days").
- **Profile & Gig Creation**:
  - Agent synthesizes your skills into 3-5 high-converting gig packages with SEO-friendly titles, pricing tiers, FAQ sections, and delivery timelines.
- **Auto-Responder**:
  - Fiverr measures "Response Time" down to the hour; a 1-hour response rate is mandatory for Level 1/2/Top Rated status.
  - AutoJob monitors Fiverr inbox notifications and answers within 2 minutes with custom client engagement prompts.

---

### 4. Direct Remote Boards (RemoteOK, WeWorkRemotely, Jobspresso)
- **Best Use**: High-paying US/EU remote jobs without middleman marketplace fees.
- **Automation Flow**:
  - Agent scrapes RSS/HTML feeds every 30 minutes.
  - If application is via email: Sends a tailored cold email from your configured email account.
  - If application is via ATS (Greenhouse, Lever, Workable): Uses Playwright to navigate the form and pre-fill fields.

---

## 3. Email Integration (Gmail / IMAP / SMTP)

Many clients email directly after seeing your applications or portfolio.

AutoJob AI includes a background email daemon:
1. **Inbox Polling**: Checks for incoming emails from hiring managers, clients, or platform notification bots.
2. **Intent Classification**: Evaluates if the email is an invitation to interview, a request for more information, or a rejection.
3. **Response Drafting**: If it is an inquiry or interview invite, it sends an immediate confirmation ("Holding response"):
   > *"Hi [Name], thank you for reaching out regarding the [Role/Project]! I have reviewed the requirements and would love to discuss how I can help. You can view my relevant project samples here: [Portfolio Link]. Please feel free to pick a time that works best for a quick 15-minute sync: [Calendly Link]. Looking forward to speaking!"*
4. **Desktop/Webhook Alert**: Sends a notification to your screen/phone so you are aware of the scheduled meeting.
