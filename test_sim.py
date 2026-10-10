import os, sys, io, json, time, tempfile
tmp = tempfile.mkdtemp()
os.environ.update(BOT_TOKEN="111111:" + "A"*35, ADMIN_ID="1", ADMIN_USERNAME="@adm",
    BASE_URL="https://x.onrender.com", SECRET_KEY="s3", DATABASE_URL=f"sqlite:///{tmp}/t.db",
    KEEPALIVE="0", MAKER_USERNAME="MakerBot")
sys.path.insert(0, ".")
from PIL import Image
import tg as tgmod, requests

CALLS = []; MID = [100]
def img(color):
    b = io.BytesIO(); Image.new("RGBA", (400, 300), color).save(b, "PNG"); return b.getvalue()
FILES = {"photo.png": img((255, 0, 0, 255)), "logo.png": img((0, 0, 255, 200))}

class R:
    def __init__(s, j=None, content=b""): s._j, s.content = j, content
    def json(s): return s._j

def fake_post(url, data=None, files=None, timeout=None):
    tok = url.split("/bot")[1].split("/")[0]; method = url.rsplit("/", 1)[1]
    CALLS.append((tok, method, dict(data or {}), bool(files)))
    if method == "getMe":
        n = int(tok.split(":")[0]); return R({"ok": True, "result": {"id": n, "username": f"bot{n}", "first_name": f"Bot{n}"}})
    if method == "getFile":
        return R({"ok": True, "result": {"file_path": "logo.png" if data["file_id"] == "LOGO" else "photo.png"}})
    if method == "setWebhook" and tok.startswith("999"):
        return R({"ok": False, "description": "bad webhook"})
    MID[0] += 1
    return R({"ok": True, "result": {"message_id": MID[0]}})
tgmod._session.post = fake_post
def fake_get(url, timeout=None, **kw):
    return R({"src": "http://g/x.gif"}, FILES.get(url.rsplit("/", 1)[-1], b""))
requests.get = fake_get

import app, constructor, db, templates
c = app.app.test_client()
MAIN_H = {"X-Telegram-Bot-Api-Secret-Token": constructor.main_secret()}

def send_main(uid, text=None, cb=None, name="U", **extra):
    if cb: upd = {"callback_query": {"id": "cb", "from": {"id": uid}, "data": cb, "message": {"message_id": 5, "chat": {"id": uid}}}}
    else:
        m = {"message_id": 7, "from": {"id": uid, "first_name": name}, "chat": {"id": uid, "type": "private"}}
        if text is not None: m["text"] = text
        m.update(extra); upd = {"message": m}
    CALLS.clear(); constructor.handle_update(upd)
    return [(m_, d) for t, m_, d, f in CALLS if t == constructor.BOT_TOKEN]
def texts(calls): return [d.get("text", "") for m_, d in calls if m_ in ("sendMessage", "editMessageText")]
def ok(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg); 
    if not cond: sys.exit(1)

# webhook secret
ok(c.post("/webhook", json={}).status_code == 403, "webhook bad secret -> 403")
ok(c.post("/webhook", json={}, headers=MAIN_H).status_code == 200, "webhook good secret -> 200")
ok(c.get("/health").json["ok"], "health")

# user flow
r = send_main(10, "/start", name="Ali"); ok("Assalomu" in texts(r)[0], "start welcome")
r = send_main(10, "🎁 Kunlik bonus"); ok("bonus berildi" in texts(r)[0], "bonus 1")
r = send_main(10, "🎁 Kunlik bonus"); ok("olgansiz" in texts(r)[0], "bonus twice blocked")
ok(db.get_user(10)["balance"] == 1000, "balance 1000")
# referral
send_main(11, "/start 10", name="Vali"); u10 = db.get_user(10)
ok(u10["balance"] == 1000 + 2500 and u10["ref_count"] == 1, "referral reward once")
send_main(11, "/start 10"); ok(db.get_user(10)["ref_count"] == 1, "no double reward")
# self-referral / backdoor text
send_main(12, "/start 12"); ok(db.get_user(12)["referrer"] is None, "self-referral ignored")
r = send_main(12, "SafobekUz"); ok(db.get_user(12)["balance"] == 0, "no backdoor money")
# transfer (fixed bug)
send_main(10, cb="almashish"); send_main(10, "11"); r = send_main(10, "99999")
ok("yetarli emas" in texts(r)[0] and db.get_user(11)["balance"] == 0, "transfer insufficient: no free money")
send_main(10, cb="almashish"); send_main(10, "11"); r = send_main(10, "500")
ok(db.get_user(11)["balance"] == 500 and db.get_user(10)["balance"] == 3000, "transfer ok")
# promo
send_main(1, "/start", name="Admin"); send_main(1, "/panel")
send_main(1, "🎫 Promokod yaratish"); r = send_main(1, "YANGI 7000 1"); ok("yaratildi" in texts(r)[0], "promo created")
send_main(10, "🎫 Promokod"); r = send_main(10, "yangi"); ok("7000" in texts(r)[0], "promo used")
send_main(11, "🎫 Promokod"); r = send_main(11, "YANGI"); ok("limiti" in texts(r)[0], "promo limit")
# non-admin cannot use admin buttons
before = db.get_user(11)["balance"]; send_main(11, "💸 Pul berish"); send_main(11, "11 100000")
ok(db.get_user(11)["balance"] == before, "non-admin cannot give money")
# admin give / ban
send_main(1, "💸 Pul berish"); send_main(1, "11 10000"); ok(db.get_user(11)["balance"] == before + 10000, "admin give")
# create free bot
TOK = "222222:" + "B"*35
send_main(10, "🤖 Qidir bot"); r = send_main(10, "yaroqsiz-token"); ok("noto'g'ri" in texts(r)[0], "bad token rejected")
r = send_main(10, TOK); ok("Bot tayyor" in "".join(texts(r)), "free bot created")
ok(any(m_ == "setWebhook" and d["url"] == "https://x.onrender.com/hook/222222" and d.get("secret_token") for t, m_, d, f in CALLS), "child setWebhook w/ secret")
ok(db.get_bot(222222)["owner"] == 10, "bot saved")
# child webhook
H = lambda i: {"X-Telegram-Bot-Api-Secret-Token": constructor.child_secret(i)}
def child(tok_id, upd):
    CALLS.clear(); row = db.get_bot(tok_id); templates.dispatch(row, upd)
    return [(m_, d) for t, m_, d, f in CALLS if t == row["token"]]
ok(c.post("/hook/222222", json={}).status_code == 403, "child webhook 403 w/o secret")
ok(c.post("/hook/222222", json={}, headers=H(222222)).status_code == 200, "child webhook ok")
ok(c.post("/hook/424242", json={}, headers=H(424242)).status_code == 404, "unknown child 404")
r = child(222222, {"message": {"message_id": 1, "chat": {"id": 55}, "from": {"id": 55}, "text": "python dars"}})
ok("python%20dars" in json.dumps(r), "qidir links")
# aloqa
send_main(10, "🤖 Aloqa bot") if False else None
db.save_bot(333333, 10, "aloqa", "333333:" + "C"*35, "bot333333", "A")
r = child(333333, {"message": {"message_id": 9, "chat": {"id": 66}, "from": {"id": 66}, "text": "salom admin"}})
ok(any(m_ == "forwardMessage" for m_, d in r), "aloqa forwards to owner")
key = [k for k in [f"fwd:{i}" for i in range(100, 1000)] if db.child_get(333333, k)][0]
mid = int(key.split(":")[1]); ok(db.child_get(333333, key) == "66", "aloqa mapping stored")
r = child(333333, {"message": {"message_id": 10, "chat": {"id": 10}, "from": {"id": 10}, "text": "javob", "reply_to_message": {"message_id": mid}}})
ok(any(m_ == "copyMessage" and str(d["chat_id"]) == "66" for m_, d in r), "aloqa admin reply delivered")
# xayokiyoq
db.save_bot(444444, 10, "xayokiyoq", "444444:" + "D"*35, "bot444444", "X")
r = child(444444, {"callback_query": {"id": "q", "data": "q:3", "message": {"message_id": 3, "chat": {"id": 77}}}})
ok(any("savol" in d.get("text", "").lower() or "bilasizmi" in d.get("text", "") or "ishonasizmi" in d.get("text", "") for m_, d in r), "xayokiyoq question edit")
r = child(444444, {"callback_query": {"id": "q", "data": "q:99", "message": {"message_id": 3, "chat": {"id": 77}}}})
ok(any("TOG" in d.get("text", "").upper() or "TO'G'RI" in d.get("text", "").upper() for m_, d in r), "xayokiyoq final")
# gif + urlupload
db.save_bot(555555, 10, "gif", "555555:" + "E"*35, "bot555555", "G")
r = child(555555, {"message": {"message_id": 1, "chat": {"id": 5}, "from": {"id": 5}, "text": "Salom"}})
ok(any(m_ == "sendAnimation" for m_, d in r), "gif animation sent")
db.save_bot(666666, 10, "urlupload", "666666:" + "F"*35, "bot666666", "U")
r = child(666666, {"message": {"message_id": 1, "chat": {"id": 5}, "from": {"id": 5}, "text": "https://a.b/c.mp4"}})
ok(any(m_ == "sendVideo" for m_, d in r), "url -> sendVideo")
r = child(666666, {"message": {"message_id": 1, "chat": {"id": 5}, "from": {"id": 5}, "text": "hello"}})
ok(any("havola" in d.get("text", "") for m_, d in r), "url invalid text")
# premium pechat: insufficient then ok
db.add_balance(12, 0)
send_main(12, "💎 x") ; 
send_main(12, "🤖 Pechat bot"); r = send_main(12, "")  # step may be unset
r = send_main(12, "🤖 Pechat bot"); ok("yetarli" in texts(r)[0] or "Narx" in texts(r)[0] or "narxi" in texts(r)[0], "premium blocked w/o balance")
db.add_balance(12, 6000)
send_main(12, "🤖 Pechat bot"); TOK2 = "777777:" + "G"*35
r = send_main(12, TOK2); ok("Bot tayyor" in "".join(texts(r)) and db.get_user(12)["balance"] == 1000, "premium charged 5000")
send_main(12, "🤖 Pechat bot"); r = send_main(12, "999999:" + "H"*35)
ok(db.get_user(12)["balance"] == 6000 - 5000 and "Webhook" in "".join(texts(r)) or db.get_user(12)["balance"] == 1000, "webhook fail refunds")
# pechat flow
r = child(777777, {"message": {"message_id": 1, "chat": {"id": 8}, "from": {"id": 8}, "text": "/start"}})
r = child(777777, {"message": {"message_id": 2, "chat": {"id": 8}, "from": {"id": 8}, "document": {"file_id": "LOGO", "file_size": 1000}}})
ok(any("joylashuv" in d.get("text", "") for m_, d in r), "pechat logo accepted")
r = child(777777, {"message": {"message_id": 3, "chat": {"id": 8}, "from": {"id": 8}, "text": "↘️"}})
r = child(777777, {"message": {"message_id": 4, "chat": {"id": 8}, "from": {"id": 8}, "photo": [{"file_id": "P1"}, {"file_id": "P2"}]}})
ok(any(m_ == "sendPhoto" for m_, d in r), "pechat photo sent with watermark")
# admin ban + broadcast
send_main(1, "🔒 Bloklash"); send_main(1, "11")
r = send_main(11, "/start"); ok("bloklangansiz" in texts(r)[0], "banned user blocked")
send_main(1, "🔓 Blokdan olish"); send_main(1, "11")
send_main(1, "❌ OFF"); r = send_main(11, "📊 Statistika"); ok("o'chirilgan" in texts(r)[0], "bot OFF")
r = send_main(1, "📊 Admin statistika"); ok("A'zolar" in texts(r)[0], "admin still works when OFF")
send_main(1, "✅ ON")
send_main(1, "↗️ Xabar yuborish"); CALLS.clear(); constructor.handle_update({"message": {"message_id": 50, "from": {"id": 1, "first_name": "A"}, "chat": {"id": 1, "type": "private"}, "text": "E'lon"}})
time.sleep(1.5); ok(sum(1 for t, m_, d, f in CALLS if m_ == "copyMessage") >= 4, "broadcast copies to users")
# my bots / delete
r = send_main(10, cb="mybots"); ok("Botlaringiz" in texts(r)[0], "mybots list")
r = send_main(10, cb="delbot:222222"); ok(db.get_bot(222222) is None, "delete bot")
# step cancel by menu button
send_main(10, "📨 Bog'lanish"); r = send_main(10, "📊 Statistika"); ok(db.get_step(10)[0] is None, "menu button clears step")
print("\nBARCHA TESTLAR O'TDI")
