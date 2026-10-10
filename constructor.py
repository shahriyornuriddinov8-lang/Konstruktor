"""Asosiy konstruktor bot (PHP: index.php + panel.php + bots.php)."""
import hashlib
import hmac
import re
import threading
import time
from datetime import datetime, timedelta

import db
import templates
from config import (ADMIN_ID, ADMIN_USERNAME, BASE_URL, BOT_PRICE, BOT_TOKEN, CHANNEL_ID,
                    CHANNEL_USERNAME, DAILY_BONUS, LOG_CHAT_ID, PAYMENT_INFO, REFERAL_PRICE,
                    SECRET_KEY, TZ_OFFSET_HOURS)
from tg import TG, esc, inline_kb, reply_kb

tg = TG(BOT_TOKEN)
_me = {}
TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")


# ---------------------------------------------------------------- yordamchilar
def me_username():
    if "u" not in _me:
        r = tg.me()
        _me["u"] = r["username"] if r else "bot"
    return _me["u"]


def child_secret(tg_id):
    return hmac.new(SECRET_KEY.encode(), f"child:{tg_id}".encode(), hashlib.sha256).hexdigest()[:40]


def main_secret():
    return hmac.new(SECRET_KEY.encode(), b"main", hashlib.sha256).hexdigest()[:40]


def now_local():
    return datetime.utcnow() + timedelta(hours=TZ_OFFSET_HOURS)


def is_admin(uid):
    return ADMIN_ID and int(uid) == int(ADMIN_ID)


def check_join(uid):
    if not CHANNEL_ID or is_admin(uid):
        return True
    r = tg.call("getChatMember", chat_id=CHANNEL_ID, user_id=uid)
    return r.get("ok") and r["result"]["status"] in ("creator", "administrator", "member")


def log_chat(text):
    if LOG_CHAT_ID:
        tg.send(LOG_CHAT_ID, text)


# ---------------------------------------------------------------- menyular
MAIN = [["🛠 Bot yaratish", "🔐 Kabinet"], ["📊 Statistika", "📚 Bot haqida"],
        ["📨 Bog'lanish", "🎁 Kunlik bonus"], ["🏆 Reyting", "🎫 Promokod"]]
MAIN_KB = reply_kb(MAIN)
CANCEL_KB = reply_kb([["⬅️ Bekor qilish"]])
PANEL = [["📊 Admin statistika"], ["💸 Pul berish", "💸 Pul ayirish"],
         ["🔒 Bloklash", "🔓 Blokdan olish"], ["↗️ Xabar yuborish", "📋 Userga xabar"],
         ["❌ OFF", "✅ ON"], ["🎫 Promokod yaratish"], ["🔙 Ortga qaytish"]]
PANEL_KB = reply_kb(PANEL)

BUTTONS = {b for row in MAIN + PANEL for b in row} | {"⬅️ Bekor qilish", "⬅️ Orqaga"}


def template_menu(premium):
    items = [t.title for t in templates.REGISTRY.values() if t.premium == premium]
    rows = [items[i:i + 2] for i in range(0, len(items), 2)]
    return reply_kb(rows + [["⬅️ Orqaga"]])


WELCOME = ("<b>Assalomu alaykum {name}!</b>\n\n@{bot} orqali o'zingizning shaxsiy "
           "botlaringizni hech qanday qiyinchiliksiz yaratishingiz mumkin!\n\n"
           "⬇ Ishni boshlash uchun quyidagi tugmalardan foydalaning!")

RULES = ("<b>⚠️ Qoidalar:</b>\n<i>1. Bot administratorlari yaratilgan botlar sizga pul "
         "to'lashi yoki to'lamasligiga javobgar emas.\n"
         "2. Taniqli shaxslar, savdo belgilari, tashkilotlar nomidan soxta bot ochish taqiqlanadi.\n"
         "3. +18, diniy aqidaparastlik, davlat siyosatiga zid yoki yolg'on manbalarni tarqatuvchi "
         "kanallarda foydalanish qat'iyan taqiqlanadi.\n"
         "4. Kiritilgan ma'lumotlar uchinchi shaxsga oshkor etilmaydi.</i>")

HOWTO = ("🤖 <b>Bot yaratish qo'llanmasi</b>\n"
         "1. @BotFather ni oching va START bosing.\n2. /newbot buyrug'ini yuboring.\n"
         "3. Bot NOMini yozing.\n4. Bot USERNAMEni yozing (oxiri <code>bot</code> bilan tugasin).\n"
         "5. BotFather bergan <b>tokenni</b> saqlang.\n"
         "6. Bu yerda shablonni tanlab, tokenni yuboring — bot tayyor!")


# ---------------------------------------------------------------- kirish nuqtasi
def handle_update(upd):
    try:
        if "message" in upd:
            on_message(upd["message"])
        elif "callback_query" in upd:
            on_callback(upd["callback_query"])
        elif "inline_query" in upd:
            on_inline(upd["inline_query"])
    except Exception:
        import logging
        logging.exception("constructor xatosi")


def on_inline(q):
    uid, un = q["from"]["id"], me_username()
    tg.call("answerInlineQuery", inline_query_id=q["id"], cache_time=1, results=[{
        "type": "article", "id": "1",
        "title": "✅ Referal havolangizni yuborish uchun bosing",
        "input_message_content": {
            "message_text": "⚡️ Bir necha daqiqada o'z Telegram botingizga ega bo'ling!\n\n"
                            "⬇️ Buning uchun quyidagi tugma orqali botga kiring va bot yarating!"},
        "reply_markup": inline_kb([[("➕ Botga kirish", f"url:https://t.me/{un}?start={uid}")]])}])


# ---------------------------------------------------------------- xabarlar
def on_message(m):
    if m["chat"]["type"] != "private":
        return
    uid, chat = m["from"]["id"], m["chat"]["id"]
    name = m["from"].get("first_name", "")
    uname = m["from"].get("username", "")
    text = m.get("text")

    referrer = None
    if text and text.startswith("/start "):
        p = text.split(maxsplit=1)[1].strip()
        referrer = int(p) if p.isdigit() else None
    user, is_new = db.touch_user(uid, name, uname, referrer)
    if is_new:
        log_chat(f"😄 Yangi a'zo\n👤 {esc(name)}\n🆔 {uid}\n✳️ @{uname}")
    if user.get("banned"):
        tg.send(chat, f"Kechirasiz <b>{esc(name)}</b>, siz 🚫 bloklangansiz!")
        return
    if db.kv_get("bot_on", "1") != "1" and not is_admin(uid):
        tg.send(chat, "🛠 Bot vaqtincha o'chirilgan. Keyinroq urinib ko'ring.")
        return

    # /start
    if text and text.startswith("/start"):
        db.set_step(uid)
        if not require_join(chat, uid):
            return
        reward_referrer(uid, name)
        tg.send(chat, WELCOME.format(name=esc(name), bot=me_username()), MAIN_KB)
        return
    if not require_join(chat, uid):
        return

    if is_admin(uid) and text == "/panel":
        db.set_step(uid)
        tg.send(chat, "👑 Admin panel", PANEL_KB)
        return

    step, data = db.get_step(uid)
    if text and (text in BUTTONS or templates.by_title(text)):
        if step:
            db.set_step(uid)
            step = None
        route_button(m, user, text)
        return
    if step:
        on_step(m, user, step, data)
        return
    if text:
        tg.send(chat, "📋 Quyidagi menyudan foydalaning 👇", MAIN_KB)


def require_join(chat, uid):
    if check_join(uid):
        return True
    rows = []
    if CHANNEL_USERNAME:
        rows.append([("➕ Kanalga a'zo bo'lish", f"url:https://t.me/{CHANNEL_USERNAME}")])
    rows.append([("✅ Tekshirish", "tekshir")])
    tg.send(chat, "☑️ Botdan to'liq foydalanish uchun kanalimizga a'zo bo'ling, "
                  "so'ng «Tekshirish» tugmasini bosing.", inline_kb(rows))
    return False


def reward_referrer(uid, name):
    ref = db.claim_ref_reward(uid)
    if ref:
        db.inc_ref(ref, REFERAL_PRICE)
        tg.send(ref, f"📡 Tabriklaymiz! Do'stingiz <b>{esc(name)}</b> botga qo'shildi — "
                     f"sizga <b>{REFERAL_PRICE}</b> UZS berildi!")


# ---------------------------------------------------------------- tugmalar
def route_button(m, user, text):
    uid, chat = user["id"], m["chat"]["id"]
    admin = is_admin(uid)

    if text in ("🔙 Ortga qaytish", "⬅️ Bekor qilish", "⬅️ Orqaga"):
        tg.send(chat, "🖥 Bosh sahifa", MAIN_KB)
    elif text == "🛠 Bot yaratish":
        tg.send(chat, "📋 Quyidagi botlardan birini tanlang:", inline_kb(
            [[("⚙️ Standart botlar", "tekin")], [("💎 Premium botlar", "pullik")]]))
    elif text == "🔐 Kabinet":
        u = db.get_user(uid)
        tg.send(chat, f"🗄 <b>Kabinetingizga xush kelibsiz!</b>\n💵 Balans: <b>{u['balance']}</b> UZS\n"
                      f"👥 Takliflaringiz: <b>{u['ref_count']}</b> ta\n🤖 Botlaringiz: "
                      f"<b>{len(db.bots_of(uid))}</b> ta",
                inline_kb([[("👥 Takliflar", "ishla"), ("🤖 Botlarim", "mybots")],
                                  [("💳 Hisobni to'ldirish", "toldir"), ("🔄 O'tkazish", "almashish")]]))
    elif text == "📊 Statistika":
        tg.send(chat, stats_text(), parse_mode="HTML")
    elif text == "📚 Bot haqida":
        tg.send(chat, f"💡 <b>Bot konstruktor</b>\n@{me_username()} orqali dasturlashni bilmasdan "
                      "ham bot yaratishingiz mumkin!\n⚙ Versiya: v1.0 (Python)",
                inline_kb([[("📋 Qo'llanma", "noma"), ("⚠️ Qoidalar", "qoida")],
                           [("📨 Yordam", f"url:https://t.me/{ADMIN_USERNAME.lstrip('@')}")]]))
    elif text == "📨 Bog'lanish":
        db.set_step(uid, "contact")
        tg.send(chat, "✍️ Xabaringizni yozing (adminga yuboriladi):", CANCEL_KB)
    elif text == "🎁 Kunlik bonus":
        if db.claim_bonus(uid, now_local().strftime("%Y-%m-%d"), DAILY_BONUS):
            tg.send(chat, f"👏 Tabriklaymiz! Sizga <b>{DAILY_BONUS}</b> UZS bonus berildi!")
        else:
            tg.send(chat, "♻️ Bugun bonus olgansiz. Keyingisini ertaga olasiz!")
    elif text == "🏆 Reyting":
        rows = db.top_users(10)
        out = "<b>🛡 TOP 10 — eng ko'p UZS to'plaganlar:</b>\n\n"
        for i, (rid, rname, bal) in enumerate(rows, 1):
            out += f"<b>{i}</b>. <a href='tg://user?id={rid}'>{esc(rname) or rid}</a> — <i>{bal}</i> UZS\n"
        tg.send(chat, out)
    elif text == "🎫 Promokod":
        db.set_step(uid, "promo")
        tg.send(chat, "🎫 Promokodni yuboring:", CANCEL_KB)
    elif (t := templates.by_title(text)):
        start_create(chat, uid, t)
    # ---- admin
    elif admin and text == "📊 Admin statistika":
        tg.send(chat, stats_text() + f"\n🚫 Bloklanganlar/👑 admin panel faol")
    elif admin and text in ("💸 Pul berish", "💸 Pul ayirish"):
        kind = "give" if "berish" in text else "take"
        db.set_step(uid, f"adm_{kind}")
        tg.send(chat, "ID va summani 2 qatorda yuboring:\n<code>123456789\n1000</code>", CANCEL_KB)
    elif admin and text in ("🔒 Bloklash", "🔓 Blokdan olish"):
        db.set_step(uid, "adm_ban" if text == "🔒 Bloklash" else "adm_unban")
        tg.send(chat, "Foydalanuvchi ID raqamini yuboring:", CANCEL_KB)
    elif admin and text == "↗️ Xabar yuborish":
        db.set_step(uid, "adm_bc")
        tg.send(chat, "Hammaga yuboriladigan xabarni yuboring (matn, rasm, video...):", CANCEL_KB)
    elif admin and text == "📋 Userga xabar":
        db.set_step(uid, "adm_msg_id")
        tg.send(chat, "Foydalanuvchi ID raqamini yuboring:", CANCEL_KB)
    elif admin and text in ("❌ OFF", "✅ ON"):
        db.kv_set("bot_on", "1" if text == "✅ ON" else "0")
        tg.send(chat, "✅ Bot yoqildi" if text == "✅ ON" else "❌ Bot o'chirildi", PANEL_KB)
    elif admin and text == "🎫 Promokod yaratish":
        db.set_step(uid, "adm_promo")
        tg.send(chat, "Format (3 qator): kod, summa, necha kishi uchun\n"
                      "<code>YANGI\n5000\n100</code>", CANCEL_KB)


def stats_text():
    free, pro = int(db.kv_get("stat_free", 0)), int(db.kv_get("stat_pro", 0))
    n = now_local()
    return (f"📊 <b>@{me_username()}</b> statistikasi:\n👥 A'zolar: <b>{db.count_users()}</b> ta\n"
            f"🆓 Bepul botlar: <b>{free}</b> ta\n💰 Premium botlar: <b>{pro}</b> ta\n"
            f"🔁 Jami: <b>{free + pro}</b> ta\n⏰ {n:%H:%M}   📆 {n:%d.%m.%Y}")


def start_create(chat, uid, t):
    if t.premium:
        bal = db.get_user(uid)["balance"]
        if bal < BOT_PRICE:
            tg.send(chat, f"❌ Premium bot narxi <b>{BOT_PRICE}</b> UZS. Balansingiz: <b>{bal}</b> UZS.\n"
                          "Kabinet → Hisobni to'ldirish.")
            return
    db.set_step(uid, f"create:{t.kind}")
    tg.send(chat, f"1️⃣ @BotFather'dan olgan <b>bot tokeningizni</b> yuboring.\n\n"
                  f"Namuna: <code>123456789:AAH...xyz</code>"
                  + (f"\n\n💎 Narxi: {BOT_PRICE} UZS" if t.premium else ""), CANCEL_KB)


# ---------------------------------------------------------------- bosqichlar
def on_step(m, user, step, data):
    uid, chat = user["id"], m["chat"]["id"]
    text = (m.get("text") or "").strip()
    done = lambda msg, kb=MAIN_KB: (db.set_step(uid), tg.send(chat, msg, kb))
    pk = PANEL_KB if is_admin(uid) else MAIN_KB

    if step == "contact":
        if not ADMIN_ID:
            return done("⚠️ Admin sozlanmagan.")
        tg.send(ADMIN_ID, f"🔏 <b>Murojaat</b>\n👤 <a href='tg://user?id={uid}'>{esc(user['name'])}</a>"
                          f" @{user.get('username') or '-'}\n🆔 <code>{uid}</code>\n━━━━━━━━\n{esc(text)}")
        done("📚 Murojaatingiz adminga yuborildi.")

    elif step == "promo":
        st, amount = db.use_promo(text.upper(), uid)
        done({"ok": f"🎉 Promokod faollashdi! Hisobingizga <b>{amount}</b> UZS qo'shildi.",
              "none": "❌ Bunday promokod yo'q.", "used": "⚠️ Siz bu kodni ishlatgansiz.",
              "empty": "⚠️ Promokod limiti tugagan."}[st])

    elif step == "tr_id":
        if not text.isdigit() or int(text) == uid:
            tg.send(chat, "❗ To'g'ri ID yuboring (o'zingizdan boshqa):")
            return
        db.set_step(uid, "tr_amt", {"to": int(text)})
        tg.send(chat, "Qancha UZS o'tkazmoqchisiz?")

    elif step == "tr_amt":
        if not text.isdigit() or int(text) <= 0:
            tg.send(chat, "❗ Summani raqamda yuboring:")
            return
        amt, to = int(text), data["to"]
        res = db.transfer(uid, to, amt)
        if res == "ok":
            tg.send(to, f"📨 Hisobingizga <b>{amt}</b> UZS o'tkazildi (ID: {uid}).")
            done(f"✅ {amt} UZS o'tkazildi.")
        else:
            done("❌ Foydalanuvchi topilmadi." if res == "nouser" else "❌ Balansingizda mablag' yetarli emas.")

    elif step.startswith("create:"):
        create_bot(chat, uid, step.split(":", 1)[1], text)

    # ------------- admin
    elif is_admin(uid) and step in ("adm_give", "adm_take"):
        parts = text.split()
        if len(parts) != 2 or not all(p.lstrip("-").isdigit() for p in parts):
            tg.send(chat, "❗ Format: ID va summa (2 qatorda)")
            return
        target, amt = int(parts[0]), int(parts[1])
        if not db.get_user(target):
            return done("❌ Foydalanuvchi topilmadi.", PANEL_KB)
        sign = 1 if step == "adm_give" else -1
        db.add_balance(target, sign * amt)
        tg.send(target, f"💳 Hisobingiz {'to‘ldirildi' if sign > 0 else 'dan ayirildi'}: <b>{amt}</b> UZS")
        done(f"✅ Bajarildi: {target} → {sign * amt} UZS", PANEL_KB)

    elif is_admin(uid) and step in ("adm_ban", "adm_unban"):
        ok = text.isdigit() and db.set_banned(int(text), step == "adm_ban")
        done("✅ Bajarildi." if ok else "❌ Foydalanuvchi topilmadi.", PANEL_KB)

    elif is_admin(uid) and step == "adm_bc":
        done("📤 Yuborish boshlandi...", PANEL_KB)
        threading.Thread(target=broadcast, args=(chat, m["message_id"]), daemon=True).start()

    elif is_admin(uid) and step == "adm_msg_id":
        if not text.isdigit():
            tg.send(chat, "❗ ID raqam yuboring:")
            return
        db.set_step(uid, "adm_msg_text", {"to": int(text)})
        tg.send(chat, "Xabar matnini yuboring:")

    elif is_admin(uid) and step == "adm_msg_text":
        r = tg.call("copyMessage", chat_id=data["to"], from_chat_id=chat, message_id=m["message_id"])
        done("✅ Yuborildi." if r.get("ok") else "❌ Yuborib bo'lmadi.", PANEL_KB)

    elif is_admin(uid) and step == "adm_promo":
        p = text.split()
        if len(p) != 3 or not (p[1].isdigit() and p[2].isdigit()):
            tg.send(chat, "❗ Format: kod, summa, limit (3 qatorda)")
            return
        ok = db.create_promo(p[0].upper(), int(p[1]), int(p[2]))
        done(f"✅ Promokod yaratildi: <code>{p[0].upper()}</code>" if ok else "⚠️ Bunday kod bor.", PANEL_KB)
    else:
        db.set_step(uid)


def broadcast(admin_chat, message_id):
    ok = fail = 0
    for uid in db.all_user_ids():
        r = tg.call("copyMessage", chat_id=uid, from_chat_id=admin_chat, message_id=message_id)
        ok, fail = (ok + 1, fail) if r.get("ok") else (ok, fail + 1)
        time.sleep(0.05)  # Telegram limiti ~30 xabar/soniya
    tg.send(admin_chat, f"✅ Yuborildi: {ok}\n❌ Yetib bormadi: {fail}")


# ---------------------------------------------------------------- bot yaratish
def create_bot(chat, uid, kind, token):
    t = templates.REGISTRY.get(kind)
    if not t:
        db.set_step(uid)
        return tg.send(chat, "❌ Shablon topilmadi.", MAIN_KB)
    if not TOKEN_RE.match(token):
        return tg.send(chat, "❌ Token noto'g'ri ko'rinishda. Qaytadan yuboring yoki bekor qiling.")
    if not BASE_URL:
        return tg.send(chat, "⚠️ Server BASE_URL sozlanmagan (admin bilan bog'laning).")
    child = TG(token)
    info = child.me()
    if not info:
        return tg.send(chat, "❌ Bu token ishlamayapti. @BotFather'dan to'g'ri token oling.")
    if info["id"] == tg.me()["id"]:
        return tg.send(chat, "❌ Bu konstruktorning o'z tokeni!")

    prev = db.get_bot(info["id"])
    charge = t.premium and not (prev and prev["kind"] == kind and prev["owner"] == uid)
    if charge and not db.take_balance(uid, BOT_PRICE):
        db.set_step(uid)
        return tg.send(chat, "❌ Balansingizda mablag' yetarli emas.", MAIN_KB)

    wait = tg.send(chat, "⏳ Tayyorlanmoqda...")
    r = child.call("setWebhook", url=f"{BASE_URL}/hook/{info['id']}",
                   secret_token=child_secret(info["id"]), drop_pending_updates=True)
    if wait.get("ok"):
        tg.delete(chat, wait["result"]["message_id"])
    if not r.get("ok"):
        if charge:
            db.add_balance(uid, BOT_PRICE)  # pulni qaytarish
        db.set_step(uid)
        return tg.send(chat, f"📛 Webhook o'rnatilmadi: {esc(r.get('description', 'noma’lum xato'))}", MAIN_KB)

    is_new = db.save_bot(info["id"], uid, kind, token, info.get("username"), info.get("first_name"))
    if is_new:
        db.kv_incr("stat_pro" if t.premium else "stat_free")
    db.set_step(uid)
    tg.send(chat, f"✅ <b>Bot tayyor!</b>\n\n💡 Turi: {t.title}\n👤 Nomi: {esc(info.get('first_name'))}\n"
                  f"✳️ @{info.get('username')}\n🆔 {info['id']}\n\nBotga kirib /start bosing.", MAIN_KB)
    log_chat(f"🆕 Yangi bot ulandi\n⚔ {t.title}\n💌 @{info.get('username')}\n👤 egasi: {uid}")


def restore_main_webhook():
    if BASE_URL and BOT_TOKEN:
        return tg.call("setWebhook", url=f"{BASE_URL}/webhook", secret_token=main_secret(),
                       allowed_updates=["message", "callback_query", "inline_query"])


# ---------------------------------------------------------------- callback
def on_callback(cb):
    uid, chat = cb["from"]["id"], cb["message"]["chat"]["id"]
    mid, data = cb["message"]["message_id"], cb["data"]
    user = db.get_user(uid)
    if not user or user.get("banned"):
        return tg.answer_cb(cb["id"])

    if data == "tekshir":
        if check_join(uid):
            tg.delete(chat, mid)
            reward_referrer(uid, user["name"])
            tg.send(chat, "✅ Rahmat! Ishni boshlash uchun menyudan foydalaning.", MAIN_KB)
            return tg.answer_cb(cb["id"])
        return tg.answer_cb(cb["id"], "❌ Siz hali kanalga a'zo bo'lmadingiz!", True)

    tg.answer_cb(cb["id"])
    back = inline_kb([[("◀️ Ortga", "malumot")]])

    if data in ("tekin", "pullik"):
        if data == "pullik" and not any(t.premium for t in templates.REGISTRY.values()):
            return tg.send(chat, "Hozircha premium botlar yo'q.")
        tg.send(chat, "📋 Quyidagi botlardan birini tanlang:", template_menu(data == "pullik"))
    elif data == "ishla":
        link = f"https://t.me/{me_username()}?start={uid}"
        tg.edit(chat, mid, f"⚡️ Taklif havolangiz:\n<code>{link}</code>\n\n"
                           f"💳 Har bir taklif uchun <b>{REFERAL_PRICE}</b> UZS olasiz.",
                inline_kb([[("📤 Ulashish", f"url:https://t.me/share/url?url={link}")]]))
    elif data == "toldir":
        tg.edit(chat, mid, f"💳 <b>Hisobni to'ldirish</b>\n\n{esc(PAYMENT_INFO)}\n\n"
                           f"📝 Izohga ID raqamingizni yozing: <code>{uid}</code>",
                inline_kb([[("☎️ Tex. yordam", f"url:https://t.me/{ADMIN_USERNAME.lstrip('@')}")]]))
    elif data == "almashish":
        db.set_step(uid, "tr_id")
        tg.send(chat, "⚠️ O'tkazma qaytarilmaydi!\nQabul qiluvchining ID raqamini yuboring:", CANCEL_KB)
    elif data == "mybots":
        rows = db.bots_of(uid)
        if not rows:
            return tg.send(chat, "Sizda hali bot yo'q. «🛠 Bot yaratish» orqali yarating.")
        kb = inline_kb([[(f"🗑 @{b['username']} ({b['kind']})", f"delbot:{b['tg_id']}")] for b in rows])
        tg.send(chat, "🤖 Botlaringiz (o'chirish uchun bosing):", kb)
    elif data.startswith("delbot:"):
        b = db.get_bot(int(data.split(":")[1]))
        if b and b["owner"] == uid:
            TG(b["token"]).call("deleteWebhook")
            db.delete_bot(b["tg_id"], uid)
            tg.edit(chat, mid, f"🗑 @{b['username']} o'chirildi.")
    elif data == "malumot":
        tg.edit(chat, mid, f"💡 <b>Bot konstruktor</b>\n@{me_username()}\n⚙ Versiya: v1.0",
                inline_kb([[("📋 Qo'llanma", "noma"), ("⚠️ Qoidalar", "qoida")]]))
    elif data == "noma":
        tg.edit(chat, mid, HOWTO, back)
    elif data == "qoida":
        tg.edit(chat, mid, RULES, back)
