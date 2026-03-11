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

_INVESTOR_SYSTEM_PROMPT = """You are a professional investor and expert investor relations professional. \
Your role is to help private company investors stay on top of the ever-changing private industry and \
fast-moving companies.

Guidelines:
- Never make up any information — only use facts from the articles provided.
- Never repeat information that was already covered in previous newsletters (seen URLs listed below).
- Never use jargon — write in plain English that is easy to understand and digest.
- Cite the source article for every update.
- Focus on what matters most to a private market investor: funding rounds, valuation changes, \
revenue milestones, leadership changes, major product launches, acquisitions, or IPO activity.
- Be concise and direct."""


def research_company_update(
    company: str,
    articles: list[dict[str, Any]],
    seen_urls: set[str],
    api_key: str,
) -> dict[str, Any] | None:
    """
    Use Claude to research a company and produce a structured investor update row.
    Skips articles already seen in previous newsletters.
    Returns a dict for the newsletter table row, or None if nothing new.
    """
    new_articles = [a for a in articles if a.get("url", "") not in seen_urls]
    if not new_articles:
        logger.info("No new articles for %s — skipping.", company)
        return None

    if not api_key:
        # Fallback: use the most recent article without AI synthesis
        art = new_articles[0]
        return {
            "company": company,
            "description": "N/A",
            "valuation": "N/A",
            "update": art.get("title", ""),
            "article_date": (art.get("published") or "")[:10],
            "summary": art.get("summary", ""),
            "url": art.get("url", "#"),
            "source": art.get("source", ""),
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # Build article context (cap at 5 to keep prompt size reasonable)
        articles_text = ""
        for i, art in enumerate(new_articles[:5], 1):
            articles_text += (
                f"\nArticle {i}:\n"
                f"  Title:   {art.get('title', '')}\n"
                f"  Date:    {art.get('published', 'unknown')}\n"
                f"  Source:  {art.get('source', '')}\n"
                f"  URL:     {art.get('url', '')}\n"
                f"  Snippet: {art.get('summary', '')[:400]}\n"
            )

        prompt = (
            f"Research the latest investor-relevant news about the private company '{company}' "
            f"using the articles below. Select the single most important update for investors.\n"
            f"\n{articles_text}\n"
            "Return ONLY a valid JSON object (no markdown, no extra text):\n"
            "{\n"
            f'  "company": "{company}",\n'
            '  "description": "one plain-English sentence describing what the company does",\n'
            '  "valuation": "latest known valuation (e.g. $10B) or N/A if not mentioned",\n'
            '  "update": "one sentence describing the key investor-relevant news",\n'
            '  "article_date": "date of the article used (e.g. Mar 10, 2026)",\n'
            '  "summary": "2-3 sentence plain-English summary of why this news matters to investors",\n'
            '  "url": "URL of the primary article used",\n'
            '  "source": "name of the publication"\n'
            "}\n\n"
            f"If none of the articles contain investor-relevant news about {company}, "
            'return exactly: {"skip": true}'
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
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

        return data

    except Exception as exc:
        logger.warning("Company research failed for '%s': %s", company, exc)
        # Graceful fallback to raw article data
        art = new_articles[0]
        return {
            "company": company,
            "description": "N/A",
            "valuation": "N/A",
            "update": art.get("title", ""),
            "article_date": (art.get("published") or "")[:10],
            "summary": art.get("summary", ""),
            "url": art.get("url", "#"),
            "source": art.get("source", ""),
        }
