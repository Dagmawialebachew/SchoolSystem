# --- Telegram Bot Token ---
TELEGRAM_BOT_TOKEN = "8141768447:AAE-sk9IROgjZWmaJEI5iU4R9rL1QyzrV7k"

# --- INTERNAL API URLs (Bot ↔ Django Communication) ---
# Use HTTPS for PythonAnywhere to reliably route requests to your Django app
BASE_API_URL_INTERNAL = "https://schoolsys.pythonanywhere.com"
DJANGO_API_URL_CONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/save_chat_id/"
DJANGO_API_URL_DISCONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/disconnect_chat_id/"
DJANGO_API_URL_FEE = f"{BASE_API_URL_INTERNAL}/parents/api/parent/"

# --- EXTERNAL WEB APP URL (For Telegram buttons/links) ---
WEB_APP_BASE_URL = "https://schoolsys.pythonanywhere.com"
