/* ═══════════════════════════════════════════════════════════════════════════
   ENT Salé — Widget IA Chat
   Fichier auto-contenu : inclure ce script dans n'importe quelle page ENT.
   Il injecte le bouton flottant + la popup de chat IA (Llama 3 / Ollama).
═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ── 1. Styles CSS injectés ───────────────────────────────────────────── */
  const CSS = `
    /* ── Variables ── */
    :root {
      --ia-blue:       #1565c0;
      --ia-blue-dark:  #0d47a1;
      --ia-blue-light: #e3f2fd;
      --ia-orange:     #e65100;
      --ia-bg:         #ffffff;
      --ia-surface:    #f5f7fa;
      --ia-border:     #e0e0e0;
      --ia-text:       #1a1a2e;
      --ia-muted:      #757575;
      --ia-shadow:     0 8px 32px rgba(21,101,192,.18);
      --ia-radius:     16px;
      --ia-font:       'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* ── Bouton flottant ── */
    #ia-fab {
      position: fixed;
      bottom: 28px;
      right: 28px;
      width: 58px;
      height: 58px;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--ia-blue) 0%, var(--ia-blue-dark) 100%);
      color: #fff;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(21,101,192,.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9998;
      transition: transform .2s ease, box-shadow .2s ease;
      outline: none;
    }
    #ia-fab:hover  { transform: scale(1.08); box-shadow: 0 6px 22px rgba(21,101,192,.55); }
    #ia-fab:active { transform: scale(.96); }
    #ia-fab svg    { width: 26px; height: 26px; pointer-events: none; }

    /* Badge notification */
    #ia-fab-badge {
      position: absolute;
      top: -2px; right: -2px;
      width: 18px; height: 18px;
      background: var(--ia-orange);
      border-radius: 50%;
      border: 2px solid #fff;
      display: none;
    }

    /* Tooltip */
    #ia-fab::after {
      content: 'Assistant IA';
      position: absolute;
      right: 68px;
      background: rgba(21,101,192,.92);
      color: #fff;
      font-family: var(--ia-font);
      font-size: 12px;
      padding: 5px 10px;
      border-radius: 8px;
      white-space: nowrap;
      opacity: 0;
      pointer-events: none;
      transition: opacity .2s;
    }
    #ia-fab:hover::after { opacity: 1; }

    /* ── Fenêtre de chat ── */
    #ia-chat-window {
      position: fixed;
      bottom: 100px;
      right: 28px;
      width: 380px;
      max-height: 580px;
      display: flex;
      flex-direction: column;
      background: var(--ia-bg);
      border-radius: var(--ia-radius);
      box-shadow: var(--ia-shadow);
      border: 1px solid var(--ia-border);
      z-index: 9999;
      overflow: hidden;
      font-family: var(--ia-font);
      transition: transform .25s cubic-bezier(.34,1.56,.64,1), opacity .2s ease;
      transform-origin: bottom right;
    }
    #ia-chat-window.ia-hidden {
      transform: scale(.85);
      opacity: 0;
      pointer-events: none;
    }

    /* ── Header ── */
    #ia-header {
      background: linear-gradient(135deg, var(--ia-blue) 0%, var(--ia-blue-dark) 100%);
      color: #fff;
      padding: 14px 16px 12px;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-shrink: 0;
    }
    #ia-header-avatar {
      width: 36px; height: 36px;
      background: rgba(255,255,255,.2);
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 18px;
      flex-shrink: 0;
    }
    #ia-header-info { flex: 1; min-width: 0; }
    #ia-header-title {
      font-size: 14px;
      font-weight: 700;
      margin: 0;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    #ia-header-subtitle {
      font-size: 11px;
      opacity: .78;
      margin: 2px 0 0;
      display: flex; align-items: center; gap: 5px;
    }
    .ia-dot {
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #69f0ae;
      animation: ia-pulse 2s infinite;
    }
    @keyframes ia-pulse {
      0%,100% { opacity:1; } 50% { opacity:.4; }
    }
    #ia-btn-clear, #ia-btn-close {
      background: none;
      border: none;
      color: rgba(255,255,255,.8);
      cursor: pointer;
      padding: 4px;
      border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      transition: background .15s, color .15s;
    }
    #ia-btn-clear:hover, #ia-btn-close:hover {
      background: rgba(255,255,255,.15);
      color: #fff;
    }
    #ia-btn-clear svg, #ia-btn-close svg { width: 18px; height: 18px; }

    /* ── Messages ── */
    #ia-messages {
      flex: 1;
      overflow-y: auto;
      padding: 14px 14px 8px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      scroll-behavior: smooth;
    }
    #ia-messages::-webkit-scrollbar { width: 4px; }
    #ia-messages::-webkit-scrollbar-thumb { background: var(--ia-border); border-radius: 2px; }

    /* Bulle de message */
    .ia-msg {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      animation: ia-slide-in .2s ease;
    }
    @keyframes ia-slide-in {
      from { opacity:0; transform: translateY(6px); }
      to   { opacity:1; transform: translateY(0); }
    }
    .ia-msg.ia-user { flex-direction: row-reverse; }

    .ia-msg-avatar {
      width: 28px; height: 28px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      font-size: 13px;
      font-weight: 700;
      flex-shrink: 0;
      margin-top: 2px;
    }
    .ia-msg.ia-bot  .ia-msg-avatar { background: var(--ia-blue-light); color: var(--ia-blue); }
    .ia-msg.ia-user .ia-msg-avatar { background: var(--ia-blue); color: #fff; }

    .ia-msg-bubble {
      max-width: 78%;
      padding: 9px 13px;
      border-radius: 14px;
      font-size: 13.5px;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .ia-msg.ia-bot  .ia-msg-bubble {
      background: var(--ia-surface);
      border: 1px solid var(--ia-border);
      border-top-left-radius: 4px;
      color: var(--ia-text);
    }
    .ia-msg.ia-user .ia-msg-bubble {
      background: var(--ia-blue);
      color: #fff;
      border-top-right-radius: 4px;
    }
    .ia-msg-time {
      font-size: 10px;
      color: var(--ia-muted);
      margin-top: 3px;
      text-align: right;
    }
    .ia-msg.ia-bot .ia-msg-time  { text-align: left; }

    /* Indicateur de frappe (trois points) */
    #ia-typing {
      display: none;
      align-items: center;
      gap: 8px;
      padding: 6px 14px 0;
    }
    #ia-typing.ia-visible { display: flex; }
    .ia-typing-dots {
      display: flex; gap: 4px;
    }
    .ia-typing-dots span {
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--ia-blue);
      animation: ia-bounce .9s infinite;
    }
    .ia-typing-dots span:nth-child(2) { animation-delay: .15s; }
    .ia-typing-dots span:nth-child(3) { animation-delay: .30s; }
    @keyframes ia-bounce {
      0%,80%,100% { transform: translateY(0); opacity:.4; }
      40% { transform: translateY(-5px); opacity:1; }
    }
    .ia-typing-label { font-size: 11px; color: var(--ia-muted); font-style: italic; }

    /* Message de bienvenue (vide) */
    #ia-welcome {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 10px;
      padding: 28px 20px;
      text-align: center;
      color: var(--ia-muted);
      font-size: 13px;
    }
    #ia-welcome svg { width: 48px; height: 48px; color: var(--ia-blue); opacity:.35; }
    #ia-welcome strong { color: var(--ia-text); font-size: 14px; }

    /* Suggestions rapides */
    #ia-suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 0 14px 10px;
    }
    .ia-suggestion {
      font-family: var(--ia-font);
      font-size: 12px;
      padding: 5px 11px;
      border-radius: 14px;
      border: 1px solid var(--ia-blue);
      color: var(--ia-blue);
      background: var(--ia-blue-light);
      cursor: pointer;
      transition: background .15s, color .15s;
      white-space: nowrap;
    }
    .ia-suggestion:hover { background: var(--ia-blue); color: #fff; }

    /* ── Zone de saisie ── */
    #ia-input-area {
      padding: 10px 12px 12px;
      border-top: 1px solid var(--ia-border);
      display: flex;
      gap: 8px;
      align-items: flex-end;
      flex-shrink: 0;
    }
    #ia-input {
      flex: 1;
      border: 1px solid var(--ia-border);
      border-radius: 20px;
      padding: 9px 14px;
      font-family: var(--ia-font);
      font-size: 13.5px;
      color: var(--ia-text);
      background: var(--ia-surface);
      resize: none;
      outline: none;
      max-height: 96px;
      overflow-y: auto;
      line-height: 1.45;
      transition: border-color .2s;
    }
    #ia-input:focus { border-color: var(--ia-blue); background: #fff; }
    #ia-input::placeholder { color: var(--ia-muted); }
    #ia-send {
      width: 38px; height: 38px;
      border-radius: 50%;
      background: var(--ia-blue);
      border: none;
      color: #fff;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
      transition: background .15s, transform .1s;
    }
    #ia-send:hover   { background: var(--ia-blue-dark); }
    #ia-send:active  { transform: scale(.92); }
    #ia-send:disabled { background: var(--ia-border); cursor: not-allowed; }
    #ia-send svg { width: 18px; height: 18px; }

    /* ── Responsive mobile ── */
    @media (max-width: 440px) {
      #ia-chat-window {
        width: calc(100vw - 20px);
        right: 10px;
        bottom: 90px;
        max-height: 70vh;
      }
      #ia-fab { bottom: 18px; right: 18px; }
    }
  `;

  /* ── 2. HTML du widget ────────────────────────────────────────────────── */
  const HTML = `
    <!-- Bouton flottant -->
    <button id="ia-fab" aria-label="Ouvrir l'assistant IA">
      <span id="ia-fab-badge"></span>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a10 10 0 0 1 10 10c0 5.52-4.48 10-10 10a9.96 9.96 0 0 1-5.19-1.45L2 22l1.45-4.81A9.96 9.96 0 0 1 2 12 10 10 0 0 1 12 2z"/>
        <circle cx="8"  cy="12" r="1" fill="currentColor" stroke="none"/>
        <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>
        <circle cx="16" cy="12" r="1" fill="currentColor" stroke="none"/>
      </svg>
    </button>

    <!-- Fenêtre de chat -->
    <div id="ia-chat-window" class="ia-hidden" role="dialog" aria-label="Assistant IA ENT">

      <!-- Header -->
      <div id="ia-header">
        <div id="ia-header-avatar">🤖</div>
        <div id="ia-header-info">
          <p id="ia-header-title">Assistant IA — ENT Salé</p>
          <p id="ia-header-subtitle">
            <span class="ia-dot"></span>
            Llama 3 · Cloud privé EST Salé
          </p>
        </div>
        <button id="ia-btn-clear" title="Effacer la conversation" aria-label="Effacer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6M14 11v6"/>
            <path d="M9 6V4h6v2"/>
          </svg>
        </button>
        <button id="ia-btn-close" title="Fermer" aria-label="Fermer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6"  y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- Zone messages -->
      <div id="ia-messages">
        <div id="ia-welcome">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
               stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <strong>Bonjour ! Je suis votre assistant IA.</strong>
          <span>Posez-moi une question sur votre scolarité, vos cours ou l'ENT.</span>
        </div>
      </div>

      <!-- Indicateur de frappe -->
      <div id="ia-typing">
        <div class="ia-typing-dots">
          <span></span><span></span><span></span>
        </div>
        <span class="ia-typing-label">L'IA rédige sa réponse…</span>
      </div>

      <!-- Suggestions rapides (affichées au démarrage) -->
      <div id="ia-suggestions">
        <button class="ia-suggestion">📅 Emploi du temps</button>
        <button class="ia-suggestion">📊 Mes notes</button>
        <button class="ia-suggestion">📁 Cours disponibles</button>
        <button class="ia-suggestion">❓ Comment fonctionne l'ENT ?</button>
      </div>

      <!-- Zone de saisie -->
      <div id="ia-input-area">
        <textarea id="ia-input" placeholder="Posez votre question…" rows="1"
                  maxlength="4000" aria-label="Message"></textarea>
        <button id="ia-send" aria-label="Envoyer">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  `;

  /* ── 3. Logique JavaScript ────────────────────────────────────────────── */

  // Inject CSS
  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);

  // Inject HTML
  const wrapper = document.createElement('div');
  wrapper.innerHTML = HTML;
  document.body.appendChild(wrapper);

  // Références DOM
  const fab         = document.getElementById('ia-fab');
  const chatWindow  = document.getElementById('ia-chat-window');
  const messagesEl  = document.getElementById('ia-messages');
  const typingEl    = document.getElementById('ia-typing');
  const inputEl     = document.getElementById('ia-input');
  const sendBtn     = document.getElementById('ia-send');
  const closeBtn    = document.getElementById('ia-btn-close');
  const clearBtn    = document.getElementById('ia-btn-clear');
  const welcomeEl   = document.getElementById('ia-welcome');
  const suggestionsEl = document.getElementById('ia-suggestions');

  // État
  let isOpen    = false;
  let isLoading = false;
  let history   = [];           // [{role, content}, ...]

  /* ── Utilitaires ── */
  function getToken() {
    return localStorage.getItem('access_token') || '';
  }

  function now() {
    return new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  function escHtml(s) {
    return String(s || '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;');
  }

  function scrollBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  /* ── Ouvrir / fermer ── */
  function openChat() {
    isOpen = true;
    chatWindow.classList.remove('ia-hidden');
    fab.style.boxShadow = '0 4px 16px rgba(21,101,192,.6)';
    setTimeout(() => inputEl.focus(), 250);
  }

  function closeChat() {
    isOpen = false;
    chatWindow.classList.add('ia-hidden');
    fab.style.boxShadow = '';
  }

  fab.addEventListener('click', () => isOpen ? closeChat() : openChat());
  closeBtn.addEventListener('click', closeChat);

  // Fermer en cliquant en dehors
  document.addEventListener('click', e => {
    if (isOpen && !chatWindow.contains(e.target) && e.target !== fab) {
      closeChat();
    }
  });

  /* ── Effacer la conversation ── */
  clearBtn.addEventListener('click', () => {
    history = [];
    messagesEl.innerHTML = '';
    messagesEl.appendChild(welcomeEl);
    welcomeEl.style.display = 'flex';
    suggestionsEl.style.display = 'flex';
  });

  /* ── Créer une bulle de message ── */
  function appendMessage(role, content) {
    if (welcomeEl.parentNode) {
      welcomeEl.style.display = 'none';
      suggestionsEl.style.display = 'none';
    }

    const userStr = localStorage.getItem('user');
    let initiale = 'U';
    try {
      const u = JSON.parse(userStr);
      initiale = (u.first_name || u.username || 'U')[0].toUpperCase();
    } catch {}

    const avatarContent = role === 'user' ? initiale : '🤖';
    const div = document.createElement('div');
    div.className = `ia-msg ia-${role}`;
    div.innerHTML = `
      <div class="ia-msg-avatar">${avatarContent}</div>
      <div>
        <div class="ia-msg-bubble" id="ia-bubble-${Date.now()}">${escHtml(content)}</div>
        <div class="ia-msg-time">${now()}</div>
      </div>
    `;
    messagesEl.appendChild(div);
    scrollBottom();
    return div.querySelector('.ia-msg-bubble');
  }

  /* ── Streaming depuis l'API ── */
  async function sendMessage(userText) {
    if (isLoading || !userText.trim()) return;
    const token = getToken();
    if (!token) {
      appendMessage('bot', '⚠️ Vous devez être connecté pour utiliser l\'assistant IA.');
      return;
    }

    isLoading = true;
    sendBtn.disabled = true;
    inputEl.setAttribute('readonly', '');

    // Afficher le message utilisateur
    appendMessage('user', userText);
    history.push({ role: 'user', content: userText });

    // Indicateur de frappe
    typingEl.classList.add('ia-visible');
    scrollBottom();

    // Préparer la bulle de réponse (vide d'abord)
    let botBubble = null;
    let fullReply = '';

    try {
      const resp = await fetch('/api/ia/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userText,
          history: history.slice(-20),   // max 20 messages de contexte
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || `Erreur HTTP ${resp.status}`);
      }

      typingEl.classList.remove('ia-visible');
      botBubble = appendMessage('bot', '');

      // Lire le flux SSE
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Traiter les lignes SSE complètes
        const lines = buffer.split('\n');
        buffer = lines.pop(); // garder le fragment incomplet

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (!data) continue;

          let parsed;
          try { parsed = JSON.parse(data); } catch { continue; }

          if (parsed.error) {
            botBubble.textContent = '⚠️ ' + parsed.error;
            break;
          }

          if (parsed.token) {
            fullReply += parsed.token;
            botBubble.textContent = fullReply;
            scrollBottom();
          }

          if (parsed.done) break;
        }
      }

      if (fullReply) {
        history.push({ role: 'assistant', content: fullReply });
      }

    } catch (err) {
      typingEl.classList.remove('ia-visible');
      if (!botBubble) botBubble = appendMessage('bot', '');
      botBubble.textContent = `⚠️ ${err.message || 'Une erreur est survenue.'}`;
    } finally {
      isLoading = false;
      sendBtn.disabled = false;
      inputEl.removeAttribute('readonly');
      inputEl.focus();
    }
  }

  /* ── Saisie et envoi ── */
  function handleSend() {
    const text = inputEl.value.trim();
    if (!text || isLoading) return;
    inputEl.value = '';
    inputEl.style.height = 'auto';
    sendMessage(text);
  }

  sendBtn.addEventListener('click', handleSend);

  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize textarea
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 96) + 'px';
  });

  /* ── Suggestions rapides ── */
  document.querySelectorAll('.ia-suggestion').forEach(btn => {
    btn.addEventListener('click', () => {
      inputEl.value = btn.textContent.replace(/^[^\w]+/, '').trim();
      inputEl.dispatchEvent(new Event('input'));
      handleSend();
    });
  });

})();
