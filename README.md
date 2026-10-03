'10# ACCESSIBILITY COPILOT

Tagline: "Scan. Understand. Fix. Build for everyone."

AI-assisted web accessibility engineering platform that helps developers scan websites, identify real accessibility issues, understand why they matter, and generate practical code fixes.

**IMPORTANT:** Real working application. Findings and score come from actual website scans using Playwright + axe-core. AI is only used for explanation and suggested fixes.

## Architecture
React + TypeScript + Vite (frontend), Django + DRF (backend), Playwright + Chromium + axe-core (scanner), Google Gemini (AI), SQLite (dev) / PostgreSQL (prod).

## Quick Start

### Backend
```powershell
cd accessibility-copilot\backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy ..\.env.example .env  # or create
python manage.py migrate
python manage.py runserver 8000
```

### Frontend
```powershell
cd accessibility-copilot\frontend
npm install
npm run dev  # http://localhost:5173
```

### Demo site
Serve demo-site (e.g. python -m http.server 8001 in demo-site dir).

## Database
SQLite by default. Set DATABASE_URL for PostgreSQL (postgresql://...).

## Security
SSRF protection blocks private/loopback/internal hosts and validates redirects. URLs are normalized and timeouts applied.

## Notes
Automated checks support—not replace—expert accessibility review. No automatic code execution. AI-generated code is copyable/reviewable only.
