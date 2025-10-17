import logging

# --- Telegram Bot Token ---
# NOTE: Using a placeholder token for safety. Replace with your actual token.
TELEGRAM_BOT_TOKEN = "8141768447:AAE-sk9IROgjZWmaJEI5iU4R9rL1QyzrV7k"

# --- INTERNAL API URLs (Bot ↔ Django Communication) ---
# CRITICAL FIX: Use the internal loopback address for reliable PythonAnywhere communication.
BASE_API_URL_INTERNAL = "http://127.0.0.1" 

# Define API Endpoints
DJANGO_API_URL_CONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/save_chat_id/"
DJANGO_API_URL_DISCONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/disconnect_chat_id/"
DJANGO_API_URL_FEE = f"{BASE_API_URL_INTERNAL}/parents/api/parent/"

# --- EXTERNAL WEB APP URL (For Telegram buttons/links) ---
# This MUST use the public HTTPS domain.
WEB_APP_BASE_URL = "https://schoolsys.pythonanywhere.com"

logger = logging.getLogger(__name__) 
