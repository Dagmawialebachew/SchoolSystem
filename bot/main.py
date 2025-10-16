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
from django.apps import apps # CRITICAL: Import 'apps' to check registry status
from typing import Dict, Any, Tuple, Optional

# --- 1. CRITICAL DJANGO SETUP ---
# Set Django settings module environment variable
if not os.getenv("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")

# Ensure Django is set up before any model imports for main thread/module scope
if not apps.ready:
    try:
        # Calls django.setup() to load the app registry and models
        django.setup()
        logging.info("DEBUG: Django environment successfully set up during module import.")
    except Exception as e:
        # This warning is okay, as it will be re-attempted in the webhook thread
        logging.warning(f"Warning: Initial Django setup failed at module level: {e}")

# IMPORTANT: These imports must be configured in your bot/config.py
try:
    from bot.config import (
        DJANGO_API_URL_DISCONNECT,
        TELEGRAM_BOT_TOKEN,
        DJANGO_API_URL_CONNECT,
        DJANGO_API_URL_FEE,
        WEB_APP_BASE_URL # Must be set to 'http://schoolsys.pythonanywhere.com'
    )
except ImportError:
    # Fail loudly if config is missing
    raise ImportError("Configuration file 'bot/config.py' not found or is missing required variables.")

# CRITICAL FIX: The model import is now safe, as it runs after django.setup() above.
# We assume 'ParentProfile' is accessible after setup.
from parents.models import ParentProfile 

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
        # Use aget for asynchronous lookup
        # We need to query on the telegram_chat_id field
        parent = await ParentProfile.objects.aget(telegram_chat_id=str(chat_id))
        # The return value is the ParentProfile's primary key (usually a UUID)
        return str(parent.id)
    except ParentProfile.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error getting parent ID from DB for chat {chat_id}: {e}")
        return None

async def _set_parent_id_in_persistence(chat_id: int, parent_id: str) -> None:
    """Store the chat_id on the ParentProfile record associated with parent_id."""
    try:
        # parent_id here should be the ParentProfile.id used to find the record
        parent = await ParentProfile.objects.aget(id=parent_id)
        parent.telegram_chat_id = str(chat_id)
        # Use sync_to_async for synchronous .save() call
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
        # Use sync_to_async for synchronous .save() call
        await sync_to_async(parent.save)()
    except ParentProfile.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error deleting parent ID from DB for chat {chat_id}: {e}")

# ----------------------
# 4. Utility Functions
# ----------------------

import re

def escape_markdown_v2(text) -> str:
    """
    Escapes special characters in MarkdownV2 to prevent formatting errors.
    Always returns a safe string, even if input is None or not a string.
    """
    if text is None:
        return "N/A"
    # Ensure it's a string (handles numbers, etc.)
    text = str(text)
    # Escape all MarkdownV2 special characters
    return re.sub(r'([_*[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def _generate_student_summary(s: Dict[str, Any]) -> Tuple[str, InlineKeyboardMarkup]:
    """Generates the message and inline keyboard for a single student summary."""
    student_id = s.get("student_id", "N/A")

    # Safely escape all API data
    student_name = escape_markdown_v2(str(s.get("student_name", "Student N/A")))
    
    # Safely handle and format money amounts
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

    # --- Nearest due ---
    nearest_due = escape_markdown_v2(str(s.get("nearest_due", "N/A")))

    # --- Build the message ---
    message = (
        f"📚 *{student_name}*\n\n"
        f"💵 *Unpaid Invoices:* {s.get('count', 0)}\n"
        f"💰 *Total Unpaid:* {formatted_unpaid} ETB\n"
        f"✅ *Total Paid:* {formatted_paid} ETB\n"
        f"📅 *Nearest Due:* {nearest_due}"
    )

    # --- Inline buttons (Using WEB_APP_BASE_URL) ---
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
# 5. Telegram Bot Handlers
# ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command, including connection and disconnection links."""
    if not update.message:
        logger.warning("No update.message in /start")
        return
        
    logger.info("Bot received /start")
    logger.info(f"Received /start: {update.message.text} from chat_id {update.effective_chat.id}")

    message_text = update.message.text
    chat_id = update.effective_chat.id
    
    # Check if there is a parameter (e.g., /start parent_XYZ)
    if len(message_text.split()) > 1:
        param = message_text.split()[1]

        # --- DISCONNECT LOGIC ---
        if param.startswith("disconnect_parent_"):
            parent_id = param.replace("disconnect_parent_", "")
            await handle_disconnect(update, parent_id)
            # CRITICAL: Update local persistence AFTER successful API call
            await _delete_parent_id_from_persistence(chat_id)
            return

        # --- CONNECT LOGIC ---
        elif param.startswith("parent_"):
            parent_id = param.replace("parent_", "")
            await handle_connect(update, parent_id, chat_id)
            # CRITICAL: Update local persistence AFTER successful API call
            await _set_parent_id_in_persistence(chat_id, parent_id)
            return
            
    # Default message if no parameter or unrecognized parameter
    await update.message.reply_text(
        "👋 Hello\\! Please open the link from your parent profile to connect or disconnect\\.",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_connect(update: Update, parent_id: str, chat_id: int):
    """Calls the Django API to connect the Telegram chat ID."""
    logger.info(f"Attempting CONNECT for parent {parent_id} with chat_id {chat_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    async with aiohttp.ClientSession() as session:
        try:
            # API call to Django to store the chat_id
            async with session.post(
                DJANGO_API_URL_CONNECT, 
                json={"parent_id": parent_id, "chat_id": str(chat_id)}
            ) as resp:
                resp_json = await resp.json(content_type=None)
                
                if resp.status == 200 and resp_json.get("success"):
                    await update.message.reply_text(
                        "✅ Your Telegram is now connected to your school account\\! "
                        "You can now use commands like /fees\\. "
                        "Please refresh your browser page to see the updated status\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    error_msg = resp_json.get("error", f"API responded with status {resp.status}")
                    safe_error = escape_markdown_v2(error_msg)
                    await update.message.reply_text(f"⚠️ Failed to connect\\. Details: {safe_error}")
        except Exception as e:
            logger.exception(f"Error connecting parent {parent_id}: {e}")
            await update.message.reply_text("⚠️ Unexpected error during connection due to network or server issue\\.")


async def handle_disconnect(update: Update, parent_id: str):
    """Calls the Django API to disconnect the Telegram chat ID."""
    logger.info(f"Attempting DISCONNECT for parent {parent_id}")
    await update.effective_chat.send_chat_action(ChatAction.TYPING) 
    
    async with aiohttp.ClientSession() as session:
        try:
            # API call to Django to remove the chat_id
            async with session.post(
                DJANGO_API_URL_DISCONNECT, 
                json={"parent_id": parent_id}
            ) as resp:
                resp_json = await resp.json(content_type=None)
                
                if resp.status == 200 and resp_json.get("success"):
                    await update.message.reply_text(
                        "❌ Your Telegram has been disconnected from your school account\\.",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                else:
                    error_msg = resp_json.get("error", f"API responded with status {resp.status}")
                    safe_error = escape_markdown_v2(error_msg)
                    await update.message.reply_text(f"⚠️ Failed to disconnect\\. Details: {safe_error}")
        except Exception as e:
            logger.exception(f"Error disconnecting parent {parent_id}: {e}")
            await update.message.reply_text("⚠️ Unexpected error during disconnection due to network or server issue\\.")

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
        # The URL for the Web App button. This points to your main dashboard.
        app_url = f"{WEB_APP_BASE_URL}/parents/dashboard/"
        
        # 1. Create the WebAppInfo object
        web_app_info = WebAppInfo(url=app_url)
        
        # 2. Define the MenuButtonWebApp using the WebAppInfo object
        menu_button = MenuButtonWebApp(text="Open School App", web_app=web_app_info)
        
        # Set the menu button for all users.
        await app.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Menu button set successfully to: {app_url}")
    except Exception as e:
        logger.error(f"❌ Failed to set menu button: {e}")

# ----------------------
# 9. Synchronous processing function for threading (Webhook handler)
# ----------------------
def process_update_sync(update_data: Dict[str, Any]):
    """
    Handles incoming Telegram updates from the webhook.
    Runs the async PTB handler inside a dedicated loop per thread.
    
    CRITICAL FIX: Explicitly sets up Django and initializes the PTB Application
    by running the necessary async calls inside the thread's new event loop.
    """
    try:
        # 1. CRITICAL: Ensure Django ORM is ready in this new thread's context
        if not django.apps.apps.ready:
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SchoolSystem.settings")
            django.setup()
            logger.debug("Django setup executed in webhook thread.")
             
        # 2. Convert JSON to Telegram Update object
        update = Update.de_json(update_data, app.bot)
        
        # 3. Define the asynchronous sequence of operations
        async def run_update_sequence():
            """
            This sequence runs the necessary initialization and then processes the update.
            """
            if not app.running:
                # CRITICAL FIX: Await the initialization call
                await app.initialize()
                
            await app.process_update(update)
        
        # 4. Each thread gets its own event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 5. Run the asynchronous task sequence synchronously
        loop.run_until_complete(run_update_sequence())
        
        # 6. Clean up the loop - The explicit loop.close() has been removed.
        # This prevents the "RuntimeError: Event loop is closed" race condition 
        # where underlying network resources attempt cleanup after the loop is shut down.
        logger.debug("Async event loop finished for update.") 

    except Exception as e:
        logger.error(f"❌ Error in webhook thread: {e}", exc_info=True)

# ----------------------
# 10. Webhook setup function (Correct for PythonAnywhere)
# ----------------------
async def setup_webhook():
    """Sets up the Telegram webhook and persistent menu button safely on PythonAnywhere."""
    
    # --- PythonAnywhere domain & webhook path ---
    DOMAIN = "schoolsys.pythonanywhere.com"
    WEBHOOK_PATH = "/parents/telegram-webhook/"
    WEBHOOK_URL = f"https://{DOMAIN}{WEBHOOK_PATH}"

    # --- Initialize bot properly ---
    await app.initialize()
    bot = app.bot

    # --- Delete old webhook ---
    await bot.delete_webhook()
    logger.info("Old webhook deleted.")

    # --- Set new webhook ---
    await bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook set successfully: {WEBHOOK_URL}")

    # --- Set persistent menu button with HTTPS ---
    try:
        await setup_menu_button()
        logger.info("✅ Persistent menu button set successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to set menu button: {e}")

# ----------------------
# 11. Local polling entry point
# ----------------------
if __name__ == "__main__":
    # If you run this file directly, it will run in polling mode (local development)
    logger.info("🤖 Bot running locally (polling mode)")
    # NOTE: In local development, you might want to call setup_menu_button() 
    # explicitly here if you aren't using the webhook entry point.
    app.run_polling()
