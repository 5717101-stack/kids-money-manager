#!/usr/bin/env python3
"""
Local Cursor Bridge: Remote Execution via Google Drive

This script runs on your local Mac and monitors a Google Drive folder for
coding prompts sent via WhatsApp. When a new task is detected, it activates
Cursor and triggers the Composer with the task content.

REQUIREMENTS:
- Python 3.8+
- Google Drive Desktop App installed and synced
- Cursor IDE installed
- Accessibility permissions for Terminal/Python

INSTALLATION:
    pip install watchdog pyautogui

USAGE:
    python local_cursor_bridge.py

PERMISSIONS:
    System Preferences > Privacy & Security > Accessibility > Add Terminal/Python
"""

import os
import sys
import time
import subprocess
import hashlib
from datetime import datetime
from pathlib import Path

# ================================================================
# CONFIGURATION
# ================================================================

# TODO: Update this path to match your Google Drive folder location
# Common paths:
# - ~/Library/CloudStorage/GoogleDrive-YOUR_EMAIL/My Drive/second_brain_memory/Cursor_Inbox
# - ~/Google Drive/My Drive/second_brain_memory/Cursor_Inbox
# 
# To find your path:
# 1. Open Finder
# 2. Navigate to Google Drive > second_brain_memory > Cursor_Inbox
# 3. Drag the folder to Terminal to see the full path

WATCH_PATH = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-itzhakbachar@gmail.com/My Drive/second_brain_memory/Cursor_Inbox"
)

# Alternative paths to try if the above doesn't work
ALTERNATIVE_PATHS = [
    "~/Google Drive/My Drive/second_brain_memory/Cursor_Inbox",
    "~/Google Drive/second_brain_memory/Cursor_Inbox",
    "~/Library/CloudStorage/GoogleDrive/My Drive/second_brain_memory/Cursor_Inbox",
]

TASK_FILENAME = "pending_task.md"
CHECK_INTERVAL = 2  # seconds between checks
DRIVE_SYNC_DELAY = 1  # seconds to wait for Drive sync

# ================================================================
# WATCHDOG-BASED MONITORING
# ================================================================

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️  watchdog not installed. Using polling fallback.")
    print("   Install with: pip install watchdog")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️  pyautogui not installed. Keyboard automation disabled.")
    print("   Install with: pip install pyautogui")


class CursorBridgeHandler(FileSystemEventHandler):
    """Handles file system events for the Cursor inbox."""
    
    def __init__(self, bridge):
        self.bridge = bridge
    
    def on_modified(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name == TASK_FILENAME:
            print(f"📝 File modified: {event.src_path}")
            time.sleep(DRIVE_SYNC_DELAY)  # Wait for Drive sync
            self.bridge.process_task()
    
    def on_created(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).name == TASK_FILENAME:
            print(f"📝 File created: {event.src_path}")
            time.sleep(DRIVE_SYNC_DELAY)
            self.bridge.process_task()


class CursorBridge:
    """Main bridge class for remote Cursor execution."""
    
    def __init__(self, watch_path: str):
        self.watch_path = Path(watch_path)
        self.task_file = self.watch_path / TASK_FILENAME
        self.last_hash = None
        
        # Verify the path exists
        if not self.watch_path.exists():
            print(f"❌ Watch path does not exist: {self.watch_path}")
            print("\n🔍 Trying alternative paths...")
            
            for alt_path in ALTERNATIVE_PATHS:
                expanded = Path(os.path.expanduser(alt_path))
                if expanded.exists():
                    print(f"✅ Found alternative path: {expanded}")
                    self.watch_path = expanded
                    self.task_file = self.watch_path / TASK_FILENAME
                    break
            else:
                print("\n❌ Could not find any valid path.")
                print("\n📋 Please update WATCH_PATH in this script with your actual path.")
                print("   To find your Google Drive path:")
                print("   1. Open Finder")
                print("   2. Navigate to: Google Drive > second_brain_memory > Cursor_Inbox")
                print("   3. Right-click > Get Info > Copy the path from 'Where'")
                sys.exit(1)
        
        print(f"✅ Monitoring: {self.watch_path}")
    
    def get_file_hash(self) -> str:
        """Get MD5 hash of the task file for change detection."""
        if not self.task_file.exists():
            return ""
        try:
            content = self.task_file.read_bytes()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            print(f"⚠️  Error reading file hash: {e}")
            return ""
    
    def read_task(self) -> str:
        """Read the task content from the file."""
        if not self.task_file.exists():
            return ""
        try:
            return self.task_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading task file: {e}")
            return ""
    
    def activate_cursor(self) -> bool:
        """Activate Cursor IDE using AppleScript."""
        try:
            script = '''
            tell application "Cursor"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
            time.sleep(0.5)  # Wait for app to come to foreground
            print("✅ Cursor activated")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to activate Cursor: {e}")
            return False
        except FileNotFoundError:
            print("❌ osascript not found. Are you running on macOS?")
            return False
    
    def trigger_composer(self, content: str) -> bool:
        """Trigger Cursor Composer and type the content."""
        if not PYAUTOGUI_AVAILABLE:
            print("❌ pyautogui not available. Cannot trigger Composer.")
            print(f"📋 Task content:\n{content}")
            return False
        
        try:
            # Trigger Composer with Cmd+I
            print("⌨️  Triggering Composer (Cmd+I)...")
            pyautogui.hotkey('command', 'i')
            time.sleep(0.8)  # Wait for Composer to open
            
            # Type the content
            print("⌨️  Typing content...")
            # Use pyautogui.write for ASCII, but for Hebrew we need clipboard
            if any('\u0590' <= c <= '\u05EA' for c in content):
                # Hebrew detected - use clipboard
                print("📝 Hebrew detected - using clipboard method...")
                import subprocess
                process = subprocess.Popen(
                    ['pbcopy'],
                    stdin=subprocess.PIPE,
                    env={'LANG': 'en_US.UTF-8'}
                )
                process.communicate(content.encode('utf-8'))
                
                time.sleep(0.2)
                pyautogui.hotkey('command', 'v')  # Paste
            else:
                # ASCII content - type directly
                pyautogui.typewrite(content, interval=0.01)
            
            time.sleep(0.3)
            
            # Press Enter to submit
            print("⌨️  Submitting (Enter)...")
            pyautogui.press('enter')
            
            print("✅ Composer triggered successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error triggering Composer: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_task(self):
        """Process a new task from the inbox."""
        current_hash = self.get_file_hash()
        
        # Skip if no change or empty file
        if not current_hash or current_hash == self.last_hash:
            return
        
        self.last_hash = current_hash
        
        content = self.read_task()
        if not content.strip():
            print("⚠️  Task file is empty")
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"🚀 NEW TASK RECEIVED at {timestamp}")
        print(f"{'='*60}")
        print(f"📝 Content preview: {content[:100]}...")
        print(f"{'='*60}")
        
        # Execute the task
        if self.activate_cursor():
            time.sleep(0.3)
            if self.trigger_composer(content):
                print("✅ Task executed successfully!")
            else:
                print("❌ Failed to trigger Composer")
        else:
            print("❌ Failed to activate Cursor")
        
        print(f"{'='*60}\n")
    
    def start_watching(self):
        """Start watching for new tasks."""
        print(f"\n{'='*60}")
        print("🔌 CURSOR BRIDGE STARTED")
        print(f"{'='*60}")
        print(f"📁 Watching: {self.watch_path}")
        print(f"📄 Task file: {TASK_FILENAME}")
        print(f"⏱️  Check interval: {CHECK_INTERVAL}s")
        print(f"{'='*60}")
        print("\n💡 Send a WhatsApp message starting with 'הרץ בקרסר' to execute!")
        print("   Example: 'הרץ בקרסר fix the bug in app.py'")
        print("\n🛑 Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        # Process any existing task first
        if self.task_file.exists():
            print("📥 Checking for existing task...")
            self.process_task()
        
        if WATCHDOG_AVAILABLE:
            # Use watchdog for efficient file monitoring
            event_handler = CursorBridgeHandler(self)
            observer = Observer()
            observer.schedule(event_handler, str(self.watch_path), recursive=False)
            observer.start()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                observer.stop()
                print("\n👋 Bridge stopped")
            observer.join()
        else:
            # Fallback to polling
            try:
                while True:
                    self.process_task()
                    time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                print("\n👋 Bridge stopped")


def check_accessibility_permissions():
    """Check if accessibility permissions are granted."""
    print("\n📋 PERMISSIONS CHECK")
    print("-" * 40)
    
    # Check if we can get screen size (requires some permissions)
    if PYAUTOGUI_AVAILABLE:
        try:
            size = pyautogui.size()
            print(f"✅ Screen access: {size.width}x{size.height}")
        except Exception as e:
            print(f"⚠️  Screen access issue: {e}")
            print("\n⚠️  If you see permission errors, you need to:")
            print("   1. Open System Preferences > Privacy & Security > Accessibility")
            print("   2. Add and enable 'Terminal' (or your Python executable)")
            print("   3. Restart this script")
    
    print("-" * 40)


def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("🔌 LOCAL CURSOR BRIDGE")
    print("   Remote Execution via WhatsApp -> Google Drive -> Cursor")
    print("="*60)
    
    # Check permissions
    check_accessibility_permissions()
    
    # Start the bridge
    bridge = CursorBridge(WATCH_PATH)
    bridge.start_watching()


if __name__ == "__main__":
    main()
