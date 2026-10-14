# Titanlar Discord Sitesi

Siyah-mor neon temalı, Flask ile hazırlanmış Titanlar Discord topluluk sitesi.

## Dosyalar
- `app.py`: Flask uygulaması
- `templates/index.html`: Sayfa içeriği
- `static/style.css`: Tasarım ve animasyonlar
- `static/script.js`: Mobil menü ve küçük etkileşimler
- `requirements.txt`: Python bağımlılıkları
- `render.yaml`: Render dağıtım ayarları

## Render
GitHub deposunu Render'a bağlayın ve `New +` → `Web Service` seçin.
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`
- Runtime: Python 3
- Health Check Path: `/health`

Discord daveti `templates/index.html` içinde `https://discord.gg/titanlar` olarak ayarlanmıştır.
Üye sayısı ve yetkili isimleri örnek metinlerdir; gerçek verilerle değiştirin.
