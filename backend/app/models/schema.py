"""All PostgreSQL SQLAlchemy models for NM-HireX.

Keeping the tables in one file makes the compact backend easy to navigate.
PostgreSQL is the source of truth; all searching is done natively in Postgres.
"""
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# ============================================================
# USERS
# Stores recruiters/users and administrators.
# ============================================================
class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(30), default="RECRUITER", nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="PENDING", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20),default="PENDING",nullable=False)
# ============================================================
# JOBS
# One row per JD uploaded by a user. created_by is the uploader.
# ============================================================
class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    work_mode: Mapped[str | None] = mapped_column(String(50))
    jd_file_url: Mapped[str | None] = mapped_column(Text)
    jd_file_name: Mapped[str | None] = mapped_column(String(255))
    jd_raw_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    requirements = relationship("JobRequirement", back_populates="job", uselist=False, cascade="all, delete-orphan")

# ============================================================
# JOB REQUIREMENTS
# Structured JD extracted by the AI extraction layer.
# ============================================================
class JobRequirement(Base):
    __tablename__ = "job_requirements"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255))
    minimum_experience: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    maximum_experience: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    location: Mapped[str | None] = mapped_column(String(255))
    work_mode: Mapped[str | None] = mapped_column(String(50))
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    mandatory_skills: Mapped[list | None] = mapped_column(JSONB, default=list)
    preferred_skills: Mapped[list | None] = mapped_column(JSONB, default=list)
    education: Mapped[list | None] = mapped_column(JSONB, default=list)
    certifications: Mapped[list | None] = mapped_column(JSONB, default=list)
    domains: Mapped[list | None] = mapped_column(JSONB, default=list)
    responsibilities: Mapped[list | None] = mapped_column(JSONB, default=list)
    other_requirements: Mapped[list | None] = mapped_column(JSONB, default=list)
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    extraction_version: Mapped[str | None] = mapped_column(String(50))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    job = relationship("Job", back_populates="requirements")

# ============================================================
# JOB SOURCES
# Kept for source configuration/audit. NM-HireX does not use Naukri.
# ============================================================
class JobSource(Base):
    __tablename__ = "job_sources"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    search_criteria: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str | None] = mapped_column(String(50))
    candidates_found: Mapped[int | None] = mapped_column(Integer)
    searched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

# ============================================================
# CANDIDATES
# Master candidate profile independent of a particular JD.
# ============================================================
class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    location: Mapped[str | None] = mapped_column(String(255))
    total_experience_years: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    current_company: Mapped[str | None] = mapped_column(String(255))
    current_role: Mapped[str | None] = mapped_column(String(255))
    notice_period_days: Mapped[int | None] = mapped_column(Integer)
    profile_summary: Mapped[str | None] = mapped_column(Text)
    raw_profile_text: Mapped[str | None] = mapped_column(Text)
    normalized_profile: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================================
# CANDIDATE SOURCES
# External-source mapping; not used for Naukri in this implementation.
# ============================================================
class CandidateSource(Base):
    __tablename__ = "candidate_sources"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    external_candidate_id: Mapped[str | None] = mapped_column(String(255))
    profile_url: Mapped[str | None] = mapped_column(Text)
    raw_source_data: Mapped[dict | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("source_name", "external_candidate_id", name="uq_candidate_source"),)

# =================================================================
# RESUMES
# Resume metadata, original extracted text, and AI extraction JSON.
# ===================================================================
class Resume(Base):
    __tablename__ = "resumes"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text)
    file_type: Mapped[str | None] = mapped_column(String(50))
    file_size: Mapped[int | None] = mapped_column(Integer)
    file_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    raw_text: Mapped[str | None] = mapped_column(Text)
    # search_vector is a PostgreSQL GENERATED ALWAYS column populated automatically
    # from raw_text by the database. SQLAlchemy treats it as read-only.
    search_vector: Mapped[object | None] = mapped_column(TSVECTOR, nullable=True)
    parsed_data: Mapped[dict | None] = mapped_column(JSONB)
    parsing_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    extraction_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    extraction_model: Mapped[str | None] = mapped_column(String(100))
    extraction_version: Mapped[str | None] = mapped_column(String(50))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# SKILL TAXONOMY
# Canonical skill names and parent/category relationships.
# ============================================================
class SkillTaxonomy(Base):
    __tablename__ = "skill_taxonomy"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    skill_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_skill: Mapped[str | None] = mapped_column(String(150))
    category: Mapped[str | None] = mapped_column(String(100))
    aliases: Mapped[list | None] = mapped_column(JSONB, default=list)
    related_skills: Mapped[list | None] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE SKILLS
# Preserves the actual skill; parent_skill is only a relationship.
# Example: Django remains Django, parent_skill=Python.
# ============================================================
class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(150), nullable=False)
    normalized_skill_name: Mapped[str] = mapped_column(String(150), nullable=False)
    parent_skill: Mapped[str | None] = mapped_column(String(150))
    skill_category: Mapped[str | None] = mapped_column(String(100))
    experience_years: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    proficiency: Mapped[str | None] = mapped_column(String(50))
    source: Mapped[str | None] = mapped_column(String(50))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE EXPERIENCE
# Employment and domain evidence used for experience/domain scoring.
# ============================================================
class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    job_title: Mapped[str | None] = mapped_column(String(255))
    employment_type: Mapped[str | None] = mapped_column(String(100))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool | None] = mapped_column(Boolean)
    description: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(255))
    normalized_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE EDUCATION
# ============================================================
class CandidateEducation(Base):
    __tablename__ = "candidate_education"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    degree: Mapped[str | None] = mapped_column(String(255))
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    institution: Mapped[str | None] = mapped_column(String(255))
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    grade: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE CERTIFICATIONS
# ============================================================
class CandidateCertification(Base):
    __tablename__ = "candidate_certifications"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    certification_name: Mapped[str | None] = mapped_column(String(255))
    issuing_organization: Mapped[str | None] = mapped_column(String(255))
    issue_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date)
    credential_id: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE PROJECTS
# Project evidence used for domain and semantic matching.
# ============================================================
class CandidateProject(Base):
    __tablename__ = "candidate_projects"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    project_name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    technologies: Mapped[list | None] = mapped_column(JSONB)
    domain: Mapped[str | None] = mapped_column(String(255))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# JOB CANDIDATES
# Links a candidate to one JD and stores job-specific ranking/status.
# ============================================================
class JobCandidate(Base):
    __tablename__ = "job_candidates"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("candidate_sources.id", ondelete="SET NULL"))
    eligibility_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    recruitment_status: Mapped[str] = mapped_column(String(50), default="NEW")
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    classification: Mapped[str | None] = mapped_column(String(50))
    is_shortlisted: Mapped[bool] = mapped_column(Boolean, default=False)
    ranking_position: Mapped[int | None] = mapped_column(Integer)
    interview_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interview_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),)

# ============================================================
# SCREENING RESULTS
# Stores the complete explainable score breakdown and evidence.
# ============================================================
class ScreeningResult(Base):
    __tablename__ = "screening_results"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_candidate_id: Mapped[UUID] = mapped_column(ForeignKey("job_candidates.id", ondelete="CASCADE"), unique=True, nullable=False)
    mandatory_skills_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    experience_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    domain_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    preferred_skills_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    education_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    location_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    availability_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    other_requirements_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)
    matching_details: Mapped[dict | None] = mapped_column(JSONB)
    semantic_matches: Mapped[list | None] = mapped_column(JSONB)
    missing_requirements: Mapped[list | None] = mapped_column(JSONB)
    strengths: Mapped[list | None] = mapped_column(JSONB)
    concerns: Mapped[list | None] = mapped_column(JSONB)
    screening_model: Mapped[str | None] = mapped_column(String(100))
    screening_version: Mapped[str | None] = mapped_column(String(50))
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# SCREENING RUNS
# Tracks one complete screening operation for a JD.
# ============================================================
class ScreeningRun(Base):
    __tablename__ = "screening_runs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="QUEUED")
    total_candidates: Mapped[int] = mapped_column(Integer, default=0)
    processed_candidates: Mapped[int] = mapped_column(Integer, default=0)
    successful_candidates: Mapped[int] = mapped_column(Integer, default=0)
    failed_candidates: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

# ============================================================
# CANDIDATE STATUS HISTORY
# Audit trail for admin/user status changes.
# ============================================================
class CandidateStatusHistory(Base):
    __tablename__ = "candidate_status_history"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_candidate_id: Mapped[UUID] = mapped_column(ForeignKey("job_candidates.id", ondelete="CASCADE"), nullable=False)
    old_status: Mapped[str | None] = mapped_column(String(50))
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    changed_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE CONTACTS
# Outreach history. Kept as a table for the complete schema but not
# invoked by the core JD-to-Top-10 pipeline.
# ============================================================
class CandidateContact(Base):
    __tablename__ = "candidate_contacts"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_candidate_id: Mapped[UUID] = mapped_column(ForeignKey("job_candidates.id", ondelete="CASCADE"), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(50))
    message_type: Mapped[str | None] = mapped_column(String(100))
    message: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(100))
    external_message_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(50))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    response_text: Mapped[str | None] = mapped_column(Text)
    response_intent: Mapped[str | None] = mapped_column(String(50))  # POSITIVE | NEGATIVE | NEUTRAL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# CANDIDATE ASSESSMENTS
# Future test/interview assignment history.
# ============================================================
class CandidateAssessment(Base):
    __tablename__ = "candidate_assessments"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    job_candidate_id: Mapped[UUID] = mapped_column(ForeignKey("job_candidates.id", ondelete="CASCADE"), nullable=False)
    assessment_type: Mapped[str | None] = mapped_column(String(100))
    provider: Mapped[str | None] = mapped_column(String(100))
    external_assessment_id: Mapped[str | None] = mapped_column(String(255))
    assessment_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(50), default="PENDING")
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    result: Mapped[str | None] = mapped_column(String(50))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# INTEGRATION EVENTS
# Generic external integration audit table.
# ============================================================
class IntegrationEvent(Base):
    __tablename__ = "integration_events"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100))
    entity_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    request_data: Mapped[dict | None] = mapped_column(JSONB)
    response_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

# ============================================================
# AI EXTRACTION LOGS
# Audit trail for JD/CV extraction and validation.
# ============================================================
class AIExtractionLog(Base):
    __tablename__ = "ai_extraction_logs"
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    input_text_hash: Mapped[str | None] = mapped_column(String(255))
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    validation_status: Mapped[str | None] = mapped_column(String(50))
    validation_errors: Mapped[list | None] = mapped_column(JSONB)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
