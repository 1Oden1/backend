// ── calendar.js — ENT EST-Salé ──

const token    = localStorage.getItem('access_token');
const username = localStorage.getItem('username');
const role     = localStorage.getItem('role') || 'etudiant';

if (!token) window.location.href = '/pages/login.html';

document.getElementById('user-name').textContent = username || 'Utilisateur';
const roleLabels = { admin: '⚙️ Administrateur', enseignant: '👨‍🏫 Enseignant', teacher: '👨‍🏫 Enseignant', etudiant: '🎓 Étudiant' };
document.getElementById('user-role').textContent = roleLabels[role] || '🎓 Étudiant';
if (['enseignant','teacher','admin'].includes(role)) document.querySelectorAll('.enseignant-only').forEach(el => el.style.display = 'flex');
if (role === 'admin') document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');

const today        = new Date();
let currentYear    = today.getFullYear();
let currentMonth   = today.getMonth();
let allEvents      = [];
let selectedDate   = null;

const MONTHS_FR = ['Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
const DAYS_FR   = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];

const TYPE_COLORS = { examen: 'red', cours: 'blue', reunion: 'purple', conge: 'green', autre: 'orange' };
const TYPE_ICONS  = { examen: '📝', cours: '📚', reunion: '👥', conge: '🏖️', autre: '📌' };

async function loadEvents() {
  try {
    const res  = await fetch('/api/calendar/calendar/', { headers: { 'Authorization': 'Bearer ' + token } });
    const data = await res.json();
    allEvents  = data;
    renderCalendar();
    renderUpcoming();
  } catch(e) {
    document.getElementById('upcoming-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray-text);font-size:0.82rem">⚠️ Erreur de chargement</div>';
  }
}

function renderCalendar() {
  document.getElementById('cal-month-title').textContent = MONTHS_FR[currentMonth] + ' ' + currentYear;

  const firstDay = new Date(currentYear, currentMonth, 1).getDay();
  const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
  const daysInPrev  = new Date(currentYear, currentMonth, 0).getDate();
  const startDay    = (firstDay + 6) % 7; // Monday first

  // Event dates set for fast lookup
  const eventDates = new Set(allEvents.map(e => {
    const d = new Date(e.date_debut);
    return d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate();
  }));

  let html = DAYS_FR.map(d => '<div class="cal-day-name">' + d + '</div>').join('');

  // Previous month days
  for (let i = startDay - 1; i >= 0; i--) {
    html += '<div class="cal-day other-month">' + (daysInPrev - i) + '</div>';
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    const key     = currentYear + '-' + currentMonth + '-' + d;
    const isToday = d === today.getDate() && currentMonth === today.getMonth() && currentYear === today.getFullYear();
    const hasEv   = eventDates.has(key);
    const isSel   = selectedDate && selectedDate.getDate() === d && selectedDate.getMonth() === currentMonth && selectedDate.getFullYear() === currentYear;
    const cls     = (isToday ? ' today' : '') + (hasEv ? ' has-event' : '') + (isSel && !isToday ? ' selected' : '');
    html += '<div class="cal-day' + cls + '" onclick="selectDay(' + d + ')">' + d + '</div>';
  }

  // Next month days
  const totalCells = Math.ceil((startDay + daysInMonth) / 7) * 7;
  for (let d = 1; d <= totalCells - startDay - daysInMonth; d++) {
    html += '<div class="cal-day other-month">' + d + '</div>';
  }

  document.getElementById('cal-grid').innerHTML = html;
}

function selectDay(d) {
  selectedDate = new Date(currentYear, currentMonth, d);
  renderCalendar();

  const dayEvents = allEvents.filter(e => {
    const ev = new Date(e.date_debut);
    return ev.getDate() === d && ev.getMonth() === currentMonth && ev.getFullYear() === currentYear;
  });

  const title = d + ' ' + MONTHS_FR[currentMonth] + ' ' + currentYear;
  document.getElementById('day-events-title').textContent = '📅 ' + title;

  if (dayEvents.length === 0) {
    document.getElementById('day-events-list').innerHTML = '<div class="no-events">Aucun événement ce jour</div>';
    return;
  }

  document.getElementById('day-events-list').innerHTML = dayEvents.map(e => {
    const t = e.type || 'autre';
    return '<div class="event-item ' + t + '">' +
      '<div class="event-info">' +
        '<div class="event-title">' + (TYPE_ICONS[t] || '📌') + ' ' + e.titre + '</div>' +
        '<div class="event-meta">' + (e.heure || '') + (e.lieu ? ' · ' + e.lieu : '') + '</div>' +
      '</div>' +
    '</div>';
  }).join('');
}

function renderUpcoming() {
  const now = new Date();
  const upcoming = allEvents
    .filter(e => new Date(e.date_debut) >= now)
    .sort((a, b) => new Date(a.date_debut) - new Date(b.date_debut))
    .slice(0, 5);

  if (upcoming.length === 0) {
    document.getElementById('upcoming-list').innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray-text);font-size:0.82rem">📭 Aucun événement à venir</div>';
    return;
  }

  document.getElementById('upcoming-list').innerHTML = upcoming.map(e => {
    const d   = new Date(e.date_debut);
    const t   = e.type || 'autre';
    const day = d.getDate();
    const mon = MONTHS_FR[d.getMonth()].substring(0, 3);
    return '<div class="event-item ' + t + '">' +
      '<div class="event-date-badge"><div class="day">' + day + '</div><div class="month">' + mon + '</div></div>' +
      '<div class="event-info">' +
        '<div class="event-title">' + e.titre + '</div>' +
        '<div class="event-meta">' + (TYPE_ICONS[t] || '📌') + ' ' + t + (e.lieu ? ' · ' + e.lieu : '') + '</div>' +
      '</div>' +
    '</div>';
  }).join('');
}

function changeMonth(dir) {
  currentMonth += dir;
  if (currentMonth > 11) { currentMonth = 0; currentYear++; }
  if (currentMonth < 0)  { currentMonth = 11; currentYear--; }
  selectedDate = null;
  renderCalendar();
  document.getElementById('day-events-title').textContent = '📅 Événements du jour';
  document.getElementById('day-events-list').innerHTML = '<div class="no-events">Cliquez sur un jour pour voir ses événements</div>';
}

function openModal() {
  document.getElementById('event-modal').classList.add('open');
  // Pre-fill today's date
  const d = selectedDate || today;
  document.getElementById('ev-date').value     = d.toISOString().split('T')[0];

}
function closeModal() {
  document.getElementById('event-modal').classList.remove('open');
  document.getElementById('ev-titre').value = '';
  document.getElementById('ev-desc').value  = '';
  document.getElementById('ev-heure').value = '';
  document.getElementById('ev-lieu').value      = '';


}

async function addEvent() {
  const titre = document.getElementById('ev-titre').value.trim();
  const desc  = document.getElementById('ev-desc').value.trim();
  const date  = document.getElementById('ev-date').value;
  const heure = document.getElementById('ev-heure').value;
  const type  = document.getElementById('ev-type').value;
  const lieu  = document.getElementById('ev-lieu').value.trim();

  if (!titre || !date) { showToast('⚠️ Titre et date sont obligatoires', 'error'); return; }

  const btn = document.getElementById('ev-submit');
  btn.disabled = true; btn.textContent = '⏳ Enregistrement...';

  try {
    const dateDebut = date + 'T' + (heure || '08:00') + ':00';
    const dateFinDT = date + 'T' + addHour(heure || '08:00') + ':00';
    const res = await fetch('/api/calendar/calendar/', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
      body: JSON.stringify({ titre, description: desc, date_debut: dateDebut, date_fin: dateFinDT, type, lieu })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Erreur');
    }
    showToast('✅ Événement ajouté !', 'success');
    closeModal();
    await loadEvents();
  } catch(e) {
    showToast('❌ ' + (e.message || 'Erreur'), 'error');
  } finally {
    btn.disabled = false; btn.textContent = '✅ Enregistrer';
  }
}

function addHour(heure) {
  const parts = heure.split(':');
  const h = (parseInt(parts[0]) + 1) % 24;
  return (h < 10 ? '0' : '') + h + ':' + parts[1];
}

function showToast(msg, type) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3500);
}

function logout() { localStorage.clear(); window.location.href = '/pages/login.html'; }

loadEvents();