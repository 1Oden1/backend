// ── notes.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';

document.getElementById('user-name').textContent = username || 'Utilisateur';
const roleLabels = { admin: '⚙️ Administrateur', enseignant: '👨‍🏫 Enseignant', teacher: '👨‍🏫 Enseignant', etudiant: '🎓 Étudiant' };
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';

if (['enseignant', 'teacher', 'admin'].includes(role)) {
  document.querySelectorAll('.enseignant-only').forEach(el => el.style.display = 'flex');
}
if (role === 'admin') {
  document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');
}

let allNotes = [];

// ── LOAD NOTES ──
async function loadNotes() {
  try {
    const endpoint = ['enseignant','teacher','admin'].includes(role)
      ? '/api/notes/notes/'
      : '/api/notes/notes/mes-notes';

    const res  = await fetch(endpoint, { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await res.json();
    allNotes   = data;

    updateStats(data);
    renderNotes(data);
  } catch(e) {
    document.getElementById('notes-container').innerHTML =
      '<div class="empty-state"><div class="icon">⚠️</div><h3>Erreur de chargement</h3><p>Impossible de récupérer les notes.</p></div>';
  }
}

// ── UPDATE STATS ──
function updateStats(notes) {
  if (notes.length === 0) {
    document.getElementById('moyenne-score').innerHTML = '--<span>/20</span>';
    document.getElementById('banner-subtitle').textContent = 'Aucune note enregistrée';
    document.getElementById('stat-total').textContent = '0';
    document.getElementById('stat-max').textContent   = '--';
    document.getElementById('stat-avg').textContent   = '--';
    document.getElementById('stat-min').textContent   = '--';
    return;
  }

  const values  = notes.map(n => parseFloat(n.note));
  const avg     = values.reduce((a, b) => a + b, 0) / values.length;
  const max     = Math.max(...values);
  const min     = Math.min(...values);

  document.getElementById('stat-total').textContent = notes.length;
  document.getElementById('stat-max').textContent   = max.toFixed(2) + '/20';
  document.getElementById('stat-avg').textContent   = avg.toFixed(2) + '/20';
  document.getElementById('stat-min').textContent   = min.toFixed(2) + '/20';
  document.getElementById('moyenne-score').innerHTML = avg.toFixed(2) + '<span>/20</span>';
  document.getElementById('banner-subtitle').textContent = notes.length + ' note' + (notes.length > 1 ? 's' : '') + ' enregistrée' + (notes.length > 1 ? 's' : '');

  // Mention
  const mentionEl = document.getElementById('mention-badge');
  let mention = '', cls = '';
  if (avg >= 16)      { mention = '🏆 Très Bien'; cls = 'tres-bien'; }
  else if (avg >= 14) { mention = '⭐ Bien'; cls = 'bien'; }
  else if (avg >= 12) { mention = '✅ Assez Bien'; cls = 'assez-bien'; }
  else if (avg >= 10) { mention = '📋 Passable'; cls = 'passable'; }
  else                { mention = '❌ Insuffisant'; cls = 'insuffisant'; }
  mentionEl.textContent = mention;
  mentionEl.className   = 'mention-badge ' + cls;
  mentionEl.style.display = 'block';
}

// ── RENDER NOTES ──
function renderNotes(notes) {
  const container = document.getElementById('notes-container');
  document.getElementById('notes-count').textContent = notes.length + ' note' + (notes.length > 1 ? 's' : '');

  if (notes.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><h3>Aucune note disponible</h3><p>Aucune note pour cette sélection.</p></div>';
    return;
  }

  let rows = '';
  notes.forEach(n => {
    const val  = parseFloat(n.note);
    const cls  = val >= 14 ? 'high' : val >= 10 ? 'mid' : 'low';
    const badgeCls = val >= 16 ? 'tres-bien' : val >= 14 ? 'bien' : val >= 12 ? 'assez-bien' : val >= 10 ? 'passable' : 'insuffisant';
    const badgeTxt = val >= 16 ? 'Très Bien' : val >= 14 ? 'Bien' : val >= 12 ? 'Assez Bien' : val >= 10 ? 'Passable' : 'Insuffisant';
    const typeIcons = { examen: '📝', controle: '✏️', tp: '🔬', projet: '💻' };
    rows += '<tr>' +
      '<td>' + (n.matiere || '--') + '</td>' +
      '<td>' + (typeIcons[n.type] || '📄') + ' ' + (n.type || '--') + '</td>' +
      '<td>' + (n.semestre || '--') + '</td>' +
      ((['enseignant','teacher','admin'].includes(role)) ? '<td>' + (n.etudiant_username || '--') + '</td>' : '') +
      '<td><span class="note-value ' + cls + '">' + val.toFixed(2) + '</span><span style="color:var(--gray-text);font-size:0.75rem">/20</span></td>' +
      '<td>' + (n.coefficient || 1) + '</td>' +
      '<td><span class="note-badge ' + badgeCls + '">' + badgeTxt + '</span></td>' +
      '<td style="font-size:0.75rem;color:var(--gray-text)">' + (n.created_at ? new Date(n.created_at).toLocaleDateString('fr-FR') : '--') + '</td>' +
    '</tr>';
  });

  const enseignantCol = ['enseignant','teacher','admin'].includes(role) ? '<th>Étudiant</th>' : '';
  container.innerHTML = '<table>' +
    '<thead><tr><th>Matière</th><th>Type</th><th>Semestre</th>' + enseignantCol + '<th>Note</th><th>Coef.</th><th>Mention</th><th>Date</th></tr></thead>' +
    '<tbody>' + rows + '</tbody>' +
    '</table>';
}

// ── FILTER ──
function filterNotes() {
  const q        = document.getElementById('search-input').value.toLowerCase();
  const type     = document.getElementById('filter-type').value;
  const semestre = document.getElementById('filter-semestre').value;

  const filtered = allNotes.filter(n => {
    const matchQ   = !q        || (n.matiere || '').toLowerCase().includes(q);
    const matchT   = !type     || n.type === type;
    const matchS   = !semestre || n.semestre === semestre;
    return matchQ && matchT && matchS;
  });

  updateStats(filtered);
  renderNotes(filtered);
}

// ── ADD NOTE ──
function openModal()  { document.getElementById('note-modal').classList.add('open'); }
function closeModal() {
  document.getElementById('note-modal').classList.remove('open');
  document.getElementById('note-etudiant').value = '';
  document.getElementById('note-matiere').value  = '';
  document.getElementById('note-valeur').value   = '';
  document.getElementById('note-coef').value     = '1';
}

async function addNote() {
  const etudiant = document.getElementById('note-etudiant').value.trim();
  const matiere  = document.getElementById('note-matiere').value.trim();
  const valeur   = document.getElementById('note-valeur').value;
  const coef     = document.getElementById('note-coef').value || 1;
  const type     = document.getElementById('note-type').value;
  const semestre = document.getElementById('note-semestre').value;

  if (!etudiant || !matiere || !valeur) {
    showToast('⚠️ Remplissez tous les champs obligatoires', 'error');
    return;
  }
  if (parseFloat(valeur) < 0 || parseFloat(valeur) > 20) {
    showToast('⚠️ La note doit être entre 0 et 20', 'error');
    return;
  }

  const btn = document.getElementById('note-submit');
  btn.disabled = true; btn.textContent = '⏳ Enregistrement...';

  try {
    const res = await fetch('/api/notes/notes/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        etudiant_username: etudiant,
        matiere:           matiere,
        note:              parseFloat(valeur),
        coefficient:       parseInt(coef),
        type:              type,
        semestre:          semestre
      })
    });

    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Erreur');
    }

    showToast('✅ Note ajoutée avec succès !', 'success');
    closeModal();
    await loadNotes();

  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur lors de l\'ajout'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '✅ Enregistrer';
  }
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

loadNotes();