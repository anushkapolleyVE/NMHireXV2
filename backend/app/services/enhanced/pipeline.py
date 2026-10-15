from app.models.schema import Candidate, JobRequirement, Job
from app.services.enhanced.match_score import score_candidates

def run_enhanced_scoring(candidate: Candidate, req: JobRequirement, job: Job) -> dict:
    """
    Adapter function that converts NMHireX database models into the raw
    dictionary format expected by the legacy Enhanced Scoring Engine.
    """
    
    # Format Job Description object
    jd_dict = {
        "job_title": req.job_title,
        "minimum_experience": float(req.minimum_experience) if req.minimum_experience is not None else None,
        "maximum_experience": float(req.maximum_experience) if req.maximum_experience is not None else None,
        "mandatory_skills": req.mandatory_skills or [],
        "core_skills": req.mandatory_skills or [],
        "preferred_skills": req.preferred_skills or [],
        "nice_to_have_skills": req.preferred_skills or [],
        "education": req.education or [],
        "certifications": req.certifications or [],
        "domain": ", ".join(req.domains) if req.domains else "",
        "location": req.location,
        "work_mode": req.work_mode,
        "jd_text_description": job.description or job.jd_raw_text or "",
    }
    
    # Format Candidate object
    prof = candidate.normalized_profile or {}
    
    cv_dict = {
        "id": str(candidate.id),
        "fullname": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "total_experience": float(candidate.total_experience_years) if candidate.total_experience_years is not None else None,
        "designation": candidate.current_role,
        "currentcompany": candidate.current_company,
        "about_me": prof.get("profile_summary", ""),
        "skills": prof.get("skills", []),
        "experiences": prof.get("experiences", []),
        "education": prof.get("education", []),
        "certifications": prof.get("certifications", []),
        "projects": prof.get("projects", []),
        "domain": "", # (Will be parsed from projects/experiences if needed)
        "cv_text_description": candidate.raw_profile_text or "",
    }
    
    # Run the legacy engine (this handles deterministic + AI adjudication)
    results = score_candidates(jd=jd_dict, candidates=[cv_dict], debug=True)
    
    if results:
        return results[0]
    return {}