/* ═══════════════════════════════════════════════════
   ENT Salé — Étudiant · app.js
   Routes corrigées selon le backend réel
═══════════════════════════════════════════════════ */
'use strict';

const token   = localStorage.getItem('access_token');
const userStr = localStorage.getItem('user');
if (!token || !userStr) location.href = '/login/';
let currentUser = {};
try { currentUser = JSON.parse(userStr); } catch { location.href = '/login/'; }

function api(method, path, body) {
  const opts = { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => { if (r.status === 401) location.href = '/login/'; return r; });
}

const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
const FILE_ICONS  = { cours: '📖', td: '✏️', tp: '🔬', examen: '📝', autre: '📄' };
const TAG_CLASSES = { cours: 'tag-cours', td: 'tag-td', tp: 'tag-tp', examen: 'tag-examen', autre: 'tag-autre' };
const PANEL_TITLES = { accueil: 'Accueil', cours: 'Cours & Fichiers', notes: 'Mes Notes', emploi: 'Emploi du temps', releve: 'Relevé de notes', classement: 'Mon classement' };

document.addEventListener('DOMContentLoaded', () => {
  const name = currentUser.first_name || currentUser.username || 'Étudiant';
  document.getElementById('userNameEl').textContent  = name;
  document.getElementById('avatarEl').textContent    = name[0].toUpperCase();
  document.getElementById('welcomeName').textContent = name;

  const now = new Date();
  const dateStr = now.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  document.getElementById('topbarDate').textContent  = dateStr;
  document.getElementById('welcomeDate').textContent = dateStr;

  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, el); })
  );
  document.querySelectorAll('.link-more[data-panel]').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, document.querySelector(`.nav-item[data-panel="${el.dataset.panel}"]`)); })
  );
  document.querySelectorAll('.filter-btn').forEach(btn =>
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      loadFiles(btn.dataset.cat);
    })
  );
  document.getElementById('logoutBtn').addEventListener('click', doLogout);
  document.getElementById('loadNotesBtn').addEventListener('click', loadNotes);
  document.getElementById('refreshEmploiBtn').addEventListener('click', loadEmploi);
  document.getElementById('submitReleveBtn').addEventListener('click', demanderReleve);

  loadAccueil();
});

function switchPanel(id, navEl) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  document.getElementById('topbarTitle').textContent = PANEL_TITLES[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  if (id === 'cours')      loadFiles('');
  if (id === 'notes')      loadNotes();
  if (id === 'emploi')     loadEmploi();
  if (id === 'classement') showClassementForm();
}

// ── ACCUEIL ───────────────────────────────────────────────────────────────────
async function loadAccueil() {
  const grid = document.getElementById('recentGrid');
  grid.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/download/ → { total, files: [FileMetadata] }
    const r = await api('GET', '/api/download/');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    document.getElementById('nbFiles').textContent = d.total || files.length;
    renderCards(files.slice(0, 6), grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }

  try {
    const r = await api('GET', '/api/calendar/modules');
    if (r.ok) { const d = await r.json(); document.getElementById('nbModules').textContent = (d || []).length; }
  } catch {}
  try {
    const r = await api('GET', '/api/calendar/seances');
    if (r.ok) { const d = await r.json(); document.getElementById('nbSeances').textContent = (d || []).length; }
  } catch {}
}

// ── FICHIERS ──────────────────────────────────────────────────────────────────
async function loadFiles(cat = '') {
  const grid = document.getElementById('allFilesGrid');
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const url = cat ? `/api/download/?category=${cat}` : '/api/download/';
    const r   = await api('GET', url);
    if (!r.ok) throw new Error();
    const d = await r.json();
    renderCards(d.files || [], grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Impossible de charger les fichiers</p></div>'; }
}

function renderCards(files, container) {
  if (typeof container === 'string') container = document.getElementById(container);
  if (!files.length) { container.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier disponible</p></div>'; return; }
  container.innerHTML = files.map(f => `
    <div class="file-card">
      <div class="fc-icon">${FILE_ICONS[f.category] || '📄'}</div>
      <span class="fc-tag ${TAG_CLASSES[f.category] || 'tag-autre'}">${f.category || 'autre'}</span>
      <div class="fc-title">${f.title || f.filename}</div>
      <div class="fc-meta">${f.module || ''} · ${f.owner_name || ''}</div>
      <button class="btn btn-gold" style="width:100%;font-size:.74rem;padding:.48rem"
        onclick="downloadFile('${f.file_id}')">↓ Télécharger</button>
    </div>`).join('');
}

async function downloadFile(fileId) {
  try {
    // Route CORRECTE : GET /api/download/{file_id} → { download_url }
    const r = await api('GET', `/api/download/${fileId}`);
    if (r.ok) { const d = await r.json(); window.open(d.download_url, '_blank'); }
    else showToast('Lien indisponible', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

// ── NOTES ─────────────────────────────────────────────────────────────────────
async function loadNotes() {
  const sem  = document.getElementById('semSelect').value;
  const wrap = document.getElementById('notesContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/notes/etudiant/notes/{semestre_id}
    // Retourne : SemestreNotesOut { calendar_semestre_id, moyenne_semestre, notes: [ElementNoteOut] }
    // ElementNoteOut : { calendar_element_id, note }
    const r = await api('GET', `/api/notes/etudiant/notes/${sem}`);
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      wrap.innerHTML = `<div class="empty"><div class="e-icon">📊</div><p>${d.detail || 'Notes non disponibles pour ce semestre.'}</p></div>`;
      return;
    }
    const d   = await r.json();
    const moy = d.moyenne_semestre ?? null;
    // d.notes est la liste ElementNoteOut avec calendar_element_id et note
    const elts = d.notes || [];

    let html = '';
    if (moy !== null) {
      const moyNum = parseFloat(moy);
      const cls = moyNum >= 12 ? 'note-ok' : moyNum >= 10 ? 'note-mid' : 'note-fail';
      html += `<div class="moy-card">
        <div>
          <div class="moy-label">Moyenne générale — Semestre ${sem}</div>
          <div class="moy-val ${cls}">${moyNum.toFixed(2)} / 20</div>
        </div>
        <div class="moy-icon">${moyNum >= 12 ? '🏆' : moyNum >= 10 ? '📈' : '📉'}</div>
      </div>`;
    }

    if (elts.length) {
      html += `<div class="table-wrap"><table>
        <thead><tr><th>Élément (ID)</th><th>Note / 20</th><th>Résultat</th></tr></thead>
        <tbody>${elts.map(e => {
          const n = e.note !== null && e.note !== undefined ? parseFloat(e.note) : null;
          const cls = n === null ? '' : n >= 12 ? 'note-ok' : n >= 10 ? 'note-mid' : 'note-fail';
          return `<tr>
            <td>Élément #${e.calendar_element_id}</td>
            <td><strong class="${cls}">${n !== null ? n.toFixed(2) : '—'}</strong></td>
            <td>${n === null ? '—' : n >= 10 ? '<span class="note-ok">✓ Validé</span>' : '<span class="note-fail">✗ Non validé</span>'}</td>
          </tr>`;
        }).join('')}</tbody>
      </table></div>`;
    } else {
      html += '<div class="empty"><div class="e-icon">📊</div><p>Aucune note enregistrée.</p></div>';
    }
    wrap.innerHTML = html;
  } catch {
    wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur lors du chargement des notes</p></div>';
  }
}

// ── EMPLOI DU TEMPS ───────────────────────────────────────────────────────────
async function loadEmploi() {
  const wrap = document.getElementById('emploiContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/calendar/seances → List[SeanceRead]
    const r = await api('GET', '/api/calendar/seances');
    if (!r.ok) throw new Error();
    const seances = await r.json();
    document.getElementById('nbSeances').textContent = seances.length;
    if (!seances.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">📅</div><p>Aucune séance planifiée</p></div>'; return; }

    const byDay = {};
    seances.forEach(s => {
      const j = s.jour || s.day || 'Lundi';
      (byDay[j] = byDay[j] || []).push(s);
    });

    wrap.innerHTML = `<div class="schedule-wrap">${
      JOURS.filter(j => byDay[j]).map(j => `
        <div class="day-block">
          <div class="day-label">${j}</div>
          ${byDay[j].sort((a, b) => (a.heure_debut || '').localeCompare(b.heure_debut || '')).map(s => `
            <div class="seance">
              <div class="seance-time">${s.heure_debut || ''} – ${s.heure_fin || ''}</div>
              <div>
                <div class="seance-mod">${s.element?.label || s.module?.label || s.libelle || '—'}</div>
                <div class="seance-det">📍 ${s.salle?.nom || '—'} · 👤 ${(s.enseignant?.prenom || '') + ' ' + (s.enseignant?.nom || '')}</div>
              </div>
            </div>`).join('')}
        </div>`).join('')}
    </div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Emploi du temps indisponible</p></div>'; }
}

// ── CLASSEMENT ────────────────────────────────────────────────────────────────
// Flux correct :
// 1. POST /api/notes/etudiant/demandes-classement { calendar_semestre_id, type_classement }
//    → { id, statut, ... }
// 2. GET /api/notes/etudiant/classements/{demande_id}
//    → MonClassementOut { mon_rang, total, ma_moyenne, scope_nom, ... }

function showClassementForm() {
  const wrap = document.getElementById('classementContent');
  wrap.innerHTML = `
    <div class="form-card" style="max-width:420px">
      <p class="form-card-desc">Demandez votre classement pour un semestre donné. L'admin doit valider la demande.</p>
      <div class="form-group">
        <label>Semestre (ID calendrier)</label>
        <input type="number" id="clSemId" placeholder="ex: 1" min="1" style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif"/>
      </div>
      <div class="form-group">
        <label>Type</label>
        <select id="clType" style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif">
          <option value="filiere">Filière</option>
          <option value="departement">Département</option>
        </select>
      </div>
      <button class="btn btn-gold" id="submitClassBtn" style="width:100%;padding:.72rem;margin-top:.5rem">Envoyer la demande</button>
      <div id="clResult" style="margin-top:1rem"></div>
    </div>`;
  document.getElementById('submitClassBtn').addEventListener('click', demanderClassement);
}

async function demanderClassement() {
  const semId = parseInt(document.getElementById('clSemId').value);
  const type  = document.getElementById('clType').value;
  const res   = document.getElementById('clResult');
  if (!semId) { res.innerHTML = '<div class="alert alert-err">Semestre ID requis.</div>'; return; }
  try {
    // POST /api/notes/etudiant/demandes-classement
    // Body : { calendar_semestre_id: int, type_classement: "filiere"|"departement" }
    const r = await api('POST', '/api/notes/etudiant/demandes-classement', {
      calendar_semestre_id: semId,
      type_classement: type,
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      res.innerHTML = `<div class="alert alert-ok">
        ✓ Demande créée (ID: ${d.id}) · Statut: <strong>${d.statut}</strong><br>
        <small>Une fois validée par l'admin, vous pourrez voir votre classement.</small>
      </div>`;
      // Essayer de récupérer le classement si déjà approuvé
      if (d.statut === 'approuve') fetchClassementResult(d.id, res);
    } else if (r.status === 409) {
      // Demande déjà en attente → récupérer la demande existante
      const d = await r.json().catch(() => ({}));
      res.innerHTML = `<div class="alert alert-ok">ℹ️ ${d.detail || 'Demande déjà en cours.'}</div>`;
    } else {
      const d = await r.json().catch(() => ({}));
      res.innerHTML = `<div class="alert alert-err">✗ ${d.detail || `Erreur ${r.status}`}</div>`;
    }
  } catch { res.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>'; }
}

async function fetchClassementResult(demandeId, resEl) {
  try {
    // GET /api/notes/etudiant/classements/{demande_id}
    // Réponse : MonClassementOut { mon_rang, total, ma_moyenne, scope_nom, type_classement }
    const r = await api('GET', `/api/notes/etudiant/classements/${demandeId}`);
    if (r.ok) {
      const d = await r.json();
      resEl.innerHTML = `<div class="classement-card">
        <div class="trophy">🏆</div>
        <div class="classement-rang">Rang ${d.mon_rang ?? '—'}</div>
        <div class="classement-sub">sur ${d.total ?? '—'} étudiants · ${d.scope_nom || ''}</div>
        <div class="classement-moy">Moyenne : ${d.ma_moyenne !== null ? parseFloat(d.ma_moyenne).toFixed(2) : '—'} / 20</div>
      </div>`;
    }
  } catch {}
}

// ── RELEVÉ ────────────────────────────────────────────────────────────────────
async function demanderReleve() {
  const sem = document.getElementById('releveSelect').value;
  const res = document.getElementById('releveResult');
  try {
    // POST /api/notes/etudiant/demandes-releve
    // Body : { calendar_semestre_id: int }  ← PAS semestre_id
    const r = await api('POST', '/api/notes/etudiant/demandes-releve', {
      calendar_semestre_id: parseInt(sem),
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      res.innerHTML = `<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut: <strong>${d.statut}</strong></div>`;
    } else if (r.status === 409) {
      res.innerHTML = '<div class="alert alert-ok">ℹ️ Une demande est déjà en attente pour ce semestre.</div>';
    } else {
      const d = await r.json().catch(() => ({}));
      res.innerHTML = `<div class="alert alert-err">✗ ${d.detail || `Erreur ${r.status}`}</div>`;
    }
  } catch { res.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>'; }
}

// ── Utils ─────────────────────────────────────────────────────────────────────
async function doLogout() {
  const rt = localStorage.getItem('refresh_token');
  if (rt) { try { await api('POST', '/api/auth/logout', { refresh_token: rt }); } catch {} }
  localStorage.clear(); location.href = '/login/';
}

let _toastTimer;
function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast show ' + type;
  clearTimeout(_toastTimer); _toastTimer = setTimeout(() => { t.className = 'toast'; }, 3200);
}
