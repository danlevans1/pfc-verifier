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

    header { margin-bottom: 1.5rem; }

    h1 { font-size: 1.75rem; font-weight: 700; color: #f0f6fc; }

    .subtitle { color: #8b949e; margin-top: 0.25rem; font-size: 0.9rem; }

    /* ── Tabs ───────────────────────────────────────────────────── */
    .tabs {
      display: flex;
      gap: 0.25rem;
      border-bottom: 1px solid #30363d;
      margin-bottom: 1.25rem;
    }

    .tab-btn {
      background: none;
      border: none;
      border-bottom: 2px solid transparent;
      color: #8b949e;
      cursor: pointer;
      font-size: 0.9rem;
      font-weight: 600;
      padding: 0.6rem 1rem;
      margin-bottom: -1px;
      border-radius: 0;
      width: auto;
      display: inline-block;
      transition: color 0.15s, border-color 0.15s;
    }

    .tab-btn:hover  { color: #e1e4e8; background: none; }
    .tab-btn.active { color: #f0f6fc; border-bottom-color: #58a6ff; background: none; }

    .tab-panel[hidden] { display: none; }

    /* ── Cards ──────────────────────────────────────────────────── */
    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }

    /* ── Form elements ──────────────────────────────────────────── */
    label {
      display: block;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      margin-bottom: 0.5rem;
    }

    textarea, input[type="text"] {
      width: 100%;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      color: #c9d1d9;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 0.85rem;
      line-height: 1.6;
      padding: 0.65rem 0.75rem;
      outline: none;
      transition: border-color 0.15s;
    }

    textarea          { height: 280px; resize: vertical; }
    textarea.short    { height: 120px; }

    textarea:focus, input[type="text"]:focus { border-color: #58a6ff; }

    .field-row { margin-bottom: 0.75rem; }
    .field-row label { font-size: 0.75rem; margin-bottom: 0.3rem; }

    /* ── Buttons ────────────────────────────────────────────────── */
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

    .btn-secondary {
      background: #21262d;
      border: 1px solid #30363d;
      color: #c9d1d9;
      margin-top: 0.5rem;
    }

    .btn-secondary:hover { background: #30363d; }

    .btn-sm {
      width: auto;
      display: inline-block;
      padding: 0.3rem 0.75rem;
      font-size: 0.8rem;
      margin: 0;
      background: #21262d;
      border: 1px solid #30363d;
      color: #c9d1d9;
      border-radius: 4px;
    }

    .btn-sm:hover { background: #30363d; }

    /* ── Inline messages ────────────────────────────────────────── */
    .inline-error { color: #f85149; font-size: 0.85rem; margin-top: 0.5rem; }

    .warning { font-size: 0.8rem; color: #e3b341; margin-bottom: 0.5rem; }

    /* ── Shareable URL section ──────────────────────────────────── */
    .share-section {
      margin-top: 1rem;
      padding-top: 1rem;
      border-top: 1px solid #30363d;
    }

    .share-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 6px;
      padding: 0.6rem 0.75rem;
      margin-top: 0.4rem;
    }

    #share-url {
      flex: 1;
      color: #58a6ff;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 0.85rem;
      word-break: break-all;
      text-decoration: none;
    }

    #share-url:hover { text-decoration: underline; }

    /* ── Verify result ──────────────────────────────────────────── */
    .result-card { display: none; }

    .verdict {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem 1.25rem;
      border-radius: 6px;
      margin-bottom: 0.5rem;
      font-size: 1.1rem;
      font-weight: 700;
    }

    .verdict.valid   { background: #0d2818; border: 1px solid #238636; color: #3fb950; }
    .verdict.invalid { background: #2d0f0f; border: 1px solid #da3633; color: #f85149; }

    .verdict-icon { font-size: 1.3rem; }

    .verified-at {
      font-size: 0.78rem;
      color: #8b949e;
      margin-bottom: 1rem;
      padding-left: 0.25rem;
    }

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

    .section-label {
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

    /* ── Raw / code panels ──────────────────────────────────────── */
    .raw-panel {
      margin-top: 1rem;
      border: 1px solid #30363d;
      border-radius: 6px;
      overflow: hidden;
    }

    .raw-panel summary {
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #8b949e;
      padding: 0.6rem 0.75rem;
      cursor: pointer;
      user-select: none;
      background: #0d1117;
      list-style: none;
    }

    .raw-panel summary::-webkit-details-marker { display: none; }
    .raw-panel summary::before { content: '▶ '; font-size: 0.65rem; vertical-align: middle; }
    .raw-panel[open] summary::before { content: '▼ '; }

    pre {
      margin: 0;
      padding: 0.75rem;
      background: #0d1117;
      color: #8b949e;
      font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
      font-size: 0.8rem;
      line-height: 1.6;
      white-space: pre;
      overflow-x: auto;
    }

    .raw-panel pre { border-top: 1px solid #30363d; }

    .code-block {
      border: 1px solid #30363d;
      border-radius: 6px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>PFC Verifier</h1>
      <p class="subtitle">Verify and generate PFC receipts with Ed25519 signatures</p>
    </header>

    <div class="tabs">
      <button class="tab-btn active" data-tab="verify">Verify</button>
      <button class="tab-btn" data-tab="generate">Generate</button>
    </div>

    <!-- ── Verify tab ──────────────────────────────────────────── -->
    <div id="tab-verify" class="tab-panel">
      <div class="card">
        <label for="receipt">Receipt JSON</label>
        <textarea id="receipt" spellcheck="false" placeholder='{
  "receiptId": "receipt-v2-001",
  "timestamp": "2026-06-21T00:00:00Z",
  "payloadHash": "aaa...aaa",
  "publicKey": "base64url-encoded-key",
  "signature": "base64url-encoded-sig"
}'></textarea>
        <p id="json-error" class="inline-error" hidden></p>
        <button id="verify-btn">Verify</button>
      </div>

      <div id="result" class="card result-card">
        <div id="verdict" class="verdict"></div>
        <p id="verified-at" class="verified-at"></p>

        <div class="checks-grid" id="checks"></div>

        <div id="errors-section" class="errors-section" hidden>
          <p class="section-label">Errors</p>
          <div id="errors-list"></div>
        </div>

        <details id="raw-json-panel" class="raw-panel">
          <summary>Raw JSON response</summary>
          <pre id="raw-json"></pre>
        </details>
      </div>
    </div>

    <!-- ── Generate tab ────────────────────────────────────────── -->
    <div id="tab-generate" class="tab-panel" hidden>
      <div class="card">
        <p class="section-label" style="margin-bottom:1rem">Receipt Fields</p>

        <div class="field-row">
          <label for="gen-receipt-id">receiptId</label>
          <input id="gen-receipt-id" type="text" placeholder="auto-generated">
        </div>

        <div class="field-row">
          <label for="gen-timestamp">timestamp</label>
          <input id="gen-timestamp" type="text" placeholder="auto-generated (now)">
        </div>

        <div class="field-row">
          <label for="gen-payload">Payload JSON</label>
          <textarea id="gen-payload" class="short" spellcheck="false"
            placeholder='{"key": "value"}'></textarea>
        </div>

        <p id="gen-error" class="inline-error" hidden></p>
        <button id="generate-btn">Generate Receipt</button>
      </div>

      <div id="generator" class="card" hidden>
        <p class="section-label" style="margin-bottom:0.5rem">Generated Receipt</p>
        <div class="code-block"><pre id="generated-receipt"></pre></div>
        <button id="copy-receipt-btn" class="btn-secondary">Copy JSON</button>

        <div class="share-section">
          <p class="section-label">Shareable Verification URL</p>
          <div class="share-row">
            <a id="share-url" href="#" target="_blank"></a>
            <button id="copy-url-btn" class="btn-sm">Copy URL</button>
          </div>
        </div>

        <button id="verify-generated-btn">Verify Generated Receipt</button>

        <p class="section-label" style="margin-top:1.25rem;margin-bottom:0.25rem">Private Key</p>
        <p class="warning">Store this securely — it will not be shown again.</p>
        <div class="code-block"><pre id="generated-private-key"></pre></div>
      </div>
    </div>
  </div>

  <script>
    // ── Tab switching ─────────────────────────────────────────────
    document.querySelectorAll('.tab-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
        document.querySelectorAll('.tab-panel').forEach(function(p) { p.hidden = true; });
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).hidden = false;
      });
    });

    // ── Verify ────────────────────────────────────────────────────
    var verifyBtn      = document.getElementById('verify-btn');
    var textarea       = document.getElementById('receipt');
    var resultEl       = document.getElementById('result');
    var verdictEl      = document.getElementById('verdict');
    var verifiedAtEl   = document.getElementById('verified-at');
    var checksEl       = document.getElementById('checks');
    var errorsSection  = document.getElementById('errors-section');
    var errorsList     = document.getElementById('errors-list');
    var jsonError      = document.getElementById('json-error');
    var rawJson        = document.getElementById('raw-json');

    verifyBtn.addEventListener('click', async function() {
      jsonError.hidden = true;
      resultEl.style.display = 'none';

      var text = textarea.value.trim();
      var data;
      try {
        data = JSON.parse(text);
      } catch (e) {
        jsonError.textContent = 'Invalid JSON: ' + e.message;
        jsonError.hidden = false;
        return;
      }

      verifyBtn.disabled = true;
      verifyBtn.textContent = 'Verifying…';
      try {
        var res = await fetch('/verify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        renderResult(await res.json());
      } catch (e) {
        jsonError.textContent = 'Request failed: ' + e.message;
        jsonError.hidden = false;
      } finally {
        verifyBtn.disabled = false;
        verifyBtn.textContent = 'Verify';
      }
    });

    function renderResult(result) {
      verdictEl.className = 'verdict ' + (result.valid ? 'valid' : 'invalid');
      verdictEl.innerHTML = result.valid
        ? '<span class="verdict-icon">&#10003;</span> VALID'
        : '<span class="verdict-icon">&#10007;</span> INVALID';

      verifiedAtEl.textContent = 'Verified at ' + new Date().toLocaleTimeString();

      checksEl.innerHTML = '';
      for (var entry of Object.entries(result.checks)) {
        var name = entry[0], status = entry[1];
        var row = document.createElement('div');
        row.className = 'check-row';
        var cls = status === 'PASS' ? 'pass' : 'fail';
        row.innerHTML =
          '<span class="check-name">' + name + '</span>' +
          '<span class="badge ' + cls + '">' + status + '</span>';
        checksEl.appendChild(row);
      }

      if (result.errors && result.errors.length > 0) {
        errorsList.innerHTML = result.errors
          .map(function(e) { return '<div class="error-item">' + e + '</div>'; })
          .join('');
        errorsSection.hidden = false;
      } else {
        errorsSection.hidden = true;
      }

      rawJson.textContent = JSON.stringify(result, null, 2);
      resultEl.style.display = 'block';
    }

    // ── Generate ──────────────────────────────────────────────────
    var generateBtn      = document.getElementById('generate-btn');
    var generatorResult  = document.getElementById('generator');
    var generatedReceipt = document.getElementById('generated-receipt');
    var generatedPrivKey = document.getElementById('generated-private-key');
    var copyReceiptBtn   = document.getElementById('copy-receipt-btn');
    var shareUrlEl       = document.getElementById('share-url');
    var copyUrlBtn       = document.getElementById('copy-url-btn');
    var verifyGenBtn     = document.getElementById('verify-generated-btn');
    var genError         = document.getElementById('gen-error');

    var _lastReceipt = null;
    var _lastUrl     = null;

    generateBtn.addEventListener('click', async function() {
      genError.hidden = true;
      generatorResult.hidden = true;
      generateBtn.disabled = true;
      generateBtn.textContent = 'Generating…';

      var req = {};
      var rid         = document.getElementById('gen-receipt-id').value.trim();
      var ts          = document.getElementById('gen-timestamp').value.trim();
      var payloadText = document.getElementById('gen-payload').value.trim();

      if (rid) req.receiptId = rid;
      if (ts)  req.timestamp = ts;

      if (payloadText) {
        try {
          req.payload = JSON.parse(payloadText);
        } catch (e) {
          genError.textContent = 'Invalid payload JSON: ' + e.message;
          genError.hidden = false;
          generateBtn.disabled = false;
          generateBtn.textContent = 'Generate Receipt';
          return;
        }
      }

      try {
        var res = await fetch('/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(req),
        });
        var data = await res.json();
        _lastReceipt = data.receipt;
        _lastUrl = window.location.origin + data.url;
        generatedReceipt.textContent = JSON.stringify(data.receipt, null, 2);
        generatedPrivKey.textContent = data.privateKey;
        shareUrlEl.textContent = data.url;
        shareUrlEl.href = _lastUrl;
        generatorResult.hidden = false;
      } catch (e) {
        genError.textContent = 'Request failed: ' + e.message;
        genError.hidden = false;
      } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate Receipt';
      }
    });

    copyReceiptBtn.addEventListener('click', function() {
      if (!_lastReceipt) return;
      navigator.clipboard.writeText(JSON.stringify(_lastReceipt, null, 2));
      copyReceiptBtn.textContent = 'Copied!';
      setTimeout(function() { copyReceiptBtn.textContent = 'Copy JSON'; }, 1500);
    });

    copyUrlBtn.addEventListener('click', function() {
      if (!_lastUrl) return;
      navigator.clipboard.writeText(_lastUrl);
      copyUrlBtn.textContent = 'Copied!';
      setTimeout(function() { copyUrlBtn.textContent = 'Copy URL'; }, 1500);
    });

    verifyGenBtn.addEventListener('click', function() {
      if (!_lastReceipt) return;
      textarea.value = JSON.stringify(_lastReceipt, null, 2);
      document.querySelector('[data-tab="verify"]').click();
      verifyBtn.click();
    });

    // ── Auto-load receipt when visiting /r/{receiptId} ────────────
    (function() {
      var m = window.location.pathname.match(/^\\/r\\/([^\\/]+)$/);
      if (!m) return;
      var receiptId = decodeURIComponent(m[1]);
      document.querySelector('[data-tab="verify"]').click();
      fetch('/receipts/' + encodeURIComponent(receiptId))
        .then(function(r) {
          if (!r.ok) throw new Error('Receipt not found');
          return r.json();
        })
        .then(function(receipt) {
          textarea.value = JSON.stringify(receipt, null, 2);
          verifyBtn.click();
        })
        .catch(function(e) {
          jsonError.textContent = 'Could not load receipt: ' + e.message;
          jsonError.hidden = false;
        });
    })();
  </script>
</body>
</html>"""
