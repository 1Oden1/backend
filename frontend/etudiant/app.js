/* ═══════════════════════════════════════════════════════════════
   ENT Salé — Étudiant · app.js  (routes vérifiées sur backend réel)
═══════════════════════════════════════════════════════════════ */
'use strict';

const token   = localStorage.getItem('access_token');
const userStr = localStorage.getItem('user');
if (!token || !userStr) { localStorage.clear(); location.href = '/login/'; }
let currentUser = {};
try { currentUser = JSON.parse(userStr); } catch { location.href = '/login/'; }

function api(method, path, body) {
  const opts = { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  return fetch(path, opts).then(r => { if (r.status === 401) { localStorage.clear(); location.href = '/login/'; } return r; });
}

const JOURS = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
const FILE_ICONS  = { cours:'📖', td:'✏️', tp:'🔬', examen:'📝', autre:'📄' };
const TAG_CLASSES = { cours:'tag-cours', td:'tag-td', tp:'tag-tp', examen:'tag-examen', autre:'tag-autre' };
const PANEL_TITLES = { accueil:'Accueil', cours:'Cours & Fichiers', notes:'Mes Notes',
                       emploi:'Emploi du temps', releve:'Relevé de notes', classement:'Mon classement' };

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ── INIT ─────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const name = currentUser.first_name || currentUser.username || 'Étudiant';
  document.getElementById('userNameEl').textContent  = name;
  document.getElementById('avatarEl').textContent    = name[0].toUpperCase();
  document.getElementById('welcomeName').textContent = name;
  const dateStr = new Date().toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  document.getElementById('topbarDate').textContent  = dateStr;
  document.getElementById('welcomeDate').textContent = dateStr;

  document.querySelectorAll('.nav-item').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault(); switchPanel(el.dataset.panel, el); }));
  document.querySelectorAll('.link-more[data-panel]').forEach(el =>
    el.addEventListener('click', e => { e.preventDefault();
      switchPanel(el.dataset.panel, document.querySelector(`.nav-item[data-panel="${el.dataset.panel}"]`)); }));
  document.querySelectorAll('.filter-btn').forEach(btn =>
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active'); loadFiles(btn.dataset.cat);
    }));
  document.getElementById('logoutBtn').addEventListener('click', doLogout);
  document.getElementById('submitReleveBtn').addEventListener('click', demanderReleve);
  loadAccueil();
});

function switchPanel(id, navEl) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  const t = document.getElementById('panel-' + id);
  if (t) t.classList.add('active');
  document.getElementById('topbarTitle').textContent = PANEL_TITLES[id] || id;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (navEl) navEl.classList.add('active');
  if (id === 'cours')      loadFiles('');
  if (id === 'notes')      initNotesPanel();
  if (id === 'emploi')     initEmploiPanel();
  if (id === 'classement') showClassementForm();
}

/* ── ACCUEIL ──────────────────────────────────────────────────────── */
async function loadAccueil() {
  const grid = document.getElementById('recentGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/download/');
    if (!r.ok) throw new Error();
    const d = await r.json();
    const files = d.files || [];
    const nbEl = document.getElementById('nbFiles');
    if (nbEl) nbEl.textContent = d.total || files.length;
    renderCards(files.slice(0, 6), grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Erreur de chargement</p></div>'; }
}

/* ── FICHIERS ─────────────────────────────────────────────────────── */
async function loadFiles(cat) {
  const grid = document.getElementById('allFilesGrid');
  if (!grid) return;
  grid.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', cat ? `/api/download/?category=${cat}` : '/api/download/');
    if (!r.ok) throw new Error();
    const d = await r.json();
    renderCards(d.files || [], grid);
  } catch { grid.innerHTML = '<div class="empty"><div class="e-icon">⚠️</div><p>Impossible de charger</p></div>'; }
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
      <div class="fc-meta">${escHtml(f.module||'')} · ${escHtml(f.owner_name||'')}</div>
      <button class="btn btn-gold" style="width:100%;font-size:.74rem;padding:.48rem"
        onclick="downloadFile('${f.file_id}')">↓ Télécharger</button>
    </div>`).join('');
}

async function downloadFile(fileId) {
  try {
    const r = await api('GET', `/api/download/${fileId}`);
    if (r.ok) { const d = await r.json(); window.open(d.download_url,'_blank'); }
    else showToast('Lien indisponible','error');
  } catch { showToast('Erreur réseau','error'); }
}

/* ── NOTES ─ Cascade Département → Filière → Semestre ─────────────── */
function initNotesPanel() {
  const wrap = document.getElementById('notesContent');
  if (!wrap || document.getElementById('notesDeptSel')) return;
  wrap.innerHTML = `
    <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end;margin-bottom:1.2rem;
                padding:1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:10px">
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Département</label>
        <select id="notesDeptSel" onchange="notesOnDept()"
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Filière</label>
        <select id="notesFiliereSel" onchange="notesOnFiliere()" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Semestre</label>
        <select id="notesSemSel" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <button class="btn btn-gold" onclick="loadNotes()" style="padding:.45rem 1.1rem;height:36px">Afficher</button>
    </div>
    <div id="notesTableWrap"></div>`;

  api('GET','/api/calendar/departements').then(r=>r.ok?r.json():[]).then(list=>{
    const sel=document.getElementById('notesDeptSel');
    (list||[]).forEach(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=d.nom;sel.appendChild(o);});
  });
}

window.notesOnDept = function() {
  const dId=parseInt(document.getElementById('notesDeptSel').value);
  const fSel=document.getElementById('notesFiliereSel'), sSel=document.getElementById('notesSemSel');
  fSel.innerHTML='<option value="">— Choisir —</option>'; sSel.innerHTML='<option value="">— Choisir —</option>';
  fSel.disabled=true; sSel.disabled=true;
  if(isNaN(dId)) return;
  api('GET',`/api/calendar/departements/${dId}/filieres`).then(r=>r.ok?r.json():[]).then(list=>{
    fSel.disabled=false;
    (list||[]).forEach(f=>{const o=document.createElement('option');o.value=f.id;o.textContent=f.nom;fSel.appendChild(o);});
  });
};
window.notesOnFiliere = function() {
  const fId=parseInt(document.getElementById('notesFiliereSel').value);
  const sSel=document.getElementById('notesSemSel');
  sSel.innerHTML='<option value="">— Choisir —</option>'; sSel.disabled=true;
  if(isNaN(fId)) return;
  api('GET',`/api/calendar/filieres/${fId}/semestres`).then(r=>r.ok?r.json():[]).then(list=>{
    sSel.disabled=false;
    (list||[]).forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.nom;sSel.appendChild(o);});
    if((list||[]).length===1) sSel.value=list[0].id;
  });
};

window.loadNotes = async function() {
  const semId=parseInt(document.getElementById('notesSemSel')?.value);
  const wrap=document.getElementById('notesTableWrap');
  if(!wrap) return;
  if(isNaN(semId)){wrap.innerHTML='<div class="empty"><div class="e-icon">📊</div><p>Sélectionnez un semestre.</p></div>';return;}
  wrap.innerHTML='<div class="loader"></div>';
  try {
    const [rMods, rNotes] = await Promise.all([
      api('GET',`/api/calendar/semestres/${semId}/modules`),
      api('GET',`/api/notes/etudiant/notes/${semId}`)
    ]);
    if(!rNotes.ok){
      const d=await rNotes.json().catch(()=>({}));
      wrap.innerHTML=`<div class="empty"><div class="e-icon">📊</div><p>${escHtml(d.detail||'Notes non disponibles.')}</p></div>`;
      return;
    }
    const notesData=await rNotes.json();
    const modules=rMods.ok?(await rMods.json()):[];

    // Construire map elementId → {nom, type, moduleNom, coeff}
    const elemMap={};
    await Promise.all(modules.map(m=>
      api('GET',`/api/calendar/modules/${m.id}/elements`).then(r=>r.ok?r.json():[]).then(els=>{
        (els||[]).forEach(e=>{elemMap[e.id]={nom:e.nom,type:e.type,moduleNom:m.nom,coeff:e.coefficient||1};});
      }).catch(()=>{})
    ));

    const moy=notesData.moyenne_semestre!=null?parseFloat(notesData.moyenne_semestre):null;
    const elts=notesData.notes||[];
    let html='';

    if(moy!==null){
      const cls=moy>=12?'note-ok':moy>=10?'note-mid':'note-fail';
      html+=`<div class="moy-card"><div>
        <div class="moy-label">Moyenne générale du semestre</div>
        <div class="moy-val ${cls}">${moy.toFixed(2)} / 20</div>
      </div><div class="moy-icon">${moy>=12?'🏆':moy>=10?'📈':'📉'}</div></div>`;
    }

    if(elts.length){
      // Grouper par module
      const byMod={};
      elts.forEach(e=>{
        const info=elemMap[e.calendar_element_id]||{nom:`Élément #${e.calendar_element_id}`,type:'—',moduleNom:'—',coeff:1};
        (byMod[info.moduleNom]=byMod[info.moduleNom]||[]).push({...e,...info});
      });
      html+='<div class="table-wrap"><table><thead><tr><th>Module</th><th>Élément</th><th>Type</th><th>Coeff.</th><th>Note / 20</th><th>Résultat</th></tr></thead><tbody>';
      Object.entries(byMod).forEach(([modNom,items])=>{
        items.forEach((e,i)=>{
          const n=e.note!=null?parseFloat(e.note):null;
          const cls=n===null?'':n>=12?'note-ok':n>=10?'note-mid':'note-fail';
          html+=`<tr>
            ${i===0?`<td rowspan="${items.length}" style="font-weight:600;vertical-align:top">${escHtml(modNom)}</td>`:''}
            <td>${escHtml(e.nom)}</td>
            <td><span style="font-size:.76rem;background:var(--cream);border:1px solid var(--border);border-radius:4px;padding:.1rem .4rem">${escHtml(e.type)}</span></td>
            <td style="text-align:center">${e.coeff||1}</td>
            <td><strong class="${cls}">${n!==null?n.toFixed(2):'—'}</strong></td>
            <td>${n===null?'—':n>=10?'<span class="note-ok">✓ Validé</span>':'<span class="note-fail">✗ Non validé</span>'}</td>
          </tr>`;
        });
      });
      html+='</tbody></table></div>';
    } else {
      html+='<div class="empty"><div class="e-icon">📊</div><p>Aucune note enregistrée pour ce semestre.</p></div>';
    }
    wrap.innerHTML=html;
  } catch(err){
    wrap.innerHTML=`<div class="empty"><div class="e-icon">⚠️</div><p>Erreur : ${escHtml(err.message)}</p></div>`;
  }
};

/* ── EMPLOI DU TEMPS ─ Cascade puis GET /api/calendar/emploi-du-temps/{id} ── */
function initEmploiPanel() {
  const wrap=document.getElementById('emploiContent');
  if(!wrap||document.getElementById('emploiDeptSel')) return;
  wrap.innerHTML=`
    <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end;margin-bottom:1.2rem;
                padding:1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:10px">
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Département</label>
        <select id="emploiDeptSel" onchange="emploiOnDept()"
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Filière</label>
        <select id="emploiFiliereSel" onchange="emploiOnFiliere()" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <div><label style="display:block;font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.25rem">Semestre</label>
        <select id="emploiSemSel" disabled
          style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:150px">
          <option value="">— Choisir —</option></select></div>
      <button class="btn btn-gold" onclick="loadEmploi()" style="padding:.45rem 1.1rem;height:36px">Afficher</button>
    </div>
    <div id="emploiGrid"></div>`;

  api('GET','/api/calendar/departements').then(r=>r.ok?r.json():[]).then(list=>{
    const sel=document.getElementById('emploiDeptSel');
    (list||[]).forEach(d=>{const o=document.createElement('option');o.value=d.id;o.textContent=d.nom;sel.appendChild(o);});
  });
}

window.emploiOnDept = function(){
  const dId=parseInt(document.getElementById('emploiDeptSel').value);
  const fSel=document.getElementById('emploiFiliereSel'),sSel=document.getElementById('emploiSemSel');
  fSel.innerHTML='<option value="">— Choisir —</option>';sSel.innerHTML='<option value="">— Choisir —</option>';
  fSel.disabled=true;sSel.disabled=true;
  if(isNaN(dId)) return;
  api('GET',`/api/calendar/departements/${dId}/filieres`).then(r=>r.ok?r.json():[]).then(list=>{
    fSel.disabled=false;
    (list||[]).forEach(f=>{const o=document.createElement('option');o.value=f.id;o.textContent=f.nom;fSel.appendChild(o);});
  });
};
window.emploiOnFiliere = function(){
  const fId=parseInt(document.getElementById('emploiFiliereSel').value);
  const sSel=document.getElementById('emploiSemSel');
  sSel.innerHTML='<option value="">— Choisir —</option>';sSel.disabled=true;
  if(isNaN(fId)) return;
  api('GET',`/api/calendar/filieres/${fId}/semestres`).then(r=>r.ok?r.json():[]).then(list=>{
    sSel.disabled=false;
    (list||[]).forEach(s=>{const o=document.createElement('option');o.value=s.id;o.textContent=s.nom;sSel.appendChild(o);});
    if((list||[]).length===1) sSel.value=list[0].id;
  });
};

window.loadEmploi = async function(){
  const semId=parseInt(document.getElementById('emploiSemSel')?.value);
  const grid=document.getElementById('emploiGrid');
  if(!grid) return;
  if(isNaN(semId)){grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Sélectionnez un semestre.</p></div>';return;}
  grid.innerHTML='<div class="loader"></div>';
  try {
    // GET /api/calendar/emploi-du-temps/{semestre_id}
    // → EmploiDuTemps { departement, filiere, annee, semestre, seances:[SeanceRead] }
    // SeanceRead : { jour, heure_debut, heure_fin, element_module, type_seance, module, enseignant_nom, enseignant_prenom, salle }
    const r=await api('GET',`/api/calendar/emploi-du-temps/${semId}`);
    if(!r.ok){
      const d=await r.json().catch(()=>({}));
      grid.innerHTML=`<div class="empty"><div class="e-icon">📅</div><p>${escHtml(d.detail||'Emploi du temps non disponible.')}</p></div>`;
      return;
    }
    const data=await r.json();
    const seances=data.seances||[];
    if(!seances.length){
      grid.innerHTML='<div class="empty"><div class="e-icon">📅</div><p>Aucune séance planifiée pour ce semestre.</p></div>';
      return;
    }
    let html=`<div style="padding:.6rem 1rem;background:var(--cream);border:1.5px solid var(--border);
      border-radius:8px;margin-bottom:1rem;font-size:.83rem;color:var(--muted)">
      🏛️ ${escHtml(data.departement||'')} &nbsp;·&nbsp; 🎓 ${escHtml(data.filiere||'')}
      &nbsp;·&nbsp; 📆 ${escHtml(data.annee||'')} &nbsp;·&nbsp; 📘 ${escHtml(data.semestre||'')}
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
              📍 ${escHtml(s.salle||'—')} &nbsp;·&nbsp; 👤 ${escHtml(s.enseignant_prenom||'')} ${escHtml(s.enseignant_nom||'')}
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

/* ── CLASSEMENT ───────────────────────────────────────────────────── */
function showClassementForm(){
  const wrap=document.getElementById('classementContent');
  if(!wrap) return;
  wrap.innerHTML=`
    <div class="form-card" style="max-width:420px">
      <p class="form-card-desc">Demandez votre classement. L'administrateur doit d'abord l'approuver.</p>
      <div class="form-group"><label>ID Semestre (calendrier)</label>
        <input type="number" id="clSemId" placeholder="ex: 1" min="1"
          style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif"/></div>
      <div class="form-group"><label>Type</label>
        <select id="clType" style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif">
          <option value="filiere">Par filière</option>
          <option value="departement">Par département</option>
        </select></div>
      <button class="btn btn-gold" id="submitClassBtn" style="width:100%;padding:.72rem;margin-top:.5rem">Envoyer la demande</button>
      <div id="clResult" style="margin-top:1rem"></div>
    </div>`;
  document.getElementById('submitClassBtn').addEventListener('click', demanderClassement);
}

async function demanderClassement(){
  const semId=parseInt(document.getElementById('clSemId').value);
  const type=document.getElementById('clType').value;
  const res=document.getElementById('clResult');
  if(!semId){res.innerHTML='<div class="alert alert-err">Semestre ID requis.</div>';return;}
  try {
    const r=await api('POST','/api/notes/etudiant/demandes-classement',{calendar_semestre_id:semId,type_classement:type});
    if(r.ok||r.status===201){
      const d=await r.json();
      res.innerHTML=`<div class="alert alert-ok">✓ Demande créée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong><br>
        <small>Une fois approuvée, votre classement apparaîtra ici.</small></div>`;
      if(d.statut==='approuve') fetchClassementResult(d.id,res);
    } else if(r.status===409){
      const d=await r.json().catch(()=>({}));
      res.innerHTML=`<div class="alert alert-ok">ℹ️ ${escHtml(d.detail||'Demande déjà en attente.')}</div>`;
    } else {
      const d=await r.json().catch(()=>({}));
      res.innerHTML=`<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch{res.innerHTML='<div class="alert alert-err">✗ Erreur réseau.</div>';}
}

async function fetchClassementResult(demandeId,resEl){
  try {
    const r=await api('GET',`/api/notes/etudiant/classements/${demandeId}`);
    if(r.ok){
      const d=await r.json();
      resEl.innerHTML=`<div class="classement-card">
        <div class="trophy">🏆</div>
        <div class="classement-rang">Rang ${d.mon_rang??'—'}</div>
        <div class="classement-sub">sur ${d.total??'—'} étudiants · ${escHtml(d.scope_nom||'')}</div>
        <div class="classement-moy">Moyenne : ${d.ma_moyenne!=null?parseFloat(d.ma_moyenne).toFixed(2):'—'} / 20</div>
      </div>`;
    }
  } catch{}
}

/* ── RELEVÉ ───────────────────────────────────────────────────────── */
async function demanderReleve(){
  const sem=document.getElementById('releveSelect').value;
  const res=document.getElementById('releveResult');
  try {
    const r=await api('POST','/api/notes/etudiant/demandes-releve',{calendar_semestre_id:parseInt(sem)});
    if(r.ok||r.status===201){
      const d=await r.json();
      res.innerHTML=`<div class="alert alert-ok">✓ Demande envoyée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong></div>`;
    } else if(r.status===409){
      res.innerHTML='<div class="alert alert-ok">ℹ️ Une demande est déjà en attente pour ce semestre.</div>';
    } else {
      const d=await r.json().catch(()=>({}));
      res.innerHTML=`<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch{res.innerHTML='<div class="alert alert-err">✗ Erreur réseau.</div>';}
}

/* ── UTILS ────────────────────────────────────────────────────────── */
async function doLogout(){
  const rt=localStorage.getItem('refresh_token');
  if(rt){try{await api('POST','/api/auth/logout',{refresh_token:rt});}catch{}}
  localStorage.clear();location.href='/login/';
}
let _toastTimer;
function showToast(msg,type=''){
  const t=document.getElementById('toast');
  if(!t) return;
  t.textContent=msg;t.className='toast show '+type;
  clearTimeout(_toastTimer);_toastTimer=setTimeout(()=>{t.className='toast';},3200);
}
