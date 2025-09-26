#!/usr/bin/env python3
"""
Script to run the bot with the token set as environment variable.
"""
import os
from bot import main

if __name__ == '__main__':
    os.environ['BOT_TOKEN'] = os.getenv("BOT_TOKEN")
    os.environ['TARGET_CHANNEL'] = os.getenv("TARGET_CHANNEL")
    os.environ['ADMIN_USER_ID'] = os.getenv("ADMIN_USER_ID")
    main()

# Now import and run the bot
from bot import main

if __name__ == '__main__':
    main()
