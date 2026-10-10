import hmac
import logging
import os
import threading
import time

import requests
from flask import Flask, abort, jsonify, request

import constructor
import db
import templates
from config import BASE_URL, BOT_TOKEN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

app = Flask(__name__)
db.init()


def _setup():
    if BOT_TOKEN and BASE_URL:
        r = constructor.restore_main_webhook()
        log.info("Asosiy webhook: %s", r)
    else:
        log.warning("BOT_TOKEN yoki BASE_URL sozlanmagan — webhook o'rnatilmadi")


def _keepalive():
    """Render bepul tarifida 15 daqiqa so'rovsiz uxlab qolmasligi uchun o'z-o'zini chaqiradi."""
    if not BASE_URL or os.getenv("KEEPALIVE", "1") != "1":
        return
    while True:
        time.sleep(600)
        try:
            requests.get(BASE_URL + "/health", timeout=15)
        except Exception:
            pass


threading.Thread(target=_setup, daemon=True).start()
threading.Thread(target=_keepalive, daemon=True).start()


def _ok_secret(expected):
    got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    return hmac.compare_digest(got, expected)


@app.get("/")
def index():
    return "Bot konstruktor ishlayapti ✅"


@app.get("/health")
def health():
    return jsonify(ok=True, shablonlar=sorted(templates.REGISTRY))


@app.post("/webhook")
def main_webhook():
    if not _ok_secret(constructor.main_secret()):
        abort(403)
    upd = request.get_json(silent=True) or {}
    threading.Thread(target=constructor.handle_update, args=(upd,), daemon=True).start()
    return "ok"


@app.post("/hook/<int:bot_id>")
def child_webhook(bot_id):
    if not _ok_secret(constructor.child_secret(bot_id)):
        abort(403)
    row = db.get_bot(bot_id)
    if not row:
        abort(404)
    upd = request.get_json(silent=True) or {}

    def run():
        try:
            templates.dispatch(row, upd)
        except Exception:
            log.exception("shablon xatosi (%s)", row["kind"])

    threading.Thread(target=run, daemon=True).start()
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
