from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Association table: user <-> interest categories
user_interests = db.Table(
    "user_interests",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("categories.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_subscribed = db.Column(db.Boolean, default=True)
    newsletter_frequency = db.Column(db.String(16), default="daily")  # daily, weekly
    preferred_send_time = db.Column(db.String(8), default="07:00")    # HH:MM UTC
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_newsletter_at = db.Column(db.DateTime, nullable=True)

    interests = db.relationship("Category", secondary=user_interests, back_populates="subscribers")
    newsletters = db.relationship("Newsletter", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    description = db.Column(db.String(256))
    icon = db.Column(db.String(8), default="📰")

    subscribers = db.relationship("User", secondary=user_interests, back_populates="interests")

    def __repr__(self):
        return f"<Category {self.name}>"


class Newsletter(db.Model):
    __tablename__ = "newsletters"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    subject = db.Column(db.String(256))
    html_content = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    was_emailed = db.Column(db.Boolean, default=False)

    user = db.relationship("User", back_populates="newsletters")

    def __repr__(self):
        return f"<Newsletter user={self.user_id} sent={self.sent_at}>"


# Default interest categories
DEFAULT_CATEGORIES = [
    {"slug": "technology",    "name": "Technology",              "icon": "💻", "description": "Software, gadgets, and digital innovation"},
    {"slug": "business",      "name": "Business & Finance",      "icon": "📈", "description": "Markets, economics, and corporate news"},
    {"slug": "science",       "name": "Science & Research",      "icon": "🔬", "description": "Discoveries, studies, and breakthroughs"},
    {"slug": "world-news",    "name": "World News",              "icon": "🌍", "description": "International headlines and geopolitics"},
    {"slug": "ai-ml",         "name": "AI & Machine Learning",   "icon": "🤖", "description": "Artificial intelligence and data science"},
    {"slug": "health",        "name": "Health & Wellness",       "icon": "🏃", "description": "Medicine, fitness, and mental health"},
    {"slug": "startups",      "name": "Startups & Entrepreneurs","icon": "🚀", "description": "Venture capital, founders, and new ventures"},
    {"slug": "environment",   "name": "Climate & Environment",   "icon": "🌿", "description": "Climate change, sustainability, and nature"},
    {"slug": "sports",        "name": "Sports",                  "icon": "⚽", "description": "Scores, transfers, and athletic stories"},
    {"slug": "culture",       "name": "Arts & Culture",          "icon": "🎨", "description": "Film, music, books, and creative work"},
    {"slug": "politics",      "name": "Politics",                "icon": "🏛️", "description": "Government, policy, and elections"},
    {"slug": "space",         "name": "Space & Astronomy",       "icon": "🚀", "description": "NASA, SpaceX, and cosmic discoveries"},
]


def seed_categories():
    """Populate category table if empty."""
    if Category.query.count() == 0:
        for cat in DEFAULT_CATEGORIES:
            db.session.add(Category(**cat))
        db.session.commit()
