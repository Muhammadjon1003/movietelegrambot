#!/usr/bin/env python3
"""
Safe bot startup script that prevents 409 conflicts.
This script ensures only one bot instance runs at a time.
"""
import os
import sys
import time
import subprocess
import psutil
from pathlib import Path

def kill_all_python_processes():
    """Kill all Python processes that might be running bot instances."""
    print("🧹 Cleaning up any existing Python processes...")
    
    killed_count = 0
    current_pid = os.getpid()
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Don't kill the current process
                if proc.info['pid'] == current_pid:
                    continue
                    
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    # Check if it's a bot-related process
                    cmdline = proc.info['cmdline'] or []
                    if any('run_bot' in arg.lower() for arg in cmdline):
                        print(f"   Killing bot process {proc.info['pid']}: {' '.join(cmdline)}")
                        proc.kill()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        print(f"✅ Cleaned up {killed_count} processes")
        
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")

def wait_for_cleanup():
    """Wait for all processes to fully stop."""
    print("⏳ Waiting for cleanup to complete...")
    time.sleep(3)
    
    # Check if any Python processes are still running
    python_processes = []
    current_pid = os.getpid()
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Don't count the current process
            if proc.info['pid'] == current_pid:
                continue
                
            if proc.info['name'] and 'python' in proc.info['name'].lower():
                cmdline = proc.info['cmdline'] or []
                if any('run_bot' in arg.lower() for arg in cmdline):
                    python_processes.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if python_processes:
        print(f"⚠️ Warning: {len(python_processes)} bot processes still running: {python_processes}")
        return False
    else:
        print("✅ All bot processes stopped")
        return True

def clear_webhook():
    """Clear Telegram webhook to prevent conflicts."""
    print("🧹 Clearing Telegram webhook...")
    try:
        import asyncio
        from telegram import Bot
        
        async def clear():
            bot = Bot(token="8338311677:AAG7f_T9GFhIzJwSSxagPGlOIC7sEO6q0Io")
            await bot.delete_webhook()
            print("✅ Webhook cleared")
        
        asyncio.run(clear())
    except Exception as e:
        print(f"⚠️ Error clearing webhook: {e}")

def start_bot_safely():
    """Start the bot with proper environment variables."""
    print("🚀 Starting bot safely...")
    
    # Set environment variables
    env = os.environ.copy()
    env.update({
        'BOT_TOKEN': '8338311677:AAG7f_T9GFhIzJwSSxagPGlOIC7sEO6q0Io',
        'TARGET_CHANNEL': '-1003038072399',
        'ADMIN_USER_ID': '1997334476'
    })
    
    try:
        # Start the bot
        process = subprocess.Popen([sys.executable, 'run_bot.py'], env=env)
        print(f"✅ Bot started with PID: {process.pid}")
        
        # Wait a moment and check if it's still running
        time.sleep(3)
        if process.poll() is None:
            print("✅ Bot is running successfully!")
            return process
        else:
            print("❌ Bot failed to start")
            return None
            
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return None

def main():
    """Main function to safely start the bot."""
    print("🤖 Safe Bot Startup")
    print("=" * 30)
    
    # Step 1: Kill all existing Python processes
    print("1. Cleaning up existing processes...")
    kill_all_python_processes()
    
    # Step 2: Wait for cleanup
    print("2. Waiting for cleanup...")
    if not wait_for_cleanup():
        print("⚠️ Some processes may still be running, but continuing...")
    
    # Step 3: Clear webhook
    print("3. Clearing webhook...")
    clear_webhook()
    
    # Step 4: Final wait
    print("4. Final preparation...")
    time.sleep(3)
    
    # Step 5: Start bot
    print("5. Starting bot...")
    process = start_bot_safely()
    
    if process:
        print("\n🎉 Bot started successfully!")
        print(f"📱 Bot PID: {process.pid}")
        print("✅ No 409 conflicts should occur now")
        print("\n📋 To stop the bot:")
        print("   - Press Ctrl+C in this terminal")
        print("   - Or run: taskkill /f /im python.exe")
        
        # Keep the script running to monitor the bot
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping bot...")
            process.terminate()
            print("✅ Bot stopped")
    else:
        print("❌ Failed to start bot")
        sys.exit(1)

if __name__ == "__main__":
    main()
