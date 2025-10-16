import threading
from asgiref.sync import async_to_sync, sync_to_async 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, MenuButton, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, Application
from telegram.constants import ParseMode, ChatAction
import asyncio
import aiohttp
import logging
import re

import os
import django
from django.apps import apps 

# Point to your Django settings module
# We ensure the environment variable is set for both top-level imports and later threaded execution.
if not os.getenv("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")

# --- CRITICAL FIX: DO NOT CALL django.setup() at the top level. ---
# This often conflicts with PythonAnywhere's WSGI loader, causing silent crashes.
# We will rely on the setup inside process_update_sync where it is needed for threads.

# IMPORTANT: These imports must be configured in your bot/config.py
from bot.config import (
    DJANGO_API_URL_DISCONNECT,
    TELEGRAM_BOT_TOKEN,
    DJANGO_API_URL_CONNECT,
    DJANGO_API_URL_FEE,
    WEB_APP_BASE_URL # Must be set to 'http://schoolsys.pythonanywhere.com'
)

# NOTE: Model import is safe ONLY if the model is not accessed before django.setup() is called.
# The _get_parent_id_from_persistence uses aget (async access), which relies on a running loop.
# We trust that the Django environment will be fully loaded by the time we call these ORM functions.
from parents.models import ParentProfile

# ----------------------
# Logging setup
# ----------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------
# Persistence using Async Django ORM
# ----------------------
async def _get_parent_id_from_persistence(chat_id: int) -> str | None:
    """Look up the parent_id from the ParentProfile model using chat_id."""
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        return str(parent.id)
    except ParentProfile.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting parent ID from DB: {e}")
        return None

async def _set_parent_id_in_persistence(chat_id: int, parent_id: str) -> None:
    """Store the chat_id on the ParentProfile record."""
    try:
        parent = await ParentProfile.objects.aget(id=parent_id)
        parent.telegram_chat_id = str(chat_id)
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        logger.warning(f"ParentProfile with ID {parent_id} not found during connection.")
        pass
    except Exception as e:
        logger.error(f"Error setting parent ID in DB: {e}")

async def _delete_parent_id_from_persistence(chat_id: int) -> None:
    """Remove the chat_id from the ParentProfile record."""
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        parent.telegram_chat_id = None
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error deleting parent ID from DB: {e}")

# ----------------------
# Utility Functions
# ----------------------

def escape_markdown_v2(text: str) -> str:
    """Escapes special characters in MarkdownV2 to prevent formatting errors."""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

# ----------------------
# Helper: Function to generate a single student summary message and buttons
# ----------------------
def _generate_student_summary(s: dict) -> tuple[str, InlineKeyboardMarkup]:
    """Generates the message and inline keyboard for a single student summary."""
    student_id = s.get("student_id", "N/A")

    student_name = escape_markdown_v2(s.get("student_name", "Student N/A"))

    # --- Handle unpaid total ---
    raw_unpaid = s.get("total_unpaid", s.get("total", 0))
    try:
        unpaid_amount = float(raw_unpaid)
    except (ValueError, TypeError):
        unpaid_amount = 0

    if unpaid_amount.is_integer():
        formatted_unpaid = f"{int(unpaid_amount):,}"
    else:
        formatted_unpaid = f"{unpaid_amount:,.2f}"
    formatted_unpaid = escape_markdown_v2(formatted_unpaid)

    # --- Handle paid total (new) ---
    raw_paid = s.get("total_paid", 0)
    try:
        paid_amount = float(raw_paid)
    except (ValueError, TypeError):
        paid_amount = 0

    if paid_amount.is_integer():
        formatted_paid = f"{int(paid_amount):,}"
    else:
        formatted_paid = f"{paid_amount:,.2f}"
    formatted_paid = escape_markdown_v2(formatted_paid)

    # --- Nearest due ---
    nearest_due = escape_markdown_v2(s.get("nearest_due", "N/A"))

    # --- Build the message ---
    message = (
        f"📚 *{student_name}*\n\n"
        f"💵 *Unpaid Invoices:* {s.get('count', 0)}\n\n"
        f"💰 *Total Unpaid:* {formatted_unpaid} ETB\n\n"
        f"✅ *Total Paid:* {formatted_paid} ETB\n\n"
        f"📅 *Nearest Due:* {nearest_due}"
    )

    # --- Inline buttons (Using WEB_APP_BASE_URL) ---
    buttons = [
    [
        InlineKeyboardButton("🔍 View Invoices", callback_data=f"view_invoices_{student_id}"),
        InlineKeyboardButton("📑 Details", url=f"{WEB_APP_BASE_URL}/parents/kids/{student_id}"),
    ],
    [
        InlineKeyboardButton("💳 Pay", url=f"{WEB_APP_BASE_URL}/parents/fees/child/{student_id}"),
    ]
]

    return message, InlineKeyboardMarkup(buttons)
# ----------------------
# Telegram Bot Handlers
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Bot received /start")
    message_text = update.message.text
    chat_id = update.effective_chat.id
    
    if len(message_text.split()) > 1:
        param = message_text.split()[1]

        # --- DISCONNECT LOGIC ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            await handle_disconnect(update, parent_id)
            await _delete_parent_id_from_persistence(chat_id)
            return

        # --- CONNECT LOGIC ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            await handle_connect(update, parent_id, chat_id)
            # Update the local persistence (Django model) state after the API confirms
            await _set_parent_id_in_persistence(chat_id, parent_id)
            return
        
    await update.message.reply_text(
        "👋 Hello\\! Please open the link from your parent profile to connect or disconnect\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )


# ----------------------
# CONNECT / DISCONNECT HANDLERS
# ----------------------
async def handle_connect(update, parent_id, chat_id):
    logger.info(f"Attempting CONNECT for parent {parent_id} with chat_id {chat_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    async with aiohttp.ClientSession() as session:
        try:
            # The API call must ensure the chat_id is stored against the parent_id in the Django DB
            async with session.post(DJANGO_API_URL_CONNECT, json={"parent_id": parent_id, "chat_id": chat_id}) as resp:
                resp_json = {}
                if resp.content_type and 'json' in resp.content_type:
                    resp_json = await resp.json()
                
                if resp.status == 200 and resp_json.get("success"):
                    await update.message.reply_text(
                        "✅ Your Telegram is now connected to your school account\\! "
                        "You can now use commands like /fees\\. "
                        "Please refresh your browser page to see the updated status\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    error_msg = resp_json.get("error", "API error details not provided\\.")
                    await update.message.reply_text(f"⚠️ Failed to connect\\. API Status: {resp.status}\\. Details: {escape_markdown_v2(error_msg)}")
        except Exception as e:
            logger.exception(f"Error connecting parent {parent_id}: {e}")
            await update.message.reply_text("⚠️ Unexpected error during connection\\.")


async def handle_disconnect(update, parent_id):
    logger.info(f"Attempting DISCONNECT for parent {parent_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    async with aiohttp.ClientSession() as session:
        try:
            # The API call must remove the chat_id from the parent_id in the Django DB
            async with session.post(DJANGO_API_URL_DISCONNECT, json={"parent_id": parent_id}) as resp:
                resp_json = {}
                if resp.content_type and 'json' in resp.content_type:
                    resp_json = await resp.json()
                
                if resp.status == 200 and resp_json.get("success"):
                    await update.message.reply_text(
                        "❌ Your Telegram has been disconnected from your school account\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    error_msg = resp_json.get("error", "API error details not provided\\.")
                    await update.message.reply_text(f"⚠️ Failed to disconnect\\. API Status: {resp.status}\\. Details: {escape_markdown_v2(error_msg)}")
        except Exception as e:
            logger.exception(f"Error disconnecting parent {parent_id}: {e}")
            await update.message.reply_text("⚠️ Unexpected error during disconnection\\.")


# ----------------------
# FEES COMMAND (SECURITY ENFORCED)
# ----------------------
async def fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send unpaid fee summary for each student. Access only if connected via /start link."""
    chat_id = update.effective_chat.id
    
    # --- SECURITY CHECK: Uses asynchronous Django ORM lookup ---
    parent_id = await _get_parent_id_from_persistence(chat_id)

    if not parent_id:
        await update.message.reply_text(
            "🔒 Access denied\\. You must connect your account using the **unique link** "
            "found in your parent profile\\. Manual IDs are not allowed\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    # --- END SECURITY CHECK ---
    
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    async with aiohttp.ClientSession() as session:
        try:
            # This uses the parent_id endpoint
            async with session.get(f"{DJANGO_API_URL_FEE}{parent_id}/fee-summary/") as resp:
                if resp.status != 200:
                    logger.error(f"API failed with status {resp.status} for parent {parent_id}")
                    await update.message.reply_text("⚠️ Could not fetch fee summary\\.")
                    return
                # Ensure content_type is handled safely
                data = await resp.json(content_type=None) 
        except Exception as e:
            logger.exception(f"Error fetching summary for parent {parent_id}: {e}")
            await update.message.reply_text("⚠️ Error fetching fee summary\\.")
            return

    if not data:
        await update.message.reply_text("🎉 All fees are fully paid\\! No action required\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    for s in data:
        message, reply_markup = _generate_student_summary(s)
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        

# ----------------------
# HANDLER: Back Button Logic (Seamless Navigation)
# ----------------------
async def handle_back_to_fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    student_id = context.match.group(1)
    
    logger.info(f"Seamlessly returning to student summary for student {student_id}")
    
    await query.edit_message_text("🔄 Loading student fee summary...")
    
    try:
        url = f"{DJANGO_API_URL_FEE}students/{student_id}/fee-summary/" 
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await query.edit_message_text("⚠️ Could not fetch student summary.")
                    return
                s = await resp.json(content_type=None)
    except Exception:
        logger.exception(f"Error fetching single student summary for {student_id}")
        await query.edit_message_text("⚠️ Error fetching student summary.")
        return

    if isinstance(s, list) and s:
        s = s[0]
    elif not s:
        await query.edit_message_text("🎉 Student summary not found or all fees are paid.")
        return
        
    message, reply_markup = _generate_student_summary(s)

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )


# ----------------------
# HANDLER: View Invoices Logic (Robustness and Navigation)
# ----------------------
async def handle_view_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    student_id = context.match.group(1)
    
    # Get parent_id from persistence for the security check (redundant, but good practice)
    chat_id = update.effective_chat.id
    parent_id = await _get_parent_id_from_persistence(chat_id)
    if not parent_id:
        await query.edit_message_text("⚠️ Parent ID not found\\. Please run /start and /fees again\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    await query.edit_message_text(f"🔍 Fetching invoices for student ID: {student_id}\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch unpaid invoices for the specific student ID
            async with session.get(f"{DJANGO_API_URL_FEE}students/{student_id}/unpaid-invoices/") as resp:
                if resp.status != 200:
                    logger.error(f"API failed with status {resp.status} for student {student_id}")
                    await query.edit_message_text("⚠️ Could not fetch invoice details\\.")
                    return
                invoices = await resp.json(content_type=None)
        except Exception as e:
            logger.exception(f"Error fetching invoices for student {student_id}: {e}")
            await query.edit_message_text("⚠️ Error fetching invoice details\\.")
            return

    if not invoices:
        text = "🎉 No unpaid invoices\\! All good\\."
    else:
        text = "*Unpaid Invoices:*\n\n"
        for inv in invoices:
            description_raw = inv.get('description', 'N/A')
            description = escape_markdown_v2(description_raw)
            
            raw_balance = inv.get('balance', 0)
            try:
                balance_amount = float(raw_balance)
            except (ValueError, TypeError):
                balance_amount = 0
            
            if balance_amount.is_integer():
                formatted_balance = f"{int(balance_amount):,}"
            else:
                formatted_balance = f"{balance_amount:,.2f}"
            
            balance = escape_markdown_v2(formatted_balance)
            due_date = escape_markdown_v2(inv.get('due_date', 'N/A'))
            
            text += f"• {description} \\- {balance} ETB \\(Due: {due_date}\\)\n"

    
    # --- NAVIGATION BUTTONS (Using WEB_APP_BASE_URL) ---
    buttons = [
    [
        InlineKeyboardButton("⬅️ Back", callback_data=f"back_to_student_{student_id}"),
        InlineKeyboardButton("📑 Details", url=f"{WEB_APP_BASE_URL}/parents/kids/{student_id}"),
    ],
    [
        InlineKeyboardButton("💳 Pay", url=f"{WEB_APP_BASE_URL}/parents/fees/child/{student_id}"),
    ]
]


    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    
# ----------------------
# Application Setup
# ----------------------
builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
app = builder.build() # Build the application instance here for setup and menu

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("fees", fees)) 
app.add_handler(CallbackQueryHandler(handle_view_invoices, pattern=r"^view_invoices_(\d+)$")) 
app.add_handler(CallbackQueryHandler(handle_back_to_fees, pattern=r"^back_to_student_(\d+)$"))
# ... (rest of command and help handlers)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
    "👋 Welcome\\!\n\n"
    "• /start \\- Connect or disconnect your account using the link from your profile\\.\n\n"
    "• /fees \\- View unpaid fees for your children \\(only after connecting\\)\\.\n\n"
    "• Click *Pay* to go to payment\n\n"
    "• Click *View Invoices* to see detailed invoices\n",
    parse_mode=ParseMode.MARKDOWN_V2,
)


app.add_handler(CommandHandler("help", help_command))

# ----------------------
# Menu Button Setup
# ----------------------
async def setup_menu_button():
    """Sets the persistent 'Open School App' button."""
    try:
        # The URL for the Web App button. This points to your main dashboard.
        app_url = f"{WEB_APP_BASE_URL}/parents/dashboard/"
        
        # 1. CRITICAL: Create the WebAppInfo object first
        web_app_info = WebAppInfo(url=app_url)
        
        # 2. Define the MenuButtonWebApp using the WebAppInfo object
        menu_button = MenuButtonWebApp(text="Open School App", web_app=web_app_info) 
        
        # Set the menu button for all users.
        await app.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Menu button set successfully to: {app_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set menu button: {e}")

# ----------------------
# Synchronous processing function for threading (Webhook handler)
# ----------------------
def process_update_sync(update_data):
    """
    Handles incoming Telegram updates from the webhook.
    Runs the async PTB handler inside a dedicated loop per thread.
    """
    try:
        # CRITICAL FIX: Ensure Django is set up in the new thread context
        if not django.apps.apps.ready:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")
            django.setup()
            
        # Convert JSON to Telegram Update object
        update = Update.de_json(update_data, app.bot)
        
        # Initialize the application instance for this thread before processing
        if not app.running:
            app.initialize() 
            
        # Each thread gets its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the asynchronous processing task
        loop.run_until_complete(app.process_update(update))
        
        # Clean up the loop
        loop.close()

    except Exception as e:
        logger.error(f"❌ Error in webhook thread: {e}")

# ----------------------
# Webhook setup function (Correct for PythonAnywhere)
# ----------------------
async def setup_webhook():
    # Use the imported WEB_APP_BASE_URL to construct the webhook URL
    # Assuming WEBHOOK_URL includes the full path (e.g., https://domain.com/path/)
    # If not, you should change WEBHOOK_URL to be the full path in bot/config.py
    
    # CRITICAL FIX: Ensure WEBHOOK_URL from config is used, which should be the full HTTPS path.
    WEBHOOK_URL = f"{WEB_APP_BASE_URL}/parents/telegram-webhook/".replace("http://", "https://")
    
    bot = app.bot
    # Always delete the old webhook before setting a new one
    await bot.delete_webhook() 
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook set successfully to: {WEBHOOK_URL}")
    
    # CRITICAL: Set the persistent menu button here
    await setup_menu_button()


# ----------------------
# Local polling (Unchanged for local testing)
# ----------------------
if __name__ == "__main__":
    # If you run this file directly, it will run in polling mode (local development)
    logger.info("🤖 Bot running locally (polling mode)")
    app.run_polling()
