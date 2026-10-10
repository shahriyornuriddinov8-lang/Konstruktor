import json
from . import register

START = ("🥳 Assalomu alaykum!\n🤔 Biz bilan bog'lana olmadingizmi?\n"
         "🙄 Xafa bo'lmang — biz buning yo'lini topdik!\n"
         "🤗 Savolingiz bo'lsa, marhamat yozib qoldiring, tez orada javob beramiz.\n"
         "🤖 Bot obunachilari: /stat")


@register("aloqa", "🤖 Aloqa bot")
def handle(ctx, upd):
    m = upd.get("message")
    if not m:
        return
    chat, txt = m["chat"]["id"], m.get("text", "")
    uid = m["from"]["id"]

    if ctx.is_owner(uid):
        # Admin foydalanuvchi xabariga reply qilsa — javob yetkaziladi
        rep = m.get("reply_to_message")
        if txt == "/stat":
            ctx.tg.send(chat, f"📊 Obunachilar: <b>{len(ctx.members())}</b> ta")
        elif rep:
            target = ctx.get(f"fwd:{rep['message_id']}")
            if target:
                ctx.tg.call("copyMessage", chat_id=int(target), from_chat_id=chat,
                            message_id=m["message_id"])
                ctx.tg.send(chat, "✅ Javob yuborildi.")
            else:
                ctx.tg.send(chat, "⚠️ Bu xabar egasi topilmadi.")
        elif txt.startswith("/start"):
            ctx.tg.send(chat, "👑 Admin: foydalanuvchi xabariga <b>reply</b> qilib javob yozing.\n/stat — statistika")
        return

    ctx.add_member(chat)
    if txt == "/stat":
        ctx.tg.send(chat, f"📊 Obunachilar: <b>{len(ctx.members())}</b> ta")
        return
    if txt.startswith("/start"):
        ctx.tg.send(chat, START)
        return
    # foydalanuvchi xabarini adminga uzatish
    r = ctx.tg.call("forwardMessage", chat_id=ctx.owner, from_chat_id=chat,
                    message_id=m["message_id"])
    if r.get("ok"):
        ctx.set(f"fwd:{r['result']['message_id']}", chat)
        ctx.tg.send(chat, "✅ Xabaringiz adminga yuborildi. Tez orada javob olasiz.")
