# IMPORTANT: This file should be placed in the ROOT directory of your Django project (where manage.py is).

import os
import django
import asyncio
import sys
# Import the function and logger from your bot
from bot.main import setup_webhook, logger 

# Set up Django environment
# Replace 'SchoolSystem.settings' with the actual path to your settings file if it is different
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolSystem.settings') 
django.setup()

async def main():
    logger.info("Starting Telegram Webhook and Menu Button Setup...")
    try:
        # This single call now handles both the webhook and the MenuButtonWebApp setup
        await setup_webhook()
        logger.info("Complete setup finished successfully.")
    except Exception as e:
        logger.error(f"Failed to set webhook/menu button. Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Fallback for environments that might not support asyncio.run directly
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except RuntimeError as e:
        if "cannot run" in str(e):
             loop = asyncio.get_event_loop()
             loop.run_until_complete(main())
        else:
             raise e
