#!/bin/bash

echo "🔍 בודק גרסאות..."
echo ""
echo "=== package.json ==="
grep '"version"' package.json
echo ""
echo "=== android/app/build.gradle ==="
grep -E "versionCode|versionName" android/app/build.gradle | head -2
echo ""
echo "=== iOS project ==="
grep -E "MARKETING_VERSION|CURRENT_PROJECT_VERSION" ios/App/App.xcodeproj/project.pbxproj | head -2
echo ""

echo "🧹 מנקה cache..."
rm -rf dist node_modules/.vite .vite
rm -rf android/app/build
rm -rf ios/App/build

echo "🔨 בונה את האפליקציה..."
npm run build

echo ""
echo "✅ בנייה הושלמה!"
echo ""
echo "📱 אם אתה משתמש באפליקציה ניידת:"
echo "   1. סנכרן עם Capacitor (אם Node >= 22):"
echo "      npx cap sync"
echo ""
echo "   2. פתח את Xcode (iOS) או Android Studio (Android)"
echo ""
echo "   3. נקה את ה-build folder:"
echo "      - Xcode: Product > Clean Build Folder (Shift+Cmd+K)"
echo "      - Android Studio: Build > Clean Project"
echo ""
echo "   4. בנה מחדש את האפליקציה:"
echo "      - Xcode: Product > Build (Cmd+B)"
echo "      - Android Studio: Build > Rebuild Project"
echo ""
echo "   5. התקן מחדש על המכשיר"
echo ""
echo "🌐 אם אתה משתמש בדפדפן:"
echo "   1. לחץ Ctrl+Shift+R (Windows/Linux) או Cmd+Shift+R (Mac) לרענון מלא"
echo "   2. או נקה את ה-cache של הדפדפן"
