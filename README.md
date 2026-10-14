# NMHireXV2

NMHireXV2 is an AI-powered recruitment platform designed for job description management, candidate screening, resume matching, ranking, and interview scheduling.

### Current Updates

- Added a new `frontend-static/` folder containing plain HTML, CSS, and JavaScript.
- Removed the need for npm, React, and Vite to run the new frontend.
- Updated `backend/app/main.py` to serve the static frontend directly through FastAPI.
- Retained the existing frontend for reference.
- Kept the existing backend APIs and application logic unchanged.
- Initial functionality review and testing are in progress.

### Project Structure

```text
NMHireXV2/
├── frontend/             # Existing React frontend
├── frontend-static/      # New HTML/CSS/JS frontend
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── backend/
│   ├── app/
│   │   └── main.py       # Updated to serve static frontend
│   └── requirements.txt
└── README.md
```

### Running the Application

From the `backend/` directory, with the Python environment activated:

```cmd
python -m uvicorn app.main:app --reload
```

Open: `http://127.0.0.1:8000/ui/`

No npm installation or separate frontend server is required.

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

Initial static frontend integration completed. Functional testing and further improvements are ongoing.