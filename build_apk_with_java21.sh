#!/bin/bash

# Script to build APK with Java 21

set -e

echo "📦 Building APK with Java 21..."
echo ""

# Check if Java 21 is installed
JAVA21_HOME=$(/usr/libexec/java_home -v 21 2>/dev/null || echo "")
if [ -z "$JAVA21_HOME" ]; then
    echo "❌ Java 21 לא מותקן!"
    echo ""
    echo "📥 הורד והתקן Java 21:"
    echo "   1. פתח: /tmp/openjdk21.pkg"
    echo "   2. או הורד מ: https://adoptium.net/temurin/releases/?version=21"
    echo "   3. בחר: macOS / aarch64 / JDK 21 / .pkg"
    echo ""
    exit 1
fi

echo "✅ Java 21 נמצא: $JAVA21_HOME"
echo ""

# Set Java 21
export JAVA_HOME="$JAVA21_HOME"
echo "☕ Using Java: $($JAVA_HOME/bin/java -version 2>&1 | head -1)"
echo ""

# Navigate to project root
cd "$(dirname "$0")"

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
./gradlew --stop
./gradlew clean
./gradlew assembleRelease
echo "   ✅ APK built"
echo ""

# Check if APK exists
APK_PATH="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    VERSION=$(grep '"version"' ../package.json | cut -d'"' -f4)
    echo "📊 APK size: $APK_SIZE"
    echo "📱 Version: $VERSION"
    echo ""
    
    # Copy to Desktop
    DESKTOP_APK="$HOME/Desktop/Family-Bank-${VERSION}.apk"
    cp "$APK_PATH" "$DESKTOP_APK"
    echo "✅ APK exported to Desktop:"
    echo "   $DESKTOP_APK"
    echo ""
    echo "📤 You can now share this APK file!"
else
    echo "❌ APK not found at: $APK_PATH"
    exit 1
fi
