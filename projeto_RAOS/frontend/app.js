// app.js — compartilhado pelas duas paginas do Uaifly.
// Agora com historico de sessao, toast de erro, e gerenciamento de sessoes.

// =====================================================
// PAGINA INICIAL (index.html)
// =====================================================
(function initHomePage() {
  const menuToggle = document.getElementById('menuToggle');
  const navLinks = document.getElementById('navLinks');

  if (menuToggle && navLinks) {
    menuToggle.addEventListener('click', () => {
      menuToggle.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach((a) => {
      a.addEventListener('click', () => {
        menuToggle.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  function updateMiniClocks() {
    const now = new Date();
    const map = { clkSP: 'America/Sao_Paulo', clkLIS: 'Europe/Lisbon', clkTYO: 'Asia/Tokyo' };
    Object.entries(map).forEach(([id, tz]) => {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = new Intl.DateTimeFormat('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
          timeZone: tz,
        }).format(now);
      }
    });
  }

  if (document.getElementById('clkSP')) {
    updateMiniClocks();
    setInterval(updateMiniClocks, 30000);
  }
})();

// =====================================================
// CHAT (chat.html)
// =====================================================
(function initChatPage() {
  const chatForm = document.getElementById('chatForm');
  const chatLog = document.getElementById('chatLog');
  const chatInput = document.getElementById('chatInput');
  const sendBtn = document.getElementById('sendBtn');
  const activeModeLabel = document.getElementById('activeModeLabel');
  const modeChips = document.getElementById('modeChips');
  const clockList = document.getElementById('clockList');
  const newChatBtn = document.getElementById('newChatBtn');
  const sessionList = document.getElementById('sessionList');

  if (!chatForm || !chatLog || !modeChips) return;

  // ---------- toast de erro ----------
  function showToast(msg) {
    let toast = document.getElementById('toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'toast';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 4000);
  }

  // ---------- sessao ----------
  let currentSessionId = localStorage.getItem('uaifly_session') || generateSessionId();

  function generateSessionId() {
    return 'sess_' + Date.now() + '_' + Math.random().toString(36).slice(2, 9);
  }

  function ensureSession() {
    if (!localStorage.getItem('uaifly_session')) {
      localStorage.setItem('uaifly_session', currentSessionId);
    }
  }
  ensureSession();

  function startNewSession() {
    currentSessionId = generateSessionId();
    localStorage.setItem('uaifly_session', currentSessionId);
    chatLog.innerHTML = '';
    appendWelcome();
    loadSessionList();
  }

  if (newChatBtn) {
    newChatBtn.addEventListener('click', startNewSession);
  }

  // ---------- modos ----------
  const MODE_LABELS = {
    geral: 'Conversa livre',
    roteiro: 'Roteiro',
    dicas: 'Dicas de viagem',
    hoteis: 'Hotéis',
    voos: 'Voos',
    eventos: 'Eventos',
    fuso_horario: 'Fuso-horário',
    restaurante_tipico: 'Restaurante típico',
    passeios: 'Passeios',
    interprete_pessoal: 'Intérprete pessoal',
    interprete_online: 'Intérprete online',
  };

  let currentMode = 'geral';

  modeChips.addEventListener('click', (event) => {
    const chip = event.target.closest('.chip');
    if (!chip) return;

    modeChips.querySelectorAll('.chip').forEach((c) => c.classList.remove('active'));
    chip.classList.add('active');

    currentMode = chip.dataset.mode;
    if (activeModeLabel) {
      activeModeLabel.textContent = MODE_LABELS[currentMode] || 'Conversa livre';
    }
    chatInput.focus();
  });

  // ---------- historico visual ----------
  function appendMessage(role, text) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;

    if (role === 'ai' || role === 'error') {
      const tag = document.createElement('div');
      tag.className = 'msg-tag';
      tag.textContent = role === 'error' ? 'erro' : 'Uaifly';
      div.appendChild(tag);
    }

    const body = document.createElement('div');
    body.textContent = text;
    div.appendChild(body);

    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
    return div;
  }

  function appendWelcome() {
    appendMessage(
      'ai',
      'Oi! Eu sou o Uaifly. Escolha uma função ao lado ou só me conta o que você está planejando.'
    );
  }

  function appendTyping() {
    const div = document.createElement('div');
    div.className = 'msg ai typing';
    div.innerHTML = '<span></span><span></span><span></span>';
    chatLog.appendChild(div);
    chatLog.scrollTop = chatLog.scrollHeight;
    return div;
  }

  // ---------- envio ----------
  async function sendMessage(text) {
    // Validacao frontend (nao envia so com espacos).
    if (!text) {
      showToast('Digite uma mensagem antes de enviar.');
      return;
    }

    appendMessage('user', text);
    const typingEl = appendTyping();

    sendBtn.disabled = true;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          mode: currentMode,
          session_id: currentSessionId,
        }),
      });

      typingEl.remove();

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        const errMsg = data.error || 'Algo deu errado ao falar com a IA.';
        appendMessage('error', errMsg);
        showToast(errMsg);
        return;
      }

      const data = await res.json();
      appendMessage('ai', data.reply);
    } catch (err) {
      typingEl.remove();
      const errMsg = 'Não consegui conectar ao servidor. Verifique se o backend está rodando.';
      appendMessage('error', errMsg);
      showToast(errMsg);
    } finally {
      sendBtn.disabled = false;
    }
  }

  chatForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = chatInput.value.trim();
    if (!text) {
      showToast('Digite uma mensagem antes de enviar.');
      return;
    }
    chatInput.value = '';
    sendMessage(text);
  });

  // Desabilita botao se input tiver so espacos.
  chatInput.addEventListener('input', () => {
    sendBtn.disabled = !chatInput.value.trim();
  });

  // ---------- sessoes anteriores ----------
  async function loadSessionList() {
    if (!sessionList) return;
    try {
      const res = await fetch('/api/sessions?limit=10');
      const data = await res.json();
      renderSessionList(data.sessions || []);
    } catch {
      // Silencioso: lista nao e critica.
    }
  }

  function renderSessionList(sessions) {
    if (!sessionList) return;
    if (sessions.length === 0) {
      sessionList.innerHTML = '<p class="session-empty">Nenhuma conversa anterior.</p>';
      return;
    }
    sessionList.innerHTML = sessions
      .map(
        (s) => `
      <div class="session-item ${s.session_id === currentSessionId ? 'active' : ''}" data-id="${s.session_id}">
        <span class="session-title">${s.title || 'Nova conversa'}</span>
        <button class="session-delete" data-id="${s.session_id}" title="Apagar conversa">&times;</button>
      </div>`
      )
      .join('');

    sessionList.querySelectorAll('.session-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        if (e.target.classList.contains('session-delete')) return;
        loadSession(item.dataset.id);
      });
    });

    sessionList.querySelectorAll('.session-delete').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteSession(btn.dataset.id);
      });
    });
  }

  async function loadSession(sessionId) {
    try {
      const res = await fetch(`/api/sessions/${sessionId}`);
      const data = await res.json();
      currentSessionId = sessionId;
      localStorage.setItem('uaifly_session', sessionId);
      chatLog.innerHTML = '';
      (data.history || []).forEach((msg) => {
        appendMessage(msg.role === 'user' ? 'user' : 'ai', msg.content);
      });
      if (!data.history || data.history.length === 0) appendWelcome();
      loadSessionList();
    } catch {
      showToast('Erro ao carregar conversa.');
    }
  }

  async function deleteSession(sessionId) {
    if (!confirm('Apagar esta conversa?')) return;
    try {
      await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
      if (sessionId === currentSessionId) startNewSession();
      else loadSessionList();
    } catch {
      showToast('Erro ao apagar conversa.');
    }
  }

  // ---------- relogio mundial ----------
  const CITIES = [
    { name: 'Sao Paulo', tz: 'America/Sao_Paulo' },
    { name: 'Lisboa', tz: 'Europe/Lisbon' },
    { name: 'Toquio', tz: 'Asia/Tokyo' },
    { name: 'Nova York', tz: 'America/New_York' },
  ];

  function buildClockRows() {
    if (!clockList) return;
    clockList.innerHTML = CITIES.map(
      (c) => `
      <div class="clock-row">
        <span class="city">${c.name}</span>
        <span class="time" data-tz="${c.tz}">--:--</span>
      </div>`
    ).join('');
  }

  function updateClocks() {
    if (!clockList) return;
    const now = new Date();
    clockList.querySelectorAll('[data-tz]').forEach((el) => {
      const tz = el.getAttribute('data-tz');
      el.textContent = new Intl.DateTimeFormat('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: tz,
      }).format(now);
    });
  }

  buildClockRows();
  updateClocks();
  setInterval(updateClocks, 30000);

  // ---------- boot do chat ----------
  // Carrega historico da sessao atual do banco.
  async function bootChat() {
    try {
      const res = await fetch(`/api/sessions/${currentSessionId}`);
      const data = await res.json();
      if (data.history && data.history.length > 0) {
        data.history.forEach((msg) => {
          appendMessage(msg.role === 'user' ? 'user' : 'ai', msg.content);
        });
      } else {
        appendWelcome();
      }
    } catch {
      appendWelcome();
    }
    loadSessionList();
  }

  bootChat();
})();
