# 🚀 Telegram Video Indexer Bot - Deployment Guide

## 📋 Prerequisites

- Python 3.8 or higher
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your Telegram user ID (get from [@userinfobot](https://t.me/userinfobot))
- Target channel ID (optional)

## 🔧 Local Setup

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd telegram-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual values
nano .env
```

### 4. Fill in Your Configuration
```env
# Get from @BotFather
BOT_TOKEN=your_actual_bot_token_here

# Get from @userinfobot (optional - leave empty to index all channels)
TARGET_CHANNEL=your_channel_id_here

# Get from @userinfobot
ADMIN_USER_ID=your_user_id_here

# Database file (default is fine)
DATABASE_PATH=video_indexer.db

# Logging level
LOG_LEVEL=INFO
```

### 5. Run the Bot
```bash
# Option 1: Using the start script
python start_bot.py

# Option 2: Direct run
python run_bot.py

# Option 3: Using bot.py directly
python bot.py
```

## 🌐 Cloud Hosting Options

### Option 1: Heroku
1. Create a Heroku app
2. Set environment variables in Heroku dashboard
3. Deploy using Git

### Option 2: Railway
1. Connect your GitHub repository
2. Set environment variables
3. Deploy automatically

### Option 3: DigitalOcean App Platform
1. Connect your repository
2. Configure environment variables
3. Deploy

### Option 4: VPS (Ubuntu/Debian)
```bash
# Install Python and dependencies
sudo apt update
sudo apt install python3 python3-pip

# Clone your repository
git clone <your-repo-url>
cd telegram-bot

# Install dependencies
pip3 install -r requirements.txt

# Create systemd service
sudo nano /etc/systemd/system/telegram-bot.service
```

**Systemd Service File:**
```ini
[Unit]
Description=Telegram Video Indexer Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/telegram-bot
ExecStart=/usr/bin/python3 run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start the service
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 🔒 Security Best Practices

1. **Never commit .env file** - It's already in .gitignore
2. **Use strong bot tokens** - Regenerate if compromised
3. **Limit admin access** - Only trusted users
4. **Monitor logs** - Check for suspicious activity
5. **Regular updates** - Keep dependencies updated

## 📊 Monitoring

### Check Bot Status
```bash
# View logs
tail -f bot.log

# Check if bot is running
ps aux | grep python

# Restart if needed
sudo systemctl restart telegram-bot
```

### Health Checks
- Bot responds to `/start` command
- Database is accessible
- No error logs in bot.log

## 🛠️ Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if bot token is correct
   - Verify bot is added to target channel
   - Check logs for errors

2. **Database errors**
   - Ensure database file is writable
   - Check disk space
   - Verify database permissions

3. **Permission errors**
   - Check file permissions
   - Ensure user has access to bot files
   - Verify environment variables are set

### Log Analysis
```bash
# View recent errors
grep "ERROR" bot.log

# View bot activity
grep "INFO" bot.log | tail -20

# Monitor real-time
tail -f bot.log
```

## 📈 Scaling Considerations

- **Database**: Consider PostgreSQL for large datasets
- **Caching**: Add Redis for better performance
- **Load Balancing**: Use multiple bot instances
- **Monitoring**: Add health check endpoints

## 🔄 Updates

To update the bot:
```bash
# Pull latest changes
git pull origin main

# Restart the bot
sudo systemctl restart telegram-bot

# Check status
sudo systemctl status telegram-bot
```

## 📞 Support

For issues or questions:
1. Check the logs first
2. Verify configuration
3. Test locally before deploying
4. Check Telegram Bot API status

