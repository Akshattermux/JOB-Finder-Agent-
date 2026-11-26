import sys
import argparse
import asyncio
import os
from pathlib import Path

from config.settings import DB_PATH, PROFILE_PATH, GEMINI_API_KEY, HEADLESS_MODE
from core.database import DatabaseManager
from core.gemini_client import GeminiClient
from engines.scraper import JobScraperEngine
from engines.evaluator import JobEvaluatorEngine
from engines.tailor import ApplicationTailorEngine
from engines.applier import PlaywrightApplierEngine
from utils.logger import log_info, log_success, log_warning, log_error, print_banner, display_dashboard_table, display_applications_table, display_job_detail, console
from utils.resume_parser import load_user_profile, extract_resume_text
from core.models import JobStatus


async def cmd_init(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()
    log_success(f"Database initialized at: {DB_PATH}")

    if not Path(PROFILE_PATH).exists():
        log_warning(f"Profile configuration not found at {PROFILE_PATH}.")
    else:
        log_success(f"User profile loaded from: {PROFILE_PATH}")
        profile = load_user_profile(PROFILE_PATH)
        resume_path = profile.get("resume_path", "")
        if resume_path:
            text = extract_resume_text(resume_path)
            if text and not text.startswith("[Error"):
                log_success(f"Loaded Candidate Resume from {resume_path} ({len(text)} characters).")
            else:
                log_warning(f"Could not load resume text from {resume_path}: {text}")


async def cmd_history(args):

    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()

    job_id = getattr(args, "id", None)
    if job_id:
        job = await db.get_job_by_id(job_id)
        if job:
            display_job_detail(job)
        else:
            log_error(f"Job ID {job_id} not found in database.")
        return

    status_filter = getattr(args, "status", "APPLIED").upper()
    if status_filter == "ALL":
        jobs = await db.get_all_jobs(limit=args.limit)
        title = f"All Recent Applications (Last {len(jobs)})"
    else:
        try:
            st_enum = JobStatus(status_filter)
        except ValueError:
            st_enum = JobStatus.APPLIED
        jobs = await db.get_all_jobs(status=st_enum, limit=args.limit)
        title = f"Applied Applications List ({status_filter}: {len(jobs)})"

    if not jobs:
        log_warning(f"No job applications found matching status '{status_filter}'.")
    else:
        display_applications_table(jobs, title=title)


async def cmd_dashboard(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()
    stats = await db.get_pipeline_stats()
    display_dashboard_table(stats)


async def cmd_run_all(args):
    print_banner()
    log_info("=== Step 1: Initializing Database & Resume ===")
    await cmd_init(args)
    log_info("=== Step 2: Collecting Jobs Across Portals ===")
    await cmd_collect(args)
    log_info("=== Step 3: Evaluating Jobs with Gemini & CV Context ===")
    await cmd_evaluate(args)
    log_info("=== Step 4: Tailoring Applications with Gemini & Portfolio ===")
    await cmd_tailor(args)
    log_info("=== Step 5: Auto-Applying with Playwright ===")
    await cmd_apply(args)
    log_info("=== Step 6: Pipeline Summary ===")
    await cmd_dashboard(args)
    log_info("=== Step 7: View Applied Applications List ===")
    await cmd_history(args)
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()
    log_success(f"Database initialized at: {DB_PATH}")

    if not Path(PROFILE_PATH).exists():
        log_warning(f"Profile configuration not found at {PROFILE_PATH}.")
    else:
        log_success(f"User profile loaded from: {PROFILE_PATH}")
        profile = load_user_profile(PROFILE_PATH)
        resume_path = profile.get("resume_path", "")
        if resume_path:
            text = extract_resume_text(resume_path)
            if text and not text.startswith("[Error"):
                log_success(f"Loaded Candidate Resume from {resume_path} ({len(text)} characters).")
            else:
                log_warning(f"Could not load resume text from {resume_path}: {text}")


async def cmd_collect(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()

    sources = args.source.split(",") if hasattr(args, "source") and args.source else ["all"]
    keywords = getattr(args, "keywords", "Python Engineer")
    location = getattr(args, "location", "Remote")
    limit = getattr(args, "limit", 10)

    log_info(f"Starting job collection [Sources: {','.join(sources)} | Keywords: '{keywords}' | Location: '{location}']...")
    scraper = JobScraperEngine(db)
    result = await scraper.ingest_jobs(sources=sources, keywords=keywords, location=location, limit=limit)
    log_success(f"Collection complete: {result['added']} new jobs added ({result['total_fetched']} fetched across portals, {result['duplicates']} duplicates skipped).")


async def cmd_evaluate(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()

    profile = load_user_profile(PROFILE_PATH)
    client = GeminiClient(api_key=GEMINI_API_KEY)

    if not client.is_configured():
        log_warning("GEMINI_API_KEY is not set in environment. Running in offline/mock evaluation mode.")

    log_info("Starting job decision evaluation with Gemini API & CV Context...")
    evaluator = JobEvaluatorEngine(db, client, profile)
    res = await evaluator.evaluate_pending_jobs(limit=args.limit)
    log_success(f"Evaluated {res['processed']} jobs: {res['qualified']} qualified, {res['skipped']} skipped.")

    for item in res["evaluations"]:
        status_mark = "QUALIFIED" if item["apply"] else "SKIPPED"
        log_info(f"[{status_mark}] Score: {item['score']}/100 | {item['company']} - {item['title']}")
        log_info(f"   Reason: {item['reason']}")


async def cmd_tailor(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()

    profile = load_user_profile(PROFILE_PATH)
    client = GeminiClient(api_key=GEMINI_API_KEY)

    log_info("Tailoring application materials (cover letters & Q&A) with Gemini API & Portfolio links...")
    tailor = ApplicationTailorEngine(db, client, profile)
    res = await tailor.tailor_qualified_jobs(limit=args.limit)
    log_success(f"Successfully tailored {len(res['tailored'])} job applications.")


async def cmd_apply(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()

    profile = load_user_profile(PROFILE_PATH)
    headless = not getattr(args, "headed", False)
    applier = PlaywrightApplierEngine(db, profile, headless=headless)

    job_id = getattr(args, "job_id", None)
    if job_id:
        log_info(f"Submitting application for Job ID {job_id}...")
        res = await applier.apply_to_job(job_id)
        if res.get("success"):
            log_success(f"Successfully applied to {res['company']} ({res['title']})")
        else:
            log_error(f"Application failed: {res.get('error')}")
    else:
        from core.models import JobStatus
        limit = getattr(args, "limit", 5)
        tailored_jobs = await db.get_jobs_by_status(JobStatus.TAILORED, limit=limit)
        
        if not tailored_jobs:
            log_info("Found 0 pending TAILORED job applications (all previous tailored applications are already APPLIED!).")
            eval_jobs = await db.get_jobs_by_status(JobStatus.EVALUATED, limit=limit)
            disc_jobs = await db.get_jobs_by_status(JobStatus.DISCOVERED, limit=limit)

            if eval_jobs or disc_jobs:
                log_info(f"Auto-processing pipeline for pending jobs ({len(disc_jobs)} discovered, {len(eval_jobs)} evaluated)...")
                if disc_jobs:
                    log_info("=== Evaluating pending DISCOVERED jobs ===")
                    await cmd_evaluate(args)
                log_info("=== Tailoring qualified EVALUATED jobs ===")
                await cmd_tailor(args)
                tailored_jobs = await db.get_jobs_by_status(JobStatus.TAILORED, limit=limit)

        log_info(f"Found {len(tailored_jobs)} pending tailored job applications to submit.")

        for job in tailored_jobs:
            log_info(f"Processing application: {job.company} - {job.title}")
            res = await applier.apply_to_job(job.id)
            if res.get("success"):
                log_success(f"Applied to {job.company} - {job.title}")
            else:
                log_error(f"Failed application for {job.company}: {res.get('error')}")



async def cmd_dashboard(args):
    print_banner()
    db = DatabaseManager(DB_PATH)
    await db.init_db()
    stats = await db.get_pipeline_stats()
    display_dashboard_table(stats)


async def cmd_loop(args):
    db = DatabaseManager(DB_PATH)
    await db.init_db()
    profile = load_user_profile(PROFILE_PATH)
    client = GeminiClient(api_key=GEMINI_API_KEY)
    headless = not getattr(args, "headed", False)
    sources = args.source.split(",") if hasattr(args, "source") and args.source else ["all"]
    keywords = getattr(args, "keywords", "Full Stack Developer")
    location = getattr(args, "location", "Dehradun")
    interval = getattr(args, "interval", 300)
    batch_size = getattr(args, "batch_size", 5)
    max_cycles = getattr(args, "max_cycles", None)

    from engines.loop import AutonomousLoopEngine
    engine = AutonomousLoopEngine(
        db=db,
        gemini_client=client,
        profile_data=profile,
        interval_seconds=interval,
        batch_size=batch_size,
        headless=headless,
        sources=sources,
        keywords=keywords,
        location=location
    )
    await engine.run(max_cycles=max_cycles)


async def cmd_run_all(args):
    print_banner()
    log_info("=== Step 1: Initializing Database & Resume ===")
    await cmd_init(args)
    log_info("=== Step 2: Collecting Jobs Across Portals ===")
    await cmd_collect(args)
    log_info("=== Step 3: Evaluating Jobs with Gemini & CV Context ===")
    await cmd_evaluate(args)
    log_info("=== Step 4: Tailoring Applications with Gemini & Portfolio ===")
    await cmd_tailor(args)
    log_info("=== Step 5: Auto-Applying with Playwright ===")
    await cmd_apply(args)
    log_info("=== Step 6: Pipeline Summary ===")
    await cmd_dashboard(args)


async def run_interactive_menu():
    print_banner()
    console.print("\n[bold yellow]Select an action to execute:[/bold yellow]\n")
    console.print("  [bold green][1][/bold green] 🚀 [bold white]Start Autonomous Continuous Loop[/bold white] (Dehradun, Gurugram, Remote)")
    console.print("  [bold green][2][/bold green] ⚡ [bold white]Run End-to-End Pipeline Once[/bold white] (Collect → Evaluate → Tailor → Apply)")
    console.print("  [bold green][3][/bold green] 🔍 [bold white]Collect Jobs Across All Portals[/bold white]")
    console.print("  [bold green][4][/bold green] 🎯 [bold white]Evaluate Pending Jobs with Gemini & CV Context[/bold white]")
    console.print("  [bold green][5][/bold green] 📝 [bold white]Tailor Cover Letters & Q&A[/bold white]")
    console.print("  [bold green][6][/bold green] 🤖 [bold white]Auto-Apply via Playwright[/bold white] (PDF CV Attached)")
    console.print("  [bold green][7][/bold green] 📊 [bold white]View Pipeline Dashboard & Statistics[/bold white]")
    console.print("  [bold green][8][/bold green] 📜 [bold white]View Application History & Applied Jobs List[/bold white]")
    console.print("  [bold green][9][/bold green] ⚙️ [bold white]Re-Initialize Database & Candidate Profile[/bold white]")
    console.print("  [bold red][0][/bold red] ❌ [bold white]Exit[/bold white]\n")

    try:
        choice = input("Enter choice (0-9) [Default: 1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    class DummyArgs:
        pass

    args = DummyArgs()
    args.source = "all"
    args.keywords = "Full Stack Developer"
    args.location = "Dehradun"
    args.limit = 10
    args.batch_size = 5
    args.interval = 300
    args.max_cycles = None
    args.headed = False
    args.status = "APPLIED"
    args.id = None

    if choice == "1":
        await cmd_loop(args)
    elif choice == "2":
        await cmd_run_all(args)
    elif choice == "3":
        await cmd_collect(args)
    elif choice == "4":
        await cmd_evaluate(args)
    elif choice == "5":
        await cmd_tailor(args)
    elif choice == "6":
        await cmd_apply(args)
    elif choice == "7":
        await cmd_dashboard(args)
    elif choice == "8":
        await cmd_history(args)
    elif choice == "9":
        await cmd_init(args)
    elif choice == "0":
        log_info("Exiting Hybrid Job-Application Agent. Goodbye!")
        return
    else:
        log_warning("Invalid choice. Running Autonomous Continuous Loop...")
        await cmd_loop(args)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Hybrid Job-Application Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("init", help="Initialize database and candidate profile/resume")

    collect_p = subparsers.add_parser("collect", help="Ingest real job listings from all portals")
    collect_p.add_argument("--source", type=str, default="all", help="Portals: linkedin,naukri,indeed,remotive,wwr,remoteok,yc,mock,all")
    collect_p.add_argument("--keywords", type=str, default="Full Stack Developer", help="Search keywords")
    collect_p.add_argument("--location", type=str, default="Dehradun", help="Location preference (e.g. Dehradun, Remote)")
    collect_p.add_argument("--limit", type=int, default=10, help="Max jobs per source")

    eval_p = subparsers.add_parser("evaluate", help="Score jobs using Gemini API & CV Context")
    eval_p.add_argument("--limit", type=int, default=10, help="Max jobs to evaluate")

    tailor_p = subparsers.add_parser("tailor", help="Generate tailored cover letters & Q&A")
    tailor_p.add_argument("--limit", type=int, default=10, help="Max jobs to tailor")

    apply_p = subparsers.add_parser("apply", help="Auto-fill applications with Playwright")
    apply_p.add_argument("--job-id", type=int, help="Specific Job ID to apply for")
    apply_p.add_argument("--limit", type=int, default=5, help="Max jobs to apply")
    apply_p.add_argument("--headed", action="store_true", help="Launch browser in visible headed mode")

    subparsers.add_parser("dashboard", help="Show application status pipeline")

    hist_p = subparsers.add_parser("history", help="List submitted applications with details")
    hist_p.add_argument("--status", type=str, default="APPLIED", help="Filter status: APPLIED, EVALUATED, SKIPPED, DISCOVERED, ALL")
    hist_p.add_argument("--limit", type=int, default=50, help="Max entries to show")
    hist_p.add_argument("--id", type=int, help="Show full details for specific Job ID")

    apps_p = subparsers.add_parser("applications", help="Alias for history: list submitted applications")
    apps_p.add_argument("--status", type=str, default="APPLIED", help="Filter status: APPLIED, EVALUATED, SKIPPED, DISCOVERED, ALL")
    apps_p.add_argument("--limit", type=int, default=50, help="Max entries to show")
    apps_p.add_argument("--id", type=int, help="Show full details for specific Job ID")

    loop_p = subparsers.add_parser("loop", help="Run continuous autonomous application loop")
    loop_p.add_argument("--source", type=str, default="all", help="Portals: linkedin,naukri,indeed,remotive,wwr,remoteok,yc,mock,all")
    loop_p.add_argument("--keywords", type=str, default="Full Stack Developer", help="Search keywords")
    loop_p.add_argument("--location", type=str, default="Dehradun", help="Location preference (e.g. Dehradun, Gurugram, Remote)")
    loop_p.add_argument("--batch-size", type=int, default=5, help="Micro-batch size per cycle")
    loop_p.add_argument("--interval", type=int, default=300, help="Sleep interval in seconds between cycles")
    loop_p.add_argument("--max-cycles", type=int, help="Optional max iterations (default: infinite loop)")
    loop_p.add_argument("--headed", action="store_true", help="Launch browser in visible headed mode")

    run_p = subparsers.add_parser("run-all", help="Execute complete end-to-end pipeline across portals")
    run_p.add_argument("--source", type=str, default="all", help="Portals: linkedin,naukri,indeed,remotive,wwr,remoteok,yc,mock,all")
    run_p.add_argument("--keywords", type=str, default="Full Stack Developer", help="Search keywords")
    run_p.add_argument("--location", type=str, default="Dehradun", help="Location preference (e.g. Dehradun, Remote)")
    run_p.add_argument("--limit", type=int, default=5, help="Max jobs per stage")
    run_p.add_argument("--headed", action="store_true", help="Launch browser in visible headed mode")

    args = parser.parse_args()

    if not args.command:
        asyncio.run(run_interactive_menu())
        return

    cmd_map = {
        "init": cmd_init,
        "collect": cmd_collect,
        "evaluate": cmd_evaluate,
        "tailor": cmd_tailor,
        "apply": cmd_apply,
        "dashboard": cmd_dashboard,
        "history": cmd_history,
        "applications": cmd_history,
        "loop": cmd_loop,
        "run-all": cmd_run_all,
    }

    asyncio.run(cmd_map[args.command](args))




if __name__ == "__main__":
    main()

