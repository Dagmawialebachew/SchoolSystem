# bot/main.py
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
from bot.config import DJANGO_API_URL_DISCONNECT, TELEGRAM_BOT_TOKEN, DJANGO_API_URL_CONNECT
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("the bot is working")
    message_text = update.message.text  # E.g., "/start parent_12" OR "/start disconnect_parent_12"
    
    if len(message_text.split()) > 1:
        param = message_text.split()[1]  # E.g., "parent_12" OR "disconnect_parent_12"
        
        # --- NEW LOGIC FOR DISCONNECT DEEP LINK ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            
            # Use the existing disconnection API
            response = requests.post(DJANGO_API_URL_DISCONNECT, json={"parent_id": parent_id})

            if response.status_code == 200 and response.json().get("success"):
                await update.message.reply_text("❌ Your Telegram has been disconnected from your school account.")
            else:
                await update.message.reply_text("⚠️ Failed to disconnect. Please try again from your profile page.")
            return # Exit after handling disconnect
        # --- END NEW LOGIC ---

        # --- EXISTING CONNECT LOGIC ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            chat_id = update.effective_chat.id

            # Send to Django
            requests.post(DJANGO_API_URL_CONNECT, json={
                "parent_id": parent_id,
                "chat_id": chat_id
            })

            await update.message.reply_text(
                "✅ Your Telegram is now connected to your school account! "
                "**Please refresh your browser page to see the updated status.**"
            )
            return # Exit after handling connect
        
    await update.message.reply_text("👋 Hello! Please open the link from your parent profile to connect or disconnect.")



# Build the bot application
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))


if __name__ == "__main__":
    print("🤖 Bot is running...")
    app.run_polling()  # ✅ PTB v21 handles the event loop
