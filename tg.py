import json
import logging
import requests

log = logging.getLogger("tg")
_session = requests.Session()


class TG:
    """Telegram Bot API uchun yupqa qobiq (PHP'dagi bot() funksiyasi o'rnida)."""

    def __init__(self, token):
        self.token = token
        self.base = f"https://api.telegram.org/bot{token}/"

    def call(self, method, files=None, timeout=25, **params):
        for k, v in list(params.items()):
            if v is None:
                del params[k]
            elif isinstance(v, (dict, list)):
                params[k] = json.dumps(v, ensure_ascii=False)
        try:
            r = _session.post(self.base + method, data=params, files=files, timeout=timeout)
            return r.json()
        except Exception as e:  # tarmoq xatosi
            log.warning("TG %s xato: %s", method, e)
            return {"ok": False, "description": str(e)}

    # --- qulay yordamchilar ---
    def send(self, chat_id, text, reply_markup=None, parse_mode="HTML", **kw):
        return self.call("sendMessage", chat_id=chat_id, text=text,
                         parse_mode=parse_mode, reply_markup=reply_markup,
                         disable_web_page_preview=True, **kw)

    def edit(self, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
        return self.call("editMessageText", chat_id=chat_id, message_id=message_id,
                         text=text, parse_mode=parse_mode, reply_markup=reply_markup,
                         disable_web_page_preview=True)

    def answer_cb(self, cb_id, text=None, alert=False):
        return self.call("answerCallbackQuery", callback_query_id=cb_id,
                         text=text, show_alert=alert)

    def delete(self, chat_id, message_id):
        return self.call("deleteMessage", chat_id=chat_id, message_id=message_id)

    def me(self):
        r = self.call("getMe", timeout=10)
        return r.get("result") if r.get("ok") else None


# --- klaviatura yordamchilari ---
def reply_kb(rows, resize=True):
    return {"keyboard": [[{"text": t} for t in row] for row in rows], "resize_keyboard": resize}


def inline_kb(rows):
    """rows: [[(text, 'cb:data' yoki 'url:https://..'), ...], ...]"""
    out = []
    for row in rows:
        r = []
        for text, target in row:
            if target.startswith("url:"):
                r.append({"text": text, "url": target[4:]})
            else:
                r.append({"text": text, "callback_data": target})
        out.append(r)
    return {"inline_keyboard": out}


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
