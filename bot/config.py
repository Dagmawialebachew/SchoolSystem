# --- Telegram Bot Token ---
TELEGRAM_BOT_TOKEN = "8141768447:AAE-sk9IROgjZWmaJEI5iU4R9rL1QyzrV7k" 

# --- INTERNAL API URLs (Bot-to-Django Communication) ---
# CRITICAL FIX: Changing from 127.0.0.1 to the public hostname with 'http://'
# This forces PythonAnywhere's internal loopback mechanism to reliably hit 
# the Django WSGI application instead of a placeholder page or the wrong port.
BASE_API_URL_INTERNAL = "http://schoolsys.pythonanywhere.com" 

# Adjust these to use the internal base URL
DJANGO_API_URL_CONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/save_chat_id/"
DJANGO_API_URL_DISCONNECT = f"{BASE_API_URL_INTERNAL}/parents/api/disconnect_chat_id/"
DJANGO_API_URL_FEE = f"{BASE_API_URL_INTERNAL}/parents/api/parent/"

# --- EXTERNAL WEB APP URL (For Telegram buttons/links) ---
# This must remain the public HTTPS URL so users can access the Django site from Telegram.
WEB_APP_BASE_URL = "https://schoolsys.pythonanywhere.com"
