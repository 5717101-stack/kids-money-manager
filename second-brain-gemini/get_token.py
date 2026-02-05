"""
Script to generate Google OAuth refresh token using credentials.json
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Google Drive access
SCOPES = ['https://www.googleapis.com/auth/drive']

def main():
    # Allow credentials path as command-line argument
    if len(sys.argv) > 1:
        credentials_path = sys.argv[1]
        if not os.path.exists(credentials_path):
            print(f"❌ Error: File not found: {credentials_path}")
            return
        print(f"✅ Using credentials file: {credentials_path}")
    else:
        # Check if credentials.json exists in current directory or parent
        credentials_path = 'credentials.json'
        if not os.path.exists(credentials_path):
            # Try parent directory
            parent_path = os.path.join('..', 'credentials.json')
            if os.path.exists(parent_path):
                credentials_path = parent_path
                print(f"✅ Found credentials.json in parent directory")
            else:
                # Try home directory
                home_path = os.path.join(os.path.expanduser('~'), 'credentials.json')
                if os.path.exists(home_path):
                    credentials_path = home_path
                    print(f"✅ Found credentials.json in home directory")
                else:
                    print(f"❌ Error: credentials.json not found")
                    print(f"   Checked: {os.path.abspath('credentials.json')}")
                    print(f"   Checked: {os.path.abspath(parent_path)}")
                    print(f"   Checked: {home_path}")
                    print(f"   Current directory: {os.getcwd()}")
                    print(f"\n💡 Please ensure credentials.json is in one of these locations,")
                    print(f"   or modify the script to point to the correct path.")
                    return
        else:
            print(f"✅ Found credentials.json in current directory")
    
    print(f"✅ Found {credentials_path}")
    print(f"🔐 Starting OAuth flow...")
    print(f"   Scopes: {SCOPES}")
    print(f"\n{'='*60}")
    print("📱 A browser window will open for authentication.")
    print("   Please authorize the application to access Google Drive.")
    print(f"{'='*60}\n")
    
    try:
        # Create the flow using the client secrets
        flow = InstalledAppFlow.from_client_secrets_file(
            credentials_path,
            SCOPES
        )
        
        # Run the OAuth flow
        credentials = flow.run_local_server(port=0)
        
        # Extract the important information
        client_id = credentials.client_id
        client_secret = credentials.client_secret
        refresh_token = credentials.refresh_token
        
        print(f"\n{'='*60}")
        print("✅ Authentication successful!")
        print(f"{'='*60}\n")
        
        print("📋 IMPORTANT CREDENTIALS:")
        print(f"{'='*60}")
        print(f"CLIENT_ID:")
        print(f"{client_id}")
        print(f"\nCLIENT_SECRET:")
        print(f"{client_secret}")
        print(f"\nREFRESH_TOKEN:")
        print(f"{refresh_token}")
        print(f"{'='*60}\n")
        
        print("💾 Save these values securely!")
        print("   You can use them to authenticate API requests.")
        
    except Exception as e:
        print(f"\n❌ Error during OAuth flow: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
