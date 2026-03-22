<div align="center">

# 🛡️ QuakeGuard AI

**Türkiye odaklı deprem güvenlik asistanı**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

Canlı deprem verisi (Kandilli kaynaklı API) · RAG ile güvenlik rehberi · Araç kullanan sohbet asistanı

</div>

---

## 📌 Genel Bakış

QuakeGuard AI; **Kandilli Rasathanesi** verilerini gerçek zamanlı olarak çekerek depremleri haritada gösterir, PDF/TXT güvenlik rehberlerini ChromaDB vektör veritabanında indeksler ve LangChain ajanı aracılığıyla kullanıcıya akıllı yanıtlar sunar.

---

## ✨ Özellikler

| # | Özellik | Detay |
|---|---------|-------|
| 🗺️ | **Canlı Harita** | Son ~24 saatte M > 3.0 depremleri tablo ve Folium haritasında gösterir |
| 🔍 | **RAG Motoru** | ChromaDB ile PDF/TXT rehberlerden anlık vektör arama |
| 🤖 | **LangChain Ajanı** | Güncel depremler, risk özeti ve protokol araması yapabilir |
| 📍 | **Konum Desteği** | Tarayıcı konumu veya şehir/adres girişi (OpenStreetMap Nominatim) |
| 🧘 | **Panik Modu** | Panik ifadelerini algılayarak yatıştırıcı yanıt verir |
| 🚨 | **Hızlı Bağlantılar** | AFAD · 112 · Kızılay tek tıkla erişim |

---

## 🔧 Gereksinimler

- **Python 3.10+**
- Sohbet + RAG için aşağıdakilerden **biri**:

  | | Sağlayıcı | Maliyet | Notlar |
  |-|-----------|---------|--------|
  | ✅ | [Groq](https://console.groq.com/keys) + yerel embedding | **Ücretsiz** | İlk çalıştırmada model indirilir |
  | 💳 | [OpenAI](https://platform.openai.com/api-keys) | Ücretli | GPT-4o desteklenir |

---

## 🚀 Kurulum

```bash
git clone <repo-url>
cd QuakeGuard
python -m venv .venv
```

<details>
<summary><b>🪟 Windows (PowerShell)</b></summary>

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

</details>

<details>
<summary><b>🐧 Linux / macOS</b></summary>

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

</details>

---

## ⚙️ Ortam Değişkenleri

`.env.example` dosyasını `.env` olarak kopyalayıp doldurun:

```bash
cp .env.example .env
```

<details>
<summary><b>Seçenek A — OpenAI (Ücretli)</b></summary>

```env
OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o
```

</details>

<details>
<summary><b>Seçenek B — Groq + Yerel Embedding (Ücretsiz)</b></summary>

```env
QUAKEGUARD_FREE=true
GROQ_API_KEY=gsk_...
# GROQ_MODEL=llama-3.3-70b-versatile
```

</details>

> [!TIP]
> Mod değiştirdiğinizde indeks karışmaması için `chroma_db` veya `chroma_db_local` klasörünü silebilirsiniz.

---

## ▶️ Çalıştırma

```powershell
.\.venv\Scripts\streamlit run main.py
```

Uygulama varsayılan olarak şu adreste açılır: **`http://localhost:8501`**

---

## 📁 Klasör Yapısı

```
QuakeGuard/
├── 📄 .env                  # Yerelde oluşturun — Git'e eklemeyin!
├── 🖥️  main.py               # Streamlit arayüzü
├── ⚙️  config.py             # QUAKEGUARD_FREE ve diğer ayarlar
├── 🌍 data_provider.py      # Kandilli deprem verisi API
├── 🔍 rag_engine.py         # Chroma + embedding motoru
├── 🤖 brain.py              # LangChain ajanı
├── 📍 geo_helpers.py        # Şehir → koordinat (Nominatim)
├── 📂 data/                 # PDF / TXT güvenlik rehberleri
├── 📋 requirements.txt
└── 📖 README.md
```

---

## 🗄️ Veri Kaynakları

- **Canlı deprem listesi:** [orhanaydogdu Kandilli live API](https://api.orhanaydogdu.com.tr/deprem/kandilli/live) — herkese açık, ek anahtar gerekmez
- **Bilgi bankası:** `data/` klasörüne kendi PDF/TXT dosyalarınızı ekleyin *(örnek içerik projede mevcut)*

---

## 🔒 GitHub'a Yüklerken

> [!WARNING]
> **`.env` dosyasını asla commit etmeyin.** API anahtarlarınız sızdırılabilir.

Aşağıdaki klasörler `.gitignore` ile dışarıda bırakılmalıdır:

```
.env
chroma_db/
chroma_db_local/
.venv/
```

---

## ⚠️ Sorumluluk Reddi

Bu proje **eğitim ve prototip** amaçlıdır. Deprem ve afet kararları için **AFAD**, yerel yönetim ve resmi kurum duyurularını esas alın. Uygulama tıbbi veya hukuki tavsiye vermez.

---

## 📄 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır.

---

<div align="center">

Türkiye'nin deprem güvenliği için 🇹🇷 ile yapıldı

**[AFAD](https://www.afad.gov.tr)** · **[112](tel:112)** · **[Kızılay](https://www.kizilay.org.tr)**

</div>
