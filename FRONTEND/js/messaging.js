// ── messaging.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';

document.getElementById('user-name').textContent = username || 'Utilisateur';
const roleLabels = { admin: '⚙️ Administrateur', enseignant: '👨‍🏫 Enseignant', teacher: '👨‍🏫 Enseignant', etudiant: '🎓 Étudiant' };
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';
if (role === 'admin') document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');

// ── STATE ──
let allMessages   = [];
let currentTab    = 'inbox';
let currentMsg    = null;

// ── LOAD INBOX ──
async function loadMessages(tab = 'inbox') {
  const endpoint = tab === 'inbox' ? '/api/messaging/messages/inbox' : '/api/messaging/messages/sent';
  try {
    const res  = await fetch(endpoint, { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await res.json();
    allMessages = data;

    const unread = data.filter(m => !m.is_read).length;
    if (unread > 0) {
      document.getElementById('unread-badge').textContent = unread;
      document.getElementById('unread-badge').style.display = 'inline';
    } else {
      document.getElementById('unread-badge').style.display = 'none';
    }

    renderMessages(data, tab);
  } catch(e) {
    document.getElementById('inbox-list').innerHTML = '<div class="empty-inbox"><div class="icon">⚠️</div><p>Erreur de chargement</p></div>';
  }
}

// ── RENDER MESSAGES ──
function renderMessages(messages, tab) {
  const list = document.getElementById('inbox-list');
  if (messages.length === 0) {
    list.innerHTML = '<div class="empty-inbox"><div class="icon">📭</div><p>Aucun message</p></div>';
    return;
  }

  list.innerHTML = messages.map(m => {
    const isUnread = !m.is_read && tab === 'inbox';
    const name     = tab === 'inbox' ? m.sender_username : m.receiver_username;
    const initial  = (name || '?')[0].toUpperCase();
    const date     = formatDate(m.created_at);
    return '<div class="inbox-item ' + (isUnread ? 'unread' : '') + '" onclick="openMessage(' + m.id + ')" id="msg-' + m.id + '">' +
      '<div class="inbox-avatar">' + initial + '</div>' +
      '<div class="inbox-info">' +
        '<div class="inbox-from">' + name + '<span class="time">' + date + '</span></div>' +
        '<div class="inbox-subject">' + (m.subject || 'Sans sujet') + '</div>' +
        '<div class="inbox-preview">' + m.content + '</div>' +
      '</div>' +
      (isUnread ? '<div class="unread-dot"></div>' : '') +
    '</div>';
  }).join('');
}

// ── OPEN MESSAGE ──
async function openMessage(id) {
  const msg = allMessages.find(m => m.id === id);
  if (!msg) return;
  currentMsg = msg;

  // Mark active
  document.querySelectorAll('.inbox-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById('msg-' + id);
  if (el) { el.classList.add('active'); el.classList.remove('unread'); el.querySelector('.unread-dot') && el.querySelector('.unread-dot').remove(); }

  // Mark as read
  if (!msg.is_read && currentTab === 'inbox') {
    try {
      await fetch('/api/messaging/messages/' + id + '/read', {
        method: 'PATCH',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      msg.is_read = true;
    } catch(e) {}
  }

  // Show conversation
  const convEmpty = document.getElementById('conv-empty');
  const convView  = document.getElementById('conv-view');
  convEmpty.style.display = 'none';
  convView.style.display  = 'flex';

  // Header
  const otherUser = currentTab === 'inbox' ? msg.sender_username : msg.receiver_username;
  const initial   = (otherUser || '?')[0].toUpperCase();
  document.getElementById('conv-header').innerHTML =
    '<div class="conv-header-avatar">' + initial + '</div>' +
    '<div class="conv-header-info">' +
      '<h3>' + otherUser + '</h3>' +
      '<p>' + (msg.subject || 'Sans sujet') + '</p>' +
    '</div>';

  // Messages
  const convMsgs = document.getElementById('conv-messages');
  const isMine   = msg.sender_username === username;
  convMsgs.innerHTML =
    '<div class="date-separator"><span>' + formatDateFull(msg.created_at) + '</span></div>' +
    '<div class="msg-group ' + (isMine ? 'mine' : 'theirs') + '">' +
      '<div class="msg-sender-name">' + (isMine ? 'Vous' : msg.sender_username) + '</div>' +
      '<div class="msg-bubble">' + msg.content + '</div>' +
      '<div class="msg-time">' + formatTime(msg.created_at) + '</div>' +
    '</div>';

  convMsgs.scrollTop = convMsgs.scrollHeight;

  // Pre-fill reply recipient
  document.getElementById('reply-text').value = '';
  document.getElementById('reply-text').focus();
}

// ── SEND REPLY ──
async function sendReply() {
  if (!currentMsg) return;
  const content = document.getElementById('reply-text').value.trim();
  if (!content) return;

  const btn = document.getElementById('reply-btn');
  btn.disabled = true;

  const receiver = currentTab === 'inbox' ? currentMsg.sender_username : currentMsg.receiver_username;

  try {
    const res = await fetch('/api/messaging/messages/send', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        receiver_username: receiver,
        subject: 'Re: ' + (currentMsg.subject || ''),
        content: content
      })
    });

    if (!res.ok) throw new Error();

    // Add to conversation view
    const convMsgs = document.getElementById('conv-messages');
    convMsgs.innerHTML += '<div class="msg-group mine">' +
      '<div class="msg-sender-name">Vous</div>' +
      '<div class="msg-bubble">' + content + '</div>' +
      '<div class="msg-time">' + formatTime(new Date().toISOString()) + '</div>' +
    '</div>';
    convMsgs.scrollTop = convMsgs.scrollHeight;

    document.getElementById('reply-text').value = '';
    document.getElementById('reply-text').style.height = 'auto';
    showToast('✅ Réponse envoyée !', 'success');

  } catch(e) {
    showToast('❌ Erreur lors de l\'envoi', 'error');
  } finally {
    btn.disabled = false;
  }
}

// ── SEND NEW MESSAGE ──
async function sendMessage() {
  const to      = document.getElementById('compose-to').value.trim();
  const subject = document.getElementById('compose-subject').value.trim();
  const content = document.getElementById('compose-body').value.trim();

  if (!to || !subject || !content) {
    showToast('⚠️ Remplissez tous les champs', 'error');
    return;
  }

  const btn = document.getElementById('compose-submit');
  btn.disabled = true; btn.textContent = '⏳ Envoi...';

  try {
    const res = await fetch('/api/messaging/messages/send', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ receiver_username: to, subject: subject, content: content })
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Erreur');
    }

    showToast('✅ Message envoyé à ' + to + ' !', 'success');
    closeCompose();
    if (currentTab === 'sent') loadMessages('sent');

  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur lors de l\'envoi'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '📤 Envoyer';
  }
}

// ── TAB SWITCH ──
function switchTab(tab, el) {
  currentTab = tab;
  currentMsg = null;
  document.getElementById('conv-empty').style.display = 'flex';
  document.getElementById('conv-view').style.display  = 'none';
  document.querySelectorAll('.inbox-tab').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  loadMessages(tab);
}

// ── FILTER ──
function filterMessages() {
  const q = document.getElementById('search-msg').value.toLowerCase();
  const filtered = allMessages.filter(m =>
    m.content.toLowerCase().includes(q) ||
    (m.subject || '').toLowerCase().includes(q) ||
    (m.sender_username || '').toLowerCase().includes(q) ||
    (m.receiver_username || '').toLowerCase().includes(q)
  );
  renderMessages(filtered, currentTab);
}

// ── COMPOSE ──
function openCompose() {
  document.getElementById('compose-modal').classList.add('open');
  document.getElementById('compose-to').focus();
}
function closeCompose() {
  document.getElementById('compose-modal').classList.remove('open');
  document.getElementById('compose-to').value      = '';
  document.getElementById('compose-subject').value = '';
  document.getElementById('compose-body').value    = '';
}

// ── HELPERS ──
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function handleReplyKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendReply(); }
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' });
}

function formatDateFull(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
}

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

// ── INIT ──
loadMessages('inbox');
// Auto-refresh toutes les 30 secondes
setInterval(() => loadMessages(currentTab), 30000);