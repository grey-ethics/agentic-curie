const elMessages = document.getElementById("messages");
const elForm = document.getElementById("composer");
const elInput = document.getElementById("chat-input");
const elSpinner = document.getElementById("spinner");

const sessionKey = "agentic-curie-session";
let sessionId = localStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionKey, sessionId);
}

function showSpinner(on){ elSpinner.style.display = on ? "flex" : "none"; }

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function linkify(text) {
  const re = /(\/api\/files\/[a-f0-9]+\/download)/g;
  return escapeHtml(text).replace(re, '<a href="$1" target="_blank">$1</a>');
}

/* ---------- intent detectors ---------- */
const MERGE_PAT = /\b(merge|combine|summarize)\b/i;
const DOC_PAT = /\b(doc|docs|document|documents|pdf|docx)\b/i;
function shouldShowMergeFromUser(t){ return MERGE_PAT.test(t) && DOC_PAT.test(t); }

const RESUME_PAT = /\b(resume|resumes|cv|cvs|candidate|candidates|parser|match)\b/i;
const JD_PAT = /\b(jd|job\s*description|job\s*desc)\b/i;
function shouldShowResumeFromUser(t){ return (RESUME_PAT.test(t) && JD_PAT.test(t)) || /\bresume\s*match/i.test(t); }

const ASK_UPLOAD = /\b(please\s+(upload|attach)|kindly\s+(upload|attach)|provide\s+the\s+files)\b/i;
const ASST_NEEDS_DOCS = /\b(doc|docs|document|documents|pdf|docx)\b/i;
const ASST_NEEDS_RESUME_OR_JD = /\b(resume|resumes|cv|cvs|jd|job\s*description)\b/i;
function shouldShowMergeFromAssistant(t){ return ASK_UPLOAD.test(t) && ASST_NEEDS_DOCS.test(t); }
function shouldShowResumeFromAssistant(t){ return ASK_UPLOAD.test(t) && ASST_NEEDS_RESUME_OR_JD.test(t); }

/* ---------- small helpers ---------- */
function describeFiles(fileList){
  if (!fileList || fileList.length === 0) return "";
  if (fileList.length === 1) return fileList[0].name;
  if (fileList.length === 2) return `${fileList[0].name} + 1 more`;
  return `${fileList[0].name} + ${fileList.length - 1} more`;
}

function initFilePicker({buttonId, inputId, nameId, emptyText}){
  const btn = document.getElementById(buttonId);
  const inp = document.getElementById(inputId);
  const name = document.getElementById(nameId);
  name.textContent = emptyText;
  btn.addEventListener("click", () => inp.click());
  inp.addEventListener("change", () => {
    name.textContent = describeFiles(inp.files) || emptyText;
  });
}

function closePanels(){
  ["panel-merge","panel-resume"].forEach(id => {
    const n = document.getElementById(id);
    if (n) n.remove();
  });
}

/* ---------- message renderers ---------- */
let firstAssistantShown = false;

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="bubble"><strong>${role}:</strong> ${escapeHtml(text)}</div>`;
  elMessages.appendChild(div);
  elMessages.scrollTop = elMessages.scrollHeight;

  if (role === "assistant") {
    if (!firstAssistantShown) { firstAssistantShown = true; return; }
    if (shouldShowMergeFromAssistant(text)) { closePanels(); showMergePanel(); }
    if (shouldShowResumeFromAssistant(text)) { closePanels(); showResumePanel(); }
  }
}

function appendToolTrace(toolCalls) {
  if (!toolCalls || toolCalls.length === 0) return;
  const div = document.createElement("div");
  div.className = "tool-trace panel";
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

  const needMerge = toolCalls.some(t => t.type === "output" && /at least two file_ids/i.test(t.output));
  const needResume = toolCalls.some(t => t.type === "output" && /resume/i.test(t.output) && /jd/i.test(t.output) && /provide/i.test(t.output));
  if (needMerge) { closePanels(); showMergePanel(); }
  if (needResume) { closePanels(); showResumePanel(); }
}

/* ---------- contextual panels ---------- */
function showMergePanel() {
  const id = "panel-merge";
  if (document.getElementById(id)) return;
  const card = document.createElement("div");
  card.className = "panel";
  card.id = id;
  card.innerHTML = `
    <h3>Merge Documents</h3>

    <div class="row">
      <button class="btn secondary" id="merge-files-btn" type="button">Choose documents…</button>
      <span class="file-name" id="merge-files-name">No files chosen — Documents (.pdf, .docx)</span>
      <input type="file" id="merge-files" multiple accept=".pdf,.docx" hidden />
    </div>

    <div class="row">
      <button class="btn secondary" id="merge-template-btn" type="button">Choose template…</button>
      <span class="file-name" id="merge-template-name">No file chosen — Template (.docx, optional)</span>
      <input type="file" id="merge-template" accept=".docx" hidden />
    </div>

    <div class="row">
      <button class="btn" id="merge-run" type="button">Attach & Run</button>
      <span class="hint">Pick ≥ 2 docs to merge. Optional: a .docx template for layout.</span>
    </div>
  `;
  elMessages.appendChild(card);
  elMessages.scrollTop = elMessages.scrollHeight;

  initFilePicker({
    buttonId: "merge-files-btn",
    inputId: "merge-files",
    nameId: "merge-files-name",
    emptyText: "No files chosen — Documents (.pdf, .docx)"
  });
  initFilePicker({
    buttonId: "merge-template-btn",
    inputId: "merge-template",
    nameId: "merge-template-name",
    emptyText: "No file chosen — Template (.docx, optional)"
  });

  document.getElementById("merge-run").addEventListener("click", async () => {
    const files = document.getElementById("merge-files").files;
    const tmpl = document.getElementById("merge-template").files;
    if (!files || files.length < 2) { appendMessage("assistant", "Please choose at least two documents to merge."); return; }
    showSpinner(true);
    try {
      const fd = new FormData();
      for (const f of files) fd.append("files", f);
      if (tmpl && tmpl.length === 1) fd.append("files", tmpl[0]);
      const up = await fetch("/api/files/upload", { method: "POST", body: fd });
      if (!up.ok) throw new Error(`upload failed ${up.status}`);
      const data = await up.json();
      const fileIds = data.files.map(f => f.id);

      let templateId = null;
      if (tmpl && tmpl.length === 1) {
        const last = data.files[data.files.length - 1];
        if (last.filename.toLowerCase().endsWith(".docx")) templateId = last.id;
      }

      const userMsg = templateId
        ? `Please merge the documents I just uploaded using this template (template_id: ${templateId}).`
        : `Please merge the documents I just uploaded.`;
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg, session_id: sessionId, attachment_ids: fileIds }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const out = await res.json();
      appendToolTrace(out.tool_calls);
      appendMessage("assistant", out.final);
    } catch (e) {
      appendMessage("assistant", `Upload/Merge error: ${e.message}`);
    } finally {
      showSpinner(false);
      closePanels();
    }
  });
}

function showResumePanel() {
  const id = "panel-resume";
  if (document.getElementById(id)) return;
  const card = document.createElement("div");
  card.className = "panel";
  card.id = id;
  card.innerHTML = `
    <h3>Resume Match</h3>

    <div class="row">
      <textarea id="jd-text" placeholder="Paste Job Description text (or upload a JD file below)"></textarea>
    </div>

    <div class="row">
      <button class="btn secondary" id="jd-file-btn" type="button">Choose JD file…</button>
      <span class="file-name" id="jd-file-name">No file chosen — Job Description (.pdf, .docx, .txt)</span>
      <input type="file" id="jd-file" accept=".pdf,.docx,.txt" hidden />
    </div>

    <div class="row">
      <button class="btn secondary" id="resume-files-btn" type="button">Choose resumes…</button>
      <span class="file-name" id="resume-files-name">No files chosen — Resumes (.pdf, .docx, .txt)</span>
      <input type="file" id="resume-files" multiple accept=".pdf,.docx,.txt" hidden />
    </div>

    <div class="row">
      <button class="btn" id="resume-run" type="button">Attach & Run</button>
      <span class="hint">Provide JD text or a JD file, plus one or more resumes.</span>
    </div>
  `;
  elMessages.appendChild(card);
  elMessages.scrollTop = elMessages.scrollHeight;

  initFilePicker({
    buttonId: "jd-file-btn",
    inputId: "jd-file",
    nameId: "jd-file-name",
    emptyText: "No file chosen — Job Description (.pdf, .docx, .txt)"
  });
  initFilePicker({
    buttonId: "resume-files-btn",
    inputId: "resume-files",
    nameId: "resume-files-name",
    emptyText: "No files chosen — Resumes (.pdf, .docx, .txt)"
  });

  document.getElementById("resume-run").addEventListener("click", async () => {
    const jdText = document.getElementById("jd-text").value.trim();
    const jdFile = document.getElementById("jd-file").files;
    const resumes = document.getElementById("resume-files").files;
    if ((!jdText && (!jdFile || jdFile.length === 0)) || !resumes || resumes.length === 0) {
      appendMessage("assistant", "Please provide a JD (text or file) and at least one resume.");
      return;
    }

    showSpinner(true);
    try {
      const fd = new FormData();
      for (const f of resumes) fd.append("files", f);
      if (jdFile && jdFile.length === 1) fd.append("files", jdFile[0]);
      const up = await fetch("/api/files/upload", { method: "POST", body: fd });
      if (!up.ok) throw new Error(`upload failed ${up.status}`);
      const data = await up.json();

      const fileIds = data.files.map(f => f.id);
      let jdFileId = null;
      if (jdFile && jdFile.length === 1) {
        const last = data.files[data.files.length - 1];
        jdFileId = last.id;
      }

      let msg = "Please run resume matching on the resumes I just uploaded.";
      if (jdText) msg += ` JD Text:\n${jdText}`;
      if (jdFileId) msg += ` Also use the uploaded JD file (template_id: ${jdFileId}).`;

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, session_id: sessionId, attachment_ids: fileIds }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const out = await res.json();
      appendToolTrace(out.tool_calls);
      appendMessage("assistant", out.final);
    } catch (e) {
      appendMessage("assistant", `Upload/Match error: ${e.message}`);
    } finally {
      showSpinner(false);
      closePanels();
    }
  });
}

/* ---------- user send ---------- */
elForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = elInput.value.trim();
  if (!text) return;
  appendMessage("you", text);
  elInput.value = "";

  if (shouldShowMergeFromUser(text)) { closePanels(); showMergePanel(); }
  if (shouldShowResumeFromUser(text)) { closePanels(); showResumePanel(); }

  showSpinner(true);
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: sessionId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    appendToolTrace(data.tool_calls);
    appendMessage("assistant", data.final);
  } catch (err) {
    appendMessage("assistant", `Oops: ${err.message}`);
  } finally {
    showSpinner(false);
  }
});

/* ---------- welcome ---------- */
appendMessage("assistant", "Hi! I can merge documents or match resumes to a JD. Tell me what you’d like to do.");
