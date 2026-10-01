# NM-HireX Candidate Scoring System
## Overview

- NM-HireX uses a two-stage candidate screening process:

    - Candidate Retrieval — identify a broad set of potentially relevant candidates.
    - AI Evaluation & Scoring — evaluate each candidate against the Job Description and generate an overall score out of 100.

#### The scoring pipeline is primarily implemented through these functions:

- screen_job()
-    ↓
- nl_to_sql_search()
-    ↓
- ai_score_candidate()
-    ↓
- calculate_score()
-    ↓
- Ranking + Eligibility + Shortlisting


## 1. AI Candidate Evaluation
    1. Candidate information sent to AI
        - Name
        - Experience
        - Current company
        - Current role
        - Location
        - Notice period
        - Profile summary
    2. JD information sent to AI
        - Minimum experience
        - Maximum experience
        - Mandatory skills
        - Preferred skills
        - Education
        - Certifications
        - Domains
        - Responsibilities
        - Location
        - Work mode
        - Notice period
        - Other requirements

    The function asks the AI to produce 8 numerical scores plus a reasoning string.

## 2. The 100-Point Scoring Rubric

    The AI is instructed to score the candidate across 8 categories.

   - Criteria	                     Maximum Points
   - Mandatory Skills Match	                30
   - Relevant Experience	                25
   - Job Role / Domain Experience	        15
   - Preferred Skills	                    10
   - Education / Certification	            5
   - Location / Work Mode	                5
   - Notice Period / Availability	        5
   - Other JD Requirements	                5
   - TOTAL	                               100
## 3. How Each Score Is Generated

    The important implementation detail is:

-    The code does NOT contain a mathematical formula for calculating each category.

-    Instead, ai_score_candidate() asks the evaluation model to determine the score for each category.

####    The AI is instructed to:

-    Be realistic and precise.
-    Give partial points when requirements are partially satisfied.
-    Give full points when the JD does not specify that requirement.

#####   For example:

    mandatory_skills_score = AI determines a value between 0 and 30

    experience_score = AI determines a value between 0 and 25

    domain_score = AI determines a value between 0 and 15

    and so on.

-    Therefore, the current implementation is:

    Candidate + JD
        ↓
    Evaluation LLM
        ↓
    8 component scores
        ↓
    Deterministic total calculation

## 4. Final Score Calculation

-    This is the deterministic part of the scoring system.

    It extracts the 8 numerical values:

    mandatory
    experience
    domain
    preferred
    education
    location
    availability
    other

    Then performs:

    total =
        mandatory
        + experience
        + domain
        + preferred
        + education
        + location
        + availability
        + other

    The total is rounded to 2 decimal places.

-    Example

    Suppose the AI returns:

    Mandatory Skills     = 26
    Experience            = 22
    Domain                = 13
    Preferred Skills      = 8
    Education             = 5
    Location              = 5
    Availability          = 4
    Other Requirements    = 4

    Then:

    Final Score
    = 26 + 22 + 13 + 8 + 5 + 5 + 4 + 4
    = 87

    Therefore:

    Overall Score = 87 / 100