#!/bin/bash

# Script to verify that web and mobile app are in sync

echo "🔍 בודק סינכרון בין דפדפן לאפליקציה..."
echo ""

# Check if OTPVerification has the fix
echo "1️⃣ בודק את התיקון ב-OTPVerification.jsx..."
if grep -q "seconds: resendTimer" src/components/OTPVerification.jsx; then
    echo "   ✅ הקוד תוקן - הפרמטר seconds מועבר נכון"
else
    echo "   ❌ הקוד לא תוקן!"
    exit 1
fi

# Check translation files
echo ""
echo "2️⃣ בודק קבצי תרגום..."
if grep -q "\"resendIn\".*seconds" src/i18n/locales/en.json && grep -q "\"resendIn\".*שניות" src/i18n/locales/he.json; then
    echo "   ✅ קבצי התרגום תקינים"
else
    echo "   ❌ בעיה בקבצי התרגום!"
    exit 1
fi

# Check build directory
echo ""
echo "3️⃣ בודק אם יש build עדכני..."
if [ -d "dist" ] && [ -f "dist/index.html" ]; then
    echo "   ✅ תיקיית dist קיימת"
    BUILD_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" dist/index.html 2>/dev/null || stat -c "%y" dist/index.html 2>/dev/null)
    echo "   📅 זמן build: $BUILD_TIME"
else
    echo "   ⚠️  תיקיית dist לא קיימת - צריך לבנות"
fi

# Check iOS build
echo ""
echo "4️⃣ בודק iOS build..."
if [ -d "ios/App/App/public" ]; then
    echo "   ✅ תיקיית iOS public קיימת"
    if [ -f "ios/App/App/public/index.html" ]; then
        IOS_BUILD_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" ios/App/App/public/index.html 2>/dev/null || stat -c "%y" ios/App/App/public/index.html 2>/dev/null)
        echo "   📅 זמן build iOS: $IOS_BUILD_TIME"
    fi
else
    echo "   ⚠️  תיקיית iOS public לא קיימת"
fi

echo ""
echo "📋 סיכום:"
echo "   - הקוד תוקן ✅"
echo "   - קבצי התרגום תקינים ✅"
echo ""
echo "🔧 כדי לוודא שהכל מסונכרן:"
echo "   1. הרץ: npm run build"
echo "   2. הרץ: npx cap sync"
echo "   3. בדפדפן: עשה hard refresh (Cmd+Shift+R)"
echo "   4. באפליקציה: בנה מחדש ב-Xcode"
echo ""
