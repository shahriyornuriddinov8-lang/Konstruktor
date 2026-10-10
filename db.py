"""Ma'lumotlar bazasi: SQLite (standart) yoki Postgres (DATABASE_URL=postgres://...).

Faqat ikkala bazada ham ishlaydigan oddiy SQL ishlatilgan.
"""
import contextlib
import json
import sqlite3
import threading
import time

from config import DATABASE_URL

IS_PG = DATABASE_URL.startswith("postgresql")
_lock = threading.Lock()  # SQLite uchun yozishni ketma-ket qilish

if IS_PG:
    import psycopg2
    from psycopg2.pool import ThreadedConnectionPool
    _pool = ThreadedConnectionPool(1, 8, DATABASE_URL.replace("+psycopg2", ""))
else:
    _path = DATABASE_URL.replace("sqlite:///", "", 1) or "maker.db"


@contextlib.contextmanager
def _cur():
    """Kursor beradi; muvaffaqiyatda commit, xatoda rollback."""
    if IS_PG:
        conn = _pool.getconn()
        try:
            cur = conn.cursor()
            yield _Cur(cur)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _pool.putconn(conn)
    else:
        with _lock:
            conn = sqlite3.connect(_path, timeout=30)
            try:
                conn.execute("PRAGMA journal_mode=WAL")
                yield _Cur(conn.cursor())
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()


class _Cur:
    def __init__(self, cur):
        self.cur = cur

    def run(self, sql, params=()):
        self.cur.execute(sql.replace("?", "%s") if IS_PG else sql, params)
        return self

    def one(self):
        return self.cur.fetchone()

    def all(self):
        return self.cur.fetchall()

    @property
    def n(self):
        return self.cur.rowcount


def init():
    ddl = [
        """CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY, name TEXT, username TEXT,
            balance BIGINT NOT NULL DEFAULT 0, referrer BIGINT,
            ref_paid INTEGER NOT NULL DEFAULT 0, ref_count INTEGER NOT NULL DEFAULT 0,
            last_bonus TEXT, banned INTEGER NOT NULL DEFAULT 0,
            step TEXT, step_data TEXT, joined BIGINT)""",
        """CREATE TABLE IF NOT EXISTS bots (
            tg_id BIGINT PRIMARY KEY, owner BIGINT, kind TEXT, token TEXT,
            username TEXT, name TEXT, created BIGINT)""",
        "CREATE INDEX IF NOT EXISTS bots_owner ON bots(owner)",
        "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT)",
        """CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY, amount BIGINT, uses_left INTEGER, used_by TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS child_members (
            bot_id BIGINT, user_id BIGINT, PRIMARY KEY (bot_id, user_id))""",
        """CREATE TABLE IF NOT EXISTS child_kv (
            bot_id BIGINT, k TEXT, v TEXT, PRIMARY KEY (bot_id, k))""",
    ]
    with _cur() as c:
        for s in ddl:
            c.run(s)


USER_COLS = ["id", "name", "username", "balance", "referrer", "ref_paid", "ref_count",
             "last_bonus", "banned", "step", "step_data", "joined"]


def _user(row):
    if not row:
        return None
    d = dict(zip(USER_COLS, row))
    d["ref_paid"], d["banned"] = bool(d["ref_paid"]), bool(d["banned"])
    return d


# ---------- users ----------
def get_user(uid):
    with _cur() as c:
        return _user(c.run(f"SELECT {','.join(USER_COLS)} FROM users WHERE id=?", (uid,)).one())


def touch_user(uid, name, username, referrer=None):
    """Foydalanuvchini yaratadi/yangilaydi -> (user, yangi_mi)."""
    with _cur() as c:
        row = c.run(f"SELECT {','.join(USER_COLS)} FROM users WHERE id=?", (uid,)).one()
        if row:
            c.run("UPDATE users SET name=?, username=? WHERE id=?", (name, username, uid))
            u = _user(row)
            u.update(name=name, username=username)
            return u, False
        ref = referrer if referrer and referrer != uid else None
        if ref and not c.run("SELECT 1 FROM users WHERE id=?", (ref,)).one():
            ref = None
        c.run("INSERT INTO users (id,name,username,balance,referrer,ref_paid,ref_count,banned,joined)"
              " VALUES (?,?,?,0,?,0,0,0,?)", (uid, name, username, ref, int(time.time())))
        return _user(c.run(f"SELECT {','.join(USER_COLS)} FROM users WHERE id=?", (uid,)).one()), True


def set_step(uid, step=None, data=None):
    with _cur() as c:
        c.run("UPDATE users SET step=?, step_data=? WHERE id=?",
              (step, json.dumps(data) if data is not None else None, uid))


def get_step(uid):
    u = get_user(uid)
    if not u or not u.get("step"):
        return None, None
    return u["step"], (json.loads(u["step_data"]) if u.get("step_data") else None)


def add_balance(uid, delta):
    with _cur() as c:
        c.run("UPDATE users SET balance=balance+? WHERE id=?", (delta, uid))
        r = c.run("SELECT balance FROM users WHERE id=?", (uid,)).one()
        return r[0] if r else None


def take_balance(uid, amount):
    """Yetarli bo'lsa atomik ayiradi."""
    with _cur() as c:
        return c.run("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?",
                     (amount, uid, amount)).n == 1


def transfer(src, dst, amount):
    with _cur() as c:
        if not c.run("SELECT 1 FROM users WHERE id=?", (dst,)).one():
            return "nouser"
        if c.run("UPDATE users SET balance=balance-? WHERE id=? AND balance>=?",
                 (amount, src, amount)).n != 1:
            return "nomoney"
        c.run("UPDATE users SET balance=balance+? WHERE id=?", (amount, dst))
        return "ok"


def set_banned(uid, flag):
    with _cur() as c:
        return c.run("UPDATE users SET banned=? WHERE id=?", (1 if flag else 0, uid)).n


def claim_ref_reward(uid):
    """Taklif mukofoti bir marta: taklif qilgan ID yoki None."""
    with _cur() as c:
        r = c.run("SELECT referrer, ref_paid FROM users WHERE id=?", (uid,)).one()
        if not r or not r[0] or r[1]:
            return None
        if c.run("UPDATE users SET ref_paid=1 WHERE id=? AND ref_paid=0", (uid,)).n != 1:
            return None
        return r[0]


def inc_ref(uid, price):
    with _cur() as c:
        c.run("UPDATE users SET balance=balance+?, ref_count=ref_count+1 WHERE id=?", (price, uid))


def claim_bonus(uid, today, amount):
    with _cur() as c:
        return c.run("UPDATE users SET last_bonus=?, balance=balance+? WHERE id=? "
                     "AND (last_bonus IS NULL OR last_bonus<>?)", (today, amount, uid, today)).n == 1


def top_users(n=10):
    with _cur() as c:
        return [tuple(r) for r in c.run(
            "SELECT id,name,balance FROM users ORDER BY balance DESC LIMIT ?", (n,)).all()]


def all_user_ids():
    with _cur() as c:
        return [r[0] for r in c.run("SELECT id FROM users").all()]


def count_users():
    with _cur() as c:
        return c.run("SELECT COUNT(*) FROM users").one()[0]


# ---------- kv ----------
def kv_get(k, default=None):
    with _cur() as c:
        r = c.run("SELECT v FROM kv WHERE k=?", (k,)).one()
        return r[0] if r else default


def kv_set(k, v):
    with _cur() as c:
        c.run("INSERT INTO kv (k,v) VALUES (?,?) ON CONFLICT (k) DO UPDATE SET v=excluded.v",
              (k, str(v)))


def kv_incr(k, n=1):
    kv_set(k, int(kv_get(k, 0) or 0) + n)


# ---------- bots ----------
BOT_COLS = ["tg_id", "owner", "kind", "token", "username", "name", "created"]


def save_bot(tg_id, owner, kind, token, username, name):
    """Yangi bo'lsa True, yangilangan bo'lsa False."""
    with _cur() as c:
        if c.run("SELECT 1 FROM bots WHERE tg_id=?", (tg_id,)).one():
            c.run("UPDATE bots SET owner=?,kind=?,token=?,username=?,name=? WHERE tg_id=?",
                  (owner, kind, token, username, name, tg_id))
            return False
        c.run("INSERT INTO bots (tg_id,owner,kind,token,username,name,created) VALUES (?,?,?,?,?,?,?)",
              (tg_id, owner, kind, token, username, name, int(time.time())))
        return True


def get_bot(tg_id):
    with _cur() as c:
        r = c.run(f"SELECT {','.join(BOT_COLS)} FROM bots WHERE tg_id=?", (tg_id,)).one()
        return dict(zip(BOT_COLS, r)) if r else None


def bots_of(owner):
    with _cur() as c:
        return [dict(zip(BOT_COLS, r)) for r in
                c.run(f"SELECT {','.join(BOT_COLS)} FROM bots WHERE owner=?", (owner,)).all()]


def delete_bot(tg_id, owner):
    with _cur() as c:
        return c.run("DELETE FROM bots WHERE tg_id=? AND owner=?", (tg_id, owner)).n


# ---------- promokod ----------
def create_promo(code, amount, uses):
    with _cur() as c:
        if c.run("SELECT 1 FROM promos WHERE code=?", (code,)).one():
            return False
        c.run("INSERT INTO promos (code,amount,uses_left,used_by) VALUES (?,?,?,'')",
              (code, amount, uses))
        return True


def use_promo(code, uid):
    """('ok', summa) | ('none'|'used'|'empty', 0)"""
    with _cur() as c:
        r = c.run("SELECT amount, uses_left, used_by FROM promos WHERE code=?", (code,)).one()
        if not r:
            return "none", 0
        amount, left, used_by = r
        used = [x for x in (used_by or "").split(",") if x]
        if str(uid) in used:
            return "used", 0
        if left <= 0:
            return "empty", 0
        used.append(str(uid))
        if c.run("UPDATE promos SET uses_left=uses_left-1, used_by=? WHERE code=? AND uses_left>0",
                 (",".join(used), code)).n != 1:
            return "empty", 0
        c.run("UPDATE users SET balance=balance+? WHERE id=?", (amount, uid))
        return "ok", amount


# ---------- yaratilgan botlar uchun ----------
def child_add_member(bot_id, uid):
    with _cur() as c:
        if c.run("SELECT 1 FROM child_members WHERE bot_id=? AND user_id=?", (bot_id, uid)).one():
            return False
        c.run("INSERT INTO child_members (bot_id,user_id) VALUES (?,?)", (bot_id, uid))
        return True


def child_members_list(bot_id):
    with _cur() as c:
        return [r[0] for r in c.run("SELECT user_id FROM child_members WHERE bot_id=?", (bot_id,)).all()]


def child_get(bot_id, k, default=None):
    with _cur() as c:
        r = c.run("SELECT v FROM child_kv WHERE bot_id=? AND k=?", (bot_id, k)).one()
        return r[0] if r else default


def child_set(bot_id, k, v):
    with _cur() as c:
        c.run("INSERT INTO child_kv (bot_id,k,v) VALUES (?,?,?) "
              "ON CONFLICT (bot_id,k) DO UPDATE SET v=excluded.v", (bot_id, k, str(v)))


def child_del(bot_id, k):
    with _cur() as c:
        c.run("DELETE FROM child_kv WHERE bot_id=? AND k=?", (bot_id, k))
