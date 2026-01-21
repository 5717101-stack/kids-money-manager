#!/bin/bash

# Script to update version number across all files and sync to mobile apps
# This script is automatically called when version is updated
# Usage: ./update_version.sh <new_version>
# Example: ./update_version.sh 5.0.10

set -e

if [ -z "$1" ]; then
  echo "❌ Error: Version number required"
  echo "Usage: ./update_version.sh <new_version>"
  echo "Example: ./update_version.sh 5.0.10"
  exit 1
fi

NEW_VERSION="$1"
echo "🔄 Updating version to $NEW_VERSION..."

# Update package.json (root)
if [ -f "package.json" ]; then
  sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" package.json
  echo "✅ Updated package.json"
fi

# Update server/package.json
if [ -f "server/package.json" ]; then
  sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" server/package.json
  echo "✅ Updated server/package.json"
fi

# Update Android build.gradle
if [ -f "android/app/build.gradle" ]; then
  sed -i '' "s/versionName \".*\"/versionName \"$NEW_VERSION\"/" android/app/build.gradle
  echo "✅ Updated android/app/build.gradle"
fi

# Update iOS project.pbxproj
if [ -f "ios/App/App.xcodeproj/project.pbxproj" ]; then
  sed -i '' "s/MARKETING_VERSION = [^;]*;/MARKETING_VERSION = $NEW_VERSION;/g" ios/App/App.xcodeproj/project.pbxproj
  echo "✅ Updated ios/App/App.xcodeproj/project.pbxproj"
fi

# Build the project
echo ""
echo "🔨 Building project..."
export PATH="$HOME/.nvm/versions/node/v24.12.0/bin:$PATH" 2>/dev/null || true
npm run build

# Sync with Capacitor
echo ""
echo "🔄 Syncing with Capacitor..."
npx cap sync ios
npx cap sync android

# Clean iOS build artifacts (after sync)
echo ""
echo "🧹 Cleaning iOS build artifacts..."
rm -rf ~/Library/Developer/Xcode/DerivedData 2>/dev/null || true
# Note: Don't delete ios/App/App/public - Capacitor needs it

echo ""
echo "✅ Version update complete!"
echo ""
echo "📋 Updated files:"
echo "   ✅ package.json: $NEW_VERSION"
echo "   ✅ server/package.json: $NEW_VERSION"
echo "   ✅ android/app/build.gradle: $NEW_VERSION"
echo "   ✅ ios/App/App.xcodeproj/project.pbxproj: $NEW_VERSION"
echo ""
echo "🔧 Next steps for iOS:"
echo "   1. Open Xcode"
echo "   2. Clean Build Folder: Shift+Cmd+K"
echo "   3. Close and reopen Xcode"
echo "   4. Build: Cmd+B"
echo "   5. Run: Cmd+R"
echo ""
echo "💡 The version in the app UI will be read from package.json at build time"
