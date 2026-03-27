// ── auth.js — ENT EST-Salé ──

function setTab(tab) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => {
    b.classList.toggle('active', (i === 0 && tab === 'login') || (i === 1 && tab === 'help'));
  });
  document.getElementById('tab-login').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('tab-help').style.display  = tab === 'help'  ? 'block' : 'none';
}

function togglePassword() {
  const pwd = document.getElementById('password');
  const btn = document.getElementById('toggle-btn');
  if (pwd.type === 'password') {
    pwd.type = 'text'; btn.textContent = '🙈';
  } else {
    pwd.type = 'password'; btn.textContent = '👁️';
  }
}

function showAlert(msg, type) {
  const box   = document.getElementById('alert-box');
  const icon  = document.getElementById('alert-icon');
  const msgEl = document.getElementById('alert-msg');
  box.className = 'alert ' + type;
  icon.textContent = type === 'error' ? '⚠️' : '✅';
  msgEl.textContent = msg;
}

async function handleLogin() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  const btn = document.getElementById('login-btn');

  if (!username || !password) {
    showAlert('Veuillez remplir tous les champs.', 'error');
    return;
  }

  btn.classList.add('loading');

  try {
    const response = await fetch('/api/auth/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await response.json();

    if (!response.ok) {
      showAlert(data.detail || 'Identifiants incorrects.', 'error');
      btn.classList.remove('loading');
      return;
    }

    // Sauvegarder les tokens
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('username', username);
    localStorage.setItem('role', data.role || '');

    showAlert('Connexion réussie ! Redirection...', 'success');

    setTimeout(() => {
      window.location.href = '/pages/dashboard.html';
    }, 1000);

  } catch (err) {
    showAlert('Erreur de connexion au serveur.', 'error');
    btn.classList.remove('loading');
  }
}

// Login avec la touche Entrée
document.addEventListener('DOMContentLoaded', () => {
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') handleLogin();
  });
});