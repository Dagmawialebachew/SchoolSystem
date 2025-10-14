# bot/main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import json
import asyncio
from bot.config import DJANGO_API_URL_DISCONNECT, TELEGRAM_BOT_TOKEN, DJANGO_API_URL_CONNECT
import threading
import time

# --- Telegram Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("the bot is working")
    message_text = update.message.text  # E.g., "/start parent_12" OR "/start disconnect_parent_12"
    
    if len(message_text.split()) > 1:
        param = message_text.split()[1]
        
        # --- DISCONNECT LOGIC ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            
            print(f"BOT: Attempting DISCONNECT API call for parent_id={parent_id}")
            response = requests.post(DJANGO_API_URL_DISCONNECT, json={"parent_id": parent_id})

            # --- CRITICAL LOGGING ---
            print(f"BOT: DISCONNECT API Response Status: {response.status_code}")
            try:
                response_json = response.json()
                print(f"BOT: DISCONNECT API Response JSON: {response_json}")
            except requests.exceptions.JSONDecodeError:
                print(f"BOT: DISCONNECT API Response Text: {response.text}")
                response_json = {"success": False} # Default if response is not valid JSON

            if response.status_code == 200 and response_json.get("success"):
                await update.message.reply_text("❌ Your Telegram has been disconnected from your school account.")
            else:
                await update.message.reply_text("⚠️ Failed to disconnect. Check server logs for API error details.")
            return
        
        # --- CONNECT LOGIC ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            chat_id = update.effective_chat.id

            print(f"BOT: Attempting CONNECT API call for parent_id={parent_id}")
            response = requests.post(DJANGO_API_URL_CONNECT, json={
                "parent_id": parent_id,
                "chat_id": chat_id
            })

            # --- CRITICAL LOGGING ---
            print(f"BOT: CONNECT API Response Status: {response.status_code}")
            try:
                response_json = response.json()
                print(f"BOT: CONNECT API Response JSON: {response_json}")
            except requests.exceptions.JSONDecodeError:
                print(f"BOT: CONNECT API Response Text: {response.text}")
                response_json = {"success": False}

            if response.status_code == 200 and response_json.get("success"):
                await update.message.reply_text("✅ Your Telegram is now connected to your school account! Please refresh your browser page to see the updated status.")
            else:
                await update.message.reply_text("⚠️ Failed to connect. Check server logs for API error details.")
            return
            
    await update.message.reply_text("👋 Hello! Please open the link from your parent profile to connect or disconnect.")

# --- Build the bot application ---
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

from asgiref.sync import async_to_sync # Make sure this is imported if not already

# --- Synchronous processing function for threading ---
def process_update_sync(update_data):
    """Processes a single Telegram update in a synchronous thread."""
    
    # 1. CRITICAL: Ensure the application is initialized in this thread's context
    try:
        # Use a synchronous wrapper to call the async initialize method
        async_to_sync(app.initialize)() 
    except Exception as e:
        # If initialization fails, log it but continue processing
        print(f"THREAD WARNING: App initialization failed: {e}")
        
    try:
        update = Update.de_json(update_data, app.bot)
        
        # 2. Run the main async processing function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.process_update(update))
        loop.close()
        
    except Exception as e:
        # Log the error, but let the thread die quietly
        print(f"THREAD ERROR during process_update: {e}")
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
    WEBHOOK_PATH = "/parents/telegram-webhook/"      # must match Django URL
    WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"
    print(WEBHOOK_URL)

    bot = app.bot
    await bot.delete_webhook()
    await bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook set successfully to: {WEBHOOK_URL}")


# --- For local testing only ---
if __name__ == "__main__":
    print("🤖 Bot running locally (polling mode)")
    app.run_polling()
