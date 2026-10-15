import re
from typing import Any

def parse_naukri_experience(exp_str: str) -> float:
    """Converts '5y 3m' into 5.25"""
    if not exp_str:
        return 0.0
    
    years = 0
    months = 0
    
    y_match = re.search(r'(\d+)y', exp_str, re.IGNORECASE)
    m_match = re.search(r'(\d+)m', exp_str, re.IGNORECASE)
    
    if y_match:
        years = int(y_match.group(1))
    if m_match:
        months = int(m_match.group(1))
        
    return round(years + (months / 12.0), 2)

def adapt_naukri_candidate(naukri_data: dict[str, Any]) -> dict[str, Any]:
    """Reshapes Naukri JSON into the exact format expected by the Enhanced Engine."""
    
    # Merge skills
    skills = naukri_data.get("keySkills", []) + naukri_data.get("mayAlsoKnow", [])
    
    headline = naukri_data.get("headline", "")
    current_employment = naukri_data.get("currentEmployment", "")
    education = naukri_data.get("education", "")
    
    # Synthesize text block for FTS matching
    synthetic_text = f"{headline}\n{current_employment}\n{education}\nSkills: {', '.join(skills)}"
    
    return {
        "id": str(naukri_data.get("candidateId", "")),
        "fullname": naukri_data.get("name", "Unknown Naukri Candidate"),
        "email": "",  # Naukri JSON preview does not expose email
        "phone": naukri_data.get("phoneNumber", ""),
        "location": naukri_data.get("currentLocation", ""),
        "total_experience": parse_naukri_experience(naukri_data.get("experience", "")),
        "designation": current_employment,
        "currentcompany": "", 
        "about_me": headline,
        "cv_text_description": synthetic_text,
        "skills": skills,
        "experiences": [{"title": current_employment}] if current_employment else [],
        "education": [{"degree": education}] if education else [],
        "certifications": [],
        "projects": []
    }