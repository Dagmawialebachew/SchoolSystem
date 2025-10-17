import threading
from turtle import update
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
import json # Explicitly import json for error handling

import os
import django
from django.apps import apps 
from typing import Dict, Any, Tuple, Optional, List, Union



# --- 1. CRITICAL DJANGO SETUP ---
if not os.getenv("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")

if not apps.ready:
    try:
        django.setup()
        logging.info("DEBUG: Django environment successfully set up.")
    except Exception as e:
        logging.error(f"FATAL: Initial Django setup failed at module level: {e}")

# IMPORTANT: These imports must be configured in your bot/config.py
try:
    from bot.config import (
        DJANGO_API_URL_DISCONNECT,
        TELEGRAM_BOT_TOKEN,
        DJANGO_API_URL_CONNECT,
        DJANGO_API_URL_FEE,
        WEB_APP_BASE_URL
    )
    from parents.models import ParentProfile 
except ImportError as e:
    raise ImportError(f"Configuration or Model import failed: {e}")

# ----------------------
# 2. Logging setup
# ----------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("SchoolBot")

# ----------------------
# 3. Persistence using Async Django ORM
# ----------------------

async def _get_parent_id_from_persistence(chat_id: int) -> Optional[str]:
    """Look up the parent_id (UUID) from the ParentProfile model using chat_id."""
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        return str(parent.id)
    except ParentProfile.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting parent ID from DB for chat {chat_id}: {e}")
        return None

async def _set_parent_id_in_persistence(chat_id: int, parent_id: str) -> None:
    """Store the chat_id on the ParentProfile record associated with parent_id."""
    try:
        parent = await ParentProfile.objects.aget(id=parent_id)
        parent.telegram_chat_id = str(chat_id)
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        logger.warning(f"ParentProfile with ID {parent_id} not found during connection.")
    except Exception as e:
        logger.error(f"Error setting parent ID in DB for parent {parent_id}: {e}")

async def _delete_parent_id_from_persistence(chat_id: int) -> None:
    """Remove the chat_id from the ParentProfile record."""
    try:
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        parent.telegram_chat_id = None
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error deleting parent ID from DB for chat {chat_id}: {e}")

# ----------------------
# 4. Utility Functions & Robust API Handler
# ----------------------

import re

def escape_markdown_v2(text: str) -> str:
    """
    Escapes Telegram MarkdownV2 reserved characters in a given string.
    Ensures that dynamic/user-supplied text won't break formatting.
    """
    if text is None:
        return "N/A"

    # Convert to string in case non-str types are passed
    text = str(text)

    # Escape all special characters defined by Telegram MarkdownV2
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def _generate_student_summary(s: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
    """Generates the message and inline keyboard for a single student summary."""
    student_id = s.get("student_id", "N/A")

    student_name = escape_markdown_v2(str(s.get("student_name", "Student N/A")))
    
    def format_currency(raw_amount):
        try:
            amount = float(raw_amount)
            if amount.is_integer():
                return escape_markdown_v2(f"{int(amount):,}")
            else:
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

async def _call_django_api(
    method: str, 
    url: str, 
    payload: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Union[Dict, List]], Optional[str]]:
    """
    Handles API calls to Django with robust error checking for connection and JSON parsing.

    Returns: (data, error_message)
    """
    async with aiohttp.ClientSession() as session:
        try:
            if method.upper() == 'POST':
                resp = await session.post(url, json=payload, timeout=10)
            elif method.upper() == 'GET':
                resp = await session.get(url, timeout=10)
            else:
                return None, "Invalid API method specified."

            logger.info(f"API Call: {method} {url} returned status {resp.status}")

            # Check for non-200 status codes (404, 500, etc.)
            if resp.status != 200:
                # Read response text for debugging the Django error page
                error_text = await resp.text()
                logger.error(f"API Error ({resp.status}) at {url}. Response text: {error_text[:200]}")
                return None, f"Server responded with status {resp.status}. This usually means the URL is incorrect or the view crashed (check Django logs)."

            # --- Attempt JSON Parsing ---
            try:
                data = await resp.json(content_type=None)
                # Check for explicit error fields in the returned JSON
                if isinstance(data, dict) and (data.get("error") or not data.get("success", True)):
                    return None, f"API Error: {data.get('error', 'Operation failed.')}"
                return data, None
            except json.JSONDecodeError as e:
                # CRITICAL FIX: Trap the JSONDecodeError. This happens if Django returns HTML (404/500 page).
                error_text = await resp.text()
                logger.error(f"JSONDecodeError at {url}: {e}. Response text: {error_text[:200]}")
                return None, "The server returned an unexpected format. This usually means the Django view is not mapped correctly."

        except aiohttp.client_exceptions.ClientConnectorError as e:
            # CRITICAL FIX: Trap ConnectionRefusedError or other network blocks.
            logger.error(f"ClientConnectorError accessing {url}: {e}")
            return None, "Connection failed. Please ensure your web app is running and the internal API URL is correct (http://127.0.0.1)."
        except asyncio.TimeoutError:
            logger.error(f"Timeout accessing {url}")
            return None, "The school system API timed out. Please try again later."
        except Exception as e:
            logger.exception(f"Unhandled Network Error accessing {url}: {e}")
            return None, "An unexpected network error occurred."

# ----------------------
# 5. Telegram Bot Handlers
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.effective_chat.id
    message_text = update.message.text or ""
    parent_id = None
    
    if len(message_text.split()) > 1:
        param = message_text.split()[1]

        # --- Disconnect ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            context.application.create_task(handle_disconnect(update, parent_id))
            await _delete_parent_id_from_persistence(chat_id)
            return

        # --- Connect ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            context.application.create_task(handle_connect(update, parent_id, chat_id))
            await _set_parent_id_in_persistence(chat_id, parent_id)
            return

    # Default message
    keyboard = [
        [
            InlineKeyboardButton(
                text="🔗 Open School App Parent Profile",
                url="https://schoolsys.pythonanywhere.com/parents/profile"  # replace with your actual link
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Hello! Please, use the button below to connect or disconnect your account:",
    reply_markup=reply_markup,
    parse_mode=None
)



async def handle_connect(update: Update, parent_id: str, chat_id: int):
    """Calls the Django API to connect the Telegram chat ID."""
    logger.info(f"Attempting CONNECT for parent {parent_id} with chat_id {chat_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    url = DJANGO_API_URL_CONNECT
    payload = {"parent_id": parent_id, "chat_id": str(chat_id)}

    resp_data, error_msg = await _call_django_api('POST', url, payload)

    if error_msg:
        safe_error = escape_markdown_v2(error_msg)
        await update.message.reply_text(f"⚠️ Failed to connect. Details: {safe_error}", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        # We assume success if no error_msg and no status error from API wrapper
        await update.message.reply_text(
            "✅ Your Telegram is now connected to your school account! "
            "You can now use commands like /fees. "
            "Please refresh your browser page to see the updated status.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def handle_disconnect(update: Update, parent_id: str):
    """Calls the Django API to disconnect the Telegram chat ID."""
    logger.info(f"Attempting DISCONNECT for parent {parent_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    url = DJANGO_API_URL_DISCONNECT
    payload = {"parent_id": parent_id}

    resp_data, error_msg = await _call_django_api('POST', url, payload)

    if error_msg:
        safe_error = escape_markdown_v2(error_msg)
        msg = escape_markdown_v2(f"⚠️ Failed to disconnect. Details: {safe_error}")
        await update.message.reply_text(msg, parse_mode=None)

    else:
        # We assume success if no error_msg and no status error from API wrapper
        await update.message.reply_text(
            "❌ Your Telegram has been disconnected from your school account.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def fees(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends unpaid fee summary for each student."""
    if not update.message:
        return
        
    chat_id = update.effective_chat.id
    
    # --- SECURITY CHECK ---
    parent_id = await _get_parent_id_from_persistence(chat_id)

    if not parent_id:
        await update.message.reply_text(
            "🔒 Access denied. You must connect your account using the **unique link** "
            "found in your parent profile. Please run /start and follow the instructions.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return
    # --- END SECURITY CHECK ---
    
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    # NOTE: Assuming your Django URL pattern is correct to capture parent_id 
    url = f"{DJANGO_API_URL_FEE}{parent_id}/fee-summary/"
    data, error_msg = await _call_django_api('GET', url)

    if error_msg:
        safe_error = escape_markdown_v2(error_msg)
        await update.message.reply_text(f"⚠️ Error fetching fee summary. Details: {safe_error}", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    if not data or not isinstance(data, list) or not data:
        await update.message.reply_text("🎉 All fees are fully paid or no student data found! No action required.", parse_mode=ParseMode.MARKDOWN_V2)
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
    await query.answer() 

    student_id = context.match.group(1)
    
    chat_id = update.effective_chat.id
    if not await _get_parent_id_from_persistence(chat_id):
        await query.edit_message_text("⚠️ Access lost. Please run /start and /fees again.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    await query.edit_message_text(f"🔍 Fetching invoices for student ID: {student_id}...", parse_mode=ParseMode.MARKDOWN_V2)
    
    url = f"{DJANGO_API_URL_FEE}students/{student_id}/unpaid-invoices/"
    invoices, error_msg = await _call_django_api('GET', url)

    if error_msg:
        await query.edit_message_text(f"⚠️ Error fetching invoice details. Details: {escape_markdown_v2(error_msg)}", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if not invoices or not isinstance(invoices, list) or not invoices:
        text = "🎉 No unpaid invoices for this student! All good."
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
            
            text += f"• {invoice_name} - {balance} ETB (Due: {due_date})\n"

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
    
    url = f"{DJANGO_API_URL_FEE}students/{student_id}/fee-summary/" 
    data, error_msg = await _call_django_api('GET', url)

    if error_msg:
        await query.edit_message_text(f"⚠️ Could not fetch student summary. Details: {escape_markdown_v2(error_msg)}", parse_mode=ParseMode.MARKDOWN_V2)
        return

    # CRITICAL FIX: The view returns a single dictionary object, not a list.
    s = data
    
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
# 7. Application Setup & Initialization
# ----------------------

# Initialize the Application instance once
builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
app = builder.build() 


# Add Handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("fees", fees)) 
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(handle_view_invoices, pattern=r"^view_invoices_(\d+)$")) 
app.add_handler(CallbackQueryHandler(handle_back_to_fees, pattern=r"^back_to_student_(\d+)$"))


# ----------------------
# 8. Menu Button Setup
# ----------------------
async def setup_menu_button():
    """Sets the persistent 'Open School App' button."""
    try:
        app_url = f"{WEB_APP_BASE_URL}/parents/dashboard/"
        web_app_info = WebAppInfo(url=app_url)
        menu_button = MenuButtonWebApp(text="Open School App", web_app=web_app_info)
        await app.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Menu button set successfully to: {app_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set menu button: {e}")

# ----------------------
# 9. Synchronous processing function for threading (Webhook handler)
# ----------------------
#----------------------

# At module level
app_initialized = False

def process_update_sync(update_data: dict):
    from telegram import Update
    import asyncio

    try:
        update = Update.de_json(update_data, app.bot)
        loop = asyncio.get_event_loop()
        loop.create_task(app.process_update(update))
    except Exception as e:
        logger.exception(f"Error processing Telegram update: {e}")

# 10. Webhook setup function (Correct for PythonAnywhere)
# ----------------------
async def setup_webhook():
    """Sets up the Telegram webhook and persistent menu button safely on PythonAnywhere."""
    
    DOMAIN = "schoolsys.pythonanywhere.com"
    WEBHOOK_PATH = "/parents/telegram-webhook/"
    WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

    await app.initialize()
    bot = app.bot

    await bot.delete_webhook()
    logger.info("Old webhook deleted.")

    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook set successfully: {WEBHOOK_URL}")

    try:
        await setup_menu_button()
        logger.info("✅ Persistent menu button set successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to set menu button: {e}")

# ----------------------
# 11. Local polling entry point
# ----------------------
if __name__ == "__main__":
    logger.info("🤖 Bot running locally (polling mode)")
    app.run_polling()
