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
    "~/Library/CloudStorage/GoogleDrive-5717101@gmail.com/My Drive/Second Brain Memory/Cursor_Inbox"
)

# Alternative paths to try if the above doesn't work
ALTERNATIVE_PATHS = [
    "~/Google Drive/My Drive/second_brain_memory/Cursor_Inbox",
    "~/Google Drive/second_brain_memory/Cursor_Inbox",
    "~/Library/CloudStorage/GoogleDrive/My Drive/second_brain_memory/Cursor_Inbox",
]

TASK_FILENAME = "pending_task.md"
ARCHIVE_FOLDER = "Cursor_Inbox_Archive"  # Folder to move completed tasks
CHECK_INTERVAL = 2  # seconds between checks
DRIVE_SYNC_DELAY = 1  # seconds to wait for Drive sync

# Server URL for sending completion notifications
SERVER_URL = "https://second-brain-6q8c.onrender.com"  # Production server
# SERVER_URL = "http://localhost:8001"  # Local development

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
    
    def is_screen_locked(self) -> bool:
        """Check if the Mac screen is locked or sleeping."""
        try:
            # Check if screen is locked using CGSession
            result = subprocess.run(
                ['python3', '-c', 
                 'import Quartz; print(Quartz.CGSessionCopyCurrentDictionary().get("CGSSessionScreenIsLocked", False))'],
                capture_output=True, text=True, timeout=5
            )
            is_locked = 'True' in result.stdout
            if is_locked:
                print("🔒 Screen is LOCKED - cannot execute GUI commands!")
            return is_locked
        except Exception as e:
            # If we can't check, assume it's not locked
            print(f"⚠️  Could not check screen lock status: {e}")
            return False
    
    def activate_cursor(self) -> bool:
        """Activate Cursor IDE using AppleScript."""
        # First check if screen is locked
        if self.is_screen_locked():
            print("❌ Cannot activate Cursor - screen is locked!")
            print("   💡 Unlock your Mac or run with: caffeinate -i python3 local_cursor_bridge.py")
            return False
        
        try:
            script = '''
            tell application "Cursor"
                activate
            end tell
            '''
            result = subprocess.run(['osascript', '-e', script], check=True, capture_output=True, text=True)
            time.sleep(0.5)  # Wait for app to come to foreground
            
            # Verify Cursor is actually frontmost
            verify_script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                return frontApp
            end tell
            '''
            verify_result = subprocess.run(['osascript', '-e', verify_script], capture_output=True, text=True)
            front_app = verify_result.stdout.strip()
            
            if 'Cursor' in front_app:
                print(f"✅ Cursor activated (front app: {front_app})")
                return True
            else:
                print(f"⚠️  Cursor may not be frontmost (front app: {front_app})")
                # Try one more time
                time.sleep(0.5)
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to activate Cursor: {e}")
            if e.stderr:
                print(f"   Error: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ osascript not found. Are you running on macOS?")
            return False
    
    def trigger_composer(self, content: str) -> bool:
        """Trigger Cursor AI Agent and execute the command."""
        if not PYAUTOGUI_AVAILABLE:
            print("❌ pyautogui not available. Cannot trigger Agent.")
            print(f"📋 Task content:\n{content}")
            return False
        
        try:
            # Step 1: Open the AI Chat panel with Cmd+L
            print("⌨️  Opening AI Chat panel (Cmd+L)...")
            pyautogui.hotkey('command', 'l')
            time.sleep(1.0)  # Wait for panel to open
            
            # Step 2: Switch to Agent mode with Cmd+. (period)
            # This toggles Agent mode in Cursor
            print("⌨️  Switching to Agent mode (Cmd+.)...")
            pyautogui.hotkey('command', '.')
            time.sleep(0.5)
            
            # Step 3: Type the content
            print("⌨️  Typing content...")
            # Use clipboard for all content (more reliable)
            import subprocess
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                env={'LANG': 'en_US.UTF-8'}
            )
            process.communicate(content.encode('utf-8'))
            
            time.sleep(0.2)
            pyautogui.hotkey('command', 'v')  # Paste
            
            time.sleep(0.5)
            
            # Step 4: Press Enter to send the message to Agent
            # In the chat panel, Enter sends the message
            print("⌨️  Sending to Agent (Enter)...")
            pyautogui.press('enter')
            
            print("✅ Agent triggered and command sent!")
            return True
            
        except Exception as e:
            print(f"❌ Error triggering Agent: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_change_description(self, content: str) -> bool:
        """
        Save a simplified version of the prompt to a local file.
        This can be used as a reference for git commit messages.
        
        Also saves to the repo's .last_change file for deployment notifications.
        """
        try:
            # Create a simplified summary (first 100 chars, clean)
            summary = content.strip()[:100]
            if len(content) > 100:
                summary += "..."
            
            # Save to local file in the project directory
            project_dir = Path(__file__).parent
            change_file = project_dir / ".last_change"
            change_file.write_text(summary, encoding='utf-8')
            print(f"💾 Saved change description: {summary[:50]}...")
            
            return True
        except Exception as e:
            print(f"⚠️  Could not save change description: {e}")
            return False
    
    def send_started_notification(self, content: str, success: bool = True) -> bool:
        """
        Send a WhatsApp notification that Cursor has started working on the task.
        Calls the server's /notify-cursor-started endpoint.
        
        This triggers Message 2: "ברגעים אלה Cursor החל את עבודת הפיתוח..."
        Also saves the prompt to Drive for deployment notification (Message 3).
        """
        try:
            import urllib.request
            import json
            
            # Save change description locally for potential git commit reference
            self.save_change_description(content)
            
            # Prepare the payload with task preview for later use in deployment message
            preview = content[:300] if len(content) <= 300 else content[:300] + "..."
            
            payload = {
                "task_preview": preview,
                "success": success,
                "save_to_drive": True  # Request server to persist for deployment notification
            }
            
            # Send to server
            url = f"{SERVER_URL}/notify-cursor-started"
            data = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                url,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            print(f"📤 Sending 'started' notification to server...")
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                print(f"✅ Server notified (Message 2 sent): {result}")
                return True
                
        except Exception as e:
            print(f"⚠️  Failed to send started notification: {e}")
            # Don't fail the whole process if notification fails
            return False
    
    def archive_task(self, content: str) -> bool:
        """
        Move the completed task to the archive folder.
        Creates a timestamped file to preserve history.
        """
        try:
            # Get archive folder path (sibling to Cursor_Inbox)
            archive_path = self.watch_path.parent / ARCHIVE_FOLDER
            
            if not archive_path.exists():
                print(f"⚠️  Archive folder not found: {archive_path}")
                print(f"   Creating it...")
                archive_path.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"task_{timestamp}.md"
            archive_file = archive_path / archive_filename
            
            # Write content to archive
            archive_file.write_text(content, encoding='utf-8')
            print(f"📦 Archived to: {archive_filename}")
            
            # Delete the original pending_task.md
            if self.task_file.exists():
                self.task_file.unlink()
                print(f"🗑️  Removed: {TASK_FILENAME}")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to archive task: {e}")
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
        task_success = False
        if self.activate_cursor():
            time.sleep(0.3)
            if self.trigger_composer(content):
                print("✅ Task injected into Cursor!")
                task_success = True
            else:
                print("❌ Failed to trigger Composer")
        else:
            print("❌ Failed to activate Cursor")
        
        # Archive the task after execution (to prevent re-processing)
        self.archive_task(content)
        
        # Send WhatsApp notification: "Cursor started working" (Message 2)
        # This is sent right after injecting the prompt, not when work is "complete"
        self.send_started_notification(content, success=task_success)
        
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
