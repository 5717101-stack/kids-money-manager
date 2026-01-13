#!/bin/bash

echo "🧹 מנקה cache..."
rm -rf dist node_modules/.vite .vite

echo "🔨 בונה את האפליקציה..."
npm run build

echo "✅ בנייה הושלמה!"
echo ""
echo "📱 אם אתה משתמש באפליקציה ניידת:"
echo "   1. פתח את Xcode (iOS) או Android Studio (Android)"
echo "   2. נקה את ה-build folder (Product > Clean Build Folder)"
echo "   3. בנה מחדש את האפליקציה (Product > Build)"
echo "   4. התקן מחדש על המכשיר"
echo ""
echo "🌐 אם אתה משתמש בדפדפן:"
echo "   1. לחץ Ctrl+Shift+R (Windows/Linux) או Cmd+Shift+R (Mac) לרענון מלא"
echo "   2. או נקה את ה-cache של הדפדפן"
