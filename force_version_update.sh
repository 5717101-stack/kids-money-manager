#!/bin/bash

echo "🔍 Checking version numbers..."
echo ""

# Check package.json
PKG_VERSION=$(grep '"version"' package.json | head -1 | cut -d'"' -f4)
echo "📦 package.json: $PKG_VERSION"

# Check Android
ANDROID_VERSION=$(grep 'versionName' android/app/build.gradle | head -1 | cut -d'"' -f2)
ANDROID_CODE=$(grep 'versionCode' android/app/build.gradle | head -1 | awk '{print $2}')
echo "🤖 Android: $ANDROID_VERSION (code: $ANDROID_CODE)"

# Check iOS
IOS_VERSION=$(grep 'MARKETING_VERSION' ios/App/App.xcodeproj/project.pbxproj | head -1 | awk '{print $3}' | tr -d ';')
IOS_CODE=$(grep 'CURRENT_PROJECT_VERSION' ios/App/App.xcodeproj/project.pbxproj | head -1 | awk '{print $3}' | tr -d ';')
echo "🍎 iOS: $IOS_VERSION (code: $IOS_CODE)"

echo ""
if [ "$PKG_VERSION" = "$ANDROID_VERSION" ] && [ "$PKG_VERSION" = "$IOS_VERSION" ]; then
    echo "✅ All versions match: $PKG_VERSION"
else
    echo "❌ Version mismatch detected!"
    exit 1
fi

echo ""
echo "🧹 Cleaning Xcode caches..."
rm -rf ~/Library/Developer/Xcode/DerivedData/* 2>/dev/null
rm -rf ~/Library/Caches/com.apple.dt.Xcode/* 2>/dev/null
echo "✅ Caches cleaned"

echo ""
echo "📱 Next steps:"
echo "1. Open Xcode: npx cap open ios"
echo "2. Product → Clean Build Folder (Shift+Cmd+K)"
echo "3. DELETE the app from your device/simulator"
echo "4. Product → Build (Cmd+B)"
echo "5. Product → Run (Cmd+R)"
