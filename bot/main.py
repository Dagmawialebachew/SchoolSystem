from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests

DJANGO_API_URL = "https://yourdomain.com/parents/api/save_chat_id/"  # use your domain

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text  # "/start parent_12"
    if len(message_text.split()) > 1:
        param = message_text.split()[1]  # "parent_12"
        parent_id = param.replace("parent_", "")
        chat_id = update.effective_chat.id

        # Send to Django
        requests.post(DJANGO_API_URL, json={
            "parent_id": parent_id,
            "chat_id": chat_id
        })

        await update.message.reply_text("✅ Your Telegram is now connected to your school account!")
    else:
        await update.message.reply_text("👋 Hello! Please open the link from your parent profile to connect.")

app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
