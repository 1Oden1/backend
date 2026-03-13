/* ═══════════════════════════════════════════════════════════════
   ENT Salé — Enseignant · app.js  (routes vérifiées sur backend réel)
═══════════════════════════════════════════════════════════════ */
'use strict';

const token   = localStorage.getItem('access_token');
const userStr = localStorage.getItem('user');
if (!token || !userStr) { localStorage.clear(); location.href = '/login/'; }
let currentUser = {};
try { currentUser = JSON.parse(userStr); } catch { location.href = '/login/'; }
if (!currentUser.roles?.includes('enseignant') && !currentUser.roles?.includes('admin'))
  location.href = '/login/';

function api(method, path, body) {
  const opts = { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => { if (r.status === 401) { localStorage.clear(); location.href = '/login/'; } return r; });
}

const JOURS = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
const FILE_ICONS  = { cours:'📖', td:'✏️', tp:'🔬', examen:'📝', autre:'📄' };
const TAG_CLASSES = { cours:'tag-cours', td:'tag-td', tp:'tag-tp', examen:'tag-examen', autre:'tag-autre' };
const PANEL_TITLES = { accueil:'Tableau de bord', upload:'Déposer un fichier',
                       mesfichiers:'Mes fichiers', emploi:'Mon planning',
                       classement:'Classements filière', releve:'Relevés' };
let selectedFile = null;

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── INIT ─────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const name = `${currentUser.first_name||''} ${currentUser.last_name||''}`.trim() || currentUser.username || 'Enseignant';
  document.getElementById('userNameEl').textContent  = name;
  document.getElementById('avatarEl').textContent    = name[0].toUpperCase();
  document.getElementById('welcomeName').textContent = name;
  document.getElementById('topbarDate').textContent  =
    new Date().toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});

  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, el); }));
  document.querySelectorAll('.link-more[data-panel]').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault();
      switchPanel(el.dataset.panel, document.querySelector(`.nav-item[data-panel="${el.dataset.panel}"]`)); }));

  document.getElementById('logoutBtn').addEventListener('click', doLogout);
  document.getElementById('refreshMesBtn').addEventListener('click', loadMesFichiers);
  document.getElementById('refreshEmploiBtn').addEventListener('click', () => loadEmploi(true));
  document.getElementById('loadClassBtn').addEventListener('click', loadClassement);
  document.getElementById('submitReleveBtn').addEventListener('click', demanderReleve);
  document.getElementById('submitUploadBtn').addEventListener('click', doUpload);

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
  const t = document.getElementById('panel-' + id);
  if (t) t.classList.add('active');
  document.getElementById('topbarTitle').textContent = PANEL_TITLES[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  if (id === 'mesfichiers') loadMesFichiers();
  if (id === 'emploi')      initEmploiPanel();
}

/* ── ACCUEIL ──────────────────────────────────────────────────────── */
async function loadAccueil() {
  const grid = document.getElementById('accueilGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/download/my → fichiers déposés par cet enseignant
    const r = await api('GET', '/api/download/my');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    const nbEl = document.getElementById('nbMesFichiers');
    if (nbEl) nbEl.textContent = d.total || files.length;
    renderCards(files.slice(0, 4), grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

/* ── MES FICHIERS ─────────────────────────────────────────────────── */
async function loadMesFichiers() {
  const grid = document.getElementById('mesFichiersGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/download/my');
    if (!r.ok) throw new Error();
    const d = await r.json();
    renderCards(d.files || [], grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

function renderCards(files, container) {
  if (typeof container === 'string') container = document.getElementById(container);
  if (!container) return;
  if (!files.length) { container.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier</p></div>'; return; }
  container.innerHTML = files.map(f => `
    <div class="file-card">
      <div class="fc-icon">${FILE_ICONS[f.category]||'📄'}</div>
      <span class="fc-tag ${TAG_CLASSES[f.category]||'tag-autre'}">${f.category||'autre'}</span>
      <div class="fc-title">${escHtml(f.title||f.filename)}</div>
      <div class="fc-meta">${escHtml(f.module||'')} · ${f.size_bytes?Math.round(f.size_bytes/1024)+' KB':''}</div>
      <div class="fc-actions">
        <button class="btn btn-outline btn-sm" onclick="downloadFile('${f.file_id}')">↓ DL</button>
        <button class="btn btn-danger  btn-sm" onclick="deleteFile('${f.file_id}')">🗑</button>
      </div>
    </div>`).join('');
}

async function downloadFile(fileId) {
  try {
    const r = await api('GET', `/api/download/${fileId}`);
    if (r.ok) { const d = await r.json(); window.open(d.download_url,'_blank'); }
    else showToast('Lien indisponible','error');
  } catch { showToast('Erreur réseau','error'); }
}

async function deleteFile(fileId) {
  if (!confirm('Supprimer ce fichier ?')) return;
  try {
    const r = await api('DELETE', `/api/upload/${fileId}`);
    if (r.ok || r.status === 204) { showToast('Fichier supprimé ✓','success'); loadMesFichiers(); loadAccueil(); }
    else showToast('Erreur suppression','error');
  } catch { showToast('Erreur réseau','error'); }
}

/* ── UPLOAD ───────────────────────────────────────────────────────── */
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
  if (!title)        { alertEl.innerHTML = '<div class="alert alert-err">⚠ Titre obligatoire.</div>'; return; }
  if (!module)       { alertEl.innerHTML = '<div class="alert alert-err">⚠ Module obligatoire.</div>'; return; }

  const btn = document.getElementById('submitUploadBtn');
  btn.disabled = true; btn.textContent = '⏳ Envoi…';

  const pw = document.getElementById('progressWrap');
  const pb = document.getElementById('progressBar');
  const pl = document.getElementById('progressLabel');
  pw.style.display = 'block'; pb.style.width = '0';

  let prog = 0;
  const iv = setInterval(() => { prog = Math.min(prog + Math.random() * 15, 90); pb.style.width = prog + '%'; }, 300);

  const form = new FormData();
  form.append('file',      selectedFile);
  form.append('title',     title);
  form.append('category',  category);
  form.append('module',    module);
  form.append('is_public', isPublic);
  if (desc) form.append('description', desc);

  try {
    // POST /api/upload/ — multipart/form-data (pas de Content-Type explicite)
    const r = await fetch('/api/upload/', {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    clearInterval(iv); pb.style.width = '100%';
    if (r.ok || r.status === 201) {
      pl.textContent = '✓ Upload terminé !';
      alertEl.innerHTML = '<div class="alert alert-ok">✓ Fichier déposé avec succès !</div>';
      showToast('Fichier déposé !','success');
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
      const d = await r.json().catch(()=>({}));
      alertEl.innerHTML = `<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch {
    clearInterval(iv);
    alertEl.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>';
  } finally {
    btn.disabled = false; btn.textContent = '📤 Déposer le fichier';
  }
}

/* ── EMPLOI DU TEMPS ─ Cascade → GET /api/calendar/emploi-du-temps/{id} ── */
// SeanceRead : { jour, heure_debut, heure_fin, element_module(str), type_seance, module(str),
//               enseignant_nom, enseignant_prenom, salle(str) }
// On filtre les séances de l'enseignant connecté par nom/prénom

function initEmploiPanel() {
  const wrap = document.getElementById('emploiContent');
  if (!wrap || document.getElementById('emplDeptSel')) return;
  wrap.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end;margin-bottom:1.2rem;
                padding:1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:10px">
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Département</label>
        <select id="emplDeptSel" onchange="emplOnDept()"
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Filière</label>
        <select id="emplFiliereSel" onchange="emplOnFiliere()" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Semestre</label>
        <select id="emplSemSel" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div style="display:flex;flex-direction:column;gap:.3rem">
        <label style="font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted)">Afficher</label>
        <select id="emplMode"
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem">
          <option value="mine">Mes séances uniquement</option>
          <option value="all">Toutes les séances</option>
        </select>
      </div>
      <button class="btn btn-gold" onclick="loadEmploi(false)" style="padding:.45rem 1.1rem;height:36px">Afficher</button>
    </div>
    <div id="emploiGrid"></div>`;

  api('GET','/api/calendar/departements').then(r=>r.ok?r.json():[]).then(list=>{
    const sel=document.getElementById('emplDeptSel');
    (list||[]).forEach(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=d.nom;sel.appendChild(o);});
  });
}

window.emplOnDept = function(){
  const dId=parseInt(document.getElementById('emplDeptSel').value);
  const fSel=document.getElementById('emplFiliereSel'),sSel=document.getElementById('emplSemSel');
  fSel.innerHTML='<option value="">— Choisir —</option>';sSel.innerHTML='<option value="">— Choisir —</option>';
  fSel.disabled=true;sSel.disabled=true;
  if(isNaN(dId)) return;
  api('GET',`/api/calendar/departements/${dId}/filieres`).then(r=>r.ok?r.json():[]).then(list=>{
    fSel.disabled=false;
    (list||[]).forEach(f=>{const o=document.createElement('option');o.value=f.id;o.textContent=f.nom;fSel.appendChild(o);});
  });
};
window.emplOnFiliere = function(){
  const fId=parseInt(document.getElementById('emplFiliereSel').value);
  const sSel=document.getElementById('emplSemSel');
  sSel.innerHTML='<option value="">— Choisir —</option>';sSel.disabled=true;
  if(isNaN(fId)) return;
  api('GET',`/api/calendar/filieres/${fId}/semestres`).then(r=>r.ok?r.json():[]).then(list=>{
    sSel.disabled=false;
    (list||[]).forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.nom;sSel.appendChild(o);});
    if((list||[]).length===1) sSel.value=list[0].id;
  });
};

window.loadEmploi = async function(forceRefresh){
  const semId=parseInt(document.getElementById('emplSemSel')?.value);
  const mode=document.getElementById('emplMode')?.value||'mine';
  const grid=document.getElementById('emploiGrid');
  if(!grid) return;
  if(isNaN(semId)){grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Sélectionnez un semestre.</p></div>';return;}
  grid.innerHTML='<div class="loader"></div>';
  try {
    const r=await api('GET',`/api/calendar/emploi-du-temps/${semId}`);
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      grid.innerHTML=`<div class="empty"><div class="e-icon">📅</div><p>${escHtml(d.detail||'Planning non disponible.')}</p></div>`;
      return;
    }
    const data=await r.json();
    let seances=data.seances||[];

    // Filtrer par nom de l'enseignant connecté si mode "mine"
    if(mode==='mine'){
      const myLastName=(currentUser.last_name||'').toLowerCase().trim();
      const myFirstName=(currentUser.first_name||'').toLowerCase().trim();
      if(myLastName||myFirstName){
        const filtered=seances.filter(s=>
          (s.enseignant_nom||'').toLowerCase().trim()===myLastName &&
          (s.enseignant_prenom||'').toLowerCase().trim()===myFirstName
        );
        // Si filtre trop restrictif (prénom/nom ne matche pas exactement), montrer tout avec avertissement
        if(filtered.length===0 && seances.length>0){
          grid.innerHTML=`<div class="empty" style="margin-bottom:1rem"><div class="e-icon">ℹ️</div>
            <p>Aucune séance trouvée pour votre nom (<strong>${escHtml(currentUser.first_name||'')} ${escHtml(currentUser.last_name||'')}</strong>).<br>
            Vérifiez que votre profil enseignant est bien enregistré dans le calendrier, ou sélectionnez "Toutes les séances".</p>
          </div>`;
          return;
        }
        seances=filtered;
      }
    }

    if(!seances.length){
      grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Aucune séance pour ce semestre.</p></div>';
      return;
    }

    let html=`<div style="padding:.6rem 1rem;background:var(--cream);border:1.5px solid var(--border);
      border-radius:8px;margin-bottom:1rem;font-size:.83rem;color:var(--muted)">
      🏛️ ${escHtml(data.departement||'')} &nbsp;·&nbsp; 🎓 ${escHtml(data.filiere||'')}
      &nbsp;·&nbsp; 📆 ${escHtml(data.annee||'')} &nbsp;·&nbsp; 📘 ${escHtml(data.semestre||'')}
      &nbsp;·&nbsp; ${seances.length} séance(s)
    </div>`;

    const byDay={};
    seances.forEach(s=>{const j=s.jour||'Lundi';(byDay[j]=byDay[j]||[]).push(s);});
    html+='<div class="schedule-wrap">';
    JOURS.filter(j=>byDay[j]).forEach(j=>{
      const sorted=byDay[j].sort((a,b)=>(a.heure_debut||'').localeCompare(b.heure_debut||''));
      html+=`<div class="day-block"><div class="day-label">${j}</div>`;
      sorted.forEach(s=>{
        const col=s.type_seance==='Cours'?'#1e4fa3':s.type_seance==='TD'?'#b45309':'#166534';
        html+=`<div class="seance">
          <div class="seance-time">${escHtml(s.heure_debut)} – ${escHtml(s.heure_fin)}</div>
          <div style="flex:1">
            <div class="seance-mod">${escHtml(s.element_module||s.module||'—')}</div>
            <div class="seance-det">
              <span style="background:${col};color:#fff;font-size:.68rem;padding:.1rem .45rem;border-radius:4px;margin-right:.4rem">${escHtml(s.type_seance||'')}</span>
              📍 ${escHtml(s.salle||'—')} &nbsp;·&nbsp; 🎓 ${escHtml(data.filiere||'—')}
            </div>
          </div>
        </div>`;
      });
      html+='</div>';
    });
    html+='</div>';
    grid.innerHTML=html;
  } catch(err){
    grid.innerHTML=`<div class="empty"><div class="e-icon">⚠️</div><p>Erreur : ${escHtml(err.message)}</p></div>`;
  }
};

/* ── CLASSEMENTS FILIÈRE ──────────────────────────────────────────── */
async function loadClassement() {
  const filiereId  = document.getElementById('clFiliere').value;
  const semestreId = document.getElementById('clSemestre').value;
  if (!filiereId || !semestreId) { showToast('Remplissez les deux champs','error'); return; }
  const wrap = document.getElementById('classementContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // GET /api/notes/enseignant/classements/filiere/{filiere_id}/semestre/{semestre_id}
    // → ClassementCompletOut { scope_nom, total, classement:[{rang, cne, nom, moyenne}] }
    const r = await api('GET', `/api/notes/enseignant/classements/filiere/${filiereId}/semestre/${semestreId}`);
    if (!r.ok) {
      const d = await r.json().catch(()=>({}));
      wrap.innerHTML = `<div class="empty"><div class="e-icon">📊</div><p>${escHtml(d.detail||'Classement non disponible')}</p></div>`;
      return;
    }
    const d    = await r.json();
    const list = d.classement || [];
    if (!list.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">🏆</div><p>Aucun étudiant</p></div>'; return; }
    wrap.innerHTML = `
      <div style="margin-bottom:1rem;font-size:.85rem;color:var(--muted)">${escHtml(d.scope_nom||'')} · ${d.total||list.length} étudiants</div>
      <div class="table-wrap"><table>
        <thead><tr><th>Rang</th><th>CNE</th><th>Nom</th><th>Moyenne</th><th>Résultat</th></tr></thead>
        <tbody>${list.map(e => {
          const moy = e.moyenne != null ? parseFloat(e.moyenne) : null;
          const cls = moy === null ? '' : moy >= 12 ? 'note-ok' : moy >= 10 ? 'note-mid' : 'note-fail';
          return `<tr>
            <td><strong>${e.rang}</strong></td>
            <td>${escHtml(e.cne||'—')}</td>
            <td>${escHtml(e.nom||'—')}</td>
            <td class="${cls}">${moy!==null?moy.toFixed(2):'—'}</td>
            <td>${moy===null?'—':moy>=10?'<span class="note-ok">✓ Admis</span>':'<span class="note-fail">✗ Ajourné</span>'}</td>
          </tr>`;
        }).join('')}</tbody>
      </table></div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

/* ── RELEVÉ ───────────────────────────────────────────────────────── */
async function demanderReleve() {
  const semId    = parseInt(document.getElementById('rSemestre').value);
  const res      = document.getElementById('releveResult');
  let etudiantId = parseInt(document.getElementById('rEtudiantId')?.value);
  if (!semId) { res.innerHTML = '<div class="alert alert-err">Semestre ID requis.</div>'; return; }
  if (!etudiantId) {
    res.innerHTML = `
      <div class="form-group" style="margin-top:.8rem">
        <label>ID Étudiant</label>
        <input type="number" id="rEtudiantId" placeholder="ex: 42" min="1"
          style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif"/>
        <button class="btn btn-gold" onclick="demanderReleve()" style="width:100%;padding:.65rem;margin-top:.5rem">Confirmer</button>
      </div>`;
    return;
  }
  try {
    // POST /api/notes/enseignant/demandes-releve
    // Body : { etudiant_id, calendar_semestre_id }
    const r = await api('POST', '/api/notes/enseignant/demandes-releve', {
      etudiant_id: etudiantId, calendar_semestre_id: semId,
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      res.innerHTML = `<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong></div>`;
    } else if (r.status === 409) {
      res.innerHTML = '<div class="alert alert-ok">ℹ️ Une demande est déjà en attente.</div>';
    } else {
      const d = await r.json().catch(()=>({}));
      res.innerHTML = `<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch { res.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>'; }
}

/* ── UTILS ────────────────────────────────────────────────────────── */
async function doLogout() {
  const rt = localStorage.getItem('refresh_token');
  if (rt) { try { await api('POST', '/api/auth/logout', { refresh_token: rt }); } catch {} }
  localStorage.clear(); location.href = '/login/';
}
let _toastTimer;
function showToast(msg, type='') {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg; t.className = 'toast show ' + type;
  clearTimeout(_toastTimer); _toastTimer = setTimeout(() => { t.className = 'toast'; }, 3200);
}
