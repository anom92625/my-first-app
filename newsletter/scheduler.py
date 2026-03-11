"""
Daily newsletter scheduler using APScheduler.

Two jobs run at the same configured time each day:

  1. _dispatch_category_newsletters  — original category-based digest
     (users who have selected interest categories)

  2. _dispatch_watchlist_newsletters — private-market watchlist edition
     (users who have companies on their watchlist)
     Generates the full two-step researched newsletter, attaches a PDF,
     and sends it.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


# ---------------------------------------------------------------------------
# Job 1: category-based newsletter (unchanged)
# ---------------------------------------------------------------------------

def _dispatch_category_newsletters(app):
    """Run inside app context: fetch articles, summarise, generate, send."""
    with app.app_context():
        from config import Config
        from models import db, User, Newsletter
        from newsletter.curator import fetch_articles_for_categories
        from newsletter.summarizer import summarize_articles, generate_newsletter_intro
        from newsletter.generator import build_html_newsletter, build_plain_text_newsletter
        from newsletter.mailer import send_newsletter

        cfg = Config()
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%A, %B %-d, %Y")

        users = User.query.filter_by(is_subscribed=True, is_active=True).all()
        logger.info("Dispatching category newsletters to %d subscribers", len(users))

        for user in users:
            try:
                slugs = [cat.slug for cat in user.interests]
                if not slugs:
                    continue

                articles = fetch_articles_for_categories(
                    slugs,
                    articles_per_category=4,
                    news_api_key=cfg.NEWS_API_KEY,
                )
                if not articles:
                    logger.warning("No articles found for user %s", user.id)
                    continue

                top   = articles[: cfg.MAX_TOP_STORIES]
                quick = articles[cfg.MAX_TOP_STORIES: cfg.MAX_TOP_STORIES + cfg.MAX_QUICK_HITS]

                summarize_articles(top, api_key=cfg.ANTHROPIC_API_KEY, max_articles=cfg.MAX_TOP_STORIES)

                cat_names = [cat.name for cat in user.interests]
                intro = generate_newsletter_intro(
                    user_name=user.name.split()[0],
                    categories=cat_names,
                    article_count=len(articles),
                    api_key=cfg.ANTHROPIC_API_KEY,
                    date_str=date_str,
                )

                unsubscribe_url = f"/unsubscribe/{user.id}"
                html  = build_html_newsletter(user.name.split()[0], intro, top, quick, date_str, unsubscribe_url)
                plain = build_plain_text_newsletter(user.name.split()[0], intro, top, quick, date_str)
                subject = f"Your Daily Brief — {date_str}"

                record = Newsletter(user_id=user.id, subject=subject, html_content=html)
                db.session.add(record)

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
                logger.error("Category newsletter failed for user %s: %s", user.id, exc)
                db.session.rollback()


# ---------------------------------------------------------------------------
# Job 2: watchlist newsletter with PDF attachment
# ---------------------------------------------------------------------------

def _dispatch_watchlist_newsletters(app):
    """
    For each active, subscribed user who has watchlist companies:
      1. Run the full two-step Claude research pipeline (baseline → update)
      2. Generate the editorial narrative
      3. Fetch market-wide deals + SEC EDGAR S-1 filings
      4. Build HTML + plain-text newsletter
      5. Render to PDF via WeasyPrint
      6. Send email with PDF attached
      7. Persist Newsletter record
    """
    with app.app_context():
        import json as _json
        from config import Config
        from models import db, User, Newsletter
        from newsletter.curator import (
            fetch_articles_for_companies,
            fetch_deals_news,
            fetch_sec_s1_filings,
        )
        from newsletter.summarizer import (
            research_company_update,
            research_deals,
            generate_newsletter_narrative,
        )
        from newsletter.generator import (
            build_watchlist_newsletter,
            build_plain_text_watchlist_newsletter,
        )
        from newsletter.mailer import send_newsletter
        from newsletter.pdf_generator import generate_pdf

        cfg = Config()
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%A, %B %-d, %Y")

        users = User.query.filter_by(is_subscribed=True, is_active=True).all()
        watchlist_users = [u for u in users if u.watchlist]
        logger.info(
            "Dispatching watchlist newsletters to %d users", len(watchlist_users)
        )

        for user in watchlist_users:
            try:
                company_names = [c.name for c in user.watchlist]

                # Deduplication: collect URLs from last 7 newsletters
                past = (
                    Newsletter.query.filter_by(user_id=user.id)
                    .order_by(Newsletter.sent_at.desc())
                    .limit(7)
                    .all()
                )
                seen_urls: set[str] = set()
                for nl in past:
                    seen_urls.update(nl.get_article_urls())

                previous_companies: list[str] = []
                if past:
                    try:
                        previous_companies = _json.loads(past[0].companies_json or "[]")
                    except Exception:
                        pass

                vol_number = Newsletter.query.filter_by(user_id=user.id).count() + 1

                # Step 1 + 2: fetch articles then research each company
                articles_by_company = fetch_articles_for_companies(
                    company_names,
                    max_per_company=8,
                    news_api_key=cfg.NEWS_API_KEY,
                )
                rows: list[dict] = []
                all_used_urls: list[str] = []
                for name in company_names:
                    row = research_company_update(
                        company=name,
                        articles=articles_by_company.get(name, []),
                        seen_urls=seen_urls,
                        api_key=cfg.ANTHROPIC_API_KEY,
                    )
                    if row:
                        rows.append(row)
                        if row.get("url"):
                            all_used_urls.append(row["url"])

                # Editorial narrative
                meta = generate_newsletter_narrative(
                    rows=rows,
                    previous_companies=previous_companies,
                    date_str=date_str,
                    vol_number=vol_number,
                    api_key=cfg.ANTHROPIC_API_KEY,
                )

                # Market-wide deals and SEC filings
                deal_articles = fetch_deals_news(max_articles=20)
                deal_rows = research_deals(
                    articles=deal_articles,
                    seen_urls=seen_urls,
                    api_key=cfg.ANTHROPIC_API_KEY,
                )
                sec_filings = fetch_sec_s1_filings(max_filings=8)

                unsubscribe_url = f"/unsubscribe/{user.id}"
                html = build_watchlist_newsletter(
                    user_name=user.name.split()[0],
                    rows=rows,
                    meta=meta,
                    date_str=date_str,
                    vol_number=vol_number,
                    unsubscribe_url=unsubscribe_url,
                    deal_rows=deal_rows,
                    sec_filings=sec_filings,
                )
                plain = build_plain_text_watchlist_newsletter(
                    user_name=user.name.split()[0],
                    rows=rows,
                    date_str=date_str,
                    vol_number=vol_number,
                    deal_rows=deal_rows,
                )

                subject = f"Private Markets Insider — Vol. {vol_number:02d} — {date_str}"

                # Generate PDF
                pdf_bytes: bytes | None = None
                pdf_filename = f"private-markets-insider-vol{vol_number:02d}.pdf"
                try:
                    pdf_bytes = generate_pdf(html)
                    logger.info(
                        "PDF generated for user %s (%d bytes)", user.id, len(pdf_bytes)
                    )
                except Exception as pdf_exc:
                    logger.warning(
                        "PDF generation failed for user %s: %s — sending without PDF",
                        user.id, pdf_exc,
                    )

                # Persist newsletter record
                record = Newsletter(
                    user_id=user.id,
                    subject=subject,
                    html_content=html,
                )
                record.set_article_urls(all_used_urls)
                record.companies_json = _json.dumps([r["company"] for r in rows])
                db.session.add(record)

                # Send
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
                    pdf_bytes=pdf_bytes,
                    pdf_filename=pdf_filename,
                )
                record.was_emailed = ok
                user.last_newsletter_at = now
                db.session.commit()
                logger.info(
                    "Watchlist newsletter dispatched for user %s (emailed=%s)", user.id, ok
                )

            except Exception as exc:
                logger.error(
                    "Watchlist newsletter failed for user %s: %s", user.id, exc
                )
                db.session.rollback()


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def start_scheduler(app, send_hour: int = 7, send_minute: int = 0):
    """Start the background scheduler. Call once at app startup."""
    global _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        func=_dispatch_category_newsletters,
        trigger=CronTrigger(hour=send_hour, minute=send_minute, timezone="UTC"),
        args=[app],
        id="daily_category_newsletter",
        name="Daily category newsletter dispatch",
        replace_existing=True,
    )

    _scheduler.add_job(
        func=_dispatch_watchlist_newsletters,
        trigger=CronTrigger(hour=send_hour, minute=send_minute, timezone="UTC"),
        args=[app],
        id="daily_watchlist_newsletter",
        name="Daily watchlist newsletter dispatch (with PDF)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Newsletter scheduler started — both jobs fire at %02d:%02d UTC",
        send_hour, send_minute,
    )


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
