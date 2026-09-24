/* ===================================================================
   AutoJob AI Telemetry & Acquisition Engine
   Rules: Pure vanilla JS, zero emojis, editorial minimalism
   =================================================================== */

let allJobs = [];
let allConversations = [];
let currentFilter = 'all';
let currentConvFilter = 'all';
let selectedJobId = null;
let profileData = null;
let searchQuery = '';
let selectedPlatform = 'all';

// Pending view to navigate to after authentication
let pendingAuthTargetView = null;

// Reels State
let currentReelIndex = 0;
let reelsTimer = null;
let reelsProgressInterval = null;
let isReelsPlaying = true;
let reelProgressPercent = 0;

const projectReels = [
  {
    title: "Multi-Source Real-Time Opportunity Scout",
    pillar: "PILLAR 01 // DISCOVERY",
    badge: "5 LIVE FEEDS",
    desc: "Autonomous ingestion engine continuously polling RemoteOK, Remotive, Jobicy, WeWorkRemotely RSS, and monthly Hacker News YC 'Who is Hiring' threads with normalized slug deduplication.",
    metrics: ["FEEDS: 5 ACTIVE", "INGESTION: 180+ ROLES", "DEDUP: SLUG HASH"],
    telemetry: [
      "[POLL] GET https://weworkremotely.com/categories/remote-programming-jobs.rss",
      "[PARSE] Ingested 25 items from WeWorkRemotely RSS",
      "[POLL] GET https://hn.algolia.com/api/v1/search (Story: Ask HN: Who is hiring?)",
      "[PARSE] Ingested top-level founder comments (Obi9, Tether, Langfuse)",
      "[DEDUP] Normalized slug hash match check: 0 collisions detected",
      "[STATUS] Stored 15 high-match candidates in local SQLite database"
    ]
  },
  {
    title: "Gemini 3.6 Flash Technical Proposal Engine",
    pillar: "PILLAR 02 // SYNTHESIS",
    badge: "GEMINI 3.6 FLASH",
    desc: "Analyzes required stack and cross-references active production case studies (URA-Shree, EduSync, BhashaBot) to draft high-converting proposals across Standard, Technical, or Concise tones.",
    metrics: ["MODEL: GEMINI-3.6-FLASH", "LATENCY: ~1.2s", "TONES: 3 PRESETS"],
    telemetry: [
      "[SEMANTIC MATCH] Job requires: React 19, FastAPI, WebSockets, Python Agents",
      "[CASE STUDY MATCH] Selected: URA-Shree (Autonomous AST Coding Agent)",
      "[PROMPT] Injecting candidate dossier, portfolio, and Calendly link",
      "[INFERENCE] Querying generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash",
      "[RESPONSE] HTTP 200 OK - 163 tokens synthesized",
      "[OUTPUT] Customized proposal citing AST parsing, PyTorch, and 3 deliverables"
    ]
  },
  {
    title: "Sub-60s Lead Retention Auto-Responder",
    pillar: "PILLAR 03 // RETENTION",
    badge: "HOLDING PROTOCOL",
    desc: "Listens for inbound messages across email and platform inboxes, evaluates scope, and generates an immediate holding reply with your Calendly booking link. Automatically flags NDAs for human review.",
    metrics: ["RESPONSE: < 60s", "CALENDLY: AUTOMATED", "ESCALATION: REGEX"],
    telemetry: [
      "[INBOUND] Platform: Email | Sender: Sarah (Fintech Labs)",
      "[MESSAGE] 'What is your hourly rate and capacity this week?'",
      "[EVALUATE] Query: Rate Inquiry & Capacity (Safe, Non-Legal)",
      "[RESPONDER] Injected: Standard rate ($65/hr) + Calendly discovery link",
      "[DISPATCH] Sent response in 48 seconds // Lead interest secured",
      "[STATUS] Logged conversation thread to local SQLite ledger"
    ]
  },
  {
    title: "Stealth Playwright Chromium Form Assistant",
    pillar: "PILLAR 04 // AUTOMATION",
    badge: "CHROMIUM STEALTH",
    desc: "Launches persistent browser sessions preserving login cookies. Detects DOM fields across Greenhouse, Lever, and standard portals, auto-injects candidate credentials, attaches resume, and enables HITL review.",
    metrics: ["ENGINE: PLAYWRIGHT", "SESSION: PERSISTENT", "HITL: 100% VERIFIED"],
    telemetry: [
      "[BROWSER] Launching persistent Chromium context at data/browser_profile",
      "[NAVIGATE] Target URL loaded (domcontentloaded in 820ms)",
      "[INSPECT] Form elements detected: 7 input fields, 1 textarea, 1 file input",
      "[DOM FILL] Full Name: Pritam Biswas | Email: pritom580cse@gmail.com",
      "[DOM FILL] Portfolio, LinkedIn, and GitHub URLs injected into form",
      "[ATTACH] Located resume file: data/resume.pdf -> File input bound",
      "[HOLD] Leaving browser active for user final inspection and submission"
    ]
  },
  {
    title: "Candidate Profile & Telemetry Ledger",
    pillar: "PILLAR 05 // CONTROL",
    badge: "AUDIT LOG",
    desc: "Single-source configuration of candidate skills, rates ($65/hr), minimum project budgets, active projects, and application ledger with complete timestamped audit history.",
    metrics: ["PROFILE: MASTER JSON", "DB: SQLITE3", "LEDGER: PERSISTENT"],
    telemetry: [
      "[PROFILE] Loaded config/profile.json (Pritam Biswas, AI Systems Architect)",
      "[PREFERENCES] Hourly: $65.00/hr | Min Budget: $800 | 40 hrs/wk",
      "[SKILLS] 28 verified technologies indexed across Frontend, Backend, AI",
      "[APPLICATIONS] Total submissions tracked: 10 | Conversations: 3 active",
      "[SECURITY] PIN Gate active // Local system access restricted"
    ]
  }
];

// Initialize upon DOM load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initAuth();
  loadAllData();
  initReels();
  initScrollReveal();
  checkAgentStatus();
  
  // Handle direct hash routing (e.g. #landing, #reels, #live-process)
  const hash = (window.location.hash || '').replace('#', '').toLowerCase();
  if (hash === 'reels') {
    switchMainView('landing');
    setTimeout(() => scrollToReels(), 200);
  } else if (hash === 'live-process' || hash === 'live_process') {
    switchMainView('live_process');
  } else if (hash === 'jobs' || hash === 'messages' || hash === 'contact' || hash === 'console') {
    switchMainView(hash);
  } else {
    switchMainView('landing');
  }
});

window.addEventListener('hashchange', () => {
  const hash = (window.location.hash || '').replace('#', '').toLowerCase();
  if (hash === 'reels') {
    switchMainView('landing');
    setTimeout(() => scrollToReels(), 200);
  } else if (hash === 'live-process' || hash === 'live_process') {
    switchMainView('live_process');
  } else if (hash === 'landing') {
    switchMainView('landing');
  } else if (hash === 'jobs' || hash === 'messages' || hash === 'contact' || hash === 'console') {
    switchMainView(hash);
  }
});

// ===================================================================
// AUTHENTICATION & PIN GATE
// ===================================================================

function isUserAuthenticated() {
  return sessionStorage.getItem('autojob_auth') === 'verified';
}

function initAuth() {
  updateAuthUI();
}

function updateAuthUI() {
  const btn = document.getElementById('authStatusBtn');
  if (!btn) return;

  if (isUserAuthenticated()) {
    btn.textContent = 'AUTH: UNLOCKED';
    btn.className = 'auth-badge-btn unlocked';
  } else {
    btn.textContent = 'AUTH: LOCKED';
    btn.className = 'auth-badge-btn';
  }
}

function openAuthModal(targetView = null) {
  pendingAuthTargetView = targetView;
  const overlay = document.getElementById('authModalOverlay');
  const input = document.getElementById('authPinInput');
  const msg = document.getElementById('authStatusMsg');
  
  if (overlay) overlay.classList.add('active');
  if (input) {
    input.value = '';
    setTimeout(() => input.focus(), 150);
  }
  if (msg) {
    msg.innerHTML = 'ENTER 4-DIGIT AUTHORIZATION PIN';
    msg.style.color = 'var(--ink-secondary)';
  }
}

function closeAuthModal() {
  const overlay = document.getElementById('authModalOverlay');
  if (overlay) overlay.classList.remove('active');
  pendingAuthTargetView = null;
}

function handleAuthOverlayClick(e) {
  if (e.target.id === 'authModalOverlay') {
    closeAuthModal();
  }
}

function toggleAuthModal() {
  if (isUserAuthenticated()) {
    const confirmLock = confirm('Session currently authenticated. Lock dashboard session?');
    if (confirmLock) {
      sessionStorage.removeItem('autojob_auth');
      updateAuthUI();
      switchMainView('landing');
      alert('Dashboard session locked. PIN required for restricted access.');
    }
  } else {
    openAuthModal();
  }
}

async function submitAuthPin(event) {
  event.preventDefault();
  const input = document.getElementById('authPinInput');
  const msg = document.getElementById('authStatusMsg');
  const btn = document.getElementById('btnSubmitPin');
  const pin = (input.value || '').trim();

  btn.disabled = true;
  btn.textContent = '[ VERIFYING... ]';

  try {
    const res = await fetch('/api/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pin: pin })
    });

    if (res.ok) {
      sessionStorage.setItem('autojob_auth', 'verified');
      updateAuthUI();
      msg.innerHTML = '<strong style="color: var(--status-green-text);">PIN CONFIRMED // ACCESS GRANTED</strong>';
      
      setTimeout(() => {
        closeAuthModal();
        btn.disabled = false;
        btn.textContent = '[ UNLOCK SYSTEM ]';
        if (pendingAuthTargetView) {
          switchMainView(pendingAuthTargetView, true);
        } else {
          switchMainView('jobs', true);
        }
      }, 500);
    } else {
      throw new Error('Invalid PIN');
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = '[ UNLOCK SYSTEM ]';
    msg.innerHTML = '<strong style="color: var(--status-red-text);">INVALID PIN // ACCESS DENIED</strong>';
    input.value = '';
    input.focus();
  }
}

function requestDashboardAccess(viewName = 'jobs') {
  if (isUserAuthenticated()) {
    switchMainView(viewName, true);
  } else {
    openAuthModal(viewName);
  }
}

// ===================================================================
// VIEW NAVIGATION & GATEKEEPING
// ===================================================================

function switchMainView(viewName, bypassAuthCheck = false) {
  // Gate restricted views behind PIN authentication
  const restrictedViews = ['jobs', 'messages', 'contact', 'console'];
  if (restrictedViews.includes(viewName) && !isUserAuthenticated() && !bypassAuthCheck) {
    openAuthModal(viewName);
    return;
  }

  // Toggle DOM containers
  document.getElementById('mainViewLanding').style.display = viewName === 'landing' ? 'block' : 'none';
  document.getElementById('mainViewLiveProcess').style.display = viewName === 'live_process' ? 'block' : 'none';
  document.getElementById('mainViewJobs').style.display = viewName === 'jobs' ? 'block' : 'none';
  document.getElementById('mainViewMessages').style.display = viewName === 'messages' ? 'block' : 'none';
  document.getElementById('mainViewContact').style.display = viewName === 'contact' ? 'block' : 'none';
  document.getElementById('mainViewConsole').style.display = viewName === 'console' ? 'block' : 'none';

  // Update Nav Buttons
  document.getElementById('viewBtnLanding').className = `view-nav-btn ${viewName === 'landing' ? 'active' : ''}`;
  document.getElementById('viewBtnLiveProcess').className = `view-nav-btn ${viewName === 'live_process' ? 'active' : ''}`;
  document.getElementById('viewBtnJobs').className = `view-nav-btn ${viewName === 'jobs' ? 'active' : ''}`;
  document.getElementById('viewBtnMessages').className = `view-nav-btn ${viewName === 'messages' ? 'active' : ''}`;
  document.getElementById('viewBtnContact').className = `view-nav-btn ${viewName === 'contact' ? 'active' : ''}`;
  document.getElementById('viewBtnConsole').className = `view-nav-btn ${viewName === 'console' ? 'active' : ''}`;

  window.scrollTo({ top: 0, behavior: 'smooth' });

  // Trigger scroll-reveal animations in active view
  setTimeout(triggerScrollRevealCheck, 100);
}

// ===================================================================
// PROJECT OVERVIEW REELS ENGINE
// ===================================================================

function initReels() {
  renderReel(0);
  startReelProgress();
}

function renderReel(index) {
  currentReelIndex = index;
  const reel = projectReels[index];
  const container = document.getElementById('reelContentContainer');
  if (!container) return;

  const telemetryLines = reel.telemetry.map(t => `<div>${escapeHtml(t)}</div>`).join('');
  const metricPills = reel.metrics.map(m => `<span>${escapeHtml(m)}</span>`).join(' • ');

  container.innerHTML = `
    <div class="reel-text-side">
      <span class="reel-pill">${escapeHtml(reel.pillar)}</span>
      <h2 class="reel-title">${escapeHtml(reel.title)}</h2>
      <p class="reel-desc">${escapeHtml(reel.desc)}</p>
      <div class="reel-metrics">${metricPills}</div>
    </div>
    <div class="reel-visual-card">
      <div style="color: var(--status-green-text); margin-bottom: 8px; font-weight: 600;">
        TELEMETRY FEED // [${escapeHtml(reel.badge)}]
      </div>
      ${telemetryLines}
    </div>
  `;

  document.getElementById('reelIndicatorLabel').textContent = 
    `REEL ${index + 1} OF ${projectReels.length} // ${reel.badge}`;

  updateReelProgressSegments(index);
}

function updateReelProgressSegments(activeIndex) {
  for (let i = 0; i < projectReels.length; i++) {
    const seg = document.getElementById(`reelBar${i}`);
    if (!seg) continue;
    if (i < activeIndex) {
      seg.style.width = '100%';
    } else if (i === activeIndex) {
      seg.style.width = `${reelProgressPercent}%`;
    } else {
      seg.style.width = '0%';
    }
  }
}

function startReelProgress() {
  stopReelProgress();
  reelProgressPercent = 0;
  if (!isReelsPlaying) return;

  const durationMs = 5000;
  const intervalMs = 50;
  const step = (intervalMs / durationMs) * 100;

  reelsProgressInterval = setInterval(() => {
    if (!isReelsPlaying) return;
    reelProgressPercent += step;
    
    const activeSeg = document.getElementById(`reelBar${currentReelIndex}`);
    if (activeSeg) activeSeg.style.width = `${reelProgressPercent}%`;

    if (reelProgressPercent >= 100) {
      nextReel();
    }
  }, intervalMs);
}

function stopReelProgress() {
  if (reelsProgressInterval) {
    clearInterval(reelsProgressInterval);
    reelsProgressInterval = null;
  }
}

function nextReel() {
  currentReelIndex = (currentReelIndex + 1) % projectReels.length;
  renderReel(currentReelIndex);
  startReelProgress();
}

function prevReel() {
  currentReelIndex = (currentReelIndex - 1 + projectReels.length) % projectReels.length;
  renderReel(currentReelIndex);
  startReelProgress();
}

function jumpToReel(index) {
  currentReelIndex = index;
  renderReel(index);
  startReelProgress();
}

function toggleReelsPlay() {
  isReelsPlaying = !isReelsPlaying;
  const btn = document.getElementById('btnToggleReelsPlay');
  const badge = document.getElementById('reelsPlayStatus');

  if (isReelsPlaying) {
    if (btn) btn.textContent = '[ PAUSE ]';
    if (badge) badge.textContent = 'PLAYING';
    startReelProgress();
  } else {
    if (btn) btn.textContent = '[ RESUME ]';
    if (badge) badge.textContent = 'PAUSED';
    stopReelProgress();
  }
}

function scrollToReels() {
  const el = document.getElementById('projectReelsSection');
  if (el) el.scrollIntoView({ behavior: 'smooth' });
}

// ===================================================================
// LIVE WORKING PROCESS ENGINE (AGENT TELEMETRY)
// ===================================================================

async function triggerProcessStepManual(stepNumber) {
  updatePipelineNodesUI(stepNumber);
  const badge = document.getElementById('liveProcessBadge');
  const stageTitle = document.getElementById('liveStageTitle');
  const stageTag = document.getElementById('liveStageStatusTag');
  const preview = document.getElementById('liveOutputPreview');

  badge.textContent = `EXECUTING PHASE ${stepNumber}...`;
  stageTag.textContent = 'IN PROGRESS';

  try {
    const res = await fetch('/api/agent/live-process/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: stepNumber })
    });
    
    const state = await res.json();
    stageTitle.textContent = state.stage_name;
    badge.textContent = state.status;
    stageTag.textContent = 'ACTIVE';

    if (state.current_job) {
      document.getElementById('liveTargetJobTitle').textContent = state.current_job.title;
      document.getElementById('liveTargetJobCompany').textContent = `${state.current_job.company} • ${state.current_job.platform}`;
      document.getElementById('liveTargetScore').textContent = `${Number(state.current_job.score).toFixed(1)}%`;
      document.getElementById('liveTargetUrl').textContent = state.current_job.url;
    }

    if (state.proposal_sample) {
      preview.textContent = state.proposal_sample;
    } else {
      preview.textContent = state.logs[state.logs.length - 1] || 'Operation completed successfully.';
    }

    appendLiveProcessLog(state.logs[state.logs.length - 1]);
  } catch (err) {
    badge.textContent = 'ERROR';
    stageTag.textContent = 'FAIL';
  }
}

async function runFullPipelineSimulation() {
  const btn = document.getElementById('btnRunFullSimulation');
  btn.disabled = true;
  btn.textContent = '[ PIPELINE RUNNING (1/5)... ]';

  for (let s = 1; s <= 5; s++) {
    btn.textContent = `[ PIPELINE RUNNING (${s}/5)... ]`;
    await triggerProcessStepManual(s);
    await new Promise(r => setTimeout(r, 1400));
  }

  btn.disabled = false;
  btn.textContent = '[ RUN FULL AUTONOMOUS PIPELINE ]';
  alert('Autonomous execution cycle completed across all 5 phases! Opportunities, proposals, and browser mappings synchronized.');
}

function updatePipelineNodesUI(activeStep) {
  for (let i = 1; i <= 5; i++) {
    const node = document.getElementById(`pNode${i}`);
    if (!node) continue;
    node.className = 'pipeline-node';
    if (i < activeStep) {
      node.classList.add('completed');
    } else if (i === activeStep) {
      node.classList.add('active');
    }
  }
}

function resetLiveProcess() {
  updatePipelineNodesUI(1);
  document.getElementById('liveProcessBadge').textContent = 'STANDBY // READY';
  document.getElementById('liveStageTitle').textContent = 'Phase 1: Multi-Feed Scraping & Ingestion';
  document.getElementById('liveStageStatusTag').textContent = 'READY';
  document.getElementById('liveOutputPreview').textContent = '[Output will stream here as the agent executes each phase...]';
  appendLiveProcessLog('PIPELINE RESET // ALL WORKERS AT STANDBY.');
}

function appendLiveProcessLog(text) {
  if (!text) return;
  const terminal = document.getElementById('liveProcessLogTerminal');
  if (!terminal) return;

  const now = new Date().toTimeString().split(' ')[0];
  const row = document.createElement('div');
  row.className = 'log-line';
  row.innerHTML = `<span class="log-time">[${now}]</span><span class="log-text">${escapeHtml(text)}</span>`;
  terminal.appendChild(row);
  terminal.scrollTop = terminal.scrollHeight;
}

function clearLiveProcessLogs() {
  const terminal = document.getElementById('liveProcessLogTerminal');
  if (terminal) {
    terminal.innerHTML = `<div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-text">LOG TERMINAL CLEARED // MONITOR READY.</span></div>`;
  }
}

// ===================================================================
// MINIMAL SCROLL REVEAL OBSERVER
// ===================================================================

function initScrollReveal() {
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll('.scroll-reveal').forEach(el => observer.observe(el));
  } else {
    document.querySelectorAll('.scroll-reveal').forEach(el => el.classList.add('visible'));
  }
}

function triggerScrollRevealCheck() {
  document.querySelectorAll('.scroll-reveal').forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight - 50) {
      el.classList.add('visible');
    }
  });
}

// ===================================================================
// THEME MANAGEMENT
// ===================================================================

function initTheme() {
  const savedTheme = localStorage.getItem('autojob_theme') || 'light';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeBtnLabel(savedTheme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('autojob_theme', next);
  updateThemeBtnLabel(next);
}

function updateThemeBtnLabel(theme) {
  const btn = document.getElementById('themeToggleBtn');
  if (btn) {
    btn.textContent = `THEME: ${theme.toUpperCase()}`;
  }
}

// ===================================================================
// DATA FETCHING & SYNCHRONIZATION
// ===================================================================

async function loadAllData() {
  setSystemStatus('UPDATING');
  try {
    await Promise.all([
      fetchStats(),
      fetchJobs(),
      fetchApplications(),
      fetchConversations(),
      fetchProfile()
    ]);
    setSystemStatus('DAEMON READY');
  } catch (err) {
    console.error('Data load error:', err);
    setSystemStatus('SYNC ERROR');
  }
}

async function fetchStats() {
  const res = await fetch('/api/stats');
  if (!res.ok) return;
  const data = await res.json();
  
  document.getElementById('metricTotalJobs').textContent = data.total_jobs;
  document.getElementById('metricHighMatches').textContent = data.high_matches;
  document.getElementById('metricTotalApplied').textContent = data.total_applied;
  document.getElementById('metricTotalConversations').textContent = data.total_conversations || 0;
  document.getElementById('inboundMsgBadge').textContent = data.total_conversations || 0;
  
  if (data.profile) {
    document.getElementById('navCandidateName').textContent = data.profile.name;
    document.getElementById('navCandidateRate').textContent = `$${Number(data.profile.hourly_rate).toFixed(2)}/HR`;
  }
}

async function fetchJobs() {
  const res = await fetch('/api/jobs');
  if (!res.ok) return;
  allJobs = await res.json();
  renderJobsList();
}

async function fetchApplications() {
  const res = await fetch('/api/applications');
  if (!res.ok) return;
  const apps = await res.json();
  renderApplicationsTable(apps);
}

async function fetchConversations() {
  const res = await fetch('/api/conversations');
  if (!res.ok) return;
  allConversations = await res.json();
  document.getElementById('inboundMsgBadge').textContent = allConversations.length;
  renderConversationsList();
}

async function fetchProfile() {
  const res = await fetch('/api/profile');
  if (!res.ok) return;
  profileData = await res.json();
  populateContactForm(profileData);
  renderProfileCredentials(profileData);
}

// ===================================================================
// OPPORTUNITIES & PROPOSALS LISTING
// ===================================================================

function handleJobSearch(val) {
  searchQuery = (val || '').toLowerCase().trim();
  renderJobsList();
}

function handlePlatformFilter(platform) {
  selectedPlatform = platform || 'all';
  renderJobsList();
}

function renderJobsList() {
  const container = document.getElementById('jobsListContainer');
  let filtered = allJobs;

  if (currentFilter === 'discovered') {
    filtered = filtered.filter(j => j.status === 'discovered');
  } else if (currentFilter === 'applied') {
    filtered = filtered.filter(j => j.status === 'applied');
  } else if (currentFilter === 'high') {
    filtered = filtered.filter(j => (j.match_score || 0) >= 70.0);
  }

  if (selectedPlatform !== 'all') {
    filtered = filtered.filter(j => j.platform && j.platform.toLowerCase().includes(selectedPlatform.toLowerCase()));
  }

  if (searchQuery) {
    filtered = filtered.filter(j => {
      const matchTitle = (j.title || '').toLowerCase().includes(searchQuery);
      const matchCompany = (j.company || '').toLowerCase().includes(searchQuery);
      const matchTags = (j.tags || []).some(t => t.toLowerCase().includes(searchQuery));
      const matchDesc = (j.description || '').toLowerCase().includes(searchQuery);
      return matchTitle || matchCompany || matchTags || matchDesc;
    });
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="padding: 32px; text-align: center; color: var(--ink-muted); font-family: var(--font-mono); font-size: 12px;">
        No listings match criteria. Adjust search or run Scout.
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(j => {
    const isSelected = j.id === selectedJobId;
    const isApplied = j.status === 'applied';
    const score = Number(j.match_score || 0).toFixed(1);
    const scoreClass = score >= 70 ? 'score-high' : 'score-mid';
    const statusLabel = isApplied ? '[APPLIED]' : '[UNAPPLIED]';
    const statusClass = isApplied ? 'applied' : 'discovered';

    const tagsHtml = (j.tags || []).slice(0, 4).map(t => `<span class="tag-pill">${escapeHtml(t)}</span>`).join('');

    return `
      <div class="job-item ${isSelected ? 'selected' : ''}" onclick="selectJob(${j.id})">
        <div class="job-main">
          <div class="job-title-row">
            <span class="job-title">${escapeHtml(j.title)}</span>
            <span class="status-tag ${statusClass}">${statusLabel}</span>
          </div>
          <div class="job-company">${escapeHtml(j.company)} • ${escapeHtml(j.platform)} • ${escapeHtml(j.location || 'Remote')}</div>
          <div class="tag-pills">${tagsHtml}</div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
          <span class="score-badge ${scoreClass}">${score}%</span>
          <button class="btn btn-secondary btn-sm" onclick="event.stopPropagation(); triggerJobProposal(${j.id})">
            ${isApplied ? '[ VIEW PROPOSAL ]' : '[ DRAFT ]'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function filterJobs(filterKey) {
  currentFilter = filterKey;
  document.querySelectorAll('#mainViewJobs .filter-tabs .tab-btn').forEach(btn => {
    if (btn.getAttribute('data-filter') === filterKey) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  renderJobsList();
}

function selectJob(jobId) {
  selectedJobId = jobId;
  renderJobsList();
  
  const job = allJobs.find(j => j.id === jobId);
  if (!job) return;

  document.getElementById('targetJobTitle').textContent = job.title;
  document.getElementById('targetJobCompany').textContent = `${job.company} • ${job.platform.toUpperCase()} • ${job.location || 'Remote'}`;
  
  const scoreBadge = document.getElementById('targetJobScore');
  scoreBadge.textContent = `${Number(job.match_score || 0).toFixed(1)}%`;
  scoreBadge.className = `score-badge ${job.match_score >= 70 ? 'score-high' : 'score-mid'}`;
  
  document.getElementById('targetJobUrlRow').innerHTML = `
    <a href="${job.url}" target="_blank" style="color: var(--ink-secondary); text-decoration: underline;">
      View Original Listing: ${job.url}
    </a>
  `;

  const textarea = document.getElementById('proposalTextarea');
  if (textarea.value.trim().length > 50) {
    document.getElementById('btnRecordApplication').disabled = false;
    document.getElementById('btnBrowserPrefill').disabled = false;
  }
}

async function triggerJobProposal(jobId, tone = null) {
  selectJob(jobId);
  const textarea = document.getElementById('proposalTextarea');
  const toneSelect = document.getElementById('proposalToneSelect');
  const selectedTone = tone || (toneSelect ? toneSelect.value : 'standard');

  textarea.value = `Synthesizing tailored proposal (${selectedTone.toUpperCase()} tone) via Gemini 3.6 Flash...`;
  document.getElementById('workbenchStatusTag').textContent = 'GENERATING...';

  try {
    const res = await fetch('/api/proposals/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId, tone: selectedTone })
    });
    
    if (!res.ok) throw new Error('Generation failed');
    const data = await res.json();
    
    textarea.value = data.proposal_text;
    document.getElementById('btnRecordApplication').disabled = false;
    document.getElementById('btnBrowserPrefill').disabled = false;
    document.getElementById('workbenchStatusTag').textContent = 'READY';
  } catch (err) {
    textarea.value = "Error generating proposal. Please retry.";
    document.getElementById('workbenchStatusTag').textContent = 'ERROR';
  }
}

function regenerateWithSelectedTone() {
  if (!selectedJobId) {
    alert("Please select a job opportunity first.");
    return;
  }
  const tone = document.getElementById('proposalToneSelect').value;
  triggerJobProposal(selectedJobId, tone);
}

async function triggerBrowserPrefill() {
  if (!selectedJobId) return;
  const textarea = document.getElementById('proposalTextarea');
  const btn = document.getElementById('btnBrowserPrefill');
  const tag = document.getElementById('workbenchStatusTag');

  btn.disabled = true;
  btn.textContent = "[ LAUNCHING BROWSER... ]";
  tag.textContent = "AUTOMATING BROWSER...";

  try {
    const res = await fetch('/api/browser/prefill', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_id: selectedJobId,
        proposal_text: textarea.value
      })
    });

    const data = await res.json();
    btn.disabled = false;
    btn.textContent = "[ PREFILL IN BROWSER ]";

    if (data.status === 'ready_for_review') {
      tag.textContent = `PREFILLED (${data.filled_fields.length} FIELDS) // READY FOR REVIEW`;
      alert(`Browser opened! Successfully pre-filled: ${data.filled_fields.join(', ')}.\nReview the application in the open browser window.`);
    } else if (data.status === 'fallback_opened') {
      tag.textContent = "OPENED IN SYSTEM BROWSER";
      alert("Job URL opened in your default browser. Proposal text has been copied to your clipboard!");
      copyProposalText();
    } else {
      tag.textContent = "BROWSER ACTIVE";
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "[ PREFILL IN BROWSER ]";
    tag.textContent = "PREFILL ERROR";
    alert(`Could not launch browser: ${err.message}`);
  }
}

async function recordCurrentApplication() {
  if (!selectedJobId) return;
  const text = document.getElementById('proposalTextarea').value;
  if (!text.trim()) return;

  const btn = document.getElementById('btnRecordApplication');
  btn.disabled = true;
  btn.textContent = "[ RECORDING... ]";

  try {
    const res = await fetch('/api/proposals/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: selectedJobId, proposal_text: text })
    });

    if (!res.ok) throw new Error('Failed to record');
    btn.textContent = "[ RECORDED ]";
    await loadAllData();
  } catch (err) {
    btn.disabled = false;
    btn.textContent = "[ RETRY RECORDING ]";
  }
}

function copyProposalText() {
  const text = document.getElementById('proposalTextarea').value;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    const tag = document.getElementById('workbenchStatusTag');
    const original = tag.textContent;
    tag.textContent = 'COPIED TO CLIPBOARD';
    setTimeout(() => tag.textContent = original, 2000);
  });
}

function renderApplicationsTable(apps) {
  const tbody = document.getElementById('appliedTableBody');
  if (!tbody) return;
  if (apps.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--ink-muted);">No applications recorded yet</td></tr>`;
    return;
  }

  tbody.innerHTML = apps.map(a => `
    <tr>
      <td><strong>${escapeHtml(a.title)}</strong></td>
      <td>${escapeHtml(a.company)}</td>
      <td><span class="score-badge score-mid" style="font-size: 11px;">${Number(a.match_score).toFixed(1)}%</span></td>
      <td style="color: var(--ink-muted);">${a.applied_at.substring(0, 16)}</td>
    </tr>
  `).join('');
}

// ===================================================================
// INBOUND COMMUNICATIONS (EMAILS & MESSAGES)
// ===================================================================

function renderConversationsList() {
  const container = document.getElementById('conversationsContainer');
  if (!container) return;
  let filtered = allConversations;

  if (currentConvFilter === 'Email') {
    filtered = allConversations.filter(c => c.platform.toLowerCase().includes('email'));
  } else if (currentConvFilter === 'Upwork') {
    filtered = allConversations.filter(c => c.platform.toLowerCase().includes('upwork'));
  } else if (currentConvFilter === 'LinkedIn') {
    filtered = allConversations.filter(c => c.platform.toLowerCase().includes('linkedin'));
  } else if (currentConvFilter === 'escalation') {
    filtered = allConversations.filter(c => c.status === 'escalation');
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="padding: 32px; text-align: center; color: var(--ink-muted); font-family: var(--font-mono); font-size: 12px;">
        No inbound communications match filter [${currentConvFilter.toUpperCase()}].
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(c => {
    const isEscalation = c.status === 'escalation';
    const statusBadgeClass = isEscalation ? 'conv-status-escalation' : 'conv-status-responded';
    const statusText = isEscalation ? 'FLAGGED FOR HUMAN ESCALATION' : 'AUTO-RESPONDED WITH CALENDLY';

    return `
      <div class="conv-card ${isEscalation ? 'escalation' : ''}">
        <div class="conv-header">
          <div class="conv-client-info">
            <span class="conv-platform-badge">${escapeHtml(c.platform)}</span>
            <span class="conv-client-name">${escapeHtml(c.client_name)}</span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="conv-status-tag ${statusBadgeClass}">${statusText}</span>
            <span class="target-meta">${c.updated_at.substring(0, 16)}</span>
          </div>
        </div>
        
        <div class="conv-body">
          <div class="conv-msg-inbound">
            <div class="conv-msg-label">CLIENT INQUIRY:</div>
            <div class="conv-msg-content">${escapeHtml(c.last_message_text)}</div>
          </div>
          
          <div class="conv-msg-reply">
            <div class="conv-msg-label">AUTOJOB SYSTEM RESPONSE:</div>
            <div class="conv-msg-content" style="white-space: pre-wrap;">${escapeHtml(c.last_reply_text)}</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function filterConversations(filterKey) {
  currentConvFilter = filterKey;
  document.querySelectorAll('#mainViewMessages .filter-tabs .tab-btn').forEach(btn => {
    if (btn.getAttribute('data-conv-filter') === filterKey) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
  renderConversationsList();
}

async function sendInboundSimulation() {
  const platform = document.getElementById('newMsgPlatform').value;
  const sender = document.getElementById('newMsgSender').value;
  const content = document.getElementById('newMsgContent').value;

  if (!content.trim()) return;

  try {
    const res = await fetch('/api/conversations/receive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: platform,
        client_name: sender,
        message_text: content
      })
    });

    if (!res.ok) throw new Error('Simulation failed');
    await fetchConversations();
    await fetchStats();
  } catch (err) {
    alert(`Inbound simulation failed: ${err.message}`);
  }
}

// ===================================================================
// CONTACT INFO & DOSSIER CONFIGURATION
// ===================================================================

function populateContactForm(data) {
  if (!data || !data.personal_info) return;
  const p = data.personal_info;
  const rates = data.preferences ? data.preferences.rates : {};

  document.getElementById('cfgFullName').value = p.full_name || '';
  document.getElementById('cfgProfessionalTitle').value = p.professional_title || '';
  document.getElementById('cfgEmail').value = p.email || '';
  document.getElementById('cfgPhone').value = p.phone || '';
  document.getElementById('cfgLocation').value = p.location || '';
  document.getElementById('cfgPortfolioUrl').value = p.portfolio_url || '';
  document.getElementById('cfgGithubUrl').value = p.github_url || '';
  document.getElementById('cfgLinkedinUrl').value = p.linkedin_url || '';
  document.getElementById('cfgCalendarUrl').value = p.calendar_booking_url || '';

  document.getElementById('cfgHourlyRate').value = rates.preferred_hourly_usd || 65;
  document.getElementById('cfgMinBudget').value = rates.minimum_project_budget_usd || 800;
}

function renderProfileCredentials(data) {
  const container = document.getElementById('profileCaseStudiesList');
  if (!container || !data.case_studies) return;

  container.innerHTML = data.case_studies.map(cs => `
    <div style="border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; background: var(--surface-inset);">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <strong style="color: var(--ink); font-size: 13px;">${escapeHtml(cs.title)}</strong>
          <div class="target-meta">${escapeHtml(cs.role)} • Built with ${cs.tech_stack.join(', ')}</div>
        </div>
        ${cs.live_url ? `<a href="${cs.live_url}" target="_blank" class="btn btn-secondary btn-sm" style="font-size: 10px;">[ DEMO ]</a>` : ''}
      </div>
      <p style="font-size: 12px; color: var(--ink-secondary); margin-top: 8px; line-height: 1.5;">${escapeHtml(cs.summary)}</p>
    </div>
  `).join('');
}

async function saveContactInfo(event) {
  event.preventDefault();
  const statusEl = document.getElementById('contactSaveStatus');
  statusEl.textContent = "SAVING...";

  const payload = {
    full_name: document.getElementById('cfgFullName').value,
    professional_title: document.getElementById('cfgProfessionalTitle').value,
    email: document.getElementById('cfgEmail').value,
    phone: document.getElementById('cfgPhone').value,
    location: document.getElementById('cfgLocation').value,
    portfolio_url: document.getElementById('cfgPortfolioUrl').value,
    github_url: document.getElementById('cfgGithubUrl').value,
    linkedin_url: document.getElementById('cfgLinkedinUrl').value,
    calendar_booking_url: document.getElementById('cfgCalendarUrl').value,
    preferred_hourly_usd: parseFloat(document.getElementById('cfgHourlyRate').value),
    minimum_project_budget_usd: parseFloat(document.getElementById('cfgMinBudget').value)
  };

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Save failed');
    statusEl.textContent = "SAVED TO PROFILE.JSON";
    await loadAllData();
    setTimeout(() => statusEl.textContent = "Ready", 3000);
  } catch (err) {
    statusEl.textContent = "ERROR SAVING";
  }
}

// ===================================================================
// ONE-CLICK AGENT RUNNER ACTIONS
// ===================================================================

async function runAgentAction(mode) {
  const badge = document.getElementById('runnerStatusBadge');
  badge.textContent = `EXECUTING [${mode.toUpperCase()}]...`;
  badge.style.background = 'var(--status-neutral-bg)';
  badge.style.color = 'var(--ink)';

  try {
    const res = await fetch('/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode: mode })
    });

    if (!res.ok) throw new Error('Action execution failed');
    const data = await res.json();
    
    badge.textContent = `SUCCESS: [${mode.toUpperCase()}]`;
    badge.style.background = 'var(--status-green-bg)';
    badge.style.color = 'var(--status-green-text)';

    if (data.logs) {
      data.logs.forEach(log => appendTerminalLog(log));
    }

    if (data.proposal_text) {
      const textarea = document.getElementById('proposalTextarea');
      textarea.value = data.proposal_text;
      document.getElementById('btnRecordApplication').disabled = false;
      document.getElementById('btnBrowserPrefill').disabled = false;
    }

    await loadAllData();
    setTimeout(() => {
      badge.textContent = 'IDLE';
      badge.style.background = 'var(--surface-inset)';
      badge.style.color = 'var(--ink-secondary)';
    }, 4000);

  } catch (err) {
    badge.textContent = `ERROR [${mode.toUpperCase()}]`;
    badge.style.background = 'var(--status-red-bg)';
    badge.style.color = 'var(--status-red-text)';
  }
}

function appendTerminalLog(text) {
  const container = document.getElementById('terminalLogsContainer');
  if (!container) return;
  const now = new Date().toTimeString().split(' ')[0];
  const div = document.createElement('div');
  div.className = 'log-line';
  div.innerHTML = `<span class="log-time">[${now}]</span><span class="log-text">${escapeHtml(text)}</span>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function clearTerminalLogs() {
  const container = document.getElementById('terminalLogsContainer');
  if (container) {
    container.innerHTML = `<div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-text">TERMINAL CLEARED // STANDBY.</span></div>`;
  }
}

function setSystemStatus(text) {
  const el = document.getElementById('systemStatus');
  if (el) el.innerHTML = `<span class="pulse-dot"></span>${text}`;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ===================================================================
// AUTONOMOUS AGENT / BOT CONTROLLER (START / STOP)
// ===================================================================

let isAgentRunning = false;
let agentPollInterval = null;

async function checkAgentStatus() {
  try {
    const res = await fetch('/api/agent/status');
    if (!res.ok) return;
    const data = await res.json();
    isAgentRunning = data.running;
    updateAgentUI(data);
  } catch (err) {
    console.error('Failed to poll agent status:', err);
  }
}

function updateAgentUI(data) {
  isAgentRunning = data.running;
  
  // Header Toggle Button
  const headerBtn = document.getElementById('headerAgentToggleBtn');
  if (headerBtn) {
    if (isAgentRunning) {
      headerBtn.textContent = '[ STOP BOT ]';
      headerBtn.className = 'btn btn-sm agent-toggle-btn running';
    } else {
      headerBtn.textContent = '[ START BOT ]';
      headerBtn.className = 'btn btn-sm agent-toggle-btn';
    }
  }

  // Hero Toggle Button
  const heroBtn = document.getElementById('heroAgentToggleBtn');
  if (heroBtn) {
    if (isAgentRunning) {
      heroBtn.textContent = '[ STOP BOT ]';
      heroBtn.className = 'btn btn-primary agent-toggle-btn running';
    } else {
      heroBtn.textContent = '[ START BOT ]';
      heroBtn.className = 'btn btn-primary agent-toggle-btn';
    }
  }

  // Live Process Toolbar Buttons
  const btnStart = document.getElementById('btnStartAgentLive');
  const btnStop = document.getElementById('btnStopAgentLive');
  const liveBadge = document.getElementById('liveProcessBadge');
  const liveDot = document.getElementById('liveAgentStatusDot');

  if (btnStart) btnStart.disabled = isAgentRunning;
  if (btnStop) btnStop.disabled = !isAgentRunning;

  if (liveBadge) {
    liveBadge.textContent = isAgentRunning ? 'RUNNING // ACTIVE CYCLING' : 'STOPPED // STANDBY';
    liveBadge.style.color = isAgentRunning ? 'var(--status-green-text)' : 'var(--ink-secondary)';
    liveBadge.style.borderColor = isAgentRunning ? 'var(--status-green-border)' : 'var(--border)';
  }

  if (liveDot) {
    liveDot.style.background = isAgentRunning ? 'var(--status-green-text)' : 'var(--ink-muted)';
  }

  // Header status indicator
  setSystemStatus(isAgentRunning ? 'BOT ACTIVE // CYCLING' : 'DAEMON READY');

  // Update pipeline nodes
  const activeStep = data.active_step || 0;
  for (let i = 1; i <= 5; i++) {
    const node = document.getElementById(`pNode${i}`);
    if (!node) continue;
    if (i === activeStep) {
      node.className = 'pipeline-node active';
    } else if (i < activeStep) {
      node.className = 'pipeline-node completed';
    } else {
      node.className = 'pipeline-node';
    }
  }

  // Update stage title & status tag
  const stageTitle = document.getElementById('liveStageTitle');
  const stageStatusTag = document.getElementById('liveStageStatusTag');
  if (stageTitle && data.stage_name) stageTitle.textContent = data.stage_name;
  if (stageStatusTag && data.status) stageStatusTag.textContent = data.status;

  // Update current job card
  if (data.current_job) {
    const j = data.current_job;
    const titleEl = document.getElementById('liveTargetJobTitle');
    const compEl = document.getElementById('liveTargetJobCompany');
    const scoreEl = document.getElementById('liveTargetScore');
    const urlEl = document.getElementById('liveTargetUrl');

    if (titleEl) titleEl.textContent = j.title || 'Senior Full-Stack Engineer';
    if (compEl) compEl.textContent = `${j.company || 'TechScale'} • ${j.platform || 'WeWorkRemotely'} • Remote Worldwide`;
    if (scoreEl) scoreEl.textContent = `${(j.score || 88.5).toFixed(1)}%`;
    if (urlEl) urlEl.textContent = j.url || 'https://weworkremotely.com';
  }

  // Update Output Preview
  const preview = document.getElementById('liveOutputPreview');
  if (preview) {
    if (activeStep === 1) {
      preview.textContent = `[FEED INGESTION ACTIVE]\nIngested candidates from RemoteOK, Remotive, Jobicy, WeWorkRemotely RSS, Hacker News YC.\nTop Match: ${data.current_job ? data.current_job.title : 'Full-Stack Engineer'}`;
    } else if (activeStep === 2) {
      preview.textContent = `[SEMANTIC SCORING]\nProfile Match Score: ${data.current_job ? (data.current_job.score || 88.5).toFixed(1) : '88.5'}%\nKeywords Detected: React 19, FastAPI, WebSockets, Python, Playwright\nAlignment: High Priority Direct Match`;
    } else if (activeStep === 3) {
      preview.textContent = data.proposal_sample || `[GEMINI 3.6 FLASH PROPOSAL GENERATED]\nTargeting: ${data.current_job ? data.current_job.company : 'Client'}\nCiting case studies: URA-Shree (Autonomous AST Agent) & EduSync.\nDiscovery link: https://calendly.com/pritom580cse`;
    } else if (activeStep === 4) {
      preview.textContent = `[PLAYWRIGHT DOM PRE-FILL READY]\nBrowser Context: Persistent Chromium (data/browser_profile)\nFields Populated: Full Name, Email, Portfolio, LinkedIn, GitHub\nResume Attached: data/resume.pdf\nState: Awaiting human 1-click submission`;
    } else if (activeStep === 5) {
      preview.textContent = `[LEAD RETENTION AUTO-RESPONDER]\nMailbox Listener: Active\nAutomated Hold: Response under 60 seconds\nInjected: Standard rate ($65/hr) + Calendly Discovery Link\nEscalation Guard: Active`;
    }
  }

  // Update Live Terminal Logs
  if (data.logs && data.logs.length > 0) {
    const term = document.getElementById('liveProcessLogTerminal');
    if (term) {
      term.innerHTML = data.logs.map(log => {
        const timeMatch = log.match(/^\[(.*?)\]\s*(.*)$/);
        const time = timeMatch ? timeMatch[1] : 'SYSTEM';
        const msg = timeMatch ? timeMatch[2] : log;
        return `<div class="log-line"><span class="log-time">[${escapeHtml(time)}]</span><span class="log-text">${escapeHtml(msg)}</span></div>`;
      }).join('');
      term.scrollTop = term.scrollHeight;
    }
  }
}

async function startAgent() {
  try {
    const res = await fetch('/api/agent/start', { method: 'POST' });
    const data = await res.json();
    isAgentRunning = true;
    updateAgentUI(data);
    startAgentPolling();
  } catch (err) {
    console.error('Failed to start agent:', err);
  }
}

async function stopAgent() {
  try {
    const res = await fetch('/api/agent/stop', { method: 'POST' });
    const data = await res.json();
    isAgentRunning = false;
    updateAgentUI(data);
    stopAgentPolling();
  } catch (err) {
    console.error('Failed to stop agent:', err);
  }
}

function toggleAgentRun() {
  if (isAgentRunning) {
    stopAgent();
  } else {
    startAgent();
  }
}

function startAgentPolling() {
  if (agentPollInterval) clearInterval(agentPollInterval);
  agentPollInterval = setInterval(checkAgentStatus, 1500);
}

function stopAgentPolling() {
  if (agentPollInterval) {
    clearInterval(agentPollInterval);
    agentPollInterval = null;
  }
  setTimeout(checkAgentStatus, 300);
}

async function triggerProcessStepManual(stepNum = 1) {
  try {
    const res = await fetch('/api/agent/live-process/step', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step: stepNum })
    });
    if (res.ok) {
      const data = await res.json();
      updateAgentUI(data);
    }
  } catch (err) {
    console.error('Manual step error:', err);
  }
}

async function resetLiveProcess() {
  await triggerProcessStepManual(0);
}

function clearLiveProcessLogs() {
  const term = document.getElementById('liveProcessLogTerminal');
  if (term) {
    term.innerHTML = '<div class="log-line"><span class="log-time">[00:00:00]</span><span class="log-text">TERMINAL CLEARED // STANDBY.</span></div>';
  }
}

