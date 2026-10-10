import random
from datetime import datetime, timedelta
from . import register
from tg import inline_kb
from config import TZ_OFFSET_HOURS

QUESTIONS = [
    "Sizga muzqaymoq yoqadimi?",
    "8-martda Onangizni tabriklaganmisiz?",
    "Dunyoda yer maydoni eng katta bo'lgan davlatni bilasizmi?",
    "O'zbekiston dunyoda birinchi bo'lishiga ishonasizmi?",
    "Qalesiz endi keyingi savolimizga javob berishga tayyormisiz?",
    "Siz musiqaga qiziqasizmi?",
    "Siz uchun havo juda kerakmi?",
    None,  # soat savoli (dinamik)
    "Men sizni sevib qoldim ❤",
]


def _yn(n):
    a = [("HA", f"q:{n}"), ("YO'Q", f"q:{n}")]
    random.shuffle(a)
    return inline_kb([a])


@register("xayokiyoq", "🤖 Xa Yoki Yoq")
def handle(ctx, upd):
    m = upd.get("message")
    if m:
        chat, txt = m["chat"]["id"], m.get("text", "")
        ctx.add_member(chat)
        if txt.startswith("/start"):
            name = m["from"].get("first_name", "")
            ctx.tg.send(chat, f"Salom <b>{name}</b>! HA YOKI YO'Q o'yiniga xush kelibsiz, "
                              "mazza qilasiz degan umiddaman!",
                        inline_kb([[("HA", "q:0"), ("YO'Q", "q:0")]]))
        return
    cb = upd.get("callback_query")
    if not cb:
        return
    chat, mid, data = cb["message"]["chat"]["id"], cb["message"]["message_id"], cb["data"]
    ctx.tg.answer_cb(cb["id"])
    if data == "end":
        ctx.tg.edit(chat, mid, "O'ynaganingiz uchun rahmat! /start orqali qayta boshlang.")
        return
    if not data.startswith("q:"):
        return
    n = int(data[2:])
    if n >= len(QUESTIONS):
        score = random.randint(1, 9)
        ctx.tg.edit(chat, mid, f"SIZ <b>{score}</b> TA SAVOLGA TO'G'RI JAVOB BERDINGIZ! TABRIKLAYMAN ★",
                    inline_kb([[("BOSHIDAN", "q:0")]]))
        return
    q = QUESTIONS[n]
    if q is None:
        now = (datetime.utcnow() + timedelta(hours=TZ_OFFSET_HOURS)).strftime("%H:%M")
        q = f"Hozir soat: {now}. Shu vaqtda uxlash mumkinmi?"
    kb = _yn(n + 1)
    if n == len(QUESTIONS) - 1:
        kb = inline_kb([[("♥ Oooo menham jonim", "q:99"), ("Uff ♡", "q:99")],
                        [("Tugatish", "end")]])
    ctx.tg.edit(chat, mid, q, kb)
