import os
import time
import random
import requests
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument
)

# ===============================
# BASE DIR (KUNCI KE FOLDER INI)
# ===============================
BASE_DIR = Path(__file__).parent

# ===============================
# LOAD ENV (KHUSUS FOLDER INI)
# ===============================
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_CHANNEL = int(os.getenv("TG_CHANNEL"))

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

POST_DELAY_MINUTES = int(os.getenv("POST_DELAY_MINUTES", "60"))
POST_DELAY_SECONDS = POST_DELAY_MINUTES * 60

print("=== ACTIVE FB PAGE ID ===", FB_PAGE_ID)

# ===============================
# PATHS (SEMUA PER FOLDER)
# ===============================
SESSION_DIR = BASE_DIR / "sessions"
IMG_DIR = BASE_DIR / "images"
LAST_ID_FILE = BASE_DIR / "last_id.txt"
LAST_TIME_FILE = BASE_DIR / "last_post_time.txt"

SESSION_DIR.mkdir(exist_ok=True)
IMG_DIR.mkdir(exist_ok=True)

# 👉 SESSION KHUSUS PAGE 2 (OTP AKAN MUNCUL)
SESSION_PATH = SESSION_DIR / "page2"

# ===============================
# TELEGRAM CLIENT (SESSION TERKUNCI)
# ===============================
client = TelegramClient(str(SESSION_PATH), TG_API_ID, TG_API_HASH)

# ===============================
# HELPERS
# ===============================
def load_last_id():
    if not LAST_ID_FILE.exists():
        return 0
    return int(LAST_ID_FILE.read_text().strip() or 0)

def save_last_id(msg_id):
    LAST_ID_FILE.write_text(str(msg_id))

def load_last_post_time():
    if not LAST_TIME_FILE.exists():
        return 0
    return int(LAST_TIME_FILE.read_text().strip() or 0)

def save_last_post_time(ts):
    LAST_TIME_FILE.write_text(str(ts))

# ===============================
# FACEBOOK API
# ===============================
def upload_photo(image_path, caption):
    url = f"https://graph.facebook.com/v24.0/{FB_PAGE_ID}/photos"
    with open(image_path, "rb") as f:
        r = requests.post(
            url,
            files={"source": f},
            data={
                "caption": caption,
                "access_token": FB_PAGE_TOKEN
            },
            timeout=120
        )
    print("📤 FB PHOTO RESPONSE:", r.text)
    return r.ok

def upload_video(video_path, caption):
    url = f"https://graph.facebook.com/v24.0/{FB_PAGE_ID}/videos"
    with open(video_path, "rb") as f:
        r = requests.post(
            url,
            files={"source": f},
            data={
                "description": caption,
                "access_token": FB_PAGE_TOKEN
            },
            timeout=600
        )
    print("📤 FB VIDEO RESPONSE:", r.text)
    return r.ok

# ===============================
# MAIN LOGIC
# ===============================
async def process_once():
    now = int(time.time())
    last_post_time = load_last_post_time()

    if now - last_post_time < POST_DELAY_SECONDS:
        wait = POST_DELAY_SECONDS - (now - last_post_time)
        print(f"⏳ Belum waktunya posting. Sisa {wait//60} menit")
        return

    last_id = load_last_id()
    print("🔁 Last posted ID:", last_id)

    async for msg in client.iter_messages(TG_CHANNEL, reverse=True):
        if msg.id <= last_id:
            continue

        caption = (msg.text or msg.message or "").strip()

        # ===============================
        # FOTO
        # ===============================
        if isinstance(msg.media, MessageMediaPhoto):
            print(f"📸 FOTO MSG ID {msg.id}")
            path = await msg.download_media(file=IMG_DIR)

            if upload_photo(path, caption):
                save_last_id(msg.id)
                save_last_post_time(int(time.time()))
                os.remove(path)
                print("✅ FOTO POST BERHASIL")
                return

            os.remove(path)

        # ===============================
        # VIDEO
        # ===============================
        if isinstance(msg.media, MessageMediaDocument) and msg.video:
            print(f"🎞️ VIDEO MSG ID {msg.id}")
            path = await msg.download_media(file=IMG_DIR)

            if upload_video(path, caption):
                save_last_id(msg.id)
                save_last_post_time(int(time.time()))
                os.remove(path)
                print("✅ VIDEO POST BERHASIL")
                return

            os.remove(path)

    print("⚠️ Tidak ada konten baru yang bisa dipost")

# ===============================
# RUN 24 JAM
# ===============================
async def main():
    await client.start()  # ← DI SINI OTP AKAN MUNCUL
    print("🚀 BOT AUTOPOST 24 JAM AKTIF")

    while True:
        try:
            await process_once()
        except Exception as e:
            print("❌ ERROR:", e)

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
