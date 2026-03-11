from src.bot import NotepadBot
from dotenv import load_dotenv
import logging
import os
import sys

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(r"c:\Users\Ahmed Fathi\Documents\vision-desktop-bot\logs\bot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

load_dotenv()

if __name__ == "__main__":
    try:
        logging.info("Starting bot...")
        bot = NotepadBot()
        bot.start()
    except Exception as e:
        logging.critical(f"Bot crashed: {e}", exc_info=True)
    finally:
        logging.info("Bot execution finished.")