// ProctorCode Application Frontend Engine
let state = {
  token: localStorage.getItem("proctor_token") || null,
  user: JSON.parse(localStorage.getItem("proctor_user") || "null"),
  quizzes: [],
  currentExam: null, // Active exam metadata & session
  currentQuestionIdx: 0,
  userAnswers: {},
  timerInterval: null,
  autoSaveInterval: null,
  proctoringActive: false,
  pendingFileQuestions: [],
  selectedFile: null
};

// ----------------- TOAST NOTIFICATIONS -----------------
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  const bg = type === "error" ? "bg-rose-600" : type === "success" ? "bg-emerald-600" : type === "warning" ? "bg-amber-600" : "bg-indigo-600";
  const icon = type === "error" ? "fa-circle-xmark" : type === "success" ? "fa-circle-check" : type === "warning" ? "fa-triangle-exclamation" : "fa-circle-info";

  toast.className = `${bg} text-white text-xs px-4 py-2.5 rounded-xl shadow-xl flex items-center space-x-2 transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto`;
  toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ----------------- API HELPER -----------------
async function apiCall(endpoint, method = "GET", body = null, isFormData = false) {
  const headers = {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const options = { method, headers };
  if (body) {
    options.body = isFormData ? body : JSON.stringify(body);
  }

  try {
    const res = await fetch(endpoint, options);
    if (res.status === 401) {
      handleLogout("Session expired. Please sign in again.");
      return null;
    }
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Request failed");
    }
    return data;
  } catch (err) {
    showToast(err.message, "error");
    throw err;
  }
}

// ----------------- AUTHENTICATION -----------------
function switchAuthTab(tab) {
  const isLogin = tab === "login";
  document.getElementById("loginForm").classList.toggle("hidden", !isLogin);
  document.getElementById("registerForm").classList.toggle("hidden", isLogin);
  document.getElementById("tabLogin").className = isLogin ? "flex-1 py-2 text-xs font-semibold rounded-md transition bg-brand-600 text-white" : "flex-1 py-2 text-xs font-semibold rounded-md transition text-slate-400 hover:text-white";
  document.getElementById("tabRegister").className = !isLogin ? "flex-1 py-2 text-xs font-semibold rounded-md transition bg-brand-600 text-white" : "flex-1 py-2 text-xs font-semibold rounded-md transition text-slate-400 hover:text-white";
}

function fillDemoUser(username, password) {
  document.getElementById("loginUsername").value = username;
  document.getElementById("loginPassword").value = password;
  switchAuthTab("login");
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById("loginUsername").value.trim();
  const password = document.getElementById("loginPassword").value;

  try {
    const res = await apiCall("/api/auth/login", "POST", { username, password });
    if (res && res.access_token) {
      state.token = res.access_token;
      state.user = res.user;
      localStorage.setItem("proctor_token", state.token);
      localStorage.setItem("proctor_user", JSON.stringify(state.user));
      showToast(`Welcome back, ${state.user.full_name}!`, "success");
      updateAppState();
    }
  } catch (err) {}
}

async function handleRegister(e) {
  e.preventDefault();
  const full_name = document.getElementById("regFullName").value.trim();
  const username = document.getElementById("regUsername").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value;
  const role = document.getElementById("regRole").value;

  try {
    const res = await apiCall("/api/auth/register", "POST", { full_name, username, email, password, role });
    if (res && res.access_token) {
      state.token = res.access_token;
      state.user = res.user;
      localStorage.setItem("proctor_token", state.token);
      localStorage.setItem("proctor_user", JSON.stringify(state.user));
      showToast("Account registered successfully!", "success");
      updateAppState();
    }
  } catch (err) {}
}

function handleLogout(msg = "Signed out successfully") {
  state.token = null;
  state.user = null;
  state.currentExam = null;
  localStorage.removeItem("proctor_token");
  localStorage.removeItem("proctor_user");
  clearInterval(state.timerInterval);
  clearInterval(state.autoSaveInterval);
  stopProctoringListeners();

  document.getElementById("userBadge").classList.add("hidden");
  document.getElementById("logoutBtn").classList.add("hidden");
  showToast(msg, "info");
  updateAppState();
}

// ----------------- APP STATE & VIEW ROUTER -----------------
function updateAppState() {
  const views = ["authView", "instructorView", "studentView", "examLockdownPromptView", "examArenaView", "submissionSuccessView"];
  views.forEach(v => {
    const el = document.getElementById(v);
    if (el) el.classList.add("hidden");
  });

  if (!state.token || !state.user) {
    document.getElementById("authView").classList.remove("hidden");
    document.getElementById("mainNav").classList.remove("hidden");
    return;
  }

  // Update Navigation UI
  document.getElementById("userBadge").classList.remove("hidden");
  document.getElementById("userBadge").classList.add("flex");
  document.getElementById("logoutBtn").classList.remove("hidden");
  document.getElementById("navUserName").textContent = state.user.full_name;
  document.getElementById("navUserRole").textContent = state.user.role;

  if (state.user.role === "admin" || state.user.role === "instructor") {
    document.getElementById("instructorView").classList.remove("hidden");
    document.getElementById("roleBadgeHeader").textContent = state.user.role.toUpperCase();
    loadQuizzes();
    loadResultsList();
  } else {
    document.getElementById("studentView").classList.remove("hidden");
    loadQuizzes();
  }
}

// ----------------- INSTRUCTOR PORTAL -----------------
function switchInstructorTab(tab) {
  const isQuizzes = tab === "quizzes";
  document.getElementById("instructorQuizzesTab").classList.toggle("hidden", !isQuizzes);
  document.getElementById("instructorResultsTab").classList.toggle("hidden", isQuizzes);

  document.getElementById("btnTabQuizzes").className = isQuizzes ? "px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg border border-slate-700 transition" : "px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-semibold rounded-lg border border-slate-800 transition";
  document.getElementById("btnTabResults").className = !isQuizzes ? "px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg border border-slate-700 transition" : "px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white text-xs font-semibold rounded-lg border border-slate-800 transition";
}

async function loadQuizzes() {
  try {
    const data = await apiCall("/api/quizzes");
    if (!data) return;
    state.quizzes = data.quizzes;

    if (state.user.role === "admin" || state.user.role === "instructor") {
      renderInstructorQuizzes();
    } else {
      renderStudentQuizzes();
    }
  } catch (err) {}
}

function renderInstructorQuizzes() {
  const container = document.getElementById("instructorQuizList");
  document.getElementById("quizCountLabel").textContent = `Showing ${state.quizzes.length} quizzes`;
  container.innerHTML = "";

  if (state.quizzes.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-500 text-xs">
        <i class="fa-solid fa-folder-open text-3xl mb-2 block"></i>
        No quizzes created yet. Click "Create Quiz" above to get started.
      </div>
    `;
    return;
  }

  state.quizzes.forEach(q => {
    const card = document.createElement("div");
    card.className = "bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 shadow-lg flex flex-col justify-between space-y-4 transition";
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-2">
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-950 text-indigo-300 border border-indigo-800 uppercase tracking-wider">${q.code}</span>
          <span class="text-[11px] px-2 py-0.5 rounded ${q.is_active ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-slate-800 text-slate-400'} font-semibold">
            ${q.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
        <h4 class="font-bold text-white text-sm leading-snug">${q.title}</h4>
        <p class="text-xs text-slate-400 mt-1 line-clamp-2">${q.description || 'No description provided.'}</p>
        
        <div class="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-300">
          <div>
            <span class="text-slate-500 block text-[10px]">DURATION</span>
            <span class="font-bold text-amber-400"><i class="fa-solid fa-clock mr-1"></i>${q.duration_minutes}m</span>
          </div>
          <div>
            <span class="text-slate-500 block text-[10px]">QUESTIONS</span>
            <span class="font-bold text-indigo-300"><i class="fa-solid fa-circle-question mr-1"></i>${q.question_count}</span>
          </div>
          <div>
            <span class="text-slate-500 block text-[10px]">MAX STRIKES</span>
            <span class="font-bold text-rose-400"><i class="fa-solid fa-shield-halved mr-1"></i>${q.max_violations}</span>
          </div>
        </div>
      </div>

      <div class="space-y-2 pt-2 border-t border-slate-800 text-xs">
        <div class="grid grid-cols-2 gap-2">
          <button onclick="openManageQuestionsModal(${q.id})" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-indigo-300 font-semibold rounded-lg border border-slate-700 transition flex items-center justify-center space-x-1">
            <i class="fa-solid fa-list-check"></i>
            <span>Questions</span>
          </button>
          <button onclick="openUploadQuestionsModal(${q.id})" class="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-300 font-semibold rounded-lg border border-slate-700 transition flex items-center justify-center space-x-1">
            <i class="fa-solid fa-file-arrow-up"></i>
            <span>Upload File</span>
          </button>
        </div>
        <div class="flex items-center space-x-2">
          <button onclick="openEditQuizModal(${q.id})" class="flex-1 py-1.5 bg-indigo-900/40 hover:bg-indigo-900/60 text-indigo-200 border border-indigo-800 rounded-lg font-semibold transition text-center">
            <i class="fa-solid fa-gear mr-1"></i> Edit Duration & Settings
          </button>
          <button onclick="handleDeleteQuiz(${q.id})" class="p-1.5 px-2.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-900/60 rounded-lg transition" title="Delete Quiz">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// ----------------- CREATE & EDIT QUIZZES -----------------
function openCreateQuizModal() {
  document.getElementById("createQuizTitle").value = "";
  document.getElementById("createQuizCode").value = "";
  document.getElementById("createQuizDuration").value = "30";
  document.getElementById("createQuizViolations").value = "3";
  document.getElementById("createQuizDesc").value = "";
  openModal("createQuizModal");
}

async function handleCreateQuiz(e) {
  e.preventDefault();
  const title = document.getElementById("createQuizTitle").value.trim();
  const code = document.getElementById("createQuizCode").value.trim().toUpperCase();
  const duration_minutes = parseInt(document.getElementById("createQuizDuration").value);
  const max_violations = parseInt(document.getElementById("createQuizViolations").value);
  const description = document.getElementById("createQuizDesc").value.trim();

  try {
    await apiCall("/api/quizzes", "POST", { title, code, duration_minutes, max_violations, description });
    showToast("Quiz created successfully!", "success");
    closeModal("createQuizModal");
    loadQuizzes();
  } catch (err) {}
}

function openEditQuizModal(quizId) {
  const quiz = state.quizzes.find(q => q.id === quizId);
  if (!quiz) return;

  document.getElementById("editQuizId").value = quiz.id;
  document.getElementById("editQuizTitle").value = quiz.title;
  document.getElementById("editQuizDuration").value = quiz.duration_minutes;
  document.getElementById("editQuizViolations").value = quiz.max_violations;
  document.getElementById("editQuizActive").value = quiz.is_active ? "true" : "false";
  document.getElementById("editQuizDesc").value = quiz.description || "";
  openModal("editQuizModal");
}

async function handleSaveQuizSettings(e) {
  e.preventDefault();
  const quizId = document.getElementById("editQuizId").value;
  const title = document.getElementById("editQuizTitle").value.trim();
  const duration_minutes = parseInt(document.getElementById("editQuizDuration").value);
  const max_violations = parseInt(document.getElementById("editQuizViolations").value);
  const is_active = document.getElementById("editQuizActive").value === "true";
  const description = document.getElementById("editQuizDesc").value.trim();

  try {
    await apiCall(`/api/quizzes/${quizId}`, "PUT", { title, duration_minutes, max_violations, is_active, description });
    showToast("Quiz duration and settings updated!", "success");
    closeModal("editQuizModal");
    loadQuizzes();
  } catch (err) {}
}

async function handleDeleteQuiz(quizId) {
  if (!confirm("Are you sure you want to delete this quiz and all its questions/submissions?")) return;
  try {
    await apiCall(`/api/quizzes/${quizId}`, "DELETE");
    showToast("Quiz deleted successfully.", "info");
    loadQuizzes();
  } catch (err) {}
}

// ----------------- DOCUMENT FILE UPLOAD & PARSER (DOCX/PDF/TXT) -----------------
function openUploadQuestionsModal(quizId) {
  document.getElementById("uploadQuizId").value = quizId;
  document.getElementById("fileInput").value = "";
  document.getElementById("fileSelectLabel").textContent = "Click to browse or drop file here";
  document.getElementById("uploadPreviewSection").classList.add("hidden");
  document.getElementById("btnConfirmImport").disabled = true;
  state.selectedFile = null;
  state.pendingFileQuestions = [];
  openModal("uploadQuestionsModal");
}

async function handleFileSelected(e) {
  const file = e.target.files[0];
  if (!file) return;

  state.selectedFile = file;
  document.getElementById("fileSelectLabel").textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

  // Call preview API
  const formData = new FormData();
  formData.append("file", file);

  try {
    showToast("Analyzing file contents...", "info");
    const previewData = await apiCall("/api/quizzes/parse-file-preview", "POST", formData, true);
    if (!previewData || !previewData.questions) return;

    state.pendingFileQuestions = previewData.questions;
    renderFilePreview(previewData.questions);
    document.getElementById("btnConfirmImport").disabled = false;
    showToast(`Found ${previewData.questions.length} questions! Click 'Import to Quiz' to save.`, "success");
  } catch (err) {}
}

function renderFilePreview(questions) {
  const container = document.getElementById("previewList");
  const countLabel = document.getElementById("previewCountLabel");
  countLabel.textContent = `Parsed ${questions.length} Questions Ready for Import:`;
  container.innerHTML = "";

  questions.forEach((q, idx) => {
    const item = document.createElement("div");
    item.className = "p-2.5 rounded bg-slate-900 border border-slate-800 space-y-1 text-[11px]";
    const isCoding = q.question_type === "coding";
    item.innerHTML = `
      <div class="flex items-center justify-between font-semibold">
        <span class="text-white">${idx + 1}. ${q.title}</span>
        <span class="text-[10px] uppercase px-1.5 py-0.5 rounded ${isCoding ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-indigo-950 text-indigo-300 border border-indigo-800'}">
          ${q.question_type}
        </span>
      </div>
      ${!isCoding && q.options && q.options.length ? `
        <div class="text-slate-400 pl-2">
          ${q.options.map(opt => `<div>• ${opt}</div>`).join('')}
          <div class="text-emerald-400 font-semibold mt-1">Ans: ${q.correct_answer || 'A'}</div>
        </div>
      ` : ''}
      ${isCoding ? `
        <div class="text-slate-400 pl-2">
          <div>Test cases: ${q.test_cases ? q.test_cases.length : 0} defined</div>
        </div>
      ` : ''}
    `;
    container.appendChild(item);
  });

  document.getElementById("uploadPreviewSection").classList.remove("hidden");
}

async function confirmImportQuestions() {
  if (!state.selectedFile) return;
  const quizId = document.getElementById("uploadQuizId").value;
  const formData = new FormData();
  formData.append("file", state.selectedFile);

  try {
    const res = await apiCall(`/api/quizzes/${quizId}/upload-questions`, "POST", formData, true);
    showToast(res.message, "success");
    closeModal("uploadQuestionsModal");
    loadQuizzes();
  } catch (err) {}
}

// ----------------- QUESTION MANAGEMENT -----------------
async function openManageQuestionsModal(quizId) {
  document.getElementById("currentManageQuizId").value = quizId;
  const quiz = await apiCall(`/api/quizzes/${quizId}`);
  if (!quiz) return;

  document.getElementById("manageQuizTitleLabel").textContent = `Questions: ${quiz.title}`;
  document.getElementById("manageQuizQuestionsCount").textContent = `${quiz.questions.length} questions configured`;

  const container = document.getElementById("quizQuestionsContainer");
  container.innerHTML = "";

  if (quiz.questions.length === 0) {
    container.innerHTML = `<div class="py-8 text-center text-slate-500">No questions in this quiz yet. Add questions below or upload a Word/PDF/TXT file.</div>`;
  } else {
    quiz.questions.forEach((q, idx) => {
      const card = document.createElement("div");
      card.className = "bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2";
      const isCoding = q.question_type === "coding";

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div class="flex items-center space-x-2">
            <span class="w-5 h-5 rounded-full bg-brand-900 text-brand-300 font-bold flex items-center justify-center text-[10px]">${idx + 1}</span>
            <span class="font-bold text-white text-xs">${q.title}</span>
            <span class="text-[10px] uppercase px-1.5 py-0.5 rounded ${isCoding ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-indigo-950 text-indigo-300 border border-indigo-800'}">${q.question_type}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-indigo-400 font-semibold text-[11px]">${q.points} Pts</span>
            <button onclick="handleDeleteQuestion(${quiz.id}, ${q.id})" class="text-rose-400 hover:text-rose-300 ml-2" title="Delete Question"><i class="fa-solid fa-trash"></i></button>
          </div>
        </div>
        ${q.description ? `<p class="text-slate-400 text-[11px] whitespace-pre-line">${q.description}</p>` : ''}
        ${!isCoding && q.options && q.options.length ? `
          <div class="space-y-1 pl-4 pt-1 text-[11px] text-slate-300">
            ${q.options.map(opt => `<div>• ${opt}</div>`).join('')}
            <div class="text-emerald-400 font-bold mt-1">Correct Answer: ${q.correct_answer || 'A'}</div>
            ${q.explanation ? `<div class="text-slate-500 italic">Explanation: ${q.explanation}</div>` : ''}
          </div>
        ` : ''}
        ${isCoding ? `
          <div class="pl-4 pt-1 text-[11px] text-slate-400">
            <div class="font-mono text-indigo-300">Template: ${q.starter_code ? q.starter_code.split('\n')[0] : 'None'}...</div>
            <div class="text-slate-400">Test Cases: ${(q.all_test_cases || q.test_cases || []).length} total</div>
          </div>
        ` : ''}
      `;
      container.appendChild(card);
    });
  }

  openModal("manageQuestionsModal");
}

async function handleDeleteQuestion(quizId, questionId) {
  if (!confirm("Delete this question?")) return;
  try {
    await apiCall(`/api/quizzes/${quizId}/questions/${questionId}`, "DELETE");
    showToast("Question deleted", "info");
    openManageQuestionsModal(quizId);
    loadQuizzes();
  } catch (err) {}
}

function openAddQuestionForm(type) {
  document.getElementById("addQType").value = type;
  document.getElementById("addQuestionModalTitle").textContent = type === "coding" ? "Add Programming Problem" : "Add Multiple Choice Question";
  document.getElementById("addQTitle").value = "";
  document.getElementById("addQDesc").value = "";
  document.getElementById("addQPoints").value = type === "coding" ? "15" : "5";

  document.getElementById("mcqSpecificFields").classList.toggle("hidden", type !== "mcq");
  document.getElementById("codingSpecificFields").classList.toggle("hidden", type !== "coding");

  openModal("addQuestionModal");
}

async function handleSaveManualQuestion(e) {
  e.preventDefault();
  const quizId = document.getElementById("currentManageQuizId").value;
  const type = document.getElementById("addQType").value;
  const title = document.getElementById("addQTitle").value.trim();
  const description = document.getElementById("addQDesc").value.trim();
  const points = parseInt(document.getElementById("addQPoints").value);

  const payload = {
    question_type: type,
    title,
    description,
    points,
    options: [],
    test_cases: []
  };

  if (type === "mcq") {
    const optA = document.getElementById("addQOptA").value.trim();
    const optB = document.getElementById("addQOptB").value.trim();
    const optC = document.getElementById("addQOptC").value.trim();
    const optD = document.getElementById("addQOptD").value.trim();
    payload.options = [optA, optB, optC, optD].filter(Boolean);
    payload.correct_answer = document.getElementById("addQCorrect").value.trim().toUpperCase() || "A";
    payload.explanation = document.getElementById("addQExplanation").value.trim();
  } else if (type === "coding") {
    payload.starter_code = document.getElementById("addQStarterCode").value;
    payload.language = "python";
    const tc1In = document.getElementById("addQTC1In").value;
    const tc1Out = document.getElementById("addQTC1Out").value;
    const tc2In = document.getElementById("addQTC2In").value;
    const tc2Out = document.getElementById("addQTC2Out").value;
    if (tc1In || tc1Out) payload.test_cases.push({ input: tc1In, expected_output: tc1Out, is_hidden: false });
    if (tc2In || tc2Out) payload.test_cases.push({ input: tc2In, expected_output: tc2Out, is_hidden: true });
  }

  try {
    await apiCall(`/api/quizzes/${quizId}/questions`, "POST", payload);
    showToast("Question added successfully!", "success");
    closeModal("addQuestionModal");
    openManageQuestionsModal(quizId);
    loadQuizzes();
  } catch (err) {}
}

// ----------------- RESULTS & PROCTORING AUDIT (STAFF ONLY) -----------------
async function loadResultsList() {
  try {
    const data = await apiCall("/api/results");
    if (!data) return;
    renderResultsTable(data.results);
  } catch (err) {}
}

function renderResultsTable(results) {
  const tbody = document.getElementById("resultsTableBody");
  tbody.innerHTML = "";

  if (results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-slate-500">No submissions recorded yet.</td></tr>`;
    return;
  }

  results.forEach(sub => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-800/40 transition";
    const passed = sub.percentage >= 60;
    const hasViolations = sub.violation_count > 0;

    tr.innerHTML = `
      <td class="py-3 px-4">
        <span class="font-bold text-white block">${sub.user_name}</span>
        <span class="text-slate-400 text-[10px]">${sub.user_email}</span>
      </td>
      <td class="py-3 px-4">
        <span class="font-semibold text-indigo-300 block">${sub.quiz_code}</span>
        <span class="text-slate-400 text-[10px] truncate max-w-xs block">${sub.quiz_title}</span>
      </td>
      <td class="py-3 px-4 font-mono font-bold text-white">${sub.score} / ${sub.total_points}</td>
      <td class="py-3 px-4 font-bold ${passed ? 'text-emerald-400' : 'text-rose-400'}">${sub.percentage}%</td>
      <td class="py-3 px-4">
        <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${hasViolations ? 'bg-rose-950 text-rose-300 border border-rose-800' : 'bg-emerald-950 text-emerald-300 border border-emerald-800'}">
          <i class="fa-solid fa-shield-halved mr-1"></i>${sub.violation_count} Violations
        </span>
      </td>
      <td class="py-3 px-4">
        <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded ${sub.status === 'auto_submitted_violations' ? 'bg-rose-950 text-rose-400' : 'bg-slate-800 text-slate-300'}">
          ${sub.status === 'auto_submitted_violations' ? 'DISQUALIFIED' : 'SUBMITTED'}
        </span>
      </td>
      <td class="py-3 px-4 text-slate-400 text-[11px]">${sub.submitted_at ? new Date(sub.submitted_at).toLocaleString() : '--'}</td>
      <td class="py-3 px-4 text-right">
        <button onclick="openSubmissionAuditReport(${sub.id})" class="px-2.5 py-1.5 bg-indigo-900/40 hover:bg-indigo-900/80 text-indigo-200 border border-indigo-800/80 rounded-lg text-xs font-semibold transition">
          <i class="fa-solid fa-file-waveform mr-1"></i> Audit Details
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function openSubmissionAuditReport(subId) {
  try {
    const data = await apiCall(`/api/results/${subId}`);
    if (!data) return;

    document.getElementById("auditModalSubtitle").textContent = `Candidate: ${data.user_name} (${data.user_email}) | Quiz: ${data.quiz_code} - ${data.quiz_title}`;
    document.getElementById("auditScoreVal").textContent = `${data.score} / ${data.total_points}`;
    document.getElementById("auditPercentageVal").textContent = `${data.percentage}%`;
    document.getElementById("auditViolationsVal").textContent = `${data.violation_count}`;
    document.getElementById("auditStatusVal").textContent = data.status === "auto_submitted_violations" ? "DISQUALIFIED (VIOLATION LIMIT)" : "SUBMITTED";
    document.getElementById("auditViolationCountBadge").textContent = `${(data.violation_logs || []).length} events`;

    // Render Timeline Log
    const timelineContainer = document.getElementById("auditViolationTimeline");
    timelineContainer.innerHTML = "";
    const logs = data.violation_logs || [];
    if (logs.length === 0) {
      timelineContainer.innerHTML = `<div class="text-emerald-400 text-[11px]"><i class="fa-solid fa-check-circle mr-1"></i> Clean record. No proctoring violations recorded during this exam session.</div>`;
    } else {
      logs.forEach((item, i) => {
        const row = document.createElement("div");
        row.className = "flex items-start space-x-2 text-[11px] bg-slate-900/80 p-2 rounded border border-rose-900/40 text-slate-300";
        row.innerHTML = `
          <span class="font-bold text-rose-400">#${i + 1}</span>
          <span class="text-slate-400 font-mono text-[10px]">[${new Date(item.timestamp).toLocaleTimeString()}]</span>
          <span class="font-semibold text-rose-300 uppercase text-[10px]">${item.type}:</span>
          <span class="text-slate-300">${item.details}</span>
        `;
        timelineContainer.appendChild(row);
      });
    }

    // Render Question Breakdown
    const qContainer = document.getElementById("auditQuestionsBreakdown");
    qContainer.innerHTML = "";
    (data.questions_breakdown || []).forEach((q, idx) => {
      const qCard = document.createElement("div");
      qCard.className = "bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2";
      const isCoding = q.question_type === "coding";

      qCard.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs">${idx + 1}. ${q.title}</span>
          <span class="text-[10px] text-indigo-400 font-semibold">${q.points} Pts</span>
        </div>
        ${!isCoding ? `
          <div class="grid grid-cols-2 gap-2 text-[11px] pt-1">
            <div class="p-2 rounded bg-slate-900 border border-slate-800">
              <span class="text-slate-500 block text-[10px]">CANDIDATE ANSWER</span>
              <span class="font-bold text-white">${q.student_answer || '<span class="text-slate-500">Unanswered</span>'}</span>
            </div>
            <div class="p-2 rounded bg-slate-900 border border-slate-800">
              <span class="text-slate-500 block text-[10px]">CORRECT ANSWER</span>
              <span class="font-bold text-emerald-400">${q.correct_answer}</span>
            </div>
          </div>
          ${q.explanation ? `<div class="text-[11px] text-slate-500 italic pl-1">Note: ${q.explanation}</div>` : ''}
        ` : `
          <div class="space-y-2 pt-1 text-[11px]">
            <div>
              <span class="text-slate-500 text-[10px] block mb-1">CANDIDATE PYTHON CODE:</span>
              <pre class="p-2 rounded bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-200 overflow-x-auto">${q.student_answer || '# No code submitted'}</pre>
            </div>
            ${q.coding_result ? `
              <div class="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] flex items-center justify-between">
                <span>Evaluation: <strong>${q.coding_result.passed || 0} / ${q.coding_result.total || 0} test cases passed</strong></span>
                <span class="${q.coding_result.all_passed ? 'text-emerald-400' : 'text-amber-400'} font-bold">
                  ${q.coding_result.all_passed ? 'ALL TEST CASES PASSED' : 'PARTIAL / FAILED'}
                </span>
              </div>
            ` : ''}
          </div>
        `}
      `;
      qContainer.appendChild(qCard);
    });

    openModal("submissionAuditModal");
  } catch (err) {}
}

function exportResultsCSV() {
  window.open("/api/results/export/csv", "_blank");
}

// ----------------- STUDENT EXAM WORKFLOW -----------------
function renderStudentQuizzes() {
  const container = document.getElementById("studentQuizList");
  container.innerHTML = "";

  if (state.quizzes.length === 0) {
    container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-500 text-xs">No active assessments available at this time.</div>`;
    return;
  }

  state.quizzes.forEach(q => {
    const card = document.createElement("div");
    card.className = "bg-slate-900 border border-slate-800 hover:border-brand-500/50 rounded-2xl p-6 shadow-xl flex flex-col justify-between space-y-4 transition";
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-3">
          <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-950 text-indigo-300 border border-indigo-800 uppercase tracking-wider">${q.code}</span>
          <span class="text-xs text-amber-400 font-bold flex items-center space-x-1">
            <i class="fa-solid fa-clock"></i>
            <span>${q.duration_minutes} Minutes</span>
          </span>
        </div>
        <h3 class="font-extrabold text-white text-base leading-snug">${q.title}</h3>
        <p class="text-xs text-slate-400 mt-2 leading-relaxed line-clamp-3">${q.description || 'Full-stack assessment under strict proctoring supervision.'}</p>
      </div>

      <div class="space-y-3 pt-3 border-t border-slate-800">
        <div class="flex items-center justify-between text-[11px] text-slate-400">
          <span><i class="fa-solid fa-circle-question text-indigo-400 mr-1"></i>${q.question_count} Questions</span>
          <span><i class="fa-solid fa-shield-halved text-rose-400 mr-1"></i>Max ${q.max_violations} Violations</span>
        </div>
        <button onclick="promptExamLockdown(${q.id})" class="w-full py-2.5 bg-brand-600 hover:bg-brand-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-brand-600/30 transition flex items-center justify-center space-x-2">
          <i class="fa-solid fa-play text-[11px]"></i>
          <span>Start Proctored Exam</span>
        </button>
      </div>
    `;
    container.appendChild(card);
  });
}

function promptExamLockdown(quizId) {
  const quiz = state.quizzes.find(q => q.id === quizId);
  if (!quiz) return;

  if (!quiz.question_count || quiz.question_count === 0) {
    showToast("This assessment does not have any questions configured yet.", "warning");
    return;
  }

  state.currentExam = { quizId, quiz };
  document.getElementById("promptQuizTitle").textContent = quiz.title;
  document.getElementById("promptQuizCode").textContent = `Assessment Code: ${quiz.code} | Duration: ${quiz.duration_minutes} Mins`;
  document.getElementById("promptMaxViolations").textContent = quiz.max_violations;

  document.getElementById("examLockdownPromptView").classList.remove("hidden");
}

function cancelExamStart() {
  document.getElementById("examLockdownPromptView").classList.add("hidden");
  state.currentExam = null;
}

async function launchFullscreenAndStartExam() {
  document.getElementById("examLockdownPromptView").classList.add("hidden");

  // Initialize and unlock AudioContext on user gesture
  getAudioContext();

  // Request browser Fullscreen
  try {
    if (document.documentElement.requestFullscreen) {
      await document.documentElement.requestFullscreen();
    } else if (document.documentElement.webkitRequestFullscreen) {
      await document.documentElement.webkitRequestFullscreen();
    }
  } catch (err) {
    console.warn("Fullscreen request declined or unsupported:", err);
  }

  // Start exam session in backend
  try {
    const sessionData = await apiCall(`/api/quizzes/${state.currentExam.quizId}/start`, "POST");
    if (!sessionData) return;

    // Use integer remaining_seconds from backend (100% immune to client timezone offset)
    const remainingSec = (sessionData.remaining_seconds != null) ? sessionData.remaining_seconds : (sessionData.duration_minutes * 60);

    state.currentExam = {
      ...state.currentExam,
      submissionId: sessionData.submission_id,
      quiz: sessionData.quiz,
      expiresAt: Date.now() + (remainingSec * 1000),
      violations: sessionData.current_violations || 0,
      maxViolations: sessionData.max_violations,
      questions: sessionData.quiz.questions || []
    };

    state.userAnswers = sessionData.saved_answers || {};
    state.currentQuestionIdx = 0;

    startProctoredArena();
  } catch (err) {}
}

function startProctoredArena() {
  document.getElementById("studentView").classList.add("hidden");
  document.getElementById("mainNav").classList.add("hidden");
  document.getElementById("examArenaView").classList.remove("hidden");

  // Setup UI meta
  document.getElementById("arenaQuizTitle").textContent = state.currentExam.quiz.title;
  document.getElementById("arenaQuizCode").textContent = state.currentExam.quiz.code;
  document.getElementById("arenaMaxViolations").textContent = state.currentExam.maxViolations;
  document.getElementById("arenaViolations").textContent = state.currentExam.violations;

  // Setup Question Grid Nav
  renderArenaQuestionNav();
  renderCurrentQuestion();

  // Start Live Timer
  startCountdownTimer();

  // Start Auto-save every 15s
  clearInterval(state.autoSaveInterval);
  state.autoSaveInterval = setInterval(autoSaveProgress, 15000);

  // Activate Proctoring Listeners
  startProctoringListeners();
}

function renderArenaQuestionNav() {
  const container = document.getElementById("arenaQuestionGrid");
  container.innerHTML = "";
  const total = state.currentExam.questions.length;

  let answeredCount = 0;
  state.currentExam.questions.forEach((q, idx) => {
    const hasAnswer = Boolean(state.userAnswers[q.id]);
    if (hasAnswer) answeredCount++;

    const btn = document.createElement("button");
    const isCurrent = idx === state.currentQuestionIdx;

    let bg = "bg-slate-800 text-slate-300 border-slate-700";
    if (isCurrent) {
      bg = "bg-brand-600 text-white font-bold border-brand-400";
    } else if (hasAnswer) {
      bg = "bg-emerald-600 text-white font-semibold border-emerald-400";
    }

    btn.className = `w-10 h-10 rounded-lg text-xs font-semibold border ${bg} transition flex items-center justify-center shadow-sm`;
    btn.textContent = idx + 1;
    btn.onclick = () => {
      saveActiveQuestionAnswer();
      state.currentQuestionIdx = idx;
      renderArenaQuestionNav();
      renderCurrentQuestion();
    };
    container.appendChild(btn);
  });

  document.getElementById("arenaNavProgress").textContent = `${answeredCount} / ${total}`;
}

function renderCurrentQuestion() {
  const q = state.currentExam.questions[state.currentQuestionIdx];
  if (!q) return;

  const total = state.currentExam.questions.length;
  document.getElementById("arenaQuestionNumberBadge").textContent = `Question ${state.currentQuestionIdx + 1} of ${total}`;
  document.getElementById("arenaQuestionTypeBadge").textContent = q.question_type.toUpperCase();
  document.getElementById("arenaQuestionPoints").textContent = `${q.points} Points`;
  document.getElementById("arenaQuestionTitle").textContent = q.title;
  document.getElementById("arenaQuestionDesc").textContent = q.description || "";

  // Prev / Next button states
  document.getElementById("btnPrevQuestion").disabled = state.currentQuestionIdx === 0;
  document.getElementById("btnPrevQuestion").classList.toggle("opacity-50", state.currentQuestionIdx === 0);
  document.getElementById("btnNextQuestion").innerHTML = state.currentQuestionIdx === total - 1 ? `<span>Review & Finish</span> <i class="fa-solid fa-check ml-1"></i>` : `<span>Next</span> <i class="fa-solid fa-arrow-right ml-1"></i>`;

  const isCoding = q.question_type === "coding";
  document.getElementById("arenaMcqContainer").classList.toggle("hidden", isCoding);
  document.getElementById("arenaCodingContainer").classList.toggle("hidden", !isCoding);

  if (isCoding) {
    // Setup Code Editor
    const editor = document.getElementById("arenaCodeEditor");
    editor.value = state.userAnswers[q.id] || q.starter_code || "# Write your python solution here\n";
    document.getElementById("arenaTerminalDrawer").classList.add("hidden");

    // Enable Tab indentation inside textarea
    editor.onkeydown = function(e) {
      if (e.key === "Tab") {
        e.preventDefault();
        const start = this.selectionStart;
        const end = this.selectionEnd;
        this.value = this.value.substring(0, start) + "    " + this.value.substring(end);
        this.selectionStart = this.selectionEnd = start + 4;
      }
    };
  } else {
    // Render MCQ Options
    const optContainer = document.getElementById("arenaOptionsList");
    optContainer.innerHTML = "";
    const savedAns = state.userAnswers[q.id] || "";

    (q.options || []).forEach(opt => {
      const optLetter = opt.substring(0, 1).toUpperCase();
      const isSelected = savedAns === opt || savedAns === optLetter || savedAns.startsWith(optLetter);

      const label = document.createElement("label");
      label.className = `flex items-center space-x-3 p-3.5 rounded-xl border cursor-pointer transition ${isSelected ? 'bg-indigo-950/70 border-brand-500 text-white shadow-md' : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'}`;
      label.innerHTML = `
        <input type="radio" name="mcqOption" value="${opt}" ${isSelected ? 'checked' : ''} class="w-4 h-4 text-brand-600 focus:ring-brand-500 bg-slate-950 border-slate-700">
        <span class="text-xs font-medium leading-relaxed">${opt}</span>
      `;
      label.onclick = () => {
        state.userAnswers[q.id] = optLetter;
        renderArenaQuestionNav();
      };
      optContainer.appendChild(label);
    });
  }
}

function saveActiveQuestionAnswer() {
  const q = state.currentExam.questions[state.currentQuestionIdx];
  if (!q) return;

  if (q.question_type === "coding") {
    const code = document.getElementById("arenaCodeEditor").value;
    state.userAnswers[q.id] = code;
  }
}

function navigateQuestion(delta) {
  saveActiveQuestionAnswer();
  const nextIdx = state.currentQuestionIdx + delta;
  if (nextIdx >= 0 && nextIdx < state.currentExam.questions.length) {
    state.currentQuestionIdx = nextIdx;
    renderArenaQuestionNav();
    renderCurrentQuestion();
  } else if (nextIdx >= state.currentExam.questions.length) {
    confirmSubmitExam();
  }
}

async function handleRunSampleTests() {
  saveActiveQuestionAnswer();
  const q = state.currentExam.questions[state.currentQuestionIdx];
  const code = document.getElementById("arenaCodeEditor").value;

  const btn = document.getElementById("btnRunTests");
  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-[10px]"></i> <span>Running...</span>`;

  try {
    const res = await apiCall("/api/code/run-sample", "POST", {
      code,
      language: "python",
      test_cases: q.test_cases || []
    });

    const drawer = document.getElementById("arenaTerminalDrawer");
    const outputContainer = document.getElementById("arenaTerminalOutput");
    const summary = document.getElementById("arenaTerminalSummary");

    drawer.classList.remove("hidden");
    summary.innerHTML = `<span class="${res.all_passed ? 'text-emerald-400' : 'text-amber-400'} font-bold">${res.passed} of ${res.total} sample cases passed</span>`;
    outputContainer.innerHTML = "";

    (res.results || []).forEach(tc => {
      const row = document.createElement("div");
      row.className = `p-2.5 rounded bg-slate-950 border ${tc.passed ? 'border-emerald-800/80' : 'border-rose-800/80'} space-y-1`;
      row.innerHTML = `
        <div class="flex items-center justify-between text-[11px] font-bold">
          <span class="${tc.passed ? 'text-emerald-400' : 'text-rose-400'}">Case ${tc.case_number}: ${tc.status}</span>
          <span class="text-slate-500 font-mono text-[10px]">${tc.runtime_ms} ms</span>
        </div>
        ${tc.error ? `<div class="text-rose-300 text-[10px] font-mono whitespace-pre-wrap">${tc.error}</div>` : ''}
        ${!tc.is_hidden ? `
          <div class="grid grid-cols-2 gap-2 text-[10px] text-slate-400 pt-1">
            <div>Expected: <code class="text-slate-200">${tc.expected || 'None'}</code></div>
            <div>Actual: <code class="${tc.passed ? 'text-emerald-300' : 'text-rose-300'}">${tc.stdout || 'Empty'}</code></div>
          </div>
        ` : ''}
      `;
      outputContainer.appendChild(row);
    });

  } catch (err) {} finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-play text-[10px]"></i> <span>Run Sample Tests</span>`;
  }
}

function startCountdownTimer() {
  clearInterval(state.timerInterval);
  const timerEl = document.getElementById("arenaTimer");

  function tick() {
    if (!state.currentExam || !state.currentExam.expiresAt) return;
    const now = Date.now();
    const diff = Math.max(0, state.currentExam.expiresAt - now);

    const hours = Math.floor(diff / 3600000);
    const mins = Math.floor((diff % 3600000) / 60000);
    const secs = Math.floor((diff % 60000) / 1000);

    timerEl.textContent = `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

    if (diff <= 300000) { // Under 5 mins
      timerEl.classList.add("text-rose-400", "animate-pulse");
    } else {
      timerEl.classList.remove("text-rose-400", "animate-pulse");
    }

    if (diff <= 0) {
      clearInterval(state.timerInterval);
      showToast("Time expired! Automatically submitting exam...", "warning");
      doSubmitExam("timed_out");
    }
  }

  tick();
  state.timerInterval = setInterval(tick, 1000);
}

async function autoSaveProgress() {
  if (!state.currentExam || !state.currentExam.submissionId) return;
  saveActiveQuestionAnswer();
  try {
    await apiCall(`/api/submissions/${state.currentExam.submissionId}/save-progress`, "POST", {
      answers: state.userAnswers
    });
  } catch (err) {}
}

function confirmSubmitExam() {
  saveActiveQuestionAnswer();
  const total = state.currentExam.questions.length;
  const answered = Object.keys(state.userAnswers).length;
  if (confirm(`You have answered ${answered} of ${total} questions. Are you sure you want to finish and submit your exam?`)) {
    doSubmitExam("submitted");
  }
}

async function doSubmitExam(status = "submitted") {
  clearInterval(state.timerInterval);
  clearInterval(state.autoSaveInterval);
  stopProctoringListeners();

  saveActiveQuestionAnswer();
  try {
    const res = await apiCall(`/api/submissions/${state.currentExam.submissionId}/submit`, "POST", {
      answers: state.userAnswers
    });

    // Exit fullscreen
    if (document.fullscreenElement || document.webkitFullscreenElement) {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen().catch(() => {});
      }
    }

    document.getElementById("examArenaView").classList.add("hidden");
    document.getElementById("submissionSuccessView").classList.remove("hidden");
    document.getElementById("submissionTimestamp").textContent = `Submitted at: ${new Date().toLocaleTimeString()} (UTC ${new Date().toISOString()})`;

  } catch (err) {}
}

function returnToStudentDashboard() {
  document.getElementById("submissionSuccessView").classList.add("hidden");
  document.getElementById("mainNav").classList.remove("hidden");
  document.getElementById("studentView").classList.remove("hidden");
  state.currentExam = null;
  loadQuizzes();
}

// ----------------- ANTI-CHEATING PROCTORING SYSTEM -----------------
let sharedAudioCtx = null;
function getAudioContext() {
  try {
    if (!sharedAudioCtx) {
      const AudioCtxClass = window.AudioContext || window.webkitAudioContext;
      if (AudioCtxClass) {
        sharedAudioCtx = new AudioCtxClass();
      }
    }
    if (sharedAudioCtx && sharedAudioCtx.state === 'suspended') {
      sharedAudioCtx.resume().catch(() => {});
    }
  } catch (e) {}
  return sharedAudioCtx;
}

function playAlertTone() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(440, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) {}
}

function startProctoringListeners() {
  state.proctoringActive = true;

  // 1. Detect Tab Switch / Visibility Change (when user navigates to another tab or minimizes)
  document.addEventListener("visibilitychange", handleVisibilityChange);

  // 2. Detect Window Defocus / Alt+Tab / App Switch
  window.addEventListener("blur", handleWindowBlur);

  // 3. Detect Cursor Leaving Proctored Boundary (cross-browser)
  document.addEventListener("mouseout", handleMouseOut);
  document.addEventListener("mouseleave", handleMouseLeave);

  // 4. Detect Fullscreen Exit
  document.addEventListener("fullscreenchange", handleFullscreenChange);
  document.addEventListener("webkitfullscreenchange", handleFullscreenChange);

  // 5. Block Clipboard (Copy / Paste / Cut)
  document.addEventListener("copy", blockEvent);
  document.addEventListener("paste", blockEvent);
  document.addEventListener("cut", blockEvent);

  // 6. Block Context Menu (Right Click)
  document.addEventListener("contextmenu", handleContextMenu);

  // 7. Block Keyboard Shortcuts (Devtools, F12, Ctrl+U, etc.)
  document.addEventListener("keydown", handleKeyShortcuts);
}

function stopProctoringListeners() {
  state.proctoringActive = false;
  document.removeEventListener("visibilitychange", handleVisibilityChange);
  window.removeEventListener("blur", handleWindowBlur);
  document.removeEventListener("mouseout", handleMouseOut);
  document.removeEventListener("mouseleave", handleMouseLeave);
  document.removeEventListener("fullscreenchange", handleFullscreenChange);
  document.removeEventListener("webkitfullscreenchange", handleFullscreenChange);
  document.removeEventListener("copy", blockEvent);
  document.removeEventListener("paste", blockEvent);
  document.removeEventListener("cut", blockEvent);
  document.removeEventListener("contextmenu", handleContextMenu);
  document.removeEventListener("keydown", handleKeyShortcuts);
}

function blockEvent(e) {
  if (state.proctoringActive) {
    e.preventDefault();
  }
}

function handleContextMenu(e) {
  if (state.proctoringActive) {
    e.preventDefault();
    throttleViolation("context_menu_blocked", "Right-click context menu was blocked.");
  }
}

function handleKeyShortcuts(e) {
  if (!state.proctoringActive) return;
  // Block F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U, Ctrl+S
  if (
    e.key === "F12" ||
    (e.ctrlKey && e.shiftKey && (e.key === "I" || e.key === "J" || e.key === "C")) ||
    (e.ctrlKey && (e.key === "u" || e.key === "U" || e.key === "s" || e.key === "S"))
  ) {
    e.preventDefault();
    throttleViolation("keyboard_shortcut_blocked", "Attempted to use inspection or unauthorized hotkey.");
  } else if (e.ctrlKey && (e.key === "v" || e.key === "V")) {
    e.preventDefault();
    throttleViolation("clipboard_paste_blocked", "Attempted to paste external content into exam.");
  }
}

let lastViolationTime = 0;
function throttleViolation(type, details) {
  const now = Date.now();
  // Throttle events within 1.5 seconds to prevent flood while remaining responsive
  if (now - lastViolationTime < 1500) return;
  lastViolationTime = now;
  triggerProctoringViolation(type, details);
}

function handleVisibilityChange() {
  if (!state.proctoringActive) return;
  if (document.hidden) {
    throttleViolation("tab_switch", "User navigated away from proctored exam tab or minimized the browser.");
  }
}

function handleWindowBlur() {
  if (!state.proctoringActive) return;
  throttleViolation("window_blur", "Exam window lost focus (switched applications, pressed Alt+Tab, or clicked outside).");
}

function handleMouseOut(e) {
  if (!state.proctoringActive) return;
  // In cross-browser DOM, if relatedTarget is null/undefined, cursor left the window entirely!
  if (!e.relatedTarget && !e.toElement) {
    throttleViolation("mouse_left_window", "Cursor moved outside the proctored exam window boundary.");
  }
}

function handleMouseLeave(e) {
  if (!state.proctoringActive) return;
  // If mouse leaves the viewport boundary
  if (e.clientY <= 0 || e.clientX <= 0 || (e.clientX >= window.innerWidth || e.clientY >= window.innerHeight)) {
    throttleViolation("mouse_left_window", "Mouse pointer departed the proctored viewport boundary.");
  }
}

function handleFullscreenChange() {
  if (!state.proctoringActive) return;
  if (!document.fullscreenElement && !document.webkitFullscreenElement) {
    throttleViolation("fullscreen_exit", "Exited full-screen lockdown mode.");
  }
}

async function triggerProctoringViolation(violationType, details) {
  if (!state.currentExam || !state.currentExam.submissionId) return;

  playAlertTone();

  try {
    const res = await apiCall(`/api/submissions/${state.currentExam.submissionId}/record-violation`, "POST", {
      violation_type: violationType,
      details
    });

    if (!res) return;

    state.currentExam.violations = res.violation_count;
    const badge = document.getElementById("arenaViolations");
    if (badge) badge.textContent = res.violation_count;

    // Visual pulse effect on violations badge
    const badgeParent = document.getElementById("violationCounterBadge");
    if (badgeParent) {
      badgeParent.classList.add("border-rose-500", "text-rose-300", "warning-pulse");
      setTimeout(() => badgeParent.classList.remove("warning-pulse"), 2500);
    }

    if (res.is_disqualified) {
      // Disqualified! Auto-submit
      stopProctoringListeners();
      clearInterval(state.timerInterval);
      clearInterval(state.autoSaveInterval);
      alert(`EXAM TERMINATED: You have exceeded the allowed violation limit (${res.violation_count}/${res.max_violations}). Your exam has been automatically submitted as Disqualified.`);
      doSubmitExam("auto_submitted_violations");
    } else {
      // Show Warning Modal
      document.getElementById("violationWarningReason").textContent = `${details}`;
      document.getElementById("violationModalCount").textContent = `${res.violation_count} / ${res.max_violations}`;
      const rem = Math.max(0, res.max_violations - res.violation_count);
      document.getElementById("violationModalRemaining").textContent = `${rem}`;
      document.getElementById("violationWarningModal").classList.remove("hidden");
    }

  } catch (err) {
    console.error("Failed to record violation:", err);
  }
}

function acknowledgeViolationWarning() {
  document.getElementById("violationWarningModal").classList.add("hidden");
  // Re-enter fullscreen if lost
  if (!document.fullscreenElement && !document.webkitFullscreenElement) {
    try {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else if (document.documentElement.webkitRequestFullscreen) {
        document.documentElement.webkitRequestFullscreen().catch(() => {});
      }
    } catch (e) {}
  }
}

// ----------------- MODAL HELPERS -----------------
function openModal(id) {
  document.getElementById(id).classList.remove("hidden");
}

function closeModal(id) {
  document.getElementById(id).classList.add("hidden");
}

// ----------------- INITIALIZATION -----------------
document.addEventListener("DOMContentLoaded", () => {
  updateAppState();
});
