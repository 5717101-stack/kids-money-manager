#!/bin/bash

echo "Force updating iOS app icon..."

# Remove old icon
rm -f ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png

# Copy new icon with proper size
if [ -f "app-icon.png" ]; then
    sips -z 1024 1024 app-icon.png --out ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png
    
    # Verify
    if [ -f "ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png" ]; then
        echo "✓ Icon copied successfully"
        sips -g pixelWidth -g pixelHeight -g hasAlpha ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png
    else
        echo "✗ Failed to copy icon"
        exit 1
    fi
else
    echo "✗ app-icon.png not found"
    exit 1
fi

# Clean all caches
echo ""
echo "Cleaning caches..."
rm -rf ~/Library/Developer/Xcode/DerivedData/*
rm -rf ~/Library/Caches/com.apple.dt.Xcode/*

echo ""
echo "✓ Done! Now:"
echo "1. Open Xcode: npx cap open ios"
echo "2. In Xcode, select the project → App target → General tab"
echo "3. Scroll to 'App Icons and Launch Screen'"
echo "4. Click on AppIcon to see the icon"
echo "5. Product → Clean Build Folder (Shift+Cmd+K)"
echo "6. DELETE the app from your device/simulator completely"
echo "7. Product → Build (Cmd+B)"
echo "8. Product → Run (Cmd+R)"
