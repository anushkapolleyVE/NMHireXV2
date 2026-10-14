# test_extraction.py
import asyncio
from app.tool_functions import extract_resume

sample_cv_text = """
John Doe
johndoe@email.com | 555-1234
Software Engineer with 5 years of experience at TechCorp.
Skills: Python, Django, React.
"""

result = extract_resume(sample_cv_text)
print(result)
