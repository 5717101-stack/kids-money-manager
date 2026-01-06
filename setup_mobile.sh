#!/bin/bash
# סקריפט להגדרת סביבת מובייל

export PATH="$HOME/.local/node22/bin:$PATH"

cd ~/Projects/kids-money-manager

echo "=== הגדרת אפליקציית מובייל ==="
echo ""

# בדוק Node.js
if ! command -v node &> /dev/null || [ "$(node --version | cut -d'v' -f2 | cut -d'.' -f1)" -lt 22 ]; then
    echo "⚠️ Node.js 22+ נדרש"
    echo "משתמש ב-Node.js 22 מהתיקייה המקומית..."
    export PATH="$HOME/.local/node22/bin:$PATH"
fi

echo "✓ Node.js: $(node --version)"
echo ""

# בדוק אם Capacitor כבר מותקן
if [ ! -d "node_modules/@capacitor" ]; then
    echo "מתקין Capacitor..."
    npm install @capacitor/core @capacitor/cli @capacitor/ios @capacitor/android @capacitor/app @capacitor/keyboard @capacitor/status-bar
    echo "✓ Capacitor הותקן"
else
    echo "✓ Capacitor כבר מותקן"
fi

echo ""

# בדוק אם יש capacitor.config
if [ ! -f "capacitor.config.ts" ] && [ ! -f "capacitor.config.js" ]; then
    echo "מאתחל Capacitor..."
    echo -e "Kids Money Manager\ncom.bachar.kidsmoneymanager\ndist" | npx cap init
    echo "✓ Capacitor אותחל"
else
    echo "✓ Capacitor כבר מוגדר"
fi

echo ""

# בדוק אם יש תיקיות iOS/Android
if [ ! -d "ios" ]; then
    echo "מוסיף פלטפורמת iOS..."
    npx cap add ios
    echo "✓ iOS נוסף"
else
    echo "✓ iOS כבר קיים"
fi

if [ ! -d "android" ]; then
    echo "מוסיף פלטפורמת Android..."
    npx cap add android
    echo "✓ Android נוסף"
else
    echo "✓ Android כבר קיים"
fi

echo ""

# בנייה וסינכרון
echo "בונה ומסנכרן..."
npm run build
npx cap sync

echo ""
echo "✅ הכל מוכן!"
echo ""
echo "לפתיחת Xcode: npm run ios"
echo "לפתיחת Android Studio: npm run android"
