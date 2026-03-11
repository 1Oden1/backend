/**
 * ENT – EST Salé
 * auth.js : Communication avec le micro-service ms-auth
 *
 * Endpoints réels (ms-auth FastAPI) :
 *   POST /auth/login        → JSON { username, password }
 *                           ← { access_token, refresh_token, token_type, expires_in }
 *   POST /auth/refresh      → JSON { refresh_token }
 *   POST /auth/logout       → JSON { refresh_token }
 *   GET  /auth/me           → Header: Authorization: Bearer <token>
 *                           ← { id, username, email, first_name, last_name, roles[] }
 *
 * Sur Docker : Nginx proxifie /api/auth/* → ent_ms_auth:8000/auth/*
 */

// ─────────────────────────────────────────────
// CONFIG
// ─────────────────────────────────────────────
const CONFIG = {
  // Sur Docker, Nginx proxifie /api vers ent_ms_auth:8000
  // En dev direct : changer pour 'http://localhost:8001'
  MS_AUTH_URL:      window.ENV?.MS_AUTH_URL      || '/api',
  REDIRECT_SUCCESS: window.ENV?.REDIRECT_SUCCESS || '/dashboard.html',
  TOKEN_KEY:        'ent_access_token',
  REFRESH_KEY:      'ent_refresh_token',
  USER_KEY:         'ent_user',
};

// ─────────────────────────────────────────────
// TOKEN STORAGE (sessionStorage)
// ─────────────────────────────────────────────
const TokenStore = {
  save(access, refresh) {
    sessionStorage.setItem(CONFIG.TOKEN_KEY,   access);
    sessionStorage.setItem(CONFIG.REFRESH_KEY, refresh || '');
  },
  getAccess()  { return sessionStorage.getItem(CONFIG.TOKEN_KEY);  },
  getRefresh() { return sessionStorage.getItem(CONFIG.REFRESH_KEY); },
  clear() {
    sessionStorage.removeItem(CONFIG.TOKEN_KEY);
    sessionStorage.removeItem(CONFIG.REFRESH_KEY);
    sessionStorage.removeItem(CONFIG.USER_KEY);
  },
  saveUser(user) {
    sessionStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
  },
  getUser() {
    try { return JSON.parse(sessionStorage.getItem(CONFIG.USER_KEY)); }
    catch { return null; }
  },
};

// ─────────────────────────────────────────────
// API HELPER (JSON)
// ─────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const url = `${CONFIG.MS_AUTH_URL}${path}`;

  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };

  const token = TokenStore.getAccess();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });

  if (!res.ok) {
    let msg = `Erreur ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || err.message || msg;
    } catch { /* réponse non-JSON */ }
    if (res.status === 401) msg = 'Identifiant ou mot de passe incorrect.';
    if (res.status === 403) msg = 'Accès refusé. Vérifiez vos droits.';
    if (res.status === 422) msg = 'Données invalides.';
    throw new Error(msg);
  }

  if (res.status === 204) return null;
  return res.json();
}

// ─────────────────────────────────────────────
// AUTH SERVICE
// ─────────────────────────────────────────────
const AuthService = {

  /**
   * POST /auth/login
   * ms-auth attend du JSON : { username, password }
   */
  async login(username, password) {
    const data = await apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    // data = { access_token, refresh_token, token_type, expires_in }
    TokenStore.save(data.access_token, data.refresh_token);
    return data;
  },

  /**
   * GET /auth/me
   * Retourne { id, username, email, first_name, last_name, roles[] }
   */
  async getProfile() {
    return apiFetch('/auth/me');
  },

  /**
   * POST /auth/refresh
   * body JSON : { refresh_token }
   */
  async refresh() {
    const refresh_token = TokenStore.getRefresh();
    if (!refresh_token) throw new Error('Aucun refresh token disponible.');

    const data = await apiFetch('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token }),
    });
    TokenStore.save(data.access_token, data.refresh_token);
    return data;
  },

  /**
   * POST /auth/logout
   * body JSON : { refresh_token }
   */
  async logout() {
    const refresh_token = TokenStore.getRefresh();
    try {
      if (refresh_token) {
        await apiFetch('/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token }),
        });
      }
    } finally {
      TokenStore.clear();
    }
  },

  /** Vérifie si un access token est présent côté client */
  isAuthenticated() {
    return Boolean(TokenStore.getAccess());
  },
};

// ─────────────────────────────────────────────
// UI HELPERS
// ─────────────────────────────────────────────
function showAlert(message, type = 'error') {
  const alert = document.getElementById('alert');
  alert.className = `alert show ${type}`;
  alert.innerHTML = `<span>${type === 'error' ? '⚠' : '✓'}</span> ${message}`;
}

function hideAlert() {
  document.getElementById('alert').classList.remove('show');
}

function setLoading(isLoading) {
  const btn = document.getElementById('btn-login');
  btn.classList.toggle('loading', isLoading);
  btn.disabled = isLoading;
}

// ─────────────────────────────────────────────
// PARTICLES
// ─────────────────────────────────────────────
function initParticles() {
  const container = document.querySelector('.particles');
  if (!container) return;
  for (let i = 0; i < 30; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.cssText = `
      left: ${Math.random() * 100}%;
      top: ${Math.random() * 100 + 100}%;
      width: ${Math.random() < 0.3 ? 3 : 2}px;
      height: ${Math.random() < 0.3 ? 3 : 2}px;
      animation-duration: ${6 + Math.random() * 12}s;
      animation-delay: ${Math.random() * 10}s;
      opacity: 0;
    `;
    container.appendChild(p);
  }
}

// ─────────────────────────────────────────────
// TOGGLE PASSWORD
// ─────────────────────────────────────────────
function initTogglePassword() {
  const btn   = document.getElementById('toggle-pw');
  const input = document.getElementById('password');
  if (!btn || !input) return;
  btn.addEventListener('click', () => {
    const hidden = input.type === 'password';
    input.type      = hidden ? 'text' : 'password';
    btn.textContent = hidden ? '🙈' : '👁';
  });
}

// ─────────────────────────────────────────────
// FORM SUBMIT
// ─────────────────────────────────────────────
async function handleLogin(e) {
  e.preventDefault();
  hideAlert();

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  if (!username || !password) {
    showAlert('Veuillez remplir tous les champs.');
    return;
  }

  setLoading(true);

  try {
    // 1. Login → access_token + refresh_token stockés
    await AuthService.login(username, password);

    // 2. Profil utilisateur
    const user = await AuthService.getProfile();
    TokenStore.saveUser(user);

    // 3. Feedback visuel
    showAlert(`Bienvenue, ${user.first_name || user.username} !`, 'success');

    // 4. Redirection
    setTimeout(() => {
      window.location.href = CONFIG.REDIRECT_SUCCESS;
    }, 1200);

  } catch (err) {
    showAlert(err.message || 'Une erreur inattendue est survenue.');
    setLoading(false);
  }
}

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (AuthService.isAuthenticated()) {
    window.location.href = CONFIG.REDIRECT_SUCCESS;
    return;
  }

  initParticles();
  initTogglePassword();

  const form = document.getElementById('login-form');
  if (form) form.addEventListener('submit', handleLogin);

  document.getElementById('validate-account')?.addEventListener('click', (e) => {
    e.preventDefault();
    showAlert("Contactez l'administration pour valider votre compte.", 'success');
  });

  document.getElementById('forgot-link')?.addEventListener('click', (e) => {
    e.preventDefault();
    showAlert("Un e-mail de réinitialisation vous sera envoyé.", 'success');
  });
});

// Exposition globale pour les autres pages (dashboard, etc.)
window.AuthService = AuthService;
window.TokenStore  = TokenStore;
