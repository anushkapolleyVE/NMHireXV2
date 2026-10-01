"""All actual NM-HireX business functions.

Each function is intentionally small and directly composable; LangGraph is not
required for this deterministic pipeline.
"""
import os
import shutil
import tempfile
import zipfile

import hashlib, json, re, time, logging, os, base64
from pathlib import Path
import gdown
from uuid import UUID
from sqlalchemy import select, delete, text, and_, or_, func
from sqlalchemy.orm import Session
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
import pymupdf
from PIL import Image
from .config import settings
from datetime import datetime
from .models import (
    User,
    Job,
    JobRequirement,
    Candidate,
    Resume,
    CandidateSkill,
    CandidateExperience,
    CandidateEducation,
    CandidateCertification,
    CandidateProject,
    JobCandidate,
    ScreeningResult,
    ScreeningRun,
    AIExtractionLog,
    CandidateContact,
)

OPENAI_API_KEY = settings.OPENAI_API_KEY

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
luna_client = openai_client

OCR_MODEL = "gpt-4o"


# ------------------------------------------------------------
# FILE HELPERS
# ------------------------------------------------------------
def _text_is_insufficient(text: str) -> bool:
    """Return True when native PDF extraction is too sparse to trust."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) < 250:
        return True

    # A page containing mostly symbols/noise is also a good OCR candidate.
    alnum = sum(ch.isalnum() for ch in cleaned)
    return alnum < max(100, int(len(cleaned) * 0.45))


def _ocr_pdf_page(page, page_number: int, native_text: str) -> str:
    """Render one PDF page and use GPT-5.6 Luna to recover only image-based text.

    Native pypdf text is preserved. Luna is asked for additional text visible
    in the page image so partial image sections are not lost or duplicated.
    """
    if luna_client is None:
        logging.warning(
            "OPENAI_API_KEY is not configured; skipping OCR for page %s.",
            page_number,
        )
        return ""

    try:
        pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        image_bytes = pix.tobytes("png")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = luna_client.responses.create(
            model=OCR_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Recover text from image-based content on this CV page. "
                                "The native PDF text extracted by pypdf is provided below. "
                                "Return ONLY additional readable text that is present in the "
                                "page image but missing from the native text. This includes "
                                "image-based experience, skills, education, certifications, "
                                "projects, tables, dates, companies, job titles and other "
                                "resume information. Do not repeat text already represented "
                                "in the native text. Do not summarize. Do not invent or infer. "
                                "If the image contains no additional text, return an empty "
                                "response.\n\n"
                                f"NATIVE PDF TEXT:\n{native_text[:12000]}"
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{image_b64}",
                        },
                    ],
                }
            ],
        )

        return (response.output_text or "").strip()

    except Exception as error:
        logging.warning(
            "OCR failed for PDF page %s: %s",
            page_number,
            error,
        )
        return ""


def _read_pdf_with_ocr(path: str) -> str:
    """Extract PDF text with pypdf and OCR only pages where native text is insufficient."""
    p = Path(path)
    pypdf_logger = logging.getLogger("pypdf")
    previous_level = pypdf_logger.level

    try:
        pypdf_logger.setLevel(logging.ERROR)

        reader = PdfReader(str(p))

        extracted_text = "\n".join(
            (page.extract_text() or "")
            for page in reader.pages
        )

        if _text_is_insufficient(extracted_text):
            print(f"   [INFO] PDF {p.name} appears to be scanned. Running OCR fallback...")
            try:
                ocr_text = []
                doc = pymupdf.open(str(p))
                for page_num, page in enumerate(doc):
                    native_page_text = ""
                    if page_num < len(reader.pages):
                        native_page_text = reader.pages[page_num].extract_text() or ""
                    page_text = _ocr_pdf_page(page, page_num, native_page_text)
                    ocr_text.append(page_text)
                extracted_text = extracted_text + "\n" + "\n".join(ocr_text)
            except Exception as e:
                print(f"   [WARNING] OCR fallback failed for {p.name}: {e}")

        return extracted_text

    finally:
        pypdf_logger.setLevel(previous_level)


def read_file(path: str) -> str:
    """
    Read a supported PDF, DOCX, or TXT file.

    PDFs use pypdf first and GPT-5.6 Luna only as a fallback for
    scanned/image-heavy pages. The returned text is then passed unchanged
    into the existing JSON extraction pipeline.
    """
    p = Path(path)

    if p.suffix.lower() == ".pdf":
        return _read_pdf_with_ocr(str(p))  

    if p.suffix.lower() == ".docx":
        doc = Document(str(p))
        text_lines = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_lines.append(paragraph.text.strip())
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip().replace('\n', ' '))
                if row_text:
                    text_lines.append(" | ".join(row_text))
        return "\n".join(text_lines)

    if p.suffix.lower() == ".txt":
        return p.read_text(
            encoding="utf-8",
            errors="ignore"
        ) 

    if p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
        try:
            if luna_client is None:
                raise ValueError("OPENAI_API_KEY is not configured; cannot OCR image files.")
            img = Image.open(str(p))
            from io import BytesIO
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            image_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            response = luna_client.responses.create(
                model=OCR_MODEL,
                input=[{
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "Extract all text from this resume image exactly as it appears. Do not add any formatting or commentary."},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{image_b64}"}
                    ]
                }]
            )
            return (response.output_text or "").strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from image: {e}")

    raise ValueError(
        f"Unsupported file type: {p.suffix}"
    )

def file_hash(path: str) -> str:
    """Input: file path. Output: SHA-256 hex digest used for duplicate detection."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()



# ------------------------------------------------------------
# AI EXTRACTION
# ------------------------------------------------------------
def _json_completion(prompt: str, model: str) -> dict:
    """Input: prompt/model. Output: validated JSON object returned by the configured LLM."""
    response = openai_client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": "Return only valid JSON."}, {"role": "user", "content": prompt}],
    )
    return json.loads(response.choices[0].message.content)

def extract_jd(text: str) -> dict:
    """Input: JD text. Output: structured JD requirements. Unknown facts must be null/empty."""
    prompt = f"""
Extract this job description into JSON with exactly these keys:
job_title, min_experience_years, max_experience_years, mandatory_skills,
preferred_skills, education, certifications, domains, responsibilities,
location, work_mode, notice_period_days, other_requirements, confidence_score.
Rules: preserve specific skills exactly; only classify a skill as mandatory when
required/essential; words such as advantageous/preferred/nice-to-have belong in
preferred_skills; never infer missing experience, location, notice period or education.
JD:\n{text[:30000]}
"""
    return _json_completion(prompt, settings.EXTRACTION_MODEL)

def extract_resume(text: str) -> dict:
    """Input: CV text. Output: structured candidate profile with explicit nulls for unsupported facts."""
    prompt = f"""
Extract the CV into JSON with exactly these keys:
name, email, phone, location, total_experience_years, current_company, current_role,
notice_period_days, profile_summary, skills, experiences, education, certifications, projects.
Rules: never guess missing values; never turn a technology into a company or role;
preserve specific skills such as Django as Django and use parent_skill only as a relationship.
CV:\n{text[:30000]}
"""
    return _json_completion(prompt, settings.EXTRACTION_MODEL)

def normalize_skill(name: str) -> tuple[str, str | None, str | None]:
    """
    Normalize a candidate skill while preserving the original specific technology.

    Input:
        name -> Skill name.

    Output:
        Tuple containing:
        - normalized skill
        - parent skill
        - skill category

    Example:
        Django -> Django, Python, Backend
        DRF -> Django REST Framework, Django, Backend
    """

    if name is None:
        return "", None, None

    raw = str(name).strip()

    if not raw:
        return "", None, None

    low = raw.lower()

    relationships = {
        "django": ("Django", "Python", "Backend"),
        "django rest framework": (
            "Django REST Framework",
            "Django",
            "Backend"
        ),
        "drf": (
            "Django REST Framework",
            "Django",
            "Backend"
        ),
        "flask": ("Flask", "Python", "Backend"),
        "fastapi": ("FastAPI", "Python", "Backend"),
        "spring boot": ("Spring Boot", "Java", "Backend"),
        "react.js": ("React", "JavaScript", "Frontend"),
        "react": ("React", "JavaScript", "Frontend"),
    }

    if low in relationships:
        return relationships[low]

    return raw, None, None

def safe_list(value) -> list:
    """
    Convert an extracted value into a safe list.

    Input:
        value -> GPT extracted value.

    Output:
        Always returns a list.

    Examples:
        None -> []
        "Python" -> ["Python"]
        ["Python", "SQL"] -> ["Python", "SQL"]
        {"name": "Python"} -> [{"name": "Python"}]
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]

def safe_dict(value) -> dict:
    """
    Convert an extracted value into a safe dictionary.

    Input:
        value -> GPT extracted value.

    Output:
        Dictionary. Invalid values become {}.
    """

    return value if isinstance(value, dict) else {}
def safe_float(value):
    """
    Convert AI-extracted experience values into a PostgreSQL-safe float.

    Input:
        value -> AI-extracted value such as:
                 5
                 "5"
                 "5 years"
                 "14+"
                 "6-10"
                 "Not provided"
                 None

    Output:
        float or None
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().lower()

    if not text or text in {
        "not provided",
        "not specified",
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
        "-"
    }:
        return None

    # Handle ranges such as "6-10"
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", text)
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        return (low + high) / 2

    # Handle values such as "14+", "5 years", "3.5 years"
    number_match = re.search(r"\d+(?:\.\d+)?", text)

    if number_match:
        return float(number_match.group())

    return None
# ------------------------------------------------------------
# RESUME INGESTION
# ------------------------------------------------------------
def store_resume(db: Session, path: str, drive_url: str | None = None) -> UUID:
    """
    Store one resume safely in PostgreSQL and Pinecone.

    Input:
        db   -> SQLAlchemy PostgreSQL session
        path -> Resume file path

    Output:
        Candidate UUID.

    Processing:
        1. Detect duplicate resume.
        2. Read resume text.
        3. Extract candidate information using GPT.
        4. If extraction fails, use safe fallback data.
        5. Store candidate and resume in PostgreSQL.
        6. Store structured skills/experience/education/etc.
        7. Create Pinecone embeddings when text is available.
        8. Pinecone failure does not prevent PostgreSQL ingestion.
    """

    path_obj = Path(path)

    # ---------------------------------------------------------
    # 1. Calculate file hash
    # ---------------------------------------------------------

    digest = file_hash(path)

    existing = db.scalar(
        select(Resume).where(
            Resume.file_hash == digest
        )
    )

    if existing:
        return existing.candidate_id

    # ---------------------------------------------------------
    # 2. Read resume
    # ---------------------------------------------------------

    try:
        text = read_file(path)
    except Exception as error:
        print(
            f"   [WARNING] Could not extract text: {error}"
        )

        # We still ingest the resume.
        text = ""
    if text.strip() and looks_like_job_description(
        text,
        path_obj.name
    ):
        raise ValueError(
            "File appears to be a Job Description, not a resume"
        )
    # ---------------------------------------------------------
    # 3. Extract resume information
    # ---------------------------------------------------------

    data = {}

    if text.strip():

        try:
            extracted = extract_resume(text)

            if isinstance(extracted, dict):
                data = extracted
            else:
                print(
                    "   [WARNING] GPT returned invalid resume data."
                )

        except Exception as error:
            print(
                f"   [WARNING] Resume extraction failed: {error}"
            )

    # ---------------------------------------------------------
    # 4. Safe candidate values
    # ---------------------------------------------------------

    candidate_name = (
        data.get("name")
        or path_obj.stem
        or "Unknown Candidate"
    )

    candidate_name = str(candidate_name).strip()

    if not candidate_name:
        candidate_name = path_obj.stem or "Unknown Candidate"

    # ---------------------------------------------------------
    # 5. Create Candidate
    # ---------------------------------------------------------

    candidate = Candidate(
    name=candidate_name,
    email=data.get("email"),
    phone=data.get("phone"),
    location=data.get("location"),
    total_experience_years=safe_float(
        data.get("total_experience_years")
    ),
    current_company=data.get("current_company"),
    current_role=data.get("current_role"),
    notice_period_days=safe_float(
        data.get("notice_period_days")
    ),
    profile_summary=data.get("profile_summary"),
    raw_profile_text=text,
    normalized_profile=data,
)

    db.add(candidate)
    db.flush()

    # ---------------------------------------------------------
    # 6. Create Resume record
    # ---------------------------------------------------------

    resume = Resume(
        candidate_id=candidate.id,
        file_name=path_obj.name,
        file_url=drive_url if drive_url else str(path_obj),
        file_type=path_obj.suffix.lower().lstrip("."),
        file_size=path_obj.stat().st_size,
        file_hash=digest,
        raw_text=text,
        parsed_data=data,
        parsing_status="COMPLETED",
        extraction_status="COMPLETED",
        extraction_model=settings.EXTRACTION_MODEL,
        extraction_version="v1",
    )

    db.add(resume)
    db.flush()

    # ---------------------------------------------------------
    # 7. Store skills safely
    # ---------------------------------------------------------

    skills = safe_list(
        data.get("skills")
    )

    for item in skills:

        if isinstance(item, dict):

            name = item.get("name")

            if not name:
                continue

            normalized, parent, category = normalize_skill(
                name
            )

            if not normalized:
                continue

            db.add(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_name=str(name),
                    normalized_skill_name=normalized,
                    parent_skill=(
                        item.get("parent_skill")
                        or parent
                    ),
                    skill_category=(
                        item.get("category")
                        or category
                    ),
                    experience_years=item.get(
                        "experience_years"
                    ),
                    proficiency=item.get(
                        "proficiency"
                    ),
                    source="resume",
                    confidence_score=item.get(
                        "confidence_score"
                    ),
                )
            )

        elif isinstance(item, str):

            normalized, parent, category = normalize_skill(
                item
            )

            if not normalized:
                continue

            db.add(
                CandidateSkill(
                    candidate_id=candidate.id,
                    skill_name=item.strip(),
                    normalized_skill_name=normalized,
                    parent_skill=parent,
                    skill_category=category,
                    source="resume",
                )
            )

    # ---------------------------------------------------------
    # 8. Store experience safely
    # ---------------------------------------------------------

    experiences = safe_list(
        data.get("experiences")
        or data.get("experience")
    )

    for item in experiences:

        if isinstance(item, str):
            item = {
                "description": item
            }

        if not isinstance(item, dict):
            continue

        db.add(
            CandidateExperience(
                candidate_id=candidate.id,
                company_name=item.get(
                    "company_name"
                ),
                job_title=item.get(
                    "job_title"
                ),
                employment_type=item.get(
                    "employment_type"
                ),
                description=item.get(
                    "description"
                ),
                domain=item.get(
                    "domain"
                ),
                normalized_data=item,
            )
        )

    # ---------------------------------------------------------
    # 9. Store education safely
    # ---------------------------------------------------------

    education = safe_list(
        data.get("education")
    )

    for item in education:

        if isinstance(item, str):
            item = {
                "degree": item
            }

        if not isinstance(item, dict):
            continue

        db.add(
            CandidateEducation(
                candidate_id=candidate.id,
                degree=item.get(
                    "degree"
                ),
                field_of_study=item.get(
                    "field_of_study"
                ),
                institution=item.get(
                    "institution"
                ),
                start_year=item.get(
                    "start_year"
                ),
                end_year=item.get(
                    "end_year"
                ),
                grade=item.get(
                    "grade"
                ),
            )
        )

    # ---------------------------------------------------------
    # 10. Store certifications safely
    # ---------------------------------------------------------

    certifications = safe_list(
        data.get("certifications")
    )

    for item in certifications:

        if isinstance(item, str):
            item = {
                "certification_name": item
            }

        if not isinstance(item, dict):
            continue

        certification_name = (
            item.get("certification_name")
            or item.get("name")
        )

        if not certification_name:
            continue

        db.add(
            CandidateCertification(
                candidate_id=candidate.id,
                certification_name=certification_name,
                issuing_organization=(
                    item.get(
                        "issuing_organization"
                    )
                    or item.get("issuer")
                ),
                credential_id=item.get(
                    "credential_id"
                ),
            )
        )

    # ---------------------------------------------------------
    # 11. Store projects safely
    # ---------------------------------------------------------

    projects = safe_list(
        data.get("projects")
    )

    for item in projects:

        if isinstance(item, str):
            item = {
                "project_name": item
            }

        if not isinstance(item, dict):
            continue

        db.add(
            CandidateProject(
                candidate_id=candidate.id,
                project_name=item.get(
                    "project_name"
                ),
                description=item.get(
                    "description"
                ),
                technologies=item.get(
                    "technologies"
                ),
                domain=item.get(
                    "domain"
                ),
            )
        )

    # ---------------------------------------------------------
    # 12. Commit PostgreSQL FIRST
    # ---------------------------------------------------------

    db.commit()

    print("   [OK] PostgreSQL")
    return candidate.id
def looks_like_job_description(text: str, filename: str) -> bool:
    """
    Detect whether a file is more likely to be a Job Description than a resume.

    Input:
        text     -> extracted document text
        filename -> original filename

    Output:
        True if the document appears to be a JD, otherwise False.
    """
    filename_lower = filename.lower()
    text_lower = text.lower()

    # Strong filename indicators
    jd_filename_terms = [
        "job description",
        "job_description",
        "jd_",
        "_jd",
        " jd",
    ]

    if any(term in filename_lower for term in jd_filename_terms):
        return True

    # Strong JD content indicators
    jd_terms = [
        "job description",
        "role overview",
        "role context",
        "responsibilities",
        "qualifications",
        "requirements",
        "key responsibilities",
        "preferred qualifications",
        "job requirements",
    ]

    matches = sum(1 for term in jd_terms if term in text_lower)

    return matches >= 3

# -------------------------------------------
#     # ingest resume folder 
# -------------------------------------------

def ingest_resume_folder(db: Session, custom_dir: str | None = None, drive_url: str | None = None, file_url_map: dict | None = None) -> dict:
    """
    Ingest all resumes from a directory. and ingest every supported CV.

    Input:
        db -> SQLAlchemy PostgreSQL database session
        custom_dir -> Optional path to scan instead of settings.RESUME_DIR
        drive_url -> Optional Google Drive URL for the resume

    Output:
        Dictionary containing:
        - total
        - successful
        - skipped
        - failed
        - failed_files

    Processing:
        1. Scan data/resumes.
        2. Process every PDF/DOCX.
        3. Store every readable or partially readable CV.
        4. Continue even when extraction fails.
        5. Continue even when Pinecone fails.
    """

    resume_dir = Path(custom_dir) if custom_dir else Path(settings.RESUME_DIR)

    if not resume_dir.exists():

        return {
            "status": "FAILED",
            "message": (
                f"Resume directory does not exist: "
                f"{resume_dir}"
            ),
            "total": 0,
            "successful": 0,
            "skipped": 0,
            "failed": 0,
            "failed_files": [],
        }

    files = sorted(
        [
            p
            for p in resume_dir.rglob("*")
            if p.is_file()
            and p.suffix.lower() in {
                ".pdf",
                ".docx",
                ".txt",
                ".png",
                ".jpg",
                ".jpeg"
            }
        ],
        key=lambda p: p.name.lower(),
    )

    total = len(files)

    successful = 0
    skipped = 0
    failed = 0

    failed_files = []

    print()
    print("=" * 70)
    print(f"FOUND {total} RESUME FILES")
    print("=" * 70)

    for index, file_path in enumerate(
        files,
        start=1
    ):

        print(
            f"\n[{index}/{total}] "
            f"Processing: {file_path.name}"
        )

        try:

            # -------------------------------------------------
            # Duplicate check
            # -------------------------------------------------

            digest = file_hash(
                str(file_path)
            )

            existing = db.scalar(
                select(Resume).where(
                    Resume.file_hash == digest
                )
            )

            if existing:

                print(
                    "   [SKIPPED] Already ingested."
                )

                skipped += 1
                continue

            # -------------------------------------------------
            # Store resume
            # -------------------------------------------------

            # Use the per-file URL if available (Google Drive individual file URL),
            # otherwise fall back to the folder URL.
            per_file_url = None
            if file_url_map:
                per_file_url = file_url_map.get(file_path.name)
            if not per_file_url:
                per_file_url = drive_url

            candidate_id = store_resume(
                db=db,
                path=str(file_path),
                drive_url=per_file_url
            )

            successful += 1

            print(
                f"   [OK] Successfully ingested "
                f"| Candidate: {candidate_id}"
            )

        except ValueError as error:
                db.rollback()

                if "Job Description" in str(error):
                    skipped += 1
                    print(f"   [SKIPPED] {file_path.name} - Job Description detected.")
                else:
                    failed += 1
                    failed_files.append({
                        "file": file_path.name,
                        "error": str(error)
                    })
                    print(f"   [FAILED] {file_path.name}")
                    print(f"   Reason: {error}")

                continue

        except Exception as error:
            db.rollback()
            failed += 1
            failed_files.append({
                "file": file_path.name,
                "error": str(error)
            })
            print(f"   [FAILED] {file_path.name}")
            print(f"   Reason: {error}")
            continue

    # ---------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("RESUME INGESTION COMPLETE")
    print("=" * 70)

    print(
        f"Total files : {total}"
    )

    print(
        f"Successful  : {successful}"
    )

    print(
        f"Skipped     : {skipped}"
    )

    print(
        f"Failed      : {failed}"
    )

    if failed_files:

        print()
        print("FAILED FILES")
        print("-" * 70)

        for item in failed_files:

            print(
                f"- {item['file']}"
            )

            print(
                f"  {item['error']}"
            )

    print("=" * 70)

    return {
        "status": "COMPLETED",
        "total": total,
        "successful": successful,
        "skipped": skipped,
        "failed": failed,
        "failed_files": failed_files,
    }

def _get_gdrive_folder_file_map(folder_url: str) -> dict:
    """
    Return a mapping of {filename: individual_file_view_url} for all files
    in a public Google Drive folder.

    Uses gdown's internal folder-listing mechanism (same one it uses when
    downloading folders) — no Google API key required.
    Falls back to an empty dict gracefully if listing fails.
    """
    import re as _re

    # Extract folder ID from URL like:
    # https://drive.google.com/drive/folders/<FOLDER_ID>?usp=sharing
    match = _re.search(r"/folders/([a-zA-Z0-9_-]+)", folder_url)
    if not match:
        print("[WARN] Could not extract folder ID from URL:", folder_url)
        return {}

    folder_id = match.group(1)
    file_map = {}

    # --- Strategy 1: Skipped (Incompatible with newer gdown versions) ---

    # --- Strategy 2: parse Google Drive folder page HTML for file IDs ---
    try:
        import urllib.request as _req
        import json as _json

        page_url = f"https://drive.google.com/drive/folders/{folder_id}"
        request = _req.Request(
            page_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with _req.urlopen(request, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Google Drive embeds file metadata as a JSON blob in the HTML.
        # The pattern looks like: ["filename.pdf","file_id","application/pdf", ...]
        # We extract all (name, id) pairs for PDF/DOCX files.
        pattern = _re.compile(
            r'"([^"]+\.(?:pdf|docx|doc|txt))","([a-zA-Z0-9_-]{25,})"',
            _re.IGNORECASE,
        )
        for name, fid in pattern.findall(html):
            if name not in file_map:
                file_map[name] = f"https://drive.google.com/file/d/{fid}/view"
    except Exception as e2:
        print(f"[WARN] HTML-parsing fallback failed: {e2}")

    return file_map


def sync_google_drive(db: Session, url: str) -> dict:
    """
    Sync resumes from a Google Drive URL.
    Assuming the URL points to a shared Folder or a ZIP file.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        if "drive.google.com/drive/folders/" in url:
            # Fetch per-file URLs BEFORE downloading so we can map
            # each local filename back to its individual Google Drive URL.
            file_url_map = _get_gdrive_folder_file_map(url)
            print(f"[Drive] Resolved {len(file_url_map)} individual file URLs.")

            gdown.download_folder(url, output=temp_dir, quiet=False, use_cookies=False)
            return ingest_resume_folder(
                db,
                custom_dir=temp_dir,
                drive_url=url,
                file_url_map=file_url_map if file_url_map else None,
            )
        else:
            cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                output_path = gdown.download(url, quiet=False)
                
                if output_path and zipfile.is_zipfile(output_path):
                    with zipfile.ZipFile(output_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    os.remove(output_path)
            finally:
                os.chdir(cwd)
            
            return ingest_resume_folder(db, custom_dir=temp_dir, drive_url=url)
    except Exception as e:
        return {
            "status": "FAILED",
            "message": f"Failed to download or process Google Drive link: {str(e)}",
            "total": 0, "successful": 0, "skipped": 0, "failed": 0, "failed_files": []
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
# ------------------------------------------------------------
# JD CREATION
# ------------------------------------------------------------
def create_job(
    db: Session,
    user_id: UUID,
    raw_text: str,
    file_name: str | None = None,
    file_path: str | None = None
) -> Job:
    """
    Create a Job from either written JD text or an uploaded JD file.

    Input:
        db        -> PostgreSQL database session
        user_id   -> authenticated recruiter/user UUID
        raw_text  -> JD text
        file_name -> optional uploaded JD filename
        file_path -> optional path of uploaded JD file

    Output:
        Persisted Job with JobRequirement and AIExtractionLog.
    """

    def _safe_float(val):
        try:
            if isinstance(val, dict):
                val = val.get("max", val.get("min", val.get("value", None)))
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    def _safe_int(val):
        try:
            if isinstance(val, dict):
                val = val.get("max", val.get("min", val.get("value", None)))
            return int(float(val)) if val is not None else None
        except (ValueError, TypeError):
            return None

    if not raw_text or not raw_text.strip():
        raise ValueError("JD content cannot be empty")

    raw_text = raw_text.strip()

    # --------------------------------------------------------
    # 1. Extract JD requirements using GPT
    # --------------------------------------------------------
    data = extract_jd(raw_text)

    # --------------------------------------------------------
    # 2. Create Job
    # --------------------------------------------------------
    job = Job(
        created_by=user_id,
        title=data.get("job_title") or "Untitled Job",
        description=raw_text,
        location=data.get("location"),
        work_mode=data.get("work_mode"),
        jd_file_name=file_name,
        jd_file_url=file_path,
        jd_raw_text=raw_text,
        status="READY"
    )

    db.add(job)
    db.flush()

    # --------------------------------------------------------
    # 3. Store extracted JD requirements
    # --------------------------------------------------------
    req = JobRequirement(
        job_id=job.id,
        job_title=data.get("job_title"),

        minimum_experience=_safe_float(data.get("min_experience_years")),
        maximum_experience=_safe_float(data.get("max_experience_years")),

        location=data.get("location") if isinstance(data.get("location"), str) else None,
        work_mode=data.get("work_mode") if isinstance(data.get("work_mode"), str) else None,
        notice_period_days=_safe_int(data.get("notice_period_days")),

        mandatory_skills=data.get("mandatory_skills") or [],
        preferred_skills=data.get("preferred_skills") or [],

        education=data.get("education") or [],
        certifications=data.get("certifications") or [],
        domains=data.get("domains") or [],
        responsibilities=data.get("responsibilities") or [],

        other_requirements=data.get("other_requirements") or [],

        extraction_model=settings.EXTRACTION_MODEL,
        extraction_version="v1",
        confidence_score=safe_float(data.get("confidence_score"))
    )

    db.add(req)

    # --------------------------------------------------------
    # 4. Store AI extraction log
    # --------------------------------------------------------
    db.add(
        AIExtractionLog(
            entity_type="JD",
            entity_id=job.id,
            model_name=settings.EXTRACTION_MODEL,
            prompt_version="v1",
            input_text_hash=hashlib.sha256(
                raw_text.encode()
            ).hexdigest(),
            output_data=data,
            confidence_score=safe_float(data.get("confidence_score")),
            validation_status="PASSED"
        )
    )

    # --------------------------------------------------------
    # 5. Save everything
    # --------------------------------------------------------
    db.commit()
    db.refresh(job)

    return job

# ------------------------------------------------------------
# MATCHING + EVIDENCE
# ------------------------------------------------------------


# def exact_skill_match(db: Session, candidate_id: UUID, required: list) -> dict:
#     """Input: candidate and JD required skills. Output: per-skill match evidence and percentage."""
#     skills = db.scalars(select(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id)).all()
#     normalized = {s.normalized_skill_name.lower(): s for s in skills}
#     parent_map = {s.parent_skill.lower(): s for s in skills if s.parent_skill}
#     details, matched = [], 0
#     required_names = [x.get("name") if isinstance(x, dict) else str(x) for x in required]
#     for req in required_names:
#         key = req.lower()
#         if key in normalized:
#             matched += 1; details.append({"required": req, "status": "EXACT", "candidate_skill": normalized[key].skill_name})
#         elif key in parent_map:
#             details.append({"required": req, "status": "PARENT_SUPPORT", "candidate_skill": parent_map[key].skill_name})
#         else:
#             details.append({"required": req, "status": "MISSING"})
#     return {"matched": matched, "total": len(required_names), "details": details}


def exact_skill_match(db: Session, candidate_id: UUID, required: list) -> dict:

    """

    Match JD-required skills against candidate skills.
 
    Uses database-normalized skill names and parent skills.

    No hardcoded skill aliases.
 
    Match priority:

        EXACT > PARENT_SUPPORT > MISSING
 
    Only EXACT matches count toward the percentage.

    """
 
    # Get candidate skills

    skills = db.scalars(

        select(CandidateSkill).where(

            CandidateSkill.candidate_id == candidate_id

        )

    ).all()
 
    # Prepare candidate skills from DB

    candidate_skills = []
 
    for skill in skills:

        normalized = (skill.normalized_skill_name or skill.skill_name or "").strip().lower()

        original = (skill.skill_name or "").strip()

        parent = (skill.parent_skill or "").strip().lower()
 
        candidate_skills.append({

            "normalized": normalized,

            "original": original,

            "parent": parent,

        })
 
    # Extract required skill names

    required_names = [

        x.get("name") if isinstance(x, dict) else str(x)

        for x in required

    ]
 
    details = []

    matched = 0
 
    for req in required_names:
 
        required_skill = str(req).strip().lower()
 
        status = "MISSING"

        matched_skill_name = None
 
        # ---------------------------------------------------------

        # 1. EXACT NORMALIZED MATCH

        # ---------------------------------------------------------

        for candidate in candidate_skills:
 
            if required_skill == candidate["normalized"]:

                status = "EXACT"

                matched_skill_name = candidate["original"]

                break
 
        # ---------------------------------------------------------

        # 2. PARENT SKILL MATCH

        # ---------------------------------------------------------

        if status == "MISSING":
 
            for candidate in candidate_skills:
 
                if (

                    candidate["parent"]

                    and required_skill == candidate["parent"]

                ):

                    status = "PARENT_SUPPORT"

                    matched_skill_name = candidate["original"]

                    break
 
        # Only exact matches count

        if status == "EXACT":

            matched += 1
 
        details.append({

            "required": req,

            "status": status,

            "candidate_skill": matched_skill_name,

        })
 
    # Calculate percentage

    total = len(required_names)
 
    percentage = (

        round((matched / total) * 100, 2)

        if total > 0

        else 0

    )
 
    return {

        "matched": matched,

        "total": total,

        "percentage": percentage,

        "details": details,

    }
 
def retrieve_evidence(db: Session, candidate_id: UUID) -> list[dict]:
    """Input: candidate UUID. Output: profile summary from PostgreSQL as evidence."""
    candidate = db.get(Candidate, candidate_id)
    if candidate and candidate.profile_summary:
        return [{"score": 1.0, "text": candidate.profile_summary}]
    return [{"score": 0.0, "text": "No evidence available."}]

# ------------------------------------------------------------
# CANDIDATE SEARCH
# ------------------------------------------------------------
def structured_candidate_search(
    db: Session,
    req: JobRequirement,
) -> list[UUID]:
    """
    Deterministic structured candidate filtering.

    No LLM. No generated SQL.
    Filters on: experience, notice period.
    Location is intentionally excluded — it is scored in calculate_normal_score().

    Candidates with NULL experience or NULL notice period are always allowed
    through so that incomplete resumes are not silently discarded.

    Input:
        db  -> SQLAlchemy PostgreSQL session
        req -> JobRequirement with structured JD fields

    Output:
        List of candidate UUIDs that pass the structured filters.
    """

    query = select(Candidate.id)

    conditions = []

    # ---------------------------------------------------------
    # EXPERIENCE
    # Candidates with NULL experience pass through; they will
    # receive a partial score in the normal scoring stage.
    # ---------------------------------------------------------
    if req.minimum_experience is not None:
        conditions.append(
            or_(
                Candidate.total_experience_years.is_(None),
                Candidate.total_experience_years >= req.minimum_experience,
            )
        )

    if req.maximum_experience is not None:
        conditions.append(
            or_(
                Candidate.total_experience_years.is_(None),
                Candidate.total_experience_years <= req.maximum_experience,
            )
        )

    # ---------------------------------------------------------
    # NOTICE PERIOD
    # Candidates with NULL notice period pass through.
    # ---------------------------------------------------------
    if req.notice_period_days is not None:
        conditions.append(
            or_(
                Candidate.notice_period_days.is_(None),
                Candidate.notice_period_days <= req.notice_period_days,
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    rows = db.execute(query).all()

    return [UUID(str(row[0])) for row in rows]



def fts_candidate_search(
    db: Session,
    req: JobRequirement,
    candidate_ids: list[UUID],
) -> list[UUID]:
    """
    PostgreSQL Full Text Search on resume raw_text.

    Only uses short keyword terms (mandatory skills, preferred skills, domains).
    Responsibilities are intentionally excluded — they are long sentences that
    cause plainto_tsquery to require every word, producing zero matches.

    If FTS returns 0 matches, falls back to the full structured search pool
    so that candidates are never silently discarded before normal scoring.

    Input:
        db            -> SQLAlchemy PostgreSQL session
        req           -> JobRequirement with skill/domain lists
        candidate_ids -> pool of candidate UUIDs to search within

    Output:
        Ordered list of candidate UUIDs sorted by FTS rank (best first).
        Falls back to candidate_ids if no search terms or no FTS matches.
    """

    search_terms = []

    # Only short keyword terms — skills and domains.
    # Responsibilities are long sentences and must NOT be included here.
    if req.mandatory_skills:
        search_terms.extend(
            str(skill) for skill in req.mandatory_skills if skill
        )

    if req.preferred_skills:
        search_terms.extend(
            str(skill) for skill in req.preferred_skills if skill
        )

    if req.domains:
        search_terms.extend(
            str(domain) for domain in req.domains if domain
        )

    if not search_terms:
        # No searchable terms — return full pool unchanged.
        return candidate_ids

    # Build an OR-based FTS query so a candidate matches if ANY skill appears,
    # not ALL of them. This avoids zero results when skills are diverse.
    # Each term is sanitised and joined with the | (OR) operator.
    def _clean_term(t: str) -> str:
        # Remove characters that break to_tsquery syntax.
        return re.sub(r"[^\w\s]", " ", t).strip()

    or_terms = []
    for term in search_terms:
        cleaned = _clean_term(term)
        if cleaned:
            # Multi-word skill (e.g. "Machine Learning") → phrase match.
            words = cleaned.split()
            if len(words) > 1:
                or_terms.append(" <-> ".join(words))
            else:
                or_terms.append(words[0])

    if not or_terms:
        return candidate_ids

    ts_query_str = " | ".join(or_terms)

    ts_query = func.to_tsquery("english", ts_query_str)

    query = (
        select(
            Resume.candidate_id,
            func.ts_rank(Resume.search_vector, ts_query).label("rank"),
        )
        .where(Resume.candidate_id.in_(candidate_ids))
        .where(Resume.search_vector.op("@@")(ts_query))
        .order_by(text("rank DESC"))
    )

    try:
        rows = db.execute(query).all()
    except Exception as fts_error:
        # If the FTS query fails for any reason, fall back to the full pool.
        print(f"[FTS] Query failed ({fts_error}), falling back to full pool.")
        return candidate_ids

    matched_ids = [UUID(str(row[0])) for row in rows]

    if not matched_ids:
        # FTS found no matches — fall back to the full structured pool so
        # normal scoring can still evaluate all candidates.
        print("[FTS] No FTS matches found, falling back to full structured pool.")
        return candidate_ids

    return matched_ids



# ------------------------------------------------------------
# GPT EVALUATION
# ------------------------------------------------------------
def ai_score_candidate(payload: dict) -> dict:
    """Output: precisely 8 numerical scores and reasoning string."""
    prompt = f"""
You are an expert AI Recruiter evaluating a candidate against a job description.
Assign precise numerical scores for each of the following 8 criteria, adhering strictly to the maximum points allowed for each.

Criteria & Maximum Points:
1. mandatory_skills_score: max 30
2. experience_score: max 25
3. domain_score: max 15
4. preferred_skills_score: max 10
5. education_score: max 5
6. location_score: max 5
7. availability_score: max 5
8. other_requirements_score: max 5

Rules:
- Be realistic and precise. Give partial points if they partially meet a requirement.
- If the JD does not mention a requirement (e.g., no location specified), award full points for that category.
- Output ONLY a JSON object with EXACTLY the keys listed above (as numbers), plus a string key 'reasoning' explaining the scores briefly.
DATA:\n{json.dumps(payload, default=str)}
"""
    return _json_completion(prompt, settings.EVALUATION_MODEL)

# ------------------------------------------------------------
# DETERMINISTIC SCORING
# ------------------------------------------------------------
def calculate_score(evaluation: dict) -> dict:
    """Input: evaluation dict with 8 numeric scores from LLM. Output: fixed 100-point score and classification."""
    try:
        mandatory = float(evaluation.get("mandatory_skills_score", 0))
        experience = float(evaluation.get("experience_score", 0))
        domain = float(evaluation.get("domain_score", 0))
        preferred = float(evaluation.get("preferred_skills_score", 0))
        education = float(evaluation.get("education_score", 0))
        location = float(evaluation.get("location_score", 0))
        availability = float(evaluation.get("availability_score", 0))
        other = float(evaluation.get("other_requirements_score", 0))
    except (ValueError, TypeError):
        mandatory, experience, domain, preferred, education, location, availability, other = 0,0,0,0,0,0,0,0
    total = round(mandatory + experience + domain + preferred + education + location + availability + other, 2)
    if total >= 90: classification = "EXCELLENT_MATCH"
    elif total >= 80: classification = "STRONG_MATCH"
    elif total >= 70: classification = "GOOD_MATCH"
    elif total >= 60: classification = "MODERATE_MATCH"
    else: classification = "LOW_MATCH_DO_NOT_PRIORITIZE"
    return {"mandatory_skills_score": mandatory, "experience_score": experience, "domain_score": domain,
            "preferred_skills_score": preferred, "education_score": education, "location_score": location,
            "availability_score": availability, "other_requirements_score": other, "total_score": total,
            "classification": classification}


def calculate_normal_score(
    candidate: Candidate,
    req: JobRequirement,
    skills_map: dict,
    experiences_map: dict,
    educations_map: dict,
    projects_map: dict,
) -> dict:
    """
    Deterministic 100-point candidate scoring.

    Uses pre-fetched, bulk-loaded data from PostgreSQL to avoid N+1 queries.
    No LLM calls.

    Scoring breakdown:
        1. Mandatory Skills   = 30
        2. Experience         = 25
        3. Domain Knowledge   = 15
        4. Preferred Skills   = 10
        5. Education          =  5
        6. Location           =  5
        7. Availability       =  5
        8. Other Requirements =  5
                               ---
                               100

    Input:
        candidate      -> Candidate ORM object
        req            -> JobRequirement ORM object
        skills_map     -> {candidate_id: [CandidateSkill, ...]}
        experiences_map-> {candidate_id: [CandidateExperience, ...]}
        educations_map -> {candidate_id: [CandidateEducation, ...]}
        projects_map   -> {candidate_id: [CandidateProject, ...]}

    Output:
        Dict with all 8 component scores, total_score, classification.
    """

    candidate_skills = skills_map.get(candidate.id, [])
    candidate_experiences = experiences_map.get(candidate.id, [])
    candidate_educations = educations_map.get(candidate.id, [])
    candidate_projects = projects_map.get(candidate.id, [])

    # Build candidate skill name set (lowercase) from all skill columns
    candidate_skill_names: set[str] = set()
    for skill in candidate_skills:
        if skill.normalized_skill_name:
            candidate_skill_names.add(str(skill.normalized_skill_name).strip().lower())
        if skill.skill_name:
            candidate_skill_names.add(str(skill.skill_name).strip().lower())
        if skill.parent_skill:
            candidate_skill_names.add(str(skill.parent_skill).strip().lower())

    # =========================================================
    # 1. MANDATORY SKILLS — 30
    # =========================================================
    mandatory_skills = [
        str(x).strip().lower() for x in (req.mandatory_skills or []) if x
    ]

    if not mandatory_skills:
        mandatory_score = 30.0
    else:
        matched = 0
        for required in mandatory_skills:
            if required in candidate_skill_names:
                matched += 1
                continue
            # Basic containment fallback
            if any(
                required in cs or cs in required
                for cs in candidate_skill_names
            ):
                matched += 1
        mandatory_score = (matched / len(mandatory_skills)) * 30

    # =========================================================
    # 2. EXPERIENCE — 25
    # =========================================================
    experience_score = 0.0
    candidate_exp = candidate.total_experience_years

    if candidate_exp is not None:
        candidate_exp = float(candidate_exp)
        min_exp = req.minimum_experience
        max_exp = req.maximum_experience

        if min_exp is None and max_exp is None:
            experience_score = 25.0
        elif min_exp is not None and max_exp is not None:
            if float(min_exp) <= candidate_exp <= float(max_exp):
                experience_score = 25.0
            elif candidate_exp < float(min_exp):
                ratio = candidate_exp / float(min_exp)
                experience_score = max(0.0, min(25.0, ratio * 25))
            else:
                excess = candidate_exp - float(max_exp)
                if excess <= 2:
                    experience_score = 20.0
                elif excess <= 5:
                    experience_score = 15.0
                else:
                    experience_score = 10.0
        elif min_exp is not None:
            if candidate_exp >= float(min_exp):
                experience_score = 25.0
            else:
                experience_score = (candidate_exp / float(min_exp)) * 25
        elif max_exp is not None:
            experience_score = 25.0 if candidate_exp <= float(max_exp) else 15.0

    # =========================================================
    # 3. DOMAIN KNOWLEDGE — 15
    # =========================================================
    required_domains = [
        str(x).strip().lower() for x in (req.domains or []) if x
    ]

    if not required_domains:
        domain_score = 15.0
    else:
        domain_text_parts = []
        for exp in candidate_experiences:
            if exp.job_title:
                domain_text_parts.append(str(exp.job_title))
            if getattr(exp, "company_name", None):
                domain_text_parts.append(str(exp.company_name))
            if getattr(exp, "description", None):
                domain_text_parts.append(str(exp.description))
        for project in candidate_projects:
            if getattr(project, "domain", None):
                domain_text_parts.append(str(project.domain))
            if getattr(project, "description", None):
                domain_text_parts.append(str(project.description))

        domain_text = " ".join(domain_text_parts).lower()
        matched_domains = sum(1 for d in required_domains if d in domain_text)
        domain_score = (matched_domains / len(required_domains)) * 15

    # =========================================================
    # 4. PREFERRED SKILLS — 10
    # =========================================================
    preferred_skills = [
        str(x).strip().lower() for x in (req.preferred_skills or []) if x
    ]

    if not preferred_skills:
        preferred_score = 10.0
    else:
        matched = 0
        for required in preferred_skills:
            if required in candidate_skill_names:
                matched += 1
                continue
            if any(
                required in cs or cs in required
                for cs in candidate_skill_names
            ):
                matched += 1
        preferred_score = (matched / len(preferred_skills)) * 10

    # =========================================================
    # 5. EDUCATION — 5
    # =========================================================
    if not req.education:
        education_score = 5.0
    else:
        education_text = " ".join(
            filter(
                None,
                [str(getattr(row, "degree", "")) for row in candidate_educations]
                + [str(getattr(row, "field_of_study", "")) for row in candidate_educations],
            )
        ).lower()

        # req.education can be a list or a string
        if isinstance(req.education, list):
            req_education_str = " ".join(str(e) for e in req.education).lower()
        else:
            req_education_str = str(req.education).lower()

        education_score = 5.0 if req_education_str and req_education_str in education_text else 0.0

    # =========================================================
    # 6. LOCATION — 5
    # =========================================================
    if not req.location:
        location_score = 5.0
    elif candidate.location:
        location_score = (
            5.0
            if str(req.location).strip().lower() in str(candidate.location).strip().lower()
            else 0.0
        )
    else:
        location_score = 0.0

    # =========================================================
    # 7. AVAILABILITY / NOTICE PERIOD — 5
    # =========================================================
    if req.notice_period_days is None:
        availability_score = 5.0
    elif candidate.notice_period_days is not None:
        availability_score = (
            5.0
            if float(candidate.notice_period_days) <= float(req.notice_period_days)
            else 0.0
        )
    else:
        availability_score = 0.0

    # =========================================================
    # 8. OTHER REQUIREMENTS — 5
    # =========================================================
    other_requirements = req.other_requirements

    if not other_requirements:
        other_score = 5.0
    else:
        candidate_text = (
            f"{candidate.profile_summary or ''} "
            f"{candidate.current_role or ''} "
            f"{candidate.current_company or ''}"
        ).lower()

        if isinstance(other_requirements, list):
            valid_requirements = [str(x).strip().lower() for x in other_requirements if x]
        else:
            valid_requirements = [str(other_requirements).strip().lower()]

        if not valid_requirements:
            other_score = 5.0
        else:
            matched = sum(1 for r in valid_requirements if r in candidate_text)
            other_score = (matched / len(valid_requirements)) * 5

    # =========================================================
    # TOTAL & CLASSIFICATION
    # =========================================================
    total = round(
        mandatory_score + experience_score + domain_score + preferred_score
        + education_score + location_score + availability_score + other_score,
        2,
    )

    if total >= 90:
        classification = "EXCELLENT_MATCH"
    elif total >= 80:
        classification = "STRONG_MATCH"
    elif total >= 70:
        classification = "GOOD_MATCH"
    elif total >= 60:
        classification = "MODERATE_MATCH"
    else:
        classification = "LOW_MATCH_DO_NOT_PRIORITIZE"

    return {
        "mandatory_skills_score": round(mandatory_score, 2),
        "experience_score": round(experience_score, 2),
        "domain_score": round(domain_score, 2),
        "preferred_skills_score": round(preferred_score, 2),
        "education_score": round(education_score, 2),
        "location_score": round(location_score, 2),
        "availability_score": round(availability_score, 2),
        "other_requirements_score": round(other_score, 2),
        "total_score": total,
        "classification": classification,
    }


# ------------------------------------------------------------
# SCREENING ORCHESTRATION
# ------------------------------------------------------------
def screen_job(db: Session, job_id: UUID) -> dict:
    """
    Multi-stage screening pipeline.

    Stage 1 — Structured Search:  experience / location / notice period  (SQL, no LLM)
    Stage 2 — FTS:                mandatory & preferred skills, domains    (PostgreSQL FTS, no LLM)
    Stage 3 — Normal Scoring:     deterministic 100-point score            (Python, no LLM)
    Stage 4 — Top 30 → LLM:       deep evaluation only on best candidates  (LLM)
    Stage 5 — Final Ranking:      persist ranked results
    """
    job = db.get(Job, job_id)
    if not job or not job.requirements:
        raise ValueError("Job or extracted requirements not found")

    req = job.requirements

    run = ScreeningRun(
        job_id=job.id,
        status="RUNNING",
        current_stage="SEARCHING",
        started_at=time_now(),
    )
    db.add(run)
    job.status = "SEARCHING"
    db.commit()

    try:

        # =====================================================
        # STEP 1 — STRUCTURED SEARCH
        # =====================================================
        candidate_ids = structured_candidate_search(db, req)

        print(f"[SEARCH] Structured search returned {len(candidate_ids)} candidates")

        # =====================================================
        # STEP 2 — FTS
        # =====================================================
        if candidate_ids:
            candidate_ids = fts_candidate_search(db, req, candidate_ids)

        print(f"[SEARCH] FTS returned {len(candidate_ids)} candidates")

        if not candidate_ids:
            print("No candidates found after search. Exiting.")
            run.status = "COMPLETED"
            run.current_stage = "COMPLETED"
            run.completed_at = time_now()
            job.status = "ACTIVE"
            db.commit()
            return {"job_id": str(job.id), "candidates_evaluated": 0, "normal_scored": 0, "llm_scored": 0, "top_10": []}

        # =====================================================
        # STEP 3 — BULK FETCH (avoids N+1 in normal scoring)
        # =====================================================
        run.total_candidates = len(candidate_ids)
        run.current_stage = "SCORING"
        db.commit()

        candidates = db.scalars(
            select(Candidate).where(Candidate.id.in_(candidate_ids))
        ).all()
        candidate_map: dict = {c.id: c for c in candidates}

        all_skills = db.scalars(
            select(CandidateSkill).where(CandidateSkill.candidate_id.in_(candidate_ids))
        ).all()
        skills_map: dict = {}
        for s in all_skills:
            skills_map.setdefault(s.candidate_id, []).append(s)

        all_experiences = db.scalars(
            select(CandidateExperience).where(CandidateExperience.candidate_id.in_(candidate_ids))
        ).all()
        experiences_map: dict = {}
        for e in all_experiences:
            experiences_map.setdefault(e.candidate_id, []).append(e)

        all_educations = db.scalars(
            select(CandidateEducation).where(CandidateEducation.candidate_id.in_(candidate_ids))
        ).all()
        educations_map: dict = {}
        for ed in all_educations:
            educations_map.setdefault(ed.candidate_id, []).append(ed)

        all_projects = db.scalars(
            select(CandidateProject).where(CandidateProject.candidate_id.in_(candidate_ids))
        ).all()
        projects_map: dict = {}
        for p in all_projects:
            projects_map.setdefault(p.candidate_id, []).append(p)

        # =====================================================
        # STEP 4 — NORMAL / DETERMINISTIC SCORING
        # =====================================================
        normal_ranked: list[tuple[UUID, dict]] = []

        for cid in candidate_ids:
            candidate = candidate_map.get(cid)
            if not candidate:
                continue
            try:
                score = calculate_normal_score(
                    candidate=candidate,
                    req=req,
                    skills_map=skills_map,
                    experiences_map=experiences_map,
                    educations_map=educations_map,
                    projects_map=projects_map,
                )
                normal_ranked.append((cid, score))
            except Exception as error:
                print(f"Normal scoring failed for {cid}: {error}")

        # =====================================================
        # STEP 5 — SORT & SLICE TOP 30
        # =====================================================
        normal_ranked.sort(key=lambda item: item[1]["total_score"], reverse=True)
        top_30 = normal_ranked[:30]

        print(
            f"[SCORING] {len(normal_ranked)} candidates scored. "
            f"Sending top {len(top_30)} to LLM."
        )

        # =====================================================
        # STEP 6 — LLM FINAL SCORING (Top 30 only)
        # =====================================================
        run.current_stage = "AI_EVALUATION"
        db.commit()

        import concurrent.futures

        scoring_tasks: list[tuple[UUID, dict, dict]] = []

        for cid, normal_score in top_30:
            candidate = candidate_map.get(cid)
            if not candidate:
                continue
            payload = {
                "candidate": {
                    "name": candidate.name,
                    "experience": candidate.total_experience_years,
                    "company": candidate.current_company,
                    "role": candidate.current_role,
                    "location": candidate.location,
                    "notice_period_days": candidate.notice_period_days,
                    "profile": candidate.profile_summary,
                },
                "requirements": {
                    "min_experience": req.minimum_experience,
                    "max_experience": req.maximum_experience,
                    "mandatory_skills": req.mandatory_skills,
                    "preferred_skills": req.preferred_skills,
                    "education": req.education,
                    "certifications": req.certifications,
                    "domains": req.domains,
                    "responsibilities": req.responsibilities,
                    "location": req.location,
                    "work_mode": req.work_mode,
                    "notice_period_days": req.notice_period_days,
                    "other_requirements": req.other_requirements,
                },
                "normal_score": normal_score,
            }
            scoring_tasks.append((cid, payload, normal_score))

        final_ranked: list[tuple, dict] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_data = {
                executor.submit(ai_score_candidate, payload): (cid, normal_score)
                for cid, payload, normal_score in scoring_tasks
            }

            for future in concurrent.futures.as_completed(future_to_data):
                cid, normal_score = future_to_data[future]
                try:
                    llm_evaluation = future.result()
                    llm_score = calculate_score(llm_evaluation)

                    # Persist final score
                    jc = db.scalar(
                        select(JobCandidate).where(
                            JobCandidate.job_id == job.id,
                            JobCandidate.candidate_id == cid,
                        )
                    )
                    if not jc:
                        jc = JobCandidate(job_id=job.id, candidate_id=cid)
                        db.add(jc)
                        db.flush()

                    jc.eligibility_status = (
                        "ELIGIBLE" if llm_score["total_score"] >= 60 else "INELIGIBLE"
                    )
                    jc.recruitment_status = "SCREENED"
                    jc.overall_score = llm_score["total_score"]
                    jc.classification = llm_score["classification"]

                    result_record = db.scalar(
                        select(ScreeningResult).where(
                            ScreeningResult.job_candidate_id == jc.id
                        )
                    )
                    if not result_record:
                        result_record = ScreeningResult(
                            job_candidate_id=jc.id,
                            classification=llm_score["classification"],
                        )
                        db.add(result_record)

                    for key in [
                        "mandatory_skills_score",
                        "experience_score",
                        "domain_score",
                        "preferred_skills_score",
                        "education_score",
                        "location_score",
                        "availability_score",
                        "other_requirements_score",
                        "total_score",
                        "classification",
                    ]:
                        setattr(result_record, key, llm_score[key])

                    result_record.matching_details = {
                        "normal_score": normal_score,
                        "evaluation": llm_evaluation.get("reasoning"),
                    }
                    result_record.semantic_matches = []
                    result_record.missing_requirements = []
                    result_record.strengths = []
                    result_record.concerns = []
                    result_record.screening_model = settings.EVALUATION_MODEL
                    result_record.screening_version = "v3"

                    final_ranked.append((jc, llm_score))
                    run.successful_candidates += 1

                except Exception as error:
                    print(f"LLM scoring failed for {cid}: {error}")
                    run.failed_candidates += 1

                run.processed_candidates += 1
                db.commit()

        # =====================================================
        # STEP 7 — FINAL SORT & RANKING
        # =====================================================
        final_ranked.sort(key=lambda item: item[1]["total_score"], reverse=True)

        for position, (jc, score) in enumerate(final_ranked, 1):
            jc.ranking_position = position
            jc.is_shortlisted = position <= settings.TOP_N
            db.add(jc)

        job.status = "ACTIVE"
        run.status = "COMPLETED"
        run.current_stage = "COMPLETED"
        run.completed_at = time_now()
        db.commit()

        return {
            "job_id": str(job.id),
            "candidates_evaluated": len(candidate_ids),
            "normal_scored": len(normal_ranked),
            "llm_scored": len(final_ranked),
            "top_10": get_job_candidates(db, job.id, limit=settings.TOP_N),
        }

    except Exception as exc:
        db.rollback()
        run.status = "FAILED"
        run.error_message = str(exc)
        run.completed_at = time_now()
        job.status = "DRAFT"
        db.commit()
        raise


def time_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)

# ------------------------------------------------------------
# QUERY FUNCTIONS
# ------------------------------------------------------------
def get_job_candidates(db: Session, job_id: UUID, limit: int = 10) -> list[dict]:
    """
    Input: job UUID.
    Output: ranked candidates with complete score breakdown
    for frontend screening card.
    """

    rows = db.execute(
        select(JobCandidate, Candidate, ScreeningResult)
        .join(
            Candidate,
            Candidate.id == JobCandidate.candidate_id
        )
        .join(
            ScreeningResult,
            ScreeningResult.job_candidate_id == JobCandidate.id
        )
        .where(
            JobCandidate.job_id == job_id,
            JobCandidate.is_shortlisted == True
        )
        .order_by(JobCandidate.ranking_position)
    ).all()

    # Bulk fetch resumes to avoid N+1 query problem
    candidate_ids = [candidate.id for jc, candidate, screening in rows[:limit]]
    resumes = {}
    if candidate_ids:
        all_resumes = db.execute(
            select(Resume).where(Resume.candidate_id.in_(candidate_ids)).order_by(Resume.uploaded_at.desc())
        ).scalars().all()
        for r in all_resumes:
            if r.candidate_id not in resumes:
                resumes[r.candidate_id] = r

    results = []

    for jc, candidate, screening in rows[:limit]:

        # Convert weighted scores into frontend percentages.
        # Example: 24/30 = 80%.
        mandatory = float(screening.mandatory_skills_score or 0)
        experience = float(screening.experience_score or 0)
        domain = float(screening.domain_score or 0)
        preferred = float(screening.preferred_skills_score or 0)
        education = float(screening.education_score or 0)
        location = float(screening.location_score or 0)
        availability = float(screening.availability_score or 0)
        other = float(screening.other_requirements_score or 0)

        score_breakdown = {
            "mandatory_skills": {
                "score": mandatory,
                "max_score": 30,
                "percentage": round((mandatory / 30) * 100)
            },
            "experience": {
                "score": experience,
                "max_score": 25,
                "percentage": round((experience / 25) * 100)
            },
            "domain": {
                "score": domain,
                "max_score": 15,
                "percentage": round((domain / 15) * 100)
            },
            "preferred_skills": {
                "score": preferred,
                "max_score": 10,
                "percentage": round((preferred / 10) * 100)
            },
            "education": {
                "score": education,
                "max_score": 5,
                "percentage": round((education / 5) * 100)
            },
            "location": {
                "score": location,
                "max_score": 5,
                "percentage": round((location / 5) * 100)
            },
            "availability": {
                "score": availability,
                "max_score": 5,
                "percentage": round((availability / 5) * 100)
            },
            "other_requirements": {
                "score": other,
                "max_score": 5,
                "percentage": round((other / 5) * 100)
            }
        }

        # Reasoning was stored inside matching_details.
        reasoning = None

        if screening.matching_details:
            reasoning = screening.matching_details.get("evaluation")

        resume = resumes.get(candidate.id)
        resume_url = resume.file_url if resume else None

        results.append({
            "rank": jc.ranking_position,
            "candidate_id": str(candidate.id),  
            "name": candidate.name,
            "email": candidate.email,
            "phone": candidate.phone,
            "resume_url": resume_url,

            # Candidate information for frontend
            "experience_years": (
                float(candidate.total_experience_years)
                if candidate.total_experience_years is not None
                else None
            ),
            "current_company": candidate.current_company,
            "current_role": candidate.current_role,
            "location": candidate.location,
            "notice_period_days": candidate.notice_period_days,
            "skills": (
                candidate.normalized_profile.get("skills", [])
                if candidate.normalized_profile
                else []
            ),
            "experience_details": (
                candidate.normalized_profile.get("experiences", [])
                if candidate.normalized_profile
                else []
            ),
            # Overall result
            "score": float(screening.total_score or 0),
            "classification": screening.classification,
            "status": jc.recruitment_status,

            # Detailed scoring
            "score_breakdown": score_breakdown,

            # AI explanation
            "reasoning": reasoning
        })

    return results
 
def get_user_jobs(db: Session, user_id: UUID) -> list[dict]:
    """Input: authenticated user UUID. Output: only that user's JDs."""
    jobs = db.scalars(select(Job).where(Job.created_by == user_id).order_by(Job.created_at.desc())).all()
    return [{"job_id": str(j.id), "id": str(j.id), "title": j.title, "description": j.description or j.jd_raw_text, "location": j.location, "work_mode": j.work_mode, "file_name": j.jd_file_name, "status": j.status,
             "created_at": j.created_at.isoformat() if j.created_at else None} for j in jobs]

def get_user_job_candidates(db: Session, user_id: UUID, job_id: UUID) -> list[dict]:
    """Input: authenticated user and job UUID. Output: Top 10 only when the user owns the JD."""
    if not db.scalar(select(Job.id).where(Job.id == job_id, Job.created_by == user_id)):
        raise PermissionError("Job does not belong to current user")
    return get_job_candidates(db, job_id)

def get_admin_jobs(db: Session) -> list[dict]:
    """Input: DB session. Output: all JDs with uploader and Top 10 summary."""
    rows = db.execute(select(Job, User).join(User, User.id == Job.created_by).order_by(Job.created_at.desc())).all()
    return [{"job_id": str(j.id), "title": j.title, "file_name": j.jd_file_name, "status": j.status,
             "uploaded_by": {"id": str(u.id), "name": u.name, "email": u.email},
             "top_10": get_job_candidates(db, j.id)} for j, u in rows]

def get_admin_job_candidates(db: Session, job_id: UUID) -> list[dict]:
    """Input: job UUID. Output: Top 10 persisted candidates for that JD."""
    if not db.get(Job, job_id):
        raise ValueError("Job not found")
    return get_job_candidates(db, job_id)

def get_user_dashboard(db: Session, user_id: UUID) -> dict:
    """Input: user UUID. Output: aggregate dashboard stats and pipeline."""
    user = db.get(User, user_id)
    if not user:
        raise ValueError("User not found")
        
    jobs = db.scalars(select(Job).where(Job.created_by == user_id).order_by(Job.created_at.desc())).all()
    active_jobs = len(jobs)
    
    job_ids = [j.id for j in jobs]
    
    # Bulk fetch requirements to avoid N+1 queries
    reqs = {}
    if job_ids:
        job_reqs = db.execute(select(JobRequirement).where(JobRequirement.job_id.in_(job_ids))).scalars().all()
        for r in job_reqs:
            reqs[r.job_id] = r
            
    screened_data = {}
    if job_ids:
        rows = db.execute(
            select(JobCandidate.job_id, ScreeningResult.total_score)
            .join(ScreeningResult, ScreeningResult.job_candidate_id == JobCandidate.id, isouter=True)
            .where(JobCandidate.job_id.in_(job_ids), JobCandidate.is_shortlisted == True)
        ).all()
        for j_id, score in rows:
            if j_id not in screened_data:
                screened_data[j_id] = {"screened": 0, "strong": 0}
            screened_data[j_id]["screened"] += 1
            if score and float(score) >= 80:
                screened_data[j_id]["strong"] += 1

    total_screened = 0
    strong_matches = 0
    whatsapp_outreach = 0
    
    pipeline = []
    
    for j in jobs:
        s_data = screened_data.get(j.id, {"screened": 0, "strong": 0})
        screened_count = s_data["screened"]
        strong_count = s_data["strong"]
        
        total_screened += screened_count
        strong_matches += strong_count
        
        j_req = reqs.get(j.id)
        exp_str = "N/A"
        if j_req:
            min_exp = j_req.minimum_experience
            max_exp = j_req.maximum_experience
            if min_exp and max_exp: 
                exp_str = f"{int(min_exp)}-{int(max_exp)} yrs"
            elif min_exp: 
                exp_str = f"{int(min_exp)}+ yrs"
                
        pipeline.append({
            "job_id": str(j.id),
            "title": j.title,
            "location": j.location or "Remote",
            "experience": exp_str,
            "sources": "Database",
            "screened": screened_count,
            "strong": strong_count,
            "outreach_count": 0,
            "outreach_total": screened_count,
            "status": j.status
        })
        
    return {
        "user_name": user.name,
        "metrics": {
            "active_jobs": active_jobs,
            "candidates_screened": total_screened,
            "strong_matches": strong_matches,
            "whatsapp_outreach": whatsapp_outreach
        },
        "pipeline": pipeline[:5]
    }

def _send_whatsapp_to_candidate(
    db: Session,
    job_id: UUID,
    candidate_id: UUID,
    target_phone: str | None = None
):
    print(f"--- Attempting WhatsApp Integration for candidate {candidate_id} ---")
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if not candidate:
            print("Candidate not found in DB.")
            return

        import urllib.request
        import json

        # Find the JobCandidate record
        job_candidate = db.scalar(
            select(JobCandidate).where(
                JobCandidate.job_id == job_id,
                JobCandidate.candidate_id == candidate_id
            )
        )

        if not job_candidate:
            print("JobCandidate not found.")
            return

        
        # Use target_phone if provided, else use stage number if configured, otherwise use candidate's phone
        raw_phone = target_phone
        if not raw_phone:
            raw_phone = getattr(settings, "WHATSAPP_STAGE_NUMBER", None)
        if not raw_phone:
            raw_phone = str(candidate.phone) if candidate.phone else ""
            
        if not raw_phone or raw_phone == "None":
            print("No phone number available for candidate (and no stage number configured). Skipping.")
            return

        clean_phone = ''.join(filter(str.isdigit, raw_phone))
        
        if clean_phone:
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            
            url = "https://nmve.io/whatsapp/api/integrations/whatsapp/messages"
            headers = {
                "Content-Type": "application/json"
            }
            if getattr(settings, "WHATSAPP_API_KEY", ""):
                headers["Authorization"] = f"Bearer {settings.WHATSAPP_API_KEY}"
                headers["api-key"] = settings.WHATSAPP_API_KEY
            
            payload = {
                "to": clean_phone,
                "type": "template",
                "template": {
                    "name": "hello_world",
                    "language": {
                    "code": "en_US"
                    }
                },
                "referenceId": f"NMHireX-{str(candidate_id)[:8]}",
                "callbackUrl": "https://nmhirex.onrender.com/api/webhooks/whatsapp"
            }
            
            print(f"Sending WhatsApp payload to {clean_phone}...")
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            
            try:
                with urllib.request.urlopen(req) as response:
                    response_body = response.read().decode('utf-8')

                    print(
                        f"WhatsApp message sent to {clean_phone}, "
                        f"status: {response.status}"
                    )
                    print(f"Response: {response_body}")

                    # Save outgoing WhatsApp message in candidate_contacts
                    contact = CandidateContact(
                        job_candidate_id=job_candidate.id,
                        channel="WHATSAPP",
                        message_type="OUTBOUND",
                        message="Hi",
                        provider="NMVE",
                        status="SENT",
                        sent_at=datetime.utcnow(),
                    )

                    db.add(contact)
                    db.commit()

                    print("WhatsApp message saved to candidate_contacts.")

            except urllib.error.HTTPError as http_err:
                error_body = http_err.read().decode('utf-8')
                print(f"WhatsApp API HTTP Error: {http_err.code}")
                print(f"Error Details: {error_body}")

            except Exception as api_err:
                print(f"WhatsApp API Error: {api_err}")

        else:
            print("Phone number is invalid or empty after cleaning.")

    except Exception as e:
        print(f"Error in WhatsApp integration: {e}")


def _send_whatsapp_text_message(raw_phone: str, text_message: str):
    """Send a plain text WhatsApp message to a phone number."""
    try:
        import urllib.request
        import json

        if not raw_phone:
            return

        clean_phone = ''.join(filter(str.isdigit, str(raw_phone)))
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        if not clean_phone:
            return

        url = "https://nmve.io/whatsapp/api/integrations/whatsapp/messages"
        headers = {"Content-Type": "application/json"}
        if getattr(settings, "WHATSAPP_API_KEY", ""):
            headers["Authorization"] = f"Bearer {settings.WHATSAPP_API_KEY}"
            headers["api-key"] = settings.WHATSAPP_API_KEY

        payload = {
            "to": clean_phone,
            "type": "text",
            "text": {"body": text_message}
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            print(f"WhatsApp reply sent to {clean_phone}, status: {response.status}")

    except Exception as e:
        print(f"Error sending WhatsApp reply: {e}")

def _send_whatsapp_cta_message(raw_phone: str, job_candidate_id: str):
    """Send a WhatsApp CTA URL interactive message for interview scheduling."""
    try:
        import urllib.request
        import json
        import os

        if not raw_phone:
            return

        clean_phone = ''.join(filter(str.isdigit, str(raw_phone)))
        if len(clean_phone) == 10:
            clean_phone = "91" + clean_phone

        if not clean_phone:
            return

        url = "https://nmve.io/whatsapp/api/integrations/whatsapp/messages"
        headers = {"Content-Type": "application/json"}
        if getattr(settings, "WHATSAPP_API_KEY", ""):
            headers["Authorization"] = f"Bearer {settings.WHATSAPP_API_KEY}"
            headers["api-key"] = settings.WHATSAPP_API_KEY

        # Fallback to localhost if FRONTEND_URL is not set in env
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        scheduling_link = f"{frontend_url}/schedule/{job_candidate_id}"

        payload = {
            "to": clean_phone,
            "type": "interactive",
            "interactive": {
                "type": "cta_url",
                "header": {
                    "type": "text",
                    "text": "Great news! 🎉"
                },
                "body": {
                    "text": "Please schedule your interview at a convenient date and time within the next 7 days.\n\nTap the button below to select your preferred date and time.\n\nWe look forward to connecting with you! 😊"
                },
                "action": {
                    "name": "cta_url",
                    "parameters": {
                        "display_text": "Schedule Now",
                        "url": scheduling_link
                    }
                }
            }
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            print(f"WhatsApp CTA message sent to {clean_phone}, status: {response.status}")

    except urllib.error.HTTPError as http_err:
        error_body = http_err.read().decode('utf-8')
        print(f"WhatsApp API HTTP Error: {http_err.code}")
        print(f"Error Details: {error_body}")
        
        # Fallback to plain text message if CTA URL is not supported by gateway
        print("Falling back to plain text message with URL...")
        fallback_msg = (
            f"Great news! 🎉 We'd love to move forward with your application.\n\n"
            f"Please schedule your interview at a convenient date and time within the next 7 days.\n\n"
            f"Tap the link below to select your preferred date and time:\n"
            f"👉 {scheduling_link}\n\n"
            f"We look forward to connecting with you! 😊"
        )
        _send_whatsapp_text_message(raw_phone, fallback_msg)

    except Exception as e:
        print(f"Error sending WhatsApp CTA: {e}")


def mark_candidate_contacted(
    db: Session,
    job_id: UUID,
    candidate_id: UUID,
    target_phone: str | None = None
):
    update_candidate_status(
        db,
        job_id,
        candidate_id,
        'CONTACTED',
        target_phone
    )

def get_outreach_candidates(db: Session, user_id: UUID) -> list[dict]:
    # Get all candidates who have been contacted, interested,
    # not interested, or have received an interview link.
    rows = db.execute(
        select(JobCandidate, Job, Candidate)
        .join(Job, Job.id == JobCandidate.job_id)
        .join(Candidate, Candidate.id == JobCandidate.candidate_id)
        .where(
            JobCandidate.recruitment_status.in_([
                'CONTACTED',
                'INTERESTED',
                'NOT_INTERESTED',
                'INTERVIEW_LINK_SENT'
            ])
        )
        .order_by(JobCandidate.updated_at.desc())
    ).all()

    results = []

    for jc, job, candidate in rows:

        # Find the latest WhatsApp response from this candidate
        latest_response = (
            db.query(CandidateContact)
            .filter(
                CandidateContact.job_candidate_id == jc.id,
                CandidateContact.channel == "WHATSAPP",
                CandidateContact.message_type == "INBOUND"
            )
            .order_by(
                CandidateContact.created_at.desc()
            )
            .first()
        )

        response_text = None
        response_intent = None
        responded_at = None

        if latest_response:
            response_text = (
                latest_response.response_text
                or latest_response.message
            )

            # Intent will be populated by the WhatsApp webhook
            response_intent = getattr(
                latest_response,
                "response_intent",
                None
            )

            responded_at = latest_response.responded_at

        results.append({
            "id": str(candidate.id),
            "job_id": str(job.id),
            "job_candidate_id": str(jc.id),
            "name": candidate.name or "Unnamed Candidate",
            "job": job.title or "Unknown Role",
            "status": jc.recruitment_status,

            # WhatsApp response information
            "response_text": response_text,
            "response_intent": response_intent,
            "responded_at": (
                responded_at.isoformat()
                if responded_at
                else None
            )
        })

    return results

def update_candidate_status(db: Session, job_id: UUID, candidate_id: UUID, status: str, target_phone: str | None = None):
    db.execute(
        text("UPDATE job_candidates SET recruitment_status = :status, updated_at = now() WHERE job_id = :job_id AND candidate_id = :candidate_id"),
        {"job_id": job_id, "candidate_id": candidate_id, "status": status}
    )
    db.commit()
    
    if status.upper() == 'CONTACTED':
        _send_whatsapp_to_candidate(db, job_id, candidate_id, target_phone)

def get_all_candidates(db: Session, user_id: UUID) -> list[dict]:
    # Fetch all candidates in the database (ensuring each is listed exactly once)
    # Only return candidates who are marked as INTERESTED or INTERVIEW_LINK_SENT
    rows = db.execute(
        select(Candidate, JobCandidate)
        .join(JobCandidate, JobCandidate.candidate_id == Candidate.id)
        .where(JobCandidate.recruitment_status.in_(['INTERESTED', 'INTERVIEW_LINK_SENT']))
        .order_by(Candidate.created_at.desc(), JobCandidate.created_at.desc())
    ).all()
    
    # Extract unique candidates, keeping their valid JobCandidate record
    seen = set()
    valid_pairs = []
    for cand, jc in rows:
        if cand.id not in seen:
            valid_pairs.append((cand, jc))
            seen.add(cand.id)
    
    results = []
    for candidate, active_jc in valid_pairs:
        # Get the screening result and job for this specific JobCandidate
        jc_row = db.execute(
            select(JobCandidate, Job, ScreeningResult)
            .join(Job, Job.id == JobCandidate.job_id)
            .outerjoin(ScreeningResult, ScreeningResult.job_candidate_id == JobCandidate.id)
            .where(JobCandidate.id == active_jc.id)
        ).first()
        
        score = 0
        scoreLabel = "-"
        job_title = "-"
        stage = "-"
        job_id = None
        
        if jc_row:
            jc, job, screening = jc_row
            job_id = str(job.id)
            job_title = job.title
            stage = jc.recruitment_status
            if screening and screening.total_score:
                score = float(screening.total_score)
                lbl = str(screening.classification).replace("_", " ").title() if screening.classification else "-"
                if "Do Not Prioritize" in lbl:
                    scoreLabel = "Low Match"
                elif "Moderate" in lbl:
                    scoreLabel = "Moderate Match"
                elif "Strong" in lbl:
                    scoreLabel = "Strong Match"
                elif "Excellent" in lbl:
                    scoreLabel = "Excellent Match"
                else:
                    scoreLabel = lbl

        # Find the interview link sent to this candidate
        interview_link = getattr(active_jc, "interview_link", None)
        interview_scheduled_at = getattr(active_jc, "interview_scheduled_at", None)
        
        # Fallback: scan outbound messages for a Teams link (legacy data)
        if not interview_link:
                outbound_interview = (
                    db.query(CandidateContact)
                    .filter(
                        CandidateContact.job_candidate_id == active_jc.id,
                        CandidateContact.channel == "WHATSAPP",
                        CandidateContact.message_type == "OUTBOUND",
                        CandidateContact.message.contains("teams.microsoft.com")
                    )
                    .order_by(CandidateContact.created_at.desc())
                    .first()
                )
                if outbound_interview and outbound_interview.message:
                    import re
                    urls = re.findall(r'https?://\S+', outbound_interview.message)
                    if urls:
                        interview_link = urls[0].rstrip("!")

        results.append({
            "id": str(candidate.id),
            "job_id": job_id,
            "name": candidate.name or "Unnamed",
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location or "-",
            "exp": f"{candidate.total_experience_years} yrs" if candidate.total_experience_years else "-",
            "score": score,
            "scoreLabel": scoreLabel,
            "job": job_title,
            "skills": ", ".join([s.get("name") or s.get("skill") or s.get("skill_name") or str(s) if isinstance(s, dict) else str(s) for s in candidate.normalized_profile.get("skills", [])][:5]) if candidate.normalized_profile and candidate.normalized_profile.get("skills") else "-",
            "stage": stage,
            "interview_link": interview_link,
            "interview_scheduled_at": interview_scheduled_at.isoformat() if interview_scheduled_at else None,
            "experience_details": candidate.normalized_profile.get("experiences", []) if candidate.normalized_profile else [],
            "all_skills": candidate.normalized_profile.get("skills", []) if candidate.normalized_profile else []
        })
    return results

def get_outreach_campaigns(db: Session, user_id: UUID) -> dict:
    # Get jobs
    jobs = db.execute(select(Job).where(Job.created_by == user_id)).scalars().all()
    
    campaigns = []
    total_contacted = 0
    total_pending = 0
    total_interested = 0
    
    for job in jobs:
        rows = db.execute(
            select(JobCandidate, ScreeningResult)
            .join(ScreeningResult, ScreeningResult.job_candidate_id == JobCandidate.id)
            .where(JobCandidate.job_id == job.id)
        ).all()
        
        eligible = 0
        contacted = 0
        interested = 0
        
        for jc, screening in rows:
            if screening.total_score and screening.total_score >= 70:
                eligible += 1
                if jc.recruitment_status == 'CONTACTED':
                    contacted += 1
                elif jc.recruitment_status == 'INTERESTED':
                    interested += 1
                    contacted += 1 # interested implies contacted
        
        status = 'Active' if contacted > 0 else 'Draft'
        if eligible > 0 and contacted == eligible:
            status = 'Completed'
            
        campaigns.append({
            "id": str(job.id),
            "name": job.title,
            "job": job.title,
            "created": job.created_at.strftime("%b %d, %Y") if job.created_at else "",
            "rule": f"{eligible} eligible",
            "eligible": eligible,
            "contacted": contacted,
            "interested": interested,
            "status": status,
            "searchStr": f"{job.title} {status}".lower()
        })
        
        total_contacted += contacted
        total_pending += (eligible - contacted)
        total_interested += interested
        
    return {
        "metrics": {
            "contacted": total_contacted,
            "pending": total_pending,
            "interested": total_interested,
            "tests_assigned": 0
        },
        "campaigns": campaigns
    }
