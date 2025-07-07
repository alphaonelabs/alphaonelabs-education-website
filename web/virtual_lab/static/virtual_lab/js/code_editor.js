// CSRF helper
function getCookie(name) {
  let cookieValue = null;
  document.cookie.split(';').forEach(c => {
    c = c.trim();
    if (c.startsWith(name + '=')) {
      cookieValue = decodeURIComponent(c.substring(name.length + 1));
    }
  });
  return cookieValue;
}

// Initialize Ace
const editor = ace.edit("editor");
editor.setTheme("ace/theme/github");
editor.session.setMode("ace/mode/python");
editor.setOptions({ fontSize: "14px", showPrintMargin: false });

// DOM refs
const runBtn   = document.getElementById("run-btn");
const outputEl = document.getElementById("output");
const stdinEl  = document.getElementById("stdin-input");

// Run handler
runBtn.addEventListener("click", () => {
  const code  = editor.getValue();
  const stdin = stdinEl.value;

  if (!code.trim()) {
    outputEl.textContent = "🛑 Please type some code first.";
    return;
  }

  const payload = { code, stdin };
  console.log("▶️ Sending payload:", payload);

  outputEl.textContent = "Running…";

  fetch(window.EVALUATE_CODE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken":  getCookie("csrftoken")
    },
    body: JSON.stringify(payload)
  })
  .then(res => {
    console.log("⬅️ HTTP status:", res.status);
    return res.text().then(text => {
      console.log("⬅️ Raw response text:", text);
      try {
        return JSON.parse(text);
      } catch (err) {
        throw new Error("Invalid JSON: " + err.message);
      }
    });
  })
  .then(data => {
    console.log("✅ Parsed JSON response:", data);
    let out = "";
    if (data.stderr) out += `ERROR:\n${data.stderr}\n`;
    if (data.stdout) out += data.stdout;
    outputEl.textContent = out || "[no output]";
  })
  .catch(err => {
    console.error("❌ Fetch/parse error:", err);
    outputEl.textContent = `Request failed: ${err.message}`;
  });
});
