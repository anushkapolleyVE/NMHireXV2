# NM-HireX static frontend (no npm required)

## Location
Place this `frontend-static/` folder at project root, **beside `backend/` and the original `frontend/`**. Keep original React frontend untouched for reference.

## Run on Windows CMD
From project root: `cd backend` then run `python -m uvicorn app.main:app --reload` using your existing backend environment. Open **http://127.0.0.1:8000/ui/**.

Add the provided mount lines at the bottom of `backend/app/main.py` if keeping your original `main.py`; alternatively use the included modified version from this package.

The browser serves the static UI at `/ui/` and calls `/api/...` on that same origin; no additional CORS policy or frontend process is necessary. You do need all backend dependencies, DB, and credentials *already required by the handed-over backend*. A browser-only visual preview is possible but live actions need a working backend.

## Navigation / supported flows
Recruiter/admin sign in; register; dashboard; jobs; create JD (paste/upload); run screening; inspect ranking and candidate JSON; mark contacted; candidates list/search/detail; outreach status update; recruiter approvals; interview scheduling (navigate to `#schedule?candidate=<job_candidate_uuid>`).

## Limits versus original React UI
This is a practical dependency-free functional baseline, **not a pixel-identical reproduction**. Its design retains the dark glass, navy/blue/teal look. Advanced match-agent charts, candidate side-by-side comparison, WhatsApp invite modal, resume sync dialog, rich animated states, and fully styled candidate profiles are **not yet converted**. The backend routes have not been rewritten.

## Security
Temporary access token uses sessionStorage (per tab); avoid production deployment until auth, uploads, CORS, public scheduling endpoints, and secrets have been audited. Do not commit .env or backend credentials.

## API
All calls are relative `/api` and reuse the existing FastAPI endpoints, including auth and screening. No demo data is fabricated.
