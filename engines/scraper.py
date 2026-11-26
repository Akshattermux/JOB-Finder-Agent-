import asyncio
import httpx
import re
import xml.etree.ElementTree as ET
import urllib.parse
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from core.database import DatabaseManager
from core.models import Job


class RemotiveJobScraper:
    """Fetches high-quality remote software development jobs from Remotive API."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Python", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        url = f"https://remotive.com/api/remote-jobs?search={urllib.parse.quote(keywords)}&limit={limit}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("jobs", [])[:limit]:
                        jobs.append({
                            "title": item.get("title", "Software Engineer"),
                            "company": item.get("company_name", "Tech Company"),
                            "location": item.get("candidate_required_location", "Remote"),
                            "url": item.get("url", "https://remotive.com"),
                            "description": item.get("description", item.get("title", "")),
                            "source": "remotive"
                        })
        except Exception:
            pass
        return jobs


class WeWorkRemotelyScraper:
    """Fetches jobs from We Work Remotely public RSS feeds."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Developer", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        feeds = [
            "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss"
        ]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"}
        kw_lower = keywords.lower()

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                for feed_url in feeds:
                    if len(jobs) >= limit:
                        break
                    resp = await client.get(feed_url)
                    if resp.status_code == 200:
                        try:
                            root = ET.fromstring(resp.text)
                            channel = root.find("channel")
                            if channel is not None:
                                for item in channel.findall("item"):
                                    title = item.findtext("title", "")
                                    link = item.findtext("link", "")
                                    desc = item.findtext("description", "")
                                    comp = item.findtext("company", "WWR Employer")

                                    if not kw_lower or kw_lower in title.lower() or kw_lower in desc.lower():
                                        jobs.append({
                                            "title": title,
                                            "company": comp,
                                            "location": "Worldwide Remote",
                                            "url": link,
                                            "description": desc[:1500] if desc else title,
                                            "source": "weworkremotely"
                                        })
                                        if len(jobs) >= limit:
                                            break
                        except Exception:
                            continue
        except Exception:
            pass
        return jobs


class LinkedInJobScraper:
    """Scrapes public LinkedIn job search listings targeting specific locations (e.g. Dehradun, Remote)."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Python Engineer", location: str = "Dehradun", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        encoded_kw = urllib.parse.quote(keywords)
        encoded_loc = urllib.parse.quote(location)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobCards?keywords={encoded_kw}&location={encoded_loc}&start=0"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("li")

                    for card in cards[:limit]:
                        title_elem = card.find("h3", class_=re.compile(r"base-search-card__title"))
                        company_elem = card.find("h4", class_=re.compile(r"base-search-card__subtitle"))
                        loc_elem = card.find("span", class_=re.compile(r"job-search-card__location"))
                        link_elem = card.find("a", class_=re.compile(r"base-card__full-link"))

                        if title_elem and link_elem:
                            title = title_elem.text.strip()
                            company = company_elem.text.strip() if company_elem else "LinkedIn Employer"
                            loc = loc_elem.text.strip() if loc_elem else location
                            job_url = link_elem["href"].split("?")[0]

                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": job_url,
                                "description": f"Position for {title} at {company} in {loc}. Full listing: {job_url}.",
                                "source": "linkedin"
                            })
        except Exception:
            pass

        return jobs


class NaukriJobScraper:
    """Scrapes public job listings from Naukri targeting India and Dehradun."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Python", location: str = "Dehradun", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        kw_slug = keywords.lower().replace(" ", "-")
        loc_slug = location.lower().replace(" ", "-")
        url = f"https://www.naukri.com/{kw_slug}-jobs-in-{loc_slug}?k={urllib.parse.quote(keywords)}&l={urllib.parse.quote(location)}"

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    article_cards = soup.find_all("div", class_=re.compile(r"cust-job-tuple|jobTuple|srp-jobtuple"))

                    for card in article_cards[:limit]:
                        title_elem = card.find("a", class_=re.compile(r"title"))
                        comp_elem = card.find("a", class_=re.compile(r"comp-name|subTitle"))
                        loc_elem = card.find("span", class_=re.compile(r"loc-wrap|location"))

                        if title_elem:
                            title = title_elem.text.strip()
                            company = comp_elem.text.strip() if comp_elem else "Naukri Hiring Enterprise"
                            loc = loc_elem.text.strip() if loc_elem else location
                            job_url = title_elem.get("href", url)

                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": job_url,
                                "description": f"Role for {title} at {company} in {loc}.",
                                "source": "naukri"
                            })
        except Exception:
            pass

        return jobs


class IndeedJobScraper:
    """Scrapes public Indeed job search listings for India & Dehradun."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Full Stack", location: str = "Dehradun", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        url = f"https://in.indeed.com/jobs?q={urllib.parse.quote(keywords)}&l={urllib.parse.quote(location)}"

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("div", class_=re.compile(r"job_seen_beacon|cardOutline"))

                    for card in cards[:limit]:
                        title_elem = card.find("a", class_=re.compile(r"jxf|jobTitle"))
                        comp_elem = card.find("span", class_=re.compile(r"companyName|company_location"))
                        loc_elem = card.find("div", class_=re.compile(r"companyLocation"))

                        if title_elem:
                            title = title_elem.text.strip()
                            company = comp_elem.text.strip() if comp_elem else "Indeed Employer"
                            loc = loc_elem.text.strip() if loc_elem else location
                            job_url = "https://in.indeed.com" + title_elem.get("href", "")

                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": job_url,
                                "description": f"Role for {title} at {company} ({loc}). Full details on Indeed.",
                                "source": "indeed"
                            })
        except Exception:
            pass

        return jobs


class YCombinatorJobScraper:
    """Fetches job postings from HackerNews Y Combinator Job Stories API."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Python", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                hn_resp = await client.get("https://hacker-news.firebaseio.com/v0/jobstories.json")
                if hn_resp.status_code == 200:
                    story_ids = hn_resp.json()[:limit]
                    for sid in story_ids:
                        s_resp = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                        if s_resp.status_code == 200:
                            data = s_resp.json()
                            if data and "title" in data:
                                title_raw = data["title"]
                                url = data.get("url", f"https://news.ycombinator.com/item?id={sid}")
                                jobs.append({
                                    "title": title_raw,
                                    "company": "YC Startup",
                                    "location": "Remote / San Francisco",
                                    "url": url,
                                    "description": data.get("text", title_raw),
                                    "source": "ycombinator"
                                })
        except Exception:
            pass

        return jobs


class RemoteOKScraper:
    """Fetches real-time remote job feeds from RemoteOK & Jobicy APIs."""
    @staticmethod
    async def fetch_jobs(keywords: str = "Python", limit: int = 10) -> List[Dict[str, str]]:
        jobs = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
                # 1. Jobicy Remote Jobs API
                jobicy_url = f"https://jobicy.com/api/v2/remote-jobs?count={limit}&tag={urllib.parse.quote(keywords)}"
                resp = await client.get(jobicy_url)
                if resp.status_code == 200:
                    res_json = resp.json()
                    for item in res_json.get("jobs", []):
                        jobs.append({
                            "title": item.get("jobTitle", "Remote Engineer"),
                            "company": item.get("companyName", "Tech Company"),
                            "location": item.get("jobGeo", "Remote"),
                            "url": item.get("url", f"https://jobicy.com/{item.get('id')}"),
                            "description": item.get("jobDescription", "Remote engineering position."),
                            "source": "jobicy"
                        })

                # 2. RemoteOK API
                rok_url = "https://remoteok.com/api"
                rok_resp = await client.get(rok_url)
                if rok_resp.status_code == 200:
                    rok_data = rok_resp.json()
                    for item in rok_data[1:limit+1]:
                        if isinstance(item, dict) and "position" in item:
                            jobs.append({
                                "title": item.get("position"),
                                "company": item.get("company"),
                                "location": "Remote",
                                "url": item.get("url", "https://remoteok.com"),
                                "description": item.get("description", item.get("position")),
                                "source": "remoteok"
                            })
        except Exception:
            pass

        return jobs


class MockJobScraper:
    """Provides fallback sample job postings for Dehradun and Remote."""
    @staticmethod
    def get_sample_jobs() -> List[Dict[str, str]]:
        return [
            {
                "title": "Full Stack Engineer (React Native & Node.js/Python)",
                "company": "Axionik Tech Solutions",
                "location": "Dehradun, Uttarakhand, India (Hybrid)",
                "url": "https://example.com/careers/axionik-dehradun-fullstack-101",
                "description": (
                    "We are seeking a Full Stack Engineer based in Dehradun or Remote. "
                    "Requirements: React Native, JavaScript/TypeScript, Python (FastAPI/Express.js), "
                    "REST APIs, MongoDB/PostgreSQL, Socket.IO real-time systems. Experience shipping apps to Play Store is a plus."
                ),
                "source": "dehradun_tech_hub"
            },
            {
                "title": "Python Backend & AI Integration Developer",
                "company": "Himalayan Tech Labs",
                "location": "Dehradun, Uttarakhand (On-site)",
                "url": "https://example.com/jobs/himalayan-ai-backend-204",
                "description": (
                    "Looking for a Python Developer in Dehradun skilled in FastAPI, OpenCV, Gemini API, "
                    "MySQL/PostgreSQL, and async web applications."
                ),
                "source": "dehradun_careers"
            },
            {
                "title": "Remote React Native & Full Stack Engineer",
                "company": "Cognitive Cloud Global",
                "location": "Remote (India)",
                "url": "https://example.com/careers/cognitive-remote-dev-309",
                "description": (
                    "Join our product team building consumer mobile and web applications with React Native, Redux, "
                    "FastAPI/Node.js, Push Notifications, and clean UI animations."
                ),
                "source": "remote_india_feed"
            }
        ]


class JobScraperEngine:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def ingest_jobs(
        self, sources: Optional[List[str]] = None, keywords: str = "Full Stack", location: str = "Dehradun", limit: int = 10
    ) -> Dict[str, Any]:
        """Collect and save jobs across all portals (linkedin, naukri, indeed, remotive, wwr, remoteok, yc, mock, all)."""
        selected = [s.lower() for s in (sources or ["all"])]
        if "all" in selected:
            selected = ["linkedin", "naukri", "indeed", "remotive", "wwr", "remoteok", "yc", "mock"]

        all_collected = []
        target_locations = [location] if isinstance(location, str) else location
        if any(loc.lower() in ("dehradun", "gurugram", "gurgaon") for loc in target_locations):
            for extra in ["Dehradun", "Gurugram", "Remote"]:
                if extra not in target_locations:
                    target_locations.append(extra)

        for loc in target_locations:

            if "linkedin" in selected:
                lk_jobs = await LinkedInJobScraper.fetch_jobs(keywords, loc, limit)
                all_collected.extend(lk_jobs)

            if "naukri" in selected:
                nk_jobs = await NaukriJobScraper.fetch_jobs(keywords, loc, limit)
                all_collected.extend(nk_jobs)

            if "indeed" in selected:
                ind_jobs = await IndeedJobScraper.fetch_jobs(keywords, loc, limit)
                all_collected.extend(ind_jobs)

        if "remotive" in selected:
            remotive_jobs = await RemotiveJobScraper.fetch_jobs(keywords, limit)
            all_collected.extend(remotive_jobs)

        if "wwr" in selected:
            wwr_jobs = await WeWorkRemotelyScraper.fetch_jobs(keywords, limit)
            all_collected.extend(wwr_jobs)

        if "remoteok" in selected:
            rok_jobs = await RemoteOKScraper.fetch_jobs(keywords, limit)
            all_collected.extend(rok_jobs)

        if "yc" in selected:
            yc_jobs = await YCombinatorJobScraper.fetch_jobs(keywords, limit)
            all_collected.extend(yc_jobs)

        if "mock" in selected or not all_collected:
            all_collected.extend(MockJobScraper.get_sample_jobs())

        added_count = 0
        duplicate_count = 0

        for raw_job in all_collected:
            saved_job = await self.db.save_job(
                title=raw_job["title"],
                company=raw_job["company"],
                location=raw_job["location"],
                url=raw_job["url"],
                description=raw_job["description"],
                source=raw_job.get("source", "direct")
            )
            if saved_job:
                added_count += 1
            else:
                duplicate_count += 1

        return {
            "total_fetched": len(all_collected),
            "added": added_count,
            "duplicates": duplicate_count,
            "sources": selected,
            "locations": target_locations
        }
