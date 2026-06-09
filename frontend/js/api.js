import { getQuestionBankEntries, toQuestionShape } from "./question-bank.js";

const REMOTE_API_GATEWAY_URL = "https://v50dh7wl24.execute-api.ap-south-1.amazonaws.com/prod/generate";
const API_GATEWAY_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? `${window.location.origin}/api/generate`
  : REMOTE_API_GATEWAY_URL;
const EXPLANATION_API_URL = ["localhost", "127.0.0.1"].includes(window.location.hostname)
  ? `${window.location.origin}/api/explanation`
  : REMOTE_API_GATEWAY_URL.replace(/\/generate$/, "/explanation");
const ACTIVE_EXAMS = ["RRB NTPC", "RRB Group D", "RRB Technician Grade 3"];
const API_TIMEOUT_MS = 45000;

function sanitizeActiveExam(examName) {
  return ACTIVE_EXAMS.includes(examName) ? examName : "RRB NTPC";
}

function shuffle(items) {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[randomIndex]] = [copy[randomIndex], copy[index]];
  }
  return copy;
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

async function pickBankQuestions(subject, topic, difficulty, count, excludeQuestions = [], excludePatterns = []) {
  const excluded = new Set(excludeQuestions.map((question) => question.trim().toLowerCase()));
  const excludedPatterns = new Set(excludePatterns.map((pattern) => String(pattern).trim().toLowerCase()));
  const entries = await getQuestionBankEntries(subject, topic, difficulty, 48);
  const seenPatterns = new Set(excludedPatterns);
  const normalized = shuffle(
    toQuestionShape(entries).filter((question) => !excluded.has(question.q.trim().toLowerCase()))
  );

  const selected = [];
  for (const question of normalized) {
    const pattern = createQuestionPatternSignature(question.q);
    if (seenPatterns.has(pattern)) {
      continue;
    }
    seenPatterns.add(pattern);
    selected.push(question);
    if (selected.length >= Math.min(count, normalized.length)) {
      break;
    }
  }

  return selected;
}

function buildFallbackQuestions(subject, topic, count, mode) {
  const label = mode === "previous-year" ? "previous year style" : mode === "mock" ? "mock test" : "practice";
  const stems = [
    `Which statement best matches the ${topic} concept?`,
    `Choose the correct answer related to ${topic}.`,
    `Identify the most accurate result for this ${topic} question.`,
    `Select the correct reasoning step for ${topic}.`,
    `Find the valid answer using the ${topic} idea.`,
    `Pick the correct exam-style option for ${topic}.`,
    `Which option is most appropriate for this ${topic} case?`,
    `Determine the right answer from the ${topic} information provided.`,
    `Choose the best conclusion for this ${topic} problem.`,
    `Find the correct response based on the ${topic} rule.`
  ];

  return Array.from({ length: count }, (_, index) => ({
    q: `${subject} - ${label}: ${stems[index % stems.length]}`,
    opts: ["Option A", "Option B", "Option C", "Option D"],
    ans: index % 4,
    exp: `This is a local fallback explanation for ${topic}.`,
    meta: {
      source: "local-fallback",
      fallbackId: index + 1
    }
  }));
}

async function fetchWithTimeout(url, options = {}, timeoutMs = API_TIMEOUT_MS) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      ...options,
      signal: controller.signal
    });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function normalizeApiResponse(payload) {
  if (Array.isArray(payload?.questions)) {
    return payload;
  }

  if (typeof payload?.body === "string") {
    try {
      const parsedBody = JSON.parse(payload.body);
      if (Array.isArray(parsedBody?.questions)) {
        return parsedBody;
      }
    } catch (error) {
      console.warn("Could not parse nested API body.", error);
    }
  }

  if (payload?.body && Array.isArray(payload.body.questions)) {
    return payload.body;
  }

  return null;
}

export async function generateQuestions(subject, topic, count, mode = "practice", excludeQuestions = [], exam = "RRB NTPC", difficulty = "intermediate", excludePatterns = [], requestOptions = {}) {
  const activeExam = sanitizeActiveExam(exam);
  const reportStatus = typeof requestOptions.onStatus === "function" ? requestOptions.onStatus : null;
  const isApiMissing = API_GATEWAY_URL.includes("xxxxxxxx");
  
  // If forceAi is requested, we bypass the local question bank entirely to request strictly AI questions
  const forceAi = !!requestOptions.forceAi;
  const forceDb = !!requestOptions.forceDb;

  let bankQuestions = [];

  if (!forceAi) {
    // If API is missing or forceDb is set, we MUST rely 100% on the local offline question bank
    const bankTargetCount = isApiMissing || requestOptions.practiceType === "topic-practice" || forceDb
      ? count
      : mode === "previous-year"
        ? Math.ceil(count / 2)
        : Math.min(2, count);

    try {
      reportStatus?.("Checking local question database...");
      bankQuestions = await pickBankQuestions(
        subject,
        topic,
        difficulty,
        bankTargetCount,
        excludeQuestions,
        excludePatterns
      );
    } catch (error) {
      console.warn("Local question bank could not be loaded. Continuing without it.", error);
      bankQuestions = [];
    }
  }

  // If forceDb is requested, return database questions immediately
  if (forceDb) {
    reportStatus?.("Using local offline question bank...");
    if (bankQuestions.length < count) {
      const fallbackQuestions = buildFallbackQuestions(subject, topic, count - bankQuestions.length, mode);
      return [...bankQuestions, ...fallbackQuestions];
    }
    return shuffle([...bankQuestions]).slice(0, count);
  }

  // If we found enough questions locally, return them immediately
  if (!forceAi && bankQuestions.length >= count) {
    reportStatus?.("Using local offline question bank...");
    return shuffle([...bankQuestions]).slice(0, count);
  }

  if (isApiMissing) {
    reportStatus?.("API URL is missing. Padding with AI fallback questions...");
    const fallbackQuestions = buildFallbackQuestions(subject, topic, Math.max(count - bankQuestions.length, 0), mode);
    return shuffle([...bankQuestions, ...fallbackQuestions]).slice(0, count);
  }

  const payload = {
    subject,
    topic,
    count: Math.max(count - bankQuestions.length, 1),
    mode,
    exam: activeExam,
    stage: requestOptions.stage || "",
    branch: requestOptions.branch || "",
    difficulty,
    practiceType: requestOptions.practiceType || "topic-practice",
    selectedChapters: requestOptions.selectedChapters || [],
    chapterQuestionMode: requestOptions.chapterQuestionMode || "",
    drillTopics: requestOptions.drillTopics || [],
    excludeQuestions,
    excludePatterns,
    questionContext: bankQuestions.map((question) => ({
      q: question.q,
      opts: question.opts,
      ans: question.ans,
      exp: question.exp,
      meta: question.meta || {}
    }))
  };

  let lastError = null;
  let data = null;

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      reportStatus?.(
        attempt === 1
          ? "Requesting questions from AWS Lambda..."
          : `Retrying question request (${attempt}/3)...`
      );
      const response = await fetchWithTimeout(API_GATEWAY_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        if (isLocalhost && response.status === 501) {
          lastError = new Error("Wrong local server is running. Start the app with start-project.bat or start-frontend.bat, not python -m http.server.");
          break;
        }
        lastError = new Error(`API request failed with status ${response.status}`);
        continue;
      }

      const responsePayload = normalizeApiResponse(await response.json());
      if (!Array.isArray(responsePayload?.questions)) {
        lastError = new Error("API returned an invalid questions payload.");
        continue;
      }
      data = responsePayload;
      lastError = null;
      break;
    } catch (error) {
      lastError = error?.name === "AbortError"
        ? new Error(`Question API timed out after ${Math.round(API_TIMEOUT_MS / 1000)} seconds.`)
        : error;
    }
  }

  if (lastError) {
    const wrongLocalServer = isLocalhost && lastError.message.includes("Wrong local server is running");

    if (wrongLocalServer) {
      reportStatus?.("Wrong local server detected. Run start-project.bat or start-frontend.bat.");
      throw lastError;
    }

    console.warn("Question API request failed. Falling back to local questions.", lastError);
    reportStatus?.("API is slow or unreachable. Using local backup questions...");
    const fallbackQuestions = buildFallbackQuestions(subject, topic, Math.max(count - bankQuestions.length, 0), mode);
    return shuffle([...bankQuestions, ...fallbackQuestions]).slice(0, count);
  }

  const lambdaQuestions = data.questions || [];
  const missingCount = Math.max(count - bankQuestions.length - lambdaQuestions.length, 0);
  const fallbackQuestions = missingCount > 0
    ? buildFallbackQuestions(subject, topic, missingCount, mode)
    : [];

  reportStatus?.("Questions received. Preparing quiz...");
  return shuffle([...bankQuestions, ...lambdaQuestions, ...fallbackQuestions]).slice(0, count);
}

export async function getExplanation(payload) {
  const response = await fetchWithTimeout(EXPLANATION_API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  let data = {};
  try {
    data = await response.json();
  } catch (error) {
    data = {};
  }

  if (!response.ok) {
    const message = data?.error || data?.details || `Explanation request failed with status ${response.status}`;
    throw new Error(message);
  }

  return data;
}
