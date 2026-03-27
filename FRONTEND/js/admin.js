// ── admin.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';
if (role !== 'admin') window.location.href = '/pages/dashboard.html';

document.getElementById('user-name').textContent = username || 'Administrateur';
document.getElementById('user-role').textContent = '⚙️ Administrateur';

let allUsers      = [];
let currentTab    = 'all';
let deleteTarget  = null;

// ── LOAD USERS ──
async function loadUsers() {
  try {
    const res  = await fetch('/api/admin/users/', { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await res.json();
    allUsers   = data;
    updateStats(data);
    renderUsers(data);
  } catch(e) {
    document.getElementById('users-container').innerHTML =
      '<div class="empty-state"><div class="icon">⚠️</div><p>Erreur de chargement</p></div>';
  }
}

// ── STATS ──
function updateStats(users) {
  document.getElementById('stat-total').textContent      = users.length;
  document.getElementById('stat-etudiants').textContent  = users.filter(u => u.role === 'etudiant').length;
  document.getElementById('stat-enseignants').textContent= users.filter(u => ['enseignant','teacher'].includes(u.role)).length;
  document.getElementById('stat-admins').textContent     = users.filter(u => u.role === 'admin').length;
}

// ── RENDER ──
function renderUsers(users) {
  document.getElementById('users-count').textContent = users.length + ' utilisateur' + (users.length > 1 ? 's' : '');
  if (users.length === 0) {
    document.getElementById('users-container').innerHTML =
      '<div class="empty-state"><div class="icon">📭</div><p>Aucun utilisateur trouvé</p></div>';
    return;
  }

  const roleBadge = r => {
    if (r === 'admin')      return '<span class="role-badge admin">⚙️ Admin</span>';
    if (r === 'enseignant' || r === 'teacher') return '<span class="role-badge enseignant">👨‍🏫 Enseignant</span>';
    return '<span class="role-badge etudiant">🎓 Étudiant</span>';
  };

  let rows = users.map(u => {
    const initial = (u.username || u.prenom || '?')[0].toUpperCase();
    const name    = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username;
    const isActive = u.is_active !== false;
    return '<tr>' +
      '<td><div class="user-cell">' +
        '<div class="user-avatar">' + initial + '</div>' +
        '<div><div class="user-name">' + name + '</div><div class="user-email">' + (u.email || '') + '</div></div>' +
      '</div></td>' +
      '<td><code style="font-size:0.8rem;background:var(--gray-soft);padding:3px 8px;border-radius:6px">' + u.username + '</code></td>' +
      '<td>' + roleBadge(u.role) + '</td>' +
      '<td>' + (u.filiere || '<span style="color:var(--gray-text)">--</span>') + '</td>' +
      '<td><span class="status-badge ' + (isActive ? 'active' : 'inactive') + '">' + (isActive ? '✅ Actif' : '❌ Inactif') + '</span></td>' +
      '<td>' + (u.created_at ? new Date(u.created_at).toLocaleDateString('fr-FR') : '--') + '</td>' +
      '<td><div class="action-btns">' +
        '<div class="action-btn" title="Changer le rôle" onclick="openRoleModal(\'' + u.username + '\',\'' + (u.role||'etudiant') + '\')">🔑</div>' +
        '<div class="action-btn danger" title="Supprimer" onclick="openDeleteModal(\'' + u.username + '\')">🗑️</div>' +
      '</div></td>' +
    '</tr>';
  }).join('');

  document.getElementById('users-container').innerHTML =
    '<table><thead><tr><th>Utilisateur</th><th>Username</th><th>Rôle</th><th>Filière</th><th>Statut</th><th>Créé le</th><th>Actions</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

// ── TABS ──
function switchTab(tab, btn) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  filterUsers();
}

// ── FILTER ──
function filterUsers() {
  const q = document.getElementById('search-input').value.toLowerCase();
  let filtered = allUsers;
  if (currentTab === 'etudiant')   filtered = filtered.filter(u => u.role === 'etudiant');
  if (currentTab === 'enseignant') filtered = filtered.filter(u => ['enseignant','teacher'].includes(u.role));
  if (currentTab === 'admin')      filtered = filtered.filter(u => u.role === 'admin');
  if (q) filtered = filtered.filter(u =>
    (u.username || '').toLowerCase().includes(q) ||
    (u.email || '').toLowerCase().includes(q) ||
    (u.first_name || '').toLowerCase().includes(q) ||
    (u.last_name || '').toLowerCase().includes(q)
  );
  renderUsers(filtered);
}

// ── CREATE USER ──
function openCreateModal()  { document.getElementById('create-modal').classList.add('open'); }
function closeCreateModal() {
  document.getElementById('create-modal').classList.remove('open');
  ['create-prenom','create-nom','create-username','create-email','create-password','create-filiere'].forEach(id => {
    document.getElementById(id).value = '';
  });
}

async function createUser() {
  const prenom   = document.getElementById('create-prenom').value.trim();
  const nom      = document.getElementById('create-nom').value.trim();
  const uname    = document.getElementById('create-username').value.trim();
  const email    = document.getElementById('create-email').value.trim();
  const password = document.getElementById('create-password').value;
  const role     = document.getElementById('create-role').value;
  const filiere  = document.getElementById('create-filiere').value.trim();

  if (!prenom || !nom || !uname || !email || !password) {
    showToast('⚠️ Remplissez tous les champs obligatoires', 'error'); return;
  }

  const btn = document.getElementById('create-submit');
  btn.disabled = true; btn.textContent = '⏳ Création...';

  try {
    const res = await fetch('/api/admin/users/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ first_name: prenom, last_name: nom, username: uname, email, password, role })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur');
    }
    showToast('✅ Utilisateur ' + uname + ' créé !', 'success');
    closeCreateModal();
    await loadUsers();
  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '✅ Créer';
  }
}

// ── ROLE MODAL ──
function openRoleModal(uname, currentRole) {
  document.getElementById('role-username').value = uname;
  document.getElementById('role-select').value   = currentRole;
  document.getElementById('role-modal').classList.add('open');
}
function closeRoleModal() { document.getElementById('role-modal').classList.remove('open'); }

async function assignRole() {
  const uname   = document.getElementById('role-username').value;
  const newRole = document.getElementById('role-select').value;
  const btn     = document.getElementById('role-submit');
  btn.disabled = true; btn.textContent = '⏳...';

  try {
    const res = await fetch('/api/admin/roles/assign', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: uname, role: newRole })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur');
    }
    showToast('✅ Rôle de ' + uname + ' changé en ' + newRole + ' !', 'success');
    closeRoleModal();
    await loadUsers();
  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '✅ Confirmer';
  }
}

// ── DELETE ──
function openDeleteModal(uname) {
  deleteTarget = uname;
  document.getElementById('delete-username-display').textContent = uname;
  document.getElementById('delete-modal').classList.add('open');
}
function closeDeleteModal() {
  document.getElementById('delete-modal').classList.remove('open');
  deleteTarget = null;
}

async function confirmDelete() {
  if (!deleteTarget) return;
  const btn = document.getElementById('delete-confirm-btn');
  btn.disabled = true; btn.textContent = '⏳...';

  try {
    const res = await fetch('/api/admin/users/' + deleteTarget, {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur');
    }
    showToast('✅ Utilisateur supprimé !', 'success');
    closeDeleteModal();
    await loadUsers();
  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🗑️ Supprimer';
  }
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

loadUsers();