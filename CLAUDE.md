# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**My Daily Brief** — a personalized daily newsletter web app built with Python and Flask.

Users register, select interest categories, and receive an AI-curated newsletter pulled from RSS feeds and optionally NewsAPI. Newsletters are generated on demand or dispatched automatically on a daily schedule. Articles are summarized using the Anthropic API.

## Setup & Run

```bash
pip install -r requirements.txt
python app.py
```

The app runs at http://localhost:5000.

## Environment Variables

Create a `.env` file in the project root (all optional except where noted):

```env
# Flask
SECRET_KEY=your-secret-key-here

# Database (defaults to SQLite)
DATABASE_URL=sqlite:///newsletter.db

# Anthropic API — required for AI article summarization and newsletter intro
ANTHROPIC_API_KEY=sk-ant-...

# NewsAPI — optional, augments RSS feeds with top headlines
NEWS_API_KEY=...

# SMTP — required for email delivery
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=you@gmail.com
EMAIL_FROM_NAME=My Daily Brief

# Newsletter schedule (UTC, defaults to 07:00)
NEWSLETTER_SEND_HOUR=7
NEWSLETTER_SEND_MINUTE=0
```

## Architecture

| File/Directory | Purpose |
|---|---|
| `app.py` | Flask app factory, all routes |
| `config.py` | Config class, reads from env |
| `models.py` | SQLAlchemy models: User, Category, Newsletter |
| `newsletter/curator.py` | RSS/Atom feed fetching and NewsAPI integration |
| `newsletter/summarizer.py` | Article summarization via Anthropic API |
| `newsletter/generator.py` | HTML and plain-text newsletter rendering |
| `newsletter/mailer.py` | SMTP email delivery |
| `newsletter/scheduler.py` | APScheduler daily dispatch job |
| `templates/` | Jinja2 HTML templates |

## Key Routes

| Route | Description |
|---|---|
| `GET /` | Landing page |
| `GET/POST /register` | User registration |
| `GET/POST /login` | Login |
| `GET/POST /preferences` | Select interest categories |
| `GET /dashboard` | Newsletter history |
| `POST /generate` | Manually generate and send newsletter now |
| `GET /preview` | View most recent newsletter in browser |
| `GET /newsletter/<id>` | View a specific newsletter |
| `GET /unsubscribe/<user_id>` | One-click unsubscribe |

## Interest Categories

Technology, Business & Finance, Science & Research, World News, AI & Machine Learning, Health & Wellness, Startups & Entrepreneurs, Climate & Environment, Sports, Arts & Culture, Politics, Space & Astronomy.
