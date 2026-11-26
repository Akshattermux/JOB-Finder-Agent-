import asyncio
from typing import Dict, Any, List, Optional
from core.database import DatabaseManager
from core.gemini_client import GeminiClient
from core.models import JobStatus, TailoredApplication
from utils.resume_parser import extract_resume_text


class ApplicationTailorEngine:
    def __init__(self, db: DatabaseManager, gemini_client: GeminiClient, profile_data: Dict[str, Any]):
        self.db = db
        self.gemini_client = gemini_client
        self.profile_data = profile_data

        resume_path = profile_data.get("resume_path", "")
        self.resume_text = extract_resume_text(resume_path) if resume_path else ""

    async def tailor_qualified_jobs(self, limit: int = 10, default_questions: Optional[List[str]] = None) -> Dict[str, Any]:
        """Fetch EVALUATED jobs and generate tailored cover letters and Q&A."""
        qualified_jobs = await self.db.get_jobs_by_status(JobStatus.EVALUATED, limit=limit)
        
        sample_screening_questions = default_questions or [
            "Why do you want to work at this company?",
            "What is your experience with core backend frameworks?",
            "What are your salary expectations and notice period?"
        ]

        results = {
            "processed": len(qualified_jobs),
            "tailored": []
        }

        for job in qualified_jobs:
            tailored: TailoredApplication = await self.gemini_client.generate_tailored_application(
                job_title=job.title,
                company=job.company,
                job_description=job.description,
                profile_data=self.profile_data,
                resume_text=self.resume_text,
                screening_questions=sample_screening_questions
            )

            await self.db.update_job_tailored(
                job_id=job.id,
                cover_letter=tailored.cover_letter,
                answers=tailored.answers
            )

            results["tailored"].append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "questions_answered": len(tailored.answers)
            })

        return results
