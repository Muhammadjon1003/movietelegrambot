#!/usr/bin/env python3
"""
Script to run the bot with the token set as environment variable.
"""
import os
import sys

# Set the bot token and target channel as environment variables
os.environ['BOT_TOKEN'] = '8338311677:AAG7f_T9GFhIzJwSSxagPGlOIC7sEO6q0Io'
os.environ['TARGET_CHANNEL'] = '-1003038072399'  # Your private channel ID
os.environ['ADMIN_USER_ID'] = '1997334476'  # Set to your actual user ID

# Now import and run the bot
from bot import main

if __name__ == '__main__':
    main()
