from __future__ import annotations
import json
import re
from typing import Any

from openai import OpenAI
from app.core.config import settings

VALID_STATUSES = {"recommended", "review", "not recommended"}
VALID_CONFIDENCE = {"low", "medium", "high"}

OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_MODEL = settings.EVALUATION_MODEL

AI_ADJUDICATION_ENABLED = True
AI_ADJUDICATION_MIN_LOCAL_SCORE = 75.0
AI_ADJUDICATION_MIN_ROLE_RELEVANCE = 0.40
AI_TIMEOUT_SECONDS = 45.0

def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []

def _text(value: Any) -> str:
    return str(value or "").strip()

def _truncate(value: Any, limit: int) -> str:
    text = _text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"

def _scrub_free_text(value: Any, limit: int = 7000) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[email removed]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:https?://|www\.)\S+", "[url removed]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)", "[phone removed]", text)
    return _truncate(text, limit)

def _experience_evidence(cv: dict[str, Any]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in _safe_list(cv.get("experiences"))[:8]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("job_title") or item.get("designation") or item.get("role") or ""
        evidence_parts = []
        for key in ("description", "responsibilities", "summary", "projects", "achievements", "technologies", "skills"):
            value = item.get(key)
            if isinstance(value, list):
                evidence_parts.extend(_text(part) for part in value if _text(part))
            elif _text(value):
                evidence_parts.append(_text(value))
        output.append({
            "title": _truncate(title, 180),
            "experience_years": item.get("experience_in_years") or item.get("years"),
            "evidence": [_truncate(part, 1200) for part in evidence_parts[:12]],
        })
    return output

def _education_evidence(cv: dict[str, Any]) -> list[str]:
    output = []
    for item in _safe_list(cv.get("education"))[:6]:
        value = item.get("degree") or item.get("title") or item.get("course") or "" if isinstance(item, dict) else item
        if _text(value):
            output.append(_truncate(value, 250))
    return output

def _certification_evidence(cv: dict[str, Any]) -> list[str]:
    output = []
    for item in _safe_list(cv.get("certifications"))[:10]:
        value = item.get("title") or item.get("name") or item.get("certification_name") or "" if isinstance(item, dict) else item
        if _text(value):
            output.append(_truncate(value, 250))
    return output

def _candidate_evidence(cv: dict[str, Any]) -> dict[str, Any]:
    return {
        "current_designation": _truncate(cv.get("designation"), 180),
        "domain": _truncate(cv.get("domain"), 180),
        "skills": cv.get("skills", []),
        "about_me": _truncate(cv.get("about_me"), 1800),
        "experiences": _experience_evidence(cv),
        "education": _education_evidence(cv),
        "certifications": _certification_evidence(cv),
        "resume_text": _scrub_free_text(cv.get("cv_text_description"), 6500),
    }

def _default_result(reason: str) -> dict[str, Any]:
    return {"used": False, "model": OPENAI_MODEL, "status": None, "reason": reason, "confidence": None, "skill_findings": []}

def should_adjudicate(local_result: dict[str, Any]) -> bool:
    if not AI_ADJUDICATION_ENABLED or not OPENAI_API_KEY:
        return False
    local_status = str(local_result.get("recommendation_status") or "").strip().lower()
    if local_status == "recommended":
        return False
    score = float(local_result.get("final_score") or 0.0)
    if score < AI_ADJUDICATION_MIN_LOCAL_SCORE:
        return False
    debug = local_result.get("debug_details") or {}
    required = debug.get("required_skills") or {}
    experience = debug.get("experience_relevance") or {}
    missing_required = _safe_list(required.get("missing"))
    missing_core = _safe_list(required.get("missing_core_skills"))
    if not missing_required and not missing_core:
        return False
    if str(experience.get("experience_fit") or "") == "far_outside":
        return False
    if bool(experience.get("title_active")):
        role_score = float(experience.get("title_score") or 0.0)
        if role_score < AI_ADJUDICATION_MIN_ROLE_RELEVANCE:
            return False
    return True

def adjudicate_candidate(jd: dict[str, Any], cv: dict[str, Any], local_result: dict[str, Any]) -> dict[str, Any]:
    if not should_adjudicate(local_result):
        return _default_result("AI adjudication was not required for this candidate.")
    debug = local_result.get("debug_details") or {}
    required = debug.get("required_skills") or {}
    experience = debug.get("experience_relevance") or {}
    missing_required = list(dict.fromkeys([*(_safe_list(required.get("missing"))), *(_safe_list(required.get("missing_core_skills")))]))

    payload = {
        "job": {
            "job_title": jd.get("job_title"),
            "minimum_experience": jd.get("minimum_experience"),
            "maximum_experience": jd.get("maximum_experience"),
            "required_skills": required.get("required_groups") or jd.get("mandatory_skills") or [],
            "preferred_skills": required.get("preferred_groups") or jd.get("preferred_skills") or [],
            "missing_required_skills": missing_required,
            "education": jd.get("education") or [],
            "certifications": jd.get("certifications") or [],
            "job_description": _truncate(jd.get("jd_text_description"), 7000),
        },
        "candidate": _candidate_evidence(cv),
        "deterministic_result": {
            "score": local_result.get("final_score"),
            "status": local_result.get("recommendation_status"),
            "reason": local_result.get("recommendation_reason"),
            "required_skill_ratio": required.get("ratio"),
            "missing_required_skills": missing_required,
            "experience_fit": experience.get("experience_fit"),
            "candidate_years": experience.get("candidate_years"),
            "role_relevance": experience.get("title_score"),
        },
    }

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "status": {"type": "string", "enum": ["recommended", "review", "not recommended"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "reason": {"type": "string"},
            "skill_findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "skill": {"type": "string"},
                        "finding": {"type": "string", "enum": ["supported", "not_supported", "uncertain"]},
                        "reason": {"type": "string"},
                        "evidence": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["skill", "finding", "reason", "evidence"],
                },
            },
        },
        "required": ["status", "confidence", "reason", "skill_findings"],
    }

    system_prompt = """
You are a job-fit adjudication assistant used only as a fallback after a
transparent deterministic scorer has already evaluated a candidate.

Use ONLY the supplied job description and candidate evidence. Do not use web
search, outside knowledge about the candidate, or assumptions based on name,
location, age, gender, race, ethnicity, religion, disability, family status,
or any other protected/personal characteristic.

Your narrow task is to decide whether REQUIRED skills that were not explicitly
found in the parsed skill list are nevertheless demonstrated by concrete
job-relevant evidence in the candidate's work, projects, tools, or outcomes.

Important rules:
- A job title alone is NOT enough to prove a missing skill.
- Require concrete evidence from responsibilities, projects, tools, or outcomes.
- Do not invent experience or credentials.
- Preferred/nice-to-have skills must not be treated as mandatory.
- If evidence is mixed or insufficient, choose "review".
- "recommended" requires strong evidence that the important missing capability
  is actually demonstrated and no major supplied job-relevant gap remains.
- "not recommended" requires clear job-relevant evidence that the missing
  requirement is not supported or that the supplied profile materially fails
  the role requirements.
- This is decision support; a human recruiter remains responsible for the final
  employment decision.

Return a concise reason plus per-skill findings.
""".strip()

    try:
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=AI_TIMEOUT_SECONDS)
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)}],
            text={"format": {"type": "json_schema", "name": "candidate_skill_adjudication", "strict": True, "schema": schema}},
            max_output_tokens=1200,
        )
        parsed = json.loads(response.output_text or "{}")
        status = _text(parsed.get("status")).lower()
        confidence = _text(parsed.get("confidence")).lower()
        reason = _text(parsed.get("reason"))
        findings = parsed.get("skill_findings", [])

        if confidence == "low":
            status = "review"
            reason = f"AI evidence was not strong enough for an automatic status change. {reason}"

        return {"used": True, "model": OPENAI_MODEL, "status": status, "reason": reason, "confidence": confidence, "skill_findings": findings}
    except Exception as exc:
        return _default_result(f"AI adjudication unavailable: {exc}")