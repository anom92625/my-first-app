"""
My Daily Brief — Personalized Newsletter App
"""
import logging
import os
from datetime import datetime, timezone
from functools import wraps

# Top private companies shown as suggestions in the watchlist autocomplete.
# Sorted alphabetically; users can still type any name not on this list.
TOP_PRIVATE_COMPANIES: list[str] = sorted([
    # AI / ML
    "Anthropic", "OpenAI", "xAI", "Cohere", "Mistral AI", "Perplexity AI",
    "Character.ai", "Hugging Face", "Scale AI", "Together AI", "Groq",
    "Stability AI", "Midjourney", "Runway ML", "Weights & Biases",
    "Harvey", "Glean", "Writer", "Adept AI", "Inflection AI",
    # Enterprise SaaS / Infrastructure
    "Databricks", "Celonis", "Rippling", "Deel", "Lattice", "Carta",
    "Retool", "Notion", "Linear", "Vercel", "dbt Labs", "Airbyte",
    "Fivetran", "Monte Carlo Data", "Navan", "Remote",
    # Fintech
    "Stripe", "Chime", "Revolut", "Klarna", "Brex", "Ramp", "Plaid",
    "Checkout.com", "Upgrade", "Bolt", "Varo Bank", "Marqeta",
    "MoonPay", "Ripple", "Kraken",
    # Cybersecurity
    "Wiz", "Snyk", "Lacework", "Abnormal Security", "Arctic Wolf",
    "Coalition", "At-Bay", "Orca Security",
    # Space / Defense / Deep Tech
    "SpaceX", "Relativity Space", "Vast Space", "Astranis", "Anduril Industries",
    "Applied Intuition", "Shield AI", "Joby Aviation", "Archer Aviation",
    # Autonomous / Mobility
    "Waymo", "Aurora", "Nuro", "Cruise", "Zoox",
    # Consumer / Social
    "Discord", "Canva", "Epic Games", "ByteDance", "Shein",
    "Instacart", "Faire", "Flexport",
    # Health
    "Devoted Health", "Nomi Health", "Cityblock Health",
    # Crypto / Web3
    "Gemini", "Fireblocks", "Chainalysis",
    # Other notable
    "Cerebras", "CoreWeave", "Lambda Labs", "CloudKitchens",
])

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from config import Config
from models import Category, Newsletter, User, WatchlistCompany, db, seed_categories
from newsletter.curator import fetch_articles_for_categories, fetch_articles_for_companies, fetch_deals_news
from newsletter.generator import (
    build_html_newsletter,
    build_plain_text_newsletter,
    build_watchlist_newsletter,
    build_plain_text_watchlist_newsletter,
)
import json as _json
from newsletter.mailer import send_newsletter
from newsletter.scheduler import start_scheduler, stop_scheduler
from newsletter.summarizer import (
    generate_newsletter_intro,
    generate_newsletter_narrative,
    research_company_update,
    research_deals,
    summarize_articles,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    login_manager = LoginManager(app)
    login_manager.login_view = "login"
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()
        seed_categories()

    # Start daily scheduler (skip in testing / debug reloader child)
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        cfg = Config()
        start_scheduler(app, send_hour=cfg.NEWSLETTER_SEND_HOUR, send_minute=cfg.NEWSLETTER_SEND_MINUTE)

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Routes — public
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "danger")
            return render_template("register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "danger")
            return render_template("register.html")

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Welcome! Add companies to your watchlist to get started.", "success")
        return redirect(url_for("watchlist"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")

        login_user(user, remember=remember)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/unsubscribe/<int:user_id>")
def unsubscribe(user_id):
    user = User.query.get_or_404(user_id)
    user.is_subscribed = False
    db.session.commit()
    return render_template("unsubscribed.html", name=user.name)


# ---------------------------------------------------------------------------
# Routes — watchlist management
# ---------------------------------------------------------------------------


@app.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist():
    if request.method == "POST":
        name = request.form.get("company_name", "").strip()
        if not name:
            flash("Please enter a company name.", "warning")
        elif len(name) > 200:
            flash("Company name is too long.", "warning")
        else:
            # Check for duplicate (case-insensitive)
            exists = WatchlistCompany.query.filter_by(
                user_id=current_user.id
            ).filter(
                db.func.lower(WatchlistCompany.name) == name.lower()
            ).first()
            if exists:
                flash(f"{name} is already on your watchlist.", "info")
            else:
                company = WatchlistCompany(user_id=current_user.id, name=name)
                db.session.add(company)
                db.session.commit()
                flash(f"{name} added to your watchlist.", "success")
        return redirect(url_for("watchlist"))

    companies = current_user.watchlist
    return render_template(
        "watchlist.html",
        companies=companies,
        popular_companies=TOP_PRIVATE_COMPANIES,
    )


@app.route("/watchlist/remove/<int:company_id>", methods=["POST"])
@login_required
def watchlist_remove(company_id):
    company = WatchlistCompany.query.filter_by(
        id=company_id, user_id=current_user.id
    ).first_or_404()
    name = company.name
    db.session.delete(company)
    db.session.commit()
    flash(f"{name} removed from your watchlist.", "info")
    return redirect(url_for("watchlist"))


# ---------------------------------------------------------------------------
# Routes — preferences (kept for backward compat, redirects to watchlist)
# ---------------------------------------------------------------------------


@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    return redirect(url_for("watchlist"))


# ---------------------------------------------------------------------------
# Routes — authenticated
# ---------------------------------------------------------------------------


@app.route("/dashboard")
@login_required
def dashboard():
    recent_newsletters = (
        Newsletter.query.filter_by(user_id=current_user.id)
        .order_by(Newsletter.sent_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "dashboard.html",
        user=current_user,
        newsletters=recent_newsletters,
    )


@app.route("/newsletter/<int:newsletter_id>")
@login_required
def view_newsletter(newsletter_id):
    nl = Newsletter.query.filter_by(id=newsletter_id, user_id=current_user.id).first_or_404()
    return nl.html_content


@app.route("/generate", methods=["POST"])
@login_required
def generate_now():
    """Manually trigger watchlist newsletter generation for the current user."""
    companies = current_user.watchlist
    if not companies:
        flash("Your watchlist is empty. Add companies to track first.", "warning")
        return redirect(url_for("watchlist"))

    cfg = Config()
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%A, %B %-d, %Y")

    try:
        # Collect URLs + previous companies from last 7 newsletters (deduplication)
        past_newsletters = (
            Newsletter.query.filter_by(user_id=current_user.id)
            .order_by(Newsletter.sent_at.desc())
            .limit(7)
            .all()
        )
        seen_urls: set[str] = set()
        for nl in past_newsletters:
            seen_urls.update(nl.get_article_urls())

        # Previous-edition company list for the "only new" banner
        previous_companies: list[str] = []
        if past_newsletters:
            try:
                previous_companies = _json.loads(past_newsletters[0].companies_json or "[]")
            except Exception:
                pass

        # Volume number = total newsletters so far + 1
        vol_number = Newsletter.query.filter_by(user_id=current_user.id).count() + 1

        # Fetch news articles for each watchlisted company
        company_names = [c.name for c in companies]
        articles_by_company = fetch_articles_for_companies(
            company_names,
            max_per_company=8,
            news_api_key=cfg.NEWS_API_KEY,
        )

        # Research each company with Claude (description + valuation from training knowledge)
        rows = []
        all_used_urls: list[str] = []
        for company_name in company_names:
            articles = articles_by_company.get(company_name, [])
            row = research_company_update(
                company=company_name,
                articles=articles,
                seen_urls=seen_urls,
                api_key=cfg.ANTHROPIC_API_KEY,
            )
            if row:
                rows.append(row)
                if row.get("url"):
                    all_used_urls.append(row["url"])

        # Generate editorial narrative (headline, deck, stats, analyst takes)
        meta = generate_newsletter_narrative(
            rows=rows,
            previous_companies=previous_companies,
            date_str=date_str,
            vol_number=vol_number,
            api_key=cfg.ANTHROPIC_API_KEY,
        )

        # Fetch and structure market-wide deals (IPOs, exits, fundraising)
        deal_articles = fetch_deals_news(max_articles=20)
        deal_rows = research_deals(
            articles=deal_articles,
            seen_urls=seen_urls,
            api_key=cfg.ANTHROPIC_API_KEY,
        )

        unsubscribe_url = url_for("unsubscribe", user_id=current_user.id, _external=True)
        html = build_watchlist_newsletter(
            user_name=current_user.name.split()[0],
            rows=rows,
            meta=meta,
            date_str=date_str,
            vol_number=vol_number,
            unsubscribe_url=unsubscribe_url,
            deal_rows=deal_rows,
        )
        plain = build_plain_text_watchlist_newsletter(
            user_name=current_user.name.split()[0],
            rows=rows,
            date_str=date_str,
            vol_number=vol_number,
            deal_rows=deal_rows,
        )

        subject = f"Private Markets Insider — Vol. {vol_number:02d} — {date_str}"
        record = Newsletter(
            user_id=current_user.id,
            subject=subject,
            html_content=html,
        )
        record.set_article_urls(all_used_urls)
        record.companies_json = _json.dumps([r["company"] for r in rows])
        db.session.add(record)

        # Attempt to email it
        ok = send_newsletter(
            to_email=current_user.email,
            to_name=current_user.name,
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
        current_user.last_newsletter_at = now
        db.session.commit()

        if ok:
            flash("Newsletter generated and sent to your email!", "success")
        else:
            flash("Newsletter generated (email delivery requires SMTP configuration).", "info")

        return redirect(url_for("view_newsletter", newsletter_id=record.id))

    except Exception as exc:
        logger.error("Newsletter generation failed: %s", exc)
        flash("An error occurred while generating your newsletter.", "danger")
        return redirect(url_for("dashboard"))


@app.route("/preview")
@login_required
def preview():
    """Show the most recent newsletter in the browser."""
    latest = (
        Newsletter.query.filter_by(user_id=current_user.id)
        .order_by(Newsletter.sent_at.desc())
        .first()
    )
    if not latest:
        flash("No newsletter yet. Generate one from your dashboard!", "info")
        return redirect(url_for("dashboard"))
    return latest.html_content


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------


@app.template_filter("format_dt")
def format_dt(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime("%b %d, %Y at %-I:%M %p UTC")


if __name__ == "__main__":
    app.run(debug=True)
