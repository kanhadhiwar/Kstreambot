from fastapi import FastAPI, Response
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
import requests, threading, os
from pathlib import Path
import uvicorn
import asyncio

BOT_TOKEN = "8514360406:AAFXSwI_b9SkLIJ7WcGquQy28z3aCS5jq6Q"
OWNER_ID = 7624032394   # <-- Yaha apna Telegram ID daalo (@userinfobot se milega)

VIDEO_DIR = "videos"
BASE_URL = os.getenv("KOYEB_APP_URL")   # Koyeb me env variable set karoge

os.makedirs(VIDEO_DIR, exist_ok=True)

app = FastAPI()

# -------------------------
#  STREAM ENDPOINT
# -------------------------
@app.get("/watch/{filename}")
def stream_file(filename: str):
    path = Path(VIDEO_DIR) / filename
    if not path.exists():
        return Response("❌ File not found", status_code=404)
    data = open(path, "rb").read()
    return Response(data, media_type="video/mp4")


# -------------------------
#  BACKGROUND DOWNLOAD
# -------------------------
def background_download(url, filename):
    save_path = Path(VIDEO_DIR) / filename
    r = requests.get(url, stream=True)
    with open(save_path, "wb") as f:
        for chunk in r.iter_content(1024 * 256):
            if chunk:
                f.write(chunk)


# -------------------------
#  HANDLE VIDEO
# -------------------------
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message

    file = msg.video or msg.document
    if not file:
        await msg.reply_text("❌ Only videos supported.")
        return

    file_id = file.file_id
    unique = file.file_unique_id + ".mp4"

    # Get Telegram CDN URL
    info = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
    ).json()

    if not info.get("ok"):
        await msg.reply_text("❌ Failed to get file info.")
        return

    file_path = info["result"]["file_path"]
    cdn_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

    stream_url = f"{BASE_URL}/watch/{unique}"

    # Send Instant Link
    await msg.reply_text(
        f"🎬 **Your Streaming Link Ready!**\n\n▶️ {stream_url}",
        parse_mode="Markdown"
    )

    # Background download
    threading.Thread(target=background_download, args=(cdn_url, unique)).start()


# -------------------------
#  /start Command
# -------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 **Hello!**\nSend or Forward any video and I will give you a Streaming Link 🎬",
        parse_mode="Markdown"
    )


# -------------------------
#  BOT START HELLO MESSAGE
# -------------------------
async def on_start(bot):
    await bot.send_message(
        OWNER_ID,
        "✅ *Bot Started Successfully!*\nReady to generate streaming links 🚀",
        parse_mode="Markdown"
    )


def start_bot():
    tg = Application.builder().token(BOT_TOKEN).build()

    tg.add_handler(CommandHandler("start", start_cmd))
    tg.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle))

    tg.post_init = lambda app: on_start(app.bot)

    tg.run_polling()


threading.Thread(target=start_bot).start()


# -------------------------
#  RUN SERVER (KOYEB)
# -------------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
