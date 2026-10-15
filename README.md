# NMHireXV2

**AI-Powered Recruitment & Candidate Matching Platform**

NMHireXV2 is an AI-powered recruitment platform designed for job description management, candidate screening, resume matching, ranking, and interview scheduling. It combines deterministic and enhanced matching engines with a unified Match Studio interface for evaluating candidates and comparing screening results.

## Live Testing Environment

**Match Studio:** [Open Live Match Studio](https://hiringassistant-dz8u.onrender.com/test-reranking)

| Test Account | Credentials |
| --- | --- |
| Recruiter email | `test@hirex.com` |
| Recruiter password | `password123` |

> **Note:** These credentials are intended for the public testing environment only. Do not reuse them for production or privileged accounts.

## Current Updates — v1.4

- **Dual-Engine Scoring:** Upgraded the core screening pipeline to evaluate candidates using both the strict deterministic **Classic** engine and the fuzzy-matching **Enhanced** engine.
- **Enhanced Matching Module:** Integrated full-text search (FTS), role-responsibility chunking, and OpenAI adjudication within an isolated `app/services/enhanced/` module to keep enhanced matching logic separate from the classic taxonomy-based engine.
- **JSON Batch Screening:** Added `app/services/naukri_adapter.py` and the `POST /jobs/{job_id}/screen-batch` endpoint to ingest, adapt, and dynamically score raw Naukri JSON candidate exports without requiring database persistence.
- **Deep Analytics:** Refactored the Enhanced engine's decision logic to return a detailed array of candidate rejection reasons, including experience-range gaps and up to five missing mandatory skills.
- **Match Studio UI:** Upgraded `/test-reranking` with a **Candidate Source** toggle (Database or JSON upload), side-by-side **Benchmark** results, and expandable candidate status explanations.

### Matching Modes

| Mode | Description |
| --- | --- |
| **Classic** | Strict, deterministic candidate screening and scoring. |
| **Enhanced** | Fuzzy matching, responsibility analysis, and AI adjudication when needed. |
| **Benchmark** | Side-by-side comparison of Classic and Enhanced screening results. |

Match Studio supports screening candidates from the **database** or a **JSON batch upload**. Enhanced and Benchmark views display detailed status reasoning to help recruiters understand screening decisions.

## Project Structure

```text
NMHireXV2/
├── backend/
│   ├── app/                         # Core application package
│   │   ├── main.py                  # FastAPI entry point and CORS setup
│   │   ├── core/                    # Configuration and setup
│   │   ├── api/                     # API endpoints
│   │   │   └── routes.py
│   │   ├── models/                  # Database schemas
│   │   └── services/                # Business logic and scoring
│   │       ├── tool_functions.py    # Main screening pipeline
│   │       ├── skill_tree.py        # Skill normalization rules
│   │       ├── naukri_adapter.py    # Naukri JSON candidate adapter
│   │       └── enhanced/            # Enhanced matching engine
│   │           ├── ai_adjudicator.py
│   │           ├── match_score.py
│   │           └── pipeline.py
│   ├── scripts/                     # Database and utility scripts
│   ├── tests/                       # Dedicated tests and Match Studio UI
│   │   └── match-agent.html
│   ├── requirements.txt             # Python dependencies
│   ├── test.py                      # Architecture diagnostics
│   └── .env                         # Local environment variables (not committed)
├── frontend-static/                 # Static frontend assets
└── README.md
```

## Running the Application Locally

### 1. Install dependencies

From the repository root, navigate to the backend directory and activate your Python virtual environment.

```cmd
cd backend
pip install -r requirements.txt
```

### 2. Configure environment variables

Create or update `backend/.env` with the environment variables required by your application (for example, API keys or database connection settings). Keep `.env` out of version control.

### 3. Run architecture diagnostics

```cmd
python test.py
```

### 4. Start the FastAPI server

```cmd
uvicorn app.main:app --reload
```

### 5. Open Match Studio

[http://127.0.0.1:8000/test-reranking](http://127.0.0.1:8000/test-reranking)

No npm installation or separate frontend development server is required to access the Match Studio test interface, which is served through FastAPI.

## Deploying on Render

Deploy the backend as a **Python Web Service** with the following configuration:

| Setting | Value |
| --- | --- |
| Branch | `feature/static` |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Configure the values from your local `backend/.env` under **Render → Web Service → Environment**. The local `.env` file is not automatically deployed when excluded from Git.

> **Production note:** Use the start command above on Render, rather than the development-only `--reload` option.

## Dummy Testing — LLM Engineer Job Description

Use the following sample job description to validate JD processing, skill extraction, candidate matching, and ranking.

| Field | Value |
| --- | --- |
| **Job Title** | LLM Engineer / Generative AI Engineer |
| **Experience** | 3–5 years |
| **Location** | Bengaluru / Remote |
| **Employment Type** | Full-Time |

### Description

We are looking for an LLM Engineer to design, develop, and deploy production-ready Generative AI applications using Python, FastAPI, LangChain, LangGraph, and Large Language Models.

### Key Responsibilities

- Develop LLM-powered applications using OpenAI, Claude, and Llama.
- Build Retrieval-Augmented Generation (RAG) pipelines.
- Implement semantic search, embeddings, and reranking.
- Integrate vector databases such as Pinecone, FAISS, and ChromaDB.
- Develop REST APIs using Python and FastAPI.
- Build AI agents using LangChain and LangGraph.
- Optimize LLM response accuracy, latency, and cost.
- Deploy and monitor production AI applications.

### Required Skills

Python, FastAPI, LangChain, LangGraph, LlamaIndex, RAG, Prompt Engineering, OpenAI API, Hugging Face, Vector Databases, PostgreSQL, Docker, REST APIs, SQL, NLP, PyTorch.

### Good-to-Have Skills

MCP, LoRA, QLoRA, AWS, Azure, Kubernetes, LangSmith, RAGAS, MLflow, Multi-Agent Systems.

### Qualifications

- 3–5 years of software engineering or ML experience.
- Hands-on experience with LLM applications.
- Strong understanding of RAG architecture and vector search.
- Experience building and deploying backend APIs.

**Testing purpose:** This job description is sample input for validating JD processing, skill extraction, candidate matching, and ranking.

## Release Status

**Version 1.4 — Deployed.** The dual-engine screening pipeline, JSON batch uploads, enhanced decision explanations, and Match Studio benchmarks are integrated into the current release.
