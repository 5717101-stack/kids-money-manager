#!/bin/bash

# Script to replace app icons with a new image
# Usage: ./replace_app_icon.sh <path_to_icon_image.png>

if [ -z "$1" ]; then
    echo "Usage: ./replace_app_icon.sh <path_to_icon_image.png>"
    exit 1
fi

ICON_FILE="$1"

if [ ! -f "$ICON_FILE" ]; then
    echo "Error: File not found: $ICON_FILE"
    exit 1
fi

echo "Replacing app icons with: $ICON_FILE"

# iOS - Replace the 1024x1024 icon
if command -v sips &> /dev/null; then
    echo "Creating iOS icon..."
    sips -z 1024 1024 "$ICON_FILE" --out ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png
    echo "✓ iOS icon created"
else
    echo "⚠ sips not found, please manually replace ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png with a 1024x1024 PNG"
fi

# Android - Create all required sizes
if command -v sips &> /dev/null; then
    echo "Creating Android icons..."
    
    # mipmap-mdpi (48x48)
    sips -z 48 48 "$ICON_FILE" --out android/app/src/main/res/mipmap-mdpi/ic_launcher.png
    sips -z 48 48 "$ICON_FILE" --out android/app/src/main/res/mipmap-mdpi/ic_launcher_round.png
    sips -z 108 108 "$ICON_FILE" --out android/app/src/main/res/mipmap-mdpi/ic_launcher_foreground.png
    
    # mipmap-hdpi (72x72)
    sips -z 72 72 "$ICON_FILE" --out android/app/src/main/res/mipmap-hdpi/ic_launcher.png
    sips -z 72 72 "$ICON_FILE" --out android/app/src/main/res/mipmap-hdpi/ic_launcher_round.png
    sips -z 162 162 "$ICON_FILE" --out android/app/src/main/res/mipmap-hdpi/ic_launcher_foreground.png
    
    # mipmap-xhdpi (96x96)
    sips -z 96 96 "$ICON_FILE" --out android/app/src/main/res/mipmap-xhdpi/ic_launcher.png
    sips -z 96 96 "$ICON_FILE" --out android/app/src/main/res/mipmap-xhdpi/ic_launcher_round.png
    sips -z 216 216 "$ICON_FILE" --out android/app/src/main/res/mipmap-xhdpi/ic_launcher_foreground.png
    
    # mipmap-xxhdpi (144x144)
    sips -z 144 144 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png
    sips -z 144 144 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxhdpi/ic_launcher_round.png
    sips -z 432 432 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxhdpi/ic_launcher_foreground.png
    
    # mipmap-xxxhdpi (192x192)
    sips -z 192 192 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png
    sips -z 192 192 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.png
    sips -z 432 432 "$ICON_FILE" --out android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_foreground.png
    
    echo "✓ Android icons created"
else
    echo "⚠ sips not found, please manually replace Android icons in android/app/src/main/res/mipmap-*/"
fi

echo ""
echo "Done! App icons have been replaced."
echo "Next steps:"
echo "1. Open Xcode and rebuild the iOS app"
echo "2. Rebuild the Android app"
