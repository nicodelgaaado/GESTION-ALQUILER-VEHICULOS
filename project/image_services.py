import json
import os
from functools import lru_cache
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USER_AGENT = os.getenv("FLEETFLOW_IMAGE_USER_AGENT", "FleetFlow/1.0 (+local-demo)")


def _fetch_json(url, headers=None, timeout=12):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return None


def _static_fallback():
    return {
        "url": "/static/images/placeholder-vehicle.svg",
        "source": "static",
        "credit": "",
    }


@lru_cache(maxsize=128)
def _wikidata_label(query):
    params = urlencode(
        {
            "action": "wbsearchentities",
            "search": query,
            "language": "en",
            "limit": 1,
            "format": "json",
            "origin": "*",
        }
    )
    data = _fetch_json(f"https://www.wikidata.org/w/api.php?{params}")
    if not data:
        return "", ""
    match = (data.get("search") or [{}])[0]
    display = match.get("display") or {}
    label = ((display.get("label") or {}).get("value") or "").strip()
    description = ((display.get("description") or {}).get("value") or "").strip()
    return label, description


@lru_cache(maxsize=128)
def _commons_image(query):
    params = urlencode(
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": 6,
            "gsrlimit": 1,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 900,
            "format": "json",
            "origin": "*",
        }
    )
    data = _fetch_json(f"https://commons.wikimedia.org/w/api.php?{params}")
    if not data:
        return None
    pages = (data.get("query") or {}).get("pages") or {}
    if not pages:
        return None
    page = next(iter(pages.values()))
    image_info = (page.get("imageinfo") or [{}])[0]
    return {
        "url": image_info.get("thumburl") or image_info.get("url"),
        "source": "wikimedia_commons",
        "credit": page.get("title", "").replace("File:", ""),
    }


def _evox_image(make, model, year):
    base_url = os.getenv("EVOX_IMAGES_BASE_URL", "").strip()
    if not base_url:
        return None

    params = urlencode({"make": make, "model": model, "year": year or ""})
    headers = {}
    api_key = os.getenv("EVOX_IMAGES_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = _fetch_json(f"{base_url}?{params}", headers=headers)
    if not data:
        return None
    candidates = data.get("results") or data.get("vehicles") or data.get("images") or []
    if not candidates:
        return None
    first = candidates[0]
    url = (
        first.get("image_url")
        or first.get("url")
        or first.get("thumbnail")
        or first.get("hero")
    )
    if not url:
        return None
    return {"url": url, "source": "evox", "credit": "EVOX Images"}


def _unsplash_image(query):
    access_key = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    if not access_key:
        return None

    params = urlencode({"query": query, "page": 1, "per_page": 1, "orientation": "landscape"})
    data = _fetch_json(
        f"https://api.unsplash.com/search/photos?{params}",
        headers={"Authorization": f"Client-ID {access_key}", "Accept-Version": "v1"},
    )
    if not data:
        return None
    first = (data.get("results") or [{}])[0]
    urls = first.get("urls") or {}
    user = first.get("user") or {}
    if not urls:
        return None
    return {
        "url": urls.get("regular") or urls.get("small") or urls.get("raw"),
        "source": "unsplash",
        "credit": user.get("name") or "Unsplash",
    }


@lru_cache(maxsize=128)
def vehicle_image_asset(make, model, year=None, category=None, fallback_seed=None):
    evox_match = _evox_image(make, model, year)
    if evox_match:
        return evox_match

    canonical_query = " ".join(part for part in [make, model] if part).strip()
    label, description = _wikidata_label(canonical_query)
    commons_queries = [
        " ".join(part for part in [label or canonical_query, "car"] if part).strip(),
        " ".join(part for part in [make, model, str(year or ""), "car"] if part).strip(),
        " ".join(part for part in [make, model, category or "", "vehicle"] if part).strip(),
        " ".join(part for part in [description, make] if part).strip(),
    ]
    for query in commons_queries:
        if not query:
            continue
        commons_match = _commons_image(query)
        if commons_match and commons_match.get("url"):
            return commons_match

    unsplash_match = _unsplash_image(" ".join(part for part in [make, model, "car"] if part))
    if unsplash_match:
        return unsplash_match

    return _static_fallback()
