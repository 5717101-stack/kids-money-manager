#!/bin/bash

# Script to setup Android build environment for APK generation

echo "🔧 Setting up Android build environment..."

# Check if Java is installed
if ! command -v java &> /dev/null; then
    echo "❌ Java is not installed."
    echo "📥 Please install Java JDK 17 or later:"
    echo "   Option 1: Download from https://adoptium.net/"
    echo "   Option 2: Install via Homebrew: brew install --cask temurin"
    echo ""
    echo "After installing Java, run this script again."
    exit 1
fi

# Check Java version
JAVA_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | cut -d'.' -f1)
if [ "$JAVA_VERSION" -lt 17 ]; then
    echo "⚠️  Java version $JAVA_VERSION detected. Java 17 or later is recommended."
fi

echo "✅ Java found: $(java -version 2>&1 | head -1)"

# Check if Android SDK is available
if [ -z "$ANDROID_HOME" ] && [ -z "$ANDROID_SDK_ROOT" ]; then
    echo "⚠️  ANDROID_HOME or ANDROID_SDK_ROOT not set."
    echo "📥 Please install Android Studio from https://developer.android.com/studio"
    echo "   After installation, set ANDROID_HOME environment variable:"
    echo "   export ANDROID_HOME=\$HOME/Library/Android/sdk"
    echo "   export PATH=\$PATH:\$ANDROID_HOME/tools:\$ANDROID_HOME/platform-tools"
    echo ""
    echo "Or add to your ~/.zshrc or ~/.bash_profile:"
    echo "   export ANDROID_HOME=\$HOME/Library/Android/sdk"
    echo "   export PATH=\$PATH:\$ANDROID_HOME/tools:\$ANDROID_HOME/platform-tools"
else
    echo "✅ Android SDK found: ${ANDROID_HOME:-$ANDROID_SDK_ROOT}"
fi

# Check if keystore exists
if [ ! -f "android/app/release.keystore" ]; then
    echo "🔑 Creating release keystore..."
    echo ""
    echo "You will be prompted to enter:"
    echo "  - Keystore password (remember this!)"
    echo "  - Key password (can be same as keystore password)"
    echo "  - Your name and organization details"
    echo ""
    read -p "Press Enter to continue..."
    
    keytool -genkey -v -keystore android/app/release.keystore \
        -alias release -keyalg RSA -keysize 2048 -validity 10000 \
        -storepass android -keypass android \
        -dname "CN=Kids Money Manager, OU=Development, O=Bachar, L=Tel Aviv, ST=Israel, C=IL"
    
    if [ $? -eq 0 ]; then
        echo "✅ Keystore created successfully!"
        echo "⚠️  Default passwords used: 'android' (CHANGE THESE IN PRODUCTION!)"
        echo "⚠️  Keystore file: android/app/release.keystore"
    else
        echo "❌ Failed to create keystore. Please install Java JDK first."
        exit 1
    fi
else
    echo "✅ Keystore already exists: android/app/release.keystore"
fi

# Create key.properties file
if [ ! -f "android/key.properties" ]; then
    echo "📝 Creating key.properties file..."
    cat > android/key.properties << EOF
storePassword=android
keyPassword=android
keyAlias=release
storeFile=app/release.keystore
EOF
    echo "✅ key.properties created!"
    echo "⚠️  Using default passwords. Change them in android/key.properties for production!"
else
    echo "✅ key.properties already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Review and update android/key.properties with your actual passwords"
echo "2. Make sure android/app/release.keystore is backed up securely"
echo "3. Run: ./build_apk.sh to build the APK"
