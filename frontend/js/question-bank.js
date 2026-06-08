let questionBankPromise = null;

function normalize(text) {
  return String(text || "").trim().toLowerCase();
}

async function loadQuestionBank() {
  if (!questionBankPromise) {
    questionBankPromise = fetch("./data/question-bank.json").then(async (response) => {
      if (!response.ok) {
        throw new Error(`Question bank failed to load: ${response.status}`);
      }
      return response.json();
    });
  }

  return questionBankPromise;
}

function scoreEntry(entry, subject, topic) {
  let score = 0;
  if (normalize(entry.subject) === normalize(subject)) {
    score += 3;
  }

  const entryTopic = normalize(entry.topic);
  const requestedTopic = normalize(topic);

  if (entryTopic === requestedTopic) {
    score += 5;
  } else if (requestedTopic.includes(entryTopic) || entryTopic.includes(requestedTopic)) {
    score += 2;
  }

  return score;
}

export async function getQuestionBankEntries(subject, topic, difficulty, count = 10) {
  const bank = await loadQuestionBank();
  return bank
    .filter((entry) => {
      if (subject && normalize(subject) !== "") {
        if (normalize(entry.subject) !== normalize(subject)) {
          return false;
        }
      }
      if (difficulty && normalize(difficulty) !== "mixed") {
        let targetLevel = normalize(difficulty);
        if (targetLevel === "basic") targetLevel = "easy";
        if (targetLevel === "intermediate") targetLevel = "medium";
        if (targetLevel === "advanced") targetLevel = "hard";
        
        const entryLevel = normalize(entry.difficulty || "medium");
        if (entryLevel !== targetLevel) {
           return false;
        }
      }
      return true;
    })
    .map((entry) => ({ ...entry, _score: scoreEntry(entry, subject, topic) }))
    .filter((entry) => entry._score > 0)
    .sort((left, right) => right._score - left._score || right.year - left.year)
    .slice(0, count);
}

export function toQuestionShape(entries) {
  return entries.map((entry) => ({
    q: entry.question,
    opts: entry.options,
    ans: entry.answer,
    exp: entry.explanation,
    meta: {
      id: entry.id,
      exam: entry.exam,
      year: entry.year,
      shift: entry.shift,
      subject: entry.subject,
      topic: entry.topic,
      source: entry.source,
      isOfficial: entry.is_official,
      difficulty: entry.difficulty,
      sourceMetadata: entry.source_metadata || null
    }
  }));
}
