// ── notifications.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';

document.getElementById('user-name').textContent = username || 'Utilisateur';
const roleLabels = { admin: '⚙️ Administrateur', enseignant: '👨‍🏫 Enseignant', teacher: '👨‍🏫 Enseignant', etudiant: '🎓 Étudiant' };
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';
if (role === 'admin') {
  document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');
}

let allNotifs  = [];
let currentFilter = 'all';

async function loadNotifications() {
  try {
    const res  = await fetch('/api/messaging/notifications/', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    const data = await res.json();
    allNotifs  = data;
    updateStats(data);
    renderNotifs(data);
  } catch(e) {
    document.getElementById('notifs-list').innerHTML =
      '<div class="empty-state"><div class="icon">⚠️</div><h3>Erreur de chargement</h3><p>Impossible de récupérer les notifications.</p></div>';
  }
}

function updateStats(notifs) {
  const unread = notifs.filter(n => !n.is_read).length;
  document.getElementById('stat-total').textContent  = notifs.length;
  document.getElementById('stat-unread').textContent = unread;
  document.getElementById('stat-read').textContent   = notifs.length - unread;
  if (unread > 0) {
    document.getElementById('unread-badge').textContent  = unread;
    document.getElementById('unread-badge').style.display = 'inline';
  } else {
    document.getElementById('unread-badge').style.display = 'none';
  }
}

function renderNotifs(notifs) {
  const list = document.getElementById('notifs-list');
  document.getElementById('notifs-count').textContent = notifs.length + ' notification' + (notifs.length > 1 ? 's' : '');

  if (notifs.length === 0) {
    list.innerHTML = '<div class="empty-state"><div class="icon">🔕</div><h3>Aucune notification</h3><p>Vous êtes à jour !</p></div>';
    return;
  }

  const typeIcons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' };
  const typeLabels = { info: 'Info', success: 'Succès', warning: 'Avertissement', error: 'Erreur' };

  list.innerHTML = notifs.map(n => {
    const t    = n.type || 'info';
    const icon = typeIcons[t] || 'ℹ️';
    return '<div class="notif-item ' + (!n.is_read ? 'unread' : '') + '" onclick="markRead(' + n.id + ', this)">' +
      '<div class="notif-icon-wrap ' + t + '">' + icon + '</div>' +
      '<div class="notif-body">' +
        '<div class="notif-title">' + (n.title || 'Notification') + '</div>' +
        '<div class="notif-message">' + (n.message || '') + '</div>' +
        '<div class="notif-meta">' +
          '<span class="notif-time">' + formatDate(n.created_at) + '</span>' +
          '<span class="notif-type-badge ' + t + '">' + (typeLabels[t] || t) + '</span>' +
        '</div>' +
      '</div>' +
      (!n.is_read ? '<div class="unread-dot"></div>' : '') +
    '</div>';
  }).join('');
}

function filterNotifs(filter, btn) {
  currentFilter = filter;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');

  let filtered = allNotifs;
  if (filter === 'unread')  filtered = allNotifs.filter(n => !n.is_read);
  else if (filter !== 'all') filtered = allNotifs.filter(n => n.type === filter);

  renderNotifs(filtered);
}

async function markRead(id, el) {
  if (!el.classList.contains('unread')) return;
  try {
    await fetch('/api/messaging/notifications/' + id + '/read', {
      method: 'PATCH',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    el.classList.remove('unread');
    const dot = el.querySelector('.unread-dot');
    if (dot) dot.remove();
    const n = allNotifs.find(n => n.id === id);
    if (n) n.is_read = true;
    updateStats(allNotifs);
  } catch(e) {}
}

async function markAllRead() {
  const unread = allNotifs.filter(n => !n.is_read);
  if (unread.length === 0) { showToast('✅ Tout est déjà lu !', 'success'); return; }
  try {
    await Promise.all(unread.map(n =>
      fetch('/api/messaging/notifications/' + n.id + '/read', {
        method: 'PATCH',
        headers: { 'Authorization': 'Bearer ' + token }
      })
    ));
    allNotifs.forEach(n => n.is_read = true);
    updateStats(allNotifs);
    document.querySelectorAll('.notif-item.unread').forEach(el => {
      el.classList.remove('unread');
      const dot = el.querySelector('.unread-dot');
      if (dot) dot.remove();
    });
    showToast('✅ Toutes les notifications marquées comme lues !', 'success');
  } catch(e) {
    showToast('❌ Erreur', 'error');
  }
}

function openModal()  { document.getElementById('send-modal').classList.add('open'); }
function closeModal() {
  document.getElementById('send-modal').classList.remove('open');
  document.getElementById('notif-to').value      = '';
  document.getElementById('notif-title').value   = '';
  document.getElementById('notif-message').value = '';
}

async function sendNotification() {
  const to      = document.getElementById('notif-to').value.trim();
  const title   = document.getElementById('notif-title').value.trim();
  const message = document.getElementById('notif-message').value.trim();
  const type    = document.getElementById('notif-type').value;

  if (!to || !title || !message) {
    showToast('⚠️ Remplissez tous les champs', 'error');
    return;
  }

  const btn = document.getElementById('notif-submit');
  btn.disabled = true; btn.textContent = '⏳ Envoi...';

  try {
    const res = await fetch('/api/messaging/notifications/send', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ receiver_username: to, title: title, message: message, type: type })
    });
    if (!res.ok) throw new Error();
    showToast('✅ Notification envoyée à ' + to + ' !', 'success');
    closeModal();
  } catch(e) {
    showToast('❌ Erreur lors de l\'envoi', 'error');
  } finally {
    btn.disabled = false; btn.textContent = '📢 Envoyer';
  }
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now - d) / 1000);
  if (diff < 60)   return 'À l\'instant';
  if (diff < 3600) return Math.floor(diff / 60) + ' min';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h';
  if (d.toDateString() === now.toDateString()) return 'Aujourd\'hui';
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

loadNotifications();
setInterval(loadNotifications, 30000);