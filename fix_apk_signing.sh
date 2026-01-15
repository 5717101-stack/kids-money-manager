#!/bin/bash

# Fix APK signing - create keystore if missing

set -e

cd "$(dirname "$0")"

echo "🔐 Fixing APK signing..."
echo ""

# Check if keystore exists
if [ -f "android/app/release.keystore" ]; then
    echo "✅ Keystore already exists"
else
    echo "📦 Creating keystore..."
    
    # Try to find keytool
    KEYTOOL=""
    if command -v keytool &> /dev/null; then
        KEYTOOL="keytool"
    elif [ -d "/Applications/Android Studio.app/Contents/jbr" ]; then
        KEYTOOL="/Applications/Android Studio.app/Contents/jbr/bin/keytool"
    elif [ -d "$HOME/Library/Application Support/Google/AndroidStudio" ]; then
        JBR_PATH=$(find "$HOME/Library/Application Support/Google/AndroidStudio" -name "jbr" -type d | head -1)
        if [ -n "$JBR_PATH" ] && [ -f "$JBR_PATH/bin/keytool" ]; then
            KEYTOOL="$JBR_PATH/bin/keytool"
        fi
    fi
    
    if [ -z "$KEYTOOL" ] || [ ! -f "$KEYTOOL" ]; then
        echo "❌ keytool not found!"
        echo ""
        echo "💡 Install Java JDK or Android Studio to create keystore"
        echo "   Or create keystore manually in Android Studio"
        exit 1
    fi
    
    # Create keystore
    mkdir -p android/app
    "$KEYTOOL" -genkey -v -keystore android/app/release.keystore \
        -alias release -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass android -keypass android \
        -dname "CN=Family Bank, OU=Development, O=Family Bank, L=Tel Aviv, ST=Israel, C=IL"
    
    echo "✅ Keystore created"
fi

# Create key.properties if missing
if [ ! -f "android/key.properties" ]; then
    echo "📝 Creating key.properties..."
    cat > android/key.properties << EOF
storePassword=android
keyPassword=android
keyAlias=release
storeFile=release.keystore
EOF
    echo "✅ key.properties created"
else
    echo "✅ key.properties already exists"
fi

echo ""
echo "✅ Signing configuration ready!"
echo ""
echo "📱 Now build APK in Android Studio:"
echo "   1. npx cap open android"
echo "   2. Build → Build Bundle(s) / APK(s) → Build APK(s)"
echo "   3. Select 'prodRelease' variant"
echo ""
