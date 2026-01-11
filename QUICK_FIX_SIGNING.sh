#!/bin/bash

# Quick fix script for iOS signing issues

echo "🔧 Fixing iOS signing issues..."
echo ""

# Clear DerivedData
echo "1. Clearing Xcode DerivedData..."
rm -rf ~/Library/Developer/Xcode/DerivedData/App-*
echo "   ✅ Cleared"

# Clear old provisioning profiles
echo "2. Clearing old provisioning profiles..."
rm -rf ~/Library/MobileDevice/Provisioning\ Profiles/* 2>/dev/null
echo "   ✅ Cleared"

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📋 Next steps in Xcode:"
echo ""
echo "1. Open Xcode:"
echo "   npx cap open ios"
echo ""
echo "2. In Xcode:"
echo "   - Click 'App' project (blue icon)"
echo "   - Select 'App' under TARGETS"
echo "   - Go to 'Signing & Capabilities' tab"
echo "   - ✅ Check 'Automatically manage signing'"
echo "   - Select your Team"
echo ""
echo "3. If you see certificate errors:"
echo "   - Xcode → Settings → Accounts"
echo "   - Select your account"
echo "   - Click 'Manage Certificates...'"
echo "   - Delete revoked certificates (red X)"
echo "   - Click '+' → 'Apple Development'"
echo ""
echo "4. Clean and build:"
echo "   - Product → Clean Build Folder (Shift+Cmd+K)"
echo "   - Product → Build (Cmd+B)"
echo "   - Product → Run (Cmd+R)"
echo ""
