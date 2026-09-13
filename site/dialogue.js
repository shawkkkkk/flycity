(() => {
  const panel = document.createElement('section');
  panel.id = 'live-dialogue';
  panel.setAttribute('aria-live', 'polite');
  panel.innerHTML = '<div class="dialogue-head"><span>LIVE ENCOUNTER</span><small>WAITING FOR FLIES TO TALK</small></div><div class="dialogue-turns"></div>';
  document.getElementById('app')?.appendChild(panel);

  const style = document.createElement('style');
  style.textContent = `
    #live-dialogue{position:absolute;z-index:12;left:338px;top:78px;width:min(440px,calc(100% - 690px));min-width:310px;pointer-events:none;border:1px solid rgba(139,255,197,.2);background:rgba(5,13,9,.9);backdrop-filter:blur(12px);opacity:0;transform:translateY(-6px);transition:opacity .2s,transform .2s;color:#eef8f1;font-family:Inter,ui-sans-serif,system-ui,sans-serif}
    #live-dialogue.show{opacity:1;transform:translateY(0)}
    #live-dialogue .dialogue-head{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 9px;border-bottom:1px solid rgba(139,255,197,.16);font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8px;letter-spacing:.12em;color:#69f4dc}
    #live-dialogue .dialogue-head small{font-size:7px;color:#8fa69a;letter-spacing:.08em}
    #live-dialogue .dialogue-turns{padding:8px 10px 9px;display:grid;gap:5px}
    #live-dialogue .dialogue-line{display:grid;grid-template-columns:auto 1fr;gap:8px;align-items:start;font-size:11px;line-height:1.35}
    #live-dialogue .dialogue-line b{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:8px;color:#c9ff67;white-space:nowrap;padding-top:2px}
    #live-dialogue .dialogue-line span{color:#e1eee6}
    #live-dialogue .dialogue-line em{display:block;color:#70897c;font:7px ui-monospace,SFMono-Regular,Menlo,monospace;margin-top:2px;font-style:normal}
    @media(max-width:980px){#live-dialogue{left:264px;width:calc(100% - 548px);min-width:260px}}
    @media(max-width:720px){#live-dialogue{display:none}}
  `;
  document.head.appendChild(style);

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let lastDialogueId = null;
  let hideTimer = null;
  let socket = null;

  function showDialogue(event) {
    if (!event || event.id === lastDialogueId || !Array.isArray(event.turns) || event.turns.length < 2) return;
    lastDialogueId = event.id;
    const turns = panel.querySelector('.dialogue-turns');
    const head = panel.querySelector('.dialogue-head small');
    const speakers = [...new Set(event.turns.map((turn) => `@${turn.handle}`))];
    head.textContent = speakers.join('  ↔  ');
    turns.innerHTML = event.turns.map((turn) => `
      <div class="dialogue-line">
        <b>@${esc(turn.handle)}</b>
        <span>“${esc(turn.text)}”<em>${esc(String(turn.words_by || 'local dialogue').toUpperCase())}</em></span>
      </div>`).join('');
    panel.classList.add('show');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => panel.classList.remove('show'), 14000);
  }

  function consume(snapshot) {
    const event = (snapshot?.events || []).find((item) => item.kind === 'dialogue' && Array.isArray(item.turns));
    showDialogue(event);
  }

  function connect() {
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    socket = new WebSocket(`${proto}//${location.host}/ws`);
    socket.addEventListener('message', (message) => {
      try { consume(JSON.parse(message.data)); } catch (_) {}
    });
    socket.addEventListener('close', () => setTimeout(connect, 2200));
    socket.addEventListener('error', () => socket.close());
  }

  fetch('/api/state', {cache:'no-store'}).then((r) => r.ok ? r.json() : null).then(consume).catch(() => {});
  connect();
})();
