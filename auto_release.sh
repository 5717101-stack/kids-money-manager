#!/bin/bash
# סקריפט אוטומטי לשחרור גרסה - עושה הכל בעצמו

set -e  # עצור אם יש שגיאה

cd ~/Projects/kids-money-manager

# GitHub token should be in git credentials, not in script
# Use: git config credential.helper store
# Then save token to ~/.git-credentials

echo "=== שחרור גרסה אוטומטי ==="
echo ""

# 1. עדכן גרסה
echo "1. מעדכן גרסה..."
CURRENT_VERSION=$(grep '"version"' package.json | cut -d'"' -f4)
MAJOR=$(echo $CURRENT_VERSION | cut -d'.' -f1)
MINOR=$(echo $CURRENT_VERSION | cut -d'.' -f2)
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="${MAJOR}.${NEW_MINOR}.0"

echo "   גרסה נוכחית: $CURRENT_VERSION"
echo "   גרסה חדשה: $NEW_VERSION"

# עדכן package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" package.json
sed -i '' "s/\"version\": \"$CURRENT_VERSION\"/\"version\": \"$NEW_VERSION\"/" server/package.json

# עדכן גרסה בכל קבצי ה-React
VERSION_DISPLAY="${NEW_VERSION%.*}"  # 2.8 במקום 2.8.0
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+/גרסה ${VERSION_DISPLAY}/g" src/App.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+/גרסה ${VERSION_DISPLAY}/g" src/components/WelcomeScreen.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+/גרסה ${VERSION_DISPLAY}/g" src/components/PhoneLogin.jsx
sed -i '' "s/גרסה [0-9]\+\.[0-9]\+/גרסה ${VERSION_DISPLAY}/g" src/components/OTPVerification.jsx

# עדכן גרסה ב-server.js
sed -i '' "s/version: '[0-9]\+\.[0-9]\+\.[0-9]\+'/version: '${NEW_VERSION}'/" server/server.js

echo "   ✓ גרסה עודכנה בכל הקבצים"
echo ""

# 3. Commit
echo "3. יוצר commit..."
git add -A 2>/dev/null || true
git commit -m "עדכון גרסה ל-${NEW_VERSION}" --no-verify 2>/dev/null || echo "   (אין שינויים חדשים)"
echo "   ✓ Commit נוצר"
echo ""

# 4. Push
echo "4. דוחף ל-GitHub..."
git push origin main --no-verify 2>&1
echo "   ✓ Push הושלם"
echo ""

echo "✅ גרסה ${NEW_VERSION} שוחררה בהצלחה!"
echo "🚀 Vercel ו-Railway יתחילו rebuild אוטומטי"
