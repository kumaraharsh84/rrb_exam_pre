# RRB AI Practice Center
## Full Frontend UI / UX Design Brief For Manus AI

This file is the current design handoff brief for the full frontend redesign of the project.
It should be shared with Manus AI as the source-of-truth UI / UX brief.

The goal of this file is not to explain code implementation.
The goal is to clearly explain what the product is, which pages exist, what each page must do, and how the entire frontend should be designed as one consistent system.

---

## 1. Project Summary

Project name:
- `RRB AI Practice Center`

Project type:
- multi-page RRB exam preparation web app

Current tech direction:
- static frontend
- HTML
- vanilla JavaScript
- multi-page flow
- local state heavy frontend
- AWS Lambda + Bedrock backend for AI-generated questions

Current product direction:
- this is not a landing page
- this is not a marketing website
- this is a working study product
- the UI should feel like a serious exam preparation platform

---

## 2. Main Product Goal

The frontend should help a student:
- sign in easily
- choose the target exam
- configure practice quickly
- take tests with focus
- review results clearly
- revisit mistakes
- track progress over time

The redesign should make the product feel:
- premium
- trustworthy
- academic
- focused
- practical
- modern
- exam-oriented

It should not feel:
- random
- flashy without purpose
- decorative like a startup showcase
- overly gamified
- cluttered
- confusing

---

## 3. Global Design Direction

Manus AI should redesign the frontend as one coherent system.

Important expectations:
- all pages should feel like part of one product
- same visual language should carry across the entire app
- spacing, hierarchy, buttons, inputs, panels, tabs, cards, and empty states should feel related
- desktop and mobile behavior should be intentionally designed
- no page should feel forgotten or low-priority

The design system should define:
- typography system
- color system for light mode
- color system for dark mode
- buttons
- form fields
- cards
- tabs
- tables or list rows
- pills / badges
- modal styles
- empty states
- loading states
- error states

---

## 4. Hard Rules

Manus AI should follow these rules:

- redesign the frontend UI / UX across all pages
- preserve the existing product structure and major flow
- do not turn the app into a marketing homepage
- do not remove key workflows
- do not oversimplify the app into only 2 or 3 pages
- do not collapse everything into one dashboard
- do not design only the “main” pages and ignore the utility pages
- do not make simple pages unnecessarily tall
- do not create awkward first-load scrollbars on pages like login or exam selection
- do not create layouts that are hard to integrate with existing JavaScript

Important:
- the result must remain implementation-friendly
- forms, action areas, stateful cards, profile areas, filters, and page sections should remain easy to wire back to the current frontend logic

---

## 5. Full Page List To Design

All of these pages should be included in the redesign:

Core flow pages:
1. `frontend/login.html`
2. `frontend/exam-select.html`
3. `frontend/dashboard.html`
4. `frontend/quiz.html`
5. `frontend/score.html`

Review and utility pages:
6. `frontend/history.html`
7. `frontend/final-mock-history.html`
8. `frontend/bookmarks.html`
9. `frontend/wrong-questions.html`
10. `frontend/analysis.html`
11. `frontend/leaderboard.html`
12. `frontend/exam-dashboard.html`

Optional entry page if needed:
13. `frontend/index.html`

Important:
- do not design only login, dashboard, and quiz
- every listed page should get a proper designed structure

---

## 6. Current Product Flow

The main student journey is:

1. Login / create account
2. Choose target exam
3. Open dashboard
4. Start one of the available study flows
5. Take quiz / mock
6. View score and analysis
7. Revisit history, bookmarks, wrong questions, and analytics pages

The frontend redesign must support this whole journey cleanly.

---

## 7. Key Study Flows That Must Be Supported

The UI must clearly support these working product flows:

- Sign in / create account
- Exam selection
- Topic practice
- Chapter practice
- Weak topic auto-drill
- Mock test without timer
- Final mock with timer
- Score review
- Wrong question retry
- Bookmark review
- Test history review
- Final mock history review
- Analysis review
- Leaderboard view
- Exam-wise dashboard summary

These flows should feel intentional and clearly different where needed.

---

## 8. Page-By-Page Design Requirements

### 8.1 Login Page

File:
- `frontend/login.html`

Purpose:
- first product entry point
- sign in or create account

Design expectations:
- polished app-like login experience
- strong first impression
- balanced two-panel or similarly strong layout
- clear sign in vs create account separation
- compact but premium feel
- should fit well on desktop without awkward scroll
- should still feel complete on mobile

Must visually support:
- theme toggle
- sign in tab
- create account tab
- email input
- password input
- optional name field in sign up state
- continue / submit button
- current setup or helper info block

The page should feel:
- serious
- elegant
- not empty
- not like a template auth form

---

### 8.2 Exam Selection Page

File:
- `frontend/exam-select.html`

Purpose:
- step after login
- user selects the target exam

Design expectations:
- clear step-based progression feel
- exam cards should feel premium and selectable
- selected state should be obvious
- strong CTA for continuing
- should not feel like an empty placeholder page

Must visually support:
- step indicator
- page title and short supporting copy
- exam cards for supported exams
- selected state
- previous action
- confirm choice action
- theme toggle

The page should feel like:
- a real onboarding step
- not a temporary screen

---

### 8.3 Dashboard

File:
- `frontend/dashboard.html`

Purpose:
- main control center of the product

This is one of the most important pages.

Design expectations:
- clear control-center structure
- strong visual hierarchy
- major actions should be immediately visible
- secondary review/tracking information should feel organized, not crowded
- user should instantly understand what to do next

Must visually support:
- top header
- brand identity
- theme toggle
- profile dropdown
- current exam context
- practice configuration section
- practice style options
- subject selector
- topic selector
- chapter practice area
- chapter search / chapter selection
- difficulty selection
- question count
- quiz mode
- continue to test CTA
- weak drill CTA
- final mock launch card
- last attempt snapshot
- subject completion overview
- navigation links to review pages

Important product meaning:
- dashboard should be a study control center
- not a cluttered overview wall

---

### 8.4 Quiz Page

File:
- `frontend/quiz.html`

Purpose:
- active test-taking environment

Design expectations:
- focused exam experience
- strong readability
- low clutter
- action clarity
- strong current-state feedback

Must visually support:
- current exam / subject / topic context
- timer
- progress state
- question number and status
- question body
- options
- bookmark action
- mark for review
- next / continue / submit actions
- question palette
- final mock section jump if needed
- loading state while questions are being generated
- error or retry state if generation fails

Different test contexts should feel visibly distinct:
- practice
- chapter practice
- weak drill
- mock without timer
- final mock
- bookmark retry
- wrong question retry

The page should feel:
- exam-like
- focused
- high-clarity

---

### 8.5 Score Page

File:
- `frontend/score.html`

Purpose:
- result and analysis after test completion

Design expectations:
- report-like
- serious
- readable
- clearly sequenced from high-level summary to deeper review

Must visually support:
- result header
- main score / performance summary
- correct / wrong / unanswered counts
- accuracy
- section breakdown
- strongest area
- weakest area
- insight cards
- retry flow for weak area
- wrong answers review
- practice again flow

The page should feel like:
- a serious academic performance report
- not a random stack of widgets

---

### 8.6 History Page

File:
- `frontend/history.html`

Purpose:
- review normal practice and non-final-mock attempts

Design expectations:
- clean filtering
- useful list layout
- easy scan of past attempts
- strong empty state if no history exists

Must visually support:
- page heading
- current exam context
- filter controls
- history cards or rows
- score summary per attempt
- retry / open actions
- clear history action

---

### 8.7 Final Mock History Page

File:
- `frontend/final-mock-history.html`

Purpose:
- dedicated review of final mock attempts

Design expectations:
- clearly distinct from regular history
- should emphasize full exam simulation attempts

Must visually support:
- final mock history identity
- list of past final mocks
- key metrics per attempt
- re-open / review actions
- empty state
- clear history action

---

### 8.8 Bookmarks Page

File:
- `frontend/bookmarks.html`

Purpose:
- saved questions for later revision

Design expectations:
- bookmarks should feel like a serious revision area
- not just a plain loose list
- grouping should feel useful

Must visually support:
- grouped saved questions
- subject/topic context
- save count or grouping info
- practice again
- remove bookmark
- empty state
- clear bookmarks action

---

### 8.9 Wrong Questions Page

File:
- `frontend/wrong-questions.html`

Purpose:
- revision of previously answered-wrong questions

Design expectations:
- should feel like a guided mistake review page
- must help the student understand what to fix next

Must visually support:
- grouped wrong questions
- retry actions
- remove item
- clear all state
- empty state
- revision-focused copy

This page should feel:
- useful
- corrective
- structured

---

### 8.10 Analysis Page

File:
- `frontend/analysis.html`

Purpose:
- subject-wise and performance insight page

Design expectations:
- stronger analytical feel
- not overly visual noise
- should present strengths, weaknesses, and actionable follow-up

Must visually support:
- overall analysis summary
- subject performance cards
- weakest-area focus
- strong-area indicators
- weak drill launch if available
- empty state if not enough history exists

---

### 8.11 Leaderboard Page

File:
- `frontend/leaderboard.html`

Purpose:
- compare performance across ranking ranges

Design expectations:
- should feel competitive but clean
- not flashy
- should remain readable and structured

Must visually support:
- leaderboard heading
- exam context
- range filters
- ranking table or list
- current user highlight
- loading state
- empty state

---

### 8.12 Exam Dashboard Page

File:
- `frontend/exam-dashboard.html`

Purpose:
- exam-wise performance summary

Design expectations:
- should help student compare progress across exams or exam categories
- should feel summary-driven and easy to scan

Must visually support:
- summary cards
- attempt count
- average performance
- best score
- exam-specific insight
- empty state if no attempt data exists

---

## 9. Navigation And Shared App Shell

The product should have a shared navigation experience across internal pages.

Shared design expectations:
- consistent header
- consistent theme toggle
- consistent profile access
- consistent sidebar or navigation system where relevant
- mobile navigation should not feel like an afterthought

The user should never feel lost moving between:
- dashboard
- history
- bookmarks
- wrong questions
- analysis
- leaderboard
- exam dashboard

---

## 10. Visual Hierarchy Expectations

The hierarchy should be obvious on every page:

- page title
- section title
- supporting copy
- primary action
- secondary action
- data region
- empty / loading / error message

Strong actions should always look strong.
Secondary controls should not visually compete with the main action.

Examples:
- `Start Practice`
- `Continue to Test`
- `Start Final Mock`
- `Submit Test`
- `Practice Again`

These actions should feel intentional and visually important.

---

## 11. Test Mode Context Requirements

The UI must clearly communicate the current study mode.

Examples:
- Practice
- Chapter Practice
- Weak Topic Drill
- Mock Test
- Final Mock
- Bookmark Revision
- Wrong Question Retry

The app should not feel like the same quiz screen with only a small title change.

Mode context should be visible through:
- labels
- page copy
- visual state
- section or pill treatment

---

## 12. Final Mock UX Requirements

Final mock is a major product feature.

The redesign must support:
- exam-specific paper identity
- timer importance
- section-wise feel
- submit seriousness
- result continuity into score page

Important:
- final mock should feel more serious than normal practice
- it should feel like a real exam simulation flow

The exam context should stay visible in:
- dashboard launch area
- quiz page
- score page
- final mock history

---

## 13. Revision UX Requirements

Revision is one of the strongest parts of the product and should be treated as a first-class experience.

Need strong UX for:
- bookmarks
- wrong questions
- weak drill
- practice again
- retry flows
- history-driven learning

The student should quickly understand:
- what they did before
- where they are weak
- what they should practice next

The redesign should make revision feel:
- guided
- useful
- smart
- motivating

---

## 14. Responsive Requirements

Every page should be properly considered for:
- desktop
- tablet
- mobile

Important expectations:
- login should feel complete on mobile
- exam selection should still feel like a step flow on mobile
- dashboard sections should stack cleanly
- quiz palette and actions should remain usable on smaller screens
- score page should remain readable when stacked
- utility pages should not become messy on mobile

No page should feel broken, cropped, or unfinished on smaller screens.

---

## 15. Empty, Loading, And Error States

The design brief must include proper state design for the whole app.

Empty states needed for:
- no history
- no final mock history
- no bookmarks
- no wrong questions
- no analysis data
- no leaderboard entries

Loading states needed for:
- generating quiz
- generating final mock
- loading history
- loading analysis
- loading leaderboard

Error states needed for:
- failed question generation
- failed retry session
- no data found
- missing saved session
- backend delay or unavailable state

These states should feel intentionally designed, not like raw fallback text.

---

## 16. Content And Tone

The tone of the product should feel:
- supportive
- smart
- serious
- student-friendly

Copy should avoid:
- fake startup jargon
- hype-heavy language
- childish gamification language

Preferred tone:
- practical
- calm
- clear
- academic

---

## 17. Important Product Notes

Current supported live exams:
- `RRB NTPC`
- `RRB Group D`
- `RRB Technician Grade 3`

Important:
- old removed exams should not accidentally become part of the new main UI unless specifically reintroduced later

Also important:
- this is a multi-page app now
- the redesign must fully respect that direction
- utility pages are part of the product, not secondary leftovers

---

## 18. Final Manus AI Instruction

Please redesign the complete frontend UI / UX for this product as a unified multi-page exam preparation system.

Design all pages listed in this brief.

Preserve the current product flow and major feature set.

Focus on:
- strong hierarchy
- premium academic visual language
- practical usability
- responsive behavior
- clear state design
- serious exam-product feel

Do not return only a partial concept for a few pages.
The redesign should cover the full user journey and all major utility pages in the same system.
