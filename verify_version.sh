#!/bin/bash
echo "🔍 Verifying all version numbers..."
echo ""

# Check package.json
PKG_VERSION=$(grep '"version"' package.json | head -1 | cut -d'"' -f4)
echo "📦 package.json: $PKG_VERSION"

# Check Android
ANDROID_VERSION=$(grep 'versionName' android/app/build.gradle | head -1 | cut -d'"' -f2)
ANDROID_CODE=$(grep 'versionCode' android/app/build.gradle | head -1 | awk '{print $2}')
echo "🤖 Android: $ANDROID_VERSION (code: $ANDROID_CODE)"

# Check iOS - all occurrences
echo "🍎 iOS versions:"
grep 'MARKETING_VERSION' ios/App/App.xcodeproj/project.pbxproj | while read line; do
  VERSION=$(echo "$line" | awk '{print $3}' | tr -d ';')
  echo "   MARKETING_VERSION: $VERSION"
done

grep 'CURRENT_PROJECT_VERSION' ios/App/App.xcodeproj/project.pbxproj | while read line; do
  CODE=$(echo "$line" | awk '{print $3}' | tr -d ';')
  echo "   CURRENT_PROJECT_VERSION: $CODE"
done

echo ""
if [ "$PKG_VERSION" = "$ANDROID_VERSION" ]; then
  echo "✅ package.json and Android match: $PKG_VERSION"
else
  echo "❌ Version mismatch: package.json=$PKG_VERSION, Android=$ANDROID_VERSION"
fi
