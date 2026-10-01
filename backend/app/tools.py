"""All tool definitions used by the NM-HireX backend.

The definitions describe callable business capabilities. Implementations live
in tool_functions.py so definitions and code stay separate.
"""
TOOLS = [
    {
        "name": "ingest_resume_folder",
        "description": "Scan the configured CV folder, extract candidates, save structured data to PostgreSQL, and index resume chunks in Pinecone.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "create_job",
        "description": "Create a JD for the authenticated recruiter, extract and normalize its requirements, and store it in PostgreSQL.",
        "input_schema": {"type": "object", "properties": {"file_name": {"type": "string"}}, "required": ["file_name"]},
    },
    {
        "name": "screen_job",
        "description": "Retrieve relevant candidates, evaluate evidence, calculate the fixed 100-point score, rank candidates, and persist the Top 10.",
        "input_schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
    },
    {
        "name": "get_user_jobs",
        "description": "Return only jobs uploaded by the authenticated user.",
        "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}}, "required": ["user_id"]},
    },
    {
        "name": "get_user_job_candidates",
        "description": "Return Top 10 candidates for a job owned by the authenticated user.",
        "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}, "job_id": {"type": "string"}}, "required": ["user_id", "job_id"]},
    },
    {
        "name": "get_admin_jobs",
        "description": "Return every JD with its uploader and Top 10 summary for administrators.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_admin_job_candidates",
        "description": "Return the persisted Top 10 candidates for any JD for administrators.",
        "input_schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
    },
]
