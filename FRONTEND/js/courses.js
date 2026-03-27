// ── courses.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';

// USER INFO
document.getElementById('user-name').textContent = username || 'Utilisateur';
const roleLabels = { admin: '⚙️ Administrateur', enseignant: '👨‍🏫 Enseignant', teacher: '👨‍🏫 Enseignant', etudiant: '🎓 Étudiant' };
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';

if (['enseignant', 'teacher', 'admin'].includes(role)) {
  document.querySelectorAll('.enseignant-only').forEach(el => el.style.display = 'flex');
}
if (role === 'admin') {
  document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');
}

let allCourses = [];
let selectedFile = null;

async function loadCourses() {
  try {
    const res  = await fetch('/api/download/courses/', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    const data = await res.json();
    allCourses = data;
    document.getElementById('total-cours').textContent = data.length;

    const filieres = [...new Set(data.map(c => c.filiere).filter(Boolean))];
    const sel = document.getElementById('filter-filiere');
    filieres.forEach(f => {
      const opt = document.createElement('option');
      opt.value = f; opt.textContent = f;
      sel.appendChild(opt);
    });

    renderCourses(data);
  } catch(e) {
    document.getElementById('courses-container').innerHTML =
      '<div class="empty-state"><div class="empty-icon">⚠️</div><h3>Erreur de chargement</h3><p>Impossible de récupérer les cours.</p></div>';
  }
}

async function renderCourses(courses) {
  const container = document.getElementById('courses-container');

  if (courses.length === 0) {
    container.innerHTML = '<div class="courses-grid"><div class="empty-state"><div class="empty-icon">📭</div><h3>Aucun cours disponible</h3><p>Aucun cours pour cette sélection.</p></div></div>';
    return;
  }

  let totalFiles = 0;
  const coursesWithFiles = await Promise.all(courses.map(async (cours) => {
    try {
      const res  = await fetch('/api/download/courses/' + cours.id, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      totalFiles += (data.files || []).length;
      return Object.assign({}, cours, { files: data.files || [] });
    } catch {
      return Object.assign({}, cours, { files: [] });
    }
  }));

  document.getElementById('total-files').textContent = totalFiles;

  const icons = ['📘','📗','📙','📕','📓','📔'];
  let html = '<div class="courses-grid">';
  coursesWithFiles.forEach((cours, i) => {
    const filesHtml = cours.files.length > 0 ? (
      '<div class="course-files"><div class="course-files-title">Fichiers</div>' +
      cours.files.map(f =>
        '<div class="file-item" onclick="downloadFile(\'' + f.file_id + '\',\'' + f.original_name + '\')">' +
        '<span class="file-icon">' + getFileIcon(f.original_name) + '</span>' +
        '<span class="file-name">' + f.original_name + '</span>' +
        '<button class="file-download">⬇ Télécharger</button></div>'
      ).join('') + '</div>'
    ) : '';

    html += '<div class="course-card" style="animation-delay:' + (i * 0.06) + 's">' +
      '<div class="course-header">' +
      '<div class="course-icon">' + icons[i % icons.length] + '</div>' +
      '<div class="course-title">' + cours.titre + '</div>' +
      '<div class="course-filiere">' + (cours.filiere || '') + (cours.niveau ? ' · ' + cours.niveau : '') + '</div>' +
      '</div>' +
      '<div class="course-body">' +
      '<div class="course-meta">' +
      (cours.enseignant ? '<div class="course-meta-item">👨‍🏫 ' + cours.enseignant + '</div>' : '') +
      '<div class="course-meta-item">📄 ' + cours.files.length + ' fichier' + (cours.files.length > 1 ? 's' : '') + '</div>' +
      '</div>' +
      (cours.description ? '<div class="course-description">' + cours.description + '</div>' : '') +
      filesHtml +
      '</div></div>';
  });
  html += '</div>';
  container.innerHTML = html;
}

function getFileIcon(name) {
  if (!name) return '📄';
  const ext = name.split('.').pop().toLowerCase();
  const map = { pdf:'📕', docx:'📘', doc:'📘', pptx:'📙', ppt:'📙', xlsx:'📗', zip:'📦', rar:'📦', mp4:'🎬', mp3:'🎵' };
  return map[ext] || '📄';
}

async function downloadFile(fileId, fileName) {
  try {
    showToast('⏳ Téléchargement en cours...', 'success');
    const res = await fetch('/api/download/files/' + fileId + '/stream', {
      headers: { 'Authorization': 'Bearer ' + token }
    });
    if (!res.ok) throw new Error();
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    a.click();
    URL.revokeObjectURL(url);
    showToast('✅ ' + fileName + ' téléchargé !', 'success');
  } catch(e) {
    showToast('❌ Erreur lors du téléchargement', 'error');
  }
}

function filterCourses() {
  const search  = document.getElementById('search-input').value.toLowerCase();
  const filiere = document.getElementById('filter-filiere').value;
  const niveau  = document.getElementById('filter-niveau').value;
  const filtered = allCourses.filter(c => {
    const matchSearch  = !search  || c.titre.toLowerCase().includes(search) || (c.description || '').toLowerCase().includes(search);
    const matchFiliere = !filiere || c.filiere === filiere;
    const matchNiveau  = !niveau  || c.niveau === niveau;
    return matchSearch && matchFiliere && matchNiveau;
  });
  renderCourses(filtered);
}

function openModal()  { document.getElementById('upload-modal').classList.add('open'); }
function closeModal() {
  document.getElementById('upload-modal').classList.remove('open');
  document.getElementById('upload-titre').value   = '';
  document.getElementById('upload-desc').value    = '';
  document.getElementById('upload-filiere').value = '';
  document.getElementById('upload-niveau').value  = '';
  document.getElementById('selected-file').style.display = 'none';
  selectedFile = null;
}

function handleFileSelect(e) { if (e.target.files[0]) setSelectedFile(e.target.files[0]); }
function handleDragOver(e)   { e.preventDefault(); document.getElementById('drop-zone').classList.add('dragover'); }
function handleDragLeave(e)  { document.getElementById('drop-zone').classList.remove('dragover'); }
function handleDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('dragover');
  if (e.dataTransfer.files[0]) setSelectedFile(e.dataTransfer.files[0]);
}
function setSelectedFile(file) {
  selectedFile = file;
  document.getElementById('selected-file-name').textContent = file.name + ' (' + (file.size/1024/1024).toFixed(2) + ' MB)';
  document.getElementById('selected-file').style.display = 'flex';
}

async function uploadCours() {
  const titre   = document.getElementById('upload-titre').value.trim();
  const desc    = document.getElementById('upload-desc').value.trim();
  const filiere = document.getElementById('upload-filiere').value.trim();
  const niveau  = document.getElementById('upload-niveau').value;
  if (!titre || !filiere || !niveau || !selectedFile) {
    showToast('⚠️ Remplissez tous les champs obligatoires', 'error');
    return;
  }
  const btn = document.getElementById('btn-submit');
  btn.disabled = true; btn.textContent = '⏳ Envoi en cours...';
  try {
    const formData = new FormData();
    formData.append('titre', titre);
    formData.append('description', desc);
    formData.append('filiere', filiere);
    formData.append('niveau', niveau);
    formData.append('file', selectedFile);
    const res = await fetch('/api/upload/upload/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token },
      body: formData
    });
    if (!res.ok) throw new Error();
    showToast('✅ Cours ajouté avec succès !', 'success');
    closeModal();
    await loadCourses();
  } catch(e) {
    showToast("❌ Erreur lors de l'envoi du cours", 'error');
  } finally {
    btn.disabled = false; btn.textContent = '📤 Envoyer le cours';
  }
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

loadCourses();