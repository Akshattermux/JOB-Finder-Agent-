import asyncio
import yaml
from typing import Dict, Any, List
from core.database import DatabaseManager
from core.gemini_client import GeminiClient
from core.models import JobStatus, JobEvaluation
from utils.resume_parser import extract_resume_text


class JobEvaluatorEngine:
    def __init__(self, db: DatabaseManager, gemini_client: GeminiClient, profile_data: Dict[str, Any]):
        self.db = db
        self.gemini_client = gemini_client
        self.profile_data = profile_data
        
        # Load CV text if path provided
        resume_path = profile_data.get("resume_path", "")
        self.resume_text = extract_resume_text(resume_path) if resume_path else ""

    async def evaluate_pending_jobs(self, limit: int = 10) -> Dict[str, Any]:
        """Fetch DISCOVERED jobs and evaluate them using Gemini API + candidate decision rules."""
        pending_jobs = await self.db.get_jobs_by_status(JobStatus.DISCOVERED, limit=limit)
        
        decision_rules = self.profile_data.get("decision_rules", {})
        excluded_keywords = [k.lower() for k in decision_rules.get("excluded_keywords", [])]

        results = {
            "processed": len(pending_jobs),
            "qualified": 0,
            "skipped": 0,
            "evaluations": []
        }

        for job in pending_jobs:
            desc_lower = f"{job.title} {job.description}".lower()
            
            # Check excluded deal-breaker keywords
            hit_excluded = [kw for kw in excluded_keywords if kw in desc_lower]
            if hit_excluded:
                evaluation = JobEvaluation(
                    score=0,
                    apply=False,
                    matching_skills=[],
                    missing_skills=[],
                    reason=f"Skipped due to excluded deal-breaker keyword: {', '.join(hit_excluded)}",
                    key_pitch="Role filtered out by candidate decision rules."
                )
            else:
                evaluation: JobEvaluation = await self.gemini_client.evaluate_job_match(
                    job_title=job.title,
                    company=job.company,
                    job_description=job.description,
                    profile_data=self.profile_data,
                    resume_text=self.resume_text
                )

            await self.db.update_job_evaluation(job.id, evaluation)

            if evaluation.apply:
                results["qualified"] += 1
            else:
                results["skipped"] += 1

            results["evaluations"].append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "score": evaluation.score,
                "apply": evaluation.apply,
                "reason": evaluation.reason
            })

        return results
