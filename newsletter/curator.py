"""
Article curation: fetches articles from RSS feeds mapped to user interest categories.

Uses Python's built-in xml.etree.ElementTree + urllib so there are no extra
dependencies for feed parsing.

Inspired by newsletters like TLDR, Morning Brew, and 1440 Daily Digest — which pull
from authoritative, varied sources and surface the most-shared/engaged stories.
"""
import logging
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RSS feed registry  –  category slug → list of feed URLs
# ---------------------------------------------------------------------------
CATEGORY_FEEDS: dict[str, list[str]] = {
    "technology": [
        "https://feeds.feedburner.com/TechCrunch/",
        "https://feeds.arstechnica.com/arstechnica/index",
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://hnrss.org/frontpage",
    ],
    "business": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://fortune.com/feed/",
        "https://feeds.feedburner.com/entrepreneur/latest",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://phys.org/rss-feed/",
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
    ],
    "world-news": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/Reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "ai-ml": [
        "https://venturebeat.com/category/ai/feed/",
        "https://www.technologyreview.com/feed/",
        "https://feeds.feedburner.com/nvidiablog",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ],
    "health": [
        "https://www.medicalnewstoday.com/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "https://www.nih.gov/rss/newsreleases/newsreleases.xml",
    ],
    "startups": [
        "https://feeds.feedburner.com/TechCrunch/startups",
        "https://venturebeat.com/feed/",
        "https://www.inc.com/rss",
    ],
    "environment": [
        "https://www.theguardian.com/environment/rss",
        "https://insideclimatenews.org/feed/",
        "https://e360.yale.edu/feed",
    ],
    "sports": [
        "https://feeds.bbci.co.uk/sport/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Sports.xml",
    ],
    "culture": [
        "https://www.theguardian.com/culture/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Arts.xml",
        "https://www.theatlantic.com/feed/all/",
    ],
    "politics": [
        "https://feeds.reuters.com/Reuters/PoliticsNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "https://thehill.com/rss/syndicator/19110",
    ],
    "space": [
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://spacenews.com/feed/",
        "https://www.space.com/feeds/all",
    ],
}

NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
MAX_ARTICLE_AGE_HOURS = 48
_HEADERS = {"User-Agent": "MyDailyBrief/1.0 (+https://github.com/example/mydailbrief)"}

# XML namespaces commonly used in RSS/Atom feeds
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc":   "http://purl.org/dc/elements/1.1/",
    "media":"http://search.yahoo.com/mrss/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    # Try RFC 2822 (RSS), then ISO 8601 (Atom)
    for fn in (parsedate_to_datetime, lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))):
        try:
            dt = fn(date_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def _fetch_xml(url: str) -> ET.Element | None:
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        return ET.fromstring(data)
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return None


def _parse_rss_channel(root: ET.Element, feed_url: str) -> tuple[str, list[dict]]:
    """Parse RSS 2.0 format. Returns (source_name, articles)."""
    channel = root.find("channel")
    if channel is None:
        return feed_url, []

    source = channel.findtext("title") or feed_url
    articles = []

    for item in channel.findall("item"):
        title = item.findtext("title", "").strip()
        link  = item.findtext("link", "").strip()
        if not title or not link:
            continue

        summary = (
            item.findtext("description", "")
            or item.findtext(f"{{{_NS['content']}}}encoded", "")
            or ""
        )
        date_str = item.findtext("pubDate") or item.findtext(f"{{{_NS['dc']}}}date")
        published = _parse_date(date_str)

        articles.append({
            "title": title,
            "url": link,
            "summary": _strip_html(summary)[:500],
            "source": source,
            "published": published.isoformat() if published else None,
            "published_dt": published,
        })

    return source, articles


def _parse_atom_feed(root: ET.Element, feed_url: str) -> tuple[str, list[dict]]:
    """Parse Atom 1.0 format. Returns (source_name, articles)."""
    ns = _NS["atom"]
    source = root.findtext(f"{{{ns}}}title") or feed_url
    articles = []

    for entry in root.findall(f"{{{ns}}}entry"):
        title = (entry.findtext(f"{{{ns}}}title") or "").strip()
        # <link> in Atom uses 'href' attribute
        link_el = entry.find(f"{{{ns}}}link[@rel='alternate']") or entry.find(f"{{{ns}}}link")
        link = (link_el.get("href", "") if link_el is not None else "").strip()
        if not title or not link:
            continue

        summary = (
            entry.findtext(f"{{{ns}}}summary")
            or entry.findtext(f"{{{ns}}}content")
            or ""
        )
        date_str = entry.findtext(f"{{{ns}}}updated") or entry.findtext(f"{{{ns}}}published")
        published = _parse_date(date_str)

        articles.append({
            "title": title,
            "url": link,
            "summary": _strip_html(summary)[:500],
            "source": source,
            "published": published.isoformat() if published else None,
            "published_dt": published,
        })

    return source, articles


def _parse_feed(url: str, max_articles: int = 10) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS or Atom feed."""
    root = _fetch_xml(url)
    if root is None:
        return []

    tag = root.tag.lower()
    if "feed" in tag or root.tag.startswith(f"{{{_NS['atom']}}}"):
        source, articles = _parse_atom_feed(root, url)
    else:
        source, articles = _parse_rss_channel(root, url)

    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=MAX_ARTICLE_AGE_HOURS)
    fresh = [
        a for a in articles
        if not a["published_dt"] or a["published_dt"] >= cutoff
    ]
    return fresh[:max_articles]


def fetch_articles_for_categories(
    category_slugs: list[str],
    articles_per_category: int = 6,
    news_api_key: str = "",
) -> list[dict[str, Any]]:
    """
    Fetch articles for the given interest categories.
    Returns a deduplicated, recency-sorted list.
    """
    seen_urls: set[str] = set()
    all_articles: list[dict[str, Any]] = []

    for slug in category_slugs:
        feeds = CATEGORY_FEEDS.get(slug, [])
        cat_articles: list[dict[str, Any]] = []

        for feed_url in feeds:
            articles = _parse_feed(feed_url, max_articles=5)
            for art in articles:
                if art["url"] and art["url"] not in seen_urls:
                    seen_urls.add(art["url"])
                    art["category"] = slug
                    cat_articles.append(art)
            if len(cat_articles) >= articles_per_category:
                break

        all_articles.extend(cat_articles[:articles_per_category])

    # Optional NewsAPI augmentation
    if news_api_key and category_slugs:
        try:
            all_articles.extend(_fetch_newsapi(category_slugs, news_api_key, seen_urls))
        except Exception as exc:
            logger.warning("NewsAPI fetch failed: %s", exc)

    # Sort by recency
    all_articles.sort(
        key=lambda a: a.get("published_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    for art in all_articles:
        art.pop("published_dt", None)

    return all_articles


def _fetch_newsapi(
    category_slugs: list[str],
    api_key: str,
    seen_urls: set[str],
) -> list[dict[str, Any]]:
    newsapi_map = {
        "technology": "technology",
        "business": "business",
        "science": "science",
        "health": "health",
        "sports": "sports",
    }
    articles: list[dict[str, Any]] = []
    queried: set[str] = set()

    for slug in category_slugs:
        cat = newsapi_map.get(slug)
        if not cat or cat in queried:
            continue
        queried.add(cat)
        try:
            resp = requests.get(
                NEWS_API_URL,
                params={"category": cat, "language": "en", "pageSize": 5, "apiKey": api_key},
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            for item in resp.json().get("articles", []):
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    articles.append({
                        "title": item.get("title", ""),
                        "url": url,
                        "summary": item.get("description", "") or "",
                        "source": item.get("source", {}).get("name", "NewsAPI"),
                        "published": item.get("publishedAt"),
                        "category": slug,
                    })
        except Exception as exc:
            logger.warning("NewsAPI error for %s: %s", cat, exc)

    return articles


# ---------------------------------------------------------------------------
# Deals & fundraising feed fetching
# ---------------------------------------------------------------------------

# RSS feeds that consistently break IPO filings, fundraising rounds, and M&A exits
DEAL_FEEDS: list[str] = [
    # TechCrunch dedicated funding / M&A tags
    "https://techcrunch.com/tag/funding/feed/",
    "https://techcrunch.com/tag/mergers-acquisitions/feed/",
    "https://techcrunch.com/tag/ipo/feed/",
    # Crunchbase News
    "https://news.crunchbase.com/feed/",
    # VentureBeat funding
    "https://venturebeat.com/category/business/feed/",
    # Reuters M&A + business wire
    "https://feeds.reuters.com/reuters/businessNews",
    # PR Newswire funding / IPO press releases
    "https://www.prnewswire.com/rss/news-releases-list.rss",
    # Axios (free RSS limited, but worth trying)
    "https://api.axios.com/feed/",
    # Fortune
    "https://fortune.com/feed/",
]

# Keywords that identify genuine deal articles (used to score/filter)
_DEAL_KEYWORDS = (
    "raises", "funding", "IPO", "files for", "goes public", "acqui", "merger",
    "acquisition", "Series A", "Series B", "Series C", "Series D", "Series E",
    "valuation", "unicorn", "round", "investment", "capital", "exit",
    "secondary", "SPAC", "listing", "priced", "per share",
)


def fetch_deals_news(max_articles: int = 20) -> list[dict[str, Any]]:
    """
    Fetch recent deal-relevant articles from curated financial / VC feeds.
    Returns a recency-sorted, deduplicated list of article dicts, pre-filtered
    to articles whose title or snippet contain deal-related keywords.
    """
    seen_urls: set[str] = set()
    all_articles: list[dict[str, Any]] = []

    for feed_url in DEAL_FEEDS:
        try:
            for art in _parse_feed(feed_url, max_articles=8):
                url = art.get("url", "")
                if not url or url in seen_urls:
                    continue
                text = (art.get("title", "") + " " + art.get("summary", "")).lower()
                if any(kw.lower() in text for kw in _DEAL_KEYWORDS):
                    seen_urls.add(url)
                    all_articles.append(art)
        except Exception as exc:
            logger.debug("Deal feed failed (%s): %s", feed_url, exc)

    all_articles.sort(
        key=lambda a: a.get("published_dt") or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    for art in all_articles:
        art.pop("published_dt", None)

    return all_articles[:max_articles]


# ---------------------------------------------------------------------------
# Company watchlist fetching
# ---------------------------------------------------------------------------

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

# Investor-relevant keywords to bias search results toward business news
_INVESTOR_KEYWORDS = "funding OR valuation OR IPO OR acquisition OR revenue OR growth OR investment OR raises"


def fetch_articles_for_companies(
    company_names: list[str],
    max_per_company: int = 8,
    news_api_key: str = "",
) -> dict[str, list[dict[str, Any]]]:
    """
    Fetch recent news articles for each company in the watchlist.
    Returns a dict mapping company name → list of article dicts.
    Uses Google News RSS (free, no key required) plus optional NewsAPI.
    """
    results: dict[str, list[dict[str, Any]]] = {}

    for company in company_names:
        articles: list[dict[str, Any]] = []
        seen: set[str] = set()

        # Primary: investor-focused Google News search
        investor_query = urllib.parse.quote(f'"{company}" ({_INVESTOR_KEYWORDS})')
        investor_url = GOOGLE_NEWS_RSS.format(query=investor_query)
        for art in _parse_feed(investor_url, max_articles=max_per_company):
            url = art.get("url", "")
            if url and url not in seen:
                seen.add(url)
                art["company"] = company
                articles.append(art)

        # Fallback: broader company name search if we didn't get enough
        if len(articles) < 3:
            general_query = urllib.parse.quote(f'"{company}" private company')
            general_url = GOOGLE_NEWS_RSS.format(query=general_query)
            for art in _parse_feed(general_url, max_articles=max_per_company):
                url = art.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    art["company"] = company
                    articles.append(art)

        # Optional: NewsAPI everything endpoint for company-specific search
        if news_api_key and len(articles) < max_per_company:
            try:
                resp = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": f'"{company}"',
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                        "apiKey": news_api_key,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("articles", []):
                        url = item.get("url", "")
                        if url and url not in seen:
                            seen.add(url)
                            articles.append({
                                "title": item.get("title", ""),
                                "url": url,
                                "summary": item.get("description", "") or "",
                                "source": item.get("source", {}).get("name", "NewsAPI"),
                                "published": item.get("publishedAt", ""),
                                "company": company,
                            })
            except Exception as exc:
                logger.warning("NewsAPI company search failed for %s: %s", company, exc)

        # Sort by recency, clean up internal datetime field
        articles.sort(
            key=lambda a: a.get("published_dt") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        for art in articles:
            art.pop("published_dt", None)

        results[company] = articles[:max_per_company]

    return results
