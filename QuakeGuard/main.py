"""
QuakeGuard AI — Streamlit arayüzü: Folium haritası + sohbet asistanı.
"""

from __future__ import annotations

import re

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

import brain
import data_provider as dp
import geo_helpers

try:
    from streamlit_js_eval import get_geolocation
except ImportError:
    get_geolocation = None


PANIC_PATTERNS = re.compile(
    r"\b(panik|korkuyorum|çok korkuyorum|ölüyorum|ölüceğim|ölücem|ne yapayım|"
    r"deliriyorum|çıldıracağım|nefes alamıyorum|kalbim çok hızlı|titriyorum|"
    r"yardım edin|imdat)\b",
    re.IGNORECASE,
)


def detect_panic(text: str) -> bool:
    return bool(PANIC_PATTERNS.search(text or ""))


def _unwrap_streamlit_js_eval(raw):
    """Bileşen bazen {'value': {...}, 'dataType': 'json'} döner; düz dict bekliyoruz."""
    if raw is None:
        return None
    if isinstance(raw, dict) and raw.get("dataType") == "json" and "value" in raw:
        return raw["value"]
    return raw


def default_map_center(df: pd.DataFrame) -> tuple[float, float]:
    if df is not None and not df.empty:
        return float(df["lat"].mean()), float(df["lon"].mean())
    return 39.0, 35.0


def build_map(
    df: pd.DataFrame,
    user_lat: float | None,
    user_lon: float | None,
    highlight_id: str | None,
) -> folium.Map:
    center = default_map_center(df)
    m = folium.Map(location=list(center), zoom_start=6, tiles="CartoDB positron")

    if df is not None and not df.empty:
        for _, row in df.iterrows():
            eid = str(row.get("earthquake_id") or "")
            is_near = highlight_id and eid == highlight_id
            mag = float(row["magnitude"])
            if is_near:
                color, radius, fill_opacity = "red", 14, 0.95
            elif mag >= 4.5:
                color, radius, fill_opacity = "darkred", 11, 0.85
            elif mag >= 4.0:
                color, radius, fill_opacity = "orange", 9, 0.8
            else:
                color, radius, fill_opacity = "blue", 7, 0.75

            popup = folium.Popup(
                f"<b>{row['location']}</b><br>M{mag}<br>{row['datetime_utc']}<br>"
                f"Derinlik: {row['depth_km']} km",
                max_width=280,
            )
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=fill_opacity,
                popup=popup,
            ).add_to(m)

    if user_lat is not None and user_lon is not None:
        folium.Marker(
            [user_lat, user_lon],
            popup="Sizin konumunuz",
            tooltip="Konumunuz",
            icon=folium.Icon(color="green"),
        ).add_to(m)

    folium.LayerControl().add_to(m)
    return m


def render_quick_actions():
    st.markdown("**Hızlı eylemler**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.link_button("AFAD Resmi Site", "https://www.afad.gov.tr/", use_container_width=True)
    with c2:
        st.link_button("Acil Çağrı 112", "tel:112", use_container_width=True)
    with c3:
        st.link_button("Kızılay", "https://www.kizilay.org.tr/", use_container_width=True)


st.set_page_config(
    page_title="QuakeGuard AI",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ QuakeGuard AI")
st.caption(
    "Canlı deprem verisi + RAG + araç kullanan asistan. "
    "Ücretli: OpenAI. Ücretsiz: `.env` içinde `QUAKEGUARD_FREE=true` ve Groq anahtarı (bkz. `.env.example`). "
    "Harita / en yakın deprem soldaki koordinat veya şehir aramasına göredir."
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "highlight_id" not in st.session_state:
    st.session_state.highlight_id = None
if "quake_df" not in st.session_state:
    st.session_state.quake_df = None
if "lat_input" not in st.session_state:
    st.session_state.lat_input = 39.0
if "lon_input" not in st.session_state:
    st.session_state.lon_input = 35.0
if "geo_poll_key" not in st.session_state:
    st.session_state.geo_poll_key = 0

with st.sidebar:
    # lat_input / lon_input widget'larından önce koordinat uygula (Streamlit kuralı)
    p = st.session_state.pop("_pending_coords_payload", None)
    if isinstance(p, dict) and "lat" in p and "lon" in p:
        st.session_state.lat_input = float(p["lat"])
        st.session_state.lon_input = float(p["lon"])
    msg = st.session_state.pop("_location_success_msg", None)
    if msg:
        st.success(msg)

    st.subheader("Konum")
    if get_geolocation is not None:
        if st.button("Tarayıcı konumumu kullan"):
            st.session_state._geo_waiting = True
            st.session_state.geo_poll_key += 1
            st.rerun()

        if st.session_state.get("_geo_waiting"):
            # İlk turda genelde None; tarayıcı izni + bileşen yanıtı sonrası Streamlit yeniden çalışır
            loc_raw = get_geolocation(component_key=f"quakeguard_geo_{st.session_state.geo_poll_key}")
            loc = _unwrap_streamlit_js_eval(loc_raw)
            gc1, gc2 = st.columns((3, 1))
            with gc2:
                if st.button("İptal", key="geo_wait_cancel"):
                    st.session_state._geo_waiting = False
                    st.rerun()
            with gc1:
                if loc and isinstance(loc, dict):
                    if "error" in loc:
                        err = loc["error"]
                        code = err.get("code")
                        msg = err.get("message", err)
                        st.session_state._geo_waiting = False
                        if code == 1:
                            st.error("Konum izni reddedildi. Adres çubuğundaki konum ikonundan izin verin.")
                        else:
                            st.warning(f"Konum alınamadı ({code}): {msg}")
                    elif "coords" in loc:
                        st.session_state._pending_coords_payload = {
                            "lat": float(loc["coords"]["latitude"]),
                            "lon": float(loc["coords"]["longitude"]),
                        }
                        st.session_state._location_success_msg = "Konum alındı."
                        st.session_state._geo_waiting = False
                        st.rerun()
                    else:
                        st.caption("Konum bekleniyor… Tarayıcıda “Konumu paylaş”ı onaylayın.")
                else:
                    st.caption("Konum bekleniyor… Tarayıcıda “Konumu paylaş”ı onaylayın.")
    else:
        st.info("Konum için `streamlit_js_eval` paketini yükleyin.")

    st.number_input(
        "Enlem (manuel)",
        format="%.6f",
        key="lat_input",
    )
    st.number_input(
        "Boylam (manuel)",
        format="%.6f",
        key="lon_input",
    )

    st.markdown("**Şehirden konum** (OpenStreetMap — API anahtarı gerekmez)")
    st.text_input(
        "Şehir veya adres",
        placeholder="Örn: Edirne  veya  Kadıköy, İstanbul",
        key="geocode_query",
    )
    if st.button("Bu konumu haritada kullan"):
        q = (st.session_state.get("geocode_query") or "").strip()
        if not q:
            st.warning("Önce bir şehir/adres yazın.")
        else:
            try:
                with st.spinner("Konum aranıyor..."):
                    hit = geo_helpers.geocode_place(q)
                if hit is None:
                    st.warning("Sonuç bulunamadı. Daha açık yazmayı deneyin (ör. “Edirne merkez”).")
                else:
                    dn = hit["display_name"]
                    short = dn[:120] + ("…" if len(dn) > 120 else "")
                    st.session_state._pending_coords_payload = {
                        "lat": hit["lat"],
                        "lon": hit["lon"],
                    }
                    st.session_state._location_success_msg = short
                    st.rerun()
            except Exception as e:
                st.error(f"Konum servisi hatası: {e}")

    if st.button("Deprem verisini yenile"):
        st.session_state.quake_df = None
        st.session_state.highlight_id = None
        st.rerun()

    st.divider()
    st.markdown(
        "PDF rehberlerinizi `data/` klasörüne koyun. İndeksi sıfırlamak için: "
        "OpenAI modunda `chroma_db`, ücretsiz modda `chroma_db_local` klasörünü silin."
    )

try:
    if st.session_state.quake_df is None:
        with st.spinner("Deprem verisi yükleniyor..."):
            st.session_state.quake_df = dp.get_latest_earthquakes()
    df = st.session_state.quake_df
except Exception as e:
    st.error(f"Deprem verisi alınamadı: {e}")
    df = pd.DataFrame()

ulat = float(st.session_state.lat_input)
ulon = float(st.session_state.lon_input)
if ulat is not None and ulon is not None and df is not None and not df.empty:
    row, dist_km = dp.nearest_earthquake(ulat, ulon, df)
    if row is not None and dist_km is not None:
        st.session_state.highlight_id = str(row.get("earthquake_id"))
        st.info(f"Konumunuza en yakın deprem (yaklaşık **{dist_km:.1f} km**): **{row['location']}** (M{row['magnitude']}). Haritada kırmızı işaretli.")
else:
    st.session_state.highlight_id = None

left, right = st.columns((1.1, 1.0), gap="large")

with left:
    st.subheader("Son depremler (M > 3.0, ~24 saat)")
    if df is None or df.empty:
        st.warning("Gösterilecek deprem yok veya veri çekilemedi.")
    else:
        st.dataframe(
            df[
                [
                    "datetime_utc",
                    "magnitude",
                    "depth_km",
                    "location",
                    "lat",
                    "lon",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    st_folium(
        build_map(df, ulat, ulon, st.session_state.highlight_id),
        width=None,
        height=480,
        returned_objects=[],
        key="quake_map",
    )

with right:
    st.subheader("Asistan")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    if prompt := st.chat_input("Konumunuzu veya sorunuzu yazın..."):
        panic = detect_panic(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        hist = [
            (m["role"], m["content"])
            for m in st.session_state.messages
            if m["role"] in ("user", "assistant")
        ]

        with st.chat_message("assistant"):
            with st.spinner("QuakeGuard düşünüyor..."):
                reply = brain.run_assistant(
                    prompt,
                    user_lat=ulat,
                    user_lon=ulon,
                    panic_mode=panic,
                    chat_history=hist[:-1],
                )
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    if not st.session_state.messages:
        st.info("Örnek: “İstanbul Kadıköy’deyim, son depremler ve ne yapmalıyım?”")
    render_quick_actions()
