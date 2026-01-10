#!/bin/bash

echo "Updating iOS app icon..."

# Clean Xcode caches
echo "1. Cleaning Xcode caches..."
rm -rf ~/Library/Developer/Xcode/DerivedData/*
rm -rf ~/Library/Caches/com.apple.dt.Xcode/*

# Copy the icon again to make sure it's updated
if [ -f "app-icon.png" ]; then
    echo "2. Copying app icon to iOS..."
    sips -z 1024 1024 app-icon.png --out ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png
    echo "✓ iOS icon updated"
    
    # Verify
    echo "3. Verifying icon..."
    sips -g hasAlpha ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png
else
    echo "Error: app-icon.png not found"
    exit 1
fi

echo ""
echo "Done! Now:"
echo "1. Open Xcode: npx cap open ios"
echo "2. Product → Clean Build Folder (Shift+Cmd+K)"
echo "3. Delete the app from your device/simulator"
echo "4. Product → Build (Cmd+B)"
echo "5. Product → Run (Cmd+R)"
