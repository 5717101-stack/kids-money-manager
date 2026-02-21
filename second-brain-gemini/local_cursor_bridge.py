#!/usr/bin/env python3
"""
Local Cursor Bridge v2: Bidirectional WhatsApp <-> Cursor

Polls the Second Brain server for coding tasks sent via WhatsApp.
When a task arrives, activates Cursor and injects it via AppleScript.
Monitors for completion and sends the summary back to WhatsApp.

No external dependencies required (uses only built-in macOS tools).

USAGE:
    caffeinate -i python3 local_cursor_bridge.py

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
import threading
from datetime import datetime
from pathlib import Path

# ================================================================
# CONFIGURATION
# ================================================================

SERVER_URL = os.environ.get(
    "BRIDGE_SERVER_URL",
    "https://second-brain-363586144218.europe-west1.run.app",
)

POLL_INTERVAL = 3
WORKSPACE_PATH = Path(os.environ.get(
    "BRIDGE_WORKSPACE",
    str(Path(__file__).parent.parent),
))
RESULT_FILE = WORKSPACE_PATH / ".bridge_result"
RESULT_TIMEOUT = 600  # seconds

BRIDGE_SUFFIX = (
    "\n\n---\n"
    "[WhatsApp Bridge] בסיום המשימה, כתוב סיכום קצר (2-3 משפטים) "
    "של מה שעשית לקובץ `.bridge_result` בתיקייה הראשית של הפרויקט. "
    "רק טקסט פשוט, בלי כותרות או formatting."
)

# ================================================================
# APPLESCRIPT HELPERS
# ================================================================


def _applescript(script: str, timeout: int = 20) -> tuple:
    """Run an AppleScript and return (success, output)."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def _is_cursor_running() -> bool:
    result = subprocess.run(
        ['pgrep', '-xq', 'Cursor'],
        capture_output=True,
    )
    return result.returncode == 0


# ================================================================
# BRIDGE
# ================================================================


class CursorBridge:
    """Bidirectional bridge between WhatsApp and Cursor IDE."""

    def __init__(self):
        self.last_task_content = None
        self._monitor_thread = None
        self._monitor_cancel = threading.Event()

    # ------ server communication ------

    def poll_server(self) -> dict:
        try:
            url = f"{SERVER_URL}/cursor-inbox/pending"
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            return {"has_task": False}

    def ack_task(self) -> bool:
        try:
            url = f"{SERVER_URL}/cursor-inbox/ack"
            req = urllib.request.Request(
                url, data=b'{}',
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8')).get('status') == 'ok'
        except Exception as e:
            print(f"⚠️  ack failed: {e}")
            return False

    def send_started_notification(self, content: str, success: bool):
        try:
            preview = content[:300] + ("..." if len(content) > 300 else "")
            payload = {"task_preview": preview, "success": success, "save_to_drive": True}
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{SERVER_URL}/notify-cursor-started",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"⚠️  started-notification failed: {e}")

    def _send_result_to_whatsapp(self, result_text: str):
        try:
            payload = {"result": result_text}
            data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                f"{SERVER_URL}/cursor-result",
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=15):
                print("📤 Completion sent to WhatsApp")
        except Exception as e:
            print(f"⚠️  Failed to send result: {e}")

    # ------ GUI automation (pure AppleScript) ------

    def activate_and_send(self, content: str) -> bool:
        """Activate Cursor and inject task using only AppleScript."""
        full_content = content + BRIDGE_SUFFIX

        # Copy to clipboard via pbcopy (handles UTF-8 correctly)
        proc = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        proc.communicate(full_content.encode('utf-8'))

        # Atomic AppleScript: activate -> focus -> open chat -> paste -> send
        script = '''
            tell application "Cursor"
                activate
            end tell

            delay 1.0

            tell application "System Events"
                -- Make sure Cursor is truly frontmost
                set frontApp to name of first application process whose frontmost is true
                if frontApp does not contain "Cursor" then
                    tell application "Cursor" to activate
                    delay 1.0
                end if

                tell process "Cursor"
                    set frontmost to true
                    delay 0.3

                    -- Dismiss any open dialogs / command palette
                    key code 53  -- Escape
                    delay 0.5

                    -- Open AI Chat (Cmd+L)
                    keystroke "l" using {command down}
                    delay 2.0

                    -- Select any existing text in the input, then paste over it
                    keystroke "a" using {command down}
                    delay 0.1
                    keystroke "v" using {command down}
                    delay 0.5

                    -- Send
                    key code 36  -- Return
                end tell
            end tell

            return "ok"
        '''

        ok, out = _applescript(script, timeout=20)
        if ok:
            print("✅ Task injected into Cursor")
        else:
            print(f"❌ AppleScript failed: {out}")
        return ok

    # ------ result monitoring (bidirectional) ------

    def start_result_monitor(self):
        """Spawn a daemon thread that watches .bridge_result."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_cancel.set()
            self._monitor_thread.join(timeout=5)

        self._monitor_cancel = threading.Event()

        # Remove stale result file
        if RESULT_FILE.exists():
            try:
                RESULT_FILE.unlink()
            except OSError:
                pass

        self._monitor_thread = threading.Thread(
            target=self._result_monitor_loop, daemon=True,
        )
        self._monitor_thread.start()

    def _result_monitor_loop(self):
        print("👁️  Monitoring for completion...")
        start = time.time()

        while not self._monitor_cancel.is_set():
            if time.time() - start > RESULT_TIMEOUT:
                print("⏱️  Result monitor timed out (no .bridge_result written)")
                return

            self._monitor_cancel.wait(timeout=5)
            if self._monitor_cancel.is_set():
                return

            if not RESULT_FILE.exists() or RESULT_FILE.stat().st_size == 0:
                continue

            # File appeared — wait for writes to finish (stable mtime)
            time.sleep(3)
            if not RESULT_FILE.exists():
                continue
            mtime = RESULT_FILE.stat().st_mtime
            time.sleep(2)
            if not RESULT_FILE.exists():
                continue
            if RESULT_FILE.stat().st_mtime != mtime:
                continue  # still being written

            content = RESULT_FILE.read_text(encoding='utf-8').strip()
            if not content:
                continue

            elapsed = int(time.time() - start)
            print(f"✅ Task completed ({elapsed}s)")
            print(f"   {content[:120]}...")
            self._send_result_to_whatsapp(content)

            try:
                RESULT_FILE.unlink()
            except OSError:
                pass
            return

    # ------ main flow ------

    def process_task(self, content: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*50}")
        print(f"🚀 NEW TASK [{ts}]")
        print(f"📝 {content[:100]}...")
        print(f"{'='*50}")

        success = self.activate_and_send(content)
        self.ack_task()
        self.send_started_notification(content, success)

        if success:
            self.start_result_monitor()

    def start_polling(self):
        print(f"\n{'='*50}")
        print("🔌 CURSOR BRIDGE v2 (Bidirectional)")
        print(f"{'='*50}")
        print(f"📡 Server : {SERVER_URL}")
        print(f"📁 Workspace: {WORKSPACE_PATH}")
        print(f"⏱️  Poll: {POLL_INTERVAL}s | Timeout: {RESULT_TIMEOUT}s")
        print(f"📄 Result file: {RESULT_FILE}")
        print("🛑 Ctrl+C to stop")
        print(f"{'='*50}\n")

        # Initial server check
        result = self.poll_server()
        if result.get('has_task'):
            print("📥 Found pending task — processing now")
            self.process_task(result['content'])
        else:
            print("✅ Server reachable. Waiting for tasks...\n")

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


# ================================================================
# ENTRY POINT
# ================================================================


def main():
    print("\n" + "=" * 50)
    print("🔌 LOCAL CURSOR BRIDGE v2")
    print("   WhatsApp <-> Server <-> Cursor (Bidirectional)")
    print("=" * 50)

    # Quick permission check
    ok, _ = _applescript('tell application "System Events" to return name of first process')
    if not ok:
        print("\n❌ Accessibility permissions required!")
        print("   System Settings > Privacy & Security > Accessibility")
        print("   Add and enable your terminal app.")
        sys.exit(1)

    print("✅ Accessibility permissions OK")

    if not _is_cursor_running():
        print("⚠️  Cursor is not running — it will be launched on first task")
    else:
        print("✅ Cursor is running")

    CursorBridge().start_polling()


if __name__ == "__main__":
    main()
