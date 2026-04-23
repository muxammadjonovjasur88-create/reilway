# 🏆 Esports Tournament Bot

Mobile Legends: Bang Bang va boshqa esports o'yinlari uchun Telegram turnir boti.

## ⚙️ O'rnatish

```bash
# 1. Python virtual muhit yaratish
python -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate     # Windows

# 2. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. config.py faylini sozlash
nano config.py
```

## 🔧 config.py sozlamalari

```python
BOT_TOKEN = "7XXXXXXXX:AAXXXXXXXXXX"  # @BotFather dan oling

REQUIRED_CHANNELS = [
    {"id": -100XXXXXXXXXX, "link": "https://t.me/kanalim", "name": "Asosiy kanal"},
    {"id": -100XXXXXXXXXX, "link": "https://t.me/esports_uz", "name": "Esports kanal"},
]

ADMIN_IDS = [123456789]  # Telegram ID (@userinfobot dan bilib oling)
```

## 🚀 Ishga tushirish

```bash
python bot.py
```

## 📋 Admin buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/admin` | Admin panelni ochish |
| `/match` | Kutilayotgan matchlarni ko'rish |
| `/lobby MATCH_ID LOBBY_ID` | Match uchun lobby berish |

## 🎮 O'yinchi buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni boshlash |
| `/join JAMOA_KODI` | Jamoaga qo'shilish |

## 🗂 Turnir jarayoni

```
Admin → Turnir yaratadi
Admin → Ro'yxatni ochadi
Lider → /start → O'yin tanlash → Ro'yxatdan o'tish → Jamoa kodi oladi
O'yinchi → /join KOD → Jamoaga qo'shiladi
Admin → Matchlarni tuzadi (random)
Admin → /lobby 1 ABC123 (har bir matchga)
O'yinchilar → O'ynaydi
Admin → /match → G'olibni belgilaydi
Admin → Offline uchun manzil beradi
```

## 📊 Ma'lumotlar bazasi (SQLite)

- `tournaments` — Turnirlar
- `teams` — Jamoalar
- `players` — O'yinchilar
- `matches` — Matchlar
- `user_states` — Foydalanuvchi holati (FSM)

## 🔮 Kelajakda qo'shish mumkin

- [ ] Screenshot yuklash va tasdiqlash
- [ ] Rating (ELO) tizimi
- [ ] To'lov tizimi (Click, Payme)
- [ ] Bracket visualization (rasmli jadval)
- [ ] Telegram channel'ga avtomatik e'lon
- [ ] MVP tanlash (har match uchun)
- [ ] Turnir tarixi va rekordlar
