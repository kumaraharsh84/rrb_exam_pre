import { getExamPattern } from "./exam-patterns.js?v=20260513c";
import { TOPICS } from "./rrb-syllabus-data.js?v=20260513c";
import { renderLeaderboard } from "./leaderboard.js?v=20260513c";

const STORAGE_KEYS = {
  profile: "rrbQuizProfile",
  authUsers: "rrbAuthUsers",
  currentUser: "rrbCurrentUser",
  theme: "rrb_theme",
  history: "rrbQuizHistory",
  finalMockHistory: "rrbFinalMockHistory",
  lastAttempt: "rrbLastAttempt",
  savedPapers: "rrbSavedPapers",
  bookmarks: "rrbQuizBookmarks",
  mistakes: "rrbQuizMistakes",
  wrongQuestions: "rrb_wrong_questions",
  replayQuestions: "rrbReplayQuestions",
  recentQuestions: "rrbRecentQuestions",
  recentPatterns: "rrbRecentPatterns",
  config: "rrbQuizConfig",
  questions: "rrbQuizQuestions",
  answers: "rrbQuizAnswers",
  results: "rrbQuizResults"
};

const FRONTEND_BUILD_TOKEN = "20260513c";

const AVAILABLE_EXAMS = [
  "RRB NTPC",
  "RRB Group D",
  "RRB Technician Grade 3"
];

const EXAM_BRANCH_OPTIONS = {};

function buildVersionedPageUrl(pagePath) {
  return `${pagePath}?v=${FRONTEND_BUILD_TOKEN}`;
}

function getStoredTheme() {
  return localStorage.getItem(STORAGE_KEYS.theme) || "light";
}

function updateThemeToggleUi(theme) {
  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    const icon = button.querySelector("[data-theme-icon]");
    const label = button.querySelector("[data-theme-label]");
    const nextMode = theme === "dark" ? "light" : "dark";

    if (icon) {
      icon.textContent = theme === "dark" ? "light_mode" : "dark_mode";
    }

    if (label) {
      label.textContent = theme === "dark" ? "Light Mode" : "Dark Mode";
    }

    button.setAttribute("aria-label", `Switch to ${nextMode} mode`);
    button.setAttribute("title", `Switch to ${nextMode} mode`);
  });
}

function applyTheme(theme = getStoredTheme()) {
  const useDark = theme === "dark";
  document.body.classList.toggle("dark-mode", useDark);
  document.documentElement.classList.toggle("dark", useDark);
  updateThemeToggleUi(useDark ? "dark" : "light");
}

function setupThemeToggle() {
  applyTheme();

  document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
    if (button.dataset.themeBound === "true") {
      return;
    }

    button.dataset.themeBound = "true";
    button.addEventListener("click", () => {
      const nextTheme = document.body.classList.contains("dark-mode") ? "light" : "dark";
      localStorage.setItem(STORAGE_KEYS.theme, nextTheme);
      applyTheme(nextTheme);
    });
  });
}

// Helper function to get exam-specific storage key
function getExamSpecificKey(baseKey, exam) {
  if (!exam) return baseKey;
  return baseKey + "_" + exam.replace(/\s+/g, '').toLowerCase();
}

// Helper function to get current selected exam
function getCurrentExam() {
  return sanitizeExamName(localStorage.getItem("selectedExam"));
}

function sanitizeExamName(examName) {
  return AVAILABLE_EXAMS.includes(examName) ? examName : "RRB NTPC";
}

function getCurrentExamContext() {
  const currentUserState = readJson(STORAGE_KEYS.currentUser, {});
  const profileState = readJson(STORAGE_KEYS.profile, {});

  return {
    exam: sanitizeExamName(profileState.preferredExam || currentUserState.preferredExam || getCurrentExam()),
    stage: profileState.preferredStage || currentUserState.preferredStage || "",
    branch: profileState.preferredBranch || currentUserState.preferredBranch || ""
  };
}

function getExamBranchOptions(examName, stage = "") {
  return EXAM_BRANCH_OPTIONS[examName] || [];
}

function sanitizeBranchName(examName, stage = "", branchName = "") {
  const branches = getExamBranchOptions(examName, stage);
  if (!branches.length) {
    return "";
  }
  return branches.includes(branchName) ? branchName : branches[0];
}

function normalizeSubjectName(subject) {
  const value = String(subject || "")
    .replace(/Ã¢â‚¬â€/g, " - ")
    .replace(/â€”/g, " - ")
    .replace(/â€“/g, "-")
    .replace(/\s+/g, " ")
    .trim();
  const mapping = {
    "General Intelligence & Reasoning": "General Intelligence and Reasoning",
    "General Awareness & Current Affairs": "General Awareness and Current Affairs",
    "Current Affairs & General Awareness": "Current Affairs and General Awareness",
    "Physics & Chemistry": "Physics and Chemistry"
  };

  return mapping[value] || value;
}

function normalizeTopicName(topic) {
  return String(topic || "")
    .replace(/â€”/g, " - ")
    .replace(/–/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeLookupText(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function normalizeTopicMap(topicMap) {
  return Object.fromEntries(
    Object.entries(topicMap || {}).map(([subject, topics]) => [
      normalizeSubjectName(subject),
      Array.isArray(topics) ? topics.map((topic) => normalizeTopicName(topic)) : []
    ])
  );
}

const EXAM_SUBJECT_TOPICS = Object.fromEntries(
  Object.entries(TOPICS || {}).map(([examName, topicMap]) => [
    examName,
    normalizeTopicMap(topicMap)
  ])
);

const SUBJECT_TOPICS = EXAM_SUBJECT_TOPICS["RRB NTPC"];
const EXAM_STAGE_SUBJECT_TOPICS = {};

const EXAM_STAGE_OPTIONS = {};

export function saveJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function readJson(key, fallback = null) {
  const raw = localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function clearQuizSession() {
  [
    STORAGE_KEYS.config,
    STORAGE_KEYS.questions,
    STORAGE_KEYS.answers,
    STORAGE_KEYS.results
  ].forEach((key) => localStorage.removeItem(key));
}

function formatDate(timestamp) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Just now";
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function getCutoffDate() {
  const cutoff = new Date();
  cutoff.setMonth(cutoff.getMonth() - 2);
  return cutoff;
}

export function pruneHistoryRecords(history = []) {
  const cutoff = getCutoffDate().getTime();
  return history.filter((attempt) => {
    const completedAt = new Date(attempt.completedAt || 0).getTime();
    return Number.isFinite(completedAt) && completedAt >= cutoff;
  });
}

export function pruneSavedPapers(papers = []) {
  const cutoff = getCutoffDate().getTime();
  return papers.filter((paper) => {
    const createdAt = new Date(paper.createdAt || 0).getTime();
    return Number.isFinite(createdAt) && createdAt >= cutoff;
  });
}

function dedupeAttempts(attempts = []) {
  return attempts.filter((attempt, index, allAttempts) => index === allAttempts.findIndex((entry) =>
    entry.completedAt === attempt.completedAt
    && entry.paperId === attempt.paperId
    && entry.subject === attempt.subject
    && entry.topic === attempt.topic
    && entry.score === attempt.score
    && entry.total === attempt.total
  ));
}

function sortAttemptsDescending(attempts = []) {
  return [...attempts].sort((left, right) =>
    new Date(right.completedAt || 0).getTime() - new Date(left.completedAt || 0).getTime()
  );
}

function getHistoryBuckets() {
  const currentExam = getCurrentExam();
  const historyKey = getExamSpecificKey(STORAGE_KEYS.history, currentExam);
  const finalMockHistoryKey = getExamSpecificKey(STORAGE_KEYS.finalMockHistory, currentExam);
  const rawHistory = pruneHistoryRecords(readJson(historyKey, []));
  const rawFinalMockHistory = pruneHistoryRecords(readJson(finalMockHistoryKey, []));
  const combined = [...rawHistory, ...rawFinalMockHistory];

  const standardHistory = sortAttemptsDescending(dedupeAttempts(combined.filter((attempt) => attempt.modeLabel !== "Final Mock")));
  const finalMockHistory = sortAttemptsDescending(dedupeAttempts(combined.filter((attempt) => attempt.modeLabel === "Final Mock")));

  saveJson(historyKey, standardHistory);
  saveJson(finalMockHistoryKey, finalMockHistory);

  return {
    standardHistory,
    finalMockHistory
  };
}

function getAllAttempts() {
  const { standardHistory, finalMockHistory } = getHistoryBuckets();
  return sortAttemptsDescending([...standardHistory, ...finalMockHistory]);
}

function refreshLastAttempt() {
  const allAttempts = getAllAttempts();
  const currentExam = getCurrentExam();
  const lastAttemptKey = getExamSpecificKey(STORAGE_KEYS.lastAttempt, currentExam);
  if (allAttempts.length) {
    saveJson(lastAttemptKey, allAttempts[0]);
    return allAttempts[0];
  }

  localStorage.removeItem(lastAttemptKey);
  return null;
}

function getStrengthLabel(accuracy) {
  if (accuracy >= 75) {
    return "Strong";
  }
  if (accuracy >= 55) {
    return "Improving";
  }
  return "Needs work";
}

function getStrengthClass(label) {
  if (label === "Strong") {
    return "insight-strong";
  }
  if (label === "Improving") {
    return "insight-improving";
  }
  return "insight-weak";
}

function getExamSubjects(examName, stage = "", branch = "") {
  const mapping = getExamTopicMapping(examName, stage, branch);
  return Object.keys(mapping);
}

function getExamStageOptions(examName) {
  return EXAM_STAGE_OPTIONS[examName] || [];
}

function getExamTopicMapping(examName, stage = "", branch = "") {
  const stageMapping = EXAM_STAGE_SUBJECT_TOPICS[examName];
  const baseMapping = stageMapping && stage && stageMapping[stage]
    ? stageMapping[stage]
    : EXAM_SUBJECT_TOPICS[examName] || EXAM_SUBJECT_TOPICS["RRB NTPC"];
  return baseMapping;
}

function resolveSubjectKey(examName, stage, selectedSubject, branch = "") {
  const examMapping = getExamTopicMapping(examName, stage, branch);
  if (examMapping[selectedSubject]) {
    return selectedSubject;
  }

  const normalizedSelected = normalizeLookupText(selectedSubject);
  return Object.keys(examMapping).find((subject) =>
    normalizeLookupText(subject) === normalizedSelected
    || normalizeLookupText(getSubjectDisplayName(examName, stage, subject)) === normalizedSelected
  ) || "";
}

function getSubjectDisplayName(examName, stage, subject) {
  const stageKey = stage ? `${examName} ${stage}` : examName;
  const displayMap = {
    "RRB NTPC": {
      "General Intelligence and Reasoning": "General Intelligence & Reasoning",
      "General Awareness": "General Awareness",
      Mathematics: "Mathematics"
    },
    "RRB Group D": {
      "General Intelligence and Reasoning": "General Intelligence & Reasoning",
      "General Awareness and Current Affairs": "General Awareness & Current Affairs",
      Mathematics: "Mathematics",
      "General Science": "General Science"
    },
    "RRB Technician Grade 3": {
      "General Intelligence and Reasoning": "General Intelligence & Reasoning",
      "General Awareness": "General Awareness and Current Affairs"
    }
  };

  return displayMap[stageKey]?.[subject] || displayMap[examName]?.[subject] || subject;
}

function syncSubjectOptions(examName, stage, branch, subjectSelect, preferredSubject = "") {
  if (!subjectSelect) {
    return;
  }

  const subjects = Object.keys(getExamTopicMapping(examName, stage, branch));
  subjectSelect.replaceChildren(
    ...subjects.map((subject) => {
      const option = document.createElement("option");
      option.value = subject;
      option.textContent = getSubjectDisplayName(examName, stage, subject);
      return option;
    })
  );

  const resolvedPreferredSubject = resolveSubjectKey(examName, stage, preferredSubject, branch);
  if (resolvedPreferredSubject && subjects.includes(resolvedPreferredSubject)) {
    subjectSelect.value = resolvedPreferredSubject;
    return;
  }

  subjectSelect.value = subjects[0] || "";
}

function syncTopicOptions(examName, stage, branch, subject, topicSelect, topicHint, preferredTopic = "") {
  if (!topicSelect) {
    return;
  }

  const examMapping = getExamTopicMapping(examName, stage, branch);
  const resolvedSubject = resolveSubjectKey(examName, stage, subject, branch);
  const fallbackSubject = Object.keys(examMapping)[0] || "";
  const activeSubject = resolvedSubject || fallbackSubject;
  const topics = examMapping[activeSubject] || [];
  topicSelect.replaceChildren(
    ...topics.map((topic) => {
      const option = document.createElement("option");
      option.value = topic;
      option.textContent = topic;
      return option;
    })
  );

  topicSelect.disabled = false;

  if (preferredTopic && topics.includes(preferredTopic)) {
    topicSelect.value = preferredTopic;
  } else {
    topicSelect.value = topics[0] || "";
  }

  if (topicHint) {
    const stageSuffix = stage ? ` ${stage}` : "";
    topicHint.textContent = `${examName}${stageSuffix} ke ${getSubjectDisplayName(examName, stage, activeSubject || subject)} topics yahan dikh rahe hain.`;
  }
}

function summarizeSubjectPerformance(attempts = [], examName = getCurrentExam(), stage = "", branch = "") {
  const activeExam = sanitizeExamName(examName || getCurrentExam());
  const validSubjects = new Set(getExamSubjects(activeExam, stage, branch));

  if (!validSubjects.size) {
    return [];
  }

  return Object.entries(
    attempts.reduce((accumulator, attempt) => {
      if (stage && attempt.stage && attempt.stage !== stage) {
        return accumulator;
      }

      const resolvedSubject = resolveSubjectKey(activeExam, stage || attempt.stage || "", attempt.subject, branch);
      if (!resolvedSubject || !validSubjects.has(resolvedSubject)) {
        return accumulator;
      }

      const current = accumulator[resolvedSubject] || {
        attempts: 0,
        totalScore: 0,
        totalQuestions: 0,
        best: 0
      };

      current.attempts += 1;
      current.totalScore += attempt.score;
      current.totalQuestions += attempt.total;
      current.best = Math.max(current.best, attempt.percentage);
      accumulator[resolvedSubject] = current;
      return accumulator;
    }, {})
  )
    .map(([subject, stats]) => ({
      subject,
      ...stats,
      accuracy: stats.totalQuestions ? Math.round((stats.totalScore / stats.totalQuestions) * 100) : 0
    }))
    .sort((left, right) => left.accuracy - right.accuracy || left.best - right.best || right.attempts - left.attempts);
}

function buildWeakSubjectPracticeConfig(examName, stage, branch, subject, accuracy = 0) {
  const subjectTopics = Array.from(new Set((getExamTopicMapping(examName, stage, branch)[subject] || []).filter(Boolean)));
  const difficulty = accuracy < 40 ? "basic" : accuracy < 75 ? "intermediate" : "advanced";

  if (subjectTopics.length > 1) {
    return {
      exam: examName,
      stage,
      branch,
      subject,
      topic: "Mixed Revision",
      count: 12,
      mode: "practice",
      difficulty,
      practiceType: "chapter-practice",
      selectedChapters: subjectTopics,
      chapterQuestionMode: "balanced-sampler"
    };
  }

  return {
    exam: examName,
    stage,
    branch,
    subject,
    topic: subjectTopics[0] || "Mixed Revision",
    count: 12,
    mode: "practice",
    difficulty
  };
}

function renderHistory(subjectFilter = "all", targetSelector = "#history-list") {
  const historyList = document.querySelector(targetSelector);
  if (!historyList) {
    return;
  }

  const currentExam = getCurrentExam();
  const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
  const { standardHistory } = getHistoryBuckets();
  const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
  saveJson(savedPapersKey, savedPapers);
  const filteredAttempts = subjectFilter === "all"
    ? standardHistory
    : standardHistory.filter((attempt) => attempt.subject === subjectFilter);

  if (!filteredAttempts.length) {
    historyList.innerHTML = `
      <article class="history-empty">
        <strong>No recent practice attempts${subjectFilter !== "all" ? ` for ${subjectFilter}` : ""}</strong>
        <span>Only the last 2 months of test history is kept here.</span>
      </article>
    `;
    return;
  }

  historyList.innerHTML = filteredAttempts.map((attempt) => {
    const isPaperSaved = savedPapers.some((paper) => paper.id === attempt.paperId);

    return `
    <article class="history-item">
      <div class="history-score">${attempt.percentage}%</div>
      <div>
        <strong>${attempt.subject} | ${attempt.topic}</strong>
        <p>Net score: ${attempt.finalScore ?? attempt.score} | Correct: ${attempt.score}/${attempt.total}</p>
        <p>${attempt.modeLabel} | ${(attempt.exam || "RRB NTPC")}${attempt.stage ? ` ${attempt.stage}` : ""} | ${formatDate(attempt.completedAt)}</p>
        <div class="bookmark-actions history-actions">
          ${isPaperSaved ? 
            `<button class="chip-btn" type="button" data-retake-test="${attempt.subject}|${attempt.topic}" data-exam="${attempt.exam || currentExam}">Retake This Test</button>` :
            `<button class="chip-btn" type="button" data-practice-similar="${attempt.subject}|${attempt.topic}" data-exam="${attempt.exam || currentExam}">Practice Similar</button>`
          }
        </div>
      </div>
    </article>
  `}).join("");

  historyList.querySelectorAll("[data-retake-test]").forEach((button) => {
    button.addEventListener("click", () => {
      const [subject, topic] = button.dataset.retakeTest.split("|");
      const exam = button.dataset.exam;
      saveJson(STORAGE_KEYS.config, {
        exam: exam,
        subject: subject,
        topic: topic,
        count: 10, // Default count
        mode: "practice",
        difficulty: "intermediate"
      });
      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });

  historyList.querySelectorAll("[data-practice-similar]").forEach((button) => {
    button.addEventListener("click", () => {
      const [subject, topic] = button.dataset.practiceSimilar.split("|");
      const exam = button.dataset.exam;
      saveJson(STORAGE_KEYS.config, {
        exam: exam,
        subject: subject,
        topic: topic,
        count: 10, // Default count
        mode: "practice",
        difficulty: "intermediate"
      });
      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });
}

function renderFinalMockHistory(targetSelector = "#final-mock-history-list") {
  const historyList = document.querySelector(targetSelector);
  if (!historyList) {
    return;
  }

  const currentExam = getCurrentExam();
  const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
  const { finalMockHistory: attempts } = getHistoryBuckets();
  const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
  saveJson(savedPapersKey, savedPapers);

  if (!attempts.length) {
    historyList.innerHTML = `
      <article class="history-empty">
        <strong>No final mock attempts yet</strong>
        <span>90-minute full pattern mock attempts will be saved separately here.</span>
      </article>
    `;
    return;
  }

  historyList.innerHTML = attempts.map((attempt) => `
    <article class="history-item">
      <div class="history-score">${attempt.percentage}%</div>
      <div>
        <strong>${(attempt.exam || "RRB NTPC")}${attempt.stage ? ` ${attempt.stage}` : ""} | Final Mock</strong>
        <p>Net score: ${attempt.finalScore ?? attempt.score} | Correct: ${attempt.score}/${attempt.total}</p>
        <p>Wrong: ${attempt.wrongAnswers ?? 0} | Unanswered: ${attempt.unansweredAnswers ?? 0}</p>
        <p>${formatDate(attempt.completedAt)}</p>
        <div class="bookmark-actions history-actions">
          <button class="chip-btn" type="button" data-open-final-paper="${attempt.paperId || ""}" ${savedPapers.some((paper) => paper.id === attempt.paperId) ? "" : "disabled"}>View Detailed Analysis</button>
        </div>
      </div>
    </article>
  `).join("");

  historyList.querySelectorAll("[data-open-final-paper]").forEach((button) => {
    button.addEventListener("click", () => {
      const paperId = button.dataset.openFinalPaper;
      if (!paperId) {
        return;
      }

      const savedPaper = savedPapers.find((paper) => paper.id === paperId);
      if (!savedPaper) {
        return;
      }

      saveJson(STORAGE_KEYS.config, {
        ...savedPaper.config,
        paperId: savedPaper.id,
        useSavedPaper: true
      });
      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });
}

function renderLastAttemptCard() {
  const card = document.querySelector("#last-attempt-card");
  if (!card) {
    return;
  }

  const latestAttempt = refreshLastAttempt();
  const currentExam = getCurrentExam();
  const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
  const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
  saveJson(savedPapersKey, savedPapers);

  if (!latestAttempt) {
    card.innerHTML = `
      <article class="history-empty">
        <strong>No last exam yet</strong>
        <span>Finish one quiz and your latest exam summary will appear here for quick revision.</span>
      </article>
    `;
    return;
  }

  card.innerHTML = `
    <article class="last-attempt-card">
      <div class="last-attempt-head">
        <div>
          <p class="eyebrow">Last exam</p>
          <strong>${(latestAttempt.exam || "RRB NTPC")}${latestAttempt.stage ? ` ${latestAttempt.stage}` : ""} | ${latestAttempt.modeLabel}</strong>
          <p>${latestAttempt.subject} | ${latestAttempt.topic}</p>
        </div>
        <div class="last-attempt-score">
          <strong>${latestAttempt.percentage}%</strong>
          <span>Accuracy</span>
        </div>
      </div>
      <div class="last-attempt-grid">
        <article class="summary-box">
          <strong>${latestAttempt.finalScore ?? latestAttempt.score}</strong>
          <span>Net Score</span>
        </article>
        <article class="summary-box">
          <strong>${latestAttempt.score}/${latestAttempt.total}</strong>
          <span>Correct</span>
        </article>
        <article class="summary-box">
          <strong>${latestAttempt.wrongAnswers ?? 0}</strong>
          <span>Wrong</span>
        </article>
        <article class="summary-box">
          <strong>${formatDate(latestAttempt.completedAt)}</strong>
          <span>Completed</span>
        </article>
      </div>
      <div class="bookmark-actions">
        <button class="chip-btn" type="button" id="last-attempt-practice-again">Practice Again</button>
        <button class="chip-btn" type="button" id="last-attempt-open-history">Open History</button>
      </div>
    </article>
  `;

  document.querySelector("#last-attempt-practice-again")?.addEventListener("click", () => {
    const savedPaper = savedPapers.find((paper) => paper.id === latestAttempt.paperId);
    if (savedPaper) {
      saveJson(STORAGE_KEYS.config, {
        ...savedPaper.config
      });
    } else {
      saveJson(STORAGE_KEYS.config, {
        exam: latestAttempt.exam || "RRB NTPC",
        subject: latestAttempt.subject,
        topic: latestAttempt.topic,
        count: Math.min(Number(latestAttempt.total) || 10, 20),
        mode: latestAttempt.modeLabel === "Final Mock"
          ? "final-mock"
          : latestAttempt.modeLabel === "Mock Test" || latestAttempt.modeLabel === "Mock Test Without Timer"
            ? "mock"
            : latestAttempt.modeLabel === "Previous Year"
              ? "previous-year"
              : "practice",
        difficulty: latestAttempt.difficulty || "intermediate"
      });
    }
    window.location.href = buildVersionedPageUrl("./quiz.html");
  });

  document.querySelector("#last-attempt-open-history")?.addEventListener("click", () => {
    window.location.href = latestAttempt.modeLabel === "Final Mock"
      ? "./history.html?view=final-mock"
      : "./history.html";
  });
}

function renderBookmarks() {
  const bookmarkList = document.querySelector("#bookmark-list");
  if (!bookmarkList) {
    return;
  }

  const { exam: currentExam, stage: activeStage, branch: activeBranch } = getCurrentExamContext();
  const bookmarksKey = getExamSpecificKey(STORAGE_KEYS.bookmarks, currentExam);
  const bookmarks = readJson(bookmarksKey, []);
  const subjectFilter = document.querySelector("#bookmark-subject-filter");

  const updateSelectOptions = (select, options, allLabel) => {
    if (!select) {
      return "all";
    }

    const previousValue = select.value || "all";
    select.replaceChildren(
      ...[
        ["all", allLabel],
        ...options.map((option) => [option, option])
      ].map(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
      })
    );

    select.value = options.includes(previousValue) ? previousValue : "all";
    select.disabled = false;
    return select.value;
  };

  const subjects = Array.from(new Set([
    ...getExamSubjects(currentExam, activeStage, activeBranch),
    ...bookmarks.map((bookmark) => bookmark.subject).filter(Boolean)
  ])).sort();
  const selectedSubject = updateSelectOptions(subjectFilter, subjects, "All Subjects");
  const filteredBookmarks = selectedSubject === "all"
    ? bookmarks
    : bookmarks.filter((bookmark) => bookmark.subject === selectedSubject);

  if (!bookmarks.length) {
    bookmarkList.innerHTML = `
      <article class="history-empty">
        <strong>No bookmarked questions for ${currentExam}</strong>
        <span>Important questions for the currently selected exam will appear here.</span>
      </article>
    `;
    return;
  }

  if (!filteredBookmarks.length) {
    bookmarkList.innerHTML = `
      <article class="history-empty">
        <strong>No bookmarked questions found</strong>
        <span>Change the filters or select another subject/topic.</span>
      </article>
    `;
    return;
  }

  const groupedBookmarks = filteredBookmarks.reduce((accumulator, bookmark) => {
    const key = `${bookmark.subject}__${bookmark.topic}`;
    if (!accumulator[key]) {
      accumulator[key] = {
        subject: bookmark.subject,
        topic: bookmark.topic,
        items: []
      };
    }
    accumulator[key].items.push(bookmark);
    return accumulator;
  }, {});

  bookmarkList.innerHTML = Object.values(groupedBookmarks).map((group) => `
    <section class="bookmark-group">
      <div class="bookmark-group-heading">
        <div>
          <strong>${group.subject}</strong>
          <p>${group.topic} | ${currentExam}</p>
        </div>
        <span class="bookmark-group-count">${group.items.length} saved</span>
      </div>
      <div class="bookmark-group-list">
        ${group.items.map((bookmark) => `
          <article class="bookmark-item">
            <div class="bookmark-top">
              <strong>${bookmark.subject} | ${bookmark.topic}</strong>
              <div class="bookmark-actions">
                <button class="chip-btn" type="button" data-practice-bookmark="${bookmark.savedAt}">Practice Again</button>
                <button class="chip-btn" type="button" data-remove-bookmark="${bookmark.savedAt}">Remove</button>
              </div>
            </div>
            <p>${bookmark.q}</p>
            <span>${formatDate(bookmark.savedAt)}</span>
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");

  bookmarkList.querySelectorAll("[data-remove-bookmark]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextBookmarks = bookmarks.filter((bookmark) => bookmark.savedAt !== button.dataset.removeBookmark);
      saveJson(bookmarksKey, nextBookmarks);
      renderBookmarks();
    });
  });

  bookmarkList.querySelectorAll("[data-practice-bookmark]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedBookmark = bookmarks.find((bookmark) => bookmark.savedAt === button.dataset.practiceBookmark);
      if (!selectedBookmark) {
        return;
      }

      saveJson(STORAGE_KEYS.config, {
        exam: selectedBookmark.exam || currentExam,
        subject: selectedBookmark.subject,
        topic: selectedBookmark.topic,
        count: 5,
        mode: "practice",
        customQuestionSource: "bookmarks"
      });

      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });
}

function renderMistakes() {
  const mistakeList = document.querySelector("#mistake-list");
  if (!mistakeList) {
    return;
  }

  const currentExam = getCurrentExam();
  const mistakesKey = getExamSpecificKey(STORAGE_KEYS.mistakes, currentExam);
  const scopedMistakes = readJson(mistakesKey, []);
  const legacyMistakes = scopedMistakes.length
    ? []
    : readJson(STORAGE_KEYS.mistakes, []).filter((item) => (item.exam || "RRB NTPC") === currentExam);
  const mistakes = scopedMistakes.length ? scopedMistakes : legacyMistakes;

  if (!scopedMistakes.length && legacyMistakes.length) {
    saveJson(mistakesKey, legacyMistakes.slice(0, 220));
  }

  if (!mistakes.length) {
    mistakeList.innerHTML = `
      <article class="history-empty">
        <strong>No mistakes saved yet for ${currentExam}</strong>
        <span>Incorrect questions will appear here for revision.</span>
      </article>
    `;
    return;
  }

  const groupedMistakes = mistakes.reduce((accumulator, item) => {
    const key = `${item.subject}__${item.topic}`;
    if (!accumulator[key]) {
      accumulator[key] = {
        subject: item.subject,
        topic: item.topic,
        items: []
      };
    }
    accumulator[key].items.push(item);
    return accumulator;
  }, {});

  mistakeList.innerHTML = Object.values(groupedMistakes).map((group) => `
    <section class="bookmark-group">
      <div class="bookmark-group-heading">
        <div>
          <strong>${group.subject}</strong>
          <p>${group.topic} | ${currentExam}</p>
        </div>
        <div class="bookmark-actions">
          <span class="bookmark-group-count">${group.items.length} mistakes</span>
          <button class="chip-btn" type="button" data-retry-mistake-topic="${group.subject}__${group.topic}">Retry Topic</button>
        </div>
      </div>
      <div class="bookmark-group-list">
        ${group.items.map((item) => `
          <article class="bookmark-item">
            <div class="bookmark-top">
              <strong>${item.subject} | ${item.topic}</strong>
              <div class="bookmark-actions">
                <button class="chip-btn" type="button" data-practice-mistake="${item.savedAt}">Practice Again</button>
                <button class="chip-btn" type="button" data-remove-mistake="${item.savedAt}">Remove</button>
              </div>
            </div>
            <p>${item.q}</p>
            <span>${formatDate(item.savedAt)}</span>
          </article>
        `).join("")}
      </div>
    </section>
  `).join("");

  mistakeList.querySelectorAll("[data-remove-mistake]").forEach((button) => {
    button.addEventListener("click", () => {
      const nextMistakes = mistakes.filter((item) => item.savedAt !== button.dataset.removeMistake);
      saveJson(mistakesKey, nextMistakes);
      renderMistakes();
    });
  });

  mistakeList.querySelectorAll("[data-retry-mistake-topic]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedGroup = Object.values(groupedMistakes).find(
        (group) => `${group.subject}__${group.topic}` === button.dataset.retryMistakeTopic
      );
      if (!selectedGroup) {
        return;
      }

      saveJson(STORAGE_KEYS.config, {
        exam: currentExam,
        subject: selectedGroup.subject,
        topic: selectedGroup.topic || "Mixed Revision",
        count: Math.min(Math.max(selectedGroup.items.length, 5), 10),
        mode: "practice",
        difficulty: "intermediate"
      });
      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });

  mistakeList.querySelectorAll("[data-practice-mistake]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedMistake = mistakes.find((item) => item.savedAt === button.dataset.practiceMistake);
      if (!selectedMistake) {
        return;
      }

      saveJson(STORAGE_KEYS.config, {
        exam: selectedMistake.exam || currentExam,
        subject: selectedMistake.subject,
        topic: selectedMistake.topic || "Mixed Revision",
        count: 5,
        mode: "practice",
        difficulty: "intermediate"
      });
      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });
}

function getScopedMistakesForExam(currentExam) {
  const mistakesKey = getExamSpecificKey(STORAGE_KEYS.mistakes, currentExam);
  const scopedMistakes = readJson(mistakesKey, []);
  const legacyMistakes = scopedMistakes.length
    ? []
    : readJson(STORAGE_KEYS.mistakes, []).filter((item) => (item.exam || "RRB NTPC") === currentExam);
  const mistakes = scopedMistakes.length ? scopedMistakes : legacyMistakes;

  if (!scopedMistakes.length && legacyMistakes.length) {
    saveJson(mistakesKey, legacyMistakes.slice(0, 220));
  }

  return { mistakesKey, mistakes };
}

function normalizeRevisionTimestamp(value) {
  const directTime = new Date(value || 0).getTime();
  if (Number.isFinite(directTime) && !Number.isNaN(directTime)) {
    return directTime;
  }

  const isoMatch = String(value || "").match(/^\d{4}-\d{2}-\d{2}T[^Z]+Z/);
  if (isoMatch) {
    const isoTime = new Date(isoMatch[0]).getTime();
    if (Number.isFinite(isoTime) && !Number.isNaN(isoTime)) {
      return isoTime;
    }
  }

  return 0;
}

function renderWrongQuestions() {
  const wrongQuestionsList = document.querySelector("#wrong-questions-list");
  if (!wrongQuestionsList) {
    return;
  }

  const { exam: currentExam, stage: activeStage, branch: activeBranch } = getCurrentExamContext();
  const subjectFilter = document.querySelector("#wrong-question-subject-filter");
  const wrongQuestions = readJson(STORAGE_KEYS.wrongQuestions, [])
    .filter((item) => (item.exam || "RRB NTPC") === currentExam)
    .sort((left, right) => Number(right.timestamp || 0) - Number(left.timestamp || 0));
  const { mistakes } = getScopedMistakesForExam(currentExam);

  const normalizedWrongQuestions = wrongQuestions.map((item) => ({
    kind: "wrong",
    id: `wrong:${item.timestamp}`,
    exam: item.exam || currentExam,
    stage: item.stage || "",
    branch: item.branch || "",
    subject: item.subject || "General",
    topic: item.topic || "Wrong Question Retry",
    question: item.question,
    options: item.options || [],
    correctIndex: item.correctIndex,
    userAnswer: item.userAnswer,
    explanation: item.explanation || "No explanation provided.",
    timestamp: Number(item.timestamp || 0),
    displayTime: item.timestamp
  }));

  const normalizedMistakes = mistakes.map((item) => ({
    kind: "mistake",
    id: `mistake:${item.savedAt}`,
    exam: item.exam || currentExam,
    stage: item.stage || "",
    branch: item.branch || "",
    subject: item.subject || "General",
    topic: item.topic || "Saved Mistake",
    question: item.q,
    options: item.opts || [],
    correctIndex: item.ans,
    userAnswer: null,
    explanation: item.exp || "No explanation provided.",
    timestamp: normalizeRevisionTimestamp(item.savedAt),
    displayTime: normalizeRevisionTimestamp(item.savedAt) || item.savedAt
  }));

  const mergedRevisionItems = [...normalizedWrongQuestions, ...normalizedMistakes].filter((item, index, collection) =>
    index === collection.findIndex((entry) =>
      entry.exam === item.exam
      && entry.subject === item.subject
      && entry.topic === item.topic
      && entry.question === item.question
    )
  ).sort((left, right) => right.timestamp - left.timestamp || left.subject.localeCompare(right.subject));

  if (subjectFilter) {
    const previousValue = subjectFilter.value || "all";
    const subjects = Array.from(new Set([
      ...getExamSubjects(currentExam, activeStage, activeBranch),
      ...mergedRevisionItems.map((item) => item.subject).filter(Boolean)
    ])).sort();
    subjectFilter.replaceChildren(
      ...[
        ["all", "All Subjects"],
        ...subjects.map((subject) => [subject, subject])
      ].map(([value, label]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = label;
        return option;
      })
    );
    subjectFilter.value = subjects.includes(previousValue) ? previousValue : "all";
  }

  const selectedSubject = subjectFilter?.value || "all";
  const filteredRevisionItems = selectedSubject === "all"
    ? mergedRevisionItems
    : mergedRevisionItems.filter((item) => item.subject === selectedSubject);

  if (!mergedRevisionItems.length) {
    wrongQuestionsList.innerHTML = `
      <article class="history-empty">
        <strong>No revision items saved yet for ${currentExam}</strong>
        <span>Incorrect answers and saved mistakes from the score screen will appear here for review and retry.</span>
      </article>
    `;
    return;
  }

  if (!filteredRevisionItems.length) {
    wrongQuestionsList.innerHTML = `
      <article class="history-empty">
        <strong>No revision items found for ${selectedSubject}</strong>
        <span>Change the filters or select another subject.</span>
      </article>
    `;
    return;
  }

  const groupedWrongQuestions = filteredRevisionItems.reduce((accumulator, item) => {
    const key = item.subject || "General";
    if (!accumulator[key]) {
      accumulator[key] = [];
    }
    accumulator[key].push(item);
    return accumulator;
  }, {});

  wrongQuestionsList.innerHTML = Object.entries(groupedWrongQuestions).map(([subject, items]) => `
    <section class="bookmark-group">
      <div class="bookmark-group-heading">
        <div>
          <strong>${subject}</strong>
          <p>${currentExam} | ${items.length} revision items</p>
        </div>
        <div class="bookmark-actions">
          <span class="bookmark-group-count">${items.length} items</span>
        </div>
      </div>
      <div class="bookmark-group-list">
        ${items.map((item) => {
          const userAnswer = item.userAnswer >= 0 ? item.options?.[item.userAnswer] || "Not answered" : "Not answered";
          const correctAnswer = item.options?.[item.correctIndex] || "Not available";
          return `
            <article class="bookmark-item">
              <div class="bookmark-top">
                <div>
                  <strong>${item.topic || "Wrong Question Retry"}</strong>
                  <p>${item.question}</p>
                </div>
                <div class="bookmark-actions">
                  <button class="chip-btn" type="button" data-retry-revision-item="${item.id}">Retry</button>
                  <button class="chip-btn" type="button" data-remove-revision-item="${item.id}">Remove</button>
                </div>
              </div>
              <p>${item.kind === "wrong" ? "Wrong Answer" : "Saved Mistake"}</p>
              <p>${item.kind === "wrong" ? `Your answer: ${userAnswer}` : "Marked for revision from previous mistake tracking."}</p>
              <p>Correct answer: ${correctAnswer}</p>
              <span>${formatDate(item.displayTime)}</span>
            </article>
          `;
        }).join("")}
      </div>
    </section>
  `).join("");

  wrongQuestionsList.querySelectorAll("[data-retry-revision-item]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedRevisionItem = mergedRevisionItems.find((item) => item.id === button.dataset.retryRevisionItem);
      if (!selectedRevisionItem) {
        return;
      }

      saveJson(STORAGE_KEYS.replayQuestions, [{
        q: selectedRevisionItem.question,
        opts: selectedRevisionItem.options,
        ans: selectedRevisionItem.correctIndex,
        exp: selectedRevisionItem.explanation || "No explanation provided."
      }]);

      saveJson(STORAGE_KEYS.config, {
        exam: selectedRevisionItem.exam || currentExam,
        stage: selectedRevisionItem.stage || "",
        branch: selectedRevisionItem.branch || "",
        subject: selectedRevisionItem.subject || "Wrong Questions",
        topic: selectedRevisionItem.topic || "Wrong Question Retry",
        count: 1,
        mode: "practice",
        difficulty: "intermediate",
        customQuestionSet: true,
        customQuestionSource: "wrong-questions"
      });

      window.location.href = buildVersionedPageUrl("./quiz.html");
    });
  });

  wrongQuestionsList.querySelectorAll("[data-remove-revision-item]").forEach((button) => {
    button.addEventListener("click", () => {
      const selectedRevisionItem = mergedRevisionItems.find((item) => item.id === button.dataset.removeRevisionItem);
      if (!selectedRevisionItem) {
        return;
      }

      const nextWrongQuestions = readJson(STORAGE_KEYS.wrongQuestions, [])
        .filter((item) =>
          !(
            (item.exam || currentExam) === selectedRevisionItem.exam
            && (item.subject || "General") === selectedRevisionItem.subject
            && (item.topic || "Wrong Question Retry") === selectedRevisionItem.topic
            && item.question === selectedRevisionItem.question
          )
        );
      saveJson(STORAGE_KEYS.wrongQuestions, nextWrongQuestions);

      const { mistakesKey, mistakes: mistakeItems } = getScopedMistakesForExam(currentExam);
      const nextMistakes = mistakeItems.filter((item) =>
        !(
          (item.exam || currentExam) === selectedRevisionItem.exam
          && (item.subject || "General") === selectedRevisionItem.subject
          && (item.topic || "Saved Mistake") === selectedRevisionItem.topic
          && item.q === selectedRevisionItem.question
        )
      );
      saveJson(mistakesKey, nextMistakes);

      renderWrongQuestions();
    });
  });
}

function renderAnalytics() {
  const analyticsList = document.querySelector("#analytics-list");
  if (!analyticsList) {
    return;
  }

  const { exam: activeExam, stage: activeStage, branch: activeBranch } = getCurrentExamContext();
  const history = getAllAttempts();
  const subjectSummary = summarizeSubjectPerformance(history, activeExam, activeStage, activeBranch);

  if (!subjectSummary.length) {
    analyticsList.innerHTML = `
      <article class="history-empty">
        <strong>No analytics yet</strong>
        <span>Complete a few subject drills or section-based tests to see your weakest subject and accuracy trends.</span>
      </article>
    `;
    return;
  }

  const weakestSubject = subjectSummary[0];
  const weakSubjectCard = weakestSubject ? `
    <article class="analytics-item analytics-card insight-weak">
      <div class="analytics-top">
        <strong>Your Weakest: ${getSubjectDisplayName(activeExam, activeStage, weakestSubject.subject)}</strong>
        <span class="insight-pill insight-weak">${weakestSubject.accuracy}%</span>
      </div>
      <p>Attempts: ${weakestSubject.attempts}</p>
      <p>Lowest average accuracy in your current ${activeExam}${activeStage ? ` ${activeStage}` : ""} history.</p>
      <p>Best move: concept rebuild + mixed chapter practice.</p>
      <div class="mt-4 flex flex-wrap gap-3">
        <button id="start-weakest-subject" class="primary-btn" type="button">Start Weak Drill</button>
      </div>
    </article>
  ` : "";

  const subjectCards = subjectSummary.map((stats) => {
    const label = getStrengthLabel(stats.accuracy);
    return `
      <article class="analytics-item analytics-card ${getStrengthClass(label)}">
        <div class="analytics-top">
          <strong>${getSubjectDisplayName(activeExam, activeStage, stats.subject)}</strong>
          <span class="insight-pill ${getStrengthClass(label)}">${label}</span>
        </div>
        <p>Attempts: ${stats.attempts}</p>
        <p>Average Accuracy: ${stats.accuracy}%</p>
        <p>Best Score: ${stats.best}%</p>
        <p>Focus: ${label === "Strong" ? "Revision and speed" : label === "Improving" ? "More mixed practice" : "Concept rebuild needed"}</p>
      </article>
    `;
  }).join("");

  analyticsList.innerHTML = `${weakSubjectCard}${subjectCards}`;

  document.querySelector("#start-weakest-subject")?.addEventListener("click", () => {
    saveJson(STORAGE_KEYS.profile, {
      ...readJson(STORAGE_KEYS.profile, {}),
      preferredExam: activeExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch,
      lastSubject: weakestSubject.subject,
      lastTopic: ""
    });
    localStorage.setItem("selectedExam", activeExam);
    saveJson(
      STORAGE_KEYS.config,
      buildWeakSubjectPracticeConfig(activeExam, activeStage, activeBranch, weakestSubject.subject, weakestSubject.accuracy)
    );
    window.location.href = buildVersionedPageUrl("./quiz.html");
  });
}

function renderExamDashboard() {
  const examDashboard = document.querySelector("#exam-dashboard");
  if (!examDashboard) {
    return;
  }

  const history = getAllAttempts();
  if (!history.length) {
    examDashboard.innerHTML = `
      <article class="history-empty">
        <strong>No exam attempts yet</strong>
        <span>Final mock and practice attempts will build exam-wise summary cards here.</span>
      </article>
    `;
    return;
  }

  const summary = history.reduce((accumulator, attempt) => {
    const examKey = `${attempt.exam || "General Practice"}${attempt.stage ? ` ${attempt.stage}` : ""}`;
    const current = accumulator[examKey] || {
      attempts: 0,
      totalScore: 0,
      totalQuestions: 0,
      best: Number.NEGATIVE_INFINITY
    };
    current.attempts += 1;
    current.totalScore += attempt.score;
    current.totalQuestions += attempt.total;
    current.best = Math.max(current.best, attempt.finalScore ?? attempt.score);
    accumulator[examKey] = current;
    return accumulator;
  }, {});

  examDashboard.innerHTML = Object.entries(summary).map(([exam, stats]) => `
    <article class="analytics-item analytics-card exam-summary-card">
      <div class="analytics-top">
        <strong>${exam}</strong>
        <span class="insight-pill insight-improving">${stats.attempts} attempts</span>
      </div>
      <p>Attempts: ${stats.attempts}</p>
      <p>Avg Accuracy: ${Math.round((stats.totalScore / stats.totalQuestions) * 100)}%</p>
      <p>Best Net Score: ${stats.best}</p>
    </article>
  `).join("");
}

function renderPatternPreview(examName, stage = "", branch = "") {
  const patternHeading = document.querySelector("#pattern-heading");
  const patternSummary = document.querySelector("#pattern-summary");
  if (!patternHeading || !patternSummary) {
    return;
  }

  const pattern = getExamPattern(examName, stage, branch);
  patternHeading.textContent = `${examName}${stage ? ` ${stage}` : ""}${branch ? ` - ${branch}` : ""} Final Mock`;
  patternSummary.innerHTML = `
    <article class="analytics-item analytics-card">
      <strong>Total Questions</strong>
      <p>${pattern.totalQuestions}</p>
    </article>
    <article class="analytics-item analytics-card">
      <strong>Timer</strong>
      <p>${pattern.timerMinutes} minutes</p>
    </article>
    <article class="analytics-item analytics-card">
      <strong>Marking</strong>
      <p>+1 correct | -0.33 wrong</p>
    </article>
    <article class="analytics-item analytics-card">
      <strong>Sections</strong>
      <p>${pattern.sections.map((section) => `${section.label || section.subject} ${section.count}`).join(" | ")}</p>
    </article>
  `;
}

function setupTabs() {
  const tabButtons = document.querySelectorAll("[data-tab-target]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");

  if (!tabButtons.length || !tabPanels.length) {
    return;
  }

  const activateTab = (target, { shouldScroll = false } = {}) => {
    tabButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.tabTarget === target);
    });

    tabPanels.forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.tabPanel !== target);
    });

    if (shouldScroll) {
      document.querySelector(`[data-tab-panel="${target}"]`)?.scrollIntoView({
        behavior: "smooth",
        block: "start"
      });
    }
  };

  tabButtons.forEach((button) => {
    button.addEventListener("click", () => activateTab(button.dataset.tabTarget, {
      shouldScroll: button.dataset.tabScroll === "true"
    }));
  });

  const defaultButton = Array.from(tabButtons).find((button) => button.dataset.defaultTab === "true") || tabButtons[0];
  activateTab(defaultButton.dataset.tabTarget);
}

function setupUtilityPage() {
  const pageKey = document.body?.dataset.utilityPage || "";
  if (!pageKey) {
    return;
  }

  if (pageKey === "final-mock-history") {
    window.location.replace("./history.html?view=final-mock");
    return;
  }

  const currentUser = readJson(STORAGE_KEYS.currentUser);
  if (!currentUser) {
    window.location.href = "./login.html";
    return;
  }

  if (!currentUser.preferredExam) {
    window.location.href = "./exam-select.html";
    return;
  }

  const profile = readJson(STORAGE_KEYS.profile, {
    name: currentUser.name || "",
    preferredExam: currentUser.preferredExam || "RRB NTPC",
    preferredStage: currentUser.preferredStage || "",
    preferredBranch: currentUser.preferredBranch || ""
  });

  const activeExam = sanitizeExamName(profile.preferredExam || currentUser.preferredExam || "RRB NTPC");
  const activeStage = profile.preferredStage || currentUser.preferredStage || "";
  const activeBranch = profile.preferredBranch || currentUser.preferredBranch || "";
  localStorage.setItem("selectedExam", activeExam);

  document.querySelectorAll("[data-nav-key]").forEach((link) => {
    link.classList.toggle("active", link.dataset.navKey === pageKey);
  });

  const examIndicator = document.querySelector("#current-exam-indicator");
  if (examIndicator) {
    examIndicator.textContent = `Current Exam: ${activeExam}${activeStage ? ` ${activeStage}` : ""}`;
  }

  const profileInput = document.querySelector("#profile-name");
  const profileHeading = document.querySelector("#profile-heading");
  const profileStatus = document.querySelector("#profile-status");
  const profileAvatar = document.querySelector("#profile-avatar");
  const profileAvatarPanel = document.querySelector("#profile-avatar-panel");
  const profileMenuButton = document.querySelector("#profile-menu-button");
  const profileMenuPanel = document.querySelector("#profile-menu-panel");
  const saveProfileButton = document.querySelector("#save-profile");
  const changeExamButton = document.querySelector("#change-exam");
  const logoutButton = document.querySelector("#logout-button");

  const refreshProfileBadge = (nameValue) => {
    const cleanName = (nameValue || currentUser.name || "Learner").trim();
    const avatarText = cleanName.charAt(0).toUpperCase() || "L";
    if (profileAvatar) {
      profileAvatar.textContent = avatarText;
    }
    if (profileAvatarPanel) {
      profileAvatarPanel.textContent = avatarText;
    }
  };

  if (profileInput) {
    profileInput.value = profile.name || currentUser.name || "";
  }
  if (profileHeading) {
    profileHeading.textContent = profile.name ? `Welcome back, ${profile.name}` : "Welcome back";
  }
  if (profileStatus) {
    profileStatus.textContent = `Signed in as ${currentUser.email} | Demo local auth active`;
  }
  refreshProfileBadge(profile.name || currentUser.name || "");

  const closeProfileMenu = () => {
    profileMenuPanel?.classList.add("hidden");
    profileMenuButton?.setAttribute("aria-expanded", "false");
  };

  const toggleProfileMenu = () => {
    const willOpen = profileMenuPanel?.classList.contains("hidden");
    profileMenuPanel?.classList.toggle("hidden", !willOpen);
    profileMenuButton?.setAttribute("aria-expanded", willOpen ? "true" : "false");
  };

  if (profileMenuButton?.dataset.profileBound !== "true") {
    profileMenuButton.dataset.profileBound = "true";

    profileMenuButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleProfileMenu();
    });

    profileMenuPanel?.addEventListener("click", (event) => {
      event.stopPropagation();
    });

    document.addEventListener("click", () => {
      closeProfileMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeProfileMenu();
      }
    });
  }

  saveProfileButton?.addEventListener("click", () => {
    const name = profileInput?.value.trim() || "";
    const savedProfile = readJson(STORAGE_KEYS.profile, {
      preferredExam: currentUser.preferredExam || "RRB NTPC"
    });

    saveJson(STORAGE_KEYS.profile, {
      ...savedProfile,
      name,
      preferredExam: savedProfile.preferredExam || activeExam,
      preferredStage: savedProfile.preferredStage || activeStage,
      preferredBranch: savedProfile.preferredBranch || activeBranch
    });

    const updatedUser = {
      ...readJson(STORAGE_KEYS.currentUser),
      name,
      preferredExam: currentUser.preferredExam || activeExam,
      preferredStage: currentUser.preferredStage || activeStage,
      preferredBranch: currentUser.preferredBranch || activeBranch
    };

    updateUserEverywhere(updatedUser);

    if (profileHeading) {
      profileHeading.textContent = name ? `Welcome back, ${name}` : "Welcome back";
    }
    if (profileStatus) {
      profileStatus.textContent = `Signed in as ${updatedUser.email || currentUser.email} | Demo local auth active`;
    }
    refreshProfileBadge(name);
    closeProfileMenu();
  });

  changeExamButton?.addEventListener("click", (event) => {
    event.preventDefault();
    closeProfileMenu();
    window.location.href = "./exam-select.html";
  });

  logoutButton?.addEventListener("click", (event) => {
    event.preventDefault();
    closeProfileMenu();
    localStorage.removeItem(STORAGE_KEYS.currentUser);
    window.location.href = "./login.html";
  });

  const historySubjectFilter = document.querySelector("#history-subject-filter");
  const historyPageShell = document.querySelector("[data-history-page]");
  const historySectionTitle = document.querySelector("#history-section-title");
  const historyPageCopy = document.querySelector("#history-page-copy");
  const historyFilterShell = document.querySelector("#history-filter-shell");
  const clearHistoryButton = document.querySelector("#clear-history");
  const practiceHistoryButton = document.querySelector("#history-view-practice");
  const finalMockHistoryButton = document.querySelector("#history-view-final-mock");
  const getHistoryView = () => {
    const params = new URLSearchParams(window.location.search);
    return params.get("view") === "final-mock" ? "final-mock" : "practice";
  };

  const setHistoryView = (view, { updateUrl = true } = {}) => {
    const activeView = view === "final-mock" ? "final-mock" : "practice";

    if (historyPageShell) {
      historyPageShell.dataset.historyView = activeView;
    }

    practiceHistoryButton?.classList.toggle("active", activeView === "practice");
    finalMockHistoryButton?.classList.toggle("active", activeView === "final-mock");

    if (historySectionTitle) {
      historySectionTitle.textContent = activeView === "final-mock" ? "Final Mock History" : "Practice History";
    }

    if (historyPageCopy) {
      historyPageCopy.textContent = activeView === "final-mock"
        ? "Review your full-length final mock attempts separately here."
        : "Review your practice sessions, weak drills, bookmark retries, and other practice attempts here.";
    }

    if (clearHistoryButton) {
      clearHistoryButton.textContent = activeView === "final-mock" ? "Clear Final Mock History" : "Clear Practice History";
    }

    if (historyFilterShell) {
      historyFilterShell.classList.toggle("hidden", activeView === "final-mock");
    }

    if (updateUrl) {
      const nextUrl = new URL(window.location.href);
      if (activeView === "final-mock") {
        nextUrl.searchParams.set("view", "final-mock");
      } else {
        nextUrl.searchParams.delete("view");
      }
      window.history.replaceState({}, "", nextUrl);
    }

    if (activeView === "final-mock") {
      renderFinalMockHistory("#history-list");
      return;
    }

    renderHistory(historySubjectFilter?.value || "all", "#history-list");
  };

  if (historySubjectFilter) {
    const subjects = getExamSubjects(activeExam, activeStage, activeBranch);
    historySubjectFilter.replaceChildren(
      ...[
        (() => {
          const option = document.createElement("option");
          option.value = "all";
          option.textContent = "All Subjects";
          return option;
        })(),
        ...subjects.map((subject) => {
          const option = document.createElement("option");
          option.value = subject;
          option.textContent = getSubjectDisplayName(activeExam, activeStage, subject);
          return option;
        })
      ]
    );
    if (historySubjectFilter.dataset.bound !== "true") {
      historySubjectFilter.dataset.bound = "true";
      historySubjectFilter.addEventListener("change", () => {
        setHistoryView("practice", { updateUrl: false });
      });
    }
  }

  if (practiceHistoryButton && practiceHistoryButton.dataset.bound !== "true") {
    practiceHistoryButton.dataset.bound = "true";
    practiceHistoryButton.addEventListener("click", () => {
      setHistoryView("practice");
    });
  }

  if (finalMockHistoryButton && finalMockHistoryButton.dataset.bound !== "true") {
    finalMockHistoryButton.dataset.bound = "true";
    finalMockHistoryButton.addEventListener("click", () => {
      setHistoryView("final-mock");
    });
  }

  switch (pageKey) {
    case "history":
      setHistoryView(getHistoryView(), { updateUrl: false });
      break;
    case "bookmarks":
      renderBookmarks();
      break;
    case "wrong-questions":
      renderWrongQuestions();
      break;
    case "analysis":
      renderAnalytics();
      break;
    case "leaderboard":
      void renderLeaderboard({
        exam: activeExam,
        username: profile.name || currentUser.name || currentUser.email || "Learner"
      });
      break;
    case "exam-dashboard":
      renderExamDashboard();
      break;
    default:
      break;
  }

  document.querySelector("#clear-history")?.addEventListener("click", () => {
    const currentExam = getCurrentExam();
    const activeView = historyPageShell?.dataset.historyView === "final-mock" ? "final-mock" : "practice";
    localStorage.removeItem(
      activeView === "final-mock"
        ? getExamSpecificKey(STORAGE_KEYS.finalMockHistory, currentExam)
        : getExamSpecificKey(STORAGE_KEYS.history, currentExam)
    );

    if (pageKey === "history") {
      setHistoryView(activeView, { updateUrl: false });
      return;
    }

    renderHistory(historySubjectFilter?.value || "all");
  });

  document.querySelector("#clear-final-mock-history")?.addEventListener("click", () => {
    const currentExam = getCurrentExam();
    localStorage.removeItem(getExamSpecificKey(STORAGE_KEYS.finalMockHistory, currentExam));
    renderFinalMockHistory();
  });

  document.querySelector("#clear-bookmarks")?.addEventListener("click", () => {
    const currentExam = getCurrentExam();
    localStorage.removeItem(getExamSpecificKey(STORAGE_KEYS.bookmarks, currentExam));
    const legacyBookmarks = readJson(STORAGE_KEYS.bookmarks, []);
    if (legacyBookmarks.length) {
      saveJson(
        STORAGE_KEYS.bookmarks,
        legacyBookmarks.filter((bookmark) => (bookmark.exam || "RRB NTPC") !== currentExam)
      );
    }
    renderBookmarks();
  });

  document.querySelector("#clear-wrong-questions")?.addEventListener("click", () => {
    const currentExam = getCurrentExam();
    const wrongQuestions = readJson(STORAGE_KEYS.wrongQuestions, []);
    const nextWrongQuestions = wrongQuestions.filter((item) => (item.exam || "RRB NTPC") !== currentExam);
    saveJson(STORAGE_KEYS.wrongQuestions, nextWrongQuestions);

    const mistakesKey = getExamSpecificKey(STORAGE_KEYS.mistakes, currentExam);
    localStorage.removeItem(mistakesKey);
    const legacyMistakes = readJson(STORAGE_KEYS.mistakes, []);
    if (legacyMistakes.length) {
      saveJson(
        STORAGE_KEYS.mistakes,
        legacyMistakes.filter((item) => (item.exam || "RRB NTPC") !== currentExam)
      );
    }

    renderWrongQuestions();
  });
}

function updateUserEverywhere(updatedUser) {
  const users = readJson(STORAGE_KEYS.authUsers, []);
  saveJson(
    STORAGE_KEYS.authUsers,
    users.map((entry) => entry.email === updatedUser.email ? updatedUser : entry)
  );
  saveJson(STORAGE_KEYS.currentUser, updatedUser);
}

function setupExamSelectPage() {
  const examForm = document.querySelector("#exam-select-form");
  if (!examForm) {
    return;
  }

  const currentUser = readJson(STORAGE_KEYS.currentUser);
  if (!currentUser) {
    window.location.href = "./login.html";
    return;
  }

  const examCards = document.querySelectorAll("[data-exam-card]");
  const examInput = document.querySelector("#selected-exam");
  const continueButton = document.querySelector("#exam-continue-button");

  const setSelectedExam = (examName) => {
    const nextExam = examName || "RRB NTPC";
    if (examInput) {
      examInput.value = nextExam;
    }
    examCards.forEach((card) => {
      const isActive = card.dataset.examCard === nextExam;
      card.classList.toggle("active", isActive);
      card.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  };

  examCards.forEach((card) => {
    card.addEventListener("click", () => {
      setSelectedExam(card.dataset.examCard);
    });
  });

  const initialExam = sanitizeExamName(currentUser.preferredExam || "");
  if (initialExam) {
    setSelectedExam(initialExam);
  }

  const continueToDashboard = () => {
    const preferredExam = sanitizeExamName(examInput?.value || "RRB NTPC");
    const stageOptions = getExamStageOptions(preferredExam);
    const preferredStage = stageOptions.length ? stageOptions[0] : "";
    const updatedUser = { ...currentUser, preferredExam, preferredStage };

    updateUserEverywhere(updatedUser);
    saveJson(STORAGE_KEYS.profile, {
      name: updatedUser.name || "",
      preferredExam,
      preferredStage,
      lastSubject: "",
      lastTopic: ""
    });

    window.location.href = "./dashboard.html";
  };

  examForm.addEventListener("submit", (event) => {
    event.preventDefault();
    continueToDashboard();
  });

  continueButton?.addEventListener("click", (event) => {
    event.preventDefault();
    continueToDashboard();
  });
}

function setupHomePage() {
  const form = document.querySelector("#start-form");
  if (!form) {
    return;
  }

  const currentUser = readJson(STORAGE_KEYS.currentUser);
  if (!currentUser) {
    window.location.href = "./login.html";
    return;
  }

  if (!currentUser.preferredExam) {
    window.location.href = "./exam-select.html";
    return;
  }

  clearQuizSession();

  const profileInput = document.querySelector("#profile-name");
  const saveProfileButton = document.querySelector("#save-profile");
  const profileHeading = document.querySelector("#profile-heading");
  const profileStatus = document.querySelector("#profile-status");
  const profileAvatar = document.querySelector("#profile-avatar");
  const profileAvatarPanel = document.querySelector("#profile-avatar-panel");
  const profileMenuButton = document.querySelector("#profile-menu-button");
  const profileMenuPanel = document.querySelector("#profile-menu-panel");
  const clearHistoryButton = document.querySelector("#clear-history");
  const changeExamButton = document.querySelector("#change-exam");
  const logoutButton = document.querySelector("#logout-button");
  const examSelect = document.querySelector("#exam");
  const stageField = document.querySelector("#stage-field");
  const stageSelect = document.querySelector("#stage");
  const branchField = document.querySelector("#branch-field");
  const branchSelect = document.querySelector("#branch");
  const practiceTypeInput = document.querySelector("#practice-type");
  const practiceTypeButtons = Array.from(document.querySelectorAll("[data-practice-type]"));

  const modeSelect = document.querySelector("#mode");
  const subjectSelect = document.querySelector("#subject");
  const topicSelect = document.querySelector("#topic");
  const topicHint = document.querySelector("#topic-hint");
  const chapterPracticePanel = document.querySelector("#chapter-practice-panel");
  const countField = document.querySelector("#count-field");
  const countFieldNote = document.querySelector("#count-field-note");
  const chapterSelectionContent = document.querySelector("#chapter-selection-content");
  const chapterToggleButton = document.querySelector("#chapter-toggle-button");
  const chapterToggleLabel = document.querySelector("#chapter-toggle-label");
  const chapterToggleIcon = document.querySelector("#chapter-toggle-icon");
  const chapterStartButton = document.querySelector("#chapter-start-button");
  const chapterStartLabel = document.querySelector("#chapter-start-label");
  const chapterList = document.querySelector("#chapter-list");
  const chapterSearchInput = document.querySelector("#chapter-search");
  const chapterCount = document.querySelector("#chapter-count");
  const chapterPracticeHint = document.querySelector("#chapter-practice-hint");
  const chapterSelectAllButton = document.querySelector("#chapter-select-all");
  const weakDrillButton = document.querySelector("#start-weak-drill");
  const weakDrillBadge = document.querySelector("#weak-drill-badge");
  const weakDrillCopy = document.querySelector("#weak-drill-copy");
  const countSelect = document.querySelector("#count");
  const difficultySelect = document.querySelector("#difficulty");
  const finalMockDifficultySelect = document.querySelector("#final-mock-difficulty");
  const mockButton = document.querySelector("#start-final-mock");
  let finalMockDifficultyInteractionAt = 0;

  const profile = readJson(STORAGE_KEYS.profile, {
    name: currentUser.name || "",
    preferredExam: currentUser.preferredExam || "RRB NTPC",
    preferredStage: currentUser.preferredStage || "",
    preferredBranch: currentUser.preferredBranch || ""
  });

  if (profileInput) {
    profileInput.value = profile.name || "";
  }

  const refreshProfileBadge = (nameValue) => {
    const cleanName = (nameValue || currentUser.name || "Learner").trim();
    const avatarText = cleanName.charAt(0).toUpperCase() || "L";
    if (profileAvatar) {
      profileAvatar.textContent = avatarText;
    }
    if (profileAvatarPanel) {
      profileAvatarPanel.textContent = avatarText;
    }
  };

  if (profileHeading) {
    profileHeading.textContent = profile.name ? `Welcome back, ${profile.name}` : "Welcome back";
  }
  if (profileStatus) {
    profileStatus.textContent = `Signed in as ${currentUser.email} | Demo local auth active`;
  }
  refreshProfileBadge(profile.name);

  const closeProfileMenu = () => {
    profileMenuPanel?.classList.add("hidden");
    profileMenuButton?.setAttribute("aria-expanded", "false");
  };

  const toggleProfileMenu = () => {
    const willOpen = profileMenuPanel?.classList.contains("hidden");
    profileMenuPanel?.classList.toggle("hidden", !willOpen);
    profileMenuButton?.setAttribute("aria-expanded", willOpen ? "true" : "false");
  };

  if (profileMenuButton?.dataset.profileBound !== "true") {
    profileMenuButton.dataset.profileBound = "true";

    profileMenuButton.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      toggleProfileMenu();
    });

    profileMenuPanel?.addEventListener("click", (event) => {
      event.stopPropagation();
    });

    document.addEventListener("click", () => {
      closeProfileMenu();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeProfileMenu();
      }
    });
  }

  renderLastAttemptCard();
  if (document.querySelector("#history-list")) {
    renderHistory();
  }
  if (document.querySelector("#final-mock-history-list")) {
    renderFinalMockHistory();
  }
  if (document.querySelector("#bookmark-list")) {
    renderBookmarks();
  }
  document.querySelector("#bookmark-subject-filter")?.addEventListener("change", () => {
    renderBookmarks();
  });
  if (document.querySelector("#mistake-list")) {
    renderMistakes();
  }
  if (document.querySelector("#wrong-questions-list")) {
    renderWrongQuestions();
  }
  document.querySelector("#wrong-question-subject-filter")?.addEventListener("change", () => {
    renderWrongQuestions();
  });
  if (document.querySelector("#analytics-list")) {
    renderAnalytics();
  }
  if (document.querySelector("[data-tab-panel='leaderboard']")) {
    void renderLeaderboard({
      exam: profile.preferredExam || currentUser.preferredExam || "RRB NTPC",
      username: profile.name || currentUser.name || currentUser.email || "Learner"
    });
  }
  if (document.querySelector("#exam-dashboard")) {
    renderExamDashboard();
  }
  if (document.querySelector("[data-tab-target]") && document.querySelector("[data-tab-panel]")) {
    setupTabs();
  }

  // Setup history subject filter
  const historySubjectFilter = document.querySelector("#history-subject-filter");
  if (historySubjectFilter) {
    historySubjectFilter.addEventListener("change", () => {
      renderHistory(historySubjectFilter.value);
    });
  }

  const syncModeFields = () => {
    const isFinalMock = modeSelect?.value === "final-mock";
    const isChapterPractice = practiceTypeInput?.value === "chapter-practice";
    if (subjectSelect) {
      subjectSelect.disabled = isFinalMock;
    }
    if (stageSelect) {
      stageSelect.disabled = isFinalMock && !getExamStageOptions(examSelect?.value || initialExamName).length;
    }
    if (topicSelect) {
      topicSelect.disabled = isFinalMock || isChapterPractice;
      if (isFinalMock) {
        topicHint.textContent = "Final mock me full syllabus pattern automatically apply hoga.";
      } else if (isChapterPractice) {
        topicHint.textContent = "Chapter practice me multiple selected chapters se mixed test banega.";
      } else {
        syncTopicOptions(
          examSelect?.value || initialExamName,
          stageSelect?.value || "",
          branchSelect?.value || "",
          subjectSelect.value,
          topicSelect,
          topicHint,
          topicSelect.value
        );
      }
    }
    syncCountField();
  };

  const getActiveSubjectTopics = (examName, stage, branch, subject) => {
    const examMapping = getExamTopicMapping(examName, stage, branch);
    const resolvedSubject = resolveSubjectKey(examName, stage, subject, branch);
    return examMapping[resolvedSubject] || [];
  };

  const getSelectedChapters = () => Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value);
  const getChapterPracticeQuestionCount = () => Math.max(getSelectedChapters().length, 1) * 5;

  const syncCountField = () => {
    if (!countSelect) {
      return;
    }

    const isFinalMock = modeSelect?.value === "final-mock";
    const isChapterPractice = practiceTypeInput?.value === "chapter-practice";
    const autoOption = countSelect.querySelector('[data-auto-count="true"]');

    if (isChapterPractice) {
      const autoCount = getChapterPracticeQuestionCount();
      let dynamicOption = autoOption;

      if (!dynamicOption) {
        dynamicOption = document.createElement("option");
        dynamicOption.dataset.autoCount = "true";
        countSelect.append(dynamicOption);
      }

      dynamicOption.value = String(autoCount);
      dynamicOption.textContent = String(autoCount);
      countSelect.value = String(autoCount);
      countSelect.disabled = true;
      countField?.classList.add("opacity-80");

      if (countFieldNote) {
        countFieldNote.textContent = `${autoCount} questions auto-set: 5 RRB-style questions per selected chapter.`;
      }
      return;
    }

    autoOption?.remove();
    countSelect.disabled = isFinalMock;
    if (!countSelect.value) {
      countSelect.value = "10";
    }
    countField?.classList.remove("opacity-80");

    if (countFieldNote) {
      countFieldNote.textContent = "Choose how many questions you want in this test.";
    }
  };
  let chapterSelectionOpen = false;

  const setChapterSelectionOpen = (shouldOpen) => {
    chapterSelectionOpen = Boolean(shouldOpen);

    if (chapterSelectionContent) {
      chapterSelectionContent.classList.toggle("hidden", !chapterSelectionOpen);
    }

    if (chapterToggleButton) {
      chapterToggleButton.setAttribute("aria-expanded", chapterSelectionOpen ? "true" : "false");
    }

    if (chapterToggleLabel) {
      chapterToggleLabel.textContent = chapterSelectionOpen ? "Hide Chapter Selection" : "Open Chapter Selection";
    }

    if (chapterToggleIcon) {
      chapterToggleIcon.textContent = chapterSelectionOpen ? "expand_less" : "expand_more";
    }
  };

  const getCurrentExamHistory = (examName) => readJson(getExamSpecificKey(STORAGE_KEYS.history, examName), []);

  const buildTopicAccuracyMap = (examName, stage, branch) => {
    const examMapping = getExamTopicMapping(examName, stage, branch);
    const history = getCurrentExamHistory(examName);
    const validTopics = new Map();

    Object.entries(examMapping).forEach(([subject, topics]) => {
      validTopics.set(subject, new Set(topics));
    });

    const accuracyMap = new Map();
    history.forEach((attempt) => {
      const resolvedSubject = resolveSubjectKey(examName, stage, attempt.subject, branch);
      if (!resolvedSubject || !validTopics.get(resolvedSubject)?.has(attempt.topic)) {
        return;
      }

      const key = `${resolvedSubject}__${attempt.topic}`;
      const current = accuracyMap.get(key) || {
        subject: resolvedSubject,
        topic: attempt.topic,
        correct: 0,
        total: 0
      };

      current.correct += Number(attempt.score || 0);
      current.total += Number(attempt.total || 0);
      accuracyMap.set(key, current);
    });

    return accuracyMap;
  };

  const getWeakTopicRecommendations = (examName, stage, branch) => {
    const accuracyMap = buildTopicAccuracyMap(examName, stage, branch);
    const entries = Array.from(accuracyMap.values()).map((entry) => ({
      ...entry,
      accuracy: entry.total ? Math.round((entry.correct / entry.total) * 100) : 0
    }));

    let weakTopics = entries.filter((entry) => entry.accuracy < 50);
    if (weakTopics.length < 3) {
      weakTopics = entries.filter((entry) => entry.accuracy < 60);
    }

    return weakTopics.sort((left, right) => left.accuracy - right.accuracy || left.topic.localeCompare(right.topic));
  };

  const updateChapterAssist = () => {
    if (!chapterCount || !chapterList) {
      return;
    }

    const selectedChapters = getSelectedChapters();
    const selected = selectedChapters.length;
    const visibleCards = Array.from(chapterList.children).filter((item) =>
      !item.classList.contains("hidden") && !item.classList.contains("chapter-empty")
    ).length;
    chapterCount.textContent = `${selected} chapter${selected === 1 ? "" : "s"} selected${visibleCards ? ` | ${visibleCards} visible` : ""}`;

    if (chapterSelectAllButton) {
      const checkboxes = Array.from(chapterList.querySelectorAll('input[type="checkbox"]'));
      const allSelected = checkboxes.length > 0 && checkboxes.every((input) => input.checked);
      chapterSelectAllButton.textContent = allSelected ? "Clear All" : "Select All";
    }

    if (chapterStartButton) {
      chapterStartButton.disabled = selected === 0;
    }

    if (chapterStartLabel) {
      chapterStartLabel.textContent = selected > 0
        ? `Continue with ${selected} Chapter${selected === 1 ? "" : "s"}`
        : "Continue with Chapters";
    }

    syncCountField();

    if (!chapterPracticeHint) {
      return;
    }

    const chapterQuestionMode = String(form?.querySelector('input[name="chapterQuestionMode"]:checked')?.value || "full-subject-mix");
    if (selected >= 2 && chapterQuestionMode === "selected-chapters-only") {
      const accuracyMap = buildTopicAccuracyMap(
        sanitizeExamName(examSelect?.value || initialExamName),
        stageSelect?.value || "",
        branchSelect?.value || ""
      );
      const weakest = selectedChapters
        .map((topic) => {
          const subject = resolveSubjectKey(
            sanitizeExamName(examSelect?.value || initialExamName),
            stageSelect?.value || "",
            subjectSelect?.value || "Mathematics",
            branchSelect?.value || ""
          );
          const found = accuracyMap.get(`${subject}__${topic}`);
          const accuracy = found?.total ? Math.round((found.correct / found.total) * 100) : 0;
          return { topic, accuracy };
        })
        .sort((left, right) => left.accuracy - right.accuracy)[0];

      chapterPracticeHint.textContent = weakest
        ? `Smart Mix on - more questions will be drawn from your weakest chapter: "${weakest.topic}".`
        : "Smart Mix on - extra weight will be given to your weakest chapter.";
      return;
    }

    chapterPracticeHint.textContent = selected
      ? `${selected * 5} RRB-style questions will be auto-generated. 5 questions from each selected chapter.`
      : "Select at least one chapter. 5 RRB-style questions will be generated for each selected chapter.";
  };

  const syncChapterSearch = () => {
    if (!chapterList || !chapterSearchInput) {
      return;
    }

    const query = chapterSearchInput.value.trim().toLowerCase();
    Array.from(chapterList.children).forEach((item) => {
      if (item.classList.contains("chapter-empty")) {
        return;
      }
      const title = item.getAttribute("data-topic") || "";
      const shouldShow = !query || title.includes(query);
      item.classList.toggle("hidden", !shouldShow);
    });

    const hasVisible = Array.from(chapterList.children).some((item) =>
      !item.classList.contains("hidden") && !item.classList.contains("chapter-empty")
    );
    const emptyState = chapterList.querySelector(".chapter-empty");
    if (!hasVisible && !emptyState) {
      const empty = document.createElement("div");
      empty.className = "chapter-empty sm:col-span-2";
      empty.textContent = "No chapters matched your search.";
      chapterList.append(empty);
    } else if (hasVisible && emptyState) {
      emptyState.remove();
    } else if (!hasVisible && emptyState) {
      emptyState.classList.remove("hidden");
    }

    updateChapterAssist();
  };

  const renderChapterOptions = (examName, stage, branch, subject, preferredChapters = []) => {
    if (!chapterList) {
      return;
    }

    const topics = getActiveSubjectTopics(examName, stage, branch, subject);
    chapterList.replaceChildren(
      ...topics.map((topic, index) => {
        const label = document.createElement("label");
        label.className = "chapter-chip";
        label.setAttribute("data-topic", topic.toLowerCase());

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.name = "selectedChapters";
        checkbox.value = topic;
        checkbox.className = "h-4 w-4 accent-teal-700";
        checkbox.checked = preferredChapters.length ? preferredChapters.includes(topic) : index < Math.min(3, topics.length);

        const box = document.createElement("span");
        box.className = "chapter-chip-box";
        box.innerHTML = '<span class="material-symbols-outlined" style="font-size:14px;font-variation-settings:\'FILL\' 1;">check</span>';

        const content = document.createElement("span");
        content.className = "block min-w-0";

        const title = document.createElement("span");
        title.className = "chapter-chip-title block";
        title.textContent = topic;

        const copy = document.createElement("span");
        copy.className = "chapter-chip-meta mt-1 block";
        copy.textContent = checkbox.checked ? "Selected" : "Tap to include";

        content.append(title, copy);
        label.append(checkbox, box, content);
        label.classList.toggle("selected", checkbox.checked);

        checkbox.addEventListener("change", () => {
          label.classList.toggle("selected", checkbox.checked);
          copy.textContent = checkbox.checked ? "Selected" : "Tap to include";
          updateChapterAssist();
        });

        return label;
      })
    );

    updateChapterAssist();
    syncChapterSearch();
  };

  const syncPracticeTypeUI = () => {
    if (practiceTypeInput) {
      practiceTypeInput.value = "subject-test";
    }

    practiceTypeButtons.forEach((button) => {
      button.classList.toggle("active", false);
    });


    chapterPracticePanel?.classList.add("hidden");
    setChapterSelectionOpen(false);

    if (chapterPracticeHint) {
      chapterPracticeHint.textContent = "All major topics from the selected subject will be mixed to generate the test.";
    }

    syncModeFields();
  };

  const applyPreferredExam = (examName) => {
    const preferredExam = sanitizeExamName(examName || "RRB NTPC");
    if (examSelect) {
      examSelect.value = preferredExam;
    }
  };

  const syncStageOptions = (examName, preferredStage = "") => {
    if (!stageField || !stageSelect) {
      return;
    }

    const stages = getExamStageOptions(examName);
    stageField.classList.toggle("hidden", !stages.length);

    if (!stages.length) {
      stageSelect.innerHTML = '<option value="">Standard</option>';
      stageSelect.value = "";
      return;
    }

    stageSelect.innerHTML = stages.map((stage) => `
      <option value="${stage}">${stage}</option>
    `).join("");

    if (preferredStage && stages.includes(preferredStage)) {
      stageSelect.value = preferredStage;
    } else {
      stageSelect.value = stages[0];
    }
  };

  const syncBranchOptions = (examName, stage, preferredBranch = "") => {
    if (!branchField || !branchSelect) {
      return;
    }

    const branches = getExamBranchOptions(examName, stage);
    branchField.classList.toggle("hidden", !branches.length);

    if (!branches.length) {
      branchSelect.innerHTML = '<option value="">Standard</option>';
      branchSelect.value = "";
      return;
    }

    branchSelect.innerHTML = branches.map((branch) => `
      <option value="${branch}">${branch}</option>
    `).join("");

    branchSelect.value = sanitizeBranchName(examName, stage, preferredBranch);
  };

  const initialExamName = sanitizeExamName(profile.preferredExam || currentUser.preferredExam || "RRB NTPC");
  applyPreferredExam(initialExamName);
  syncStageOptions(initialExamName, profile.preferredStage || currentUser.preferredStage || "");
  syncBranchOptions(initialExamName, stageSelect?.value || "", profile.preferredBranch || currentUser.preferredBranch || "");
  syncSubjectOptions(initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect, profile.lastSubject || "Mathematics");
  syncTopicOptions(initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect?.value || getExamSubjects(initialExamName, stageSelect?.value || "", branchSelect?.value || "")[0] || "Mathematics", topicSelect, topicHint, profile.lastTopic || "");
  practiceTypeInput.value = "subject-test";
  renderChapterOptions(initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect?.value || "Mathematics", profile.selectedChapters || []);
  if (subjectSelect && topicSelect && !topicSelect.options.length) {
    syncSubjectOptions(initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect, getExamSubjects(initialExamName, stageSelect?.value || "", branchSelect?.value || "")[0] || "");
    syncTopicOptions(initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect.value, topicSelect, topicHint, profile.lastTopic || "");
  }
  syncPracticeTypeUI();

  examSelect?.addEventListener("change", () => {
    const preferredExam = sanitizeExamName(examSelect.value || "RRB NTPC");
    const latestUser = readJson(STORAGE_KEYS.currentUser, currentUser);
    const latestProfile = readJson(STORAGE_KEYS.profile, profile);
    syncStageOptions(preferredExam);
    syncBranchOptions(preferredExam, stageSelect?.value || "", latestProfile.preferredBranch || latestUser.preferredBranch || "");
    const activeStage = stageSelect?.value || "";
    const activeBranch = branchSelect?.value || "";

    syncSubjectOptions(preferredExam, activeStage, activeBranch, subjectSelect);
    syncTopicOptions(preferredExam, activeStage, activeBranch, subjectSelect?.value || getExamSubjects(preferredExam, activeStage, activeBranch)[0] || "Mathematics", topicSelect, topicHint);
    renderChapterOptions(preferredExam, activeStage, activeBranch, subjectSelect?.value || "Mathematics");

    updateUserEverywhere({
      ...latestUser,
      preferredExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch
    });

    saveJson(STORAGE_KEYS.profile, {
      ...latestProfile,
      preferredExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch,
      practiceType: "subject-test",
      lastSubject: subjectSelect?.value || "",
      lastTopic: topicSelect?.value || "",
      selectedChapters: Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value)
    });

    renderBookmarks();
    renderMistakes();
    renderWrongQuestions();
    renderHistory();
    renderFinalMockHistory();
    renderLastAttemptCard();
    renderAnalytics();
    void renderLeaderboard({
      exam: preferredExam,
      username: latestProfile.name || latestUser.name || latestUser.email || "Learner"
    });
    renderExamDashboard();
    refreshWeakDrillState();
  });

  stageSelect?.addEventListener("change", () => {
    const activeExam = sanitizeExamName(examSelect?.value || initialExamName);
    const activeStage = stageSelect.value || "";
    const latestUser = readJson(STORAGE_KEYS.currentUser, currentUser);
    const latestProfile = readJson(STORAGE_KEYS.profile, profile);
    syncBranchOptions(activeExam, activeStage, latestProfile.preferredBranch || latestUser.preferredBranch || "");
    const activeBranch = branchSelect?.value || "";

    syncSubjectOptions(activeExam, activeStage, activeBranch, subjectSelect);
    syncTopicOptions(activeExam, activeStage, activeBranch, subjectSelect?.value || getExamSubjects(activeExam, activeStage, activeBranch)[0] || "Mathematics", topicSelect, topicHint);
    renderChapterOptions(activeExam, activeStage, activeBranch, subjectSelect?.value || "Mathematics");

    updateUserEverywhere({
      ...latestUser,
      preferredExam: activeExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch
    });

    saveJson(STORAGE_KEYS.profile, {
      ...latestProfile,
      preferredExam: activeExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch,
      practiceType: "subject-test",
      lastSubject: subjectSelect?.value || "",
      lastTopic: topicSelect?.value || "",
      selectedChapters: Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value)
    });
    refreshWeakDrillState();
  });

  branchSelect?.addEventListener("change", () => {
    const activeExam = sanitizeExamName(examSelect?.value || initialExamName);
    const activeStage = stageSelect?.value || "";
    const activeBranch = branchSelect.value || "";
    const latestUser = readJson(STORAGE_KEYS.currentUser, currentUser);
    const latestProfile = readJson(STORAGE_KEYS.profile, profile);

    syncSubjectOptions(activeExam, activeStage, activeBranch, subjectSelect);
    syncTopicOptions(activeExam, activeStage, activeBranch, subjectSelect?.value || getExamSubjects(activeExam, activeStage, activeBranch)[0] || "Mathematics", topicSelect, topicHint);
    renderChapterOptions(activeExam, activeStage, activeBranch, subjectSelect?.value || "Mathematics");

    updateUserEverywhere({
      ...latestUser,
      preferredExam: activeExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch
    });

    saveJson(STORAGE_KEYS.profile, {
      ...latestProfile,
      preferredExam: activeExam,
      preferredStage: activeStage,
      preferredBranch: activeBranch,
      practiceType: "subject-test",
      lastSubject: subjectSelect?.value || "",
      lastTopic: topicSelect?.value || "",
      selectedChapters: Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value)
    });

    renderExamDashboard();
    refreshWeakDrillState();
  });

  subjectSelect?.addEventListener("change", () => {
    syncTopicOptions(examSelect?.value || initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect.value, topicSelect, topicHint);
    renderChapterOptions(examSelect?.value || initialExamName, stageSelect?.value || "", branchSelect?.value || "", subjectSelect.value);
  });

  practiceTypeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!practiceTypeInput) {
        return;
      }

      practiceTypeInput.value = button.dataset.practiceType || "topic-practice";
      syncPracticeTypeUI();
    });
  });

  chapterSelectAllButton?.addEventListener("click", () => {
    const checkboxes = Array.from(chapterList?.querySelectorAll('input[type="checkbox"]') || []);
    const shouldSelectAll = checkboxes.some((input) => !input.checked);
    checkboxes.forEach((input) => {
      input.checked = shouldSelectAll;
      const card = input.closest(".chapter-chip");
      const meta = card?.querySelector(".chapter-chip-meta");
      card?.classList.toggle("selected", input.checked);
      if (meta) {
        meta.textContent = input.checked ? "Selected" : "Tap to include";
      }
    });
    updateChapterAssist();
  });

  chapterToggleButton?.addEventListener("click", () => {
    setChapterSelectionOpen(!chapterSelectionOpen);
  });

  if (chapterSearchInput && chapterSearchInput.dataset.bound !== "true") {
    chapterSearchInput.dataset.bound = "true";
    chapterSearchInput.addEventListener("input", syncChapterSearch);
  }

  form.querySelectorAll('input[name="chapterQuestionMode"]').forEach((input) => {
    input.addEventListener("change", updateChapterAssist);
  });

  const refreshWeakDrillState = () => {
    if (!weakDrillButton || !weakDrillBadge || !weakDrillCopy) {
      return;
    }

    const activeExam = sanitizeExamName(examSelect?.value || initialExamName);
    const activeStage = stageSelect?.value || "";
    const activeBranch = branchSelect?.value || "";
    const weakTopics = getWeakTopicRecommendations(activeExam, activeStage, activeBranch);
    weakDrillBadge.textContent = `${weakTopics.length}`;
    weakDrillButton.disabled = !weakTopics.length;

    if (!weakTopics.length) {
      weakDrillCopy.textContent = "Practice more tests to unlock weak-topic drill.";
      return;
    }

    const involvedSubjects = Array.from(new Set(weakTopics.map((entry) => entry.subject))).slice(0, 2);
    weakDrillCopy.textContent = `${weakTopics.length} weak topics found${involvedSubjects.length ? ` across ${involvedSubjects.join(" and ")}` : ""}.`;
  };

  modeSelect?.addEventListener("change", syncModeFields);
  syncModeFields();
  refreshWeakDrillState();

  if (finalMockDifficultySelect) {
    const markFinalMockDifficultyInteraction = (event) => {
      finalMockDifficultyInteractionAt = Date.now();
      event.stopPropagation();
    };

    ["pointerdown", "click", "change", "focus", "touchstart"].forEach((eventName) => {
      finalMockDifficultySelect.addEventListener(eventName, markFinalMockDifficultyInteraction);
    });
  }

  saveProfileButton?.addEventListener("click", () => {
    const name = profileInput?.value.trim() || "";
    const savedProfile = readJson(STORAGE_KEYS.profile, {
      preferredExam: currentUser.preferredExam || "RRB NTPC"
    });

    saveJson(STORAGE_KEYS.profile, {
      name,
      preferredExam: savedProfile.preferredExam || "RRB NTPC",
      preferredStage: savedProfile.preferredStage || "",
      preferredBranch: savedProfile.preferredBranch || "",
      practiceType: "subject-test",
      lastSubject: subjectSelect?.value || "",
      lastTopic: topicSelect?.value || "",
      selectedChapters: Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value)
    });

    const updatedUser = {
      ...readJson(STORAGE_KEYS.currentUser),
      name,
      preferredExam: currentUser.preferredExam || savedProfile.preferredExam || "RRB NTPC",
      preferredStage: currentUser.preferredStage || savedProfile.preferredStage || "",
      preferredBranch: currentUser.preferredBranch || savedProfile.preferredBranch || ""
    };

    updateUserEverywhere(updatedUser);

    if (profileHeading) {
      profileHeading.textContent = name ? `Welcome back, ${name}` : "Welcome back";
    }
    if (profileStatus) {
      const updatedCurrentUser = readJson(STORAGE_KEYS.currentUser);
      profileStatus.textContent = `Signed in as ${updatedCurrentUser?.email || currentUser.email} | Demo local auth active`;
    }
    refreshProfileBadge(name);
    closeProfileMenu();
  });

  clearHistoryButton?.addEventListener("click", () => {
    const { exam: currentExam, stage: activeStage, branch: activeBranch } = getCurrentExamContext();
    localStorage.removeItem(getExamSpecificKey(STORAGE_KEYS.history, currentExam));
    renderHistory();
    refreshLastAttempt();
    renderLastAttemptCard();
    renderAnalytics();
    renderExamDashboard();
    refreshWeakDrillState();
  });

  document.querySelector("#clear-final-mock-history")?.addEventListener("click", () => {
    const { exam: currentExam, stage: activeStage, branch: activeBranch } = getCurrentExamContext();
    localStorage.removeItem(getExamSpecificKey(STORAGE_KEYS.finalMockHistory, currentExam));
    renderFinalMockHistory();
    refreshLastAttempt();
    renderLastAttemptCard();
    renderAnalytics();
    renderExamDashboard();
  });

  document.querySelector("#clear-bookmarks")?.addEventListener("click", () => {
    const { exam: currentExam } = getCurrentExamContext();
    localStorage.removeItem(getExamSpecificKey(STORAGE_KEYS.bookmarks, currentExam));
    const legacyBookmarks = readJson(STORAGE_KEYS.bookmarks, []);
    if (legacyBookmarks.length) {
      saveJson(
        STORAGE_KEYS.bookmarks,
        legacyBookmarks.filter((bookmark) => (bookmark.exam || "RRB NTPC") !== currentExam)
      );
    }
    renderBookmarks();
  });

  document.querySelector("#clear-wrong-questions")?.addEventListener("click", () => {
    const { exam: currentExam } = getCurrentExamContext();
    const wrongQuestions = readJson(STORAGE_KEYS.wrongQuestions, []);
    const nextWrongQuestions = wrongQuestions.filter((item) => (item.exam || "RRB NTPC") !== currentExam);
    saveJson(STORAGE_KEYS.wrongQuestions, nextWrongQuestions);

    const mistakesKey = getExamSpecificKey(STORAGE_KEYS.mistakes, currentExam);
    localStorage.removeItem(mistakesKey);
    const legacyMistakes = readJson(STORAGE_KEYS.mistakes, []);
    if (legacyMistakes.length) {
      saveJson(
        STORAGE_KEYS.mistakes,
        legacyMistakes.filter((item) => (item.exam || "RRB NTPC") !== currentExam)
      );
    }

    renderWrongQuestions();
  });

  weakDrillButton?.addEventListener("click", () => {
    const activeExam = sanitizeExamName(examSelect?.value || initialExamName);
    const activeStage = stageSelect?.value || "";
    const activeBranch = branchSelect?.value || "";
    const weakTopics = getWeakTopicRecommendations(activeExam, activeStage, activeBranch).slice(0, 8);

    if (!weakTopics.length) {
      return;
    }

    const config = {
      exam: activeExam,
      stage: activeStage,
      branch: activeBranch,
      subject: "Weak Areas",
      topic: "Auto Drill",
      count: 15,
      mode: "practice",
      difficulty: "intermediate",
      practiceType: "weak-drill",
      drillTopics: weakTopics.map((entry) => ({
        subject: entry.subject,
        topic: entry.topic,
        accuracy: entry.accuracy
      }))
    };

    saveJson(STORAGE_KEYS.config, config);
    window.location.href = buildVersionedPageUrl("./quiz.html");
  });

  changeExamButton?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    closeProfileMenu();
    window.location.href = "./exam-select.html";
  });

  logoutButton?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    closeProfileMenu();
    localStorage.removeItem(STORAGE_KEYS.currentUser);
    window.location.href = "./login.html";
  });

  mockButton?.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();

    if (Date.now() - finalMockDifficultyInteractionAt < 600) {
      return;
    }

    const config = {
      exam: sanitizeExamName(examSelect?.value || currentUser.preferredExam || "RRB NTPC"),
      stage: stageSelect?.value || profile.preferredStage || currentUser.preferredStage || "",
      branch: branchSelect?.value || profile.preferredBranch || currentUser.preferredBranch || "",
      subject: "Full Syllabus",
      topic: "Full Pattern Mock",
      count: 0,
      mode: "final-mock",
      difficulty: finalMockDifficultySelect?.value || difficultySelect?.value || "intermediate"
    };

    saveJson(STORAGE_KEYS.config, config);
    window.location.href = buildVersionedPageUrl("./quiz.html");
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const formData = new FormData(form);
    const selectedMode = String(formData.get("mode") || "subject-test");
    const practiceType = "subject-test";
    const currentExamName = sanitizeExamName(String(formData.get("exam") || "RRB NTPC"));
    const currentStageValue = String(formData.get("stage") || stageSelect?.value || "");
    const currentBranchValue = String(formData.get("branch") || branchSelect?.value || "");
    const currentSubjectValue = String(formData.get("subject") || "Mathematics");
    const selectedChapters = Array.from(chapterList?.querySelectorAll('input[type="checkbox"]:checked') || []).map((input) => input.value);
    const subjectTopics = getActiveSubjectTopics(currentExamName, currentStageValue, currentBranchValue, currentSubjectValue);
    const chapterQuestionMode = String(formData.get("chapterQuestionMode") || "full-subject-mix");
    const smartMixWeakestChapter = practiceType === "chapter-practice" && chapterQuestionMode === "selected-chapters-only" && selectedChapters.length >= 2
      ? selectedChapters
          .map((topic) => {
            const accuracyEntry = buildTopicAccuracyMap(currentExamName, currentStageValue, currentBranchValue).get(`${resolveSubjectKey(currentExamName, currentStageValue, currentSubjectValue, currentBranchValue)}__${topic}`);
            const accuracy = accuracyEntry?.total ? Math.round((accuracyEntry.correct / accuracyEntry.total) * 100) : 0;
            return { topic, accuracy };
          })
          .sort((left, right) => left.accuracy - right.accuracy)[0]?.topic || ""
      : "";

    if (practiceType === "chapter-practice" && !selectedChapters.length) {
      window.alert("Please select at least one chapter for Chapter Practice.");
      return;
    }

    let topicLabel = String(formData.get("topic") || "All Topics");
    if (practiceType === "chapter-practice") {
      topicLabel = chapterQuestionMode === "full-subject-mix"
        ? "Full Subject Mix"
        : chapterQuestionMode === "balanced-sampler"
          ? "Balanced Sampler"
          : `${selectedChapters.length} Selected Chapters`;
    }

    const config = {
      exam: currentExamName,
      stage: currentStageValue,
      branch: currentBranchValue,
      subject: selectedMode === "final-mock" ? "Full Syllabus" : String(formData.get("subject") || "Mathematics"),
      topic: selectedMode === "final-mock" ? "Full Pattern Mock" : topicLabel,
      count: practiceType === "chapter-practice"
        ? selectedChapters.length * 5
        : Number(formData.get("count") || 10),
      mode: selectedMode,
      difficulty: String(formData.get("difficulty") || "intermediate"),
      practiceType,
      selectedChapters,
      subjectTopics,
      chapterQuestionMode,
      smartMixWeakestChapter
    };

    saveJson(STORAGE_KEYS.profile, {
      ...readJson(STORAGE_KEYS.profile, {}),
      preferredExam: currentExamName,
      preferredStage: currentStageValue,
      preferredBranch: currentBranchValue,
      practiceType,
      lastSubject: currentSubjectValue,
      lastTopic: topicSelect?.value || "",
      selectedChapters
    });

    saveJson(STORAGE_KEYS.config, config);
    window.location.href = buildVersionedPageUrl("./quiz.html");
  });
}

function setupLoginPage() {
  const authForm = document.querySelector("#auth-form");
  if (!authForm) {
    return;
  }

  const authName = document.querySelector("#auth-name");
  const authEmail = document.querySelector("#auth-email");
  const authPassword = document.querySelector("#auth-password");
  const authMessage = document.querySelector("#auth-message");
  const signinTab = document.querySelector("#signin-tab");
  const signupTab = document.querySelector("#signup-tab");
  const nameField = document.querySelector("#name-field");
  let authMode = "signin";

  const setAuthMode = (mode) => {
    authMode = mode;
    const isSignup = mode === "signup";
    nameField?.classList.toggle("hidden", !isSignup);
    signinTab?.classList.toggle("active", !isSignup);
    signupTab?.classList.toggle("active", isSignup);
    signinTab?.classList.toggle("text-on-surface-variant", isSignup);
    signupTab?.classList.toggle("text-on-surface-variant", !isSignup);
    if (authMessage) {
      authMessage.textContent = "";
    }
  };

  signinTab?.addEventListener("click", () => setAuthMode("signin"));
  signupTab?.addEventListener("click", () => setAuthMode("signup"));
  setAuthMode("signin");

  const completeLogin = (user) => {
    saveJson(STORAGE_KEYS.currentUser, user);
    saveJson(STORAGE_KEYS.profile, {
      name: user.name || "",
      preferredExam: user.preferredExam || ""
    });
    window.location.href = "./exam-select.html";
  };

  authForm.addEventListener("submit", (event) => {
    event.preventDefault();

    if (authMode === "signup") {
      const users = readJson(STORAGE_KEYS.authUsers, []);
      const name = authName?.value.trim() || "Learner";
      const email = authEmail?.value.trim().toLowerCase() || "";
      const password = authPassword?.value || "";

      if (!authName?.value.trim() || !email || password.length < 4) {
        authMessage.textContent = "Name, email and password (min 4 chars) required.";
        return;
      }

      if (users.some((user) => user.email === email)) {
        authMessage.textContent = "Account already exists. Please sign in.";
        return;
      }

      const newUser = { name, email, password, preferredExam: "" };
      saveJson(STORAGE_KEYS.authUsers, [newUser, ...users]);
      authMessage.textContent = "Account created. Redirecting...";
      completeLogin(newUser);
      return;
    }

    const users = readJson(STORAGE_KEYS.authUsers, []);
    const email = authEmail?.value.trim().toLowerCase() || "";
    const password = authPassword?.value || "";
    const user = users.find((entry) => entry.email === email && entry.password === password);

    if (!email || password.length < 4) {
      authMessage.textContent = "Email and password (min 4 chars) required.";
      return;
    }

    if (user) {
      authMessage.textContent = "Signed in successfully. Redirecting...";
      completeLogin(user);
      return;
    }

    const existingUserForEmail = users.find((entry) => entry.email === email);
    if (existingUserForEmail) {
      authMessage.textContent = "Invalid email or password.";
      return;
    }

    const demoUser = {
      name: authName?.value.trim() || "Learner",
      email,
      password,
      preferredExam: ""
    };
    saveJson(STORAGE_KEYS.authUsers, [demoUser, ...users]);
    authMessage.textContent = "Demo access created. Redirecting...";
    completeLogin(demoUser);
  });
}

setupThemeToggle();
setupLoginPage();
setupExamSelectPage();
setupHomePage();
setupUtilityPage();

export {
  STORAGE_KEYS,
  getExamSpecificKey,
  getCurrentExam,
  SUBJECT_TOPICS,
  renderAnalytics,
  renderBookmarks,
  renderHistory,
  renderWrongQuestions,
  renderLastAttemptCard,
  renderFinalMockHistory,
  renderExamDashboard
};




