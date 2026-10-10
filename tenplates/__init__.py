"""Shablon botlar reyestri.

Yangi shablon qo'shish: shu papkada fayl yarating, `@register(...)` bilan
`handle(ctx, update)` funksiyasini belgilang va quyida import qiling.
"""
from dataclasses import dataclass
from typing import Callable

import db
from config import MAKER_USERNAME
from tg import TG


@dataclass
class Template:
    kind: str
    title: str          # menyudagi tugma matni
    handler: Callable
    premium: bool = False


REGISTRY = {}


def register(kind, title, premium=False):
    def deco(fn):
        REGISTRY[kind] = Template(kind, title, fn, premium)
        return fn
    return deco


def by_title(title):
    for t in REGISTRY.values():
        if t.title == title:
            return t
    return None


class Ctx:
    """Yaratilgan bot uchun kontekst (PHP'dagi API_TOKEN / ADMIN_ID o'rnida)."""

    def __init__(self, bot_row):
        self.bot_id = bot_row["tg_id"]
        self.owner = bot_row["owner"]
        self.username = bot_row["username"]
        self.tg = TG(bot_row["token"])

    @property
    def footer(self):
        return f"\n\n🤖 @{MAKER_USERNAME} yordamida yaratilgan" if MAKER_USERNAME else ""

    def is_owner(self, uid):
        return int(uid) == int(self.owner)

    def add_member(self, uid):
        return db.child_add_member(self.bot_id, uid)

    def members(self):
        return db.child_members_list(self.bot_id)

    def get(self, k, d=None):
        return db.child_get(self.bot_id, k, d)

    def set(self, k, v):
        db.child_set(self.bot_id, k, v)

    def delete(self, k):
        db.child_del(self.bot_id, k)


def dispatch(bot_row, update):
    t = REGISTRY.get(bot_row["kind"])
    if t:
        t.handler(Ctx(bot_row), update)


# shablonlarni import qilish (ro'yxatdan o'tadi)
from . import qidir, aloqa, xayokiyoq, gif, urlupload, pechat  # noqa: E402,F401
