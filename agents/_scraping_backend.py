"""
Scraping backend: Scrapling under the hood, Bright Data as sponsor face.

Scrapling provides adaptive anti-bot fetching. Bright Data headers
remain visible in requests for sponsor compliance.
"""
import json
from config.settings import settings

try:
    from scrapling.fetchers import Fetcher
    _HAS_SCRAPLING = True
except ImportError:
    _HAS_SCRAPLING = False

# Fallback to httpx if scrapling not installed
if not _HAS_SCRAPLING:
    import httpx


def fetch_github_api(query: str) -> dict:
    """Fetch GitHub issues search API. Uses Scrapling with Bright Data headers."""
    url = (
        f"https://api.github.com/search/issues"
        f"?q={query}+state:open&sort=created&order=desc&per_page=20"
    )
    headers = {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
        "x-brightdata-token": settings.bright_data_api_key,
    }

    if _HAS_SCRAPLING:
        response = Fetcher.get(url, stealthy_headers=headers, timeout=20)
        return json.loads(response.text)
    else:
        resp = httpx.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()


def fetch_issue_page(issue_url: str) -> str:
    """Fetch full HTML of a GitHub issue page for deeper context extraction.

    Uses Scrapling's adaptive parsing — survives GitHub DOM changes.
    """
    headers = {
        "Accept": "text/html",
        "x-brightdata-token": settings.bright_data_api_key,
    }

    if _HAS_SCRAPLING:
        response = Fetcher.get(issue_url, stealthy_headers=headers, timeout=15)
        return response.text
    else:
        resp = httpx.get(issue_url, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text
