# Hybrid Job-Application Agent 🚀

A modular, production-ready **Hybrid Job-Application Agent** built in Python. 

The system strictly separates **AI Intelligence** (powered by the free-tier Google Gemini Developer API) from **Deterministic System Operations** (job scraping, deduplication, SQLite tracking, Playwright browser automation, and rate limiting).

---

## 🏗️ System Architecture

```
                      Candidate Profile (user_profile.yaml)
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│                          PYTHON AGENT ENGINE                          │
│                                                                       │
│  ┌────────────────┐     ┌──────────────────┐    ┌──────────────────┐  │
│  │  Job Scraper / │ ──► │ SQLite Database  │ ──►│   Job Matcher /  │  │
│  │  Collector     │     │ (Job Pipeline)   │    │   Evaluator      │  │
│  └────────────────┘     └──────────────────┘    └────────┬─────────┘  │
│                                                          │            │
│  ┌────────────────┐     ┌──────────────────┐             │            │
│  │ Playwright Web │ ◄── │ Cover Letter &   │ ◄───────────┘            │
│  │ Auto-Applier   │     │ Q&A Tailor Engine│                          │
│  └────────────────┘     └──────────────────┘                          │
└──────────────────────────────────┬────────────────────────────────────┘
                                   │
                                   ▼ Gemini API (Structured JSON Schemas)
                     ┌───────────────────────────┐
                     │ Google Gemini API         │
                     │ (gemini-2.5-flash)        │
                     └───────────────────────────┘
```

---

## 🌟 Key Features

1. **Deterministic Execution**: Job collection, URL deduplication, SQLite persistence, and Playwright form interactions are handled strictly in Python.
2. **Gemini API Integration**: Uses the official `google-genai` SDK with Pydantic structured output schemas for 100% reliable JSON parsing.
3. **Free Tier Rate Limiter**: Built-in sliding window rate limiter (`GeminiRateLimiter`) ensuring API calls stay strictly within Gemini free tier RPM limits (15 RPM / 1M TPM / 1,500 RPD).
4. **Playwright Auto-Applier**: Automatically fills candidate contact details, attaches tailored cover letters, and handles custom screening questions. Supports both **Headed** (visible browser window for observation/manual CAPTCHA handling) and **Headless** modes.
5. **Rich CLI & Dashboard**: Clean command-line interface with pipeline statistics and progress formatting.

---

## ⚡ Quick Start & Setup

### 1. Environment Setup

Initialize virtual environment and install dependencies:

```bash
python -m venv .venv

# On Windows PowerShell:
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Install Playwright browser binaries:
playwright install chromium
```

### 2. Configure Gemini API Key

Obtain your free API key from [Google AI Studio](https://aistudio.google.com/).

Set the key in your environment or create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
PLAYWRIGHT_HEADLESS=false
```

### 3. Customize Candidate Profile

Edit `config/user_profile.yaml` to include your contact information, target job titles, technical skills, experience summary, and screening question presets.

---

## 🎮 Usage Guide

### 🌟 Single Command Interactive Select Menu (Recommended)
Simply run `python main.py`, `./run.sh`, or `run.bat` without arguments to launch the interactive select menu:

```bash
# On Linux / macOS / Git Bash:
./run.sh

# On Windows Command Prompt / PowerShell:
run.bat

# Or directly in Python:
python main.py
```

```text
Select an action to execute:
  [1] 🚀 Start Autonomous Continuous Loop (Dehradun, Gurugram, Remote)
  [2] ⚡ Run End-to-End Pipeline Once (Collect → Evaluate → Tailor → Apply)
  [3] 🔍 Collect Jobs Across All Portals
  [4] 🎯 Evaluate Pending Jobs with Gemini & CV Context
  [5] 📝 Tailor Cover Letters & Q&A
  [6] 🤖 Auto-Apply via Playwright (PDF CV Attached)
  [7] 📊 View Pipeline Dashboard & Statistics
  [8] 📜 View Application History & Applied Jobs List
  [9] ⚙️ Re-Initialize Database & Candidate Profile
  [0] ❌ Exit
```

---

### Command Line Direct Options
If you prefer running direct CLI subcommands:

```bash
# Start autonomous continuous loop
python main.py loop

# Run full end-to-end pipeline once
python main.py run-all --keywords "Full Stack Developer" --location "Dehradun" --headed

# View applied applications history table
python main.py history

# View details for a specific Job ID
python main.py history --id 1
```



---

## 📁 Project Structure

```
d:\Agent\
├── config/
│   ├── settings.py           # Application settings & environment variables
│   └── user_profile.yaml     # Candidate profile, skills & presets
├── core/
│   ├── database.py           # Async SQLite database manager
│   ├── models.py             # Pydantic data schemas
│   ├── rate_limiter.py       # Sliding window rate limiter for Gemini API
│   └── gemini_client.py      # Gemini API client with structured outputs
├── engines/
│   ├── scraper.py            # Job collector & deduplicator
│   ├── evaluator.py          # Match scoring engine
│   ├── tailor.py             # Cover letter & Q&A generator
│   └── applier.py            # Playwright browser auto-fill engine
├── utils/
│   ├── logger.py             # Rich console output formatting
│   └── resume_parser.py      # Profile & resume loader
├── cli.py                    # Main CLI application controller
├── pyproject.toml            # Project packaging specification
├── requirements.txt          # Python dependencies
└── README.md                 # Documentation
```
