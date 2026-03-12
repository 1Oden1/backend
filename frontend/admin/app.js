/* ═══════════════════════════════════════════════════
   ENT Salé — Admin · app.js
   Routes corrigées selon le backend réel
═══════════════════════════════════════════════════ */
'use strict';

const token   = localStorage.getItem('access_token');
const userStr = localStorage.getItem('user');
if (!token || !userStr) location.href = '/login/';
let currentUser = {};
try { currentUser = JSON.parse(userStr); } catch { location.href = '/login/'; }
if (!currentUser.roles?.includes('admin')) location.href = '/login/';

async function api(method, path, body) {
  const headers = { Authorization: `Bearer ${token}` };
  const opts = { method, headers };
  if (body) { headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  const r = await fetch(path, opts);
  if (r.status === 401) location.href = '/login/';
  return r;
}

document.addEventListener('DOMContentLoaded', () => {
  const name = currentUser.first_name || currentUser.username || 'Admin';
  document.getElementById('userNameEl').textContent = name;
  document.getElementById('avatarEl').textContent   = name[0].toUpperCase();

  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, el); })
  );
  document.getElementById('logoutBtn').addEventListener('click', doLogout);
  document.getElementById('refreshBtn').addEventListener('click', () => { loadDashboard(); showToast('Actualisé'); });
  document.getElementById('addUserBtn').addEventListener('click', () => openModal('modalUser'));
  document.getElementById('createUserBtn2').addEventListener('click', () => openModal('modalUser'));
  document.getElementById('addFiliereBtn').addEventListener('click', () => openModal('modalFiliere'));
  document.getElementById('cancelUserModal').addEventListener('click', () => closeModal('modalUser'));
  document.getElementById('cancelFiliereModal').addEventListener('click', () => closeModal('modalFiliere'));
  document.getElementById('confirmUserModal').addEventListener('click', createUser);
  document.getElementById('confirmFiliereModal').addEventListener('click', createFiliere);
  document.getElementById('reloadHealthBtn').addEventListener('click', () => loadHealth('healthGrid'));
  document.getElementById('fileCatFilter').addEventListener('change', loadFiles);
  document.querySelectorAll('.modal-overlay').forEach(o =>
    o.addEventListener('click', e => { if (e.target === o) closeModal(o.id); })
  );
  loadDashboard();
});

const panelTitles = {
  dashboard: 'Vue d\'ensemble', users: 'Utilisateurs', files: 'Fichiers & Cours',
  calendar: 'Calendrier académique', notes: 'Notes', audit: 'Journal d\'audit', health: 'État des services',
};

function switchPanel(id, navEl) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  document.getElementById('topbarTitle').textContent = panelTitles[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  const loaders = { users: loadUsers, files: loadFiles, calendar: loadCalendar, notes: loadNotes, audit: loadAudit, health: () => loadHealth('healthGrid') };
  if (loaders[id]) loaders[id]();
}

// ── DASHBOARD ─────────────────────────────────────────────────────────────────
async function loadDashboard() {
  loadHealth('servicesGrid', true);
  const el = document.getElementById('recentFilesList');
  el.innerHTML = '<div class="loader"></div>';
  try {
    // Admin : GET /api/admin/fichiers/ → voit tous les fichiers (publics + privés)
    const r = await api('GET', '/api/admin/fichiers/');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    document.getElementById('st-files').textContent = files.length;
    if (!files.length) { el.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier</p></div>'; return; }
    el.innerHTML = files.slice(0, 6).map(f => `
      <div class="audit-item">
        <div class="audit-dot"></div>
        <div>
          <div class="audit-text"><strong>${f.title || f.filename}</strong> — ${f.category || ''} / ${f.module || ''}</div>
          <div class="audit-time">${f.owner_name || '—'} · ${f.upload_date ? new Date(f.upload_date).toLocaleDateString('fr-FR') : ''}</div>
        </div>
      </div>`).join('');
  } catch { el.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur chargement fichiers</p></div>'; }
}

// ── HEALTH ────────────────────────────────────────────────────────────────────
const SERVICES = [
  { name: 'Auth',      url: '/api/auth/health',     icon: '🔐' },
  { name: 'Upload',    url: '/api/upload/health',    icon: '📤' },
  { name: 'Download',  url: '/api/download/health',  icon: '📥' },
  { name: 'Calendar',  url: '/api/calendar/health',  icon: '📅' },
  { name: 'Notes',     url: '/api/notes/health',     icon: '📊' },
  { name: 'Admin',     url: '/api/admin/health',     icon: '⚙️' },
  { name: 'Messaging', url: '/api/messaging/health', icon: '💬' },
];

function loadHealth(containerId, mini = false) {
  const grid = document.getElementById(containerId);
  if (!grid) return;
  grid.innerHTML = '';
  let up = 0;
  for (const s of SERVICES) {
    const card = document.createElement('div');
    card.className = 'service-card';
    card.innerHTML = `<div class="sc-icon">${s.icon}</div><div class="sc-name">${s.name}</div><div class="sc-status" style="color:var(--muted)">…</div>`;
    grid.appendChild(card);
    fetch(s.url, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => {
        if (r.ok) up++;
        card.style.borderColor = r.ok ? 'rgba(46,125,50,.3)' : 'rgba(192,57,43,.3)';
        const st = card.querySelector('.sc-status');
        st.textContent = r.ok ? '● Opérationnel' : '● Hors ligne';
        st.className = 'sc-status ' + (r.ok ? 'sc-up' : 'sc-down');
        if (mini) document.getElementById('st-services').textContent = up + '/7';
      })
      .catch(() => {
        card.style.borderColor = 'rgba(192,57,43,.3)';
        card.querySelector('.sc-status').textContent = '● Inaccessible';
        card.querySelector('.sc-status').className = 'sc-status sc-down';
      });
  }
}

// ── USERS ─────────────────────────────────────────────────────────────────────
async function loadUsers() {
  const wrap = document.getElementById('usersTable');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/admin/users → retourne List[UserRead] (tableau JSON direct)
    const r = await api('GET', '/api/admin/users');
    if (!r.ok) throw new Error(r.status);
    const users = await r.json(); // TABLEAU direct, pas {users:[...]}
    document.getElementById('st-users').textContent = users.length;
    if (!users.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">👤</div><p>Aucun utilisateur</p></div>'; return; }
    wrap.innerHTML = `<table>
      <thead><tr><th>Nom complet</th><th>Identifiant</th><th>Email</th><th>Rôle(s)</th><th>Actif</th><th>Actions</th></tr></thead>
      <tbody>${users.map(u => `<tr>
        <td>${u.first_name || ''} ${u.last_name || ''}</td>
        <td>${u.username || ''}</td>
        <td>${u.email || ''}</td>
        <td>${(u.roles || []).map(r => `<span class="badge badge-${r}">${r}</span>`).join(' ') || '—'}</td>
        <td>${u.enabled ? '✅' : '❌'}</td>
        <td class="td-actions"><button class="btn btn-danger btn-sm" onclick="deleteUser('${u.id}')">🗑</button></td>
      </tr>`).join('')}</tbody>
    </table>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Impossible de charger les utilisateurs</p></div>'; }
}

async function createUser() {
  // IMPORTANT : le backend attend first_name / last_name (snake_case)
  const body = {
    username:   document.getElementById('uUsername').value.trim(),
    email:      document.getElementById('uEmail').value.trim(),
    first_name: document.getElementById('uFirstName').value.trim(),
    last_name:  document.getElementById('uLastName').value.trim(),
    password:   document.getElementById('uPassword').value,
    roles:      [document.getElementById('uRole').value],
  };
  if (!body.username || !body.password || !body.email) { showToast('Champs obligatoires manquants', 'error'); return; }
  try {
    const r = await api('POST', '/api/admin/users', body);
    if (r.ok || r.status === 201) { showToast('Utilisateur créé ✓', 'success'); closeModal('modalUser'); loadUsers(); }
    else { const d = await r.json().catch(() => ({})); showToast(d.detail || `Erreur ${r.status}`, 'error'); }
  } catch { showToast('Erreur réseau', 'error'); }
}

async function deleteUser(id) {
  if (!id || !confirm('Supprimer cet utilisateur ?')) return;
  try {
    const r = await api('DELETE', `/api/admin/users/${id}`);
    if (r.ok || r.status === 204) { showToast('Supprimé ✓', 'success'); loadUsers(); }
    else showToast('Erreur suppression', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

// ── FILES ─────────────────────────────────────────────────────────────────────
const FILE_ICONS  = { cours: '📖', td: '✏️', tp: '🔬', examen: '📝', autre: '📄' };
const TAG_CLASSES = { cours: 'tag-cours', td: 'tag-td', tp: 'tag-tp', examen: 'tag-examen', autre: 'tag-autre' };

async function loadFiles() {
  const grid = document.getElementById('filesGrid');
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const cat = document.getElementById('fileCatFilter').value;
    // Admin : /api/admin/fichiers (voit tout, y compris privés)
    const url = cat ? `/api/admin/fichiers/?category=${cat}` : '/api/admin/fichiers/';
    const r = await api('GET', url);
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    if (!files.length) { grid.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier</p></div>'; return; }
    grid.innerHTML = files.map(f => `
      <div class="file-card">
        <div class="fc-icon">${FILE_ICONS[f.category] || '📄'}</div>
        <span class="fc-tag ${TAG_CLASSES[f.category] || 'tag-autre'}">${f.category || 'autre'}</span>
        <div class="fc-title">${f.title || f.filename}</div>
        <div class="fc-meta">${f.module || ''} · ${f.size_bytes ? Math.round(f.size_bytes / 1024) + ' KB' : ''}</div>
        <div class="fc-actions">
          <button class="btn btn-outline btn-sm" onclick="downloadFile('${f.file_id}')">↓</button>
          <button class="btn btn-danger  btn-sm" onclick="deleteFile('${f.file_id}')">🗑</button>
        </div>
      </div>`).join('');
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur chargement fichiers</p></div>'; }
}

async function downloadFile(fileId) {
  try {
    // Route CORRECTE : GET /api/download/{file_id} (pas /link)
    // Réponse : { file_id, filename, download_url, expires_in }
    const r = await api('GET', `/api/download/${fileId}`);
    if (r.ok) { const d = await r.json(); window.open(d.download_url, '_blank'); }
    else showToast('Lien indisponible', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

async function deleteFile(fileId) {
  if (!confirm('Supprimer ce fichier ?')) return;
  try {
    // Admin supprime via /api/admin/fichiers/{file_id}
    const r = await api('DELETE', `/api/admin/fichiers/${fileId}`);
    if (r.ok || r.status === 204) { showToast('Fichier supprimé ✓', 'success'); loadFiles(); }
    else showToast('Erreur suppression', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

// ── CALENDAR ──────────────────────────────────────────────────────────────────
async function loadCalendar() {
  const wrap = document.getElementById('calendarContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/calendar/filieres → List[FiliereRead] (tableau direct)
    const r = await api('GET', '/api/calendar/filieres');
    if (!r.ok) throw new Error();
    const filieres = await r.json();
    document.getElementById('st-filieres').textContent = filieres.length;
    if (!filieres.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">🎓</div><p>Aucune filière</p></div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>Code</th><th>Libellé</th><th>Département</th><th>Actions</th></tr></thead>
      <tbody>${filieres.map(f => `<tr>
        <td>${f.id}</td><td>${f.code || '—'}</td><td>${f.label || f.nom || '—'}</td>
        <td>${f.departement?.nom || f.departement_id || '—'}</td>
        <td><button class="btn btn-danger btn-sm" onclick="deleteFiliere(${f.id})">🗑</button></td>
      </tr>`).join('')}</tbody>
    </table></div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur chargement calendrier</p></div>'; }
}

async function createFiliere() {
  const body = {
    label: document.getElementById('fLabel').value.trim(),
    code:  document.getElementById('fCode').value.trim(),
    departement_id: parseInt(document.getElementById('fDeptId').value),
  };
  if (!body.label) { showToast('Libellé requis', 'error'); return; }
  try {
    const r = await api('POST', '/api/calendar/filieres', body);
    if (r.ok || r.status === 201) { showToast('Filière créée ✓', 'success'); closeModal('modalFiliere'); loadCalendar(); }
    else { const d = await r.json().catch(() => ({})); showToast(d.detail || 'Erreur', 'error'); }
  } catch { showToast('Erreur réseau', 'error'); }
}

async function deleteFiliere(id) {
  if (!confirm('Supprimer cette filière ?')) return;
  try {
    const r = await api('DELETE', `/api/calendar/filieres/${id}`);
    if (r.ok || r.status === 204) { showToast('Supprimée ✓', 'success'); loadCalendar(); }
    else showToast('Erreur', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

// ── NOTES ─────────────────────────────────────────────────────────────────────
async function loadNotes() {
  const wrap = document.getElementById('notesContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/notes/admin/etudiants → tableau d'étudiants
    const r = await api('GET', '/api/notes/admin/etudiants');
    if (!r.ok) throw new Error();
    const data = await r.json();
    const etudiants = Array.isArray(data) ? data : (data.etudiants || []);
    if (!etudiants.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">📊</div><p>Aucun étudiant dans ms-notes</p></div>'; return; }
    wrap.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>ID</th><th>CNE</th><th>Prénom</th><th>Nom</th><th>Filière ID</th></tr></thead>
      <tbody>${etudiants.map(e => `<tr>
        <td>${e.id}</td><td>${e.cne || '—'}</td>
        <td>${e.prenom || '—'}</td><td>${e.nom || '—'}</td>
        <td>${e.calendar_filiere_id || '—'}</td>
      </tr>`).join('')}</tbody>
    </table></div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur chargement notes</p></div>'; }
}

// ── AUDIT ─────────────────────────────────────────────────────────────────────
async function loadAudit() {
  const wrap = document.getElementById('auditList');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/admin/audit → List[AuditLogRead] (tableau direct)
    const r = await api('GET', '/api/admin/audit');
    if (!r.ok) throw new Error();
    const logs = await r.json(); // tableau direct
    if (!logs.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">📋</div><p>Journal vide</p></div>'; return; }
    wrap.innerHTML = logs.map(l => `
      <div class="audit-item">
        <div class="audit-dot"></div>
        <div>
          <div class="audit-text"><strong>${l.action || '—'}</strong> · ${l.target_type || ''} · ${l.details || ''}</div>
          <div class="audit-time">${l.admin_id || '—'} · ${l.created_at ? new Date(l.created_at).toLocaleString('fr-FR') : ''}</div>
        </div>
      </div>`).join('');
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Journal indisponible</p></div>'; }
}

// ── Utils ─────────────────────────────────────────────────────────────────────
function openModal(id)  { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

let _toastTimer;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast show ' + type;
  clearTimeout(_toastTimer); _toastTimer = setTimeout(() => { t.className = 'toast'; }, 3200);
}

async function doLogout() {
  const rt = localStorage.getItem('refresh_token');
  if (rt) { try { await api('POST', '/api/auth/logout', { refresh_token: rt }); } catch {} }
  localStorage.clear(); location.href = '/login/';
}
