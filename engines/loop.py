import asyncio
import sys
import time
from typing import Dict, Any, Optional, List
from core.database import DatabaseManager
from core.gemini_client import GeminiClient
from engines.scraper import JobScraperEngine
from engines.evaluator import JobEvaluatorEngine
from engines.tailor import ApplicationTailorEngine
from engines.applier import PlaywrightApplierEngine
from utils.logger import log_info, log_success, log_warning, log_error, print_banner, display_dashboard_table, display_applications_table
from utils.resume_parser import load_user_profile


class AutonomousLoopEngine:
    """
    Agile continuous loop engine that runs ongoing iterations of:
    Collect -> Evaluate -> Tailor -> Apply -> Report -> Sleep.
    """
    def __init__(
        self,
        db: DatabaseManager,
        gemini_client: GeminiClient,
        profile_data: Dict[str, Any],
        interval_seconds: int = 300,
        batch_size: int = 5,
        headless: bool = False,
        sources: Optional[List[str]] = None,
        keywords: str = "Full Stack Developer",
        location: str = "Dehradun",
    ):
        self.db = db
        self.gemini_client = gemini_client
        self.profile_data = profile_data
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.headless = headless
        self.sources = sources or ["all"]
        self.keywords = keywords
        self.location = location

        self.scraper = JobScraperEngine(db)
        self.evaluator = JobEvaluatorEngine(db, gemini_client, profile_data)
        self.tailor = ApplicationTailorEngine(db, gemini_client, profile_data)
        self.applier = PlaywrightApplierEngine(db, profile_data, headless=headless)

    async def run(self, max_cycles: Optional[int] = None):
        """Execute continuous agile application loop."""
        print_banner()
        log_info(f"🚀 Starting Autonomous Continuous Job Engine [Interval: {self.interval_seconds}s | Micro-Batch: {self.batch_size} jobs]")
        log_info(f"Target Locations: Dehradun, Gurugram, Remote | Roles: {self.keywords}")

        cycle = 1
        while True:
            log_info(f"\n=======================================================")
            log_info(f"🔄 AUTONOMOUS CYCLE #{cycle} STARTED at {time.strftime('%X')}")
            log_info(f"=======================================================")

            try:
                # 1. Collect
                log_info(f"Step 1/5: Ingesting fresh job postings across all portals...")
                c_res = await self.scraper.ingest_jobs(
                    sources=self.sources,
                    keywords=self.keywords,
                    location=self.location,
                    limit=self.batch_size
                )
                log_success(f"Ingested {c_res['added']} new jobs ({c_res['duplicates']} duplicates skipped).")

                # 2. Evaluate
                log_info(f"Step 2/5: Evaluating job fit against candidate CV with Gemini API...")
                e_res = await self.evaluator.evaluate_pending_jobs(limit=self.batch_size)
                log_success(f"Evaluated {e_res['processed']} jobs ({e_res['qualified']} qualified, {e_res['skipped']} skipped).")

                # 3. Tailor
                log_info(f"Step 3/5: Generating tailored cover letters & screening Q&A...")
                t_res = await self.tailor.tailor_qualified_jobs(limit=self.batch_size)
                log_success(f"Tailored {len(t_res['tailored'])} job applications.")

                # 4. Auto-Apply
                log_info(f"Step 4/5: Auto-submitting applications via Playwright (PDF CV attached)...")
                from core.models import JobStatus
                tailored = await self.db.get_jobs_by_status(JobStatus.TAILORED, limit=self.batch_size)
                applied_count = 0
                for job in tailored:
                    a_res = await self.applier.apply_to_job(job.id)
                    if a_res.get("success"):
                        applied_count += 1
                        log_success(f"Applied to {job.company} - {job.title}")
                    else:
                        log_error(f"Failed application for {job.company}: {a_res.get('error')}")

                log_success(f"Completed {applied_count} application submissions in this cycle.")

                # 5. Report Dashboard
                log_info(f"Step 5/5: Pipeline Statistics Update")
                stats = await self.db.get_pipeline_stats()
                display_dashboard_table(stats)

            except KeyboardInterrupt:
                log_warning("Autonomous loop stopped by user interrupt (Ctrl+C).")
                break
            except Exception as e:
                log_error(f"Error encountered in cycle #{cycle}: {e}")

            if max_cycles and cycle >= max_cycles:
                log_success(f"Reached specified max cycles limit ({max_cycles}). Loop complete.")
                break

            log_info(f"😴 Cycle #{cycle} finished. Sleeping for {self.interval_seconds} seconds before next iteration...\n")
            await asyncio.sleep(self.interval_seconds)
            cycle += 1
