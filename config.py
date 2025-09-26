"""
Configuration settings for the Telegram Video Indexer Bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the bot."""
    
    # Bot token from BotFather
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
    # Admin configuration
    ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '1997334476'))
    
    # Database configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'video_indexer.db')
    
    # Channel configuration
    TARGET_CHANNEL = os.getenv('TARGET_CHANNEL', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        if not cls.TARGET_CHANNEL:
            print("Warning: TARGET_CHANNEL not set. Bot will index all channels it's added to.")
        
        return True