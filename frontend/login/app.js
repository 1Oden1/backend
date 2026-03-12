/* ═══════════════════════════════════════════════════
   ENT Salé — Login · app.js
═══════════════════════════════════════════════════ */

'use strict';

// ── Éléments DOM ────────────────────────────────────────────────────────────
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const loginBtn      = document.getElementById('loginBtn');
const btnLabel      = document.getElementById('btnLabel');
const eyeBtn        = document.getElementById('eyeBtn');
const eyeIcon       = document.getElementById('eyeIcon');
const errorBox      = document.getElementById('errorBox');
const errorText     = document.getElementById('errorText');

// ── Auto-redirect si déjà connecté ──────────────────────────────────────────
(function checkExistingSession() {
  const token = localStorage.getItem('access_token');
  const user  = localStorage.getItem('user');
  if (!token || !user) return;
  try {
    redirect(JSON.parse(user).roles || []);
  } catch { /* ignore */ }
})();

// ── Toggle affichage mot de passe ────────────────────────────────────────────
eyeBtn.addEventListener('click', () => {
  if (passwordInput.type === 'password') {
    passwordInput.type = 'text';
    eyeIcon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>'
      + '<path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>'
      + '<line x1="1" y1="1" x2="23" y2="23"/>';
  } else {
    passwordInput.type = 'password';
    eyeIcon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  }
});

// ── Clic sur le bouton ───────────────────────────────────────────────────────
loginBtn.addEventListener('click', doLogin);

// ── Touche Entrée ────────────────────────────────────────────────────────────
[usernameInput, passwordInput].forEach(el =>
  el.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); })
);

// ── Fonction principale de connexion ─────────────────────────────────────────
async function doLogin() {
  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (!username || !password) {
    showError('Veuillez remplir tous les champs.');
    return;
  }

  setLoading(true);
  hideError();

  try {
    // 1) Login → tokens
    const loginRes = await fetch('/api/auth/login', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ username, password }),
    });

    if (!loginRes.ok) {
      const data = await loginRes.json().catch(() => ({}));
      showError(data.detail || 'Identifiants incorrects. Veuillez réessayer.');
      setLoading(false);
      return;
    }

    const tokens = await loginRes.json();
    saveTokens(tokens);

    // 2) /auth/me → rôles
    const meRes = await fetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    if (!meRes.ok) {
      showError('Erreur lors de la récupération du profil utilisateur.');
      setLoading(false);
      return;
    }

    const user = await meRes.json();
    localStorage.setItem('user', JSON.stringify(user));

    // 3) Succès visuel puis redirection
    setSuccess();
    setTimeout(() => redirect(user.roles || []), 750);

  } catch {
    showError('Impossible de joindre le serveur. Vérifiez votre connexion réseau.');
    setLoading(false);
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function saveTokens(tokens) {
  localStorage.setItem('access_token',  tokens.access_token);
  localStorage.setItem('refresh_token', tokens.refresh_token);
  localStorage.setItem('expires_in',    String(tokens.expires_in));
  localStorage.setItem('token_ts',      String(Date.now()));
}

function redirect(roles) {
  if (roles.includes('admin'))            window.location.href = '/admin/';
  else if (roles.includes('enseignant'))  window.location.href = '/enseignant/';
  else                                    window.location.href = '/etudiant/';
}

function setLoading(on) {
  loginBtn.disabled = on;
  if (on) {
    btnLabel.innerHTML = '<span class="spinner"></span>Connexion…';
  } else {
    btnLabel.textContent = 'Se connecter';
    loginBtn.classList.remove('success');
    loginBtn.style.cssText = '';
  }
}

function setSuccess() {
  loginBtn.classList.add('success');
  btnLabel.textContent = '✓ Connexion réussie';
}

function showError(msg) {
  errorText.textContent = msg;
  errorBox.classList.add('show');
}

function hideError() {
  errorBox.classList.remove('show');
}
