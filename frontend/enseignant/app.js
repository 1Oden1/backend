/* ═══════════════════════════════════════════════════════════════
   ENT Salé — Enseignant · app.js  (v2 — avec Messagerie + Notifications)
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
  messagerie:'Messagerie', notifications:'Notifications'
};
let selectedFile = null;
let _allConvs = [];
let _activeConvId = null;
let _pollInterval = null;

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
  document.getElementById('markAllReadBtn').addEventListener('click', markAllNotifRead);

  const dz = document.getElementById('dropzone');
  dz.addEventListener('click', () => document.getElementById('fileInput').click());
  dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
  dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
  dz.addEventListener('drop', e => { e.preventDefault(); setFile(e.dataTransfer.files[0]); });
  document.getElementById('fileInput').addEventListener('change', e => setFile(e.target.files[0]));

  // fermer modal en cliquant dehors
  document.getElementById('newConvModal').addEventListener('click', e => {
    if (e.target === document.getElementById('newConvModal')) closeNewConvModal();
  });

  loadAccueil();
  // Charger les badges en arrière-plan
  loadNotifBadge();
  loadConvBadge();
});

function switchPanel(id, navEl) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const t = document.getElementById('panel-' + id);
  if (t) t.classList.add('active');
  document.getElementById('topbarTitle').textContent = PANEL_TITLES[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  if (id === 'mesfichiers')    loadMesFichiers();
  if (id === 'emploi')         initEmploiPanel();
  if (id === 'messagerie')     loadConversations();
  if (id === 'releve')         loadMesDemandes();
  if (id === 'notifications')  loadNotifications();
  // stopper le polling si on quitte la messagerie
  if (id !== 'messagerie' && _pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
}

/* ── ACCUEIL ──────────────────────────────────────────────────────── */
async function loadAccueil() {
  const grid = document.getElementById('accueilGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/download/my');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    const nbEl = document.getElementById('nbMesFichiers');
    if (nbEl) nbEl.textContent = d.total || files.length;
    renderCards(files.slice(0, 4), grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }

  // Charger stats séances et filières
  try {
    const rDepts = await api('GET', '/api/calendar/departements');
    if (rDepts.ok) {
      const depts = await rDepts.json() || [];
      // Compter filières de tous les départements
      let totalFilieres = 0;
      await Promise.all((depts||[]).map(async d => {
        try {
          const rf = await api('GET', '/api/calendar/departements/' + d.id + '/filieres');
          if (rf.ok) { const fs = await rf.json(); totalFilieres += (fs||[]).length; }
        } catch {}
      }));
      const nbF = document.getElementById('nbFilières');
      if (nbF) nbF.textContent = totalFilieres;
    }
  } catch {}

  // Charger nb conversations pour la stat
  try {
    const r2 = await api('GET', '/api/messaging/chat/conversations');
    if (r2.ok) {
      const data2 = await r2.json();
      const convs = Array.isArray(data2) ? data2 : (data2.conversations || []);
      const nbC = document.getElementById('nbConvs');
      if (nbC) nbC.textContent = convs.length;
    }
  } catch {}
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
    const r = await api('GET', '/api/download/' + fileId);
    if (!r.ok) { showToast('Lien indisponible','error'); return; }
    const d = await r.json();
    let url = d.download_url || '';
    // Fix: si l'URL pointe vers minio:9000 ou ent_minio:9000 (réseau interne),
    // on remplace par localhost:9000 accessible depuis le navigateur
    url = url.replace(/http:\/\/(ent_minio|minio):9000/g, 'http://localhost:9000');
    window.open(url, '_blank');
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
  const pw = document.getElementById('progressWrap'), pb = document.getElementById('progressBar'), pl = document.getElementById('progressLabel');
  pw.style.display = 'block'; pb.style.width = '0';
  let prog = 0;
  const iv = setInterval(() => { prog = Math.min(prog + Math.random() * 15, 90); pb.style.width = prog + '%'; }, 300);

  const form = new FormData();
  form.append('file', selectedFile); form.append('title', title); form.append('category', category);
  form.append('module', module); form.append('is_public', isPublic);
  if (desc) form.append('description', desc);

  try {
    const r = await fetch('/api/upload/', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form });
    clearInterval(iv); pb.style.width = '100%';
    if (r.ok || r.status === 201) {
      pl.textContent = '✓ Upload terminé !';
      alertEl.innerHTML = '<div class="alert alert-ok">✓ Fichier déposé avec succès !</div>';
      showToast('Fichier déposé !','success');
      setTimeout(() => {
        selectedFile = null; document.getElementById('fileInput').value = '';
        document.getElementById('dzSelected').textContent = ''; document.getElementById('fTitle').value = '';
        document.getElementById('fModule').value = ''; document.getElementById('fDesc').value = '';
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

/* ── EMPLOI DU TEMPS ─────────────────────────────────────────────── */
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
      const myLN=(currentUser.last_name||'').toLowerCase().trim();
      const myFN=(currentUser.first_name||'').toLowerCase().trim();
      if(myLN||myFN){
        const filtered=seances.filter(s=>(s.enseignant_nom||'').toLowerCase().trim()===myLN&&(s.enseignant_prenom||'').toLowerCase().trim()===myFN);
        if(filtered.length===0&&seances.length>0){
          grid.innerHTML=`<div class="empty"><div class="e-icon">ℹ️</div><p>Aucune séance pour <strong>${escHtml(currentUser.first_name||'')} ${escHtml(currentUser.last_name||'')}</strong>. Essayez "Toutes les séances".</p></div>`;
          return;
        }
        seances=filtered;
      }
    }
    if(!seances.length){grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Aucune séance pour ce semestre.</p></div>';return;}
    let html=`<div style="padding:.6rem 1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:8px;margin-bottom:1rem;font-size:.83rem;color:var(--muted)">
      🏛️ ${escHtml(data.departement||'')} &nbsp;·&nbsp; 🎓 ${escHtml(data.filiere||'')} &nbsp;·&nbsp; 📆 ${escHtml(data.annee||'')} &nbsp;·&nbsp; 📘 ${escHtml(data.semestre||'')} &nbsp;·&nbsp; ${seances.length} séance(s)</div>`;
    const byDay={};seances.forEach(s=>{const j=s.jour||'Lundi';(byDay[j]=byDay[j]||[]).push(s);});
    html+='<div class="schedule-wrap">';
    JOURS.filter(j=>byDay[j]).forEach(j=>{
      const sorted=byDay[j].sort((a,b)=>(a.heure_debut||'').localeCompare(b.heure_debut||''));
      html+=`<div class="day-block"><div class="day-label">${j}</div>`;
      sorted.forEach(s=>{
        const col=s.type_seance==='Cours'?'#1e4fa3':s.type_seance==='TD'?'#b45309':'#166534';
        html+=`<div class="seance"><div class="seance-time">${escHtml(s.heure_debut)} – ${escHtml(s.heure_fin)}</div><div style="flex:1"><div class="seance-mod">${escHtml(s.element_module||s.module||'—')}</div><div class="seance-det"><span style="background:${col};color:#fff;font-size:.68rem;padding:.1rem .45rem;border-radius:4px;margin-right:.4rem">${escHtml(s.type_seance||'')}</span>📍 ${escHtml(s.salle||'—')} &nbsp;·&nbsp; 🎓 ${escHtml(data.filiere||'—')}</div></div></div>`;
      });
      html+='</div>';
    });
    html+='</div>';
    grid.innerHTML=html;
  } catch(err){grid.innerHTML=`<div class="empty"><div class="e-icon">⚠️</div><p>Erreur : ${escHtml(err.message)}</p></div>`;}
};

/* ── CLASSEMENTS ──────────────────────────────────────────────────── */
async function loadClassement() {
  const filiereId  = document.getElementById('clFiliere').value;
  const semestreId = document.getElementById('clSemestre').value;
  if (!filiereId || !semestreId) { showToast('Remplissez les deux champs','error'); return; }
  const wrap = document.getElementById('classementContent');
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', `/api/notes/enseignant/classements/filiere/${filiereId}/semestre/${semestreId}`);
    if (!r.ok) { const d=await r.json().catch(()=>({})); wrap.innerHTML=`<div class="empty"><div class="e-icon">📊</div><p>${escHtml(d.detail||'Classement non disponible')}</p></div>`; return; }
    const d=await r.json();const list=d.classement||[];
    if(!list.length){wrap.innerHTML='<div class="empty"><div class="e-icon">🏆</div><p>Aucun étudiant</p></div>';return;}
    wrap.innerHTML=`<div style="margin-bottom:1rem;font-size:.85rem;color:var(--muted)">${escHtml(d.scope_nom||'')} · ${d.total||list.length} étudiants</div>
      <div class="table-wrap"><table><thead><tr><th>Rang</th><th>CNE</th><th>Nom</th><th>Moyenne</th><th>Résultat</th></tr></thead>
      <tbody>${list.map(e=>{const moy=e.moyenne!=null?parseFloat(e.moyenne):null;const cls=moy===null?'':moy>=12?'note-ok':moy>=10?'note-mid':'note-fail';
        return `<tr><td><strong>${e.rang}</strong></td><td>${escHtml(e.cne||'—')}</td><td>${escHtml(e.nom||'—')}</td><td class="${cls}">${moy!==null?moy.toFixed(2):'—'}</td><td>${moy===null?'—':moy>=10?'<span class="note-ok">✓ Admis</span>':'<span class="note-fail">✗ Ajourné</span>'}</td></tr>`;
      }).join('')}</tbody></table></div>`;
  } catch { wrap.innerHTML='<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

/* ── RELEVÉ ───────────────────────────────────────────────────────── */
async function loadRelevePanel() {
  await Promise.all([loadMesDemandes(), ]);
}

async function loadMesDemandes() {
  const wrap = document.getElementById('mesDemandes');
  if (!wrap) return;
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    // Charger les demandes en_attente et approuvées
    const [rA, rE] = await Promise.all([
      api('GET', '/api/notes/enseignant/demandes-releve/1').catch(()=>null), // placeholder
      api('GET', '/api/notes/enseignant/demandes-releve/1').catch(()=>null),
    ]);
    // On liste via les demandes connues stockées en localStorage
    const demandes = JSON.parse(localStorage.getItem('mes_demandes_releve') || '[]');
    if (!demandes.length) {
      wrap.innerHTML = '<div class="empty"><div class="e-icon">📄</div><p>Aucune demande envoyée pour le moment.</p></div>';
      return;
    }
    // Pour chaque demande, vérifier le statut
    const rows = await Promise.all(demandes.map(async d => {
      try {
        const r = await api('GET', `/api/notes/enseignant/demandes-releve/${d.id}`);
        if (r.ok) return await r.json();
        return d;
      } catch { return d; }
    }));
    // Mettre à jour localStorage avec statuts actuels
    localStorage.setItem('mes_demandes_releve', JSON.stringify(rows));
    renderDemandes(rows, wrap);
  } catch(e) {
    wrap.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div><p>${escHtml(e.message)}</p></div>`;
  }
}

function renderDemandes(demandes, wrap) {
  if (!demandes.length) {
    wrap.innerHTML = '<div class="empty"><div class="e-icon">📄</div><p>Aucune demande.</p></div>';
    return;
  }
  const STATUT = { en_attente: '⏳ En attente', approuve: '✅ Approuvé', rejete: '❌ Rejeté' };
  const COLORS = { en_attente: '#E65100', approuve: '#2E7D32', rejete: '#C0392B' };
  wrap.innerHTML = demandes.map(d => {
    const color = COLORS[d.statut] || '#888';
    const label = STATUT[d.statut] || d.statut;
    return `<div style="background:var(--white);border:1px solid var(--border);border-left:4px solid ${color};border-radius:10px;padding:1rem 1.2rem;margin-bottom:.7rem;display:flex;align-items:center;justify-content:space-between;gap:1rem">
      <div>
        <div style="font-weight:600;font-size:.85rem">Demande #${d.id} — Semestre ${d.calendar_semestre_id}</div>
        <div style="font-size:.75rem;color:var(--muted);margin-top:.2rem">
          Étudiant ID: ${d.etudiant_id} · Demandé le: ${d.demande_le ? new Date(d.demande_le).toLocaleDateString('fr-FR') : '—'}
          ${d.motif_rejet ? `<br>Motif rejet: <em>${escHtml(d.motif_rejet)}</em>` : ''}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:.7rem">
        <span style="font-size:.75rem;font-weight:700;color:${color}">${label}</span>
        ${d.statut === 'approuve' ? `<button class="btn btn-gold btn-sm" onclick="voirReleve(${d.id})">📊 Voir le relevé</button>` : ''}
      </div>
    </div>`;
  }).join('');
}

async function demanderReleve() {
  const semId=parseInt(document.getElementById('rSemestre').value);
  const res=document.getElementById('releveResult');
  let etudiantId=parseInt(document.getElementById('rEtudiantId')?.value);
  if(!semId){res.innerHTML='<div class="alert alert-err">Semestre ID requis.</div>';return;}
  if(!etudiantId){
    res.innerHTML=`<div class="form-group" style="margin-top:.8rem"><label>ID Étudiant</label>
      <input type="number" id="rEtudiantId" placeholder="ex: 42" min="1" style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif"/>
      <button class="btn btn-gold" onclick="demanderReleve()" style="width:100%;padding:.65rem;margin-top:.5rem">Confirmer</button></div>`;
    return;
  }
  try {
    const r=await api('POST','/api/notes/enseignant/demandes-releve',{etudiant_id:etudiantId,calendar_semestre_id:semId});
    if(r.ok||r.status===201){
      const d=await r.json();
      // Sauvegarder la demande en localStorage pour tracking
      const demandes = JSON.parse(localStorage.getItem('mes_demandes_releve') || '[]');
      if (!demandes.find(x => x.id === d.id)) demandes.unshift(d);
      localStorage.setItem('mes_demandes_releve', JSON.stringify(demandes));
      res.innerHTML=`<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong></div>`;
      loadMesDemandes();
    }
    else if(r.status===409){res.innerHTML='<div class="alert alert-ok">ℹ️ Une demande est déjà en attente.</div>';}
    else{const d=await r.json().catch(()=>({}));res.innerHTML=`<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;}
  } catch{res.innerHTML='<div class="alert alert-err">✗ Erreur réseau.</div>';}
}

async function voirReleve(demandeId) {
  const modal = document.getElementById('releveModal');
  const content_el = document.getElementById('releveModalContent');
  modal.classList.add('open');
  content_el.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/notes/enseignant/releves/' + demandeId);
    if (!r.ok) {
      const d = await r.json().catch(function(){ return {}; });
      content_el.innerHTML = '<div class="alert alert-err">✗ ' + escHtml(d.detail || 'Erreur ' + r.status) + '</div>';
      return;
    }
    const data = await r.json();
    const notesData = data.notes || {};
    const elements  = notesData.notes || [];
    const moyenne   = notesData.moyenne_semestre != null ? parseFloat(notesData.moyenne_semestre) : null;

    let html = '<div style="margin-bottom:1.5rem">';
    html += '<div style="font-size:1.1rem;font-weight:700;margin-bottom:.3rem">👤 ' + escHtml(data.etudiant_nom) + '</div>';
    html += '<div style="font-size:.78rem;color:var(--muted)">CNE : ' + escHtml(data.etudiant_cne) + ' · Semestre ID : ' + (notesData.calendar_semestre_id || '—') + '</div>';
    html += '</div>';

    if (elements.length === 0) {
      html += '<div class="empty"><div class="e-icon">📭</div><p>Aucune note saisie pour ce semestre.</p></div>';
    } else {
      html += '<div class="table-wrap"><table>';
      html += '<thead><tr><th>ID Élément</th><th>Note</th><th>Résultat</th></tr></thead><tbody>';
      elements.forEach(function(e) {
        var note = e.note != null ? parseFloat(e.note) : null;
        var cls  = note === null ? '' : note >= 12 ? 'note-ok' : note >= 10 ? 'note-mid' : 'note-fail';
        var res  = note === null ? '—' : note >= 10 ? '<span class="note-ok">✓ Validé</span>' : '<span class="note-fail">✗ Ajourné</span>';
        html += '<tr>';
        html += '<td>Élément #' + e.calendar_element_id + '</td>';
        html += '<td class="' + cls + '">' + (note !== null ? note.toFixed(2) + ' / 20' : '—') + '</td>';
        html += '<td>' + res + '</td>';
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      var moyColor = (moyenne != null && moyenne >= 10) ? 'var(--success)' : 'var(--error)';
      html += '<div style="margin-top:1rem;padding:.8rem 1rem;background:var(--cream);border-radius:8px;display:flex;justify-content:space-between;align-items:center">';
      html += '<span style="font-size:.82rem;color:var(--muted)">Moyenne générale du semestre</span>';
      html += '<span style="font-size:1.2rem;font-weight:700;color:' + moyColor + '">';
      html += (moyenne != null ? moyenne.toFixed(2) + ' / 20' : '—');
      html += '</span></div>';
    }
    content_el.innerHTML = html;
  } catch(e) {
    document.getElementById('releveModalContent').innerHTML = '<div class="alert alert-err">✗ Erreur : ' + escHtml(e.message) + '</div>';
  }
}
window.voirReleve = voirReleve;

function closeReleveModal() {
  document.getElementById('releveModal').classList.remove('open');
}
window.closeReleveModal = closeReleveModal;

/* ════════════════════════════════════════════════════════
   MESSAGERIE
════════════════════════════════════════════════════════ */
async function loadConversations() {
  const items = document.getElementById('convItems');
  items.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/messaging/chat/conversations');
    if (!r.ok) throw new Error('Erreur chargement');
    const data = await r.json();
    _allConvs = Array.isArray(data) ? data : (data.conversations || data || []);
    renderConvList(_allConvs);
    updateConvBadge(_allConvs);
    // polling toutes les 10s
    if (_pollInterval) clearInterval(_pollInterval);
    _pollInterval = setInterval(async () => {
      const r2 = await api('GET', '/api/messaging/chat/conversations').catch(()=>null);
      if (r2 && r2.ok) { const d2 = await r2.json(); _allConvs = Array.isArray(d2) ? d2 : (d2.conversations || d2 || []); renderConvList(_allConvs); updateConvBadge(_allConvs); }
    }, 10000);
  } catch(e) {
    items.innerHTML = `<div style="padding:1rem;font-size:.78rem;color:var(--muted)">Impossible de charger les conversations.<br>${escHtml(e.message)}</div>`;
  }
}

function renderConvList(convs) {
  const items = document.getElementById('convItems');
  if (!items) return;
  if (!convs.length) {
    items.innerHTML = '<div style="padding:1.2rem;text-align:center;font-size:.78rem;color:var(--muted)">Aucune conversation.<br>Démarrez-en une !</div>';
    return;
  }
  items.innerHTML = convs.map(c => {
    const name = c.other_user_name || c.other_user_id || 'Utilisateur';
    const lastMsg = c.last_message || '';
    const isActive = c.conversation_id === _activeConvId;
    return `<div class="conv-item ${isActive?'active':''}" onclick="openConversation('${c.conversation_id}','${escHtml(name)}','${escHtml(c.other_user_role||'')}')">
      <div class="conv-avatar">${name[0].toUpperCase()}</div>
      <div class="conv-info">
        <div class="conv-name">${escHtml(name)}</div>
        <div class="conv-last">${escHtml(lastMsg.substring(0,40))}${lastMsg.length>40?'…':''}</div>
      </div>
    </div>`;
  }).join('');
}

async function openConversation(convId, name, role) {
  _activeConvId = convId;
  // mettre à jour l'item actif
  document.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
  const chatArea = document.getElementById('chatArea');
  chatArea.innerHTML = `
    <div class="chat-topbar">
      <div class="conv-avatar">${name[0].toUpperCase()}</div>
      <div>
        <div class="chat-topbar-name">${escHtml(name)}</div>
        <div class="chat-topbar-role">${escHtml(role||'')}</div>
      </div>
    </div>
    <div class="chat-messages" id="chatMessages"><div class="loader"></div></div>
    <div class="chat-input-area">
      <textarea id="chatMsgInput" placeholder="Écrivez votre message…" rows="1"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();sendMessage();}"></textarea>
      <button class="chat-send-btn" onclick="sendMessage()">➤</button>
    </div>`;
  await loadMessages(convId);
  // Re-highlight l'item actif
  renderConvList(_allConvs);
}

async function loadMessages(convId) {
  const box = document.getElementById('chatMessages');
  if (!box) return;
  try {
    const r = await api('GET', `/api/messaging/chat/conversations/${convId}/messages`);
    if (!r.ok) throw new Error();
    const data = await r.json();
    const msgs = data.messages || data || [];
    if (!msgs.length) {
      box.innerHTML = '<div style="text-align:center;padding:2rem;font-size:.78rem;color:var(--muted)">Aucun message. Commencez la conversation !</div>';
      return;
    }
    box.innerHTML = msgs.map(m => {
      const mine = m.sender_id === (currentUser.id || currentUser.sub);
      const time = m.created_at ? new Date(m.created_at).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'}) : '';
      return `<div class="msg-bubble ${mine?'mine':'theirs'}">
        ${escHtml(m.content||'')}
        <div class="msg-meta">${time}</div>
      </div>`;
    }).join('');
    box.scrollTop = box.scrollHeight;
  } catch {
    box.innerHTML = '<div style="text-align:center;padding:1rem;font-size:.78rem;color:var(--muted)">Erreur chargement messages.</div>';
  }
}

async function sendMessage() {
  const input = document.getElementById('chatMsgInput');
  if (!input || !_activeConvId) return;
  const content = input.value.trim();
  if (!content) return;
  input.value = '';
  input.style.height = 'auto';
  try {
    const r = await api('POST', `/api/messaging/chat/conversations/${_activeConvId}/messages`, { content });
    if (r.ok || r.status === 201) {
      await loadMessages(_activeConvId);
    } else {
      showToast('Erreur envoi message','error');
    }
  } catch { showToast('Erreur réseau','error'); }
}

function openNewConvModal() {
  document.getElementById('newConvModal').classList.add('open');
  document.getElementById('newConvTargetId').value = '';
  document.getElementById('newConvError').textContent = '';
}
window.openNewConvModal = openNewConvModal;

function closeNewConvModal() {
  document.getElementById('newConvModal').classList.remove('open');
}
window.closeNewConvModal = closeNewConvModal;

async function startNewConversation() {
  const targetId = document.getElementById('newConvTargetId').value.trim();
  const errEl = document.getElementById('newConvError');
  if (!targetId) { errEl.textContent = 'Veuillez saisir un ID utilisateur.'; return; }
  errEl.textContent = '';
  try {
    const r = await api('POST', '/api/messaging/chat/conversations', { target_user_id: targetId });
    if (r.ok || r.status === 201) {
      const conv = await r.json();
      closeNewConvModal();
      showToast('Conversation démarrée !','success');
      await loadConversations();
      openConversation(conv.conversation_id, conv.other_user_name || targetId, conv.other_user_role || '');
    } else {
      const d = await r.json().catch(()=>({}));
      errEl.textContent = d.detail || `Erreur ${r.status}`;
    }
  } catch { errEl.textContent = 'Erreur réseau.'; }
}
window.startNewConversation = startNewConversation;

function filterConvs(query) {
  const q = query.toLowerCase();
  const filtered = q ? _allConvs.filter(c => (c.other_user_name||'').toLowerCase().includes(q)) : _allConvs;
  renderConvList(filtered);
}
window.filterConvs = filterConvs;

function updateConvBadge(convs) {
  const badge = document.getElementById('unreadBadge');
  if (!badge) return;
  badge.style.display = 'none';
}

async function loadConvBadge() {
  try {
    const r = await api('GET', '/api/messaging/chat/conversations');
    if (r.ok) {
      const convs = await r.json() || [];
      const badge = document.getElementById('unreadBadge');
      if (badge && convs.length > 0) {
        badge.textContent = convs.length;
        badge.style.display = '';
      }
    }
  } catch {}
}

/* ════════════════════════════════════════════════════════
   NOTIFICATIONS
════════════════════════════════════════════════════════ */
async function loadNotifications() {
  const list = document.getElementById('notifList');
  list.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/messaging/notifications/');
    if (!r.ok) throw new Error('Erreur');
    const data = await r.json();
    const notifs = Array.isArray(data) ? data : (data.notifications || data.items || []);
    if (!notifs.length) {
      list.innerHTML = '<div class="empty"><div class="e-icon">🔔</div><p>Aucune notification pour le moment.</p></div>';
      return;
    }
    const ICONS = { 'emploi_du_temps':'📅', 'note':'📊', 'filiere':'🎓', 'message':'💬', 'default':'🔔' };
    list.innerHTML = `<div class="notif-list">${notifs.map(n => {
      const icon = ICONS[n.type] || ICONS.default;
      const time = n.created_at ? new Date(n.created_at).toLocaleString('fr-FR',{day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}) : '';
      return `<div class="notif-item ${n.is_read?'':'unread'}" onclick="markNotifRead('${n.id}','${n.created_at||''}',this)">
        <div class="notif-icon">${icon}</div>
        <div class="notif-body">
          <div class="notif-title">${escHtml(n.title||n.type||'Notification')}</div>
          <div class="notif-desc">${escHtml(n.body||n.message||'')}</div>
          <div class="notif-time">${time} ${!n.is_read?'<span class="notif-badge">Nouveau</span>':''}</div>
        </div>
      </div>`;
    }).join('')}</div>`;
    updateNotifBadge(notifs);
  } catch(e) {
    list.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div><p>Erreur chargement notifications.<br><small>${escHtml(e.message)}</small></p></div>`;
  }
}

async function markNotifRead(notifId, createdAt, el) {
  try {
    const url = `/api/messaging/notifications/${notifId}/read?created_at_iso=${encodeURIComponent(createdAt||new Date().toISOString())}`;
    await api('PUT', url);
    if (el) el.classList.remove('unread');
    const badge = el?.querySelector('.notif-badge');
    if (badge) badge.remove();
  } catch {}
}

async function markAllNotifRead() {
  try {
    const r = await api('PUT', '/api/messaging/notifications/read-all');
    if (r.ok) {
      showToast('Toutes les notifications lues ✓','success');
      document.querySelectorAll('.notif-item.unread').forEach(el => el.classList.remove('unread'));
      document.querySelectorAll('.notif-badge').forEach(el => el.remove());
      const badge = document.getElementById('notifBadge');
      if (badge) badge.style.display = 'none';
    }
  } catch { showToast('Erreur','error'); }
}

function updateNotifBadge(notifs) {
  const unread = notifs.filter(n => !n.is_read).length;
  const badge = document.getElementById('notifBadge');
  if (!badge) return;
  if (unread > 0) { badge.textContent = unread; badge.style.display = ''; }
  else badge.style.display = 'none';
}

async function loadNotifBadge() {
  try {
    const r = await api('GET', '/api/messaging/notifications/');
    if (r.ok) {
      const data = await r.json();
      updateNotifBadge(data.notifications || data || []);
    }
  } catch {}
}

/* ── UTILS ────────────────────────────────────────────────────────── */
async function doLogout() {
  if (_pollInterval) clearInterval(_pollInterval);
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

// Exposer les fonctions globales nécessaires
window.switchPanel   = switchPanel;
window.downloadFile  = downloadFile;
window.deleteFile    = deleteFile;
window.sendMessage   = sendMessage;
window.openConversation = openConversation;
window.markNotifRead = markNotifRead;