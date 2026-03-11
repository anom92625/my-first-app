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


def _table_row_html(row: dict, index: int) -> str:
    """Render one <tr> for the deal tracker table."""
    from newsletter.summarizer import UPDATE_TYPE_PILL, SECTOR_BADGE

    company       = row.get("company", "")
    sector        = row.get("sector", "Other")
    update_type   = row.get("update_type", "Other")
    article_date  = row.get("article_date", "")
    valuation     = row.get("valuation", "Not publicly disclosed")
    last_round    = row.get("last_round", "")
    key_investors = row.get("key_investors", [])
    update        = row.get("update", "")
    summary       = row.get("summary", "")
    url           = row.get("url", "#")
    source        = row.get("source", "")

    badge_label, badge_cls = SECTOR_BADGE.get(sector, ("Tech", "b-macro"))
    pill_label,  pill_cls  = UPDATE_TYPE_PILL.get(update_type, ("Update", "p-analysis"))

    # Valuation: separate the main figure from the parenthetical context
    # e.g. "$4.5B (Series C, Jan 2024)" → figure="$4.5B"  ctx="(Series C, Jan 2024)"
    val_figure = valuation
    val_ctx    = ""
    if "(" in valuation:
        val_figure = valuation[:valuation.index("(")].strip()
        val_ctx    = valuation[valuation.index("("):].strip()

    val_lower   = val_figure.lower()
    val_is_real = val_lower not in ("not publicly disclosed", "not disclosed", "n/a", "", "unknown")
    val_class   = "val val-h" if val_is_real else "val"

    val_html = f"<span class='{val_class}'>{val_figure}</span>"
    if val_ctx:
        val_html += f"<br><span style='font-family:monospace;font-size:9px;color:#4a4e5a;'>{val_ctx}</span>"
    if last_round:
        val_html += (
            f"<br><span style='font-family:monospace;font-size:9px;letter-spacing:.08em;"
            f"color:#4a4e5a;text-transform:uppercase;'>{last_round}</span>"
        )

    # Show top investor(s) from baseline as small badges under the company name
    investor_badges = ""
    if key_investors:
        investor_badges = "".join(
            f"<span style='display:inline-block;font-family:monospace;font-size:9px;"
            f"background:#f0ece3;border:1px solid #d8d3c8;padding:0 5px;margin:1px 2px 1px 0;"
            f"border-radius:1px;color:#282830;'>{inv}</span>"
            for inv in key_investors[:2]
        )
        investor_badges = f"<div style='margin-top:3px;'>{investor_badges}</div>"

    # Combine update headline + summary into one readable cell
    summary_html = ""
    if update:
        summary_html += f"<strong>{update}</strong>"
    if summary:
        summary_html += f"<br><span style='font-weight:300;color:#4a4e5a;'>{summary}</span>"

    row_num = str(index + 1).zfill(2)

    return (
        f"<tr>"
        f"<td class='rn'>{row_num}</td>"
        f"<td class='co'>"
        f"  <span class='co-name'>{company}<span class='new-dot'></span></span>"
        f"  <span class='badge {badge_cls}'>{badge_label}</span>"
        f"  {investor_badges}"
        f"</td>"
        f"<td><span class='pill {pill_cls}'>{pill_label}</span></td>"
        f"<td class='date-cell'>{article_date}</td>"
        f"<td>{val_html}</td>"
        f"<td class='sum'>{summary_html}</td>"
        f"<td>"
        f"  <a class='src-link' href='{url}' target='_blank'>{source}</a>"
        f"</td>"
        f"</tr>"
    )


def _ipo_grid_html(ipo_rows: list[dict]) -> str:
    """Render the IPO watchlist grid (only shown when IPO Activity rows exist)."""
    color_cycle = ["c1", "c2", "c3", "c4", "c5", "c6"]
    cards = ""
    for i, row in enumerate(ipo_rows):
        cls    = color_cycle[i % len(color_cycle)]
        status = row.get("update", "")[:60]
        val    = row.get("valuation", "N/A")
        detail = row.get("summary", "")[:180]
        cards += (
            f"<div class='ipo-card {cls}'>"
            f"<div class='ipo-co'>{row.get('company','')}</div>"
            f"<div class='ipo-status'>{status}</div>"
            f"<div class='ipo-val'>{val}</div>"
            f"<div class='ipo-detail'>{detail}</div>"
            f"</div>"
        )
    return (
        "<div class='sec'>"
        "<span class='sec-title'>IPO Pipeline — Watchlist View</span>"
        "<span class='sec-sub'>Companies with active IPO activity</span>"
        "</div>"
        f"<div class='ipo-grid'>{cards}</div>"
    )


def _deal_card_html(deal: dict[str, Any], index: int) -> str:
    """Render one deal card for the Deals & Fundraising section."""
    company        = deal.get("company", "Unknown")
    deal_type      = deal.get("deal_type", "Fundraise")
    sector         = deal.get("sector", "Other")
    round_label    = deal.get("round", "")
    amount         = deal.get("amount", "Not disclosed")
    valuation      = deal.get("valuation", "Not disclosed")
    prior_val      = deal.get("prior_valuation", "Not disclosed")
    lead_investors = deal.get("lead_investors", [])
    pricing_notes  = deal.get("pricing_notes", "")
    summary        = deal.get("summary", "")
    article_date   = deal.get("article_date", "")
    url            = deal.get("url", "#")
    source         = deal.get("source", "")
    is_down_round  = bool(deal.get("is_down_round", False))

    # Down rounds get a red top-border; fund closes get gold; everything else navy
    if is_down_round or deal_type == "Down Round":
        top_border = "#b8271f"
    elif deal_type == "Fund Close":
        top_border = "#c9a84c"
    elif deal_type in ("IPO Filing", "IPO Priced"):
        top_border = "#0f2545"
    else:
        top_border = "#0f2545"

    # Deal-type pill colours
    pill_styles = {
        "Fundraise":      "color:#0d4f2c;border-color:#98d4b0;background:#e4f0ea;",
        "Down Round":     "color:#7a0f0f;border-color:#e8a0a0;background:#fdeaea;font-weight:700;",
        "Bridge Round":   "color:#7a4400;border-color:#e8c07a;background:#fef5e5;",
        "Fund Close":     "color:#5a3d00;border-color:#c9a84c;background:#faf4e3;font-weight:700;",
        "IPO Filing":     "color:#0f2545;border-color:#8aa8d8;background:#e5eaf3;",
        "IPO Priced":     "color:#0a3020;border-color:#4a9c70;background:#d4f0e3;font-weight:700;",
        "Acquisition":    "color:#5a1f0a;border-color:#e8a87a;background:#fef0e5;",
        "Exit":           "color:#5a1f0a;border-color:#e8a87a;background:#fef0e5;",
        "Secondary Sale": "color:#4a3200;border-color:#d4b870;background:#faf4e3;",
        "SPAC":           "color:#2b0d50;border-color:#b89fd8;background:#f0e9fb;",
        "Debt Financing": "color:#3a3a3a;border-color:#aaa;background:#f0ece3;",
    }
    pill_style = pill_styles.get(deal_type, "color:#3a3a3a;border-color:#aaa;background:#f0ece3;")

    # Amount display — highlight if real figure
    amount_lower = amount.lower()
    amount_is_real = amount_lower not in ("not disclosed", "n/a", "")
    amount_color = "#b8271f" if amount_is_real else "#4a4e5a"

    # Down-round alert banner (shown above the card content)
    down_round_banner = ""
    if is_down_round or deal_type == "Down Round":
        prior_note = f" (prior: {prior_val})" if prior_val not in ("Not disclosed", "N/A", "") else ""
        down_round_banner = (
            f'<div style="background:#fdeaea;border-left:3px solid #b8271f;'
            f'padding:6px 10px;margin-bottom:10px;font-family:monospace;font-size:10px;'
            f'color:#7a0f0f;letter-spacing:.04em;">'
            f'&#9660;&nbsp;<strong>DOWN ROUND</strong> — Valuation reset{prior_note}. '
            f'Monitor for follow-on distress.</div>'
        )

    # Lead investors badge list
    investors_html = ""
    if lead_investors:
        badges = "".join(
            f'<span style="display:inline-block;font-family:monospace;font-size:10px;'
            f'background:#f0ece3;border:1px solid #d8d3c8;padding:1px 7px;border-radius:2px;'
            f'margin:2px 3px 2px 0;color:#282830;">{inv}</span>'
            for inv in lead_investors[:3]
        )
        label = "Fund LPs" if deal_type == "Fund Close" else "Lead Investors"
        investors_html = (
            f'<div style="margin-top:10px;">'
            f'<span style="font-family:monospace;font-size:9px;letter-spacing:.12em;'
            f'text-transform:uppercase;color:#4a4e5a;">{label}&nbsp;&nbsp;</span>'
            f'{badges}</div>'
        )

    pricing_html = ""
    if pricing_notes:
        pricing_html = (
            f'<div style="margin-top:8px;padding:6px 10px;background:#faf4e3;'
            f'border-left:3px solid #c9a84c;font-size:12px;color:#4a3200;line-height:1.5;">'
            f'<strong>Pricing:</strong> {pricing_notes}</div>'
        )

    valuation_html = ""
    if valuation and valuation.lower() not in ("not disclosed", "n/a", ""):
        val_bg = "#fdeaea" if (is_down_round or deal_type == "Down Round") else "#f5e8e7"
        valuation_html = (
            f'<span style="font-family:monospace;font-size:10px;padding:2px 8px;'
            f'background:{val_bg};border:1px solid #e0b0ab;border-radius:2px;'
            f'color:#b8271f;margin-left:8px;">Val: {valuation}</span>'
        )

    round_html = (
        f'<span style="font-family:monospace;font-size:10px;color:#4a4e5a;">{round_label}</span>&nbsp;&nbsp;'
        if round_label else ""
    )

    return (
        f'<div style="background:#fff;border:1px solid #d8d3c8;border-radius:2px;'
        f'border-top:3px solid {top_border};padding:18px 20px;margin-bottom:1px;">'
        f'{down_round_banner}'
        # Top row: company + deal type pill
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between;'
        f'gap:12px;margin-bottom:10px;flex-wrap:wrap;">'
        f'  <div>'
        f'    <a href="{url}" target="_blank" style="font-family:Georgia,serif;font-size:16px;'
        f'font-weight:700;color:#0a0a0c;text-decoration:none;line-height:1.2;">{company}</a>'
        f'    <div style="margin-top:4px;font-family:monospace;font-size:9px;letter-spacing:.15em;'
        f'text-transform:uppercase;color:#4a4e5a;">{sector}</div>'
        f'  </div>'
        f'  <span style="font-family:monospace;font-size:9px;letter-spacing:.09em;'
        f'text-transform:uppercase;padding:3px 9px;border:1px solid;border-radius:1px;'
        f'white-space:nowrap;{pill_style}">{deal_type}</span>'
        f'</div>'
        # Amount row
        f'<div style="display:flex;align-items:baseline;gap:6px;margin-bottom:8px;flex-wrap:wrap;">'
        f'  <span style="font-family:Georgia,serif;font-size:22px;font-weight:700;'
        f'line-height:1;color:{amount_color};">{amount}</span>'
        f'  {round_html}{valuation_html}'
        f'</div>'
        # Investors / LPs
        f'{investors_html}'
        # Summary
        f'<p style="margin:10px 0 0;font-size:12.5px;color:#282830;line-height:1.65;">{summary}</p>'
        # Pricing notes
        f'{pricing_html}'
        # Source / date footer
        f'<div style="margin-top:10px;font-family:monospace;font-size:10px;color:#4a4e5a;">'
        f'  {article_date}&nbsp;&middot;&nbsp;'
        f'  <a href="{url}" target="_blank" style="color:#0f2545;text-decoration:none;'
        f'border-bottom:1px solid rgba(15,37,69,.25);">{source}&nbsp;&#x2197;</a>'
        f'</div>'
        f'</div>'
    )


def _sec_filings_html(sec_filings: list[dict[str, Any]]) -> str:
    """
    Render SEC EDGAR S-1 / F-1 filings as a compact list subsection.
    These are the most authoritative IPO intent signals available — free and real-time.
    """
    if not sec_filings:
        return ""

    rows_html = ""
    for f in sec_filings:
        form  = f.get("form_type", "S-1")
        co    = f.get("company_raw") or f.get("title", "Unknown")
        url   = f.get("url", "#")
        date  = f.get("published", "")[:10]
        rows_html += (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:8px 0;border-bottom:1px solid #e8e3d8;gap:12px;flex-wrap:wrap;">'
            f'  <div>'
            f'    <span style="font-family:monospace;font-size:8px;letter-spacing:.15em;'
            f'text-transform:uppercase;background:#0f2545;color:#fff;'
            f'padding:1px 6px;margin-right:8px;border-radius:1px;">{form}</span>'
            f'    <a href="{url}" target="_blank" style="font-family:Georgia,serif;font-size:13px;'
            f'font-weight:700;color:#0a0a0c;text-decoration:none;">{co}</a>'
            f'  </div>'
            f'  <span style="font-family:monospace;font-size:10px;color:#4a4e5a;'
            f'white-space:nowrap;">{date}&nbsp;&middot;&nbsp;'
            f'<a href="{url}" target="_blank" style="color:#0f2545;text-decoration:none;'
            f'border-bottom:1px solid rgba(15,37,69,.25);">EDGAR&nbsp;&#x2197;</a></span>'
            f'</div>'
        )

    return (
        '<div style="margin-top:28px;padding:16px 20px;background:#e5eaf3;'
        'border:1px solid #8aa8d8;border-radius:2px;">'
        '<div style="font-family:monospace;font-size:8.5px;letter-spacing:.2em;'
        'text-transform:uppercase;color:#0f2545;margin-bottom:12px;">'
        '&#128196;&nbsp;SEC EDGAR — Recent IPO Registrations (S-1 / F-1)'
        '</div>'
        f'{rows_html}'
        '<div style="margin-top:10px;font-family:monospace;font-size:10px;color:#4a4e5a;">'
        'Source: <a href="https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&amp;type=S-1" '
        'target="_blank" style="color:#0f2545;text-decoration:none;'
        'border-bottom:1px solid rgba(15,37,69,.25);">SEC EDGAR public filings feed</a>'
        '</div>'
        '</div>'
    )


def _deals_section_html(
    deal_rows: list[dict[str, Any]],
    sec_filings: list[dict[str, Any]] | None = None,
) -> str:
    """Render the full IPOs, Exits & Fundraising section."""
    if not deal_rows and not sec_filings:
        return ""

    from collections import Counter

    # Sort: down rounds first (highest urgency), then fund closes, then rest
    def _sort_key(d: dict) -> int:
        dt = d.get("deal_type", "")
        if d.get("is_down_round") or dt == "Down Round":
            return 0
        if dt == "Bridge Round":
            return 1
        if dt in ("IPO Priced", "IPO Filing"):
            return 2
        if dt == "Fund Close":
            return 3
        return 4

    sorted_rows = sorted(deal_rows, key=_sort_key)
    cards_html = "".join(_deal_card_html(d, i) for i, d in enumerate(sorted_rows))

    # Stat bar: count deal types + flag if any down rounds
    type_counts = Counter(d.get("deal_type", "Fundraise") for d in deal_rows)
    down_count  = sum(1 for d in deal_rows if d.get("is_down_round") or d.get("deal_type") == "Down Round")
    stat_items  = " &middot; ".join(
        f'<span style="font-family:monospace;font-size:9px;letter-spacing:.1em;'
        f'text-transform:uppercase;">{count}&nbsp;{dtype}</span>'
        for dtype, count in sorted(type_counts.items())
    )
    down_alert = ""
    if down_count:
        down_alert = (
            f'&nbsp;&nbsp;<span style="font-family:monospace;font-size:9px;'
            f'color:#b8271f;font-weight:700;letter-spacing:.05em;">'
            f'&#9660;&nbsp;{down_count} DOWN ROUND{"S" if down_count > 1 else ""}</span>'
        )

    sec_html = _sec_filings_html(sec_filings or [])

    return (
        # Section header
        '<div style="padding:44px 0 14px;border-bottom:2px solid #0a0a0c;margin-bottom:24px;'
        'display:flex;align-items:baseline;justify-content:space-between;gap:16px;">'
        '  <span style="font-family:Georgia,serif;font-size:18px;font-weight:700;">'
        '    IPOs, Exits &amp; Fundraising</span>'
        '  <span style="font-family:monospace;font-size:8.5px;color:#4a4e5a;'
        'letter-spacing:.1em;white-space:nowrap;">New deals today</span>'
        '</div>'
        # Type breakdown bar (with down-round alert if any)
        f'<div style="margin-bottom:20px;padding:10px 14px;background:#f0ece3;'
        f'border:1px solid #d8d3c8;font-size:11px;color:#4a4e5a;">'
        f'{stat_items}{down_alert}</div>'
        # Deal cards (sorted: down rounds first)
        f'{cards_html}'
        # SEC EDGAR S-1 filings subsection
        f'{sec_html}'
    )


def _analyst_takes_html(takes: list[dict]) -> str:
    """Render the analyst takes section."""
    if not takes:
        return ""
    cards = ""
    for take in takes[:2]:
        tag   = take.get("tag", "Analysis")
        title = take.get("title", "")
        body  = take.get("body", "")
        cards += (
            f"<div class='a-card'>"
            f"<div class='a-tag'>{tag}</div>"
            f"<h3>{title}</h3>"
            f"<p>{body}</p>"
            f"</div>"
        )
    return (
        "<div class='sec'>"
        "<span class='sec-title'>What It Means For Investors</span>"
        "<span class='sec-sub'>Editorial Perspective</span>"
        "</div>"
        f"<div class='analysis-grid'>{cards}</div>"
    )


def build_watchlist_newsletter(
    user_name: str,
    rows: list[dict],
    meta: dict,
    date_str: str,
    vol_number: int = 1,
    unsubscribe_url: str = "#",
    deal_rows: list[dict] | None = None,
    sec_filings: list[dict] | None = None,
) -> str:
    """
    Build an HTML newsletter modelled on 'Private Markets Insider' example:
    - Branded top ribbon
    - Dark editorial header with serif headline + stats
    - "Only new stories" banner (navy, gold border)
    - Deal & Company Tracker table (dark thead, full-width)
    - IPO Pipeline grid (rendered only if IPO Activity rows exist)
    - Analyst Takes section (if narrative produced them)
    - Disclaimer + footer
    """
    n = len(rows)

    # Key-stats bar
    stats_html = ""
    for stat in meta.get("key_stats", []):
        stats_html += (
            f"<div class='hs-item'>"
            f"<span class='hs-val'>{stat.get('value','')}</span>"
            f"<span class='hs-key'>{stat.get('label','')}</span>"
            f"</div>"
        )
    if deal_rows:
        down_count = sum(
            1 for d in deal_rows
            if d.get("is_down_round") or d.get("deal_type") == "Down Round"
        )
        stats_html += (
            f"<div class='hs-item'>"
            f"<span class='hs-val'>{len(deal_rows)}</span>"
            f"<span class='hs-key'>New Deals &amp; IPOs</span>"
            f"</div>"
        )
        if down_count:
            stats_html += (
                f"<div class='hs-item'>"
                f"<span class='hs-val' style='color:#b8271f;'>&#9660;&nbsp;{down_count}</span>"
                f"<span class='hs-key'>Down Round{'s' if down_count > 1 else ''}</span>"
                f"</div>"
            )
    if sec_filings:
        stats_html += (
            f"<div class='hs-item'>"
            f"<span class='hs-val'>{len(sec_filings)}</span>"
            f"<span class='hs-key'>SEC IPO Filings</span>"
            f"</div>"
        )

    # Deal table rows
    if rows:
        table_rows_html = "\n".join(_table_row_html(r, i) for i, r in enumerate(rows))
        deal_section = f"""
<div class="page">
  <div class="sec">
    <span class="sec-title">Deal &amp; Company Tracker &mdash; {date_str}</span>
    <span class="sec-sub">All stories new since previous edition</span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th><th>Company</th><th>Type</th><th>Date</th>
          <th>Valuation</th><th>Summary</th><th>Source</th>
        </tr>
      </thead>
      <tbody>
        {table_rows_html}
      </tbody>
    </table>
  </div>
</div>"""
    else:
        deal_section = """
<div class="page" style="padding:40px 0;text-align:center;">
  <p style="font-family:'Space Mono',monospace;font-size:13px;color:#4a4e5a;">
    No new investor-relevant updates found for your watchlist today.
  </p>
</div>"""

    # IPO grid (only if IPO Activity rows exist)
    ipo_rows = [r for r in rows if r.get("update_type") == "IPO Activity"]
    ipo_section = (
        f"<div class='page'>{_ipo_grid_html(ipo_rows)}</div>"
        if ipo_rows else ""
    )

    # Analyst takes
    takes = meta.get("analyst_takes", [])
    analyst_section = (
        f"<div class='page'>{_analyst_takes_html(takes)}</div>"
        if takes else ""
    )

    # Deals & Fundraising section (includes SEC filings subsection)
    deals_section = (
        f"<div class='page'>{_deals_section_html(deal_rows or [], sec_filings)}</div>"
        if (deal_rows or sec_filings) else ""
    )

    headline_html = meta.get("headline_html", f"Private Market Intelligence &mdash; {date_str}")
    deck          = meta.get("deck", "")
    only_new_text = meta.get("only_new_text", "All stories are new in this edition.")

    # Day of week for header tag
    try:
        from datetime import datetime as _dt
        day_name = _dt.strptime(date_str, "%A, %B %-d, %Y").strftime("%A")
    except Exception:
        day_name = "Today"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Private Markets Insider &mdash; {date_str}</title>
<link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Space+Mono:wght@400;700&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --black:#0a0a0c; --white:#f9f7f2; --cream:#ede9e0;
    --red:#b8271f; --red-light:#f5e8e7;
    --navy:#0f2545; --navy-light:#e5eaf3;
    --gold:#c9a84c; --gold-light:#faf4e3;
    --green:#0d4f2c; --green-light:#e4f0ea;
    --slate:#4a4e5a; --rule:#d8d3c8; --card:#ffffff;
  }}
  *{{margin:0;padding:0;box-sizing:border-box;}}
  body{{font-family:'Outfit',sans-serif;background:var(--white);color:var(--black);font-size:14.5px;line-height:1.65;}}

  .ribbon{{background:var(--red);padding:7px 40px;display:flex;justify-content:space-between;align-items:center;}}
  .ribbon span{{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:.22em;text-transform:uppercase;color:rgba(249,247,242,.75);}}
  .ribbon .live{{color:#ffde7a;}}

  header{{background:var(--black);padding:52px 40px 46px;position:relative;overflow:hidden;}}
  header::before{{content:'';position:absolute;top:0;right:0;bottom:0;width:38%;background:repeating-linear-gradient(-45deg,transparent,transparent 8px,rgba(255,255,255,.018) 8px,rgba(255,255,255,.018) 9px);pointer-events:none;}}
  .vol-tag{{display:inline-flex;align-items:center;gap:10px;font-family:'Space Mono',monospace;font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:22px;}}
  .vol-tag::after{{content:'';display:block;width:30px;height:1px;background:var(--gold);}}
  header h1{{font-family:'Libre Baskerville',serif;font-size:clamp(28px,4vw,48px);font-weight:700;color:var(--white);line-height:1.1;max-width:780px;margin-bottom:16px;}}
  header h1 em{{font-style:italic;color:var(--gold);}}
  .header-deck{{font-size:13.5px;color:rgba(249,247,242,.5);max-width:600px;line-height:1.8;font-weight:300;}}
  .header-stats{{display:flex;gap:32px;margin-top:32px;padding-top:22px;border-top:1px solid rgba(249,247,242,.1);flex-wrap:wrap;}}
  .hs-item{{display:flex;flex-direction:column;gap:3px;}}
  .hs-val{{font-family:'Libre Baskerville',serif;font-size:24px;font-weight:700;color:var(--white);line-height:1;}}
  .hs-key{{font-family:'Space Mono',monospace;font-size:8px;letter-spacing:.15em;text-transform:uppercase;color:rgba(249,247,242,.32);}}

  .page{{max-width:1100px;margin:0 auto;padding:0 40px;}}

  .only-new{{display:flex;gap:18px;align-items:flex-start;background:var(--navy);color:var(--white);padding:22px 26px;margin:32px 0 0;border-left:3px solid var(--gold);}}
  .on-icon{{font-size:18px;flex-shrink:0;margin-top:1px;}}
  .on-label{{font-family:'Space Mono',monospace;font-size:8.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--gold);margin-bottom:6px;}}
  .on-body{{font-size:13px;color:rgba(249,247,242,.75);font-weight:300;line-height:1.75;}}

  .sec{{padding:44px 0 14px;border-bottom:2px solid var(--black);margin-bottom:24px;display:flex;align-items:baseline;justify-content:space-between;gap:16px;}}
  .sec-title{{font-family:'Libre Baskerville',serif;font-size:18px;font-weight:700;}}
  .sec-sub{{font-family:'Space Mono',monospace;font-size:8.5px;color:var(--slate);letter-spacing:.1em;white-space:nowrap;}}

  .tbl-wrap{{overflow-x:auto;border:1px solid var(--rule);margin-bottom:50px;border-radius:2px;}}
  table{{width:100%;border-collapse:collapse;background:var(--card);min-width:860px;}}
  thead{{background:var(--black);}}
  thead th{{font-family:'Space Mono',monospace;font-size:8.5px;letter-spacing:.17em;text-transform:uppercase;color:rgba(249,247,242,.42);padding:12px 16px;text-align:left;font-weight:400;white-space:nowrap;}}
  tbody tr{{border-bottom:1px solid var(--rule);}}
  tbody tr:last-child{{border-bottom:none;}}
  tbody tr:hover{{background:#f2ede5;}}
  td{{padding:16px;vertical-align:top;}}

  .rn{{font-family:'Space Mono',monospace;font-size:9px;color:#ccc;text-align:right;width:28px;padding-right:6px;}}
  .co{{min-width:140px;}}
  .co-name{{font-family:'Libre Baskerville',serif;font-size:15.5px;font-weight:700;display:block;margin-bottom:5px;line-height:1.2;}}
  .badge{{display:inline-block;font-family:'Space Mono',monospace;font-size:7.5px;letter-spacing:.1em;text-transform:uppercase;padding:2px 7px;color:white;border-radius:1px;margin-right:3px;}}
  .b-ai{{background:#0f2545;}}.b-fin{{background:#5a1f0a;}}.b-chip{{background:#2b0d50;}}
  .b-crypto{{background:#1a4a2e;}}.b-social{{background:#4a3200;}}.b-macro{{background:#3a3a3a;}}

  .pill{{display:inline-block;font-family:'Space Mono',monospace;font-size:8px;letter-spacing:.09em;text-transform:uppercase;padding:2px 8px;border:1px solid;border-radius:1px;white-space:nowrap;}}
  .p-ipo{{color:#0f2545;border-color:#8aa8d8;background:#e5eaf3;}}
  .p-acq{{color:#5a1f0a;border-color:#e8a87a;background:#fef0e5;}}
  .p-funding{{color:#0d4f2c;border-color:#98d4b0;background:#e4f0ea;}}
  .p-analysis{{color:#4a3200;border-color:#d4b870;background:#faf4e3;}}

  .date-cell{{font-family:'Space Mono',monospace;font-size:10px;color:var(--slate);white-space:nowrap;min-width:88px;}}
  .val{{font-family:'Space Mono',monospace;font-size:10.5px;display:inline-block;padding:3px 8px;background:#f0ece3;border:1px solid var(--rule);border-radius:2px;white-space:nowrap;}}
  .val-h{{background:var(--red-light);border-color:#e0b0ab;color:var(--red);}}
  .sum{{min-width:280px;max-width:420px;font-size:12.5px;color:#282830;line-height:1.65;}}
  .sum strong{{font-weight:600;color:var(--black);}}

  .src-link{{font-family:'Space Mono',monospace;font-size:10px;color:var(--navy);text-decoration:none;border-bottom:1px solid rgba(15,37,69,.25);display:inline-flex;gap:3px;align-items:center;}}
  .src-link:hover{{color:var(--red);border-color:var(--red);}}
  .src-link::after{{content:'↗';font-size:8.5px;}}
  .new-dot{{display:inline-block;width:6px;height:6px;background:var(--red);border-radius:50%;margin-left:5px;vertical-align:middle;}}

  .ipo-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--rule);border:1px solid var(--rule);margin-bottom:50px;}}
  .ipo-card{{background:var(--card);padding:22px 20px;position:relative;}}
  .ipo-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;}}
  .ipo-card.c1::before{{background:var(--red);}}.ipo-card.c2::before{{background:var(--navy);}}
  .ipo-card.c3::before{{background:var(--green);}}.ipo-card.c4::before{{background:var(--gold);}}
  .ipo-card.c5::before{{background:#5a1f0a;}}.ipo-card.c6::before{{background:#2b0d50;}}
  .ipo-co{{font-family:'Libre Baskerville',serif;font-size:17px;font-weight:700;margin-bottom:3px;}}
  .ipo-status{{font-family:'Space Mono',monospace;font-size:8px;letter-spacing:.12em;text-transform:uppercase;color:var(--slate);margin-bottom:10px;}}
  .ipo-val{{font-family:'Libre Baskerville',serif;font-size:22px;font-weight:700;line-height:1;margin-bottom:4px;}}
  .ipo-detail{{font-size:11.5px;color:var(--slate);line-height:1.6;}}

  .analysis-grid{{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--rule);border:1px solid var(--rule);margin-bottom:50px;}}
  .a-card{{background:var(--card);padding:26px 24px;border-top:3px solid;}}
  .a-card:nth-child(1){{border-color:var(--red);}}.a-card:nth-child(2){{border-color:var(--navy);}}
  .a-tag{{font-family:'Space Mono',monospace;font-size:8px;letter-spacing:.18em;text-transform:uppercase;color:var(--slate);margin-bottom:10px;}}
  .a-card h3{{font-family:'Libre Baskerville',serif;font-size:16.5px;font-weight:700;margin-bottom:10px;line-height:1.3;}}
  .a-card p{{font-size:12.5px;color:#3a3a44;line-height:1.75;}}

  footer{{background:var(--black);padding:22px 40px;display:flex;justify-content:space-between;align-items:center;gap:20px;margin-top:50px;flex-wrap:wrap;}}
  footer span{{font-family:'Space Mono',monospace;font-size:9px;color:rgba(249,247,242,.32);letter-spacing:.04em;}}

  @media(max-width:800px){{header,.page,footer,.ribbon{{padding-left:18px;padding-right:18px;}}
    .ipo-grid{{grid-template-columns:1fr 1fr;}}.analysis-grid{{grid-template-columns:1fr;}}.header-stats{{gap:18px;}}}}
  @media(max-width:520px){{.ipo-grid{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>

<!-- RIBBON -->
<div class="ribbon">
  <span>Private Markets Insider</span>
  <span class="live">&#x2B24; &nbsp;Vol. {vol_number:02d} &middot; {date_str} &middot; New Stories Only</span>
</div>

<!-- HEADER -->
<header>
  <div class="page">
    <div class="vol-tag">{day_name} Edition &middot; Vol. {vol_number:02d}</div>
    <h1>{headline_html}</h1>
    <p class="header-deck">{deck}</p>
    <div class="header-stats">{stats_html}</div>
  </div>
</header>

<!-- ONLY-NEW BANNER -->
<div class="page">
  <div class="only-new">
    <span class="on-icon">&#128203;</span>
    <div>
      <div class="on-label">New Stories Only &mdash; No Repeats</div>
      <p class="on-body">{only_new_text}</p>
    </div>
  </div>
</div>

<!-- DEAL TRACKER -->
{deal_section}

<!-- IPO PIPELINE -->
{ipo_section}

<!-- ANALYST TAKES -->
{analyst_section}

<!-- DEALS & FUNDRAISING -->
{deals_section}

<!-- DISCLAIMER -->
<div class="page">
  <p style="font-size:11px;color:var(--slate);font-family:'Space Mono',monospace;line-height:1.75;margin-bottom:36px;padding:16px;border:1px solid var(--rule);background:#f7f4ee;">
    &#9888; DISCLOSURE: This newsletter is for informational purposes only and does not constitute
    investment advice. All data sourced from cited articles. No information has been invented or
    estimated by the author. Private market valuations are inherently uncertain and may not reflect
    actual exit prices. Consult a qualified financial professional before making any investment decisions.
    <br><br>
    <a href="{unsubscribe_url}" style="color:var(--navy);text-decoration:none;border-bottom:1px solid rgba(15,37,69,.3);">Unsubscribe</a>
  </p>
</div>

<!-- FOOTER -->
<footer>
  <span>Private Markets Insider &middot; Vol. {vol_number:02d} &middot; {date_str}</span>
  <span>New stories only &middot; No repeats from prior editions</span>
  <span>Not investment advice &middot; All sources cited above</span>
</footer>

</body>
</html>"""


def build_plain_text_watchlist_newsletter(
    user_name: str,
    rows: list[dict],
    date_str: str,
    vol_number: int = 1,
    deal_rows: list[dict] | None = None,
) -> str:
    """Plain-text fallback for the watchlist newsletter."""
    lines = [
        f"PRIVATE MARKETS INSIDER — Vol. {vol_number:02d} — {date_str}",
        "=" * 60,
        "",
        f"Good morning, {user_name}. {len(rows)} new update(s) across your watchlist.",
        "",
    ]
    for i, row in enumerate(rows, 1):
        lines += [
            f"{i:02d}. [ {row.get('update_type', 'Update').upper()} ] {row.get('company', '')}",
            f"    Sector:    {row.get('sector', '')}",
            f"    Valuation: {row.get('valuation', 'Not disclosed')}",
            f"    What:      {row.get('description', '')}",
            f"    Update:    {row.get('update', '')}",
            f"    Summary:   {row.get('summary', '')}",
            f"    Date:      {row.get('article_date', '')}  |  {row.get('source', '')}",
            f"    Link:      {row.get('url', '')}",
            "",
        ]

    if deal_rows:
        lines += [
            "",
            "IPOS, EXITS & FUNDRAISING",
            "-" * 60,
            "",
        ]
        for i, deal in enumerate(deal_rows, 1):
            investors = ", ".join(deal.get("lead_investors", [])) or "Not disclosed"
            lines += [
                f"{i:02d}. [ {deal.get('deal_type', 'Fundraise').upper()} ] {deal.get('company', '')}",
                f"    Round:     {deal.get('round', '')}",
                f"    Amount:    {deal.get('amount', 'Not disclosed')}",
                f"    Valuation: {deal.get('valuation', 'Not disclosed')}",
                f"    Lead Inv:  {investors}",
                f"    Pricing:   {deal.get('pricing_notes', '') or 'N/A'}",
                f"    Summary:   {deal.get('summary', '')}",
                f"    Date:      {deal.get('article_date', '')}  |  {deal.get('source', '')}",
                f"    Link:      {deal.get('url', '')}",
                "",
            ]

    lines += ["-" * 60, "Private Markets Insider — Not investment advice — All sources cited above"]
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
