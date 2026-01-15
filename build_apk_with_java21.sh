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
echo "3. Building signed release APK..."
cd android
./gradlew --stop
./gradlew clean

# Check if key.properties exists
if [ ! -f "key.properties" ]; then
    echo "❌ key.properties לא נמצא!"
    echo "   צריך ליצור את הקובץ android/key.properties עם:"
    echo "   storePassword=..."
    echo "   keyPassword=..."
    echo "   keyAlias=..."
    echo "   storeFile=app/release.keystore"
    exit 1
fi

# Build signed APK for prod flavor
./gradlew assembleProdRelease
echo "   ✅ APK built"
echo ""

# Check if signed APK exists (signed APKs don't have "-unsigned" in the name)
APK_PATH=""
if [ -f "app/build/outputs/apk/prod/release/app-prod-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/prod/release/app-prod-release.apk"
elif [ -f "app/build/outputs/apk/prod/release/app-prod-release-unsigned.apk" ]; then
    echo "⚠️  Warning: Found unsigned APK. Checking signing config..."
    APK_PATH="app/build/outputs/apk/prod/release/app-prod-release-unsigned.apk"
elif [ -f "app/build/outputs/apk/release/app-release.apk" ]; then
    APK_PATH="app/build/outputs/apk/release/app-release.apk"
else
    # Try to find any APK (prefer prod release, signed)
    APK_PATH=$(find app/build/outputs/apk -name "*.apk" -type f 2>/dev/null | grep -E "prod.*release" | grep -v "unsigned" | head -1)
    if [ -z "$APK_PATH" ]; then
        APK_PATH=$(find app/build/outputs/apk -name "*.apk" -type f 2>/dev/null | grep -E "prod.*release" | head -1)
    fi
    if [ -z "$APK_PATH" ]; then
        APK_PATH=$(find app/build/outputs/apk -name "*.apk" -type f 2>/dev/null | grep -E "release" | grep -v "unsigned" | head -1)
    fi
fi

if [ -n "$APK_PATH" ] && [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    VERSION=$(grep '"version"' ../package.json | cut -d'"' -f4)
    echo "📊 APK size: $APK_SIZE"
    echo "📱 Version: $VERSION"
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
