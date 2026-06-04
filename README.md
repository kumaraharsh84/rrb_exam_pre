# RRB AI Practice Center

RRB exam preparation web app with a static multi-page frontend and an AWS Lambda + Bedrock backend for AI-generated questions.

## Current Project State

This project is currently working as a personal-use practice platform with:

- local demo auth
- exam selection
- dashboard-focused test setup
- topic practice
- chapter practice
- weak topic auto-drill
- subject completion tracking
- mock test without timer
- final mock with timer
- wrong-question review and retry flow
- bookmarks
- analysis and leaderboard pages
- score analysis with explanation-based review

## Supported Exams

- `RRB NTPC`
- `RRB Group D`
- `RRB Technician Grade 3`

`RRB JE` has been removed from the live app flow and current frontend experience.

## Current Frontend Page Structure

The app now follows a dedicated multi-page structure instead of mixing all review tools into one dashboard.

### Core Flow Pages

1. `frontend/login.html`
2. `frontend/exam-select.html`
3. `frontend/dashboard.html`
4. `frontend/quiz.html`
5. `frontend/score.html`

### Review And Tracking Pages

6. `frontend/history.html`
7. `frontend/final-mock-history.html`
8. `frontend/bookmarks.html`
9. `frontend/wrong-questions.html`
10. `frontend/analysis.html`
11. `frontend/leaderboard.html`
12. `frontend/exam-dashboard.html`

## Page Responsibilities

### `dashboard.html`

Used only for:

- exam setup
- topic practice setup
- chapter practice setup
- weak drill launch
- final mock launch
- last attempt snapshot
- subject completion overview

### Dedicated Utility Pages

These are now separate pages to keep the dashboard clean:

- `history.html`
  - normal test history
- `final-mock-history.html`
  - final full-length mock history
- `bookmarks.html`
  - bookmarked questions only
- `wrong-questions.html`
  - merged wrong answers + saved mistake revision queue
- `analysis.html`
  - subject accuracy and weakest-area insights
- `leaderboard.html`
  - range-based leaderboard view
- `exam-dashboard.html`
  - exam-wise attempt summary cards

## Current Test Modes

### Practice Mode

- topic-focused learning mode
- user selects subject + one topic

### Chapter Practice

- user selects multiple chapters/topics from the chosen subject
- chapter list opens only when needed
- supports:
  - `Full Subject Mix`
  - `Selected Chapters Only`
  - `Balanced Sampler`

### Weak Topic Auto-Drill

- dashboard button
- built from weak topics found in local history
- auto-launches a short targeted drill

### Mock Test Without Timer

- exam-style test feeling
- no timer pressure
- useful for self-check and subject revision

### Final Mock

- full exam-pattern simulation
- timer active
- section-wise distribution from `exam-patterns.js`

## Implemented Dashboard Features

- profile dropdown
- theme toggle with saved preference
- change exam
- logout
- current exam badge
- subject and topic sync
- chapter practice selector
- compact chapter drawer with search
- visible `Continue to Test` action
- weak drill button with live badge
- subject completion cards
- last attempt snapshot
- final mock launch card
- quick links to dedicated review pages

## Revision And Tracking Features

- `Test History`
- `Final Mock History`
- `Bookmarks`
- `Wrong Questions`
- `Last Attempt Snapshot`
- recent questions / recent patterns tracking for anti-repeat behavior

### Wrong Questions Flow

The old overlap between `Mistake Book` and `Wrong Questions` has been simplified.

Current behavior:

- wrong answers from tests are saved
- older mistake entries are merged into the same revision flow
- everything is reviewed from `wrong-questions.html`
- each entry can be retried or removed
- items are grouped subject-wise

## Score And Analysis Features

- score summary
- correct / wrong / unanswered count
- accuracy
- negative marking support
- section breakdown
- strong / weak insights
- weakest-subject retry flow
- answer review with explanations
- practice-again flow for wrong questions

## Leaderboard

Leaderboard support is now available on a dedicated page:

- `frontend/leaderboard.html`

Current behavior:

- current exam leaderboard view
- filters:
  - `Today`
  - `This Week`
  - `All Time`
- current user row highlight
- local fallback ranking works even without Supabase keys

If real Supabase credentials are added in `frontend/js/config.js`, the leaderboard can sync to a live backend table.

## Current Exam Patterns

### RRB NTPC

- `100 questions`
- `90 minutes`
- `Math 30`
- `Reasoning 30`
- `General Awareness 40`

### RRB Group D

- `100 questions`
- `90 minutes`
- `Math 25`
- `Reasoning 30`
- `General Science 25`
- `General Awareness 20`

### RRB Technician Grade 3

- `100 questions`
- `90 minutes`
- `Math 30`
- `Reasoning 30`
- `General Science 20`
- `General Awareness 20`

## Syllabus Source

The active syllabus source for exam-wise subject/topic mapping is:

- `frontend/js/rrb-syllabus-data.js`

This file is currently used for:

- subject dropdown options
- topic dropdown options
- chapter practice selections
- subject completion calculations

## Key Frontend Files

- `frontend/js/app.js`
  - auth-like flow
  - dashboard state
  - exam/subject/topic/chapter sync
  - dedicated utility-page setup
  - history, bookmarks, wrong-question rendering
  - weak drill logic
  - subject completion cards
  - analytics and exam dashboard rendering

- `frontend/js/quiz.js`
  - quiz generation flow
  - chapter practice handling
  - weak drill handling
  - continue/finish button flow
  - submit flow
  - score save
  - history save
  - wrong-question save for revision

- `frontend/js/leaderboard.js`
  - leaderboard rendering
  - local fallback leaderboard logic
  - optional Supabase-backed ranking sync

- `frontend/js/exam-patterns.js`
  - final mock patterns

- `frontend/js/rrb-syllabus-data.js`
  - exam-wise subjects and topics

- `frontend/js/api.js`
  - frontend API request builder
  - sends exam/stage/mode/chapter/drill context to backend
  - falls back more safely when remote fetch is unavailable

- `frontend/css/app-shell.css`
  - shared utility-page shell
  - same theme styling for new review pages
  - dark mode shell overrides

## Backend

Main backend file:

- `backend/lambda_function.py`

Current backend expects:

- `exam`
- `stage`
- `branch` if needed
- `subject`
- `topic`
- `mode`
- `difficulty`
- `practiceType`
- `selectedChapters`
- `chapterQuestionMode`
- `drillTopics`
- recent question exclusion context
- recent pattern exclusion context

Backend prompt shaping currently supports:

- topic practice
- chapter practice
- weak drill
- mock without timer
- final mock

## Local Run

Best local run path:

```powershell
cd "C:\Users\kumar\Desktop\project\rrb exam pre"
python -m http.server 5500
```

Then open:

```text
http://localhost:5500/rrb-exam-prep/frontend/login.html
```

Important:

- keep terminal open while testing
- if `ERR_CONNECTION_REFUSED` appears, local server is not running
- if old UI changes still appear, do `Ctrl + F5` once to hard refresh

## Project Structure

```text
rrb-exam-prep/
|-- frontend/
|   |-- login.html
|   |-- exam-select.html
|   |-- dashboard.html
|   |-- quiz.html
|   |-- score.html
|   |-- history.html
|   |-- final-mock-history.html
|   |-- bookmarks.html
|   |-- wrong-questions.html
|   |-- analysis.html
|   |-- leaderboard.html
|   |-- exam-dashboard.html
|   |-- css/
|   |   |-- app-shell.css
|   |   `-- style.css
|   `-- js/
|       |-- api.js
|       |-- app.js
|       |-- config.js
|       |-- exam-patterns.js
|       |-- leaderboard.js
|       |-- question-bank.js
|       |-- quiz.js
|       `-- rrb-syllabus-data.js
|-- backend/
|   |-- lambda_function.py
|   `-- requirements.txt
|-- AI_HANDOFF.md
|-- LOCAL_START.md
|-- UI_UX_DISCUSSION.md
|-- start-project.bat
`-- README.md
```

## Current Constraints

- auth is local demo auth only
- localStorage is used heavily, so state is browser-local
- backend deploy/update still needs to be done separately after local code changes
- Supabase live sync still depends on adding real credentials
- some legacy references may still exist in docs or older notes, but live app uses the current frontend files only

## Current Direction

The project is now structured with this product logic:

- `dashboard = start tests and see quick overview`
- `other pages = review, track, revise, and compare`

This keeps the main action page cleaner and makes the app feel more complete.

## Next Recommended Work

- full browser click-by-click smoke test
- live Supabase setup if online leaderboard is needed
- final documentation sync in handoff notes if more pages/features are added later
- optional deeper cleanup of older legacy comments/data blocks

## Summary

This project is no longer a basic static frontend. It now supports:

- full entry flow
- 3 active RRB exams
- 12-page frontend structure
- topic practice
- chapter practice
- weak-topic drill
- subject completion insights
- mock without timer
- final mock with timer
- dedicated review pages
- wrong-question revision flow
- result analysis and leaderboard support

For the current personal-use phase, the app is in a strong and much cleaner working state.
