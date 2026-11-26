from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    EVALUATED = "EVALUATED"
    TAILORED = "TAILORED"
    APPLIED = "APPLIED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class JobEvaluation(BaseModel):
    score: int = Field(description="Match percentage score from 0 to 100")
    apply: bool = Field(description="Boolean recommendation whether candidate should apply")
    matching_skills: List[str] = Field(default_factory=list, description="Skills candidate possesses that match the job requirements")
    missing_skills: List[str] = Field(default_factory=list, description="Key skills or requirements the candidate lacks")
    reason: str = Field(description="Brief 1-2 sentence explanation for the score")
    key_pitch: str = Field(description="Short sentence highlighting candidate's top value proposition for this role")


class ApplicationQuestion(BaseModel):
    question: str = Field(description="The question asked on the job application")
    answer: str = Field(description="Tailored response generated based on candidate's profile")
    confidence: float = Field(default=1.0, description="Confidence rating from 0.0 to 1.0")


class TailoredApplication(BaseModel):
    cover_letter: str = Field(description="Complete tailored cover letter text")
    answers: List[ApplicationQuestion] = Field(default_factory=list, description="Custom screening questions and generated answers")


class Job(BaseModel):
    id: Optional[int] = None
    title: str
    company: str
    location: str
    url: str
    description: str
    source: str = "direct"
    job_hash: str
    status: JobStatus = JobStatus.DISCOVERED
    score: Optional[int] = None
    evaluation_json: Optional[str] = None
    cover_letter: Optional[str] = None
    answers_json: Optional[str] = None
    applied_at: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
