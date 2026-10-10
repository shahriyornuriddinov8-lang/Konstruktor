from urllib.parse import quote
from . import register
from tg import inline_kb

START = ("🔎 <b>Qidiruv botimizga xush kelibsiz!</b>\n\n"
         "🔍 Biror narsani qidirish uchun matn yuboring. Masalan: video, rasm, musiqa yoki "
         "telefon uchun dastur nomi — bot qidiruv havolalarini beradi.")


@register("qidir", "🤖 Qidir bot")
def handle(ctx, upd):
    m = upd.get("message")
    if not m or "text" not in m:
        return
    chat, txt = m["chat"]["id"], m["text"]
    ctx.add_member(chat)
    if txt.startswith("/start"):
        ctx.tg.send(chat, START)
        return
    q = quote(txt)
    ctx.tg.send(chat, f"🔍 Qidirilmoqda: <b>{txt[:100]}</b>\n━━━━━━━━━━━━\n🔎 Natijalar: 👇",
                inline_kb([
                    [("App Store 🌐", f"url:https://apple.com/us/search?q={q}")],
                    [("Google 📈", f"url:https://google.com/search?q={q}")],
                    [("YouTube 🎥", f"url:https://m.youtube.com/results?search_query={q}")],
                    [("Instagram 📯", f"url:https://instagram.com/{q}")],
                    [("Telegram 📪", f"url:https://t.me/{q}")],
                ]))
