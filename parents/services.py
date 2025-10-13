import os
from io import BytesIO
import qrcode
import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

def build_qr_payload(username: str, password: str, login_url: str) -> str:
    return f"Username: {username}\nPassword: {password}\nLogin: {login_url}"

def generate_qr_image(payload: str) -> bytes:
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def save_qr(username: str, image_bytes: bytes) -> str:
    path = os.path.join("parents/qr", f"{username}.png")
    default_storage.save(path, ContentFile(image_bytes))
    return default_storage.url(path)

def send_telegram_photo(bot_token: str, chat_id: str, caption: str, image_bytes: bytes):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    files = {"photo": ("credentials.png", image_bytes)}
    data = {"chat_id": chat_id, "caption": caption}
    requests.post(url, data=data, files=files, timeout=10)

def send_parent_credentials(profile, login_url: str, bot_token: str = None):
    username = profile.phone_number
    password = "1234"
    payload = build_qr_payload(username, password, login_url)
    img_bytes = generate_qr_image(payload)
    qr_url = save_qr(username, img_bytes)

    caption = (
        f"Your School Portal credentials\n\n"
        f"Username: {username}\nPassword: {password}\nLogin: {login_url}"
    )

    chat_id = profile.telegram_username
    if bot_token and chat_id:
        try:
            send_telegram_photo(bot_token, chat_id, caption, img_bytes)
        except Exception:
            pass

    return {"qr_url": qr_url, "username": username}
