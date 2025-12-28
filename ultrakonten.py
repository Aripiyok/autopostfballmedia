import os
import time
import random
import requests
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument
)

# ===============================
# LOAD ENV
# ===============================
load_dotenv(dotenv_path="/root/autopostfb/.env", override=True)

TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_CHANNEL = int(os.getenv("TG_CHANNEL"))

FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_PAGE_TOKEN = os.getenv("FB_PAGE_TOKEN")

POST_DELAY_MINUTES = int(os.getenv("POST_DELAY_MINUTES", "60"))
POST_DELAY_SECONDS = POST_DELAY_MINUTES * 60

# ===============================
# PATHS
# ===============================
BASE_DIR = "/root/autopostfb"
SESSION_DIR = os.path.join(BASE_DIR, "session")
IMG_DIR = os.path.join(BASE_DIR, "images")
LAST_ID_FILE = os.path.join(BASE_DIR, "last_id.txt")
LAST_TIME_FILE = os.path.join(BASE_DIR, "last_post_time.txt")

os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

SESSION_PATH = os.path.join(SESSION_DIR, "ultra")

# ===============================
# TELEGRAM CLIENT (GLOBAL)
# ===============================
client = TelegramClient(SESSION_PATH, TG_API_ID, TG_API_HASH)

# ===============================
# HELPERS
# ===============================
def load_last_id():
    if not os.path.exists(LAST_ID_FILE):
        return 0
    return int(open(LAST_ID_FILE).read().strip() or 0)

def save_last_id(msg_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(msg_id))

def load_last_post_time():
    if not os.path.exists(LAST_TIME_FILE):
        return 0
    return int(open(LAST_TIME_FILE).read().strip() or 0)

def save_last_post_time(ts):
    with open(LAST_TIME_FILE, "w") as f:
        f.write(str(ts))

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
        if isinstance(msg.media, MessageMediaDocument):
            if msg.video:
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
    await client.start()
    print("🚀 BOT AUTOPOST 24 JAM AKTIF")

    while True:
        try:
            await process_once()
        except Exception as e:
            print("❌ ERROR:", e)

        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
