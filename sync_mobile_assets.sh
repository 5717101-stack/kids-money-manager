#!/bin/bash

# Script to build and sync web assets to iOS and Android
# This ensures the version number is always updated in mobile builds

set -e

echo "🔨 Building web assets..."
npm run build

echo "📦 Copying assets to iOS..."
rm -rf ios/App/App/public
mkdir -p ios/App/App/public
cp -r dist/* ios/App/App/public/
echo "✅ iOS assets synced"

echo "📦 Copying assets to Android..."
rm -rf android/app/src/main/assets/public
mkdir -p android/app/src/main/assets/public
cp -r dist/* android/app/src/main/assets/public/
echo "✅ Android assets synced"

echo "🧹 Cleaning Xcode DerivedData..."
rm -rf ~/Library/Developer/Xcode/DerivedData/*
echo "✅ DerivedData cleaned"

# Get version from package.json
VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
echo ""
echo "✅ Build complete! Version: $VERSION"
echo "📱 Next steps:"
echo "   1. Open Xcode/Android Studio"
echo "   2. Clean Build Folder (⇧⌘K in Xcode)"
echo "   3. Build and Run (⌘R in Xcode)"
