#!/usr/bin/env python3
"""
Telegram Video Indexer Bot
Main entry point for the bot application.
"""
import logging
import sys
from telegram.ext import Application
from config import Config
from database import VideoDatabase
from handlers import BotHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Handle errors that occur during bot operation."""
    error = context.error
    if "Conflict" in str(error) and "409" in str(error):
        # Log 409 conflicts but don't treat them as critical errors
        logger.warning(f"409 Conflict detected - another bot instance may be running: {error}")
        return
    logger.error(f"Update {update} caused error {error}")

def main():
    """Main function to start the bot."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize database
        database = VideoDatabase(Config.DATABASE_PATH)
        logger.info(f"Database initialized at: {Config.DATABASE_PATH}")
        
        # Initialize bot handlers
        handlers = BotHandlers(database)
        logger.info("Bot handlers initialized")
        
        # Create application
        application = Application.builder().token(Config.BOT_TOKEN).build()
        
        # Add handlers
        for handler in handlers.get_handlers():
            application.add_handler(handler)
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        logger.info("Bot starting...")
        logger.info(f"Target channel: {Config.TARGET_CHANNEL or 'All channels'}")
        logger.info("Admin user ID: " + str(Config.ADMIN_USER_ID))
        
        # Start the bot with simplified polling
        logger.info("Starting polling...")
        application.run_polling(
            allowed_updates=['message', 'channel_post', 'callback_query'],
            drop_pending_updates=True
        )
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        logger.info("Bot stopped")

if __name__ == '__main__':
    main()