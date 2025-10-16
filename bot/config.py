# bots/config.py

TELEGRAM_BOT_TOKEN = "8141768447:AAE-sk9IROgjZWmaJEI5iU4R9rL1QyzrV7k" 

# CHANGE 'https' TO 'http' for internal PythonAnywhere calls
DJANGO_API_URL_CONNECT = "http://schoolsys.pythonanywhere.com/parents/api/save_chat_id/"
DJANGO_API_URL_DISCONNECT = "http://schoolsys.pythonanywhere.com/parents/api/disconnect_chat_id/"
DJANGO_API_URL_FEE = "http://schoolsys.pythonanywhere.com/parents/api/parent/"
WEB_APP_BASE_URL = "http://schoolsys.pythonanywhere.com" # Must be set to 'http://schoolsys.pythonanywhere.com'