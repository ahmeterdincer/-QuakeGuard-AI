# QuakeGuard AI

Türkiye odaklı **deprem güvenlik asistanı**: canlı deprem verisi (Kandilli kaynaklı API), RAG ile güvenlik rehberi ve araç kullanan sohbet asistanı. Arayüz **Streamlit**, harita **Folium**.

## Özellikler

- Son ~24 saatte **M > 3.0** depremleri tablo ve haritada gösterme  
- **ChromaDB** ile PDF/TXT rehberlerden vektör arama (RAG)  
- **LangChain** ajanı: güncel depremler, risk özeti, protokol araması  
- Tarayıcı konumu veya **şehir/adres** ile konum (OpenStreetMap Nominatim)  
- İsteğe bağlı **panik** ifadelerinde yatıştırıcı yanıt modu  
- AFAD / 112 / Kızılay hızlı bağlantıları  

## Gereksinimler

- Python 3.10+  
- **Sohbet + RAG** için aşağıdakilerden biri:  
  - **Ücretsiz:** [Groq](https://console.groq.com/keys) API anahtarı + yerel embedding (ilk çalıştırmada model indirir)  
  - **Ücretli:** [OpenAI](https://platform.openai.com/api-keys) API anahtarı  

## Kurulum

```bash
git clone <repo-url>
cd QuakeGuard
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

**Linux / macOS:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Ortam değişkenleri

`.env.example` dosyasını `.env` olarak kopyalayın ve doldurun.

### Seçenek A — OpenAI

```env
OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o
```

### Seçenek B — Ücretsiz (Groq + yerel embedding)

```env
QUAKEGUARD_FREE=true
GROQ_API_KEY=gsk_...
# GROQ_MODEL=llama-3.3-70b-versatile
```

Mod değiştirdiğinizde eski ve yeni indeks karışmasın diye `chroma_db` / `chroma_db_local` klasörlerinden uygun olanı silebilirsiniz.

## Çalıştırma

```powershell
.\.venv\Scripts\streamlit run main.py
```

Tarayıcıda genelde: `http://localhost:8501`

## Klasör yapısı

```
QuakeGuard/
├── .env                  # yerelde oluşturun (Git’e eklemeyin)
├── main.py               # Streamlit arayüzü
├── config.py             # QUAKEGUARD_FREE vb.
├── data_provider.py      # Deprem verisi API
├── rag_engine.py         # Chroma + embedding
├── brain.py              # LangChain ajanı
├── geo_helpers.py        # Şehir → koordinat (Nominatim)
├── data/                 # PDF / TXT rehberler
├── requirements.txt
└── README.md
```

## Veri kaynakları

- Canlı deprem listesi: [orhanaydogdu Kandilli live API](https://api.orhanaydogdu.com.tr/deprem/kandilli/live) (herkese açık, ek anahtar gerekmez)  
- Bilgi bankası: `data/` altına kendi PDF/TXT dosyalarınızı ekleyin (örnek metin projede mevcut)  

## GitHub’a yüklerken

- **`.env` dosyasını commit etmeyin** (API anahtarları sızdırılır).  
- `chroma_db/`, `chroma_db_local/`, `.venv/` zaten `.gitignore` ile dışarıda bırakılmaya uygun.  

## Sorumluluk reddi

Bu proje eğitim ve prototip amaçlıdır. Deprem ve afet kararları için **AFAD**, yerel yönetim ve resmi kurum duyurularını esas alın. Uygulama tıbbi veya hukuki tavsiye vermez.

## Lisans

İhtiyacınıza uygun bir lisans ekleyebilirsiniz (ör. MIT). Şu an repo sahibi tanımlamalıdır.
