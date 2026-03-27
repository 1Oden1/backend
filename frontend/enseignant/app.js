/* ═══════════════════════════════════════════════════════════════
   ENT Salé — Enseignant · app.js
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
const PANEL_TITLES = {
  accueil:'Tableau de bord', upload:'Déposer un fichier',
  mesfichiers:'Mes fichiers', emploi:'Mon planning',
  classement:'Classements filière', releve:'Relevés',
  notifs:'Notifications', chat:'Messagerie'
};
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
  document.getElementById('refreshMesBtn')?.addEventListener('click', loadMesFichiers);
  document.getElementById('refreshEmploiBtn')?.addEventListener('click', () => loadEmploi(true));
  document.getElementById('loadClassBtn')?.addEventListener('click', loadClassement);
  document.getElementById('submitUploadBtn')?.addEventListener('click', doUpload);
  document.getElementById('submitReleveBtn')?.addEventListener('click', demanderReleve);

  const dz = document.getElementById('dropzone');
  if (dz) {
    dz.addEventListener('click', () => document.getElementById('fileInput').click());
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
    dz.addEventListener('drop', e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); });
    document.getElementById('fileInput').addEventListener('change', e => setFile(e.target.files[0]));
  }

  initClassSelects();
  initReleveSelects();
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
  if (id === 'notifs')      loadNotifs();
  if (id === 'chat')        loadEnsConversations();
  if (id === 'releve')      initReleveHistory();
}

/* ── ACCUEIL ──────────────────────────────────────────────────────── */
async function loadAccueil() {
  const grid = document.getElementById('accueilGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const [rFiles, rDepts] = await Promise.all([
      api('GET', '/api/download/my'),
      api('GET', '/api/calendar/departements'),
    ]);
    if (rFiles.ok) {
      const d = await rFiles.json();
      const files = d.files || [];
      const nbEl = document.getElementById('nbMesFichiers');
      if (nbEl) nbEl.textContent = d.total || files.length;
      renderCards(files.slice(0, 4), grid);
    } else {
      grid.innerHTML = '<div class="empty"><div class="e-icon">📭</div><p>Aucun fichier déposé</p></div>';
    }
    if (rDepts.ok) {
      const depts = await rDepts.json();
      let totalFilieres = 0, totalSeances = 0;
      const myLastName  = (currentUser.last_name  || '').toLowerCase().trim();
      const myFirstName = (currentUser.first_name || '').toLowerCase().trim();
      await Promise.all((depts || []).map(async d => {
        const rF = await api('GET', `/api/calendar/departements/${d.id}/filieres`);
        if (!rF.ok) return;
        const filieres = await rF.json();
        totalFilieres += (filieres || []).length;
        await Promise.all((filieres || []).map(async f => {
          const rS = await api('GET', `/api/calendar/filieres/${f.id}/semestres`);
          if (!rS.ok) return;
          const sems = await rS.json();
          await Promise.all((sems || []).map(async s => {
            const rE = await api('GET', `/api/calendar/emploi-du-temps/${s.id}`);
            if (!rE.ok) return;
            const ed = await rE.json();
            totalSeances += (ed.seances || []).filter(sc =>
              (sc.enseignant_nom    || '').toLowerCase().trim() === myLastName &&
              (sc.enseignant_prenom || '').toLowerCase().trim() === myFirstName
            ).length;
          }));
        }));
      }));
      const nbS = document.getElementById('nbSeances');
      const nbF = document.getElementById('nbFilieres');
      if (nbS) nbS.textContent = totalSeances;
      if (nbF) nbF.textContent = totalFilieres;
    }
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
  form.append('file', selectedFile); form.append('title', title);
  form.append('category', category); form.append('module', module);
  form.append('is_public', isPublic);
  if (desc) form.append('description', desc);
  try {
    const r = await fetch('/api/upload/', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form });
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
  } finally { btn.disabled = false; btn.textContent = '📤 Déposer le fichier'; }
}

/* ── EMPLOI DU TEMPS ──────────────────────────────────────────────── */
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
        <select id="emplMode" style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem">
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
    if(!r.ok){const d=await r.json().catch(()=>({}));grid.innerHTML=`<div class="empty"><div class="e-icon">📅</div><p>${escHtml(d.detail||'Planning non disponible.')}</p></div>`;return;}
    const data=await r.json();
    let seances=data.seances||[];
    if(mode==='mine'){
      const myLastName=(currentUser.last_name||'').toLowerCase().trim();
      const myFirstName=(currentUser.first_name||'').toLowerCase().trim();
      if(myLastName||myFirstName){
        const filtered=seances.filter(s=>(s.enseignant_nom||'').toLowerCase().trim()===myLastName&&(s.enseignant_prenom||'').toLowerCase().trim()===myFirstName);
        if(filtered.length===0&&seances.length>0){
          grid.innerHTML=`<div class="empty" style="margin-bottom:1rem"><div class="e-icon">ℹ️</div><p>Aucune séance pour <strong>${escHtml(currentUser.first_name||'')} ${escHtml(currentUser.last_name||'')}</strong>.<br>Sélectionnez "Toutes les séances".</p></div>`;return;
        }
        seances=filtered;
      }
    }
    if(!seances.length){grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Aucune séance.</p></div>';return;}
    let html=`<div style="padding:.6rem 1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:8px;margin-bottom:1rem;font-size:.83rem;color:var(--muted)">
      🏛️ ${escHtml(data.departement||'')} · 🎓 ${escHtml(data.filiere||'')} · 📆 ${escHtml(data.annee||'')} · 📘 ${escHtml(data.semestre||'')} · ${seances.length} séance(s)</div>`;
    const byDay={};seances.forEach(s=>{const j=s.jour||'Lundi';(byDay[j]=byDay[j]||[]).push(s);});
    html+='<div class="schedule-wrap">';
    JOURS.filter(j=>byDay[j]).forEach(j=>{
      const sorted=byDay[j].sort((a,b)=>(a.heure_debut||'').localeCompare(b.heure_debut||''));
      html+=`<div class="day-block"><div class="day-label">${j}</div>`;
      sorted.forEach(s=>{
        const col=s.type_seance==='Cours'?'#1e4fa3':s.type_seance==='TD'?'#b45309':'#166534';
        html+=`<div class="seance"><div class="seance-time">${escHtml(s.heure_debut)} – ${escHtml(s.heure_fin)}</div>
          <div style="flex:1"><div class="seance-mod">${escHtml(s.element_module||s.module||'—')}</div>
          <div class="seance-det"><span style="background:${col};color:#fff;font-size:.68rem;padding:.1rem .45rem;border-radius:4px;margin-right:.4rem">${escHtml(s.type_seance||'')}</span>
          📍 ${escHtml(s.salle||'—')} · 🎓 ${escHtml(data.filiere||'—')}</div></div></div>`;
      });
      html+='</div>';
    });
    html+='</div>';
    grid.innerHTML=html;
  } catch(err){grid.innerHTML=`<div class="empty"><div class="e-icon">⚠️</div><p>Erreur : ${escHtml(err.message)}</p></div>`;}
};

/* ── CLASSEMENTS ──────────────────────────────────────────────────── */
function initClassSelects() {
  api('GET', '/api/calendar/departements').then(r => r.ok ? r.json() : []).then(list => {
    const sel = document.getElementById('clDept');
    if (!sel) return;
    (list || []).forEach(d => {
      const o = document.createElement('option'); o.value = d.id; o.textContent = d.nom; sel.appendChild(o);
    });
  });
}

window.classOnDept = function() {
  const dId = document.getElementById('clDept').value;
  const fSel = document.getElementById('clFiliere'), sSel = document.getElementById('clSemestre');
  fSel.innerHTML = '<option value="">— Choisir —</option>'; sSel.innerHTML = '<option value="">— Choisir —</option>';
  fSel.disabled = true; sSel.disabled = true;
  if (!dId) return;
  api('GET', `/api/calendar/departements/${dId}/filieres`).then(r => r.ok ? r.json() : []).then(list => {
    fSel.disabled = false;
    (list || []).forEach(f => { const o = document.createElement('option'); o.value = f.id; o.textContent = f.nom; fSel.appendChild(o); });
  });
};
window.classOnFiliere = function() {
  const fId = document.getElementById('clFiliere').value;
  const sSel = document.getElementById('clSemestre');
  sSel.innerHTML = '<option value="">— Choisir —</option>'; sSel.disabled = true;
  if (!fId) return;
  api('GET', `/api/calendar/filieres/${fId}/semestres`).then(r => r.ok ? r.json() : []).then(list => {
    sSel.disabled = false;
    (list || []).forEach(s => { const o = document.createElement('option'); o.value = s.id; o.textContent = s.nom; sSel.appendChild(o); });
  });
};

async function loadClassement() {
  const filiereId  = document.getElementById('clFiliere').value;
  const semestreId = document.getElementById('clSemestre').value;
  if (!filiereId || !semestreId) { showToast('Sélectionnez une filière et un semestre','error'); return; }
  const wrap = document.getElementById('classementContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', `/api/notes/enseignant/classements/filiere/${filiereId}/semestre/${semestreId}`);
    if (!r.ok) { const d = await r.json().catch(()=>({})); wrap.innerHTML = `<div class="empty"><div class="e-icon">📊</div><p>${escHtml(d.detail||'Classement non disponible')}</p></div>`; return; }
    const d = await r.json();
    const list = d.classement || [];
    if (!list.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">🏆</div><p>Aucun étudiant</p></div>'; return; }
    wrap.innerHTML = `
      <div style="margin-bottom:1rem;font-size:.85rem;color:var(--muted)">${escHtml(d.scope_nom||'')} · ${d.total||list.length} étudiants</div>
      <div class="table-wrap"><table>
        <thead><tr><th>Rang</th><th>CNE</th><th>Nom</th><th>Moyenne</th><th>Résultat</th></tr></thead>
        <tbody>${list.map(e => {
          const moy = e.moyenne != null ? parseFloat(e.moyenne) : null;
          const cls = moy === null ? '' : moy >= 12 ? 'note-ok' : moy >= 10 ? 'note-mid' : 'note-fail';
          return `<tr><td><strong>${e.rang}</strong></td><td>${escHtml(e.cne||'—')}</td><td>${escHtml(e.nom||'—')}</td>
            <td class="${cls}">${moy!==null?moy.toFixed(2):'—'}</td>
            <td>${moy===null?'—':moy>=10?'<span class="note-ok">✓ Admis</span>':'<span class="note-fail">✗ Ajourné</span>'}</td></tr>`;
        }).join('')}</tbody>
      </table></div>`;
  } catch { wrap.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

/* ── RELEVÉS ──────────────────────────────────────────────────────── */
function initReleveSelects() {
  api('GET', '/api/calendar/departements').then(r => r.ok ? r.json() : []).then(depts => {
    return Promise.all((depts || []).map(d =>
      api('GET', `/api/calendar/departements/${d.id}/filieres`).then(r => r.ok ? r.json() : [])
    ));
  }).then(groups => {
    const all = [].concat(...groups);
    const sel = document.getElementById('rFiliere');
    if (!sel) return;
    sel.innerHTML = '<option value="">— Choisir —</option>';
    all.forEach(f => { const o = document.createElement('option'); o.value = f.id; o.textContent = f.nom; sel.appendChild(o); });
  });
}

window.releveOnFiliere = function() {
  const fId = document.getElementById('rFiliere').value;
  const sSel = document.getElementById('rSemestre'), eSel = document.getElementById('rEtudiantId');
  sSel.innerHTML = '<option value="">— Choisir —</option>'; sSel.disabled = true;
  eSel.innerHTML = '<option value="">— Choisir un semestre d\'abord —</option>'; eSel.disabled = true;
  if (!fId) return;
  api('GET', `/api/calendar/filieres/${fId}/semestres`).then(r => r.ok ? r.json() : []).then(list => {
    sSel.disabled = false;
    (list || []).forEach(s => { const o = document.createElement('option'); o.value = s.id; o.textContent = s.nom; sSel.appendChild(o); });
  });
};

window.releveOnSemestre = async function() {
  const fId = document.getElementById('rFiliere').value;
  const eSel = document.getElementById('rEtudiantId');
  eSel.innerHTML = '<option value="">Chargement…</option>'; eSel.disabled = true;
  if (!fId) return;
  try {
    const r = await api('GET', '/api/admin/notes/admin/etudiants');
    if (!r.ok) throw new Error();
    let list = await r.json();
    if (!Array.isArray(list)) list = list.etudiants || [];
    list = list.filter(e => String(e.calendar_filiere_id) === String(fId));
    eSel.innerHTML = '<option value="">— Choisir un étudiant —</option>';
    list.forEach(e => { const o = document.createElement('option'); o.value = e.id; o.textContent = `${e.prenom} ${e.nom} (${e.cne})`; eSel.appendChild(o); });
    eSel.disabled = false;
  } catch { eSel.innerHTML = '<option value="">Erreur chargement</option>'; }
};

async function demanderReleve() {
  const semId      = parseInt(document.getElementById('rSemestre').value);
  const etudiantId = parseInt(document.getElementById('rEtudiantId').value);
  const res        = document.getElementById('releveResult');
  if (!semId || isNaN(semId))           { res.innerHTML = '<div class="alert alert-err">Sélectionnez un semestre.</div>'; return; }
  if (!etudiantId || isNaN(etudiantId)) { res.innerHTML = '<div class="alert alert-err">Sélectionnez un étudiant.</div>'; return; }
  try {
    const r = await api('POST', '/api/notes/enseignant/demandes-releve', { etudiant_id: etudiantId, calendar_semestre_id: semId });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      // Sauvegarder en sessionStorage
      const hist = JSON.parse(sessionStorage.getItem('ens_releve_history') || '[]');
      if (!hist.find(h => h.id === d.id)) {
        const semSel = document.getElementById('rSemestre');
        const semNom = semSel ? semSel.options[semSel.selectedIndex]?.text : '';
        const etSel  = document.getElementById('rEtudiantId');
        const etNom  = etSel  ? etSel.options[etSel.selectedIndex]?.text  : '';
        hist.unshift({ id: d.id, semNom, etNom, statut: d.statut });
        sessionStorage.setItem('ens_releve_history', JSON.stringify(hist.slice(0, 20)));
      }
      res.innerHTML = `<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong><br>
        <small>Vous serez notifié(e) dès la décision de l'admin.</small></div>`;
      initReleveHistory();
    } else if (r.status === 409) {
      res.innerHTML = '<div class="alert alert-ok">ℹ️ Une demande est déjà en attente pour cet étudiant et ce semestre.</div>';
    } else {
      const d = await r.json().catch(()=>({}));
      res.innerHTML = `<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch { res.innerHTML = '<div class="alert alert-err">✗ Erreur réseau.</div>'; }
}

async function initReleveHistory() {
  const histWrap = document.getElementById('releveHistory');
  if (!histWrap) return;
  histWrap.innerHTML = '<div class="loader" style="margin:.5rem 0"></div>';
  try {
    const r = await api('GET', '/api/notes/enseignant/mes-demandes-releve');
    if (!r.ok) { histWrap.innerHTML = ''; return; }
    const demandes = await r.json();
    if (!demandes || !demandes.length) { histWrap.innerHTML = ''; return; }
    histWrap.innerHTML = '<div style="margin-top:1.5rem"><div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:.5rem">Mes demandes de relevés</div>'
      + demandes.map(d => {
          const date = d.demande_le ? new Date(d.demande_le).toLocaleDateString('fr-FR') : '';
          const badgeClass = d.statut==='approuve'?'enseignant':d.statut==='rejete'?'admin':'etudiant';
          return `<div style="display:flex;align-items:center;justify-content:space-between;padding:.6rem .85rem;
            background:var(--cream);border:1.5px solid var(--border);border-radius:8px;margin-bottom:.4rem">
            <div>
              <span style="font-weight:600;font-size:.83rem">Demande #${d.id}</span>
              <span style="font-size:.75rem;color:var(--muted);margin-left:.5rem">Semestre #${d.calendar_semestre_id} · Étudiant #${d.etudiant_id}</span>
              <span class="badge badge-${badgeClass}" style="margin-left:.4rem;font-size:.68rem">${escHtml(d.statut)}</span>
              ${d.motif_rejet ? `<div style="font-size:.72rem;color:crimson">Motif : ${escHtml(d.motif_rejet)}</div>` : ''}
              <span style="font-size:.71rem;color:var(--muted)">${date}</span>
            </div>
            <div style="display:flex;gap:.4rem">
              ${d.statut==='approuve'
                ? `<button class="btn btn-gold btn-sm" onclick="telechargerReleveEns(${d.id})">📄 PDF</button>`
                : `<button class="btn btn-outline btn-sm" onclick="initReleveHistory()">↻</button>`}
            </div>
          </div>`;
        }).join('')
      + '</div>';
  } catch { histWrap.innerHTML = ''; }
}

window.telechargerReleveEns = async function(demandeId) {
  showToast('Génération du PDF…', '');
  try {
    const r = await api('GET', `/api/notes/enseignant/releves/${demandeId}`);
    if (!r.ok) { const d = await r.json().catch(()=>({})); showToast('✗ '+(d.detail||`Erreur ${r.status}`),'error'); return; }
    const releve = await r.json();
    const notes = releve.notes || {};
    const elts  = notes.notes || [];
    const moy   = notes.moyenne_semestre != null ? parseFloat(notes.moyenne_semestre).toFixed(2) : '—';
    const now   = new Date().toLocaleDateString('fr-FR', {day:'2-digit', month:'long', year:'numeric'});
    const rows  = elts.map(e => `<tr><td>Élément #${e.calendar_element_id}</td>
      <td style="text-align:center">${e.note!=null?parseFloat(e.note).toFixed(2):'—'}</td>
      <td style="text-align:center">${e.note!=null?(parseFloat(e.note)>=10?'✓':'✗'):'—'}</td></tr>`).join('');
    const html = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"/>
      <title>Relevé — ${escHtml(releve.etudiant_nom)}</title>
      <style>body{font-family:Arial,sans-serif;margin:40px;color:#1a1a1a}h1{color:#8B6914;font-size:1.4rem}
      table{width:100%;border-collapse:collapse;margin-bottom:1rem}th{background:#8B6914;color:#fff;padding:.5rem .7rem;text-align:left;font-size:.78rem}
      td{padding:.45rem .7rem;border-bottom:1px solid #eee;font-size:.85rem}
      .moy{background:#faf8f2;border:2px solid #8B6914;border-radius:8px;padding:.8rem 1.2rem;display:inline-block;margin-bottom:1rem}
      .moy .val{font-size:1.5rem;font-weight:700;color:#8B6914}
      @media print{.no-print{display:none}}</style></head><body>
      <h1>EST Salé — Relevé de notes officiel</h1>
      <p style="color:#666;font-size:.85rem">Généré le ${now}</p>
      <div style="display:flex;gap:2rem;margin-bottom:1.5rem;font-size:.88rem">
        <div><strong style="display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:#888">Étudiant</strong>${escHtml(releve.etudiant_nom)}</div>
        <div><strong style="display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:#888">CNE</strong>${escHtml(releve.etudiant_cne)}</div>
        <div><strong style="display:block;font-size:.7rem;text-transform:uppercase;letter-spacing:.06em;color:#888">N° Demande</strong>${releve.demande_id}</div>
      </div>
      <table><thead><tr><th>Élément</th><th style="text-align:center">Note / 20</th><th style="text-align:center">Résultat</th></tr></thead>
      <tbody>${rows}</tbody></table>
      <div class="moy"><div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#888;margin-bottom:.2rem">Moyenne</div>
      <div class="val">${moy} / 20</div></div>
      <div style="margin-top:2rem;font-size:.75rem;color:#999;border-top:1px solid #eee;padding-top:.8rem">Document officiel — EST Salé</div>
      <div class="no-print" style="margin-top:1.5rem;text-align:center">
        <button onclick="window.print()" style="padding:.6rem 1.5rem;background:#8B6914;color:#fff;border:none;border-radius:8px;cursor:pointer">🖨️ Imprimer / PDF</button>
      </div></body></html>`;
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const win  = window.open(url, '_blank');
    if (!win) showToast('Autorisez les popups pour télécharger le PDF', 'error');
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch { showToast('Erreur génération PDF', 'error'); }
};

/* ── NOTIFICATIONS ────────────────────────────────────────────────── */
async function loadNotifs() {
  const wrap = document.getElementById('notifsContent');
  if (!wrap) return;
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/messaging/notifications/');
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const list = d.notifications || [];
    if (!list.length) { wrap.innerHTML = '<div class="empty"><div class="e-icon">🔔</div><p>Aucune notification</p></div>'; return; }
    wrap.innerHTML = list.map(n => `
      <div class="notif-item ${n.is_read ? '' : 'notif-unread'}" style="
        padding:.8rem 1rem;border-bottom:1px solid var(--border);display:flex;
        gap:.8rem;align-items:flex-start;cursor:pointer"
        onclick="markRead('${n.notification_id}', '${n.created_at}', this)">
        <div style="font-size:1.3rem;flex-shrink:0">${n.type==='schedule_update'?'📅':n.type==='grade_reminder'?'⏰':n.type==='releve_approuve'?'✅':n.type==='releve_rejete'?'❌':'🔔'}</div>
        <div style="flex:1">
          <div style="font-weight:600;font-size:.85rem">${escHtml(n.title)}</div>
          <div style="font-size:.78rem;color:var(--muted);margin-top:.15rem">${escHtml(n.content)}</div>
          <div style="font-size:.7rem;color:var(--muted);margin-top:.2rem">${new Date(n.created_at).toLocaleString('fr-FR')}</div>
        </div>
        ${!n.is_read ? '<div style="width:8px;height:8px;background:var(--gold);border-radius:50%;flex-shrink:0;margin-top:4px"></div>' : ''}
      </div>`).join('');
  } catch(e) { wrap.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div><p>Erreur notifications</p></div>`; }
}

window.markRead = async function(notifId, createdAt, el) {
  try {
    await api('PUT', `/api/messaging/notifications/${notifId}/read`, { created_at: createdAt });
    el.classList.remove('notif-unread');
    const dot = el.querySelector('[style*="background:var(--gold)"]');
    if (dot) dot.remove();
  } catch {}
};

async function markAllRead() {
  try {
    await api('PUT', '/api/messaging/notifications/read-all');
    loadNotifs();
    showToast('Toutes les notifications lues ✓', 'success');
  } catch { showToast('Erreur','error'); }
}

/* ── CHAT ─────────────────────────────────────────────────────────── */
var _ensSelectedUser = null, _ensChatCache = {}, _ensPollTimer = null;
var _ensActiveChatId = null, _ensSearchTimer = null;

window.loadEnsConversations = async function() {
  const wrap = document.getElementById('ensConvItems');
  if (!wrap) return;
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/messaging/chat/conversations');
    if (!r.ok) throw new Error(r.status);
    const convs = await r.json();
    if (!convs.length) {
      wrap.innerHTML = '<div style="padding:1rem;color:var(--muted);font-size:.82rem;text-align:center">Aucune conversation.<br>Cliquez <strong>+ Nouvelle</strong>.</div>';
      return;
    }
    wrap.innerHTML = convs.map(c =>
      `<div class="conv-item" onclick="openEnsConv('${c.conversation_id}','${escHtml(c.other_user_name||'?')}')">
        <div class="conv-avatar">${(c.other_user_name||'?')[0].toUpperCase()}</div>
        <div><div class="conv-name">${escHtml(c.other_user_name||'—')}</div>
        <div class="conv-last">${c.last_message_at ? new Date(c.last_message_at).toLocaleDateString('fr-FR') : 'Aucun message'}</div></div>
      </div>`
    ).join('');
  } catch { wrap.innerHTML = `<div style="padding:1rem;color:var(--muted);font-size:.82rem;text-align:center">⚠ Indisponible<br><button class="btn btn-outline btn-sm" style="margin-top:.5rem" onclick="loadEnsConversations()">↻</button></div>`; }
};

window.openEnsConv = function(convId, convName) {
  _ensActiveChatId = convId;
  const area = document.getElementById('ensChatArea');
  area.innerHTML =
    `<div class="chat-header"><div class="conv-avatar" style="width:32px;height:32px;font-size:.85rem">${convName[0].toUpperCase()}</div><strong>${escHtml(convName)}</strong></div>`
    + `<div id="ensMsgsWrap"></div>`
    + `<div class="chat-input-row"><input type="text" id="ensMsgInput" placeholder="Écrire un message…"/>
       <button class="btn btn-gold" onclick="sendEnsMsg('${convId}')">Envoyer</button></div>`;
  document.getElementById('ensMsgInput').onkeydown = e => { if (e.key === 'Enter') sendEnsMsg(convId); };
  fetchEnsMessages(convId);
  clearInterval(_ensPollTimer);
  _ensPollTimer = setInterval(() => fetchEnsMessages(convId), 5000);
};

async function fetchEnsMessages(convId) {
  const wrap = document.getElementById('ensMsgsWrap');
  if (!wrap) { clearInterval(_ensPollTimer); return; }
  try {
    const r = await api('GET', `/api/messaging/chat/conversations/${convId}/messages`);
    if (!r.ok) return;
    const d = await r.json();
    const msgs = (d.messages || []).filter(m => !m.is_hidden);
    const myId = currentUser.id || '';
    const atBottom = (wrap.scrollHeight - wrap.scrollTop - wrap.clientHeight) < 40;
    if (!msgs.length) { wrap.innerHTML = '<div class="chat-empty-msgs">Aucun message. Dites bonjour !</div>'; return; }
    wrap.innerHTML = msgs.map(m => {
      const isMe = m.sender_id === myId;
      return `<div class="msg ${isMe ? 'msg-me' : 'msg-other'}">
        ${!isMe ? `<div class="msg-sender">${escHtml(m.sender_name)}</div>` : ''}
        <div class="msg-bubble">${escHtml(m.content)}</div>
        <div class="msg-time">${m.sent_at ? new Date(m.sent_at).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) : ''}</div>
      </div>`;
    }).join('');
    if (atBottom) wrap.scrollTop = wrap.scrollHeight;
  } catch {}
}

window.sendEnsMsg = async function(convId) {
  const input = document.getElementById('ensMsgInput');
  const content = input ? input.value.trim() : '';
  if (!content) return;
  input.value = '';
  try {
    const r = await api('POST', `/api/messaging/chat/conversations/${convId}/messages`, { content });
    if (r.ok || r.status === 201) fetchEnsMessages(convId);
    else { input.value = content; showToast('Erreur envoi', 'error'); }
  } catch { input.value = content; showToast('Erreur réseau', 'error'); }
};

window.openEnsChat = function() {
  _ensSelectedUser = null;
  const btn = document.getElementById('btnStartEnsChat');
  if (btn) btn.disabled = true;
  const list = document.getElementById('ensChatUserList');
  if (list) list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Tapez pour chercher...</div>';
  const inp = document.getElementById('ensChatSearch');
  if (inp) inp.value = '';
  const modal = document.getElementById('ensChatModal');
  if (modal) modal.style.display = 'flex';
};

window.closeEnsChat = function() {
  const modal = document.getElementById('ensChatModal');
  if (modal) modal.style.display = 'none';
};

window.ensChatSearchUsers = function(q) {
  clearTimeout(_ensSearchTimer);
  const list = document.getElementById('ensChatUserList');
  if (!q || q.length < 2) {
    list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Tapez au moins 2 caractères...</div>';
    return;
  }
  list.innerHTML = '<div class="loader" style="margin:.6rem auto"></div>';
  _ensSearchTimer = setTimeout(async () => {
    try {
      const r = await api('GET', '/api/admin/users/?search=' + encodeURIComponent(q) + '&max=50');
      const users = r.ok ? await r.json() : [];
      const myId = currentUser.id || '';
      // Enseignants + admins + délégués — exclure soi-même et les étudiants simples
      const targets = (users || []).filter(u => {
        const roles = u.roles || [];
        return u.id !== myId && (
          roles.includes('enseignant') ||
          roles.includes('admin')      ||
          roles.includes('delegue')
        );
      });
      if (!targets.length) {
        list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Aucun résultat.</div>';
        return;
      }
      _ensChatCache = {};
      list.innerHTML = targets.map(u => {
        const name = `${u.first_name || ''} ${u.last_name || ''}`.trim() || u.username;
        const roles = u.roles || [];
        const isAdmin = roles.includes('admin');
        const isDelegue = roles.includes('delegue');
        const bg = isAdmin ? '#7c3aed' : isDelegue ? '#0369a1' : 'var(--gold,#C9A84C)';
        const roleLabel = isAdmin ? '👑 Admin' : isDelegue ? '🎖 Délégué' : '🎓 Enseignant';
        _ensChatCache[u.id] = { id: u.id, name, roles };
        return `<div onclick="selectEnsUser('${u.id}')" data-uid="${u.id}"
          style="padding:.6rem 1rem;cursor:pointer;border-bottom:1px solid var(--border);display:flex;gap:.65rem;align-items:center">
          <div style="width:32px;height:32px;border-radius:50%;background:${bg};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0">${name[0].toUpperCase()}</div>
          <div>
            <div style="font-weight:600;font-size:.83rem">${escHtml(name)}</div>
            <div style="font-size:.71rem;color:var(--muted)">${escHtml(u.email || u.username)}</div>
            <div style="font-size:.69rem;margin-top:.1rem">${roleLabel}</div>
          </div>
        </div>`;
      }).join('');
    } catch {
      list.innerHTML = '<div style="padding:.8rem;text-align:center;color:crimson;font-size:.82rem">Erreur de chargement.</div>';
    }
  }, 350);
};

window.selectEnsUser = function(id) {
  _ensSelectedUser = _ensChatCache[id];
  if (!_ensSelectedUser) return;
  document.querySelectorAll('#ensChatUserList [data-uid]').forEach(el =>
    el.style.background = el.dataset.uid === id ? 'var(--cream,#FAF8F2)' : ''
  );
  const btn = document.getElementById('btnStartEnsChat');
  if (btn) btn.disabled = false;
};

window.startEnsChatConv = async function() {
  if (!_ensSelectedUser) return;
  const btn = document.getElementById('btnStartEnsChat');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ …'; }
  try {
    const r = await api('POST', '/api/messaging/chat/conversations', {
      target_user_id:    _ensSelectedUser.id,
      target_user_name:  _ensSelectedUser.name,
      target_user_roles: _ensSelectedUser.roles,
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      closeEnsChat();
      loadEnsConversations();
      openEnsConv(d.conversation_id, _ensSelectedUser.name);
      showToast('Conversation démarrée ✓', 'success');
    } else {
      const d = await r.json().catch(() => ({}));
      showToast('✗ ' + (d.detail || `Erreur ${r.status}`), 'error');
    }
  } catch { showToast('Erreur réseau', 'error'); }
  finally { if (btn) { btn.disabled = false; btn.textContent = 'Démarrer'; } }
};

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
