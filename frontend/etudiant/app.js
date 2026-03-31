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

function meErrMsg(status) {
  if (status === 403) return 'Accès refusé — votre compte délégué n\'a pas encore de profil étudiant dans ms-notes. Contactez l\'administration.';
  if (status === 404) return 'Profil étudiant introuvable — contactez l\'administration pour créer votre profil.';
  return 'Erreur de chargement (HTTP ' + status + ')';
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
  initChatPanel();  // affiche/masque le lien Chat selon le rôle délégué

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
  const _rlBtn = document.getElementById('submitReleveBtn');
  if (_rlBtn) _rlBtn.addEventListener('click', demanderReleve);
  loadAccueil();
  initSemestreSelects();  // peuple le select relevé dès le chargement
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
  if (id === 'releve')     initRelevePanel();
  if (id === 'notifs')     loadNotifs();
  if (id === 'chat')       loadChatConversations();
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

  // Stats modules + séances : uniquement la filière de l'étudiant connecté
  // 1. GET /api/notes/etudiant/me → { calendar_filiere_id }
  // 2. GET /api/calendar/filieres/{id}/semestres → liste des semestres
  // 3. Pour chaque semestre : modules + emploi-du-temps
  try {
    const rMe = await api('GET', '/api/notes/etudiant/me');
    if (!rMe.ok) { console.warn('Profil étudiant:', rMe.status, meErrMsg(rMe.status)); return; }
    const me = await rMe.json();
    const filiereId = me.calendar_filiere_id;

    const rSems = await api('GET', `/api/calendar/filieres/${filiereId}/semestres`);
    const sems = rSems.ok ? (await rSems.json()) : [];

    let totalModules = 0;
    let totalSeances = 0;
    for (const s of sems) {
      const [rMod, rEdt] = await Promise.all([
        api('GET', `/api/calendar/semestres/${s.id}/modules`),
        api('GET', `/api/calendar/emploi-du-temps/${s.id}`)
      ]);
      if (rMod.ok) { const mods = await rMod.json(); totalModules += (mods||[]).length; }
      if (rEdt.ok) { const edt  = await rEdt.json(); totalSeances += (edt.seances||[]).length; }
    }

    const nbMod = document.getElementById('nbModules');
    const nbSea = document.getElementById('nbSeances');
    if (nbMod) nbMod.textContent = totalModules || 0;
    if (nbSea) nbSea.textContent = totalSeances || 0;
  } catch {
    // L'étudiant n'est peut-être pas encore enregistré dans ms-notes
    const nbMod = document.getElementById('nbModules');
    const nbSea = document.getElementById('nbSeances');
    if (nbMod) nbMod.textContent = '—';
    if (nbSea) nbSea.textContent = '—';
  }

  // Également déclencher les notifs en arrière-plan pour le badge
  try {
    const rN = await api('GET', '/api/messaging/notifications/?limit=50');
    if (rN.ok) {
      const dn = await rN.json();
      const unread = (dn.notifications||[]).filter(n => !n.is_read).length;
      const navNotif = document.querySelector('[data-panel="notifs"]');
      if (navNotif && unread > 0) {
        navNotif.innerHTML = `<span class="nav-icon">🔔</span>Notifications <span style="background:#C9A84C;color:#fff;border-radius:99px;font-size:.63rem;padding:.05rem .45rem;margin-left:.3rem">${unread}</span>`;
      }
    }
  } catch {}
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
async function initNotesPanel() {
  const wrap = document.getElementById('notesContent');
  if (!wrap) return;
  // Déjà initialisé ?
  if (document.getElementById('notesSemSel')) return;

  wrap.innerHTML = '<div class="loader"></div>';

  try {
    // 1. Récupérer la filière de l'étudiant connecté
    const rMe = await api('GET', '/api/notes/etudiant/me');
    if (!rMe.ok) throw new Error(meErrMsg(rMe.status));
    const me = await rMe.json();

    // 2. Récupérer les semestres de sa filière
    const rSems = await api('GET', `/api/calendar/filieres/${me.calendar_filiere_id}/semestres`);
    const sems = rSems.ok ? await rSems.json() : [];

    // 3. Construire le sélecteur (un seul : Semestre)
    wrap.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end;margin-bottom:1.2rem;
                  padding:1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:10px">
        <div style="flex:1;min-width:200px">
          <div style="font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.35rem">
            Filière : <strong style="color:var(--dark)">${escHtml(me.prenom)} ${escHtml(me.nom)} — filière #${me.calendar_filiere_id}</strong>
          </div>
          <div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap">
            <select id="notesSemSel"
              style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:180px">
              <option value="">— Choisir un semestre —</option>
              ${(sems||[]).map(s=>`<option value="${s.id}">${escHtml(s.nom)}</option>`).join('')}
            </select>
            <button class="btn btn-gold" onclick="loadNotes()" style="padding:.45rem 1.1rem;height:36px">Afficher</button>
          </div>
        </div>
      </div>
      <div id="notesTableWrap"></div>`;

    // Auto-afficher si un seul semestre
    if ((sems||[]).length === 1) {
      document.getElementById('notesSemSel').value = sems[0].id;
      loadNotes();
    }
  } catch(e) {
    wrap.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div>
      <p>${escHtml(e.message)}</p></div>`;
  }
}

// Stubs supprimés (cascade dept/filière non nécessaire pour l'étudiant)
window.notesOnDept    = function() {};
window.notesOnFiliere = function() {};

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
async function initEmploiPanel() {
  const wrap = document.getElementById('emploiContent');
  if (!wrap) return;
  if (document.getElementById('emploiSemSel')) return;

  wrap.innerHTML = '<div class="loader"></div>';

  try {
    // Filière de l'étudiant → semestres directement
    const rMe = await api('GET', '/api/notes/etudiant/me');
    if (!rMe.ok) throw new Error(meErrMsg(rMe.status));
    const me = await rMe.json();

    const rSems = await api('GET', `/api/calendar/filieres/${me.calendar_filiere_id}/semestres`);
    const sems = rSems.ok ? await rSems.json() : [];

    wrap.innerHTML = `
      <div style="display:flex;flex-wrap:wrap;gap:.7rem;align-items:flex-end;margin-bottom:1.2rem;
                  padding:1rem;background:var(--cream);border:1.5px solid var(--border);border-radius:10px">
        <div style="flex:1;min-width:200px">
          <div style="font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-bottom:.35rem">
            Semestre à afficher
          </div>
          <div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap">
            <select id="emploiSemSel"
              style="padding:.4rem .75rem;border:1.5px solid var(--border);border-radius:7px;font-size:.84rem;min-width:180px">
              <option value="">— Choisir un semestre —</option>
              ${(sems||[]).map(s=>`<option value="${s.id}">${escHtml(s.nom)}</option>`).join('')}
            </select>
            <button class="btn btn-gold" onclick="loadEmploi()" style="padding:.45rem 1.1rem;height:36px">Afficher</button>
          </div>
        </div>
      </div>
      <div id="emploiGrid"></div>`;

    // Auto-afficher si un seul semestre
    if ((sems||[]).length === 1) {
      document.getElementById('emploiSemSel').value = sems[0].id;
      loadEmploi();
    }
  } catch(e) {
    wrap.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div><p>${escHtml(e.message)}</p></div>`;
  }
}

window.emploiOnDept    = function(){};
window.emploiOnFiliere = function(){};

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
async function showClassementForm(){
  const wrap=document.getElementById('classementContent');
  if(!wrap) return;
  wrap.innerHTML='<div class="loader"></div>';

  // Charger en parallèle : semestres de ma filière + mes demandes existantes
  let semsOpts = '<option value="">Erreur chargement</option>';
  let demandesHtml = '';
  try {
    const rMe = await api('GET', '/api/notes/etudiant/me');
    if (rMe.ok) {
      const me = await rMe.json();
      const [rSems, rDemandes] = await Promise.all([
        api('GET', `/api/calendar/filieres/${me.calendar_filiere_id}/semestres`),
        api('GET', '/api/notes/etudiant/mes-demandes-classement')
          .catch(() => ({ ok: false }))  // route optionnelle
      ]);
      if (rSems.ok) {
        const sems = await rSems.json();
        semsOpts = sems && sems.length
          ? sems.map(s => `<option value="${s.id}">${escHtml(s.nom)}</option>`).join('')
          : '<option value="">Aucun semestre</option>';
      }
      // Charger les demandes existantes via /demandes-classement/{id} n'est pas listable
      // → on garde l'historique en sessionStorage
      // Charger les demandes depuis l'API (pas sessionStorage)
      const rDem = await api('GET', '/api/notes/etudiant/mes-demandes-classement').catch(() => ({ok:false}));
      const hist = rDem.ok ? (await rDem.json()).map(d => ({
        id: d.id, semId: d.calendar_semestre_id,
        semNom: 'Semestre #' + d.calendar_semestre_id,
        type: d.type_classement, statut: d.statut
      })) : [];
      if (hist.length) {
        demandesHtml = '<div style="margin-bottom:1rem">'
          + '<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:.5rem">Mes demandes précédentes</div>'
          + hist.map(h => `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:.6rem .85rem;
                         background:var(--cream);border:1.5px solid var(--border);border-radius:8px;margin-bottom:.4rem">
              <div>
                <span style="font-weight:600;font-size:.83rem">${escHtml(h.semNom||'Semestre #'+h.semId)}</span>
                <span style="font-size:.75rem;color:var(--muted);margin-left:.4rem">${escHtml(h.type)}</span>
              </div>
              <button class="btn btn-outline btn-sm"
                onclick="verifierClassementHistorique(${h.id}, this)">↻ Voir résultat</button>
            </div>`).join('')
          + '</div>';
      }
    } else {
      semsOpts = `<option value="">${escHtml(meErrMsg(rMe.status))}</option>`;
    }
  } catch { semsOpts = '<option value="">Erreur chargement</option>'; }

  wrap.innerHTML=`
    ${demandesHtml}
    <div class="form-card" style="max-width:420px">
      <p class="form-card-desc">Demandez votre classement. L'administrateur doit d'abord l'approuver. Vous serez notifié(e) dès la décision.</p>
      <div class="form-group">
        <label>Semestre</label>
        <select id="clSemId" style="width:100%;padding:.65rem .85rem;border:1.5px solid var(--border);border-radius:8px;font-family:Jost,sans-serif">
          ${semsOpts}
        </select>
      </div>
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

// Vérifier un classement depuis l'historique sessionStorage
window.verifierClassementHistorique = async function(demandeId, btn) {
  const resEl = btn.closest('div[style]');
  btn.disabled = true; btn.textContent = '⏳';
  try {
    const r = await api('GET', `/api/notes/etudiant/demandes-classement/${demandeId}`);
    if (!r.ok) { btn.disabled=false; btn.textContent='↻ Voir résultat'; showToast('Erreur','error'); return; }
    const d = await r.json();
    if (d.statut === 'approuve') {
      const rc = await api('GET', `/api/notes/etudiant/classements/${demandeId}`);
      if (rc.ok) {
        const cl = await rc.json();
        const wrap = document.getElementById('classementContent');
        if (wrap) {
          const card = document.createElement('div');
          card.className = 'classement-card';
          card.innerHTML = `<div class="trophy">🏆</div>
            <div class="classement-rang">Rang ${cl.mon_rang ?? '—'}</div>
            <div class="classement-sub">sur ${cl.total ?? '—'} étudiants · ${escHtml(cl.scope_nom||'')}</div>
            <div class="classement-moy">Moyenne : ${cl.ma_moyenne!=null?parseFloat(cl.ma_moyenne).toFixed(2):'—'} / 20</div>`;
          wrap.insertBefore(card, wrap.firstChild);
        }
      }
    } else if (d.statut === 'rejete') {
      showToast('Demande refusée : '+(d.motif_rejet||'sans motif'), 'error');
    } else {
      showToast('Demande toujours en attente…', '');
    }
  } catch { showToast('Erreur réseau','error'); }
  btn.disabled=false; btn.textContent='↻ Voir résultat';
};

async function demanderClassement(){
  const semId=parseInt(document.getElementById('clSemId')?.value||'');
  const type=document.getElementById('clType').value;
  const res=document.getElementById('clResult');
  if(!semId||isNaN(semId)){res.innerHTML='<div class="alert alert-err">Sélectionnez un semestre.</div>';return;}
  try {
    const r=await api('POST','/api/notes/etudiant/demandes-classement',{calendar_semestre_id:semId,type_classement:type});
    if(r.ok||r.status===201){
      const d=await r.json();
      res.innerHTML=`<div class="alert alert-ok">
        ✓ Demande créée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong><br>
        <small>Vous recevrez une notification quand l'admin aura traité votre demande.</small>
        <br><button class="btn btn-outline btn-sm" style="margin-top:.5rem"
          onclick="verifierClassement(${d.id},this.parentElement)">↻ Vérifier le statut</button>
      </div>`;
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

window.verifierClassement = async function(demandeId, resEl) {
  try {
    const r = await api('GET', `/api/notes/etudiant/demandes-classement/${demandeId}`);
    if (!r.ok) { showToast('Erreur vérification','error'); return; }
    const d = await r.json();
    if (d.statut === 'approuve') {
      fetchClassementResult(demandeId, resEl);
    } else if (d.statut === 'rejete') {
      resEl.innerHTML = `<div class="alert alert-err">❌ Demande refusée. Motif : ${escHtml(d.motif_rejet||'Non précisé')}</div>`;
    } else {
      showToast('Demande toujours en attente…','');
    }
  } catch { showToast('Erreur réseau','error'); }
};

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
  if (!sem || sem === '' || isNaN(parseInt(sem))) {
    res.innerHTML='<div class="alert alert-err">Sélectionnez un semestre valide.</div>';
    return;
  }
  try {
    const r=await api('POST','/api/notes/etudiant/demandes-releve',{calendar_semestre_id:parseInt(sem)});
    if(r.ok||r.status===201){
      const d=await r.json();
      res.innerHTML=`<div class="alert alert-ok">
        ✓ Demande envoyée (ID: ${d.id}) · Statut : <strong>${d.statut}</strong><br>
        <small>Vous recevrez une notification dès que l'admin aura traité votre demande.</small>
        <br><button class="btn btn-outline btn-sm" style="margin-top:.5rem"
          onclick="verifierReleve(${d.id},this.parentElement)">↻ Vérifier le statut</button>
      </div>`;
    } else if(r.status===409){
      res.innerHTML='<div class="alert alert-ok">ℹ️ Une demande est déjà en attente pour ce semestre.</div>';
    } else {
      const d=await r.json().catch(()=>({}));
      res.innerHTML=`<div class="alert alert-err">✗ ${escHtml(d.detail||`Erreur ${r.status}`)}</div>`;
    }
  } catch{res.innerHTML='<div class="alert alert-err">✗ Erreur réseau.</div>';}
}

/* ── Panel relevé avec liste depuis l'API ───────────────────────── */
async function initRelevePanel() {
  const res = document.getElementById('releveResult');
  if (!res) return;
  res.innerHTML = '<div class="loader" style="margin:.5rem 0"></div>';
  try {
    // GET /api/notes/etudiant/mes-demandes-releve → toutes mes demandes
    const r = await api('GET', '/api/notes/etudiant/mes-demandes-releve');
    if (!r.ok) { res.innerHTML = ''; return; }
    const demandes = await r.json();
    if (!demandes || !demandes.length) { res.innerHTML = ''; return; }

    // Enrichir avec les noms de semestres depuis le calendrier
    const semIds = [...new Set(demandes.map(d => d.calendar_semestre_id))];
    const semMap = {};
    await Promise.all(semIds.map(sid =>
      api('GET', `/api/calendar/semestres/${sid}`)
        .then(r => r.ok ? r.json() : null)
        .then(s => { if (s) semMap[sid] = s.nom; })
        .catch(() => {})
    ));

    res.innerHTML = '<div style="margin-bottom:.8rem">'
      + '<div style="font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-bottom:.4rem">Mes demandes de relevé</div>'
      + demandes.map(d => {
          const semNom = semMap[d.calendar_semestre_id] || ('Semestre #' + d.calendar_semestre_id);
          const badgeClass = d.statut==='approuve'?'enseignant':d.statut==='rejete'?'admin':'etudiant';
          const date = d.demande_le ? new Date(d.demande_le).toLocaleDateString('fr-FR') : '';
          return `<div style="display:flex;align-items:center;justify-content:space-between;padding:.55rem .85rem;
                       background:var(--cream);border:1.5px solid var(--border);border-radius:8px;margin-bottom:.35rem">
            <div>
              <span style="font-weight:600;font-size:.83rem">${escHtml(semNom)}</span>
              <span class="badge badge-${badgeClass}" style="margin-left:.4rem;font-size:.68rem">${escHtml(d.statut)}</span>
              <span style="font-size:.71rem;color:var(--muted);margin-left:.4rem">${date}</span>
              ${d.motif_rejet ? `<div style="font-size:.72rem;color:crimson;margin-top:.15rem">Motif : ${escHtml(d.motif_rejet)}</div>` : ''}
            </div>
            <div style="display:flex;gap:.4rem">
              ${d.statut==='approuve'
                ? `<button class="btn btn-gold btn-sm" onclick="telechargerReleve(${d.id})">📄 PDF</button>`
                : `<button class="btn btn-outline btn-sm" onclick="initRelevePanel()">↻</button>`}
            </div>
          </div>`;
        }).join('')
      + '</div>';
  } catch { res.innerHTML = ''; }
}

window.telechargerReleve = async function(demandeId) {
  showToast('Génération du PDF…', '');
  try {
    // GET /api/notes/etudiant/releves/{id} → { demande_id, etudiant_cne, etudiant_nom, notes }
    const r = await api('GET', `/api/notes/etudiant/releves/${demandeId}`);
    if (!r.ok) {
      const d = await r.json().catch(() => ({}));
      showToast('✗ ' + (d.detail || `Erreur ${r.status}`), 'error');
      return;
    }
    const releve = await r.json();
    const notes = releve.notes || {};
    const elts  = notes.notes || [];
    const moy   = notes.moyenne_semestre != null
                  ? parseFloat(notes.moyenne_semestre).toFixed(2) : '—';

    // Construire le HTML du relevé
    const now = new Date().toLocaleDateString('fr-FR', {day:'2-digit', month:'long', year:'numeric'});
    const rows = elts.map(e =>
      `<tr>
        <td>Élément #${e.calendar_element_id}</td>
        <td style="text-align:center">${e.note != null ? parseFloat(e.note).toFixed(2) : '—'}</td>
        <td style="text-align:center">${e.note != null ? (parseFloat(e.note) >= 10 ? '✓' : '✗') : '—'}</td>
      </tr>`
    ).join('');

    const html = `<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"/>
      <title>Relevé de notes — ${escHtml(releve.etudiant_nom)}</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 40px; color: #1a1a1a; }
        h1 { color: #8B6914; font-size: 1.4rem; margin-bottom: .2rem; }
        .sub { color: #666; font-size: .85rem; margin-bottom: 1.5rem; }
        .info { display: flex; gap: 2rem; margin-bottom: 1.5rem; }
        .info div { font-size: .88rem; }
        .info strong { display: block; font-size: .7rem; text-transform: uppercase;
                       letter-spacing: .06em; color: #888; margin-bottom: .15rem; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
        th { background: #8B6914; color: #fff; padding: .5rem .7rem; text-align: left;
             font-size: .78rem; text-transform: uppercase; letter-spacing: .05em; }
        td { padding: .45rem .7rem; border-bottom: 1px solid #eee; font-size: .85rem; }
        tr:nth-child(even) td { background: #faf8f2; }
        .moy { background: #faf8f2; border: 2px solid #8B6914; border-radius: 8px;
               padding: .8rem 1.2rem; display: inline-block; margin-bottom: 1rem; }
        .moy .val { font-size: 1.5rem; font-weight: 700; color: #8B6914; }
        .footer { margin-top: 2rem; font-size: .75rem; color: #999; border-top: 1px solid #eee;
                  padding-top: .8rem; }
        @media print { .no-print { display: none; } }
      </style></head><body>
      <h1>EST Salé — Relevé de notes officiel</h1>
      <p class="sub">Généré le ${now}</p>
      <div class="info">
        <div><strong>Étudiant</strong>${escHtml(releve.etudiant_nom)}</div>
        <div><strong>CNE</strong>${escHtml(releve.etudiant_cne)}</div>
        <div><strong>N° Demande</strong>${releve.demande_id}</div>
      </div>
      <table>
        <thead><tr><th>Élément</th><th style="text-align:center">Note / 20</th><th style="text-align:center">Résultat</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div class="moy">
        <div style="font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#888;margin-bottom:.2rem">Moyenne générale</div>
        <div class="val">${moy} / 20</div>
      </div>
      <div class="footer">Document officiel — EST Salé / Université Mohammed V Rabat</div>
      <div class="no-print" style="margin-top:1.5rem;text-align:center">
        <button onclick="window.print()"
          style="padding:.6rem 1.5rem;background:#8B6914;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:.88rem">
          🖨️ Imprimer / Enregistrer en PDF
        </button>
      </div>
    </body></html>`;

    // Ouvrir dans un nouvel onglet pour impression / enregistrement PDF
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url  = URL.createObjectURL(blob);
    const win  = window.open(url, '_blank');
    if (!win) showToast('Autorisez les popups pour télécharger le PDF', 'error');
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  } catch { showToast('Erreur génération PDF', 'error'); }
};

window.verifierReleve = async function(demandeId, el) {
  try {
    const r = await api('GET', `/api/notes/etudiant/demandes-releve/${demandeId}`);
    if (!r.ok) { showToast('Erreur vérification','error'); return; }
    const d = await r.json();
    // Mettre à jour le statut dans sessionStorage
    const hist = JSON.parse(sessionStorage.getItem('releve_history')||'[]');
    const idx = hist.findIndex(h=>h.id===demandeId);
    if (idx>=0) { hist[idx].statut=d.statut; sessionStorage.setItem('releve_history',JSON.stringify(hist)); }

    if (d.statut==='approuve') {
      showToast('✅ Relevé approuvé ! Vous pouvez consulter vos notes.','success');
      if(el) el.querySelector('button').textContent='✓ Approuvé';
    } else if (d.statut==='rejete') {
      showToast('❌ Relevé refusé : '+(d.motif_rejet||'sans motif'),'error');
      if(el) el.querySelector('button').textContent='✗ Refusé';
    } else {
      showToast('Demande toujours en attente…','');
    }
    initRelevePanel();  // rafraîchir l'affichage
  } catch { showToast('Erreur réseau','error'); }
};

/* ── Peupler selects relevé/classement avec les semestres réels ─── */
async function initSemestreSelects() {
  const sel = document.getElementById('releveSelect');
  if (!sel) return;
  try {
    const rMe = await api('GET', '/api/notes/etudiant/me');
    if (!rMe.ok) {
      sel.innerHTML = '<option value="">' + meErrMsg(rMe.status) + '</option>';
      return;
    }
    const me = await rMe.json();
    const rSems = await api('GET', `/api/calendar/filieres/${me.calendar_filiere_id}/semestres`);
    if (!rSems.ok) { sel.innerHTML = '<option value="">Erreur chargement</option>'; return; }
    const sems = await rSems.json();
    if (!sems || !sems.length) {
      sel.innerHTML = '<option value="">Aucun semestre disponible</option>';
      return;
    }
    sel.innerHTML = sems.map(s => `<option value="${s.id}">${escHtml(s.nom)}</option>`).join('');
  } catch {
    sel.innerHTML = '<option value="">Erreur — réessayez</option>';
  }
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

/* ══════════════════════════════════════════════════════════════════
   NOTIFICATIONS
══════════════════════════════════════════════════════════════════ */
window.loadNotifs = async function() {
  const wrap = document.getElementById('notifsList');
  if (!wrap) return;
  wrap.innerHTML = '<div class="loader"></div>';
  try {
    const r = await api('GET', '/api/messaging/notifications/');
    if (!r.ok) throw new Error(r.status);
    const d = await r.json();
    const list = d.notifications || [];
    if (!list.length) {
      wrap.innerHTML = '<div class="empty"><div class="e-icon">🔔</div><p>Aucune notification.</p></div>';
      return;
    }
    wrap.innerHTML = list.map(n => `
      <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotifRead('${n.notification_id}','${n.created_at}',this)">
        <div class="notif-dot ${n.is_read ? 'read' : ''}"></div>
        <div>
          <div class="notif-title">${escHtml(n.title || n.type)}</div>
          <div class="notif-meta">${escHtml(n.content || '')}</div>
          <div class="notif-meta" style="margin-top:.2rem;opacity:.7">${n.created_at ? new Date(n.created_at).toLocaleString('fr-FR') : ''}</div>
        </div>
      </div>`).join('');
  } catch(e) {
    wrap.innerHTML = `<div class="empty"><div class="e-icon">⚠️</div><p>Notifications indisponibles (${escHtml(e.message)})</p></div>`;
  }
};

window.markNotifRead = async function(id, createdAt, el) {
  try {
    await api('PUT', `/api/messaging/notifications/${id}/read?created_at_iso=${encodeURIComponent(createdAt)}`);
    if (el) { el.classList.remove('unread'); el.querySelector('.notif-dot')?.classList.add('read'); }
  } catch {}
};

window.markAllNotifsRead = async function() {
  try {
    await api('PUT', '/api/messaging/notifications/read-all');
    showToast('Toutes les notifications marquées lues ✓', 'success');
    loadNotifs();
  } catch { showToast('Erreur','error'); }
};

/* ══════════════════════════════════════════════════════════════════
   CHAT DÉLÉGUÉ  (visible seulement si role = delegue)
══════════════════════════════════════════════════════════════════ */
var _chatSelectedUser = null;
var _chatUsersCache   = {};
var _chatPollTimer    = null;
var _activeChatConvId = null;
var _chatSearchTimer  = null;

function initChatPanel() {
  // Afficher le nav item chat seulement si délégué
  const isDelegue = (currentUser.roles || []).includes('delegue');
  const chatNav = document.getElementById('chatNavItem');
  if (chatNav) chatNav.style.display = isDelegue ? '' : 'none';
  if (isDelegue) loadChatConversations();
}

window.loadChatConversations = async function() {
  const wrap = document.getElementById('convItems');
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
      `<div class="conv-item" onclick="openChatConv('${c.conversation_id}','${escHtml(c.other_user_name||'?')}')">
        <div class="conv-avatar">${(c.other_user_name||'?')[0].toUpperCase()}</div>
        <div>
          <div class="conv-name">${escHtml(c.other_user_name||'—')}</div>
          <div class="conv-last">${c.last_message_at ? new Date(c.last_message_at).toLocaleDateString('fr-FR') : 'Aucun message'}</div>
        </div>
      </div>`
    ).join('');
  } catch(e) {
    wrap.innerHTML = `<div style="padding:1rem;color:var(--muted);font-size:.82rem;text-align:center">⚠ Chat indisponible<br><button class="btn btn-outline btn-sm" style="margin-top:.5rem" onclick="loadChatConversations()">↻ Réessayer</button></div>`;
  }
};

window.openChatConv = function(convId, convName) {
  _activeChatConvId = convId;
  const area = document.getElementById('chatArea');
  area.innerHTML =
    `<div class="chat-header"><div class="conv-avatar" style="width:32px;height:32px;font-size:.85rem">${convName[0].toUpperCase()}</div><strong>${escHtml(convName)}</strong></div>`
    + `<div id="msgsWrap"></div>`
    + `<div class="chat-input-row"><input type="text" id="msgInput" placeholder="Écrire un message…"/><button class="btn btn-gold" onclick="sendChatMsg('${convId}')">Envoyer</button></div>`;
  document.getElementById('msgInput').onkeydown = e => { if (e.key === 'Enter') sendChatMsg(convId); };
  fetchChatMessages(convId);
  clearInterval(_chatPollTimer);
  _chatPollTimer = setInterval(() => fetchChatMessages(convId), 5000);
};

async function fetchChatMessages(convId) {
  const wrap = document.getElementById('msgsWrap');
  if (!wrap) { clearInterval(_chatPollTimer); return; }
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

window.sendChatMsg = async function(convId) {
  const input = document.getElementById('msgInput');
  const content = input ? input.value.trim() : '';
  if (!content) return;
  input.value = '';
  try {
    const r = await api('POST', `/api/messaging/chat/conversations/${convId}/messages`, { content });
    if (r.ok || r.status === 201) fetchChatMessages(convId);
    else { input.value = content; showToast('Erreur envoi', 'error'); }
  } catch { input.value = content; showToast('Erreur réseau', 'error'); }
};

/* ── Modal nouvelle conv (délégué → enseignant) ─────────────────── */
window.openChatModal = function() {
  _chatSelectedUser = null;
  const btn = document.getElementById('btnStartChat');
  if (btn) btn.disabled = true;
  const list = document.getElementById('chatUserList');
  if (list) list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Tapez pour chercher…</div>';
  const inp = document.getElementById('chatSearchInput');
  if (inp) inp.value = '';
  document.getElementById('chatModalOverlay').style.display = 'flex';
};

window.closeChatModal = function() {
  document.getElementById('chatModalOverlay').style.display = 'none';
};

window.chatSearchUsers = function(q) {
  clearTimeout(_chatSearchTimer);
  const list = document.getElementById('chatUserList');
  if (!q || q.length < 2) {
    list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Tapez au moins 2 caractères…</div>';
    return;
  }
  list.innerHTML = '<div class="loader" style="margin:.6rem auto"></div>';
  _chatSearchTimer = setTimeout(async () => {
    try {
      const q2 = q.toLowerCase();
      const myId = (currentUser && currentUser.id) || '';

      // Étape 1 : récupérer la filière du délégué depuis ms-notes
      const rMe = await api('GET', '/api/notes/etudiant/me');
      const meData = rMe.ok ? (await rMe.json()) : null;
      const filiereId = meData ? meData.calendar_filiere_id : null;

      // Étape 2 : récupérer les enseignants de cette filière depuis ms-calendar
      let enseignants = [];
      if (filiereId) {
        const rEns = await api('GET', `/api/calendar/filieres/${filiereId}/enseignants`);
        enseignants = rEns.ok ? (await rEns.json()) : [];
      } else {
        // Fallback : tous les enseignants du calendrier
        const rEns = await api('GET', '/api/calendar/enseignants');
        enseignants = rEns.ok ? (await rEns.json()) : [];
      }

      const filtered = enseignants.filter(e =>
        e.user_id && e.user_id !== myId && (
          (e.nom || '').toLowerCase().includes(q2) ||
          (e.prenom || '').toLowerCase().includes(q2)
        )
      );
      if (!filtered.length) {
        list.innerHTML = '<div style="padding:.8rem;text-align:center;color:var(--muted);font-size:.82rem">Aucun enseignant trouvé.</div>';
        return;
      }
      _chatUsersCache = {};
      list.innerHTML = filtered.map(e => {
        const name = `${e.prenom || ''} ${e.nom || ''}`.trim() || `Enseignant #${e.id}`;
        const uid = e.user_id || '';
        const peutChatter = e.peut_chatter && uid;
        if (peutChatter) {
          _chatUsersCache[uid] = { id: uid, name, roles: ['enseignant'] };
        }
        return `<div ${peutChatter ? `onclick="selectChatUser('${uid}')"` : ''} data-uid="${uid}"
          style="padding:.6rem 1rem;${peutChatter ? 'cursor:pointer;' : 'opacity:.5;cursor:not-allowed;'}border-bottom:1px solid var(--border);display:flex;gap:.65rem;align-items:center">
          <div style="width:32px;height:32px;border-radius:50%;background:${peutChatter ? 'var(--gold,#C9A84C)' : 'var(--border)'};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;flex-shrink:0">${name[0].toUpperCase()}</div>
          <div>
            <div style="font-weight:600;font-size:.83rem">${escHtml(name)}</div>
            <div style="font-size:.71rem;color:var(--muted)">
              ${peutChatter ? 'Enseignant · Disponible pour le chat' : 'Enseignant · Compte non lié — contacter l\'admin'}
            </div>
          </div>
        </div>`;
      }).join('');
    } catch {
      list.innerHTML = '<div style="padding:.8rem;text-align:center;color:crimson;font-size:.82rem">Erreur de chargement.</div>';
    }
  }, 350);
};

window.selectChatUser = function(id) {
  _chatSelectedUser = _chatUsersCache[id];
  if (!_chatSelectedUser) return;
  document.querySelectorAll('#chatUserList [data-uid]').forEach(el =>
    el.style.background = el.dataset.uid === id ? 'var(--cream,#FAF8F2)' : ''
  );
  const btn = document.getElementById('btnStartChat');
  if (btn) btn.disabled = false;
};

window.startChatConv = async function() {
  if (!_chatSelectedUser) return;
  const btn = document.getElementById('btnStartChat');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ …'; }
  try {
    const r = await api('POST', '/api/messaging/chat/conversations', {
      target_user_id:    _chatSelectedUser.id,
      target_user_name:  _chatSelectedUser.name,
      target_user_roles: _chatSelectedUser.roles,
    });
    if (r.ok || r.status === 201) {
      const d = await r.json();
      closeChatModal();
      loadChatConversations();
      openChatConv(d.conversation_id, _chatSelectedUser.name);
      showToast('Conversation démarrée ✓', 'success');
    } else {
      const d = await r.json().catch(() => ({}));
      showToast('✗ ' + (d.detail || `Erreur ${r.status}`), 'error');
    }
  } catch { showToast('Erreur réseau', 'error'); }
  finally { if (btn) { btn.disabled = false; btn.textContent = 'Démarrer'; } }
};

// Afficher le nav chat selon rôle — appelé après DOMContentLoaded dans le bloc principal
// (initChatPanel est défini plus haut et appelé dans addEventListener DOMContentLoaded)
