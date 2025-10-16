# --- Telegram Bot Token ---
TELEGRAM_BOT_TOKEN = "8141768447:AAE-sk9IROgjZWmaJEI5iU4R9rL1QyzrV7k" 

# --- INTERNAL API URLs (Bot-to-Django Communication) ---
# CRITICAL FIX: Use http://127.0.0.1 for internal loopback on PythonAnywhere
# This bypasses the platform's outbound connection restrictions.
BASE_API_URL_INTERNAL = "http://127.0.0.1:8000" 

# Adjust these to use the internal base URL
DJANGO_API_URL_CONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/save_chat_id/"
DJANGO_API_URL_DISCONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/disconnect_chat_id/"
DJANGO_API_URL_FEE = f"{BASE_API_URL_INTERNAL}/parents/api/parent/"

# --- EXTERNAL WEB APP URL (For Telegram buttons/links) ---
# This must remain the public URL so users can access the Django site from Telegram.
WEB_APP_BASE_URL = "https://schoolsys.pythonanywhere.com"
