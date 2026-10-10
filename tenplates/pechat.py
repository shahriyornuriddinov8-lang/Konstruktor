import base64
import io
import requests
from PIL import Image
from . import register
from tg import reply_kb

ARROWS = {"↖️": 1, "⬆️": 2, "↗️": 3, "↙️": 4, "⬇️": 5, "↘️": 6}
KB = reply_kb([["↖️", "⬆️", "↗️"], ["↙️", "⬇️", "↘️"]])
MAX_LOGO = 1_500_000  # bayt


def _download(ctx, file_id):
    r = ctx.tg.call("getFile", file_id=file_id)
    if not r.get("ok"):
        return None
    url = f"https://api.telegram.org/file/bot{ctx.tg.token}/{r['result']['file_path']}"
    try:
        return requests.get(url, timeout=30).content
    except Exception:
        return None


def _place(photo, logo, pos):
    pw, ph = photo.size
    lw = max(24, pw // 4)
    lh = int(logo.size[1] * lw / logo.size[0])
    logo = logo.resize((lw, lh))
    pad = max(4, pw // 100)
    x = {1: pad, 4: pad, 2: (pw - lw) // 2, 5: (pw - lw) // 2}.get(pos, pw - lw - pad)
    y = pad if pos in (1, 2, 3) else ph - lh - pad
    photo.paste(logo, (x, y), logo)
    return photo


@register("pechat", "🤖 Pechat bot", premium=True)
def handle(ctx, upd):
    m = upd.get("message")
    if not m:
        return
    chat, txt = m["chat"]["id"], m.get("text", "")
    ctx.add_member(chat)
    step = ctx.get(f"step:{chat}")

    if txt in ("/start", "/help"):
        ctx.set(f"step:{chat}", "logo")
        ctx.tg.send(chat, "😊 <b>Salom!</b> Men rasmlaringizga o'z pechatingizni (logotip) qo'yaman.\n\n"
                          "Avval logotipni <b>fayl</b> ko'rinishida yuboring (rasm emas, <b>fayl</b>; "
                          "PNG shaffof fonli bo'lsa yaxshi)." + ctx.footer)
        return
    if txt == "/stat":
        ctx.tg.send(chat, f"📈 Foydalanuvchilar: <b>{len(ctx.members())}</b> ta")
        return

    if "document" in m and step == "logo":
        doc = m["document"]
        if doc.get("file_size", 0) > MAX_LOGO:
            ctx.tg.send(chat, "❌ Logotip hajmi 1.5 MB dan oshmasligi kerak.")
            return
        data = _download(ctx, doc["file_id"])
        try:
            Image.open(io.BytesIO(data)).verify()
        except Exception:
            ctx.tg.send(chat, "❌ Bu rasm fayli emas. PNG yoki JPG yuboring.")
            return
        ctx.set(f"logo:{chat}", base64.b64encode(data).decode())
        ctx.set(f"step:{chat}", "joy")
        ctx.tg.send(chat, "✅ Fayl yuklandi. Endi logotip joylashuvini tanlang.", KB)
        return

    if step == "joy" and txt in ARROWS:
        ctx.set(f"joy:{chat}", ARROWS[txt])
        ctx.delete(f"step:{chat}")
        ctx.tg.send(chat, "👍 Endi rasmlarni yuborishingiz mumkin!", {"remove_keyboard": True})
        return

    if "photo" in m:
        logo_b64, pos = ctx.get(f"logo:{chat}"), ctx.get(f"joy:{chat}")
        if not logo_b64 or not pos:
            ctx.tg.send(chat, "Avval /start bosib logotip va joylashuvni sozlang.")
            return
        data = _download(ctx, m["photo"][-1]["file_id"])
        if not data:
            ctx.tg.send(chat, "❌ Rasmni yuklab bo'lmadi.")
            return
        photo = Image.open(io.BytesIO(data)).convert("RGBA")
        logo = Image.open(io.BytesIO(base64.b64decode(logo_b64))).convert("RGBA")
        out = _place(photo, logo, int(pos)).convert("RGB")
        buf = io.BytesIO()
        out.save(buf, "JPEG", quality=92)
        buf.seek(0)
        ctx.tg.call("sendPhoto", chat_id=chat, files={"photo": ("pechat.jpg", buf)},
                    caption="😊 Tayyor!" + ctx.footer)
