#!/bin/bash
echo "🔨 Force rebuilding for version 3.10.4..."
echo ""

echo "📦 Building web assets..."
npm run build

echo ""
echo "🔄 Syncing Capacitor..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 22
npx cap sync ios

echo ""
echo "🧹 Cleaning Xcode caches..."
find ~/Library/Developer/Xcode/DerivedData -name "App-*" -type d -exec rm -rf {} + 2>/dev/null
rm -rf ~/Library/Caches/com.apple.dt.Xcode/* 2>/dev/null

echo ""
echo "✅ Done! Now:"
echo "1. Open Xcode: npx cap open ios"
echo "2. Product → Clean Build Folder (Shift+Cmd+K)"
echo "3. DELETE the app from your device/simulator"
echo "4. Product → Build (Cmd+B)"
echo "5. Product → Run (Cmd+R)"
