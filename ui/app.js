/* ===================================================================
   AutoJob AI Dashboard Frontend Engine
   Rule: Pure vanilla JS, zero emojis, crisp monospace telemetry
   =================================================================== */

let allJobs = [];
let allConversations = [];
let currentFilter = 'all';
let currentConvFilter = 'all';
let selectedJobId = null;
let profileData = null;

// Initialize upon DOM load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadAllData();
});

// View Navigation Switcher
function switchMainView(viewName) {
  document.getElementById('mainViewJobs').style.display = viewName === 'jobs' ? 'block' : 'none';
  document.getElementById('mainViewMessages').style.display = viewName === 'messages' ? 'block' : 'none';
  document.getElementById('mainViewContact').style.display = viewName === 'contact' ? 'block' : 'none';
  document.getElementById('mainViewConsole').style.display = viewName === 'console' ? 'block' : 'none';

  document.getElementById('viewBtnJobs').className = `view-nav-btn ${viewName === 'jobs' ? 'active' : ''}`;
  document.getElementById('viewBtnMessages').className = `view-nav-btn ${viewName === 'messages' ? 'active' : ''}`;
  document.getElementById('viewBtnContact').className = `view-nav-btn ${viewName === 'contact' ? 'active' : ''}`;
  document.getElementById('viewBtnConsole').className = `view-nav-btn ${viewName === 'console' ? 'active' : ''}`;
}

// Theme Management
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

// Master Data Fetching
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

// Rendering Jobs
function renderJobsList() {
  const container = document.getElementById('jobsListContainer');
  let filtered = allJobs;

  if (currentFilter === 'discovered') {
    filtered = allJobs.filter(j => j.status === 'discovered');
  } else if (currentFilter === 'applied') {
    filtered = allJobs.filter(j => j.status === 'applied');
  } else if (currentFilter === 'high') {
    filtered = allJobs.filter(j => (j.match_score || 0) >= 70.0);
  }

  if (filtered.length === 0) {
    container.innerHTML = `
      <div style="padding: 32px; text-align: center; color: var(--ink-muted); font-family: var(--font-mono); font-size: 12px;">
        No listings match filter [${currentFilter.toUpperCase()}]. Run scout or switch filters.
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
          <div class="job-company">${escapeHtml(j.company)} • ${escapeHtml(j.location || 'Remote')}</div>
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

// Select and Inspect a Job
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
}

// Proposal Generation
async function triggerJobProposal(jobId) {
  selectJob(jobId);
  const textarea = document.getElementById('proposalTextarea');
  textarea.value = "Generating tailored technical proposal referencing relevant case studies...";
  document.getElementById('workbenchStatusTag').textContent = 'GENERATING...';

  try {
    const res = await fetch('/api/proposals/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId })
    });
    
    if (!res.ok) throw new Error('Generation failed');
    const data = await res.json();
    
    textarea.value = data.proposal_text;
    document.getElementById('btnRecordApplication').disabled = false;
    document.getElementById('workbenchStatusTag').textContent = 'READY';
  } catch (err) {
    textarea.value = "Error generating proposal. Please retry.";
    document.getElementById('workbenchStatusTag').textContent = 'ERROR';
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

// Applications Table
function renderApplicationsTable(apps) {
  const tbody = document.getElementById('appliedTableBody');
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
        No communications logged under filter [${currentConvFilter.toUpperCase()}].
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(c => {
    const isEscalation = c.status === 'escalation';
    const statusTag = isEscalation 
      ? '<span class="status-tag tag-escalation">[NEEDS FOUNDER REVIEW]</span>' 
      : '<span class="status-tag tag-responded">[AUTO-RESPONDED WITH CALENDLY]</span>';

    return `
      <div class="msg-thread-card">
        <div class="msg-thread-header">
          <div class="sender-block">
            <span class="sender-name">${escapeHtml(c.client_name)}</span>
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 3px;">
              <span class="msg-platform-badge">${escapeHtml(c.platform)}</span>
              <span class="target-meta">${c.updated_at ? c.updated_at.substring(0, 16) : 'Just now'}</span>
            </div>
          </div>
          <div>${statusTag}</div>
        </div>

        <div>
          <span class="panel-title" style="font-size: 10px; margin-bottom: 4px; display: block; color: var(--ink-muted);">INBOUND CLIENT INQUIRY:</span>
          <div class="msg-body-box">${escapeHtml(c.last_message_text)}</div>
        </div>

        <div>
          <span class="panel-title" style="font-size: 10px; margin-bottom: 4px; display: block; color: var(--ink-muted);">AUTO-GENERATED HOLDING RESPONSE:</span>
          <div class="reply-body-box">${escapeHtml(c.last_reply_text)}</div>
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
  const clientName = document.getElementById('newMsgSender').value.trim() || 'Inbound Lead';
  const messageText = document.getElementById('newMsgContent').value.trim();

  if (!messageText) return;

  try {
    const res = await fetch('/api/conversations/receive', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ platform, client_name: clientName, message_text: messageText })
    });
    if (!res.ok) throw new Error('Receive error');
    
    appendLog(`[INBOUND] Received inquiry via ${platform} from '${clientName}'. Dispatched holding response.`);
    await fetchConversations();
    await fetchStats();
  } catch (err) {
    alert("Error processing simulated message.");
  }
}

// ===================================================================
// CONTACT INFO & PROFILE FORM
// ===================================================================

function populateContactForm(data) {
  if (!data || !data.personal_info) return;
  const p = data.personal_info;
  const r = data.preferences ? data.preferences.rates : {};

  document.getElementById('cfgFullName').value = p.full_name || '';
  document.getElementById('cfgProfessionalTitle').value = p.professional_title || '';
  document.getElementById('cfgEmail').value = p.email || '';
  document.getElementById('cfgPhone').value = p.phone || '';
  document.getElementById('cfgLocation').value = p.location || '';
  document.getElementById('cfgHourlyRate').value = r.preferred_hourly_usd || 65;
  document.getElementById('cfgMinBudget').value = r.minimum_project_budget_usd || 800;
  document.getElementById('cfgCalendarUrl').value = p.calendar_booking_url || '';
  document.getElementById('cfgPortfolioUrl').value = p.portfolio_url || '';
  document.getElementById('cfgGithubUrl').value = p.github_url || '';
  document.getElementById('cfgLinkedinUrl').value = p.linkedin_url || '';
}

async function saveContactInfo(e) {
  e.preventDefault();
  const statusEl = document.getElementById('contactSaveStatus');
  statusEl.textContent = 'Saving changes to config/profile.json...';

  const payload = {
    full_name: document.getElementById('cfgFullName').value,
    professional_title: document.getElementById('cfgProfessionalTitle').value,
    email: document.getElementById('cfgEmail').value,
    phone: document.getElementById('cfgPhone').value || null,
    location: document.getElementById('cfgLocation').value,
    portfolio_url: document.getElementById('cfgPortfolioUrl').value || null,
    github_url: document.getElementById('cfgGithubUrl').value || null,
    linkedin_url: document.getElementById('cfgLinkedinUrl').value || null,
    calendar_booking_url: document.getElementById('cfgCalendarUrl').value || null,
    preferred_hourly_usd: parseFloat(document.getElementById('cfgHourlyRate').value),
    minimum_project_budget_usd: parseFloat(document.getElementById('cfgMinBudget').value)
  };

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Save error');
    
    statusEl.textContent = 'Contact info saved successfully!';
    appendLog(`[CONFIG] Contact profile updated: ${payload.full_name} (${payload.email})`);
    await loadAllData();
    setTimeout(() => statusEl.textContent = 'Ready', 3000);
  } catch (err) {
    statusEl.textContent = 'Error saving profile.';
  }
}

function renderProfileCredentials(profile) {
  const container = document.getElementById('profileCaseStudiesList');
  if (!profile || !profile.case_studies) return;

  container.innerHTML = profile.case_studies.map(cs => `
    <div style="background-color: var(--surface-inset); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px 14px;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">
        <strong style="color: var(--ink); font-size: 13px;">${escapeHtml(cs.title)}</strong>
        <span class="tag-pill" style="font-size: 10px;">${escapeHtml(cs.role)}</span>
      </div>
      <p style="font-size: 12px; color: var(--ink-secondary); margin-bottom: 6px;">${escapeHtml(cs.summary)}</p>
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <div class="tag-pills">
          ${cs.tech_stack.map(t => `<span class="tag-pill">${escapeHtml(t)}</span>`).join('')}
        </div>
        ${cs.live_url ? `<a href="${cs.live_url}" target="_blank" style="font-family: var(--font-mono); font-size: 11px; color: var(--ink-secondary); text-decoration: underline;">[ REPO / DEMO ]</a>` : ''}
      </div>
    </div>
  `).join('');
}

// ===================================================================
// ONE-CLICK AGENT RUNNER & LOGS
// ===================================================================

async function runAgentAction(mode) {
  const badge = document.getElementById('runnerStatusBadge');
  const termBadge = document.getElementById('terminalStatusBadge');
  badge.textContent = `RUNNING [${mode.toUpperCase()}]`;
  termBadge.textContent = 'ACTIVE';

  appendLog(`--- EXECUTION TRIGGER: MODE [${mode.toUpperCase()}] ---`);

  try {
    const res = await fetch('/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode })
    });
    
    if (!res.ok) throw new Error('Agent execution failed');
    const data = await res.json();

    if (data.logs && Array.isArray(data.logs)) {
      data.logs.forEach(l => appendLog(l));
    }

    if (mode === 'top_proposal' && data.proposal_text) {
      document.getElementById('proposalTextarea').value = data.proposal_text;
      selectedJobId = data.job_id;
      document.getElementById('targetJobTitle').textContent = data.title;
      document.getElementById('targetJobCompany').textContent = data.company;
      document.getElementById('btnRecordApplication').disabled = false;
      switchMainView('jobs');
    }

    badge.textContent = 'DONE';
    termBadge.textContent = 'STANDBY';
    await loadAllData();
    setTimeout(() => badge.textContent = 'IDLE', 3000);
  } catch (err) {
    badge.textContent = 'ERROR';
    termBadge.textContent = 'ERROR';
    appendLog(`[ERROR] Failed to execute mode ${mode}: ${err.message}`);
    setTimeout(() => badge.textContent = 'IDLE', 4000);
  }
}

function appendLog(text) {
  const container = document.getElementById('terminalLogsContainer');
  if (!container) return;
  const time = new Date().toTimeString().split(' ')[0];
  const line = document.createElement('div');
  line.className = 'log-line';
  line.innerHTML = `
    <span class="log-time">[${time}]</span>
    <span class="log-text">${escapeHtml(text)}</span>
  `;
  container.appendChild(line);
  container.scrollTop = container.scrollHeight;
}

function clearTerminalLogs() {
  const container = document.getElementById('terminalLogsContainer');
  if (container) {
    container.innerHTML = `
      <div class="log-line">
        <span class="log-time">[${new Date().toTimeString().split(' ')[0]}]</span>
        <span class="log-text">TERMINAL LOGS CLEARED // STANDBY.</span>
      </div>
    `;
  }
}

function setSystemStatus(text) {
  const el = document.getElementById('systemStatus');
  if (el) el.textContent = text;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
