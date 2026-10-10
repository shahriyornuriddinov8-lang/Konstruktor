import re
from . import register

HELLO = ("<b>👋 Assalomu alaykum!</b>\n🤖 Menga fayl havolasini (rasm, video, audio, hujjat) "
         "yuboring — men uni Telegram'ga yuklab beraman.\n⚠️ Hajm cheklovi: ~20 MB.")
URL_RE = re.compile(r"^https?://[^\s]+\.[a-zA-Z0-9]+", re.I)


@register("urlupload", "🤖 UrlUpload")
def handle(ctx, upd):
    m = upd.get("message")
    if not m or "text" not in m:
        return
    chat, txt = m["chat"]["id"], m["text"].strip()
    ctx.add_member(chat)
    if txt.startswith("/start"):
        ctx.tg.send(chat, HELLO)
        return
    if not URL_RE.match(txt):
        ctx.tg.send(chat, "❗ Iltimos, to'g'ri havola yuboring (http:// yoki https:// bilan).")
        return
    low = txt.lower().split("?")[0]
    if low.endswith((".jpg", ".jpeg", ".png", ".webp")):
        method, field = "sendPhoto", "photo"
    elif low.endswith((".mp4", ".mov", ".mkv")):
        method, field = "sendVideo", "video"
    elif low.endswith((".mp3", ".m4a", ".ogg", ".wav")):
        method, field = "sendAudio", "audio"
    elif low.endswith(".gif"):
        method, field = "sendAnimation", "animation"
    else:
        method, field = "sendDocument", "document"
    r = ctx.tg.call(method, chat_id=chat, caption="✅ Muvaffaqiyatli yuklandi!" + ctx.footer,
                    **{field: txt})
    if not r.get("ok"):
        ctx.tg.send(chat, "❌ Yuklab bo'lmadi (havola ishlamayapti yoki fayl juda katta).")
