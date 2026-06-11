# Local Start Guide

Project ko local me chalane ka best aur current working method ye hai.

## Recommended Method

PowerShell me ye command run karo:

```powershell
cd "C:\Users\kumar\Desktop\project\rrb exam pre"
python -m http.server 5500
```

Agar `python` command kaam na kare to:

```powershell
cd "C:\Users\kumar\Desktop\project\rrb exam pre"
py -m http.server 5500
```

Phir browser me ye URL kholo:

```text
http://localhost:5500/rrb-exam-prep/frontend/login.html
```

## Important Notes

- terminal window open rehni chahiye
- agar terminal band kar doge to site band ho jayegi
- agar `ERR_CONNECTION_REFUSED` aaye to matlab local server run nahi ho raha
- current stable URL yehi hai:
  - `http://localhost:5500/rrb-exam-prep/frontend/login.html`
- hard refresh ke liye `Ctrl + F5` use karo agar old UI cache dikh raha ho

## Optional Batch File

Project me batch files bhi hain:

- `start-project.bat`
- `start-frontend.bat`

Lekin safest manual method abhi parent folder se server run karna hai.

## Current Main Page Set

Live frontend ab multi-page structure use karta hai.

Core flow:

- `login.html`
- `exam-select.html`
- `dashboard.html`
- `quiz.html`
- `score.html`

Dedicated review pages:

- `history.html`
- `final-mock-history.html`
- `bookmarks.html`
- `wrong-questions.html`
- `analysis.html`
- `leaderboard.html`
- `exam-dashboard.html`

## Backend Note

Backend local machine par alag se run nahi hota.

Current backend stack:

- AWS Lambda
- API Gateway
- Bedrock

Isliye local testing ke liye normally sirf frontend server run karna hota hai.
