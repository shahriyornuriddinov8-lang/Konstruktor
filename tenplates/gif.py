import requests
from . import register

URL = ("http://www.flamingtext.com/net-fu/image_output.cgi?_comBuyRedirect=false&script=blue-fire"
       "&text={text}&symbol_tagname=popular&fontsize=70&fontname=futura_poster&fontname_tagname=cool"
       "&textBorder=15&growSize=0&antialias=on&hinting=on&justify=2&letterSpacing=0&lineSpacing=0"
       "&textSlant=0&textVerticalSlant=0&textAngle=0&textOutline=off&textOutlineSize=2"
       "&textColor=%230000CC&angle=0&blueFlame=on&framerate=75&frames=5&pframes=5&oframes=4"
       "&distance=2&transparent=off&extAnim=gif&animLoop=on&defaultFrameRate=75&doScale=off"
       "&scaleWidth=240&scaleHeight=120&&_=1469943010141")


@register("gif", "🤖 Gif bot")
def handle(ctx, upd):
    m = upd.get("message")
    if not m or "text" not in m:
        return
    chat, txt = m["chat"]["id"], m["text"]
    ctx.add_member(chat)
    if txt.startswith("/start"):
        ctx.tg.send(chat, "Gif yasash uchun matn yuboring!" + ctx.footer)
        return
    wait = ctx.tg.send(chat, "<b>Yuklanmoqda, kuting...</b>", reply_to_message_id=m["message_id"])
    try:
        r = requests.get(URL.format(text=requests.utils.quote(txt[:40])), timeout=20)
        src = r.json().get("src")
    except Exception:
        src = None
    if wait.get("ok"):
        ctx.tg.delete(chat, wait["result"]["message_id"])
    if src:
        ctx.tg.call("sendAnimation", chat_id=chat, animation=src, caption=f"{txt[:40]} — GIF tayyor!")
    else:
        ctx.tg.send(chat, "❌ Gif yasab bo'lmadi, keyinroq urinib ko'ring.")
