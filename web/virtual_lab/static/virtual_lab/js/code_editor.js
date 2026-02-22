// static/virtual_lab/js/code_editor.js

// Simple CSRF helper
function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
  return match ? decodeURIComponent(match[2]) : null;
}

// Language configuration for Ace editor
const languageConfig = {
  python: {
    mode: "ace/mode/python",
    sample: 'print("Hello, World!")'
  },
  javascript: {
    mode: "ace/mode/javascript",
    sample: 'console.log("Hello, World!");'
  },
  c: {
    mode: "ace/mode/c_cpp",
    sample: '#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}'
  },
  cpp: {
    mode: "ace/mode/c_cpp",
    sample: '#include <iostream>\nusing namespace std;\n\nint main() {\n    cout << "Hello, World!" << endl;\n    return 0;\n}'
  }
};

// Bootstrap Ace
const editor = ace.edit("editor");
editor.setTheme("ace/theme/github");
editor.session.setMode("ace/mode/python");
editor.setOptions({
  fontSize: "14px",
  showPrintMargin: false,
  wrap: true,
  enableBasicAutocompletion: true,
  enableLiveAutocompletion: true
});

const runBtn   = document.getElementById("run-btn");
const outputEl = document.getElementById("output");
const stdinEl  = document.getElementById("stdin-input");
const langSel  = document.getElementById("language-select");

// Function to update editor mode and sample code based on selected language
function updateEditorLanguage(language) {
  const config = languageConfig[language];
  if (config) {
    editor.session.setMode(config.mode);
    editor.setValue(config.sample, -1); // -1 moves cursor to end
  }
}

// Language selector change handler
langSel.addEventListener("change", (e) => {
  const selectedLanguage = e.target.value;
  updateEditorLanguage(selectedLanguage);
});

// Initialize with Python sample code
updateEditorLanguage("python");

runBtn.addEventListener("click", () => {
  const code     = editor.getValue();
  const stdin    = stdinEl.value;
  const language = langSel.value;

  if (!code.trim()) {
    outputEl.textContent = "🛑 Please type some code first.";
    return;
  }
  outputEl.textContent = "Running…";
  runBtn.disabled = true;

  fetch(window.EVALUATE_CODE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken":  getCookie("csrftoken")
    },
    body: JSON.stringify({ code, language, stdin })
  })
  .then(res => res.json())
  .then(data => {
    let out = "";
    if (data.stderr) out += `ERROR:\n${data.stderr}\n`;
    if (data.stdout) out += data.stdout;
    outputEl.textContent = out || "[no output]";
  })
  .catch(err => {
    outputEl.textContent = `Request failed: ${err.message}`;
  })
  .finally(() => {
    runBtn.disabled = false;
  });
});
