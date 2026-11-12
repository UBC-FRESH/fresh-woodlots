"""Portal-level chat panel backed by a selected WS4 assistant."""

from __future__ import annotations

ASSISTANT_SLUG = "wl-w0026"

ASSISTANT_CSS = """<style>
  .portal-assistant {
    position: fixed; z-index: 5000; right: 1rem; bottom: 1rem;
    width: min(390px, calc(100vw - 2rem)); max-height: min(680px, 78vh);
    display: flex; flex-direction: column;
    background: #fff; border: 1px solid var(--line);
    border-radius: 16px; box-shadow: 0 18px 50px rgba(23, 35, 31, .18);
    overflow: hidden; font: 14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif;
    color: var(--ink);
  }
  .portal-assistant[hidden] { display: none; }
  .assistant-head {
    display: flex; align-items: center; gap: .5rem;
    padding: .75rem .85rem; background: #eef4ef;
    border-bottom: 1px solid var(--line);
  }
  .assistant-head strong { font-size: .9rem; }
  .assistant-head span { color: var(--muted); font-size: .7rem; margin-left: auto; }
  .assistant-head button {
    border: 1px solid var(--line); background: #fff; color: var(--ink);
    border-radius: 7px; padding: .2rem .45rem; font: inherit;
    font-size: .72rem; cursor: pointer;
  }
  .assistant-log {
    flex: 1; min-height: 150px; overflow: auto; padding: .75rem;
    display: flex; flex-direction: column; gap: .5rem;
    background: #fbfdfb;
  }
  .assistant-msg {
    padding: .45rem .6rem; border-radius: 10px; white-space: pre-wrap;
    overflow-wrap: anywhere;
  }
  .assistant-msg.user { align-self: flex-end; max-width: 88%; background: #e8eef5; }
  .assistant-msg.agent {
    align-self: stretch; background: #fff; border: 1px solid var(--line);
  }
  .assistant-msg.error { background: #fff4f4; border-color: #e7bcbc; }
  .assistant-hint { color: var(--muted); font-size: .78rem; margin: 0; }
  .assistant-form {
    display: flex; gap: .4rem; padding: .6rem .7rem .35rem;
    border-top: 1px solid var(--line); background: #fff;
  }
  .assistant-form textarea {
    flex: 1; resize: none; min-height: 42px; max-height: 110px;
    padding: .5rem .6rem; border: 1px solid var(--line); border-radius: 9px;
    font: inherit; color: var(--ink); background: #fff;
  }
  .assistant-form button {
    align-self: flex-end; border: 1px solid var(--accent);
    background: var(--accent); color: #fff; border-radius: 9px;
    padding: .55rem .7rem; font: inherit; font-weight: 700; cursor: pointer;
  }
  .assistant-form button:disabled { opacity: .55; cursor: wait; }
  .assistant-status {
    margin: 0; padding: 0 .8rem .65rem; color: var(--muted);
    font-size: .7rem; background: #fff;
  }
  .assistant-msg.markdown p { margin: .25rem 0; }
  .assistant-msg.markdown ul,
  .assistant-msg.markdown ol { margin: .3rem 0; padding-left: 1.2rem; }
  .assistant-msg.markdown h1,
  .assistant-msg.markdown h2,
  .assistant-msg.markdown h3 { margin: .45rem 0 .2rem; line-height: 1.2; }
  .assistant-msg.markdown h1 { font-size: 1.05rem; }
  .assistant-msg.markdown h2 { font-size: .98rem; }
  .assistant-msg.markdown h3 { font-size: .9rem; }
  .assistant-msg.markdown pre {
    margin: .35rem 0; padding: .5rem; overflow: auto;
    background: #f1f5f2; border-radius: 7px; font-size: .75rem;
  }
  .assistant-msg.markdown code {
    background: #eef4ef; border-radius: 3px; padding: .05rem .2rem;
    font-size: .78rem;
  }
  .assistant-msg.markdown pre code { padding: 0; background: none; }
  .assistant-msg.markdown a { color: var(--accent); }
  .assistant-msg.markdown table { border-collapse: collapse; font-size: .75rem; }
  .assistant-msg.markdown th,
  .assistant-msg.markdown td { border: 1px solid var(--line); padding: .2rem .3rem; }
  @media (max-width: 600px) {
    .portal-assistant { right: .5rem; bottom: .5rem; width: calc(100vw - 1rem); }
  }
</style>"""

ASSISTANT_HTML = """<script src="https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.2.4/dist/purify.min.js"></script>
<aside id="portal-assistant" class="portal-assistant" hidden
       aria-label="Portal assistant">
  <div class="assistant-head">
    <strong>✦ Ask</strong>
    <span id="assistant-model">WS4 assistant</span>
    <button id="assistant-new" type="button">New</button>
    <button id="assistant-close" type="button" aria-label="Close assistant">×</button>
  </div>
  <div id="assistant-log" class="assistant-log">
    <p class="assistant-hint">Ask about the portal, a woodlot, a model, or what to
    try next. This assistant can read the selected workspace and may run
    commands.</p>
  </div>
  <form id="assistant-form" class="assistant-form">
    <textarea id="assistant-input" rows="2" placeholder="Ask about the portal…"
              aria-label="Ask the portal assistant"></textarea>
    <button id="assistant-send" type="submit">Send</button>
  </form>
  <p id="assistant-status" class="assistant-status"></p>
</aside>"""

ASSISTANT_JS = f"""<script>
(() => {{
  const slug = '{ASSISTANT_SLUG}';
  const panel = document.getElementById('portal-assistant');
  const log = document.getElementById('assistant-log');
  const form = document.getElementById('assistant-form');
  const input = document.getElementById('assistant-input');
  const send = document.getElementById('assistant-send');
  const status = document.getElementById('assistant-status');
  const askButton = document.getElementById('portal-ask');
  let session = null;
  let busy = false;

  function addMessage(kind, text) {{
    const row = document.createElement('div');
    row.className = 'assistant-msg ' + kind;
    if (
      kind === 'agent'
      && window.marked
      && window.DOMPurify
      && typeof window.marked.parse === 'function'
    ) {{
      row.classList.add('markdown');
      row.innerHTML = window.DOMPurify.sanitize(
        window.marked.parse(text, {{ breaks: true, gfm: true }})
      );
    }} else {{
      row.textContent = text;
    }}
    log.appendChild(row);
    log.scrollTop = log.scrollHeight;
    return row;
  }}

  function setBusy(value) {{
    busy = value;
    send.disabled = value;
    input.disabled = value;
  }}

  async function poll(job) {{
    for (;;) {{
      await new Promise((resolve) => setTimeout(resolve, 1200));
      const response = await fetch(
        '/instance/' + slug + '/api/chat/' + encodeURIComponent(job)
      );
      if (!response.ok) throw new Error(await response.text());
      const data = await response.json();
      if (data.status === 'running') continue;
      if (data.status === 'error') throw new Error(data.detail || 'assistant failed');
      if (data.session) session = data.session;
      addMessage('agent', data.reply || 'The assistant returned no text.');
      if (Array.isArray(data.actions) && data.actions.length) {{
        const tools = data.actions
          .map((item) => item.tool + (item.summary ? ': ' + item.summary : ''))
          .join(' · ');
        status.textContent = 'Tools used: ' + tools;
      }} else {{
        status.textContent = '';
      }}
      return;
    }}
  }}

  async function submit(message) {{
    if (!message || busy) return;
    addMessage('user', message);
    input.value = '';
    setBusy(true);
    status.textContent = 'Thinking…';
    try {{
      const response = await fetch('/instance/' + slug + '/api/chat', {{
        method: 'POST',
        headers: {{'content-type': 'application/json'}},
        body: JSON.stringify({{message, session, async: true}}),
      }});
      if (!response.ok) throw new Error(await response.text());
      const job = await response.json();
      await poll(job.job);
    }} catch (error) {{
      addMessage('error', 'Assistant unavailable: ' + error.message);
      status.textContent = '';
    }} finally {{
      setBusy(false);
      input.focus();
    }}
  }}

  function open() {{
    panel.hidden = false;
    askButton?.setAttribute('aria-expanded', 'true');
    input.focus();
  }}

  function close() {{
    panel.hidden = true;
    askButton?.setAttribute('aria-expanded', 'false');
  }}

  askButton?.addEventListener('click', open);
  document.getElementById('assistant-close').addEventListener('click', close);
  document.getElementById('assistant-new').addEventListener('click', () => {{
    session = null;
    log.replaceChildren();
    const hint = document.createElement('p');
    hint.className = 'assistant-hint';
    hint.textContent = 'New conversation.';
    log.appendChild(hint);
    status.textContent = '';
    input.focus();
  }});
  form.addEventListener('submit', (event) => {{
    event.preventDefault();
    submit(input.value.trim());
  }});
  input.addEventListener('keydown', (event) => {{
    if (event.key === 'Enter' && !event.shiftKey) {{
      event.preventDefault();
      form.requestSubmit();
    }}
  }});
  document.addEventListener('keydown', (event) => {{
    if (event.key === 'Escape' && !panel.hidden) close();
  }});
}})();
</script>"""


def render_assistant() -> str:
    """Return the portal-level assistant markup, styles, and behavior."""
    return ASSISTANT_CSS + ASSISTANT_HTML + ASSISTANT_JS
