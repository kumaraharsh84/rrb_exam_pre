# Question Bank Collection Prompts

Use this file when asking another tool (for example Claude) to help collect question-bank content in small, reviewable batches.

## Important Expectation

Sending these prompts does **not** mean the full question-bank work is automatically done.

It completes the **collection stage**, but we still need to:

1. review Claude's output
2. remove doubtful questions
3. remove duplicates
4. verify answer indexes
5. improve weak explanations if needed
6. merge accepted questions into the project's bank format

So this file is for **bank collection**, not full automatic completion.

## Recommended Batch Size

- 25 questions per batch

This is the best size for:
- quality control
- reviewability
- avoiding messy output

## Recommended Collection Order

### Mathematics
- Percentage
- Ratio and Proportion
- Profit and Loss
- Time and Work

### Reasoning
- Coding-Decoding
- Blood Relations
- Direction Sense
- Number Series and Analogies

### Science
- Laws of Motion
- Matter, Atoms and Chemical Reactions
- Cell Biology and Human Respiratory System

### General Awareness
- Indian Polity
- Indian History and Geography
- Sports, Awards and Important Days

## Setup Prompt

Send this first:

```text
You are helping me build a clean, verified question bank for an RRB exam preparation app.

Current app scope:
- Subject Test
- Final Full-Length Mock Test

Your role:
- collect railway-exam-style MCQs from trusted educational / exam-prep sources online
- verify answer correctness
- rewrite clearly when needed
- normalize into my JSON format
- remove duplicates
- keep RRB level appropriate

Do NOT dump copied text blindly.
Do NOT return long copyrighted source text.
Do NOT use doubtful or low-quality sources.

Use this JSON format exactly:

{
  "exam": "RRB NTPC",
  "subject": "Mathematics",
  "topic": "Percentage",
  "difficulty": "basic",
  "question": "Out of 500 railway applicants, 320 cleared Stage 1. What percent cleared the stage?",
  "options": ["A) 60%", "B) 62%", "C) 64%", "D) 68%"],
  "answer": 2,
  "explanation": "Step 1: ... Step 2: ... Step 3: ...",
  "source_type": "exam-prep",
  "source_name": "Site name",
  "source_url": "https://...",
  "verified": true
}

Rules:
- exactly 4 options
- answer must be 0-indexed
- explanation must support the answer
- no duplicates
- no vague questions
- no doubtful questions
- keep questions concise and exam-style
- use trusted sources only

I will now send you one topic at a time in small batches.
Wait for my next message.
```

## Batch Prompt Template

Use this reusable prompt for every batch:

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: [SUBJECT]
- Topic: [TOPIC]

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

## Review / Fix Prompt

If the output looks weak, send this:

```text
Review and fix the previous batch.

Please do all of the following:
- remove duplicates
- remove doubtful or incorrect questions
- fix wrong answer indexes
- improve weak explanations
- ensure each question matches the requested topic exactly
- keep only verified, clean JSON entries

Return the corrected final JSON array only.
```

## Ready-to-Send Prompts

### Batch 1 - Mathematics - Percentage

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: Mathematics
- Topic: Percentage

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 2 - Mathematics - Ratio and Proportion

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: Mathematics
- Topic: Ratio and Proportion

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 3 - Mathematics - Profit and Loss

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: Mathematics
- Topic: Profit and Loss

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 4 - Mathematics - Time and Work

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: Mathematics
- Topic: Time and Work

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 5 - Reasoning - Coding-Decoding

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Intelligence & Reasoning
- Topic: Coding-Decoding

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 6 - Reasoning - Blood Relations

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Intelligence & Reasoning
- Topic: Blood Relations

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 7 - Reasoning - Direction Sense

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Intelligence & Reasoning
- Topic: Direction Sense

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 8 - Reasoning - Number Series and Analogies

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Intelligence & Reasoning
- Topic: Number Series and Analogies

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 9 - Science - Laws of Motion

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Science
- Topic: Laws of Motion

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep Class 10 / RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 10 - Science - Matter, Atoms and Chemical Reactions

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Science
- Topic: Matter, Atoms and Chemical Reactions

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep Class 10 / RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 11 - Science - Cell Biology and Human Respiratory System

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Science
- Topic: Cell Biology and Human Respiratory System

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep Class 10 / RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 12 - General Awareness - Indian Polity

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Awareness
- Topic: Indian Polity

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 13 - General Awareness - Indian History and Geography

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Awareness
- Topic: Indian History and Geography

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

### Batch 14 - General Awareness - Sports, Awards and Important Days

```text
Next batch

Collect and normalize 25 verified MCQs for:

- Exam style: RRB NTPC / RRB Group D
- Subject: General Awareness
- Topic: Sports, Awards and Important Days

Requirements:
- use trusted educational / exam-prep sources
- rewrite clearly when needed
- remove duplicates
- verify answer correctness
- keep RRB level appropriate

Return:
1. JSON array only
2. then a short summary:
   - candidates reviewed
   - accepted count
   - sources used
   - doubtful items if any
```

## Final Reminder

Use one batch at a time.
Do **not** send all 14 batch prompts together.

Best workflow:

1. send setup prompt once
2. send one batch prompt
3. review output
4. send review/fix prompt if needed
5. move to next batch
