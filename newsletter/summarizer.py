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


_BASELINE_SYSTEM_PROMPT = """You are a private market intelligence analyst. \
Your job is to provide a structured, clearly-labelled company profile from your training knowledge. \
\
Critical rules for financial figures: \
- All valuations, round sizes, and revenue figures from training knowledge MUST be labelled \
  "(training data — verify)" so the reader knows they require independent verification. \
- Never present a training-knowledge figure as if it were a confirmed live fact. \
- If the company is bootstrapped or pre-funding, say so explicitly. \
- Descriptions should be factual and written for a sophisticated investor."""


def _fetch_company_baseline(
    company: str,
    client: Any,
    known_val: str,
) -> dict[str, Any]:
    """
    Step 1 of the two-step research flow.

    Ask Claude to produce a structured baseline from training knowledge ONLY —
    no articles involved at this stage.  Because the prompt references no external
    sources, Claude draws on its internal knowledge and always returns concrete
    figures rather than defaulting to "Not publicly disclosed".

    Returns a dict with: company, sector, description, valuation, last_round,
    last_round_amount, key_investors, founded_year.
    """
    sectors = ", ".join(f'"{s}"' for s in _VALID_SECTORS)

    if known_val:
        val_instruction = (
            f"Your records show approximately {known_val} for this company. "
            f"Use it as a starting point and append '(training data — verify)' to the value."
        )
    else:
        val_instruction = (
            "Provide the most recent post-money valuation you know, with round and year, "
            "e.g. '$4.5B post-money (Series C, Jan 2024) (training data — verify)'. "
            "If bootstrapped or pre-funding, write 'Bootstrapped' or 'Pre-seed'. "
            "Always append '(training data — verify)' to any dollar figure."
        )

    prompt = (
        f"Provide a baseline investor profile for the private company: {company}\n\n"
        "Use ONLY your training knowledge. All financial figures must be labelled "
        "'(training data — verify)' so the reader knows they need independent verification.\n\n"
        f"Valuation instruction: {val_instruction}\n\n"
        "Return ONLY valid JSON (no markdown fences):\n"
        "{{\n"
        f'  "company": "{company}",\n'
        f'  "sector": one of [{sectors}],\n'
        '  "description": "One sentence: what does the company do and for whom.",\n'
        '  "valuation": "e.g. \'$4.5B post-money (Series C, Jan 2024) (training data — verify)\'",\n'
        '  "last_round": "Most recent funding round label e.g. \'Series D\', \'Pre-IPO\', '
        '\'Bootstrapped\', or \'Unknown\'",\n'
        '  "last_round_amount": "e.g. \'$150M (training data — verify)\', or \'Not disclosed\'",\n'
        '  "key_investors": ["Lead investor", "Investor 2", "Investor 3"],\n'
        '  "founded_year": "e.g. 2016 — or \'unknown\'"\n'
        "}}\n"
    )

    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=_BASELINE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json_response(msg.content[0].text)


_INVESTOR_SYSTEM_PROMPT = """You are a fact-checking financial journalist writing for a professional \
private-market investor audience.

Sourcing rules (non-negotiable):
1. Use ONLY facts explicitly stated in the provided article text — never supplement with training knowledge.
2. Use only Tier 1 primary sources: company press releases, SEC filings, Bloomberg, WSJ, FT, Reuters, \
   TechCrunch, The Information.  If the article source is an aggregator, state which primary source it cites.
3. Label every financial figure:
   - "confirmed-closed" if the round/acquisition has definitively closed (money transferred, filing made)
   - "announced" if reported/announced but not yet confirmed closed
   - "projected" if the figure comes from an analyst, model, or unnamed source
4. For valuations: always specify pre-money or post-money.  If the article does not specify, write \
   "valuation type not specified".
5. If two sources in the provided text cite different figures, report the range and name both sources.
6. Never aggregate or paraphrase financial figures — quote the specific sentence from the source.
7. If a fact cannot be verified from the provided article text, omit it entirely.
8. The company baseline (sector, description) is pre-filled — do not re-derive it from articles."""

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
    Two-step research flow for a single watchlist company.

    Step 1 — Baseline (Haiku, knowledge-only):
        Ask Claude what it knows about the company from training data: sector,
        description, valuation, last round, key investors.  No articles are
        provided at this stage so Claude cannot fall back on article silence
        to justify "Not publicly disclosed".

    Step 2 — Update (Sonnet, articles-only):
        Pass the baseline + fetched articles to Claude.  Claude checks whether
        any article represents new investor-relevant news and, if so, produces
        the update fields.  If the articles contain a newer valuation it
        overrides the baseline figure; otherwise the baseline stands.

    Returns a merged row dict ready for the newsletter, or None if there are
    no new articles and no baseline was produced.
    """
    new_articles = [a for a in articles if a.get("url", "") not in seen_urls]
    if not new_articles:
        logger.info("No new articles for %s — skipping.", company)
        return None

    # ------------------------------------------------------------------ #
    # No-API fallback                                                      #
    # ------------------------------------------------------------------ #
    if not api_key:
        art = new_articles[0]
        known_val = _KNOWN_VALUATIONS.get(company, "Not disclosed")
        return {
            "company":       company,
            "sector":        "Other",
            "description":   "",
            "valuation":     f"{known_val} (training data — verify)" if known_val != "Not disclosed" else known_val,
            "last_round":    "",
            "key_investors": [],
            "update_type":   "Other",
            "deal_status":   "announced",
            "update":        art.get("title", ""),
            "article_date":  (art.get("published") or "")[:10],
            "summary":       art.get("summary", ""),
            "citation":      "",
            "source_tier":   art.get("source_tier", 3),
            "url":           art.get("url", "#"),
            "source":        art.get("source", ""),
        }

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        # ------------------------------------------------------------------ #
        # STEP 1: Baseline — knowledge-only, no articles                      #
        # ------------------------------------------------------------------ #
        known_val = _KNOWN_VALUATIONS.get(company, "")
        try:
            baseline = _fetch_company_baseline(company, client, known_val)
        except Exception as exc:
            logger.warning("Baseline fetch failed for '%s': %s", company, exc)
            # Fall back to dict seeded from known valuations
            baseline = {
                "company":          company,
                "sector":           "Other",
                "description":      "",
                "valuation":        known_val or "Not disclosed",
                "last_round":       "Unknown",
                "last_round_amount":"Not disclosed",
                "key_investors":    [],
                "founded_year":     "unknown",
            }

        if baseline.get("sector") not in SECTOR_BADGE:
            baseline["sector"] = "Other"

        # ------------------------------------------------------------------ #
        # STEP 2: Update — articles anchored to baseline                      #
        # ------------------------------------------------------------------ #
        articles_text = ""
        for i, art in enumerate(new_articles[:5], 1):
            # Use full article text when available, fall back to RSS snippet
            body = art.get("full_text") or art.get("summary", "")
            tier = art.get("source_tier", 3)
            tier_label = {1: "Tier 1 (Primary)", 2: "Tier 2 (Quality secondary)", 3: "Tier 3 (Aggregator)"}.get(tier, "Tier 3")
            articles_text += (
                f"\n--- Article {i} ---\n"
                f"Title:       {art.get('title', '')}\n"
                f"Date:        {art.get('published', 'unknown')}\n"
                f"Source:      {art.get('source', '')}  [{tier_label}]\n"
                f"URL:         {art.get('url', '')}\n"
                f"Body text:\n{body[:3000]}\n"
            )

        upd_types = ", ".join(f'"{t}"' for t in _VALID_UPD_TYPES)
        baseline_summary = (
            f"Company: {baseline.get('company', company)}\n"
            f"Sector: {baseline.get('sector', 'Other')}\n"
            f"Description: {baseline.get('description', '')}\n"
            f"Baseline valuation (training data, needs verification): {baseline.get('valuation', 'Unknown')}\n"
            f"Last round: {baseline.get('last_round', 'Unknown')} "
            f"({baseline.get('last_round_amount', 'Not disclosed')})\n"
            f"Key investors: {', '.join(baseline.get('key_investors', []))}\n"
        )

        prompt = (
            f"Baseline for {company} (training data — for context only):\n"
            f"{baseline_summary}\n"
            "---\n"
            "FACT-CHECKING RULES:\n"
            "1. Only report financial figures explicitly stated in the article body text below.\n"
            "2. For each number, provide a citation: the exact sentence from the article.\n"
            "3. Label every financial figure with its deal_status:\n"
            "   - 'confirmed-closed': round definitively closed (press release, SEC filing, or company statement)\n"
            "   - 'announced': reported/announced but not yet confirmed closed\n"
            "   - 'projected': analyst estimate or unnamed source\n"
            "4. For valuations: specify pre-money or post-money. If not stated, write 'type not specified'.\n"
            "5. If two articles give different figures, report the range: e.g. '$4B–$4.5B (Source A vs Source B)'.\n"
            "6. If source is Tier 3 (aggregator), name the primary source the aggregator cites.\n"
            "7. If no verifiable investor-relevant news exists in the articles, return {\"skip\": true}.\n\n"
            f"{articles_text}\n"
            "Return ONLY valid JSON (no markdown fences):\n"
            "{{\n"
            f'  "update_type": one of [{upd_types}],\n'
            '  "deal_status": "confirmed-closed" | "announced" | "projected" | "not-applicable",\n'
            '  "update": "One sentence — the key investor-relevant news headline.",\n'
            '  "article_date": "Date of the article e.g. Mar 10, 2026",\n'
            '  "summary": "3-4 sentences. Only facts from the article text. '
            'Bold key figures with <strong>. State the source tier.",\n'
            '  "citation": "The exact sentence(s) from the article that support the key figure(s).",\n'
            '  "source_tier": 1 | 2 | 3,\n'
            '  "url": "URL of the primary article",\n'
            '  "source": "Publication name",\n'
            '  "valuation_override": '
            '"If articles state a NEW valuation: \'$5.2B post-money (Series D, Mar 2026) [announced]\' — else omit"\n'
            "}}\n\n"
            f"If none of the articles contain useful investor news about {company}, "
            'return exactly: {{"skip": true}}'
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=700,
            system=_INVESTOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        update = _parse_json_response(msg.content[0].text)

        if update.get("skip"):
            logger.info("No investor-relevant news for %s — skipping.", company)
            return None

        if update.get("update_type") not in UPDATE_TYPE_PILL:
            update["update_type"] = "Other"

        # ------------------------------------------------------------------ #
        # Merge: baseline fields + update fields                              #
        # ------------------------------------------------------------------ #
        final_valuation = update.pop("valuation_override", None) or baseline.get("valuation", "Not disclosed")

        return {
            # From baseline (training knowledge, labelled as such)
            "company":       baseline.get("company", company),
            "sector":        baseline.get("sector", "Other"),
            "description":   baseline.get("description", ""),
            "valuation":     final_valuation,
            "last_round":    baseline.get("last_round", ""),
            "key_investors": baseline.get("key_investors", []),
            # From update (article-derived, fact-checked)
            "update_type":   update.get("update_type", "Other"),
            "deal_status":   update.get("deal_status", "announced"),
            "update":        update.get("update", ""),
            "article_date":  update.get("article_date", ""),
            "summary":       update.get("summary", ""),
            "citation":      update.get("citation", ""),
            "source_tier":   update.get("source_tier", 3),
            "url":           update.get("url", "#"),
            "source":        update.get("source", ""),
        }

    except Exception as exc:
        logger.warning("Company research failed for '%s': %s", company, exc)
        art = new_articles[0]
        return {
            "company":       company,
            "sector":        "Other",
            "description":   "",
            "valuation":     _KNOWN_VALUATIONS.get(company, "Not disclosed"),
            "last_round":    "",
            "key_investors": [],
            "update_type":   "Other",
            "update":        art.get("title", ""),
            "article_date":  (art.get("published") or "")[:10],
            "summary":       art.get("summary", ""),
            "url":           art.get("url", "#"),
            "source":        art.get("source", ""),
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
    "Fundraise",       # Standard up-round equity raise
    "Down Round",      # Raise at a lower valuation than prior round — distress signal
    "Bridge Round",    # Short-term capital to extend runway — often precedes restructuring
    "Fund Close",      # VC/PE fund reaching a close — LP intelligence
    "IPO Filing",      # S-1 / F-1 registration statement filed
    "IPO Priced",      # IPO pricing set; shares to begin trading
    "Acquisition",     # Company acquired (disclosed buyer)
    "Exit",            # Founder/investor exit (secondary, buyout, or acqui-hire)
    "Secondary Sale",  # LP stake or employee share sale on secondary market
    "SPAC",            # SPAC merger / blank-cheque vehicle
    "Debt Financing",  # Venture debt, credit facility, or convertible note
]

_DEALS_SYSTEM_PROMPT = """You are a fact-checking financial journalist covering private markets for \
a professional investor audience.

Non-negotiable sourcing rules:
1. Extract ONLY facts explicitly stated in the provided article text. Never invent figures.
2. Accept only Tier 1 primary sources: company press releases, SEC filings, Bloomberg, WSJ, FT, \
   Reuters, TechCrunch, The Information. If the article is from a secondary source, identify what \
   primary source it cites.
3. Label every financial figure:
   - "confirmed-closed": round/deal definitively closed (confirmed by press release, SEC, company)
   - "announced": reported/announced but closure not yet confirmed
   - "projected": analyst estimate, valuation model, or unnamed source
4. Always specify pre-money vs post-money for valuations. Write "type not specified" if absent.
5. If two sources in the text give different figures, report both: "$4B–$4.5B (Source A vs Source B)".
6. For each key figure, provide a citation — the exact quote from the article.
7. Omit any fact that cannot be traced to a specific sentence in the provided text."""


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
                "company":         "",
                "deal_type":       "Fundraise",
                "sector":          "Other",
                "round":           "",
                "amount":          "Not disclosed",
                "valuation":       "Not disclosed",
                "prior_valuation": "Not disclosed",
                "lead_investors":  [],
                "pricing_notes":   "",
                "is_down_round":   False,
                "summary":         art.get("title", ""),
                "article_date":    (art.get("published") or "")[:10],
                "url":             art.get("url", "#"),
                "source":          art.get("source", ""),
            })
        return stubs

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        articles_text = ""
        for i, art in enumerate(new_articles[:15], 1):
            body = art.get("full_text") or art.get("summary", "")
            tier = art.get("source_tier", 3)
            tier_label = {1: "Tier 1 (Primary)", 2: "Tier 2", 3: "Tier 3 (Aggregator)"}.get(tier, "Tier 3")
            articles_text += (
                f"\n--- Article {i} ---\n"
                f"Title:   {art.get('title', '')}\n"
                f"Date:    {art.get('published', 'unknown')}\n"
                f"Source:  {art.get('source', '')}  [{tier_label}]\n"
                f"URL:     {art.get('url', '')}\n"
                f"Body:\n{body[:2500]}\n"
            )

        prompt = (
            f"Below are {len(new_articles[:15])} articles. "
            "Identify every genuine capital-markets event: fundraising rounds, IPO filings/pricings, "
            "acquisitions, exits, fund closes, down rounds, bridge rounds, secondary sales, "
            "debt financings, and SPACs.\n\n"
            "FACT-CHECKING RULES:\n"
            "- Extract ONLY figures explicitly stated in the article body text.\n"
            "- Label deal_status: 'confirmed-closed' / 'announced' / 'projected'.\n"
            "- Specify pre-money or post-money for each valuation. Write 'type not specified' if absent.\n"
            "- Provide a citation: the exact sentence from the article supporting each key figure.\n"
            "- If Tier 3 source: name the primary source it cites in primary_source_cited.\n"
            "- Set deal_type='Down Round' only if the article explicitly states valuation is below the "
            "prior round or uses 'down round'/'flat round'.\n"
            "- Set deal_type='Fund Close' for GP fund announcements (company = GP name).\n"
            "- SKIP any article where no specific named company or verifiable dollar figure exists.\n\n"
            f"{articles_text}\n"
            "Return ONLY valid JSON — a top-level array (no markdown fences):\n"
            "[\n"
            "  {{\n"
            f'    "company": "Company or GP firm name",\n'
            f'    "deal_type": one of [{deal_types_str}],\n'
            f'    "sector": one of [{sectors_str}],\n'
            '    "round": "Round label e.g. Series C, Fund IV — or empty string",\n'
            '    "amount": "e.g. \'$500M (announced)\' — or \\"Not disclosed\\"",\n'
            '    "valuation": "e.g. \'$4.5B post-money (announced)\' — or \\"Not disclosed\\"",\n'
            '    "prior_valuation": "Prior-round valuation if stated — or \\"Not disclosed\\"",\n'
            '    "lead_investors": ["Lead investor 1", "Lead investor 2"],\n'
            '    "pricing_notes": "IPO price range or pricing details — or empty string",\n'
            '    "is_down_round": true or false,\n'
            '    "deal_status": "confirmed-closed" | "announced" | "projected",\n'
            '    "citation": "Exact sentence from the article supporting the key figure.",\n'
            '    "source_tier": 1 | 2 | 3,\n'
            '    "primary_source_cited": "Primary source named by aggregator — or empty string",\n'
            '    "summary": "2-3 sentences: what happened, why it matters. Bold figures with <strong>. '
            'State deal_status and valuation type explicitly.",\n'
            '    "article_date": "e.g. Mar 10, 2026",\n'
            '    "url": "article URL",\n'
            '    "source": "publication name"\n'
            "  }}\n"
            "]\n\n"
            "Return [] if no verifiable deal articles found. Max 10 deals."
        )

        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2800,
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

        # Normalise fields and cap at 10 deals
        cleaned = []
        _valid_statuses = {"confirmed-closed", "announced", "projected"}
        for d in deals[:10]:
            if not isinstance(d, dict) or not d.get("company"):
                continue
            if d.get("deal_type") not in DEAL_TYPES:
                d["deal_type"] = "Fundraise"
            if d.get("sector") not in SECTOR_BADGE:
                d["sector"] = "Other"
            if not isinstance(d.get("lead_investors"), list):
                d["lead_investors"] = []
            d["is_down_round"] = bool(d.get("is_down_round", False))
            if d["is_down_round"] and d["deal_type"] == "Fundraise":
                d["deal_type"] = "Down Round"
            d.setdefault("prior_valuation", "Not disclosed")
            # Ensure new fact-checking fields exist with safe defaults
            if d.get("deal_status") not in _valid_statuses:
                d["deal_status"] = "announced"
            d.setdefault("citation", "")
            d.setdefault("source_tier", 3)
            d.setdefault("primary_source_cited", "")
            cleaned.append(d)

        return cleaned

    except Exception as exc:
        logger.warning("research_deals failed: %s", exc)
        return []
