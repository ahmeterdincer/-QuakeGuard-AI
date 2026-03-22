"""
Kandilli kaynaklı canlı deprem verisi (orhanaydogdu API).
3.0'dan büyük (mag > 3.0) olayları son 24 saat penceresinde döndürür.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

import pandas as pd
import requests

KANDILLI_LIVE_URL = "https://api.orhanaydogdu.com.tr/deprem/kandilli/live"
MIN_MAGNITUDE = 3.0
REQUEST_TIMEOUT = 25


def _parse_datetime(s: str | None) -> datetime | None:
    """Kandilli API tarih alanı genelde Europe/Istanbul yerel saatidir."""
    if not s:
        return None
    tz_ist = ZoneInfo("Europe/Istanbul")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=tz_ist)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def fetch_raw_earthquakes() -> list[dict[str, Any]]:
    r = requests.get(KANDILLI_LIVE_URL, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("status"):
        raise RuntimeError(payload.get("desc") or "API status false")
    return list(payload.get("result") or [])


def earthquakes_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=24)

    for row in rows:
        mag = float(row.get("mag") or 0)
        if mag <= MIN_MAGNITUDE:
            continue
        gj = row.get("geojson") or {}
        coords = gj.get("coordinates") or []
        if len(coords) < 2:
            continue
        lon, lat = float(coords[0]), float(coords[1])
        dt = _parse_datetime(row.get("date_time"))
        if dt is not None and dt < cutoff:
            continue
        records.append(
            {
                "earthquake_id": row.get("earthquake_id"),
                "datetime_utc": dt.isoformat() if dt else row.get("date_time"),
                "magnitude": mag,
                "depth_km": float(row.get("depth") or 0),
                "lon": lon,
                "lat": lat,
                "location": row.get("title") or "",
                "provider": row.get("provider") or "kandilli",
            }
        )

    df = pd.DataFrame.from_records(records)
    if df.empty:
        return df
    return df.sort_values("datetime_utc", ascending=False).reset_index(drop=True)


def get_latest_earthquakes() -> pd.DataFrame:
    return earthquakes_to_dataframe(fetch_raw_earthquakes())


def nearest_earthquake(
    user_lat: float,
    user_lon: float,
    df: pd.DataFrame,
) -> tuple[pd.Series | None, float | None]:
    if df is None or df.empty:
        return None, None
    best_idx = None
    best_km = None
    for idx, row in df.iterrows():
        d = haversine_km(user_lat, user_lon, float(row["lat"]), float(row["lon"]))
        if best_km is None or d < best_km:
            best_km = d
            best_idx = idx
    if best_idx is None:
        return None, None
    return df.loc[best_idx], float(best_km)


def risk_from_distance_and_magnitude(distance_km: float, magnitude: float) -> dict[str, Any]:
    """
    Basit sezgisel risk skoru (bilgilendirme amaçlı; bilimsel tahmin değildir).
    """
    if distance_km < 0 or magnitude <= 0:
        return {"level": "bilinmiyor", "score": 0.0, "note": "Geçersiz girdi."}

    # Mesafe ve büyüklüğe göre kabaca ağırlık
    dist_factor = max(0.0, 1.0 - min(distance_km, 500.0) / 500.0)
    mag_factor = min(1.0, max(0.0, (magnitude - 3.0) / 5.0))
    score = round(0.55 * mag_factor + 0.45 * dist_factor, 3)

    if score >= 0.75:
        level = "yüksek"
    elif score >= 0.45:
        level = "orta"
    else:
        level = "düşük"

    return {
        "level": level,
        "score": score,
        "distance_km": round(distance_km, 2),
        "magnitude": magnitude,
        "note": "Tahmini relative risk; resmi kurum duyurularını esas alın.",
    }
