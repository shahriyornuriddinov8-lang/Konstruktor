# 🤖 Bot Konstruktor (Python) — OldMakerBot (TexnoPHPuz) ning Python varianti

Telegram foydalanuvchilari bu botga **o'z bot tokenini** yuborib, tayyor shablondan bot yaratadi.
Asl PHP loyiha `index.php + panel.php + bots.php` ning Python (Flask) ga o'tkazilgan varianti.

## Nimalar bor
**Konstruktor:** bot yaratish (standart/premium), kabinet, balans, referal (taklif), kunlik bonus,
reyting, promokod, UZS o'tkazish, majburiy kanalga obuna, "Botlarim" (ko'rish/o'chirish), statistika.
**Admin (`/panel`):** pul berish/ayirish, bloklash/blokdan olish, hammaga xabar, userga xabar,
ON/OFF, promokod yaratish.
**Shablonlar:** `qidir`, `aloqa`, `xayokiyoq`, `gif`, `urlupload`, `pechat` (premium).

## 1) Telegram'da tayyorlash
1. @BotFather → `/newbot` → **asosiy bot tokeni** (BOT_TOKEN).
2. O'z ID raqamingizni @userinfobot dan oling (ADMIN_ID).
3. (ixtiyoriy) Majburiy obuna kanali: botni kanalga **admin** qiling, `CHANNEL_ID` (-100...) va `CHANNEL_USERNAME` ni yozing.

## 2) GitHub'ga yuklash
```bash
git init && git add . && git commit -m "bot konstruktor"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO.git
git push -u origin main
```

## 3) Bepul baza (MUHIM)
Render bepul serverining diski **vaqtinchalik** — qayta ishga tushganda SQLite o'chib ketadi
(foydalanuvchilar, balanslar, yaratilgan botlar yo'qoladi). Shuning uchun bepul Postgres oling:
**Neon.tech** yoki **Supabase** → connection string (`postgresql://...`) ni `DATABASE_URL` ga yozing.
(Renderning o'z bepul Postgres'i 30 kundan keyin o'chadi.)

## 4) Render'ga joylash
1. render.com → **New → Web Service** → GitHub repo'ni tanlang (yoki **Blueprint**: `render.yaml`).
2. Build: `pip install -r requirements.txt`
   Start: `gunicorn app:app --workers 1 --threads 8 --timeout 60 --bind 0.0.0.0:$PORT`
3. **Environment** bo'limiga `.env.example` dagi o'zgaruvchilarni kiriting:
   `BOT_TOKEN`, `ADMIN_ID`, `ADMIN_USERNAME`, `SECRET_KEY`, `DATABASE_URL`, (`CHANNEL_ID`, `CHANNEL_USERNAME`, `PAYMENT_INFO`, `MAKER_USERNAME` ...).
4. Deploy tugagach server o'zi webhook'ni o'rnatadi (`RENDER_EXTERNAL_URL` avtomatik).
   Tekshirish: `https://NOMI.onrender.com/health` → `{"ok":true,...}`.
5. Botga `/start`, admin sifatida `/panel`.

> ⚠️ **`--workers 1` ni o'zgartirmang** (fon oqimlar va ichki holat uchun).
> Bepul Render 15 daqiqa so'rovsiz bo'lsa uxlaydi; kod har 10 daqiqada o'zini chaqiradi
> (`KEEPALIVE=0` bilan o'chiriladi), baribir ishonchli bo'lishi uchun UptimeRobot bilan
> `/health` ni har 5 daqiqada ping qiling.

## Yangi shablon qo'shish
`templates/` ga fayl yarating:
```python
from . import register

@register("mening", "🤖 Mening bot")          # premium=True — pullik
def handle(ctx, upd):
    m = upd.get("message")
    if m and m.get("text") == "/start":
        ctx.tg.send(m["chat"]["id"], "Salom!" + ctx.footer)
```
So'ng `templates/__init__.py` oxiridagi import qatoriga nomini qo'shing. `ctx` da: `ctx.tg` (Telegram API),
`ctx.owner`, `ctx.add_member()`, `ctx.members()`, `ctx.get()/set()` (har bot uchun saqlash).

## Asl PHP bilan farqlar
- Foydalanuvchi botlari **PHP fayl yaratib emas**, bitta server ichida shablon sifatida ishlaydi (xavfsizroq, Renderda mumkin).
- Webhook'lar `secret_token` bilan himoyalangan.
- Tuzatildi: `/almashish` da tekinga pul chiqarish xatosi; asl kodda `SafobekUz` matni 100 000 UZS berar edi — **olib tashlandi**.
- Karta/hamyon raqamlari kodda emas, `PAYMENT_INFO` da.

## Hali o'tkazilmagan shablonlar
Asl zipda ~60 ta shablon bor edi; bu versiyada 6 tasi o'tkazildi. Qolganlari (Posbon, Quron, Logo, Music,
Konvertor, Tarjimon, Uzmobile, Vunder, Suhbatchi, OnlineTest, ZArchiver, Pul/Nakrutka/UC botlari va h.k.)
shu `register` tizimi orqali birin-ketin qo'shiladi.
