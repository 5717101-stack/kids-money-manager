#!/usr/bin/env python3
"""
Local Cursor Bridge: Remote Execution via Server API

This script runs on your local Mac and polls the Second Brain server for
coding prompts sent via WhatsApp. When a new task is detected, it activates
Cursor and triggers the Composer with the task content.

REQUIREMENTS:
- Python 3.8+
- Cursor IDE installed
- Accessibility permissions for Terminal/Python

INSTALLATION:
    pip install pyautogui

USAGE:
    python local_cursor_bridge.py
    caffeinate -i python3 local_cursor_bridge.py   # prevent sleep

PERMISSIONS:
    System Preferences > Privacy & Security > Accessibility > Add Terminal/Python
"""

import os
import sys
import time
import subprocess
import json
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ================================================================
# CONFIGURATION
# ================================================================

# Server URL for polling pending tasks and sending notifications
SERVER_URL = "https://second-brain-363586144218.europe-west1.run.app"  # Production (Cloud Run)
# SERVER_URL = "http://localhost:8001"  # Local development

POLL_INTERVAL = 3  # seconds between API polls

# ================================================================
# OPTIONAL DEPENDENCIES
# ================================================================

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️  pyautogui not installed. Keyboard automation disabled.")
    print("   Install with: pip install pyautogui")


class CursorBridge:
    """Main bridge class for remote Cursor execution via server API polling."""
    
    def __init__(self):
        self.last_task_content = None
        print(f"✅ Bridge initialized - polling {SERVER_URL}")
    
    def poll_server(self) -> dict:
        """Poll the server for pending cursor tasks."""
        try:
            url = f"{SERVER_URL}/cursor-inbox/pending"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            # Server might be cold-starting, don't spam errors
            return {"has_task": False}
        except Exception as e:
            return {"has_task": False}
    
    def ack_task(self) -> bool:
        """Acknowledge that the task has been processed (deletes from Drive)."""
        try:
            url = f"{SERVER_URL}/cursor-inbox/ack"
            req = urllib.request.Request(
                url,
                data=b'{}',
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get('status') == 'ok'
        except Exception as e:
            print(f"⚠️  Failed to ack task: {e}")
            return False
    
    def is_screen_locked(self) -> bool:
        """Check if the Mac screen is locked or sleeping."""
        try:
            result = subprocess.run(
                ['python3', '-c', 
                 'import Quartz; print(Quartz.CGSessionCopyCurrentDictionary().get("CGSSessionScreenIsLocked", False))'],
                capture_output=True, text=True, timeout=5
            )
            is_locked = 'True' in result.stdout
            if is_locked:
                print("🔒 Screen is LOCKED - cannot execute GUI commands!")
            return is_locked
        except Exception:
            return False
    
    def activate_cursor(self) -> bool:
        """Activate Cursor IDE using AppleScript."""
        if self.is_screen_locked():
            print("❌ Cannot activate Cursor - screen is locked!")
            return False
        
        try:
            script = '''
            tell application "Cursor"
                activate
            end tell
            '''
            subprocess.run(['osascript', '-e', script], check=True, capture_output=True, text=True)
            time.sleep(0.5)
            
            # Verify Cursor is frontmost
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
                time.sleep(0.5)
                subprocess.run(['osascript', '-e', script], check=True, capture_output=True)
                return True
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to activate Cursor: {e}")
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
            time.sleep(1.0)
            
            # Step 2: Switch to Agent mode with Cmd+.
            print("⌨️  Switching to Agent mode (Cmd+.)...")
            pyautogui.hotkey('command', '.')
            time.sleep(0.5)
            
            # Step 3: Type the content via clipboard
            print("⌨️  Typing content...")
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                env={'LANG': 'en_US.UTF-8'}
            )
            process.communicate(content.encode('utf-8'))
            
            time.sleep(0.2)
            pyautogui.hotkey('command', 'v')  # Paste
            time.sleep(0.5)
            
            # Step 4: Press Enter to send
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
        """Save a simplified version of the prompt for git commit reference."""
        try:
            summary = content.strip()[:100]
            if len(content) > 100:
                summary += "..."
            project_dir = Path(__file__).parent
            change_file = project_dir / ".last_change"
            change_file.write_text(summary, encoding='utf-8')
            print(f"💾 Saved change description: {summary[:50]}...")
            return True
        except Exception as e:
            print(f"⚠️  Could not save change description: {e}")
            return False
    
    def send_started_notification(self, content: str, success: bool = True) -> bool:
        """Send WhatsApp notification that Cursor has started working."""
        try:
            self.save_change_description(content)
            
            preview = content[:300] if len(content) <= 300 else content[:300] + "..."
            payload = {
                "task_preview": preview,
                "success": success,
                "save_to_drive": True
            }
            
            url = f"{SERVER_URL}/notify-cursor-started"
            data = json.dumps(payload).encode('utf-8')
            
            req = urllib.request.Request(
                url, data=data,
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
            return False
    
    def process_task(self, content: str):
        """Process a new task."""
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
        
        # Acknowledge the task (delete from Drive)
        if self.ack_task():
            print("✅ Task acknowledged (removed from Drive)")
        else:
            print("⚠️  Failed to acknowledge task")
        
        # Send WhatsApp notification
        self.send_started_notification(content, success=task_success)
        
        print(f"{'='*60}\n")
    
    def start_polling(self):
        """Start polling the server for new tasks."""
        print(f"\n{'='*60}")
        print("🔌 CURSOR BRIDGE STARTED (API Polling Mode)")
        print(f"{'='*60}")
        print(f"🌐 Server: {SERVER_URL}")
        print(f"⏱️  Poll interval: {POLL_INTERVAL}s")
        print(f"{'='*60}")
        print("\n💡 Send a WhatsApp message starting with 'הרץ בקרסר' to execute!")
        print("   Example: 'הרץ בקרסר fix the bug in app.py'")
        print("\n🛑 Press Ctrl+C to stop")
        print(f"{'='*60}\n")
        
        # Initial server check
        print("🔍 Checking server connectivity...")
        result = self.poll_server()
        if result.get('has_task'):
            print(f"📥 Found existing pending task! Processing...")
            self.process_task(result['content'])
        else:
            print("✅ Server reachable. No pending tasks. Waiting...\n")
        
        # Main polling loop
        try:
            while True:
                time.sleep(POLL_INTERVAL)
                result = self.poll_server()
                if result.get('has_task'):
                    content = result.get('content', '')
                    if content and content != self.last_task_content:
                        self.last_task_content = content
                        self.process_task(content)
        except KeyboardInterrupt:
            print("\n👋 Bridge stopped")


def check_accessibility_permissions():
    """Check if accessibility permissions are granted."""
    print("\n📋 PERMISSIONS CHECK")
    print("-" * 40)
    
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
    print("   Remote Execution via WhatsApp -> Server API -> Cursor")
    print("="*60)
    
    # Check permissions
    check_accessibility_permissions()
    
    # Start the bridge
    bridge = CursorBridge()
    bridge.start_polling()


if __name__ == "__main__":
    main()
