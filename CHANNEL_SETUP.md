# Channel Setup Guide

This guide will help you set up the Telegram bot to work with your channel for movie storage and search.

## Prerequisites

1. A Telegram bot token from [@BotFather](https://t.me/botfather)
2. A Telegram channel where you want to store movies
3. Admin access to the channel

## Step 1: Create a Channel

1. Open Telegram and create a new channel
2. Give it a name (e.g., "My Movie Library")
3. Make it public or private (your choice)
4. Note the channel username (without @)

## Step 2: Add Bot to Channel

1. Go to your channel settings
2. Add administrators
3. Search for your bot username
4. Add the bot as an administrator
5. Give the bot these permissions:
   - ✅ Post messages
   - ✅ Edit messages
   - ✅ Delete messages
   - ✅ Invite users via link

## Step 3: Configure Bot

1. Update your `.env` file or `run_bot.py`:
   ```env
   BOT_TOKEN=your_bot_token_here
   TARGET_CHANNEL=your_channel_username  # without @
   ADMIN_USER_ID=your_telegram_user_id
   ```

2. To get your User ID:
   - Message [@userinfobot](https://t.me/userinfobot)
   - Copy your User ID

## Step 4: Test the Setup

1. Start the bot:
   ```bash
   python run_bot.py
   ```

2. Test the `/addmovie` command:
   ```
   /addmovie TEST001 | Test Movie | Test
   ```
   Then send a video file.

3. Check your channel - you should see:
   - The video posted with caption
   - Hashtag #TEST001
   - Title and category information

## Step 5: Verify Search Works

1. Use the `/search` command:
   ```
   /search TEST001
   ```

2. The bot should forward the message from your channel.

## How It Works

### Movie Addition Process

1. Admin sends `/addmovie CODE | TITLE | CATEGORY`
2. Bot asks for video file
3. Admin sends video
4. Bot posts to channel with:
   - Video file
   - Caption: "🎬 TITLE\n📁 Category: CATEGORY\n#CODE"
5. Bot stores channel message ID in database

### Movie Search Process

1. User sends `/search CODE`
2. Bot searches database for movie
3. Bot forwards original message from channel
4. User gets the video with original context

### Channel Benefits

- **Centralized Storage**: All movies in one place
- **Hashtag Organization**: Easy to browse with Telegram's hashtag feature
- **Original Context**: Videos maintain their original captions and metadata
- **Public Access**: Channel can be public for easy sharing
- **Backup**: Channel serves as a backup of your movie library

## Troubleshooting

### Bot Can't Post to Channel

- Check if bot is admin in channel
- Verify bot has "Post messages" permission
- Make sure channel username is correct (without @)

### Movies Not Found

- Check if movie was successfully posted to channel
- Verify hashtag format (#CODE)
- Check database for stored movie entry

### Permission Errors

- Ensure bot has all required permissions
- Check if channel is private and bot has access
- Verify ADMIN_USER_ID is correct

## Example Channel Structure

Your channel will look like this:

```
🎬 The Matrix
📁 Category: Action
#A001

🎬 Avengers: Endgame  
📁 Category: Action
#M005

🎬 The Hangover
📁 Category: Comedy
#C001
```

Users can search by code (`/search A001`) or browse by category (`/categories`).

## Advanced Features

### Multiple Categories

- Movies automatically organized by category
- Dynamic category menu from database
- Easy to add new categories

### Pagination

- Categories with >5 movies show pagination
- Navigate with Next/Prev buttons
- Efficient for large libraries

### Search Integration

- Searches both movies database and channel videos
- Finds movies by hashtag codes
- Maintains original channel context

## Security Notes

- Keep your bot token secure
- Don't share admin commands publicly
- Consider making channel private for sensitive content
- Regular backups of your database





