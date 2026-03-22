"""
Ücretsiz adres / şehir → koordinat (OpenStreetMap Nominatim).
Kullanım politikası: düşük frekans, anlamlı User-Agent.
"""

from __future__ import annotations

from typing import Any

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "QuakeGuardAI/1.0 (education; contact: local)"


def geocode_place(query: str, *, country_code: str = "tr") -> dict[str, Any] | None:
    q = (query or "").strip()
    if len(q) < 2:
        return None
    params = {
        "q": q,
        "format": "json",
        "limit": 1,
        "countrycodes": country_code.lower(),
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "tr"}
    r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data:
        return None
    hit = data[0]
    return {
        "lat": float(hit["lat"]),
        "lon": float(hit["lon"]),
        "display_name": hit.get("display_name") or q,
    }
