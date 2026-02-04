#!/usr/bin/env python3
"""
Script to check Meta WhatsApp token type and expiration.
Run this to see if your token is Short-Lived (1 hour) or Long-Lived (60 days).
"""

import sys
import requests
from datetime import datetime

def check_token(token):
    """Check token type and expiration."""
    if not token:
        print("❌ No token provided")
        return
    
    print(f"\n{'='*60}")
    print(f"🔍 Checking Meta WhatsApp Token")
    print(f"{'='*60}\n")
    
    try:
        url = "https://graph.facebook.com/v18.0/debug_token"
        params = {
            "input_token": token,
            "access_token": token
        }
        
        print("📡 Sending request to Meta API...")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            token_data = data.get('data', {})
            
            is_valid = token_data.get('is_valid', False)
            expires_at = token_data.get('expires_at')
            app_id = token_data.get('app_id')
            
            print(f"✅ Token is valid: {is_valid}")
            print(f"   App ID: {app_id}")
            
            if expires_at:
                exp_time = datetime.fromtimestamp(expires_at)
                now = datetime.now()
                days_left = (exp_time - now).days
                hours_left = (exp_time - now).total_seconds() / 3600
                minutes_left = (exp_time - now).total_seconds() / 60
                
                print(f"\n📅 Token Expiration Info:")
                print(f"   Expires at: {exp_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Time left: {days_left} days, {int(hours_left % 24)} hours, {int(minutes_left % 60)} minutes")
                
                if days_left > 30:
                    print(f"\n✅ Token Type: LONG-LIVED (60 days)")
                    print(f"   ✅ This token will last 60 days - you're good!")
                elif hours_left < 24:
                    print(f"\n⚠️  Token Type: SHORT-LIVED (1 hour)")
                    print(f"   ❌ This token expires after 1 hour!")
                    print(f"   ⚠️  You need to convert it to Long-Lived token!")
                    print(f"\n   To convert, run:")
                    print(f"   curl -X GET \"https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token={token[:20]}...\"")
                else:
                    print(f"\n⚠️  Token Type: UNKNOWN (expires in {int(hours_left)} hours)")
            else:
                print(f"\n⚠️  Could not determine expiration date")
        else:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            print(f"❌ Error checking token: {error_msg}")
            print(f"   Status code: {response.status_code}")
            
            if "expired" in error_msg.lower() or "invalid" in error_msg.lower():
                print(f"\n⚠️  Your token is EXPIRED or INVALID!")
                print(f"   You need to generate a new token.")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_token.py YOUR_TOKEN")
        print("\nTo get your token from Render:")
        print("1. Go to Render Dashboard")
        print("2. Select your service")
        print("3. Go to Environment tab")
        print("4. Copy WHATSAPP_CLOUD_API_TOKEN value")
        sys.exit(1)
    
    token = sys.argv[1]
    check_token(token)
