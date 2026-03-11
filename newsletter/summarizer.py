"""
Article summarization and company research using the Anthropic Claude API.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Original article summarizer (used by category-based newsletter)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a newsletter editor for a high-quality personalized news digest,
similar to Morning Brew or Axios. Your job is to summarize articles in a concise,
engaging way for a general but informed audience.

For each article you must produce:
1. A one-sentence "hook" explaining why this matters to the reader.
2. A 2-3 sentence summary of what happened / what the article covers.
3. A one-sentence "key takeaway" — the single most important insight.

Keep language clear, active, and jargon-free. Do not editorialize beyond the article's content.
Do not use bullet points in your output — write short prose paragraphs."""

ARTICLE_PROMPT_TEMPLATE = """Please summarize the following article.

Title: {title}
Source: {source}
URL: {url}

Article snippet:
{snippet}

---
Return ONLY a JSON object with these exact keys:
{{
  "hook": "...",
  "summary": "...",
  "takeaway": "..."
}}"""


def _build_snippet(article: dict[str, Any]) -> str:
    """Use existing summary/description if available; otherwise just the title."""
    snippet = article.get("summary", "") or article.get("description", "") or ""
    return snippet[:1500] if snippet else article.get("title", "")


def summarize_articles(
    articles: list[dict[str, Any]],
    api_key: str,
    max_articles: int | None = None,
) -> list[dict[str, Any]]:
    """
    Enrich each article dict with AI-generated 'hook', 'summary', and 'takeaway' fields.
    Articles that fail (no API key, API error) keep their original summary.
    """
    if not api_key:
        logger.warning("No ANTHROPIC_API_KEY set — skipping AI summarization.")
        for art in articles:
            art.setdefault("hook", "")
            art.setdefault("takeaway", "")
        return articles

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.error("anthropic package not installed.")
        return articles

    target = articles[:max_articles] if max_articles else articles

    for art in target:
        try:
            prompt = ARTICLE_PROMPT_TEMPLATE.format(
                title=art.get("title", ""),
                source=art.get("source", ""),
                url=art.get("url", ""),
                snippet=_build_snippet(art),
            )

            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)

            art["hook"] = data.get("hook", "")
            art["summary"] = data.get("summary", art.get("summary", ""))
            art["takeaway"] = data.get("takeaway", "")

        except Exception as exc:
            logger.warning("Summarization failed for '%s': %s", art.get("title"), exc)
            art.setdefault("hook", "")
            art.setdefault("takeaway", "")

    return articles


def generate_newsletter_intro(
    user_name: str,
    categories: list[str],
    article_count: int,
    api_key: str,
    date_str: str,
) -> str:
    """Generate a short, personalized intro paragraph for the newsletter."""
    if not api_key:
        return (
            f"Good morning, {user_name}! Here's your personalized digest for {date_str}, "
            f"featuring {article_count} stories across your selected topics."
        )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = (
            f"Write a warm, 2-sentence personalized introduction for a daily newsletter.\n"
            f"Reader's name: {user_name}\n"
            f"Date: {date_str}\n"
            f"Topics covered: {', '.join(categories)}\n"
            f"Number of stories: {article_count}\n\n"
            f"Be friendly, energetic, and mention 1-2 of their interest areas naturally. "
            f"Do NOT use emojis. Output the two sentences only."
        )

        msg = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception as exc:
        logger.warning("Intro generation failed: %s", exc)
        return (
            f"Good morning, {user_name}! Here's your personalized digest for {date_str}, "
            f"featuring {article_count} stories across your selected topics."
        )


# ---------------------------------------------------------------------------
# Investor watchlist research (company-focused newsletter)
# ---------------------------------------------------------------------------

_INVESTOR_SYSTEM_PROMPT = """You are a professional investor and expert investor relations professional \
helping private market investors stay on top of fast-moving private companies.

Core rules:
- For company DESCRIPTION and VALUATION: use your own training knowledge — do not try to extract \
these from article snippets. You know what these companies do and their last reported valuations.
- For the NEWS UPDATE: use only the provided articles — never invent facts.
- If the articles contain a valuation figure that is more recent than what you know, use the article's figure.
- Never use jargon — write in plain English.
- Be concise and direct. Write for a sophisticated investor who reads quickly."""

# Maps update_type values to display labels and hex colors used in the newsletter
UPDATE_TYPE_COLORS = {
    "Funding Round":       "#3b82f6",   # blue
    "IPO Activity":        "#f59e0b",   # amber
    "Acquisition":         "#8b5cf6",   # purple
    "Revenue Milestone":   "#10b981",   # emerald
    "Leadership Change":   "#6b7280",   # gray
    "Product Launch":      "#0ea5e9",   # sky
    "Partnership":         "#0d9488",   # teal
    "Valuation Update":    "#f97316",   # orange
    "Legal / Regulatory":  "#ef4444",   # red
    "Other":               "#6b7280",   # gray
}


def research_company_update(
    company: str,
    articles: list[dict[str, Any]],
    seen_urls: set[str],
    api_key: str,
) -> dict[str, Any] | None:
    """
    Use Claude to research a company and produce a structured investor update.
    Description and valuation come from Claude's training knowledge.
    News update comes from the fetched articles.
    Returns a dict for the newsletter card, or None if nothing new.
    """
    new_articles = [a for a in articles if a.get("url", "") not in seen_urls]
    if not new_articles:
        logger.info("No new articles for %s — skipping.", company)
        return None

    if not api_key:
        art = new_articles[0]
        return {
            "company": company,
            "description": "",
            "valuation": "Not disclosed",
            "update_type": "Other",
            "update": art.get("title", ""),
            "article_date": (art.get("published") or "")[:10],
            "summary": art.get("summary", ""),
            "url": art.get("url", "#"),
            "source": art.get("source", ""),
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        articles_text = ""
        for i, art in enumerate(new_articles[:5], 1):
            articles_text += (
                f"\nArticle {i}:\n"
                f"  Title:   {art.get('title', '')}\n"
                f"  Date:    {art.get('published', 'unknown')}\n"
                f"  Source:  {art.get('source', '')}\n"
                f"  URL:     {art.get('url', '')}\n"
                f"  Snippet: {art.get('summary', '')[:500]}\n"
            )

        update_types = ", ".join(f'"{t}"' for t in UPDATE_TYPE_COLORS)

        prompt = (
            f"You are writing an investor briefing entry for the private company: {company}\n\n"
            f"PART 1 — From YOUR KNOWLEDGE (do not use the articles for these fields):\n"
            f"• description: What does {company} do? One plain-English sentence.\n"
            f"• valuation: What is {company}'s most recently reported valuation "
            f"(e.g. '$65B as of 2024')? If truly unknown, write 'Not publicly disclosed'.\n\n"
            f"PART 2 — From the ARTICLES BELOW, find the single most investor-relevant recent update.\n"
            f"If an article mentions a newer valuation than your knowledge, use that for the valuation field.\n"
            f"{articles_text}\n"
            f"Return ONLY valid JSON (no markdown fences, no extra text):\n"
            "{\n"
            f'  "company": "{company}",\n'
            '  "description": "from your knowledge: one sentence on what the company does",\n'
            '  "valuation": "from your knowledge (updated if articles have newer figure): e.g. $65B",\n'
            f'  "update_type": one of [{update_types}],\n'
            '  "update": "one sentence — the key investor-relevant news from the articles",\n'
            '  "article_date": "date of the article used (e.g. Mar 10, 2026)",\n'
            '  "summary": "2-3 sentences: what happened and why it matters to a private market investor",\n'
            '  "url": "URL of the primary article",\n'
            '  "source": "publication name"\n'
            "}\n\n"
            f"If none of the articles contain useful investor news about {company}, "
            'return exactly: {"skip": true}'
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=_INVESTOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()

        data = json.loads(raw)

        if data.get("skip"):
            logger.info("Claude found no investor-relevant news for %s.", company)
            return None

        # Ensure update_type is a known value
        if data.get("update_type") not in UPDATE_TYPE_COLORS:
            data["update_type"] = "Other"

        return data

    except Exception as exc:
        logger.warning("Company research failed for '%s': %s", company, exc)
        art = new_articles[0]
        return {
            "company": company,
            "description": "",
            "valuation": "Not publicly disclosed",
            "update_type": "Other",
            "update": art.get("title", ""),
            "article_date": (art.get("published") or "")[:10],
            "summary": art.get("summary", ""),
            "url": art.get("url", "#"),
            "source": art.get("source", ""),
        }
