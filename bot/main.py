# bot/main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import json
import asyncio
from bot.config import DJANGO_API_URL_DISCONNECT, TELEGRAM_BOT_TOKEN, DJANGO_API_URL_CONNECT

# --- Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("the bot is working")
    message_text = update.message.text  # E.g., "/start parent_12" OR "/start disconnect_parent_12"
    
    if len(message_text.split()) > 1:
        param = message_text.split()[1]  # E.g., "parent_12" OR "disconnect_parent_12"
        
        # --- DISCONNECT LOGIC ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            response = requests.post(DJANGO_API_URL_DISCONNECT, json={"parent_id": parent_id})

            if response.status_code == 200 and response.json().get("success"):
                await update.message.reply_text("❌ Your Telegram has been disconnected from your school account.")
            else:
                await update.message.reply_text("⚠️ Failed to disconnect. Please try again from your profile page.")
            return
        
        # --- CONNECT LOGIC ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            chat_id = update.effective_chat.id

            requests.post(DJANGO_API_URL_CONNECT, json={
                "parent_id": parent_id,
                "chat_id": chat_id
            })

            await update.message.reply_text(
                "✅ Your Telegram is now connected to your school account! "
                "Please refresh your browser page to see the updated status."
            )
            return
        
    await update.message.reply_text("👋 Hello! Please open the link from your parent profile to connect or disconnect.")


# --- Build the bot application ---
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))


# --- Helper function for Django webhook ---
def run_async(update):
    """Run Telegram async updates inside Django's synchronous environment."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app.process_update(update))
    loop.close()


# --- Webhook setup function (run once in console) ---
import asyncio

async def setup_webhook():
    """Sets Telegram webhook to your PythonAnywhere domain"""
    DOMAIN = "schoolsys.pythonanywhere.com"  # ✅ your actual domain
    WEBHOOK_PATH = "parents/telegram-webhook/"      # must match Django URL
    WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

    bot = app.bot
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook set successfully to: {WEBHOOK_URL}")


# --- For local testing only ---
if __name__ == "__main__":
    print("🤖 Bot running locally (polling mode)")
    app.run_polling()
