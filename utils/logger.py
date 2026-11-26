import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.style import Style

console = Console()


def log_info(msg: str):
    console.print(f"[bold cyan][INFO][/bold cyan] {msg}")


def log_success(msg: str):
    console.print(f"[bold green][SUCCESS][/bold green] {msg}")


def log_warning(msg: str):
    console.print(f"[bold yellow][WARNING][/bold yellow] {msg}")


def log_error(msg: str):
    console.print(f"[bold red][ERROR][/bold red] {msg}")


def print_banner():
    panel = Panel(
        "[bold magenta]Hybrid Job-Application Agent[/bold magenta]\n"
        "[dim]Python Engine + Playwright + SQLite + Gemini API (Free Tier)[/dim]",
        expand=False,
        border_style="magenta"
    )
    console.print(panel)


def display_dashboard_table(stats: dict):
    table = Table(title="Pipeline Application Tracker", show_header=True, header_style="bold blue")
    table.add_column("Stage / Status", style="dim")
    table.add_column("Count", justify="right")

    status_colors = {
        "DISCOVERED": "cyan",
        "EVALUATED": "yellow",
        "TAILORED": "magenta",
        "APPLIED": "green",
        "SKIPPED": "dim",
        "FAILED": "red"
    }

    for status, count in stats.items():
        color = status_colors.get(status, "white")
        table.add_row(f"[{color}]{status}[/{color}]", str(count))

    console.print(table)


def display_applications_table(jobs: list, title: str = "Job Applications"):
    table = Table(title=title, show_header=True, header_style="bold blue")
    table.add_column("ID", justify="right", style="dim", width=4)
    table.add_column("Company", style="bold white")
    table.add_column("Job Title", style="cyan")
    table.add_column("Location", style="green")
    table.add_column("Source", style="yellow")
    table.add_column("Status", style="magenta")
    table.add_column("Score", justify="right")
    table.add_column("URL / Application Link", style="blue dim", overflow="fold")

    status_colors = {
        "DISCOVERED": "cyan",
        "EVALUATED": "yellow",
        "TAILORED": "magenta",
        "APPLIED": "green",
        "SKIPPED": "dim",
        "FAILED": "red"
    }

    for job in jobs:
        st = job.status.value if hasattr(job.status, "value") else str(job.status)
        color = status_colors.get(st, "white")
        score_str = f"{job.score}/100" if job.score is not None else "-"
        table.add_row(
            str(job.id),
            job.company[:25],
            job.title[:35],
            job.location[:25],
            job.source,
            f"[{color}]{st}[/{color}]",
            score_str,
            job.url
        )

    console.print(table)


def display_job_detail(job):
    st = job.status.value if hasattr(job.status, "value") else str(job.status)
    content = (
        f"[bold cyan]ID:[/bold cyan] {job.id}\n"
        f"[bold cyan]Company:[/bold cyan] {job.company}\n"
        f"[bold cyan]Title:[/bold cyan] {job.title}\n"
        f"[bold cyan]Location:[/bold cyan] {job.location}\n"
        f"[bold cyan]Source Portal:[/bold cyan] {job.source}\n"
        f"[bold cyan]Status:[/bold cyan] {st}\n"
        f"[bold cyan]Match Score:[/bold cyan] {job.score}/100\n"
        f"[bold cyan]URL:[/bold cyan] {job.url}\n"
        f"[bold cyan]Applied At:[/bold cyan] {job.applied_at or 'N/A'}\n"
        f"[bold cyan]Notes:[/bold cyan] {job.notes or 'N/A'}\n"
    )
    if job.cover_letter:
        content += f"\n[bold green]--- Tailored Cover Letter ---[/bold green]\n{job.cover_letter}\n"
    if job.answers_json:
        content += f"\n[bold green]--- Generated Screening Q&A ---[/bold green]\n{job.answers_json}\n"

    panel = Panel(content, title=f"Job Application #{job.id} Detail", border_style="cyan")
    console.print(panel)

