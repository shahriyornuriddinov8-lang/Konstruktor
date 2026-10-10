import os


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = _int("ADMIN_ID", 0)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@admin")

# Render avtomatik RENDER_EXTERNAL_URL beradi
BASE_URL = (os.getenv("BASE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "o'zgartiring-bu-kalitni")

# Majburiy obuna kanali (ixtiyoriy). CHANNEL_ID: -100xxxxxxxxxx
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").lstrip("@")
# Yangi a'zo / yangi bot haqida xabar boradigan chat (ixtiyoriy)
LOG_CHAT_ID = os.getenv("LOG_CHAT_ID", "")

BOT_PRICE = _int("BOT_PRICE", 5000)            # premium bot narxi (UZS)
REFERAL_PRICE = _int("REFERAL_PRICE", 2500)    # bitta taklif uchun (UZS)
DAILY_BONUS = _int("DAILY_BONUS", 1000)        # kunlik bonus (UZS)
TZ_OFFSET_HOURS = _int("TZ_OFFSET_HOURS", 5)   # O'zbekiston UTC+5

PAYMENT_INFO = os.getenv(
    "PAYMENT_INFO",
    "💳 Karta: 8600 0000 0000 0000\n📝 Izoh: sizning ID raqamingiz",
)

# Bazani saqlash: Render bepul diski vaqtinchalik! Neon/Supabase Postgres URL tavsiya etiladi.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///maker.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

MAKER_USERNAME = os.getenv("MAKER_USERNAME", "")  # yaratilgan botlar pastida ko'rinadi
