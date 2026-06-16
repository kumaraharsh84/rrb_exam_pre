export const EXAM_PATTERNS = {
  "RRB NTPC": {
    code: "ntpc",
    timerMinutes: 90,
    totalQuestions: 100,
    negativeMarking: 1 / 3,
    sections: [
      { subject: "General Awareness", label: "General Awareness", count: 40, topic: "Full Syllabus" },
      { subject: "Mathematics", count: 30, topic: "Full Syllabus" },
      { subject: "General Intelligence and Reasoning", label: "General Intelligence & Reasoning", count: 30, topic: "Full Syllabus" }
    ]
  },
  "RRB Group D": {
    code: "group-d",
    timerMinutes: 90,
    totalQuestions: 100,
    negativeMarking: 1 / 3,
    sections: [
      { subject: "General Science", label: "General Science", count: 25, topic: "Physics, Chemistry, Biology and Everyday Science" },
      { subject: "Mathematics", count: 25, topic: "Full Syllabus" },
      { subject: "General Intelligence and Reasoning", label: "General Intelligence & Reasoning", count: 30, topic: "Full Syllabus" },
      { subject: "General Awareness and Current Affairs", label: "General Awareness & Current Affairs", count: 20, topic: "Current Affairs, Railways and Static GK" }
    ]
  },
  "RRB Technician Grade 3": {
    code: "technician-grade-3",
    timerMinutes: 90,
    totalQuestions: 100,
    negativeMarking: 1 / 3,
    sections: [
      { subject: "Mathematics", label: "Mathematics", count: 30, topic: "Full Syllabus" },
      { subject: "General Intelligence and Reasoning", label: "General Intelligence & Reasoning", count: 30, topic: "Full Syllabus" },
      { subject: "General Science", label: "General Science", count: 20, topic: "Full Syllabus" },
      { subject: "General Awareness", label: "General Awareness", count: 20, topic: "Full Syllabus" }
    ]
  }
};

export const ACTIVE_EXAMS = ["RRB NTPC", "RRB Group D", "RRB Technician Grade 3"];

export function sanitizeActiveExam(examName) {
  if (ACTIVE_EXAMS.includes(examName)) return examName;
  const cleaned = String(examName || "").trim();
  if (cleaned.toLowerCase().includes("ntpc")) return "RRB NTPC";
  if (cleaned.toLowerCase().includes("group d") || cleaned.toLowerCase().includes("group-d")) return "RRB Group D";
  if (cleaned.toLowerCase().includes("technician")) return "RRB Technician Grade 3";
  return "RRB NTPC";
}

export function getExamPattern(examName, stage = "", branch = "") {
  const activeExam = sanitizeActiveExam(examName);
  const combinedKey = stage ? `${activeExam} ${stage}` : activeExam;
  const basePattern = EXAM_PATTERNS[combinedKey] || EXAM_PATTERNS[activeExam] || EXAM_PATTERNS["RRB NTPC"];
  return basePattern;
}
