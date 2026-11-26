import os
import json
import asyncio
import yaml
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from config.settings import GEMINI_API_KEY, DEFAULT_GEMINI_MODEL, GEMINI_RPM_LIMIT, GEMINI_RETRY_ATTEMPTS
from core.rate_limiter import GeminiRateLimiter
from core.models import JobEvaluation, TailoredApplication, ApplicationQuestion

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_GEMINI_MODEL):
        self.api_key = api_key or GEMINI_API_KEY
        self.model_name = model_name
        self.rate_limiter = GeminiRateLimiter(rpm_limit=GEMINI_RPM_LIMIT)
        self.client = None

        if GENAI_AVAILABLE and self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def is_configured(self) -> bool:
        return bool(self.client and self.api_key)

    async def evaluate_job_match(
        self, job_title: str, company: str, job_description: str, profile_data: Dict[str, Any], resume_text: str = ""
    ) -> JobEvaluation:
        """
        Evaluate job match using candidate profile, CV text, portfolio, and GitHub/LinkedIn links.
        """
        candidate = profile_data.get("candidate", {})
        decision_rules = profile_data.get("decision_rules", {})
        min_threshold = decision_rules.get("min_score_threshold", 70)

        prompt = f"""
You are an expert technical recruiter and career advisor evaluating candidate compatibility.

CANDIDATE DETAILS:
Name: {candidate.get('full_name')}
Email: {candidate.get('email')}
Location: {candidate.get('location')}
LinkedIn: {candidate.get('linkedin')}
GitHub: {candidate.get('github')}
Portfolio: {candidate.get('portfolio')}

CANDIDATE TOP PROJECTS:
{yaml.dump(profile_data.get('top_projects', []), sort_keys=False)}

CANDIDATE FULL CV / RESUME TEXT:
{resume_text if resume_text else 'Not provided directly.'}

DECISION THRESHOLD:
Minimum score required to apply: {min_threshold}/100

JOB DETAILS:
Title: {job_title}
Company: {company}
Description:
{job_description}

EVALUATION CRITERIA:
Compare the candidate's skills, resume experience, projects, and online links against the job description.
Return a structured output with:
- score: Integer from 0 to 100 representing overall fit.
- apply: True if score >= {min_threshold} and candidate meets essential requirements.
- matching_skills: List of candidate skills/experiences that directly match the role.
- missing_skills: Key requirements candidate lacks.
- reason: Concise 1-2 sentence justification for the match score.
- key_pitch: A 1-sentence value proposition tailored to this position.
"""

        if not self.is_configured():
            return self._mock_evaluation(job_title, job_description, profile_data, min_threshold)

        candidate_models = [self.model_name, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        # Deduplicate while preserving order
        candidate_models = list(dict.fromkeys(candidate_models))

        for model in candidate_models:
            await self.rate_limiter.wait_if_needed()
            try:
                def _call():
                    return self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=JobEvaluation,
                            temperature=0.2,
                        ),
                    )
                response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=8.0)

                if response.text:
                    data = json.loads(response.text)
                    return JobEvaluation(**data)
            except Exception as e:
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    continue
                await asyncio.sleep(0.5)

        return self._mock_evaluation(job_title, job_description, profile_data, min_threshold)

    async def generate_tailored_application(
        self,
        job_title: str,
        company: str,
        job_description: str,
        profile_data: Dict[str, Any],
        resume_text: str = "",
        screening_questions: Optional[List[str]] = None
    ) -> TailoredApplication:
        """
        Generate tailored cover letter & Q&A incorporating full CV text, Portfolio, and GitHub links.
        """
        candidate = profile_data.get("candidate", {})
        questions_str = "\n".join(f"- {q}" for q in (screening_questions or [])) if screening_questions else "None requested."

        prompt = f"""
You are an expert executive career strategist crafting tailored job application materials.

CANDIDATE DETAILS:
Name: {candidate.get('full_name')}
Email: {candidate.get('email')}
LinkedIn: {candidate.get('linkedin')}
GitHub: {candidate.get('github')}
Portfolio: {candidate.get('portfolio')}

CANDIDATE PROJECTS & RESUME:
{yaml.dump(profile_data.get('top_projects', []), sort_keys=False)}
{resume_text}

JOB DETAILS:
Title: {job_title}
Company: {company}
Description:
{job_description}

SCREENING QUESTIONS:
{questions_str}

TASKS:
1. Write a 3-paragraph tailored cover letter referencing candidate's specific background, projects, GitHub/Portfolio links, and interest in {company}.
2. Provide concise, direct answers to any screening questions using candidate data.

Return structured JSON with 'cover_letter' and 'answers'.
"""

        if not self.is_configured():
            return self._mock_tailored_application(job_title, company, screening_questions, candidate)

        candidate_models = [self.model_name, "gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
        candidate_models = list(dict.fromkeys(candidate_models))

        for model in candidate_models:
            await self.rate_limiter.wait_if_needed()
            try:
                def _call():
                    return self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TailoredApplication,
                            temperature=0.4,
                        ),
                    )
                response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=8.0)

                if response.text:
                    data = json.loads(response.text)
                    return TailoredApplication(**data)
            except Exception as e:
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    continue
                await asyncio.sleep(0.5)

        return self._mock_tailored_application(job_title, company, screening_questions, candidate)


    def _mock_evaluation(self, job_title: str, job_description: str, profile_data: Dict[str, Any], min_threshold: int) -> JobEvaluation:
        title_lower = job_title.lower()
        has_match = any(t.lower() in title_lower for t in profile_data.get("target_roles", [])) or "engineer" in title_lower or "developer" in title_lower

        score = 88 if has_match else 55
        return JobEvaluation(
            score=score,
            apply=score >= min_threshold,
            matching_skills=["Python", "JavaScript", "REST APIs", "Playwright", "SQLite"],
            missing_skills=["Kubernetes"] if score >= min_threshold else ["Java Enterprise", "C#"],
            reason=f"Candidate's full CV and project portfolio align well with {job_title}." if score >= min_threshold else "Skills do not meet primary role requirements.",
            key_pitch=f"Full-stack software engineer with deep Python, API design, and automation background tailored for {job_title}."
        )

    def _mock_tailored_application(
        self, job_title: str, company: str, questions: Optional[List[str]], candidate: Dict[str, Any]
    ) -> TailoredApplication:
        candidate_name = candidate.get("full_name", "Alex Vance")
        github_url = candidate.get("github", "https://github.com/alexvance")
        portfolio_url = candidate.get("portfolio", "https://alexvance.dev")

        cover_letter = (
            f"Dear Hiring Manager at {company},\n\n"
            f"I am writing to express my enthusiastic interest in the {job_title} position. "
            f"As the Founder & CEO of Axionik and the sole developer behind FriendsBook — a full-featured social networking platform live on the Google Play Store (friendsbook.co.in) — "
            f"I bring hands-on experience building, scaling, and deploying production mobile and web applications.\n\n"
            f"My core expertise spans React Native, JavaScript, Python (FastAPI/Express.js), Socket.IO real-time architecture, and AWS/Oracle Cloud infrastructure. "
            f"Whether building intuitive mobile user interfaces, designing high-throughput REST APIs, or configuring cloud deployments, I am accustomed to taking complete ownership of projects from concept to release.\n\n"
            f"You can explore my live applications, open-source repositories, and technical portfolio at {portfolio_url} and GitHub ({github_url}). "
            f"I would welcome the opportunity to discuss how my full-stack development skills and self-directed drive can contribute value to {company}.\n\n"
            f"Sincerely,\n{candidate_name}"
        )

        qa_list = []
        if questions:
            for q in questions:
                answer_text = f"As sole developer of FriendsBook on Google Play Store, I have deep practical experience handling '{q}' using React Native, Python, and cloud services."
                qa_list.append(ApplicationQuestion(
                    question=q,
                    answer=answer_text,
                    confidence=0.95
                ))

        return TailoredApplication(cover_letter=cover_letter, answers=qa_list)

