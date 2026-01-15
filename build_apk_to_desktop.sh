#!/bin/bash

# Script to build APK and copy to Desktop/apk folder

set -e

echo "📦 Building APK..."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Check if Java is available (try multiple methods)
JAVA_HOME=""
if [ -n "$JAVA_HOME" ]; then
    echo "✅ Using JAVA_HOME: $JAVA_HOME"
elif command -v java &> /dev/null; then
    JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
    echo "✅ Found Java: $JAVA_HOME"
elif [ -d "/Applications/Android Studio.app/Contents/jbr" ]; then
    JAVA_HOME="/Applications/Android Studio.app/Contents/jbr"
    echo "✅ Using Android Studio Java: $JAVA_HOME"
elif [ -d "$HOME/Library/Application Support/Google/AndroidStudio" ]; then
    JBR_PATH=$(find "$HOME/Library/Application Support/Google/AndroidStudio" -name "jbr" -type d | head -1)
    if [ -n "$JBR_PATH" ]; then
        JAVA_HOME="$JBR_PATH"
        echo "✅ Using Android Studio JBR: $JAVA_HOME"
    fi
fi

if [ -z "$JAVA_HOME" ]; then
    echo "⚠️ Java not found. Trying to build anyway with system Java..."
    echo "   If build fails, install Java 21 or use Android Studio"
    echo ""
fi

# Set JAVA_HOME if found
if [ -n "$JAVA_HOME" ]; then
    export JAVA_HOME
    export PATH="$JAVA_HOME/bin:$PATH"
fi

# Build web assets
echo "1. Building web assets..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
PATH="$HOME/.nvm/versions/node/v24.12.0/bin:$PATH"
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

# Try to build with gradlew
if [ -f "./gradlew" ]; then
    chmod +x ./gradlew
    ./gradlew clean
    ./gradlew assembleRelease
else
    echo "❌ gradlew not found!"
    exit 1
fi

echo "   ✅ APK built"
echo ""

# Find APK
APK_PATH=""
if [ -f "app/build/outputs/apk/prod/release/app-prod-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/prod/release/app-prod-release.apk"
elif [ -f "app/build/outputs/apk/release/app-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/release/app-release.apk"
else
    # Try to find any release APK
    APK_PATH=$(find app/build/outputs/apk -name "*release*.apk" -type f 2>/dev/null | head -1)
fi

if [ -z "$APK_PATH" ] || [ ! -f "$APK_PATH" ]; then
    echo "❌ APK not found!"
    echo "   Searched in: app/build/outputs/apk/"
    echo ""
    echo "💡 Try building through Android Studio:"
    echo "   1. npx cap open android"
    echo "   2. Build → Build Bundle(s) / APK(s) → Build APK(s)"
    exit 1
fi

# Get version and create Desktop/apk folder
VERSION=$(grep '"version"' ../package.json | cut -d'"' -f4)
APK_DIR="$HOME/Desktop/apk"
mkdir -p "$APK_DIR"

# Copy APK to Desktop/apk
APK_NAME="Family-Bank-${VERSION}.apk"
DESKTOP_APK="$APK_DIR/$APK_NAME"
cp "$APK_PATH" "$DESKTOP_APK"

# Get APK size
APK_SIZE=$(du -h "$DESKTOP_APK" | cut -f1)

echo "✅ APK exported successfully!"
echo ""
echo "📱 Version: $VERSION"
echo "📊 Size: $APK_SIZE"
echo "📁 Location: $DESKTOP_APK"
echo ""
echo "🎉 APK ready to share!"
