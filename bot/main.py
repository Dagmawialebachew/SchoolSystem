import threading
from asgiref.sync import sync_to_async 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, WebAppInfo
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    ContextTypes, 
    CallbackQueryHandler, 
    Application,
    filters
)
from telegram.constants import ParseMode, ChatAction
import asyncio
import aiohttp
import logging
import re
import os
import django
from django.apps import apps
from typing import Dict, Any, Tuple, Optional

# ----------------------
# 1. Django Setup
# ----------------------
if not os.getenv("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")

if not apps.ready:
    try:
        django.setup()
        logging.info("DEBUG: Django environment successfully set up.")
    except Exception as e:
        logging.warning(f"Warning: Initial Django setup failed: {e}")

# Config import
try:
    from bot.config import (
        DJANGO_API_URL_DISCONNECT,
        TELEGRAM_BOT_TOKEN,
        DJANGO_API_URL_CONNECT,
        DJANGO_API_URL_FEE,
        WEB_APP_BASE_URL
    )
except ImportError:
    raise ImportError("Configuration file 'bot/config.py' missing or incomplete.")

from parents.models import ParentProfile 

# ----------------------
# 2. Logging
# ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("SchoolBot")

# ----------------------
# 3. Persistence (Async ORM)
# ----------------------
async def _get_parent_id_from_persistence(chat_id: int) -> Optional[str]:
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        return str(parent.id)
    except ParentProfile.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting parent ID for chat {chat_id}: {e}")
        return None

async def _set_parent_id_in_persistence(chat_id: int, parent_id: str) -> None:
    try:
        parent = await ParentProfile.objects.aget(id=parent_id)
        parent.telegram_chat_id = str(chat_id)
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        logger.warning(f"ParentProfile {parent_id} not found.")
    except Exception as e:
        logger.error(f"Error setting parent ID {parent_id}: {e}")

async def _delete_parent_id_from_persistence(chat_id: int) -> None:
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        parent.telegram_chat_id = None
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error deleting parent ID for chat {chat_id}: {e}")

# ----------------------
# 4. Utilities
# ----------------------
def escape_markdown_v2(text) -> str:
    if text is None:
        return "N/A"
    text = str(text)
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def _generate_student_summary(s: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
    student_id = s.get("student_id", "N/A")
    student_name = escape_markdown_v2(str(s.get("student_name", "Student N/A")))
    
    def format_currency(raw_amount):
        try:
            amount = float(raw_amount)
            if amount.is_integer():
                return escape_markdown_v2(f"{int(amount):,}")
            return escape_markdown_v2(f"{amount:,.2f}")
        except (ValueError, TypeError):
            return escape_markdown_v2("0.00")

    formatted_unpaid = format_currency(s.get("total_unpaid", s.get("total", 0)))
    formatted_paid = format_currency(s.get("total_paid", 0))
    nearest_due = escape_markdown_v2(str(s.get("nearest_due", "N/A")))

    message = (
        f"📚 *{student_name}*\n\n"
        f"💵 *Unpaid Invoices:* {s.get('count', 0)}\n"
        f"💰 *Total Unpaid:* {formatted_unpaid} ETB\n"
        f"✅ *Total Paid:* {formatted_paid} ETB\n"
        f"📅 *Nearest Due:* {nearest_due}"
    )

    buttons = [
        [
            InlineKeyboardButton("🔍 View Invoices", callback_data=f"view_invoices_{student_id}"),
            InlineKeyboardButton("📑 Details", url=f"{WEB_APP_BASE_URL}/parents/kids/{student_id}/"),
        ],
        [
            InlineKeyboardButton("💳 Pay", url=f"{WEB_APP_BASE_URL}/parents/fees/child/{student_id}/"),
        ]
    ]
    return message, InlineKeyboardMarkup(buttons)

# ----------------------
# 5. Bot Handlers
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    chat_id = update.effective_chat.id
    msg_text = update.message.text

    if len(msg_text.split()) > 1:
        param = msg_text.split()[1]
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            await handle_disconnect(update, parent_id)
            await _delete_parent_id_from_persistence(chat_id)
            return
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            await handle_connect(update, parent_id, chat_id)
            await _set_parent_id_in_persistence(chat_id, parent_id)
            return

    await update.message.reply_text(
        "👋 Hello\\! Please open the link from your parent profile to connect or disconnect\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_connect(update: Update, parent_id: str, chat_id: int):
    logger.info(f"Connecting parent {parent_id} with chat {chat_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DJANGO_API_URL_CONNECT, json={"parent_id": parent_id, "chat_id": str(chat_id)}) as resp:
                data = await resp.json(content_type=None)
                if resp.status == 200 and data.get("success"):
                    await update.message.reply_text(
                        "✅ Connected successfully\\! You can now use /fees\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    await update.message.reply_text(f"⚠️ Failed: {escape_markdown_v2(str(data.get('error', resp.status)))}")
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text("⚠️ Unexpected error during connection\\.")

async def handle_disconnect(update: Update, parent_id: str):
    logger.info(f"Disconnecting parent {parent_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING)
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DJANGO_API_URL_DISCONNECT, json={"parent_id": parent_id}) as resp:
                data = await resp.json(content_type=None)
                if resp.status == 200 and data.get("success"):
                    await update.message.reply_text(
                        "❌ Disconnected successfully\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    await update.message.reply_text(f"⚠️ Failed: {escape_markdown_v2(str(data.get('error', resp.status)))}")
        except Exception as e:
            logger.exception(e)
            await update.message.reply_text("⚠️ Unexpected error during disconnection\\.")

# fees, help_command, handle_view_invoices, handle_back_to_fees remain unchanged
# (Insert all previously defined async handlers here)

async def fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends unpaid fee summary for each student."""
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    
    # --- SECURITY CHECK: Uses asynchronous Django ORM lookup ---
    parent_id = await _get_parent_id_from_persistence(chat_id)

    if not parent_id:
        await update.message.reply_text(
            "🔒 Access denied\\. You must connect your account using the **unique link** "
            "found in your parent profile\\. Please run /start and follow the instructions\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    # --- END SECURITY CHECK ---
    
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    try:
        url = f"{DJANGO_API_URL_FEE}{parent_id}/fee-summary/"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"API failed with status {resp.status} for parent {parent_id} at {url}")
                    await update.message.reply_text("⚠️ Could not fetch fee summary from the school system\\.")
                    return
                # Use content_type=None for robust JSON parsing
                data = await resp.json(content_type=None) 
    except Exception as e:
        logger.exception(f"Network error fetching summary for parent {parent_id}: {e}")
        await update.message.reply_text("⚠️ Network error fetching fee summary\\. Please try again later\\.")
        return

    if not data or (isinstance(data, list) and not data):
        await update.message.reply_text("🎉 All fees are fully paid or no student data found\\! No action required\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    # Send a message for each student
    for s in data:
        message, reply_markup = _generate_student_summary(s)
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=reply_markup,
        )
        
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays help text."""
    if not update.message:
        return
        
    await update.message.reply_text(
        "👋 Welcome\\!\n\n"
        "• /start \\- Connect or disconnect your account using the link from your profile\\.\n"
        "• /fees \\- View unpaid fees for your children \\(only after connecting\\)\\.\n\n"
        "• Click *Pay* to go to payment\n"
        "• Click *View Invoices* to see detailed invoices\n",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# ----------------------
# 6. Callback Handlers (Inline Keyboard Actions)
# ----------------------

async def handle_view_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and displays detailed unpaid invoices for a specific student."""
    query = update.callback_query
    # Always answer the query to prevent "Loading" state indefinitely
    await query.answer() 

    # Extract student_id from the pattern match
    student_id = context.match.group(1)
    
    # Simple check if the user is still connected (using chat_id from the original message)
    chat_id = update.effective_chat.id
    if not await _get_parent_id_from_persistence(chat_id):
        await query.edit_message_text("⚠️ Access lost\\. Please run /start and /fees again\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    await query.edit_message_text(f"🔍 Fetching invoices for student ID: {student_id}\\.\\.\\.", parse_mode=ParseMode.MARKDOWN_V2)
    
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch unpaid invoices for the specific student ID
            url = f"{DJANGO_API_URL_FEE}students/{student_id}/unpaid-invoices/"
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"API failed with status {resp.status} for student {student_id}")
                    await query.edit_message_text("⚠️ Could not fetch invoice details\\.")
                    return
                invoices = await resp.json(content_type=None)
        except Exception as e:
            logger.exception(f"Error fetching invoices for student {student_id}: {e}")
            await query.edit_message_text("⚠️ Error fetching invoice details\\.")
            return

    if not invoices or (isinstance(invoices, list) and not invoices):
        text = "🎉 No unpaid invoices for this student\\! All good\\."
    else:
        text = "*Unpaid Invoices:*\n\n"
        for inv in invoices:
            invoice_name = escape_markdown_v2(inv.get('invoice_name', 'N/A'))
            
            # Currency formatting for balance
            raw_balance = inv.get('balance', 0)
            try:
                balance_amount = float(raw_balance)
                if balance_amount.is_integer():
                    formatted_balance = f"{int(balance_amount):,}"
                else:
                    formatted_balance = f"{balance_amount:,.2f}"
            except (ValueError, TypeError):
                formatted_balance = "0.00"
            
            balance = escape_markdown_v2(formatted_balance)
            due_date = escape_markdown_v2(inv.get('due_date', 'N/A'))
            
            # Note: Using bullet point and escaped text
            text += f"• {invoice_name} \\- {balance} ETB \\(Due: {due_date}\\)\n"

    # --- NAVIGATION BUTTONS (Student-specific) ---
    buttons = [
        [
            InlineKeyboardButton("⬅️ Back to Summary", callback_data=f"back_to_student_{student_id}"),
            InlineKeyboardButton("📑 Details", url=f"{WEB_APP_BASE_URL}/parents/kids/{student_id}/"),
        ],
        [
            InlineKeyboardButton("💳 Pay Now", url=f"{WEB_APP_BASE_URL}/parents/fees/child/{student_id}/"),
        ]
    ]

    await query.edit_message_text(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    
async def handle_back_to_fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Seamlessly returns to the single student summary."""
    query = update.callback_query
    await query.answer()

    student_id = context.match.group(1)
    
    logger.info(f"Returning to student summary for student {student_id}")
    await query.edit_message_text("🔄 Reloading student fee summary...")
    
    try:
        # Fetch summary for the single student
        url = f"{DJANGO_API_URL_FEE}students/{student_id}/fee-summary/" 
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    await query.edit_message_text("⚠️ Could not fetch student summary.")
                    return
                # Expecting a list of one or a single dict, handle safely
                data = await resp.json(content_type=None)
                s = data[0] if isinstance(data, list) and data else data
    except Exception:
        logger.exception(f"Error fetching single student summary for {student_id}")
        await query.edit_message_text("⚠️ Error fetching student summary.")
        return

    if not s or not isinstance(s, dict):
        await query.edit_message_text("🎉 Student summary not found or all fees are paid.")
        return
        
    message, reply_markup = _generate_student_summary(s)

    await query.edit_message_text(
        message,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=reply_markup,
    )

# ----------------------
# 6. Application Setup
# ----------------------
builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
app = builder.build()

# Command Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("fees", fees))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(handle_view_invoices, pattern=r"^view_invoices_(\d+)$"))
app.add_handler(CallbackQueryHandler(handle_back_to_fees, pattern=r"^back_to_student_(\d+)$"))

# ----------------------
# 7. Menu Button Setup
# ----------------------
async def setup_menu_button():
    try:
        menu_button = MenuButtonWebApp(
            text="Open School App",
            web_app=WebAppInfo(url=f"{WEB_APP_BASE_URL}/parents/dashboard/")
        )
        await app.bot.set_chat_menu_button(menu_button=menu_button)
    except Exception as e:
        logger.error(f"Failed to set menu button: {e}")

# ----------------------
# 8. Thread-Safe Webhook Update Processing
# ----------------------
def process_update_sync(update_data: dict):
    import asyncio
    from telegram import Update
    try:
        update = Update.de_json(update_data, app.bot)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(app.process_update(update))
        loop.close()
    except Exception as e:
        logger.exception(f"Error processing Telegram update: {e}")

# ----------------------
# 9. Webhook Setup for PythonAnywhere
# ----------------------
async def setup_webhook():
    await app.initialize()  # Critical fix
    await app.bot.delete_webhook()
    DOMAIN = "schoolsys.pythonanywhere.com"
    WEBHOOK_PATH = "/parents/telegram-webhook/"
    WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"
    await app.bot.set_webhook(url=WEBHOOK_URL)
    await setup_menu_button()
    logger.info(f"✅ Webhook set: {WEBHOOK_URL}")

# ----------------------
# 10. Local Polling (Development)
# ----------------------
if __name__ == "__main__":
    logger.info("Bot running locally (polling mode)")
    asyncio.run(setup_menu_button())
    app.run_polling()
