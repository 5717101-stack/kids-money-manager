#!/bin/bash

# Script to build Android APK

set -e

echo "🔨 Building Android APK..."

# Check if we're in the right directory
if [ ! -d "android" ]; then
    echo "❌ Error: android directory not found. Please run this script from the project root."
    exit 1
fi

# Set environment variables
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/build-tools/34.0.0
export JAVA_HOME=$(/usr/libexec/java_home 2>/dev/null || echo "")

# Build web assets first
echo "📦 Building web assets..."
npm run build

# Sync Capacitor
echo "🔄 Syncing Capacitor..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 22 2>/dev/null || true
npx cap sync android

# Navigate to android directory
cd android

# Build APK
echo "🔨 Building release APK..."
./gradlew assembleRelease

# Check if APK was created
APK_PATH="app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
    echo ""
    echo "✅ APK built successfully!"
    echo "📱 APK location: $(pwd)/$APK_PATH"
    echo ""
    
    # Get APK size
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo "📊 APK size: $APK_SIZE"
    
    # Copy to project root for easy access
    cp "$APK_PATH" "../kids-money-manager-$(date +%Y%m%d-%H%M%S).apk"
    echo "📋 Also copied to project root with timestamp"
    
    # Copy to FamilyBank folder on Desktop
    FAMILYBANK_DIR="$HOME/Desktop/FamilyBank"
    mkdir -p "$FAMILYBANK_DIR"
    VERSION=$(grep '"version"' ../package.json | cut -d'"' -f4)
    FAMILYBANK_APK="$FAMILYBANK_DIR/Family-Bank-${VERSION}.apk"
    cp "$APK_PATH" "$FAMILYBANK_APK"
    echo "📁 Also copied to FamilyBank folder:"
    echo "   $FAMILYBANK_APK"
else
    echo "❌ APK not found at expected location: $APK_PATH"
    exit 1
fi
