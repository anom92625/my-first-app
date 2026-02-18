"""
Daily newsletter scheduler using APScheduler.

Queues a send job that iterates over all active, subscribed users and dispatches
their personalised newsletter.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _dispatch_newsletters(app):
    """Run inside app context: fetch articles, summarise, generate, send."""
    with app.app_context():
        from config import Config
        from models import db, User
        from newsletter.curator import fetch_articles_for_categories
        from newsletter.summarizer import summarize_articles, generate_newsletter_intro
        from newsletter.generator import build_html_newsletter, build_plain_text_newsletter
        from newsletter.mailer import send_newsletter

        cfg = Config()
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%A, %B %-d, %Y")

        users = User.query.filter_by(is_subscribed=True, is_active=True).all()
        logger.info("Dispatching newsletters to %d subscribers", len(users))

        for user in users:
            try:
                slugs = [cat.slug for cat in user.interests]
                if not slugs:
                    continue

                # 1. Curate articles
                articles = fetch_articles_for_categories(
                    slugs,
                    articles_per_category=4,
                    news_api_key=cfg.NEWS_API_KEY,
                )
                if not articles:
                    logger.warning("No articles found for user %s", user.id)
                    continue

                # 2. AI summarise (top stories only)
                top = articles[: cfg.MAX_TOP_STORIES]
                quick = articles[cfg.MAX_TOP_STORIES: cfg.MAX_TOP_STORIES + cfg.MAX_QUICK_HITS]

                summarize_articles(top, api_key=cfg.ANTHROPIC_API_KEY, max_articles=cfg.MAX_TOP_STORIES)

                # 3. Personalised intro
                cat_names = [cat.name for cat in user.interests]
                intro = generate_newsletter_intro(
                    user_name=user.name.split()[0],
                    categories=cat_names,
                    article_count=len(articles),
                    api_key=cfg.ANTHROPIC_API_KEY,
                    date_str=date_str,
                )

                # 4. Render
                unsubscribe_url = f"/unsubscribe/{user.id}"
                html = build_html_newsletter(user.name.split()[0], intro, top, quick, date_str, unsubscribe_url)
                plain = build_plain_text_newsletter(user.name.split()[0], intro, top, quick, date_str)

                subject = f"Your Daily Brief — {date_str}"

                # 5. Persist newsletter record
                from models import Newsletter
                record = Newsletter(
                    user_id=user.id,
                    subject=subject,
                    html_content=html,
                )
                db.session.add(record)

                # 6. Send
                ok = send_newsletter(
                    to_email=user.email,
                    to_name=user.name,
                    subject=subject,
                    html_body=html,
                    plain_body=plain,
                    smtp_host=cfg.SMTP_HOST,
                    smtp_port=cfg.SMTP_PORT,
                    smtp_username=cfg.SMTP_USERNAME,
                    smtp_password=cfg.SMTP_PASSWORD,
                    from_email=cfg.EMAIL_FROM,
                    from_name=cfg.EMAIL_FROM_NAME,
                )
                record.was_emailed = ok
                user.last_newsletter_at = now
                db.session.commit()

            except Exception as exc:
                logger.error("Failed to send newsletter for user %s: %s", user.id, exc)
                db.session.rollback()


def start_scheduler(app, send_hour: int = 7, send_minute: int = 0):
    """Start the background scheduler. Call once at app startup."""
    global _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        func=_dispatch_newsletters,
        trigger=CronTrigger(hour=send_hour, minute=send_minute, timezone="UTC"),
        args=[app],
        id="daily_newsletter",
        name="Daily newsletter dispatch",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Newsletter scheduler started (sends at %02d:%02d UTC)", send_hour, send_minute)


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
