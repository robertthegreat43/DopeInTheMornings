"""Keyless ESPN RSS-backed news endpoints for the dashboards and tickers."""

import html
import re
import xml.etree.ElementTree as ET

import requests
from django.core.cache import cache
from django.http import JsonResponse


FEEDS = {
    "nfl": "https://www.espn.com/espn/rss/nfl/news",
    "nba": "https://www.espn.com/espn/rss/nba/news",
}
CACHE_SECONDS = 300


def _plain_text(value):
    value = re.sub(r"<[^>]*>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def _fetch_articles(league):
    cache_key = f"sports_news_{league}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    response = requests.get(
        FEEDS[league],
        timeout=8,
        headers={"User-Agent": "DopeInTheMornings/1.0 (sports news reader)"},
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)

    articles = []
    for item in root.findall(".//item")[:25]:
        title = _plain_text(item.findtext("title"))
        url = (item.findtext("link") or "").strip()
        if not title or not url.startswith(("https://", "http://")):
            continue
        articles.append({
            "title": title,
            "source": "ESPN",
            "snippet": _plain_text(item.findtext("description")),
            "url": url,
        })

    cache.set(cache_key, articles, CACHE_SECONDS)
    return articles


def _news_response(league, format_name="news"):
    try:
        articles = _fetch_articles(league)
    except (requests.RequestException, ET.ParseError, ValueError) as exc:
        return JsonResponse({"error": f"Could not load {league.upper()} news: {exc}"}, status=502)

    if format_name == "ticker":
        return JsonResponse({
            "ticker": [
                {"title": article["title"], "snippet": article["snippet"],
                 "link": article["url"], "source": article["source"]}
                for article in articles
            ]
        })
    return JsonResponse({"news": articles})


def get_nfl_news(request):
    return _news_response("nfl")


def get_nba_news(request):
    return _news_response("nba")


def get_nfl_ticker(request):
    return _news_response("nfl", "ticker")


def get_nba_ticker(request):
    return _news_response("nba", "ticker")
