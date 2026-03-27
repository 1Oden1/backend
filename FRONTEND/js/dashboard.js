// ── dashboard.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

// Redirect if not logged in
if (!token) window.location.href = '/pages/login.html';

// ── DATE ──
const now        = new Date();
const days       = ['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
const months     = ['Jan','Fév','Mar','Avr','Mai','Jun','Jul','Aoû','Sep','Oct','Nov','Déc'];
const monthsFull = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

document.getElementById('topbar-date').textContent  = `${days[now.getDay()]} ${now.getDate()} ${monthsFull[now.getMonth()]} ${now.getFullYear()}`;
document.getElementById('banner-day').textContent   = days[now.getDay()];
document.getElementById('banner-date').textContent  = `${now.getDate()} ${monthsFull[now.getMonth()]} ${now.getFullYear()}`;

// ── USER INFO ──
document.getElementById('welcome-name').textContent = username || 'Utilisateur';
document.getElementById('user-name').textContent    = username || 'Utilisateur';

const roleLabels = {
  admin:      '⚙️ Administrateur',
  enseignant: '👨‍🏫 Enseignant',
  teacher:    '👨‍🏫 Enseignant',
  etudiant:   '🎓 Étudiant',
  student:    '🎓 Étudiant'
};
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';

// Show admin link if admin
if (role === 'admin') {
  document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');
}

// ── MODULES selon rôle ──
const allModules = [
  { icon: '📚', bg: '#e8f2ff',  href: 'courses.html',      title: 'Cours en ligne',     desc: 'Accédez aux ressources pédagogiques disponibles',    roles: ['etudiant','enseignant','admin','teacher','student'] },
  { icon: '📅', bg: '#f0fdf4',  href: 'calendar.html',     title: 'Calendrier',          desc: 'Consultez votre emploi du temps et vos examens',      roles: ['etudiant','enseignant','admin','teacher','student'] },
  { icon: '📊', bg: '#fff7ed',  href: 'notes.html',        title: 'Notes & Résultats',   desc: 'Consultez vos notes et vos moyennes',                 roles: ['etudiant','enseignant','admin','teacher','student'] },
  { icon: '✉️', bg: '#f3f0ff',  href: 'messaging.html',    title: 'Messagerie',          desc: 'Échangez avec vos enseignants et collègues',          roles: ['etudiant','enseignant','admin','teacher','student'] },
  { icon: '🤖', bg: '#fef2f2',  href: 'ai.html',           title: 'Assistant IA',        desc: "Posez vos questions à l'assistant Llama 3",           roles: ['etudiant','enseignant','admin','teacher','student'] },
  { icon: '⚙️', bg: '#f0f4fb',  href: 'admin.html',        title: 'Administration',      desc: 'Gérez les utilisateurs, rôles et permissions',        roles: ['admin'] },
];

const grid = document.getElementById('modules-grid');
allModules
  .filter(m => m.roles.includes(role))
  .forEach((m, i) => {
    grid.innerHTML += `
      <a class="module-card" href="${m.href}" style="animation-delay:${0.1 + i * 0.05}s">
        <span class="module-arrow">→</span>
        <div class="module-icon-wrap" style="background:${m.bg}">${m.icon}</div>
        <h3>${m.title}</h3>
        <p>${m.desc}</p>
      </a>`;
  });

// ── LOAD MESSAGES ──
async function loadMessages() {
  try {
    const res  = await fetch('/api/messaging/messages/inbox', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const msgs = await res.json();
    const unread = msgs.filter(m => !m.is_read).length;

    document.getElementById('stat-msgs').textContent = unread;

    if (unread > 0) {
      document.getElementById('msg-badge').textContent    = unread;
      document.getElementById('msg-dot').style.display   = 'block';
    }

    const list = document.getElementById('messages-list');
    if (msgs.length === 0) {
      list.innerHTML = `
        <div class="msg-item">
          <div class="msg-avatar">📭</div>
          <div class="msg-content">
            <div class="msg-from">Aucun message</div>
            <div class="msg-text">Votre boîte de réception est vide</div>
          </div>
        </div>`;
      return;
    }

    list.innerHTML = msgs.slice(0, 4).map(m => `
      <div class="msg-item">
        <div class="msg-avatar">👤</div>
        <div class="msg-content">
          <div class="msg-from">${m.sender_username}</div>
          <div class="msg-text">${m.content}</div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
          <div class="msg-time">${new Date(m.created_at).toLocaleDateString('fr-FR')}</div>
          ${!m.is_read ? '<div class="msg-unread"></div>' : ''}
        </div>
      </div>`).join('');

  } catch(e) {
    document.getElementById('stat-msgs').textContent = '--';
  }
}

// ── LOAD COURSES ──
async function loadCours() {
  try {
    const res  = await fetch('/api/download/courses/', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    document.getElementById('stat-cours').textContent = data.length;
  } catch(e) {
    document.getElementById('stat-cours').textContent = '--';
  }
}

// ── LOAD NOTES ──
async function loadNotes() {
  try {
    const res  = await fetch('/api/notes/notes/mes-notes', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const data = await res.json();
    document.getElementById('stat-notes').textContent = data.length;
  } catch(e) {
    document.getElementById('stat-notes').textContent = '--';
  }
}

// ── LOAD EVENTS ──
async function loadEvents() {
  try {
    const res  = await fetch('/api/calendar/calendar/', {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const evts = await res.json();
    document.getElementById('stat-events').textContent = evts.length;

    const list = document.getElementById('events-list');
    if (evts.length === 0) {
      list.innerHTML = `
        <div class="evt-item">
          <div class="evt-info">
            <div class="evt-title">Aucun événement à venir</div>
          </div>
        </div>`;
      return;
    }

    list.innerHTML = evts.slice(0, 4).map(e => {
      const d = new Date(e.date_debut);
      return `
        <div class="evt-item">
          <div class="evt-date">
            <div class="day">${d.getDate()}</div>
            <div class="month">${months[d.getMonth()]}</div>
          </div>
          <div class="evt-info">
            <div class="evt-title">${e.titre}</div>
            <div class="evt-sub">${e.lieu || ''} ${e.niveau ? '· ' + e.niveau : ''}</div>
          </div>
          <span class="evt-badge ${e.type}">${e.type}</span>
        </div>`;
    }).join('');

  } catch(e) {
    document.getElementById('stat-events').textContent = '--';
  }
}

// ── LOGOUT ──
function logout() {
  localStorage.clear();
  window.location.href = '/pages/login.html';
}

// ── INIT ──
loadMessages();
loadCours();
loadNotes();
loadEvents();