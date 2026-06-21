INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PFC Verifier</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      background: #0f1117;
      color: #e1e4e8;
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container { max-width: 720px; margin: 0 auto; }

    header { margin-bottom: 2rem; }

    h1 { font-size: 1.75rem; font-weight: 700; color: #f0f6fc; }

    .subtitle { color: #8b949e; margin-top: 0.25rem; font-size: 0.9rem; }

    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }

    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      margin-bottom: 0.5rem;
    }

    textarea {
      width: 100%;
      height: 280px;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #c9d1d9;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 0.85rem;
      line-height: 1.6;
      padding: 0.75rem;
      resize: vertical;
      outline: none;
      transition: border-color 0.15s;
    }

    textarea:focus { border-color: #58a6ff; }

    button {
      display: block;
      width: 100%;
      padding: 0.75rem;
      margin-top: 0.75rem;
      background: #238636;
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s;
    }

    button:hover  { background: #2ea043; }
    button:active { background: #1a7f37; }
    button:disabled { background: #21262d; color: #484f58; cursor: default; }

    .json-error { color: #f85149; font-size: 0.85rem; margin-top: 0.5rem; }

    .result-card { display: none; }

    .verdict {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.25rem;
      border-radius: 6px;
      margin-bottom: 1rem;
      font-size: 1.1rem;
      font-weight: 700;
    }

    .verdict.valid   { background: #0d2818; border: 1px solid #238636; color: #3fb950; }
    .verdict.invalid { background: #2d0f0f; border: 1px solid #da3633; color: #f85149; }

    .verdict-icon { font-size: 1.3rem; }

    .checks-grid { display: flex; flex-direction: column; gap: 0.4rem; }

    .check-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 0.75rem;
      background: #0d1117;
      border-radius: 4px;
      font-size: 0.9rem;
    }

    .check-name { color: #c9d1d9; font-family: monospace; }

    .badge {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 99px;
      letter-spacing: 0.04em;
    }

    .badge.pass { background: #0d2818; color: #3fb950; border: 1px solid #238636; }
    .badge.fail { background: #2d0f0f; color: #f85149; border: 1px solid #da3633; }

    .errors-section { margin-top: 1rem; }

    .errors-title {
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      margin-bottom: 0.4rem;
    }

    .error-item {
      font-size: 0.85rem;
      color: #f85149;
      padding: 0.3rem 0;
      border-bottom: 1px solid #21262d;
    }

    .error-item:last-child { border-bottom: none; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>PFC Verifier</h1>
      <p class="subtitle">Verify PFC receipt integrity and Ed25519 signatures</p>
    </header>

    <div class="card">
      <label for="receipt">Receipt JSON</label>
      <textarea id="receipt" spellcheck="false" placeholder='{
  "receiptId": "receipt-v2-001",
  "timestamp": "2026-06-21T00:00:00Z",
  "payloadHash": "aaa...aaa",
  "publicKey": "base64url-encoded-key",
  "signature": "base64url-encoded-sig"
}'></textarea>
      <p id="json-error" class="json-error" hidden></p>
      <button id="verify-btn">Verify</button>
    </div>

    <div id="result" class="card result-card">
      <div id="verdict" class="verdict"></div>
      <div class="checks-grid" id="checks"></div>
      <div id="errors-section" class="errors-section" hidden>
        <p class="errors-title">Errors</p>
        <div id="errors-list"></div>
      </div>
    </div>
  </div>

  <script>
    const btn            = document.getElementById('verify-btn');
    const textarea       = document.getElementById('receipt');
    const resultEl       = document.getElementById('result');
    const verdictEl      = document.getElementById('verdict');
    const checksEl       = document.getElementById('checks');
    const errorsSection  = document.getElementById('errors-section');
    const errorsList     = document.getElementById('errors-list');
    const jsonError      = document.getElementById('json-error');

    btn.addEventListener('click', async () => {
      jsonError.hidden = true;
      resultEl.style.display = 'none';

      const text = textarea.value.trim();
      let data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        jsonError.textContent = 'Invalid JSON: ' + e.message;
        jsonError.hidden = false;
        return;
      }

      btn.disabled = true;
      btn.textContent = 'Verifying…';
      try {
        const res = await fetch('/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        render(await res.json());
      } catch (e) {
        jsonError.textContent = 'Request failed: ' + e.message;
        jsonError.hidden = false;
      } finally {
        btn.disabled = false;
        btn.textContent = 'Verify';
      }
    });

    function render(result) {
      verdictEl.className = 'verdict ' + (result.valid ? 'valid' : 'invalid');
      verdictEl.innerHTML = result.valid
        ? '<span class="verdict-icon">&#10003;</span> VALID'
        : '<span class="verdict-icon">&#10007;</span> INVALID';

      checksEl.innerHTML = '';
      for (const [name, status] of Object.entries(result.checks)) {
        const row = document.createElement('div');
        row.className = 'check-row';
        const cls = status === 'PASS' ? 'pass' : 'fail';
        row.innerHTML =
          '<span class="check-name">' + name + '</span>' +
          '<span class="badge ' + cls + '">' + status + '</span>';
        checksEl.appendChild(row);
      }

      if (result.errors && result.errors.length > 0) {
        errorsList.innerHTML = result.errors
          .map(e => '<div class="error-item">' + e + '</div>')
          .join('');
        errorsSection.hidden = false;
      } else {
        errorsSection.hidden = true;
      }

      resultEl.style.display = 'block';
    }
  </script>
</body>
</html>"""
