"""
My Daily Brief — Personalized Newsletter App
"""
import logging
import os
from datetime import datetime, timezone
from functools import wraps

from flask import (
    Flask,
    flash,
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
from models import Category, Newsletter, User, db, seed_categories
from newsletter.curator import fetch_articles_for_categories
from newsletter.generator import build_html_newsletter, build_plain_text_newsletter
from newsletter.mailer import send_newsletter
from newsletter.scheduler import start_scheduler, stop_scheduler
from newsletter.summarizer import generate_newsletter_intro, summarize_articles

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
        flash("Welcome! Choose your interests to get started.", "success")
        return redirect(url_for("preferences"))

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
# Routes — authenticated
# ---------------------------------------------------------------------------


@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    all_categories = Category.query.order_by(Category.name).all()

    if request.method == "POST":
        selected_ids = request.form.getlist("categories")
        if not selected_ids:
            flash("Please select at least one interest category.", "warning")
            return render_template("preferences.html", categories=all_categories, user_interests=set())

        selected = Category.query.filter(Category.id.in_(selected_ids)).all()
        current_user.interests = selected
        db.session.commit()
        flash("Preferences saved!", "success")
        return redirect(url_for("dashboard"))

    user_interest_ids = {cat.id for cat in current_user.interests}
    return render_template("preferences.html", categories=all_categories, user_interests=user_interest_ids)


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
    """Manually trigger newsletter generation for the current user."""
    slugs = [cat.slug for cat in current_user.interests]
    if not slugs:
        flash("You haven't selected any interests yet.", "warning")
        return redirect(url_for("preferences"))

    cfg = Config()
    now = datetime.now(tz=timezone.utc)
    date_str = now.strftime("%A, %B %-d, %Y")

    try:
        articles = fetch_articles_for_categories(
            slugs,
            articles_per_category=4,
            news_api_key=cfg.NEWS_API_KEY,
        )

        if not articles:
            flash("Could not fetch articles right now. Please try again later.", "warning")
            return redirect(url_for("dashboard"))

        top = articles[: cfg.MAX_TOP_STORIES]
        quick = articles[cfg.MAX_TOP_STORIES: cfg.MAX_TOP_STORIES + cfg.MAX_QUICK_HITS]

        summarize_articles(top, api_key=cfg.ANTHROPIC_API_KEY, max_articles=cfg.MAX_TOP_STORIES)

        cat_names = [cat.name for cat in current_user.interests]
        intro = generate_newsletter_intro(
            user_name=current_user.name.split()[0],
            categories=cat_names,
            article_count=len(articles),
            api_key=cfg.ANTHROPIC_API_KEY,
            date_str=date_str,
        )

        unsubscribe_url = url_for("unsubscribe", user_id=current_user.id, _external=True)
        html = build_html_newsletter(
            current_user.name.split()[0], intro, top, quick, date_str, unsubscribe_url
        )
        plain = build_plain_text_newsletter(
            current_user.name.split()[0], intro, top, quick, date_str
        )

        subject = f"Your Daily Brief — {date_str}"
        record = Newsletter(
            user_id=current_user.id,
            subject=subject,
            html_content=html,
        )
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
