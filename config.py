import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///newsletter.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email settings
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "My Daily Brief")

    # AI summarization
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Optional NewsAPI
    NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

    # Newsletter send schedule (UTC)
    NEWSLETTER_SEND_HOUR = int(os.getenv("NEWSLETTER_SEND_HOUR", "7"))
    NEWSLETTER_SEND_MINUTE = int(os.getenv("NEWSLETTER_SEND_MINUTE", "0"))

    # Article limits
    MAX_TOP_STORIES = 5
    MAX_QUICK_HITS = 8
