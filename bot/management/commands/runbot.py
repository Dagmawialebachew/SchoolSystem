# bot/management/commands/runbot.py
from django.core.management.base import BaseCommand
import asyncio
from bot.main import start_bot  # your main bot entry point

class Command(BaseCommand):
    help = "Run the Telegram bot internally"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Starting Telegram bot...")
        try:
            asyncio.run(start_bot())
        except Exception as e:
            self.stderr.write(f"❌ Bot crashed: {e}")
