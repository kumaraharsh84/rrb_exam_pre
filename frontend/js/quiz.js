import { generateQuestions, getExplanation } from "./api.js?v=20260513c";
import { STORAGE_KEYS, getExamSpecificKey, getCurrentExam, readJson, saveJson, pruneHistoryRecords, pruneSavedPapers, setupThemeToggle, applyTheme, escapeHtml } from "./app.js?v=20260513c";
import { getExamPattern, ACTIVE_EXAMS, sanitizeActiveExam } from "./exam-patterns.js?v=20260513c";

const MODE_LABELS = {
  practice: "Practice",
  mock: "Mock Test Without Timer",
  "previous-year": "Previous Year",
  "final-mock": "Final Mock"
};

const PRACTICE_TYPE_LABELS = {
  "topic-practice": "Topic Practice",
  "chapter-practice": "Chapter Practice",
  "weak-drill": "Weak Topic Drill"
};

const DIFFICULTY_LABELS = {
  basic: "Basic",
  intermediate: "Intermediate",
  advanced: "Advanced"
};

function createCustomQuestionSetConfig({
  exam,
  stage = "",
  branch = "",
  subject = "Wrong Questions",
  topic = "Wrong Question Retry",
  difficulty = "intermediate",
  questions = []
}) {
  return {
    exam: sanitizeActiveExam(exam),
    stage,
    branch,
    subject,
    topic,
    count: questions.length,
    mode: "practice",
    difficulty,
    customQuestionSet: true,
    customQuestionSource: "wrong-questions"
  };
}

function toReplayQuestion(entry) {
  return {
    q: entry.question,
    opts: entry.options,
    ans: entry.correctIndex,
    exp: entry.explanation || "No explanation provided."
  };
}

function getSectionInsight(accuracy) {
  if (accuracy >= 75) {
    return {
      label: "Strong",
      className: "insight-strong",
      focus: "Maintain your revision and speed."
    };
  }

  if (accuracy >= 50) {
    return {
      label: "Improving",
      className: "insight-improving",
      focus: "Focus on both mixed practice and accuracy."
    };
  }

  return {
    label: "Needs Work",
    className: "insight-weak",
    focus: "Revise the basics again and practice step-by-step."
  };
}


function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = "quiz-toast";
  toast.style.position = "fixed";
  toast.style.top = "24px";
  toast.style.left = "50%";
  toast.style.transform = "translateX(-50%) translateY(-20px)";
  toast.style.opacity = "0";
  toast.style.zIndex = "9999";
  toast.style.backgroundColor = type === "success" ? "var(--primary)" : "#0f766e"; // Teal for info/success
  toast.style.color = "#ffffff";
  toast.style.padding = "12px 24px";
  toast.style.borderRadius = "12px";
  toast.style.boxShadow = "0 8px 30px rgba(0, 0, 0, 0.15)";
  toast.style.fontWeight = "bold";
  toast.style.fontSize = "14px";
  toast.style.transition = "transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease";
  toast.style.pointerEvents = "none";
  toast.style.display = "flex";
  toast.style.alignItems = "center";
  toast.style.gap = "8px";
  
  const icon = document.createElement("span");
  icon.className = "material-symbols-outlined";
  icon.style.fontSize = "18px";
  icon.textContent = type === "success" ? "check_circle" : "info";
  
  const text = document.createElement("span");
  text.textContent = message;
  
  toast.append(icon, text);
  document.body.append(toast);
  
  // Force reflow
  toast.offsetHeight;
  
  // Transition in
  toast.style.transform = "translateX(-50%) translateY(0)";
  toast.style.opacity = "1";
  
  window.setTimeout(() => {
    // Transition out
    toast.style.transform = "translateX(-50%) translateY(-20px)";
    toast.style.opacity = "0";
    window.setTimeout(() => {
      toast.remove();
    }, 300);
  }, 4000);
}

function buildExplanationPayload(question, index, attempt = {}) {
  const metadata = question.meta || {};
  const subject = question.sectionSubject || question.section || metadata.subject || attempt.subject || "General";
  const topic = metadata.topic || attempt.topic || "General";
  const questionId = metadata.id
    || metadata.sourceMetadata?.source_id
    || `${metadata.exam || attempt.exam || "rrb"}-${subject}-${index + 1}-${createQuestionPatternSignature(question.q).slice(0, 40)}`;

  return {
    questionId,
    question: question.q,
    options: question.opts,
    answer: question.ans,
    correctAnswer: question.opts?.[question.ans] || "",
    subject,
    topic,
    difficulty: metadata.difficulty || attempt.difficulty || "medium",
    exam: metadata.exam || attempt.exam || "RRB NTPC",
    source: metadata.source || "",
    sourceMetadata: metadata.sourceMetadata || null
  };
}

function renderExplanationBox(box, response, payload) {
  const cacheLabel = response.cached ? "Loaded from saved explanation cache" : "Generated now and saved for next time";
  box.classList.remove("hidden");
  box.classList.remove("solution-animation");
  void box.offsetHeight; // trigger reflow
  box.classList.add("solution-animation");
  box.innerHTML = `
    <div class="mt-4 rounded-lg border border-surface-variant bg-surface-container p-4">
      <div class="mb-3 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
        <span>${escapeHtml(cacheLabel)}</span>
        <span>Topic: ${escapeHtml(response.topic || payload.topic || "General")}</span>
        <span>Difficulty: ${escapeHtml(payload.difficulty || "medium")}</span>
      </div>
      <div style="margin-top: 8px; line-height: 1.6; white-space: pre-wrap;"><strong>Explanation:</strong>\n${escapeHtml(response.explanation || "No explanation returned.")}</div>
    </div>
  `;
}

function getQuestionState(answer, reviewMarked) {
  if (answer !== null && reviewMarked) {
    return "review-answered";
  }
  if (reviewMarked) {
    return "review";
  }
  if (answer !== null) {
    return "answered";
  }
  return "unanswered";
}

function getStateLabel(state) {
  if (state === "answered") {
    return "Answered";
  }
  if (state === "review") {
    return "Review";
  }
  if (state === "review-answered") {
    return "Answered + Review";
  }
  return "Not Answered";
}

function getCurrentSelectedOption(container) {
  const selected = container?.querySelector('input[name="answer"]:checked');
  return selected ? Number(selected.value) : null;
}

function createPaperId() {
  return `paper-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createQuestionPatternSignature(questionText = "") {
  return String(questionText)
    .toLowerCase()
    .replace(/\d+(?:\.\d+)?/g, "<n>")
    .replace(/\b(rs|rupees|km|hours|hour|minutes|minute|days|day|percent|percentage)\b/g, "<u>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 180);
}

function getQuestionPatternKey(question = {}) {
  const basePattern = createQuestionPatternSignature(question.q);
  if (question?.meta?.source === "local-fallback") {
    return `${basePattern}::fallback::${question.meta.fallbackId || "x"}`;
  }
  return basePattern;
}

async function generateSectionQuestionsInBatches({
  subject,
  topic,
  count,
  mode,
  exam,
  stage = "",
  branch = "",
  difficulty,
  recentQuestions,
  recentPatterns,
  practiceType = "topic-practice",
  selectedChapters = [],
  chapterQuestionMode = "",
  drillTopics = [],
  onStatus = null,
  forceDb = false,
  forceAi = false,
  signal = null
}) {
  const batchSize = forceAi ? 5 : (mode === "final-mock" ? 12 : count);
  const collectedQuestions = [];
  const collectedPatterns = [];
  let noProgressRounds = 0;

  while (collectedQuestions.length < count) {
    const remaining = count - collectedQuestions.length;
    const currentBatchCount = Math.min(batchSize, remaining);
    const generatedBatch = await generateQuestions(
      subject,
      topic,
      currentBatchCount,
      mode,
      [
        ...recentQuestions,
        ...collectedQuestions.map((question) => question.q)
      ],
      exam,
      difficulty,
      [
        ...recentPatterns,
        ...collectedPatterns
      ],
      {
        stage,
        branch,
        practiceType,
        selectedChapters,
        chapterQuestionMode,
        drillTopics,
        onStatus,
        forceDb,
        forceAi,
        signal
      }
    );

    if (!generatedBatch.length) {
      break;
    }

    let acceptedInRound = 0;
    for (const question of generatedBatch) {
      if (collectedQuestions.length >= count) {
        break;
      }

      const alreadyExists = collectedQuestions.some((entry) => entry.q === question.q);
      const pattern = getQuestionPatternKey(question);
      const patternExists = collectedPatterns.includes(pattern);

      if (alreadyExists || patternExists) {
        continue;
      }

      collectedQuestions.push(question);
      collectedPatterns.push(pattern);
      acceptedInRound += 1;
    }

    if (acceptedInRound === 0) {
      noProgressRounds += 1;
    } else {
      noProgressRounds = 0;
    }

    if (noProgressRounds >= 2) {
      break;
    }

    if (generatedBatch.length < currentBatchCount && acceptedInRound === 0) {
      break;
    }
  }

  return collectedQuestions.slice(0, count);
}

function distributeCounts(totalCount, topics, chapterQuestionMode) {
  if (!topics.length || totalCount <= 0) {
    return [];
  }

  if (chapterQuestionMode === "balanced-sampler") {
    const remainingTopics = [...topics];
    const counts = new Map(topics.map((topic) => [topic, 0]));
    let assigned = 0;

    while (assigned < totalCount) {
      let progress = false;
      for (const topic of remainingTopics) {
        const current = counts.get(topic) || 0;
        const maxPerTopic = totalCount >= topics.length * 2 ? 2 : 1;
        if (current >= maxPerTopic) {
          continue;
        }
        counts.set(topic, current + 1);
        assigned += 1;
        progress = true;
        if (assigned >= totalCount) {
          break;
        }
      }

      if (!progress) {
        const fallbackTopic = topics[(assigned - 1 + topics.length) % topics.length];
        counts.set(fallbackTopic, (counts.get(fallbackTopic) || 0) + 1);
        assigned += 1;
      }
    }

    return topics
      .map((topic) => ({ topic, count: counts.get(topic) || 0 }))
      .filter((entry) => entry.count > 0);
  }

  const baseCount = Math.floor(totalCount / topics.length);
  let remainder = totalCount % topics.length;

  return topics.map((topic) => {
    const count = baseCount + (remainder > 0 ? 1 : 0);
    remainder = Math.max(remainder - 1, 0);
    return { topic, count };
  }).filter((entry) => entry.count > 0);
}

async function generateChapterPracticeQuestions({
  subject,
  topics,
  count,
  mode,
  exam,
  stage = "",
  branch = "",
  difficulty,
  recentQuestions,
  recentPatterns,
  chapterQuestionMode,
  smartMixWeakestChapter = "",
  onStatus = null,
  forceDb = false,
  forceAi = false
}) {
  const selectedTopics = Array.from(new Set((topics || []).filter(Boolean)));
  let topicPlan = distributeCounts(count, selectedTopics, chapterQuestionMode);

  if (chapterQuestionMode === "selected-chapters-only" && selectedTopics.length >= 2 && smartMixWeakestChapter) {
    const weakestCount = Math.max(1, Math.ceil(count * 0.6));
    const remainingCount = Math.max(count - weakestCount, 0);
    const otherTopics = selectedTopics.filter((topic) => topic !== smartMixWeakestChapter);
    const otherPlan = distributeCounts(remainingCount, otherTopics, "selected-chapters-only");
    topicPlan = [
      { topic: smartMixWeakestChapter, count: weakestCount },
      ...otherPlan
    ];
  }

  const collectedQuestions = [];
  const collectedPatterns = [];

  for (const entry of topicPlan) {
    const generatedBatch = await generateSectionQuestionsInBatches({
      subject,
      topic: entry.topic,
      count: entry.count,
      mode,
      exam,
      stage,
      branch,
      difficulty,
      recentQuestions: [
        ...recentQuestions,
        ...collectedQuestions.map((question) => question.q)
      ],
      recentPatterns: [
        ...recentPatterns,
        ...collectedPatterns
      ],
      practiceType: "chapter-practice",
      selectedChapters: selectedTopics,
      chapterQuestionMode,
      onStatus,
      forceDb,
      forceAi
    });

    for (const question of generatedBatch) {
      if (collectedQuestions.length >= count) {
        break;
      }

      const pattern = getQuestionPatternKey(question);
      if (collectedPatterns.includes(pattern)) {
        continue;
      }

      collectedQuestions.push({
        ...question,
        section: entry.topic,
        sectionSubject: subject
      });
      collectedPatterns.push(pattern);
    }
  }

  return collectedQuestions.slice(0, count);
}

async function generateWeakDrillQuestions({
  targets,
  count,
  mode,
  exam,
  stage = "",
  branch = "",
  difficulty,
  recentQuestions,
  recentPatterns,
  onStatus = null,
  forceDb = false,
  forceAi = false
}) {
  const selectedTargets = Array.from(new Map((targets || [])
    .filter((target) => target?.subject && target?.topic)
    .map((target) => [`${target.subject}__${target.topic}`, target]))
    .values());

  const plan = distributeCounts(count, selectedTargets.map((target) => `${target.subject}__${target.topic}`), "selected-chapters-only");
  const collectedQuestions = [];
  const collectedPatterns = [];

  for (const entry of plan) {
    const target = selectedTargets.find((item) => `${item.subject}__${item.topic}` === entry.topic);
    if (!target) {
      continue;
    }

    const generatedBatch = await generateSectionQuestionsInBatches({
      subject: target.subject,
      topic: target.topic,
      count: entry.count,
      mode,
      exam,
      stage,
      branch,
      difficulty,
      recentQuestions: [
        ...recentQuestions,
        ...collectedQuestions.map((question) => question.q)
      ],
      recentPatterns: [
        ...recentPatterns,
        ...collectedPatterns
      ],
      practiceType: "weak-drill",
      drillTopics: selectedTargets,
      onStatus,
      forceDb,
      forceAi
    });

    for (const question of generatedBatch) {
      if (collectedQuestions.length >= count) {
        break;
      }

      const pattern = getQuestionPatternKey(question);
      if (collectedPatterns.includes(pattern)) {
        continue;
      }

      collectedQuestions.push({
        ...question,
        section: target.subject,
        sectionSubject: target.subject
      });
      collectedPatterns.push(pattern);
    }
  }

  return collectedQuestions.slice(0, count);
}

async function setupQuizPage() {
  const quizRoot = document.querySelector("#quiz-form");
  if (!quizRoot) {
    return;
  }
  const backgroundFetchController = new AbortController();
  const currentUser = readJson(STORAGE_KEYS.currentUser);
  if (!currentUser) {
    window.location.href = "./login.html";
    return;
  }

  const config = readJson(STORAGE_KEYS.config);
  if (!config) {
    window.location.href = "./dashboard.html";
    return;
  }

  const loadingState = document.querySelector("#loading-state");
  const errorState = document.querySelector("#error-state");
  const errorMessage = document.querySelector("#error-message");
  const loadingMessage = loadingState?.querySelector("span");
  const heading = document.querySelector("#quiz-heading");
  const progressPill = document.querySelector("#progress-pill");
  const modePill = document.querySelector("#mode-pill");
  const difficultyPill = document.querySelector("#difficulty-pill");
  const timerPill = document.querySelector("#timer-pill");
  const questionIndex = document.querySelector("#question-index");
  const questionText = document.querySelector("#question-text");
  const optionsList = document.querySelector("#options-list");
  const answerFeedback = document.querySelector("#answer-feedback");
  const answerFeedbackStatus = document.querySelector("#answer-feedback-status");
  const answerFeedbackText = document.querySelector("#answer-feedback-text");
  const bookmarkButton = document.querySelector("#bookmark-button");
  const clearButton = document.querySelector("#clear-button");
  const reviewButton = document.querySelector("#review-button");
  const saveNextButton = document.querySelector("#save-next-button");
  const submitTestButton = document.querySelector("#submit-test-button");
  const questionPalette = document.querySelector("#question-palette");
  const quizSummary = document.querySelector("#quiz-summary");
  const sectionOverview = document.querySelector("#section-overview");
  const sectionOverviewPanel = document.querySelector("#section-overview-panel");
  const sectionJumpPanel = document.querySelector("#section-jump-panel");
  const sectionJumpList = document.querySelector("#section-jump-list");
  const currentSectionTitle = document.querySelector("#current-section-title");
  const modeContextBanner = document.querySelector("#mode-context-banner");
  const modeContextTitle = document.querySelector("#mode-context-title");
  const modeContextBody = document.querySelector("#mode-context-body");
  const tipTitle = document.querySelector("#tip-title");
  const tipBody = document.querySelector("#tip-body");
  const submitModal = document.querySelector("#submit-modal");
  const submitModalEyebrow = document.querySelector("#submit-modal-eyebrow");
  const submitModalTitle = document.querySelector("#submit-modal-title");
  const submitModalCopy = document.querySelector("#submit-modal-copy");
  const submitModalMetrics = document.querySelector("#submit-modal-metrics");
  const submitCancelButton = document.querySelector("#submit-cancel-button");
  const submitConfirmButton = document.querySelector("#submit-confirm-button");
  const submitForceButton = document.querySelector("#submit-force-button");

  const currentExam = sanitizeActiveExam(config.exam || "RRB NTPC");
  const examPattern = getExamPattern(currentExam, config.stage || "", config.branch || "");
  const currentStage = config.stage || "";
  const difficulty = config.difficulty || "intermediate";
  const negativeMarking = Number(examPattern.negativeMarking || (1 / 3));
  const isChapterPractice = config.practiceType === "chapter-practice";

  heading.textContent = config.mode === "final-mock"
    ? `${currentExam}${currentStage ? ` ${currentStage}` : ""} | Final Mock`
    : isChapterPractice
      ? `${config.subject} | ${PRACTICE_TYPE_LABELS[config.practiceType] || "Chapter Practice"}`
      : `${config.subject} | ${config.topic}`;
  modePill.textContent = isChapterPractice
    ? PRACTICE_TYPE_LABELS[config.practiceType] || "Chapter Practice"
    : MODE_LABELS[config.mode] || "Practice";
  difficultyPill.textContent = `${DIFFICULTY_LABELS[difficulty] || "Intermediate"} Level`;
  document.body.classList.toggle("exam-mode", config.mode === "mock" || config.mode === "final-mock");
  document.body.classList.toggle("final-mock-mode", config.mode === "final-mock");
  document.body.classList.toggle("focused-mode", config.mode === "practice" || config.mode === "previous-year");

  if (sectionOverviewPanel) {
    sectionOverviewPanel.classList.toggle("hidden", config.mode !== "final-mock");
  }

  const getTimedQuizSeconds = () => {
    if (config.mode === "mock") {
      return null;
    }

    if (config.mode === "final-mock") {
      return examPattern.timerMinutes * 60;
    }

    const questionCount = Number(config.count || 10);
    return Math.max(questionCount, 1) * 60;
  };

  const initialTimerSeconds = getTimedQuizSeconds();
  const initialTimerMinutes = initialTimerSeconds === null ? null : Math.ceil(initialTimerSeconds / 60);

  if (config.mode === "final-mock") {
    modeContextBanner?.classList.remove("hidden");
    if (modeContextTitle) {
      modeContextTitle.textContent = `${currentExam}${currentStage ? ` ${currentStage}` : ""}${config.branch ? ` - ${config.branch}` : ""} Final Mock`;
    }
    if (modeContextBody) {
      modeContextBody.textContent = `${examPattern.totalQuestions} questions | ${examPattern.timerMinutes} minutes | ${examPattern.sections.map((section) => `${section.label || section.subject} ${section.count}`).join(" | ")}`;
    }
    if (tipTitle) {
      tipTitle.textContent = "Final Mock Strategy";
    }
    if (tipBody) {
      tipBody.textContent = "Maintain section balance, secure easy questions first, and keep checking the timer at regular intervals.";
    }
  } else if (config.mode === "mock") {
    modeContextBanner?.classList.remove("hidden");
    if (modeContextTitle) {
      modeContextTitle.textContent = `${currentExam}${currentStage ? ` ${currentStage}` : ""} Mock Session`;
    }
    if (modeContextBody) {
      modeContextBody.textContent = `${config.count} mixed questions for ${config.subject} without a timer. Use this mode for an exam-style self-check.`;
    }
    if (tipTitle) {
      tipTitle.textContent = "Mock Strategy";
    }
    if (tipBody) {
      tipBody.textContent = "Maintain exam discipline even without a timer. Secure accuracy first, and speed will improve naturally.";
    }
  } else {
    modeContextBanner?.classList.remove("hidden");
    if (isChapterPractice) {
      if (modeContextTitle) {
        modeContextTitle.textContent = `${config.subject} Chapter Practice`;
      }
      if (modeContextBody) {
        modeContextBody.textContent = `${(config.selectedChapters || []).length} chapters selected | ${config.chapterQuestionMode === "full-subject-mix" ? "Full subject mix" : config.chapterQuestionMode === "balanced-sampler" ? "Balanced sampler" : "Selected chapters only"} | ${initialTimerMinutes} min timer`;
      }
    } else if (config.practiceType === "weak-drill") {
      if (modeContextTitle) {
        modeContextTitle.textContent = `${currentExam}${currentStage ? ` ${currentStage}` : ""} Weak Topic Auto-Drill`;
      }
      if (modeContextBody) {
        modeContextBody.textContent = `${(config.drillTopics || []).length} weak topics se 15-question drill generate hua hai | ${initialTimerMinutes} min timer.`;
      }
    } else {
      if (modeContextTitle) {
        modeContextTitle.textContent = config.mode === "previous-year"
          ? `${currentExam}${currentStage ? ` ${currentStage}` : ""} Previous Year Style`
          : `${currentExam}${currentStage ? ` ${currentStage}` : ""} Practice Session`;
      }
      if (modeContextBody) {
        modeContextBody.textContent = `${config.count} questions for ${config.subject} | ${initialTimerMinutes} min timer | ${DIFFICULTY_LABELS[difficulty] || "Intermediate"} level.`;
      }
    }
    if (tipTitle) {
      tipTitle.textContent = config.mode === "previous-year" ? "Previous Year Focus" : isChapterPractice ? "Chapter Practice Tip" : "Practice Tip";
    }
    if (tipBody) {
      tipBody.textContent = config.mode === "previous-year"
        ? "Focus on PYQ framing and patterns. Similar concepts often repeat, so be sure to read the explanations."
        : isChapterPractice
          ? "Practicing a mix of multiple chapters. Compare and improve your weak areas."
          : config.practiceType === "weak-drill"
            ? "Running a quick drill targeting weak topics. Keep your focus on accuracy."
            : "In practice mode, read each question carefully, eliminate options, and solve step-by-step.";
    }
  }

  let timeLeft = initialTimerSeconds;
  let timerId = null;
  let currentIndex = 0;
  const BUILD_TIMEOUT_MS = 70000;

  const setLoadingStatus = (message) => {
    if (loadingMessage && message) {
      loadingMessage.textContent = message;
    }
  };

  const isBookmarked = (questionTextToCheck) => {
    const bookmarksKey = getExamSpecificKey(STORAGE_KEYS.bookmarks, currentExam);
    const bookmarks = readJson(bookmarksKey, []);
    return bookmarks.some((bookmark) => bookmark.q === questionTextToCheck);
  };

  const saveBookmarkEntry = (entry) => {
    const bookmarksKey = getExamSpecificKey(STORAGE_KEYS.bookmarks, entry.exam);
    const bookmarks = readJson(bookmarksKey, []);
    const alreadySaved = bookmarks.some((bookmark) => bookmark.q === entry.q);
    if (alreadySaved) {
      return false;
    }

    saveJson(bookmarksKey, [entry, ...bookmarks].slice(0, 50));
    return true;
  };

  const updateTimer = () => {
    if (timeLeft === null) {
      timerPill.textContent = "No timer";
      return;
    }

    const minutes = String(Math.floor(timeLeft / 60)).padStart(2, "0");
    const seconds = String(timeLeft % 60).padStart(2, "0");
    timerPill.textContent = `${minutes}:${seconds}`;
    timerPill.classList.toggle("timer-warn", timeLeft <= 300 && timeLeft > 60);
    timerPill.classList.toggle("timer-danger", timeLeft <= 60);
  };

  if (progressPill) {
    progressPill.textContent = config.count ? `0 / ${config.count}` : "Preparing";
  }
  if (questionIndex) {
    questionIndex.textContent = "Preparing questions...";
  }
  setLoadingStatus("Loading your test setup...");
  updateTimer();

  const buildSectionIndexMap = (questions) => questions.reduce((accumulator, question, index) => {
    const key = question.section || config.subject;
    if (!accumulator[key]) {
      accumulator[key] = [];
    }
    accumulator[key].push(index);
    return accumulator;
  }, {});

  const finishQuiz = (questions, answers, reviewFlags) => {
    try {
      backgroundFetchController.abort();
    } catch (e) {
      console.warn("Failed to abort background fetch:", e);
    }
    const correctAnswers = answers.reduce((total, answer, index) => total + (answer === questions[index].ans ? 1 : 0), 0);
    const wrongAnswers = answers.reduce((total, answer, index) => total + (answer !== null && answer !== questions[index].ans ? 1 : 0), 0);
    const unansweredAnswers = answers.reduce((total, answer) => total + (answer === null ? 1 : 0), 0);
    const reviewCount = reviewFlags.reduce((total, flag) => total + (flag ? 1 : 0), 0);
    const negativeMarks = Number((wrongAnswers * negativeMarking).toFixed(2));
    const finalScore = Number((correctAnswers - negativeMarks).toFixed(2));

    saveJson(STORAGE_KEYS.answers, answers);
    saveJson(STORAGE_KEYS.results, {
      total: questions.length,
      score: correctAnswers,
      finalScore,
      wrongAnswers,
      unansweredAnswers,
      reviewCount,
      negativeMarks,
      percentage: Math.round((correctAnswers / questions.length) * 100),
      answers,
      mode: config.mode,
      difficulty
    });

    if (timerId) {
      window.clearInterval(timerId);
    }
    window.location.href = "./score.html";
  };

  const closeSubmitModal = () => {
    submitModal?.classList.add("hidden");
  };

  const openSubmitModal = (questions, answers, reviewFlags) => {
    if (!submitModal || !submitModalMetrics) {
      finishQuiz(questions, answers, reviewFlags);
      return;
    }

    const unanswered = answers.filter((answer) => answer === null).length;
    const answered = answers.length - unanswered;
    const reviewCount = reviewFlags.filter(Boolean).length;

    if (submitModalEyebrow) {
      submitModalEyebrow.textContent = config.mode === "final-mock" ? "Final Mock Submission" : "Submission Check";
    }
    if (submitModalTitle) {
      submitModalTitle.textContent = config.mode === "final-mock"
        ? `Submit ${currentExam}${currentStage ? ` ${currentStage}` : ""} Final Mock?`
        : "Submit Test?";
    }

    const hasPlaceholders = questions.some((q) => q.placeholder);

    if (submitModalCopy) {
      submitModalCopy.textContent = hasPlaceholders
        ? "AI Coach is currently generating and setting the exam questions in the background. Please wait a few seconds until the questions are fully loaded before submitting."
        : (unanswered
            ? `You still have ${unanswered} unanswered questions. Once submitted, the test will close and your result will be generated.`
            : "All responses have been reviewed. Once submitted, the result page will open.");
    }

    submitModalMetrics.innerHTML = `
      <article class="modal-metric">
        <strong>${questions.length}</strong>
        <span>Total Questions</span>
      </article>
      <article class="modal-metric">
        <strong>${answered}</strong>
        <span>Answered</span>
      </article>
      <article class="modal-metric">
        <strong>${unanswered}</strong>
        <span>Unanswered</span>
      </article>
      <article class="modal-metric">
        <strong>${reviewCount}</strong>
        <span>Marked for Review</span>
      </article>
    `;

    submitModal.classList.remove("hidden");

    submitCancelButton.onclick = () => closeSubmitModal();

    if (hasPlaceholders) {
      if (submitConfirmButton) {
        submitConfirmButton.disabled = true;
        submitConfirmButton.style.opacity = "0.5";
        submitConfirmButton.style.cursor = "not-allowed";
        submitConfirmButton.textContent = "Please Wait...";
        submitConfirmButton.onclick = null;
      }
      if (submitForceButton) {
        submitForceButton.classList.remove("hidden");
        submitForceButton.onclick = () => {
          closeSubmitModal();
          finishQuiz(questions, answers, reviewFlags);
        };
      }
    } else {
      if (submitConfirmButton) {
        submitConfirmButton.disabled = false;
        submitConfirmButton.style.opacity = "";
        submitConfirmButton.style.cursor = "";
        submitConfirmButton.textContent = "Submit Now";
      }
      submitConfirmButton.onclick = () => {
        closeSubmitModal();
        finishQuiz(questions, answers, reviewFlags);
      };
      if (submitForceButton) {
        submitForceButton.classList.add("hidden");
        submitForceButton.onclick = null;
      }
    }
  };

  try {
    setLoadingStatus("Reading saved test settings...");
    const recentQuestionsKey = getExamSpecificKey(STORAGE_KEYS.recentQuestions, currentExam);
    const recentPatternsKey = getExamSpecificKey(STORAGE_KEYS.recentPatterns, currentExam);
    const recentQuestions = readJson(recentQuestionsKey, []);
    const recentPatterns = readJson(recentPatternsKey, []);
    const buildQuestions = async () => {
      if (config.customQuestionSet) {
        const customQuestions = readJson(STORAGE_KEYS.replayQuestions, []);
        if (customQuestions.length) {
          localStorage.removeItem(STORAGE_KEYS.replayQuestions);
          return {
            paperId: createPaperId(),
            questions: customQuestions
          };
        }
      }

      if (config.paperId && config.useSavedPaper) {
        const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
        const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
        saveJson(savedPapersKey, savedPapers);
        const savedPaper = savedPapers.find((paper) => paper.id === config.paperId);
        if (savedPaper?.questions?.length) {
          return {
            paperId: savedPaper.id,
            questions: savedPaper.questions
          };
        }
      }

      if (config.mode !== "final-mock") {
        const totalCount = Number(config.count || 10);
        const db_count = Math.ceil(totalCount / 2);

        const scopedRecentQuestions = recentQuestions
          .filter((entry) => entry.subject === config.subject && (entry.exam || currentExam) === currentExam)
          .map((entry) => entry.q)
          .slice(0, 20);
        const scopedRecentPatterns = recentPatterns
          .filter((entry) => entry.subject === config.subject && (entry.exam || currentExam) === currentExam)
          .map((entry) => entry.pattern)
          .slice(0, 25);

        const dbQuestions = isChapterPractice
          ? await generateChapterPracticeQuestions({
              subject: config.subject,
              topics: config.chapterQuestionMode === "full-subject-mix"
                ? (config.subjectTopics || [])
                : (config.selectedChapters || []),
              count: db_count,
              mode: config.mode,
              exam: currentExam,
              stage: currentStage,
              branch: config.branch || "",
              difficulty,
              recentQuestions: scopedRecentQuestions,
              recentPatterns: scopedRecentPatterns,
              chapterQuestionMode: config.chapterQuestionMode || "full-subject-mix",
              smartMixWeakestChapter: config.smartMixWeakestChapter || "",
              onStatus: setLoadingStatus,
              forceDb: true
            })
          : config.practiceType === "weak-drill"
            ? await generateWeakDrillQuestions({
                targets: config.drillTopics || [],
                count: db_count,
                mode: config.mode,
                exam: currentExam,
                stage: currentStage,
                branch: config.branch || "",
                difficulty,
                recentQuestions: scopedRecentQuestions,
                recentPatterns: scopedRecentPatterns,
                onStatus: setLoadingStatus,
                forceDb: true
              })
            : await generateSectionQuestionsInBatches({
                subject: config.subject,
                topic: config.topic,
                count: db_count,
                mode: config.mode,
                exam: currentExam,
                stage: currentStage,
                branch: config.branch || "",
                difficulty,
                recentQuestions: scopedRecentQuestions,
                recentPatterns: scopedRecentPatterns,
                practiceType: config.practiceType || "topic-practice",
                onStatus: setLoadingStatus,
                forceDb: true
            });

        const finalQuestions = [...dbQuestions];
        const loadedDbCount = dbQuestions.length;
        const remainingAiCount = Math.max(totalCount - loadedDbCount, 0);

        for (let i = 0; i < remainingAiCount; i++) {
          finalQuestions.push({
            placeholder: true,
            q: "Generating unique exam questions via RRB AI Coach...",
            opts: ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
            ans: 0,
            section: "",
            sectionSubject: config.subject
          });
        }

        return {
          paperId: createPaperId(),
          questions: finalQuestions
        };
      }

      const sectionQuestions = [];
      for (const section of examPattern.sections) {
        const db_count = Math.ceil(section.count / 2);

        const scopedRecentQuestions = recentQuestions
          .filter((entry) => (entry.exam || currentExam) === currentExam && entry.subject === section.subject)
          .map((entry) => entry.q)
          .slice(0, 35);
        const scopedRecentPatterns = recentPatterns
          .filter((entry) => (entry.exam || currentExam) === currentExam && entry.subject === section.subject)
          .map((entry) => entry.pattern)
          .slice(0, 35);

        const dbQuestions = await generateSectionQuestionsInBatches({
          subject: section.subject,
          topic: section.topic,
          count: db_count,
          mode: "final-mock",
          exam: currentExam,
          stage: currentStage,
          branch: config.branch || "",
          difficulty,
          recentQuestions: scopedRecentQuestions,
          recentPatterns: scopedRecentPatterns,
          onStatus: setLoadingStatus,
          forceDb: true
        });

        sectionQuestions.push(...dbQuestions.map((question) => ({
          ...question,
          section: section.label || section.subject,
          sectionSubject: section.subject
        })));

        const loadedDbCount = dbQuestions.length;
        const remainingAiCount = Math.max(section.count - loadedDbCount, 0);

        for (let i = 0; i < remainingAiCount; i++) {
          sectionQuestions.push({
            placeholder: true,
            q: "Generating unique exam questions via RRB AI Coach...",
            opts: ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
            ans: 0,
            section: section.label || section.subject,
            sectionSubject: section.subject
          });
        }
      }

      const finalSectionQuestions = [];
      for (const section of examPattern.sections) {
        const key = section.label || section.subject;
        const currentQuestions = sectionQuestions.filter((q) => q.section === key);

        if (currentQuestions.length < section.count) {
          const needed = section.count - currentQuestions.length;
          for (let i = 0; i < needed; i++) {
            currentQuestions.push({
              placeholder: true,
              q: "Generating unique exam questions via RRB AI Coach...",
              opts: ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
              ans: 0,
              section: key,
              sectionSubject: section.subject
            });
          }
        } else if (currentQuestions.length > section.count) {
          currentQuestions.splice(section.count);
        }

        finalSectionQuestions.push(...currentQuestions);
      }

      return {
        paperId: createPaperId(),
        questions: finalSectionQuestions
      };
    };

    setLoadingStatus("Preparing question batches...");
    const paperBundle = await Promise.race([
      buildQuestions(),
      new Promise((_, reject) => {
        window.setTimeout(() => {
          reject(new Error("Question loading took too long. Please retry once."));
        }, BUILD_TIMEOUT_MS);
      })
    ]);
    const paperId = paperBundle.paperId;
    const questions = paperBundle.questions;

    if (!questions.length) {
      throw new Error("Questions could not be generated for this test. Please try another topic or retry once.");
    }

    const answers = Array(questions.length).fill(null);
    const reviewFlags = Array(questions.length).fill(false);
    const sectionIndexMap = buildSectionIndexMap(questions);

    const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
    const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
    const existingPaperIndex = savedPapers.findIndex((paper) => paper.id === paperId);
    const paperRecord = {
      id: paperId,
      createdAt: new Date().toISOString(),
      config: {
        exam: currentExam,
        stage: currentStage,
        subject: config.subject,
        topic: config.topic,
        count: config.count,
        mode: config.mode,
        difficulty,
        practiceType: config.practiceType || "topic-practice",
        selectedChapters: config.selectedChapters || [],
        subjectTopics: config.subjectTopics || [],
        chapterQuestionMode: config.chapterQuestionMode || "",
        smartMixWeakestChapter: config.smartMixWeakestChapter || "",
        drillTopics: config.drillTopics || []
      },
      questions
    };
    const nextSavedPapers = existingPaperIndex >= 0
      ? savedPapers.map((paper, index) => index === existingPaperIndex ? { ...paper, ...paperRecord, createdAt: paper.createdAt || paperRecord.createdAt } : paper)
      : [paperRecord, ...savedPapers];
    saveJson(savedPapersKey, nextSavedPapers.slice(0, 80));
    saveJson(STORAGE_KEYS.config, { ...config, paperId });

    saveJson(STORAGE_KEYS.questions, questions);
    saveJson(STORAGE_KEYS.answers, answers);
    setLoadingStatus("Rendering questions on screen...");

    const saveCurrentSelection = () => {
      answers[currentIndex] = getCurrentSelectedOption(optionsList);
      saveJson(STORAGE_KEYS.answers, answers);
    };

    const renderPalette = () => {
      if (!questionPalette) {
        return;
      }

      questionPalette.innerHTML = questions.map((question, index) => {
        const state = getQuestionState(answers[index], reviewFlags[index]);
        const activeClass = index === currentIndex ? "active" : "";
        const sectionCode = (question.section || question.subject || "").slice(0, 2).toUpperCase();
        return `
          <button class="palette-btn ${state} ${activeClass}" type="button" data-palette-index="${index}" title="${getStateLabel(state)}">
            <span>${index + 1}</span>
            <small>${escapeHtml(sectionCode || "Q")}</small>
          </button>
        `;
      }).join("");

      questionPalette.querySelectorAll("[data-palette-index]").forEach((button) => {
        button.addEventListener("click", () => {
          saveCurrentSelection();
          currentIndex = Number(button.dataset.paletteIndex);
          renderQuestion();
        });
      });

      updatePaletteStatus();
    };

    const updatePaletteStatus = () => {
      const statusElement = document.querySelector("#palette-status");
      if (!statusElement) {
        return;
      }

      const answeredCount = answers.filter((answer) => answer !== null).length;
      const reviewCount = reviewFlags.filter(Boolean).length;
      statusElement.textContent = `${answeredCount} answered • ${reviewCount} review`;
    };

    const renderSummary = () => {
      if (!quizSummary) {
        return;
      }

      const counts = {
        answered: 0,
        unanswered: 0,
        review: 0,
        reviewAnswered: 0
      };

      answers.forEach((answer, index) => {
        const state = getQuestionState(answer, reviewFlags[index]);
        if (state === "answered") {
          counts.answered += 1;
        } else if (state === "review") {
          counts.review += 1;
        } else if (state === "review-answered") {
          counts.reviewAnswered += 1;
        } else {
          counts.unanswered += 1;
        }
      });

      quizSummary.innerHTML = `
        <article class="summary-box"><strong>${counts.answered}</strong><span>Answered</span></article>
        <article class="summary-box"><strong>${counts.unanswered}</strong><span>Not Answered</span></article>
        <article class="summary-box"><strong>${counts.review}</strong><span>Review</span></article>
        <article class="summary-box"><strong>${counts.reviewAnswered}</strong><span>Answered + Review</span></article>
      `;
    };

    const renderSections = () => {
      if (!sectionOverview || config.mode !== "final-mock") {
        return;
      }

      const sections = questions.reduce((accumulator, question, index) => {
        const key = question.section || config.subject;
        const current = accumulator[key] || { total: 0, answered: 0 };
        current.total += 1;
        if (answers[index] !== null) {
          current.answered += 1;
        }
        accumulator[key] = current;
        return accumulator;
      }, {});

      sectionOverview.innerHTML = Object.entries(sections).map(([section, stats]) => `
        <article class="section-pill">
          <strong>${section}</strong>
          <span>${stats.answered}/${stats.total} answered</span>
        </article>
      `).join("");
    };

    const renderSectionJump = () => {
      if (!sectionJumpPanel || !sectionJumpList || config.mode !== "final-mock") {
        return;
      }

      sectionJumpPanel.classList.remove("hidden");
      const currentSection = questions[currentIndex]?.section || "Current Section";
      if (currentSectionTitle) {
        currentSectionTitle.textContent = currentSection;
      }

      sectionJumpList.innerHTML = Object.entries(sectionIndexMap).map(([section, indexes]) => {
        const answered = indexes.filter((index) => answers[index] !== null).length;
        const activeClass = section === currentSection ? "active" : "";
        return `
          <button class="section-jump-btn ${activeClass}" type="button" data-section-start="${indexes[0]}">
            <strong>${section}</strong>
            <span>${answered}/${indexes.length} answered</span>
          </button>
        `;
      }).join("");

      sectionJumpList.querySelectorAll("[data-section-start]").forEach((button) => {
        button.addEventListener("click", () => {
          saveCurrentSelection();
          currentIndex = Number(button.dataset.sectionStart);
          renderQuestion();
        });
      });
    };

    const renderQuestion = () => {
      const currentQuestion = questions[currentIndex];
      const selectedAnswer = answers[currentIndex];
      const isAnswered = selectedAnswer !== null;
      progressPill.textContent = `${currentIndex + 1} / ${questions.length}`;
      questionIndex.textContent = `Question ${currentIndex + 1} | ${getStateLabel(getQuestionState(answers[currentIndex], reviewFlags[currentIndex]))}`;
      
      if (currentQuestion.placeholder) {
        questionText.innerHTML = `
          <div class="flex flex-col items-center justify-center p-8 text-center" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px; text-align: center;">
            <div class="spinner" style="width: 48px; height: 48px; border: 4px solid rgba(216, 111, 69, 0.18); border-top-color: var(--accent); border-radius: 50%; margin: 0 auto 16px; animation: spin 1s linear infinite;"></div>
            <h3 class="text-lg font-bold text-on-surface mb-2" style="font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; font-weight: 700; margin-bottom: 8px;">Generating Quiz Questions with AI</h3>
            <p class="text-sm text-on-surface-variant max-w-md mb-4" style="color: var(--muted); font-size: 0.95rem; max-width: 400px; line-height: 1.5; margin: 0 auto 16px;">Our AI Coach is generating a unique question set for this section. This takes about 15-30 seconds. You can start solving the other questions in the meantime!</p>
            <button id="bypass-ai-btn" class="mt-4 px-4 py-2.5 text-xs font-semibold rounded-xl border border-outline-variant/30 bg-surface-container-high text-primary hover:bg-primary-soft transition-all" style="margin-top: 16px; padding: 8px 16px; font-size: 0.85rem; font-weight: 600; border-radius: 12px; border: 1px solid var(--border); background: var(--bg-elevated); color: var(--primary); cursor: pointer;">Load Backup Local Questions Instead</button>
          </div>
        `;
        optionsList.innerHTML = "";
        bookmarkButton.textContent = "Bookmark This Question";
        reviewButton.textContent = reviewFlags[currentIndex] ? "Unmark Review" : "Mark for Review";
        
        if (answerFeedback && answerFeedbackStatus && answerFeedbackText) {
          answerFeedback.classList.add("hidden");
        }
        
        renderPalette();
        renderSummary();
        renderSections();

        if (saveNextButton) {
          saveNextButton.textContent = currentIndex === questions.length - 1 ? "Finish & See Results" : "Continue";
          saveNextButton.classList.add("hidden");
        }
        renderSectionJump();
        return;
      }

      if (questionText) {
        questionText.classList.remove("question-anim");
        void questionText.offsetHeight; // trigger reflow
        questionText.classList.add("question-anim");
      }
      if (optionsList) {
        optionsList.classList.remove("question-anim");
        void optionsList.offsetHeight; // trigger reflow
        optionsList.classList.add("question-anim");
      }

      questionText.textContent = currentQuestion.q;
      bookmarkButton.textContent = isBookmarked(currentQuestion.q) ? "Bookmarked" : "Bookmark This Question";
      reviewButton.textContent = reviewFlags[currentIndex] ? "Unmark Review" : "Mark for Review";

      optionsList.innerHTML = currentQuestion.opts.map((option, optionIndex) => {
        const checked = selectedAnswer === optionIndex ? "checked" : "";
        const selectedClass = selectedAnswer === optionIndex ? "selected" : "";
        return `
          <label class="option-card ${selectedClass}">
            <input type="radio" name="answer" value="${optionIndex}" ${checked}>
            <span>${escapeHtml(option)}</span>
          </label>
        `;
      }).join("");

      optionsList.querySelectorAll('input[name="answer"]').forEach((input) => {
        input.addEventListener("change", () => {
          answers[currentIndex] = Number(input.value);
          saveJson(STORAGE_KEYS.answers, answers);
          renderQuestion();
        });
      });

      if (answerFeedback && answerFeedbackStatus && answerFeedbackText) {
        answerFeedback.classList.add("hidden");
        answerFeedback.classList.remove("correct", "incorrect");
        answerFeedbackStatus.textContent = "Answer Review";
        answerFeedbackText.textContent = "Explanation will appear after you submit the test.";
      }

      renderPalette();
      renderSummary();
      renderSections();

      if (saveNextButton) {
        saveNextButton.textContent = currentIndex === questions.length - 1 ? "Finish & See Results" : "Continue";
        saveNextButton.classList.toggle("hidden", !isAnswered);
      }
      renderSectionJump();
    };

    const moveNext = () => {
      if (currentIndex < questions.length - 1) {
        currentIndex += 1;
        renderQuestion();
      }
    };

    questionText?.addEventListener("click", (e) => {
      const btn = e.target.closest("#bypass-ai-btn");
      if (btn) {
        e.preventDefault();
        btn.disabled = true;
        btn.textContent = "Loading Backup Questions...";
        try {
          backgroundFetchController.abort();
        } catch (err) {
          console.warn("Failed to abort background fetch:", err);
        }
      }
    });

    bookmarkButton?.addEventListener("click", () => {
      const currentQuestion = questions[currentIndex];
      const entry = {
        exam: currentExam,
        subject: currentQuestion.section || config.subject,
        topic: config.topic,
        q: currentQuestion.q,
        opts: currentQuestion.opts,
        ans: currentQuestion.ans,
        exp: currentQuestion.exp || "",
        savedAt: new Date().toISOString()
      };

      if (!saveBookmarkEntry(entry)) {
        bookmarkButton.textContent = "Already Bookmarked";
        return;
      }

      bookmarkButton.textContent = "Bookmarked";
    });

    clearButton?.addEventListener("click", () => {
      answers[currentIndex] = null;
      saveJson(STORAGE_KEYS.answers, answers);
      renderQuestion();
    });

    reviewButton?.addEventListener("click", () => {
      reviewFlags[currentIndex] = !reviewFlags[currentIndex];
      renderQuestion();
    });

    saveNextButton?.addEventListener("click", () => {
      if (answers[currentIndex] === null) {
        return;
      }

      if (currentIndex === questions.length - 1) {
        finishQuiz(questions, answers, reviewFlags);
        return;
      }

      moveNext();
    });

    submitTestButton?.addEventListener("click", () => {
      saveCurrentSelection();
      openSubmitModal(questions, answers, reviewFlags);
    });

    submitModal?.addEventListener("click", (event) => {
      if (event.target === submitModal) {
        closeSubmitModal();
      }
    });

    loadingState.classList.add("hidden");
    quizRoot.classList.remove("hidden");
    updateTimer();

    if (timeLeft !== null) {
      timerId = window.setInterval(() => {
        timeLeft -= 1;
        updateTimer();

        if (timeLeft <= 0) {
          finishQuiz(questions, answers, reviewFlags);
        }
      }, 1000);
    }

    renderQuestion();

    const startBackgroundQuestionsFetch = async () => {
      const placeholders = questions.filter((q) => q.placeholder);
      if (placeholders.length === 0) {
        return;
      }


      let hadFallbackError = false;

      const sectionsWithPlaceholders = {};
      questions.forEach((q, idx) => {
        if (q.placeholder) {
          const key = q.sectionSubject || q.section || config.subject || "General";
          if (!sectionsWithPlaceholders[key]) {
            sectionsWithPlaceholders[key] = [];
          }
          sectionsWithPlaceholders[key].push({ question: q, index: idx });
        }
      });

      const fetchPromises = Object.entries(sectionsWithPlaceholders).map(async ([subjectKey, items]) => {
        const aiCount = items.length;
        const firstPlaceholder = items[0].question;
        const sectionTopic = config.mode === "final-mock" ? "All Topics" : config.topic;

        const excludeList = questions
          .filter((q) => !q.placeholder && (q.sectionSubject === subjectKey || q.section === subjectKey))
          .map((q) => q.q);

        try {


          const apiOptions = {
            stage: currentStage,
            branch: config.branch || "",
            practiceType: config.practiceType || "topic-practice",
            selectedChapters: config.selectedChapters || [],
            chapterQuestionMode: config.chapterQuestionMode || "",
            drillTopics: config.drillTopics || [],
            forceAi: true
          };

          const generated = await generateSectionQuestionsInBatches({
            subject: subjectKey,
            topic: sectionTopic,
            count: aiCount,
            mode: config.mode,
            exam: currentExam,
            stage: currentStage,
            branch: config.branch || "",
            difficulty,
            recentQuestions: excludeList,
            recentPatterns: [],
            practiceType: config.practiceType || "topic-practice",
            selectedChapters: config.selectedChapters || [],
            chapterQuestionMode: config.chapterQuestionMode || "",
            drillTopics: config.drillTopics || [],
            onStatus: null,
            forceAi: true,
            signal: backgroundFetchController.signal
          });

          if (!generated || generated.length === 0) {
            throw new Error(`No AI questions returned for ${subjectKey}`);
          }

          items.forEach((item, i) => {
            if (i < generated.length) {
              const newQ = generated[i];
              questions[item.index] = {
                ...newQ,
                section: firstPlaceholder.section,
                sectionSubject: firstPlaceholder.sectionSubject
              };
            }
          });


        } catch (err) {
          console.warn(`Failed to fetch AI questions for ${subjectKey}, falling back to local DB:`, err);
          try {
            const fallbackGenerated = await generateSectionQuestionsInBatches({
              subject: subjectKey,
              topic: sectionTopic,
              count: aiCount,
              mode: config.mode,
              exam: currentExam,
              stage: currentStage,
              branch: config.branch || "",
              difficulty,
              recentQuestions: excludeList,
              recentPatterns: [],
              practiceType: config.practiceType || "topic-practice",
              selectedChapters: config.selectedChapters || [],
              chapterQuestionMode: config.chapterQuestionMode || "",
              drillTopics: config.drillTopics || [],
              onStatus: null,
              forceDb: true
            });

            items.forEach((item, i) => {
              if (i < fallbackGenerated.length) {
                const newQ = fallbackGenerated[i];
                questions[item.index] = {
                  ...newQ,
                  section: firstPlaceholder.section,
                  sectionSubject: firstPlaceholder.sectionSubject
                };
              }
            });

          } catch (fallbackErr) {
            console.error(`Double failure: both AI and fallback local questions failed for ${subjectKey}:`, fallbackErr);
            hadFallbackError = true;
            items.forEach((item) => {
              questions[item.index] = {
                q: `Mock Practice Question: Solve the standard RRB sample for ${subjectKey}.`,
                opts: ["A) Option A", "B) Option B", "C) Option C", "D) Option D"],
                ans: 0,
                exp: "Use standard exam formulas to compute the answer.",
                section: firstPlaceholder.section,
                sectionSubject: firstPlaceholder.sectionSubject
              };
            });
          }
        }
      });

      await Promise.all(fetchPromises);

      saveJson(STORAGE_KEYS.questions, questions);
      const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
      const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
      const existingPaperIndex = savedPapers.findIndex((paper) => paper.id === paperId);
      if (existingPaperIndex >= 0) {
        savedPapers[existingPaperIndex].questions = questions;
        saveJson(savedPapersKey, savedPapers);
      }

      renderPalette();
      renderSections();
      renderSectionJump();

      if (questions[currentIndex] && !questions[currentIndex].placeholder) {
        renderQuestion();
      }

      if (hadFallbackError) {
        showToast("Backup local questions loaded successfully.", "info");
      } else {
        showToast("Exam questions successfully configured by RRB AI Coach!", "success");
      }

      if (submitModal && !submitModal.classList.contains("hidden")) {
        openSubmitModal(questions, answers, reviewFlags);
      }
    };

    startBackgroundQuestionsFetch();
  } catch (error) {
    loadingState.classList.add("hidden");
    errorState.classList.remove("hidden");
    errorMessage.textContent = error instanceof Error ? error.message : "Unexpected error occurred.";
  }
}

function setupScorePage() {
  const scoreValue = document.querySelector("#score-value");
  if (!scoreValue) {
    return;
  }

  const currentUser = readJson(STORAGE_KEYS.currentUser);
  if (!currentUser) {
    window.location.href = "./login.html";
    return;
  }

  const results = readJson(STORAGE_KEYS.results);
  const questions = readJson(STORAGE_KEYS.questions, []);
  const answers = readJson(STORAGE_KEYS.answers, []);
  const prefetchCache = new Map();
  const scoreSummary = document.querySelector("#score-summary");
  const reviewList = document.querySelector("#review-list");
  const reviewWrongAnswersButton = document.querySelector("#review-wrong-answers");
  const wrongAnswersPanel = document.querySelector("#wrong-answers-panel");
  const wrongAnswersList = document.querySelector("#wrong-answers-list");
  const practiceWrongQuestionsButton = document.querySelector("#practice-wrong-questions");
  const scoreRing = document.querySelector(".score-ring");
  const scoreMetrics = document.querySelector("#score-metrics");
  const sectionMetrics = document.querySelector("#section-metrics");
  const sectionInsights = document.querySelector("#section-insights");
  const topSectionSummary = document.querySelector("#top-section-summary");
  const subjectChart = document.querySelector("#subject-chart");
  const weakestSectionCard = document.querySelector("#weakest-section-card");
  const config = readJson(STORAGE_KEYS.config);
  const currentExam = config?.exam || "RRB NTPC";
  const currentStage = config?.stage || "";
  const currentBranch = config?.branch || "";

  const isBookmarked = (questionTextToCheck) => {
    const bookmarksKey = getExamSpecificKey(STORAGE_KEYS.bookmarks, currentExam);
    const bookmarks = readJson(bookmarksKey, []);
    return bookmarks.some((bookmark) => bookmark.q === questionTextToCheck);
  };

  const saveBookmarkEntry = (entry) => {
    const bookmarksKey = getExamSpecificKey(STORAGE_KEYS.bookmarks, entry.exam);
    const bookmarks = readJson(bookmarksKey, []);
    const alreadySaved = bookmarks.some((bookmark) => bookmark.q === entry.q);
    if (alreadySaved) {
      return false;
    }

    saveJson(bookmarksKey, [entry, ...bookmarks].slice(0, 50));
    return true;
  };

  if (!results || !questions.length) {
    window.location.href = "./dashboard.html";
    return;
  }

  const historyKey = results.mode === "final-mock" ? getExamSpecificKey(STORAGE_KEYS.finalMockHistory, currentExam) : getExamSpecificKey(STORAGE_KEYS.history, currentExam);
  const history = pruneHistoryRecords(readJson(historyKey, []));
  const savedPapersKey = getExamSpecificKey(STORAGE_KEYS.savedPapers, currentExam);
  const savedPapers = pruneSavedPapers(readJson(savedPapersKey, []));
  saveJson(savedPapersKey, savedPapers);
  const attempt = {
    subject: config?.subject || "Unknown Subject",
    topic: config?.topic || "Unknown Topic",
    score: results.score,
    total: results.total,
    percentage: results.percentage,
    completedAt: new Date().toISOString(),
    modeLabel: results.mode === "final-mock"
      ? (MODE_LABELS[results.mode] || "Final Mock")
      : config?.customQuestionSource === "bookmarks"
        ? "Bookmark Retry"
      : config?.customQuestionSource === "wrong-questions"
        ? "Wrong Questions Retry"
      : config?.practiceType === "weak-drill"
        ? "Weak Topic Drill"
      : config?.practiceType === "chapter-practice"
        ? `${config?.subject || "General"} Chapter Practice`
        : `${config?.subject || "General"} ${MODE_LABELS[results.mode || config?.mode || "practice"] || "Practice"}`,
    exam: currentExam,
    stage: currentStage,
    finalScore: results.finalScore ?? results.score,
    wrongAnswers: results.wrongAnswers ?? 0,
    unansweredAnswers: results.unansweredAnswers ?? 0,
    negativeMarks: results.negativeMarks ?? 0,
    difficulty: config?.difficulty || "intermediate",
    paperId: config?.paperId || null
  };

  // Kick off background prefetching for all wrong attempts
  questions.forEach((question, index) => {
    const userAnswer = answers[index];
    const isCorrect = userAnswer === question.ans;
    if (userAnswer !== null && !isCorrect) {
      const payload = buildExplanationPayload(question, index, {
        exam: currentExam,
        subject: question.sectionSubject || question.section || attempt.subject,
        topic: attempt.topic,
        difficulty: config?.difficulty || "medium"
      });
      const promise = (async () => {
        try {
          const response = await getExplanation(payload);
          return { success: true, response, payload };
        } catch (error) {
          console.warn(`Background explanation prefetch failed for question ${index}:`, error);
          return { success: false, error, payload };
        }
      })();
      prefetchCache.set(index, promise);
    }
  });

  const isLatestDuplicate = history[0]
    && history[0].subject === attempt.subject
    && history[0].topic === attempt.topic
    && history[0].score === attempt.score
    && history[0].total === attempt.total;

  if (!isLatestDuplicate) {
    const nextHistory = [attempt, ...history].slice(0, 60);
    saveJson(historyKey, nextHistory);
    saveJson(getExamSpecificKey(STORAGE_KEYS.lastAttempt, currentExam), attempt);


  }
  if (isLatestDuplicate) {
    saveJson(getExamSpecificKey(STORAGE_KEYS.lastAttempt, currentExam), history[0]);
  }

  const recentQuestionsKey = getExamSpecificKey(STORAGE_KEYS.recentQuestions, currentExam);
  const recentPatternsKey = getExamSpecificKey(STORAGE_KEYS.recentPatterns, currentExam);
  const recentQuestions = readJson(recentQuestionsKey, []);
  const recentPatterns = readJson(recentPatternsKey, []);
  const newRecentQuestions = questions.map((question) => ({
    exam: currentExam,
    subject: question.sectionSubject || question.section || attempt.subject,
    topic: attempt.topic,
    q: question.q,
    savedAt: attempt.completedAt
  }));
  const newRecentPatterns = questions.map((question) => ({
    exam: currentExam,
    subject: question.sectionSubject || question.section || attempt.subject,
    pattern: createQuestionPatternSignature(question.q),
    savedAt: attempt.completedAt
  }));
  saveJson(recentQuestionsKey, [...newRecentQuestions, ...recentQuestions].slice(0, 180));
  saveJson(recentPatternsKey, [...newRecentPatterns, ...recentPatterns].slice(0, 220));

  scoreValue.textContent = `${results.percentage}%`;
  scoreSummary.textContent = `Correct: ${results.score}, Wrong: ${results.wrongAnswers}, Unanswered: ${results.unansweredAnswers}, Net Score: ${results.finalScore}. Marking rule: +1 correct, -0.33 wrong.`;
  scoreRing.style.background = `radial-gradient(circle at center, var(--bg-card) 0 58%, transparent 59%), conic-gradient(var(--primary) ${results.percentage * 3.6}deg, var(--bg-elevated) 0deg)`;
  scoreMetrics.innerHTML = `
    <article class="analytics-item">
      <strong>Mode</strong>
      <p>${attempt.modeLabel}</p>
    </article>
    <article class="analytics-item">
      <strong>Difficulty</strong>
      <p>${DIFFICULTY_LABELS[attempt.difficulty] || "Intermediate"}</p>
    </article>
    <article class="analytics-item">
      <strong>Subject</strong>
      <p>${results.mode === "final-mock" ? `${attempt.exam}${attempt.stage ? ` ${attempt.stage}` : ""}` : attempt.subject}</p>
    </article>
    <article class="analytics-item">
      <strong>Topic</strong>
      <p>${results.mode === "final-mock" ? "Full Pattern Mock" : attempt.topic}</p>
    </article>
    <article class="analytics-item">
      <strong>Accuracy</strong>
      <p>${attempt.percentage}%</p>
    </article>
    <article class="analytics-item">
      <strong>Net Score</strong>
      <p>${results.finalScore}</p>
    </article>
    <article class="analytics-item">
      <strong>Wrong</strong>
      <p>${results.wrongAnswers}</p>
    </article>
    <article class="analytics-item">
      <strong>Unanswered</strong>
      <p>${results.unansweredAnswers}</p>
    </article>
    <article class="analytics-item">
      <strong>Negative Marks</strong>
      <p>${results.negativeMarks}</p>
    </article>
  `;

  const sectionSummary = questions.reduce((accumulator, question, index) => {
    const key = question.section || attempt.subject;
    const current = accumulator[key] || {
      total: 0,
      correct: 0,
      wrong: 0,
      unanswered: 0,
      sourceSubject: question.sectionSubject || question.section || attempt.subject
    };
    current.total += 1;
    if (answers[index] === null) {
      current.unanswered += 1;
    } else if (answers[index] === question.ans) {
      current.correct += 1;
    } else {
      current.wrong += 1;
    }
    accumulator[key] = current;
    return accumulator;
  }, {});

  const rankedSections = Object.entries(sectionSummary)
    .map(([section, stats]) => ({
      section,
      stats,
      accuracy: Math.round((stats.correct / stats.total) * 100)
    }))
    .sort((left, right) => right.accuracy - left.accuracy);

  sectionMetrics.innerHTML = Object.entries(sectionSummary).map(([section, stats]) => `
    <article class="analytics-item">
      <strong>${section}</strong>
      <p>Correct: ${stats.correct}/${stats.total}</p>
      <p>Wrong: ${stats.wrong} | Unanswered: ${stats.unanswered}</p>
      <p>Accuracy: ${Math.round((stats.correct / stats.total) * 100)}%</p>
    </article>
  `).join("");

  if (sectionInsights) {
    sectionInsights.innerHTML = Object.entries(sectionSummary).map(([section, stats]) => {
      const accuracy = Math.round((stats.correct / stats.total) * 100);
      const insight = getSectionInsight(accuracy);

      return `
        <article class="analytics-item analytics-card ${insight.className}">
          <div class="analytics-top">
            <strong>${section}</strong>
            <span class="insight-pill ${insight.className}">${insight.label}</span>
          </div>
          <p>Accuracy: ${accuracy}%</p>
          <p>Correct: ${stats.correct}/${stats.total}</p>
          <p>Wrong: ${stats.wrong} | Unanswered: ${stats.unanswered}</p>
          <p>Focus: ${insight.focus}</p>
        </article>
      `;
    }).join("");
  }

  if (topSectionSummary) {
    const bestSection = rankedSections[0];
    const weakestSection = rankedSections[rankedSections.length - 1];

    topSectionSummary.innerHTML = `
      <article class="analytics-item analytics-card insight-strong">
        <div class="analytics-top">
          <strong>Best Section</strong>
          <span class="insight-pill insight-strong">${bestSection ? `${bestSection.accuracy}%` : "--"}</span>
        </div>
        <p>${bestSection ? bestSection.section : "No data"}</p>
        <p>${bestSection ? `Correct: ${bestSection.stats.correct}/${bestSection.stats.total}` : ""}</p>
        <p>${bestSection ? "Keep revision and speed practice going here." : ""}</p>
      </article>
      <article class="analytics-item analytics-card insight-weak">
        <div class="analytics-top">
          <strong>Weakest Section</strong>
          <span class="insight-pill insight-weak">${weakestSection ? `${weakestSection.accuracy}%` : "--"}</span>
        </div>
        <p>${weakestSection ? weakestSection.section : "No data"}</p>
        <p>${weakestSection ? `Wrong: ${weakestSection.stats.wrong} | Unanswered: ${weakestSection.stats.unanswered}` : ""}</p>
        <p>${weakestSection ? "Start with basics, then do step-by-step revision here." : ""}</p>
      </article>
    `;
  }

  if (subjectChart) {
    if (!rankedSections.length) {
      subjectChart.innerHTML = `
        <article class="history-empty">
          <strong>No chart data yet</strong>
          <span>Finish a multi-section test to see subject-wise accuracy bars here.</span>
        </article>
      `;
    } else {
      subjectChart.innerHTML = rankedSections.map((item) => {
        const barClass = item.accuracy >= 70 ? "chart-good" : item.accuracy >= 40 ? "chart-mid" : "chart-low";
        return `
          <article class="chart-row">
            <strong class="chart-label">${item.section}</strong>
            <div class="chart-bar-track">
              <div class="chart-bar-fill ${barClass}" style="width: ${item.accuracy}%"></div>
            </div>
            <span class="chart-value">${item.accuracy}%</span>
          </article>
        `;
      }).join("");
    }
  }

  if (weakestSectionCard) {
    const weakestSection = rankedSections[rankedSections.length - 1] || null;
    const retrySubject = weakestSection?.stats?.sourceSubject || attempt.subject;
    const retryAccuracy = weakestSection?.accuracy ?? results.percentage;
    const retryLabel = rankedSections.length > 1 ? "Weakest Subject" : "Retry This Subject";
    const retryCopy = rankedSections.length > 1
      ? "This subject was your weakest in this paper. You can start a focused retry from the dashboard with this subject pre-selected."
      : "Since this was a single-subject test, you can launch your next focused practice with this subject pre-selected on the dashboard.";

    weakestSectionCard.innerHTML = `
      <article class="retry-card">
        <strong>${retryLabel}: ${retrySubject} (${retryAccuracy}%)</strong>
        <p>${retryCopy}</p>
        <div class="bookmark-actions">
          <button id="retry-weakest-subject" class="primary-btn" type="button">Retry ${retrySubject}</button>
        </div>
      </article>
    `;

    document.querySelector("#retry-weakest-subject")?.addEventListener("click", () => {
      saveJson(STORAGE_KEYS.profile, {
        ...readJson(STORAGE_KEYS.profile, {}),
        preferredExam: currentExam,
        preferredStage: currentStage,
        preferredBranch: currentBranch,
        lastSubject: retrySubject,
        lastTopic: ""
      });
      window.location.href = "./dashboard.html";
    });
  }

  const mistakesKey = getExamSpecificKey(STORAGE_KEYS.mistakes, currentExam);
  const existingMistakes = readJson(mistakesKey, []);
  const newMistakes = questions
    .map((question, index) => ({
      question,
      answer: answers[index]
    }))
    .filter((item) => item.answer !== null && item.answer !== item.question.ans)
    .map((item) => ({
      exam: currentExam,
      subject: item.question.section || attempt.subject,
      topic: attempt.topic,
      q: item.question.q,
      opts: item.question.opts,
      ans: item.question.ans,
      exp: item.question.exp || "",
      savedAt: `${attempt.completedAt}-${createQuestionPatternSignature(item.question.q).slice(0, 24)}`
    }));

  if (newMistakes.length) {
    const dedupedMistakes = [...newMistakes, ...existingMistakes].filter((item, index, array) =>
      index === array.findIndex((entry) => entry.exam === item.exam && entry.q === item.q)
    );
    saveJson(mistakesKey, dedupedMistakes.slice(0, 220));
  }

  const wrongQuestionEntries = questions
    .map((question, index) => ({
      question,
      userAnswer: answers[index]
    }))
    .filter((item) => item.userAnswer !== null && item.userAnswer !== item.question.ans)
    .map((item, index) => ({
      exam: currentExam,
      stage: currentStage,
      branch: currentBranch,
      question: item.question.q,
      options: item.question.opts,
      correctIndex: item.question.ans,
      userAnswer: item.userAnswer,
      subject: item.question.sectionSubject || item.question.section || attempt.subject,
      topic: attempt.topic,
      timestamp: Date.now() + index
    }));

  if (wrongQuestionEntries.length) {
    const existingWrongQuestions = readJson(STORAGE_KEYS.wrongQuestions, []);
    const mergedWrongQuestions = [...wrongQuestionEntries, ...existingWrongQuestions].filter((item, index, collection) =>
      index === collection.findIndex((entry) =>
        entry.exam === item.exam
        && entry.question === item.question
      )
    );
    saveJson(STORAGE_KEYS.wrongQuestions, mergedWrongQuestions.slice(0, 320));
  }

  if (reviewWrongAnswersButton && wrongAnswersPanel && wrongAnswersList) {
    if (!wrongQuestionEntries.length) {
      reviewWrongAnswersButton.disabled = true;
      reviewWrongAnswersButton.textContent = "No Wrong Answers";
      wrongAnswersList.innerHTML = `
        <article class="empty-card">
          <strong>No wrong answers for this attempt</strong>
          <span>Perfect attempt hone par yahan koi question show nahi hoga.</span>
        </article>
      `;
      practiceWrongQuestionsButton?.classList.add("hidden");
    } else {
      wrongAnswersList.innerHTML = wrongQuestionEntries.map((item, index) => {
        const userAnswer = item.options?.[item.userAnswer] || "Not answered";
        const correctAnswer = item.options?.[item.correctIndex] || "Not available";
        return `
          <article class="wrong-answer-card">
            <div class="mb-4 flex items-center justify-between gap-3">
              <span class="badge incorrect">Wrong ${index + 1}</span>
              <span class="text-xs font-semibold uppercase tracking-widest text-on-surface-variant">${item.subject}</span>
            </div>
            <h3>${escapeHtml(item.question)}</h3>
            <div class="grid gap-3">
              <div class="wrong-answer-option user-wrong">Your Answer: ${escapeHtml(userAnswer)}</div>
              <div class="wrong-answer-option correct-answer">Correct Answer: ${escapeHtml(correctAnswer)}</div>
            </div>
            <p class="mt-4 text-sm text-on-surface-variant">Open the full review below and click Show Solution when you want the AI explanation.</p>
          </article>
        `;
      }).join("");

      reviewWrongAnswersButton.addEventListener("click", () => {
        const willOpen = wrongAnswersPanel.classList.contains("hidden");
        wrongAnswersPanel.classList.toggle("hidden", !willOpen);
        reviewWrongAnswersButton.textContent = willOpen ? "Hide Wrong Answers" : "Review Wrong Answers";
      });

      practiceWrongQuestionsButton?.addEventListener("click", () => {
        const replayQuestions = wrongQuestionEntries.map(toReplayQuestion);
        saveJson(STORAGE_KEYS.replayQuestions, replayQuestions);
        saveJson(STORAGE_KEYS.config, createCustomQuestionSetConfig({
          exam: currentExam,
          stage: currentStage,
          branch: currentBranch,
          subject: "Wrong Questions",
          topic: `${wrongQuestionEntries.length} Questions Review`,
          difficulty: config?.difficulty || "intermediate",
          questions: replayQuestions
        }));
        window.location.href = "./quiz.html";
      });
    }
  }

  reviewList.innerHTML = questions.map((question, index) => {
    const userAnswer = answers[index];
    const isCorrect = userAnswer === question.ans;
    const userLabel = userAnswer === null ? "Not answered" : question.opts[userAnswer];
    const correctLabel = question.opts[question.ans];
    const savedLabel = isBookmarked(question.q) ? "Bookmarked" : "Bookmark";

    return `
      <article class="review-item ${isCorrect ? "correct" : "incorrect"}">
        <div class="badge ${isCorrect ? "correct" : "incorrect"}">${isCorrect ? "Correct" : userAnswer === null ? "Unanswered" : "Incorrect"}</div>
        <h3>${escapeHtml(question.q)}</h3>
        <p><strong>Your answer:</strong> ${escapeHtml(userLabel)}</p>
        <p><strong>Correct answer:</strong> ${escapeHtml(correctLabel)}</p>
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <button class="chip-btn show-solution-btn" type="button" data-show-solution="${index}">Show Solution</button>
          <button class="chip-btn review-bookmark-btn" type="button" data-review-bookmark="${index}">${savedLabel}</button>
          <span class="text-sm text-on-surface-variant" data-solution-status="${index}"></span>
        </div>
        <div class="hidden" data-solution-box="${index}"></div>
      </article>
    `;
  }).join("");

  reviewList.querySelectorAll("[data-show-solution]").forEach((button) => {
    button.addEventListener("click", async () => {
      const index = Number(button.dataset.showSolution);
      const question = questions[index];
      const status = reviewList.querySelector(`[data-solution-status="${index}"]`);
      const box = reviewList.querySelector(`[data-solution-box="${index}"]`);

      button.disabled = true;
      button.textContent = "Loading...";
      if (status) {
        status.textContent = "Checking explanation cache...";
      }

      try {
        const payload = buildExplanationPayload(question, index, {
          exam: currentExam,
          subject: question.sectionSubject || question.section || attempt.subject,
          topic: attempt.topic,
          difficulty: config?.difficulty || "medium"
        });

        let response;
        if (prefetchCache.has(index)) {
          if (status) {
            status.textContent = "Loading pre-fetched explanation...";
          }
          const result = await prefetchCache.get(index);
          if (result.success) {
            response = result.response;
          } else {
            throw result.error;
          }
        } else {
          response = await getExplanation(payload);
        }

        renderExplanationBox(box, response, payload);
        prefetchCache.delete(index);
        button.textContent = "Solution Loaded";
        if (status) {
          status.textContent = response.cached ? "Cached explanation" : "Generated and saved";
        }
      } catch (error) {
        if (question.exp) {
          console.warn("Explanation API failed. Using local fallback explanation.", error);
          const fallbackResponse = {
            explanation: question.exp,
            cached: true,
            topic: question.topic || (typeof payload !== "undefined" ? payload.topic : "")
          };
          renderExplanationBox(box, fallbackResponse, {
            topic: question.topic || "General",
            difficulty: question.difficulty || "medium"
          });
          button.textContent = "Solution Loaded";
          if (status) {
            status.textContent = "Loaded from offline question bank";
          }
        } else {
          button.disabled = false;
          button.textContent = "Show Solution";
          if (status) {
            status.textContent = "Could not load explanation. Check the local API or AWS credentials.";
          }
          if (box) {
            box.classList.remove("hidden");
            box.innerHTML = `
              <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                ${escapeHtml(error?.message || "Explanation request failed.")}
              </div>
            `;
          }
        }
      }
    });
  });

  reviewList.querySelectorAll("[data-review-bookmark]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.dataset.reviewBookmark);
      const question = questions[index];
      const entry = {
        exam: currentExam,
        subject: question.section || attempt.subject,
        topic: attempt.topic,
        q: question.q,
        opts: question.opts,
        ans: question.ans,
        exp: question.exp || "",
        savedAt: new Date().toISOString()
      };

      if (!saveBookmarkEntry(entry)) {
        button.textContent = "Already Bookmarked";
        return;
      }

      button.textContent = "Bookmarked";
    });
  });
}

setupThemeToggle();
setupQuizPage();
setupScorePage();



