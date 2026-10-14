# NM-HireX compact backend

## Flow
1. Admin runs resume ingestion once to scan `data/resumes`.
2. CV text is extracted, structured with GPT-3.5, normalized, stored in PostgreSQL, chunked and embedded into Pinecone.
3. A recruiter uploads a JD through `POST /api/jobs`.
4. The authenticated user becomes `jobs.created_by`; the client cannot choose the owner.
5. JD extraction is stored in `jobs` + `job_requirements`.
6. Screening performs Pinecone semantic retrieval, exact skill matching, evidence retrieval, GPT-5.6 evaluation, deterministic 100-point scoring and ranking.
7. Top 10 are persisted in `job_candidates` and `screening_results`.
8. Admin sees every JD, uploader and Top 10. Users see only their own JDs and Top 10.

## Run
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

## Temporary authentication
The compact implementation uses `X-User-Id` and checks the user in PostgreSQL. Replace this with your real JWT/session dependency before production. Ownership rules already use the authenticated user and never trust `created_by` from the request body.

## Database
Use Alembic to create the tables from `app.models.Base.metadata`. All tables are intentionally kept in `app/models.py`.

## Scoring
Mandatory Skills 30, Experience 25, Domain 15, Preferred Skills 10, Education/Certification 5, Location/Work Mode 5, Notice Period/Availability 5, Other Requirements 5.

Unknown evidence is never treated as satisfied. If the JD has no notice-period requirement, availability contributes 0 points.
