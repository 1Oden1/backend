/* ═══════════════════════════════════════════════════
   ENT Salé — Enseignant · app.js
   Routes corrigées selon le backend réel
═══════════════════════════════════════════════════ */
'use strict';

const token   = localStorage.getItem('access_token');
const userStr = localStorage.getItem('user');
if (!token || !userStr) location.href = '/login/';
let currentUser = {};
try { currentUser = JSON.parse(userStr); } catch { location.href = '/login/'; }
if (!currentUser.roles?.includes('enseignant') && !currentUser.roles?.includes('admin')) location.href = '/login/';

function api(method, path, body) {
  const opts = { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => { if (r.status === 401) location.href = '/login/'; return r; });
}

const JOURS = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
const FILE_ICONS  = { cours: '📖', td: '✏️', tp: '🔬', examen: '📝', autre: '📄' };
const TAG_CLASSES = { cours: 'tag-cours', td: 'tag-td', tp: 'tag-tp', examen: 'tag-examen', autre: 'tag-autre' };
const PANEL_TITLES = { accueil: 'Tableau de bord', upload: 'Déposer un fichier', mesfichiers: 'Mes fichiers', emploi: 'Mon planning', classement: 'Classements', releve: 'Relevés' };

let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  const name = `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() || currentUser.username || 'Enseignant';
  document.getElementById('userNameEl').textContent  = name;
  document.getElementById('avatarEl').textContent    = name[0].toUpperCase();
  document.getElementById('welcomeName').textContent = name;
  document.getElementById('topbarDate').textContent  = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, el); })
  );
  document.querySelectorAll('.link-more[data-panel]').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, document.querySelector(`.nav-item[data-panel="${el.dataset.panel}"]`)); })
  );
  document.getElementById('logoutBtn').addEventListener('click', doLogout);
  document.getElementById('refreshMesBtn').addEventListener('click', loadMesFichiers);
  document.getElementById('refreshEmploiBtn').addEventListener('click', loadEmploi);
  document.getElementById('loadClassBtn').addEventListener('click', loadClassement);
  document.getElementById('submitReleveBtn').addEventListener('click', demanderReleve);
  document.getElementById('submitUploadBtn').addEventListener('click', doUpload);

  // Dropzone
  const dz = document.getElementById('dropzone');
  dz.addEventListener('click', () => document.getElementById('fileInput').click());
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); });
  document.getElementById('fileInput').addEventListener('change', e => setFile(e.target.files[0]));

  loadAccueil();
});

function switchPanel(id, navEl) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  document.getElementById('topbarTitle').textContent = PANEL_TITLES[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  if (id === 'mesfichiers') loadMesFichiers();
  if (id === 'emploi')      loadEmploi();
}

// ── ACCUEIL ───────────────────────────────────────────────────────────────────
async function loadAccueil() {
  const grid = document.getElementById('accueilGrid');
  grid.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/download/my → fichiers de l'enseignant connecté (endpoint dédié)
    const r = await api('GET', '/api/download/my');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    document.getElementById('nbMesFichiers').textContent = d.total || files.length;
    renderCards(files.slice(0, 4), grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }

  try {
    const r = await api('GET', '/api/calendar/seances');
    if (r.ok) { const d = await r.json(); document.getElementById('nbSeances').textContent = (d || []).length; }
  } catch {}
  try {
    const r = await api('GET', '/api/calendar/filieres');
    if (r.ok) { const d = await r.json(); document.getElementById('nbFilières').textContent = (d || []).length; }
  } catch {}
}

// ── FICHIERS ──────────────────────────────────────────────────────────────────
function renderCards(files, container) {
  if (typeof container === 'string') container = document.getElementById(container);
  if (!files.length) { container.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier</p></div>'; return; }
  container.innerHTML = files.map(f => `
    <div class="file-card">
      <div class="fc-icon">${FILE_ICONS[f.category] || '📄'}</div>
      <span class="fc-tag ${TAG_CLASSES[f.category] || 'tag-autre'}">${f.category || 'autre'}</span>
      <div class="fc-title">${f.title || f.filename}</div>
      <div class="fc-meta">${f.module || ''} · ${f.size_bytes ? Math.round(f.size_bytes / 1024) + ' KB' : ''}</div>
      <div class="fc-actions">
        <button class="btn btn-outline btn-sm" onclick="downloadFile('${f.file_id}')">↓ DL</button>
        <button class="btn btn-danger  btn-sm" onclick="deleteFile('${f.file_id}')">🗑</button>
      </div>
    </div>`).join('');
}

async function loadMesFichiers() {
  const grid = document.getElementById('mesFichiersGrid');
  grid.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/download/my → mes propres fichiers (enseignant connecté)
    const r = await api('GET', '/api/download/my');
    if (!r.ok) throw new Error();
    const d = await r.json();
    renderCards(d.files || [], grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

async function downloadFile(fileId) {
  try {
    // Route CORRECTE : GET /api/download/{file_id} → { download_url }
    const r = await api('GET', `/api/download/${fileId}`);
    if (r.ok) { const d = await r.json(); window.open(d.download_url, '_blank'); }
    else showToast('Lien indisponible', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

async function deleteFile(fileId) {
  if (!confirm('Supprimer ce fichier ?')) return;
  try {
    // DELETE /api/upload/{file_id} (enseignant supprime ses propres fichiers)
    const r = await api('DELETE', `/api/upload/${fileId}`);
    if (r.ok || r.status === 204) { showToast('Fichier supprimé ✓', 'success'); loadMesFichiers(); loadAccueil(); }
    else showToast('Erreur suppression', 'error');
  } catch { showToast('Erreur réseau', 'error'); }
}

// ── UPLOAD ────────────────────────────────────────────────────────────────────
function setFile(f) {
  if (!f) return;
  selectedFile = f;
  document.getElementById('dzSelected').textContent = '📎 ' + f.name;
  document.getElementById('dropzone').classList.remove('drag');
}

async function doUpload() {
  const title    = document.getElementById('fTitle').value.trim();
  const category = document.getElementById('fCategory').value;
  const module   = document.getElementById('fModule').value.trim();
  const desc     = document.getElementById('fDesc').value.trim();
  const isPublic = document.getElementById('fPublic').value === 'true';
  const alertEl  = document.getElementById('uploadAlert');
  alertEl.innerHTML = '';

  if (!selectedFile) { alertEl.innerHTML = '<div class="alert alert-err">⚠ Sélectionnez un fichier.</div>'; return; }
  if (!title)  { alertEl.innerHTML = '<div class="alert alert-err">⚠ Titre obligatoire.</div>'; return; }
  if (!module) { alertEl.innerHTML = '<div class="alert alert-err">⚠ Module obligatoire.</div>'; return; }

  const btn = document.getElementById('submitUploadBtn');
  btn.disabled = true; btn.textContent = '⏳ Envoi…';

  const pw = document.getElementById('progressWrap');
  const pb = document.getElementById('progressBar');
  const pl = document.getElementById('progressLabel');
  pw.style.display = 'block'; pb.style.width = '0';

  let prog = 0;
  const interval = setInterval(() => { prog = Math.min(prog + Math.random() * 15, 90); pb.style.width = prog + '%'; }, 300);

  // POST /api/upload/ — multipart/form-data
  // Champs : file, title, description, category, module, is_public
  const form = new FormData();
  form.append('file',     selectedFile);
  form.append('title',    title);
  form.append('category', category);
  form.append('module',   module);
  form.append('is_public', isPublic);
  if (desc) form.append('description', desc);

  try {
    // Ne PAS mettre Content-Type (browser le met avec le boundary)
    const r = await fetch('/api/upload/', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    clearInterval(interval);
    pb.style.width = '100%';
    if (r.ok || r.status === 201) {
      pl.textContent = '✓ Upload terminé !';
      alertEl.innerHTML = '<div class="alert alert-ok">✓ Fichier déposé avec succès !</div>';
      showToast('Fichier déposé !', 'success');
      setTimeout(() => {
        selectedFile = null;
        document.getElementById('fileInput').value = '';
        document.getElementById('dzSelected').textContent = '';
        document.getElementById('fTitle').value = '';
        document.getElementById('fModule').value = '';
        document.getElementById('fDesc').value = '';
        pw.style.display = 'none';
      }, 2000);
      loadAccueil();
    } else {
      pl.textContent = '✗ Erreur';
      const d = await r.json().catch(() => ({}));
      alertEl.innerHTML = `<div class="alert alert-err">✗ ${d.detail || `Erreur ${r.status}`}</div>`;
    }
  } catch {
    clearInterval(interval);
    alertEl.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>';
  } finally {
    btn.disabled = false; btn.textContent = '📤 Déposer le fichier';
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
    seances.forEach(s => { const j = s.jour || s.day || 'Lundi'; (byDay[j] = byDay[j] || []).push(s); });

    wrap.innerHTML = `<div class="schedule-wrap">${
      JOURS.filter(j => byDay[j]).map(j => `
        <div class="day-block">
          <div class="day-label">${j}</div>
          ${byDay[j].sort((a, b) => (a.heure_debut || '').localeCompare(b.heure_debut || '')).map(s => `
            <div class="seance">
              <div class="seance-time">${s.heure_debut || ''} – ${s.heure_fin || ''}</div>
              <div>
                <div class="seance-mod">${s.element?.label || s.module?.label || s.libelle || '—'}</div>
                <div class="seance-det">📍 ${s.salle?.nom || '—'} · 👥 ${s.filiere?.label || s.filiere?.nom || '—'}</div>
              </div>
            </div>`).join('')}
        </div>`).join('')}
    </div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Planning indisponible</p></div>'; }
}

// ── CLASSEMENTS ───────────────────────────────────────────────────────────────
async function loadClassement() {
  const filiereId  = document.getElementById('clFiliere').value;
  const semestreId = document.getElementById('clSemestre').value;
  if (!filiereId || !semestreId) { showToast('Remplissez les deux champs', 'error'); return; }

  const wrap = document.getElementById('classementContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/notes/enseignant/classements/filiere/{filiere_id}/semestre/{semestre_id}
    // Réponse : ClassementCompletOut { scope_id, scope_nom, type_classement, total, classement: EntreeClassement[] }
    // EntreeClassement : { rang, cne, nom, moyenne }
    const r = await api('GET', `/api/notes/enseignant/classements/filiere/${filiereId}/semestre/${semestreId}`);
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      wrap.innerHTML = `<div class="empty"><div class="e-icon">📊</div><p>${d.detail || 'Classement non disponible'}</p></div>`;
      return;
    }
    const d    = await r.json();
    // d.classement est List[EntreeClassement] avec { rang, cne, nom, moyenne }
    const list = d.classement || [];
    if (!list.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">🏆</div><p>Aucun étudiant</p></div>'; return; }

    wrap.innerHTML = `
      <div style="margin-bottom:1rem;font-size:.85rem;color:var(--muted)">
        ${d.scope_nom || ''} · ${d.total || list.length} étudiants
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Rang</th><th>CNE</th><th>Nom</th><th>Moyenne</th><th>Résultat</th></tr></thead>
        <tbody>${list.map(e => {
          const moy = e.moyenne !== null ? parseFloat(e.moyenne) : null;
          const cls = moy === null ? '' : moy >= 12 ? 'note-ok' : moy >= 10 ? 'note-mid' : 'note-fail';
          return `<tr>
            <td><strong>${e.rang}</strong></td>
            <td>${e.cne || '—'}</td>
            <td>${e.nom || '—'}</td>
            <td class="${cls}">${moy !== null ? moy.toFixed(2) : '—'}</td>
            <td>${moy === null ? '—' : moy >= 10 ? '<span class="note-ok">✓ Admis</span>' : '<span class="note-fail">✗ Ajourné</span>'}</td>
          </tr>`;
        }).join('')}</tbody>
      </table></div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

// ── RELEVÉ ────────────────────────────────────────────────────────────────────
async function demanderReleve() {
  const semId     = parseInt(document.getElementById('rSemestre').value);
  const res       = document.getElementById('releveResult');

  // L'enseignant doit fournir l'ID de l'étudiant cible
  // POST /api/notes/enseignant/demandes-releve
  // Body : { etudiant_id: int, calendar_semestre_id: int }
  if (!semId) { res.innerHTML = '<div class="alert alert-err">Semestre ID requis.</div>'; return; }

  // Afficher un champ pour l'etudiant_id si pas présent
  let etudiantId = parseInt(document.getElementById('rEtudiantId')?.value);
  if (!etudiantId) {
    res.innerHTML = `
      <div class="form-group" style="margin-top:.8rem">
        <label>ID Étudiant cible</label>
        <input type="number" id="rEtudiantId" placeholder="ex: 42" min="1"
          style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif"/>
        <button class="btn btn-gold" onclick="demanderReleve()" style="width:100%;padding:.65rem;margin-top:.5rem">Confirmer</button>
      </div>`;
    return;
  }

  try {
    const r = await api('POST', '/api/notes/enseignant/demandes-releve', {
      etudiant_id:          etudiantId,
      calendar_semestre_id: semId,
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      res.innerHTML = `<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut: <strong>${d.statut}</strong></div>`;
    } else if (r.status === 409) {
      res.innerHTML = '<div class="alert alert-ok">ℹ️ Une demande est déjà en attente.</div>';
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
