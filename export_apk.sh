#!/bin/bash

# Script to export APK for distribution

set -e

echo "📦 Exporting APK for distribution..."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Get version
VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
echo "📱 Version: $VERSION"
echo ""

# Build web assets
echo "1. Building web assets..."
npm run build
echo "   ✅ Web assets built"
echo ""

# Sync Capacitor
echo "2. Syncing Capacitor..."
npx cap sync android
echo "   ✅ Capacitor synced"
echo ""

# Build APK
echo "3. Building release APK..."
cd android
export JAVA_HOME=$(/usr/libexec/java_home -v 17 2>/dev/null || /usr/libexec/java_home)
./gradlew assembleRelease
echo "   ✅ APK built"
echo ""

# Check if APK exists
APK_PATH="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo "📊 APK size: $APK_SIZE"
    echo ""
    
    # Copy to Desktop and FamilyBank folder
    DESKTOP_APK="$HOME/Desktop/Family-Bank-${VERSION}.apk"
    FAMILYBANK_DIR="$HOME/Desktop/FamilyBank"
    FAMILYBANK_APK="$FAMILYBANK_DIR/Family-Bank-${VERSION}.apk"
    
    # Create FamilyBank directory if it doesn't exist
    mkdir -p "$FAMILYBANK_DIR"
    
    # Copy to Desktop
    cp "$APK_PATH" "$DESKTOP_APK"
    echo "✅ APK exported to Desktop:"
    echo "   $DESKTOP_APK"
    
    # Copy to FamilyBank folder
    cp "$APK_PATH" "$FAMILYBANK_APK"
    echo "✅ APK exported to FamilyBank folder:"
    echo "   $FAMILYBANK_APK"
    echo ""
    echo "📤 You can now share this APK file!"
else
    echo "❌ APK not found at: $APK_PATH"
    exit 1
fi
