#!/bin/bash

# Script to install Java 21 and build APK

set -e

cd "$(dirname "$0")"

echo "☕ Installing Java 21 and building APK..."
echo ""

# Check if Java 21 is already installed
JAVA21_HOME=$(/usr/libexec/java_home -v 21 2>/dev/null || echo "")

if [ -n "$JAVA21_HOME" ]; then
    echo "✅ Java 21 already installed: $JAVA21_HOME"
else
    echo "📥 Java 21 not found. Installing..."
    
    # Check if installer exists
    if [ -f "/tmp/openjdk21.pkg" ]; then
        echo "✅ Installer found at /tmp/openjdk21.pkg"
        echo "📦 Opening installer..."
        open /tmp/openjdk21.pkg
        echo ""
        echo "⚠️  Please complete the installation wizard."
        echo "   After installation, run this script again to build APK."
        exit 0
    else
        echo "❌ Installer not found. Downloading..."
        curl -L -o /tmp/openjdk21.pkg "https://api.adoptium.net/v3/installer/latest/21/ga/mac/aarch64/jdk/hotspot/normal/eclipse?project=jdk"
        echo "✅ Download complete. Opening installer..."
        open /tmp/openjdk21.pkg
        echo ""
        echo "⚠️  Please complete the installation wizard."
        echo "   After installation, run this script again to build APK."
        exit 0
    fi
fi

# Set Java 21
export JAVA_HOME="$JAVA21_HOME"
export PATH="$JAVA_HOME/bin:$PATH"

echo "☕ Using Java: $($JAVA_HOME/bin/java -version 2>&1 | head -1)"
echo ""

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
./gradlew clean
./gradlew assembleProdRelease
echo "   ✅ APK built"
echo ""

# Find APK
APK_PATH=""
if [ -f "app/build/outputs/apk/prod/release/app-prod-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/prod/release/app-prod-release.apk"
elif [ -f "app/build/outputs/apk/release/app-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/release/app-release.apk"
else
    APK_PATH=$(find app/build/outputs/apk -name "*release*.apk" -type f 2>/dev/null | head -1)
fi

if [ -z "$APK_PATH" ] || [ ! -f "$APK_PATH" ]; then
    echo "❌ APK not found!"
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
