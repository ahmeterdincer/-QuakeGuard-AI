"""
LangChain araç kullanan QuakeGuard asistanı.
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

import config
import data_provider as dp
import rag_engine

load_dotenv()


@tool
def get_latest_earthquakes() -> str:
    """Kandilli canlı verisinden son 24 saatte magnitüdü 3.0'dan büyük depremleri getirir."""
    df = dp.get_latest_earthquakes()
    if df.empty:
        return "Kriterlere uyan deprem kaydı bulunamadı (son 24 saat, M>3.0)."
    lines = []
    for _, r in df.head(20).iterrows():
        lines.append(
            f"- {r['location']} | M{r['magnitude']} | {r['datetime_utc']} | "
            f"derinlik {r['depth_km']} km | enlem {r['lat']:.4f} boylam {r['lon']:.4f}"
        )
    return "\n".join(lines)


@tool
def search_safety_protocols(query: str) -> str:
    """AFAD/Kızılay tarzı deprem güvenlik rehberi parçalarını vektör veri tabanında arar. Soru veya anahtar kelime ver."""
    return rag_engine.search_safety_protocols(query, k=4)


@tool
def calculate_risk(
    user_latitude: float,
    user_longitude: float,
    epicenter_latitude: float,
    epicenter_longitude: float,
    magnitude: float,
) -> str:
    """Kullanıcı konumu ile deprem merkezi arasındaki mesafeye ve magnitüde göre basit risk özetini hesaplar."""
    dist = dp.haversine_km(user_latitude, user_longitude, epicenter_latitude, epicenter_longitude)
    info = dp.risk_from_distance_and_magnitude(dist, magnitude)
    return json.dumps(info, ensure_ascii=False)


TOOLS = [get_latest_earthquakes, search_safety_protocols, calculate_risk]


def _build_system_prompt(
    *,
    user_lat: float | None,
    user_lon: float | None,
    panic_mode: bool,
) -> str:
    base = """Sen QuakeGuard AI — Türkiye odaklı deprem güvenlik asistanısın.
Her zaman Türkçe, net ve uygulanabilir yanıt ver.
Önce güvenlik: resmi AFAD/Kızılay/112 hatlarını hatırlat; kesin deprem tahmini yapma.
Araçları kullan: güncel depremler için get_latest_earthquakes, protokol için search_safety_protocols,
mesafe ve büyüklük varsa calculate_risk.
Kullanıcı konumu verilmişse yakın depremleri ve riski özelleştir."""
    if user_lat is not None and user_lon is not None:
        base += f"\nKullanıcının bildirdiği konum (yaklaşık): enlem {user_lat}, boylam {user_lon}."
    if panic_mode:
        base += (
            "\nKullanıcı panik/yoğun kaygı sinyali veriyor: sakin, kısa cümleler, yatıştırıcı ve yönlendirici ol; "
            "önce güvenli davranış adımlarını söyle, sonra detay."
        )
    return base


def _history_to_messages(history: list[tuple[str, str]] | None) -> list[BaseMessage]:
    if not history:
        return []
    out: list[BaseMessage] = []
    for role, content in history[-10:]:
        if role == "user":
            out.append(HumanMessage(content=content))
        elif role == "assistant":
            out.append(AIMessage(content=content))
    return out


def _make_chat_model(model: str | None) -> tuple[BaseChatModel | None, str | None]:
    """
    (llm, hata_mesajı). hata_mesajı doluysa llm None.
    Ücretsiz mod: QUAKEGUARD_FREE=true + GROQ_API_KEY (https://console.groq.com/keys)
    """
    if config.is_free_mode():
        groq_key = os.getenv("GROQ_API_KEY", "").strip()
        if not groq_key:
            return None, (
                "**Ücretsiz mod:** `.env` dosyasına `QUAKEGUARD_FREE=true` ve `GROQ_API_KEY=...` ekleyin. "
                "Groq anahtarı ücretsiz: https://console.groq.com/keys — "
                "İlk RAG kullanımında HuggingFace embedding modeli indirilebilir (~420 MB)."
            )
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            return None, "`langchain-groq` yüklü değil. Çalıştırın: `pip install langchain-groq`"

        m = (model or os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")).strip()
        llm = ChatGroq(api_key=groq_key, model=m, temperature=0.2)
        return llm, None

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, (
            "**OpenAI anahtarı yok.** `.env` içine `OPENAI_API_KEY=...` ekleyin "
            "veya ücretsiz kullanım için `QUAKEGUARD_FREE=true` ve `GROQ_API_KEY=...` kullanın."
        )

    llm = ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o"),
        temperature=0.2,
    )
    return llm, None


def run_assistant(
    user_message: str,
    *,
    user_lat: float | None = None,
    user_lon: float | None = None,
    panic_mode: bool = False,
    chat_history: list[tuple[str, str]] | None = None,
    model: str | None = None,
) -> str:
    llm, err = _make_chat_model(model)
    if err or llm is None:
        return err or "Model oluşturulamadı."

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_prompt}"),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_tool_calling_agent(llm, TOOLS, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=TOOLS,
        verbose=False,
        max_iterations=8,
        handle_parsing_errors=True,
    )

    system_prompt = _build_system_prompt(
        user_lat=user_lat,
        user_lon=user_lon,
        panic_mode=panic_mode,
    )

    try:
        result: dict[str, Any] = executor.invoke(
            {
                "system_prompt": system_prompt,
                "input": user_message,
                "chat_history": _history_to_messages(chat_history),
            }
        )
        return str(result.get("output") or "").strip() or "Yanıt üretilemedi."
    except Exception as e:
        return _friendly_assistant_error(e)


def _friendly_assistant_error(exc: BaseException) -> str:
    raw = f"{type(exc).__name__}: {exc}"
    low = raw.lower()
    if "insufficient_quota" in low or ("429" in raw and "quota" in low):
        return (
            "**OpenAI kotası / bakiye:** Kredi/limit yetersiz (429). "
            "[Faturalandırma](https://platform.openai.com/account/billing) — "
            "veya `.env` ile ücretsiz yığın: `QUAKEGUARD_FREE=true` ve `GROQ_API_KEY` "
            "(Groq: https://console.groq.com/keys)."
        )
    if "groq" in low and ("403" in raw or "invalid" in low or "api key" in low):
        return "**Groq API anahtarı:** `GROQ_API_KEY` değerini https://console.groq.com/keys adresinden kontrol edin."
    if "401" in raw or "invalid_api_key" in low or "incorrect api key" in low:
        return (
            "**API anahtarı geçersiz:** `.env` içindeki `OPENAI_API_KEY` değerini kontrol edin; "
            "başta/sonda boşluk veya tırnak olmamalı."
        )
    if "rate_limit" in low or ("429" in raw and "quota" not in low):
        return (
            "**Çok sık istek (rate limit):** Bir süre bekleyip tekrar deneyin veya OpenAI plandaki dakikalık limiti kontrol edin."
        )
    return f"Asistan hatası: {exc}"
