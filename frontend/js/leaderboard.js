import { SUPABASE_KEY, SUPABASE_URL, isSupabaseConfigured } from "./config.js";
import { escapeHtml } from "./app.js?v=20260513c";

const LOCAL_LEADERBOARD_KEY = "rrbLeaderboardLocal";
const LOCAL_LEADERBOARD_EVENTS_KEY = "rrbLeaderboardLocalEvents";
const DEFAULT_RANGE = "all";

let supabaseClientPromise;

function readJson(key, fallback = []) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error("Failed to write to localStorage:", error);
  }
}

function normalizeRange(range = DEFAULT_RANGE) {
  return ["today", "week", "all"].includes(range) ? range : DEFAULT_RANGE;
}

function getRangeCutoff(range = DEFAULT_RANGE) {
  const normalizedRange = normalizeRange(range);
  const now = new Date();

  if (normalizedRange === "today") {
    const startOfDay = new Date(now);
    startOfDay.setHours(0, 0, 0, 0);
    return startOfDay;
  }

  if (normalizedRange === "week") {
    return new Date(now.getTime() - (7 * 24 * 60 * 60 * 1000));
  }

  return null;
}

function filterEntriesByRange(entries = [], range = DEFAULT_RANGE) {
  const cutoff = getRangeCutoff(range);
  if (!cutoff) {
    return entries;
  }

  return entries.filter((entry) => {
    const updatedAt = new Date(entry.updated_at || entry.updatedAt || 0);
    return !Number.isNaN(updatedAt.getTime()) && updatedAt >= cutoff;
  });
}

function sortLeaderboard(entries = []) {
  return [...entries].sort((left, right) =>
    (right.points || 0) - (left.points || 0)
    || (right.best_score || 0) - (left.best_score || 0)
    || (right.tests_done || 0) - (left.tests_done || 0)
    || String(left.username || "").localeCompare(String(right.username || ""))
  );
}

function migrateLegacyLeaderboard() {
  const eventRecords = readJson(LOCAL_LEADERBOARD_EVENTS_KEY, []);
  if (eventRecords.length) {
    return;
  }
  
  const legacyRecords = readJson(LOCAL_LEADERBOARD_KEY, []);
  if (legacyRecords.length) {
    const migrated = legacyRecords.map(entry => ({
      username: entry.username,
      email: entry.email || entry.username,
      exam: entry.exam,
      points: entry.points,
      tests_done: entry.tests_done || 1,
      best_score: entry.best_score || 0,
      updated_at: entry.updated_at || new Date().toISOString()
    }));
    saveJson(LOCAL_LEADERBOARD_EVENTS_KEY, migrated);
    try {
      localStorage.removeItem(LOCAL_LEADERBOARD_KEY);
    } catch (e) {
      console.warn(e);
    }
  }
}

function aggregateLeaderboardEntries(entries = []) {
  return sortLeaderboard(
    Object.values(
      entries.reduce((accumulator, entry) => {
        const emailKey = entry.email || entry.username || "unknown";
        const key = `${entry.exam}::${String(emailKey).toLowerCase()}`;
        const current = accumulator[key] || {
          username: entry.username,
          exam: entry.exam,
          points: 0,
          tests_done: 0,
          best_score: 0,
          updated_at: entry.updated_at
        };

        if (!current.updated_at || new Date(entry.updated_at).getTime() >= new Date(current.updated_at).getTime()) {
          current.username = entry.username;
          current.updated_at = entry.updated_at;
        }

        current.points += Number(entry.points || 0);
        current.tests_done += Number(entry.tests_done || 1);
        current.best_score = Math.max(current.best_score || 0, Number(entry.best_score || 0));
        accumulator[key] = current;
        return accumulator;
      }, {})
    )
  );
}

function getLocalLeaderboard(exam, range = DEFAULT_RANGE) {
  migrateLegacyLeaderboard();
  const eventRecords = readJson(LOCAL_LEADERBOARD_EVENTS_KEY, []);
  const filteredEvents = filterEntriesByRange(
    eventRecords.filter((entry) => entry.exam === exam),
    range
  );
  return aggregateLeaderboardEntries(filteredEvents);
}

function updateLocalLeaderboard(username, exam, points, score) {
  migrateLegacyLeaderboard();
  const timestamp = new Date().toISOString();
  const currentUser = readJson("rrbCurrentUser", {});
  const email = currentUser.email || username;

  const eventRecords = readJson(LOCAL_LEADERBOARD_EVENTS_KEY, []);
  eventRecords.unshift({
    username,
    email,
    exam,
    points,
    tests_done: 1,
    best_score: score || 0,
    updated_at: timestamp
  });
  saveJson(LOCAL_LEADERBOARD_EVENTS_KEY, eventRecords.slice(0, 2000));

  return getLocalLeaderboard(exam);
}

async function getSupabaseClient() {
  if (!isSupabaseConfigured()) {
    return null;
  }

  if (!supabaseClientPromise) {
    supabaseClientPromise = import("https://esm.sh/@supabase/supabase-js")
      .then(({ createClient }) => createClient(SUPABASE_URL, SUPABASE_KEY))
      .catch(() => null);
  }

  return supabaseClientPromise;
}

function getCurrentUsername(fallback = "Learner") {
  const profile = readJson("rrbQuizProfile", {});
  const currentUser = readJson("rrbCurrentUser", {});
  return profile.name || currentUser.name || currentUser.email || fallback;
}

function calculateLeaderboardPoints({ correctAnswers = 0, percentage = 0 }) {
  let points = Number(correctAnswers || 0) * 5;
  points += 20;

  if (percentage >= 80) {
    points += 50;
  } else if (percentage >= 60) {
    points += 20;
  }

  return points;
}

async function updateLeaderboard(username, exam, points, score) {
  const safeUsername = String(username || "").trim();
  const safeExam = String(exam || "").trim();
  const safePoints = Number(points || 0);
  const safeScore = Number(score || 0);

  if (!safeUsername || !safeExam || safePoints <= 0) {
    return { source: "skipped", data: null };
  }

  updateLocalLeaderboard(safeUsername, safeExam, safePoints, safeScore);

  const supabase = await getSupabaseClient();
  if (!supabase) {
    return { source: "local", data: getLocalLeaderboard(safeExam) };
  }

  const timestamp = new Date().toISOString();

  try {
    const { data: existing, error: fetchError } = await supabase
      .from("leaderboard")
      .select("id, username, exam, points, tests_done, best_score")
      .eq("username", safeUsername)
      .eq("exam", safeExam)
      .maybeSingle();

    if (fetchError) {
      throw fetchError;
    }

    const payload = existing
      ? {
        id: existing.id,
        username: safeUsername,
        exam: safeExam,
        points: Number(existing.points || 0) + safePoints,
        tests_done: Number(existing.tests_done || 0) + 1,
        best_score: Math.max(Number(existing.best_score || 0), safeScore),
        updated_at: timestamp
      }
      : {
        username: safeUsername,
        exam: safeExam,
        points: safePoints,
        tests_done: 1,
        best_score: safeScore,
        updated_at: timestamp
      };

    const { data, error } = await supabase
      .from("leaderboard")
      .upsert(payload, { onConflict: "username,exam" })
      .select();

    if (error) {
      throw error;
    }

    return { source: "supabase", data };
  } catch {
    return { source: "local", data: getLocalLeaderboard(safeExam) };
  }
}

async function getLeaderboard(exam, range = DEFAULT_RANGE) {
  const safeExam = String(exam || "").trim();
  if (!safeExam) {
    return { source: "local", data: [] };
  }

  const supabase = await getSupabaseClient();
  if (!supabase) {
    return {
      source: "local",
      data: getLocalLeaderboard(safeExam, range)
    };
  }

  try {
    let query = supabase
      .from("leaderboard")
      .select("username, exam, points, tests_done, best_score, updated_at")
      .eq("exam", safeExam)
      .order("points", { ascending: false })
      .order("best_score", { ascending: false })
      .limit(50);

    const cutoff = getRangeCutoff(range);
    if (cutoff) {
      query = query.gte("updated_at", cutoff.toISOString());
    }

    const { data, error } = await query;
    if (error) {
      throw error;
    }

    return {
      source: "supabase",
      data: sortLeaderboard(Array.isArray(data) ? data : [])
    };
  } catch {
    return {
      source: "local",
      data: getLocalLeaderboard(safeExam, range)
    };
  }
}

async function renderLeaderboard({ exam, username = getCurrentUsername() }) {
  const leaderboardPanel = document.querySelector("[data-tab-panel='leaderboard']");
  const leaderboardTableBody = document.querySelector("#leaderboard-table-body");
  const leaderboardStatus = document.querySelector("#leaderboard-status");
  const filterButtons = Array.from(document.querySelectorAll("button[data-leaderboard-range]"));

  if (!leaderboardPanel || !leaderboardTableBody) {
    return;
  }

  const activeRange = normalizeRange(leaderboardPanel.dataset.leaderboardRange || DEFAULT_RANGE);
  leaderboardPanel.dataset.leaderboardExam = exam;
  leaderboardPanel.dataset.leaderboardRange = activeRange;

  filterButtons.forEach((button) => {
    const isActive = button.dataset.leaderboardRange === activeRange;
    button.classList.toggle("bg-primary", isActive);
    button.classList.toggle("text-white", isActive);
    button.classList.toggle("bg-surface-container-high", !isActive);
    button.classList.toggle("text-on-surface", !isActive);

    if (button.dataset.leaderboardBound === "true") {
      return;
    }

    button.dataset.leaderboardBound = "true";
    button.addEventListener("click", () => {
      leaderboardPanel.dataset.leaderboardRange = normalizeRange(button.dataset.leaderboardRange || DEFAULT_RANGE);
      void renderLeaderboard({
        exam: leaderboardPanel.dataset.leaderboardExam || exam,
        username: getCurrentUsername(username)
      });
    });
  });

  leaderboardTableBody.innerHTML = `
    <tr>
      <td colspan="5" class="px-4 py-8 text-center text-sm text-on-surface-variant">Loading leaderboard...</td>
    </tr>
  `;

  const { data, source } = await getLeaderboard(exam, activeRange);

  if (leaderboardStatus) {
    leaderboardStatus.textContent = source === "supabase"
      ? "Live Supabase ranking"
      : "Local fallback ranking until Supabase keys are added";
  }

  if (!data.length) {
    leaderboardTableBody.innerHTML = `
      <tr>
        <td colspan="5" class="px-4 py-8 text-center text-sm text-on-surface-variant">No leaderboard entries yet for this exam.</td>
      </tr>
    `;
    return;
  }

  const safeCurrentUser = String(username || "").trim().toLowerCase();
  leaderboardTableBody.innerHTML = data.map((entry, index) => {
    const medals = ["&#129351;", "&#129352;", "&#129353;"];
    const rankLabel = medals[index] ? `${medals[index]} ${index + 1}` : `${index + 1}`;
    const isCurrentUser = String(entry.username || "").trim().toLowerCase() === safeCurrentUser;
    const rowClass = isCurrentUser ? "bg-primary-container/20 text-on-surface" : "text-on-surface";

    return `
      <tr class="border-b border-outline-variant/10 ${rowClass}">
        <td class="px-4 py-3 font-semibold">${rankLabel}</td>
        <td class="px-4 py-3 font-semibold">${escapeHtml(entry.username || "Learner")}${isCurrentUser ? " (You)" : ""}</td>
        <td class="px-4 py-3">${Number(entry.points || 0)}</td>
        <td class="px-4 py-3">${Number(entry.tests_done || 0)}</td>
        <td class="px-4 py-3">${Number(entry.best_score || 0)}%</td>
      </tr>
    `;
  }).join("");
}

export {
  calculateLeaderboardPoints,
  getLeaderboard,
  renderLeaderboard,
  updateLeaderboard
};
