# NMHireXV2

NMHireXV2 is an AI-powered recruitment platform designed for job description management, candidate screening, resume matching, ranking, and interview scheduling.

### Current Updates (v1.2)

- Completely refactored the backend directory structure for better modularity and maintainability.
- Separated core API routing, database schemas, and AI business logic into a dedicated `app/` package.
- Cleaned up the backend root by migrating utility, testing, and database scripts into `scripts/` and `tests/` folders.
- Added a `test.py` diagnostic script to automatically verify the integrity of the new architecture.
- Retained the `frontend-static/` folder to serve plain HTML, CSS, and JavaScript directly through FastAPI without npm.
- Kept the existing backend APIs and application logic unchanged.

### Project Structure

```text
backend/
│
├── app/                        # All core application code
│   ├── main.py                 # FastAPI entry point and CORS setup
│   ├── core/                   # Setup and configurations
│   │   ├── config.py
│   │   ├── database.py
│   │   └── auth.py
│   ├── api/                    # API endpoints
│   │   └── routes.py           # Previously api.py
│   ├── models/                 # Database schemas
│   │   └── schema.py           # Previously models.py
│   └── services/               # AI and business logic
│       ├── tool_functions.py   # Main pipeline and scoring logic
│       ├── skill_tree.py       # Skill normalization rules
│       └── tools.py            # LangGraph tools (if retained)
│
├── scripts/                    # Utility and database scripts
│   ├── db/
│   │   ├── create_table.py
│   │   ├── alter_db.py
│   │   ├── apply_gin_indexes.py
│   │   └── run_fts_migration.py
│   └── admin/
│       ├── seed_admin.py
│       ├── run_ingestion.py
│       ├── check_candidate.py
│       └── query.py
│
├── tests/                      # Dedicated testing folder
│   ├── test_extraction.py
│   └── test_pipeline.py
│
├── alembic/                    # Database migrations
├── alembic.ini                 # Alembic configuration
├── cand.json                   # Dummy candidate data
├── requirements.txt
├── test.py                     # Architecture diagnostics
└── .env                        # Environment variables
```

### Running the Application

From the `backend/` directory, with your Python environment activated, run the architecture diagnostics:

```cmd
python test.py
```

Then start the FastAPI server:

```cmd
uvicorn app.main:app --reload
```

Open: http://127.0.0.1:8000/ui/

No npm installation or separate frontend server is required. The static frontend is served directly through FastAPI from `frontend-static/`.

### Dummy Testing — LLM Engineer JD

**Job Title:** LLM Engineer / Generative AI Engineer  
**Experience:** 3–5 Years  
**Location:** Bengaluru / Remote  
**Employment Type:** Full-Time

**Description:**

We are looking for an LLM Engineer to design, develop, and deploy production-ready Generative AI applications using Python, FastAPI, LangChain, LangGraph, and Large Language Models.

**Key Responsibilities:**

- Develop LLM-powered applications using OpenAI, Claude, and Llama.
- Build Retrieval-Augmented Generation (RAG) pipelines.
- Implement semantic search, embeddings, and reranking.
- Integrate vector databases such as Pinecone, FAISS, and ChromaDB.
- Develop REST APIs using Python and FastAPI.
- Build AI agents using LangChain and LangGraph.
- Optimize LLM response accuracy, latency, and cost.
- Deploy and monitor production AI applications.

**Required Skills:**

Python, FastAPI, LangChain, LangGraph, LlamaIndex, RAG, Prompt Engineering, OpenAI API, Hugging Face, Vector Databases, PostgreSQL, Docker, REST APIs, SQL, NLP, PyTorch.

**Good-to-Have Skills:**

MCP, LoRA, QLoRA, AWS, Azure, Kubernetes, LangSmith, RAGAS, MLflow, Multi-Agent Systems.

**Qualifications:**

- 3–5 years of software engineering or ML experience.
- Hands-on experience with LLM applications.
- Strong understanding of RAG architecture and vector search.
- Experience building and deploying backend APIs.

**Testing Purpose:** Used as sample input to validate JD processing, skill extraction, candidate matching, and ranking.

### Status

Backend structural refactoring completed. Functional testing, UI refinements, and AI skill-matching enhancements are ongoing.
