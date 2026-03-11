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

# ---------------------------------------------------------------------------
# Known approximate valuations for top private companies.
# Used to seed the prompt so Claude always has a concrete figure to work with
# rather than writing "Not publicly disclosed".  Values are last-reported
# estimates and will be superseded if a more recent figure appears in articles.
# ---------------------------------------------------------------------------
_KNOWN_VALUATIONS: dict[str, str] = {
    # AI / ML
    "OpenAI":            "$157B",
    "Anthropic":         "$61B",
    "xAI":               "$50B",
    "Databricks":        "$62B",
    "Scale AI":          "$13.8B",
    "Cerebras":          "$23B",
    "Groq":              "$2.8B",
    "Hugging Face":      "$4.5B",
    "Perplexity AI":     "$9B",
    "Character.ai":      "$5B",
    "Cohere":            "$5B",
    "Mistral AI":        "$6B",
    "Together AI":       "$1.25B",
    "Stability AI":      "$1B",
    "Weights & Biases":  "$1.25B",
    "Harvey":            "$3B",
    "Glean":             "$4.6B",
    "Writer":            "$1.9B",
    "Adept AI":          "$1B",
    # Fintech
    "Stripe":            "$70B",
    "Revolut":           "$45B",
    "Klarna":            "$15B",
    "Chime":             "$25B",
    "Brex":              "$12B",
    "Ramp":              "$32B",
    "Plaid":             "$13B",
    "Checkout.com":      "$11B",
    "Ripple":            "$15B",
    "Kraken":            "$20B",
    "Upgrade":           "$6.3B",
    "Bolt":              "$11B",
    "Varo Bank":         "$2.5B",
    # Enterprise SaaS / Infrastructure
    "Rippling":          "$13.4B",
    "Deel":              "$12B",
    "Celonis":           "$13B",
    "Navan":             "$9.2B",
    "Carta":             "$8.5B",
    "Notion":            "$10B",
    "Retool":            "$3.2B",
    "Vercel":            "$3.25B",
    "dbt Labs":          "$4.2B",
    "Airbyte":           "$1.5B",
    "Fivetran":          "$5.6B",
    "Lattice":           "$3B",
    "Remote":            "$3B",
    # Cybersecurity
    "Wiz":               "$12B",
    "Snyk":              "$7.4B",
    "Lacework":          "$8.3B",
    "Abnormal Security": "$5.1B",
    "Arctic Wolf":       "$4.3B",
    "Coalition":         "$5B",
    "At-Bay":            "$1.35B",
    "Orca Security":     "$1.8B",
    # Space / Defense
    "SpaceX":            "$350B",
    "Anduril Industries":"$28B",
    "Applied Intuition": "$12B",
    "Relativity Space":  "$4.2B",
    "Vast Space":        "$1.8B",
    # Autonomous / Mobility
    "Waymo":             "$45B",
    "Aurora":            "$3B",
    "Nuro":              "$8.6B",
    # Consumer / Social
    "Discord":           "$15B",
    "Canva":             "$26B",
    "Epic Games":        "$32B",
    "ByteDance":         "$300B",
    "Shein":             "$66B",
    "Flexport":          "$3.2B",
    "Faire":             "$7B",
    # Crypto / Web3
    "Gemini":            "$7.1B",
    "Fireblocks":        "$8B",
    "Chainalysis":       "$8.6B",
    "MoonPay":           "$3.4B",
    # Other
    "CoreWeave":         "$19B",
    "Lambda Labs":       "$1.5B",
    "CloudKitchens":     "$15B",
    "Midjourney":        "not publicly disclosed (bootstrapped/profitable)",
    "Runway ML":         "$1.5B",
    "Joby Aviation":     "$4B",
    "Archer Aviation":   "$1.8B",
    "Shield AI":         "$2.8B",
}


_INVESTOR_SYSTEM_PROMPT = """You are a professional investor and expert investor relations professional \
helping private market investors stay on top of fast-moving private companies.

Core rules:
- For company DESCRIPTION and VALUATION: use your own training knowledge — do not try to extract \
these from article snippets. You know what these companies do and their last reported valuations.
- For the NEWS UPDATE: use only the provided articles — never invent facts.
- If the articles contain a valuation figure that is more recent than what you know, use the article's figure.
- Never use jargon — write in plain English.
- Be concise and direct. Write for a sophisticated investor who reads quickly."""

# Maps update_type → CSS pill class (used in generator)
UPDATE_TYPE_PILL = {
    "Funding Round":      ("Funding Round",   "p-funding"),
    "IPO Activity":       ("IPO Filing",       "p-ipo"),
    "Acquisition":        ("Acquisition",      "p-acq"),
    "Revenue Milestone":  ("Revenue",          "p-funding"),
    "Leadership Change":  ("Leadership",       "p-analysis"),
    "Product Launch":     ("Product Launch",   "p-analysis"),
    "Partnership":        ("Partnership",      "p-analysis"),
    "Valuation Update":   ("Valuation Update", "p-funding"),
    "Legal / Regulatory": ("Legal / Reg",      "p-analysis"),
    "Other":              ("Update",           "p-analysis"),
}

# Maps sector → (short label, CSS badge class)
SECTOR_BADGE = {
    "AI / ML":           ("AI / ML",    "b-ai"),
    "Fintech":           ("Fintech",    "b-fin"),
    "Crypto":            ("Crypto",     "b-crypto"),
    "Chips / Hardware":  ("AI Chips",   "b-chip"),
    "Social / Consumer": ("Consumer",   "b-social"),
    "Space Tech":        ("Space Tech", "b-ai"),
    "Health Tech":       ("Health",     "b-fin"),
    "Enterprise SaaS":   ("SaaS",       "b-fin"),
    "E-Commerce":        ("E-Commerce", "b-social"),
    "Macro":             ("Macro",      "b-macro"),
    "Other":             ("Tech",       "b-macro"),
}

_VALID_SECTORS   = list(SECTOR_BADGE.keys())
_VALID_UPD_TYPES = list(UPDATE_TYPE_PILL.keys())


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rstrip("`").strip()
    return json.loads(raw)


def research_company_update(
    company: str,
    articles: list[dict[str, Any]],
    seen_urls: set[str],
    api_key: str,
) -> dict[str, Any] | None:
    """
    Use Claude to research a company and produce a structured investor update.
    Description, valuation, and sector come from Claude's training knowledge.
    News update comes from the fetched articles.
    Returns a dict for the newsletter table row, or None if nothing new.
    """
    new_articles = [a for a in articles if a.get("url", "") not in seen_urls]
    if not new_articles:
        logger.info("No new articles for %s — skipping.", company)
        return None

    if not api_key:
        art = new_articles[0]
        return {
            "company": company,
            "sector": "Other",
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

        sectors    = ", ".join(f'"{s}"' for s in _VALID_SECTORS)
        upd_types  = ", ".join(f'"{t}"' for t in _VALID_UPD_TYPES)

        # Seed with known valuation so Claude doesn't default to "Not disclosed"
        known_val = _KNOWN_VALUATIONS.get(company, "")
        val_instruction = (
            f"Use '{known_val}' as the baseline valuation (update it only if an article "
            f"contains a more recent figure)."
            if known_val else
            "Use the most recently reported valuation from your training knowledge, "
            "or 'Not publicly disclosed' if genuinely unknown."
        )

        prompt = (
            f"Write an investor briefing row for the private company: {company}\n\n"
            f"PART 1 — Use YOUR TRAINING KNOWLEDGE for these fields (not the articles):\n"
            f"• sector:      Industry sector. One of [{sectors}]\n"
            f"• description: What does {company} do? One plain-English sentence.\n"
            f"• valuation:   {val_instruction}\n\n"
            f"PART 2 — From the ARTICLES BELOW, pick the single most investor-relevant update.\n"
            f"• If an article mentions a newer valuation, use it instead of the baseline above.\n"
            f"• In the summary field, bold key numbers and names using <strong> tags.\n"
            f"{articles_text}\n"
            f"Return ONLY valid JSON (no markdown fences):\n"
            "{{\n"
            f'  "company": "{company}",\n'
            f'  "sector": one of [{sectors}],\n'
            '  "description": "one plain-English sentence",\n'
            '  "valuation": "$XX.XB",\n'
            f'  "update_type": one of [{upd_types}],\n'
            '  "update": "one sentence — the key investor-relevant news headline",\n'
            '  "article_date": "date of the article (e.g. Mar 10, 2026)",\n'
            '  "summary": "3-4 sentences with <strong> around key figures. What happened and why it matters.",\n'
            '  "url": "URL of the primary article",\n'
            '  "source": "publication name"\n'
            "}}\n\n"
            f"If none of the articles contain useful investor news about {company}, "
            'return exactly: {{"skip": true}}'
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            system=_INVESTOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        data = _parse_json_response(msg.content[0].text)

        if data.get("skip"):
            logger.info("Claude found no investor-relevant news for %s.", company)
            return None

        if data.get("sector") not in SECTOR_BADGE:
            data["sector"] = "Other"
        if data.get("update_type") not in UPDATE_TYPE_PILL:
            data["update_type"] = "Other"

        return data

    except Exception as exc:
        logger.warning("Company research failed for '%s': %s", company, exc)
        art = new_articles[0]
        return {
            "company": company,
            "sector": "Other",
            "description": "",
            "valuation": "Not publicly disclosed",
            "update_type": "Other",
            "update": art.get("title", ""),
            "article_date": (art.get("published") or "")[:10],
            "summary": art.get("summary", ""),
            "url": art.get("url", "#"),
            "source": art.get("source", ""),
        }


# ---------------------------------------------------------------------------
# Newsletter-level narrative generation
# ---------------------------------------------------------------------------

_EDITOR_SYSTEM_PROMPT = """You are the editor of "Private Markets Insider", a premium newsletter \
for professional investors in private markets. Your writing is punchy, precise, and editorial — \
like The Information meets The Economist. No fluff. No jargon. Use plain English."""


def generate_newsletter_narrative(
    rows: list[dict[str, Any]],
    previous_companies: list[str],
    date_str: str,
    vol_number: int,
    api_key: str,
) -> dict[str, Any]:
    """
    Generate the editorial layer that wraps the per-company rows:
    - Headline (with <em> emphasis)
    - Deck paragraph
    - Key stats (3-4 data points from the stories)
    - "Only new" banner text
    - Analyst takes (1-2 cross-cutting editorial pieces)
    Returns a dict with all fields, falling back gracefully on error.
    """
    fallback = _default_narrative(rows, previous_companies, date_str, vol_number)

    if not api_key or not rows:
        return fallback

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        rows_summary = "\n".join(
            f"- {r['company']} ({r.get('update_type','?')}): {r.get('update','')} "
            f"| Valuation: {r.get('valuation','?')} | Date: {r.get('article_date','?')}"
            for r in rows
        )
        prev_str = (
            "Previous edition covered: " + ", ".join(previous_companies)
            if previous_companies
            else "This is the first edition."
        )

        prompt = (
            f"Today is {date_str}. This is Vol. {vol_number} of Private Markets Insider.\n"
            f"{prev_str}\n\n"
            f"TODAY'S {len(rows)} STORIES:\n{rows_summary}\n\n"
            "Write the newsletter editorial narrative. Return ONLY valid JSON (no markdown fences):\n"
            "{{\n"
            '  "headline_html": "12-18 word punchy headline about the most important theme(s) today. '
            'Wrap 2-4 key words in <em> tags for italic emphasis. Example: '
            '\\"The IPO Queue Is <em>Building Fast</em> — Cerebras Files, Discord Prepares\\"",\n'
            '  "deck": "2-3 sentence lead paragraph. State what edition covers vs previous. '
            'Name the most important 2-3 stories. No fluff.",\n'
            '  "key_stats": [\n'
            '    {{"value": "X", "label": "brief label"}}\n'
            '  ],\n'
            '  // 3-4 stats pulled from today\'s stories (story count, notable valuations, deal sizes)\n'
            '  "only_new_text": "1-2 sentences: name what the previous edition covered, '
            'then state none of those stories repeat here.",\n'
            '  "analyst_takes": [\n'
            '    {{"tag": "short thematic label", "title": "8-12 word analytical headline", '
            '"body": "3-4 sentence analysis of a cross-cutting pattern from today\'s stories"}}\n'
            '  ]\n'
            '  // 1-2 analyst takes that connect dots across multiple stories\n'
            "}}"
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1200,
            system=_EDITOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        data = _parse_json_response(msg.content[0].text)

        # Validate and fill defaults
        if not data.get("headline_html"):
            data["headline_html"] = fallback["headline_html"]
        if not data.get("deck"):
            data["deck"] = fallback["deck"]
        if not isinstance(data.get("key_stats"), list) or not data["key_stats"]:
            data["key_stats"] = fallback["key_stats"]
        if not data.get("only_new_text"):
            data["only_new_text"] = fallback["only_new_text"]
        if not isinstance(data.get("analyst_takes"), list):
            data["analyst_takes"] = []

        return data

    except Exception as exc:
        logger.warning("Narrative generation failed: %s", exc)
        return fallback


def _default_narrative(
    rows: list[dict],
    previous_companies: list[str],
    date_str: str,
    vol_number: int,
) -> dict[str, Any]:
    n = len(rows)
    stats: list[dict] = [{"value": str(n), "label": "New Stories Today"}]

    # Pull one notable valuation
    for r in rows:
        v = r.get("valuation", "")
        if v and v not in ("Not publicly disclosed", "Not disclosed", "N/A", ""):
            stats.append({"value": v, "label": f"{r['company']} Valuation"})
            break

    # Count IPO-related rows
    ipo_count = sum(1 for r in rows if r.get("update_type") == "IPO Activity")
    if ipo_count:
        stats.append({"value": str(ipo_count), "label": "IPO-Track Updates"})

    if previous_companies:
        prev_str = (
            f"Our previous edition covered {', '.join(previous_companies[:4])}. "
            "None of those stories appear here."
        )
    else:
        prev_str = "This is a fresh edition covering all-new stories."

    companies_str = " — ".join(r["company"] for r in rows[:3])
    return {
        "headline_html": f"Private Market Intelligence — <em>{companies_str}</em> and More",
        "deck": (
            f"Today's brief covers {n} new update{'s' if n != 1 else ''} across your watchlist. "
            "All stories are new and have not appeared in previous editions."
        ),
        "key_stats": stats,
        "only_new_text": prev_str,
        "analyst_takes": [],
    }


# ---------------------------------------------------------------------------
# Deals & Fundraising section
# ---------------------------------------------------------------------------

DEAL_TYPES = [
    "Fundraise",
    "IPO Filing",
    "IPO Priced",
    "Acquisition",
    "Exit",
    "Secondary Sale",
    "SPAC",
    "Debt Financing",
]

_DEALS_SYSTEM_PROMPT = """You are a senior analyst at a top-tier private equity firm. \
Your job is to extract clean, structured data from raw article titles and snippets about \
IPOs, fundraising rounds, acquisitions, and other capital-markets events. \
Be precise with numbers. Never invent investors or amounts not stated in the source text. \
Write 'Not disclosed' for any field not mentioned in the articles."""


def research_deals(
    articles: list[dict[str, Any]],
    seen_urls: set[str],
    api_key: str,
) -> list[dict[str, Any]]:
    """
    Given a list of deal-relevant articles, use Claude to extract up to 8
    structured deal records covering: deal type, company, round, amount raised,
    valuation, lead investors, and pricing details (for IPOs).

    Returns a list of deal dicts (may be empty).  Falls back to simple
    title-based stub records if the API key is absent or the call fails.
    """
    new_articles = [a for a in articles if a.get("url", "") not in seen_urls]
    if not new_articles:
        return []

    deal_types_str = ", ".join(f'"{t}"' for t in DEAL_TYPES)
    sectors_str    = ", ".join(f'"{s}"' for s in _VALID_SECTORS)

    # Stub fallback (no API key)
    if not api_key:
        stubs = []
        for art in new_articles[:6]:
            stubs.append({
                "company":        "",
                "deal_type":      "Fundraise",
                "sector":         "Other",
                "round":          "",
                "amount":         "Not disclosed",
                "valuation":      "Not disclosed",
                "lead_investors": [],
                "pricing_notes":  "",
                "summary":        art.get("title", ""),
                "article_date":   (art.get("published") or "")[:10],
                "url":            art.get("url", "#"),
                "source":         art.get("source", ""),
            })
        return stubs

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        articles_text = ""
        for i, art in enumerate(new_articles[:15], 1):
            articles_text += (
                f"\nArticle {i}:\n"
                f"  Title:   {art.get('title', '')}\n"
                f"  Date:    {art.get('published', 'unknown')}\n"
                f"  Source:  {art.get('source', '')}\n"
                f"  URL:     {art.get('url', '')}\n"
                f"  Snippet: {art.get('summary', '')[:400]}\n"
            )

        prompt = (
            f"Below are {len(new_articles[:15])} news articles. "
            "Identify every genuine capital-markets event (IPO filing, fundraising round, "
            "acquisition, exit, secondary sale, debt financing) described in them.\n\n"
            f"{articles_text}\n"
            "For each real deal you find, extract the following fields. "
            "ONLY include articles that describe an actual deal — skip general opinion pieces, "
            "market commentary, or articles where no specific company/amount is mentioned.\n\n"
            "Return ONLY valid JSON — a top-level array (no markdown fences):\n"
            "[\n"
            "  {{\n"
            f'    "company": "Company name",\n'
            f'    "deal_type": one of [{deal_types_str}],\n'
            f'    "sector": one of [{sectors_str}],\n'
            '    "round": "Round label e.g. Series C, Pre-IPO, Growth Round, or empty string",\n'
            '    "amount": "Amount raised e.g. $500M, or \\"Not disclosed\\"",\n'
            '    "valuation": "Post-money valuation if stated e.g. $4.5B, or \\"Not disclosed\\"",\n'
            '    "lead_investors": ["Investor 1", "Investor 2"],\n'
            '    "pricing_notes": "IPO price range or other pricing detail, or empty string",\n'
            '    "summary": "2-3 sentences: what happened, why it matters, key numbers. '
            'Bold figures with <strong> tags.",\n'
            '    "article_date": "e.g. Mar 10, 2026",\n'
            '    "url": "article URL",\n'
            '    "source": "publication name"\n'
            "  }}\n"
            "]\n\n"
            "Return an empty array [] if no genuine deal articles are found."
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            system=_DEALS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = msg.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rstrip("`").strip()

        deals = json.loads(raw)
        if not isinstance(deals, list):
            return []

        # Normalise fields and cap at 8 deals
        cleaned = []
        for d in deals[:8]:
            if not isinstance(d, dict) or not d.get("company"):
                continue
            if d.get("deal_type") not in DEAL_TYPES:
                d["deal_type"] = "Fundraise"
            if d.get("sector") not in SECTOR_BADGE:
                d["sector"] = "Other"
            if not isinstance(d.get("lead_investors"), list):
                d["lead_investors"] = []
            cleaned.append(d)

        return cleaned

    except Exception as exc:
        logger.warning("research_deals failed: %s", exc)
        return []
