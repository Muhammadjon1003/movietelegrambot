#!/usr/bin/env python3
"""
Stop all bot instances safely.
"""
import os
import subprocess
import psutil

def stop_all_bot_processes():
    """Stop all bot-related Python processes."""
    print("🛑 Stopping all bot processes...")
    
    killed_count = 0
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] and 'python' in proc.info['name'].lower():
                    cmdline = proc.info['cmdline'] or []
                    if any('bot' in arg.lower() or 'run_bot' in arg.lower() for arg in cmdline):
                        print(f"   Stopping process {proc.info['pid']}: {' '.join(cmdline)}")
                        proc.terminate()
                        killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Force kill if needed
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/f', '/im', 'python.exe'], 
                         capture_output=True, text=True)
        
        print(f"✅ Stopped {killed_count} bot processes")
        
    except Exception as e:
        print(f"⚠️ Error stopping processes: {e}")

def main():
    """Main function to stop the bot."""
    print("🛑 Bot Stop Script")
    print("=" * 20)
    
    stop_all_bot_processes()
    print("✅ All bot processes stopped")

if __name__ == "__main__":
    main()

