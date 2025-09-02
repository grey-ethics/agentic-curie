const elMessages = document.getElementById("messages");
const elForm = document.getElementById("composer");
const elInput = document.getElementById("chat-input");
const elUploadBtn = document.getElementById("upload-btn");
const elFile = document.getElementById("file-input");
const elChips = document.getElementById("chips");

const sessionKey = "agentic-curie-session";
let sessionId = localStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionKey, sessionId);
}

// files attached for *next* message
let pendingFileIds = [];
let pendingFileMeta = [];

function chip(text) {
  const span = document.createElement("span");
  span.className = "chip";
  span.textContent = text;
  elChips.appendChild(span);
}

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="bubble"><strong>${role}:</strong> ${escapeHtml(text)}</div>`;
  elMessages.appendChild(div);
  elMessages.scrollTop = elMessages.scrollHeight;
}

function appendToolTrace(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return;
  const div = document.createElement("div");
  div.className = "tool-trace";
  div.innerHTML = `<div class="trace-title">Tool calls</div>`;
  toolCalls.forEach((tc) => {
    if (tc.type === "call") {
      const row = document.createElement("div");
      row.className = "trace-row";
      row.textContent = `-> ${tc.tool}(${tc.arguments})`;
      div.appendChild(row);
    } else if (tc.type === "output") {
      const row = document.createElement("div");
      row.className = "trace-row out";
      row.innerHTML = linkify(`<- ${tc.output}`);
      div.appendChild(row);
    }
  });
  elMessages.appendChild(div);
  elMessages.scrollTop = elMessages.scrollHeight;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function linkify(text) {
  // Turn /api/files/<id>/download into clickable links
  const re = /(\/api\/files\/[a-f0-9]+\/download)/g;
  return escapeHtml(text).replace(re, '<a href="$1" target="_blank">$1</a>');
}

elUploadBtn.addEventListener("click", async () => {
  const files = elFile.files;
  if (!files || files.length === 0) return;
  const fd = new FormData();
  for (const f of files) fd.append("files", f);
  try {
    const res = await fetch("/api/files/upload", { method: "POST", body: fd });
    if (!res.ok) throw new Error(`Upload failed ${res.status}`);
    const data = await res.json();
    for (const f of data.files) {
      pendingFileIds.push(f.id);
      pendingFileMeta.push(f);
      chip(f.filename);
    }
    elFile.value = "";
  } catch (e) {
    appendMessage("assistant", `Upload error: ${e.message}`);
  }
});

elForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = elInput.value.trim();
  if (!text) return;
  appendMessage("you", text);
  elInput.value = "";

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: sessionId,
        attachment_ids: pendingFileIds,
      }),
    });
    // reset pending files after sending
    pendingFileIds = [];
    pendingFileMeta = [];
    elChips.innerHTML = "";

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    appendToolTrace(data.tool_calls);
    appendMessage("assistant", data.final);
  } catch (err) {
    appendMessage("assistant", `Oops: ${err.message}`);
  }
});

// welcome blurb
appendMessage("assistant", "Hi! Upload a couple of PDFs/DOCX with the Attach button, then say: “merge the two docs into one summary.”");
