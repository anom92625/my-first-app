"""
Newsletter HTML generator.

Design philosophy (learned from Morning Brew, TLDR, Axios, 1440):
  - Single-column layout, max 600px — mobile-first
  - Clear visual hierarchy: header → intro → top stories → quick hits → footer
  - Each story has a hook, summary, takeaway, and cited source with link
  - "Why it matters" framing (Axios Smart Brevity)
  - Consistent typography; generous whitespace; subtle colour accents
  - Plain-text fallback maintained alongside HTML
"""
from datetime import datetime
from typing import Any


CATEGORY_DISPLAY = {
    "technology":  "Technology",
    "business":    "Business & Finance",
    "science":     "Science & Research",
    "world-news":  "World News",
    "ai-ml":       "AI & Machine Learning",
    "health":      "Health & Wellness",
    "startups":    "Startups",
    "environment": "Climate & Environment",
    "sports":      "Sports",
    "culture":     "Arts & Culture",
    "politics":    "Politics",
    "space":       "Space & Astronomy",
}

BRAND_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
BG_COLOR = "#f8f9fa"
CARD_BG = "#ffffff"
MUTED_COLOR = "#6c757d"


def _article_card_html(article: dict[str, Any], index: int) -> str:
    """Render a single top-story card."""
    title = article.get("title", "Untitled")
    url = article.get("url", "#")
    source = article.get("source", "Unknown source")
    hook = article.get("hook", "")
    summary = article.get("summary", "")
    takeaway = article.get("takeaway", "")
    published = article.get("published", "")
    category_slug = article.get("category", "")
    category_label = CATEGORY_DISPLAY.get(category_slug, category_slug.title())

    # Format date
    date_str = ""
    if published:
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            date_str = dt.strftime("%b %d, %Y")
        except ValueError:
            date_str = published[:10]

    hook_html = f'<p style="margin:0 0 10px;font-style:italic;color:#555;font-size:15px;">{hook}</p>' if hook else ""
    summary_html = f'<p style="margin:0 0 10px;font-size:15px;line-height:1.6;color:#222;">{summary}</p>' if summary else ""
    takeaway_html = (
        f'<div style="background:#f0f4ff;border-left:4px solid {ACCENT_COLOR};padding:10px 14px;margin:12px 0 0;border-radius:0 4px 4px 0;">'
        f'<span style="font-size:12px;font-weight:700;text-transform:uppercase;color:{ACCENT_COLOR};letter-spacing:0.5px;">Key Takeaway</span>'
        f'<p style="margin:4px 0 0;font-size:14px;color:#333;line-height:1.5;">{takeaway}</p>'
        f'</div>'
    ) if takeaway else ""

    return f"""
<div style="background:{CARD_BG};border-radius:8px;padding:20px 24px;margin-bottom:16px;border:1px solid #e8e8e8;">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px;">
    <span style="background:#eef2ff;color:#4361ee;font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;text-transform:uppercase;letter-spacing:0.5px;">{category_label}</span>
    {f'<span style="color:{MUTED_COLOR};font-size:12px;">{date_str}</span>' if date_str else ''}
  </div>
  <h2 style="margin:0 0 10px;font-size:18px;line-height:1.4;font-weight:700;">
    <a href="{url}" style="color:{BRAND_COLOR};text-decoration:none;" target="_blank">{title}</a>
  </h2>
  {hook_html}
  {summary_html}
  {takeaway_html}
  <div style="margin-top:14px;font-size:13px;color:{MUTED_COLOR};">
    Source: <a href="{url}" style="color:{ACCENT_COLOR};text-decoration:none;" target="_blank">{source}</a>
    &nbsp;&middot;&nbsp;
    <a href="{url}" style="color:{MUTED_COLOR};font-size:12px;" target="_blank">Read full article &rarr;</a>
  </div>
</div>"""


def _quick_hit_html(article: dict[str, Any]) -> str:
    """Render a single quick-hit row (compact format)."""
    title = article.get("title", "Untitled")
    url = article.get("url", "#")
    source = article.get("source", "")
    summary = article.get("summary", "")[:160]
    category_slug = article.get("category", "")
    category_label = CATEGORY_DISPLAY.get(category_slug, "")

    return f"""
<div style="padding:12px 0;border-bottom:1px solid #eee;">
  <div style="font-size:11px;color:{MUTED_COLOR};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">{category_label}</div>
  <a href="{url}" style="font-size:15px;font-weight:600;color:{BRAND_COLOR};text-decoration:none;line-height:1.4;" target="_blank">{title}</a>
  {f'<p style="margin:4px 0 0;font-size:13px;color:#555;line-height:1.4;">{summary}...</p>' if summary else ''}
  <div style="margin-top:4px;font-size:12px;color:{MUTED_COLOR};">{source}</div>
</div>"""


def build_html_newsletter(
    user_name: str,
    intro_text: str,
    top_stories: list[dict[str, Any]],
    quick_hits: list[dict[str, Any]],
    date_str: str,
    unsubscribe_url: str = "#",
) -> str:
    """Assemble the full HTML newsletter."""

    top_stories_html = "".join(_article_card_html(a, i) for i, a in enumerate(top_stories))
    quick_hits_html = "".join(_quick_hit_html(a) for a in quick_hits)

    # All sources for citation footer
    all_articles = top_stories + quick_hits
    sources = sorted({a.get("source", "") for a in all_articles if a.get("source")})
    sources_html = " &middot; ".join(
        f'<a href="{a.get("url","#")}" style="color:{MUTED_COLOR};text-decoration:none;">{a.get("source","")}</a>'
        for a in all_articles if a.get("source")
    )

    quick_hits_section = ""
    if quick_hits:
        quick_hits_section = f"""
<div style="background:{CARD_BG};border-radius:8px;padding:20px 24px;margin-bottom:16px;border:1px solid #e8e8e8;">
  <h3 style="margin:0 0 4px;font-size:13px;font-weight:700;color:{ACCENT_COLOR};text-transform:uppercase;letter-spacing:1px;">Quick Hits</h3>
  <p style="margin:0 0 14px;font-size:12px;color:{MUTED_COLOR};">Stories worth a click</p>
  {quick_hits_html}
</div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Your Daily Brief — {date_str}</title>
</head>
<body style="margin:0;padding:0;background:{BG_COLOR};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:620px;margin:0 auto;padding:24px 16px;">

  <!-- HEADER -->
  <div style="background:{BRAND_COLOR};border-radius:10px 10px 0 0;padding:28px 32px;text-align:center;margin-bottom:0;">
    <div style="font-size:11px;color:rgba(255,255,255,0.6);text-transform:uppercase;letter-spacing:2px;margin-bottom:6px;">Your Daily Brief</div>
    <h1 style="margin:0;font-size:26px;font-weight:800;color:#fff;">{date_str}</h1>
    <div style="width:40px;height:3px;background:{ACCENT_COLOR};margin:12px auto 0;border-radius:2px;"></div>
  </div>

  <!-- INTRO BANNER -->
  <div style="background:#16213e;border-radius:0 0 10px 10px;padding:18px 32px 22px;margin-bottom:20px;">
    <p style="margin:0;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.85);">
      {intro_text}
    </p>
  </div>

  <!-- WHAT'S INSIDE -->
  <div style="background:{CARD_BG};border-radius:8px;padding:16px 24px;margin-bottom:20px;border:1px solid #e8e8e8;">
    <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:{ACCENT_COLOR};text-transform:uppercase;letter-spacing:1px;">In Today's Brief</p>
    <ul style="margin:0;padding-left:18px;font-size:14px;color:#444;line-height:1.8;">
      {chr(10).join(f'<li><strong>{a.get("title","")[:72]}{"..." if len(a.get("title","")) > 72 else ""}</strong></li>' for a in top_stories[:3])}
      {"<li>+ " + str(len(quick_hits)) + " quick hits</li>" if quick_hits else ""}
    </ul>
  </div>

  <!-- TOP STORIES -->
  <h3 style="margin:0 0 12px;font-size:13px;font-weight:700;color:{MUTED_COLOR};text-transform:uppercase;letter-spacing:1px;padding-left:4px;">Top Stories</h3>
  {top_stories_html}

  <!-- QUICK HITS -->
  {quick_hits_section}

  <!-- SOURCES / CITATIONS -->
  <div style="background:{CARD_BG};border-radius:8px;padding:16px 24px;margin-bottom:20px;border:1px solid #e8e8e8;">
    <p style="margin:0 0 8px;font-size:11px;font-weight:700;color:{MUTED_COLOR};text-transform:uppercase;letter-spacing:1px;">Sources</p>
    <p style="margin:0;font-size:12px;color:{MUTED_COLOR};line-height:1.8;">{sources_html}</p>
  </div>

  <!-- FOOTER -->
  <div style="text-align:center;padding:20px 0 12px;">
    <p style="margin:0 0 6px;font-size:12px;color:{MUTED_COLOR};">
      You're receiving this because you subscribed to My Daily Brief.
    </p>
    <p style="margin:0;font-size:12px;">
      <a href="{unsubscribe_url}" style="color:{MUTED_COLOR};text-decoration:underline;">Unsubscribe</a>
      &nbsp;&middot;&nbsp;
      <a href="#" style="color:{MUTED_COLOR};text-decoration:underline;">Update preferences</a>
    </p>
    <p style="margin:12px 0 0;font-size:11px;color:#bbb;">My Daily Brief &copy; {date_str[-4:]}</p>
  </div>

</div>
</body>
</html>"""


def _company_card_html(row: dict, index: int) -> str:
    """
    Render a single company story card.
    Design inspired by Axios Pro Deals and Term Sheet (Fortune):
    - Color-coded update-type badge
    - Company name + valuation in card header
    - One-liner company description
    - Bold update headline
    - Investor summary paragraph
    - Source + date footer with read link
    """
    from newsletter.summarizer import UPDATE_TYPE_COLORS

    company      = row.get("company", "")
    description  = row.get("description", "")
    valuation    = row.get("valuation", "Not publicly disclosed")
    update_type  = row.get("update_type", "Other")
    update       = row.get("update", "")
    article_date = row.get("article_date", "")
    summary      = row.get("summary", "")
    url          = row.get("url", "#")
    source       = row.get("source", "")

    badge_color  = UPDATE_TYPE_COLORS.get(update_type, "#6b7280")

    # Valuation display: dim if not disclosed
    val_is_known = valuation and valuation.lower() not in ("n/a", "not publicly disclosed", "not disclosed", "")
    val_color    = "#059669" if val_is_known else MUTED_COLOR   # green if real number
    val_display  = valuation if val_is_known else "Not disclosed"

    return f"""
<div style="background:#ffffff;border-radius:10px;border:1px solid #e5e7eb;margin-bottom:18px;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">

  <!-- Card header: update-type badge + company name + valuation -->
  <div style="background:#f9fafb;border-bottom:1px solid #e5e7eb;padding:14px 20px;display:table;width:100%;box-sizing:border-box;">
    <div style="display:table-cell;vertical-align:middle;">
      <span style="display:inline-block;background:{badge_color};color:#fff;font-size:10px;font-weight:700;padding:3px 9px;border-radius:20px;text-transform:uppercase;letter-spacing:0.6px;margin-bottom:6px;">{update_type}</span>
      <div style="font-size:20px;font-weight:800;color:{BRAND_COLOR};letter-spacing:-0.3px;line-height:1.1;">{company}</div>
    </div>
    <div style="display:table-cell;vertical-align:middle;text-align:right;white-space:nowrap;padding-left:16px;">
      <div style="font-size:22px;font-weight:800;color:{val_color};letter-spacing:-0.5px;">{val_display}</div>
      <div style="font-size:10px;font-weight:600;color:{MUTED_COLOR};text-transform:uppercase;letter-spacing:0.5px;margin-top:2px;">Valuation</div>
    </div>
  </div>

  <!-- Card body -->
  <div style="padding:18px 20px 16px;">

    <!-- Company description (one-liner) -->
    {"" if not description else f'<p style="margin:0 0 14px;font-size:13px;color:#6b7280;line-height:1.5;font-style:italic;">{description}</p>'}

    <!-- Bold update headline -->
    <p style="margin:0 0 10px;font-size:15px;font-weight:700;color:#111827;line-height:1.4;">{update}</p>

    <!-- Investor summary -->
    {"" if not summary else f'<p style="margin:0 0 14px;font-size:14px;color:#374151;line-height:1.65;">{summary}</p>'}

    <!-- Footer: date · source · read link -->
    <div style="display:table;width:100%;margin-top:4px;">
      <div style="display:table-cell;vertical-align:middle;">
        <span style="font-size:12px;color:{MUTED_COLOR};">{article_date}</span>
        {"" if not source else f' <span style="color:#d1d5db;font-size:12px;">&middot;</span> <span style="font-size:12px;color:{MUTED_COLOR};">{source}</span>'}
      </div>
      <div style="display:table-cell;vertical-align:middle;text-align:right;">
        <a href="{url}" style="font-size:13px;font-weight:600;color:{ACCENT_COLOR};text-decoration:none;" target="_blank">Read article &rarr;</a>
      </div>
    </div>

  </div>
</div>"""


def build_watchlist_newsletter(
    user_name: str,
    rows: list[dict],
    date_str: str,
    unsubscribe_url: str = "#",
) -> str:
    """
    Build an HTML newsletter for private company watchlist updates.
    Design inspired by Axios Pro Deals, Term Sheet (Fortune), and Morning Brew:
    - Story cards per company (not a flat table — better for readability and mobile)
    - Color-coded update-type badges (Funding Round, IPO, Acquisition, etc.)
    - Company valuation prominently displayed in card header
    - Clean dark header + subtle intro banner
    """
    n = len(rows)

    if not rows:
        body_html = f"""
<div style="background:#fff;border-radius:10px;padding:40px 32px;text-align:center;border:1px solid #e5e7eb;">
  <div style="font-size:36px;margin-bottom:16px;">&#128202;</div>
  <p style="font-size:16px;font-weight:600;color:#111827;margin:0 0 8px;">No new updates today</p>
  <p style="font-size:14px;color:{MUTED_COLOR};margin:0;">
    No investor-relevant news was found for your watchlist. Check back tomorrow.
  </p>
</div>"""
    else:
        cards = "".join(_company_card_html(row, i) for i, row in enumerate(rows))
        body_html = f"""
<p style="margin:0 0 16px;font-size:11px;font-weight:700;color:{MUTED_COLOR};text-transform:uppercase;letter-spacing:1.5px;">
  {n} Update{"s" if n != 1 else ""} &mdash; {date_str}
</p>
{cards}"""

    # "In this brief" summary bar (only when there are rows)
    if rows:
        company_pills = "".join(
            f'<span style="display:inline-block;background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.9);'
            f'font-size:12px;font-weight:600;padding:4px 11px;border-radius:20px;'
            f'border:1px solid rgba(255,255,255,0.2);margin:3px 4px 3px 0;">'
            f'{r.get("company", "")}</span>'
            for r in rows
        )
        toc_html = f'<div style="margin-top:14px;">{company_pills}</div>'
    else:
        toc_html = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Private Market Brief &mdash; {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<div style="max-width:660px;margin:0 auto;padding:28px 16px 40px;">

  <!-- ── HEADER ── -->
  <div style="background:{BRAND_COLOR};border-radius:12px 12px 0 0;padding:30px 32px 24px;text-align:center;">
    <div style="font-size:10px;color:rgba(255,255,255,0.5);text-transform:uppercase;letter-spacing:2.5px;margin-bottom:8px;">Private Market Intelligence</div>
    <h1 style="margin:0;font-size:28px;font-weight:800;color:#ffffff;letter-spacing:-0.5px;">{date_str}</h1>
    <div style="width:36px;height:3px;background:{ACCENT_COLOR};border-radius:2px;margin:14px auto 0;"></div>
  </div>

  <!-- ── INTRO BAND ── -->
  <div style="background:#16213e;border-radius:0 0 12px 12px;padding:18px 32px 22px;margin-bottom:28px;">
    <p style="margin:0 0 4px;font-size:15px;line-height:1.7;color:rgba(255,255,255,0.88);">
      Good morning, {user_name}. Your watchlist has {n} new update{"s" if n != 1 else ""} today.
    </p>
    {toc_html}
  </div>

  <!-- ── STORY CARDS ── -->
  {body_html}

  <!-- ── DISCLAIMER ── -->
  <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:14px 18px;margin-top:24px;margin-bottom:24px;">
    <p style="margin:0;font-size:12px;color:#92400e;line-height:1.6;">
      <strong>Disclaimer:</strong> All updates are sourced from publicly available news articles.
      This brief is for informational purposes only and does not constitute investment advice.
      Always verify information independently before making any investment decisions.
    </p>
  </div>

  <!-- ── FOOTER ── -->
  <div style="text-align:center;padding:8px 0 4px;">
    <p style="margin:0 0 6px;font-size:12px;color:{MUTED_COLOR};">
      You're receiving this because you subscribed to My Daily Brief.
    </p>
    <p style="margin:0;font-size:12px;">
      <a href="{unsubscribe_url}" style="color:{MUTED_COLOR};text-decoration:underline;">Unsubscribe</a>
    </p>
    <p style="margin:10px 0 0;font-size:11px;color:#9ca3af;">My Daily Brief &copy; {date_str[-4:]}</p>
  </div>

</div>
</body>
</html>"""


def build_plain_text_watchlist_newsletter(
    user_name: str,
    rows: list[dict],
    date_str: str,
) -> str:
    """Plain-text fallback for the watchlist newsletter."""
    lines = [
        f"PRIVATE MARKET BRIEF — {date_str}",
        "=" * 60,
        "",
        f"Good morning, {user_name}. {len(rows)} update(s) across your watchlist.",
        "",
    ]
    for row in rows:
        lines += [
            f"[ {row.get('update_type', 'Update').upper()} ]",
            f"COMPANY:    {row.get('company', '')}",
            f"VALUATION:  {row.get('valuation', 'Not disclosed')}",
            f"WHAT:       {row.get('description', '')}",
            f"UPDATE:     {row.get('update', '')}",
            f"SUMMARY:    {row.get('summary', '')}",
            f"DATE:       {row.get('article_date', '')}  |  {row.get('source', '')}",
            f"LINK:       {row.get('url', '')}",
            "-" * 60,
            "",
        ]
    lines += ["My Daily Brief — Private Market Intelligence"]
    return "\n".join(lines)


def build_plain_text_newsletter(
    user_name: str,
    intro_text: str,
    top_stories: list[dict[str, Any]],
    quick_hits: list[dict[str, Any]],
    date_str: str,
) -> str:
    """Plain-text fallback for email clients that don't render HTML."""
    lines = [
        f"MY DAILY BRIEF — {date_str}",
        "=" * 50,
        "",
        intro_text,
        "",
        "TOP STORIES",
        "-" * 50,
    ]

    for i, art in enumerate(top_stories, 1):
        lines += [
            f"\n{i}. {art.get('title', 'Untitled')}",
            f"   Source: {art.get('source', '')} | {art.get('url', '')}",
        ]
        if art.get("hook"):
            lines.append(f"   Why it matters: {art['hook']}")
        if art.get("summary"):
            lines.append(f"   {art['summary']}")
        if art.get("takeaway"):
            lines.append(f"   Key takeaway: {art['takeaway']}")

    if quick_hits:
        lines += ["", "QUICK HITS", "-" * 50]
        for art in quick_hits:
            lines += [
                f"\n- {art.get('title', '')}",
                f"  {art.get('source', '')} | {art.get('url', '')}",
            ]

    lines += ["", "=" * 50, "My Daily Brief"]
    return "\n".join(lines)
